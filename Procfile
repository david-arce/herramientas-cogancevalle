web: python manage.py collectstatic --no-input && gunicorn herramientas_cg.wsgi:application --workers 8 --threads 4 --timeout 400 --preload
