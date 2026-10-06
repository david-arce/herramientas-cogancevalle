import datetime
import logging

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Max, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from django.urls import reverse
from urllib.parse import urlencode

from .models import Inventario, Tarea, User, UserCity, Venta
from . import depuracion
from .permisos import USUARIOS_ADMIN, puede_depurar

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constantes (antes estaban repetidas dentro de cada vista)
# ─────────────────────────────────────────────────────────────────────────────

BODEGA_ALMACEN_POR_CIUDAD = {
    'Tulua': '0101',
    'Buga': '0201',
    'Cartago': '0301',
    'Cali': '0401',
}
BODEGA_CONTEO_EXTRA = '0105'
MARCAS_EXCLUIDAS = ['INSMEVET', 'JL INSTRUMENTAL', 'LHAURA', 'FEDEGAN']

COLUMNAS_EXPORTACION = {
    'usuario__first_name': 'Nombre',
    'usuario__last_name': 'Apellido',
    'producto__marca_nom': 'Marca',
    'producto__sku': 'Item',
    'producto__sku_nom': 'Nombre Producto',
    'producto__lpt': 'Fecha Vencimiento',
    'inventario': 'Inventario',
    'conteo': 'Conteo',
    'diferencia': 'Diferencia',
    'producto__vlr_unit': 'Valor Unitario',
    'consolidado': 'Valor total',
    'observacion': 'Observaciones',
    'fecha_asignacion': 'Fecha Asignación',
    'verificado': 'Verificado',
}

# Acciones de solo consulta del panel de asignación. Se atienden por GET para
# que recargar la página no vuelva a enviar un formulario (POST "anclado").
ACCIONES_CONSULTA = (
    'filter_users', 'filter_all_users', 'view_user_tasks',
    'view_all_user_tasks', 'view_all_tasks', 'ver_no_verificados',
)


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────────────────────────────────────────
def _ciudad_usuario(user, default="No asignada"):
    try:
        return user.usercity.ciudad
    except UserCity.DoesNotExist:
        return default


def _ids_validos(valores):
    """Deja solo IDs numéricos (evita errores 500 por valores manipulados)."""
    if isinstance(valores, (str, int)):
        valores = [valores]
    return [str(v) for v in valores if str(v).strip().isdigit()]


def _parse_fecha(valor):
    try:
        return datetime.date.fromisoformat(str(valor))
    except (TypeError, ValueError):
        return None


def get_fecha_asignar(bodega=None):
    """
    Busca la fecha de venta más reciente disponible en la BD,
    anterior a hoy, para la bodega indicada (opcional).
    """
    hoy = datetime.date.today()
    qs = Venta.objects.filter(fecha__lt=hoy.strftime("%Y%m%d"))  # Fechas anteriores a hoy
    if bodega:
        qs = qs.filter(bod=bodega)

    # MAX() en lugar de ORDER BY ... LIMIT 1: mismo resultado sin ordenar toda la tabla.
    ultima_venta = qs.aggregate(m=Max('fecha'))['m']
    if ultima_venta:
        return ultima_venta  # Ya viene en formato YYYYMMDD desde la BD

    # Fallback: si no hay nada en BD, usar lógica anterior
    hoy_dt = datetime.datetime.now()
    if hoy_dt.weekday() == 0:
        return (hoy_dt - datetime.timedelta(days=2)).strftime("%Y%m%d")
    return (hoy_dt - datetime.timedelta(days=1)).strftime("%Y%m%d")


def _skus_vendidos(bodega, fechas):
    """Subconsulta con los SKU vendidos en la bodega/fechas (no se trae a Python)."""
    return (
        Venta.objects
        .filter(sku__regex=r'^\d+$', bod=bodega, fecha__in=fechas)
        .exclude(marca_nom__in=MARCAS_EXCLUIDAS)
        .values('sku')
    )


def _inventario_disponible(bodega, fechas):
    """
    Productos de inventario con saldo > 0 en el corte más reciente, para los SKU
    vendidos en la bodega/fechas indicadas. Misma lógica que antes, pero resuelta
    con subconsultas dentro de la BD en vez de cargar miles de filas de ventas.
    """
    base = Inventario.objects.filter(sku__in=_skus_vendidos(bodega, fechas), bod=bodega)
    fecha_corte_reciente = base.aggregate(m=Max('fecha_corte'))['m']
    return base.filter(inv_saldo__gt=0, fecha_corte=fecha_corte_reciente)


def _tareas_con_producto(qs):
    """Evita una consulta por fila al pintar la tabla (N+1)."""
    return qs.select_related('producto').order_by('id')


