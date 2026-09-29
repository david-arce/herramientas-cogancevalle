# presupuesto_area pasa de HORIZONTAL (una columna por mes) a VERTICAL (un
# registro por línea y mes, con su fecha), y se renombran columnas:
#
#   centro_tra -> mcnzona        cuenta         -> mcncuenta
#   nombre_cen -> zonnombre      cuenta_mayor   -> ctanombre
#   codcosto   -> mcnccosto      detalle_cuenta -> mcndetalle
#   fecha      -> fecha_version  (la fecha de subida/aprobación de la versión;
#                                 "fecha" pasa a ser el mes presupuestado)
#
# Cada fila existente se convierte en 12 registros (enero..diciembre) con la
# misma "linea". La copia se VERIFICA por área/etapa/versión (cantidad de
# líneas y suma de cada mes); si algo no cuadra lanza un error y, como la
# migración es atómica, no queda nada a medias. Es reversible.
#
# Año de los meses (automático, sin datos manuales): el año siguiente a
# fecha_version (una versión subida en el año N es el presupuesto N+1) y, para
# el borrador sin fecha, el año siguiente al actual.

import datetime

from django.db import migrations, models
from django.db.models import Count, Sum

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
CAMPOS_LINEA = [
    "mcnzona", "zonnombre", "mcnccosto", "responsable", "mcncuenta",
    "ctanombre", "mcndetalle", "sede_distribucion", "proveedor", "comentario",
]
RENOMBRES = [
    ("fecha", "fecha_version"),
    ("centro_tra", "mcnzona"),
    ("nombre_cen", "zonnombre"),
    ("codcosto", "mcnccosto"),
    ("cuenta", "mcncuenta"),
    ("cuenta_mayor", "ctanombre"),
    ("detalle_cuenta", "mcndetalle"),
]


def _anio(fecha_version):
    if fecha_version:
        return fecha_version.year + 1
    return datetime.date.today().year + 1


def _grupos(qs):
    return qs.values("area", "etapa", "version").distinct().order_by("area", "etapa", "version")


def horizontal_a_vertical(apps, schema_editor):
    PresupuestoArea = apps.get_model("presupuestoApp", "PresupuestoArea")
    horizontales = PresupuestoArea.objects.filter(fecha__isnull=True)   # filas aún sin convertir

    for g in _grupos(horizontales):
        filas = list(horizontales.filter(**g).order_by("id"))
        esperado = {m: sum(getattr(f, m) or 0 for f in filas) for m in MESES}

        nuevos = []
        for linea, f in enumerate(filas, start=1):
            anio = _anio(f.fecha_version)
            comunes = {c: getattr(f, c) for c in CAMPOS_LINEA}
            for numero, mes in enumerate(MESES, start=1):
                nuevos.append(PresupuestoArea(
                    area=f.area, etapa=f.etapa, version=f.version, fecha_version=f.fecha_version,
                    linea=linea, fecha=datetime.date(anio, numero, 1), valor=getattr(f, mes) or 0,
                    **comunes,
                ))
        PresupuestoArea.objects.bulk_create(nuevos, batch_size=1000)
        PresupuestoArea.objects.filter(id__in=[f.id for f in filas]).delete()

        # ── Verificación ──
        convertidos = PresupuestoArea.objects.filter(**g, fecha__isnull=False)
        n_lineas = convertidos.aggregate(n=Count("linea", distinct=True))["n"]
        if n_lineas != len(filas) or convertidos.count() != 12 * len(filas):
            raise RuntimeError(f"{g}: {len(filas)} filas → {n_lineas} líneas / {convertidos.count()} registros")
        for numero, mes in enumerate(MESES, start=1):
            obtenido = convertidos.filter(fecha__month=numero).aggregate(s=Sum("valor"))["s"] or 0
            if obtenido != esperado[mes]:
                raise RuntimeError(f"{g}.{mes}: suma original {esperado[mes]} ≠ convertida {obtenido}")
        print(f"  ✔ {g['area']}/{g['etapa']}/v{g['version']}: {len(filas)} filas → {len(nuevos)} registros")


def vertical_a_horizontal(apps, schema_editor):
    PresupuestoArea = apps.get_model("presupuestoApp", "PresupuestoArea")
    verticales = PresupuestoArea.objects.filter(fecha__isnull=False)

    for g in _grupos(verticales):
        lineas = {}
        for r in verticales.filter(**g).order_by("linea", "fecha", "id"):
            fila = lineas.setdefault(r.linea, {
                "area": r.area, "etapa": r.etapa, "version": r.version,
                "fecha_version": r.fecha_version,
                **{c: getattr(r, c) for c in CAMPOS_LINEA},
                **{m: 0 for m in MESES},
            })
            fila[MESES[r.fecha.month - 1]] = r.valor or 0
        nuevos = []
        for fila in lineas.values():
            fila["total"] = sum(fila[m] for m in MESES)
            nuevos.append(PresupuestoArea(**fila))
        verticales.filter(**g).delete()
        PresupuestoArea.objects.bulk_create(nuevos, batch_size=1000)


class Migration(migrations.Migration):

    dependencies = [
        ('presupuestoApp', '0029_drop_tablas_legacy'),
    ]

    operations = [
        *[
            migrations.RenameField(model_name="presupuestoarea", old_name=viejo, new_name=nuevo)
            for viejo, nuevo in RENOMBRES
        ],
        migrations.AddField(
            model_name="presupuestoarea", name="linea",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="presupuestoarea", name="fecha",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="presupuestoarea", name="valor",
            field=models.BigIntegerField(blank=True, null=True),
        ),

        migrations.RunPython(horizontal_a_vertical, vertical_a_horizontal),

        *[
            migrations.RemoveField(model_name="presupuestoarea", name=campo)
            for campo in [*MESES, "total"]
        ],
        migrations.AlterField(
            model_name="presupuestoarea", name="linea",
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterField(
            model_name="presupuestoarea", name="fecha",
            field=models.DateField(),
        ),
        migrations.AlterField(
            model_name="presupuestoarea", name="valor",
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddIndex(
            model_name="presupuestoarea",
            index=models.Index(fields=["fecha"], name="presup_area_fecha_idx"),
        ),
    ]
