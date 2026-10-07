# Asignación de presupuestos por usuario (tabla presupuesto_asignacion).
#
# Antes, quién podía llenar cada presupuesto estaba escrito en el código
# (SEDE_CONFIG["usuarios_permitidos"], views_nomina y base_comercial). Ahora
# vive en esta tabla y se administra en Ajustes → Asignación de presupuestos.
#
# Para que nadie pierda acceso, aquí se copian esas listas a la tabla: cada
# usuario que YA EXISTE queda asignado a su presupuesto. Los que todavía no
# existen se asignan desde el panel cuando se creen.
#
# Reversible (al revertir se borra la tabla).

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

# Copia congelada de las listas que había en el código (sin los aprobadores
# "admin" y "NICOLAS", que entran a todo sin necesidad de asignación).
ASIGNACIONES_INICIALES = {
    "almacen-tulua": ["JEFEALMACENTULUA", "DBENITEZ"],
    "almacen-buga": ["JEFEALMACENBUGA", "FDUQUE"],
    "almacen-cartago": ["JEFEALMACENCARTAGO", "CHINCAPI"],
    "almacen-cali": ["JEFEALMACENCALI", "LAMAYA"],
    "comunicaciones": ["COMUNICACIONES"],
    "comercial-costos": ["COMERCIALCOSTOS", "EVALENCIA"],
    "contabilidad": ["CONTABILIDAD"],
    "gerencia": ["GERENCIA"],
    "gestion-humana": ["GESTIONHUMANA"],
    "gestion-riesgos": ["GESTIONRIESGOS"],
    "logistica": ["PLOZANO"],
    "servicios-tecnicos": ["SERVICIOSTECNICOS"],
    "salud-ocupacional": ["SALUDOCUPACIONAL"],
    "tecnologia": ["TECNOLOGIA"],
    "nomina": ["PQUINTERO"],
    "comercial": ["AGRAJALE", "EVALENCIA", "SCORTES"],
}


def _usuario(User, username):
    exacto = User.objects.filter(username=username).first()
    if exacto:
        return exacto
    parecidos = list(User.objects.filter(username__iexact=username)[:2])
    return parecidos[0] if len(parecidos) == 1 else None


def sembrar(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    Asignacion = apps.get_model("presupuestoApp", "AsignacionPresupuesto")
    nuevas = []
    for presupuesto, usernames in ASIGNACIONES_INICIALES.items():
        for username in usernames:
            usuario = _usuario(User, username)
            if usuario:
                nuevas.append(Asignacion(
                    usuario=usuario, presupuesto=presupuesto, asignado_por="migración inicial",
                ))
    Asignacion.objects.bulk_create(nuevas, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ("presupuestoApp", "0036_nomina_codcosto_y_confirmacion"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AsignacionPresupuesto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("presupuesto", models.CharField(max_length=40)),
                ("asignado_por", models.CharField(blank=True, default="", max_length=150)),
                ("creado", models.DateTimeField(auto_now_add=True)),
                ("usuario", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="presupuestos_asignados",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "db_table": "presupuesto_asignacion",
                "indexes": [models.Index(fields=["presupuesto"], name="presup_asignacion_clave_idx")],
                "constraints": [
                    models.UniqueConstraint(fields=("usuario", "presupuesto"), name="presup_asignacion_unica"),
                ],
            },
        ),
        migrations.RunPython(sembrar, migrations.RunPython.noop),
    ]
