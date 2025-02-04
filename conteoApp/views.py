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
from django.http import HttpResponse, HttpResponseForbidden
import logging
from django.db import transaction

logger = logging.getLogger(__name__)
# fecha = datetime.datetime.now().strftime("%Y%m%d")
fecha_asignar = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y%m%d")
# fecha_asignar = '20250201'
    
@login_required
# @permission_required('conteoApp.view_tarea', raise_exception=True)
def asignar_tareas(request):
    if request.user.username != "JPRADO" and request.user.username != "admin":
        raise PermissionDenied("No tienes permiso para acceder a esta vista.")
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
            # productos = list(Venta.objects.filter(mcnproduct__regex=r'^\d+$', mcnbodega = 101).distinct('mcnproduct', 'mcnbodega'))
            productos = list(Venta.objects.filter(
                sku__regex=r'^\d+$', 
                bod = '0101', 
                fecha = fecha_asignar).exclude(marca_nom__in = ['INSMEVET', 'JL INSTRUMENTAL', 'LHAURA', 'FEDEGAN']).distinct('sku', 'bod'))
            # Convertir a listas y validar
            sku_list = []
            bod_list = []
            print(len(productos))
            for producto in productos:
                try:
                    # Convertir mcnproduct y mcnbodega a enteros
                    sku_list.append(int(producto.sku))
                    bod_list.append(int(producto.bod))
                except (ValueError, TypeError):
                    # Si no se puede convertir, continuar sin agregar el producto
                    continue

            productos_disponibles = [] # Inicializar la lista de productos disponibles
            # Buscar en la tabla Inv06 los productos que cumplen con las condiciones y tienen saldo mayor a 0
            if sku_list and bod_list:
                productos_disponibles = Inv06.objects.filter(
                    mcnproduct__in=sku_list,
                    mcnbodega__in=bod_list,
                    saldo__gt=0
                ).order_by('marnombre') # Ordenar por nombre de laboratorio
            
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
            
            with transaction.atomic():
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

                            # Verificar que el producto no ha sido asignado previamente en la fecha actual
                            if not Tarea.objects.filter(producto=producto, fecha_asignacion = datetime.date.today()).exists():
                                tareas_a_crear.append(Tarea(
                                    usuario=usuario,
                                    producto=producto,
                                    conteo=0,
                                    observacion='',
                                    diferencia=0
                                ))
                            producto_index += 1 
                Tarea.objects.bulk_create(tareas_a_crear)
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
                    .values('usuario__username', 'usuario__first_name', 'usuario__last_name')
                    .annotate(total_tareas=Count('id'))
                )
            # return redirect('asignar_tareas')
        if 'view_user_tasks' in request.POST:
            # Mostrar las tareas de un usuario específico
            usuario_id = request.POST.get('usuario_id')  # Obtener el ID del usuario
            tareas = Tarea.objects.filter(usuario__id=usuario_id, fecha_asignacion=datetime.date.today()).exclude(diferencia=0)
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
        
        # if 'activate_task' in request.POST:
        #     selected_user_ids = request.POST.getlist('usuarios')
        #     fecha = datetime.date.today()
        #     tareas = Tarea.objects.filter(usuario__in=selected_user_ids, fecha_asignacion=fecha)
        #     for tarea in tareas:
        #         tarea.activo = True
        #         tarea.save()
        #     return redirect('asignar_tareas')
            
        if 'export_excel' in request.POST:
            # Recuperar los datos de la sesión
            selected_user_ids = request.session.get('selected_user_ids', [])
            fecha_asignacion = request.session.get('fecha_asignacion', None)
            if selected_user_ids and fecha_asignacion:
                selected_users = User.objects.filter(id__in=selected_user_ids)
                tareas = Tarea.objects.filter(usuario__in=selected_users, fecha_asignacion=fecha_asignacion)
                
                # Crear un DataFrame con las tareas
                df = pd.DataFrame(list(tareas.values('usuario__first_name','usuario__last_name', 'producto__marnombre', 'producto__mcnproduct','producto__pronombre','producto__fecvence', 'producto__saldo', 'conteo', 'diferencia','producto__vrunit', 'consolidado', 'observacion', 'fecha_asignacion')))
                
                # Renombrar las columnas con nombres personalizados
                df.rename(columns={
                    'usuario__first_name': 'Nombre',
                    'usuario__last_name': 'Apellido',
                    'producto__marnombre': 'Marca',
                    'producto__mcnproduct': 'Item',
                    'producto__pronombre': 'Nombre Producto',
                    'producto__fecvence': 'Fecha Vencimiento',
                    'producto__saldo': 'Inventario',
                    'conteo': 'Conteo',
                    'diferencia': 'Diferencia',
                    'producto__vrunit': 'Valor Unitario',
                    'consolidado': 'Valor total',
                    'observacion': 'Observaciones',
                    'fecha_asignacion': 'Fecha Asignación'
                }, inplace=True)
                response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = 'attachment; filename=tareas.xlsx'
                df.to_excel(response, index=False)
                # Limpiar la sesión
                selected_user_ids = request.session.pop('selected_user_ids', [])
                fecha_asignacion = request.session.pop('fecha_asignacion', None)
                return response
            # return redirect('asignar_tareas')
        if 'reconteo' in request.POST:
            usuario_id = request.POST.get('usuario_id')
            tareas = Tarea.objects.filter(usuario__id=usuario_id, fecha_asignacion=datetime.date.today()).exclude(diferencia=0)
            for tarea in tareas:
                tarea.activo = True
                tarea.save()
            return redirect('asignar_tareas')
    # else:
    #     form = AsignarTareaForm()
    
    # Limpiar usuarios seleccionados y mostrar tareas si `assigned=1`
    if 'assigned' in request.GET:
        tareas = Tarea.objects.filter(usuario__in=selected_users) if selected_users else None
        selected_users = None  # Limpiar seleccionados para evitar reasignación

    usuarios = User.objects.exclude(username="admin") # retornar todos los usuarios
    usuarios_con_tareas = (Tarea.objects.filter(fecha_asignacion = datetime.date.today())
                           .values('usuario__id', 'usuario__username', 'usuario__first_name', 'usuario__last_name')
                           .annotate(total_tareas=Count('id'))) # retornar los usuarios que tienen tareas asignadas
    
    total_tareas_usuarios = Tarea.objects.filter(fecha_asignacion=datetime.date.today()).count()
    productos = list(Venta.objects.filter(sku__regex=r'^\d+$',bod = '0101',fecha = fecha_asignar).exclude(marca_nom__in = ['INSMEVET', 'JL INSTRUMENTAL', 'LHAURA', 'FEDEGAN']).distinct('sku', 'bod'))
    sku_list = []
    bod_list = []
    for producto in productos:
        try:
            sku_list.append(int(producto.sku))
            bod_list.append(int(producto.bod))
        except (ValueError, TypeError):
            continue
    total_tareas_hoy = []
    if sku_list and bod_list:
        total_tareas_hoy = Inv06.objects.filter(
            mcnproduct__in=sku_list,
            mcnbodega__in=bod_list,
            saldo__gt=0
        )
    total_tareas_hoy = len(total_tareas_hoy)
    return render(request, 'conteoApp/asignar_tareas.html', {
        # 'form': form,
        'tareas': tareas,
        'selected_users': selected_users,
        'cant_tareas_por_usuario': cant_tareas_por_usuario,
        'usuarios_con_tareas': usuarios_con_tareas,
        'total_tareas_usuarios': total_tareas_usuarios,
        'total_tareas_hoy': total_tareas_hoy,
        'usuarios': usuarios
    })
    
