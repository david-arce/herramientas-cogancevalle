# Los segmentos del comercial se guardan tal como vienen en el Excel.
#
# Antes la importación renombraba CLIENTE -> CLIENTES y PRODUCCION -> PRODUCTOR.
# Ya no (ver _limpiar_clase_cliente en views.py), así que los datos guardados
# se pasan a los nombres del Excel; si no, los meses viejos quedarían como
# "CLIENTES" y los nuevos como "CLIENTE" (dos segmentos para lo mismo) y los
# crecimientos guardados dejarían de coincidir.
#
# SOLO cambia el nombre del segmento, en estas columnas:
#   bd_ventas_comercial.nombre_clase_cliente
#   PresupuestoComercial.nombre_clase_cliente (crecimientos)
#   PresupuestoCentroSegmento{Ventas,Costos}.segmento
#   PresupuestoCentroSegLinea{Ventas,Costos}.segmento
# Valores, meses, centros, líneas y cualquier otro segmento quedan igual.
#
# Reversible: al revertir vuelven a CLIENTES / PRODUCTOR.

from django.db import migrations
from django.db.models.functions import Trim, Upper

RENOMBRAR = {"CLIENTES": "CLIENTE", "PRODUCTOR": "PRODUCCION"}

TABLAS = [
    ("BdVentasComercial", "nombre_clase_cliente"),
    ("PresupuestoComercial", "nombre_clase_cliente"),
    ("PresupuestoCentroSegmentoVentas", "segmento"),
    ("PresupuestoCentroSegmentoCostos", "segmento"),
    ("PresupuestoCentroSegLineaVentas", "segmento"),
    ("PresupuestoCentroSegLineaCostos", "segmento"),
]


def _renombrar(apps, mapa):
    resumen = []
    for modelo, campo in TABLAS:
        Modelo = apps.get_model("presupuestoApp", modelo)
        for viejo, nuevo in mapa.items():
            n = (Modelo.objects.annotate(_seg=Upper(Trim(campo)))
                 .filter(_seg=viejo).update(**{campo: nuevo}))
            if n:
                resumen.append(f"{modelo}: {n} {viejo} -> {nuevo}")
    if resumen:
        print("\n  " + "\n  ".join(resumen))


def adelante(apps, schema_editor):
    _renombrar(apps, RENOMBRAR)


def atras(apps, schema_editor):
    _renombrar(apps, {nuevo: viejo for viejo, nuevo in RENOMBRAR.items()})


class Migration(migrations.Migration):

    dependencies = [
        ("presupuestoApp", "0050_codigo_costo_buga_020202"),
    ]

    operations = [
        migrations.RunPython(adelante, atras),
    ]
