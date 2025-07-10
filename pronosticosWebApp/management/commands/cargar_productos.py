import json, os
from django.core.management.base import BaseCommand
from pronosticosWebApp.pronosticos.pronosticos import Pronosticos
from django.conf import settings

class Command(BaseCommand):
    help = "Carga inicial de productos para pronósticos"

    def handle(self, *args, **options):
        # Ejecuta tu lógica
        df_demanda, df_total, df_pronosticos, *_ = Pronosticos.pronosticos()
        productos = df_pronosticos.to_dict(orient="records")

        # Ruta absoluta para guardar el JSON
        out_path = os.path.join(settings.BASE_DIR, "productos.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"productos": productos}, f, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(f"JSON escrito en {out_path}"))