#!/usr/bin/env python3
"""
Integra la tabla única de nómina en la app Django.

    python aplicar_cambios.py RUTA_APP [--templates DIR] [--static DIR] [--simular]

  RUTA_APP     carpeta de la app (donde están models.py y views.py)
  --templates  carpeta que contiene "presupuesto_nomina/" (por defecto RUTA_APP/templates)
  --static     carpeta que contiene "js/" y "css/"        (por defecto RUTA_APP/static)
  --simular    no escribe nada, solo informa

Qué hace (deja copia .bak de cada archivo que modifica):
  1. models.py : saca las 34 clases viejas de nómina a models_nomina_legado.py
                 (sin cambiarlas, para que Django no borre las tablas todavía)
                 e importa el modelo nuevo.
  2. views.py  : quita la sección de NÓMINA (ahora vive en views_nomina.py)
                 y limpia el import de los modelos viejos.
  3. Copia models_nomina.py, nomina_motor.py, views_nomina.py, urls_nomina.py
     y el comando migrar_nomina_tabla_unica.
  4. Copia templates y estáticos nuevos y mueve los 36 templates viejos a
     una carpeta _obsoletos (no los borra).
"""
import argparse
import ast
import shutil
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent / 'app'

LEGADO = [
    'PresupuestoSueldos', 'PresupuestoSueldosAux',
    'PresupuestoComisiones', 'PresupuestoComisionesAux',
    'PresupuestoHorasExtra', 'PresupuestoHorasExtraAux',
    'PresupuestoAuxilioTransporte', 'PresupuestoAuxilioTransporteAux',
    'PresupuestoMediosTransporte', 'PresupuestoMediosTransporteAux',
    'PresupuestoAyudaTransporte', 'PresupuestoAyudaTransporteAux',
    'PresupuestoCesantias', 'PresupuestoCesantiasAux',
    'PresupuestoInteresesCesantias', 'PresupuestoInteresesCesantiasAux',
    'PresupuestoPrima', 'PresupuestoPrimaAux',
    'PresupuestoVacaciones', 'PresupuestoVacacionesAux',
    'PresupuestoBonificaciones', 'PresupuestoBonificacionesAux',
    'PresupuestoSeguridadSocial', 'PresupuestoSeguridadSocialAux',
    'PresupuestoAprendiz', 'PresupuestoAprendizAux',
    'PresupuestoBolsaConsumibles', 'PresupuestoBolsaConsumiblesAux',
    'PresupuestoAuxilioTBCKIT', 'PresupuestoAuxilioTCBKITAux',
    'PresupuestoBonificacionesFoco', 'PresupuestoBonificacionesFocoAux',
    'PresupuestoAuxilioEducacion', 'PresupuestoAuxilioEducacionAux',
    'PresupuestoBonosKyrovet', 'PresupuestoBonosKyrovetAux',
]

INICIO_NOMINA = '#  ---------------------NOMINA'
FIN_NOMINA = '# -----------------------------PRESUPUESTO GENERAL'

TEMPLATES_VIEJOS = [
    'presupuesto_nomina.html', 'aux_presupuesto_nomina.html', '_barra_auxiliar.html',
    '_barra_principal.html',
] + [f'{p}{n}.html' for n in (
    'aprendiz', 'auxilio_educacion', 'auxilio_TBCKIT', 'auxilio_transporte', 'ayuda_transporte',
    'bolsa_consumibles', 'bonificaciones', 'bonificaciones_foco', 'bonos_kyrovet', 'cesantias',
    'comisiones', 'horas_extra', 'intereses_cesantias', 'medios_transporte', 'prima',
    'seguridad_social', 'vacaciones') for p in ('', 'aux_')]

ENCABEZADO_LEGADO = '''"""
Modelos ANTIGUOS de nómina (34 tablas). Solo existen para que Django no borre
las tablas antes de copiar los datos con:

    python manage.py migrar_nomina_tabla_unica

Después de migrar: borrar este archivo, quitar su import al final de
models.py, ejecutar makemigrations + migrate (eso elimina las tablas).
"""
from django.db import models
from django.utils import timezone

'''

IMPORTS_MODELS = '''

# ── Nómina: tabla única ────────────────────────────────────────────────
from .models_nomina import PresupuestoNomina  # noqa: E402,F401
# TEMPORAL: borrar esta línea (y el archivo) después de migrar los datos
from .models_nomina_legado import *  # noqa: E402,F401,F403
'''

SECCION_NUEVA = '''#  ---------------------NOMINA-------------------------------------------------------------
#  La nómina usa ahora una sola tabla (PresupuestoNomina). Las vistas están en
#  views_nomina.py, la lógica en nomina_motor.py y las rutas en urls_nomina.py.


'''


def fallar(mensaje):
    print(f'✖ {mensaje}')
    sys.exit(1)


