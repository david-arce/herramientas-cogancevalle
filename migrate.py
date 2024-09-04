import subprocess
# Crear las migraciones
subprocess.run(['python', 'manage.py', 'makemigrations'], shell=True)
subprocess.run(['python', 'manage.py', 'migrate'], shell=True)
