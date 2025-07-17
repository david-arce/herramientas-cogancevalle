from django.apps import AppConfig
import os

class PronosticoswebappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pronosticosWebApp'
    
    # def ready(self):
    #     import pronosticosWebApp.signals