def respaldar(ruta, simular):
    if not simular:
        shutil.copy2(ruta, ruta.with_suffix(ruta.suffix + '.bak'))


# ─────────────────────────────────────────────────────────────── models.py
def procesar_models(ruta):
    fuente = ruta.read_text(encoding='utf-8')
    if 'from .models_nomina import PresupuestoNomina' in fuente:
        fallar(f'{ruta} ya fue modificado (encontré el import de models_nomina).')
    lineas = fuente.splitlines(keepends=True)
    arbol = ast.parse(fuente)

    rangos, encontradas = [], set()
    for nodo in arbol.body:
        if isinstance(nodo, ast.ClassDef) and nodo.name in LEGADO:
            inicio = min([nodo.lineno] + [d.lineno for d in nodo.decorator_list]) - 1
            rangos.append((inicio, nodo.end_lineno))
            encontradas.add(nodo.name)

    faltan = set(LEGADO) - encontradas
    if faltan:
        print(f'  ⚠ no encontré en models.py: {", ".join(sorted(faltan))}')
    if not rangos:
        fallar('No encontré ninguna clase antigua de nómina en models.py.')

    movidas = ''.join(''.join(lineas[a:b]).rstrip() + '\n\n\n' for a, b in rangos)
    quitar = set()
    for a, b in rangos:
        quitar.update(range(a, b))
    restante = ''.join(l for i, l in enumerate(lineas) if i not in quitar).rstrip() + '\n' + IMPORTS_MODELS

    ast.parse(restante)
    ast.parse(ENCABEZADO_LEGADO + movidas)
    return restante, ENCABEZADO_LEGADO + movidas, len(rangos)


