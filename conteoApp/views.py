import datetime
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import permission_required, login_required
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import PermissionDenied
from .models import UserCity, Venta, Tarea, Inv06, User, Inventario
from django.contrib import messages
from django.db.models import Count, Max
import pandas as pd
from django.http import HttpResponse, HttpResponseForbidden
import logging
from django.db import transaction
from django.db.models import Sum
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

def get_fecha_asignar(bodega=None):
    """
    Busca la fecha de venta más reciente disponible en la BD,
    anterior a hoy, para la bodega indicada (opcional).
    """
    hoy = datetime.date.today()
    
    qs = Venta.objects.filter(
        fecha__lt=hoy.strftime("%Y%m%d")  # Fechas anteriores a hoy
    )
    
    if bodega:
        qs = qs.filter(bod=bodega)
    
    ultima_venta = qs.order_by('-fecha').values_list('fecha', flat=True).first()
    
    if ultima_venta:
        return ultima_venta  # Ya viene en formato YYYYMMDD desde la BD
    
    # Fallback: si no hay nada en BD, usar lógica anterior
    hoy_dt = datetime.datetime.now()
    if hoy_dt.weekday() == 0:
        return (hoy_dt - datetime.timedelta(days=2)).strftime("%Y%m%d")
    return (hoy_dt - datetime.timedelta(days=1)).strftime("%Y%m%d")

