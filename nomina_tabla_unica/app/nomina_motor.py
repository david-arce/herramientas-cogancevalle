"""
Motor del presupuesto de nómina.

Todo lo que antes estaba repartido entre 34 tablas, ~150 vistas generadas y
los cálculos del navegador (presupuesto_calculos.js) vive aquí:

  1. CONCEPTOS  → qué es cada concepto, de dónde se carga, qué fórmula usa y
                  de qué otros conceptos depende.
  2. FÓRMULAS   → cómo se calculan los 12 meses de un concepto base.
  3. GENERADORES→ cómo se arman los conceptos que salen de otros
                  (cesantías, prima, seguridad social, ...).
  4. PROPAGAR   → cuando cambia un concepto o un parámetro, se recalculan
                  en orden todos los que dependen de él.

Regla de oro: una fila con origen='manual' nunca se sobrescribe.
"""
import unicodedata
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field

from django.db import connection, transaction
from django.db.models import Avg, Count, Q, Sum

from . import nomina_conceptos as origen
from .models import ParametrosPresupuestos
from .models_nomina import MESES, ConceptosNomina, DistribucionNomina, PresupuestoNomina

MESES = list(MESES)
SISTEMA = PresupuestoNomina.ORIGEN_SISTEMA
MANUAL = PresupuestoNomina.ORIGEN_MANUAL
CAMPOS_TEXTO = ('cedula', 'nombre', 'centro', 'area', 'cargo', 'concepto')
# Diferencia (en pesos) por debajo de la cual un valor se considera igual al
# calculado. Absorbe el redondeo que hace el navegador al distribuir.
TOLERANCIA = 2
LOCK_NOMINA = 874231002   # candado de PostgreSQL para no recalcular en paralelo


# ══════════════════════════════════════════════════════════════════════
#  Parámetros
# ══════════════════════════════════════════════════════════════════════

@dataclass
class Parametros:
    incremento_salarial: float = 0
    incremento_ipc: float = 0
    auxilio_transporte: float = 0
    cesantias: float = 0
    intereses_cesantias: float = 0
    prima: float = 0
    vacaciones: float = 0
    salario_minimo: float = 0
    incremento_comisiones: float = 0

    @classmethod
    def cargar(cls):
        fila = ParametrosPresupuestos.objects.first()
        if not fila:
            return cls()
        return cls(**{campo: float(getattr(fila, campo) or 0) for campo in cls.__dataclass_fields__})

    def pct(self, campo):
        return (getattr(self, campo, 0) or 0) / 100 if campo else 0

    @property
    def minimo_incrementado(self):
        return self.salario_minimo * (1 + self.incremento_salarial / 100)


# ══════════════════════════════════════════════════════════════════════
#  1. Catálogo de conceptos
# ══════════════════════════════════════════════════════════════════════

@dataclass
class Concepto:
    slug: str
    etiqueta: str
    grupo: str
    derivado: bool = False
    formula: str = None          # solo conceptos base (ver FORMULAS)
    pct: str = None              # campo de ParametrosPresupuestos que usa la fórmula
    con_minimo: bool = False     # sueldos: quien gana el mínimo sube desde enero
    titulo_base: str = None      # None → la tabla no muestra la columna "base"
    con_cedula: bool = True
    con_pegar: bool = False
    parametros: tuple = ()       # campos de parámetros que se muestran en la barra
    carga: dict = field(default_factory=dict)
    depende: tuple = ()

    def invertibles(self, fila, meses_reales):
        """Meses que, al editarlos, ajustan el histórico en vez de volver la fila manual."""
        if self.formula == 'incrementar':
            return set(MESES)
        if self.formula == 'incremento_promedio':
            propios = [m for m in MESES if m in (fila.historico or {})]
            return set(propios or MESES[:meses_reales])
        return set()


G_PRINCIPAL = 'Operaciones principales'
G_TRANSPORTE = 'Transporte y auxilios'
G_PRESTACIONES = 'Prestaciones y bonos'
G_SEGURIDAD = 'Seguridad y formación'

PRESTACION = ('sueldos', 'comisiones', 'medios_transporte', 'auxilio_transporte',
              'horas_extra', 'aprendiz')