# ─────────────────────────────────────────────────────────────────────────────
# Panel de asignación
# ─────────────────────────────────────────────────────────────────────────────
@login_required
# @permission_required('conteoApp.view_tarea', raise_exception=True)
def asignar_tareas(request):
    if request.user.username not in USUARIOS_ADMIN:
        raise PermissionDenied("No tienes permiso para acceder a esta vista.")

    ciudad = _ciudad_usuario(request.user)

    if request.method == 'POST':
        if 'assign_task' in request.POST:
            _asignar(request, ciudad)
            return redirect('asignar_tareas')

        if 'delete_task' in request.POST:
            usuarios_sede = User.objects.filter(usercity__ciudad=ciudad)
            Tarea.objects.filter(usuario__in=usuarios_sede, fecha_asignacion=datetime.date.today()).delete()
            return redirect('asignar_tareas')

        if 'export_excel' in request.POST:
            return _exportar(request, solo_diferencias=False)

        if 'export_excel_diferencias' in request.POST:
            return _exportar(request, solo_diferencias=True)

        # Compatibilidad: si llega una consulta por POST (p. ej. una pestaña abierta
        # con la versión anterior), se redirige a la misma consulta por GET.
        params = request.POST.copy()
        params.pop('csrfmiddlewaretoken', None)
        destino = reverse('asignar_tareas')
        if any(a in params for a in ACCIONES_CONSULTA):
            destino = f"{destino}?{params.urlencode()}"
        return redirect(destino)

    # ── GET ──────────────────────────────────────────────────────────────────
    consulta = _resolver_consulta(request, ciudad)
    if isinstance(consulta, HttpResponse):
        return consulta
    tareas, cant_tareas_por_usuario, mostrar_exportar_todo, tipo_bodega_actual = consulta

    hoy = datetime.date.today()
    fecha_asignar = get_fecha_asignar()
    bodega = BODEGA_ALMACEN_POR_CIUDAD.get(ciudad, '')

    # Resumen de tareas de hoy por usuario y tipo de bodega: 1 consulta en vez de 4.
    resumen = (
        Tarea.objects
        .filter(fecha_asignacion=hoy, usuario__usercity__ciudad=ciudad, tipo_bodega__in=['0101', BODEGA_CONTEO_EXTRA])
        .values('tipo_bodega', 'usuario__id', 'usuario__username', 'usuario__first_name', 'usuario__last_name')
        .annotate(total_tareas=Count('id'))
        .order_by('usuario__first_name', 'usuario__last_name', 'usuario__id')
    )
    usuarios_con_tareas_almacen = [r for r in resumen if r['tipo_bodega'] == '0101']
    usuarios_con_tareas_bodega = [r for r in resumen if r['tipo_bodega'] == BODEGA_CONTEO_EXTRA]

    # usuarios que se mostraran en el select de la vista
    usuarios = (
        User.objects.exclude(username="admin")
        .filter(usercity__ciudad=ciudad, is_active=True)
        .order_by('first_name', 'last_name')
    )

    total_tareas_hoy_almacen = _inventario_disponible(bodega, [fecha_asignar]).count() if bodega else 0
    # La sección de Bodega 0105 solo se muestra en Tuluá: no se calcula para las demás sedes.
    total_tareas_hoy_bodega = (
        _inventario_disponible(BODEGA_CONTEO_EXTRA, [fecha_asignar]).count() if ciudad == 'Tulua' else 0
    )

    # formatear la fecha para mostrar en la vista
    fecha_asignar_formateada = datetime.datetime.strptime(fecha_asignar, "%Y%m%d").strftime("%Y-%m-%d")

    return render(request, 'conteoApp/asignar_tareas.html', {
        'tareas': tareas,
        'cant_tareas_por_usuario': cant_tareas_por_usuario,
        'usuarios_con_tareas_almacen': usuarios_con_tareas_almacen,
        'usuarios_con_tareas_bodega': usuarios_con_tareas_bodega,
        'total_tareas_almacen': sum(r['total_tareas'] for r in usuarios_con_tareas_almacen),
        'total_tareas_bodega': sum(r['total_tareas'] for r in usuarios_con_tareas_bodega),
        'total_tareas_hoy_almacen': total_tareas_hoy_almacen,
        'total_tareas_hoy_bodega': total_tareas_hoy_bodega,
        'usuarios': usuarios,
        'mostrar_exportar_todo': mostrar_exportar_todo,
        'fecha_asignar': fecha_asignar_formateada,
        'ciudad': ciudad,
        'tipo_bodega_actual': tipo_bodega_actual,
    })


