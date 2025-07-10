"""
WSGI config for pronosticos_web project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os
import sys
from django.core.wsgi import get_wsgi_application

from pathlib import Path
# Add project directory to the sys.path
path_home = str(Path(__file__).parents[1])
if path_home not in sys.path:
    sys.path.append(path_home)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'herramientas_cg.settings')

application = get_wsgi_application()
# Carga tus pronósticos una sola vez al levantar cada worker
# try:
#     from pronosticosWebApp.views import lista_productos
#     lista_productos()
#     # tal vez pongas un print o logging aquí
# except Exception:
#     pass