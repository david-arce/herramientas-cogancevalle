"""Destinos de nómina: uno por área (el reparto sale de la distribución de nómina).

Antes cada persona tenía sus destinos con un porcentaje escrito a mano. Ahora el
reparto lo da la distribución de nómina (que ya parte las filas por centro/área)
y aquí solo se elige el destino de cada área con centro de costo 020301.

Las asignaciones que ya existían se conservan cuando son inequívocas: un solo
destino al 100 % y la persona con UNA sola área en 020301 → ese destino para
esa área. Las demás (repartos a mano) se quitan: esas personas quedan como
pendientes en Ajustes → Destinos de nómina para elegir el destino de cada área.
"""
import unicodedata
from collections import defaultdict

from django.db import migrations, models


def _codcosto(valor):
    texto = str(valor or "").strip()
    return texto.zfill(6) if texto.isdigit() else texto


def _clave_area(area):
    texto = unicodedata.normalize("NFKD", str(area or "")).encode("ascii", "ignore").decode()
    return " ".join(texto.upper().split())


def _clave_persona(cedula, nombre=""):
    cedula = str(cedula or "").strip()
    if cedula.endswith(".0"):
        cedula = cedula[:-2]
    return cedula or "SIN CEDULA: " + " ".join(str(nombre or "").upper().split())


def pasar_a_areas(apps, schema_editor):
    Destino = apps.get_model("presupuestoApp", "DestinoNomina")
    Mes = apps.get_model("presupuestoApp", "PresupuestoNominaMes")
    if not Destino.objects.exists():
        return
    areas = defaultdict(set)
    for cedula, nombre, area, codcosto in (Mes.objects.filter(codcosto__contains="20301")
                                           .exclude(valor=0).exclude(cuenta="")
                                           .values_list("cedula", "nombre", "area", "codcosto")):
        if _codcosto(codcosto) == "020301":
            areas[_clave_persona(cedula, nombre)].add(_clave_area(area))

    por_persona = defaultdict(list)
    for d in Destino.objects.all():
        por_persona[d.persona].append(d)
    conservadas = quitadas = 0
    for persona, filas in por_persona.items():
        suyas = areas.get(persona, set())
        if len(filas) == 1 and abs(filas[0].porcentaje - 100) < 0.01 and len(suyas) == 1:
            filas[0].area = next(iter(suyas))
            filas[0].save(update_fields=["area"])
            conservadas += 1
        else:
            Destino.objects.filter(id__in=[f.id for f in filas]).delete()
            quitadas += len(filas)
    if conservadas or quitadas:
        print(f"\n  Destinos de nómina: {conservadas} conservado(s) por área, {quitadas} quitado(s) "
              f"(esas personas quedan pendientes en Ajustes → Destinos de nómina)")


class Migration(migrations.Migration):

    dependencies = [
        ("presupuestoApp", "0053_destino_nomina_porcentaje"),
    ]

    operations = [
        migrations.AddField(
            model_name="destinonomina",
            name="area",
            field=models.CharField(default="", max_length=150),
        ),
        migrations.RemoveConstraint(
            model_name="destinonomina",
            name="destino_nomina_persona_destino_uniq",
        ),
        migrations.RunPython(pasar_a_areas, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="destinonomina",
            name="porcentaje",
        ),
        migrations.AddConstraint(
            model_name="destinonomina",
            constraint=models.UniqueConstraint(fields=("persona", "area"), name="destino_nomina_persona_area_uniq"),
        ),
    ]
