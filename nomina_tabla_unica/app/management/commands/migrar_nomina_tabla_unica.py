"""
Copia los datos de las 34 tablas antiguas de nómina a `presupuesto_nomina`.

    python manage.py migrar_nomina_tabla_unica                 # desde las tablas definitivas
    python manage.py migrar_nomina_tabla_unica --desde auxiliar
    python manage.py migrar_nomina_tabla_unica --simular

Lee las tablas por nombre con SQL directo, así funciona aunque los modelos
viejos ya no existan en models.py (mientras las tablas sigan en la BD).

Qué hace:
  - Conceptos base (sueldos, comisiones, ...): se copian como filas MANUALES,
    con sus valores exactos. No tienen histórico, así que el sistema no los
    recalcula hasta que se use "Cargar desde Conceptos" en cada uno.
  - Conceptos derivados (cesantías, prima, seguridad social, ...): no se copian,
    los calcula el motor a partir de los conceptos base.
"""
from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from ... import nomina_motor as nomina
from ...models_nomina import MESES, PresupuestoNomina

# slug → (tabla definitiva, tabla auxiliar, columna de base)
TABLAS = {
    'sueldos': ('presupuesto_sueldos', 'presupuesto_sueldos_auxiliar', 'salario_base'),
    'comisiones': ('presupuesto_comisiones', 'presupuesto_comisiones_auxiliar', None),
    'horas_extra': ('presupuesto_horas_extra', 'presupuesto_horas_extra_auxiliar', None),
    'medios_transporte': ('presupuesto_medios_transporte', 'presupuesto_medios_transporte_auxiliar', 'base'),
    'ayuda_transporte': ('presupuesto_ayuda_transporte', 'presupuesto_ayuda_transporte_auxiliar', 'base'),
    'bolsa_consumibles': ('presupuesto_bolsa_consumibles', 'presupuesto_bolsa_consumibles_auxiliar', None),
    'auxilio_tbckit': ('presupuesto_auxilio_tbckit', 'presupuesto_auxilio_tbckit_auxiliar', None),
    'auxilio_educacion': ('presupuesto_auxilio_educacion', 'presupuesto_auxilio_educacion_auxiliar', None),
    'aprendiz': ('presupuesto_aprendiz', 'presupuesto_aprendiz_auxiliar', 'salario_base'),
    'bonos_kyrovet': ('presupuesto_bonos_kyrovet', 'presupuesto_bonos_kyrovet_auxiliar', 'base'),
    'auxilio_transporte': ('presupuesto_auxilio_transporte', 'presupuesto_auxilio_transporte_auxiliar', 'base'),
    'cesantias': ('presupuesto_cesantias', 'presupuesto_cesantias_auxiliar', None),
    'prima': ('presupuesto_prima', 'presupuesto_prima_auxiliar', None),
    'vacaciones': ('presupuesto_vacaciones', 'presupuesto_vacaciones_auxiliar', None),
    'intereses_cesantias': ('presupuesto_intereses_cesantias', 'presupuesto_intereses_cesantias_auxiliar', None),
    'bonificaciones': ('presupuesto_bonificaciones', 'presupuesto_bonificaciones_auxiliar', None),
    'bonificaciones_foco': ('presupuesto_bonificaciones_foco', 'presupuesto_bonificaciones_foco_auxiliar', None),
    'seguridad_social': ('presupuesto_seguridad_social', 'presupuesto_seguridad_social_auxiliar', None),
}


def leer_tabla(tabla):
    existentes = set(connection.introspection.table_names())
    if tabla not in existentes:
        return None
    with connection.cursor() as cursor:
        columnas = {c.name for c in connection.introspection.get_table_description(cursor, tabla)}
        cursor.execute(f'SELECT * FROM {connection.ops.quote_name(tabla)} ORDER BY id')
        nombres = [d[0] for d in cursor.description]
        return columnas, [dict(zip(nombres, fila)) for fila in cursor.fetchall()]


class Command(BaseCommand):
    help = 'Pasa los datos de las tablas antiguas de nómina a la tabla única presupuesto_nomina.'

    def add_arguments(self, parser):
        parser.add_argument('--desde', choices=['principal', 'auxiliar'], default='principal',
                            help='Tablas de origen (por defecto las definitivas).')
        parser.add_argument('--copiar-derivados', action='store_true',   # en desuso
                            help='(en desuso) los conceptos calculados se rehacen siempre.')
        parser.add_argument('--simular', action='store_true', help='Solo muestra lo que haría.')

    def handle(self, *args, **opciones):
        indice = 0 if opciones['desde'] == 'principal' else 1
        if opciones['copiar_derivados']:
            self.stdout.write(self.style.WARNING(
                '  --copiar-derivados ya no tiene efecto: los conceptos calculados '
                '(cesantías, prima, seguridad social…) se recalculan siempre.'))

        if PresupuestoNomina.objects.exists() and not opciones['simular']:
            raise CommandError('presupuesto_nomina ya tiene datos. Vacíala antes de migrar '
                               '(PresupuestoNomina.objects.all().delete()).')

        nuevas, conteo = [], Counter()
        for slug, tablas in TABLAS.items():
            concepto = nomina.CONCEPTOS[slug]
            if concepto.derivado:
                continue     # los conceptos calculados se rehacen con el motor
            leido = leer_tabla(tablas[indice])
            if leido is None:
                self.stdout.write(self.style.WARNING(f'  {tablas[indice]}: no existe, se omite'))
                continue
            columnas, filas = leido
            for fila in filas:
                obj = PresupuestoNomina(
                    tipo=slug, origen=nomina.MANUAL,
                    cedula=nomina.cedula_normalizada(fila.get('cedula')),
                    nombre=nomina.texto(fila.get('nombre')),
                    centro=nomina.texto(fila.get('centro')),
                    area=nomina.texto(fila.get('area')),
                    cargo=nomina.texto(fila.get('cargo')),
                    concepto=nomina.texto(fila.get('concepto')),
                    base=int(round(nomina.numero(fila.get(tablas[2])))) if tablas[2] in columnas else 0,
                    actualizado_por='migración',
                )
                nomina.fijar_meses(obj, {m: nomina.numero(fila.get(m)) for m in MESES})
                nuevas.append(obj)
            conteo[slug] = len(filas)
            self.stdout.write(f'  {tablas[indice]}: {len(filas)} filas → {slug}')

        if opciones['simular']:
            self.stdout.write(self.style.NOTICE(f'Simulación: se crearían {len(nuevas)} filas.'))
            return

        PresupuestoNomina.objects.bulk_create(nuevas, batch_size=1000)
        self.stdout.write(self.style.SUCCESS(f'{len(nuevas)} filas copiadas.'))

        self.stdout.write('Regenerando conceptos derivados…')
        nomina.recalcular_todo()
        for fila in nomina.resumen():
            self.stdout.write(f"  {fila['etiqueta']:<42} {fila['filas']:>6} filas  "
                              f"{fila['manuales']:>6} manuales  total {fila['total']:>18,}")
        self.stdout.write(self.style.SUCCESS('Listo.'))
