# 1. presupuesto_nomina recibe la columna codcosto (CODCOSTO de conceptos_nomina,
#    según el área / NOMCOSTO de cada fila, igual que la cuenta). La vista
#    presupuesto_nomina_lineas y sus disparadores se rehacen para incluirla y
#    las filas que ya existen la toman de conceptos_nomina.
# 2. configuracion_nomina recibe la confirmación de "presupuesto listo"
#    (listo, listo_por, listo_en). Sin confirmar no se sube a Cuenta 5.
#
# Reversible.

import unicodedata
from collections import Counter, defaultdict

from django.db import migrations, models

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
CAMPOS_ANTES = [
    "tipo", "cedula", "nombre", "centro", "area", "cargo", "concepto", "cuenta",
    "base", "factor", "historico", "origen", "clave", "centro_origen", "area_origen",
    "excluir_de", "creado", "actualizado", "actualizado_por",
]
CAMPOS_AHORA = [*CAMPOS_ANTES, "codcosto"]


def _q(campos):
    return ", ".join(f'"{c}"' for c in campos)


def sql_vista(campos):
    """Vista horizontal + disparadores (misma lógica que la migración 0034)."""
    new = ", ".join(f'NEW."{c}"' for c in campos)
    asignar = ", ".join(f'"{c}" = NEW."{c}"' for c in campos)
    valor_mes = "CASE {mes} " + " ".join(f'WHEN {i} THEN NEW."{m}"' for i, m in enumerate(MESES, 1)) + " END"
    total = " + ".join(f'COALESCE(NEW."{m}", 0)' for m in MESES)
    return f"""
CREATE VIEW presupuesto_nomina_lineas AS
SELECT m.linea AS id, {", ".join(f'm."{c}"' for c in campos)},
       EXTRACT(YEAR FROM m.fecha)::integer AS anio,
       {", ".join(f'v."{mes}"' for mes in MESES)}, v.total
FROM presupuesto_nomina m
CROSS JOIN LATERAL (
    SELECT {", ".join(
        f'COALESCE(SUM(x.valor) FILTER (WHERE EXTRACT(MONTH FROM x.fecha) = {i}), 0)::bigint AS "{mes}"'
        for i, mes in enumerate(MESES, 1))},
           COALESCE(SUM(x.valor), 0)::bigint AS total
    FROM presupuesto_nomina x WHERE x.linea = m.linea
) v
WHERE EXTRACT(MONTH FROM m.fecha) = 1;

CREATE FUNCTION presupuesto_nomina_lineas_insertar() RETURNS trigger AS $$
BEGIN
    IF NEW.id IS NULL THEN
        NEW.id := nextval('presupuesto_nomina_linea_seq');
    END IF;
    IF NEW.anio IS NULL THEN
        NEW.anio := EXTRACT(YEAR FROM (now() AT TIME ZONE 'America/Bogota'))::integer + 1;
    END IF;
    INSERT INTO presupuesto_nomina ("linea", {_q(campos)}, "fecha", "valor")
    SELECT NEW.id, {new}, make_date(NEW.anio, mes, 1),
           COALESCE({valor_mes.format(mes="mes")}, 0)
    FROM generate_series(1, 12) AS mes;
    NEW.total := {total};
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE FUNCTION presupuesto_nomina_lineas_actualizar() RETURNS trigger AS $$
BEGIN
    UPDATE presupuesto_nomina SET
        {asignar},
        "fecha" = make_date(COALESCE(NEW.anio, EXTRACT(YEAR FROM fecha)::integer),
                            EXTRACT(MONTH FROM fecha)::integer, 1),
        "valor" = COALESCE({valor_mes.format(mes="EXTRACT(MONTH FROM fecha)::integer")}, 0)
    WHERE linea = OLD.id;
    NEW.id := OLD.id;
    NEW.total := {total};
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE FUNCTION presupuesto_nomina_lineas_borrar() RETURNS trigger AS $$
BEGIN
    DELETE FROM presupuesto_nomina WHERE linea = OLD.id;
    RETURN OLD;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER presupuesto_nomina_lineas_ins INSTEAD OF INSERT ON presupuesto_nomina_lineas
    FOR EACH ROW EXECUTE FUNCTION presupuesto_nomina_lineas_insertar();
CREATE TRIGGER presupuesto_nomina_lineas_upd INSTEAD OF UPDATE ON presupuesto_nomina_lineas
    FOR EACH ROW EXECUTE FUNCTION presupuesto_nomina_lineas_actualizar();
CREATE TRIGGER presupuesto_nomina_lineas_del INSTEAD OF DELETE ON presupuesto_nomina_lineas
    FOR EACH ROW EXECUTE FUNCTION presupuesto_nomina_lineas_borrar();
"""


BORRAR_VISTA = """
DROP VIEW IF EXISTS presupuesto_nomina_lineas;
DROP FUNCTION IF EXISTS presupuesto_nomina_lineas_insertar();
DROP FUNCTION IF EXISTS presupuesto_nomina_lineas_actualizar();
DROP FUNCTION IF EXISTS presupuesto_nomina_lineas_borrar();
"""


def _clave_area(valor):
    valor = unicodedata.normalize("NFKD", str(valor or "").strip()).encode("ascii", "ignore").decode()
    return " ".join(valor.upper().split())


def llenar_codcosto(apps, schema_editor):
    """CODCOSTO de cada fila según su área, con el mismo criterio del motor:
    el más frecuente de cada NOMCOSTO en el año más reciente de conceptos_nomina."""
    Conceptos = apps.get_model("presupuestoApp", "ConceptosNomina")
    Mes = apps.get_model("presupuestoApp", "PresupuestoNominaMes")
    qs = Conceptos.objects.exclude(codcosto="").exclude(nomcosto="")
    anio = qs.order_by("-anio").values_list("anio", flat=True).first()
    if anio is None:
        return
    conteo = defaultdict(Counter)
    for nomcosto, codcosto in qs.filter(anio=anio).values_list("nomcosto", "codcosto"):
        conteo[_clave_area(nomcosto)][str(codcosto).strip()] += 1
    mapa = {area: c.most_common(1)[0][0] for area, c in conteo.items()}
    areas = defaultdict(list)
    for area in Mes.objects.exclude(area="").values_list("area", flat=True).distinct():
        codcosto = mapa.get(_clave_area(area))
        if codcosto:
            areas[codcosto].append(area)
    for codcosto, lista in areas.items():
        Mes.objects.filter(area__in=lista).update(codcosto=codcosto)


class Migration(migrations.Migration):

    dependencies = [
        ('presupuestoApp', '0035_borrar_presupuesto_nomina_respaldo'),
    ]

    operations = [
        # La vista depende de las columnas de la tabla: se quita y se rehace.
        migrations.RunSQL(BORRAR_VISTA, sql_vista(CAMPOS_ANTES)),
        migrations.AddField(
            model_name='presupuestonominames',
            name='codcosto',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='presupuestonomina',
                    name='codcosto',
                    field=models.CharField(blank=True, default='', max_length=30),
                ),
            ],
            database_operations=[],
        ),
        migrations.RunSQL(sql_vista(CAMPOS_AHORA), BORRAR_VISTA),
        migrations.RunPython(llenar_codcosto, migrations.RunPython.noop),

        migrations.AddField(
            model_name='configuracionnomina',
            name='listo',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='configuracionnomina',
            name='listo_por',
            field=models.CharField(blank=True, default='', max_length=150),
        ),
        migrations.AddField(
            model_name='configuracionnomina',
            name='listo_en',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
