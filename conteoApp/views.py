import datetime
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import permission_required, login_required
from django.core.exceptions import PermissionDenied
from .models import Venta, Tarea, Inv06, User
from pronosticosWebApp.models import Demanda
from django.contrib import messages
from django.db.models import Count
import pandas as pd
from django.http import HttpResponse
import logging
from django.db import transaction

logger = logging.getLogger(__name__)
    
@login_required
# @permission_required('conteoApp.view_tarea', raise_exception=True)
def asignar_tareas(request):
    tareas = None  # Inicializamos la variable de las tareas
    selected_users = None
    fecha_asignacion = None
    cant_tareas_por_usuario = []  # Lista para almacenar los usuarios y la cantidad de tareas asignadas
    usuarios_con_tareas = []  

    if request.method == 'POST':
        if 'assign_task' in request.POST:
            selected_user_ids = request.POST.getlist('usuarios')  # Obtiene una lista de IDs de los usuarios seleccionados
            selected_users = User.objects.filter(id__in=selected_user_ids)

            # Filtrar productos disponibles con un valor numérico en 'mcnproduct' y 'mcnbodega' = 101
            productos = list(Venta.objects.filter(mcnproduct__regex=r'^\d+$', mcnbodega = 101).distinct('mcnproduct', 'mcnbodega'))
            
            # Convertir a listas y validar
            mcnproduct_list = []
            mcnbodega_list = []
            print(len(productos))
            for producto in productos:
                try:
                    # Convertir mcnproduct y mcnbodega a enteros
                    mcnproduct_list.append(int(producto.mcnproduct))
                    mcnbodega_list.append(int(producto.mcnbodega))
                except (ValueError, TypeError):
                    # Si no se puede convertir, continuar sin agregar el producto
                    continue

            # Buscar en la tabla Inv06 los productos que cumplen con las condiciones y tienen saldo mayor a 0
            if mcnproduct_list and mcnbodega_list:
                productos_disponibles = Inv06.objects.filter(
                    mcnproduct__in=mcnproduct_list,
                    mcnbodega__in=mcnbodega_list,
                    saldo__gt=0
                ).order_by('marnombre') # Ordenar por nombre de laboratorio

                # Contar los productos que cumplen la condición
                cantidad_productos = productos_disponibles.count()
            else:
                cantidad_productos = 0

            # Procesar la cantidad de productos disponibles o asignar tarea según sea necesario
            print(f"Cantidad de productos disponibles: {cantidad_productos}")
            
            # guardad los productos disponibles en un excel
            # import pandas as pd
            # df = pd.DataFrame(list(productos_disponibles.values()))
            # df.to_excel('productos_disponibles.xlsx', index=False)
            
            # Convertir la consulta a una lista para facilitar el manejo posterior
            productos_disponibles = list(productos_disponibles)
            
            total_productos = len(productos_disponibles)
            # Verificar que hay suficientes productos para asignar
            if total_productos == 0 or len(selected_users) == 0:
                messages.error(request, "No hay productos disponibles o no se seleccionaron usuarios.")
                return redirect('asignar_tareas')

            # Calcular productos por usuario
            productos_por_usuario = total_productos // len(selected_users)
            productos_restantes = total_productos % len(selected_users)

            # Barajar los productos para distribuir aleatoriamente
            # random.shuffle(productos_disponibles)
            
            # Crear tareas para cada usuario
            producto_index = 0
            for usuario in selected_users:
                # Determinar cuántos productos asignar a este usuario
                cantidad_a_asignar = productos_por_usuario
                if productos_restantes > 0:  # Repartir los productos sobrantes
                    cantidad_a_asignar += 1
                    productos_restantes -= 1

                # Asignar productos a este usuario
                for _ in range(cantidad_a_asignar):
                    if producto_index < total_productos:
                        producto = productos_disponibles[producto_index]

                        # Verificar que el producto no ha sido asignado previamente
                        if not Tarea.objects.filter(producto=producto).exists():
                            Tarea.objects.create(
                                usuario=usuario,
                                producto=producto,
                                conteo=0,
                                observacion='',
                                diferencia=0
                            )
                        producto_index += 1 
            return redirect('asignar_tareas')
    
        if 'delete_task' in request.POST:
            selected_user_ids = request.POST.getlist('usuarios')  # Obtiene una lista de IDs de los usuarios seleccionados
            selected_users = User.objects.filter(id__in=selected_user_ids)
            fecha = datetime.date.today()
            tareas = Tarea.objects.filter(usuario__in=selected_users, fecha_asignacion=fecha)
            tareas.delete()
            return redirect('asignar_tareas')
        if 'filter_users' in request.POST:
            selected_user_ids = request.POST.getlist('usuarios')  # Obtiene una lista de IDs de los usuarios seleccionados
            selected_users = User.objects.filter(id__in=selected_user_ids) # Obtener los objetos Usuario a partir de los IDs
            fecha_asignacion = request.POST.get('fecha_asignacion') # obtener la fecha seleccionada
            
            # Guardar los datos en la sesión
            request.session['selected_user_ids'] = selected_user_ids
            request.session['fecha_asignacion'] = fecha_asignacion
           
            # Verificar si se seleccionaron usuarios 
            if not selected_users:
                tareas = []
                cant_tareas_por_usuario = []
            else:
                # Filtrar las tareas por esos usuarios.
                tareas = Tarea.objects.filter(usuario__in=selected_user_ids, fecha_asignacion = fecha_asignacion)
                
                # Si quieres agrupar y contar tareas por usuario:
                cant_tareas_por_usuario = (
                    Tarea.objects.filter(usuario__in=selected_users, fecha_asignacion = fecha_asignacion)
                    .values('usuario__username')
                    .annotate(total_tareas=Count('id'))
                )
            return redirect('asignar_tareas')
        if 'view_user_tasks' in request.POST:
            # Mostrar las tareas de un usuario específico
            usuario_id = request.POST.get('usuario_id')  # Obtener el ID del usuario
            tareas = Tarea.objects.filter(usuario__id=usuario_id, fecha_asignacion=datetime.date.today())
            # guardar tareas en la session
            request.session['selected_user_ids'] = usuario_id
            request.session['fecha_asignacion'] = str(datetime.date.today())
            # return redirect('asignar_tareas')

        if 'view_all_tasks' in request.POST:
            # Mostrar todas las tareas asignadas para hoy
            tareas = Tarea.objects.filter(fecha_asignacion=datetime.date.today())
            # guardar un solo id de los usuarios que están en tareas obteniendo el numero, quitando el queryset
            usuario_id = list(tareas.values_list('usuario__id', flat=True).distinct())
            request.session['selected_user_ids'] = usuario_id
            request.session['fecha_asignacion'] = str(datetime.date.today())
            # return redirect('asignar_tareas')
        
        if 'activate_task' in request.POST:
            selected_user_ids = request.POST.getlist('usuarios')
            fecha = datetime.date.today()
            tareas = Tarea.objects.filter(usuario__in=selected_user_ids, fecha_asignacion=fecha)
            for tarea in tareas:
                tarea.activo = True
                tarea.save()
            return redirect('asignar_tareas')
            
        
        if 'export_excel' in request.POST:
            # Recuperar los datos de la sesión
            selected_user_ids = request.session.get('selected_user_ids', [])
            fecha_asignacion = request.session.get('fecha_asignacion', None)
            if selected_user_ids and fecha_asignacion:
                selected_users = User.objects.filter(id__in=selected_user_ids)
                tareas = Tarea.objects.filter(usuario__in=selected_users, fecha_asignacion=fecha_asignacion)
                
                # Crear un DataFrame con las tareas
                df = pd.DataFrame(list(tareas.values('usuario__username', 'producto__marnombre', 'producto__fecvence', 'producto__saldo', 'conteo', 'diferencia', 'consolidado', 'observacion', 'fecha_asignacion')))
                response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = 'attachment; filename=tareas.xlsx'
                df.to_excel(response, index=False)
                # Limpiar la sesión
                selected_user_ids = request.session.pop('selected_user_ids', [])
                fecha_asignacion = request.session.pop('fecha_asignacion', None)
                return response
            # return redirect('asignar_tareas')
    # else:
    #     form = AsignarTareaForm()
    
    # Limpiar usuarios seleccionados y mostrar tareas si `assigned=1`
    if 'assigned' in request.GET:
        tareas = Tarea.objects.filter(usuario__in=selected_users) if selected_users else None
        selected_users = None  # Limpiar seleccionados para evitar reasignación

    usuarios = User.objects.all() # retornar todos los usuarios
    usuarios_con_tareas = (Tarea.objects.filter(fecha_asignacion = datetime.date.today())
                           .values('usuario__id', 'usuario__username')
                           .annotate(total_tareas=Count('id'))) # retornar los usuarios que tienen tareas asignadas
    
    total_tareas_hoy = Tarea.objects.filter(fecha_asignacion=datetime.date.today()).count()
    return render(request, 'conteoApp/asignar_tareas.html', {
        # 'form': form,
        'tareas': tareas,
        'selected_users': selected_users,
        'cant_tareas_por_usuario': cant_tareas_por_usuario,
        'usuarios_con_tareas': usuarios_con_tareas,
        'total_tareas_hoy': total_tareas_hoy,
        'usuarios': usuarios
    })
    
