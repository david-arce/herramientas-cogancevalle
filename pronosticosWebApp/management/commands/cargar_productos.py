import json, os
from django.core.management.base import BaseCommand
from pronosticosWebApp.pronosticos.pronosticos import Pronosticos
from django.conf import settings
from django.core.cache import cache

class Command(BaseCommand):
    help = "Carga inicial de productos para pronósticos"

    def handle(self, *args, **options):
        _, _, df_pronosticos, *_ = Pronosticos.pronosticos()
        print(df_pronosticos)
        cache.set("productos", df_pronosticos.to_dict("records"), None)
        self.stdout.write("Productos cacheados")