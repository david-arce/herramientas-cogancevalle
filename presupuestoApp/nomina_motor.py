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
from .models_nomina import (MESES, ConceptosNomina, CorreccionPersonaNomina, DistribucionNomina,
                            FilaEliminadaNomina, FocoCargoInforme, FocoSinComision, PresupuestoNomina)

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

# Base del auxilio de transporte si no se ha definido en los parámetros
AUXILIO_TRANSPORTE_BASE = 200000
BASES_POR_DEFECTO = {'base_auxilio_transporte': AUXILIO_TRANSPORTE_BASE}


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
    base_auxilio_transporte: float = 0
    ipc_actual: float = 0

    @classmethod
    def cargar(cls):
        fila = ParametrosPresupuestos.objects.first()
        if not fila:
            return cls()
        return cls(**{campo: float(getattr(fila, campo) or 0) for campo in cls.__dataclass_fields__})

    def pct(self, campo):
        return (getattr(self, campo, 0) or 0) / 100 if campo else 0

    @property
    def base_auxilio(self):
        """Base del auxilio de transporte (se edita en la pantalla del concepto)."""
        return self.base_auxilio_transporte or AUXILIO_TRANSPORTE_BASE

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
    permite_manual: bool = False  # derivado que además acepta filas agregadas a mano
    con_minimo: bool = False     # sueldos: quien gana el mínimo sube desde enero
    base_editable: str = None    # parámetro (en pesos) que se edita en la pantalla del concepto
    crea_en_otros: bool = False  # al agregar una persona se puede crear en cero en los demás conceptos base
    pct_previo: str = None       # incremento que se aplica ANTES de `pct` (auxilio de educación: IPC año actual)
    titulo_base: str = None      # None → la tabla no muestra la columna "base"
    con_cedula: bool = True
    con_pegar: bool = False
    parametros: tuple = ()       # campos de parámetros que se muestran en la barra
    carga: dict = field(default_factory=dict)
    depende: tuple = ()

    def invertibles(self, fila, meses_reales):
        """Meses que, al restablecer el cálculo de una fila escrita a mano, pasan a ser su histórico."""
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
    Concepto('sueldos', 'Sueldos', G_PRINCIPAL, formula='retroactivo', crea_en_otros=True,
             pct='incremento_salarial', con_minimo=True, titulo_base='Salario base',
             parametros=('incremento_salarial', 'salario_minimo'),
             carga={'filtro': {'concepto': '001'}, 'base': True}),
    Concepto('comisiones', 'Comisiones', G_PRINCIPAL, formula='incremento_promedio',
             pct='incremento_comisiones', con_pegar=True,
             parametros=('incremento_comisiones',),
             carga={'filtro': {'concepto': '389'}, 'historico': 'reales'}),
    Concepto('horas_extra', 'Horas extra', G_PRINCIPAL, formula='incremento_promedio',
             pct='incremento_salarial', parametros=('incremento_salarial',),
             # Histórico: de enero hasta el mes de corte / "meses con datos reales"
             # elegido (incluido); los meses siguientes se llenan con su promedio.
             carga={'filtro': {'concepto__in': ['114', '110', '111']},
                    'historico': 'reales',
                    'agrupar': True, 'concepto': 'HORAS EXTRA'}),
    Concepto('medios_transporte', 'Medios de transporte', G_TRANSPORTE, formula='retroactivo',
             pct='incremento_ipc', titulo_base='Base', parametros=('incremento_ipc',),
             carga={'filtro': {'concepto': '011'}, 'base': True}),
    Concepto('ayuda_transporte', 'Ayuda de transporte', G_TRANSPORTE, formula='retroactivo',
             pct='incremento_ipc', titulo_base='Base', con_pegar=True, parametros=('incremento_ipc',),
             carga={'filtro': {'concepto': '013'}, 'base': True}),
    Concepto('bolsa_consumibles', 'Bolsa de consumibles (auxilio movilidad)', G_TRANSPORTE,
             formula='incrementar', pct='incremento_ipc', con_pegar=True,
             parametros=('incremento_ipc',),
             carga={'filtro': {'concepto': 'E32'}, 'historico': 'reales', 'descartar': 1}),
    Concepto('auxilio_tbckit', 'Auxilio TBC y KIT', G_TRANSPORTE, formula='incrementar',
             pct='incremento_ipc', parametros=('incremento_ipc',),
             carga={'filtro': {'concepto': 'E33'}, 'historico': 'reales'}),
    Concepto('auxilio_educacion', 'Auxilio de educación', G_TRANSPORTE, formula='incrementar',
             pct='incremento_ipc', pct_previo='ipc_actual', con_pegar=True,
             parametros=('ipc_actual', 'incremento_ipc'),
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
             base_editable='base_auxilio_transporte',
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
             permite_manual=True,              # se pueden agregar personas a mano
             # IPC: base de quienes no comisionan · comisiones: julio (presupuestadas)
             parametros=('incremento_ipc', 'incremento_comisiones'),
             depende=('sueldos', 'comisiones')),   # enero: comisiones REALES · julio: PRESUPUESTADAS
    Concepto('auxilio_antiguedad', 'Auxilio de antigüedad', G_PRESTACIONES, derivado=True,
             # 20 años → 2 SMMLV · 25 → 3 · 30 → 4 (salario mínimo proyectado), en diciembre
             parametros=('salario_minimo', 'incremento_salarial'),
             depende=('sueldos',)),
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
    'base_auxilio_transporte': 'Base auxilio de transporte ($)',
    'ipc_actual': 'IPC año actual (%)',
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


def cuotas_mensuales(filas, clave):
    """Parte de cada fila dentro de su grupo, MES A MES: {id(fila): {mes: 0‑1}}.

    Si una persona tiene el sueldo repartido en varias filas por meses (p. ej.
    en VENTAS de enero a abril y en PROYECTO AFTOSA en mayo y junio), lo que se
    calcula "por persona" en cada mes va a la fila que tiene valor ese mes, en
    proporción a su valor. Si ese mes ninguna fila tiene valor se reparte según
    el `factor` (como `cuotas`).
    """
    fija = cuotas(filas, clave)
    sumas = defaultdict(lambda: dict.fromkeys(MESES, 0.0))
    for fila in filas:
        for mes in MESES:
            sumas[clave(fila)][mes] += abs(getattr(fila, mes) or 0)
    salida = {}
    for fila in filas:
        total = sumas[clave(fila)]
        salida[id(fila)] = {mes: (abs(getattr(fila, mes) or 0) / total[mes]) if total[mes] else fija[id(fila)]
                            for mes in MESES}
    return salida


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


def _mapa_por_area(campo, anio=None):
    """{NOMCOSTO normalizado: valor de `campo`} (el más frecuente de cada NOMCOSTO).
    Se leen los datos del año base; si no tiene, los de cualquier año."""
    qs = ConceptosNomina.objects.exclude(**{campo: ''}).exclude(nomcosto='')
    if anio is not None and qs.filter(anio=anio).exists():
        qs = qs.filter(anio=anio)
    conteo = defaultdict(Counter)
    for nomcosto, valor, n in qs.values_list('nomcosto', campo).annotate(n=Count('id')):
        conteo[_clave_area(nomcosto)][texto(valor)] += n
    return {area: c.most_common(1)[0][0] for area, c in conteo.items()}


def mapa_cuentas(anio=None):
    """{NOMCOSTO normalizado: cuenta}

    Cada NOMCOSTO (en presupuesto_nomina: `area`) corresponde a una cuenta.
    Si en los datos un NOMCOSTO aparece con varias cuentas, se toma la más
    frecuente. Se leen los datos del año base; si no tiene, los de cualquier año.
    """
    return _mapa_por_area('cuenta', anio)


def mapa_codcostos(anio=None):
    """{NOMCOSTO normalizado: CODCOSTO}, con el mismo criterio que mapa_cuentas."""
    return _mapa_por_area('codcosto', anio)


def cuenta_para(mapa, area):
    return mapa.get(_clave_area(area), '') if texto(area) else ''


def asignar_cuentas(ctx=None, solo_vacias=False):
    """Pone a cada fila guardada la cuenta y el CODCOSTO de su área (NOMCOSTO).
    Las áreas que no están en ConceptosNomina conservan lo que tenían."""
    ctx = ctx or Contexto()
    qs = PresupuestoNomina.objects.exclude(area='')
    if solo_vacias:
        qs = qs.filter(Q(cuenta='') | Q(codcosto=''))
    cambiadas = []
    for fila in qs.only('id', 'area', 'cuenta', 'codcosto'):
        cuenta, codcosto = ctx.cuenta(fila.area), ctx.codcosto(fila.area)
        cambio = False
        if cuenta and cuenta != fila.cuenta:
            fila.cuenta, cambio = cuenta, True
        if codcosto and codcosto != fila.codcosto:
            fila.codcosto, cambio = codcosto, True
        if cambio:
            cambiadas.append(fila)
    PresupuestoNomina.objects.bulk_update(cambiadas, ['cuenta', 'codcosto'], batch_size=1000)
    return len(cambiadas)


