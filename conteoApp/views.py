import datetime
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import permission_required, login_required
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import PermissionDenied
from .models import UserCity, Venta, Tarea, Inv06, User, Inventario
from django.contrib import messages
from django.db.models import Count
import pandas as pd
from django.http import HttpResponse, HttpResponseForbidden
import logging
from django.db import transaction
from django.db.models import Sum
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)
@login_required
# @permission_required('conteoApp.view_tarea', raise_exception=True)
def asignar_tareas(request):
    # Obtener la fecha actual
    hoy = datetime.datetime.now()
    # Verificar si es lunes (0 = Lunes, 6 = Domingo))
    if hoy.weekday() == 0:
        fecha_asignar = (hoy - datetime.timedelta(days=2)).strftime("%Y%m%d")  # Restar 2 días si es lunes
    else:
        fecha_asignar = (hoy - datetime.timedelta(days=1)).strftime("%Y%m%d")  # Restar 1 día normalmente
    # fecha_asignar =  '20251101'
    
    if request.user.username != "DBENITEZ" and request.user.username != "CHINCAPI" and request.user.username != "FDUQUE" and request.user.username != "LAMAYA" and request.user.username != "AGRAJALE"  and request.user.username != "admin":
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
            selected_user_ids = request.POST.getlist('usuarios')  # Obtiene una lista de IDs de los usuarios seleccionados
            selected_users = User.objects.filter(id__in=selected_user_ids)

            bodega = ''
           
            if ciudad == 'Tulua':
                bodega = '0101'
            elif ciudad == 'Buga':
                bodega = '0201'
            elif ciudad == 'Cartago':
                bodega = '0301'
            elif ciudad == 'Cali':
                bodega = '0401'
            
            # Filtrar productos disponibles con un valor numérico en 'mcnproduct' y 'mcnbodega' = 101
            productos = (Venta.objects.filter(
                sku__regex=r'^\d+$', 
                bod = bodega, 
                fecha=fecha_asignar).exclude(marca_nom__in = ['INSMEVET', 'JL INSTRUMENTAL', 'LHAURA', 'FEDEGAN']).distinct('sku', 'bod'))
            print(len(productos))

            sku_list = [producto.sku for producto in productos]
            bod_list = [producto.bod for producto in productos]
            productos_disponibles = []
            productos_disponibles = Inventario.objects.filter(
                sku__in=sku_list,
                bod__in=bod_list,
                inv_saldo__gt=0
            ).order_by('marca_nom') # Ordenar por nombre de laboratorio
            
            # Procesar la cantidad de productos disponibles o asignar tarea según sea necesario
            print(f"Cantidad de productos disponibles: {len(productos_disponibles)}")
            
            if productos_disponibles:
                # Convertir la consulta a una lista para facilitar el manejo posterior
                productos_disponibles = list(productos_disponibles)
            
            if not productos_disponibles:
                messages.error(request, "No hay productos disponibles para asignar.")
                return redirect('asignar_tareas')

            total_productos = len(productos_disponibles)
            # Verificar que hay suficientes productos para asignar
            if total_productos == 0 or len(selected_users) == 0:
                messages.error(request, "No hay productos disponibles o no se seleccionaron usuarios.")
                return redirect('asignar_tareas')

            # Calcular productos por usuario
            productos_por_usuario = total_productos // len(selected_users)
            productos_restantes = total_productos % len(selected_users)
            
            # Crear tareas para cada usuario
            tareas_a_crear = []
            producto_index = 0
            sum_item_last = 0
            with transaction.atomic():
                for usuario in selected_users:
                    # Determinar cuántos productos asignar a este usuario
                    cantidad_a_asignar = productos_por_usuario
                    if productos_restantes > 0:  # Repartir los productos sobrantes
                        cantidad_a_asignar += 1
                        productos_restantes -= 1
                    
                    # bloque de codigo para verificar si el ultimo producto asignado al usuario es igual al siguiente, de ser asi, aumentar la cantidad a asignar
                    sum_item_last += cantidad_a_asignar
                    item_last = productos_disponibles[sum_item_last-1].sku
                    bandera = True
                    sum_item_next = sum_item_last
                    while bandera:
                        # obtener el proximo item de los productos disponibles, si no hay o se desborda, no asignar
                        try:
                            item_next = productos_disponibles[sum_item_next].sku
                        except IndexError:
                            item_next = None
                            
                        if item_last == item_next:
                            cantidad_a_asignar += 1
                            sum_item_next += 1
                        else:
                            bandera = False
                    # print(f"Item last: {item_last}, Item next: {item_next}")
                    
                    # Asignar productos a este usuario
                    for _ in range(cantidad_a_asignar):
                        if producto_index < total_productos:
                            producto = productos_disponibles[producto_index]
                            # Verificar que el producto no ha sido asignado previamente en la fecha actual
                            if not Tarea.objects.filter(producto=producto, fecha_asignacion = datetime.date.today()).exists():
                                tareas_a_crear.append(Tarea(
                                    usuario=usuario,
                                    producto=producto,
                                    observacion='',
                                ))
                            producto_index += 1 
                Tarea.objects.bulk_create(tareas_a_crear)
            return redirect('asignar_tareas')
    
        if 'delete_task' in request.POST:
            usuarios_sede = User.objects.filter(usercity__ciudad=ciudad)
            fecha = datetime.date.today()
            Tarea.objects.filter(usuario__in=usuarios_sede, fecha_asignacion=fecha).delete()
            return redirect('asignar_tareas')
        if 'filter_users' in request.POST:
            selected_user_ids = request.POST.getlist('usuarios')  # Obtiene una lista de IDs de los usuarios seleccionados
            selected_users = User.objects.filter(id__in=selected_user_ids) # Obtener los objetos Usuario a partir de los IDs
            fecha_asignacion_filter = request.POST.get('fecha_asignacion') # obtener la fecha seleccionada
            
            # Guardar los datos en la sesión
            request.session['selected_user_ids'] = selected_user_ids
            request.session['fecha_asignacion'] = fecha_asignacion_filter
           
            # Verificar si se seleccionaron usuarios 
            if not selected_users:
                tareas = []
                cant_tareas_por_usuario = []
            else:
                # Filtrar las tareas por esos usuarios.
                tareas = Tarea.objects.filter(usuario__in=selected_user_ids, fecha_asignacion = fecha_asignacion_filter)
                
                # Si quieres agrupar y contar tareas por usuario:
                cant_tareas_por_usuario = (
                    Tarea.objects.filter(usuario__in=selected_users, fecha_asignacion = fecha_asignacion)
                    .values('usuario__username', 'usuario__first_name', 'usuario__last_name')
                    .annotate(total_tareas=Count('id'))
                )
            # return redirect('asignar_tareas')
        if 'view_user_tasks' in request.POST:
            # Mostrar las tareas de un usuario específico
            usuario_id = request.POST.get('usuario_id')  # Obtener el ID del usuario
            tareas = Tarea.objects.filter(usuario__id=usuario_id, fecha_asignacion=datetime.date.today(), usuario__usercity__ciudad=ciudad).exclude(diferencia=0)
            # guardar tareas en la session
            request.session['selected_user_ids'] = usuario_id
            request.session['fecha_asignacion'] = str(datetime.date.today())
            # return redirect('asignar_tareas')
        if 'view_all_user_tasks' in request.POST:
            fecha_tasks = datetime.date.today()
            # fecha_tasks = "2025-10-21"
            # usuario_id = request.POST.get('usuario_id')  # Obtener el ID del usuario
            tareas = Tarea.objects.filter(fecha_asignacion=fecha_tasks, activo=True, usuario__usercity__ciudad=ciudad).exclude(diferencia=0)
            # guardar tareas en la session
            request.session['selected_user_ids'] = list(tareas.values_list('usuario__id', flat=True).distinct())
            request.session['fecha_asignacion'] = str(fecha_tasks)
            mostrar_exportar_todo = False
        else:
            mostrar_exportar_todo = True

        if 'view_all_tasks' in request.POST:
            # Mostrar todas las tareas asignadas para hoy
            fecha_tasks = datetime.date.today()
            # fecha_tasks = "2025-10-21"
            tareas = Tarea.objects.filter(fecha_asignacion=fecha_tasks, usuario__usercity__ciudad=ciudad)
            # guardar un solo id de los usuarios que están en tareas obteniendo el numero, quitando el queryset
            usuario_id = list(tareas.values_list('usuario__id', flat=True).distinct())
            request.session['selected_user_ids'] = usuario_id
            request.session['fecha_asignacion'] = str(fecha_tasks)
            # return redirect('asignar_tareas')
        
        if 'ver_no_verificados' in request.POST:
            tareas = Tarea.objects.filter(fecha_asignacion=datetime.date.today(), usuario__usercity__ciudad=ciudad, verificado=False)
            
        if 'export_excel' in request.POST:
            # Recuperar los datos de la sesión
            selected_user_ids = request.session.get('selected_user_ids', [])
            fecha_asignacion = request.session.get('fecha_asignacion', None)
            
            if selected_user_ids and fecha_asignacion:
                selected_users = User.objects.filter(id__in=selected_user_ids)
                tareas = Tarea.objects.filter(usuario__in=selected_users, fecha_asignacion=fecha_asignacion)

                # Validar si hay tareas
                if not tareas.exists():
                    return redirect('asignar_tareas')
                
                # Crear un DataFrame con las tareas
                df = pd.DataFrame(list(tareas.values('usuario__first_name','usuario__last_name', 'producto__marca_nom', 'producto__sku','producto__sku_nom','producto__lpt', 'producto__inv_saldo', 'conteo', 'diferencia','producto__vlr_unit', 'consolidado', 'observacion', 'fecha_asignacion','verificado')))
                
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
                    'producto__inv_saldo': 'Inventario',
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
            if selected_user_ids and fecha_asignacion:
                selected_users = User.objects.filter(id__in=selected_user_ids)
                tareas = Tarea.objects.filter(usuario__in=selected_users, fecha_asignacion=fecha_asignacion, activo=True).exclude(diferencia=0)

                # Validar si hay tareas
                if not tareas.exists():
                    return redirect('asignar_tareas')
                
                # Crear un DataFrame con las tareas
                df = pd.DataFrame(list(tareas.values('usuario__first_name','usuario__last_name', 'producto__marca_nom', 'producto__sku','producto__sku_nom','producto__lpt', 'producto__inv_saldo', 'conteo', 'diferencia','producto__vlr_unit', 'consolidado', 'observacion', 'fecha_asignacion', 'verificado')))
                
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
                    'producto__inv_saldo': 'Inventario',
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
            
    # Limpiar usuarios seleccionados y mostrar tareas si `assigned=1`
    if 'assigned' in request.GET:
        tareas = Tarea.objects.filter(usuario__in=selected_users) if selected_users else None
        selected_users = None  # Limpiar seleccionados para evitar reasignación

    usuarios_con_tareas = (Tarea.objects.filter(fecha_asignacion = datetime.date.today(), usuario__usercity__ciudad=ciudad)
                           .values('usuario__id', 'usuario__username', 'usuario__first_name', 'usuario__last_name')
                           .annotate(total_tareas=Count('id'))) # retornar los usuarios que tienen tareas asignadas
    
    total_tareas_usuarios = Tarea.objects.filter(fecha_asignacion=datetime.date.today(), usuario__usercity__ciudad=ciudad).count()
    
    bodega = ''
    if ciudad == 'Tulua':
        bodega = '0101'
    elif ciudad == 'Buga':
        bodega = '0201'
    elif ciudad == 'Cartago':
        bodega = '0301'
    elif ciudad == 'Cali':
        bodega = '0401'

    # usuarios que se mostraran en el select de la vista
    usuarios = User.objects.exclude(username="admin").filter(usercity__ciudad=ciudad) # retornar todos los usuarios
    
    productos = list(Venta.objects.filter(sku__regex=r'^\d+$',bod = bodega,fecha=fecha_asignar).exclude(marca_nom__in = ['INSMEVET', 'JL INSTRUMENTAL', 'LHAURA', 'FEDEGAN']).distinct('sku', 'bod'))
    
    sku_list = [producto.sku for producto in productos]
    bod_list = [producto.bod for producto in productos]
    total_tareas_hoy = Inventario.objects.filter(
        sku__in=sku_list,
        bod__in=bod_list,
        inv_saldo__gt=0
    ).order_by('marca_nom')
    total_tareas_hoy = len(total_tareas_hoy)
    return render(request, 'conteoApp/asignar_tareas.html', {
        # 'form': form,
        'tareas': tareas,
        'selected_users': selected_users,
        'cant_tareas_por_usuario': cant_tareas_por_usuario,
        'usuarios_con_tareas': usuarios_con_tareas,
        'total_tareas_usuarios': total_tareas_usuarios,
        'total_tareas_hoy': total_tareas_hoy,
        'usuarios': usuarios,
        'mostrar_exportar_todo': mostrar_exportar_todo,
    })

