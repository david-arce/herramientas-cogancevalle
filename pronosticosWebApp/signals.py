# signals.py
from django.db.backends.signals import connection_created
from django.dispatch import receiver
from pronosticosWebApp import views

@receiver(connection_created)
def ejecutar_funcion(sender, **kwargs):
    # desconectamos el receptor para que no vuelva a dispararse
    connection_created.disconnect(ejecutar_funcion, sender=sender)
    # tu llamada inicial
    views.lista_productos()