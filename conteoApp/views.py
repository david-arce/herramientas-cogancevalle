from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import permission_required, login_required
from django.core.exceptions import PermissionDenied
from django.views.generic import ListView
from django.views.generic import CreateView
from django.urls import reverse, reverse_lazy
from .models import Venta
from .models import Tarea
from pronosticosWebApp.models import Demanda
from .forms import AsignarTareaForm
import random
from django.contrib import messages
from django.db.models import Count
from django.db.models import Q # Importar el objeto Q para consultas complejas con filtros lógicos

# class TareaListView(ListView):
#     model = Tarea
#     template_name = 'conteo/tareas.html'  # Este es el archivo HTML donde se renderizará la lista de productos
#     context_object_name = 'tareas'

# vista para crear tareas
# class TareaCreateView(LoginRequiredMixin,CreateView):
#     model = Tarea
#     template_name = 'conteo/asignar_tarea.html'
#     success_url = reverse_lazy('lista_tareas')  # Redirige a la lista de productos
    
#     def form_valid(self, form):
#         return super().form_valid(form)
    
    
@login_required
def asignar_tareas(request):
    tareas = None  # Inicializamos la variable de las tareas
    selected_users = None
    usuarios_con_tareas = []  # Lista para almacenar los usuarios y la cantidad de tareas asignadas

    if request.method == 'POST':
        form = AsignarTareaForm(request.POST)
        if 'assign_task' in request.POST:
            if form.is_valid():
                # Obtener el usuario seleccionado
                selected_users = form.cleaned_data['users']

                # Filtrar productos disponibles con un valor numérico en 'mcnproduct'
                productos = list(Venta.objects.filter(mcnproduct__regex=r'^\d+$'))
                total_productos = len(productos)

                # Verificar que hay suficientes productos para asignar
                if total_productos == 0 or len(selected_users) == 0:
                    messages.error(request, "No hay productos disponibles o no se seleccionaron usuarios.")
                    return redirect('asignar_tareas')

                # Calcular productos por usuario
                productos_por_usuario = total_productos // len(selected_users)
                productos_restantes = total_productos % len(selected_users)

                # Barajar los productos para distribuir aleatoriamente
                random.shuffle(productos)

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
                            producto = productos[producto_index]

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

                # Mensaje de éxito y redirección
                # messages.success(request, f"Tareas asignadas equitativamente a {', '.join([user.username for user in selected_users])}.")
                # return redirect(reverse('asignar_tareas') + '?assigned=1')    
        if 'delete_task' in request.POST:
            if form.is_valid():
                # Obtener el usuario seleccionado
                selected_users = form.cleaned_data['users']
                tareas = Tarea.objects.filter(usuario__in=selected_users)
                tareas.delete()
                messages.success(request, f"Tareas eliminadas de {', '.join([user.username for user in selected_users])}.")
                # return redirect(reverse('asignar_tareas') + '?assigned=1')
        if 'filter_users' in request.POST:
            if form.is_valid():
                selected_users = form.cleaned_data['users']
                tareas = Tarea.objects.filter(usuario__in=selected_users)
                
                # Calcular el número de tareas por usuario
                usuarios_con_tareas = (
                    Tarea.objects.filter(usuario__in=selected_users)
                    .values('usuario__username')  # Agrupar por nombre de usuario
                    .annotate(total_tareas=Count('id'))  # Contar las tareas
                )
    else:
        form = AsignarTareaForm()
    
    # Limpiar usuarios seleccionados y mostrar tareas si `assigned=1`
    if 'assigned' in request.GET:
        tareas = Tarea.objects.filter(usuario__in=selected_users) if selected_users else None
        selected_users = None  # Limpiar seleccionados para evitar reasignación

    return render(request, 'conteoApp/asignar_tareas.html', {
        'form': form,
        'tareas': tareas,
        'selected_users': selected_users,
        'usuarios_con_tareas': usuarios_con_tareas
    })