_LISTA = [
    # ── Conceptos base: se cargan de ConceptosNomina ────────────────────
    # carga = {
    #   'filtro':    filtro sobre ConceptosNomina,
    #   'anio':      desfase respecto al año base (0 = año base, -1 = anterior),
    #   'historico': 'reales' → enero..último mes con datos (dinámico),
    #                o una lista fija de meses,
    #   'descartar': cuántos de los últimos meses reales NO se usan
    #                (el último suele venir incompleto),
    #   'base':      True → la base es CONCEPTO_F,
    #   'agrupar':   True → suma varios conceptos en una fila por persona,
    # }
    Concepto('sueldos', 'Sueldos', G_PRINCIPAL, formula='retroactivo',
             pct='incremento_salarial', con_minimo=True, titulo_base='Salario base',
             parametros=('incremento_salarial', 'salario_minimo'),
             carga={'filtro': {'concepto': '001'}, 'base': True}),
    Concepto('comisiones', 'Comisiones', G_PRINCIPAL, formula='incremento_promedio',
             pct='incremento_comisiones', con_pegar=True,
             parametros=('incremento_comisiones',),
             carga={'filtro': {'concepto': '389'}, 'historico': 'reales'}),
    Concepto('horas_extra', 'Horas extra', G_PRINCIPAL, formula='incremento_promedio',
             pct='incremento_salarial', parametros=('incremento_salarial',),
             carga={'filtro': {'concepto__in': ['114', '110', '111']},
                    'historico': 'reales', 'descartar': 1,
                    'agrupar': True, 'concepto': 'HORAS EXTRA'}),
    Concepto('medios_transporte', 'Medios de transporte', G_TRANSPORTE, formula='retroactivo',
             pct='incremento_ipc', titulo_base='Base', parametros=('incremento_ipc',),
             carga={'filtro': {'concepto': '011'}, 'base': True}),
    Concepto('ayuda_transporte', 'Ayuda de transporte', G_TRANSPORTE, formula='retroactivo',
             pct='incremento_ipc', titulo_base='Base', parametros=('incremento_ipc',),
             carga={'filtro': {'concepto': '013'}, 'base': True}),
    Concepto('bolsa_consumibles', 'Bolsa de consumibles (auxilio movilidad)', G_TRANSPORTE,
             formula='incrementar', pct='incremento_ipc', con_pegar=True,
             parametros=('incremento_ipc',),
             carga={'filtro': {'concepto': 'E14'}, 'historico': 'reales', 'descartar': 1}),
    Concepto('auxilio_tbckit', 'Auxilio TBC y KIT', G_TRANSPORTE, formula='incrementar',
             pct='incremento_ipc', parametros=('incremento_ipc',),
             carga={'filtro': {'concepto': 'E14'}, 'historico': 'reales'}),
    Concepto('auxilio_educacion', 'Auxilio de educación', G_TRANSPORTE, formula='incrementar',
             pct='incremento_ipc', con_pegar=True, parametros=('incremento_ipc',),
             carga={'filtro': {'concepto': '016'}, 'anio': -1,
                    'historico': ['diciembre']}),
    Concepto('aprendiz', 'Aprendices', G_SEGURIDAD, formula='base_fija',
             pct='incremento_salarial', titulo_base='Salario base',
             parametros=('incremento_salarial',),
             carga={'filtro': {'concepto__in': ['003', '006']}, 'base': True}),
    Concepto('bonos_kyrovet', 'Bonos Kyrovet', G_PRESTACIONES, formula='kyrovet',
             pct='incremento_ipc', titulo_base='Base', con_pegar=True,
             parametros=('incremento_ipc',),
             carga={'filtro': {'nombre_con__icontains': 'BONOS CANASTA KYROVET'}, 'base': True}),

    # ── Conceptos derivados: el ORDEN importa (topológico) ─────────────
    Concepto('auxilio_transporte', 'Auxilio de transporte', G_TRANSPORTE, derivado=True,
             titulo_base='Base', parametros=('auxilio_transporte', 'salario_minimo'),
             depende=('sueldos', 'comisiones', 'horas_extra', 'medios_transporte', 'aprendiz')),
    Concepto('cesantias', 'Cesantías', G_PRESTACIONES, derivado=True, pct='cesantias',
             parametros=('cesantias',), depende=PRESTACION),
    Concepto('prima', 'Prima', G_PRESTACIONES, derivado=True, pct='prima',
             parametros=('prima',), depende=PRESTACION),
    Concepto('vacaciones', 'Vacaciones', G_PRESTACIONES, derivado=True, pct='vacaciones',
             parametros=('vacaciones',),
             depende=('sueldos', 'comisiones', 'medios_transporte', 'aprendiz')),
    Concepto('intereses_cesantias', 'Intereses de cesantías', G_PRESTACIONES, derivado=True,
             pct='intereses_cesantias', parametros=('intereses_cesantias',),
             depende=('cesantias',)),
    Concepto('bonificaciones', 'Bonificaciones', G_PRESTACIONES, derivado=True,
             depende=('sueldos',)),
    Concepto('bonificaciones_foco', 'Bonificaciones foco', G_PRESTACIONES, derivado=True,
             parametros=('incremento_ipc', 'incremento_comisiones'),
             depende=('sueldos', 'comisiones')),
    Concepto('seguridad_social', 'Seguridad social', G_SEGURIDAD, derivado=True, parametros=('incremento_salarial', 'salario_minimo'),
             depende=('sueldos', 'medios_transporte', 'comisiones', 'horas_extra', 'aprendiz')),
]

CONCEPTOS = {c.slug: c for c in _LISTA}
BASE = [c for c in _LISTA if not c.derivado]
DERIVADOS = [c for c in _LISTA if c.derivado]
GRUPOS = [G_PRINCIPAL, G_TRANSPORTE, G_PRESTACIONES, G_SEGURIDAD]

ETIQUETAS_PARAMETRO = {
    'incremento_salarial': 'Incremento salarial (%)',
    'incremento_ipc': 'Incremento IPC (%)',
    'auxilio_transporte': 'Auxilio de transporte (%)',
    'cesantias': 'Cesantías (%)',
    'intereses_cesantias': 'Intereses de cesantías (%)',
    'prima': 'Prima (%)',
    'vacaciones': 'Vacaciones (%)',
    'salario_minimo': 'Salario mínimo',
    'incremento_comisiones': 'Incremento comisiones (%)',
}


def obtener(slug):
    concepto = CONCEPTOS.get(slug)
    if concepto is None:
        raise KeyError(f'Concepto de nómina desconocido: {slug}')
    return concepto


def afectados_por(slug):
    """Conceptos que se recalculan si cambia `slug` (en el orden en que se hace)."""
    cambiados, orden = {slug}, []
    for c in DERIVADOS:
        if cambiados.intersection(c.depende):
            orden.append(c.slug)
            cambiados.add(c.slug)
    return orden


# ══════════════════════════════════════════════════════════════════════
#  Utilidades
# ══════════════════════════════════════════════════════════════════════

def numero(valor, defecto=0.0):
    if valor in (None, ''):
        return defecto
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace(' ', '')
    if ',' in texto:                       # formato colombiano 1.234,56
        texto = texto.replace('.', '').replace(',', '.')
    try:
        return float(texto)
    except ValueError:
        return defecto


def texto(valor):
    return '' if valor is None else str(valor).strip()


def cedula_normalizada(valor):
    if valor in (None, ''):
        return ''
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    valor = str(valor).strip()
    return valor[:-2] if valor.endswith('.0') else valor


def valores(fila):
    return {mes: getattr(fila, mes) or 0 for mes in MESES}


def fijar_meses(fila, meses):
    for mes in MESES:
        setattr(fila, mes, int(round(meses.get(mes, 0) or 0)))
    fila.calcular_total()


def sumar_por(filas, clave):
    """{clave(fila): {mes: suma}}"""
    acumulado = defaultdict(lambda: dict.fromkeys(MESES, 0))
    for fila in filas:
        destino = acumulado[clave(fila)]
        for mes in MESES:
            destino[mes] += getattr(fila, mes) or 0
    return acumulado


def cuotas(filas, clave):
    """Parte (0‑1) de cada fila dentro de su grupo, según su `factor`.

    Si una persona está distribuida en tres filas (50/30/20), los valores que
    se calculan "por persona" se reparten igual y no se triplican.
    """
    sumas = defaultdict(float)
    for fila in filas:
        sumas[clave(fila)] += fila.factor or 0
    return {
        id(fila): ((fila.factor or 0) / sumas[clave(fila)]) if sumas[clave(fila)] else 0
        for fila in filas
    }


def identidad(fila, **extra):
    datos = {campo: getattr(fila, campo) or '' for campo in CAMPOS_TEXTO}
    # Lo que una fila excluye se hereda a lo que se calcula con ella
    # (p. ej. cesantías → intereses de cesantías).
    datos['excluir_de'] = list(getattr(fila, 'excluir_de', None) or [])
    datos.update(extra)
    return datos


