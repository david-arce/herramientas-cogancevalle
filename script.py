import os
import subprocess
import chardet

# Ruta del archivo models.py
file_path = 'pronosticosWebApp/models.py'

# Eliminar el archivo models.py si ya existe
if os.path.exists(file_path):
    os.remove(file_path)

# Generar el archivo models.py con inspectdb
subprocess.run(['python', 'manage.py', 'inspectdb', 'demanda', '>', 'pronosticosWebApp/models.py'], shell=True)

# Convertir el archivo models.py a UTF-8
input_file_path = 'pronosticosWebApp/models.py'
output_file_path = 'pronosticosWebApp/models.py'

# Detecta la codificación del archivo de entrada
with open(input_file_path, 'rb') as input_file:
    raw_data = input_file.read()
    result = chardet.detect(raw_data)
    encoding = result['encoding']

with open(input_file_path, 'r', encoding=encoding) as input_file:
    content = input_file.read()

with open(output_file_path, 'w', encoding='utf-8') as output_file:
    output_file.write(content)

os.replace(output_file_path, input_file_path)

subprocess.run(['python', 'manage.py', 'makemigrations', 'pronosticosWebApp'], shell=True)
subprocess.run(['python', 'manage.py', 'migrate', 'pronosticosWebApp'], shell=True)

