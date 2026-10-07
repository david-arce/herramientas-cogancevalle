# El presupuesto de gastos del área "Comercial y Costos" pasa a llamarse
# "Comercial y Gastos" y su clave cambia de "comercial-costos" a
# "comercial-gastos" (URL: /presupuesto/area/comercial-gastos/...).
#
# Se actualiza la clave en todas las tablas que la guardan, sin perder datos:
#   presupuesto_area            (borrador, versiones y aprobado)
#   presupuesto_plazo_edicion   (fecha límite configurada)
#   presupuesto_asignacion      (usuarios asignados)
#   cuenta_5_presupuestado      (lo que ya se subió a Cuenta 5)
#
# Reversible.

from django.db import migrations

ANTES, AHORA = "comercial-costos", "comercial-gastos"

CAMPOS = [
    ("PresupuestoArea", "area"),
    ("PlazoEdicionArea", "area"),
    ("AsignacionPresupuesto", "presupuesto"),
    ("Cuenta5Presupuestado", "origen_area"),
]


def _renombrar(apps, desde, hacia):
    for modelo, campo in CAMPOS:
        Modelo = apps.get_model("presupuestoApp", modelo)
        Modelo.objects.filter(**{campo: desde}).update(**{campo: hacia})


def adelante(apps, schema_editor):
    _renombrar(apps, ANTES, AHORA)


def atras(apps, schema_editor):
    _renombrar(apps, AHORA, ANTES)


class Migration(migrations.Migration):

    dependencies = [
        ("presupuestoApp", "0038_agrupacion_cuenta"),
    ]

    operations = [
        migrations.RunPython(adelante, atras),
    ]