@login_required
# @permission_required('conteoApp.view_tarea', raise_exception=True)
def asignar_tareas(request):
    fecha_asignar = get_fecha_asignar()
    
    print(f"Fecha de asignación determinada: {fecha_asignar}")
    if request.user.username != "DBENITEZ" and request.user.username != "CHINCAPI" and request.user.username != "PROJAS" and request.user.username != "LAMAYA" and request.user.username != "AGRAJALE"  and request.user.username != "admin":
        raise PermissionDenied("No tienes permiso para acceder a esta vista.")
    
    tareas = None  # Inicializamos la variable de las tareas
    selected_users = None
    fecha_asignacion = None
    cant_tareas_por_usuario = []  # Lista para almacenar los usuarios y la cantidad de tareas asignadas
    usuarios_con_tareas = [] 
    mostrar_exportar_todo = True
    try:
        ciudad = request.user.usercity.ciudad
    except UserCity.DoesNotExist:
        ciudad = "No asignada"
    if request.method == 'POST':
        if 'assign_task' in request.POST:
            print(fecha_asignar)
            selected_user_ids = request.POST.getlist('usuarios')
            selected_users = User.objects.filter(id__in=selected_user_ids).select_related('usercity')

            BODEGA_ALMACEN_POR_CIUDAD = {
                'Tulua': '0101',
                'Buga': '0201',
                'Cartago': '0301',
                'Cali': '0401',
            }

            fechas_raw = request.POST.getlist('fechas_venta')
            fechas_asignar = [f.strip().replace('-', '') for f in fechas_raw if f.strip()]
            if not fechas_asignar:
                fechas_asignar = [fecha_asignar]

            print(f"Fechas para asignar: {fechas_asignar}")

            # Agrupar usuarios seleccionados según su bodega_asignada (almacen / 0105 / etc.)
            grupos_usuarios = {}
            for usuario in selected_users:
                try:
                    tipo_bodega_usuario = usuario.usercity.bodega_asignada
                except UserCity.DoesNotExist:
                    continue  # usuario sin bodega asignada, se ignora
                grupos_usuarios.setdefault(tipo_bodega_usuario, []).append(usuario)

            if not grupos_usuarios:
                messages.error(request, "Los usuarios seleccionados no tienen bodega asignada.")
                return redirect('asignar_tareas')

            tareas_a_crear = []

            with transaction.atomic():
                for tipo_bodega, usuarios_grupo in grupos_usuarios.items():
                    if tipo_bodega == 'almacen':
                        bodega = BODEGA_ALMACEN_POR_CIUDAD.get(ciudad, '')
                    else:
                        bodega = tipo_bodega  # ej. '0105'

                    if not bodega:
                        messages.error(request, f"Bodega no válida para el grupo '{tipo_bodega}'.")
                        continue

                    # Productos vendidos en esa bodega/fechas
                    productos = (Venta.objects.filter(
                        sku__regex=r'^\d+$',
                        bod=bodega,
                        fecha__in=fechas_asignar
                    ).exclude(marca_nom__in=['INSMEVET', 'JL INSTRUMENTAL', 'LHAURA', 'FEDEGAN']).distinct('sku', 'bod'))

                    sku_list = [producto.sku for producto in productos]
                    bod_list = [producto.bod for producto in productos]
                    fecha_corte_reciente = (
                        Inventario.objects
                        .filter(sku__in=sku_list, bod__in=bod_list)
                        .aggregate(Max('fecha_corte'))['fecha_corte__max']
                    )

                    productos_disponibles = list(
                        Inventario.objects.filter(
                            sku__in=sku_list,
                            bod__in=bod_list,
                            inv_saldo__gt=0,
                            fecha_corte=fecha_corte_reciente
                        ).order_by('marca_nom')
                    )

                    print(f"[{tipo_bodega}] Cantidad de productos disponibles: {len(productos_disponibles)}")

                    if not productos_disponibles:
                        messages.error(request, f"No hay productos disponibles para asignar en '{tipo_bodega}'.")
                        continue

                    total_productos = len(productos_disponibles)
                    if total_productos == 0 or len(usuarios_grupo) == 0:
                        continue

                    productos_por_usuario = total_productos // len(usuarios_grupo)
                    productos_restantes = total_productos % len(usuarios_grupo)

                    producto_index = 0
                    sum_item_last = 0
                    for usuario in usuarios_grupo:
                        cantidad_a_asignar = productos_por_usuario
                        if productos_restantes > 0:
                            cantidad_a_asignar += 1
                            productos_restantes -= 1

                        sum_item_last += cantidad_a_asignar
                        item_last = productos_disponibles[sum_item_last - 1].sku
                        bandera = True
                        sum_item_next = sum_item_last
                        while bandera:
                            try:
                                item_next = productos_disponibles[sum_item_next].sku
                            except IndexError:
                                item_next = None

                            if item_last == item_next:
                                cantidad_a_asignar += 1
                                sum_item_next += 1
                            else:
                                bandera = False

                        for _ in range(cantidad_a_asignar):
                            if producto_index < total_productos:
                                producto = productos_disponibles[producto_index]
                                if not Tarea.objects.filter(
                                    producto=producto,
                                    fecha_asignacion=datetime.date.today(),
                                    tipo_bodega=tipo_bodega
                                ).exists():
                                    tareas_a_crear.append(Tarea(
                                        usuario=usuario,
                                        producto=producto,
                                        observacion='',
                                        inventario=producto.inv_saldo,
                                        tipo_bodega=tipo_bodega
                                    ))
                                producto_index += 1

                Tarea.objects.bulk_create(tareas_a_crear)

            return redirect('asignar_tareas')
        if 'delete_task' in request.POST:
            tipo_bodega = request.POST.get('tipo_bodega', 'almacen')
            usuarios_sede = User.objects.filter(usercity__ciudad=ciudad)
            fecha = datetime.date.today()
            Tarea.objects.filter(usuario__in=usuarios_sede, fecha_asignacion=fecha, tipo_bodega = tipo_bodega).delete()
            return redirect('asignar_tareas')
        if 'filter_users' in request.POST:
            selected_user_ids = request.POST.getlist('usuarios')  # Obtiene una lista de IDs de los usuarios seleccionados
            selected_users = User.objects.filter(id__in=selected_user_ids) # Obtener los objetos Usuario a partir de los IDs
            fecha_asignacion_filter = request.POST.get('fecha_asignacion') # obtener la fecha seleccionada
            tipo_bodega_filter = request.POST.get('tipo_bodega', 'almacen')
            # Guardar los datos en la sesión
            request.session['tipo_bodega'] = tipo_bodega_filter
            request.session['selected_user_ids'] = selected_user_ids
            request.session['fecha_asignacion'] = fecha_asignacion_filter
           
            # Verificar si se seleccionaron usuarios 
            if not selected_users:
                tareas = []
                cant_tareas_por_usuario = []
            else:
                # Filtrar las tareas por esos usuarios.
                tareas = Tarea.objects.filter(usuario__in=selected_user_ids, fecha_asignacion = fecha_asignacion_filter, tipo_bodega=tipo_bodega_filter)
                
                # Si quieres agrupar y contar tareas por usuario:
                cant_tareas_por_usuario = (
                    Tarea.objects.filter(usuario__in=selected_users, fecha_asignacion = fecha_asignacion, tipo_bodega=tipo_bodega_filter)
                    .values('usuario__username', 'usuario__first_name', 'usuario__last_name')
                    .annotate(total_tareas=Count('id'))
                )
            # return redirect('asignar_tareas')
        if 'view_user_tasks' in request.POST:
            # Mostrar las tareas de un usuario específico
            usuario_id = request.POST.get('usuario_id')  # Obtener el ID del usuario
            tipo_bodega_filter = request.POST.get('tipo_bodega', 'almacen')
            request.session['tipo_bodega'] = tipo_bodega_filter
            tareas = Tarea.objects.filter(usuario__id=usuario_id, fecha_asignacion=datetime.date.today(), usuario__usercity__ciudad=ciudad, tipo_bodega=tipo_bodega_filter).exclude(diferencia=0)
            # guardar tareas en la session
            request.session['selected_user_ids'] = usuario_id
            request.session['fecha_asignacion'] = str(datetime.date.today())
            # return redirect('asignar_tareas')
        if 'view_all_user_tasks' in request.POST:
            fecha_tasks = datetime.date.today()
            tipo_bodega_filter = request.POST.get('tipo_bodega', 'almacen')
            request.session['tipo_bodega'] = tipo_bodega_filter
            # usuario_id = request.POST.get('usuario_id')  # Obtener el ID del usuario
            tareas = Tarea.objects.filter(fecha_asignacion=fecha_tasks, activo=True, usuario__usercity__ciudad=ciudad, tipo_bodega=tipo_bodega_filter).exclude(diferencia=0)
            # guardar tareas en la session
            request.session['selected_user_ids'] = list(tareas.values_list('usuario__id', flat=True).distinct())
            request.session['fecha_asignacion'] = str(fecha_tasks)
            mostrar_exportar_todo = False
        else:
            mostrar_exportar_todo = True

        if 'view_all_tasks' in request.POST:
            # Mostrar todas las tareas asignadas para hoy
            fecha_tasks = datetime.date.today()
            tipo_bodega_filter = request.POST.get('tipo_bodega', 'almacen')
            request.session['tipo_bodega'] = tipo_bodega_filter
            tareas = Tarea.objects.filter(fecha_asignacion=fecha_tasks, usuario__usercity__ciudad=ciudad, tipo_bodega=tipo_bodega_filter)
            # guardar un solo id de los usuarios que están en tareas obteniendo el numero, quitando el queryset
            usuario_id = list(tareas.values_list('usuario__id', flat=True).distinct())
            request.session['selected_user_ids'] = usuario_id
            request.session['fecha_asignacion'] = str(fecha_tasks)
            # return redirect('asignar_tareas')
        
        if 'ver_no_verificados' in request.POST:
            tipo_bodega_filter = request.POST.get('tipo_bodega', 'almacen')
            request.session['tipo_bodega'] = tipo_bodega_filter
            tareas = Tarea.objects.filter(fecha_asignacion=datetime.date.today(), usuario__usercity__ciudad=ciudad, verificado=False, tipo_bodega=tipo_bodega_filter)
            
        if 'export_excel' in request.POST:
            # Recuperar los datos de la sesión
            selected_user_ids = request.session.get('selected_user_ids', [])
            fecha_asignacion = request.session.get('fecha_asignacion', None)
            tipo_bodega_filter = request.POST.get('tipo_bodega', 'almacen')
            request.session['tipo_bodega'] = tipo_bodega_filter
            
            if selected_user_ids and fecha_asignacion:
                selected_users = User.objects.filter(id__in=selected_user_ids)
                tareas = Tarea.objects.filter(usuario__in=selected_users, fecha_asignacion=fecha_asignacion, tipo_bodega=tipo_bodega_filter)

                # Validar si hay tareas
                if not tareas.exists():
                    return redirect('asignar_tareas')
                
                # Crear un DataFrame con las tareas
                df = pd.DataFrame(list(tareas.values('usuario__first_name','usuario__last_name', 'producto__marca_nom', 'producto__sku','producto__sku_nom','producto__lpt', 'inventario', 'conteo', 'diferencia','producto__vlr_unit', 'consolidado', 'observacion', 'fecha_asignacion','verificado')))
                
                # Validar si el DataFrame quedó vacío
                if df.empty:
                    return redirect('asignar_tareas')
                
                # Cambiar True/False a 'OK' o ''
                df['verificado'] = df['verificado'].apply(lambda x: 'OK' if x else '')

                # Renombrar las columnas con nombres personalizados
                df.rename(columns={
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
                    'verificado': 'Verificado'
                }, inplace=True)
                response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = 'attachment; filename=tareas.xlsx'
                df.to_excel(response, index=False)
                # Limpiar la sesión
                selected_user_ids = request.session.pop('selected_user_ids', [])
                fecha_asignacion = request.session.pop('fecha_asignacion', None)
                return response
            # return redirect('asignar_tareas')
        
        if 'export_excel_diferencias' in request.POST:
            # Recuperar los datos de la sesión
            selected_user_ids = request.session.get('selected_user_ids', [])
            fecha_asignacion = request.session.get('fecha_asignacion', None)
            tipo_bodega_filter = request.POST.get('tipo_bodega', 'almacen')
            request.session['tipo_bodega'] = tipo_bodega_filter
            if selected_user_ids and fecha_asignacion:
                selected_users = User.objects.filter(id__in=selected_user_ids)
                tareas = Tarea.objects.filter(usuario__in=selected_users, fecha_asignacion=fecha_asignacion, activo=True, tipo_bodega=tipo_bodega_filter).exclude(diferencia=0)

                # Validar si hay tareas
                if not tareas.exists():
                    return redirect('asignar_tareas')
                
                # Crear un DataFrame con las tareas
                df = pd.DataFrame(list(tareas.values('usuario__first_name','usuario__last_name', 'producto__marca_nom', 'producto__sku','producto__sku_nom','producto__lpt', 'inventario', 'conteo', 'diferencia','producto__vlr_unit', 'consolidado', 'observacion', 'fecha_asignacion', 'verificado')))
                
                # Validar si el DataFrame quedó vacío
                if df.empty:
                    return redirect('asignar_tareas')
                
                # Cambiar True/False a 'OK' o ''
                df['verificado'] = df['verificado'].apply(lambda x: 'OK' if x else '')
                
                # Renombrar las columnas con nombres personalizados
                df.rename(columns={
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
                    'verificado': 'Verificado'
                }, inplace=True)
                response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = 'attachment; filename=diferencias.xlsx'
                df.to_excel(response, index=False)
                # Limpiar la sesión
                selected_user_ids = request.session.pop('selected_user_ids', [])
                fecha_asignacion = request.session.pop('fecha_asignacion', None)
                return response
            # return redirect('asignar_tareas')
        
        if 'filter_all_users' in request.POST:
            # Obtener todos los usuarios de la sede
            usuarios_sede = User.objects.filter(usercity__ciudad=ciudad, is_active=True).exclude(username="admin")
            selected_users = usuarios_sede
            tipo_bodega_filter = request.POST.get('tipo_bodega', 'almacen')
            request.session['tipo_bodega'] = tipo_bodega_filter
            
            # Obtener la fecha seleccionada
            fecha_asignacion_filter = request.POST.get('fecha_asignacion')
            
            # Validar que se haya seleccionado una fecha
            if not fecha_asignacion_filter:
                messages.error(request, "Por favor selecciona una fecha.")
                return redirect('asignar_tareas')
            
            # Guardar los datos en la sesión
            request.session['selected_user_ids'] = list(usuarios_sede.values_list('id', flat=True))
            request.session['fecha_asignacion'] = fecha_asignacion_filter
            
            # Filtrar las tareas por todos los usuarios de la sede en esa fecha
            tareas = Tarea.objects.filter(
                usuario__in=usuarios_sede, 
                fecha_asignacion=fecha_asignacion_filter,
                tipo_bodega=tipo_bodega_filter
            )
            
            # Si quieres agrupar y contar tareas por usuario:
            cant_tareas_por_usuario = (
                Tarea.objects.filter(usuario__in=selected_users, fecha_asignacion=fecha_asignacion_filter, tipo_bodega=tipo_bodega_filter)
                .values('usuario__username', 'usuario__first_name', 'usuario__last_name')
                .annotate(total_tareas=Count('id'))
            )
    # Limpiar usuarios seleccionados y mostrar tareas si `assigned=1`
    if 'assigned' in request.GET:
        tareas = Tarea.objects.filter(usuario__in=selected_users) if selected_users else None
        selected_users = None  # Limpiar seleccionados para evitar reasignación
    usuarios_con_tareas_almacen = (
        Tarea.objects.filter(fecha_asignacion=datetime.date.today(), usuario__usercity__ciudad=ciudad, tipo_bodega='almacen')
        .values('usuario__id', 'usuario__username', 'usuario__first_name', 'usuario__last_name')
        .annotate(total_tareas=Count('id'))
    )
    usuarios_con_tareas_bodega = (
        Tarea.objects.filter(fecha_asignacion=datetime.date.today(), usuario__usercity__ciudad=ciudad, tipo_bodega='0105')
        .values('usuario__id', 'usuario__username', 'usuario__first_name', 'usuario__last_name')
        .annotate(total_tareas=Count('id'))
    )

    total_tareas_almacen = Tarea.objects.filter(fecha_asignacion=datetime.date.today(), usuario__usercity__ciudad=ciudad, tipo_bodega='almacen').count()
    total_tareas_bodega = Tarea.objects.filter(fecha_asignacion=datetime.date.today(), usuario__usercity__ciudad=ciudad, tipo_bodega='0105').count()
    BODEGA_ALMACEN_POR_CIUDAD = {
        'Tulua': '0101',
        'Buga': '0201',
        'Cartago': '0301',
        'Cali': '0401',
    }
    bodega = BODEGA_ALMACEN_POR_CIUDAD.get(ciudad, '')
    # usuarios que se mostraran en el select de la vista
    usuarios = User.objects.exclude(username="admin").filter(usercity__ciudad=ciudad, is_active=True) # retornar todos los usuarios
    
    productos = list(Venta.objects.filter(sku__regex=r'^\d+$',bod = bodega,fecha=fecha_asignar).exclude(marca_nom__in = ['INSMEVET', 'JL INSTRUMENTAL', 'LHAURA', 'FEDEGAN']).distinct('sku', 'bod'))
    
    sku_list = [producto.sku for producto in productos]
    bod_list = [producto.bod for producto in productos]
    fecha_corte_reciente = (
        Inventario.objects
        .filter(sku__in=sku_list, bod__in=bod_list)
        .aggregate(Max('fecha_corte'))['fecha_corte__max']
    )
    total_tareas_hoy = Inventario.objects.filter(
        sku__in=sku_list,
        bod__in=bod_list,
        inv_saldo__gt=0,
        fecha_corte=fecha_corte_reciente
    ).order_by('marca_nom')
    total_tareas_hoy = len(total_tareas_hoy)
    # formatear la fecha para mostrar en la vista
    fecha_asignar_formateada = datetime.datetime.strptime(fecha_asignar, "%Y%m%d").strftime("%Y-%m-%d")
    
    BODEGA_CONTEO_EXTRA = '0105'

    def calcular_total_disponibles(bod):
        productos = list(Venta.objects.filter(
            sku__regex=r'^\d+$', bod=bod, fecha=fecha_asignar
        ).exclude(marca_nom__in=['INSMEVET', 'JL INSTRUMENTAL', 'LHAURA', 'FEDEGAN']).distinct('sku', 'bod'))

        sku_list = [p.sku for p in productos]
        bod_list = [p.bod for p in productos]
        fecha_corte_reciente = (
            Inventario.objects.filter(sku__in=sku_list, bod__in=bod_list)
            .aggregate(Max('fecha_corte'))['fecha_corte__max']
        )
        return Inventario.objects.filter(
            sku__in=sku_list, bod__in=bod_list, inv_saldo__gt=0, fecha_corte=fecha_corte_reciente
        ).count()

    total_tareas_hoy_almacen = calcular_total_disponibles(bodega) if bodega else 0
    total_tareas_hoy_bodega = calcular_total_disponibles(BODEGA_CONTEO_EXTRA)
    return render(request, 'conteoApp/asignar_tareas.html', {
        # 'form': form,
        'tareas': tareas,
        'cant_tareas_por_usuario': cant_tareas_por_usuario,
        'usuarios_con_tareas_almacen': usuarios_con_tareas_almacen,
        'usuarios_con_tareas_bodega': usuarios_con_tareas_bodega,
        'total_tareas_almacen': total_tareas_almacen,
        'total_tareas_bodega': total_tareas_bodega,
        'total_tareas_hoy_almacen': total_tareas_hoy_almacen,
        'total_tareas_hoy_bodega': total_tareas_hoy_bodega,
        'usuarios': usuarios,
        'mostrar_exportar_todo': mostrar_exportar_todo,
        'fecha_asignar': fecha_asignar_formateada,
        'ciudad': ciudad,
    })

