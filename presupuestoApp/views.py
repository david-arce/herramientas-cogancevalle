from collections import defaultdict
from decimal import Decimal
from itertools import chain
from pyexpat.errors import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
import pandas as pd
from .models import BdVentas2020, BdVentas2021, BdVentas2022, BdVentas2023, BdVentas2024, BdVentas2025, ParametrosPresupuestos, PresupuestoSueldos, PresupuestoSueldosAux, ConceptosFijosYVariables, PresupuestoComisiones, PresupuestoComisionesAux, PresupuestoHorasExtra, PresupuestoHorasExtraAux, PresupuestoMediosTransporte, PresupuestoMediosTransporteAux, PresupuestoAuxilioTransporte, PresupuestoAuxilioTransporteAux, PresupuestoAyudaTransporte, PresupuestoAyudaTransporteAux, PresupuestoCesantias, PresupuestoCesantiasAux, PresupuestoPrima, PresupuestoPrimaAux, PresupuestoVacaciones, PresupuestoVacacionesAux, PresupuestoBonificaciones, PresupuestoBonificacionesAux, PresupuestoAprendiz, PresupuestoAprendizAux, PresupuestoAuxilioMovilidad, PresupuestoAuxilioMovilidadAux, PresupuestoSeguridadSocial, PresupuestoSeguridadSocialAux, PresupuestoInteresesCesantias, PresupuestoInteresesCesantiasAux, PresupuestoBonificacionesFoco, PresupuestoBonificacionesFocoAux, PresupuestoAuxilioEducacion, PresupuestoAuxilioEducacionAux, ConceptoAuxilioEducacion, PresupuestoBonosKyrovet, PresupuestoBonosKyrovetAux, PresupuestoGeneralVentas, PresupuestoCentroOperacionVentas, PresupuestoCentroSegmentoVentas, PresupuestoGeneralCostos, PresupuestoCentroOperacionCostos, PresupuestoCentroSegmentoCostos, PresupuestoComercial, Plantillagastos2025, PresupuestoTecnologia, PresupuestoTecnologiaAux, CuentasContables
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.db.models.functions import Concat
from django.db.models import Sum, Max
import numpy as np
import json
from django.utils import timezone
from django.contrib.auth.decorators import login_required

def exportar_excel_presupuestos(request):
    # Obtener datos de cada tabla
    nomina = list(PresupuestoSueldos.objects.values())
    comisiones = list(PresupuestoComisiones.objects.values())
    horas_extra = list(PresupuestoHorasExtra.objects.values())
    auxlio_transporte = list(PresupuestoAuxilioTransporte.objects.values())
    medios_transporte = list(PresupuestoMediosTransporte.objects.values())
    ayuda_transporte = list(PresupuestoAyudaTransporte.objects.values())
    cesantias = list(PresupuestoCesantias.objects.values())
    intereses_cesantias = list(PresupuestoInteresesCesantias.objects.values())  
    prima = list(PresupuestoPrima.objects.values())
    vacaciones = list(PresupuestoVacaciones.objects.values())
    bonificaciones = list(PresupuestoBonificaciones.objects.values())
    auxilio_movilidad = list(PresupuestoAuxilioMovilidad.objects.values())
    aprendiz = list(PresupuestoAprendiz.objects.values())

    # Crear DataFrames con columna de origen
    def prepare_df(data, origen):
        df = pd.DataFrame(data)
        if not df.empty:
            df["origen"] = origen
            # 🔹 Asegurar que no haya datetime con timezone
            for col in df.select_dtypes(include=["datetimetz"]).columns:
                df[col] = df[col].dt.tz_localize(None)
        return df

    df_nomina = prepare_df(nomina, "Nómina")
    df_comisiones = prepare_df(comisiones, "Comisiones")
    df_horas_extra = prepare_df(horas_extra, "Horas Extra")
    df_auxilio_transporte = prepare_df(auxlio_transporte, "Auxilio Transporte")
    df_medios_transporte = prepare_df(medios_transporte, "Medios Transporte")
    df_ayuda_transporte = prepare_df(ayuda_transporte, "Ayuda Transporte")
    df_cesantias = prepare_df(cesantias, "Cesantías")
    df_intereses_cesantias = prepare_df(intereses_cesantias, "Intereses Cesantías")
    df_prima = prepare_df(prima, "Prima")
    df_vacaciones = prepare_df(vacaciones, "Vacaciones")
    df_bonificaciones = prepare_df(bonificaciones, "Bonificaciones")
    df_auxilio_movilidad = prepare_df(auxilio_movilidad, "Auxilio Movilidad")
    df_aprendiz = prepare_df(aprendiz, "Aprendiz")

    # Concatenar todos en un solo DataFrame
    df_final = pd.concat(
        [df_nomina, df_comisiones, df_horas_extra, df_auxilio_transporte, df_medios_transporte, df_ayuda_transporte, df_cesantias, df_intereses_cesantias, df_prima, df_vacaciones, df_bonificaciones, df_auxilio_movilidad, df_aprendiz],
        ignore_index=True
    )

    # Crear la respuesta HTTP para Excel
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="Presupuestos_Todo.xlsx"'

    # Exportar a una sola hoja
    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        df_final.to_excel(writer, sheet_name="Presupuestos", index=False)

    return response

@login_required
def base_comercial(request):
    return render(request, 'presupuesto_comercial/base_presupuesto_comercial.html')

def presupuesto_comercial_costos():
    # obtener la suma de cada mes y nombre_linea_n1 es decir, si el lapso es 202001 retornar la suma
    # de los productos que pertenecen a la linea_n1
    bd2020 = BdVentas2020.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2021 = BdVentas2021.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2022 = BdVentas2022.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2023 = BdVentas2023.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2024 = BdVentas2024.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2025 = BdVentas2025.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    
    df1 = pd.DataFrame(list(bd2020))
    df2 = pd.DataFrame(list(bd2021))
    df3 = pd.DataFrame(list(bd2022))
    df4 = pd.DataFrame(list(bd2023))
    df5 = pd.DataFrame(list(bd2024))
    df6 = pd.DataFrame(list(bd2025))
    
    year_actual = timezone.now().year
    year_siguiente = timezone.now().year + 1
   
    df_total = pd.concat([df1, df2, df3, df4, df5, df6], ignore_index=True)
    print(df_total)
    # calcular suma por lapso y centro de operacion
    df_lapso_total = df_total.groupby('lapso')['suma'].sum().reset_index()
    df_centro_operacion = df_total.groupby(['centro_de_operacion', 'lapso'])['suma'].sum().reset_index()
    df_centro_operacion_segmento = df_total.groupby(['nombre_clase_cliente', 'centro_de_operacion', 'lapso'])['suma'].sum().reset_index()
    
    # ------------PROYECCION PRESUPUESTO GENERAL - CALUCLAR PREDICCIÓN PARA 2025 POR CADA MES -----------------------------------------
    # Extraer año y mes
    df_lapso_total['year'] = df_lapso_total['lapso'] // 100
    df_lapso_total['mes'] = df_lapso_total['lapso'] % 100
    # 📌 Suma por año
    df_por_año = df_lapso_total.groupby("year")["suma"].sum().reset_index()
    # 📌 Suma por mes (todos los años juntos, ej: todos los eneros, febreros, etc.)
    df_por_mes = df_lapso_total.groupby("mes")["suma"].sum().reset_index()
    # suma por año y mes
    df_por_year_mes = df_lapso_total.groupby(["year", "mes"])["suma"].sum().reset_index()
    
    # calcular predicción para 2025 por cada mes usando regresión lineal
    predicciones_2026_general = []
    # recorrer cada mes (1 a 12)
    for mes in range(1, 13):
        datos_mes = df_por_year_mes[df_por_year_mes["mes"] == mes]

        x = datos_mes["year"].values
        y = datos_mes["suma"].values

        if len(x) >= 2:  # se necesitan al menos 2 años
            a, b = np.polyfit(x, y, 1)  # ajuste lineal
            y_pred = a * year_siguiente + b
            predicciones_2026_general.append({
                "year": year_siguiente,
                "mes": mes,
                "suma_pred": round(y_pred),
                "lapso": year_siguiente * 100 + mes
            })

    # convertir a dataframe
    df_pred_2026_general = pd.DataFrame(predicciones_2026_general)
    # unir con df_por_year_mes
    df_proyeccion_general = pd.concat([df_lapso_total[['lapso', 'suma']], df_pred_2026_general[['lapso', 'suma_pred']].rename(columns={'suma_pred': 'suma'})], ignore_index=True)
   
    #extrer año y mes
    df_proyeccion_general['year'] = df_proyeccion_general['lapso'] // 100
    df_proyeccion_general['mes'] = df_proyeccion_general['lapso'] % 100
    # calcular el coeficiente de correlación R2 para la proyección general---
    correlaciones = []
    for mes in range(1, 13):
        datos_mes = df_proyeccion_general[df_proyeccion_general["mes"] == mes]

        if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
            coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
        else:
            coef = np.nan  # si no hay variación, correlación indefinida

        correlaciones.append({
            "mes": mes,
            "coef_correlacion": (round(coef, 4))*100 if not np.isnan(coef) else None
        })
    
    df_correl_por_mes = pd.DataFrame(correlaciones)
    
    # unir con el df_proyeccion_centro_operacion
    df_proyeccion_general = pd.merge(df_proyeccion_general, df_correl_por_mes, on='mes', how='left')
    df_proyeccion_general['suma'] = df_proyeccion_general['suma'].round().astype(int)
   
    # ----------CALCULAR PROYECCION PRESUPUESTO CENTRO DE OPERACION--------------------------------
    # Extraer año y mes
    df_centro_operacion['year'] = df_centro_operacion['lapso'] // 100
    df_centro_operacion['mes'] = df_centro_operacion['lapso'] % 100
    # Lista para almacenar predicciones por centro de operacion
    predicciones_2026_centro = []
    # Hacer predicción para cada centro de operacion y mes
    for centro, grupo in df_centro_operacion.groupby('centro_de_operacion'):
        for mes in range(1, 13):
            datos_mes = grupo[grupo['mes'] == mes]
            
            # Datos para regresión
            x = datos_mes['year'].values
            y = datos_mes['suma'].values

            if len(x) >= 2:  # Se necesita al menos 2 puntos para ajustar una recta
                a, b = np.polyfit(x, y, 1)  # Ajuste lineal
                y_pred = a * year_siguiente + b
                predicciones_2026_centro.append({'centro_de_operacion': centro, 'lapso': year_siguiente * 100 + mes, 'suma': round(y_pred)})
    # Crear DataFrame con predicciones
    df_pred_2026_centro = pd.DataFrame(predicciones_2026_centro)
    # (Opcional) Unir con el DataFrame original y ordenar por lapso y centro de operacion
    df_proyeccion_centro_operacion = pd.concat([df_centro_operacion[['centro_de_operacion', 'lapso', 'suma']], df_pred_2026_centro], ignore_index=True)
    df_proyeccion_centro_operacion = df_proyeccion_centro_operacion.sort_values(['centro_de_operacion', 'lapso']).reset_index(drop=True)
    # extraer año y mes
    df_proyeccion_centro_operacion['year'] = df_proyeccion_centro_operacion['lapso'] // 100
    df_proyeccion_centro_operacion['mes'] = df_proyeccion_centro_operacion['lapso'] % 100
    
    # calcular el coeficiente de correlación R2 para la proyección por centro de operacion y lapso -----------
    correlaciones_centro = []   
    for centro, grupo in df_proyeccion_centro_operacion.groupby('centro_de_operacion'):
        for mes in range(1, 13):
            datos_mes = grupo[grupo["mes"] == mes]

            if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
                coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
            else:
                coef = np.nan  # si no hay variación, correlación indefinida

            correlaciones_centro.append({
                "centro_de_operacion": centro,
                "mes": mes,
                "coef_correlacion": (round(coef, 4))*100 if not np.isnan(coef) else None
            })
    df_correl_por_mes_centro = pd.DataFrame(correlaciones_centro)
    # unir con el df_proyeccion_centro_operacion
    df_proyeccion_centro_operacion = pd.merge(df_proyeccion_centro_operacion, df_correl_por_mes_centro, on=['centro_de_operacion', 'mes'], how='left')
    df_proyeccion_centro_operacion['suma'] = df_proyeccion_centro_operacion['suma'].round().astype(int)   
    
    # ------------ CALCULAR PROYECCION PRESUPUESTO CENTRO DE OPERACION - SEGMENTO (CLASE CLIENTE) -----------------------------------------
    # Extraer año y mes
    # df_centro_operacion_segmento.to_excel("df_centro_operacion_segmento.xlsx")
    df_centro_operacion_segmento['year'] = df_centro_operacion_segmento['lapso'] // 100
    df_centro_operacion_segmento['mes'] = df_centro_operacion_segmento['lapso'] % 100
    # Lista para almacenar predicciones por centro de operacion y segmento
    predicciones_2026_centro_segmento = []
    # Hacer predicción para cada centro de operacion, segmento y mes
    for (centro, segmento), grupo in df_centro_operacion_segmento.groupby(['centro_de_operacion', 'nombre_clase_cliente']):
        for mes in range(1, 13):
            datos_mes = grupo[grupo['mes'] == mes]
            
            # Datos para regresión
            x = datos_mes['year'].values
            y = datos_mes['suma'].values

            if len(x) >= 2:  # Se necesita al menos 2 puntos para ajustar una recta
                a, b = np.polyfit(x, y, 1)  # Ajuste lineal
                y_pred = a * year_siguiente + b
                predicciones_2026_centro_segmento.append({'centro_de_operacion': centro, 'nombre_clase_cliente': segmento, 'lapso': year_siguiente * 100 + mes, 'suma': round(y_pred)})
    # Crear DataFrame con predicciones
    df_pred_2026_centro_segmento = pd.DataFrame(predicciones_2026_centro_segmento)
    # (Opcional) Unir con el DataFrame original y ordenar por lapso, centro de operacion y segmento
    df_proyeccion_centro_operacion_segmento = pd.concat([df_centro_operacion_segmento[['centro_de_operacion', 'nombre_clase_cliente', 'lapso', 'suma']], df_pred_2026_centro_segmento], ignore_index=True)
    df_proyeccion_centro_operacion_segmento = df_proyeccion_centro_operacion_segmento.sort_values(['centro_de_operacion', 'nombre_clase_cliente', 'lapso']).reset_index(drop=True)
    # extraer año y mes
    df_proyeccion_centro_operacion_segmento['year'] = df_proyeccion_centro_operacion_segmento['lapso'] // 100
    df_proyeccion_centro_operacion_segmento['mes'] = df_proyeccion_centro_operacion_segmento['lapso'] % 100
    
    # ----------------------------calcular el coeficiente de correlación R2 para la proyección por centro de operacion, segmento y lapso ----------------------------
    correlaciones_centro_segmento = []
    for (centro, segmento), grupo in df_proyeccion_centro_operacion_segmento.groupby(['centro_de_operacion', 'nombre_clase_cliente']):
        for mes in range(1, 13):
            datos_mes = grupo[grupo["mes"] == mes]

            if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
                coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
            else:
                coef = np.nan  # si no hay variación, correlación indefinida

            correlaciones_centro_segmento.append({
                "centro_de_operacion": centro,
                "nombre_clase_cliente": segmento,
                "mes": mes,
                "coef_correlacion": (round(coef, 4))*100 if not np.isnan(coef) else None
            })
    df_correl_por_mes_centro_segmento = pd.DataFrame(correlaciones_centro_segmento)
    # unir con el df_proyeccion_centro_operacion_segmento
    df_proyeccion_centro_operacion_segmento = pd.merge(df_proyeccion_centro_operacion_segmento, df_correl_por_mes_centro_segmento, on=['centro_de_operacion', 'nombre_clase_cliente', 'mes'], how='left')
    df_proyeccion_centro_operacion_segmento['suma'] = df_proyeccion_centro_operacion_segmento['suma'].round().astype(int)
    
    #------------------------------------------------------PRONOSTICO FINAL---------------------------------------------------
    # Lista para almacenar predicciones
    predicciones_2026 = []

    # Hacer predicción para cada mes
    for mes in range(1, 13):
        datos_mes = df_lapso_total[df_lapso_total['mes'] == mes]
        
        # Datos para regresión
        x = datos_mes['year'].values
        y = datos_mes['suma'].values

        if len(x) >= 2:  # Se necesita al menos 2 puntos para ajustar una recta
            a, b = np.polyfit(x, y, 1)  # Ajuste lineal
            y_pred = a * year_siguiente + b
            predicciones_2026.append({'lapso': year_siguiente * 100 + mes, 'suma': round(y_pred)})

    # Crear DataFrame con predicciones
    df_pred_2026_general = pd.DataFrame(predicciones_2026)

    # Concatenar los dataframes para el dinamismo
    df_dinamismo = pd.concat([df1, df2, df3, df4, df5, df6], ignore_index=True)
    
    # Extraer el año desde 'lapso'
    df_dinamismo['year'] = df_dinamismo['lapso'] // 100

    # Agrupar por nombre de producto, año, y sumar
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
            y_pred = a * year_siguiente + b
            predicciones.append({
                'nombre_linea_n1': nombre,
                'year': year_siguiente,
                'suma': round(y_pred)
            })

    # Crear DataFrame con predicciones
    df_pred_2026_pro_lineal = pd.DataFrame(predicciones)
    df_final_pronostico = pd.concat([df_agrupado, df_pred_2026_pro_lineal], ignore_index=True)
    df_final_pronostico = df_final_pronostico.sort_values(by=['nombre_linea_n1', 'year']).reset_index(drop=True)
    
    # R2 ----------------------------------------------
    # Lista para almacenar resultados
    correlaciones = []
    # Agrupar por producto
    for nombre, grupo in df_final_pronostico.groupby('nombre_linea_n1'):
        x = grupo['year'].values
        y = grupo['suma'].values

        if len(x) >= 2 and np.std(y) != 0 and np.std(x) != 0:  # evitar división por 0
            coef = np.corrcoef(x, y)[0, 1]
            coef_abs_pct = abs(coef) * 100  # valor absoluto en porcentaje
        else:
            coef_abs_pct = 0.0  # o NaN si prefieres marcarlo

        correlaciones.append({
            'nombre_linea_n1': nombre,
            'R2': round(coef_abs_pct, 2)
        })

    # Crear DataFrame con los coeficientes
    df_correlaciones = pd.DataFrame(correlaciones)
    
    # concatenar con el df_final_pronostico
    df_final_pronostico = pd.merge(df_final_pronostico, df_correlaciones, on='nombre_linea_n1', how='left')
   
    # ---------------------calcular variacion porcentual entre 2025 y 2026-------------------------------
    df_2025 = df_final_pronostico[df_final_pronostico['year'] == year_actual][['nombre_linea_n1', 'suma']].rename(columns={'suma': 'suma_2024'})
    df_2026 = df_final_pronostico[df_final_pronostico['year'] == year_siguiente][['nombre_linea_n1', 'suma']].rename(columns={'suma': 'suma_2025'})
    df_variacion = pd.merge(df_2025, df_2026, on='nombre_linea_n1')
    df_variacion['variacion_pct'] = ((df_variacion['suma_2025'] - df_variacion['suma_2024']) / df_variacion['suma_2024']) * 100
    df_variacion['variacion_pct'] = df_variacion['variacion_pct'].round(2)
    
    # calcular variacion en valor en pesos entre 2024 y 2025
    df_variacion['variacion_valor'] = df_variacion['suma_2025'] - df_variacion['suma_2024']
    # calcular variacion mes, es decir, dividir la variacion_valor entre 12
    df_variacion['variacion_mes'] = (df_variacion['variacion_valor'] / 12).round().astype(int)
    # calcular variacion precios, es decir, tomar el año anterior(2024) y multiplicarlo por el 2%
    df_variacion['variacion_precios'] = (df_variacion['suma_2024'] * 0.02).round().astype(int)
    # calcular crecimiento comercial, es decir, restar la variacion_pct y la variacion_precios
    df_variacion['crecimiento_comercial'] = (df_variacion['variacion_valor'] - df_variacion['variacion_precios']).round().astype(int) 
    # calcular crecimiento comercial mes, es decir, dividir el crecimiento_comercial entre 12
    df_variacion['crecimiento_comercial_mes'] = (df_variacion['crecimiento_comercial'] / 12).round().astype(int)
    
    # concatenar con el df_final_pronostico
    df_final_pronostico = pd.merge(df_final_pronostico, df_variacion[['nombre_linea_n1', 'variacion_pct', 'variacion_valor', 'variacion_mes', 'variacion_precios', 'crecimiento_comercial', 'crecimiento_comercial_mes']], on='nombre_linea_n1', how='left')
  
    
    # convertir a diccionario para enviar a la vista y renderizar en la tabla el pronostico final
    # data = data.to_dict(orient='records')
    # proyección presupuesto general
    # proyeccion_general = df_proyeccion_general.to_dict(orient='records')
    # # proyección presupuesto centro de operacion
    # proyeccion_centro_operacion = df_proyeccion_centro_operacion.to_dict(orient='records')
    # # proyección presupuesto centro de operacion - segmento
    # proyeccion_centro_operacion_segmento = df_proyeccion_centro_operacion_segmento.to_dict(orient='records')
    
    return df_proyeccion_general, df_proyeccion_centro_operacion, df_proyeccion_centro_operacion_segmento, df_final_pronostico