def excluciones_validas(slug, valores):
    """Solo conceptos que realmente dependen de `slug`."""
    posibles = set(afectados_por(slug))
    return sorted({v for v in (valores or []) if v in posibles})


def es_aprendiz_reforma(fila):
    return (fila.concepto or '').strip().upper() == 'SALARIO APRENDIZ REFORMA'


@contextmanager
def bloqueo():
    """Transacción + candado de PostgreSQL (en otros motores solo transacción)."""
    with transaction.atomic():
        if connection.vendor == 'postgresql':
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_xact_lock(%s)', [LOCK_NOMINA])
        yield


# ══════════════════════════════════════════════════════════════════════
#  Cuentas contables (ligadas al NOMCOSTO)
# ══════════════════════════════════════════════════════════════════════

def _clave_area(area):
    """Área normalizada para comparar: sin tildes, mayúsculas, espacios simples."""
    return _sin_tildes(area)


def mapa_cuentas(anio=None):
    """{NOMCOSTO normalizado: cuenta}

    Cada NOMCOSTO (en presupuesto_nomina: `area`) corresponde a una cuenta.
    Si en los datos un NOMCOSTO aparece con varias cuentas, se toma la más
    frecuente. Se leen los datos del año base; si no tiene, los de cualquier año.
    """
    qs = ConceptosNomina.objects.exclude(cuenta='').exclude(nomcosto='')
    if anio is not None and qs.filter(anio=anio).exists():
        qs = qs.filter(anio=anio)
    conteo = defaultdict(Counter)
    for nomcosto, cuenta, n in qs.values_list('nomcosto', 'cuenta').annotate(n=Count('id')):
        conteo[_clave_area(nomcosto)][cuenta] += n
    return {area: c.most_common(1)[0][0] for area, c in conteo.items()}


def cuenta_para(mapa, area):
    return mapa.get(_clave_area(area), '') if texto(area) else ''


def asignar_cuentas(ctx=None, solo_vacias=False):
    """Pone a cada fila guardada la cuenta de su área (NOMCOSTO).
    Las áreas que no están en ConceptosNomina conservan su cuenta."""
    ctx = ctx or Contexto()
    qs = PresupuestoNomina.objects.exclude(area='')
    if solo_vacias:
        qs = qs.filter(cuenta='')
    cambiadas = []
    for fila in qs.only('id', 'area', 'cuenta'):
        cuenta = ctx.cuenta(fila.area)
        if cuenta and cuenta != fila.cuenta:
            fila.cuenta = cuenta
            cambiadas.append(fila)
    PresupuestoNomina.objects.bulk_update(cambiadas, ['cuenta'], batch_size=1000)
    return len(cambiadas)


class Contexto:
    """Lee cada concepto una sola vez por operación."""

    def __init__(self, parametros=None):
        self.p = parametros or Parametros.cargar()
        self._cache = {}
        self._meses = {}
        self.anio = origen.anio_base()

    def anio_de(self, c):
        return self.anio + (c.carga.get('anio') or 0)

    def meses_reales(self, anio=None):
        """Meses con datos reales de ese año (1‑12); se consulta una vez."""
        anio = anio or self.anio
        if anio not in self._meses:
            self._meses[anio] = origen.meses_reales(anio)
        return self._meses[anio]

    def meses_historico(self, c):
        """Meses que se leen como histórico para el concepto `c`."""
        spec = c.carga.get('historico', [])
        if spec != 'reales':
            return list(spec)
        n = self.meses_reales(self.anio_de(c)) - (c.carga.get('descartar') or 0)
        return MESES[:max(n, 1)]

    derivado_actual = None   # lo fija regenerar(): las filas que lo excluyen no se ven

    def filas(self, slug):
        if slug not in self._cache:
            self._cache[slug] = list(PresupuestoNomina.objects.filter(tipo=slug).order_by('id'))
        filas = self._cache[slug]
        actual = self.derivado_actual
        if actual and slug != actual:
            filas = [f for f in filas if actual not in (f.excluir_de or [])]
        return filas

    # ---------------------------------------------------------- cuentas
    def cuenta(self, area, tipo=None):
        """Cuenta del área (NOMCOSTO). `tipo` se ignora: la cuenta depende solo del área."""
        if not hasattr(self, '_cuentas'):
            self._cuentas = mapa_cuentas(self.anio)
        return cuenta_para(self._cuentas, area)

    def olvidar(self, slug):
        self._cache.pop(slug, None)

    def personas(self):
        """Empleados de nómina + aprendices con salario de reforma."""
        return self.filas('sueldos') + [a for a in self.filas('aprendiz') if es_aprendiz_reforma(a)]


# ══════════════════════════════════════════════════════════════════════
#  2. Fórmulas de los conceptos base   (antes: presupuesto_calculos.js)
#     Devuelven los 12 meses SIN aplicar el factor de distribución.
# ══════════════════════════════════════════════════════════════════════

def f_retroactivo(fila, c, p):
    """Enero y febrero con la base anterior; en marzo se paga el nuevo valor
    más el retroactivo de enero y febrero; de abril en adelante, el nuevo."""
    base = fila.base or 0
    if c.con_minimo and p.salario_minimo and 0 < base <= p.salario_minimo:
        # El salario mínimo sube por decreto desde enero: sin retroactivo.
        return dict.fromkeys(MESES, p.minimo_incrementado)
    nuevo = base * (1 + p.pct(c.pct))
    meses = dict.fromkeys(MESES, nuevo)
    meses['enero'] = meses['febrero'] = base
    meses['marzo'] = nuevo + 2 * (nuevo - base)
    return meses


def f_base_fija(fila, c, p):
    return dict.fromkeys(MESES, (fila.base or 0) * (1 + p.pct(c.pct)))


def f_incrementar(fila, c, p):
    factor = 1 + p.pct(c.pct)
    historico = fila.historico or {}
    return {mes: numero(historico.get(mes)) * factor for mes in MESES}


def f_incremento_promedio(fila, c, p):
    """Meses con dato real: histórico + incremento. Meses sin dato: su promedio.

    Los meses con dato son los que trae el histórico de la fila (enero hasta el
    último mes cargado), así funciona igual con datos hasta agosto que hasta
    noviembre.
    """
    factor = 1 + p.pct(c.pct)
    historico = fila.historico or {}
    base = [mes for mes in MESES if mes in historico]
    meses = {mes: numero(historico.get(mes)) * factor for mes in base}
    promedio = sum(meses.values()) / len(base) if base else 0
    for mes in MESES:
        meses.setdefault(mes, promedio)
    return meses


def f_kyrovet(fila, c, p):
    meses = dict.fromkeys(MESES, 0)
    meses['febrero'] = (fila.base or 0) * (1 + p.pct(c.pct))
    return meses