@login_required
@permission_required('conteoApp.view_tarea', raise_exception=True)
def lista_tareas(request):
    # Obtener la fecha actual
    hoy = datetime.datetime.now()
    # Verificar si es lunes (0 = Lunes, 6 = Domingo))
    if hoy.weekday() == 0:
        fecha_asignar = (hoy - datetime.timedelta(days=2)).strftime("%Y%m%d")  # Restar 2 días si es lunes
    else:
        fecha_asignar = (hoy - datetime.timedelta(days=1)).strftime("%Y%m%d")  # Restar 1 día normalmente
    # fecha_asignar =  '20251101'
    fecha_especifica = datetime.date.today() 
    try:
        ciudad = request.user.usercity.ciudad
    except Exception:
        ciudad = None
    bodega = ''
           
    if ciudad == 'Tulua':
        bodega = '0101'
    elif ciudad == 'Buga':
        bodega = '0201'
    elif ciudad == 'Cartago':
        bodega = '0301'
    elif ciudad == 'Cali':
        bodega = '0401'
    # 🔹 Evitar consultas si no hay bodega asignada
    tareas = (
        Tarea.objects.filter(usuario=request.user, fecha_asignacion=fecha_especifica, activo=True)
        .order_by('producto__marca_nom')
    ) if bodega else []
    if request.method == 'POST':
        if 'update_tarea' in request.POST: 
            try:
                with transaction.atomic():
                    tarea_ids = set()
                    tareas_a_actualizar = []
                    inv06_data = {}

                    # Obtener todas las tareas de la BD en una sola consulta
                    # tareas_dict = Tarea.objects.in_bulk([tarea.id for tarea in tareas])
                    tareas_dict = {t.id: t for t in tareas}
                    
                    # 🔹 Validar que haya tareas cargadas
                    if not tareas_dict:
                        logger.warning("No hay tareas disponibles para actualizar.")
                        return JsonResponse({'status': 'error', 'msg': 'Sin tareas disponibles.'})
                    # Actualizar los valores de conteo y observación
                    for key, value in request.POST.items():
                        try:
                            if key.startswith('conteo_'):  # Identificar los campos de conteo
                                tarea_id = int(key.split('_')[1]) # Obtener el ID de la tarea a partir del nombre del campo (tarea_1, tarea_2, etc.)
                                if tarea_id in tareas_dict:
                                    tarea = tareas_dict[tarea_id]
                                    # Solo actualizar si el valor no está vacío y es un número entero válido
                                    if value.strip().isdigit():
                                        tarea.conteo = int(value)
                                        tarea_ids.add(tarea_id)
                                    else:
                                        # No asignar nada (omite el cambio)
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
                    
                    # 🔹 Consultar inventario relacionado
                    try:
                        productos_ids = {tareas_dict[tid].producto.id for tid in tarea_ids if tareas_dict[tid].producto}
                        inv_records = Inventario.objects.filter(
                            sku__in=[tareas_dict[tid].producto.sku for tid in tarea_ids],
                            bod__in=[tareas_dict[tid].producto.bod for tid in tarea_ids],
                            lpt__in=[tareas_dict[tid].producto.lpt for tid in tarea_ids]
                        ).values('sku', 'bod', 'lpt', 'inv_saldo', 'vlr_unit')
                        
                        # Convertir resultados en un diccionario para acceso rápido
                        for record in inv_records:
                            key = (record['sku'], record['bod'], record['lpt'])
                            inv06_data[key] = {'inv_saldo': record['inv_saldo'], 'vlr_unit': record['vlr_unit']}
                    except Exception as e:
                        logger.error(f"Error consultando inventario: {e}")
                        inv06_data = {}
                        
                    # Procesar las tareas para consolidar valores y aplicar cálculos
                    for tarea_id in tarea_ids:
                        tarea = tareas_dict[tarea_id]
                        producto = tarea.producto

                        key = (producto.sku, producto.bod, producto.lpt)
                        saldo = inv06_data.get(key, {}).get('inv_saldo', 0) or 0
                        vrunit = inv06_data.get(key, {}).get('vlr_unit', 0) or 0
                        conteo = tarea.conteo or 0
                        
                        try:
                            tarea.diferencia = conteo - saldo
                            tarea.consolidado = round(vrunit * tarea.diferencia, 2)
                            tareas_a_actualizar.append(tarea)
                        except Exception as e:
                            logger.error(f"Error calculando diferencia/consolidado para tarea ID {tarea_id}: {e}")
                        
                    # Guardar todos los cambios en una sola operación
                    if tareas_a_actualizar:
                        Tarea.objects.bulk_update(
                            tareas_a_actualizar, ['conteo', 'observacion', 'diferencia', 'consolidado']
                        )
                try:
                #-------------------------------------------------------------------------------
                    productos_filtrados = list(Venta.objects.filter(
                        sku__regex=r'^\d+$', 
                        bod = bodega, 
                        fecha=fecha_asignar).exclude(marca_nom__in = ['INSMEVET', 'JL INSTRUMENTAL', 'LHAURA', 'FEDEGAN']).distinct('sku', 'bod'))
                    sku_list = [producto.sku for producto in productos_filtrados]
                    bod_list = [producto.bod for producto in productos_filtrados]
                    productos_disponibles = Inventario.objects.filter(
                        sku__in=sku_list,
                        bod__in=bod_list
                    ).values('sku', 'marca_nom', 'sku_nom').annotate(total_saldo=Sum('inv_saldo'))
                    
                    # obtener el total del conteo de la tarea agrupando por marnombre, pronombre y mcnproduct 
                    conteo = (
                        Tarea.objects
                        .filter(usuario=request.user, fecha_asignacion=datetime.date.today())
                        .values('producto__sku', 'producto__marca_nom', 'producto__sku_nom')
                        .annotate(total_conteo=Sum('conteo'))
                    )
                    # Convertir los querysets a listas de diccionarios
                    productos_list = list(productos_disponibles)
                    conteo_list = list(conteo)
                    # print(productos_list)
                    # Crear diccionarios indexados por la clave compuesta
                    productos_dict = {
                        (p['sku'], p['marca_nom'], p['sku_nom']): p['total_saldo']
                        for p in productos_list
                    }
                    conteo_dict = {
                        (c['producto__sku'], c['producto__marca_nom'], c['producto__sku_nom']): c['total_conteo']
                        for c in conteo_list
                    }
                    for key, total_saldo in productos_dict.items():
                        total_conteo = conteo_dict.get(key, 0)  # Si no existe, se considera 0
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
                #----------------------------------------------------------------------------
                tareas = Tarea.objects.filter(usuario=request.user, fecha_asignacion=fecha_especifica, activo=True).exclude(diferencia=0).order_by('producto__marca_nom')
                
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    try:
                        # renderizamos sólo las filas
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