class Contexto:
    """Lee cada concepto una sola vez por operación."""

    def __init__(self, parametros=None):
        self.p = parametros or Parametros.cargar()
        self._cache = {}
        self._meses = {}
        self._sedes = None
        self.repetidos = {}
        self.bloqueadas = {}     # {slug: personas cuya fila manual reemplaza a la calculada}
        self.omitidas = {}       # {slug: filas de Conceptos que no se cargan porque se eliminaron}
        self.anio = origen.anio_base()
        self._correcciones = None

    def correcciones(self):
        """{cédula de origen: (cédula correcta, nombre correcto)}"""
        if self._correcciones is None:
            self._correcciones = mapa_correcciones()
        return self._correcciones

    def olvidar_todo(self):
        self._cache.clear()
        self._correcciones = None

    def sedes(self):
        if self._sedes is None:
            self._sedes = sedes_vigentes(self.anio)
        return self._sedes

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

    def codcosto(self, area):
        """CODCOSTO del área (NOMCOSTO)."""
        if not hasattr(self, '_codcostos'):
            self._codcostos = mapa_codcostos(self.anio)
        return cuenta_para(self._codcostos, area)

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
    más el retroactivo de enero y febrero; de abril en adelante, el nuevo.

    Sueldos (con_minimo):
    - Quien gana el mínimo actual: mínimo proyectado (mínimo × (1 + incremento))
      todo el año, porque sube por decreto desde enero.
    - Quien gana más del mínimo actual pero no alcanza el mínimo proyectado:
      enero y febrero con el mínimo proyectado (nadie puede ganar menos) y desde
      marzo su salario + el incremento, con el retroactivo de enero y febrero
      sobre lo que ya se le pagó.
    - Los demás: enero y febrero con su salario actual y desde marzo el
      incremento con retroactivo.
    """
    base = fila.base or 0
    if c.con_minimo and p.salario_minimo and 0 < base <= p.salario_minimo:
        return dict.fromkeys(MESES, p.minimo_incrementado)
    nuevo = base * (1 + p.pct(c.pct))
    pagado = base
    if c.con_minimo and p.salario_minimo and base > 0:
        pagado = max(base, p.minimo_incrementado)     # enero y febrero nunca por debajo del mínimo nuevo
    meses = dict.fromkeys(MESES, nuevo)
    meses['enero'] = meses['febrero'] = pagado
    meses['marzo'] = nuevo + 2 * (nuevo - pagado)
    return meses


def f_base_fija(fila, c, p):
    return dict.fromkeys(MESES, (fila.base or 0) * (1 + p.pct(c.pct)))


def f_incrementar(fila, c, p):
    """Histórico × (1 + incremento). Con `pct_previo` (auxilio de educación):
    histórico × (1 + IPC año actual) × (1 + incremento IPC del año proyectado)."""
    factor = (1 + p.pct(c.pct_previo)) * (1 + p.pct(c.pct))
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
    # Los meses fijos en 0 (no trabajó) no bajan el promedio de los demás
    con_dato = [mes for mes in base if mes not in meses_en_cero(fila)]
    promedio = sum(meses[mes] for mes in con_dato) / len(con_dato) if con_dato else 0
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


# Meses que quedan en 0 aunque la fórmula dé otro valor: los que estaban en 0
# cuando a una fila MANUAL se le restableció el cálculo (p. ej. alguien que no
# trabaja esos meses). Se guardan dentro del histórico con esta clave.
MESES_CERO = '_meses_cero'


def meses_en_cero(fila):
    return set((fila.historico or {}).get(MESES_CERO) or [])


def _fijar_meses_cero(fila, meses):
    historico = dict(fila.historico or {})
    meses = [m for m in MESES if m in set(meses)]
    if meses:
        historico[MESES_CERO] = meses
    else:
        historico.pop(MESES_CERO, None)
    fila.historico = historico


def calcular(fila, c, p):
    """Los 12 meses que le corresponden a la fila según su fórmula y factor."""
    meses = FORMULAS[c.formula](fila, c, p)
    factor = fila.factor if fila.factor is not None else 1
    ceros = meses_en_cero(fila)
    return {mes: 0 if mes in ceros else int(round((meses.get(mes) or 0) * factor)) for mes in MESES}


def aplicar_formula(fila, c, p):
    fijar_meses(fila, calcular(fila, c, p))


# ══════════════════════════════════════════════════════════════════════
#  Carga de conceptos base desde ConceptosNomina (filtrado por año)
# ══════════════════════════════════════════════════════════════════════

def sedes_vigentes(anio):
    """{cédula: (centro, área)} de la sede donde la persona aparece más reciente.

    Si alguien está dos veces porque cambió de sede, se mira en todos sus
    registros del año cuál tiene el mes más reciente con valor.
    """
    mejor = {}
    campos = ('cedula', 'nombre_cen', 'nomcosto', *MESES)
    for r in ConceptosNomina.objects.filter(anio=anio).values(*campos):
        cedula = cedula_normalizada(r['cedula'])
        if not cedula:
            continue
        ultimo = total = 0
        for i, mes in enumerate(MESES, start=1):
            valor = numero(r[mes])
            total += valor
            if valor:
                ultimo = i
        if not ultimo:
            continue
        marca = (ultimo, total)
        if cedula not in mejor or marca > mejor[cedula][0]:
            mejor[cedula] = (marca, (texto(r['nombre_cen']), texto(r['nomcosto'])))
    return {cedula: sede for cedula, (_, sede) in mejor.items()}


def un_registro_por_persona(registros, leer, meses, sedes):
    """Deja un solo registro por cédula: el más reciente.

    Se prefiere, en este orden: el que tenga el mes con valor más reciente, el
    que esté en la sede vigente de la persona, el de mayor valor y, si todo
    empata, el último del archivo.
    """
    mejores, sueltos = {}, []
    for i, r in enumerate(registros):
        cedula = cedula_normalizada(r['cedula'])
        if not cedula:
            sueltos.append((i, r))
            continue
        ultimo = total = 0
        for n, mes in enumerate(meses, start=1):
            valor = numero(leer(r, mes))
            total += valor
            if valor:
                ultimo = n
        en_sede = sedes.get(cedula) == (texto(r['nombre_cen']), texto(r['nomcosto']))
        marca = (ultimo, 1 if en_sede else 0, total, numero(leer(r, 'concepto_f')), i)
        if cedula not in mejores or marca > mejores[cedula][0]:
            mejores[cedula] = (marca, i, r)
    elegidos = sueltos + [(i, r) for _, i, r in mejores.values()]
    return [r for _, r in sorted(elegidos)], len(registros) - len(elegidos)


def filas_de_conceptos(c, ctx):
    p = ctx.p
    carga = c.carga
    historico = ctx.meses_historico(c)
    ident = ['cedula', 'nombre', 'nombrecar', 'nomcosto', 'nombre_cen']
    consulta = ConceptosNomina.objects.filter(anio=ctx.anio_de(c), **carga['filtro'])
    campos_extra = [] if carga.get('agrupar') else ['cuenta', 'codcosto']   # respaldo si el área no tiene mapa

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

    # Una persona puede venir dos veces (cambió de sede): se deja la más reciente
    registros, repetidos = un_registro_por_persona(list(registros), leer, historico, ctx.sedes())
    if repetidos:
        ctx.repetidos[c.slug] = repetidos

    filas = []
    correcciones = ctx.correcciones()
    for i, r in enumerate(registros):
        # cédula y nombre corregidos en el presupuesto (CorreccionPersonaNomina)
        cedula, nombre = identidad_corregida(cedula_normalizada(r['cedula']), texto(r['nombre']), correcciones)
        fila = PresupuestoNomina(
            tipo=c.slug, origen=SISTEMA, clave=f'{cedula}#{i}',
            centro_origen=texto(r['nombre_cen']), area_origen=texto(r['nomcosto']),
            cedula=cedula, nombre=nombre,
            cuenta=ctx.cuenta(r['nomcosto']) or texto(r.get('cuenta')),
            codcosto=ctx.codcosto(r['nomcosto']) or texto(r.get('codcosto')),
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
                codcosto=ctx.codcosto(area) or (ref.codcosto if _clave_area(area) == _clave_area(ref.area) else ''),
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
        for c in DERIVADOS:
            regenerar(ctx, c)
    return {'personas': len(cedulas), 'filas': filas_nuevas, 'descartadas': 0}


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


def gen_auxilio_transporte(ctx, c):
    """Auxilio para quien devengue menos de 2 salarios mínimos en el mes:
    base (editable en la pantalla del concepto) × (1 + % auxilio de transporte)."""
    p = ctx.p
    limite = p.minimo_incrementado * 2
    base = p.base_auxilio
    valor = base * (1 + p.pct('auxilio_transporte'))
    por_cedula = lambda f: f.cedula  # noqa: E731
    totales = {t: sumar_por(ctx.filas(t), por_cedula)
               for t in ('medios_transporte', 'sueldos', 'comisiones', 'horas_extra', 'aprendiz')}
    personas = ctx.personas()
    cuota = cuotas_mensuales(personas, por_cedula)   # mes a mes: va a la fila que tiene sueldo ese mes

    for persona in personas:
        meses = dict.fromkeys(MESES, 0)
        for mes in MESES:
            devengado = sum(t.get(persona.cedula, {}).get(mes, 0) for t in totales.values())
            if mes == 'marzo':
                # marzo trae el retroactivo: se compara con el sueldo de abril
                sueldo = totales['sueldos'].get(persona.cedula, {})
                devengado += sueldo.get('abril', 0) - sueldo.get('marzo', 0)
            if devengado and devengado < limite:
                meses[mes] = valor * cuota[id(persona)][mes]
        yield dict(identidad(persona, concepto='AUXILIO DE TRANSPORTE'),
                   base=base, clave=clave_persona(persona), **meses)


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
    cuota = cuotas_mensuales(personas, por_clave)

    for persona in personas:
        meses = valores(persona)
        for tipo, indice in indices.items():
            if tipo == persona.tipo:
                continue
            otros = indice.get(por_clave(persona))
            if otros:
                parte = cuota[id(persona)]
                for mes in MESES:
                    meses[mes] += otros[mes] * parte[mes]
        yield dict(identidad(persona, concepto=concepto), clave=clave_persona(persona),
                   **{mes: v * pct for mes, v in meses.items()})


def gen_cesantias(ctx, c):
    return _prestacion(ctx, c, PRESTACION, 'CESANTÍAS')


def gen_prima(ctx, c):
    return _prestacion(ctx, c, PRESTACION, 'PRIMA LEGAL')


def gen_vacaciones(ctx, c):
    return _prestacion(ctx, c, ('comisiones', 'medios_transporte'), 'VACACIONES')


DIAS_MES = 30
DIAS_ANIO = 360


def intereses_acumulados(cesantias_mes, pct):
    """Intereses mes a mes sobre las cesantías acumuladas.

    interés del mes = cesantías acumuladas × días acumulados × % / 360
                      − intereses causados en los meses anteriores

    Los días se cuentan desde el primer mes con cesantías: quien entra en
    marzo tiene 30 días en marzo, 60 en abril, etc.

    Una persona puede tener varios periodos en el año (por ejemplo mayo–junio
    y noviembre–diciembre). Un mes sin cesantías corta el periodo: no causa
    intereses y el siguiente periodo vuelve a empezar en 30 días, con el
    acumulado en cero. (Si la persona tiene varias filas, aquí llega la SUMA
    de sus filas: ver gen_intereses_cesantias.)
    """
    salida, acumulado, causado, meses_trabajados = {}, 0.0, 0.0, 0
    for mes in MESES:
        valor = cesantias_mes.get(mes) or 0
        if not valor:                 # no ha entrado, o terminó un periodo
            salida[mes] = 0
            acumulado = causado = 0.0
            meses_trabajados = 0
            continue
        meses_trabajados += 1
        acumulado += valor
        total = acumulado * (DIAS_MES * meses_trabajados) * pct / DIAS_ANIO
        salida[mes] = total - causado
        causado = total
    return salida


def gen_intereses_cesantias(ctx, c):
    """Intereses de cesantías POR PERSONA.

    Si la persona tiene varias filas (p. ej. VENTAS de enero a abril y
    PROYECTO AFTOSA en mayo y junio), el acumulado se lleva como si fuera una
    sola línea: se suman sus cesantías de cada mes, se calculan los intereses
    sobre esa suma (sin reiniciar cuando una de las filas tiene el mes en 0) y
    el interés de cada mes se reparte entre las filas según las cesantías que
    cada una tiene ese mes.
    """
    pct = ctx.p.pct(c.pct)
    filas = ctx.filas('cesantias')
    persona = lambda f: f.cedula or f'#{id(f)}'  # noqa: E731  sin cédula: cada fila por su lado
    cuota = cuotas_mensuales(filas, persona)
    grupos = defaultdict(list)
    for ces in filas:
        grupos[persona(ces)].append(ces)
    intereses = {}
    for clave, del_grupo in grupos.items():
        suma = {mes: sum(getattr(f, mes) or 0 for f in del_grupo) for mes in MESES}
        intereses[clave] = intereses_acumulados(suma, pct)
    for ces in filas:
        total = intereses[persona(ces)]
        yield dict(identidad(ces, concepto='INTERESES CESANTÍAS'), clave=clave_persona(ces),
                   **{mes: total[mes] * cuota[id(ces)][mes] for mes in MESES})


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
# Base mensual de quienes no comisionan, cuando no se puede leer de los datos
BONIFICACION_FOCO_FIJA = 220000
CODIGO_COMISIONES = '389'          # concepto de comisiones en ConceptosNomina
CODIGO_FOCO = 'E17'                # concepto de la bonificación foco real en ConceptosNomina


def dias_360(desde, hasta_dia=30, hasta_mes=12):
    """Días trabajados en el año hasta el 30 de diciembre, con meses de 30 días.

    1 de enero → 360 · 1 de julio → 180 · 16 de septiembre → 105
    """
    dias = (hasta_mes - desde.month) * 30 + (hasta_dia - min(desde.day, 30)) + 1
    return max(0, min(360, dias))


def comisiones_reales(ctx):
    """{cédula: {mes: valor}} de las comisiones REALES (no presupuestadas)."""
    reales = defaultdict(lambda: dict.fromkeys(MESES, 0.0))
    correcciones = ctx.correcciones()
    for r in (ConceptosNomina.objects.filter(anio=ctx.anio, concepto=CODIGO_COMISIONES)
              .values('cedula', *MESES)):
        destino = reales[cedula_corregida(r['cedula'], correcciones)]
        for mes in MESES:
            destino[mes] += numero(r[mes])
    return reales


def promedio_anual_comisiones(meses_reales_dict, n_meses):
    """Promedio mensual del año completo.

    - El promedio de lo real se saca solo con los meses que tienen valor: si la
      persona comisionó de junio a septiembre, se divide entre 4, no entre 9.
    - Con ese promedio se llenan los meses que todavía no tienen dato real
      (octubre a diciembre, por ejemplo).
    - Al final se suman los 12 meses y se divide entre 12, aunque solo haya
      valores en dos o tres meses.
    """
    n = max(1, min(12, n_meses))
    reales = [meses_reales_dict.get(m) or 0 for m in MESES[:n]]
    con_valor = [v for v in reales if v]
    promedio_real = sum(con_valor) / len(con_valor) if con_valor else 0
    total = sum(reales) + promedio_real * (12 - n)
    return total / 12


def fechas_ingreso(anio):
    """{cédula: fecha de ingreso} tomada de ConceptosNomina."""
    propias, corregidas = {}, {}
    correcciones = mapa_correcciones()
    for cedula, fecha in (ConceptosNomina.objects.filter(anio=anio, fecha_ingreso__isnull=False)
                          .values_list('cedula', 'fecha_ingreso')):
        original = cedula_normalizada(cedula)
        clave = cedula_corregida(cedula, correcciones)
        if not clave:
            continue
        # La fecha de la propia persona manda sobre la que llega por una
        # corrección de cédula (que podría ser de otra persona).
        destino = corregidas if original != clave else propias
        if clave not in destino or fecha < destino[clave]:
            destino[clave] = fecha
    return {**corregidas, **propias}


def valores_foco_informe(ctx):
    """{cédula: {mes: valor}} de la bonificación foco del informe (concepto E17, año base)."""
    salida = defaultdict(lambda: dict.fromkeys(MESES, 0.0))
    correcciones = ctx.correcciones()
    for r in (ConceptosNomina.objects.filter(anio=ctx.anio, concepto=CODIGO_FOCO)
              .values('cedula', *MESES)):
        destino = salida[cedula_corregida(r['cedula'], correcciones)]
        for mes in MESES:
            destino[mes] += numero(r[mes])
    return {ced: meses for ced, meses in salida.items() if any(meses.values())}


def guardar_foco_cargos_informe(cargos, usuario=''):
    """Guarda los cargos que toman el valor del informe + IPC y recalcula la bonificación foco."""
    cargos = sorted({' '.join(texto(c_).upper().split()) for c_ in cargos} - {''})
    with transaction.atomic():
        FocoCargoInforme.objects.exclude(cargo__in=cargos).delete()
        for cargo in cargos:
            FocoCargoInforme.objects.update_or_create(cargo=cargo, defaults={'actualizado_por': usuario})
        ctx = Contexto()
        with bloqueo():
            regenerar(ctx, obtener('bonificaciones_foco'))
    return len(cargos)


def base_bonificacion_foco(ctx, comisionan, ingresos):
    """Valor de enero de alguien que no comisiona y trabajó el año completo.

    Se busca en ConceptosNomina el concepto de bonificación foco (CONCEPTO =
    E17) del año base: el valor de enero que más se repite entre quienes no
    comisionan y trabajaron el año completo. Si no está en los datos, se usa
    BONIFICACION_FOCO_FIJA.
    """
    candidatos = Counter()
    correcciones = ctx.correcciones()
    for r in (ConceptosNomina.objects.filter(anio=ctx.anio, concepto=CODIGO_FOCO)
              .values('cedula', 'enero')):
        cedula = cedula_corregida(r['cedula'], correcciones)
        valor = numero(r['enero'])
        ingreso = ingresos.get(cedula)
        anio_completo = not ingreso or ingreso.year < ctx.anio
        if valor > 0 and cedula not in comisionan and anio_completo:
            candidatos[round(valor)] += 1
    return float(candidatos.most_common(1)[0][0]) if candidatos else float(BONIFICACION_FOCO_FIJA)

MESES_SEMESTRE_1 = MESES[:6]       # enero a junio

def promedio_primer_semestre(fila):
    """Promedio mensual de enero a junio de una fila de comisiones presupuestadas.

    Los valores de la fila ya traen aplicado su factor de distribución, así que
    si la persona está repartida en varias filas cada una aporta su parte.
    """
    return sum(getattr(fila, mes) or 0 for mes in MESES_SEMESTRE_1) / len(MESES_SEMESTRE_1)

def gen_bonificaciones_foco(ctx, c):
    """Bonificación foco: se paga en enero y en julio.

    Enero
    - Quien comisiona: promedio mensual de sus comisiones REALES del año base
      (los meses que faltan se llenan con el promedio de los meses reales y el
      total se divide entre 12). No se le aplica ningún incremento.
    - Quien no comisiona (y quien esté en la lista "sin comisión"): la base
      mensual más el IPC, proporcional a los días trabajados desde su fecha de
      ingreso hasta el 30 de diciembre (base/360 × días).

    Julio
    - Solo quien comisiona y NO está en la lista "sin comisión": la mitad del
      promedio de sus comisiones PRESUPUESTADAS de enero a junio.
    - Quien no comisiona o está en la lista: no recibe pago en julio.

    Cargos elegidos en el tablero ("valor del informe"): para esas personas no
    se usa nada de lo anterior. Cada mes se toma su valor del informe (concepto
    E17 del Excel del año base) × (1 + incremento IPC).
    """
    p = ctx.p
    reales = comisiones_reales(ctx)
    ingresos = fechas_ingreso(ctx.anio)
    sin_comision = set(FocoSinComision.objects.values_list('cedula', flat=True))

    # 0) Cargos que toman el valor del informe + IPC
    cargos_informe = {c_.strip().upper() for c_ in FocoCargoInforme.objects.values_list('cargo', flat=True)}
    cargo_elegido = lambda f: (f.cargo or '').strip().upper() in cargos_informe  # noqa: E731
    con_sueldo = [f for f in ctx.filas('sueldos') if f.cedula and cargo_elegido(f)]
    del_informe = {f.cedula for f in con_sueldo}
    solo_comision = [f for f in ctx.filas('comisiones')
                     if f.cedula and cargo_elegido(f) and f.cedula not in del_informe]
    del_informe |= {f.cedula for f in solo_comision}
    if del_informe:
        valores_informe = valores_foco_informe(ctx)
        factor = 1 + p.pct('incremento_ipc')
        filas_informe = con_sueldo + solo_comision
        cuota = cuotas_mensuales(filas_informe, lambda f: f.cedula)
        for fila in filas_informe:
            informe = valores_informe.get(fila.cedula)
            if not informe:
                continue                       # no tiene valor en el informe: no recibe
            datos = {mes: informe[mes] * factor * cuota[id(fila)][mes] for mes in MESES}
            yield dict(identidad(fila, concepto='BONIFICACIÓN FOCO'), clave=clave_persona(fila), **datos)

    filas_comisiones = [f for f in ctx.filas('comisiones') if f.cedula not in del_informe]
    comisionan = {f.cedula for f in ctx.filas('comisiones') if f.cedula}
    por_promedio = [f for f in filas_comisiones if f.cedula and f.cedula not in sin_comision]

    # 1) Quienes comisionan: enero con las comisiones reales (sin incremento)
    #    y julio con la mitad del promedio presupuestado de enero a junio
    cuota = cuotas_mensuales(por_promedio, lambda f: f.cedula)
    vistos = set()
    for fila in por_promedio:
        promedio = promedio_anual_comisiones(reales.get(fila.cedula, {}), ctx.meses_reales())
        datos = dict.fromkeys(MESES, 0)
        datos['enero'] = promedio * cuota[id(fila)]['enero']
        datos['julio'] = promedio_primer_semestre(fila) / 2
        vistos.add(fila.cedula)
        yield dict(identidad(fila, concepto='BONIFICACIÓN FOCO'), clave=clave_persona(fila), **datos)

    # 2) Quienes no comisionan (y los de la lista): solo enero, base proporcional a los días
    base = base_bonificacion_foco(ctx, comisionan, ingresos) * (1 + p.pct('incremento_ipc'))
    fijos = [f for f in ctx.filas('sueldos')
             if f.cedula not in vistos and f.cedula not in del_informe
             # quien está en la lista la recibe aunque su cargo sea comercial
             and (f.cedula in sin_comision
                  or (f.cargo or '').strip().upper() not in CARGOS_SIN_BONIFICACION_FOCO)]
    cuota = cuotas_mensuales(fijos, lambda f: f.cedula)
    for fila in fijos:
        ingreso = ingresos.get(fila.cedula)
        dias = dias_360(ingreso) if ingreso and ingreso.year >= ctx.anio else 360
        datos = dict.fromkeys(MESES, 0)
        datos['enero'] = base / 360 * dias * cuota[id(fila)]['enero']
        yield dict(identidad(fila, concepto='BONIFICACIÓN FOCO'), clave=clave_persona(fila), **datos)

# Años cumplidos en la empresa → salarios mínimos de auxilio de antigüedad
ANTIGUEDAD_SALARIOS = {20: 2, 25: 3, 30: 4}


def gen_auxilio_antiguedad(ctx, c):
    """Auxilio de antigüedad, en DICIEMBRE del año del presupuesto.

    Quien cumple 20, 25 o 30 años en la empresa durante el año del presupuesto
    (año base + 1), según su fecha de ingreso en Conceptos, recibe 2, 3 o 4
    salarios mínimos proyectados (mínimo × (1 + incremento salarial)).

    Solo se paga a quien tiene sueldo en diciembre (sigue en la empresa). Si la
    persona tiene varias filas, va a la(s) que tienen sueldo en diciembre.
    """
    anio = ctx.anio + 1
    ingresos = fechas_ingreso(ctx.anio)
    personas = ctx.personas()
    persona_de = lambda f: f.cedula or f'#{id(f)}'  # noqa: E731
    cuota = cuotas_mensuales(personas, persona_de)
    con_sueldo_dic = defaultdict(float)
    for f in personas:
        con_sueldo_dic[persona_de(f)] += abs(f.diciembre or 0)
    for persona in personas:
        ingreso = ingresos.get(persona.cedula)
        anios = anio - ingreso.year if ingreso else None
        salarios = ANTIGUEDAD_SALARIOS.get(anios)
        if not salarios or not con_sueldo_dic[persona_de(persona)]:
            continue
        valor = salarios * ctx.p.minimo_incrementado * cuota[id(persona)]['diciembre']
        if not valor:
            continue
        meses = dict.fromkeys(MESES, 0)
        meses['diciembre'] = valor
        yield dict(identidad(persona, concepto=f'AUXILIO DE ANTIGÜEDAD {anios} AÑOS'),
                   clave=clave_persona(persona), **meses)


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
# Proyecto aftosa: su ARL es 1,04 %. Se usa cuando el informe no trae filas de esa área.
AREA_AFTOSA = 'PROYECTO AFTOSA GASTOS DE PERSONAL'
ARL_AFTOSA = 0.0104
APORTE_SALUD_APRENDIZ = 0.125
# Técnicos: su seguridad social se calcula por persona (no se consolida por área)
AREAS_POR_PERSONA = {'ASISTENCIA TECNICA PROPIA', 'ASISTENCIA TECNICA CONVENIO'}
# Estas áreas se consolidan sin centro
AREAS_AGRUPADAS = [
    ['PROYECTO AFTOSA GASTOS DE PERSONAL'],
]


def porcentajes_arl_persona(ctx):
    """{cédula: % ARL (fracción)} de cada persona según el Excel del año base.

    Se toma el ARLPORC que más se repite en sus filas (ignorando vacíos y ceros),
    sin redondear.
    """
    conteo = defaultdict(Counter)
    correcciones = ctx.correcciones()
    for cedula, valor in (ConceptosNomina.objects.filter(anio=ctx.anio, arlporc__isnull=False, arlporc__gt=0)
                          .values_list('cedula', 'arlporc')):
        conteo[cedula_corregida(cedula, correcciones)][valor] += 1
    return {ced: c.most_common(1)[0][0] / 100.0 for ced, c in conteo.items() if ced}


def porcentajes_arl(anio):
    """{(centro, área): %} y {área: %}: promedio de ARLPORC redondeado a 4 decimales.

    El promedio por área (todos los centros juntos) sirve para las áreas que se
    consolidan sin centro (aftosa) y como respaldo cuando un centro no tiene
    filas de esa área en el informe.
    """
    base = ConceptosNomina.objects.filter(anio=anio, arlporc__isnull=False)
    por_centro = {
        (texto(p['nombre_cen']), texto(p['nomcosto'])): round((p['promedio'] or 0) / 100.0, 4)
        for p in base.values('nombre_cen', 'nomcosto').annotate(promedio=Avg('arlporc'))
        if p['promedio'] is not None
    }
    por_area = {
        _sin_tildes(p['nomcosto']): round((p['promedio'] or 0) / 100.0, 4)
        for p in base.values('nomcosto').annotate(promedio=Avg('arlporc'))
        if p['promedio'] is not None
    }
    return por_centro, por_area


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
    arl_persona = porcentajes_arl_persona(ctx)
    arl_centro, arl_area = porcentajes_arl(ctx.anio)
    generales = defaultdict(lambda: dict.fromkeys(MESES, 0))
    altos = defaultdict(lambda: dict.fromkeys(MESES, 0))
    aprendices_salud = defaultdict(lambda: dict.fromkeys(MESES, 0))
    # ARL:
    #  · filas agrupadas "SEGURIDAD SOCIAL" (centro + área): promedio de ARLPORC
    #    del centro de costo; si ese centro no tiene filas del área en el
    #    informe, el promedio del área en todos los centros.
    #  · aftosa (se consolida sin centro): un solo promedio del área; si el
    #    informe no trae filas de aftosa, 1,04 % (ARL_AFTOSA). Solo aplica a
    #    filas cuya área es exactamente PROYECTO AFTOSA GASTOS DE PERSONAL.
    #  · filas por persona (asistencia técnica): el ARLPORC de la persona tal
    #    cual viene del informe; si no tiene, el promedio de su centro.
    #  Sin ningún dato se usa 0,93 %.
    arl_valor = defaultdict(lambda: dict.fromkeys(MESES, 0))

    def pct_arl(fila, llave):
        area = _sin_tildes(fila.area)
        del_area = arl_area.get(area)
        if area == AREA_AFTOSA:
            # aftosa: un solo % para toda el área; si el informe no lo trae, 1,04 %
            del_centro = del_area or ARL_AFTOSA
        else:
            del_centro = arl_centro.get((fila.centro, fila.area)) or del_area
        if llave[2]:                                   # fila por persona
            return arl_persona.get(fila.cedula) or del_centro or ARL_POR_DEFECTO
        return del_centro or ARL_POR_DEFECTO


    def sumar(destino, fila, meses=None):
        meses = meses or valores(fila)
        llave = llave_seguridad_social(fila)
        for mes in MESES:
            destino[llave][mes] += meses[mes]
        if destino is generales or destino is aprendices_salud:     # la base de ARL incluye ambos
            pct = pct_arl(fila, llave)
            for mes in MESES:
                arl_valor[llave][mes] += meses[mes] * pct

    # Salud, SENA e ICBF: solo quien DEVENGA más de 10 salarios mínimos en el
    # mes (sueldo + medios de transporte + comisiones + horas extra de todas
    # sus filas). Ese mes cotiza sobre todo lo que devenga. Antes se miraba
    # solo el salario base y había una cédula fija para sumarle el resto.
    devengables = ('sueldos', 'medios_transporte', 'comisiones', 'horas_extra')
    persona = lambda f: f.cedula or f'#{id(f)}'  # noqa: E731
    devengado = defaultdict(lambda: dict.fromkeys(MESES, 0))
    for tipo in devengables:
        for fila in ctx.filas(tipo):
            for mes in MESES:
                devengado[persona(fila)][mes] += getattr(fila, mes) or 0

    for tipo in devengables:
        for fila in ctx.filas(tipo):
            sumar(generales, fila)
            total = devengado[persona(fila)]
            meses_altos = {m: (getattr(fila, m) or 0) if total[m] > tope else 0 for m in MESES}
            if any(meses_altos.values()):
                sumar(altos, fila, meses_altos)

    for apr in ctx.filas('aprendiz'):
        # el aprendiz cotiza siempre sobre un salario mínimo incrementado
        meses = {m: (p.minimo_incrementado if v > 0 else v) for m, v in valores(apr).items()}
        destino = aprendices_salud if (apr.concepto or '').strip().upper() == 'SALARIO APRENDIZ' else generales
        sumar(destino, apr, meses)

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
                datos = arl_valor.get(llave, dict.fromkeys(MESES, 0))   # ya va con su % (centro o persona)
                porcentaje = 1
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
    'auxilio_antiguedad': gen_auxilio_antiguedad,
    'seguridad_social': gen_seguridad_social,
}


# ══════════════════════════════════════════════════════════════════════
#  4. Operaciones: regenerar, propagar, cargar, guardar, borrar
# ══════════════════════════════════════════════════════════════════════

def regenerar(ctx, c):
    """Recalcula un concepto derivado por completo.

    Los conceptos calculados (cesantías, prima, vacaciones, intereses,
    bonificaciones, seguridad social, auxilio de transporte) se rehacen
    siempre. Para que una persona no entre en alguno de ellos se usa
    `excluir_de` en la fila de origen.

    Los conceptos con `permite_manual` (bonificaciones foco) conservan las
    filas que se agregaron a mano; esas no se calculan y bloquean la fila
    calculada de la misma persona.
    """
    manuales = ([f for f in ctx.filas(c.slug) if f.origen == MANUAL] if c.permite_manual else [])
    bloqueadas = {f.clave for f in manuales if f.clave}
    if c.permite_manual:
        # filas calculadas que se eliminaron en pantalla: no vuelven
        bloqueadas |= set(FilaEliminadaNomina.objects.filter(tipo=c.slug).values_list('llave', flat=True))
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
        datos.setdefault('codcosto', ctx.codcosto(datos.get('area')))
        fila = PresupuestoNomina(tipo=c.slug, origen=SISTEMA, clave=clave, **datos)
        fijar_meses(fila, meses)
        nuevas.append(fila)

    PresupuestoNomina.objects.filter(tipo=c.slug).exclude(
        pk__in=[f.pk for f in manuales]).delete()
    PresupuestoNomina.objects.bulk_create(nuevas, batch_size=1000)
    ctx.olvidar(c.slug)
    return len(nuevas) + len(manuales)


def propagar(slug, ctx=None):
    """Recalcula en cascada todo lo que depende de `slug`."""
    ctx = ctx or Contexto()
    hechos = []
    for dependiente in afectados_por(slug):
        regenerar(ctx, CONCEPTOS[dependiente])
        hechos.append(dependiente)
    return hechos


def _ventana_desactualizada(c, ctx):
    """True si las filas calculadas de `c` se cargaron con otros meses reales
    que los que hay configurados ahora (histórico 'reales')."""
    if c.carga.get('historico') != 'reales':
        return False
    ventana = set(ctx.meses_historico(c))
    return any({m for m in (f.historico or {}) if m in MESES} != ventana
               for f in ctx.filas(c.slug) if f.origen == SISTEMA and _viene_de_conceptos(f))


def recalcular_todo():
    """Tras cambiar parámetros: fórmulas de los conceptos base + todos los derivados."""
    ctx = Contexto()
    with bloqueo():
        for c in BASE:
            if _ventana_desactualizada(c, ctx):
                # Cambiaron los meses con datos reales (o la fecha de corte) desde
                # la última carga: el histórico guardado ya no sirve, se vuelve a
                # leer de Conceptos (las filas manuales se conservan).
                _reemplazar_base(c, ctx)
                continue
            automaticas = [f for f in ctx.filas(c.slug) if f.origen == SISTEMA]
            for fila in automaticas:
                aplicar_formula(fila, c, ctx.p)
            PresupuestoNomina.objects.bulk_update(automaticas, MESES + ['total'], batch_size=1000)
        for c in DERIVADOS:
            regenerar(ctx, c)
        asignar_cuentas(ctx)
    return [c.slug for c in _LISTA]

def _viene_de_conceptos(fila):
    """True si la fila salió de cargar Conceptos (clave 'cédula#n').

    Las filas agregadas en pantalla no tienen clave, o la tienen con '#m' si se
    distribuyeron. Siguen siendo "propias" aunque después se les restablezca el
    cálculo: por eso aquí no se mira `origen`.
    """
    return bool(fila.clave) and '#m' not in fila.clave


def _cedula_de_clave(fila):
    """Cédula con que la fila salió de Conceptos (clave 'cédula#n')."""
    return (fila.clave or '').split('#')[0] if _viene_de_conceptos(fila) else fila.cedula


def llave_eliminada(fila):
    """Cómo se reconoce una fila de Conceptos eliminada: la cédula de la persona
    (la de la clave) o, si el concepto no tiene cédula, centro|área|concepto."""
    cedula = _cedula_de_clave(fila)
    if cedula:
        return cedula
    return '|'.join(texto(v).upper() for v in (fila.centro_origen or fila.centro,
                                               fila.area_origen or fila.area, fila.concepto))


def _recordar_eliminadas(c, filas, usuario):
    """Las filas de Conceptos que se eliminaron no vuelven en la próxima carga."""
    for fila in filas:
        if _viene_de_conceptos(fila):
            FilaEliminadaNomina.objects.update_or_create(
                tipo=c.slug, llave=llave_eliminada(fila)[:400],
                defaults={'nombre': fila.nombre or fila.concepto, 'eliminado_por': usuario})


def personas_retiradas():
    """Cédulas que se eliminaron de Sueldos y no tienen ninguna otra fila de sueldo."""
    eliminadas = set(FilaEliminadaNomina.objects.filter(tipo='sueldos').values_list('llave', flat=True))
    if not eliminadas:
        return set()
    con_sueldo = set(PresupuestoNomina.objects.filter(tipo='sueldos', cedula__in=eliminadas)
                     .values_list('cedula', flat=True))
    return eliminadas - con_sueldo


def listar_eliminadas():
    return [dict(f, etiqueta=CONCEPTOS[f['tipo']].etiqueta if f['tipo'] in CONCEPTOS else f['tipo'])
            for f in FilaEliminadaNomina.objects.values('id', 'tipo', 'llave', 'nombre',
                                                       'eliminado', 'eliminado_por')]


def quitar_eliminada(pk):
    """La fila vuelve a cargarse desde Conceptos en la próxima carga."""
    return FilaEliminadaNomina.objects.filter(pk=pk).delete()[0]


def _reemplazar_base(c, ctx):
    """Vuelve a cargar un concepto base desde Conceptos.

    - Se borran y se crean de nuevo solo las filas CALCULADAS que salieron de
      Conceptos.
    - Se conservan las filas manuales y las agregadas en pantalla, aunque a
      estas se les haya restablecido el cálculo.
    - Si una fila de Conceptos fue editada (ahora manual), la editada reemplaza
      a la nueva de esa persona para no contarla dos veces.
    Devuelve (creadas, conservadas).
    """
    actuales = ctx.filas(c.slug)
    nuevas = filas_de_conceptos(c, ctx)
    # Filas que se eliminaron en pantalla: no se vuelven a crear. Y quien se
    # eliminó de Sueldos (y ya no tiene ninguna fila ahí) tampoco se carga en
    # los demás conceptos: comisiones, auxilio de educación del año anterior…
    eliminadas = set(FilaEliminadaNomina.objects.filter(tipo=c.slug).values_list('llave', flat=True))
    retiradas = personas_retiradas() if c.slug != 'sueldos' else set()
    if eliminadas or retiradas:
        antes_n = len(nuevas)
        nuevas = [f for f in nuevas
                  if llave_eliminada(f) not in eliminadas and not (f.cedula and f.cedula in retiradas)]
        if antes_n != len(nuevas):
            ctx.omitidas[c.slug] = antes_n - len(nuevas)
    nombre_en_conceptos = {f.cedula: f.nombre for f in nuevas if f.cedula}

    # Filas calculadas a las que se les cambió la cédula o el nombre a mano
    # antes de que eso las volviera manuales: se conservan como manuales en
    # lugar de reemplazarlas (si no, se perdería el cambio).
    retocadas = []
    for f in actuales:
        if f.origen == SISTEMA and _viene_de_conceptos(f):
            original = _cedula_de_clave(f)
            if original in nombre_en_conceptos and (f.cedula, f.nombre) != (original, nombre_en_conceptos[original]):
                f.origen = MANUAL
                retocadas.append(f)
    if retocadas:
        PresupuestoNomina.objects.bulk_update(retocadas, ['origen'], batch_size=1000)

    reemplazables = {f.pk for f in actuales if f.origen == SISTEMA and _viene_de_conceptos(f)}
    # Los meses fijos en 0 de una persona pasan a sus filas recargadas
    ceros_por_cedula = {_cedula_de_clave(f): sorted(meses_en_cero(f)) for f in actuales
                        if f.pk in reemplazables and meses_en_cero(f)}
    for f in nuevas:
        if f.cedula in ceros_por_cedula:
            _fijar_meses_cero(f, ceros_por_cedula[f.cedula])
            aplicar_formula(f, c, ctx.p)
    conservadas = [f for f in actuales if f.pk not in reemplazables]
    # La persona se reconoce por la cédula con que salió de Conceptos (la de
    # la clave): así una fila a la que se le cambió la cédula también reemplaza
    # a la nueva y la persona no queda dos veces.
    editadas = {_cedula_de_clave(f) for f in conservadas
                if f.origen == MANUAL and _viene_de_conceptos(f)} - {''}

    bloqueadas = {f.cedula for f in nuevas if f.cedula in editadas}
    nuevas = [f for f in nuevas if f.cedula not in editadas]

    PresupuestoNomina.objects.filter(pk__in=reemplazables).delete()
    PresupuestoNomina.objects.bulk_create(nuevas, batch_size=1000)
    ctx.olvidar(c.slug)
    if bloqueadas:
        ctx.bloqueadas[c.slug] = len(bloqueadas)
    return len(nuevas), len(conservadas)

def cargar_base(slug):
    """Concepto base: recarga lo calculado desde Conceptos (las filas manuales se conservan).
    Concepto derivado: lo vuelve a calcular."""
    c = obtener(slug)
    ctx = Contexto()
    conservadas = 0
    with bloqueo():
        if c.derivado:
            creadas = regenerar(ctx, c)
        else:
            creadas, conservadas = _reemplazar_base(c, ctx)
        recalculados = propagar(slug, ctx)
    return (creadas, recalculados, sum(ctx.repetidos.values()),
            conservadas, sum(ctx.bloqueadas.values()), sum(ctx.omitidas.values()))

def personas_que_comisionan():
    """[(cédula, nombre)] de quienes tienen comisiones en el presupuesto."""
    filas = (PresupuestoNomina.objects.filter(tipo='comisiones').exclude(cedula='')
             .values_list('cedula', 'nombre').distinct())
    return sorted({(c, n) for c, n in filas}, key=lambda x: (x[1] or '', x[0]))


def guardar_foco_sin_comision(cedulas, usuario=''):
    """Guarda a quiénes se les calcula la bonificación foco como si no comisionaran."""
    cedulas = sorted({cedula_normalizada(c) for c in cedulas} - {''})
    nombres = dict(personas_que_comisionan())
    with transaction.atomic():
        FocoSinComision.objects.exclude(cedula__in=cedulas).delete()
        for cedula in cedulas:
            FocoSinComision.objects.update_or_create(
                cedula=cedula, defaults={'nombre': nombres.get(cedula, ''), 'actualizado_por': usuario})
        ctx = Contexto()
        with bloqueo():
            regenerar(ctx, obtener('bonificaciones_foco'))
    return len(cedulas)


def recargar_bases():
    """Vuelve a cargar TODOS los conceptos base desde ConceptosNomina
    (p. ej. tras subir un Excel nuevo) y recalcula los derivados.
    Las filas manuales de los conceptos base se conservan."""
    ctx = Contexto()
    conteo, manuales = {}, 0
    with bloqueo():
        for c in BASE:
            creadas, conservadas = _reemplazar_base(c, ctx)
            conteo[c.slug] = creadas
            manuales += conservadas
        for c in DERIVADOS:
            regenerar(ctx, c)
        asignar_cuentas(ctx)
    conteo['_repetidos'] = sum(ctx.repetidos.values())
    conteo['_manuales'] = manuales
    conteo['_bloqueadas'] = sum(ctx.bloqueadas.values())
    conteo['_eliminadas'] = sum(ctx.omitidas.values())
    return conteo

def borrar(slug):
    c = obtener(slug)
    ctx = Contexto()
    with bloqueo():
        eliminadas, _ = PresupuestoNomina.objects.filter(tipo=slug).delete()
        if c.derivado:       # un derivado no se puede vaciar: se vuelve a calcular
            ctx.olvidar(slug)
            eliminadas = regenerar(ctx, c)
        recalculados = propagar(slug, ctx)
    return eliminadas, recalculados


def _cambio(antes, fila):
    return any(antes[campo] != getattr(fila, campo)
               for campo in (*CAMPOS_TEXTO, 'base', *MESES))


# ══════════════════════════════════════════════════════════════════════
#  Correcciones de cédula / nombre de una persona
#  Los datos de origen traen la cédula y el nombre del Excel. Si en el
#  presupuesto se corrigen, se cambian en TODOS los conceptos y la corrección
#  se guarda para que las próximas cargas desde Conceptos la respeten.
# ══════════════════════════════════════════════════════════════════════

def mapa_correcciones():
    """{cédula de origen: (cédula correcta, nombre correcto)}"""
    return {c.cedula_origen: (c.cedula, c.nombre)
            for c in CorreccionPersonaNomina.objects.all()}


def identidad_corregida(cedula, nombre, correcciones):
    """(cédula, nombre) con que debe verse en el presupuesto alguien que viene de Conceptos."""
    if cedula in correcciones:
        nueva, nombre_nuevo = correcciones[cedula]
        return nueva or cedula, nombre_nuevo or nombre
    return cedula, nombre


def cedula_corregida(cedula, correcciones):
    cedula = cedula_normalizada(cedula)
    return (correcciones.get(cedula) or (cedula,))[0] or cedula


def _clave_con_cedula(clave, vieja, nueva):
    """Las claves empiezan por la cédula ('cédula#n' o 'cédula|centro|área')."""
    clave = clave or ''
    for separador in ('#', '|'):
        if clave.startswith(vieja + separador):
            return nueva + clave[len(vieja):]
    return clave


def _vuelve_a_su_cedula(vieja, nueva):
    """¿Se está deshaciendo una corrección (volver a la cédula que trae el Excel)?"""
    return CorreccionPersonaNomina.objects.filter(cedula_origen=nueva, cedula=vieja).exists()


def _cedula_de_otra_persona(cedula, excluir_pks=(), vieja=''):
    """¿La cédula ya es de alguien: está en el Excel de Conceptos o en otras filas del presupuesto?"""
    if vieja and _vuelve_a_su_cedula(vieja, cedula):
        return False
    if cedula.isdigit() and ConceptosNomina.objects.filter(cedula=int(cedula)).exists():
        return True
    return PresupuestoNomina.objects.filter(cedula=cedula).exclude(pk__in=list(excluir_pks)).exists()


def corregir_persona(cedula_actual, cedula_nueva='', nombre_nuevo='', usuario='', ctx=None,
                     recalcular=True):
    """Cambia la cédula y/o el nombre de una persona en todo el presupuesto.

    - Todas las filas de todos los conceptos con `cedula_actual` pasan a
      `cedula_nueva` (y al nombre nuevo, si se indica). También las filas que
      ya tienen la cédula nueva toman el nombre nuevo.
    - Distribución por persona y bonificación foco se mueven a la cédula nueva.
    - Si la persona viene de Conceptos, se guarda la corrección para que las
      próximas cargas la respeten.
    - Si la cédula nueva ya es de OTRA persona en un mismo concepto, no se hace
      nada (ValueError): sería mezclar a dos personas.
    Devuelve cuántas filas cambiaron.
    """
    vieja = cedula_normalizada(cedula_actual)
    nueva = cedula_normalizada(cedula_nueva) or vieja
    nombre_nuevo = ' '.join(texto(nombre_nuevo).upper().split())
    if not vieja:
        raise ValueError('Indique la cédula actual de la persona')
    if nueva == vieja and not nombre_nuevo:
        raise ValueError('Indique la cédula correcta o el nombre correcto')
    if nueva != vieja:
        con_vieja = set(PresupuestoNomina.objects.filter(cedula=vieja).values_list('tipo', flat=True))
        con_nueva = set(PresupuestoNomina.objects.filter(cedula=nueva).values_list('tipo', flat=True))
        choque = con_vieja & con_nueva
        if (nueva.isdigit() and ConceptosNomina.objects.filter(cedula=int(nueva)).exists()
                and not _vuelve_a_su_cedula(vieja, nueva)):
            raise ValueError(f'La cédula {nueva} ya existe en el Excel de Conceptos (es otra persona)')
        if choque:
            raise ValueError(f'La cédula {nueva} ya es de otra persona en '
                             f"{', '.join(sorted(CONCEPTOS[t].etiqueta for t in choque if t in CONCEPTOS))}")
    ctx = ctx or Contexto()
    with bloqueo():
        cambiadas = []
        filas = list(PresupuestoNomina.objects.filter(
            Q(cedula__in={vieja, nueva}) | Q(clave__startswith=vieja + '#') | Q(clave__startswith=vieja + '|')))
        for fila in filas:
            antes = (fila.cedula, fila.nombre, fila.clave)
            if fila.cedula == vieja:
                fila.cedula = nueva
            # la clave guarda la cédula con que la fila salió de Conceptos
            fila.clave = _clave_con_cedula(fila.clave, vieja, nueva)
            if nombre_nuevo and fila.cedula == nueva:
                fila.nombre = nombre_nuevo
            if (fila.cedula, fila.nombre, fila.clave) != antes:
                fila.actualizado_por = usuario or fila.actualizado_por
                cambiadas.append(fila)
        PresupuestoNomina.objects.bulk_update(cambiadas, ['cedula', 'nombre', 'clave', 'actualizado_por'],
                                              batch_size=1000)

        if nueva != vieja:
            FilaEliminadaNomina.objects.filter(llave=vieja).exclude(
                tipo__in=FilaEliminadaNomina.objects.filter(llave=nueva).values('tipo')).update(llave=nueva)
            if DistribucionNomina.objects.filter(cedula=nueva).exists():
                DistribucionNomina.objects.filter(cedula=vieja).delete()
            else:
                DistribucionNomina.objects.filter(cedula=vieja).update(cedula=nueva)
            if FocoSinComision.objects.filter(cedula=nueva).exists():
                FocoSinComision.objects.filter(cedula=vieja).delete()
            else:
                FocoSinComision.objects.filter(cedula=vieja).update(cedula=nueva)
        if nombre_nuevo:
            FocoSinComision.objects.filter(cedula=nueva).update(nombre=nombre_nuevo)

        _guardar_correccion(vieja, nueva, nombre_nuevo, usuario)
        ctx.olvidar_todo()
        if recalcular:
            for c in DERIVADOS:
                regenerar(ctx, c)
    return len(cambiadas)


def _guardar_correccion(vieja, nueva, nombre_nuevo, usuario):
    """Guarda (o actualiza / quita) la corrección respecto a los datos de origen."""
    previa = CorreccionPersonaNomina.objects.filter(cedula=vieja).first()
    cedula_origen = previa.cedula_origen if previa else vieja
    fuente = None
    if cedula_origen.isdigit():
        fuente = (ConceptosNomina.objects.filter(cedula=int(cedula_origen))
                  .order_by('-anio', '-id').values_list('nombre', flat=True).first())
    if fuente is None:                       # la persona no viene de Conceptos: nada que recordar
        return
    nombre = nombre_nuevo or (previa.nombre if previa else '')
    if nueva == cedula_origen and (not nombre or nombre == ' '.join(texto(fuente).upper().split())):
        CorreccionPersonaNomina.objects.filter(cedula_origen=cedula_origen).delete()   # volvió a ser la original
        return
    CorreccionPersonaNomina.objects.update_or_create(
        cedula_origen=cedula_origen,
        defaults={'cedula': nueva, 'nombre': nombre, 'actualizado_por': usuario})


def quitar_correccion(cedula_origen):
    """Deja de aplicar una corrección en las próximas cargas (no cambia las filas actuales)."""
    return CorreccionPersonaNomina.objects.filter(cedula_origen=cedula_normalizada(cedula_origen)).delete()[0]


def listar_correcciones():
    return list(CorreccionPersonaNomina.objects.values(
        'cedula_origen', 'cedula', 'nombre', 'actualizado', 'actualizado_por'))


def _firma_guardada(fila):
    """Contenido de una fila guardada (para reconocer un reenvío del autoguardado)."""
    return (*(getattr(fila, c) or '' for c in CAMPOS_TEXTO), int(fila.base or 0),
            *(int(getattr(fila, m) or 0) for m in MESES))


def _firma_entrante(datos):
    """La misma firma calculada sobre una fila tal como llega del navegador."""
    textos = (cedula_normalizada(texto(datos.get(c))) if c == 'cedula' else texto(datos.get(c))
              for c in CAMPOS_TEXTO)
    return (*textos, int(round(numero(datos.get('base')))),
            *(int(round(numero(datos.get(m)))) for m in MESES))


CREAR_EN = '_crear_en'


def conceptos_para_crear(slug):
    """Conceptos base (distintos de `slug`) donde se puede crear en cero a una persona nueva."""
    return [c.slug for c in BASE if c.slug != slug and c.con_cedula]


def _crear_en_otros(filas, usuario, ctx):
    """Crea en cero, en los conceptos pendientes de cada fila, a la persona nueva.

    Se hace cuando la fila ya tiene cédula (antes no se sabría quién es). Si la
    persona ya tiene fila en ese concepto, no se duplica. Devuelve
    {"NOMBRE (cédula)": [slugs creados]}.
    """
    hechas, limpiar = {}, []
    for fila in filas:
        pendientes = (fila.historico or {}).get(CREAR_EN)
        if not pendientes or not fila.cedula:
            continue
        existentes = set(PresupuestoNomina.objects.filter(cedula=fila.cedula, tipo__in=pendientes)
                         .values_list('tipo', flat=True))
        nuevas = []
        for slug in pendientes:
            c = CONCEPTOS.get(slug)
            if not c or slug in existentes:
                continue
            nueva = PresupuestoNomina(
                tipo=slug, origen=MANUAL, clave='', cedula=fila.cedula, nombre=fila.nombre,
                centro=fila.centro, area=fila.area, cargo=fila.cargo,
                concepto=(c.carga or {}).get('concepto') or c.etiqueta.upper(),
                cuenta=ctx.cuenta(fila.area) or fila.cuenta, codcosto=ctx.codcosto(fila.area) or fila.codcosto,
                actualizado_por=usuario)
            fijar_meses(nueva, {})
            nuevas.append(nueva)
        PresupuestoNomina.objects.bulk_create(nuevas, batch_size=1000)
        for n in nuevas:
            ctx.olvidar(n.tipo)
        if nuevas:
            hechas[f'{fila.nombre or "la persona"} ({fila.cedula})'] = [n.tipo for n in nuevas]
        historico = dict(fila.historico)
        historico.pop(CREAR_EN, None)
        fila.historico = historico
        limpiar.append(fila)
    PresupuestoNomina.objects.bulk_update(limpiar, ['historico'], batch_size=1000)
    return hechas


def _propagar_identidades(identidades, finales, usuario, ctx, avisos):
    """Lleva a todos los conceptos las cédulas / nombres corregidos al guardar.

    Solo se toma como corrección de la PERSONA si se cambiaron todas sus filas
    de este concepto y todas igual; si quedó alguna con la cédula anterior es
    que se reasignó una fila suelta y no se toca nada más. Tampoco se hace si
    la cédula nueva ya es de otra persona.
    """
    grupos = defaultdict(list)
    for cedula_antes, nombre_antes, fila in identidades:
        if cedula_antes:
            grupos[cedula_antes].append((nombre_antes, fila))
    corregidas = 0
    for vieja, cambios in grupos.items():
        destinos = {(f.cedula, f.nombre if f.nombre != nombre_antes else '') for nombre_antes, f in cambios}
        if len(destinos) != 1:
            avisos.append(f'La cédula {vieja} se cambió de formas distintas en sus filas: '
                          'no se cambió en los demás conceptos')
            continue
        nueva, nombre = destinos.pop()
        if not nueva:
            continue
        propias = {id(f) for _, f in cambios}
        if any(f.cedula == vieja and id(f) not in propias for f in finales):
            continue                       # se reasignó solo una fila: no es la misma persona
        if nueva != vieja and (any(f.cedula == nueva and id(f) not in propias for f in finales)
                               or _cedula_de_otra_persona(nueva, {f.pk for _, f in cambios if f.pk}, vieja)):
            # La fila se le pasó a OTRA persona que ya existe (no es corregir una
            # cédula mal escrita): solo cambia esa fila, nada más.
            avisos.append(f'La cédula {nueva} ya es de otra persona: solo se cambió esta fila, '
                          'no los demás conceptos')
            continue
        try:
            corregir_persona(vieja, nueva, nombre, usuario, ctx=ctx, recalcular=False)
            corregidas += 1
        except ValueError as exc:
            avisos.append(f'{exc}: no se cambió en los demás conceptos')
    return corregidas


def guardar(slug, filas_json, usuario='', con_editados=False):
    """Guarda lo que el usuario editó en la tabla y propaga los cambios.

    Solo se puede guardar en los conceptos base (los que se cargan desde
    Conceptos). Los calculados se rehacen solos.

    - Fila nueva                              → manual
    - Fila calculada con un mes, la cédula, el nombre u otro texto editado
                                              → manual (los meses no editados
                                                quedan con su valor calculado)
    - Fila con `_recalcular`                  → vuelve a ser calculada

    con_editados=True (pantalla con autoguardado): cada fila trae en
    `_editados` los campos que el usuario cambió ('*' = todos). Solo esos se
    toman del navegador; los demás se dejan como están en la base de datos.
    Así una pestaña abierta desde hace rato no deshace lo que se recalculó o
    corrigió mientras tanto (parámetros, cédulas corregidas, distribuciones).

    La tabla llega completa (lo que no viene se borra), así que reenviar lo
    mismo deja el mismo resultado. Para que eso también valga con las filas
    NUEVAS (sin id) cuando el autoguardado reintenta un envío que sí alcanzó
    a guardarse pero cuya respuesta se perdió, una fila nueva idéntica a una
    fila manual que ya existe y que el envío no menciona reutiliza esa fila
    en lugar de crear un duplicado.

    Cada fila nueva puede traer `_uid` (identificador del navegador): se
    devuelve en resumen['nuevos'] = {_uid: id} para que la pantalla sepa el
    id que le tocó sin tener que recargar la tabla.
    """
    c = obtener(slug)
    ignoradas = 0
    if c.derivado and not c.permite_manual:
        raise ValueError(f'{c.etiqueta} se calcula solo: edite el concepto de origen '
                         f"({', '.join(CONCEPTOS[d].etiqueta for d in c.depende)})")
    ctx = Contexto()
    p = ctx.p
    resumen = Counter()
    if ignoradas:
        resumen['calculadas'] = ignoradas

    with bloqueo():
        # En los calculados que admiten filas a mano (bonificaciones foco) también
        # se pueden editar o eliminar las filas calculadas (ver más abajo).
        existentes = {f.pk: f for f in ctx.filas(slug)}
        crear, actualizar, forzadas = [], [], False
        regenerar_concepto = False                  # derivado: volver a calcularlo al final
        restablecidas = []                          # derivado: filas manuales que vuelven a ser calculadas
        bloquear = []                               # derivado: claves calculadas que ya no deben salir
        uids = []                                   # (_uid del navegador, fila)
        identidades = []                            # (cédula antes, nombre antes, fila) si cambiaron

        def pk_de(datos):
            try:
                return int(datos.get('id') or 0)
            except (TypeError, ValueError):
                return 0

        # Filas manuales que este envío no menciona: candidatas a ser la misma
        # fila nueva de un envío anterior que sí se guardó (reintento).
        mencionadas = {pk_de(d) for d in filas_json}
        huerfanas = {}
        for pk, f in existentes.items():
            if pk not in mencionadas and f.origen == MANUAL:
                huerfanas.setdefault(_firma_guardada(f), []).append(f)

        for datos in filas_json:
            pk = pk_de(datos)
            fila = existentes.pop(pk, None)
            if c.derivado and fila is not None:
                marcas0 = set(datos.get('_editados') or []) if con_editados else None
                if fila.origen == MANUAL and datos.get('_recalcular'):
                    # "Restablecer cálculo": se quita la fila manual y vuelve la calculada
                    restablecidas.append(fila)
                    regenerar_concepto = True
                    continue
                if fila.origen == SISTEMA:
                    if marcas0 is None:
                        editada = (any(texto(datos.get(k)) != (getattr(fila, k) or '') for k in CAMPOS_TEXTO
                                       if k != 'cedula')
                                   or cedula_normalizada(texto(datos.get('cedula'))) != (fila.cedula or '')
                                   or any(abs(int(round(numero(datos.get(m)))) - (getattr(fila, m) or 0)) > TOLERANCIA
                                          for m in MESES))
                    else:
                        editada = bool(marcas0 & {'*', 'base', *CAMPOS_TEXTO, *MESES})
                    if not editada:
                        continue                    # fila calculada sin cambios: se deja como está
                    # Editar una fila calculada la vuelve MANUAL (y ya no se recalcula)
                    clave_calculada = fila.clave
                    fila.origen = MANUAL
                    resumen['calculadas_editadas'] += 1
                    bloquear.append((clave_calculada, fila))
            if c.derivado and fila is None and not pk_de(datos) and datos.get('_restaurada') \
                    and datos.get('origen') == SISTEMA:
                # se deshizo la eliminación de una fila calculada: vuelve a calcularse
                FilaEliminadaNomina.objects.filter(tipo=slug, llave=texto(datos.get('clave'))).delete()
                regenerar_concepto = True
                continue
            if fila is None and not pk:
                repetida = huerfanas.get(_firma_entrante(datos))
                if repetida:
                    fila = repetida.pop(0)
                    existentes.pop(fila.pk, None)
                    resumen['reutilizadas'] += 1
            nueva = fila is None
            antes = None
            if nueva:
                fila = PresupuestoNomina(tipo=slug, origen=MANUAL)
                if datos.get('_restaurada') and not c.derivado and datos.get('origen') == SISTEMA:
                    # Fila eliminada que se recuperó con "Deshacer": vuelve tal como
                    # era (calculada, con su clave y su histórico), no como manual.
                    fila.origen = SISTEMA
                    fila.clave = texto(datos.get('clave'))
                    fila.historico = datos.get('historico') if isinstance(datos.get('historico'), dict) else {}
                if datos.get('_restaurada') and not c.derivado:
                    # ya no cuenta como eliminada
                    fila.centro_origen = texto(datos.get('centro_origen'))
                    fila.area_origen = texto(datos.get('area_origen'))
                    fila.clave = fila.clave or texto(datos.get('clave'))
                    fila.concepto = texto(datos.get('concepto'))
                    FilaEliminadaNomina.objects.filter(tipo=slug, llave=llave_eliminada(fila)[:400]).delete()
            if datos.get('_uid'):
                uids.append((str(datos['_uid']), fila))
            if not nueva:
                antes = {campo: getattr(fila, campo) for campo in (*CAMPOS_TEXTO, 'base', *MESES)}

            marcas = set(datos.get('_editados') or []) if con_editados else None

            def tocado(campo, nueva=nueva, marcas=marcas):
                """¿Este campo se toma de lo que envió el navegador?"""
                return nueva or marcas is None or '*' in marcas or campo in marcas

            for campo in CAMPOS_TEXTO:
                if not tocado(campo):
                    continue
                valor = texto(datos.get(campo))
                setattr(fila, campo, cedula_normalizada(valor) if campo == 'cedula' else valor)
            if nueva and c.crea_en_otros and datos.get('crear_en'):
                # conceptos donde la persona nueva debe aparecer (en cero); se crean
                # en cuanto la fila tenga cédula (ver _crear_en_otros)
                pendientes = [s for s in conceptos_para_crear(slug) if s in set(datos['crear_en'])]
                if pendientes:
                    fila.historico = dict(fila.historico or {}, **{CREAR_EN: pendientes})
            if ('excluir_de' in datos or nueva) and tocado('excluir_de'):
                excluir = excluciones_validas(slug, datos.get('excluir_de'))
                if not nueva and excluir != sorted(fila.excluir_de or []):
                    resumen['exclusiones'] += 1
                fila.excluir_de = excluir
            # la cuenta la define el área (NOMCOSTO)
            misma_area = not nueva and _clave_area(antes['area']) == _clave_area(fila.area)
            fila.cuenta = ctx.cuenta(fila.area) or (fila.cuenta if misma_area else '')
            fila.codcosto = ctx.codcosto(fila.area) or (fila.codcosto if misma_area else '')
            if not nueva and (antes['cedula'], antes['nombre']) != (fila.cedula, fila.nombre):
                identidades.append((antes['cedula'], antes['nombre'], fila))
            if c.derivado:
                # así bloquea la fila calculada de esa misma persona
                fila.clave = clave_persona(fila)
                if nueva and datos.get('_restaurada'):
                    FilaEliminadaNomina.objects.filter(tipo=slug, llave=fila.clave).delete()
            if tocado('base'):
                fila.base = int(round(numero(datos.get('base'))))
            if nueva or marcas is None:          # el factor lo maneja la distribución, no la pantalla
                factor = numero(datos.get('factor'), 1)
                fila.factor = factor if factor > 0 else 1
            entrantes = {m: int(round(numero(datos.get(m)))) if tocado(m) else antes[m] for m in MESES}
            fila.actualizado_por = usuario

            forzar = bool(datos.get('_recalcular'))
            era_manual = fila.origen == MANUAL
            if forzar:
                fila.origen = SISTEMA
                forzadas = True
                invertibles = c.invertibles(fila, ctx.meses_reales())
                if not c.derivado and invertibles and not any(m in (fila.historico or {}) for m in MESES):
                    # fila escrita a mano: sus valores pasan a ser el histórico
                    divisor = fila.factor or 1
                    fila.historico = dict(fila.historico or {}, **{m: entrantes[m] / divisor for m in invertibles})
                if not c.derivado:
                    # Los meses que la fila manual tenía en 0 se quedan en 0
                    # (si todos estaban en 0 se calcula todo el año).
                    ceros = [m for m in MESES if not entrantes[m]] if era_manual else []
                    _fijar_meses_cero(fila, ceros if len(ceros) < len(MESES) else [])
                    if ceros and len(ceros) < len(MESES):
                        resumen['meses_cero'] += len(ceros)
            elif meses_en_cero(fila):
                # Si se escribe un valor en un mes que estaba fijo en 0, ese mes se libera.
                _fijar_meses_cero(fila, [m for m in meses_en_cero(fila) if not entrantes[m]])

            # Cambiar a mano la cédula, el nombre, el centro, el área, el cargo o
            # el concepto de una fila calculada la vuelve MANUAL (como editar un mes).
            if (not nueva and not forzar and not c.derivado and fila.origen == SISTEMA
                    and any(antes[campo] != getattr(fila, campo) for campo in CAMPOS_TEXTO)):
                fila.origen = MANUAL
                resumen['texto_editado'] += 1

            if not c.derivado and fila.origen == SISTEMA:
                calculado = calcular(fila, c, p)
                editados = {m for m in MESES if abs(entrantes[m] - calculado[m]) > TOLERANCIA}
                if editados and not forzar:
                    # Editar un mes de una fila calculada la vuelve MANUAL (en todos
                    # los conceptos, también en los de histórico como auxilio TBC y
                    # KIT o comisiones). Los meses no editados quedan como estaban.
                    fila.origen = MANUAL
                    fijar_meses(fila, {m: entrantes[m] if m in editados else calculado[m] for m in MESES})
                else:
                    fijar_meses(fila, calculado)
            else:
                fijar_meses(fila, entrantes)

            if fila.origen == MANUAL and (nueva or antes is None or _cambio(antes, fila)):
                resumen['manuales'] += 1
            (crear if nueva else actualizar).append(fila)

        # Filas que el usuario quitó de la tabla (las de Conceptos no vuelven al recargar)
        eliminar = [fila.pk for fila in existentes.values()]
        if not c.derivado:
            _recordar_eliminadas(c, existentes.values(), usuario)
        else:
            # calculados (bonificaciones foco): lo eliminado no vuelve al recalcular
            for fila in existentes.values():
                if fila.clave:
                    FilaEliminadaNomina.objects.update_or_create(
                        tipo=slug, llave=fila.clave[:400],
                        defaults={'nombre': fila.nombre or fila.concepto, 'eliminado_por': usuario})
            # la fila editada (ahora manual) reemplaza a la calculada aunque se le cambie el área
            for clave_calculada, fila in bloquear:
                if clave_calculada and clave_calculada != fila.clave:
                    FilaEliminadaNomina.objects.update_or_create(
                        tipo=slug, llave=clave_calculada[:400],
                        defaults={'nombre': fila.nombre or fila.concepto, 'eliminado_por': usuario})
            for fila in restablecidas:
                eliminar.append(fila.pk)
                FilaEliminadaNomina.objects.filter(tipo=slug, llave=fila.clave).delete()
            if crear:
                regenerar_concepto = True           # una fila nueva puede reemplazar a una calculada

        campos = [*CAMPOS_TEXTO, 'cuenta', 'codcosto', 'excluir_de', 'base', 'factor', 'historico',
                  *MESES, 'total', 'origen', 'actualizado_por']
        PresupuestoNomina.objects.filter(pk__in=eliminar).delete()
        PresupuestoNomina.objects.bulk_update(actualizar, campos, batch_size=1000)
        PresupuestoNomina.objects.bulk_create(crear, batch_size=1000)
        ctx.olvidar(slug)
        if c.derivado and regenerar_concepto:
            regenerar(ctx, c)

        # Persona nueva en Sueldos: su fila en cero en los demás conceptos elegidos
        en_cero = _crear_en_otros(crear + actualizar, usuario, ctx)
        if en_cero:
            resumen['filas_en_cero'] = sum(len(v) for v in en_cero.values())

        # Cédula o nombre corregidos en un concepto base: se corrigen en todos
        # los demás conceptos (y en las próximas cargas desde Conceptos).
        avisos = []
        corregidas = 0 if c.derivado else _propagar_identidades(identidades, crear + actualizar,
                                                                usuario, ctx, avisos)
        if corregidas:
            resumen['personas_corregidas'] = corregidas
            for d in DERIVADOS:
                regenerar(ctx, d)
            recalculados = [d.slug for d in DERIVADOS]
        else:
            recalculados = propagar(slug, ctx)

    resumen.update(creadas=len(crear), actualizadas=len(actualizar), eliminadas=len(eliminar))
    salida = dict(resumen)
    salida['avisos'] = avisos
    if en_cero:
        salida['avisos'].insert(0, 'Fila en cero creada en ' + ' · '.join(
            f"{', '.join(CONCEPTOS[s].etiqueta for s in slugs)} para {quien}" for quien, slugs in en_cero.items()))
    salida['nuevos'] = {uid: fila.pk for uid, fila in uids if fila is not None and fila.pk}
    return salida, recalculados


# ══════════════════════════════════════════════════════════════════════
#  Lectura
# ══════════════════════════════════════════════════════════════════════

CAMPOS_SALIDA = ('id', 'tipo', *CAMPOS_TEXTO, 'centro_origen', 'area_origen', 'cuenta', 'codcosto', 'excluir_de', 'base', 'factor', 'historico',
                 *MESES, 'total', 'origen', 'clave', 'actualizado', 'actualizado_por')


ORDEN_CONCEPTO = {c.slug: i for i, c in enumerate(_LISTA)}


def _orden_fila(fila):
    """Nombre y centro alfabéticos (sin tildes ni mayúsculas); los vacíos al final."""
    nombre = _sin_tildes(fila.get('nombre'))
    centro = _sin_tildes(fila.get('centro'))
    return (not nombre, nombre, not centro, centro, _sin_tildes(fila.get('area')),
            ORDEN_CONCEPTO.get(fila['tipo'], len(ORDEN_CONCEPTO)),
            _sin_tildes(fila.get('concepto')), fila['id'])

def listar(slug=None):
    qs = PresupuestoNomina.objects.all()
    if slug:
        qs = qs.filter(tipo=slug)
    filas = list(qs.values(*CAMPOS_SALIDA))
    filas.sort(key=_orden_fila)
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
