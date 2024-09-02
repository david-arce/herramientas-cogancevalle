from django.apps import AppConfig


class PronosticoswebappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pronosticosWebApp'
    
    def ready(self):
        #importar el archivo prueba.py que está por fuera de la carpeta de la aplicación
        from pronosticosWebApp import views
        views.lista_productos()
        
