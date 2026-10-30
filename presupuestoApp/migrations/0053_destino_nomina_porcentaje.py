from django.db import migrations, models


class Migration(migrations.Migration):
    """Varios destinos por persona: cada fila con su porcentaje.

    Las asignaciones que ya existían (un destino por persona) quedan con 100 %,
    así que siguen igual sin volver a asignarlas.
    """

    dependencies = [
        ("presupuestoApp", "0052_destino_nomina"),
    ]

    operations = [
        migrations.AddField(
            model_name="destinonomina",
            name="porcentaje",
            field=models.FloatField(default=100),
        ),
        migrations.AlterField(
            model_name="destinonomina",
            name="persona",
            field=models.CharField(db_index=True, max_length=200),
        ),
        migrations.AddConstraint(
            model_name="destinonomina",
            constraint=models.UniqueConstraint(fields=("persona", "destino"),
                                               name="destino_nomina_persona_destino_uniq"),
        ),
    ]
