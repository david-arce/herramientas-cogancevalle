from django.urls import path
from pronosticosWebApp import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('lista/', views.lista_productos, name='lista'),
    path('chart/', views.get_chart, name='chart'),
    path('send_data/', views.send_data, name='send_data'),
    path('filtro/', views.filtro, name='filtro'),
]