from django.db.models import Q, CharField, IntegerField
from django.db.models.functions import Cast
@login_required
def lista_tareas(request):
    tareas = Tarea.objects.none()  # Inicializamos la variable de las tareas
    usuarios_con_tareas = []  # Lista para almacenar los usuarios y la cantidad de tareas asignadas
    inventarios = []  # Lista para almacenar las coincidencias de productos y su inventario
    # tareass = Tarea.objects.filter(usuario=request.user)
    
    if request.method == 'POST':
        # Verificar si el formulario es para filtrar usuarios o actualizar valores de conteo
        form = AsignarTareaForm(request.POST)
        if 'filter_users' in request.POST:
            if form.is_valid():
                selected_users = form.cleaned_data['users']
                tareas = Tarea.objects.filter(usuario__in=selected_users)
                
                # Calcular el número de tareas por usuario
                usuarios_con_tareas = (
                    Tarea.objects.filter(usuario__in=selected_users)
                    .values('usuario__username')  # Agrupar por nombre de usuario
                    .annotate(total_tareas=Count('id'))  # Contar las tareas
                )
                
                # Filtrar inventarios relacionados con tipo de dato compatible
                inventarios = Demanda.objects.filter(
                    Q(
                        codcmc_c50__in=(
                            tareas.annotate(
                                cod_producto=Cast('producto__mcnproduct', output_field=IntegerField())
                            ).values_list('cod_producto', flat=True)
                        )
                    )
                    & Q(
                        proveedor__in=(
                            tareas.annotate(
                                proveedor_cast=Cast('producto__marnombre', output_field=CharField())
                            ).values_list('proveedor_cast', flat=True)
                        )
                    )
                    & Q(
                        nombre_c100__in=(
                            tareas.annotate(
                                nombre_cast=Cast('producto__pronombre', output_field=CharField())
                            ).values_list('nombre_cast', flat=True)
                        )
                    )
                    & Q(
                        bodega_c5__in=(
                            tareas.annotate(
                                bodega_cast=Cast('producto__mcnbodega', output_field=IntegerField())
                            ).values_list('bodega_cast', flat=True)
                        )
                    )
                ).values('codcmc_c50', 'inventario')

                # print(list(inventarios.values_list('inventario', flat=True)))
                print(inventarios)
                
                # Reiniciar el formulario con los usuarios seleccionados
                # form = AsignarTareaForm(initial={'users': selected_users})

            # Redirigir para evitar reenvío del formulario
            # return redirect('tareas_contador')
        if 'update_tarea' in request.POST:
            # Actualizar los valores de conteo y observación
            for key, value in request.POST.items():
                if key.startswith('conteo_'):  # Identificar los campos de conteo
                    tarea_id = key.split('_')[1] # Obtener el ID de la tarea a partir del nombre del campo (tarea_1, tarea_2, etc.)
                    try:
                        tarea = Tarea.objects.get(id=tarea_id)
                        tarea.conteo = int(value)  # Actualizar el conteo
                        tarea.save()
                    except (Tarea.DoesNotExist, ValueError):
                        tarea.conteo = 0
                
                if key.startswith('observacion_'):  # Identificar los campos de observación
                    tarea_id = key.split('_')[1] 
                    try:
                        tarea = Tarea.objects.get(id=tarea_id)
                        tarea.observacion = value.strip()  # Actualizar observación. Eliminar espacios en blanco al inicio y al final con `strip()`
                        tarea.save()
                    except Tarea.DoesNotExist:
                        pass  # Manejar errores si la tarea no existe
            
        

    else:
        form = AsignarTareaForm()
    
    return render(request, 'conteoApp/tareas_contador.html', {
        'form': form, 
        'tareas': tareas, 
        'usuarios_con_tareas': usuarios_con_tareas})

@login_required
def actualizar_tarea(request):
    tareas = None
    inventarios = []
    if request.method == 'POST':
        if 'update_tarea' in request.POST:
            # Actualizar los valores de conteo y observación
            for key, value in request.POST.items():
                if key.startswith('conteo_'):  # Identificar los campos de conteo
                    tarea_id = key.split('_')[1] # Obtener el ID de la tarea a partir del nombre del campo (tarea_1, tarea_2, etc.)
                    try:
                        tarea = Tarea.objects.get(id=tarea_id)
                        tarea.conteo = int(value)  # Actualizar el conteo
                        tarea.save()
                    except (Tarea.DoesNotExist, ValueError):
                        tarea.conteo = 0
                
                if key.startswith('observacion_'):  # Identificar los campos de observación
                    tarea_id = key.split('_')[1] 
                    try:
                        tarea = Tarea.objects.get(id=tarea_id)
                        tarea.observacion = value.strip()  # Actualizar observación. Eliminar espacios en blanco al inicio y al final con `strip()`
                        tarea.save()
                    except Tarea.DoesNotExist:
                        pass  # Manejar errores si la tarea no existe
            
    else:
        form = AsignarTareaForm()
    
    return render(request, 'conteoApp/tareas_contadores.html', {
        'form': form, 
        'tareas': tareas})

@permission_required('conteoApp.view_conteo', raise_exception=True)
def conteo(request):
    return render(request, 'conteoApp/conteo.html')

def error_permiso(request, exception):
    return render(request, 'error.html', status=403)

