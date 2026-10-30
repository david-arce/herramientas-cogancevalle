from django.db import migrations, models


class Migration(migrations.Migration):
    """Destino (AT/VT) de cada persona de nómina con centro de costo 020301."""

    dependencies = [
        ("presupuestoApp", "0051_segmentos_como_en_excel"),
    ]

    operations = [
        migrations.CreateModel(
            name="DestinoNomina",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("persona", models.CharField(max_length=200, unique=True)),
                ("destino", models.CharField(max_length=30)),
                ("actualizado", models.DateTimeField(auto_now=True)),
                ("actualizado_por", models.CharField(blank=True, default="", max_length=150)),
            ],
            options={"db_table": "destino_nomina"},
        ),
    ]
