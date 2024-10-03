from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView
# from mi_app.models import MiModelo

class MiVistaLista(PermissionRequiredMixin, ListView):
    # model = MiModelo
    permission_required = 'herramientaInventario.can_view_model'
    template_name = 'index.html'
