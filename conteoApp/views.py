from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import permission_required, login_required
from django.core.exceptions import PermissionDenied
from django.views.generic import ListView
from django.views.generic import CreateView
from django.urls import reverse_lazy
from .models import Venta
from .models import Tarea
from .forms import AsignarTareaForm
import random

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

    if request.method == 'POST':
        form = AsignarTareaForm(request.POST)
        if form.is_valid():
            # Obtener el usuario seleccionado
            selected_users = form.cleaned_data['users']

            # Filtrar productos donde 'mcnproduct' contenga solo valores numéricos
            productos = list(Venta.objects.filter(mcnproduct__regex=r'^\d+$'))
            productos_random = random.sample(productos, min(len(productos), 5 * len(selected_users)))  # Ejemplo: Asignar 5 productos aleatorios

            # Crear un índice para distribuir productos entre usuarios
            producto_index = 0
            total_productos = len(productos_random)

            # Asignar productos únicos a cada usuario seleccionado
            for usuario in selected_users:
                # Asignar productos únicos hasta alcanzar el límite por usuario (ejemplo: 5 productos)
                for _ in range(5):
                    if producto_index < total_productos:
                        producto = productos_random[producto_index]

                        # Verificar que el producto no ha sido asignado a otro usuario
                        if not Tarea.objects.filter(producto=producto).exists():
                            Tarea.objects.create(
                                usuario=usuario,
                                producto=producto,
                                conteo=0,  # Valor por defecto o personalizado
                                estado='pendiente'
                            )
                        producto_index += 1
                    else:
                        break  # Romper si no hay más productos disponibles

            # Obtener las tareas asignadas a ese usuario para mostrarlas
            tareas = Tarea.objects.filter(usuario__in=selected_users)

    else:
        form = AsignarTareaForm()

    return render(request, 'conteoApp/asignar_tareas.html', {
        'form': form,
        'tareas': tareas,
        'selected_users': selected_users,
    })
    
@login_required
def lista_tareas(request):
    tareas = None
    # tareas = Tarea.objects.filter(usuario=request.user)
    if request.method == 'POST':
        form = AsignarTareaForm(request.POST)
        if form.is_valid():
            selected_users = form.cleaned_data['users']
            tareas = Tarea.objects.filter(usuario__in=selected_users)
            # Reiniciar el formulario con los usuarios seleccionados
            form = AsignarTareaForm(initial={'users': selected_users})
    else:
        form = AsignarTareaForm()
    
    return render(request, 'conteoApp/lista_tareas.html', {'form': form, 'tareas': tareas})

@permission_required('conteoApp.view_conteo', raise_exception=True)
def conteo(request):
    return render(request, 'conteoApp/conteo.html')

def error_permiso(request, exception):
    return render(request, 'error.html', status=403)

