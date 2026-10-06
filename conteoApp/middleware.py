from django.shortcuts import redirect
from django.urls import Resolver404, resolve

from .permisos import es_contador

# Pantallas a las que un contador no debe llegar: se le envía a "Productos asignados".
VISTAS_BLOQUEADAS_PARA_CONTADOR = {"dashboard"}


class RedireccionContadoresMiddleware:
    """
    Si un contador entra a Pronósticos (por ejemplo, justo después de iniciar
    sesión), lo lleva a su lista de productos asignados.
    Debe ir en MIDDLEWARE después de AuthenticationMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "GET" and es_contador(request.user):
            try:
                nombre = resolve(request.path_info).url_name
            except Resolver404:
                nombre = None
            if nombre in VISTAS_BLOQUEADAS_PARA_CONTADOR:
                return redirect("lista_tareas")
        return self.get_response(request)