@login_required
@permission_required('conteoApp.view_tarea', raise_exception=True)
def lista_tareas(request):
    try:
        ciudad = request.user.usercity.ciudad
    except Exception:
        ciudad = None

    BODEGA_ALMACEN_POR_CIUDAD = {
        'Tulua': '0101',
        'Buga': '0201',
        'Cartago': '0301',
        'Cali': '0401',
    }
    bodega = BODEGA_ALMACEN_POR_CIUDAD.get(ciudad, '')  # Obtener la bodega según la ciudad, o '' si no se encuentra

    fecha_especifica = datetime.date.today()

    # Evitar consultas si no hay bodega asignada
    tareas = (
        Tarea.objects.filter(usuario=request.user, fecha_asignacion=fecha_especifica, activo=True)
        .order_by('tipo_bodega', 'producto__marca_nom')
    ) if bodega else []

    if request.method == 'POST':
        if 'update_tarea' in request.POST:
            try:
                with transaction.atomic():
                    tarea_ids = set()
                    tareas_a_actualizar = []
                    inv06_data = {}

                    tareas_dict = {t.id: t for t in tareas}

                    if not tareas_dict:
                        logger.warning("No hay tareas disponibles para actualizar.")
                        return JsonResponse({'status': 'error', 'msg': 'Sin tareas disponibles.'})

                    for key, value in request.POST.items():
                        try:
                            if key.startswith('conteo_'):
                                tarea_id = int(key.split('_')[1])
                                if tarea_id in tareas_dict:
                                    tarea = tareas_dict[tarea_id]
                                    if value.strip().isdigit():
                                        tarea.conteo = int(value)
                                        tarea_ids.add(tarea_id)
                                    else:
                                        continue

                            elif key.startswith('observacion_'):
                                tarea_id = int(key.split('_')[1])
                                if tarea_id in tareas_dict:
                                    tarea = tareas_dict[tarea_id]
                                    tarea.observacion = value.strip()
                                    tarea_ids.add(tarea_id)

                            elif key.startswith('consolidado_'):
                                tarea_id = int(key.split('_')[1])
                                if tarea_id in tareas_dict:
                                    tarea = tareas_dict[tarea_id]
                                    tarea.consolidado = 1
                                    tarea_ids.add(tarea_id)
                        except Exception as e:
                            logger.error(f"Error procesando campo {key}: {e}")
                            continue

                    if not tarea_ids:
                        return JsonResponse({'status': 'error', 'msg': 'No se encontraron tareas para actualizar.'})

                    try:
                        # 1. Obtener la fecha de corte más reciente para los SKUs/bodegas relevantes
                        skus = [tareas_dict[tid].producto.sku for tid in tarea_ids]
                        bods = [tareas_dict[tid].producto.bod for tid in tarea_ids]

                        fecha_corte_reciente = (
                            Inventario.objects
                            .filter(sku__in=skus, bod__in=bods)
                            .aggregate(Max('fecha_corte'))['fecha_corte__max']
                        )
                        # 2. Consultar inventario solo en esa fecha de corte
                        inv_records = Inventario.objects.filter(
                            sku__in=skus,
                            bod__in=bods,
                            fecha_corte=fecha_corte_reciente
                        ).values('sku', 'bod', 'lpt', 'inv_saldo', 'vlr_unit')

                        for record in inv_records:
                            key = (record['sku'], record['bod'], record['lpt'])
                            inv06_data[key] = {
                                'inv_saldo': record['inv_saldo'],
                                'vlr_unit': record['vlr_unit']
                            }
                    except Exception as e:
                        logger.error(f"Error consultando inventario: {e}")
                        inv06_data = {}

                    for tarea_id in tarea_ids:
                        tarea = tareas_dict[tarea_id]
                        producto = tarea.producto
                        key = (producto.sku, producto.bod, producto.lpt)
                        saldo = inv06_data.get(key, {}).get('inv_saldo', 0) or 0
                        vrunit = inv06_data.get(key, {}).get('vlr_unit', 0) or 0
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
                            tareas_a_actualizar, ['conteo', 'observacion', 'diferencia', 'consolidado', 'inventario']
                        )

                # ── Bloque de desactivación de tareas completadas ──────────────
                try:
                    # SKUs asignados al usuario hoy, directo desde Tarea
                    skus_asignados = list(
                        Tarea.objects
                        .filter(usuario=request.user, fecha_asignacion=datetime.date.today())
                        .values_list('producto__sku', flat=True)
                        .distinct()
                    )
                    bod_list = list(
                        Tarea.objects
                        .filter(usuario=request.user, fecha_asignacion=datetime.date.today())
                        .values_list('producto__bod', flat=True)
                        .distinct()
                    )

                    # Fecha de corte más reciente (igual que en asignar_tareas)
                    fecha_corte_reciente = (
                        Inventario.objects
                        .filter(sku__in=skus_asignados, bod__in=bod_list)
                        .aggregate(Max('fecha_corte'))['fecha_corte__max']
                    )

                    # Saldo real del inventario en esa fecha de corte
                    productos_disponibles = Inventario.objects.filter(
                        sku__in=skus_asignados,
                        bod__in=bod_list,
                        fecha_corte=fecha_corte_reciente
                    ).values('sku', 'marca_nom', 'sku_nom').annotate(total_saldo=Sum('inv_saldo'))

                    # Conteo total del usuario hoy agrupado por SKU
                    conteo_qs = (
                        Tarea.objects
                        .filter(usuario=request.user, fecha_asignacion=datetime.date.today())
                        .values('producto__sku', 'producto__marca_nom', 'producto__sku_nom')
                        .annotate(total_conteo=Sum('conteo'))
                    )

                    productos_dict = {
                        (p['sku'], p['marca_nom'], p['sku_nom']): p['total_saldo']
                        for p in productos_disponibles
                    }
                    conteo_dict = {
                        (c['producto__sku'], c['producto__marca_nom'], c['producto__sku_nom']): c['total_conteo']
                        for c in conteo_qs
                    }

                    for key, total_saldo in productos_dict.items():
                        total_conteo = conteo_dict.get(key, 0)
                        if total_saldo == total_conteo:
                            Tarea.objects.filter(
                                producto__sku=key[0],
                                producto__marca_nom=key[1],
                                producto__sku_nom=key[2],
                                fecha_asignacion=datetime.date.today(),
                                usuario=request.user
                            ).update(activo=False)

                except Exception as e:
                    logger.error(f"Error al desactivar tareas con conteo igual a inventario: {e}")
                # ──────────────────────────────────────────────────────────────

                tareas = (
                    Tarea.objects
                    .filter(usuario=request.user, fecha_asignacion=fecha_especifica, activo=True)
                    .exclude(diferencia=0)
                    .order_by('tipo_bodega', 'producto__marca_nom')
                )

                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    try:
                        html = render_to_string(
                            'conteoApp/_tareas_rows.html',
                            {'tareas': tareas},
                            request=request
                        )
                        return JsonResponse({'status': 'ok', 'html': html})
                    except Exception as e:
                        logger.error(f"Error al renderizar HTML: {e}")
                        return JsonResponse({'status': 'error', 'msg': 'Error al renderizar tareas.'})

            except Exception as e:
                logger.error(f"Error al actualizar tareas: {e}")
                return JsonResponse({'status': 'error', 'msg': 'Error al actualizar tareas.'})

    return render(request, 'conteoApp/tareas_contador.html', {'tareas': tareas})

