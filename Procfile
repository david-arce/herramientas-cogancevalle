release: python manage.py collectstatic --no-input && python manage.py cargar_productos
web: gunicorn herramientas_cg.wsgi:application --workers 6 --timeout 400