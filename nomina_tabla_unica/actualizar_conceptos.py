"""
Actualiza una instalación donde YA se ejecutó aplicar_cambios.py.

Copia los módulos, templates y estáticos de nómina que hayan cambiado
(deja .bak de cada archivo que reemplaza). Se puede ejecutar cada vez que
llegue una versión nueva.

    python actualizar_conceptos.py RUTA_APP [--templates DIR] [--static DIR] [--simular]

Ejemplo (desde la raíz del proyecto):
    python nomina_tabla_unica/actualizar_conceptos.py presupuestoApp
"""
import argparse
import shutil
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent / 'app'

ARCHIVOS = [
    'models_nomina.py',
    'nomina_motor.py',
    'nomina_conceptos.py',
    'views_nomina.py',
    'urls_nomina.py',
    'management/commands/migrar_conceptos_nomina.py',
    'management/commands/migrar_nomina_tabla_unica.py',
]


def copiar(origen, destino, simular):
    if destino.exists() and destino.read_bytes() == origen.read_bytes():
        print(f'  = {destino} (sin cambios)')
        return
    print(f'  + {destino}')
    if simular:
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        shutil.copy2(destino, destino.with_name(destino.name + '.bak'))
    shutil.copy2(origen, destino)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('app')
    parser.add_argument('--templates')
    parser.add_argument('--static')
    parser.add_argument('--simular', action='store_true')
    args = parser.parse_args()

    app = Path(args.app).resolve()
    if not (app / 'models_nomina.py').exists():
        sys.exit(f'✖ {app} no tiene models_nomina.py: ejecute primero aplicar_cambios.py')
    plantillas = Path(args.templates).resolve() if args.templates else app / 'templates'
    estaticos = Path(args.static).resolve() if args.static else app / 'static'

    for init in ('management/__init__.py', 'management/commands/__init__.py'):
        if not (app / init).exists():
            print(f'  + {app / init}')
            if not args.simular:
                (app / init).parent.mkdir(parents=True, exist_ok=True)
                (app / init).touch()
    for nombre in ARCHIVOS:
        copiar(AQUI / nombre, app / nombre, args.simular)
    for archivo in sorted((AQUI / 'templates/presupuesto_nomina').iterdir()):
        copiar(archivo, plantillas / 'presupuesto_nomina' / archivo.name, args.simular)
    for sub in ('js', 'css'):
        for archivo in sorted((AQUI / 'static' / sub).iterdir()):
            copiar(archivo, estaticos / sub / archivo.name, args.simular)

    print('\n' + ('SIMULACIÓN: no se escribió nada.' if args.simular else
                  '✔ Listo. Ahora: python manage.py makemigrations y migrate.'))


if __name__ == '__main__':
    main()
