# ALMACEN BUGA pasa a tener código de costo 020202 (antes 020200), igual que
# los demás almacenes. Ver CODIGO_COSTO_POR_CENTRO en models_presupuesto.py.
#
# Esta migración corrige lo que ya estaba guardado. SOLO cambia la columna del
# código de costo (mcnccosto) de "020200" a "020202" en las filas cuyo centro
# (zonnombre) es ALMACEN BUGA. No toca valores, fechas, versiones,
# aprobaciones ni ningún otro campo, así que los estados ("Subido a Cuenta 5",
# versión aprobada, totales) siguen igual.
#
# Qué se corrige:
#   - presupuesto_area: borrador del área (auxiliar), versiones de trabajo
#     (proyectado) y versiones aprobadas (aprobado).
#   - cuenta_5_presupuestado: solo lo que subieron las áreas.
#
# Qué NO se toca:
#   - La copia de auditoría de lo que envió el área (etapa "preaprobado"):
#     es intocable a propósito.
#   - Lo cargado por Excel en Cuenta 5 presupuestado (sin origen_area) y lo
#     subido desde nómina (origen_area = "nomina"), que trae su propio código.
#   - Filas de Buga con un código distinto de 020200 y filas de otros centros.
#
# Revertir esta migración no cambia ningún dato (no hay forma segura de saber
# qué filas tenían 020200 antes).

from django.db import migrations
from django.db.models.functions import Trim, Upper

CENTRO = "ALMACEN BUGA"
CODIGO_VIEJO = "020200"
CODIGO_NUEVO = "020202"
ETAPAS_A_CORREGIR = ("auxiliar", "proyectado", "aprobado")


def _filas_de_buga(queryset):
    return (queryset
            .annotate(_centro=Upper(Trim("zonnombre")), _codigo=Trim("mcnccosto"))
            .filter(_centro=CENTRO, _codigo=CODIGO_VIEJO))


def corregir_codigo_buga(apps, schema_editor):
    PresupuestoArea = apps.get_model("presupuestoApp", "PresupuestoArea")
    Cuenta5Presupuestado = apps.get_model("presupuestoApp", "Cuenta5Presupuestado")

    ids_area = list(_filas_de_buga(
        PresupuestoArea.objects.filter(etapa__in=ETAPAS_A_CORREGIR)
    ).values_list("id", flat=True))
    ids_c5 = list(_filas_de_buga(
        Cuenta5Presupuestado.objects.filter(origen_area__isnull=False).exclude(origen_area__in=["", "nomina"])
    ).values_list("id", flat=True))

    # update() por id: solo escribe mcnccosto, nada más.
    n_area = PresupuestoArea.objects.filter(id__in=ids_area).update(mcnccosto=CODIGO_NUEVO)
    n_c5 = Cuenta5Presupuestado.objects.filter(id__in=ids_c5).update(mcnccosto=CODIGO_NUEVO)
    if n_area or n_c5:
        print(f"\n  ALMACEN BUGA {CODIGO_VIEJO} -> {CODIGO_NUEVO}: "
              f"{n_area} registros de presupuesto_area, {n_c5} de cuenta_5_presupuestado")


class Migration(migrations.Migration):

    dependencies = [
        ("presupuestoApp", "0049_arl_cargo_nomina"),
    ]

    operations = [
        migrations.RunPython(corregir_codigo_buga, migrations.RunPython.noop),
    ]