def _resolver_consulta(request, ciudad):
    """
    Interpreta la consulta pedida por GET (mismos nombres de botones y campos que
    antes). Devuelve (tareas, cant_tareas_por_usuario, mostrar_exportar_todo,
    tipo_bodega) o un redirect si faltan datos. Guarda en sesión lo necesario
    para los botones de exportar, igual que la versión anterior.
    """
    q = request.GET
    session = request.session
    hoy = datetime.date.today()
    tipo_bodega = q.get('tipo_bodega', '0101')
    tareas = None
    cant_tareas_por_usuario = []
    mostrar_exportar_todo = True

    if not any(a in q for a in ACCIONES_CONSULTA):
        return tareas, cant_tareas_por_usuario, mostrar_exportar_todo, session.get('tipo_bodega', '0101')

    session['tipo_bodega'] = tipo_bodega

    if 'filter_users' in q:
        selected_user_ids = _ids_validos(q.getlist('usuarios'))
        fecha = _parse_fecha(q.get('fecha_asignacion'))
        if fecha is None:
            messages.error(request, "Por favor selecciona una fecha.")
            return redirect('asignar_tareas')
        session['selected_user_ids'] = selected_user_ids
        session['fecha_asignacion'] = fecha.isoformat()
        if not selected_user_ids:
            tareas = []
        else:
            filtro = dict(usuario__in=selected_user_ids, fecha_asignacion=fecha, tipo_bodega=tipo_bodega)
            tareas = _tareas_con_producto(Tarea.objects.filter(**filtro))
            # Antes se filtraba por una variable vacía y el resumen nunca aparecía.
            cant_tareas_por_usuario = (
                Tarea.objects.filter(**filtro)
                .values('usuario__username', 'usuario__first_name', 'usuario__last_name')
                .annotate(total_tareas=Count('id'))
                .order_by('usuario__first_name', 'usuario__last_name')
            )

    elif 'filter_all_users' in q:
        fecha = _parse_fecha(q.get('fecha_asignacion'))
        if fecha is None:
            messages.error(request, "Por favor selecciona una fecha.")
            return redirect('asignar_tareas')
        usuarios_sede = User.objects.filter(usercity__ciudad=ciudad, is_active=True).exclude(username="admin")
        session['selected_user_ids'] = [str(i) for i in usuarios_sede.values_list('id', flat=True)]
        session['fecha_asignacion'] = fecha.isoformat()
        filtro = dict(usuario__in=usuarios_sede, fecha_asignacion=fecha, tipo_bodega=tipo_bodega)
        tareas = _tareas_con_producto(Tarea.objects.filter(**filtro))
        cant_tareas_por_usuario = (
            Tarea.objects.filter(**filtro)
            .values('usuario__username', 'usuario__first_name', 'usuario__last_name')
            .annotate(total_tareas=Count('id'))
            .order_by('usuario__first_name', 'usuario__last_name')
        )

    elif 'view_user_tasks' in q:
        usuario_ids = _ids_validos(q.get('usuario_id', ''))
        tareas = _tareas_con_producto(
            Tarea.objects.filter(
                usuario__id__in=usuario_ids, fecha_asignacion=hoy,
                usuario__usercity__ciudad=ciudad, tipo_bodega=tipo_bodega,
            ).exclude(diferencia=0)
        )
        # Antes se guardaba el ID como texto ("12") y al exportar se leía como ["1", "2"].
        session['selected_user_ids'] = usuario_ids
        session['fecha_asignacion'] = str(hoy)

    elif 'view_all_user_tasks' in q:
        filtro = Tarea.objects.filter(
            fecha_asignacion=hoy, activo=True, usuario__usercity__ciudad=ciudad, tipo_bodega=tipo_bodega,
        ).exclude(diferencia=0)
        tareas = _tareas_con_producto(filtro)
        session['selected_user_ids'] = [str(i) for i in filtro.order_by().values_list('usuario__id', flat=True).distinct()]
        session['fecha_asignacion'] = str(hoy)
        mostrar_exportar_todo = False

    elif 'view_all_tasks' in q:
        filtro = Tarea.objects.filter(fecha_asignacion=hoy, usuario__usercity__ciudad=ciudad, tipo_bodega=tipo_bodega)
        tareas = _tareas_con_producto(filtro)
        session['selected_user_ids'] = [str(i) for i in filtro.order_by().values_list('usuario__id', flat=True).distinct()]
        session['fecha_asignacion'] = str(hoy)

    elif 'ver_no_verificados' in q:
        tareas = _tareas_con_producto(
            Tarea.objects.filter(
                fecha_asignacion=hoy, usuario__usercity__ciudad=ciudad, verificado=False, tipo_bodega=tipo_bodega,
            )
        )

    return tareas, cant_tareas_por_usuario, mostrar_exportar_todo, tipo_bodega


