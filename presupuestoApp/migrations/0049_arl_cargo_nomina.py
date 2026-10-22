from django.db import migrations, models


class Migration(migrations.Migration):
    """Seguridad social de asistencia técnica: ARL elegida por cargo."""

    dependencies = [
        ("presupuestoApp", "0048_distribucion_nomina_activa"),
    ]

    operations = [
        migrations.CreateModel(
            name="ArlCargoNomina",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cargo", models.CharField(max_length=150, unique=True)),
                ("porcentaje", models.FloatField()),
                ("actualizado", models.DateTimeField(auto_now=True)),
                ("actualizado_por", models.CharField(blank=True, default="", max_length=150)),
            ],
            options={
                "db_table": "arl_cargo_nomina",
                "ordering": ["cargo"],
            },
        ),
    ]
