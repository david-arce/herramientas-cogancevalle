web: python manage.py collectstatic --no-input && python manage.py cargar_productos && gunicorn herramientas_cg.wsgi:application --workers 8 --threads 4 --timeout 400
