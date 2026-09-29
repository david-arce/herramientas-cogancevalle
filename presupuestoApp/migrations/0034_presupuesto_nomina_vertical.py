# presupuesto_nomina pasa de HORIZONTAL (una columna por mes + total) a
# VERTICAL: 12 registros por fila, con las columnas linea, fecha y valor.
#
#   linea -> la fila de nómina (conserva el id que tenía, así no cambia nada
#            para la pantalla ni para el motor de cálculo)
#   fecha -> primer día del mes; el año es el siguiente al actual (automático)
#   valor -> el valor de ese mes
#
# Para que el motor (nomina_motor.py) y la pantalla sigan trabajando en
# horizontal se crea la VISTA presupuesto_nomina_lineas (una fila por línea,
# con enero..diciembre y total) con disparadores INSTEAD OF que convierten cada
# INSERT / UPDATE / DELETE en los 12 registros de la tabla vertical.
#
# La copia se VERIFICA (cantidad de filas y suma de cada mes por tipo); si algo
# no cuadra lanza un error y, como la migración es atómica, no queda nada a
# medias. La tabla anterior se conserva como presupuesto_nomina_respaldo (se
# puede borrar cuando se confirme que todo está bien). Es reversible.
#
# Requiere PostgreSQL (vista con disparadores).


from django.db import migrations, models

import presupuestoApp.models_nomina

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
CAMPOS_LINEA = [
    "tipo", "cedula", "nombre", "centro", "area", "cargo", "concepto", "cuenta",
    "base", "factor", "historico", "origen", "clave", "centro_origen", "area_origen",
    "excluir_de", "creado", "actualizado", "actualizado_por",
]
RESPALDO = "presupuesto_nomina_respaldo"


def _q(campos):
    return ", ".join(f'"{c}"' for c in campos)


# ── 1. Apartar la tabla horizontal (con sus índices y su secuencia) ─────────
RENOMBRAR_A_RESPALDO = f"""
ALTER TABLE presupuesto_nomina RENAME TO {RESPALDO};
ALTER TABLE {RESPALDO} RENAME CONSTRAINT presupuesto_nomina_pkey TO {RESPALDO}_pkey;
ALTER SEQUENCE IF EXISTS presupuesto_nomina_id_seq RENAME TO {RESPALDO}_id_seq;
DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT indexname FROM pg_indexes
           WHERE tablename = '{RESPALDO}' AND indexname <> '{RESPALDO}_pkey'
  LOOP
    EXECUTE format('ALTER INDEX %I RENAME TO %I', r.indexname, left('resp_' || r.indexname, 63));
  END LOOP;
END $$;
"""
RESPALDO_A_ORIGINAL = f"""
DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT indexname FROM pg_indexes
           WHERE tablename = '{RESPALDO}' AND indexname LIKE 'resp\\_%'
  LOOP
    EXECUTE format('ALTER INDEX %I RENAME TO %I', r.indexname, substr(r.indexname, 6));
  END LOOP;
END $$;
ALTER SEQUENCE IF EXISTS {RESPALDO}_id_seq RENAME TO presupuesto_nomina_id_seq;
ALTER TABLE {RESPALDO} RENAME CONSTRAINT {RESPALDO}_pkey TO presupuesto_nomina_pkey;
ALTER TABLE {RESPALDO} RENAME TO presupuesto_nomina;
"""


# ── 3. Copiar horizontal -> vertical y verificar ────────────────────────────
def _anio_presupuesto():
    from django.utils import timezone
    return timezone.localdate().year + 1


