"""Respaldo del presupuesto de nómina antes de cada recálculo, para poder revertirlo.

- nomina_respaldo_recalculo: un registro por respaldo (cuándo, quién, motivo,
  parámetros de ese momento).
- nomina_respaldo_recalculo_lineas: copia de presupuesto_nomina (tabla
  vertical) + respaldo_id.
"""
from django.db import migrations, models

LINEAS = "nomina_respaldo_recalculo_lineas"

CREAR = f"""
CREATE TABLE {LINEAS} AS SELECT * FROM presupuesto_nomina WITH NO DATA;
ALTER TABLE {LINEAS} ADD COLUMN respaldo_id bigint NOT NULL;
CREATE INDEX {LINEAS}_respaldo_idx ON {LINEAS} (respaldo_id);
"""
BORRAR = f"DROP TABLE IF EXISTS {LINEAS};"


class Migration(migrations.Migration):

    dependencies = [
        ("presupuestoApp", "0056_codigo_costo_por_cuenta"),
    ]

    operations = [
        migrations.CreateModel(
            name="RespaldoRecalculoNomina",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("creado", models.DateTimeField(auto_now_add=True)),
                ("usuario", models.CharField(blank=True, default="", max_length=150)),
                ("motivo", models.CharField(blank=True, default="", max_length=200)),
                ("parametros", models.JSONField(blank=True, default=dict)),
                ("filas", models.IntegerField(default=0)),
                ("revertido", models.DateTimeField(blank=True, null=True)),
                ("revertido_por", models.CharField(blank=True, default="", max_length=150)),
            ],
            options={"db_table": "nomina_respaldo_recalculo", "ordering": ["-creado", "-id"]},
        ),
        migrations.RunSQL(CREAR, BORRAR),
    ]
