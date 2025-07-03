# signals.py
# from django.db.backends.signals import connection_created
# from django.dispatch import receiver
# from pronosticosWebApp import views

# # Variable global para controlar que la función solo se ejecute una vez
# has_run = False

# @receiver(connection_created)
# def ejecutar_funcion(sender, **kwargs):
#     global has_run
#     # Solo ejecuta la función si no ha sido ejecutada antes
#     if not has_run:
#         views.lista_productos()
#         has_run = True