def copiar_a_vertical(apps, schema_editor):
    anio = _anio_presupuesto()
    casos = " ".join(f'WHEN {i} THEN o."{m}"' for i, m in enumerate(MESES, 1))
    with schema_editor.connection.cursor() as cur:
        cur.execute(f"""
            INSERT INTO presupuesto_nomina ("linea", {_q(CAMPOS_LINEA)}, "fecha", "valor")
            SELECT o.id, {", ".join(f'o."{c}"' for c in CAMPOS_LINEA)},
                   make_date(%s, m, 1), COALESCE(CASE m {casos} END, 0)
            FROM {RESPALDO} o CROSS JOIN generate_series(1, 12) AS m
        """, [anio])

        # Verificación por tipo: filas y suma de cada mes.
        sumas_origen = ", ".join(f'COALESCE(SUM("{m}"), 0)' for m in MESES)
        cur.execute(f"SELECT tipo, COUNT(*), {sumas_origen} FROM {RESPALDO} GROUP BY tipo ORDER BY tipo")
        origen = cur.fetchall()
        sumas_nuevo = ", ".join(
            f"COALESCE(SUM(valor) FILTER (WHERE EXTRACT(MONTH FROM fecha) = {i}), 0)"
            for i in range(1, 13)
        )
        cur.execute(f"""
            SELECT tipo, COUNT(DISTINCT linea), {sumas_nuevo} FROM presupuesto_nomina
            GROUP BY tipo ORDER BY tipo
        """)
        nuevo = cur.fetchall()
    if [tuple(map(str, r)) for r in origen] != [tuple(map(str, r)) for r in nuevo]:
        raise RuntimeError(f"La copia de presupuesto_nomina no cuadra:\n origen={origen}\n nuevo={nuevo}")
    for fila in origen:
        print(f"  ✔ nómina {fila[0]}: {fila[1]} filas → {fila[1] * 12} registros")


def copiar_a_horizontal(apps, schema_editor):
    """Reverso: pivota la tabla vertical de vuelta al respaldo horizontal."""
    meses = ", ".join(
        f'COALESCE(SUM(valor) FILTER (WHERE EXTRACT(MONTH FROM fecha) = {i}), 0) AS "{m}"'
        for i, m in enumerate(MESES, 1)
    )
    with schema_editor.connection.cursor() as cur:
        cur.execute(f"DELETE FROM {RESPALDO}")
        cur.execute(f"""
            INSERT INTO {RESPALDO} ("id", {_q(CAMPOS_LINEA)}, {_q(MESES)}, "total")
            SELECT l.linea, {", ".join(f'l."{c}"' for c in CAMPOS_LINEA)},
                   {", ".join(f's."{m}"' for m in MESES)}, s.total
            FROM (SELECT DISTINCT ON (linea) * FROM presupuesto_nomina ORDER BY linea, fecha) l
            JOIN (SELECT linea, {meses}, COALESCE(SUM(valor), 0) AS total
                  FROM presupuesto_nomina GROUP BY linea) s ON s.linea = l.linea
        """)
        cur.execute(f"""SELECT setval(pg_get_serial_sequence('{RESPALDO}', 'id'),
                               GREATEST((SELECT MAX(id) FROM {RESPALDO}), 1))""")


# ── 4. Vista horizontal + disparadores ──────────────────────────────────────
_lista_linea = _q(CAMPOS_LINEA)
_new_linea = ", ".join(f'NEW."{c}"' for c in CAMPOS_LINEA)
_set_linea = ", ".join(f'"{c}" = NEW."{c}"' for c in CAMPOS_LINEA)
_valor_mes = "CASE {mes} " + " ".join(f'WHEN {i} THEN NEW."{m}"' for i, m in enumerate(MESES, 1)) + " END"
_total_new = " + ".join(f'COALESCE(NEW."{m}", 0)' for m in MESES)

CREAR_VISTA = f"""
CREATE SEQUENCE presupuesto_nomina_linea_seq;
SELECT setval('presupuesto_nomina_linea_seq',
              GREATEST((SELECT MAX(linea) FROM presupuesto_nomina),
                       (SELECT last_value FROM {RESPALDO}_id_seq), 1));

CREATE VIEW presupuesto_nomina_lineas AS
SELECT m.linea AS id, {", ".join(f'm."{c}"' for c in CAMPOS_LINEA)},
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
    INSERT INTO presupuesto_nomina ("linea", {_lista_linea}, "fecha", "valor")
    SELECT NEW.id, {_new_linea}, make_date(NEW.anio, mes, 1),
           COALESCE({_valor_mes.format(mes="mes")}, 0)
    FROM generate_series(1, 12) AS mes;
    NEW.total := {_total_new};
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE FUNCTION presupuesto_nomina_lineas_actualizar() RETURNS trigger AS $$
BEGIN
    UPDATE presupuesto_nomina SET
        {_set_linea},
        "fecha" = make_date(COALESCE(NEW.anio, EXTRACT(YEAR FROM fecha)::integer),
                            EXTRACT(MONTH FROM fecha)::integer, 1),
        "valor" = COALESCE({_valor_mes.format(mes="EXTRACT(MONTH FROM fecha)::integer")}, 0)
    WHERE linea = OLD.id;
    NEW.id := OLD.id;
    NEW.total := {_total_new};
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
DROP SEQUENCE IF EXISTS presupuesto_nomina_linea_seq;
"""


