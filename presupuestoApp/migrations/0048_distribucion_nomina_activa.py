from django.db import migrations, models


class Migration(migrations.Migration):
    """Distribución por persona: se puede desactivar sin borrar el reparto."""

    dependencies = [
        ("presupuestoApp", "0047_foco_cargo_informe"),
    ]

    operations = [
        migrations.AddField(
            model_name="distribucionnomina",
            name="activa",
            field=models.BooleanField(default=True),
        ),
    ]
