"""
Pasa los datos de las dos tablas anteriores a `conceptos_nomina`, con su año.

    python manage.py migrar_conceptos_nomina --anio 2026 --simular
    python manage.py migrar_conceptos_nomina --anio 2026
    python manage.py migrar_conceptos_nomina --anio 2026 --anio-educacion 2025
    python manage.py migrar_conceptos_nomina --anio 2026 --fecha-corte 2026-08-31

  conceptos_fijos_y_variables → año --anio
  concepto_auxilio_educacion  → año --anio-educacion (por defecto --anio menos 1)

Lee las tablas por nombre con SQL directo, así funciona aunque los modelos
viejos (ConceptosFijosYVariables, ConceptoAuxilioEducacion) ya se hayan
quitado de models.py. Esas tablas no se modifican ni se borran.
Los datos que ya existan en conceptos_nomina para esos años se reemplazan.
"""
import datetime as dt

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from ...models_nomina import MESES, ConceptosNomina
from ...nomina_conceptos import CAMPOS_CODIGO, CAMPOS_TEXTO, _cedula, _codigo, _entero, _texto, meses_detectados

ORIGENES = [
    ('conceptos_fijos_y_variables', 'anio'),
    ('concepto_auxilio_educacion', 'anio_educacion'),
]


def leer_tabla(tabla):
    if tabla not in set(connection.introspection.table_names()):
        return None
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT * FROM {connection.ops.quote_name(tabla)}')
        nombres = [d[0].lower() for d in cursor.description]
        return [dict(zip(nombres, fila)) for fila in cursor.fetchall()]


class Command(BaseCommand):
    help = 'Copia conceptos_fijos_y_variables y concepto_auxilio_educacion a conceptos_nomina.'

    def add_arguments(self, parser):
        parser.add_argument('--anio', type=int, required=True,
                            help='Año de los datos de conceptos_fijos_y_variables.')
        parser.add_argument('--anio-educacion', type=int,
                            help='Año de concepto_auxilio_educacion (por defecto --anio - 1).')
        parser.add_argument('--fecha-corte', help='AAAA-MM-DD: hasta dónde llegan los datos de --anio.')
        parser.add_argument('--simular', action='store_true', help='Solo muestra lo que haría.')

    def handle(self, *args, **op):
        anios = {'anio': op['anio'], 'anio_educacion': op['anio_educacion'] or op['anio'] - 1}
        corte = None
        if op['fecha_corte']:
            try:
                corte = dt.date.fromisoformat(op['fecha_corte'])
            except ValueError:
                raise CommandError('--fecha-corte debe tener el formato AAAA-MM-DD')

        nuevos = []
        for tabla, clave in ORIGENES:
            filas = leer_tabla(tabla)
            anio = anios[clave]
            if filas is None:
                self.stdout.write(self.style.WARNING(f'  {tabla}: no existe, se omite'))
                continue
            for f in filas:
                nuevos.append(ConceptosNomina(
                    anio=anio,
                    fecha_corte=corte if clave == 'anio' else None,
                    cedula=_cedula(f.get('cedula')),
                    arlporc=f.get('arlporc'),
                    concepto_f=_entero(f.get('concepto_f')),
                    archivo=f'(migrado de {tabla})',
                    cargado_por='migracion',
                    **{c: (_codigo if c in CAMPOS_CODIGO else _texto)(f.get(c)) for c in CAMPOS_TEXTO},
                    **{m: _entero(f.get(m)) for m in MESES},
                ))
                nuevos[-1].total = sum(getattr(nuevos[-1], m) for m in MESES)
            self.stdout.write(f'  {tabla:<30} → año {anio}: {len(filas)} filas')

        if op['simular']:
            self.stdout.write(self.style.WARNING('Simulación: no se guardó nada.'))
            return

        with transaction.atomic():
            borradas, _ = ConceptosNomina.objects.filter(anio__in=set(anios.values())).delete()
            ConceptosNomina.objects.bulk_create(nuevos, batch_size=2000)
        if borradas:
            self.stdout.write(f'  Se reemplazaron {borradas} filas que ya existían para esos años.')
        for anio in sorted(set(anios.values())):
            n = meses_detectados(anio)
            self.stdout.write(f'  {anio}: datos hasta {MESES[n - 1] if n else "—"} ({n} meses)')
        self.stdout.write(self.style.SUCCESS(f'Listo: {len(nuevos)} filas en conceptos_nomina ✅'))