from django.http import JsonResponse
@csrf_exempt
def toggle_verificado(request):
    if request.method == "POST":
        tarea_id = request.POST.get("tarea_id")
        try:
            tarea = Tarea.objects.get(id=tarea_id)
            tarea.verificado = not tarea.verificado
            tarea.save()
            return JsonResponse({"status": "ok", "verificado": tarea.verificado})
        except Tarea.DoesNotExist:
           return JsonResponse({"status": "error", "message": "Tarea no encontrada"}, status=404)
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

@permission_required('conteoApp.view_conteo', raise_exception=True)
def conteo(request):
    return render(request, 'conteoApp/conteo.html')

def error_permiso(request, exception):
    return render(request, 'error.html', status=403)

@login_required
def asignar_bodega_usuarios(request):
    if request.user.username not in ("DBENITEZ","CHINCAPI","PROJAS","LAMAYA","AGRAJALE","admin"):
        raise PermissionDenied("No tienes permiso para acceder a esta vista.")

    try:
        ciudad = request.user.usercity.ciudad
    except UserCity.DoesNotExist:
        ciudad = "No asignada"

    if request.method == 'POST':
        if 'mover_usuarios' in request.POST:
            destino = request.POST.get('destino')  # 'almacen' o '0105'
            user_ids = request.POST.getlist('usuarios')

            if destino not in ('almacen', '0105'):
                messages.error(request, "Destino inválido.")
                return redirect('asignar_bodega_usuarios')

            UserCity.objects.filter(
                user__id__in=user_ids,
                ciudad=ciudad
            ).update(bodega_asignada=destino)

            return redirect('asignar_bodega_usuarios')

    usuarios_almacen = UserCity.objects.filter(
        ciudad=ciudad, bodega_asignada='almacen', user__is_active=True
    ).exclude(user__username="admin").select_related('user')

    usuarios_bodega = UserCity.objects.filter(
        ciudad=ciudad, bodega_asignada='0105', user__is_active=True
    ).exclude(user__username="admin").select_related('user')

    return render(request, 'conteoApp/asignar_bodega_usuarios.html', {
        'usuarios_almacen': usuarios_almacen,
        'usuarios_bodega': usuarios_bodega,
        'ciudad': ciudad,
    })