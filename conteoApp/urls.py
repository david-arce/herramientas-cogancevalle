from django.urls import path
from . import views
# from .views import TareaListView, TareaCreateView

urlpatterns = [
    path('', views.conteo, name='conteo'),
    path('asignar-tareas/', views.asignar_tareas, name='asignar_tareas'),
    path('lista-tareas/', views.lista_tareas, name='lista_tareas'),
    path('tareas-contador/', views.actualizar_tarea, name='tareas_contador'),
    # path('tareas/', TareaListView.as_view(), name='lista_tareas'),
    # path('tareas/asignar/', TareaCreateView.as_view(), name='asignar_tarea'),
]

