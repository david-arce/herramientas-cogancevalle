"""
Depuración de conteos e inventario.

1) Por mes (fecha de asignación de la tarea) — apartado "Depurar conteos":
   * Se eliminan las tareas de los meses elegidos y las filas de inventario que
     quedan sin ninguna tarea: las que usaban esas tareas y las de los cortes de
     inventario de esos meses (por fecha de corte) que ninguna tarea usa.
   * Se CONSERVAN las filas de inventario que todavía usan tareas de otros meses
     y las del corte más reciente de cada bodega (es el que se usa para asignar).
   * El mes en curso no se puede depurar (tiene el conteo del día).

2) Por corte y bodega — apartado "Depurar inventario":
   * Se eliminan solo filas de inventario que no aparecen en la tabla de tareas.
   * El corte más reciente de cada bodega no se puede depurar.

Todo se calcula y borra dentro de la base de datos (subconsultas), sin traer
las filas a Python, y cada borrado es todo o nada (transacción).
"""
import datetime

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Exists, Max, Min, OuterRef, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone

from .models import Inventario, Tarea

MESES_ES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
            'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
LOTE = 5000  # tamaño de lote para listas de IDs (límite de parámetros de PostgreSQL)
SIN_CORTE = 'sin-corte'


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────────────────────────────────────────
def nombre_mes(fecha):
    return f"{MESES_ES[fecha.month - 1].capitalize()} {fecha.year}"


def inicio_mes_actual(hoy=None):
    hoy = hoy or datetime.date.today()
    return hoy.replace(day=1)


def parse_meses(valores, hoy=None):
    """'2026-08' -> date(2026, 8, 1). Ignora valores inválidos y el mes en curso o futuros."""
    limite = inicio_mes_actual(hoy)
    meses = set()
    for v in valores:
        try:
            anio, mes = str(v).split('-')
            d = datetime.date(int(anio), int(mes), 1)
        except (ValueError, TypeError):
            continue
        if d < limite:
            meses.add(d)
    return sorted(meses)


def _siguiente_mes(d):
    return datetime.date(d.year + (d.month == 12), d.month % 12 + 1, 1)


def _a_datetime(d):
    dt = datetime.datetime(d.year, d.month, d.day)
    return timezone.make_aware(dt) if settings.USE_TZ else dt


def _filtro_meses(meses):
    """Tareas cuya fecha de asignación cae en alguno de los meses."""
    q = Q()
    for d in meses:
        q |= Q(fecha_asignacion__gte=d, fecha_asignacion__lt=_siguiente_mes(d))
    return q


def _filtro_cortes_meses(meses):
    """Filas de inventario cuya fecha de corte cae en alguno de los meses."""
    q = Q()
    for d in meses:
        q |= Q(fecha_corte__gte=_a_datetime(d), fecha_corte__lt=_a_datetime(_siguiente_mes(d)))
    return q


def _lotes(ids):
    ids = list(ids)
    for i in range(0, len(ids), LOTE):
        yield ids[i:i + LOTE]


def _con_tareas():
    """True si alguna tarea apunta a la fila de inventario."""
    return Exists(Tarea.objects.filter(producto_id=OuterRef('pk')))


def _q_en_tareas():
    """
    Mismo criterio que _con_tareas(), para contar muchas filas a la vez: PostgreSQL
    arma una sola vez el conjunto de IDs usados en tareas (hashed subplan) en vez
    de consultar fila por fila.
    """
    return Q(pk__in=Tarea.objects.order_by().values('producto_id'))


def ultimos_cortes():
    """{bodega: fecha del corte más reciente}"""
    return {r['bod']: r['m'] for r in Inventario.objects.order_by().values('bod').annotate(m=Max('fecha_corte'))}


def _filtro_corte_reciente(cortes=None):
    """Filas que pertenecen al corte más reciente de su bodega (protegidas)."""
    cortes = ultimos_cortes() if cortes is None else cortes
    q = Q(pk__in=[])
    for bod, corte in cortes.items():
        q |= Q(bod=bod, fecha_corte=corte) if corte is not None else Q(bod=bod, fecha_corte__isnull=True)
    return q


def _borrar_sin_tareas(qs):
    """
    Borra las filas del queryset que no tienen tareas, en una sola sentencia SQL.
    Como ninguna tarea apunta a ellas no hay nada que borrar en cascada; si en
    ese instante otra persona les asigna una tarea, la llave foránea de la BD
    hace fallar la transacción y no se borra nada.
    """
    qs = qs.filter(~_con_tareas())
    return qs._raw_delete(qs.db)


