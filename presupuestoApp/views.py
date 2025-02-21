from django.shortcuts import render

def presupuesto(request):
    return render(request, 'presupuestoApp/presupuesto.html')