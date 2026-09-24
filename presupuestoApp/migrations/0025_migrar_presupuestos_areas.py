# Copia los datos de las 42 tablas antiguas de presupuesto por área a la tabla
# única `presupuesto_area`, y VERIFICA la copia (cantidad de filas y suma de
# cada mes + total, tabla por tabla). Si algo no cuadra lanza un error y, como
# la migración es atómica, no queda nada a medias.
#
# No borra las tablas antiguas: eso se hace después, en un paso aparte.

from django.db import migrations
from django.db.models import Count, Sum

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
CAMPOS = [
    "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta",
    "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor",
    *MESES, "total", "comentario",
]
CAMPOS_VERIFICADOS = [*MESES, "total"]

# clave del área (la misma de SEDE_CONFIG / URLs) -> nombre base de las tablas viejas
TABLAS_POR_AREA = {
    "almacen-tulua": "presupuesto_almacen_tulua",
    "almacen-buga": "presupuesto_almacen_buga",
    "almacen-cartago": "presupuesto_almacen_cartago",
    "almacen-cali": "presupuesto_almacen_cali",
    "comunicaciones": "presupuesto_comunicaciones",
    "comercial-costos": "presupuesto_comercial_costos",
    "contabilidad": "presupuesto_contabilidad",
    "gerencia": "presupuesto_gerencia",
    "gestion-humana": "presupuesto_gh",
    "gestion-riesgos": "presupuesto_gestion_riesgos",
    "logistica": "presupuesto_logistica",
    "servicios-tecnicos": "presupuesto_servicios_tecnicos",
    "salud-ocupacional": "presupuesto_ocupacional",
    "tecnologia": "presupuesto_tecnologia",
}
# (etapa, sufijo de la tabla vieja, ¿tiene version/fecha?)
ETAPAS = (
    ("proyectado", "", True),
    ("auxiliar", "_auxiliar", False),
    ("aprobado", "_aprobado", True),
)


def _modelo_nuevo(apps):
    # Se busca por tabla para no depender del nombre de la app.
    return next(m for m in apps.get_models() if m._meta.db_table == "presupuesto_area")


def copiar_presupuestos(apps, schema_editor):
    Nuevo = _modelo_nuevo(apps)
    conn = schema_editor.connection
    qn = conn.ops.quote_name
    existentes = set(conn.introspection.table_names())

    if Nuevo.objects.exists():
        raise RuntimeError("presupuesto_area ya tiene datos: la copia no se ejecuta dos veces.")

    for area, base in TABLAS_POR_AREA.items():
        for etapa, sufijo, versionado in ETAPAS:
            tabla = base + sufijo
            if tabla not in existentes:
                print(f"  ⚠ {tabla}: no existe en la base de datos, se omite")
                continue

            columnas = CAMPOS + (["version", "fecha"] if versionado else [])
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT {', '.join(qn(c) for c in columnas)} FROM {qn(tabla)} ORDER BY {qn('id')}"
                )
                filas = [dict(zip(columnas, fila)) for fila in cur.fetchall()]

            # "guardar_presupuesto_consolidado" dejaba filas aprobadas con
            # version NULL. Se les asigna la última versión (o 1) para que
            # sigan siendo las que se muestran.
            if etapa == "aprobado":
                maxima = max((f["version"] for f in filas if f["version"] is not None), default=None)
                for f in filas:
                    if f["version"] is None:
                        f["version"] = maxima or 1

            Nuevo.objects.bulk_create(
                [Nuevo(area=area, etapa=etapa, **f) for f in filas], batch_size=1000
            )

            # ── Verificación: misma cantidad de filas y mismas sumas ──
            with conn.cursor() as cur:
                sumas = ", ".join(f"SUM({qn(c)})" for c in CAMPOS_VERIFICADOS)
                cur.execute(f"SELECT COUNT(*), {sumas} FROM {qn(tabla)}")
                origen = cur.fetchone()
            copiado = Nuevo.objects.filter(area=area, etapa=etapa).aggregate(
                n=Count("id"), **{c: Sum(c) for c in CAMPOS_VERIFICADOS}
            )
            if origen[0] != copiado["n"]:
                raise RuntimeError(f"{tabla}: {origen[0]} filas en origen, {copiado['n']} copiadas")
            for campo, valor_origen in zip(CAMPOS_VERIFICADOS, origen[1:]):
                if (valor_origen or 0) != (copiado[campo] or 0):
                    raise RuntimeError(
                        f"{tabla}.{campo}: suma origen {valor_origen} ≠ copiada {copiado[campo]}"
                    )
            print(f"  ✔ {tabla:45s} → {area}/{etapa}: {copiado['n']} filas")


def revertir(apps, schema_editor):
    # Las tablas antiguas siguen intactas en este punto; basta con vaciar la nueva.
    _modelo_nuevo(apps).objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('presupuestoApp', '0024_presupuestoarea_delete_presupuestoaprendiz_and_more'),
    ]

    operations = [
        migrations.RunPython(copiar_presupuestos, revertir),
    ]