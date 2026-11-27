from django.urls import path
from pronosticosWebApp import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('lista/', views.demanda, name='lista'),
    path('chart/', views.get_chart, name='chart'),
    path('send_data/', views.send_data, name='send_data'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('export-elanco/', views.export_elanco, name='export_elanco'), # Exportar a excel Elanco
    path('clientes-elanco/', views.clientes_elanco, name='clientes_elanco'), # Clientes sin codificar (solo admin)
    path('clientes-elanco/plantilla/', views.plantilla_clientes_elanco, name='plantilla_clientes_elanco'),
    path('traslados_resumen_json/', views.traslados_resumen_json, name='traslados_resumen_json'),
    path('config_proveedor_sku/', views.config_proveedor_sku_json, name='config_proveedor_sku'),
    # path('save_data/', views.guardar_productos, name='save_data'), # Guardar productos
]