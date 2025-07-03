from django.core.management.base import BaseCommand
from pronosticosWebApp.views import lista_productos

class Command(BaseCommand):
    help = "Carga inicial de productos para pronósticos"

    def handle(self, *args, **options):
        # lista_productos()
        self.stdout.write(self.style.SUCCESS("✅ lista_productos ejecutada correctamente."))