@login_required
@permission_required('conteoApp.view_tarea', raise_exception=True)
def lista_tareas(request):
    # tareas = Tarea.objects.none()  # Inicializamos la variable de las tareas
    usuarios_con_tareas = []  # Lista para almacenar los usuarios y la cantidad de tareas asignadas
    
    # filtrar las tareas por fecha de asignación y usuario. La fecha de asignación se debe comparar con una fecha específica
    # fecha_especifica = datetime.date(2024, 12, 31)  # Reemplaza con la fecha específica deseada
    fecha_especifica = datetime.date.today() #- datetime.timedelta(days=1) # Reemplaza con la fecha específica deseada (ayer). Se resta un día a la fecha actual
    
    tareas = Tarea.objects.filter(usuario=request.user, fecha_asignacion=fecha_especifica)
    if request.method == 'POST':
        if 'update_tarea' in request.POST: 
            with transaction.atomic():
                tarea_ids = set()
                tareas_a_actualizar = []
                inv06_data = {}

                # Obtener todas las tareas de la BD en una sola consulta
                tareas_dict = Tarea.objects.in_bulk([tarea.id for tarea in tareas])
                
                # Actualizar los valores de conteo y observación
                for key, value in request.POST.items():
                    if key.startswith('conteo_'):  # Identificar los campos de conteo
                        tarea_id = int(key.split('_')[1]) # Obtener el ID de la tarea a partir del nombre del campo (tarea_1, tarea_2, etc.)
                        if tarea_id in tareas_dict:
                            tarea = tareas_dict[tarea_id]
                            # si el valor no es un entero o es null o vacío, se asigna 0
                            if not value or not value.isdigit():
                                value = 0 
                            tarea.conteo = int(value)
                            tarea_ids.add(tarea_id)
                    
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
                            
                # Obtener productos y sus registros de Inv06 en una sola consulta
                productos_ids = {tareas_dict[tid].producto.id for tid in tarea_ids}
                inv06_records = Inv06.objects.filter(
                    mcnproduct__in=[tareas_dict[tid].producto.mcnproduct for tid in tarea_ids],
                    mcnbodega__in=[tareas_dict[tid].producto.mcnbodega for tid in tarea_ids],
                    fecvence__in=[tareas_dict[tid].producto.fecvence for tid in tarea_ids]
                ).values('mcnproduct', 'mcnbodega', 'fecvence', 'saldo', 'vrunit')
                
                # Convertir resultados en un diccionario para acceso rápido
                for record in inv06_records:
                    key = (record['mcnproduct'], record['mcnbodega'], record['fecvence'])
                    inv06_data[key] = {'saldo': record['saldo'], 'vrunit': record['vrunit']}
                    
                # Procesar las tareas para consolidar valores y aplicar cálculos
                for tarea_id in tarea_ids:
                    tarea = tareas_dict[tarea_id]
                    producto = tarea.producto

                    key = (producto.mcnproduct, producto.mcnbodega, producto.fecvence)
                    saldo = inv06_data.get(key, {}).get('saldo', 0)
                    vrunit = inv06_data.get(key, {}).get('vrunit', 0)

                    tarea.diferencia = tarea.conteo - saldo
                    tarea.consolidado = round(vrunit * tarea.diferencia, 2)
                    # tarea.activo = False  # Se desactiva la tarea tras ser procesada

                    tareas_a_actualizar.append(tarea)
                
                # Guardar todos los cambios en una sola operación
                if tareas_a_actualizar:
                    Tarea.objects.bulk_update(
                        tareas_a_actualizar, ['conteo', 'observacion', 'diferencia', 'consolidado']
                    )
            tareas = Tarea.objects.filter(usuario=request.user, fecha_asignacion=fecha_especifica).exclude(diferencia=0)
            # return redirect('lista_tareas')
    return render(request, 'conteoApp/tareas_contador.html', {
        # 'form': form, 
        'tareas': tareas, 
        'usuarios_con_tareas': usuarios_con_tareas})