# ─────────────────────────────────────────────────────────────────────────────
# 1) Depurar conteos por mes
# ─────────────────────────────────────────────────────────────────────────────
def resumen_general(hoy=None):
    """Rango de fechas con conteos y cantidad de tareas por mes."""
    limite = inicio_mes_actual(hoy)
    rango = Tarea.objects.aggregate(desde=Min('fecha_asignacion'), hasta=Max('fecha_asignacion'), total=Count('id'))
    meses = []
    for fila in (Tarea.objects.annotate(mes=TruncMonth('fecha_asignacion'))
                 .values('mes')
                 .annotate(tareas=Count('id'), desde=Min('fecha_asignacion'), hasta=Max('fecha_asignacion'))
                 .order_by('mes')):
        mes = fila['mes']
        if isinstance(mes, datetime.datetime):
            mes = mes.date()
        meses.append({
            'clave': mes.strftime('%Y-%m'),
            'nombre': nombre_mes(mes),
            'tareas': fila['tareas'],
            'desde': fila['desde'],
            'hasta': fila['hasta'],
            'bloqueado': mes >= limite,
        })
    return rango, meses


def planificar(meses):
    """Calcula qué se borraría, sin borrar nada."""
    plan = {'meses': meses, 'tareas': 0, 'inventario_de_tareas': 0, 'inventario_sin_tareas': 0,
            'protegidas_otros_meses': 0, 'protegidas_corte_reciente': 0}
    if not meses:
        return plan

    filtro = _filtro_meses(meses)
    plan['tareas'] = Tarea.objects.filter(filtro).count()

    candidatas = Inventario.objects.annotate(
        en_meses=Exists(Tarea.objects.filter(filtro, producto_id=OuterRef('pk'))),
        en_otros=Exists(Tarea.objects.filter(producto_id=OuterRef('pk')).exclude(filtro)),
    ).filter(Q(en_meses=True) | _filtro_cortes_meses(meses))

    reciente = _filtro_corte_reciente()
    libres = candidatas.filter(en_otros=False)          # quedarían sin ninguna tarea
    borrar = libres.exclude(reciente)

    conteo = borrar.aggregate(
        de_tareas=Count('id', filter=Q(en_meses=True)),
        sin_tareas=Count('id', filter=Q(en_meses=False)),
    )
    plan['inventario_de_tareas'] = conteo['de_tareas']
    plan['inventario_sin_tareas'] = conteo['sin_tareas']
    plan['protegidas_otros_meses'] = candidatas.filter(en_meses=True, en_otros=True).count()
    plan['protegidas_corte_reciente'] = libres.filter(reciente).count()
    return plan


@transaction.atomic
def ejecutar(meses):
    """Borra según planificar(). Todo o nada: si algo falla no se borra nada."""
    plan = planificar(meses)
    if not plan['meses']:
        return {'tareas': 0, 'inventario': 0, 'plan': plan}

    filtro = _filtro_meses(meses)
    # IDs de inventario que usaban las tareas de esos meses (antes de borrarlas)
    usadas = list(Tarea.objects.filter(filtro).values_list('producto_id', flat=True).distinct())

    # 1) Tareas de esos meses
    _, detalle = Tarea.objects.filter(filtro).delete()
    tareas_borradas = detalle.get(Tarea._meta.label, 0)

    # 2) Inventario que quedó sin tareas: el que usaban esas tareas y el de los
    #    cortes de esos meses. Nunca el corte más reciente de cada bodega.
    reciente = _filtro_corte_reciente()
    inventario_borrado = 0
    for lote in _lotes(usadas):
        inventario_borrado += _borrar_sin_tareas(Inventario.objects.filter(id__in=lote).exclude(reciente))
    inventario_borrado += _borrar_sin_tareas(Inventario.objects.filter(_filtro_cortes_meses(meses)).exclude(reciente))

    return {'tareas': tareas_borradas, 'inventario': inventario_borrado, 'plan': plan}


# ─────────────────────────────────────────────────────────────────────────────
# 2) Depurar inventario por corte y bodega
# ─────────────────────────────────────────────────────────────────────────────
def clave_grupo(bod, corte):
    return f"{bod}|{corte.isoformat() if corte else SIN_CORTE}"


def parse_grupo(clave):
    """'0101|2026-08-10T11:00:00+00:00' -> ('0101', datetime). None si es inválida."""
    bod, sep, corte = str(clave).partition('|')
    if not sep or not bod:
        return None
    if corte == SIN_CORTE:
        return bod, None
    try:
        return bod, datetime.datetime.fromisoformat(corte)
    except ValueError:
        return None


def _filtro_grupo(bod, corte):
    return Q(bod=bod, fecha_corte=corte) if corte is not None else Q(bod=bod, fecha_corte__isnull=True)