FORMULAS = {
    'retroactivo': f_retroactivo,
    'base_fija': f_base_fija,
    'incrementar': f_incrementar,
    'incremento_promedio': f_incremento_promedio,
    'kyrovet': f_kyrovet,
}


def calcular(fila, c, p):
    """Los 12 meses que le corresponden a la fila según su fórmula y factor."""
    meses = FORMULAS[c.formula](fila, c, p)
    factor = fila.factor if fila.factor is not None else 1
    return {mes: int(round((meses.get(mes) or 0) * factor)) for mes in MESES}


def aplicar_formula(fila, c, p):
    fijar_meses(fila, calcular(fila, c, p))


def ajustar_historico(fila, c, p, mes, valor):
    """Inverso de la fórmula: el usuario escribió `valor` para `mes`."""
    divisor = (1 + p.pct(c.pct)) * (fila.factor or 1)
    historico = dict(fila.historico or {})
    historico[mes] = valor / divisor if divisor else 0
    fila.historico = historico


# ══════════════════════════════════════════════════════════════════════
#  Carga de conceptos base desde ConceptosNomina (filtrado por año)
# ══════════════════════════════════════════════════════════════════════

def filas_de_conceptos(c, ctx):
    p = ctx.p
    carga = c.carga
    historico = ctx.meses_historico(c)
    ident = ['cedula', 'nombre', 'nombrecar', 'nomcosto', 'nombre_cen']
    consulta = ConceptosNomina.objects.filter(anio=ctx.anio_de(c), **carga['filtro'])
    campos_extra = [] if carga.get('agrupar') else ['cuenta']   # respaldo si el área no tiene mapa

    if carga.get('agrupar'):
        # alias con prefijo: anotar con el mismo nombre del campo ("enero")
        # hace fallar a Django — era un error de la versión anterior.
        anotaciones = {f's_{mes}': Sum(mes) for mes in historico}
        anotaciones['s_concepto_f'] = Sum('concepto_f')
        registros = consulta.values(*ident).annotate(**anotaciones).order_by(*ident)
        leer = lambda r, campo: r.get(f's_{campo}')  # noqa: E731
    else:
        registros = consulta.values(*ident, *campos_extra, 'nombre_con', 'concepto_f', *historico).order_by('pk')
        leer = lambda r, campo: r.get(campo)  # noqa: E731

    filas = []
    for i, r in enumerate(registros):
        cedula = cedula_normalizada(r['cedula'])
        fila = PresupuestoNomina(
            tipo=c.slug, origen=SISTEMA, clave=f'{cedula}#{i}',
            centro_origen=texto(r['nombre_cen']), area_origen=texto(r['nomcosto']),
            cedula=cedula, nombre=texto(r['nombre']),
            cuenta=ctx.cuenta(r['nomcosto']) or texto(r.get('cuenta')),
            cargo=texto(r['nombrecar']), area=texto(r['nomcosto']), centro=texto(r['nombre_cen']),
            concepto=carga.get('concepto') or texto(r.get('nombre_con')) or c.etiqueta.upper(),
            base=int(round(numero(leer(r, 'concepto_f')))) if carga.get('base') else 0,
            historico={mes: numero(leer(r, mes)) for mes in historico},
        )
        aplicar_formula(fila, c, p)
        filas.append(fila)
    # Las distribuciones por persona se aplican siempre al cargar
    return distribuir_filas(c, filas, repartos(), p, ctx=ctx)


# ══════════════════════════════════════════════════════════════════════
#  Distribución por persona (se define una vez, en la vista consolidada)
# ══════════════════════════════════════════════════════════════════════

def repartos(cedulas=None):
    """{cedula: [(centro, area, porcentaje), ...]}"""
    qs = DistribucionNomina.objects.all()
    if cedulas is not None:
        qs = qs.filter(cedula__in=list(cedulas))
    salida = defaultdict(list)
    for d in qs.order_by('cedula', 'id'):
        salida[d.cedula].append((d.centro, d.area, d.porcentaje))
    return dict(salida)


def distribuir_filas(c, filas, reparto_por_cedula, p, usuario='', ctx=None):
    """Reparte las filas de las personas de `reparto_por_cedula`.

    Las filas que salieron de un mismo registro (misma `clave`) se tratan como
    un todo: se juntan y se vuelven a repartir. Un reparto vacío devuelve la
    fila completa a su centro/área de origen.
      - filas calculadas → cada copia guarda su porcentaje en `factor` y sigue
                            recalculándose sola.
      - filas manuales   → se reparten sus valores y siguen siendo manuales.
    """
    if not reparto_por_cedula:
        return filas
    ctx = ctx or Contexto(p)
    salida, grupos = [], {}
    for fila in filas:
        if fila.cedula and fila.cedula in reparto_por_cedula:
            clave = fila.clave or f'{fila.cedula}#m{fila.pk or id(fila)}'
            grupos.setdefault(clave, []).append(fila)
        else:
            salida.append(fila)

    for clave, miembros in grupos.items():
        ref = miembros[0]
        centro0 = ref.centro_origen or ref.centro
        area0 = ref.area_origen or ref.area
        destinos = reparto_por_cedula[ref.cedula] or [(centro0, area0, 100.0)]
        sistema = all(m.origen == SISTEMA for m in miembros)
        entero = {mes: sum(getattr(m, mes) or 0 for m in miembros) for mes in MESES}
        for centro, area, porcentaje in destinos:
            parte = (porcentaje or 0) / 100
            if parte <= 0:
                continue
            nueva = PresupuestoNomina(
                tipo=ref.tipo, origen=SISTEMA if sistema else MANUAL, clave=clave,
                cedula=ref.cedula, nombre=ref.nombre, cargo=ref.cargo, concepto=ref.concepto,
                centro=centro, area=area, centro_origen=centro0, area_origen=area0,
                base=ref.base or 0, historico=dict(ref.historico or {}), factor=parte,
                excluir_de=list(ref.excluir_de or []),
                cuenta=ctx.cuenta(area) or (ref.cuenta if _clave_area(area) == _clave_area(ref.area) else ''),
                actualizado_por=usuario or ref.actualizado_por,
            )
            if sistema:
                aplicar_formula(nueva, c, p)
            else:
                fijar_meses(nueva, {mes: entero[mes] * parte for mes in MESES})
            salida.append(nueva)
    return salida


