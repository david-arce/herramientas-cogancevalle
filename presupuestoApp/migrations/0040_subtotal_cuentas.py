# Tabla presupuesto_subtotal_cuentas: qué cuentas suma cada fila calculada del
# Consolidado / Presupuestado / Comparativo (Otros Ingresos, Gastos por
# Servicios, Gastos de Administración...).
#
# Nace vacía: mientras una fila no se edite en Ajustes → Filas calculadas se
# usan los valores por defecto de subtotales.CATALOGO, que son exactamente los
# que estaban escritos en las plantillas. Así las tablas no cambian al migrar.
#
# Reversible (al revertir se borra la tabla y se vuelve a los valores por defecto).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("presupuestoApp", "0039_renombrar_comercial_gastos"),
    ]

    operations = [
        migrations.CreateModel(
            name="SubtotalCuentas",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("clave", models.CharField(max_length=40, unique=True)),
                ("cuentas", models.JSONField(blank=True, default=list)),
                ("prefijos", models.JSONField(blank=True, default=list)),
                ("actualizado_por", models.CharField(blank=True, default="", max_length=150)),
                ("actualizado", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "presupuesto_subtotal_cuentas",
                "ordering": ["clave"],
            },
        ),
    ]
