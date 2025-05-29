from django.shortcuts import render
import pandas as pd
from .models import Producto, BdPresupuesto1, BdPresupuesto2, BdPresupuesto3
from django.db.models.functions import Concat
from django.db.models import Sum
import numpy as np

def presupuesto(request):
    # ventas = BdPresupuesto1.objects.values('nombre_linea_n1','lapso').distinct()
    # obtener la suma de cada mes y nombre_linea_n1 es decir, si el lapso es 202001 retornar la suma
    # de los productos que pertenecen a la linea_n1
    bd1 = BdPresupuesto1.objects.values('nombre_linea_n1', 'lapso').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'suma')
    bd2 = BdPresupuesto2.objects.values('nombre_linea_n1', 'lapso').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'suma')
    bd3 = BdPresupuesto3.objects.values('nombre_linea_n1', 'lapso').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'suma')
    
    
    df1 = pd.DataFrame(list(bd1))
    df2 = pd.DataFrame(list(bd2))
    df3 = pd.DataFrame(list(bd3))
    
    bd1_centro_operacion1 = BdPresupuesto1.objects.filter(centro_de_operacion=1).values('lapso').annotate(suma=Sum('valor_neto'))
    bd1_centro_operacion2 = BdPresupuesto1.objects.filter(centro_de_operacion=2).values('lapso').annotate(suma=Sum('valor_neto'))
    bd1_centro_operacion3 = BdPresupuesto1.objects.filter(centro_de_operacion=3).values('lapso').annotate(suma=Sum('valor_neto'))
    bd1_centro_operacion4 = BdPresupuesto1.objects.filter(centro_de_operacion=4).values('lapso').annotate(suma=Sum('valor_neto'))
    bd2_centro_operacion1 = BdPresupuesto2.objects.filter(centro_de_operacion=1).values('lapso').annotate(suma=Sum('valor_neto'))
    bd2_centro_operacion2 = BdPresupuesto2.objects.filter(centro_de_operacion=2).values('lapso').annotate(suma=Sum('valor_neto'))
    bd2_centro_operacion3 = BdPresupuesto2.objects.filter(centro_de_operacion=3).values('lapso').annotate(suma=Sum('valor_neto'))
    bd2_centro_operacion4 = BdPresupuesto2.objects.filter(centro_de_operacion=4).values('lapso').annotate(suma=Sum('valor_neto'))
    bd3_centro_operacion1 = BdPresupuesto3.objects.filter(centro_de_operacion=1).values('lapso').annotate(suma=Sum('valor_neto'))
    bd3_centro_operacion2 = BdPresupuesto3.objects.filter(centro_de_operacion=2).values('lapso').annotate(suma=Sum('valor_neto'))
    bd3_centro_operacion3 = BdPresupuesto3.objects.filter(centro_de_operacion=3).values('lapso').annotate(suma=Sum('valor_neto'))
    bd3_centro_operacion4 = BdPresupuesto3.objects.filter(centro_de_operacion=4).values('lapso').annotate(suma=Sum('valor_neto'))
    
    bd1_clase_cliente1 = BdPresupuesto1.objects.filter(nombre_clase_cliente='CLIENTES', centro_de_operacion=1).values('lapso').annotate(suma=Sum('valor_neto'))
    bd1_clase_distribuidor1 = BdPresupuesto1.objects.filter(nombre_clase_cliente='DISTRIBUIDOR', centro_de_operacion=1).values('lapso').annotate(suma=Sum('valor_neto'))
    bd2_clase_cliente2 = BdPresupuesto1.objects.filter(nombre_clase_cliente='CLIENTES', centro_de_operacion=2).values('lapso').annotate(suma=Sum('valor_neto'))
    bd2_clase_distribuidor2 = BdPresupuesto1.objects.filter(nombre_clase_cliente='DISTRIBUIDOR', centro_de_operacion=2).values('lapso').annotate(suma=Sum('valor_neto'))
    bd3_clase_cliente3 = BdPresupuesto1.objects.filter(nombre_clase_cliente='CLIENTES', centro_de_operacion=3).values('lapso').annotate(suma=Sum('valor_neto'))
    bd3_clase_distribuidor3 = BdPresupuesto1.objects.filter(nombre_clase_cliente='DISTRIBUIDOR', centro_de_operacion=3).values('lapso').annotate(suma=Sum('valor_neto'))
    bd4_clase_cliente4 = BdPresupuesto1.objects.filter(nombre_clase_cliente='CLIENTES', centro_de_operacion=4).values('lapso').annotate(suma=Sum('valor_neto'))
    bd4_clase_distribuidor4 = BdPresupuesto1.objects.filter(nombre_clase_cliente='DISTRIBUIDOR', centro_de_operacion=4).values('lapso').annotate(suma=Sum('valor_neto'))
   
    df_lapso_2020_2021 = df1.groupby('lapso')['suma'].sum().reset_index()
    df_lapso_2024 = df2.groupby('lapso')['suma'].sum().reset_index()
    df_lapso_2022_2023 = df3.groupby('lapso')['suma'].sum().reset_index()
    df_lapso_total = pd.concat([df_lapso_2020_2021, df_lapso_2024, df_lapso_2022_2023], ignore_index=True)

    # CALUCLAR PREDICCIÓN PARA 2025 POR CADA MES -----------------------------------------
    # Extraer año y mes
    df_lapso_total['año'] = df_lapso_total['lapso'] // 100
    df_lapso_total['mes'] = df_lapso_total['lapso'] % 100

    # Lista para almacenar predicciones
    predicciones_2025 = []

    # Hacer predicción para cada mes
    for mes in range(1, 13):
        datos_mes = df_lapso_total[df_lapso_total['mes'] == mes]
        
        # Datos para regresión
        x = datos_mes['año'].values
        y = datos_mes['suma'].values

        if len(x) >= 2:  # Se necesita al menos 2 puntos para ajustar una recta
            a, b = np.polyfit(x, y, 1)  # Ajuste lineal
            y_pred = a * 2025 + b
            predicciones_2025.append({'lapso': 2025 * 100 + mes, 'suma': round(y_pred)})

    # Crear DataFrame con predicciones
    df_pred_2025 = pd.DataFrame(predicciones_2025)

    # (Opcional) Unir con el DataFrame original y ordenar por lapso
    df_proyeccion_centro_operacion = pd.concat([df_lapso_total[['lapso', 'suma']], df_pred_2025], ignore_index=True)
    df_proyeccion_centro_operacion = df_proyeccion_centro_operacion.sort_values('lapso').reset_index(drop=True)


    # Concatenar los dataframes para el dinamismo
    df_dinamismo = pd.concat([df1, df3, df2], ignore_index=True)
    
    # Extraer el año desde 'lapso'
    df_dinamismo['year'] = df_dinamismo['lapso'] // 100

    # Agrupar por nombre de producto y año, y sumar
    df_agrupado = df_dinamismo.groupby(['nombre_linea_n1', 'year'])['suma'].sum().reset_index()

    # (Opcional) Ordenar resultados
    df_agrupado = df_agrupado.sort_values(by=['nombre_linea_n1', 'year'])

    # PREDICCION PARA 2025 POR PRONOSTICO LINEAL -----------------------------------------
    # Lista para almacenar resultados
    predicciones = []

    # Agrupar por producto
    for nombre, grupo in df_agrupado.groupby('nombre_linea_n1'):
        x = grupo['year'].values
        y = grupo['suma'].values
        
        if len(x) >= 2:
            # Ajuste lineal
            a, b = np.polyfit(x, y, 1)
            y_pred = a * 2025 + b
            predicciones.append({
                'nombre_linea_n1': nombre,
                'year': 2025,
                'suma': round(y_pred)
            })

    # Crear DataFrame con predicciones
    df_pred_2025_pro_lineal = pd.DataFrame(predicciones)
    df_final_pronostico = pd.concat([df_agrupado, df_pred_2025_pro_lineal], ignore_index=True)
    df_final_pronostico = df_final_pronostico.sort_values(by=['nombre_linea_n1', 'year']).reset_index(drop=True)

    # R2 ----------------------------------------------
    # Lista para almacenar resultados
    correlaciones = []

    # Agrupar por producto
    for nombre, grupo in df_final_pronostico.groupby('nombre_linea_n1'):
        x = grupo['year'].values
        y = grupo['suma'].values

        if len(x) >= 2:
            coef = np.corrcoef(x, y)[0, 1]
            coef_abs_pct = abs(coef) * 100  # valor absoluto en porcentaje
            correlaciones.append({
                'nombre_linea_n1': nombre,
                'coef_correl_pct': round(coef_abs_pct, 2)  # ej. 87.32%
            })


    # Crear DataFrame con los coeficientes
    df_correlaciones = pd.DataFrame(correlaciones)

    # Mostrar resultados
    print(df_correlaciones)
    
    # concatenar yyyy y mm en una sola columna llamada lapso
    # df['lapso'] = df['yyyy'].astype(str) + df['mm'].astype(str)
    
    # df.to_excel('ventas.xlsx', index=False)
    # Convertir a lista de diccionarios para pasar al template
    data = df_final_pronostico.to_dict(orient='records')
    return render(request, 'presupuestoApp/presupuesto.html', {'data': data})