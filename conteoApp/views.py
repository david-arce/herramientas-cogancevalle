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
    usuario = None

    if request.method == 'POST':
        form = AsignarTareaForm(request.POST)
        if form.is_valid():
            # Obtener el usuario seleccionado
            usuario = form.cleaned_data['usuario']

            # Seleccionar productos aleatorios del modelo Venta
            productos = list(Venta.objects.all())  # Obtenemos todos los productos
            productos_random = random.sample(productos, min(len(productos), 5))  # Ejemplo: Asignar 5 productos aleatorios

            # Crear una tarea para cada producto seleccionado
            for producto in productos_random:
                Tarea.objects.create(
                    usuario=usuario,
                    producto=producto,
                    conteo=0,  # Puedes asignar un valor por defecto o personalizarlo
                    estado='pendiente'
                )

            # Obtener las tareas asignadas a ese usuario para mostrarlas
            tareas = Tarea.objects.filter(usuario=usuario)

    else:
        form = AsignarTareaForm()

    return render(request, 'conteo/asignar_tareas.html', {
        'form': form,
        'tareas': tareas,
        'usuario': usuario,
    })
    
@login_required
def lista_tareas(request):
    tareas = Tarea.objects.filter(usuario=request.user)
    return render(request, 'conteo/lista_tareas.html', {'tareas': tareas})

@permission_required('conteoApp.view_conteo', raise_exception=True)
def conteo(request):
    return render(request, 'conteo/conteo.html')

def error_permiso(request, exception):
    return render(request, 'error.html', status=403)

