web:service cron start && 
python manage.py crontab add && 
python manage.py collectstatic --no-input &&
gunicorn herramientas_cg.wsgi:application --workers 8 --threads 4 --timeout 400
