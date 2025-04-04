from django.shortcuts import render
import pandas as pd
from .models import Producto
from django.db.models.functions import Concat

def presupuesto(request):
    ventas = Producto.objects.values('yyyy','mm','zona','zona_nom','marca','marca_nom','sku','sku_nom','linea','linea_nom','ccnit','cliente_nom','cliente_grp','cliente_grp_nom','subtotal','costo_vta','cantidad')[:100]
    df = pd.DataFrame(ventas)
    # concatenar yyyy y mm en una sola columna llamada lapso
    df['lapso'] = df['yyyy'].astype(str) + df['mm'].astype(str)
    # eliminar las columnas yyyy y mm
    df.drop(columns=['yyyy', 'mm'], inplace=True)
    
    df.to_excel('ventas.xlsx', index=False)
    print(df)
    return render(request, 'presupuestoApp/presupuesto.html')