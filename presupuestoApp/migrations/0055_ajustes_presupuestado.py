from django.db import migrations, models


class Migration(migrations.Migration):
    """Modo edición del Presupuestado general (valores escritos a mano) y huella
    del ejecutado para recalcular el presupuesto de ventas cuando cambia."""

    dependencies = [
        ("presupuestoApp", "0054_destino_nomina_por_area"),
    ]

    operations = [
        migrations.CreateModel(
            name="AjustePresupuestado",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sede", models.CharField(max_length=20)),
                ("cuenta", models.CharField(max_length=60)),
                ("ctanombre", models.CharField(blank=True, default="", max_length=255)),
                ("mes", models.PositiveSmallIntegerField()),
                ("anio", models.PositiveIntegerField()),
                ("valor", models.FloatField()),
                ("valor_calculado", models.FloatField(blank=True, null=True)),
                ("actualizado", models.DateTimeField(auto_now=True)),
                ("actualizado_por", models.CharField(blank=True, default="", max_length=150)),
            ],
            options={"db_table": "ajuste_presupuestado"},
        ),
        migrations.AddConstraint(
            model_name="ajustepresupuestado",
            constraint=models.UniqueConstraint(fields=("sede", "cuenta", "mes", "anio"), name="ajuste_presupuestado_uniq"),
        ),
        migrations.CreateModel(
            name="EstadoPresupuestoVentas",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("clave", models.CharField(default="ventas", max_length=20, unique=True)),
                ("huella_ejecutado", models.TextField(blank=True, default="")),
                ("generado", models.DateTimeField(blank=True, null=True)),
                ("generado_por", models.CharField(blank=True, default="", max_length=150)),
                ("ultimo_error", models.TextField(blank=True, default="")),
            ],
            options={"db_table": "estado_presupuesto_ventas"},
        ),
    ]