@permission_required('conteoApp.view_conteo', raise_exception=True)
def conteo(request):
    return render(request, 'conteoApp/conteo.html')

def error_permiso(request, exception):
    return render(request, 'error.html', status=403)

import os
# Cargar el archivo Excel
# def actualizar_saldo_desde_excel(request):
#     ruta_carpeta = os.path.join('..', 'bd')
#     ruta_excel = os.path.join(ruta_carpeta, 'inv06.xlsx')
#     df = pd.read_excel(ruta_excel, sheet_name="inv", dtype={"FECVENCE": str})
    
#     with transaction.atomic():  # Usar transacción para mayor seguridad
#         # Primero, insertar los productos que no existen
#         for _, row in df.iterrows():
#             if not Inv06.objects.filter(
#                 marnombre=row["MARNOMBRE"],
#                 mcnproduct=row["MCNPRODUCT"],
#                 pronombre=row["PRONOMBRE"],
#                 fecvence=row["FECVENCE"]
#             ).exists():
#                 Inv06.objects.create(
#                     mcncuenta=row["MCNCUENTA"],
#                     promarca=row["PROMARCA"],
#                     marnombre=row["MARNOMBRE"],
#                     mcnproduct=row["MCNPRODUCT"],
#                     pronombre=row["PRONOMBRE"],
#                     fecvence=row["FECVENCE"],
#                     mcnbodega=row["MCNBODEGA"],
#                     bodnombre=row["BODNOMBRE"],
#                     saldo=row["SALDO"],
#                     vrunit=row["VRUNIT"],
#                     vrtotal=row["VRTOTAL"]
#                 )
        
