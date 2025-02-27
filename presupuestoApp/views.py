from django.shortcuts import render
from .models import Producto

def presupuesto(request):
    ventas = Producto.objects.values('bod_nom','linea_nom','cliente_grp_nom')[:100]
    print(ventas)
    return render(request, 'presupuestoApp/presupuesto.html')