def _normalizar_reparto(reparto):
    limpio = {}
    for r in reparto or []:
        porcentaje = numero(r.get('porcentaje'))
        if porcentaje <= 0:
            continue
        area = texto(r.get('area')).upper()
        if not area:
            raise ValueError('Cada destino necesita un área (NOMCOSTO)')
        clave = (texto(r.get('centro')).upper(), area)
        limpio[clave] = limpio.get(clave, 0) + porcentaje
    if limpio and abs(sum(limpio.values()) - 100) > 0.01:
        raise ValueError(f'Los porcentajes deben sumar 100% (suman {sum(limpio.values()):g}%)')
    return [(centro, area, pct) for (centro, area), pct in limpio.items()]


def aplicar_distribucion(cedulas, usuario=''):
    """Vuelve a repartir todas las filas base de esas personas y recalcula los derivados."""
    cedulas = sorted({cedula_normalizada(c) for c in cedulas} - {''})
    ctx = Contexto()
    actual = repartos(cedulas)
    por_cedula = {c: actual.get(c, []) for c in cedulas}
    filas_nuevas = 0
    with bloqueo():
        for c in BASE:
            filas = list(PresupuestoNomina.objects.filter(tipo=c.slug, cedula__in=cedulas).order_by('id'))
            if not filas:
                continue
            nuevas = distribuir_filas(c, filas, por_cedula, ctx.p, usuario, ctx=ctx)
            PresupuestoNomina.objects.filter(pk__in=[f.pk for f in filas]).delete()
            PresupuestoNomina.objects.bulk_create(nuevas, batch_size=1000)
            filas_nuevas += len(nuevas)
        # Los ajustes manuales de derivados quedaron con el centro/área anterior
        descartadas, _ = PresupuestoNomina.objects.filter(
            tipo__in=[c.slug for c in DERIVADOS], cedula__in=cedulas, origen=MANUAL).delete()
        for c in DERIVADOS:
            regenerar(ctx, c)
    return {'personas': len(cedulas), 'filas': filas_nuevas, 'descartadas': descartadas}


def guardar_distribucion(cedulas, reparto, usuario=''):
    cedulas = sorted({cedula_normalizada(c) for c in cedulas} - {''})
    if not cedulas:
        raise ValueError('Seleccione al menos una persona con cédula')
    destinos = _normalizar_reparto(reparto)
    if not destinos:
        raise ValueError('Ingrese al menos un porcentaje')
    with transaction.atomic():
        DistribucionNomina.objects.filter(cedula__in=cedulas).delete()
        DistribucionNomina.objects.bulk_create([
            DistribucionNomina(cedula=ced, centro=centro, area=area, porcentaje=pct,
                               actualizado_por=usuario)
            for ced in cedulas for centro, area, pct in destinos
        ])
        return aplicar_distribucion(cedulas, usuario)


def quitar_distribucion(cedulas, usuario=''):
    cedulas = sorted({cedula_normalizada(c) for c in cedulas} - {''})
    with transaction.atomic():
        DistribucionNomina.objects.filter(cedula__in=cedulas).delete()
        return aplicar_distribucion(cedulas, usuario)


def listar_distribuciones():
    nombres = dict(PresupuestoNomina.objects.filter(tipo__in=[c.slug for c in BASE])
                   .exclude(cedula='').values_list('cedula', 'nombre'))
    salida = []
    for cedula, destinos in repartos().items():
        salida.append({
            'cedula': cedula, 'nombre': nombres.get(cedula, ''),
            'reparto': [{'centro': c, 'area': a, 'porcentaje': p} for c, a, p in destinos],
        })
    return sorted(salida, key=lambda d: d['nombre'] or d['cedula'])


# ══════════════════════════════════════════════════════════════════════
#  3. Generadores de los conceptos derivados
#     Cada uno devuelve dicts con: identidad, meses, base (opcional) y clave.
# ══════════════════════════════════════════════════════════════════════

def clave_persona(fila):
    return f'{fila.cedula}|{fila.centro}|{fila.area}'


AUXILIO_TRANSPORTE_BASE = 200000


def gen_auxilio_transporte(ctx, c):
    """Auxilio para quien devengue menos de 2 salarios mínimos en el mes."""
    p = ctx.p
    limite = p.minimo_incrementado * 2
    valor = AUXILIO_TRANSPORTE_BASE * (1 + p.pct('auxilio_transporte'))
    por_cedula = lambda f: f.cedula  # noqa: E731
    totales = {t: sumar_por(ctx.filas(t), por_cedula)
               for t in ('medios_transporte', 'sueldos', 'comisiones', 'horas_extra', 'aprendiz')}
    personas = ctx.personas()
    cuota = cuotas(personas, por_cedula)

    for persona in personas:
        meses = dict.fromkeys(MESES, 0)
        for mes in MESES:
            devengado = sum(t.get(persona.cedula, {}).get(mes, 0) for t in totales.values())
            if mes == 'marzo':
                # marzo trae el retroactivo: se compara con el sueldo de abril
                sueldo = totales['sueldos'].get(persona.cedula, {})
                devengado += sueldo.get('abril', 0) - sueldo.get('marzo', 0)
            if devengado and devengado < limite:
                meses[mes] = valor * cuota[id(persona)]
        yield dict(identidad(persona, concepto='AUXILIO DE TRANSPORTE'),
                   base=AUXILIO_TRANSPORTE_BASE, clave=clave_persona(persona), **meses)


def _prestacion(ctx, c, fuentes, concepto):
    """Suma de lo que devenga cada persona × el porcentaje de la prestación.

    La fila propia (sueldo o salario de aprendiz) se toma completa; lo que
    viene de otras tablas se busca por (cédula, área) y se reparte entre las
    filas de la persona según su factor, para no contarlo dos veces.
    """
    pct = ctx.p.pct(c.pct)
    por_clave = lambda f: (f.cedula, f.area)  # noqa: E731
    indices = {t: sumar_por(ctx.filas(t), por_clave) for t in fuentes}
    personas = ctx.personas()
    cuota = cuotas(personas, por_clave)

    for persona in personas:
        meses = valores(persona)
        for tipo, indice in indices.items():
            if tipo == persona.tipo:
                continue
            otros = indice.get(por_clave(persona))
            if otros:
                parte = cuota[id(persona)]
                for mes in MESES:
                    meses[mes] += otros[mes] * parte
        yield dict(identidad(persona, concepto=concepto), clave=clave_persona(persona),
                   **{mes: v * pct for mes, v in meses.items()})


def gen_cesantias(ctx, c):
    return _prestacion(ctx, c, PRESTACION, 'CESANTÍAS')


def gen_prima(ctx, c):
    return _prestacion(ctx, c, PRESTACION, 'PRIMA LEGAL')


def gen_vacaciones(ctx, c):
    return _prestacion(ctx, c, ('comisiones', 'medios_transporte'), 'VACACIONES')