#         # Luego, actualizar los saldos de todos los productos
#         for _, row in df.iterrows():
#             Inv06.objects.filter(
#                 marnombre=row["MARNOMBRE"],
#                 mcnproduct=row["MCNPRODUCT"],
#                 pronombre=row["PRONOMBRE"],
#                 fecvence=row["FECVENCE"]
#             ).update(saldo=row["SALDO"])
    
#     print("Inserción y actualización completadas.")
#     return HttpResponse("Inserción y actualización completadas.")

from django.db.models import Q
from functools import reduce
import operator

def actualizar_saldo_desde_excel(request):
    ruta_carpeta = os.path.join('..', 'bd')
    ruta_excel = os.path.join(ruta_carpeta, 'inv06.xlsx')
    df = pd.read_excel(ruta_excel, sheet_name="inv", dtype={"FECVENCE": str})
    
    # 2. Crear una columna clave (tupla) para identificar unívocamente cada registro
    df["__key__"] = df.apply(
        lambda row: (
            row["MARNOMBRE"],
            row["MCNPRODUCT"],
            row["PRONOMBRE"],
            row["FECVENCE"]
        ),
        axis=1
    )

    # 3. Crear un diccionario de clave -> datos de la fila
    data_dict = df.set_index("__key__").to_dict(orient="index")

    # Tomamos todas las tuplas clave
    all_keys = list(data_dict.keys())

    # Para evitar un query gigante con OR en caso de muchísimas claves,
    # podrías partirlo en lotes más pequeños (chunking) si se requiere.
    # Aquí lo hacemos en una sola consulta para simplificar.

    with transaction.atomic():
        # 4. Buscar todos los objetos existentes que coinciden con alguna clave
        #    Esto produce una sola consulta con OR encadenados.
        if all_keys:
            # Generamos una lista de condiciones Q
            q_objects = [
                Q(marnombre=k[0], mcnproduct=k[1], pronombre=k[2], fecvence=k[3])
                for k in all_keys
            ]
            existing_objs = Inv06.objects.filter(reduce(operator.or_, q_objects))
        else:
            existing_objs = Inv06.objects.none()

        # 5. Preparar lista de objetos a actualizar
        to_update = []
        existing_keys = set()
        for obj in existing_objs:
            # Creamos la clave a partir del objeto
            obj_key = (
                obj.marnombre,
                obj.mcnproduct,
                obj.pronombre,
                obj.fecvence
            )
            existing_keys.add(obj_key)

            # Actualizamos solo el campo saldo (u otros campos si hiciera falta)
            obj.saldo = float(data_dict[obj_key]["SALDO"])
            to_update.append(obj)

        # 6. Hacer bulk update de todos los objetos existentes
        if to_update:
            Inv06.objects.bulk_update(to_update, ["saldo"])

        # 7. Preparar la lista de nuevos objetos para creación masiva
        new_keys = set(all_keys) - existing_keys
        new_objs = []
        for key in new_keys:
            row_data = data_dict[key]
            new_objs.append(
                Inv06(
                    mcncuenta=row_data["MCNCUENTA"],
                    promarca=row_data["PROMARCA"],
                    marnombre=key[0],
                    mcnproduct=key[1],
                    pronombre=key[2],
                    fecvence=key[3],
                    mcnbodega=row_data["MCNBODEGA"],
                    bodnombre=row_data["BODNOMBRE"],
                    saldo=float(row_data["SALDO"]),
                    vrunit=row_data["VRUNIT"],
                    vrtotal=row_data["VRTOTAL"],
                )
            )

        # 8. Crear en lote los nuevos objetos
        if new_objs:
            Inv06.objects.bulk_create(new_objs)
    return HttpResponse("Inserción y actualización completadas.")