def _campos_linea():
    return [
        ('tipo', models.CharField(db_index=True, max_length=40)),
        ('cedula', models.CharField(blank=True, default='', max_length=20)),
        ('nombre', models.CharField(blank=True, default='', max_length=150)),
        ('centro', models.CharField(blank=True, default='', max_length=150)),
        ('area', models.CharField(blank=True, default='', max_length=150)),
        ('cargo', models.CharField(blank=True, default='', max_length=150)),
        ('concepto', models.CharField(blank=True, default='', max_length=80)),
        ('cuenta', models.CharField(blank=True, default='', max_length=30)),
        ('base', models.BigIntegerField(default=0)),
        ('factor', models.FloatField(default=1)),
        ('historico', models.JSONField(blank=True, default=dict)),
        ('origen', models.CharField(choices=[('sistema', 'Calculado'), ('manual', 'Manual')],
                                    default='manual', max_length=10)),
        ('clave', models.CharField(blank=True, default='', max_length=255)),
        ('centro_origen', models.CharField(blank=True, default='', max_length=150)),
        ('area_origen', models.CharField(blank=True, default='', max_length=150)),
        ('excluir_de', models.JSONField(blank=True, default=list)),
        ('creado', models.DateTimeField(auto_now_add=True)),
        ('actualizado', models.DateTimeField(auto_now=True)),
        ('actualizado_por', models.CharField(blank=True, default='', max_length=150)),
    ]


class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        ('presupuestoApp', '0033_plazo_edicion_area'),
    ]

    operations = [
        # 1. La tabla horizontal pasa a ser el respaldo.
        migrations.RunSQL(RENOMBRAR_A_RESPALDO, RESPALDO_A_ORIGINAL),

        # 2. Estado de Django: PresupuestoNomina pasa a ser la vista (no
        #    administrada) y PresupuestoNominaMes es la tabla vertical, que
        #    se crea en la base de datos.
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='PresupuestoNomina'),
                migrations.CreateModel(
                    name='PresupuestoNomina',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                                   serialize=False, verbose_name='ID')),
                        *_campos_linea(),
                        ('anio', models.IntegerField(default=presupuestoApp.models_nomina._anio_presupuesto)),
                        *[(m, models.BigIntegerField(default=0)) for m in MESES],
                        ('total', models.BigIntegerField(default=0)),
                    ],
                    options={
                        'db_table': 'presupuesto_nomina_lineas',
                        'ordering': ['tipo', 'id'],
                        'managed': False,
                    },
                ),
            ],
            database_operations=[],
        ),
        migrations.CreateModel(
            name='PresupuestoNominaMes',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                *_campos_linea(),
                ('linea', models.BigIntegerField()),
                ('fecha', models.DateField()),
                ('valor', models.BigIntegerField(default=0)),
            ],
            options={
                'db_table': 'presupuesto_nomina',
                'ordering': ['linea', 'fecha'],
                'indexes': [
                    models.Index(fields=['tipo', 'origen'], name='nomina_tipo_origen_idx'),
                    models.Index(fields=['tipo', 'cedula'], name='nomina_tipo_cedula_idx'),
                    models.Index(fields=['linea', 'fecha'], name='nomina_linea_fecha_idx'),
                    models.Index(fields=['fecha'], name='nomina_fecha_idx'),
                ],
            },
        ),

        # 3. Datos: horizontal -> vertical (verificado).
        migrations.RunPython(copiar_a_vertical, copiar_a_horizontal),

        # 4. Vista horizontal con disparadores.
        migrations.RunSQL(CREAR_VISTA, BORRAR_VISTA),
    ]
