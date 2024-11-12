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

            # Seleccionar productos aleatorios del modelo Venta
            productos = list(Venta.objects.all())  # Obtenemos todos los productos
            productos_random = random.sample(productos, min(len(productos), 5))  # Ejemplo: Asignar 5 productos aleatorios

            # Crear una tarea para cada producto seleccionado
            for usuario in selected_users:
                for producto in productos_random:
                    Tarea.objects.create(
                        usuario=usuario,
                        producto=producto,
                        conteo=0,  # Puedes asignar un valor por defecto o personalizarlo
                        estado='pendiente'
                    )

            # Obtener las tareas asignadas a ese usuario para mostrarlas
            tareas = Tarea.objects.filter(usuario__in=selected_users)

    else:
        form = AsignarTareaForm()

    return render(request, 'conteoApp/user_selection.html', {
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