def _asignar(request, ciudad):
    """Reparte los productos disponibles entre los usuarios seleccionados."""
    fecha_asignar = get_fecha_asignar()
    hoy = datetime.date.today()
    selected_user_ids = _ids_validos(request.POST.getlist('usuarios'))
    selected_users = User.objects.filter(id__in=selected_user_ids).select_related('usercity').order_by('id')

    fechas_raw = request.POST.getlist('fechas_venta')
    fechas_asignar = [f.strip().replace('-', '') for f in fechas_raw if f.strip()]
    if not fechas_asignar:
        fechas_asignar = [fecha_asignar]
    logger.debug("Fechas para asignar: %s", fechas_asignar)

    # Agrupar usuarios seleccionados según su bodega_asignada (0101 / 0105 / etc.)
    grupos_usuarios = {}
    for usuario in selected_users:
        try:
            tipo_bodega_usuario = usuario.usercity.bodega_asignada
        except UserCity.DoesNotExist:
            continue  # usuario sin bodega asignada, se ignora
        grupos_usuarios.setdefault(tipo_bodega_usuario, []).append(usuario)

    if not grupos_usuarios:
        messages.error(request, "Los usuarios seleccionados no tienen bodega asignada.")
        return

    tareas_a_crear = []
    with transaction.atomic():
        for tipo_bodega, usuarios_grupo in grupos_usuarios.items():
            if tipo_bodega == '0101':
                bodega = BODEGA_ALMACEN_POR_CIUDAD.get(ciudad, '')
            else:
                bodega = tipo_bodega  # ej. '0105'

            if not bodega:
                messages.error(request, f"Bodega no válida para el grupo '{tipo_bodega}'.")
                continue

            # Ordenar también por SKU garantiza que los lotes de un mismo producto queden
            # contiguos y, por tanto, en el mismo usuario (antes podían partirse).
            productos_disponibles = list(
                _inventario_disponible(bodega, fechas_asignar)
                .order_by('marca_nom', 'sku', 'id')
                .only('id', 'sku', 'inv_saldo')
            )
            logger.debug("[%s] Cantidad de productos disponibles: %s", tipo_bodega, len(productos_disponibles))

            if not productos_disponibles:
                messages.error(request, f"No hay productos disponibles para asignar en '{tipo_bodega}'.")
                continue

            # Productos ya asignados hoy: 1 consulta en vez de una por producto.
            ya_asignados = set(
                Tarea.objects.filter(fecha_asignacion=hoy, tipo_bodega=tipo_bodega)
                .values_list('producto_id', flat=True)
            )

            total = len(productos_disponibles)
            por_usuario, restantes = divmod(total, len(usuarios_grupo))
            inicio = 0
            for usuario in usuarios_grupo:
                cantidad = por_usuario
                if restantes > 0:
                    cantidad += 1
                    restantes -= 1

                fin = min(inicio + cantidad, total)
                # No partir un mismo SKU entre dos usuarios: se extiende hasta el último lote.
                while inicio < fin < total and productos_disponibles[fin].sku == productos_disponibles[fin - 1].sku:
                    fin += 1

                for producto in productos_disponibles[inicio:fin]:
                    if producto.id in ya_asignados:
                        continue
                    ya_asignados.add(producto.id)
                    tareas_a_crear.append(Tarea(
                        usuario=usuario,
                        producto=producto,
                        observacion='',
                        inventario=producto.inv_saldo,
                        tipo_bodega=tipo_bodega,
                    ))
                inicio = fin

        Tarea.objects.bulk_create(tareas_a_crear, batch_size=1000)


