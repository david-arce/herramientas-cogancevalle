"""
{% static_v 'js/archivo.js' %}  ->  /static/js/archivo.js?v=<fecha de modificación>

Igual que {% static %}, pero la URL cambia sola cada vez que el archivo
cambia. Así el navegador descarga la versión nueva del JS/CSS después de
cada actualización, sin tener que borrar la caché ni cambiar nada a mano.
"""
import os

from django import template
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.templatetags.static import static

register = template.Library()


def _version(ruta):
    """Fecha de modificación del archivo, o None si no se encuentra.

    Nunca lanza error: si no puede calcular la versión, la página usa la URL
    normal de {% static %}.
    """
    try:
        archivo = finders.find(ruta)
        if not archivo:
            archivo = staticfiles_storage.path(ruta)       # después de collectstatic
        if archivo and os.path.exists(archivo):
            return str(int(os.path.getmtime(archivo)))
    except Exception:
        pass
    return None


@register.simple_tag
def static_v(ruta):
    url = static(ruta)
    version = _version(ruta)
    if not version:
        return url
    return f"{url}{'&' if '?' in url else '?'}v={version}"
