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
]