import json, os
from django.core.management.base import BaseCommand
from pronosticosWebApp.pronosticos.pronosticos import Pronosticos
from django.conf import settings

class Command(BaseCommand):
    help = "Carga inicial de productos para pronósticos"

    def handle(self, *args, **options):
        # 1) Obtén todos los dfs
        (
            df_demanda,
            df_pronosticos,
            df_pronostico_p3,
            df_pronostico_p4,
            df_pronostico_p5,
            df_pronostico_ses,
            df_pronostico_sed,
        ) = Pronosticos.pronosticos()
        # 2) Convierte cada uno a lista de dicts
        payload = {
            "demanda":      df_demanda.to_dict(orient="records"),
            "pronosticos":  df_pronosticos.to_dict(orient="records"),
            "p3":           df_pronostico_p3.to_dict(orient="records"),
            "p4":           df_pronostico_p4.to_dict(orient="records"),
            "p5":           df_pronostico_p5.to_dict(orient="records"),
            "ses":          df_pronostico_ses.to_dict(orient="records"),
            "sed":          df_pronostico_sed.to_dict(orient="records"),
        }
    
        # 3) Escribe un único JSON con todo
        out_path = os.path.join(settings.BASE_DIR, "productos.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(f"JSON escrito en {out_path}"))