def bodegas_inventario():
    return list(Inventario.objects.order_by('bod').values('bod').annotate(nombre=Max('bod_nom')))


def _filtro_tabla(bod=None, hasta=None):
    """Filtro de la tabla de inventario: bodega y/o cortes hasta una fecha (las filas sin fecha siempre se incluyen)."""
    q = Q()
    if bod:
        q &= Q(bod=bod)
    if hasta:
        q &= Q(fecha_corte__lt=_a_datetime(hasta + datetime.timedelta(days=1))) | Q(fecha_corte__isnull=True)
    return q


def parse_fecha(valor):
    try:
        return datetime.date.fromisoformat(str(valor))
    except (TypeError, ValueError):
        return None


def resumen_inventario(bod=None, hasta=None):
    """Filas por corte y bodega, cuántas tienen tareas y cuántas no."""
    qs = Inventario.objects.filter(_filtro_tabla(bod, hasta))

    cortes = ultimos_cortes()
    grupos = []
    for g in (qs.values('fecha_corte', 'bod')
              .annotate(filas=Count('id'), con_tareas=Count('id', filter=_q_en_tareas()), bod_nom=Max('bod_nom'))
              .order_by('-fecha_corte', 'bod')):
        g['sin_tareas'] = g['filas'] - g['con_tareas']
        g['reciente'] = cortes.get(g['bod']) == g['fecha_corte']
        g['clave'] = clave_grupo(g['bod'], g['fecha_corte'])
        grupos.append(g)
    total = {k: sum(g[k] for g in grupos) for k in ('filas', 'con_tareas', 'sin_tareas')}
    total['grupos_elegibles'] = sum(1 for g in grupos if not g['reciente'] and g['sin_tareas'])
    return total, grupos


def filas_grupo(bod, corte, solo_sin_tareas=False):
    qs = (Inventario.objects.filter(_filtro_grupo(bod, corte))
          .annotate(en_tareas=_con_tareas())
          .order_by('marca_nom', 'sku', 'lpt', 'id'))
    if solo_sin_tareas:
        qs = qs.filter(en_tareas=False)
    return qs


def _grupos_validos(claves):
    """Grupos elegidos, sin los del corte más reciente de su bodega."""
    cortes = ultimos_cortes()
    grupos = set()
    for c in claves:
        g = parse_grupo(c)
        if g and g[0] in cortes and cortes[g[0]] != g[1]:
            grupos.add(g)
    return sorted(grupos, key=lambda g: (g[0], g[1] or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)))


def _filtro_grupos(grupos):
    q = Q(pk__in=[])
    for bod, corte in grupos:
        q |= _filtro_grupo(bod, corte)
    return q


def _filtro_seleccion(seleccion):
    """
    seleccion = {'todos': bool, 'bod': str|None, 'hasta': date|None, 'claves': [...]}
    'todos' = todos los cortes que muestra la tabla con ese filtro (sin enviar una
    clave por corte, que con muchos cortes supera el límite de campos de Django).
    Devuelve (filtro, número de grupos) o (None, 0) si no hay nada elegido.
    """
    if seleccion.get('todos'):
        filtro = _filtro_tabla(seleccion.get('bod'), seleccion.get('hasta'))
        n = (Inventario.objects.filter(filtro).exclude(_filtro_corte_reciente())
             .values('bod', 'fecha_corte').distinct().count())
        return (filtro, n) if n else (None, 0)
    grupos = _grupos_validos(seleccion.get('claves') or [])
    return (_filtro_grupos(grupos), len(grupos)) if grupos else (None, 0)


def planificar_inventario(seleccion):
    filtro, n = _filtro_seleccion(seleccion)
    plan = {'n_grupos': n, 'sin_tareas': 0, 'con_tareas': 0}
    if filtro is None:
        return plan
    conteo = Inventario.objects.filter(filtro).exclude(_filtro_corte_reciente()).aggregate(
        filas=Count('id'), con_tareas=Count('id', filter=_q_en_tareas()))
    plan['con_tareas'] = conteo['con_tareas']
    plan['sin_tareas'] = conteo['filas'] - conteo['con_tareas']
    return plan


@transaction.atomic
def ejecutar_inventario(seleccion):
    """Borra las filas sin tareas de la selección (nunca el corte más reciente). Todo o nada."""
    filtro, n = _filtro_seleccion(seleccion)
    if filtro is None:
        return {'inventario': 0, 'n_grupos': 0}
    borradas = _borrar_sin_tareas(Inventario.objects.filter(filtro).exclude(_filtro_corte_reciente()))
    return {'inventario': borradas, 'n_grupos': n}