def presupuesto_comercial(request):
    # obtener la suma de cada mes y nombre_linea_n1 es decir, si el lapso es 202001 retornar la suma
    # de los productos que pertenecen a la linea_n1
    bd2020 = BdVentas2020.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2021 = BdVentas2021.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2022 = BdVentas2022.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2023 = BdVentas2023.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2024 = BdVentas2024.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2025 = BdVentas2025.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    
    df1 = pd.DataFrame(list(bd2020))
    df2 = pd.DataFrame(list(bd2021))
    df3 = pd.DataFrame(list(bd2022))
    df4 = pd.DataFrame(list(bd2023))
    df5 = pd.DataFrame(list(bd2024))
    df6 = pd.DataFrame(list(bd2025))
    
    year_anterior = timezone.now().year - 1
    year_actual = timezone.now().year
    year_siguiente = timezone.now().year + 1
   
    df_total = pd.concat([df1, df2, df3, df4, df5, df6], ignore_index=True)
    print(df_total)
    # calcular suma por lapso y centro de operacion
    df_lapso_total = df_total.groupby('lapso')['suma'].sum().reset_index()
    df_centro_operacion = df_total.groupby(['centro_de_operacion', 'lapso'])['suma'].sum().reset_index()
    df_centro_operacion_segmento = df_total.groupby(['nombre_clase_cliente', 'centro_de_operacion', 'lapso'])['suma'].sum().reset_index()
    
    # ------------PROYECCION PRESUPUESTO GENERAL - CALUCLAR PREDICCIÓN PARA 2025 POR CADA MES -----------------------------------------
    # Extraer año y mes
    df_lapso_total['year'] = df_lapso_total['lapso'] // 100
    df_lapso_total['mes'] = df_lapso_total['lapso'] % 100
    # 📌 Suma por año
    df_por_año = df_lapso_total.groupby("year")["suma"].sum().reset_index()
    # 📌 Suma por mes (todos los años juntos, ej: todos los eneros, febreros, etc.)
    df_por_mes = df_lapso_total.groupby("mes")["suma"].sum().reset_index()
    # suma por año y mes
    df_por_year_mes = df_lapso_total.groupby(["year", "mes"])["suma"].sum().reset_index()
    
    # calcular predicción para 2025 por cada mes usando regresión lineal
    predicciones_2026_general = []
    # recorrer cada mes (1 a 12)
    for mes in range(1, 13):
        datos_mes = df_por_year_mes[df_por_year_mes["mes"] == mes]

        x = datos_mes["year"].values
        y = datos_mes["suma"].values

        if len(x) >= 2:  # se necesitan al menos 2 años
            a, b = np.polyfit(x, y, 1)  # ajuste lineal
            y_pred = a * year_siguiente + b
            predicciones_2026_general.append({
                "year": year_siguiente,
                "mes": mes,
                "suma_pred": round(y_pred),
                "lapso": year_siguiente * 100 + mes
            })

    # convertir a dataframe
    df_pred_2026_general = pd.DataFrame(predicciones_2026_general)
    # unir con df_por_year_mes
    df_proyeccion_general = pd.concat([df_lapso_total[['lapso', 'suma']], df_pred_2026_general[['lapso', 'suma_pred']].rename(columns={'suma_pred': 'suma'})], ignore_index=True)
   
    #extrer año y mes
    df_proyeccion_general['year'] = df_proyeccion_general['lapso'] // 100
    df_proyeccion_general['mes'] = df_proyeccion_general['lapso'] % 100
    # calcular el coeficiente de correlación R2 para la proyección general---
    correlaciones = []
    for mes in range(1, 13):
        datos_mes = df_proyeccion_general[df_proyeccion_general["mes"] == mes]

        if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
            coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
        else:
            coef = np.nan  # si no hay variación, correlación indefinida

        correlaciones.append({
            "mes": mes,
            "coef_correlacion": (round(coef, 4))*100 if not np.isnan(coef) else None
        })
    
    df_correl_por_mes = pd.DataFrame(correlaciones)
    
    # unir con el df_proyeccion_centro_operacion
    df_proyeccion_general = pd.merge(df_proyeccion_general, df_correl_por_mes, on='mes', how='left')
    df_proyeccion_general['suma'] = df_proyeccion_general['suma'].round().astype(int)
   
    # ----------CALCULAR PROYECCION PRESUPUESTO CENTRO DE OPERACION--------------------------------
    # Extraer año y mes
    df_centro_operacion['year'] = df_centro_operacion['lapso'] // 100
    df_centro_operacion['mes'] = df_centro_operacion['lapso'] % 100
    # Lista para almacenar predicciones por centro de operacion
    predicciones_2026_centro = []
    # Hacer predicción para cada centro de operacion y mes
    for centro, grupo in df_centro_operacion.groupby('centro_de_operacion'):
        for mes in range(1, 13):
            datos_mes = grupo[grupo['mes'] == mes]
            
            # Datos para regresión
            x = datos_mes['year'].values
            y = datos_mes['suma'].values

            if len(x) >= 2:  # Se necesita al menos 2 puntos para ajustar una recta
                a, b = np.polyfit(x, y, 1)  # Ajuste lineal
                y_pred = a * year_siguiente + b
                predicciones_2026_centro.append({'centro_de_operacion': centro, 'lapso': year_siguiente * 100 + mes, 'suma': round(y_pred)})
    # Crear DataFrame con predicciones
    df_pred_2026_centro = pd.DataFrame(predicciones_2026_centro)
    # (Opcional) Unir con el DataFrame original y ordenar por lapso y centro de operacion
    df_proyeccion_centro_operacion = pd.concat([df_centro_operacion[['centro_de_operacion', 'lapso', 'suma']], df_pred_2026_centro], ignore_index=True)
    df_proyeccion_centro_operacion = df_proyeccion_centro_operacion.sort_values(['centro_de_operacion', 'lapso']).reset_index(drop=True)
    # extraer año y mes
    df_proyeccion_centro_operacion['year'] = df_proyeccion_centro_operacion['lapso'] // 100
    df_proyeccion_centro_operacion['mes'] = df_proyeccion_centro_operacion['lapso'] % 100
    
    # calcular el coeficiente de correlación R2 para la proyección por centro de operacion y lapso -----------
    correlaciones_centro = []   
    for centro, grupo in df_proyeccion_centro_operacion.groupby('centro_de_operacion'):
        for mes in range(1, 13):
            datos_mes = grupo[grupo["mes"] == mes]

            if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
                coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
            else:
                coef = np.nan  # si no hay variación, correlación indefinida

            correlaciones_centro.append({
                "centro_de_operacion": centro,
                "mes": mes,
                "coef_correlacion": (round(coef, 4))*100 if not np.isnan(coef) else None
            })
    df_correl_por_mes_centro = pd.DataFrame(correlaciones_centro)
    # unir con el df_proyeccion_centro_operacion
    df_proyeccion_centro_operacion = pd.merge(df_proyeccion_centro_operacion, df_correl_por_mes_centro, on=['centro_de_operacion', 'mes'], how='left')
    df_proyeccion_centro_operacion['suma'] = df_proyeccion_centro_operacion['suma'].round().astype(int)   
    
    # ------------ CALCULAR PROYECCION PRESUPUESTO CENTRO DE OPERACION - SEGMENTO (CLASE CLIENTE) -----------------------------------------
    # Extraer año y mes
    # df_centro_operacion_segmento.to_excel("df_centro_operacion_segmento.xlsx")
    df_centro_operacion_segmento['year'] = df_centro_operacion_segmento['lapso'] // 100
    df_centro_operacion_segmento['mes'] = df_centro_operacion_segmento['lapso'] % 100
    # Lista para almacenar predicciones por centro de operacion y segmento
    predicciones_2026_centro_segmento = []
    # Hacer predicción para cada centro de operacion, segmento y mes
    for (centro, segmento), grupo in df_centro_operacion_segmento.groupby(['centro_de_operacion', 'nombre_clase_cliente']):
        for mes in range(1, 13):
            datos_mes = grupo[grupo['mes'] == mes]
            
            # Datos para regresión
            x = datos_mes['year'].values
            y = datos_mes['suma'].values

            if len(x) >= 2:  # Se necesita al menos 2 puntos para ajustar una recta
                a, b = np.polyfit(x, y, 1)  # Ajuste lineal
                y_pred = a * year_siguiente + b
                predicciones_2026_centro_segmento.append({'centro_de_operacion': centro, 'nombre_clase_cliente': segmento, 'lapso': year_siguiente * 100 + mes, 'suma': round(y_pred)})
    # Crear DataFrame con predicciones
    df_pred_2026_centro_segmento = pd.DataFrame(predicciones_2026_centro_segmento)
    # (Opcional) Unir con el DataFrame original y ordenar por lapso, centro de operacion y segmento
    df_proyeccion_centro_operacion_segmento = pd.concat([df_centro_operacion_segmento[['centro_de_operacion', 'nombre_clase_cliente', 'lapso', 'suma']], df_pred_2026_centro_segmento], ignore_index=True)
    df_proyeccion_centro_operacion_segmento = df_proyeccion_centro_operacion_segmento.sort_values(['centro_de_operacion', 'nombre_clase_cliente', 'lapso']).reset_index(drop=True)
    # extraer año y mes
    df_proyeccion_centro_operacion_segmento['year'] = df_proyeccion_centro_operacion_segmento['lapso'] // 100
    df_proyeccion_centro_operacion_segmento['mes'] = df_proyeccion_centro_operacion_segmento['lapso'] % 100
    
    # ----------------------------calcular el coeficiente de correlación R2 para la proyección por centro de operacion, segmento y lapso ----------------------------
    correlaciones_centro_segmento = []
    for (centro, segmento), grupo in df_proyeccion_centro_operacion_segmento.groupby(['centro_de_operacion', 'nombre_clase_cliente']):
        for mes in range(1, 13):
            datos_mes = grupo[grupo["mes"] == mes]

            if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
                coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
            else:
                coef = np.nan  # si no hay variación, correlación indefinida

            correlaciones_centro_segmento.append({
                "centro_de_operacion": centro,
                "nombre_clase_cliente": segmento,
                "mes": mes,
                "coef_correlacion": (round(coef, 4))*100 if not np.isnan(coef) else None
            })
    df_correl_por_mes_centro_segmento = pd.DataFrame(correlaciones_centro_segmento)
    # unir con el df_proyeccion_centro_operacion_segmento
    df_proyeccion_centro_operacion_segmento = pd.merge(df_proyeccion_centro_operacion_segmento, df_correl_por_mes_centro_segmento, on=['centro_de_operacion', 'nombre_clase_cliente', 'mes'], how='left')
    df_proyeccion_centro_operacion_segmento['suma'] = df_proyeccion_centro_operacion_segmento['suma'].round().astype(int)
    
    #------------------------------------------------------PRONOSTICO FINAL---------------------------------------------------
    # Lista para almacenar predicciones
    predicciones_2026 = []

    # Hacer predicción para cada mes
    for mes in range(1, 13):
        datos_mes = df_lapso_total[df_lapso_total['mes'] == mes]
        
        # Datos para regresión
        x = datos_mes['year'].values
        y = datos_mes['suma'].values

        if len(x) >= 2:  # Se necesita al menos 2 puntos para ajustar una recta
            a, b = np.polyfit(x, y, 1)  # Ajuste lineal
            y_pred = a * year_siguiente + b
            predicciones_2026.append({'lapso': year_siguiente * 100 + mes, 'suma': round(y_pred)})

    # Crear DataFrame con predicciones
    df_pred_2026_general = pd.DataFrame(predicciones_2026)

    # Concatenar los dataframes para el dinamismo
    df_dinamismo = pd.concat([df1, df2, df3, df4, df5, df6], ignore_index=True)
    
    # Extraer el año desde 'lapso'
    df_dinamismo['year'] = df_dinamismo['lapso'] // 100

    # Agrupar por nombre de producto, año, y sumar
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
            y_pred = a * year_siguiente + b
            predicciones.append({
                'nombre_linea_n1': nombre,
                'year': year_siguiente,
                'suma': round(y_pred)
            })

    # Crear DataFrame con predicciones
    df_pred_2026_pro_lineal = pd.DataFrame(predicciones)
    df_final_pronostico = pd.concat([df_agrupado, df_pred_2026_pro_lineal], ignore_index=True)
    df_final_pronostico = df_final_pronostico.sort_values(by=['nombre_linea_n1', 'year']).reset_index(drop=True)
    
    # R2 ----------------------------------------------
    # Lista para almacenar resultados
    correlaciones = []
    # Agrupar por producto
    for nombre, grupo in df_final_pronostico.groupby('nombre_linea_n1'):
        x = grupo['year'].values
        y = grupo['suma'].values

        if len(x) >= 2 and np.std(y) != 0 and np.std(x) != 0:  # evitar división por 0
            coef = np.corrcoef(x, y)[0, 1]
            coef_abs_pct = abs(coef) * 100  # valor absoluto en porcentaje
        else:
            coef_abs_pct = 0.0  # o NaN si prefieres marcarlo

        correlaciones.append({
            'nombre_linea_n1': nombre,
            'R2': round(coef_abs_pct, 2)
        })

    # Crear DataFrame con los coeficientes
    df_correlaciones = pd.DataFrame(correlaciones)
    
    # concatenar con el df_final_pronostico
    df_final_pronostico = pd.merge(df_final_pronostico, df_correlaciones, on='nombre_linea_n1', how='left')
   
    # ---------------------calcular variacion porcentual entre 2025 y 2026-------------------------------
    df_2025 = df_final_pronostico[df_final_pronostico['year'] == year_actual][['nombre_linea_n1', 'suma']].rename(columns={'suma': 'suma_2024'})
    df_2026 = df_final_pronostico[df_final_pronostico['year'] == year_siguiente][['nombre_linea_n1', 'suma']].rename(columns={'suma': 'suma_2025'})
    df_variacion = pd.merge(df_2025, df_2026, on='nombre_linea_n1')
    df_variacion['variacion_pct'] = ((df_variacion['suma_2025'] - df_variacion['suma_2024']) / df_variacion['suma_2024']) * 100
    df_variacion['variacion_pct'] = df_variacion['variacion_pct'].round(2)
    
    # calcular variacion en valor en pesos entre 2024 y 2025
    df_variacion['variacion_valor'] = df_variacion['suma_2025'] - df_variacion['suma_2024']
    # calcular variacion mes, es decir, dividir la variacion_valor entre 12
    df_variacion['variacion_mes'] = (df_variacion['variacion_valor'] / 12).round().astype(int)
    # calcular variacion precios, es decir, tomar el año anterior(2024) y multiplicarlo por el 2%
    df_variacion['variacion_precios'] = (df_variacion['suma_2024'] * 0.02).round().astype(int)
    # calcular crecimiento comercial, es decir, restar la variacion_pct y la variacion_precios
    df_variacion['crecimiento_comercial'] = (df_variacion['variacion_valor'] - df_variacion['variacion_precios']).round().astype(int) 
    # calcular crecimiento comercial mes, es decir, dividir el crecimiento_comercial entre 12
    df_variacion['crecimiento_comercial_mes'] = (df_variacion['crecimiento_comercial'] / 12).round().astype(int)
    
    # concatenar con el df_final_pronostico
    df_final_pronostico = pd.merge(df_final_pronostico, df_variacion[['nombre_linea_n1', 'variacion_pct', 'variacion_valor', 'variacion_mes', 'variacion_precios', 'crecimiento_comercial', 'crecimiento_comercial_mes']], on='nombre_linea_n1', how='left')
    
    # convertir a diccionario para enviar a la vista y renderizar en la tabla el pronostico final
    # data = data.to_dict(orient='records')
    # proyección presupuesto general
    proyeccion_general = df_proyeccion_general.to_dict(orient='records')
    # proyección presupuesto centro de operacion
    proyeccion_centro_operacion = df_proyeccion_centro_operacion.to_dict(orient='records')
    # proyección presupuesto centro de operacion - segmento
    proyeccion_centro_operacion_segmento = df_proyeccion_centro_operacion_segmento.to_dict(orient='records')
    
    #-----------COSTOS----------------------
    df_proyeccion_general_costos, df_proyeccion_centro_operacion_costos, df_proyeccion_centro_operacion_segmento_costos, df_final_pronostico_costos = presupuesto_comercial_costos()
    
    #unir df_final_pronostico con df_final_pronostico_costos
    df_final_neto_costos = pd.merge(df_final_pronostico, df_final_pronostico_costos, on=['nombre_linea_n1', 'year']) # x= netos y= costos
    
    #-------------------UTILIDAD----------------------- 
    # calcular utilidad por año, 1 - (costos / ventas), el costo está en el df_fnal_pronostico_costos es decir la predicción, y las ventas están en el df_fnal_pronostico
    df_final_neto_costos['utilidad'] = (1 - (df_final_neto_costos['suma_y'] / df_final_neto_costos['suma_x'])) * 100
    df_final_neto_costos['utilidad'] = df_final_neto_costos['utilidad'].round(2)
    # llenar los valores infinitos o NaN con 0
    df_final_neto_costos['utilidad'] = df_final_neto_costos['utilidad'].replace([np.inf, -np.inf], 0).fillna(0)
    # renombrar columnas
    df_final_neto_costos = df_final_neto_costos.rename(columns={'suma_x': 'ventas', 'suma_y': 'costos'})    
    # calcular utilidad en valor
    df_final_neto_costos['utilidad_valor'] = df_final_neto_costos['ventas'] - df_final_neto_costos['costos']
    
    # agregar un cero a las columnas vacias
    df_final_neto_costos['variacion_pct_x'] = df_final_neto_costos['variacion_pct_x'].fillna(0)
    df_final_neto_costos['variacion_valor_x'] = df_final_neto_costos['variacion_valor_x'].fillna(0)
    df_final_neto_costos['variacion_mes_x'] = df_final_neto_costos['variacion_mes_x'].fillna(0)
    df_final_neto_costos['variacion_precios_x'] = df_final_neto_costos['variacion_precios_x'].fillna(0)
    df_final_neto_costos['crecimiento_comercial_x'] = df_final_neto_costos['crecimiento_comercial_x'].fillna(0)
    df_final_neto_costos['crecimiento_comercial_mes_x'] = df_final_neto_costos['crecimiento_comercial_mes_x'].fillna(0)
    df_final_neto_costos['variacion_pct_y'] = df_final_neto_costos['variacion_pct_y'].fillna(0)
    df_final_neto_costos['variacion_valor_y'] = df_final_neto_costos['variacion_valor_y'].fillna(0)
    df_final_neto_costos['variacion_mes_y'] = df_final_neto_costos['variacion_mes_y'].fillna(0)
    df_final_neto_costos['variacion_precios_y'] = df_final_neto_costos['variacion_precios_y'].fillna(0)
    df_final_neto_costos['crecimiento_comercial_y'] = df_final_neto_costos['crecimiento_comercial_y'].fillna(0)
    df_final_neto_costos['crecimiento_comercial_mes_y'] = df_final_neto_costos['crecimiento_comercial_mes_y'].fillna(0)
    
    # redondear las columnas que son float a int
    columnas_a_redondear = ['ventas', 'costos', 'utilidad_valor', 'variacion_valor_x', 'variacion_mes_x', 'variacion_precios_x', 'crecimiento_comercial_x', 'crecimiento_comercial_mes_x', 'variacion_valor_y', 'variacion_mes_y', 'variacion_precios_y', 'crecimiento_comercial_y', 'crecimiento_comercial_mes_y']
    df_final_neto_costos[columnas_a_redondear] = df_final_neto_costos[columnas_a_redondear].round().astype(int)
    
    # df_final_neto_costos.to_excel('df_final_neto_costos.xlsx', index=False)
    data = df_final_neto_costos.to_dict(orient='records')
    
    proyeccion_general_costos = df_proyeccion_general_costos.to_dict(orient='records')
    proyeccion_centro_operacion_costos = df_proyeccion_centro_operacion_costos.to_dict(orient='records')
    proyeccion_centro_operacion_segmento_costos = df_proyeccion_centro_operacion_segmento_costos.to_dict(orient='records')
    data_costos = df_final_pronostico_costos.to_dict(orient='records')
    
    return render(request, 'presupuesto_comercial/presupuesto_comercial copy.html', {'data': data, 'proyeccion_general': proyeccion_general, 'proyeccion_centro_operacion': proyeccion_centro_operacion, 'proyeccion_centro_operacion_segmento': proyeccion_centro_operacion_segmento, 'proyeccion_general_costos': proyeccion_general_costos, 'proyeccion_centro_operacion_costos': proyeccion_centro_operacion_costos, 'proyeccion_centro_operacion_segmento_costos': proyeccion_centro_operacion_segmento_costos, 'data_costos': data_costos})