def gen_intereses_cesantias(ctx, c):
    """Interés mensual = cesantía del mes × % de intereses."""
    pct = ctx.p.pct(c.pct)
    for ces in ctx.filas('cesantias'):
        yield dict(identidad(ces, concepto='INTERESES CESANTÍAS'), clave=clave_persona(ces),
                   **{mes: v * pct for mes, v in valores(ces).items()})


def gen_bonificaciones(ctx, c):
    """Media prestación mensual: (valor del mes / 2) / 12."""
    for emp in ctx.filas('sueldos'):
        yield dict(identidad(emp, concepto='BONIFICACIÓN'), clave=clave_persona(emp),
                   **{mes: v / 2 / 12 for mes, v in valores(emp).items()})


CARGOS_SIN_BONIFICACION_FOCO = {
    'ASESOR COMERCIAL',
    'AUXILIAR COMERCIAL',
    'JEFE DE ALMACEN',
    'DIRECTOR COMERCIAL SUBDISTRIBUCION Y DIGITAL',
    'DIRECTOR COMERCIAL GRANDES ESPECIES Y PUNTO VENTA',
}
BONIFICACION_FOCO_FIJA = 220000


def gen_bonificaciones_foco(ctx, c):
    p = ctx.p
    factor = 1 + p.pct('incremento_comisiones')

    # 1) Con comisiones: enero = promedio anual sin el incremento;
    #    julio = mitad del promedio de enero–junio.
    grupos = defaultdict(lambda: dict.fromkeys(MESES, 0))
    ejemplo = {}
    for fila in ctx.filas('comisiones'):
        k = (fila.cedula, fila.nombre, fila.centro, fila.area, fila.cargo)
        ejemplo.setdefault(k, fila)
        for mes in MESES:
            grupos[k][mes] += getattr(fila, mes) or 0

    for k, meses in grupos.items():
        total_ajustado = sum(meses.values()) / factor if factor else 0
        primer_semestre = sum(meses[m] for m in MESES[:6])
        datos = dict.fromkeys(MESES, 0)
        datos['enero'] = total_ajustado / 12
        datos['julio'] = primer_semestre / 6 / 2
        yield dict(identidad(ejemplo[k], concepto='BONIFICACIÓN FOCO'),
                   clave=clave_persona(ejemplo[k]), **datos)

    # 2) El resto de la planta: bonificación fija + IPC en enero.
    fijos = [f for f in ctx.filas('sueldos')
             if (f.cargo or '').strip().upper() not in CARGOS_SIN_BONIFICACION_FOCO]
    cuota = cuotas(fijos, lambda f: f.cedula)
    enero = BONIFICACION_FOCO_FIJA * (1 + p.pct('incremento_ipc'))
    for fila in fijos:
        datos = dict.fromkeys(MESES, 0)
        datos['enero'] = enero * cuota[id(fila)]
        yield dict(identidad(fila, concepto='BONIFICACIÓN FOCO'), clave=clave_persona(fila), **datos)


APORTES = {
    'APORTE PENSIÓN': 0.12,
    'APORTE SALUD': 0.085,
    'APORTE CAJAS DE COMPENSACIÓN': 0.04,
    'APORTE A.R.L': None,        # sale del promedio real de arlporc
    'APORTE SENA': 0.02,
    'APORTE I.C.B.F': 0.03,
}
APORTES_SOLO_ALTOS = {'APORTE SALUD', 'APORTE SENA', 'APORTE I.C.B.F'}
ARL_POR_DEFECTO = 0.0093
APORTE_SALUD_APRENDIZ = 0.125
# Técnicos: su seguridad social se calcula por persona (no se consolida por área)
AREAS_POR_PERSONA = {'ASISTENCIA TECNICA PROPIA', 'ASISTENCIA TECNICA CONVENIO'}
# Estas áreas se consolidan sin centro
AREAS_AGRUPADAS = [
    ['PROYECTO AFTOSA GASTOS DE PERSONAL'],
]
CEDULA_ESPECIAL = '31793592'     # tratamiento heredado del cálculo original


def porcentajes_arl(anio):
    promedios = (ConceptosNomina.objects.filter(anio=anio, arlporc__isnull=False)
                 .values('nombre_cen', 'nomcosto')
                 .annotate(promedio=Avg('arlporc')))
    return {
        (texto(p['nombre_cen']), texto(p['nomcosto'])): round((p['promedio'] or 0) / 100.0, 4)
        for p in promedios if p['promedio'] is not None
    }


def _sin_tildes(valor):
    valor = unicodedata.normalize('NFKD', texto(valor)).encode('ascii', 'ignore').decode()
    return ' '.join(valor.upper().split())


def llave_seguridad_social(fila):
    """(centro, área, cédula, nombre, cargo): la persona solo cuenta en áreas de técnicos."""
    if _sin_tildes(fila.area) in AREAS_POR_PERSONA:
        return (fila.centro, fila.area, fila.cedula, fila.nombre, fila.cargo)
    return (fila.centro, fila.area, '', '', '')


