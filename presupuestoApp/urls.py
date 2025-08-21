from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboardPresupuesto'),
    path('presupuesto/', views.presupuesto, name='presupuesto'),
]