def _exportar(request, solo_diferencias):
    """Exporta a Excel las tareas de la última consulta mostrada."""
    session = request.session
    selected_user_ids = _ids_validos(session.get('selected_user_ids', []))
    fecha_asignacion = session.get('fecha_asignacion')
    tipo_bodega = request.POST.get('tipo_bodega') or session.get('tipo_bodega', '0101')
    session['tipo_bodega'] = tipo_bodega

    # Si no hay nada que exportar se vuelve a la misma consulta (no a la página vacía).
    volver = redirect(request.get_full_path())
    if not (selected_user_ids and fecha_asignacion):
        return volver

    tareas = Tarea.objects.filter(
        usuario__in=selected_user_ids, fecha_asignacion=fecha_asignacion, tipo_bodega=tipo_bodega,
    )
    if solo_diferencias:
        tareas = tareas.filter(activo=True).exclude(diferencia=0)

    filas = list(tareas.order_by('id').values(*COLUMNAS_EXPORTACION.keys()))
    if not filas:
        return volver

    df = pd.DataFrame(filas)
    # Cambiar True/False a 'OK' o ''
    df['verificado'] = df['verificado'].map(lambda x: 'OK' if x else '')
    df.rename(columns=COLUMNAS_EXPORTACION, inplace=True)

    nombre = 'diferencias.xlsx' if solo_diferencias else 'tareas.xlsx'
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename={nombre}'
    df.to_excel(response, index=False)
    # Ya no se borra la sesión: así se puede exportar "todo" y luego "diferencias"
    # (antes la segunda exportación fallaba y devolvía la página vacía).
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Vista del contador
# ─────────────────────────────────────────────────────────────────────────────
@login_required
@permission_required('conteoApp.view_tarea', raise_exception=True)
def lista_tareas(request):
    ciudad = _ciudad_usuario(request.user, default=None)
    bodega = BODEGA_ALMACEN_POR_CIUDAD.get(ciudad, '')  # Obtener la bodega según la ciudad, o '' si no se encuentra
    hoy = datetime.date.today()

    def tareas_activas():
        return (
            Tarea.objects.filter(usuario=request.user, fecha_asignacion=hoy, activo=True)
            .select_related('producto')
            .order_by('tipo_bodega', 'producto__marca_nom', 'producto__sku', 'id')
        )

    if request.method == 'POST':
        es_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        if 'update_tarea' not in request.POST:
            return redirect('lista_tareas')

        # Evitar consultas si no hay bodega asignada
        tareas = list(tareas_activas()) if bodega else []
        resultado = _actualizar_conteo(request, tareas, hoy)
        if resultado is not None:  # error
            return JsonResponse(resultado) if es_ajax else redirect('lista_tareas')

        if not es_ajax:
            return redirect('lista_tareas')  # PRG: recargar no reenvía el formulario

        try:
            html = render_to_string(
                'conteoApp/_tareas_rows.html',
                {'tareas': tareas_activas().exclude(diferencia=0)},
                request=request,
            )
            return JsonResponse({'status': 'ok', 'html': html})
        except Exception as e:
            logger.exception("Error al renderizar HTML: %s", e)
            return JsonResponse({'status': 'error', 'msg': 'Error al renderizar tareas.'})

    # Igual que lo que devuelve "Actualizar conteo": al recargar no reaparecen las
    # filas ya cuadradas (diferencia 0). Las aún no contadas (diferencia vacía) sí se muestran.
    tareas = tareas_activas().exclude(diferencia=0) if bodega else []
    return render(request, 'conteoApp/tareas_contador.html', {'tareas': tareas})