def gen_seguridad_social(ctx, c):
    p = ctx.p
    tope = p.minimo_incrementado * 10
    arl = porcentajes_arl(ctx.anio)
    generales = defaultdict(lambda: dict.fromkeys(MESES, 0))
    altos = defaultdict(lambda: dict.fromkeys(MESES, 0))
    aprendices_salud = defaultdict(lambda: dict.fromkeys(MESES, 0))

    def sumar(destino, fila, meses=None):
        meses = meses or valores(fila)
        for mes in MESES:
            destino[llave_seguridad_social(fila)][mes] += meses[mes]

    hay_altos = False
    for emp in ctx.filas('sueldos'):
        sumar(generales, emp)
        if (emp.base or 0) * (1 + p.pct('incremento_salarial')) > tope:
            hay_altos = True
            sumar(altos, emp)

    for tipo in ('medios_transporte', 'comisiones', 'horas_extra'):
        for fila in ctx.filas(tipo):
            sumar(generales, fila)
            if hay_altos and fila.cedula == CEDULA_ESPECIAL:
                sumar(altos, fila)

    for apr in ctx.filas('aprendiz'):
        # el aprendiz cotiza siempre sobre un salario mínimo incrementado
        meses = {m: (p.minimo_incrementado if v > 0 else v) for m, v in valores(apr).items()}
        destino = aprendices_salud if (apr.concepto or '').strip().upper() == 'SALARIO APRENDIZ' else generales
        sumar(destino, apr, meses)
        if hay_altos and apr.cedula == CEDULA_ESPECIAL:
            sumar(altos, apr, meses)

    def mas(a, b):
        return {m: a[m] + b[m] for m in MESES}

    filas = []
    llaves = list(generales) + [k for k in aprendices_salud if k not in generales]
    for llave in llaves:
        centro, area, cedula, nombre, cargo = llave
        base = generales.get(llave, dict.fromkeys(MESES, 0))
        for aporte, porcentaje in APORTES.items():
            if aporte in APORTES_SOLO_ALTOS:
                datos = altos.get(llave)
                if aporte == 'APORTE SALUD' and llave in aprendices_salud:
                    aprendiz = aprendices_salud[llave]
                    datos = mas(datos, aprendiz) if datos else aprendiz
                    porcentaje = APORTE_SALUD_APRENDIZ
                if not datos:
                    continue
            elif aporte == 'APORTE A.R.L':
                datos = base
                if llave in aprendices_salud:
                    datos = mas(base, aprendices_salud[llave])
                porcentaje = arl.get((centro, area), ARL_POR_DEFECTO)
            else:
                datos = base
            if not any(datos.values()):
                continue
            filas.append({'centro': centro, 'area': area, 'concepto': aporte,
                          'cedula': cedula, 'nombre': nombre or 'SEGURIDAD SOCIAL', 'cargo': cargo,
                          **{m: datos[m] * porcentaje for m in MESES}})

    # Ciertas áreas se consolidan sin centro (asistencia técnica, aftosa)
    agrupables = {area for grupo in AREAS_AGRUPADAS for area in grupo}
    agrupado = defaultdict(lambda: dict.fromkeys(MESES, 0))
    salida = []
    for fila in filas:
        if fila['area'] in agrupables and not fila['cedula']:
            destino = agrupado[(fila['area'], fila['concepto'])]
            for m in MESES:
                destino[m] += fila[m]
        else:
            salida.append(fila)
    for (area, concepto), meses in agrupado.items():
        salida.append({'centro': '', 'area': area, 'concepto': concepto, 'cedula': '',
                       'nombre': 'SEGURIDAD SOCIAL', 'cargo': '', **meses})

    for fila in salida:
        yield dict(fila, clave=f"{fila['centro']}|{fila['area']}|{fila['cedula']}|{fila['concepto']}")


GENERADORES = {
    'auxilio_transporte': gen_auxilio_transporte,
    'cesantias': gen_cesantias,
    'prima': gen_prima,
    'vacaciones': gen_vacaciones,
    'intereses_cesantias': gen_intereses_cesantias,
    'bonificaciones': gen_bonificaciones,
    'bonificaciones_foco': gen_bonificaciones_foco,
    'seguridad_social': gen_seguridad_social,
}


# ══════════════════════════════════════════════════════════════════════
#  4. Operaciones: regenerar, propagar, cargar, guardar, borrar
# ══════════════════════════════════════════════════════════════════════

def regenerar(ctx, c):
    """Recalcula un concepto derivado respetando las filas manuales."""
    bloqueadas = {f.clave for f in ctx.filas(c.slug) if f.origen == MANUAL and f.clave}
    vistas = Counter()
    nuevas = []
    ctx.derivado_actual = c.slug
    try:
        generados = list(GENERADORES[c.slug](ctx, c))
    finally:
        ctx.derivado_actual = None
    for datos in generados:
        clave = datos.pop('clave')
        vistas[clave] += 1
        if vistas[clave] > 1:
            clave = f'{clave}#{vistas[clave]}'
        if clave in bloqueadas:
            continue
        meses = {m: datos.pop(m, 0) for m in MESES}
        datos.setdefault('cuenta', ctx.cuenta(datos.get('area')))
        fila = PresupuestoNomina(tipo=c.slug, origen=SISTEMA, clave=clave, **datos)
        fijar_meses(fila, meses)
        nuevas.append(fila)

    PresupuestoNomina.objects.filter(tipo=c.slug, origen=SISTEMA).delete()
    PresupuestoNomina.objects.bulk_create(nuevas, batch_size=1000)
    ctx.olvidar(c.slug)
    return len(nuevas)


def propagar(slug, ctx=None):
    """Recalcula en cascada todo lo que depende de `slug`."""
    ctx = ctx or Contexto()
    hechos = []
    for dependiente in afectados_por(slug):
        regenerar(ctx, CONCEPTOS[dependiente])
        hechos.append(dependiente)
    return hechos


def recalcular_todo():
    """Tras cambiar parámetros: fórmulas de los conceptos base + todos los derivados."""
    ctx = Contexto()
    with bloqueo():
        for c in BASE:
            automaticas = [f for f in ctx.filas(c.slug) if f.origen == SISTEMA]
            for fila in automaticas:
                aplicar_formula(fila, c, ctx.p)
            PresupuestoNomina.objects.bulk_update(automaticas, MESES + ['total'], batch_size=1000)
        for c in DERIVADOS:
            regenerar(ctx, c)
        asignar_cuentas(ctx)
    return [c.slug for c in _LISTA]


def cargar_base(slug):
    """Concepto base: reemplaza todo con lo de Conceptos.
    Concepto derivado: lo regenera (conserva las filas manuales)."""
    c = obtener(slug)
    ctx = Contexto()
    with bloqueo():
        if c.derivado:
            creadas = regenerar(ctx, c)
        else:
            filas = filas_de_conceptos(c, ctx)
            PresupuestoNomina.objects.filter(tipo=slug).delete()
            PresupuestoNomina.objects.bulk_create(filas, batch_size=1000)
            ctx.olvidar(slug)
            creadas = len(filas)
        recalculados = propagar(slug, ctx)
    return creadas, recalculados


def recargar_bases():
    """Vuelve a cargar TODOS los conceptos base desde ConceptosNomina
    (p. ej. tras subir un Excel nuevo) y recalcula los derivados.
    Reemplaza las filas de los conceptos base, incluidas las manuales."""
    ctx = Contexto()
    conteo = {}
    with bloqueo():
        for c in BASE:
            filas = filas_de_conceptos(c, ctx)
            PresupuestoNomina.objects.filter(tipo=c.slug).delete()
            PresupuestoNomina.objects.bulk_create(filas, batch_size=1000)
            ctx.olvidar(c.slug)
            conteo[c.slug] = len(filas)
        for c in DERIVADOS:
            regenerar(ctx, c)
    return conteo


def borrar(slug):
    c = obtener(slug)
    ctx = Contexto()
    with bloqueo():
        eliminadas, _ = PresupuestoNomina.objects.filter(tipo=slug).delete()
        if c.derivado:       # "borrar" un derivado = descartar ajustes manuales
            regenerar(ctx, c)
        recalculados = propagar(slug, ctx)
    return eliminadas, recalculados