# ──────────────────────────────────────────────────────────────── views.py
def nombres_definidos(nodos):
    nombres = set()
    for nodo in nodos:
        if isinstance(nodo, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            nombres.add(nodo.name)
        elif isinstance(nodo, (ast.Assign, ast.AnnAssign)):
            objetivos = nodo.targets if isinstance(nodo, ast.Assign) else [nodo.target]
            for t in objetivos:
                nombres.update(n.id for n in ast.walk(t) if isinstance(n, ast.Name))
        elif isinstance(nodo, (ast.Import, ast.ImportFrom)):
            nombres.update((a.asname or a.name).split('.')[0] for a in nodo.names)
    return nombres


def nombres_globales_usados(arbol):
    """Nombres que el módulo lee como globales (descarta variables locales)."""
    usados = set()

    def locales_de(funcion):
        args = funcion.args
        nombres = {a.arg for a in args.args + args.kwonlyargs + args.posonlyargs}
        nombres.update(a.arg for a in (args.vararg, args.kwarg) if a)
        for n in ast.walk(funcion):
            if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
                nombres.add(n.id)
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n is not funcion:
                nombres.add(n.name)
            elif isinstance(n, (ast.Import, ast.ImportFrom)):
                nombres.update((a.asname or a.name).split('.')[0] for a in n.names)
            elif isinstance(n, ast.ExceptHandler) and n.name:
                nombres.add(n.name)
        return nombres

    for nodo in arbol.body:
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            locales = locales_de(nodo)
            cargas = {n.id for n in ast.walk(nodo) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
            usados.update(cargas - locales)
            for d in nodo.decorator_list:
                usados.update(n.id for n in ast.walk(d) if isinstance(n, ast.Name))
        else:
            usados.update(n.id for n in ast.walk(nodo) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load))
    return usados


def procesar_views(ruta):
    fuente = ruta.read_text(encoding='utf-8')
    lineas = fuente.splitlines(keepends=True)

    inicios = [i for i, l in enumerate(lineas) if l.startswith(INICIO_NOMINA)]
    fines = [i for i, l in enumerate(lineas) if l.startswith(FIN_NOMINA)]
    if len(inicios) != 1 or len(fines) != 1 or fines[0] <= inicios[0]:
        fallar(f'No encontré una única sección de nómina entre "{INICIO_NOMINA}" y "{FIN_NOMINA}".')
    a, b = inicios[0], fines[0]

    quitado = ''.join(lineas[a:b])
    nuevo = ''.join(lineas[:a]) + SECCION_NUEVA + ''.join(lineas[b:])

    # Limpiar el import de modelos
    arbol = ast.parse(nuevo)
    lineas = nuevo.splitlines(keepends=True)
    for nodo in arbol.body:
        if (isinstance(nodo, ast.ImportFrom) and nodo.level == 1 and nodo.module == 'models'
                and any(al.name in LEGADO for al in nodo.names)):
            conservar = [al.name if not al.asname else f'{al.name} as {al.asname}'
                         for al in nodo.names if al.name not in LEGADO]
            linea = 'from .models import (\n' + ''.join(f'    {n},\n' for n in conservar) + ')\n'
            lineas[nodo.lineno - 1:nodo.end_lineno] = [linea]
            break
    nuevo = ''.join(lineas)

    # Validaciones: sintaxis y nombres que el resto del archivo aún use
    arbol = ast.parse(nuevo)
    definidos = nombres_definidos(arbol.body) | set(dir(__builtins__))
    usados = nombres_globales_usados(arbol)
    solo_en_nomina = nombres_definidos(ast.parse(quitado).body) - definidos
    rotos = sorted(usados & solo_en_nomina)
    legado_usado = sorted(usados & set(LEGADO))
    if rotos or legado_usado:
        fallar('views.py seguiría usando nombres que se eliminan: ' + ', '.join(rotos + legado_usado))
    return nuevo, b - a, definidos


def revisar_urls(ruta, definidos):
    """Lista las rutas de urls.py que apuntan a vistas de nómina eliminadas."""
    if not ruta.exists():
        return []
    arbol = ast.parse(ruta.read_text(encoding='utf-8'))
    return sorted({
        n.attr for n in ast.walk(arbol)
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
        and n.value.id == 'views' and n.attr not in definidos
    })


# ─────────────────────────────────────────────────────────────── archivos
def copiar(origen, destino, simular):
    print(f'  + {destino}')
    if not simular:
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origen, destino)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('app', type=Path)
    parser.add_argument('--templates', type=Path)
    parser.add_argument('--static', type=Path)
    parser.add_argument('--simular', action='store_true')
    args = parser.parse_args()

    app = args.app.resolve()
    plantillas = (args.templates or app / 'templates').resolve()
    estaticos = (args.static or app / 'static').resolve()
    simular = args.simular
    for requerido in (app / 'models.py', app / 'views.py'):
        if not requerido.exists():
            fallar(f'No existe {requerido}')

    print('1) models.py')
    models_nuevo, legado, n = procesar_models(app / 'models.py')
    print(f'  {n} clases antiguas → models_nomina_legado.py')

    print('2) views.py')
    views_nuevo, n, definidos = procesar_views(app / 'views.py')
    print(f'  {n} líneas de nómina eliminadas (ahora en views_nomina.py)')
    rotas = revisar_urls(app / 'urls.py', definidos)

    if not simular:
        respaldar(app / 'models.py', simular)
        respaldar(app / 'views.py', simular)
        (app / 'models.py').write_text(models_nuevo, encoding='utf-8')
        (app / 'models_nomina_legado.py').write_text(legado, encoding='utf-8')
        (app / 'views.py').write_text(views_nuevo, encoding='utf-8')

    print('3) módulos nuevos')
    for nombre in ('models_nomina.py', 'nomina_motor.py', 'nomina_conceptos.py',
                   'views_nomina.py', 'urls_nomina.py'):
        copiar(AQUI / nombre, app / nombre, simular)
    for init in ('management/__init__.py', 'management/commands/__init__.py'):
        if not (app / init).exists():
            print(f'  + {app / init}')
            if not simular:
                (app / init).parent.mkdir(parents=True, exist_ok=True)
                (app / init).touch()
    for comando in (AQUI / 'management/commands').glob('*.py'):
        copiar(comando, app / 'management/commands' / comando.name, simular)

    print('4) templates y estáticos')
    carpeta = plantillas / 'presupuesto_nomina'
    obsoletos = plantillas.parent / '_nomina_templates_obsoletos'
    for nombre in TEMPLATES_VIEJOS:
        viejo = carpeta / nombre
        if viejo.exists():
            print(f'  → {viejo.name} a {obsoletos}')
            if not simular:
                obsoletos.mkdir(parents=True, exist_ok=True)
                shutil.move(str(viejo), obsoletos / nombre)
    for archivo in (AQUI / 'templates/presupuesto_nomina').iterdir():
        copiar(archivo, carpeta / archivo.name, simular)
    for sub in ('js', 'css'):
        for archivo in (AQUI / 'static' / sub).iterdir():
            copiar(archivo, estaticos / sub / archivo.name, simular)
    calculos = estaticos / 'js/presupuesto_calculos.js'
    if calculos.exists():
        print(f'  → {calculos.name} a {obsoletos} (ya no se usa)')
        if not simular:
            obsoletos.mkdir(parents=True, exist_ok=True)
            shutil.move(str(calculos), obsoletos / calculos.name)

    if rotas:
        print(f'\n⚠ urls.py todavía apunta a {len(rotas)} vistas que ya no existen. '
              'Borra esas rutas y agrega las de urls_nomina.py (ver README):')
        for nombre in rotas:
            print(f'    views.{nombre}')

    print('\n' + ('SIMULACIÓN: no se escribió nada.' if simular else '✔ Listo. Sigue los pasos del README.'))


if __name__ == '__main__':
    main()
