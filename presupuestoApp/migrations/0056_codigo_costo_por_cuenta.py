# Presupuesto por área: las cuentas que empiezan por 5105 van al código de costo
# 0101 y las que empiezan por 5405 al 020201, sin importar el centro. Ver
# CODIGO_COSTO_POR_CUENTA en models_presupuesto.py.
#
# Esta migración corrige lo que ya estaba guardado. SOLO cambia la columna del
# código de costo (mcnccosto) de esas cuentas. No toca valores, fechas,
# versiones, aprobaciones ni ningún otro campo, así que los estados ("Subido a
# Cuenta 5", versión aprobada, totales) siguen igual.
#
# Qué se corrige:
#   - presupuesto_area: borrador (auxiliar), versiones de trabajo (proyectado)
#     y versiones aprobadas (aprobado).
#   - cuenta_5_presupuestado: solo lo que subieron las áreas.
#
# Qué NO se toca:
#   - La copia de auditoría de lo que envió el área (etapa "preaprobado").
#   - Lo cargado por Excel en Cuenta 5 presupuestado (sin origen_area) y lo
#     subido desde nómina (origen_area = "nomina"), que trae su propio código.
#
# Revertir esta migración no cambia ningún dato.

from django.db import migrations
from django.db.models import CharField
from django.db.models.functions import Cast, Trim

CODIGO_COSTO_POR_CUENTA = {"5105": "0101", "5405": "020201"}
ETAPAS_A_CORREGIR = ("auxiliar", "proyectado", "aprobado")


def corregir(apps, schema_editor):
    PresupuestoArea = apps.get_model("presupuestoApp", "PresupuestoArea")
    Cuenta5Presupuestado = apps.get_model("presupuestoApp", "Cuenta5Presupuestado")

    areas = (PresupuestoArea.objects.filter(etapa__in=ETAPAS_A_CORREGIR)
             .annotate(_cuenta=Trim(Cast("mcncuenta", CharField()))))
    subidos = (Cuenta5Presupuestado.objects.filter(origen_area__isnull=False)
               .exclude(origen_area__in=["", "nomina"])
               .annotate(_cuenta=Trim("mcncuenta")))
    total_area = total_c5 = 0
    for prefijo, codigo in CODIGO_COSTO_POR_CUENTA.items():
        # update() por id: solo escribe mcnccosto, nada más.
        ids = list(areas.filter(_cuenta__startswith=prefijo).exclude(mcnccosto=codigo)
                   .values_list("id", flat=True))
        total_area += PresupuestoArea.objects.filter(id__in=ids).update(mcnccosto=codigo)
        ids = list(subidos.filter(_cuenta__startswith=prefijo).exclude(mcnccosto=codigo)
                   .values_list("id", flat=True))
        total_c5 += Cuenta5Presupuestado.objects.filter(id__in=ids).update(mcnccosto=codigo)
    if total_area or total_c5:
        print(f"\n  5105 -> 0101 / 5405 -> 020201: {total_area} registros de presupuesto_area, "
              f"{total_c5} de cuenta_5_presupuestado")


class Migration(migrations.Migration):

    dependencies = [
        ("presupuestoApp", "0055_ajustes_presupuestado"),
    ]

    operations = [
        migrations.RunPython(corregir, migrations.RunPython.noop),
    ]