def _cambio(antes, fila):
    return any(antes[campo] != getattr(fila, campo)
               for campo in (*CAMPOS_TEXTO, 'base', *MESES))


def guardar(slug, filas_json, usuario=''):
    """Guarda lo que el usuario editó en la tabla y propaga los cambios.

    - Fila nueva                              → manual
    - Fila calculada con meses editados       → ajusta el histórico si la
                                                fórmula lo permite; si no, manual
    - Fila calculada de un derivado editada   → manual (conserva su clave)
    - Fila con `_recalcular`                  → vuelve a ser calculada
    - Fila calculada eliminada de un derivado → queda manual en cero, para que
                                                el motor no la vuelva a crear
    """
    c = obtener(slug)
    ctx = Contexto()
    p = ctx.p
    resumen = Counter()

    with bloqueo():
        existentes = {f.pk: f for f in ctx.filas(slug)}
        crear, actualizar, forzadas = [], [], False

        for datos in filas_json:
            try:
                pk = int(datos.get('id') or 0)
            except (TypeError, ValueError):
                pk = 0
            fila = existentes.pop(pk, None)
            nueva = fila is None
            antes = None
            if nueva:
                fila = PresupuestoNomina(tipo=slug, origen=MANUAL)
            else:
                antes = {campo: getattr(fila, campo) for campo in (*CAMPOS_TEXTO, 'base', *MESES)}

            for campo in CAMPOS_TEXTO:
                valor = texto(datos.get(campo))
                setattr(fila, campo, cedula_normalizada(valor) if campo == 'cedula' else valor)
            if 'excluir_de' in datos or nueva:
                excluir = excluciones_validas(slug, datos.get('excluir_de'))
                if not nueva and excluir != sorted(fila.excluir_de or []):
                    resumen['exclusiones'] += 1
                fila.excluir_de = excluir
            # la cuenta la define el área (NOMCOSTO)
            misma_area = not nueva and _clave_area(antes['area']) == _clave_area(fila.area)
            fila.cuenta = ctx.cuenta(fila.area) or (fila.cuenta if misma_area else '')
            fila.base = int(round(numero(datos.get('base'))))
            factor = numero(datos.get('factor'), 1)
            fila.factor = factor if factor > 0 else 1
            entrantes = {m: int(round(numero(datos.get(m)))) for m in MESES}
            fila.actualizado_por = usuario

            forzar = bool(datos.get('_recalcular'))
            if forzar:
                fila.origen = SISTEMA
                forzadas = True
                invertibles = c.invertibles(fila, ctx.meses_reales())
                if not c.derivado and not fila.historico and invertibles:
                    # fila escrita a mano: sus valores pasan a ser el histórico
                    divisor = fila.factor or 1
                    fila.historico = {m: entrantes[m] / divisor for m in invertibles}

            if not c.derivado and fila.origen == SISTEMA:
                calculado = calcular(fila, c, p)
                editados = {m for m in MESES if abs(entrantes[m] - calculado[m]) > TOLERANCIA}
                if editados and not forzar:
                    if editados <= c.invertibles(fila, ctx.meses_reales()):
                        for mes in editados:
                            ajustar_historico(fila, c, p, mes, entrantes[mes])
                        calculado = calcular(fila, c, p)
                        resumen['historico_ajustado'] += 1
                    else:
                        fila.origen = MANUAL
                fijar_meses(fila, calculado if fila.origen == SISTEMA else entrantes)
            else:
                fijar_meses(fila, entrantes)
                if c.derivado and not nueva and not forzar and fila.origen == SISTEMA and _cambio(antes, fila):
                    fila.origen = MANUAL

            if fila.origen == MANUAL and (nueva or antes is None or _cambio(antes, fila)):
                resumen['manuales'] += 1
            (crear if nueva else actualizar).append(fila)

        # Filas que el usuario quitó de la tabla
        eliminar = []
        for fila in existentes.values():
            if c.derivado and fila.origen == SISTEMA:
                fila.origen = MANUAL
                fila.actualizado_por = usuario
                fijar_meses(fila, {})
                actualizar.append(fila)
            else:
                eliminar.append(fila.pk)

        campos = [*CAMPOS_TEXTO, 'cuenta', 'excluir_de', 'base', 'factor', 'historico',
                  *MESES, 'total', 'origen', 'actualizado_por']
        PresupuestoNomina.objects.filter(pk__in=eliminar).delete()
        PresupuestoNomina.objects.bulk_update(actualizar, campos, batch_size=1000)
        PresupuestoNomina.objects.bulk_create(crear, batch_size=1000)
        ctx.olvidar(slug)

        if c.derivado and forzadas:
            regenerar(ctx, c)
        recalculados = propagar(slug, ctx)

    resumen.update(creadas=len(crear), actualizadas=len(actualizar), eliminadas=len(eliminar))
    return dict(resumen), recalculados


# ══════════════════════════════════════════════════════════════════════
#  Lectura
# ══════════════════════════════════════════════════════════════════════

CAMPOS_SALIDA = ('id', 'tipo', *CAMPOS_TEXTO, 'cuenta', 'excluir_de', 'base', 'factor', 'historico',
                 *MESES, 'total', 'origen', 'clave', 'actualizado', 'actualizado_por')


def listar(slug=None):
    qs = PresupuestoNomina.objects.all()
    if slug:
        qs = qs.filter(tipo=slug)
    filas = list(qs.order_by('tipo', 'id').values(*CAMPOS_SALIDA))
    if not slug:
        for fila in filas:
            c = CONCEPTOS.get(fila['tipo'])
            fila['tipo_nombre'] = c.etiqueta if c else fila['tipo']
    return filas


def resumen():
    """Totales por concepto: base del tablero consolidado."""
    anotaciones = {f's_{m}': Sum(m) for m in MESES}
    datos = {
        r['tipo']: r for r in PresupuestoNomina.objects.values('tipo').annotate(
            filas=Count('id'), manuales=Count('id', filter=Q(origen=MANUAL)),
            suma_total=Sum('total'), **anotaciones)
    }
    salida = []
    for c in _LISTA:
        r = datos.get(c.slug, {})
        salida.append({
            'slug': c.slug, 'etiqueta': c.etiqueta, 'grupo': c.grupo, 'derivado': c.derivado,
            'filas': r.get('filas', 0), 'manuales': r.get('manuales', 0),
            'total': r.get('suma_total') or 0,
            'meses': {m: r.get(f's_{m}') or 0 for m in MESES},
            'depende': [CONCEPTOS[d].etiqueta for d in c.depende],
            'afecta': [CONCEPTOS[d].etiqueta for d in afectados_por(c.slug)],
        })
    return salida