def _actualizar_conteo(request, tareas, hoy):
    """Guarda conteos/observaciones. Devuelve None si todo fue bien o un dict de error."""
    try:
        with transaction.atomic():
            tareas_dict = {t.id: t for t in tareas}
            if not tareas_dict:
                logger.warning("No hay tareas disponibles para actualizar.")
                return {'status': 'error', 'msg': 'Sin tareas disponibles.'}

            tarea_ids = set()
            for key, value in request.POST.items():
                prefijo, _, sufijo = key.partition('_')
                if prefijo not in ('conteo', 'observacion', 'consolidado') or not sufijo.isdigit():
                    continue
                tarea = tareas_dict.get(int(sufijo))
                if tarea is None:
                    continue
                if prefijo == 'conteo':
                    if value.strip().isdigit():
                        tarea.conteo = int(value)
                        tarea_ids.add(tarea.id)
                elif prefijo == 'observacion':
                    tarea.observacion = value.strip()
                    tarea_ids.add(tarea.id)
                else:  # consolidado
                    tarea.consolidado = 1
                    tarea_ids.add(tarea.id)

            if not tarea_ids:
                return {'status': 'error', 'msg': 'No se encontraron tareas para actualizar.'}

            # Inventario vigente para los productos (ya vienen cargados con select_related).
            inv06_data = {}
            try:
                productos = [tareas_dict[tid].producto for tid in tarea_ids]
                skus = {p.sku for p in productos}
                bods = {p.bod for p in productos}
                base = Inventario.objects.filter(sku__in=skus, bod__in=bods)
                fecha_corte_reciente = base.aggregate(m=Max('fecha_corte'))['m']
                for record in base.filter(fecha_corte=fecha_corte_reciente).values(
                        'sku', 'bod', 'lpt', 'inv_saldo', 'vlr_unit'):
                    inv06_data[(record['sku'], record['bod'], record['lpt'])] = record
            except Exception as e:
                logger.error(f"Error consultando inventario: {e}")
                inv06_data = {}

            tareas_a_actualizar = []
            for tarea_id in tarea_ids:
                tarea = tareas_dict[tarea_id]
                producto = tarea.producto
                registro = inv06_data.get((producto.sku, producto.bod, producto.lpt), {})
                saldo = registro.get('inv_saldo', 0) or 0
                vrunit = registro.get('vlr_unit', 0) or 0
                conteo = tarea.conteo or 0
                try:
                    if tarea.inventario is None:
                        tarea.inventario = saldo
                    tarea.diferencia = conteo - saldo
                    tarea.consolidado = round(vrunit * tarea.diferencia, 2)
                    tareas_a_actualizar.append(tarea)
                except Exception as e:
                    logger.error(f"Error calculando diferencia/consolidado para tarea ID {tarea_id}: {e}")

            if tareas_a_actualizar:
                Tarea.objects.bulk_update(
                    tareas_a_actualizar,
                    ['conteo', 'observacion', 'diferencia', 'consolidado', 'inventario'],
                    batch_size=500,
                )
    except Exception as e:
        logger.exception(f"Error al actualizar tareas: {e}")
        return {'status': 'error', 'msg': 'Error al actualizar tareas.'}

    _desactivar_completadas(request.user, hoy)
    return None


def _desactivar_completadas(usuario, hoy):
    """
    Desactiva las tareas de los SKU cuyo conteo total del usuario coincide con el
    saldo total del inventario. Misma regla que antes, con 4 consultas fijas en
    lugar de 3 + un UPDATE por cada SKU.
    """
    try:
        # Tareas del usuario hoy, directo desde Tarea
        filas = list(
            Tarea.objects.filter(usuario=usuario, fecha_asignacion=hoy)
            .values_list('id', 'conteo', 'producto__sku', 'producto__marca_nom', 'producto__sku_nom', 'producto__bod')
        )
        if not filas:
            return
        skus_asignados = {f[2] for f in filas}
        bod_list = {f[5] for f in filas}

        # Fecha de corte más reciente (igual que en asignar_tareas)
        base = Inventario.objects.filter(sku__in=skus_asignados, bod__in=bod_list)
        fecha_corte_reciente = base.aggregate(m=Max('fecha_corte'))['m']

        # Saldo real del inventario en esa fecha de corte
        productos_dict = {
            (p['sku'], p['marca_nom'], p['sku_nom']): p['total_saldo']
            for p in base.filter(fecha_corte=fecha_corte_reciente)
            .values('sku', 'marca_nom', 'sku_nom').annotate(total_saldo=Sum('inv_saldo'))
        }

        # Conteo total del usuario hoy agrupado por SKU (SUM ignora los vacíos, como en SQL)
        conteo_dict, ids_por_clave = {}, {}
        for tarea_id, conteo, sku, marca_nom, sku_nom, _ in filas:
            clave = (sku, marca_nom, sku_nom)
            ids_por_clave.setdefault(clave, []).append(tarea_id)
            actual = conteo_dict.get(clave)
            if conteo is None:
                conteo_dict.setdefault(clave, None)
            else:
                conteo_dict[clave] = conteo if actual is None else actual + conteo

        ids_desactivar = []
        for clave, total_saldo in productos_dict.items():
            total_conteo = conteo_dict.get(clave, 0)
            if total_saldo == total_conteo:
                ids_desactivar.extend(ids_por_clave.get(clave, []))

        if ids_desactivar:
            Tarea.objects.filter(id__in=ids_desactivar).update(activo=False)
    except Exception as e:
        logger.error(f"Error al desactivar tareas con conteo igual a inventario: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Otras vistas
# ─────────────────────────────────────────────────────────────────────────────
@login_required
def toggle_verificado(request):
    if request.method == "POST":
        tarea_id = request.POST.get("tarea_id", "")
        if not str(tarea_id).isdigit():
            return JsonResponse({"status": "error", "message": "Tarea no encontrada"}, status=404)
        try:
            tarea = Tarea.objects.only('id', 'verificado').get(id=tarea_id)
        except Tarea.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Tarea no encontrada"}, status=404)
        tarea.verificado = not tarea.verificado
        # update_fields: no pisa el conteo que el contador pueda estar guardando a la vez.
        tarea.save(update_fields=['verificado'])
        return JsonResponse({"status": "ok", "verificado": tarea.verificado})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)