# ------------------------------------------PRESUPUESTO GENERAL VENTAS-----------------------------------------------------
def cargar_presupuesto_general_ventas(request):
    # de los productos que pertenecen a la linea_n1
    bd2020 = BdVentas2020.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2021 = BdVentas2021.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2022 = BdVentas2022.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2023 = BdVentas2023.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2024 = BdVentas2024.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2025 = BdVentas2025.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    
    df1 = pd.DataFrame(list(bd2020))
    df2 = pd.DataFrame(list(bd2021))
    df3 = pd.DataFrame(list(bd2022))
    df4 = pd.DataFrame(list(bd2023))
    df5 = pd.DataFrame(list(bd2024))
    df6 = pd.DataFrame(list(bd2025))
    
    year_actual = timezone.now().year
    year_siguiente = timezone.now().year + 1
    
    df_total = pd.concat([df1, df2, df3, df4, df5, df6], ignore_index=True)
    # print(df_total)
    # calcular suma por lapso y centro de operacion
    df_lapso_total = df_total.groupby('lapso')['suma'].sum().reset_index()
    
    # ------------PROYECCION PRESUPUESTO GENERAL - CALUCLAR PREDICCIÓN PARA 2025 POR CADA MES -----------------------------------------
    # Extraer año y mes
    df_lapso_total['year'] = df_lapso_total['lapso'] // 100
    df_lapso_total['mes'] = df_lapso_total['lapso'] % 100
    
    df_por_year_mes = df_lapso_total.groupby(["year", "mes"])["suma"].sum().reset_index()
    
    # calcular predicción para 2025 por cada mes usando regresión lineal
    predicciones_2026_general = []
    # recorrer cada mes (1 a 12)
    for mes in range(1, 13):
        datos_mes = df_por_year_mes[df_por_year_mes["mes"] == mes]

        x = datos_mes["year"].values
        y = datos_mes["suma"].values

        if len(x) >= 2:  # se necesitan al menos 2 años
            a, b = np.polyfit(x, y, 1)  # ajuste lineal
            y_pred = a * year_siguiente + b
            predicciones_2026_general.append({
                "year": year_siguiente,
                "mes": mes,
                "suma_pred": round(y_pred),
                "lapso": year_siguiente * 100 + mes
            })

    # convertir a dataframe
    df_pred_2025_general = pd.DataFrame(predicciones_2026_general)
    # unir con df_por_year_mes
    df_proyeccion_general = pd.concat([df_lapso_total[['lapso', 'suma']], df_pred_2025_general[['lapso', 'suma_pred']].rename(columns={'suma_pred': 'suma'})], ignore_index=True)
    
    df_proyeccion_general['year'] = df_proyeccion_general['lapso'] // 100
    df_por_año = df_proyeccion_general.groupby("year")["suma"].sum().reset_index()
    df_por_año = df_por_año.sort_values("year").reset_index(drop=True)
    df_por_año["variacion_pesos"] = (df_por_año["suma"].diff()).round().astype('Int64')
    df_por_año["variacion_pct"] = (df_por_año["suma"].pct_change() * 100).round(2)
    df_por_año["variacion_pct"] = df_por_año["variacion_pct"].fillna(0)
    df_por_año["variacion_pesos"] = df_por_año["variacion_pesos"].fillna(0) 
    # renombrar suma por total
    df_por_año = df_por_año.rename(columns={'suma': 'total'})
    
    # ================== COSTOS: total_year ==============================
    costos = PresupuestoGeneralCostos.objects.values("year", "total_year")
    df_costos = pd.DataFrame(list(costos)).rename(columns={"total_year": "total_year_costos"})

    # Merge ventas + costos
    df_por_año = pd.merge(df_por_año, df_costos, on="year", how="left")
    
    #extrer año y mes
    df_proyeccion_general['mes'] = df_proyeccion_general['lapso'] % 100
    # calcular el coeficiente de correlación R2 para la proyección general---
    correlaciones = []
    for mes in range(1, 13):
        datos_mes = df_proyeccion_general[df_proyeccion_general["mes"] == mes]

        if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
            coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
        else:
            coef = np.nan  # si no hay variación, correlación indefinida

        correlaciones.append({
            "mes": mes,
            "coef_correlacion": (round(coef, 4))*100 if not np.isnan(coef) else None
        })
    
    df_correl_por_mes = pd.DataFrame(correlaciones)
    
    # unir con el df_proyeccion_centro_operacion
    df_proyeccion_general = pd.merge(df_proyeccion_general, df_correl_por_mes, on='mes', how='left')
    df_proyeccion_general['suma'] = df_proyeccion_general['suma'].round().astype(int)

    # merge de df_proyeccion_general con df_por_año para agregar las columnas de variacion_pesos y variacion_pct
    df_proyeccion_general = pd.merge(df_proyeccion_general, df_por_año[['year', 'total', 'total_year_costos','variacion_pesos', 'variacion_pct']], on='year', how='left')
    # calcular utilidad por año, 1 - (costos / ventas), el costo está en el df_proyeccion_general y se encuentra en la columna total_year_costos, y las ventas están en la columna total
    df_proyeccion_general['utilidad_pct'] = (1 - (df_proyeccion_general['total_year_costos'] / df_proyeccion_general['total'])) * 100
    df_proyeccion_general['utilidad_pct'] = df_proyeccion_general['utilidad_pct'].round(2)
    # llenar los valores infinitos o NaN con 0
    df_proyeccion_general['utilidad_pct'] = df_proyeccion_general['utilidad_pct'].replace([np.inf, -np.inf], 0).fillna(0)
    # utilidad en valor
    df_proyeccion_general['utilidad_valor'] = df_proyeccion_general['total'] - df_proyeccion_general['total_year_costos']
    df_proyeccion_general['utilidad_valor'] = df_proyeccion_general['utilidad_valor'].round().astype(int)
    
    # ----------- GUARDAR EN LA BD ------------
    registros = []
    for _, row in df_proyeccion_general.iterrows():
        registros.append(
            PresupuestoGeneralVentas(
                year=int(row['year']),
                mes=int(row['mes']),
                total=int(row['suma']),
                r2=row['coef_correlacion'] if row['coef_correlacion'] is not None else 0,
                total_year=row['total'] if row['total'] is not None else 0,
                total_year_costos=row['total_year_costos'] if row['total_year_costos'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0,
                utilidad_pct=row['utilidad_pct'] if row['utilidad_pct'] is not None else 0,
                utilidad_valor=row['utilidad_valor'] if row['utilidad_valor'] is not None else 0,
            )
        )

    # Opcional: limpiar tabla antes de insertar para evitar duplicados
    PresupuestoGeneralVentas.objects.all().delete()
    PresupuestoGeneralVentas.objects.bulk_create(registros)
    
    data = list(PresupuestoGeneralVentas.objects.values())
    return JsonResponse(data, safe=False) 

@csrf_exempt
def guardar_presupuesto_general_ventas(request):
    print("Guardar presupuesto general ventas")
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # 📥 datos editados del DataTable
            df = pd.DataFrame(data)

            # --- asegurarse de que los tipos sean correctos ---
            df["year"] = df["year"].astype(int)
            df["mes"] = df["mes"].astype(int)
            df["total"] = df["total"].astype(int)

            # --- recalcular coeficiente de correlación R² por mes ---
            correlaciones = []
            for mes in range(1, 13):
                datos_mes = df[df["mes"] == mes]

                if len(datos_mes) >= 2 and datos_mes["total"].std() != 0:
                    coef = np.corrcoef(datos_mes["year"], datos_mes["total"])[0, 1]
                else:
                    coef = np.nan

                correlaciones.append({
                    "mes": mes,
                    "coef_correlacion": (round(coef, 4)) * 100 if not np.isnan(coef) else 0
                })

            df_correl = pd.DataFrame(correlaciones)

            # unir correlaciones recalculadas con los datos originales
            df = pd.merge(df, df_correl, on="mes", how="left")

            # --- guardar en la BD ---
            registros = []
            for _, row in df.iterrows():
                registros.append(
                    PresupuestoGeneralVentas(
                        year=int(row["year"]),
                        mes=int(row["mes"]),
                        total=int(row["total"]),
                        r2=row["coef_correlacion"]
                    )
                )

            PresupuestoGeneralVentas.objects.all().delete()
            PresupuestoGeneralVentas.objects.bulk_create(registros)

            data = list(PresupuestoGeneralVentas.objects.values())
            return JsonResponse(data, safe=False)

        except Exception as e:
            return JsonResponse({"status": "error", "mensaje": str(e)}, status=400)

    return JsonResponse({"status": "error", "mensaje": "Método no permitido"}, status=405)

def obtener_presupuesto_general_ventas(request):
    data = list(PresupuestoGeneralVentas.objects.values())
    return JsonResponse(data, safe=False)

def vista_presupuesto_general_ventas(request):
    return render(request, 'presupuesto_comercial/presupuesto_general_ventas.html')

# PRESUPUESTO POR CENTRO OPERACION VENTAS
def cargar_presupuesto_centro_ventas(request):
    # obtener la suma de cada mes y nombre_linea_n1 es decir, si el lapso es 202001 retornar la suma
    # de los productos que pertenecen a la linea_n1
    bd2020 = BdVentas2020.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2021 = BdVentas2021.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2022 = BdVentas2022.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2023 = BdVentas2023.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2024 = BdVentas2024.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2025 = BdVentas2025.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    
    df1 = pd.DataFrame(list(bd2020))
    df2 = pd.DataFrame(list(bd2021))
    df3 = pd.DataFrame(list(bd2022))
    df4 = pd.DataFrame(list(bd2023))
    df5 = pd.DataFrame(list(bd2024))
    df6 = pd.DataFrame(list(bd2025))
    
    year_actual = timezone.now().year
    year_siguiente = timezone.now().year + 1
    
    df_total = pd.concat([df1, df2, df3, df4, df5, df6], ignore_index=True)
    df_centro_operacion = df_total.groupby(['nombre_centro_de_operacion', 'lapso'])['suma'].sum().reset_index()
    
    # Extraer año y mes
    df_centro_operacion['year'] = df_centro_operacion['lapso'] // 100
    df_centro_operacion['mes'] = df_centro_operacion['lapso'] % 100
    # Lista para almacenar predicciones por centro de operacion
    predicciones_2025_centro = []
    # Hacer predicción para cada centro de operacion y mes
    for centro, grupo in df_centro_operacion.groupby('nombre_centro_de_operacion'):
        for mes in range(1, 13):
            datos_mes = grupo[grupo['mes'] == mes]
            
            # Datos para regresión
            x = datos_mes['year'].values
            y = datos_mes['suma'].values

            if len(x) >= 2:  # Se necesita al menos 2 puntos para ajustar una recta
                a, b = np.polyfit(x, y, 1)  # Ajuste lineal
                y_pred = a * year_siguiente + b
                predicciones_2025_centro.append({'nombre_centro_de_operacion': centro, 'lapso': year_siguiente * 100 + mes, 'suma': round(y_pred)})
    # Crear DataFrame con predicciones
    df_pred_2025_centro = pd.DataFrame(predicciones_2025_centro)
    # (Opcional) Unir con el DataFrame original y ordenar por lapso y centro de operacion
    df_proyeccion_centro_operacion = pd.concat([df_centro_operacion[['nombre_centro_de_operacion', 'lapso', 'suma']], df_pred_2025_centro], ignore_index=True)
    df_proyeccion_centro_operacion = df_proyeccion_centro_operacion.sort_values(['nombre_centro_de_operacion', 'lapso']).reset_index(drop=True)
    # extraer año y mes
    df_proyeccion_centro_operacion['year'] = df_proyeccion_centro_operacion['lapso'] // 100
    df_proyeccion_centro_operacion['mes'] = df_proyeccion_centro_operacion['lapso'] % 100
    
    # calcular el coeficiente de correlación R2 para la proyección por centro de operacion y lapso -----------
    correlaciones_centro = []   
    for centro, grupo in df_proyeccion_centro_operacion.groupby('nombre_centro_de_operacion'):
        for mes in range(1, 13):
            datos_mes = grupo[grupo["mes"] == mes]

            if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
                coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
            else:
                coef = np.nan  # si no hay variación, correlación indefinida

            correlaciones_centro.append({
                "nombre_centro_de_operacion": centro,
                "mes": mes,
                "coef_correlacion": (round(coef, 4))*100 if not np.isnan(coef) else None
            })
    df_correl_por_mes_centro = pd.DataFrame(correlaciones_centro)
    # unir con el df_proyeccion_centro_operacion
    df_proyeccion_centro_operacion = pd.merge(df_proyeccion_centro_operacion, df_correl_por_mes_centro, on=['nombre_centro_de_operacion', 'mes'], how='left')
    df_proyeccion_centro_operacion['suma'] = df_proyeccion_centro_operacion['suma'].round().astype(int)   
    
    # ================= TOTAL_YEAR POR CENTRO ===================
    df_total_year_centro = (
        df_proyeccion_centro_operacion
        .groupby(['nombre_centro_de_operacion', 'year'])['suma']
        .sum()
        .reset_index()
        .rename(columns={'suma': 'total_year'})
    )
    # Calcular variaciones por centro
    df_total_year_centro['variacion_pesos'] = df_total_year_centro.groupby('nombre_centro_de_operacion')['total_year'].diff().round().astype('Int64')
    df_total_year_centro['variacion_pct'] = (df_total_year_centro.groupby('nombre_centro_de_operacion')['total_year'].pct_change() * 100).round(2)

    # Rellenar NaN en la primera fila de cada grupo
    df_total_year_centro[['variacion_pesos', 'variacion_pct']] = df_total_year_centro[['variacion_pesos', 'variacion_pct']].fillna(0)
    
    # ================== COSTOS: total_year ==============================
    costos = PresupuestoCentroOperacionCostos.objects.values("year", "nombre_centro_operacion", "total_year")
    df_costos = pd.DataFrame(list(costos)).rename(columns={"total_year": "total_year_costos"})

    # Merge ventas + costos
    df_total_year_centro = pd.merge(
        df_total_year_centro,
        df_costos,
        left_on=["nombre_centro_de_operacion", "year"],
        right_on=["nombre_centro_operacion", "year"],
        how="left"
    ).drop(columns=["nombre_centro_operacion"])  # evitar columna duplicada
    
    # merge de df_proyeccion_centro_operacion con df_por_año para agregar las columnas de total, variacion_pesos y variacion_pct
    df_proyeccion_centro_operacion = pd.merge(df_proyeccion_centro_operacion, df_total_year_centro[['nombre_centro_de_operacion','year', 'total_year', 'total_year_costos','variacion_pesos', 'variacion_pct']], on=["nombre_centro_de_operacion", "year"], how='left')
    
    # calcular utilidad por año, 1 - (costos / ventas), el costo está en el df_proyeccion_general y se encuentra en la columna total_year_costos, y las ventas están en la columna total
    df_proyeccion_centro_operacion['utilidad_pct'] = (1 - (df_proyeccion_centro_operacion['total_year_costos'] / df_proyeccion_centro_operacion['total_year'])) * 100
    df_proyeccion_centro_operacion['utilidad_pct'] = df_proyeccion_centro_operacion['utilidad_pct'].round(2)
    # llenar los valores infinitos o NaN con 0
    df_proyeccion_centro_operacion['utilidad_pct'] = df_proyeccion_centro_operacion['utilidad_pct'].replace([np.inf, -np.inf], 0).fillna(0)
    # utilidad en valor
    df_proyeccion_centro_operacion['utilidad_valor'] = df_proyeccion_centro_operacion['total_year'] - df_proyeccion_centro_operacion['total_year_costos']
    df_proyeccion_centro_operacion['utilidad_valor'] = df_proyeccion_centro_operacion['utilidad_valor'].round().astype(int)
    
    # guardar en la bd
    registros = []
    for _, row in df_proyeccion_centro_operacion.iterrows():
        registros.append(
            PresupuestoCentroOperacionVentas(
                nombre_centro_operacion=row['nombre_centro_de_operacion'],
                year=int(row['year']),
                mes=int(row['mes']),
                total=int(row['suma']),
                r2=row['coef_correlacion'] if row['coef_correlacion'] is not None else 0,
                total_year=row['total_year'] if row['total_year'] is not None else 0,
                total_year_costos=row['total_year_costos'] if row['total_year_costos'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0,
                utilidad_pct=row['utilidad_pct'] if row['utilidad_pct'] is not None else 0,
                utilidad_valor=row['utilidad_valor'] if row['utilidad_valor'] is not None else 0
            )
        )
    
    # Opcional: limpiar tabla antes de insertar para evitar duplicados
    PresupuestoCentroOperacionVentas.objects.all().delete() 
    PresupuestoCentroOperacionVentas.objects.bulk_create(registros)
    
    data = list(PresupuestoCentroOperacionVentas.objects.values())
    return JsonResponse(data, safe=False)
    
@csrf_exempt
def guardar_presupuesto_centro_ventas(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # 📥 datos editados desde DataTable
            df = pd.DataFrame(data)
            # print(data)
            # --- asegurar tipos correctos ---
            df["year"] = df["year"].astype(int)
            df["mes"] = df["mes"].astype(int)
            df["total"] = df["total"].astype(int)
            df["nombre_centro_operacion"] = df["nombre_centro_operacion"].astype(str)

            # --- recalcular R² por centro de operación y mes ---
            correlaciones = []
            for centro, grupo in df.groupby("nombre_centro_operacion"):
                for mes in range(1, 13):
                    datos_mes = grupo[grupo["mes"] == mes]

                    if len(datos_mes) >= 2 and datos_mes["total"].std() != 0:
                        coef = np.corrcoef(datos_mes["year"], datos_mes["total"])[0, 1]
                    else:
                        coef = np.nan

                    correlaciones.append({
                        "nombre_centro_operacion": centro,
                        "mes": mes,
                        "coef_correlacion": (round(coef, 4)) * 100 if not np.isnan(coef) else 0
                    })

            df_correl = pd.DataFrame(correlaciones)

            # unir correlaciones recalculadas con los datos originales
            df = pd.merge(df, df_correl, on=["nombre_centro_operacion", "mes"], how="left")

            # --- guardar en la BD ---
            registros = []
            for _, row in df.iterrows():
                registros.append(
                    PresupuestoCentroOperacionVentas(
                        nombre_centro_operacion=row["nombre_centro_operacion"],
                        year=int(row["year"]),
                        mes=int(row["mes"]),
                        total=int(row["total"]),
                        r2=row["coef_correlacion"]
                    )
                )

            PresupuestoCentroOperacionVentas.objects.all().delete()
            PresupuestoCentroOperacionVentas.objects.bulk_create(registros)

            data = list(PresupuestoCentroOperacionVentas.objects.values())
            return JsonResponse(data, safe=False)

        except Exception as e:
            return JsonResponse({"status": "error", "mensaje": str(e)}, status=400)


def obtener_presupuesto_centro_ventas(request):
    data = list(PresupuestoCentroOperacionVentas.objects.values())
    return JsonResponse(data, safe=False)

def vista_presupuesto_centro_ventas(request):
    return render(request, 'presupuesto_comercial/presupuesto_centro_ventas.html') 

#------PRESUPUESTO POR CENTRO OPERACION - SEGMENTO VENTAS
def cargar_presupuesto_centro_segmento_ventas(request):
    bd2020 = BdVentas2020.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2021 = BdVentas2021.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2022 = BdVentas2022.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2023 = BdVentas2023.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2024 = BdVentas2024.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2025 = BdVentas2025.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    
    df1 = pd.DataFrame(list(bd2020))
    df2 = pd.DataFrame(list(bd2021))
    df3 = pd.DataFrame(list(bd2022))
    df4 = pd.DataFrame(list(bd2023))
    df5 = pd.DataFrame(list(bd2024))
    df6 = pd.DataFrame(list(bd2025))
    
    year_actual = timezone.now().year
    year_siguiente = timezone.now().year + 1
   
    df_total = pd.concat([df1, df2, df3, df4, df5, df6], ignore_index=True)
    df_centro_operacion_segmento = df_total.groupby(['nombre_clase_cliente', 'nombre_centro_de_operacion', 'lapso'])['suma'].sum().reset_index()
    
    # Extraer año y mes
    df_centro_operacion_segmento['year'] = df_centro_operacion_segmento['lapso'] // 100
    df_centro_operacion_segmento['mes'] = df_centro_operacion_segmento['lapso'] % 100
    # Lista para almacenar predicciones por centro de operacion y segmento
    predicciones_2025_centro_segmento = []
    # Hacer predicción para cada centro de operacion, segmento y mes
    for (centro, segmento), grupo in df_centro_operacion_segmento.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente']):
        for mes in range(1, 13):
            datos_mes = grupo[grupo['mes'] == mes]
            
            # Datos para regresión
            x = datos_mes['year'].values
            y = datos_mes['suma'].values

            if len(x) >= 2:  # Se necesita al menos 2 puntos para ajustar una recta
                a, b = np.polyfit(x, y, 1)  # Ajuste lineal
                y_pred = a * year_siguiente + b
                predicciones_2025_centro_segmento.append({'nombre_centro_de_operacion': centro, 'nombre_clase_cliente': segmento, 'lapso': year_siguiente * 100 + mes, 'suma': round(y_pred)})
    # Crear DataFrame con predicciones
    df_pred_2025_centro_segmento = pd.DataFrame(predicciones_2025_centro_segmento)
    # (Opcional) Unir con el DataFrame original y ordenar por lapso, centro de operacion y segmento
    df_proyeccion_centro_operacion_segmento = pd.concat([df_centro_operacion_segmento[['nombre_centro_de_operacion', 'nombre_clase_cliente', 'lapso', 'suma']], df_pred_2025_centro_segmento], ignore_index=True)
    df_proyeccion_centro_operacion_segmento = df_proyeccion_centro_operacion_segmento.sort_values(['nombre_centro_de_operacion', 'nombre_clase_cliente', 'lapso']).reset_index(drop=True)
    # extraer año y mes
    df_proyeccion_centro_operacion_segmento['year'] = df_proyeccion_centro_operacion_segmento['lapso'] // 100
    df_proyeccion_centro_operacion_segmento['mes'] = df_proyeccion_centro_operacion_segmento['lapso'] % 100
    # ----------------------------calcular el coeficiente de correlación R2 para la proyección por centro de operacion, segmento y lapso ----------------------------
    correlaciones_centro_segmento = []
    for (centro, segmento), grupo in df_proyeccion_centro_operacion_segmento.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente']):
        for mes in range(1, 13):
            datos_mes = grupo[grupo["mes"] == mes]

            if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
                coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
            else:
                coef = 0  # si no hay variación, correlación indefinida

            correlaciones_centro_segmento.append({
                "nombre_centro_de_operacion": centro,
                "nombre_clase_cliente": segmento,
                "mes": mes,
                "coef_correlacion": (round(coef, 4))*100 if not np.isnan(coef) else None
            })
    df_correl_por_mes_centro_segmento = pd.DataFrame(correlaciones_centro_segmento)
    # unir con el df_proyeccion_centro_operacion_segmento
    df_proyeccion_centro_operacion_segmento = pd.merge(df_proyeccion_centro_operacion_segmento, df_correl_por_mes_centro_segmento, on=['nombre_centro_de_operacion', 'nombre_clase_cliente', 'mes'], how='left')
    df_proyeccion_centro_operacion_segmento['suma'] = df_proyeccion_centro_operacion_segmento['suma'].round().astype(int)

    # ================= TOTAL_YEAR POR CENTRO + SEGMENTO ===================
    df_total_year_centro_segmento = (
        df_proyeccion_centro_operacion_segmento
        .groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'])['suma']
        .sum()
        .reset_index()
        .rename(columns={'suma': 'total_year'})
    )
    
    # Variaciones
    df_total_year_centro_segmento['variacion_pesos'] = (
        df_total_year_centro_segmento
        .groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente'])['total_year']
        .diff()
        .round()
        .astype('Int64')
    )
    df_total_year_centro_segmento['variacion_pct'] = (
        df_total_year_centro_segmento
        .groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente'])['total_year']
        .pct_change() * 100
    ).round(2)
    df_total_year_centro_segmento[['variacion_pesos', 'variacion_pct']] = df_total_year_centro_segmento[['variacion_pesos', 'variacion_pct']].fillna(0)

    # ================== COSTOS ==================
    costos = PresupuestoCentroSegmentoCostos.objects.values(
        "year", "nombre_centro_operacion", "segmento", "total_year"
    )
    df_costos = pd.DataFrame(list(costos)).rename(columns={"total_year": "total_year_costos"})

    df_total_year_centro_segmento = pd.merge(
        df_total_year_centro_segmento,
        df_costos,
        left_on=["nombre_centro_de_operacion", "nombre_clase_cliente", "year"],
        right_on=["nombre_centro_operacion", "segmento", "year"],
        how="left"
    ).drop(columns=["nombre_centro_operacion", "segmento"])

    # Merge con proyección
    df_proyeccion_centro_operacion_segmento = pd.merge(
        df_proyeccion_centro_operacion_segmento,
        df_total_year_centro_segmento[['nombre_centro_de_operacion', 'nombre_clase_cliente', 'year', 'total_year', 'total_year_costos','variacion_pesos', 'variacion_pct']],
        on=["nombre_centro_de_operacion", "nombre_clase_cliente", "year"],
        how="left"
    )
   
    # ================== UTILIDAD ==================
    df_proyeccion_centro_operacion_segmento['utilidad_pct'] = (
        1 - (df_proyeccion_centro_operacion_segmento['total_year_costos'] / df_proyeccion_centro_operacion_segmento['total_year'])
    ) * 100
    df_proyeccion_centro_operacion_segmento['utilidad_pct'] = df_proyeccion_centro_operacion_segmento['utilidad_pct'].round(2)
    df_proyeccion_centro_operacion_segmento['utilidad_pct'] = df_proyeccion_centro_operacion_segmento['utilidad_pct'].replace([np.inf, -np.inf], 0).fillna(0)

    df_proyeccion_centro_operacion_segmento['utilidad_valor'] = (
        df_proyeccion_centro_operacion_segmento['total_year'] - df_proyeccion_centro_operacion_segmento['total_year_costos']
    )
    df_proyeccion_centro_operacion_segmento['utilidad_valor'] = df_proyeccion_centro_operacion_segmento['utilidad_valor'].round().astype(int)


    # guardar en la bd
    registros = []
    for _, row in df_proyeccion_centro_operacion_segmento.iterrows():
        registros.append(
            PresupuestoCentroSegmentoVentas(
                nombre_centro_operacion=row['nombre_centro_de_operacion'],
                segmento=row['nombre_clase_cliente'],
                year=int(row['year']),
                mes=int(row['mes']),
                total=int(row['suma']),
                r2=row['coef_correlacion'] if row['coef_correlacion'] is not None else 0,
                total_year=row['total_year'] if row['total_year'] is not None else 0,
                total_year_costos=row['total_year_costos'] if row['total_year_costos'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0,
                utilidad_pct=row['utilidad_pct'] if row['utilidad_pct'] is not None else 0,
                utilidad_valor=row['utilidad_valor'] if row['utilidad_valor'] is not None else 0
            )
        )
    
    # Opcional: limpiar tabla antes de insertar para evitar duplicados
    PresupuestoCentroSegmentoVentas.objects.all().delete()
    PresupuestoCentroSegmentoVentas.objects.bulk_create(registros)
    
    data = list(PresupuestoCentroSegmentoVentas.objects.values())
    return JsonResponse(data, safe=False)

@csrf_exempt
def guardar_presupuesto_centro_segmento_ventas(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # 📥 los datos del DataTable
            df = pd.DataFrame(data)

            # asegurar tipos correctos
            df["year"] = df["year"].astype(int)
            df["mes"] = df["mes"].astype(int)
            df["total"] = df["total"].astype(int)

            # 🔄 recalcular R2 por centro, segmento y mes
            correlaciones = []
            for (centro, segmento), grupo in df.groupby(["nombre_centro_operacion", "segmento"]):
                for mes in range(1, 13):
                    datos_mes = grupo[grupo["mes"] == mes]

                    if len(datos_mes) >= 2 and datos_mes["total"].std() != 0:
                        coef = np.corrcoef(datos_mes["year"], datos_mes["total"])[0, 1]
                    else:
                        coef = np.nan

                    correlaciones.append({
                        "nombre_centro_operacion": centro,
                        "segmento": segmento,
                        "mes": mes,
                        "r2": (round(coef, 4)) * 100 if not np.isnan(coef) else 0
                    })

            df_r2 = pd.DataFrame(correlaciones)

            # unir R2 recalculado con df original
            df_final = pd.merge(
                df,
                df_r2,
                on=["nombre_centro_operacion", "segmento", "mes"],
                how="left"
            )
            df_final["r2"] = df_final["r2_y"].fillna(df_final["r2_x"])  # prioriza recalculado
            df_final = df_final.drop(columns=["r2_x", "r2_y"], errors="ignore")

            # preparar objetos para guardar
            registros = []
            for _, row in df_final.iterrows():
                registros.append(
                    PresupuestoCentroSegmentoVentas(
                        nombre_centro_operacion=row["nombre_centro_operacion"],
                        segmento=row["segmento"],
                        year=int(row["year"]),
                        mes=int(row["mes"]),
                        total=int(row["total"]),
                        r2=float(row["r2"])
                    )
                )

            # limpiar tabla antes de insertar
            PresupuestoCentroSegmentoVentas.objects.all().delete()
            PresupuestoCentroSegmentoVentas.objects.bulk_create(registros)

            data = list(PresupuestoCentroSegmentoVentas.objects.values())
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({"status": "error", "mensaje": str(e)}, status=400)

    return JsonResponse({"status": "error", "mensaje": "Método no permitido"}, status=405)

def obtener_presupuesto_centro_segmento_ventas(request):
    data = list(PresupuestoCentroSegmentoVentas.objects.values())
    return JsonResponse(data, safe=False)

def vista_presupuesto_centro_segmento_ventas(request):
    return render(request, 'presupuesto_comercial/presupuesto_centro_segmento_ventas.html')

#-----------PRESUPUESTO GENERAL COSTOS
def cargar_presupuesto_general_costos(request):
    bd2020 = BdVentas2020.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2021 = BdVentas2021.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2022 = BdVentas2022.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2023 = BdVentas2023.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2024 = BdVentas2024.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2025 = BdVentas2025.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    
    df1 = pd.DataFrame(list(bd2020))
    df2 = pd.DataFrame(list(bd2021))
    df3 = pd.DataFrame(list(bd2022))
    df4 = pd.DataFrame(list(bd2023))
    df5 = pd.DataFrame(list(bd2024))
    df6 = pd.DataFrame(list(bd2025))
    
    year_actual = timezone.now().year
    year_siguiente = timezone.now().year + 1
    
    df_total = pd.concat([df1, df2, df3, df4, df5, df6], ignore_index=True)
    
    df_lapso_total = df_total.groupby('lapso')['suma'].sum().reset_index()
    
    # Extraer año y mes
    df_lapso_total['year'] = df_lapso_total['lapso'] // 100
    df_lapso_total['mes'] = df_lapso_total['lapso'] % 100
    # 📌 Suma por año
    # df_por_año = df_lapso_total.groupby("year")["suma"].sum().reset_index()
    # 📌 Suma por mes (todos los años juntos, ej: todos los eneros, febreros, etc.)
    df_por_mes = df_lapso_total.groupby("mes")["suma"].sum().reset_index()
    # suma por año y mes
    df_por_year_mes = df_lapso_total.groupby(["year", "mes"])["suma"].sum().reset_index()
    
    # calcular predicción para 2025 por cada mes usando regresión lineal
    predicciones_2025_general = []
    # recorrer cada mes (1 a 12)
    for mes in range(1, 13):
        datos_mes = df_por_year_mes[df_por_year_mes["mes"] == mes]

        x = datos_mes["year"].values
        y = datos_mes["suma"].values
        if len(x) >= 2:  # se necesitan al menos 2 años
            a, b = np.polyfit(x, y, 1)  # ajuste lineal
            y_pred = a * year_siguiente + b
            predicciones_2025_general.append({
                "year": year_siguiente,
                "mes": mes,
                "suma_pred": round(y_pred),
                "lapso": year_siguiente * 100 + mes
            })

    # convertir a dataframe
    df_pred_2025_general = pd.DataFrame(predicciones_2025_general)
    # unir con df_por_year_mes
    df_proyeccion_general = pd.concat([df_lapso_total[['lapso', 'suma']], df_pred_2025_general[['lapso', 'suma_pred']].rename(columns={'suma_pred': 'suma'})], ignore_index=True)
   
    #extrer año y mes
    df_proyeccion_general['year'] = df_proyeccion_general['lapso'] // 100
    df_proyeccion_general['mes'] = df_proyeccion_general['lapso'] % 100
    # calcular el coeficiente de correlación R2 para la proyección general---
    correlaciones = []
    for mes in range(1, 13):
        datos_mes = df_proyeccion_general[df_proyeccion_general["mes"] == mes]
        if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
            coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
        else:
            coef = np.nan  # si no hay variación, correlación indefinida

        correlaciones.append({
            "mes": mes,
            "coef_correlacion": (round(coef, 4))*100 if not np.isnan(coef) else None
        })
    
    df_correl_por_mes = pd.DataFrame(correlaciones)
    
    # unir con el df_proyeccion_centro_operacion
    df_proyeccion_general = pd.merge(df_proyeccion_general, df_correl_por_mes, on='mes', how='left')
    df_proyeccion_general['suma'] = df_proyeccion_general['suma'].round().astype(int)
    
    df_por_año = df_proyeccion_general.groupby("year")["suma"].sum().reset_index()
    df_por_año = df_por_año.sort_values("year").reset_index(drop=True)
    df_por_año["variacion_pesos"] = (df_por_año["suma"].diff()).round().astype('Int64')
    df_por_año["variacion_pct"] = (df_por_año["suma"].pct_change() * 100).round(2)
    df_por_año["variacion_pct"] = df_por_año["variacion_pct"].fillna(0)
    df_por_año["variacion_pesos"] = df_por_año["variacion_pesos"].fillna(0) 
    # renombrar suma por total
    df_por_año = df_por_año.rename(columns={'suma': 'total'})
    # merge de df_proyeccion_general con df_por_año para agregar las columnas de total, variacion_pesos y variacion_pct
    df_proyeccion_general = pd.merge(df_proyeccion_general, df_por_año[['year', 'total','variacion_pesos', 'variacion_pct']], on='year', how='left')
    # ----------- GUARDAR EN LA BD ------------
    registros = []
    for _, row in df_proyeccion_general.iterrows():
        registros.append(
            PresupuestoGeneralCostos(
                year=int(row['year']),
                mes=int(row['mes']),
                total=int(row['suma']),
                r2=row['coef_correlacion'] if row['coef_correlacion'] is not None else 0,
                total_year=row['total'] if row['total'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0
            )
        )
    # Opcional: limpiar tabla antes de insertar para evitar duplicados
    PresupuestoGeneralCostos.objects.all().delete()
    PresupuestoGeneralCostos.objects.bulk_create(registros)
    
    data = list(PresupuestoGeneralCostos.objects.values())
    return JsonResponse(data, safe=False)

@csrf_exempt
def guardar_presupuesto_general_costos(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # 📥 los datos del DataTable
            df = pd.DataFrame(data)

            # --- asegurarse de que los tipos sean correctos ---
            df["year"] = df["year"].astype(int)
            df["mes"] = df["mes"].astype(int)
            df["total"] = df["total"].astype(int)

            # --- recalcular coeficiente de correlación R² por mes ---
            correlaciones = []
            for mes in range(1, 13):
                datos_mes = df[df["mes"] == mes]

                if len(datos_mes) >= 2 and datos_mes["total"].std() != 0:
                    coef = np.corrcoef(datos_mes["year"], datos_mes["total"])[0, 1]
                else:
                    coef = np.nan

                correlaciones.append({
                    "mes": mes,
                    "coef_correlacion": (round(coef, 4)) * 100 if not np.isnan(coef) else 0
                })

            df_correl = pd.DataFrame(correlaciones)

            # unir correlaciones recalculadas con los datos originales
            df = pd.merge(df, df_correl, on="mes", how="left")

            registros = []
            for _, row in df.iterrows():
                registros.append(
                    PresupuestoGeneralCostos(
                        year=int(row["year"]),
                        mes=int(row["mes"]),
                        total=int(row["total"]),
                        r2=row["coef_correlacion"]
                    )
                )

            # limpiar tabla antes de insertar
            PresupuestoGeneralCostos.objects.all().delete()
            PresupuestoGeneralCostos.objects.bulk_create(registros)

            data = list(PresupuestoGeneralCostos.objects.values())
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({"status": "error", "mensaje": str(e)}, status=400)

    return JsonResponse({"status": "error", "mensaje": "Método no permitido"}, status=405)

def obtener_presupuesto_general_costos(request):
    data = list(PresupuestoGeneralCostos.objects.values())
    return JsonResponse(data, safe=False)

def vista_presupuesto_general_costos(request):
    return render(request, 'presupuesto_comercial/presupuesto_general_costos.html')

#-----------PRESUPUESTO POR CENTRO OPERACION - COSTOS
def cargar_presupuesto_centro_costos(request):
    bd2020 = BdVentas2020.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2021 = BdVentas2021.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2022 = BdVentas2022.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2023 = BdVentas2023.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2024 = BdVentas2024.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2025 = BdVentas2025.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    
    df1 = pd.DataFrame(list(bd2020))
    df2 = pd.DataFrame(list(bd2021))
    df3 = pd.DataFrame(list(bd2022))
    df4 = pd.DataFrame(list(bd2023))
    df5 = pd.DataFrame(list(bd2024))
    df6 = pd.DataFrame(list(bd2025))
    year_actual = timezone.now().year
    year_siguiente = timezone.now().year + 1
    
    df_total = pd.concat([df1, df2, df3, df4, df5, df6], ignore_index=True)
    df_centro_operacion = df_total.groupby(['nombre_centro_de_operacion', 'lapso'])['suma'].sum().reset_index()
    
    # Extraer año y mes
    df_centro_operacion['year'] = df_centro_operacion['lapso'] // 100
    df_centro_operacion['mes'] = df_centro_operacion['lapso'] % 100
    # Lista para almacenar predicciones por centro de operacion
    predicciones_2025_centro = []
    # Hacer predicción para cada centro de operacion y mes
    for centro, grupo in df_centro_operacion.groupby('nombre_centro_de_operacion'):
        for mes in range(1, 13):
            datos_mes = grupo[grupo['mes'] == mes]
            # Datos para regresión
            x = datos_mes['year'].values
            y = datos_mes['suma'].values

            if len(x) >= 2:  # Se necesita al menos 2 puntos para ajustar una recta
                a, b = np.polyfit(x, y, 1)  # Ajuste lineal
                y_pred = a * year_siguiente + b
                predicciones_2025_centro.append({'nombre_centro_de_operacion': centro, 'lapso': year_siguiente * 100 + mes, 'suma': round(y_pred)})
    # Crear DataFrame con predicciones
    df_pred_2025_centro = pd.DataFrame(predicciones_2025_centro)
    # (Opcional) Unir con el DataFrame original y ordenar por lapso y centro de operacion
    df_proyeccion_centro_operacion = pd.concat([df_centro_operacion[['nombre_centro_de_operacion', 'lapso', 'suma']], df_pred_2025_centro], ignore_index=True)
    df_proyeccion_centro_operacion = df_proyeccion_centro_operacion.sort_values(['nombre_centro_de_operacion', 'lapso']).reset_index(drop=True)
    # extraer año y mes
    df_proyeccion_centro_operacion['year'] = df_proyeccion_centro_operacion['lapso'] // 100
    df_proyeccion_centro_operacion['mes'] = df_proyeccion_centro_operacion['lapso'] % 100
    
    # calcular el coeficiente de correlación R2 para la proyección por centro de operacion y lapso -----------
    correlaciones_centro = []   
    for centro, grupo in df_proyeccion_centro_operacion.groupby('nombre_centro_de_operacion'):
        for mes in range(1, 13):
            datos_mes = grupo[grupo["mes"] == mes]

            if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
                coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
            else:
                coef = np.nan  # si no hay variación, correlación indefinida

            correlaciones_centro.append({
                "nombre_centro_de_operacion": centro,
                "mes": mes,
                "coef_correlacion": (round(coef, 4))*100 if not np.isnan(coef) else None
            })
    df_correl_por_mes_centro = pd.DataFrame(correlaciones_centro)
    # unir con el df_proyeccion_centro_operacion
    df_proyeccion_centro_operacion = pd.merge(df_proyeccion_centro_operacion, df_correl_por_mes_centro, on=['nombre_centro_de_operacion', 'mes'], how='left')
    df_proyeccion_centro_operacion['suma'] = df_proyeccion_centro_operacion['suma'].round().astype(int)   
    
    
    # ================= TOTAL_YEAR POR CENTRO ===================
    df_total_year_centro = (
        df_proyeccion_centro_operacion
        .groupby(['nombre_centro_de_operacion', 'year'])['suma']
        .sum()
        .reset_index()
        .rename(columns={'suma': 'total_year'})
    )
    # Calcular variaciones por centro
    df_total_year_centro['variacion_pesos'] = df_total_year_centro.groupby('nombre_centro_de_operacion')['total_year'].diff().round().astype('Int64')
    df_total_year_centro['variacion_pct'] = (df_total_year_centro.groupby('nombre_centro_de_operacion')['total_year'].pct_change() * 100).round(2)

    # Rellenar NaN en la primera fila de cada grupo
    df_total_year_centro[['variacion_pesos', 'variacion_pct']] = df_total_year_centro[['variacion_pesos', 'variacion_pct']].fillna(0)
    # merge de df_proyeccion_centro_operacion con df_por_año para agregar las columnas de total, variacion_pesos y variacion_pct
    df_proyeccion_centro_operacion = pd.merge(
        df_proyeccion_centro_operacion,
        df_total_year_centro[['nombre_centro_de_operacion', 'year', 'total_year','variacion_pesos', 'variacion_pct']],
        on=['nombre_centro_de_operacion','year'],
        how='left'
    )
    # guardar en la bd
    registros = []
    for _, row in df_proyeccion_centro_operacion.iterrows():
        registros.append(
            PresupuestoCentroOperacionCostos(
                nombre_centro_operacion=row['nombre_centro_de_operacion'],
                year=int(row['year']),
                mes=int(row['mes']),
                total=int(row['suma']),
                r2=row['coef_correlacion'] if row['coef_correlacion'] is not None else 0,
                total_year=row['total_year'] if row['total_year'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0
            )
        )
    
    # Opcional: limpiar tabla antes de insertar para evitar duplicados
    PresupuestoCentroOperacionCostos.objects.all().delete()
    PresupuestoCentroOperacionCostos.objects.bulk_create(registros)
    
    data = list(PresupuestoCentroOperacionCostos.objects.values())
    return JsonResponse(data, safe=False)

@csrf_exempt
def guardar_presupuesto_centro_costos(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # 📥 los datos del DataTable
            df = pd.DataFrame(data)

            # --- asegurar tipos correctos ---
            df["year"] = df["year"].astype(int)
            df["mes"] = df["mes"].astype(int)
            df["total"] = df["total"].astype(int)
            df["nombre_centro_operacion"] = df["nombre_centro_operacion"].astype(str)

            # --- recalcular R² por centro de operación y mes ---
            correlaciones = []
            for centro, grupo in df.groupby("nombre_centro_operacion"):
                for mes in range(1, 13):
                    datos_mes = grupo[grupo["mes"] == mes]

                    if len(datos_mes) >= 2 and datos_mes["total"].std() != 0:
                        coef = np.corrcoef(datos_mes["year"], datos_mes["total"])[0, 1]
                    else:
                        coef = np.nan

                    correlaciones.append({
                        "nombre_centro_operacion": centro,
                        "mes": mes,
                        "coef_correlacion": (round(coef, 4)) * 100 if not np.isnan(coef) else 0
                    })

            df_correl = pd.DataFrame(correlaciones)

            # unir correlaciones recalculadas con los datos originales
            df = pd.merge(df, df_correl, on=["nombre_centro_operacion", "mes"], how="left")
            registros = []
            for _, row in df.iterrows():
                registros.append(
                    PresupuestoCentroOperacionCostos(
                        nombre_centro_operacion=row["nombre_centro_operacion"],
                        year=int(row["year"]),
                        mes=int(row["mes"]),
                        total=int(row["total"]),
                        r2=row["coef_correlacion"]
                    )
                )

            # limpiar tabla antes de insertar
            PresupuestoCentroOperacionCostos.objects.all().delete()
            PresupuestoCentroOperacionCostos.objects.bulk_create(registros)

            data = list(PresupuestoCentroOperacionCostos.objects.values())
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({"status": "error", "mensaje": str(e)}, status=400)

    return JsonResponse({"status": "error", "mensaje": "Método no permitido"}, status=405)

def obtener_presupuesto_centro_costos(request):
    data = list(PresupuestoCentroOperacionCostos.objects.values())
    return JsonResponse(data, safe=False)

def vista_presupuesto_centro_costos(request):
    return render(request, 'presupuesto_comercial/presupuesto_centro_costos.html')

#--------------------------PRESUPUESTO CENTRO OPERACION - SEGMENTO COSTOS---------------
def cargar_presupuesto_centro_segmento_costos(request):
    bd2020 = BdVentas2020.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2021 = BdVentas2021.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2022 = BdVentas2022.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2023 = BdVentas2023.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2024 = BdVentas2024.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2025 = BdVentas2025.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    
    df1 = pd.DataFrame(list(bd2020))
    df2 = pd.DataFrame(list(bd2021))
    df3 = pd.DataFrame(list(bd2022))
    df4 = pd.DataFrame(list(bd2023))
    df5 = pd.DataFrame(list(bd2024))
    df6 = pd.DataFrame(list(bd2025))
    year_actual = timezone.now().year
    year_siguiente = timezone.now().year + 1
    
    df_total = pd.concat([df1, df2, df3, df4, df5, df6], ignore_index=True)
    df_centro_operacion_segmento = df_total.groupby(['nombre_clase_cliente', 'nombre_centro_de_operacion', 'lapso'])['suma'].sum().reset_index()
    
    # Extraer año y mes
    df_centro_operacion_segmento['year'] = df_centro_operacion_segmento['lapso'] // 100
    df_centro_operacion_segmento['mes'] = df_centro_operacion_segmento['lapso'] % 100
    # Lista para almacenar predicciones por centro de operacion y segmento
    predicciones_2025_centro_segmento = []
    # Hacer predicción para cada centro de operacion, segmento y mes
    for (centro, segmento), grupo in df_centro_operacion_segmento.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente']):
        for mes in range(1, 13):
            datos_mes = grupo[grupo['mes'] == mes]
            
            # Datos para regresión
            x = datos_mes['year'].values
            y = datos_mes['suma'].values

            if len(x) >= 2:  # Se necesita al menos 2 puntos para ajustar una recta
                a, b = np.polyfit(x, y, 1)  # Ajuste lineal
                y_pred = a * year_siguiente + b
                predicciones_2025_centro_segmento.append({'nombre_centro_de_operacion': centro, 'nombre_clase_cliente': segmento, 'lapso': year_siguiente * 100 + mes, 'suma': round(y_pred)})
    # Crear DataFrame con predicciones
    df_pred_2025_centro_segmento = pd.DataFrame(predicciones_2025_centro_segmento)
    # (Opcional) Unir con el DataFrame original y ordenar por lapso, centro de operacion y segmento
    df_proyeccion_centro_operacion_segmento = pd.concat([df_centro_operacion_segmento[['nombre_centro_de_operacion', 'nombre_clase_cliente', 'lapso', 'suma']], df_pred_2025_centro_segmento], ignore_index=True)
    df_proyeccion_centro_operacion_segmento = df_proyeccion_centro_operacion_segmento.sort_values(['nombre_centro_de_operacion', 'nombre_clase_cliente', 'lapso']).reset_index(drop=True)
    # extraer año y mes
    df_proyeccion_centro_operacion_segmento['year'] = df_proyeccion_centro_operacion_segmento['lapso'] // 100
    df_proyeccion_centro_operacion_segmento['mes'] = df_proyeccion_centro_operacion_segmento['lapso'] % 100
    # ----------------------------calcular el coeficiente de correlación R2 para la proyección por centro de operacion, segmento y lapso ----------------------------
    correlaciones_centro_segmento = []
    for (centro, segmento), grupo in df_proyeccion_centro_operacion_segmento.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente']):
        for mes in range(1, 13):
            datos_mes = grupo[grupo["mes"] == mes]

            if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
                coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
            else:
                coef = 0 # si no hay variación, correlación indefinida

            correlaciones_centro_segmento.append({
                "nombre_centro_de_operacion": centro,
                "nombre_clase_cliente": segmento,
                "mes": mes,
                "coef_correlacion": (round(coef, 4))*100 if not np.isnan(coef) else None
            })
    df_correl_por_mes_centro_segmento = pd.DataFrame(correlaciones_centro_segmento)
    # unir con el df_proyeccion_centro_operacion_segmento
    df_proyeccion_centro_operacion_segmento = pd.merge(df_proyeccion_centro_operacion_segmento, df_correl_por_mes_centro_segmento, on=['nombre_centro_de_operacion', 'nombre_clase_cliente', 'mes'], how='left')
    df_proyeccion_centro_operacion_segmento['suma'] = df_proyeccion_centro_operacion_segmento['suma'].round().astype(int)
    
    # ================= TOTAL_YEAR POR CENTRO Y CLASE CLIENTE ===================
    df_total_year_centro_clase = (
        df_proyeccion_centro_operacion_segmento
        .groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'])['suma']
        .sum()
        .reset_index()
        .rename(columns={'suma': 'total_year'})
    )

    # Calcular variaciones por centro + clase cliente
    df_total_year_centro_clase['variacion_pesos'] = (
        df_total_year_centro_clase
        .groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente'])['total_year']
        .diff()
        .round()
        .astype('Int64')
    )

    df_total_year_centro_clase['variacion_pct'] = (
        df_total_year_centro_clase
        .groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente'])['total_year']
        .pct_change() * 100
    ).round(2)

    # Rellenar NaN en la primera fila de cada grupo
    df_total_year_centro_clase[['variacion_pesos', 'variacion_pct']] = (
        df_total_year_centro_clase[['variacion_pesos', 'variacion_pct']].fillna(0)
    )

    # merge con df_proyeccion_centro_operacion_segmento
    df_proyeccion_centro_operacion_segmento = pd.merge(
        df_proyeccion_centro_operacion_segmento,
        df_total_year_centro_clase[
            ['nombre_centro_de_operacion', 'nombre_clase_cliente', 'year', 'total_year', 'variacion_pesos', 'variacion_pct']
        ],
        on=['nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'],
        how='left'
    )
    # guardar en la bd
    registros = []
    for _, row in df_proyeccion_centro_operacion_segmento.iterrows():
        registros.append(
            PresupuestoCentroSegmentoCostos(
                nombre_centro_operacion=row['nombre_centro_de_operacion'],
                segmento=row['nombre_clase_cliente'],
                year=int(row['year']),
                mes=int(row['mes']),
                total=int(row['suma']),
                r2=row['coef_correlacion'] if row['coef_correlacion'] is not None else 0,
                total_year=row['total_year'] if row['total_year'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0
            )
        )
    
    # Opcional: limpiar tabla antes de insertar para evitar duplicados
    PresupuestoCentroSegmentoCostos.objects.all().delete()
    PresupuestoCentroSegmentoCostos.objects.bulk_create(registros)
    
    data = list(PresupuestoCentroSegmentoCostos.objects.values())
    return JsonResponse(data, safe=False)

@csrf_exempt
def guardar_presupuesto_centro_segmento_costos(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # 📥 los datos del DataTable
            df = pd.DataFrame(data)

            # asegurar tipos correctos
            df["year"] = df["year"].astype(int)
            df["mes"] = df["mes"].astype(int)
            df["total"] = df["total"].astype(int)

            # 🔄 recalcular R2 por centro, segmento y mes
            correlaciones = []
            for (centro, segmento), grupo in df.groupby(["nombre_centro_operacion", "segmento"]):
                for mes in range(1, 13):
                    datos_mes = grupo[grupo["mes"] == mes]

                    if len(datos_mes) >= 2 and datos_mes["total"].std() != 0:
                        coef = np.corrcoef(datos_mes["year"], datos_mes["total"])[0, 1]
                    else:
                        coef = np.nan

                    correlaciones.append({
                        "nombre_centro_operacion": centro,
                        "segmento": segmento,
                        "mes": mes,
                        "r2": (round(coef, 4)) * 100 if not np.isnan(coef) else 0
                    })

            df_r2 = pd.DataFrame(correlaciones)

            # unir R2 recalculado con df original
            df_final = pd.merge(
                df,
                df_r2,
                on=["nombre_centro_operacion", "segmento", "mes"],
                how="left"
            )
            df_final["r2"] = df_final["r2_y"].fillna(df_final["r2_x"])  # prioriza recalculado
            df_final = df_final.drop(columns=["r2_x", "r2_y"], errors="ignore")
            
            registros = []
            for _, row in df_final.iterrows():
                registros.append(
                    PresupuestoCentroSegmentoCostos(
                        nombre_centro_operacion=row["nombre_centro_operacion"],
                        segmento=row["segmento"],
                        year=int(row["year"]),
                        mes=int(row["mes"]),
                        total=int(row["total"]),
                        r2=float(row["r2"])
                    )
                )

            # limpiar tabla antes de insertar
            PresupuestoCentroSegmentoCostos.objects.all().delete()
            PresupuestoCentroSegmentoCostos.objects.bulk_create(registros)

            data = list(PresupuestoCentroSegmentoCostos.objects.values())
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({"status": "error", "mensaje": str(e)}, status=400)

    return JsonResponse({"status": "error", "mensaje": "Método no permitido"}, status=405)

def obtener_presupuesto_centro_segmento_costos(request):
    data = list(PresupuestoCentroSegmentoCostos.objects.values())
    return JsonResponse(data, safe=False)

def vista_presupuesto_centro_segmento_costos(request):
    return render(request, 'presupuesto_comercial/presupuesto_centro_segmento_costos.html')

def dashboard(request):
    return render(request, 'presupuestoApp/dashboard.html')

#----------------PRESUPUESTO COMERCIAL-----------------------
def aux_presupuesto_comercial_costos():
    bd2020 = BdVentas2020.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2021 = BdVentas2021.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2022 = BdVentas2022.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2023 = BdVentas2023.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2024 = BdVentas2024.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2025 = BdVentas2025.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    
    df1 = pd.DataFrame(list(bd2020))
    df2 = pd.DataFrame(list(bd2021))
    df3 = pd.DataFrame(list(bd2022))
    df4 = pd.DataFrame(list(bd2023))
    df5 = pd.DataFrame(list(bd2024))
    df6 = pd.DataFrame(list(bd2025))
    year_actual = timezone.now().year
    year_siguiente = timezone.now().year + 1
    
    df_total = pd.concat([df1, df2, df3, df4, df5, df6], ignore_index=True)
    # print(df_total)
    # calcular suma por lapso y centro de operacion
    df_lapso_total = df_total.groupby('lapso')['suma'].sum().reset_index()
    # Extraer año y mes
    df_lapso_total['year'] = df_lapso_total['lapso'] // 100
    df_lapso_total['mes'] = df_lapso_total['lapso'] % 100
    #------------------------------------------------------PRONOSTICO FINAL---------------------------------------------------
    # Extraer el año desde 'lapso'
    df_total['year'] = df_total['lapso'] // 100

    # Agrupar por nombre de producto, año, y sumar
    df_agrupado = df_total.groupby(['nombre_linea_n1', 'year', 'nombre_centro_de_operacion', 'nombre_clase_cliente'])['suma'].sum().reset_index()
    # (Opcional) Ordenar resultados
    df_agrupado = df_agrupado.sort_values(by=['nombre_linea_n1', 'year'])
   
    # Definir el rango de años esperado para añadir año faltante y agergarle 0
    year = list(range(2020, 2026))
    # Crear un dataframe con todas las combinaciones posibles
    df_completo = (
        pd.MultiIndex.from_product(
            [
                df_agrupado['nombre_linea_n1'].unique(), 
                df_agrupado['nombre_centro_de_operacion'].unique(),
                df_agrupado['nombre_clase_cliente'].unique(),
                year],
            names=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year']
        )
        .to_frame(index=False)
    )
    # Unir con tus datos reales
    df_total_fill = df_completo.merge(df_agrupado, on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'], how='left')
    # Rellenar con 0 las sumas faltantes
    df_total_fill['suma'] = df_total_fill['suma'].fillna(0)
    # print(df_total_fill)
    # PREDICCION PARA 2025 POR PRONOSTICO LINEAL -----------------------------------------
    # Lista para almacenar resultados
    predicciones = []
    # Agrupar por producto
    for (nombre, centro, clase), grupo in df_total_fill.groupby( ['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente']):
        x = grupo['year'].values
        y = grupo['suma'].values
        
        if len(x) >= 2:
            # Ajuste lineal
            a, b = np.polyfit(x, y, 1)
            y_pred = a * year_siguiente + b
            predicciones.append({
                'nombre_linea_n1': nombre,
                'nombre_centro_de_operacion': centro,
                'nombre_clase_cliente': clase,
                'year': year_siguiente,
                'suma': round(y_pred)
            })

    # Crear DataFrame con predicciones
    df_pred_2025_pro_lineal = pd.DataFrame(predicciones)
    df_final_pronostico = pd.concat([df_total_fill, df_pred_2025_pro_lineal], ignore_index=True)
    df_final_pronostico = df_final_pronostico.sort_values(by=['nombre_linea_n1', 'year']).reset_index(drop=True)
    
    # R2 ----------------------------------------------
    # Lista para almacenar resultados
    correlaciones = []
    # Agrupar por producto
    for (nombre, centro, clase), grupo in df_final_pronostico.groupby(['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente']):
        x = grupo['year'].values
        y = grupo['suma'].values

        if len(x) >= 2 and np.std(y) != 0 and np.std(x) != 0:  # evitar división por 0
            coef = np.corrcoef(x, y)[0, 1]
            coef_abs_pct = abs(coef) * 100  # valor absoluto en porcentaje
        else:
            coef_abs_pct = 0.0  # o NaN si prefieres marcarlo

        correlaciones.append({
            'nombre_linea_n1': nombre,
            'nombre_centro_de_operacion': centro,
            'nombre_clase_cliente': clase,
            'R2': round(coef_abs_pct, 2)
        })

    # Crear DataFrame con los coeficientes
    df_correlaciones = pd.DataFrame(correlaciones)
    
    # concatenar con el df_final_pronostico
    df_final_pronostico = pd.merge(df_final_pronostico, df_correlaciones, on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente'], how='left')
   
    # --------------------- Calcular variaciones año vs año anterior -------------------------------
    df_final_pronostico['suma_anterior'] = df_final_pronostico.groupby(
        ['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente']
    )['suma'].shift(1)

    # Calcular variación en porcentaje
    df_final_pronostico['variacion_pct'] = np.where(
        df_final_pronostico['suma_anterior'] == 0,
        0,
        ((df_final_pronostico['suma'] - df_final_pronostico['suma_anterior']) / df_final_pronostico['suma_anterior']) * 100
    ).round(2)

    # Calcular variación en valor (pesos)
    df_final_pronostico['variacion_valor'] = (df_final_pronostico['suma'] - df_final_pronostico['suma_anterior']).fillna(0)

    # Variación mensual
    df_final_pronostico['variacion_mes'] = (df_final_pronostico['variacion_valor'] / 12).round().astype(int)

    # Variación por precios (2% del año anterior)
    df_final_pronostico['variacion_precios'] = (df_final_pronostico['suma_anterior'] * 0.02).round().fillna(0).astype(int)

    # Crecimiento comercial (variación - variación precios)
    df_final_pronostico['crecimiento_comercial'] = (df_final_pronostico['variacion_valor'] - df_final_pronostico['variacion_precios']).round().astype(int)

    # Crecimiento comercial mensual
    df_final_pronostico['crecimiento_comercial_mes'] = (df_final_pronostico['crecimiento_comercial'] / 12).round().astype(int)

    # Reemplazar NaN por 0 en variaciones
    cols_variaciones = ['variacion_pct', 'variacion_valor', 'variacion_mes', 'variacion_precios',
                        'crecimiento_comercial', 'crecimiento_comercial_mes']
    df_final_pronostico[cols_variaciones] = df_final_pronostico[cols_variaciones].fillna(0)
    
    # concatenar con el df_final_pronostico
    # df_final_pronostico = pd.merge(df_final_pronostico, df_variacion[['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'variacion_pct', 'variacion_valor', 'variacion_mes', 'variacion_precios', 'crecimiento_comercial', 'crecimiento_comercial_mes']], on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente'], how='left') 
    
    return df_final_pronostico
    

def cargar_presupuesto_comercial(request):
    bd2020 = BdVentas2020.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2021 = BdVentas2021.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2022 = BdVentas2022.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2023 = BdVentas2023.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2024 = BdVentas2024.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2025 = BdVentas2025.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    
    df1 = pd.DataFrame(list(bd2020))
    df2 = pd.DataFrame(list(bd2021))
    df3 = pd.DataFrame(list(bd2022))
    df4 = pd.DataFrame(list(bd2023))
    df5 = pd.DataFrame(list(bd2024))
    df6 = pd.DataFrame(list(bd2025))
    year_actual = timezone.now().year
    year_siguiente = timezone.now().year + 1
   
    df_total = pd.concat([df1, df2, df3, df4, df5, df6], ignore_index=True)
    # print(df_total)
    df_lapso_total = df_total.groupby('lapso')['suma'].sum().reset_index()
    # print(df_lapso_total)
    # Extraer año y mes
    df_lapso_total['year'] = df_lapso_total['lapso'] // 100
    df_lapso_total['mes'] = df_lapso_total['lapso'] % 100
    #------------------------------------------------------PRONOSTICO FINAL---------------------------------------------------
    # Extraer el año desde 'lapso'
    df_total['year'] = df_total['lapso'] // 100

    # Agrupar por nombre de producto, año, y sumar
    df_agrupado = df_total.groupby(['nombre_linea_n1', 'year', 'nombre_centro_de_operacion', 'nombre_clase_cliente'])['suma'].sum().reset_index()
    # (Opcional) Ordenar resultados
    df_agrupado = df_agrupado.sort_values(by=['nombre_linea_n1', 'year'])
   
    # Definir el rango de años esperado para añadir año faltante y agergarle 0
    year = list(range(2020, 2026))
    # Crear un dataframe con todas las combinaciones posibles
    df_completo = (
        pd.MultiIndex.from_product(
            [
                df_agrupado['nombre_linea_n1'].unique(), 
                df_agrupado['nombre_centro_de_operacion'].unique(),
                df_agrupado['nombre_clase_cliente'].unique(),
                year],
            names=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year']
        )
        .to_frame(index=False)
    )
    # Unir con tus datos reales
    df_total_fill = df_completo.merge(df_agrupado, on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'], how='left')
    # Rellenar con 0 las sumas faltantes
    df_total_fill['suma'] = df_total_fill['suma'].fillna(0)
    # print(df_total_fill)
    # PREDICCION PARA 2025 POR PRONOSTICO LINEAL -----------------------------------------
    # Lista para almacenar resultados
    predicciones = []
    # Agrupar por producto
    for (nombre, centro, clase), grupo in df_total_fill.groupby( ['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente']):
        x = grupo['year'].values
        y = grupo['suma'].values
        
        if len(x) >= 2:
            # Ajuste lineal
            a, b = np.polyfit(x, y, 1)
            y_pred = a * year_siguiente + b
            predicciones.append({
                'nombre_linea_n1': nombre,
                'nombre_centro_de_operacion': centro,
                'nombre_clase_cliente': clase,
                'year': year_siguiente,
                'suma': round(y_pred)
            })

    # Crear DataFrame con predicciones
    df_pred_2025_pro_lineal = pd.DataFrame(predicciones)
    df_final_pronostico = pd.concat([df_total_fill, df_pred_2025_pro_lineal], ignore_index=True)
    df_final_pronostico = df_final_pronostico.sort_values(by=['nombre_linea_n1', 'year']).reset_index(drop=True)
    
    # R2 ----------------------------------------------
    # Lista para almacenar resultados
    correlaciones = []
    # Agrupar por producto
    for (nombre, centro, clase), grupo in df_final_pronostico.groupby(['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente']):
        x = grupo['year'].values
        y = grupo['suma'].values

        if len(x) >= 2 and np.std(y) != 0 and np.std(x) != 0:  # evitar división por 0
            coef = np.corrcoef(x, y)[0, 1]
            coef_abs_pct = abs(coef) * 100  # valor absoluto en porcentaje
        else:
            coef_abs_pct = 0.0  # o NaN si prefieres marcarlo

        correlaciones.append({
            'nombre_linea_n1': nombre,
            'nombre_centro_de_operacion': centro,
            'nombre_clase_cliente': clase,
            'R2': round(coef_abs_pct, 2)
        })

    # Crear DataFrame con los coeficientes
    df_correlaciones = pd.DataFrame(correlaciones)
    
    # concatenar con el df_final_pronostico
    df_final_pronostico = pd.merge(df_final_pronostico, df_correlaciones, on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente'], how='left')
   
    # --------------------- Calcular variaciones año vs año anterior -------------------------------
    df_final_pronostico['suma_anterior'] = df_final_pronostico.groupby(
        ['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente']
    )['suma'].shift(1)

    # Calcular variación en porcentaje
    df_final_pronostico['variacion_pct'] = np.where(
        df_final_pronostico['suma_anterior'] == 0,
        0,
        ((df_final_pronostico['suma'] - df_final_pronostico['suma_anterior']) / df_final_pronostico['suma_anterior']) * 100
    ).round(2)

    # Calcular variación en valor (pesos)
    df_final_pronostico['variacion_valor'] = (df_final_pronostico['suma'] - df_final_pronostico['suma_anterior']).fillna(0)

    # Variación mensual
    df_final_pronostico['variacion_mes'] = (df_final_pronostico['variacion_valor'] / 12).round().astype(int)

    # Variación por precios (2% del año anterior)
    df_final_pronostico['variacion_precios'] = (df_final_pronostico['suma_anterior'] * 0.02).round().fillna(0).astype(int)

    # Crecimiento comercial (variación - variación precios)
    df_final_pronostico['crecimiento_comercial'] = (df_final_pronostico['variacion_valor'] - df_final_pronostico['variacion_precios']).round().astype(int)

    # Crecimiento comercial mensual
    df_final_pronostico['crecimiento_comercial_mes'] = (df_final_pronostico['crecimiento_comercial'] / 12).round().astype(int)

    # Reemplazar NaN por 0 en variaciones
    cols_variaciones = ['variacion_pct', 'variacion_valor', 'variacion_mes', 'variacion_precios',
                        'crecimiento_comercial', 'crecimiento_comercial_mes']
    df_final_pronostico[cols_variaciones] = df_final_pronostico[cols_variaciones].fillna(0)
    
    # concatenar con el df_final_pronostico
    # df_final_pronostico = pd.merge(df_final_pronostico, df_variacion[['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'variacion_pct', 'variacion_valor', 'variacion_mes', 'variacion_precios', 'crecimiento_comercial', 'crecimiento_comercial_mes']], on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente'], how='left')

    df_final_pronostico_costos = aux_presupuesto_comercial_costos()
    
    df_final_neto_costos = pd.merge(df_final_pronostico, df_final_pronostico_costos, on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year']) # x= netos y= costos
    df_final_neto_costos = pd.merge(
    df_final_pronostico,
    df_final_pronostico_costos,
    on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'],
    suffixes=('_ventas', '_costos')
    )

    # renombrar para claridad
    df_final_neto_costos = df_final_neto_costos.rename(
        columns={'suma_ventas': 'ventas', 'suma_costos': 'costos'}
    )
    #-------------------UTILIDAD----------------------- 
    # calcular utilidad por año, 1 - (costos / ventas), el costo está en el df_fnal_pronostico_costos es decir la predicción, y las ventas están en el df_fnal_pronostico
    # df_final_neto_costos['utilidad'] = (1 - (df_final_neto_costos['suma_y'] / df_final_neto_costos['suma_x'])) * 100
    # df_final_neto_costos['utilidad'] = df_final_neto_costos['utilidad'].round(2)
    # # llenar los valores infinitos o NaN con 0
    # df_final_neto_costos['utilidad'] = df_final_neto_costos['utilidad'].replace([np.inf, -np.inf], 0).fillna(0)
    # # renombrar columnas
    # df_final_neto_costos = df_final_neto_costos.rename(columns={'suma_x': 'ventas', 'suma_y': 'costos'})    
    # # calcular utilidad en valor
    # df_final_neto_costos['utilidad_valor'] = df_final_neto_costos['ventas'] - df_final_neto_costos['costos']
    
    # ------------------- UTILIDAD SOLO AÑO ACTUAL -----------------------
    # calcular solo para el año actual
    df_final_neto_costos['utilidad_porcentual_actual'] = np.where(
        df_final_neto_costos['year'] == year_actual,
        (1 - (df_final_neto_costos['costos'] / df_final_neto_costos['ventas'])) * 100,
        0
    ).round(2)

    df_final_neto_costos['utilidad_valor_actual'] = np.where(
        df_final_neto_costos['year'] == year_actual,
        df_final_neto_costos['ventas'] - df_final_neto_costos['costos'],
        0
    ).round().astype(int)
    # limpiar NaN e infinitos
    df_final_neto_costos['utilidad_porcentual_actual'] = df_final_neto_costos['utilidad_porcentual_actual'].replace([np.inf, -np.inf], 0).fillna(0)
    df_final_neto_costos['utilidad_valor_actual'] = df_final_neto_costos['utilidad_valor_actual'].fillna(0)

    # crear clave única para mapear utilidad del año actual al siguiente
    df_actual = df_final_neto_costos[df_final_neto_costos['year'] == year_actual].copy()
    df_actual['clave'] = df_actual['nombre_linea_n1'] + '|' + df_actual['nombre_centro_de_operacion'] + '|' + df_actual['nombre_clase_cliente']

    # diccionarios para mapear valores
    utilidad_pct_dict = df_actual.set_index('clave')['utilidad_porcentual_actual'].to_dict()
    utilidad_val_dict = df_actual.set_index('clave')['utilidad_valor_actual'].to_dict()

    # asignar al año siguiente
    mask = df_final_neto_costos['year'] == year_siguiente
    df_final_neto_costos.loc[mask, 'clave'] = df_final_neto_costos.loc[mask, 'nombre_linea_n1'] + '|' + df_final_neto_costos.loc[mask, 'nombre_centro_de_operacion'] + '|' + df_final_neto_costos.loc[mask, 'nombre_clase_cliente']

    df_final_neto_costos.loc[mask, 'utilidad_porcentual_actual'] = df_final_neto_costos.loc[mask, 'clave'].map(utilidad_pct_dict)
    df_final_neto_costos.loc[mask, 'utilidad_valor_actual'] = df_final_neto_costos.loc[mask, 'clave'].map(utilidad_val_dict)

    # opcional: eliminar columna clave
    df_final_neto_costos.drop(columns=['clave'], inplace=True)
    
    # agregar un cero a las columnas vacias
    df_final_neto_costos['variacion_pct_ventas'] = df_final_neto_costos['variacion_pct_ventas'].fillna(0)
    df_final_neto_costos['variacion_valor_ventas'] = df_final_neto_costos['variacion_valor_ventas'].fillna(0)
    df_final_neto_costos['variacion_mes_ventas'] = df_final_neto_costos['variacion_mes_ventas'].fillna(0)
    df_final_neto_costos['variacion_precios_ventas'] = df_final_neto_costos['variacion_precios_ventas'].fillna(0)
    df_final_neto_costos['crecimiento_comercial_ventas'] = df_final_neto_costos['crecimiento_comercial_ventas'].fillna(0)
    df_final_neto_costos['crecimiento_comercial_mes_ventas'] = df_final_neto_costos['crecimiento_comercial_mes_ventas'].fillna(0)

    df_final_neto_costos['variacion_pct_costos'] = df_final_neto_costos['variacion_pct_costos'].fillna(0)
    df_final_neto_costos['variacion_valor_costos'] = df_final_neto_costos['variacion_valor_costos'].fillna(0)
    df_final_neto_costos['variacion_mes_costos'] = df_final_neto_costos['variacion_mes_costos'].fillna(0)
    df_final_neto_costos['variacion_precios_costos'] = df_final_neto_costos['variacion_precios_costos'].fillna(0)
    df_final_neto_costos['crecimiento_comercial_costos'] = df_final_neto_costos['crecimiento_comercial_costos'].fillna(0)
    df_final_neto_costos['crecimiento_comercial_mes_costos'] = df_final_neto_costos['crecimiento_comercial_mes_costos'].fillna(0)
        
    # redondear las columnas que son float a int
    columnas_a_redondear = [
    'ventas', 'costos',
    'variacion_valor_ventas', 'variacion_mes_ventas', 'variacion_precios_ventas',
    'crecimiento_comercial_ventas', 'crecimiento_comercial_mes_ventas',
    'variacion_valor_costos', 'variacion_mes_costos', 'variacion_precios_costos',
    'crecimiento_comercial_costos', 'crecimiento_comercial_mes_costos'
    ]
    df_final_neto_costos[columnas_a_redondear] = df_final_neto_costos[columnas_a_redondear].round().astype(int)
    
    # guardar en la bd
    registros = []
    for _, row in df_final_neto_costos.iterrows():
        registros.append(
            PresupuestoComercial(
                linea=row['nombre_linea_n1'],
                year=int(row['year']),
                nombre_centro_de_operacion=row['nombre_centro_de_operacion'],
                nombre_clase_cliente=row['nombre_clase_cliente'],
                ventas=int(row['ventas']),
                costos=int(row['costos']),
                r2_ventas=float(row['R2_ventas']),
                r2_costos=float(row['R2_costos']),
                variacion_porcentual_ventas=float(row['variacion_pct_ventas']),
                variacion_porcentual_costos=float(row['variacion_pct_costos']),
                variacion_valor_ventas=int(row['variacion_valor_ventas']),
                variacion_valor_costos=int(row['variacion_valor_costos']),
                variacion_mes_ventas=int(row['variacion_mes_ventas']),
                variacion_mes_costos=int(row['variacion_mes_costos']),
                variacion_precios_ventas=int(row['variacion_precios_ventas']),
                variacion_precios_costos=int(row['variacion_precios_costos']),
                crecimiento_comercial_ventas=int(row['crecimiento_comercial_ventas']),
                crecimiento_comercial_costos=int(row['crecimiento_comercial_costos']),
                crecimiento_comercial_mes_ventas=int(row['crecimiento_comercial_mes_ventas']),
                crecimiento_comercial_mes_costos=int(row['crecimiento_comercial_mes_costos']),
                # 👇 Aquí asignamos proyección = ventas si el año es el siguiente
                proyeccion_ventas=int(row['ventas']) if int(row['year']) == year_siguiente else 0,
                proyeccion_costos=int(row['costos']) if int(row['year']) == year_siguiente else 0,
                # 👇 utilidad solo para 2025
                utilidad_porcentual_actual=float(row['utilidad_porcentual_actual']),
                utilidad_valor_actual=int(row['utilidad_valor_actual'])
            )
        )
    
    # Opcional: limpiar tabla antes de insertar para evitar duplicados
    PresupuestoComercial.objects.all().delete()
    PresupuestoComercial.objects.bulk_create(registros)
    
    return JsonResponse({"status": "ok", "mensaje": "Datos cargados correctamente ✅"})

@csrf_exempt
def guardar_presupuesto_comercial(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # datos enviados desde DataTable

            # 🔹 Convertir en DataFrame
            df = pd.DataFrame(data)

            # 🔹 Nos aseguramos que ventas y costos sean enteros
            df["ventas"] = df["ventas"].fillna(0).astype(int)
            df["costos"] = df["costos"].fillna(0).astype(int)

            # ================== 🔄 Recalcular proyecciones con base en ventas y costos 2025 ==================
            if "crecimiento_ventas" in df.columns and "crecimiento_costos" in df.columns and "ventas" in df.columns and "costos" in df.columns and "year" in df.columns:
                df["crecimiento_ventas"] = pd.to_numeric(df["crecimiento_ventas"], errors="coerce").fillna(0)
                df["crecimiento_costos"] = pd.to_numeric(df["crecimiento_costos"], errors="coerce").fillna(0)
                df["ventas"] = pd.to_numeric(df["ventas"], errors="coerce").fillna(0)
                df["costos"] = pd.to_numeric(df["costos"], errors="coerce").fillna(0)

                mask_2025 = df["year"] == 2026

                # Proyección ventas = ventas 2025 + (ventas 2025 * crecimiento_ventas%)
                df.loc[mask_2025, "proyeccion_ventas"] = (
                    df.loc[mask_2025, "ventas"] + (df.loc[mask_2025, "ventas"] * (df.loc[mask_2025, "crecimiento_ventas"] / 100))
                ).round().astype("int64")

                # Proyección costos = costos 2025 + (costos 2025 * crecimiento_costos%)
                df.loc[mask_2025, "proyeccion_costos"] = (
                    df.loc[mask_2025, "costos"] + (df.loc[mask_2025, "costos"] * (df.loc[mask_2025, "crecimiento_costos"] / 100))
                ).round().astype("int64")

            # ================== 🔄 Recalcular métricas ==================
            # df["utilidad_valor"] = df["proyeccion_ventas"] - df["proyeccion_costos"]
            # df["utilidad_porcentual"] = (1 - (df["proyeccion_ventas"] / df["proyeccion_costos"])) * 100
            # df["utilidad_porcentual"] = df["utilidad_porcentual"].replace([np.inf, -np.inf], 0).fillna(0).round(2)
            
            # # recalcular variaciones
            # df["variacion_proyectada_valor"] = df["utilidad_valor"] - df["utilidad_valor_actual"]
            # df["variacion_proyectada_porcentual"] = df["utilidad_porcentual"] - df["utilidad_porcentual_actual"]

            # Agrupamos por línea para calcular variaciones entre 2024 y 2025
            # for linea, grupo in df.groupby("linea"):
            #     if 2025 in grupo["year"].values and 2026 in grupo["year"].values:
            #         row2024 = grupo[grupo["year"] == 2025].iloc[0]
            #         row2025 = grupo[grupo["year"] == 2026].iloc[0]

            #         # Variaciones para ventas
            #         variacion_valor_ventas = row2025["ventas"] - row2024["ventas"]
            #         variacion_pct_ventas = (variacion_valor_ventas / row2024["ventas"] * 100) if row2024["ventas"] != 0 else 0
            #         variacion_mes_ventas = round(variacion_valor_ventas / 12)
            #         variacion_precios_ventas = round(row2024["ventas"] * 0.02)
            #         crecimiento_comercial_ventas = variacion_valor_ventas - variacion_precios_ventas
            #         crecimiento_comercial_mes_ventas = round(crecimiento_comercial_ventas / 12)

            #         # Variaciones para costos
            #         variacion_valor_costos = row2025["costos"] - row2024["costos"]
            #         variacion_pct_costos = (variacion_valor_costos / row2024["costos"] * 100) if row2024["costos"] != 0 else 0
            #         variacion_mes_costos = round(variacion_valor_costos / 12)
            #         variacion_precios_costos = round(row2024["costos"] * 0.02)
            #         crecimiento_comercial_costos = variacion_valor_costos - variacion_precios_costos
            #         crecimiento_comercial_mes_costos = round(crecimiento_comercial_costos / 12)

            #         # Actualizar fila 2025
            #         df.loc[(df["linea"] == linea) & (df["year"] == 2026), [
            #             "variacion_porcentual_ventas", "variacion_valor_ventas", "variacion_mes_ventas",
            #             "variacion_precios_ventas", "crecimiento_comercial_ventas", "crecimiento_comercial_mes_ventas",
            #             "variacion_porcentual_costos", "variacion_valor_costos", "variacion_mes_costos",
            #             "variacion_precios_costos", "crecimiento_comercial_costos", "crecimiento_comercial_mes_costos"
            #         ]] = [
            #             round(variacion_pct_ventas, 2), variacion_valor_ventas, variacion_mes_ventas,
            #             variacion_precios_ventas, crecimiento_comercial_ventas, crecimiento_comercial_mes_ventas,
            #             round(variacion_pct_costos, 2), variacion_valor_costos, variacion_mes_costos,
            #             variacion_precios_costos, crecimiento_comercial_costos, crecimiento_comercial_mes_costos
            #         ]
                    
            # ================== 🔄 Recalcular R2 ==================
            # for linea, grupo in df.groupby("linea"):
            #     x = grupo["year"].values
            #     # --- R2 ventas ---
            #     y_ventas = grupo["ventas"].values
            #     if len(x) >= 2 and np.std(y_ventas) != 0 and np.std(x) != 0:
            #         r2_ventas = abs(np.corrcoef(x, y_ventas)[0, 1]) * 100
            #     else:
            #         r2_ventas = 0.0
            #     df.loc[df["linea"] == linea, "r2_ventas"] = round(r2_ventas, 2)

            #     # --- R2 costos ---
            #     y_costos = grupo["costos"].values
            #     if len(x) >= 2 and np.std(y_costos) != 0 and np.std(x) != 0:
            #         r2_costos = abs(np.corrcoef(x, y_costos)[0, 1]) * 100
            #     else:
            #         r2_costos = 0.0
            #     df.loc[df["linea"] == linea, "r2_costos"] = round(r2_costos, 2)

            # ================== 🔄 Guardar en BD ==================
            registros = []
            for _, row in df.iterrows():
                registros.append(
                    PresupuestoComercial(
                        linea=row["linea"],
                        nombre_centro_de_operacion=row.get("nombre_centro_de_operacion", ""),
                        nombre_clase_cliente=row.get("nombre_clase_cliente", ""),
                        year=int(row["year"]),
                        ventas=int(row["ventas"]),
                        costos=int(row["costos"]),
                        r2_ventas=float(row.get("r2_ventas", 0)),
                        r2_costos=float(row.get("r2_costos", 0)),
                        variacion_porcentual_ventas=float(row.get("variacion_porcentual_ventas", 0)),
                        variacion_porcentual_costos=float(row.get("variacion_porcentual_costos", 0)),
                        variacion_valor_ventas=int(row.get("variacion_valor_ventas", 0)),
                        variacion_valor_costos=int(row.get("variacion_valor_costos", 0)),
                        variacion_mes_ventas=int(row.get("variacion_mes_ventas", 0)),
                        variacion_mes_costos=int(row.get("variacion_mes_costos", 0)),
                        variacion_precios_ventas=int(row.get("variacion_precios_ventas", 0)),
                        variacion_precios_costos=int(row.get("variacion_precios_costos", 0)),
                        crecimiento_comercial_ventas=int(row.get("crecimiento_comercial_ventas", 0)),
                        crecimiento_comercial_costos=int(row.get("crecimiento_comercial_costos", 0)),
                        crecimiento_comercial_mes_ventas=int(row.get("crecimiento_comercial_mes_ventas", 0)),
                        crecimiento_comercial_mes_costos=int(row.get("crecimiento_comercial_mes_costos", 0)),
                        crecimiento_ventas=int(row.get("crecimiento_ventas", 0)),
                        proyeccion_ventas=int(row.get("proyeccion_ventas", 0)),
                        crecimiento_costos=int(row.get("crecimiento_costos", 0)),
                        proyeccion_costos=int(row.get("proyeccion_costos", 0)),
                        utilidad_porcentual=float(row["utilidad_porcentual"]),
                        utilidad_valor=int(row["utilidad_valor"]),
                        utilidad_porcentual_actual=float(row["utilidad_porcentual_actual"]),
                        utilidad_valor_actual=int(row["utilidad_valor_actual"]),
                        variacion_proyectada_porcentual=float(row["variacion_proyectada_porcentual"]),
                        variacion_proyectada_valor=int(row["variacion_proyectada_valor"])
                    )
                )
            
            # Limpieza antes de insertar
            PresupuestoComercial.objects.all().delete()
            PresupuestoComercial.objects.bulk_create(registros)
            
            year_actual = timezone.now().year
            year_siguiente = timezone.now().year + 1
            # ================== 🔄 Actualizar PresupuestoGeneralVentas con total_proyectado ==================
            total_2026 = PresupuestoComercial.objects.filter(year=year_siguiente).aggregate(
                total_proyectado=Sum("proyeccion_ventas")
            )["total_proyectado"] or 0

            PresupuestoGeneralVentas.objects.filter(year=year_siguiente).update(
                total_proyectado=total_2026
            )
            
            # ================== 🔄 Actualizar PresupuestoCentroOperacionVentas con total_proyectado ==================
            proyecciones = (
                PresupuestoComercial.objects.filter(year=year_siguiente)
                .values("year", "nombre_centro_de_operacion")
                .annotate(total_proyectado=Sum("proyeccion_ventas"))
            )

            for item in proyecciones:
                year = item["year"]
                centro = item["nombre_centro_de_operacion"]
                total_proyectado = item["total_proyectado"] or 0

                PresupuestoCentroOperacionVentas.objects.filter(
                    year=year,
                    nombre_centro_operacion=centro
                ).update(total_proyectado=total_proyectado)
            
            # ================== 🔄 Actualizar total_proyectado por año, centro y clase cliente ==================
            proyecciones_seg_centro = (
                PresupuestoComercial.objects.filter(year=2026)
                .values("year", "nombre_centro_de_operacion", "nombre_clase_cliente")
                .annotate(total_proyectado=Sum("proyeccion_ventas"))
            )

            for item in proyecciones_seg_centro:
                year = item["year"]
                centro = item["nombre_centro_de_operacion"]
                clase = item["nombre_clase_cliente"]
                total_proyectado = item["total_proyectado"] or 0

                PresupuestoCentroSegmentoVentas.objects.filter(
                    year=year,
                    nombre_centro_operacion=centro,
                    segmento=clase  # 👈 aquí "segmento" representa la clase cliente
                ).update(total_proyectado=total_proyectado)

            return JsonResponse({"status": "ok", "mensaje": "Cambios guardados y recalculados ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "mensaje": str(e)}, status=400)

    return JsonResponse({"status": "error", "mensaje": "Método no permitido"}, status=405)


def obtener_presupuesto_comercial(request):
    data = list(PresupuestoComercial.objects.values())
    return JsonResponse(data, safe=False)

def vista_presupuesto_comercial(request):
    return render(request, 'presupuesto_comercial/presupuesto_comercial_final.html')

#  ---------------------NOMINA-------------------------------------------------------------
def presupuestoNomina(request):
   # Obtiene el único registro (o lo crea vacío la primera vez)
    parametros, created = ParametrosPresupuestos.objects.get_or_create(id=1)

    if request.method == "POST" and request.headers.get("x-requested-with") == "XMLHttpRequest":
        # Actualizar con los valores enviados desde AJAX
        parametros.incremento_salarial = request.POST.get("incrementoSalarial") or None
        parametros.incremento_ipc = request.POST.get("incrementoIPC") or None
        parametros.auxilio_transporte = request.POST.get("auxilioTransporte") or None
        parametros.cesantias = request.POST.get("cesantias") or None
        parametros.intereses_cesantias = request.POST.get("interesesCesantias") or None
        parametros.prima = request.POST.get("prima") or None
        parametros.vacaciones = request.POST.get("vacaciones") or None
        parametros.salario_minimo = request.POST.get("salarioMinimo") or None
        parametros.incremento_comisiones = request.POST.get("incrementoComisiones") or None
        parametros.save()
        return JsonResponse({"status": "ok", "msg": "Parámetros actualizados correctamente ✅"})

    return render(request, "presupuesto_nomina/dashboard_nomina.html", {"parametros": parametros})


def presupuesto_sueldos(request):
    # obtener los valores de nomina unicos
    # nomina = Nom005Salarios.objects.values('cedula','nombre','nombre_car','nombre_cco','nombre_cen','salario').distinct()
    return render(request, "presupuesto_nomina/presupuesto_nomina.html")

def obtener_nomina_temp(request):
    data = list(PresupuestoSueldosAux.objects.values())
    return JsonResponse(data, safe=False)

def tabla_auxiliar_sueldos(request):
    # obtener el incremento salarial desde la tabla auxiliar
    parametros = ParametrosPresupuestos.objects.first()
    incremento_salarial = parametros.incremento_salarial if parametros else 0
    salario = parametros.salario_minimo if parametros else 0
    return render(request, "presupuesto_nomina/aux_presupuesto_nomina.html", {'incrementoSalarial': incremento_salarial, 'salarioMinimo': salario})

def cargar_nomina_base(request):
    """
    Llena la tabla auxiliar con datos de ConceptosFijosYVariables
    """
    PresupuestoSueldosAux.objects.all().delete()  # limpia tabla temporal
    base_data = ConceptosFijosYVariables.objects.values(
        "cedula","nombre","nombrecar","nomcosto","nombre_cen","concepto_f", "nombre_con"
    )

    # filtrar solo concepto = 001
    base_data = base_data.filter(concepto="001")
    
    for row in base_data:
        PresupuestoSueldosAux.objects.create(
            cedula=row["cedula"],
            nombre=row["nombre"],
            cargo=row["nombrecar"],
            area=row["nomcosto"],
            centro=row["nombre_cen"],
            concepto=row["nombre_con"],
            salario_base=row["concepto_f"],
            enero=row["concepto_f"],
            febrero=row["concepto_f"],
        )

    return JsonResponse({"status": "ok"})

def guardar_nomina_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto",
                "salario_base", "enero", "febrero", "marzo", "abril", "mayo",
                "junio", "julio", "agosto", "septiembre", "octubre",
                "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoSueldosAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "salario_base","enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoSueldosAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoSueldosAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def subir_presupuesto_sueldos(request):
    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "msg": "Método no permitido"
        }, status=405)

    temporales = PresupuestoSueldosAux.objects.all()
    if not temporales.exists():
        return JsonResponse({
            "success": False,
            "msg": "No hay datos temporales para subir ❌"
        }, status=400)

    # Calcular versión siguiente
    ultima_version = PresupuestoSueldos.objects.aggregate(Max("version"))["version__max"] or 0
    nueva_version = ultima_version + 1

    # Obtener todos los registros existentes de esta versión
    cedula_concepto_existentes = set(
        PresupuestoSueldos.objects.filter(version=nueva_version)
        .values_list("cedula", "concepto")
    )

    # Preparar lista de objetos a crear
    registros_a_crear = []
    for temp in temporales:
        key = (temp.cedula, temp.concepto)
        if key not in cedula_concepto_existentes:
            registros_a_crear.append(
                PresupuestoSueldos(
                    cedula=temp.cedula,
                    nombre=temp.nombre,
                    centro=temp.centro,
                    area=temp.area,
                    cargo=temp.cargo,
                    concepto=temp.concepto,
                    salario_base=temp.salario_base,
                    enero=temp.enero,
                    febrero=temp.febrero,
                    marzo=temp.marzo,
                    abril=temp.abril,
                    mayo=temp.mayo,
                    junio=temp.junio,
                    julio=temp.julio,
                    agosto=temp.agosto,
                    septiembre=temp.septiembre,
                    octubre=temp.octubre,
                    noviembre=temp.noviembre,
                    diciembre=temp.diciembre,
                    total=temp.total,
                    version=nueva_version,
                    fecha_carga=timezone.now()
                )
            )

    if not registros_a_crear:
        return JsonResponse({
            "success": False,
            "msg": "Todos los registros ya existían ❌"
        }, status=400)

    # Guardar todos los registros de una sola vez
    PresupuestoSueldos.objects.bulk_create(registros_a_crear)

    return JsonResponse({
        "success": True,
        "msg": f"Presupuesto subido como versión {nueva_version} ✅ ({len(registros_a_crear)} nuevos registros)"
    })

def listar_versiones():
    return (
        PresupuestoSueldos.objects
        .values("version")
        .annotate(fecha=Max("fecha_carga"))
        .order_by("-version")
    )

def obtener_presupuesto_sueldos(request):
    data = list(PresupuestoSueldos.objects.values())
    return JsonResponse({"data": data}, safe=False)

@csrf_exempt
def borrar_presupuesto_sueldos(request):
    if request.method == "POST":
        PresupuestoSueldos.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

# -------------------------------COMISIONES---------------------------------
def comisiones(request):
    return render(request, "presupuesto_nomina/comisiones.html")

def obtener_presupuesto_comisiones(request):
    comisiones = list(PresupuestoComisiones.objects.values())
    return JsonResponse({"data": comisiones}, safe=False)

def tabla_auxiliar_comisiones(request):
    # obtener el incremento de comisiones desde la tabla auxiliar
    parametros = ParametrosPresupuestos.objects.first()
    incremento_comisiones = parametros.incremento_comisiones if parametros else 0
    return render(request, "presupuesto_nomina/aux_comisiones.html", {'incrementoComisiones': incremento_comisiones})

def subir_presupuesto_comisiones(request):
    if request.method == "POST":
        temporales = PresupuestoComisionesAux.objects.all()

        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoComisiones.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de comisiones subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)

def guardar_comisiones_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoComisionesAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoComisionesAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoComisionesAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_comisiones_temp(request):
    data = list(PresupuestoComisionesAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_comisiones_base(request):
    """
    Llena la tabla auxiliar con datos de conceptos
    """
    PresupuestoComisionesAux.objects.all().delete()  # limpia tabla temporal
    base_data = ConceptosFijosYVariables.objects.values(
        "cedula","nombre","nombrecar","nomcosto","nombre_cen", "nombre_con", "enero", "febrero", "marzo", "abril", "mayo",
        "junio", "julio", "agosto", "total"
    )

    # filtrar solo concepto que sea igual a 389
    base_data = base_data.filter(concepto="389")
    
    for row in base_data:
        PresupuestoComisionesAux.objects.create(
            cedula=row["cedula"],
            nombre=row["nombre"],
            cargo=row["nombrecar"],
            area=row["nomcosto"],
            centro=row["nombre_cen"],
            concepto=row["nombre_con"],
            enero=row["enero"] or 0,
            febrero=row["febrero"] or 0,
            marzo=row["marzo"] or 0,
            abril=row["abril"] or 0,
            mayo=row["mayo"] or 0,
            junio=row["junio"] or 0,
            julio=row["julio"] or 0,
            agosto=row["agosto"] or 0,
            total=row["total"] or 0,
        )

        
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_comisiones(request):
    if request.method == "POST":
        PresupuestoComisiones.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de comisiones eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

# -------------------------------HORAS EXTRA---------------------------------
def horas_extra(request):
    return render(request, "presupuesto_nomina/horas_extra.html")

def obtener_presupuesto_horas_extra(request):
    horas_extra = list(PresupuestoHorasExtra.objects.values())
    return JsonResponse({"data": horas_extra}, safe=False)

def tabla_auxiliar_horas_extra(request):
    # obtener el incremento de horas extra desde la tabla auxiliar
    parametros = ParametrosPresupuestos.objects.first()
    incremento_horas_extra = parametros.incremento_salarial if parametros else 0
    return render(request, "presupuesto_nomina/aux_horas_extra.html", {'incrementoSalarial': incremento_horas_extra})

def subir_presupuesto_horas_extra(request):
    if request.method == "POST":
        temporales = PresupuestoHorasExtraAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoHorasExtra.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de horas extra subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)

def guardar_horas_extra_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoHorasExtraAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoHorasExtraAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoHorasExtraAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_horas_extra_temp(request):
    data = list(PresupuestoHorasExtraAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_horas_extra_base(request):
    """
    Llena la tabla auxiliar con datos de conceptos
    """
    PresupuestoHorasExtraAux.objects.all().delete()  # limpia tabla temporal
    base_data = ConceptosFijosYVariables.objects.values(
        "cedula","nombre","nombrecar","nomcosto","nombre_cen", "nombre_con", "enero", "febrero", "marzo", "abril", "mayo",
        "junio", "julio", "agosto", "total"
    )

    # Filtrar solo los conceptos que necesitamos
    base_data = (
        ConceptosFijosYVariables.objects
        .filter(concepto__in=["114", "110", "111"])
        .values("cedula", "nombre", "nombrecar", "nomcosto", "nombre_cen")  # agrupadores
        .annotate(
            enero=Sum("enero"),
            febrero=Sum("febrero"),
            marzo=Sum("marzo"),
            abril=Sum("abril"),
            mayo=Sum("mayo"),
            junio=Sum("junio"),
            julio=Sum("julio"),
            agosto=Sum("agosto"),
            total=Sum("total"),
        )
    )
    
    for row in base_data:
        PresupuestoHorasExtraAux.objects.create(
            cedula=row["cedula"],
            nombre=row["nombre"],
            cargo=row["nombrecar"],
            area=row["nomcosto"],
            centro=row["nombre_cen"],
            concepto="HORAS EXTRA",
            enero=row["enero"] or 0,
            febrero=row["febrero"] or 0,
            marzo=row["marzo"] or 0,
            abril=row["abril"] or 0,
            mayo=row["mayo"] or 0,
            junio=row["junio"] or 0,
            julio=row["julio"] or 0,
            agosto=row["agosto"] or 0,
            total=row["total"] or 0,
        )

        
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_horas_extra(request):
    if request.method == "POST":
        PresupuestoHorasExtra.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de horas extra eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)
# -------------------------------MEDIOS DE TRANSPORTE---------------------------------
def medios_transporte(request):
    return render(request, "presupuesto_nomina/medios_transporte.html")

def obtener_presupuesto_medios_transporte(request):
    medios_transporte = list(PresupuestoMediosTransporte.objects.values())
    return JsonResponse({"data": medios_transporte}, safe=False)

def tabla_auxiliar_medios_transporte(request):
    # obtener el incremento de medios de transporte desde la tabla auxiliar
    parametros = ParametrosPresupuestos.objects.first()
    incremento_medios_transporte = parametros.incremento_ipc if parametros else 0
    return render(request, "presupuesto_nomina/aux_medios_transporte.html", {'incrementoIPC': incremento_medios_transporte})

def subir_presupuesto_medios_transporte(request):
    if request.method == "POST":
        temporales = PresupuestoMediosTransporteAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoMediosTransporte.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                base=temp.base,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de medios de transporte subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_medios_transporte_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "base", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoMediosTransporteAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoMediosTransporteAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoMediosTransporteAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_medios_transporte_temp(request):
    data = list(PresupuestoMediosTransporteAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_medios_transporte_base(request):
    """
    Llena la tabla auxiliar con datos de conceptos
    """
    PresupuestoMediosTransporteAux.objects.all().delete()  # limpia tabla temporal
    base_data = ConceptosFijosYVariables.objects.values(
        "cedula","nombre","nombrecar","nomcosto","nombre_cen", "nombre_con", "concepto_f"
    )

    # filtrar solo concepto que sea igual a 389
    base_data = base_data.filter(concepto="011")
    
    for row in base_data:
        PresupuestoMediosTransporteAux.objects.create(
            cedula=row["cedula"],
            nombre=row["nombre"],
            cargo=row["nombrecar"],
            area=row["nomcosto"],
            centro=row["nombre_cen"],
            concepto=row["nombre_con"],
            base=row["concepto_f"] or 0,
            enero=row["concepto_f"] or 0,
            febrero=row["concepto_f"] or 0,
        )

        
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_medios_transporte(request):
    if request.method == "POST":
        PresupuestoMediosTransporte.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de medios de transporte eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)
# -------------------------------AUXILIO DE TRANSPORTE---------------------------------
def auxilio_transporte(request):
    return render(request, "presupuesto_nomina/auxilio_transporte.html")

def obtener_presupuesto_auxilio_transporte(request):
    auxilio_transporte = list(PresupuestoAuxilioTransporte.objects.values())
    return JsonResponse({"data": auxilio_transporte}, safe=False)

def tabla_auxiliar_auxilio_transporte(request):
    # obtener el auxilio de transporte desde la tabla auxiliar
    parametros = ParametrosPresupuestos.objects.first()
    auxilio_transporte = parametros.auxilio_transporte if parametros else 0
    return render(request, "presupuesto_nomina/aux_auxilio_transporte.html", {'auxilioTransporte': auxilio_transporte})

def subir_presupuesto_auxilio_transporte(request):
    if request.method == "POST":
        temporales = PresupuestoAuxilioTransporteAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoAuxilioTransporte.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                base=temp.base,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de auxilio de transporte subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)

def guardar_auxilio_transporte_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "base", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoAuxilioTransporteAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoAuxilioTransporteAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoAuxilioTransporteAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_auxilio_transporte_temp(request):
    data = list(PresupuestoAuxilioTransporteAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_auxilio_transporte_base(request):
    """
    Llena la tabla auxiliar con datos de conceptos y agrega auxilio de transporte
    cuando el salario mensual consolidado es menor al SMMLV (1.423.500).
    """
    parametros = ParametrosPresupuestos.objects.first()
    salarioIncremento = parametros.salario_minimo + (parametros.salario_minimo * (parametros.incremento_salarial / 100))
    LIMITE_SMMLV = (salarioIncremento) * 2
    AUXILIO_BASE = 200000
    MESES = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    PresupuestoAuxilioTransporteAux.objects.all().delete()  # limpia tabla temporal
    # Obtener base de empleados
    base_data = ConceptosFijosYVariables.objects.filter(concepto__in=["001", "006"]).values(
        "cedula", "nombre", "nombrecar", "nomcosto", "nombre_cen", "concepto_f"
    )
    
    for row in base_data:
        aux = PresupuestoAuxilioTransporteAux.objects.create(
            cedula=row["cedula"],
            nombre=row["nombre"],
            cargo=row["nombrecar"],
            area=row["nomcosto"],
            centro=row["nombre_cen"],
            concepto="AUXILIO DE TRANSPORTE",
            base=AUXILIO_BASE,
        )

        # 🔹 recorrer meses
        for mes in MESES:
            # Sumar el valor del mes en todas las tablas
            total_mes = 0

            total_mes += PresupuestoMediosTransporte.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0
            total_mes += PresupuestoSueldos.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0
            total_mes += PresupuestoComisiones.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0
            total_mes += PresupuestoHorasExtra.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0

            # 🔹 Condición: si la suma < SMMLV, asignar 200000 a ese mes
            if total_mes < LIMITE_SMMLV:
                setattr(aux, mes, AUXILIO_BASE)

            if mes == "marzo":
                salario_base = row["concepto_f"] or 0
                nuevo_salario = salario_base + (salario_base * (parametros.incremento_salarial / 100))
                auxRetroactivo = (nuevo_salario - salario_base) * 2  # retroactivo de enero y febrero
               
                # Sumar el valor del mes en todas las tablas
                total_mes = 0

                total_mes += PresupuestoMediosTransporte.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0
                total_mes += PresupuestoSueldos.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0
                total_mes += PresupuestoComisiones.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0
                total_mes += PresupuestoHorasExtra.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0

                total_mes -= auxRetroactivo * 2
                
                # 🔹 Condición: si la suma < SMMLV, asignar 200000 a ese mes
                if total_mes < LIMITE_SMMLV:
                    setattr(aux, mes, AUXILIO_BASE)

        # Guardar cambios
        aux.save()

        
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_auxilio_transporte(request):
    if request.method == "POST":
        PresupuestoAuxilioTransporte.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de auxilio de transporte eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)
# -------------------------------AYUDA AL TRANSPORTE---------------------------------
def ayuda_transporte(request):
    return render(request, "presupuesto_nomina/ayuda_transporte.html")

def obtener_presupuesto_ayuda_transporte(request):
    ayuda_transporte = list(PresupuestoAyudaTransporte.objects.values())
    return JsonResponse({"data": ayuda_transporte}, safe=False)

def tabla_auxiliar_ayuda_transporte(request):
    # obtener la ayuda de transporte desde la tabla auxiliar
    parametros = ParametrosPresupuestos.objects.first()
    ayuda_transporte = parametros.incremento_ipc if parametros else 0
    return render(request, "presupuesto_nomina/aux_ayuda_transporte.html", {'incrementoIPC': ayuda_transporte})

def subir_presupuesto_ayuda_transporte(request):
    if request.method == "POST":
        temporales = PresupuestoAyudaTransporteAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoAyudaTransporte.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                base=temp.base,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de ayuda de transporte subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_ayuda_transporte_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "base", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoAyudaTransporteAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoAyudaTransporteAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoAyudaTransporteAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_ayuda_transporte_temp(request):
    data = list(PresupuestoAyudaTransporteAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_ayuda_transporte_base(request):
    """
    Llena la tabla auxiliar con datos de conceptos
    """
    PresupuestoAyudaTransporteAux.objects.all().delete()  # limpia tabla temporal
    base_data = ConceptosFijosYVariables.objects.values(
        "cedula","nombre","nombrecar","nomcosto","nombre_cen", "nombre_con", "concepto_f"
    )

    # filtrar solo concepto que sea igual a 389
    base_data = base_data.filter(concepto="013")
    
    for row in base_data:
        PresupuestoAyudaTransporteAux.objects.create(
            cedula=row["cedula"],
            nombre=row["nombre"],
            cargo=row["nombrecar"],
            area=row["nomcosto"],
            centro=row["nombre_cen"],
            concepto=row["nombre_con"],
            base=row["concepto_f"] or 0,
            enero=row["concepto_f"] or 0,
            febrero=row["concepto_f"] or 0,
        )

        
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_ayuda_transporte(request):
    if request.method == "POST":
        PresupuestoAyudaTransporte.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de ayuda de transporte eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

# -----------------------------Cesantias---------------------
def cesantias(request):
    return render(request, "presupuesto_nomina/cesantias.html")

def obtener_presupuesto_cesantias(request):
    cesantias = list(PresupuestoCesantias.objects.values())
    return JsonResponse({"data": cesantias}, safe=False)

def tabla_auxiliar_cesantias(request):
    # obtener el auxilio de transporte desde la tabla auxiliar
    parametros = ParametrosPresupuestos.objects.first()
    cesantias = parametros.cesantias if parametros else 0
    return render(request, "presupuesto_nomina/aux_cesantias.html", {'cesantias': cesantias})

def subir_presupuesto_cesantias(request):
    if request.method == "POST":
        temporales = PresupuestoCesantiasAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoCesantias.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de cesantías subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)

def guardar_cesantias_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoCesantiasAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoCesantiasAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoCesantiasAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_cesantias_temp(request):
    data = list(PresupuestoCesantiasAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_cesantias_base(request):
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]

    # Limpio la tabla de cesantías antes de recalcular
    PresupuestoCesantiasAux.objects.all().delete()

    # Tomo todos los empleados desde nómina (puede ser tu base principal)
    empleados = PresupuestoSueldos.objects.all()
    # Tomo también los aprendices
    aprendices = PresupuestoAprendiz.objects.filter(concepto="SALARIO APRENDIZ REFORMA")
    
    # # Uno empleados y aprendices en una sola lista
    personas = list(empleados) + list(aprendices)
    for emp in personas:
        # Inicializo acumuladores por mes
        data_meses = {mes: 0 for mes in meses}

        # Sumo de nómina
        nomina = PresupuestoSueldos.objects.filter(cedula=emp.cedula).first()
        if nomina:
            for mes in meses:
                data_meses[mes] += getattr(nomina, mes, 0)
        
        # Sumo de comisiones
        comision = PresupuestoComisiones.objects.filter(cedula=emp.cedula).first()
        if comision:
            for mes in meses:
                data_meses[mes] += getattr(comision, mes, 0)

        # Sumo de medios de transporte
        medio = PresupuestoMediosTransporte.objects.filter(cedula=emp.cedula).first()
        if medio:
            for mes in meses:
                data_meses[mes] += getattr(medio, mes, 0)

        # Sumo de auxilio transporte
        aux = PresupuestoAuxilioTransporte.objects.filter(cedula=emp.cedula).first()
        if aux:
            for mes in meses:
                data_meses[mes] += getattr(aux, mes, 0)

        # Sumo de horas extra
        extra = PresupuestoHorasExtra.objects.filter(cedula=emp.cedula).first()
        if extra:
            for mes in meses:
                data_meses[mes] += getattr(extra, mes, 0)

        # Creo el registro en cesantías con la suma
        PresupuestoCesantiasAux.objects.create(
            cedula=emp.cedula,
            nombre=emp.nombre,
            centro=emp.centro,
            area=emp.area,
            cargo=emp.cargo,
            concepto="CESANTÍAS",
            **data_meses,
            total=sum(data_meses.values())
        )

    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_cesantias(request):
    if request.method == "POST":
        PresupuestoCesantias.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de cesantías eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

# ------------------------Prima------------------
def prima(request):
    return render(request, "presupuesto_nomina/prima.html")

def obtener_presupuesto_prima(request):
    prima = list(PresupuestoPrima.objects.values())
    return JsonResponse({"data": prima}, safe=False)

def tabla_auxiliar_prima(request):
    # obtener la prima desde la tabla auxiliar
    parametros = ParametrosPresupuestos.objects.first()
    prima = parametros.prima if parametros else 0
    return render(request, "presupuesto_nomina/aux_prima.html", {'prima': prima})

def subir_presupuesto_prima(request):
    if request.method == "POST":
        temporales = PresupuestoPrimaAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoPrima.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de prima subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_prima_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoPrimaAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoPrimaAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoPrimaAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_prima_temp(request):
    data = list(PresupuestoPrimaAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_prima_base(request):
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]

    # Limpio la tabla de cesantías antes de recalcular
    PresupuestoPrimaAux.objects.all().delete()

    # Tomo todos los empleados desde nómina (puede ser tu base principal)
    empleados = PresupuestoSueldos.objects.all()
    # Tomo también los aprendices
    aprendices = PresupuestoAprendiz.objects.filter(concepto="SALARIO APRENDIZ REFORMA")
    # Uno empleados y aprendices en una sola lista
    personas = list(empleados) + list(aprendices)
    for emp in personas:
        # Inicializo acumuladores por mes
        data_meses = {mes: 0 for mes in meses}

        # Sumo de nómina
        for mes in meses:
            data_meses[mes] += getattr(emp, mes, 0)

        # Sumo de comisiones
        comision = PresupuestoComisiones.objects.filter(cedula=emp.cedula).first()
        if comision:
            for mes in meses:
                data_meses[mes] += getattr(comision, mes, 0)
                
        # Sumo de medios de transporte
        medio = PresupuestoMediosTransporte.objects.filter(cedula=emp.cedula).first()
        if medio:
            for mes in meses:
                data_meses[mes] += getattr(medio, mes, 0)

        # Sumo de auxilio transporte
        aux = PresupuestoAuxilioTransporte.objects.filter(cedula=emp.cedula).first()
        if aux:
            for mes in meses:
                data_meses[mes] += getattr(aux, mes, 0)

        # Sumo de horas extra
        extra = PresupuestoHorasExtra.objects.filter(cedula=emp.cedula).first()
        if extra:
            for mes in meses:
                data_meses[mes] += getattr(extra, mes, 0)

        # Creo el registro en cesantías con la suma
        PresupuestoPrimaAux.objects.create(
            cedula=emp.cedula,
            nombre=emp.nombre,
            centro=emp.centro,
            area=emp.area,
            cargo=emp.cargo,
            concepto="PRIMA LEGAL",
            **data_meses,
            total=sum(data_meses.values())
        )

    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_prima(request):
    if request.method == "POST":
        PresupuestoPrima.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de prima eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

# ------------------------Vacaciones------------------
def vacaciones(request):
    return render(request, "presupuesto_nomina/vacaciones.html")

def obtener_presupuesto_vacaciones(request):
    vacaciones = list(PresupuestoVacaciones.objects.values())
    return JsonResponse({"data": vacaciones}, safe=False)

def tabla_auxiliar_vacaciones(request):
    # obtener la vacaciones desde la tabla auxiliar
    parametros = ParametrosPresupuestos.objects.first()
    vacaciones = parametros.vacaciones if parametros else 0
    return render(request, "presupuesto_nomina/aux_vacaciones.html", {'vacaciones': vacaciones})

def subir_presupuesto_vacaciones(request):
    if request.method == "POST":
        temporales = PresupuestoVacacionesAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoVacaciones.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de vacaciones subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_vacaciones_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoVacacionesAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoVacacionesAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoVacacionesAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_vacaciones_temp(request):
    data = list(PresupuestoVacacionesAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_vacaciones_base(request):
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]

    # Limpio la tabla de cesantías antes de recalcular
    PresupuestoVacacionesAux.objects.all().delete()

    # Tomo todos los empleados desde nómina (puede ser tu base principal)
    empleados = PresupuestoSueldos.objects.all()
    # Tomo también los aprendices
    aprendices = PresupuestoAprendiz.objects.filter(concepto="SALARIO APRENDIZ REFORMA")
    # Uno empleados y aprendices en una sola lista
    personas = list(empleados) + list(aprendices)
    for emp in personas:
        # Inicializo acumuladores por mes
        data_meses = {mes: 0 for mes in meses}

        # Sumo de nómina
        for mes in meses:
            data_meses[mes] += getattr(emp, mes, 0)

        # Sumo de comisiones
        comision = PresupuestoComisiones.objects.filter(cedula=emp.cedula).first()
        if comision:
            for mes in meses:
                data_meses[mes] += getattr(comision, mes, 0)
                
        # Sumo de medios de transporte
        medio = PresupuestoMediosTransporte.objects.filter(cedula=emp.cedula).first()
        if medio:
            for mes in meses:
                data_meses[mes] += getattr(medio, mes, 0)

        # Creo el registro en cesantías con la suma
        PresupuestoVacacionesAux.objects.create(
            cedula=emp.cedula,
            nombre=emp.nombre,
            centro=emp.centro,
            area=emp.area,
            cargo=emp.cargo,
            concepto="VACACIONES",
            **data_meses,
            total=sum(data_meses.values())
        )

    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_vacaciones(request):
    if request.method == "POST":
        PresupuestoVacaciones.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de vacaciones eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#----------------------------BONIFICACIONES----------------------
def bonificaciones(request):
    return render(request, "presupuesto_nomina/bonificaciones.html")

def obtener_presupuesto_bonificaciones(request):
    bonificaciones = list(PresupuestoBonificaciones.objects.values())
    return JsonResponse({"data": bonificaciones}, safe=False)

def tabla_auxiliar_bonificaciones(request):
    return render(request, "presupuesto_nomina/aux_bonificaciones.html")

def subir_presupuesto_bonificaciones(request):
    if request.method == "POST":
        temporales = PresupuestoBonificacionesAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoBonificaciones.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de bonificaciones subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_bonificaciones_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoBonificacionesAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoBonificacionesAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoBonificacionesAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_bonificaciones_temp(request):
    data = list(PresupuestoBonificacionesAux.objects.values())
    return JsonResponse(data, safe=False)

# para la carga de bonificaciones se toma el valor de cada mes de la nomina se divide entre 2 y luego entre 12
def cargar_bonificaciones_base(request):
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]

    # Limpio la tabla de bonificaciones antes de recalcular
    PresupuestoBonificacionesAux.objects.all().delete()

    # Tomo todos los empleados desde nómina (puede ser tu base principal)
    empleados = PresupuestoSueldos.objects.all()

    for emp in empleados:
        # Inicializo acumuladores por mes
        data_meses = {mes: 0 for mes in meses}

        # Sumo de nómina y calculo bonificación
        for mes in meses:
            valor_mes = getattr(emp, mes, 0)
            bonificacion_mes = (valor_mes / 2) / 12  # Bonificación es la mitad del salario anual dividido entre 12
            data_meses[mes] += bonificacion_mes

        # Creo el registro en bonificaciones con la suma
        PresupuestoBonificacionesAux.objects.create(
            cedula=emp.cedula,
            nombre=emp.nombre,
            centro=emp.centro,
            area=emp.area,
            cargo=emp.cargo,
            concepto="BONIFICACIÓN",
            **data_meses,
            total=sum(data_meses.values())
        )

    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_bonificaciones(request):
    if request.method == "POST":
        PresupuestoBonificaciones.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de bonificaciones eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#------------auxilio movilidad (novedad de nomina extra, consumibles y tuberculina)----------------
def auxilio_movilidad(request):
    return render(request, "presupuesto_nomina/auxilio_movilidad.html")

def obtener_presupuesto_auxilio_movilidad(request):
    auxilio_movilidad = list(PresupuestoAuxilioMovilidad.objects.values())
    return JsonResponse({"data": auxilio_movilidad}, safe=False)

def tabla_auxiliar_auxilio_movilidad(request):
    parametros = ParametrosPresupuestos.objects.first()
    incremento_ipc = parametros.incremento_ipc if parametros else 0
    return render(request, "presupuesto_nomina/aux_auxilio_movilidad.html", {'incrementoIPC': incremento_ipc})

def subir_presupuesto_auxilio_movilidad(request):
    if request.method == "POST":
        temporales = PresupuestoAuxilioMovilidadAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoAuxilioMovilidad.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de auxilio de movilidad subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_auxilio_movilidad_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoAuxilioMovilidadAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoAuxilioMovilidadAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoAuxilioMovilidadAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_auxilio_movilidad_temp(request):
    data = list(PresupuestoAuxilioMovilidadAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_auxilio_movilidad_base(request):
    PresupuestoAuxilioMovilidadAux.objects.all().delete()  # limpia tabla temporal
    base_data = ConceptosFijosYVariables.objects.values(
        "cedula","nombre","nombrecar","nomcosto","nombre_cen", "nombre_con", "enero", "febrero", "marzo", "abril", "mayo",
        "junio", "julio", "agosto", "total"
    )

    # filtrar solo concepto que sea igual a 389
    base_data = base_data.filter(concepto="E14")
    
    for row in base_data:
        PresupuestoAuxilioMovilidadAux.objects.create(
            cedula=row["cedula"],
            nombre=row["nombre"],
            cargo=row["nombrecar"],
            area=row["nomcosto"],
            centro=row["nombre_cen"],
            concepto=row["nombre_con"],
            enero=row["enero"] or 0,
            febrero=row["febrero"] or 0,
            marzo=row["marzo"] or 0,
            abril=row["abril"] or 0,
            mayo=row["mayo"] or 0,
            junio=row["junio"] or 0,
            julio=row["julio"] or 0,
            agosto=row["agosto"] or 0,
            total=row["total"] or 0,
        )

        
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_auxilio_movilidad(request):
    if request.method == "POST":
        PresupuestoAuxilioMovilidad.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de auxilio de movilidad eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

# ----------------------------SEGURIDAD SOCIAL---------------------
def seguridad_social(request):
    return render(request, "presupuesto_nomina/seguridad_social.html")

def obtener_presupuesto_seguridad_social(request):
    seguridad_social = list(PresupuestoSeguridadSocial.objects.values())
    return JsonResponse({"data": seguridad_social}, safe=False)

def tabla_auxiliar_seguridad_social(request):
    return render(request, "presupuesto_nomina/aux_seguridad_social.html")

def subir_presupuesto_seguridad_social(request):
    if request.method == "POST":
        temporales = PresupuestoSeguridadSocialAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoSeguridadSocial.objects.create(
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                concepto=temp.concepto,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de seguridad social subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_seguridad_social_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoSeguridadSocialAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoSeguridadSocialAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoSeguridadSocialAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_seguridad_social_temp(request):
    data = list(PresupuestoSeguridadSocialAux.objects.values())
    return JsonResponse(data, safe=False)

# para obtener la seguridad social se debe agrupar las tablas de nomina, comisiones, horas extra y medios de transporte por sede(centro) y por area y sumar los valores de cada mes
from django.db.models import Avg
def cargar_seguridad_social_base(request):
    # Promedios agrupados por sede y área
    promedios_arl = ConceptosFijosYVariables.objects.values(
        "nombre_cen", "nomcosto"
    ).annotate(
        promedio_arl=Avg("arlporc")
    )
    
    # Diccionario: {(sede, area): promedio_arl}
    arl_porcentajes = {
        (item["nombre_cen"], item["nomcosto"]): (item["promedio_arl"] / 100.0)
        for item in promedios_arl if item["promedio_arl"] is not None
    }
    
    # imprimir el diccionario
    print(arl_porcentajes)
    
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]

    # Diccionario de conceptos con su porcentaje
    conceptos = {
        "APORTE PENSIÓN": 0.12,               # 12%
        "APORTE SALUD": 0.085,                # 8.5%
        "APORTE CAJAS DE COMPENSACIÓN": 0.04, # 4%
        "APORTE A.R.L": None,              # 0.931%
        "APORTE SENA": 0.02,                  # 2%
        "APORTE I.C.B.F": 0.03                # 3%
    }

    # Salario mínimo (ajusta según el año correspondiente)
    parametros = ParametrosPresupuestos.objects.first()
    salarioIncremento = parametros.salario_minimo + (parametros.salario_minimo * (parametros.incremento_salarial / 100))
    TOPE = (salarioIncremento) * 10
    
    # Limpio tabla antes de recalcular
    PresupuestoSeguridadSocialAux.objects.all().delete()

    # Diccionarios separados para acumulación
    acumulados_generales = defaultdict(lambda: {mes: 0 for mes in meses})  # pensión, cajas, ARL, SENA
    acumulados_salud_icbf = defaultdict(lambda: {mes: 0 for mes in meses})  # solo > 10 SMMLV
    acumulados_aprendiz_salud = defaultdict(lambda: {mes: 0 for mes in meses}) # aprendices con salario aprendiz

    empleados = PresupuestoSueldos.objects.all()
    aprendices = PresupuestoAprendiz.objects.all()
    
    for emp in empleados:
        key = (emp.centro, emp.area)

        # Calcular base mensual del empleado (nomina + comision + medio + extra)
        base_empleado = {mes: getattr(emp, mes, 0) for mes in meses}

        # Comisiones
        comision = PresupuestoComisiones.objects.filter(cedula=emp.cedula).first()
        if comision:
            for mes in meses:
                base_empleado[mes] += getattr(comision, mes, 0)

        # Medios de transporte
        medio = PresupuestoMediosTransporte.objects.filter(cedula=emp.cedula).first()
        if medio:
            for mes in meses:
                base_empleado[mes] += getattr(medio, mes, 0)

        # Horas extra
        extra = PresupuestoHorasExtra.objects.filter(cedula=emp.cedula).first()
        if extra:
            for mes in meses:
                base_empleado[mes] += getattr(extra, mes, 0)

        
        # Sumar a los acumulados
        # → siempre suman a pensión, cajas, ARL y SENA
        for mes in meses:
            acumulados_generales[key][mes] += base_empleado[mes]

        salario_base = emp.salario_base
        nuevo_salario = salario_base + (salario_base * (parametros.incremento_salarial / 100))
        
        # → si excede los 10 SMMLV, también suma a salud e ICBF
        if nuevo_salario > TOPE:
            for mes in meses:
                acumulados_salud_icbf[key][mes] += base_empleado[mes]

    # === APRENDICES (tabla aparte) ===
    for apr in aprendices:
        if apr.concepto == "SALARIO APRENDIZ":
            key = (apr.centro, apr.area)
            for mes in meses:
                acumulados_aprendiz_salud[key][mes] += getattr(apr, mes, 0)
        if apr.concepto == "SALARIO APRENDIZ REFORMA":
            # además suman a todos los aportes (como parte de la base general)
            key = (apr.centro, apr.area)
            for mes in meses:
                acumulados_generales[key][mes] += getattr(apr, mes, 0)

    # Crear registros en la tabla
    for (centro, area), data_meses in acumulados_generales.items():
        for concepto, porcentaje in conceptos.items():
            if concepto in ["APORTE SALUD", "APORTE SENA", "APORTE I.C.B.F"]:
                data = None

                # 1. Si hay empleados > 10 SMMLV
                if (centro, area) in acumulados_salud_icbf:
                    data = acumulados_salud_icbf[(centro, area)]

                # 2. Si son aprendices con SALARIO APRENDIZ → solo para SALUD
                if concepto == "APORTE SALUD" and (centro, area) in acumulados_aprendiz_salud:
                    aprendiz_data = acumulados_aprendiz_salud[(centro, area)]
                    if data:
                        data = {mes: data[mes] + aprendiz_data[mes] for mes in meses}
                    else:
                        data = aprendiz_data

                    # sobrescribo el porcentaje SOLO para aprendices
                    porcentaje = 0.125 

                # Si no aplica, salto
                if not data:
                    continue
            elif concepto == "APORTE A.R.L":
                # Los aprendices con SALARIO APRENDIZ también deben aportar ARL
                data = data_meses.copy()
                if (centro, area) in acumulados_aprendiz_salud:
                    aprendiz_data = acumulados_aprendiz_salud[(centro, area)]
                    data = {mes: data[mes] + aprendiz_data[mes] for mes in meses}
                # aquí reemplazamos el porcentaje fijo con el promedio real
                porcentaje = arl_porcentajes.get((centro, area), 0.00931)
            else:
                data = data_meses

            valores_mensuales = {mes: round(data[mes] * porcentaje, 2) for mes in meses}
            PresupuestoSeguridadSocialAux.objects.create(
                nombre="SEGURIDAD SOCIAL",
                centro=centro,
                area=area,
                concepto=concepto,
                **valores_mensuales,
                total=round(sum(valores_mensuales.values()), 2)
            )
    # === AGRUPAR POR ÁREA LOS DE ASISTENCIA TÉCNICA ===
    asistencia = (
        PresupuestoSeguridadSocialAux.objects
        .filter(area__in=["ASISTENCIA TECNICA PROPIA", "ASISTENCIA TECNICA CONVENIO"])
        .values("area", "concepto")  # agrupamos por área y concepto
        .annotate(
            enero=Sum("enero"),
            febrero=Sum("febrero"),
            marzo=Sum("marzo"),
            abril=Sum("abril"),
            mayo=Sum("mayo"),
            junio=Sum("junio"),
            julio=Sum("julio"),
            agosto=Sum("agosto"),
            septiembre=Sum("septiembre"),
            octubre=Sum("octubre"),
            noviembre=Sum("noviembre"),
            diciembre=Sum("diciembre"),
            total=Sum("total"),
        )
    )
    
    # Insertar en la tabla como "ASISTENCIA TECNICA AGRUPADA"
    for item in asistencia:
        PresupuestoSeguridadSocialAux.objects.create(
            nombre="SEGURIDAD SOCIAL",
            centro="",  # omitimos centro
            area=item["area"],  # mantenemos el nombre de área original (PROPIA o CONVENIO)
            concepto=item["concepto"],
            enero=item["enero"] or 0,
            febrero=item["febrero"] or 0,
            marzo=item["marzo"] or 0,
            abril=item["abril"] or 0,
            mayo=item["mayo"] or 0,
            junio=item["junio"] or 0,
            julio=item["julio"] or 0,
            agosto=item["agosto"] or 0,
            septiembre=item["septiembre"] or 0,
            octubre=item["octubre"] or 0,
            noviembre=item["noviembre"] or 0,
            diciembre=item["diciembre"] or 0,
            total=item["total"] or 0,
        )
    # 2. Eliminamos las filas originales (con centro)
    PresupuestoSeguridadSocialAux.objects.filter(
        area__in=["ASISTENCIA TECNICA PROPIA", "ASISTENCIA TECNICA CONVENIO"]
    ).exclude(centro="").delete()
    

    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_seguridad_social(request):
    if request.method == "POST":
        PresupuestoSeguridadSocial.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de seguridad social eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#--------------------------INTERESES DE CESANTIAS----------------------
def intereses_cesantias(request):
    return render(request, "presupuesto_nomina/intereses_cesantias.html")

def obtener_presupuesto_intereses_cesantias(request):
    intereses_cesantias = list(PresupuestoInteresesCesantias.objects.values())
    return JsonResponse({"data": intereses_cesantias}, safe=False)

def tabla_auxiliar_intereses_cesantias(request):
    # obtener la cesantías desde la tabla auxiliar
    parametros = ParametrosPresupuestos.objects.first()
    interesesCesantias = parametros.intereses_cesantias if parametros else 0
    return render(request, "presupuesto_nomina/aux_intereses_cesantias.html", {'interesesCesantias': interesesCesantias})

def subir_presupuesto_intereses_cesantias(request):
    if request.method == "POST":
        temporales = PresupuestoInteresesCesantiasAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoInteresesCesantias.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de intereses de cesantías subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_intereses_cesantias_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoInteresesCesantiasAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoInteresesCesantiasAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoInteresesCesantiasAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_intereses_cesantias_temp(request):
    data = list(PresupuestoInteresesCesantiasAux.objects.values())
    return JsonResponse(data, safe=False)

# para la carga de intereses de cesantías se toma el valor de cada mes de la tabla de cesantias, esto para enero o sea el primer mes y para el mes siguiente se toma el valor de enero, se multiplica por el 200% y se suma el valor del mes anterior, esto hasta completar los 12 meses
def cargar_intereses_cesantias_base(request):
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]

    # parametrización
    parametros = ParametrosPresupuestos.objects.first()
    interesCesantias = parametros.intereses_cesantias if parametros else 0
    print(f"Intereses cesantías parámetro: {interesCesantias}")

    # limpio tabla auxiliar de intereses antes de recalcular
    PresupuestoInteresesCesantiasAux.objects.all().delete()

    # días acumulados por mes (ejemplo típico calendario 30 días/mes)
    dias_acumulados = [30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330, 360]
    
    # recorro cada registro de cesantías (por persona / fila)
    cesantias_qs = PresupuestoCesantias.objects.all()
    for reg in cesantias_qs:
        # valores de cesantías base mes a mes
        cesantias_base = [getattr(reg, m) or 0 for m in meses]

        valores = {}
        intereses_acumulados = 0  # lo ya calculado hasta el mes anterior

        for i, mes in enumerate(meses):
            suma_cesantias = sum(cesantias_base[: i + 1])  # hasta mes actual
            interes_teorico = suma_cesantias * (interesCesantias / 100) * (dias_acumulados[i] / 360)
            interes_mes = interes_teorico - intereses_acumulados

            valores[mes] = interes_mes
            intereses_acumulados += interes_mes

        # suma total
        total = sum(Decimal(valores[m]) for m in meses)

        create_kwargs = {m: int(round(float(valores[m]))) for m in meses}

        PresupuestoInteresesCesantiasAux.objects.create(
            cedula=reg.cedula,
            nombre=reg.nombre,
            centro=reg.centro,
            area=reg.area,
            cargo=reg.cargo,
            concepto="INTERESES CESANTÍAS",
            **create_kwargs,
            total=int(round(float(total)))
        )

    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_intereses_cesantias(request):
    if request.method == "POST":
        PresupuestoInteresesCesantias.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de intereses de cesantías eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#----------------------------APRENDIZ------------------
def aprendiz(request):
    return render(request, "presupuesto_nomina/aprendiz.html")

def obtener_presupuesto_aprendiz(request):
    aprendiz = list(PresupuestoAprendiz.objects.values())
    return JsonResponse({"data": aprendiz}, safe=False)

def tabla_auxiliar_aprendiz(request):
    parametros = ParametrosPresupuestos.objects.first()
    incrementoSalarial = parametros.incremento_salarial if parametros else 0
    return render(request, "presupuesto_nomina/aux_aprendiz.html", {'incrementoSalarial': incrementoSalarial})

def subir_presupuesto_aprendiz(request):
    if request.method == "POST":
        temporales = PresupuestoAprendizAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoAprendiz.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                salario_base=temp.salario_base,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de aprendices subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)  
    
def guardar_aprendiz_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "salario_base", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoAprendizAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoAprendizAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoAprendizAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_aprendiz_temp(request):
    data = list(PresupuestoAprendizAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_aprendiz_base(request):
    PresupuestoAprendizAux.objects.all().delete()  # limpia tabla temporal
    base_data = ConceptosFijosYVariables.objects.values(
        "cedula","nombre","nombrecar","nomcosto","nombre_cen", "nombre_con", "concepto_f")
    
    # filtrar solo concepto que sea igual a 003 y 006
    base_data = base_data.filter(concepto__in=["003", "006"])
    
    for row in base_data:
        PresupuestoAprendizAux.objects.create(
            cedula=row["cedula"],
            nombre=row["nombre"],
            cargo=row["nombrecar"],
            area=row["nomcosto"],
            centro=row["nombre_cen"],
            concepto=row["nombre_con"],
            salario_base=row["concepto_f"],
        )
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_aprendiz(request):
    if request.method == "POST":
        PresupuestoAprendiz.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de aprendices eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#--------------------------BONIFICACIONES FOCO----------------------
def bonificaciones_foco(request):
    return render(request, "presupuesto_nomina/bonificaciones_foco.html")

def obtener_presupuesto_bonificaciones_foco(request):
    bonificaciones_foco = list(PresupuestoBonificacionesFoco.objects.values())
    return JsonResponse({"data": bonificaciones_foco}, safe=False)

def tabla_auxiliar_bonificaciones_foco(request):
    return render(request, "presupuesto_nomina/aux_bonificaciones_foco.html")

def subir_presupuesto_bonificaciones_foco(request):
    if request.method == "POST":
        temporales = PresupuestoBonificacionesFocoAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoBonificacionesFoco.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de bonificaciones subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_bonificaciones_foco_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoBonificacionesFocoAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoBonificacionesFocoAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoBonificacionesFocoAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_bonificaciones_foco_temp(request):
    data = list(PresupuestoBonificacionesFocoAux.objects.values())
    return JsonResponse(data, safe=False)

# para la carga de bonificaciones foco se el valor total del mes de la tabla comisiones y se agrega al mes correspondiente en la tabla temporal de bonificaciones foco

def cargar_bonificaciones_foco_base(request):
    # limpio tabla auxiliar de bonificaciones antes de recalcular
    PresupuestoBonificacionesFocoAux.objects.all().delete()

    parametros = ParametrosPresupuestos.objects.first()
    incrementoComisiones = parametros.incremento_comisiones if parametros else 0

    
    # agrupamos por persona sumando los meses de enero a junio
    comisiones_agrupadas = (
        PresupuestoComisiones.objects
        .values("cedula", "nombre", "centro", "area", "cargo")
        .annotate(
            total=Sum("total"),        # total de todos los meses
            total_ene_jun=Sum("enero") + Sum("febrero") + Sum("marzo") + Sum("abril") + Sum("mayo") + Sum("junio"),
            enero=Sum("enero"),
            febrero=Sum("febrero"),
            marzo=Sum("marzo"),
            abril=Sum("abril"),
            mayo=Sum("mayo"),
            junio=Sum("junio"),
            julio=Sum("julio"),
            agosto=Sum("agosto"),
            septiembre=Sum("septiembre"),
            octubre=Sum("octubre"),
            noviembre=Sum("noviembre"),
            diciembre=Sum("diciembre"),
        )
    )

    for com in comisiones_agrupadas:
        # -------------------------
        # Cálculo para enero usando total anual / 12
        if com["total"] > 0:
            # Ajustar cada mes según incrementoComisiones
            incremento_factor = 1 + (incrementoComisiones / 100)
            enero_base = (com["enero"] or 0) / incremento_factor
            febrero_base = (com["febrero"] or 0) / incremento_factor
            marzo_base = (com["marzo"] or 0) / incremento_factor
            abril_base = (com["abril"] or 0) / incremento_factor
            mayo_base = (com["mayo"] or 0) / incremento_factor
            junio_base = (com["junio"] or 0) / incremento_factor
            julio_base = (com["julio"] or 0) / incremento_factor
            agosto_base = (com["agosto"] or 0) / incremento_factor
            septiembre_base = (com["septiembre"] or 0) / incremento_factor
            octubre_base = (com["octubre"] or 0) / incremento_factor
            noviembre_base = (com["noviembre"] or 0) / incremento_factor
            diciembre_base = (com["diciembre"] or 0) / incremento_factor
            total_ajustado = (
                enero_base + febrero_base + marzo_base + abril_base +
                mayo_base + junio_base + julio_base + agosto_base +
                septiembre_base + octubre_base + noviembre_base + diciembre_base
            )
            enero_valor = total_ajustado / 12

        # -------------------------
        # Cálculo para julio: promedio ene-jun / 2
        julio_valor = 0
        if com["total_ene_jun"] > 0:
            promedio_ene_jun = com["total_ene_jun"] / 6
            julio_valor = promedio_ene_jun / 2

        PresupuestoBonificacionesFocoAux.objects.create(
            cedula=com["cedula"],
            nombre=com["nombre"],
            centro=com["centro"],
            area=com["area"],
            cargo=com["cargo"],
            concepto="BONIFICACIÓN FOCO",
            enero=enero_valor,
            febrero=0,
            marzo=0,
            abril=0,
            mayo=0,
            junio=0,
            julio=julio_valor,
            agosto=0,
            septiembre=0,
            octubre=0,
            noviembre=0,
            diciembre=0,
            total=enero_valor + julio_valor,  # suma lo de enero y julio
        )
    
    # 2️⃣ Empleados de ConceptosFijosYVariables filtrando COMISIONES y excluyendo ciertos cargos
    cargos_excluidos = [
        "ASESOR COMERCIAL",
        "AUXILIAR COMERCIAL",
        "JEFE DE ALMACEN",
        "DIRECTOR COMERCIAL SUBDISTRIBUCION Y DIGITAL",
        "DIRECTOR COMERCIAL GRANDES ESPECIES Y PUNTO VENTA",
    ]
    
    empleados_fijos = (
        PresupuestoSueldos.objects
        .exclude(cargo__in=cargos_excluidos)
        .values("cedula", "nombre", "centro", "area", "cargo")
        .annotate(total=Sum("total"))
    )
    
    # 2️⃣ Insertar en la tabla de bonificaciones con enero = 220000 + IPC
    for emp in empleados_fijos:
        enero_valor = 220000 * (1 + incrementoComisiones / 100)
        PresupuestoBonificacionesFocoAux.objects.create(
            cedula=emp["cedula"],
            nombre=emp["nombre"],
            centro=emp["centro"],
            area=emp["area"],
            cargo=emp["cargo"],
            concepto="BONIFICACIÓN FOCO",
            enero=enero_valor,
            febrero=0,
            marzo=0,
            abril=0,
            mayo=0,
            junio=0,
            julio=0,
            agosto=0,
            septiembre=0,
            octubre=0,
            noviembre=0,
            diciembre=0,
            total=enero_valor,  # solo enero por ahora
        )


    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_bonificaciones_foco(request):
    if request.method == "POST":
        PresupuestoBonificacionesFoco.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de bonificaciones foco eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#------------------------AUXILIO EDUCACION----------------------
def auxilio_educacion(request):
    return render(request, "presupuesto_nomina/auxilio_educacion.html")

def obtener_presupuesto_auxilio_educacion(request):
    auxilio_educacion = list(PresupuestoAuxilioEducacion.objects.values())
    return JsonResponse({"data": auxilio_educacion}, safe=False)

def tabla_auxiliar_auxilio_educacion(request):
    return render(request, "presupuesto_nomina/aux_auxilio_educacion.html")

def subir_presupuesto_auxilio_educacion(request):
    if request.method == "POST":
        temporales = PresupuestoAuxilioEducacionAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoAuxilioEducacion.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de auxilio de educación subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)

def guardar_auxilio_educacion_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoAuxilioEducacionAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoAuxilioEducacionAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoAuxilioEducacionAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)


def obtener_auxilio_educacion_temp(request):
    data = list(PresupuestoAuxilioEducacionAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_auxilio_educacion_base(request):
    # limpio tabla auxiliar de auxilio educación antes de recalcular
    PresupuestoAuxilioEducacionAux.objects.all().delete()
    base_data = ConceptoAuxilioEducacion.objects.values(
        "cedula","nombre","nombrecar","nomcosto","nombre_cen","diciembre", "nombre_con", "total"
    )
    # filtrar solo concepto = 001
    base_data = base_data.filter(concepto="016")
    
    parametros = ParametrosPresupuestos.objects.first()
    incrementoIPC = parametros.incremento_ipc if parametros else 0
    
    for row in base_data:
        diciembreIncremento = row["diciembre"] * (1 + incrementoIPC / 100)
        PresupuestoAuxilioEducacionAux.objects.create(
            cedula=row["cedula"],
            nombre=row["nombre"],
            cargo=row["nombrecar"],
            area=row["nomcosto"],
            centro=row["nombre_cen"],
            concepto=row["nombre_con"],
            diciembre=diciembreIncremento,
            total=diciembreIncremento,
        )
    
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_auxilio_educacion(request):
    if request.method == "POST":
        PresupuestoAuxilioEducacion.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de auxilio de educación eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#------------------------BONOS KYROVET----------------------
def bonos_kyrovet(request):
    return render(request, "presupuesto_nomina/bonos_kyrovet.html")

def obtener_presupuesto_bonos_kyrovet(request):
    bonos_kyrovet = list(PresupuestoBonosKyrovet.objects.values())
    return JsonResponse({"data": bonos_kyrovet}, safe=False)

def tabla_auxiliar_bonos_kyrovet(request):
    parametros = ParametrosPresupuestos.objects.first()
    incrementoIPC = parametros.incremento_ipc if parametros else 0
    return render(request, "presupuesto_nomina/aux_bonos_kyrovet.html", {'incrementoIPC': incrementoIPC})

def subir_presupuesto_bonos_kyrovet(request):
    if request.method == "POST":
        temporales = PresupuestoBonosKyrovetAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoBonosKyrovet.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                base=temp.base,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de bonos Kyrovet subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_bonos_kyrovet_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto","base", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoBonosKyrovetAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoBonosKyrovetAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoBonosKyrovetAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_bonos_kyrovet_temp(request):
    data = list(PresupuestoBonosKyrovetAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_bonos_kyrovet_base(request):
    # limpio tabla auxiliar de bonos kyrovet antes de recalcular
    PresupuestoBonosKyrovetAux.objects.all().delete()
    base_data = ConceptosFijosYVariables.objects.values(
        "cedula","nombre","nombrecar","nomcosto","nombre_cen", "nombre_con", "concepto_f"
    )
    # filtrar solo concepto = 001
    base_data = base_data.filter(nombre_con="BONO CANASTA KYROVET")
    parametros = ParametrosPresupuestos.objects.first()
    incrementoIPC = parametros.incremento_ipc if parametros else 0
   
    for row in base_data:
        febreroIncremento = row["concepto_f"] * (1 + incrementoIPC / 100)
        PresupuestoBonosKyrovetAux.objects.create(
            cedula=row["cedula"],
            nombre=row["nombre"],
            cargo=row["nombrecar"],
            area=row["nomcosto"],
            centro=row["nombre_cen"],
            concepto=row["nombre_con"],
            base=row["concepto_f"],
            febrero=febreroIncremento,
            total=febreroIncremento,
        )
    
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_bonos_kyrovet(request):
    if request.method == "POST":
        PresupuestoBonosKyrovet.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de bonos Kyrovet eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)


# -----------------------------PRESUPUESTO GENERAL----------------------------------------------------------------------
#SELECCIÓN DE CUENTAS CONTABLES-----------------
def seleccion_cuentas_contables(request):
    cuentas = list(CuentasContables.objects.values_list('cuenta', flat=True))
    nom_cuentas = list(CuentasContables.objects.values_list('nom_cuenta', flat=True))
 
    # Creamos el diccionario 
    cuentas_dict = dict(zip(cuentas, nom_cuentas))
    return JsonResponse({"cuentas": cuentas, "nom_cuentas": nom_cuentas, "cuentas_dict": cuentas_dict}, safe=False)

# -PRESUPUESTO TECNOLOGIA--------------------------------
def presupuesto_tecnologia(request):
    return render(request, "presupuesto_general/presupuesto_tecnologia.html")

def obtener_presupuesto_tecnologia(request):
    tecnologia = list(PresupuestoTecnologia.objects.values())
    return JsonResponse({"data": tecnologia}, safe=False)

def tabla_auxiliar_tecnologia(request):
    return render(request, "presupuesto_general/aux_presupuesto_tecnologia.html")

def subir_presupuesto_tecnologia(request):
    if request.method == "POST":
        temporales = PresupuestoTecnologiaAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoTecnologia.objects.create(
                centro_tra=temp.centro_tra,
                nombre_cen=temp.nombre_cen,
                codcosto=temp.codcosto,
                responsable=temp.responsable,
                cuenta=temp.cuenta,
                cuenta_mayor=temp.cuenta_mayor,
                detalle_cuenta=temp.detalle_cuenta,
                sede_distribucion=temp.sede_distribucion,
                proveedor=temp.proveedor,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
                comentario=temp.comentario,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de tecnología subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_tecnologia_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total", "comentario"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoTecnologiaAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoTecnologiaAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoTecnologiaAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_tecnologia_temp(request):
    data = list(PresupuestoTecnologiaAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_tecnologia_base(request):
    # limpio tabla auxiliar de tecnología antes de recalcular
    PresupuestoTecnologiaAux.objects.all().delete()
    base_data = Plantillagastos2025.objects.values(
       "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    )
    # filtrar por responsable = 'DIEGO CANO'
    base_data = base_data.filter(responsable__iexact="DIEGO CANO")
    
    for row in base_data:
        PresupuestoTecnologiaAux.objects.create(
            centro_tra=row["centro_tra"],
            nombre_cen=row["nombre_cen"],
            codcosto=row["codcosto"],
            responsable=row["responsable"],
            cuenta=row["cuenta"],
            cuenta_mayor=row["cuenta_mayor"],
            detalle_cuenta=row["detalle_cuenta"],
            sede_distribucion=row["sede_distribucion"],
            proveedor=row["proveedor"],
            enero=row["enero"],
            febrero=row["febrero"],
            marzo=row["marzo"],
            abril=row["abril"],
            mayo=row["mayo"],
            junio=row["junio"],
            julio=row["julio"], 
            agosto=row["agosto"],
            septiembre=row["septiembre"],
            octubre=row["octubre"],
            noviembre=row["noviembre"],
            diciembre=row["diciembre"],
            total=row["enero"] + row["febrero"] + row["marzo"] + row["abril"] + row["mayo"] + row["junio"] + row["julio"] + row["agosto"] + row["septiembre"] + row["octubre"] + row["noviembre"] + row["diciembre"],
            comentario = ""
        )
    
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_tecnologia(request):
    if request.method == "POST":
        PresupuestoTecnologia.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de tecnología eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)
    