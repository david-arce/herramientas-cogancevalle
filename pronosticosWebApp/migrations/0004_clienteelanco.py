from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pronosticosWebApp', '0003_alter_producto_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClienteElanco',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ccnit', models.CharField(max_length=50, unique=True)),
                ('razon_social', models.CharField(blank=True, default='', max_length=255)),
            ],
            options={
                'db_table': 'clientes_elanco',
                'ordering': ['razon_social'],
            },
        ),
    ]