@permission_required('conteoApp.view_conteo', raise_exception=True)
def conteo(request):
    return render(request, 'conteoApp/conteo.html')


def error_permiso(request, exception):
    return render(request, 'error.html', status=403)


@login_required
def asignar_bodega_usuarios(request):
    if request.user.username not in USUARIOS_ADMIN:
        raise PermissionDenied("No tienes permiso para acceder a esta vista.")

    ciudad = _ciudad_usuario(request.user)

    if request.method == 'POST':
        es_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        if 'mover_usuarios' in request.POST:
            destino = request.POST.get('destino')  # '0101' o '0105'
            user_ids = _ids_validos(request.POST.getlist('usuarios'))

            if destino not in ('0101', BODEGA_CONTEO_EXTRA):
                if es_ajax:
                    return JsonResponse({'status': 'error', 'msg': 'Destino inválido.'}, status=400)
                messages.error(request, "Destino inválido.")
                return redirect('asignar_bodega_usuarios')

            actualizados = UserCity.objects.filter(
                user__id__in=user_ids,
                ciudad=ciudad
            ).update(bodega_asignada=destino)

            if es_ajax:
                return JsonResponse({'status': 'ok', 'actualizados': actualizados})
        return redirect('asignar_bodega_usuarios')

    usuarios_almacen = UserCity.objects.filter(
        ciudad=ciudad, bodega_asignada='0101', user__is_active=True
    ).exclude(user__username="admin").select_related('user').order_by('user__first_name', 'user__last_name')

    usuarios_bodega = UserCity.objects.filter(
        ciudad=ciudad, bodega_asignada=BODEGA_CONTEO_EXTRA, user__is_active=True
    ).exclude(user__username="admin").select_related('user').order_by('user__first_name', 'user__last_name')

    return render(request, 'conteoApp/asignar_bodega_usuarios.html', {
        'usuarios_almacen': usuarios_almacen,
        'usuarios_bodega': usuarios_bodega,
        'ciudad': ciudad,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Depuración de conteos antiguos (solo usuario "admin")
# ─────────────────────────────────────────────────────────────────────────────
TEXTO_CONFIRMACION = "ELIMINAR"


@login_required
def depurar_conteos(request):
    if not puede_depurar(request.user):
        raise PermissionDenied("No tienes permiso para acceder a esta vista.")

    if request.method == 'POST':
        meses = depuracion.parse_meses(request.POST.getlist('meses'))
        if not meses:
            messages.error(request, "Selecciona al menos un mes válido.")
            return redirect('depurar_conteos')
        if request.POST.get('confirmacion', '').strip().upper() != TEXTO_CONFIRMACION:
            messages.error(request, f'Para eliminar escribe "{TEXTO_CONFIRMACION}" en el campo de confirmación.')
            consulta = '&'.join(f"meses={m.strftime('%Y-%m')}" for m in meses)
            return redirect(f"{reverse('depurar_conteos')}?revisar=1&{consulta}")
        try:
            resultado = depuracion.ejecutar(meses)
        except Exception as e:
            logger.exception("Error al depurar conteos: %s", e)
            messages.error(request, "No se pudo eliminar. No se borró nada. Revisa los permisos de la base de datos sobre la tabla inventario.")
            return redirect('depurar_conteos')
        nombres = ', '.join(depuracion.nombre_mes(m) for m in meses)
        logger.warning("Depuración de conteos por %s: meses=%s tareas=%s inventario=%s",
                       request.user.username, nombres, resultado['tareas'], resultado['inventario'])
        miles = lambda n: f"{n:,}".replace(',', '.')
        messages.success(
            request,
            f"Se eliminaron {miles(resultado['tareas'])} tareas y {miles(resultado['inventario'])} filas de inventario ({nombres}).",
        )
        return redirect('depurar_conteos')

    rango, meses = depuracion.resumen_general()
    plan = None
    if 'revisar' in request.GET:
        seleccion = depuracion.parse_meses(request.GET.getlist('meses'))
        if not seleccion:
            messages.error(request, "Selecciona al menos un mes para revisar.")
            return redirect('depurar_conteos')
        plan = depuracion.planificar(seleccion)
        plan['nombres'] = [depuracion.nombre_mes(m) for m in seleccion]
        plan['claves'] = [m.strftime('%Y-%m') for m in seleccion]
        plan['inventario'] = plan['inventario_de_tareas'] + plan['inventario_sin_tareas']

    return render(request, 'conteoApp/depurar_conteos.html', {
        'rango': rango,
        'meses': meses,
        'plan': plan,
        'seleccionados': request.GET.getlist('meses'),
        'texto_confirmacion': TEXTO_CONFIRMACION,
    })


MAX_CORTES_MANUALES = 500  # más que esto se pide usar "Seleccionar todos" + filtros


def _seleccion_inventario(datos):
    """Lee la selección del formulario: 'todos' + filtros, o una lista de cortes."""
    return {
        'todos': datos.get('todos') == '1',
        'bod': datos.get('bod') or None,
        'hasta': depuracion.parse_fecha(datos.get('hasta')),
        'claves': datos.getlist('grupos')[:MAX_CORTES_MANUALES],
    }


def _url_inventario(bod=None, hasta=None, **extra):
    params = {k: v for k, v in {'bod': bod, 'hasta': hasta.isoformat() if hasta else None, **extra}.items() if v}
    url = reverse('depurar_inventario')
    return f"{url}?{urlencode(params, doseq=True)}" if params else url


@login_required
def depurar_inventario(request):
    """Inventario por corte y bodega; permite borrar filas que no están en la tabla de tareas."""
    if not puede_depurar(request.user):
        raise PermissionDenied("No tienes permiso para acceder a esta vista.")

    if request.method == 'POST':
        sel = _seleccion_inventario(request.POST)
        volver = _url_inventario(sel['bod'], sel['hasta'])
        if request.POST.get('confirmacion', '').strip().upper() != TEXTO_CONFIRMACION:
            messages.error(request, f'Para eliminar escribe "{TEXTO_CONFIRMACION}" en el campo de confirmación.')
            return redirect(volver)
        try:
            resultado = depuracion.ejecutar_inventario(sel)
        except Exception as e:
            logger.exception("Error al depurar inventario: %s", e)
            messages.error(request, "No se pudo eliminar. No se borró nada.")
            return redirect(volver)
        if not resultado['n_grupos']:
            messages.error(request, "Selecciona al menos un corte válido (el corte más reciente no se puede eliminar).")
            return redirect(volver)
        logger.warning("Depuración de inventario por %s: todos=%s bod=%s hasta=%s cortes=%s filas=%s",
                       request.user.username, sel['todos'], sel['bod'], sel['hasta'],
                       resultado['n_grupos'], resultado['inventario'])
        messages.success(request, f"Se eliminaron {resultado['inventario']:,} filas de inventario sin tareas.".replace(',', '.'))
        return redirect(volver)

    sel = _seleccion_inventario(request.GET)
    total, grupos = depuracion.resumen_inventario(sel['bod'], sel['hasta'])
    contexto = {
        'total': total,
        'grupos': grupos,
        'bodegas': depuracion.bodegas_inventario(),
        'bod_filtro': sel['bod'] or '',
        'hasta_filtro': sel['hasta'].isoformat() if sel['hasta'] else '',
        'texto_confirmacion': TEXTO_CONFIRMACION,
        'seleccionados': sel['claves'],
        'max_manual': MAX_CORTES_MANUALES,
    }

    # Revisión previa al borrado
    if 'revisar' in request.GET:
        plan = depuracion.planificar_inventario(sel)
        if not plan['n_grupos']:
            messages.error(request, "Selecciona al menos un corte válido (el corte más reciente no se puede eliminar).")
            return redirect(_url_inventario(sel['bod'], sel['hasta']))
        plan['todos'] = sel['todos']
        plan['claves'] = [] if sel['todos'] else sel['claves']
        contexto['plan'] = plan

    # Detalle de filas de un corte/bodega
    ver = request.GET.get('ver')
    grupo = depuracion.parse_grupo(ver) if ver else None
    if grupo:
        solo_sin = request.GET.get('solo_sin_tareas') == '1'
        pagina = Paginator(depuracion.filas_grupo(*grupo, solo_sin_tareas=solo_sin), 100).get_page(request.GET.get('page'))
        params = request.GET.copy()
        params.pop('page', None)
        contexto.update({
            'detalle': {'bod': grupo[0], 'corte': grupo[1], 'clave': ver, 'solo_sin_tareas': solo_sin},
            'pagina': pagina,
            'params_detalle': params.urlencode(),
            'base_detalle': _url_inventario(sel['bod'], sel['hasta']),
        })

    return render(request, 'conteoApp/depurar_inventario.html', contexto)
