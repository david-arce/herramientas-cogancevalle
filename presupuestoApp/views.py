from django.shortcuts import render
import pandas as pd
from .models import Producto, BdPresupuesto1, BdPresupuesto2, BdPresupuesto3
from django.db.models.functions import Concat
from django.db.models import Sum

def presupuesto(request):
    # ventas = BdPresupuesto1.objects.values('nombre_linea_n1','lapso').distinct()
    # obtener la suma de cada mes y nombre_linea_n1 es decir, si el lapso es 202001 retornar la suma
    # de los productos que pertenecen a la linea_n1
    bd1 = BdPresupuesto1.objects.values('nombre_linea_n1', 'lapso').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'suma')
    bd2 = BdPresupuesto2.objects.values('nombre_linea_n1', 'lapso').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'suma')
    bd3 = BdPresupuesto3.objects.values('nombre_linea_n1', 'lapso').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'suma')
    
    bd_centro_operacion1 = BdPresupuesto1.objects.filter(centro_de_operacion=1).values('lapso').annotate(suma=Sum('valor_neto'))
    bd_centro_operacion2 = BdPresupuesto2.objects.values('centro_de_operacion').distinct()
    bd_centro_operacion3 = BdPresupuesto3.objects.values('centro_de_operacion').distinct()
    
    df1 = pd.DataFrame(list(bd1))
    df2 = pd.DataFrame(list(bd2))
    df3 = pd.DataFrame(list(bd3))
    
    df_centro_operacion1 = pd.DataFrame(list(bd_centro_operacion1))
    
    print(df_centro_operacion1) 
    # Concatenar los dataframes
    df = pd.concat([df1, df3, df2], ignore_index=True)
    # concatenar yyyy y mm en una sola columna llamada lapso
    # df['lapso'] = df['yyyy'].astype(str) + df['mm'].astype(str)
    
    # df.to_excel('ventas.xlsx', index=False)
    # Convertir a lista de diccionarios para pasar al template
    data = df.to_dict(orient='records')
    return render(request, 'presupuestoApp/presupuesto.html', {'data': data})