@login_required
# @permission_required('conteoApp.view_tarea', raise_exception=True)
def lista_tareas(request):
    # tareas = Tarea.objects.none()  # Inicializamos la variable de las tareas
    usuarios_con_tareas = []  # Lista para almacenar los usuarios y la cantidad de tareas asignadas
    
    # filtrar las tareas por fecha de asignación y usuario. La fecha de asignación se debe comparar con una fecha específica
    # fecha_especifica = datetime.date(2024, 12, 31)  # Reemplaza con la fecha específica deseada
    fecha_especifica = datetime.date.today() #- datetime.timedelta(days=1) # Reemplaza con la fecha específica deseada (ayer). Se resta un día a la fecha actual
    
    tareas = Tarea.objects.filter(usuario=request.user, fecha_asignacion=fecha_especifica, activo=True)
    
    if request.method == 'POST':
        if 'update_tarea' in request.POST:
            with transaction.atomic():
            # Actualizar los valores de conteo y observación
                for key, value in request.POST.items():
                    if key.startswith('conteo_'):  # Identificar los campos de conteo
                        tarea_id = key.split('_')[1] # Obtener el ID de la tarea a partir del nombre del campo (tarea_1, tarea_2, etc.)
                        try:
                            tarea = Tarea.objects.get(id=tarea_id)
                            tarea.conteo = int(value)  # Actualizar el conteo
                            try:
                                tarea.save()
                            except Exception as e:
                                print(f"Error al guardar la tarea {tarea.id}: {e}")
                            # obtener la tarea
                            
                            # Obtener el producto relacionado con la tarea
                            producto = tarea.producto
                            
                            fecha_vencimiento = producto.fecvence
                            if fecha_vencimiento:
                                
                                inv06_records = Inv06.objects.filter(
                                    mcnproduct=producto.mcnproduct, 
                                    mcnbodega=producto.mcnbodega,
                                    fecvence=fecha_vencimiento
                                )
                                # Tomar el saldo del primer registro encontrado o manejar duplicados si existen
                                saldo = inv06_records.first().saldo if inv06_records.exists() and inv06_records.first().saldo is not None else 0

                                if inv06_records.exists():
                                    # Calcular y guardar la diferencia
                                    tarea.diferencia = tarea.conteo - saldo 
                                    tarea.consolidado = round((inv06_records.first().vrunit * tarea.diferencia), 2)
                                    tarea.activo = False
                                    try:
                                        tarea.save()
                                    except Exception as e:
                                        print(f"Error al guardar la tarea {tarea.id}: {e}")
                                else: 
                                    print('No hay registros en Inv06')
                                    # Maneja el caso donde no hay registros en Inv06
                                    tarea.diferencia = tarea.conteo
                                    tarea.consolidado = 0
                            
                        except Tarea.DoesNotExist:
                            # Manejar el caso donde la tarea no existe
                            logger.error(f"Tarea con ID {tarea_id} no existe.")
                            # Puedes optar por saltar, registrar el error o notificar al usuario
                        except ValueError:
                            # Manejar el caso donde la conversión a entero falla
                            logger.error(f"Valor inválido para conteo: {value} para tarea ID {tarea_id}.")
                    
                    if key.startswith('observacion_'):  # Identificar los campos de observación
                        tarea_id = key.split('_')[1] 
                        try:
                            tarea = Tarea.objects.get(id=tarea_id)
                            tarea.observacion = value.strip()  # Actualizar observación. Eliminar espacios en blanco al inicio y al final con `strip()`
                            try:
                                tarea.save()
                            except Exception as e:
                                print(f"Error al guardar la tarea {tarea.id}: {e}")
                        except Tarea.DoesNotExist:
                            pass  # Manejar errores si la tarea no existe
                    
                    if key.startswith('consolidado_'):
                        tarea_id = key.split('_')[1]
                        try:
                            tarea = Tarea.objects.get(id=tarea_id)
                            tarea.consolidado = 1
                            try:
                                tarea.save()
                            except Exception as e:
                                print(f"Error al guardar la tarea {tarea.id}: {e}")
                        except Tarea.DoesNotExist:
                            pass
            return redirect('lista_tareas')
    
    return render(request, 'conteoApp/tareas_contador.html', {
        # 'form': form, 
        'tareas': tareas, 
        'usuarios_con_tareas': usuarios_con_tareas})

@permission_required('conteoApp.view_conteo', raise_exception=True)
def conteo(request):
    return render(request, 'conteoApp/conteo.html')

def error_permiso(request, exception):
    return render(request, 'error.html', status=403)

