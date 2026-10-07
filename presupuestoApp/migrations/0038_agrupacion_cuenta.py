# Agrupación y nombres de cuentas en una tabla (presupuesto_agrupacion_cuenta).
#
# Antes estaban escritos en views.py:
#   _GRUPOS               cuentas exactas que se suman en una fila
#   PREFIJOS_AGRUPADOS    cuentas que empiezan por ... se suman en una fila
#   startswith('541001')  regla suelta de Honorarios
#   NOMBRES_ESPECIALES    nombre de cada fila
#
# Aquí se copian tal cual a la tabla, así el consolidado da exactamente los
# mismos resultados. Desde ahora se editan en Ajustes → Agrupación de cuentas.
#
# Reversible (al revertir se borra la tabla).

from django.db import migrations, models

# Copia congelada de lo que había en views.py.
GRUPOS = {
    "54100207_54100211": ["54100207", "54100208", "54100209", "54100210", "54100211"],
    "541009_541033": ["541009", "541033", "54103301", "54103302"],
    "541015_541016": ["541015", "541016"],
    "511015_511016": ["511015", "511016"],
    "51109501_51109502": ["51109501", "51109502"],
}
PREFIJOS = ["541001", "5230", "541003", "541005", "541006", "541024", "541027", "5415"]
NOMBRES = {
    "541001": "Honorarios", "54100207_54100211": "Tasas Bomberil-otras",
    "541003": "Arrendamientos", "541005": "Seguros",
    "541006": "Mantenimiento y Reparaciónes",
    "541009_541033": "Adecuación e Instalaciones-Reparac locat",
    "541015_541016": "Utiles - Papelería- Fotocopias",
    "541024": "Gastos Legales", "541027": "Gastos de Viaje",
    "5415": "Depreciación", "511015_511016": "Papelería y Utiles de Oficina",
    "5405": "Gastos de Personal", "5105": "Gastos de Personal",
    "51109501_51109502": "Gastos de Fondos Sociales",
    "5": "Proyecto de Aftosa", "6": "Asistencia Técnica Propia",
    "7": "Asistencia Técnica Convenios",
    "8": "Asistencia Técnica Otros - Capacitaciones",
    "5230": "Gastos no Operacionales-IVA obsequios",
    "521015": "Gastos Contribución 4 x1000", "615035": "Intereses",
    "AT-00003": "Convenio Elanco", "AT-00004": "Apoyo ciclo aftosa Virbac",
    "AT-00005": "Convenio Proalba-Santa Lucía", "AT-00007": "Convenio Tecnoquímicas",
    "AT-00008": "Seminario ambiental",
    "AT-00010": "Jornada de actualización en reproducción",
    "AT-00013": "Curso de gestión empresarial", "AT-00014": "Curso de mayordomía",
    "AT-00015": "Ecografo Bovino", "AT-00016": "Curso de Inseminación",
    "AT-00019": "Brucelosis-Tuberculosis", "AT-00020": "Programa ambiental",
    "AT-00021": "Chequeo reproductivo", "AT-00022": "Curso de Bromatología",
    "AT-00023": "Capacitación software ganadero", "AT-00024": "Atencion urgencias",
    "AT-00026": "Taller atención básica equipos de ordeño",
    "AT-00028": "Mantenimiento equipo técnico-Diplomado",
    "AT-00029": "Taller en bienestar y sanidad bovina",
    "AT-00030": "Seminario productividad láctea",
    "AT-00032": "Servicio de imágenes con dron",
    "VT-00025": "Convenio Tecnoquímicas", "41659505": "Proyecto de Aftosa",
    "41659501": "Patrocinio de eventos", "420560": "Venta PPE (moto)",
}


def sembrar(apps, schema_editor):
    Agrupacion = apps.get_model("presupuestoApp", "AgrupacionCuenta")
    filas = {}
    for codigo, cuentas in GRUPOS.items():
        filas[codigo] = {"cuentas": list(cuentas), "prefijos": []}
    for prefijo in PREFIJOS:
        filas.setdefault(prefijo, {"cuentas": [], "prefijos": []})["prefijos"].append(prefijo)
    for codigo in NOMBRES:
        filas.setdefault(codigo, {"cuentas": [], "prefijos": []})
    Agrupacion.objects.bulk_create([
        Agrupacion(codigo=codigo, nombre=NOMBRES.get(codigo, codigo), actualizado_por="migración inicial", **datos)
        for codigo, datos in filas.items()
    ], ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ("presupuestoApp", "0037_asignacion_presupuesto"),
    ]

    operations = [
        migrations.CreateModel(
            name="AgrupacionCuenta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(max_length=60, unique=True)),
                ("nombre", models.CharField(max_length=255)),
                ("cuentas", models.JSONField(blank=True, default=list)),
                ("prefijos", models.JSONField(blank=True, default=list)),
                ("actualizado_por", models.CharField(blank=True, default="", max_length=150)),
                ("actualizado", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "presupuesto_agrupacion_cuenta",
                "ordering": ["codigo"],
            },
        ),
        migrations.RunPython(sembrar, migrations.RunPython.noop),
    ]
