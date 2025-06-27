import statistics
import numpy as np
from pronosticosWebApp.pronosticos.suavizacionExpSimple import (
    PronosticoExpSimple as ses,
)
from pronosticosWebApp.pronosticos.suavizacionExpDoble import PronosticoExpDoble as sed
import pandas as pd
import math
from pronosticosWebApp.pronosticos.promedioMovil import PronosticoMovil as pm
from statistics import multimode 
from pronosticosWebApp.models import LeadTime
from conteoApp.models import Inventario
from django.db.models import Sum
from datetime import date
class Pronosticos:

    def __init__(self):
        pass

    def pronosticos():
        
        (
            df_pronostico_p3,
            df_demanda
        ) = pm.promedioMovil_3(3)
        # obtener los datos del Inventario
        inv = Inventario.objects.all()
        # agrupar inv por sku, sku_nom, y bod y sumar inv_saldo
        inv = inv.values('sku', 'sku_nom', 'bod').annotate(inv_saldo=Sum('inv_saldo'))
        df_inventario = pd.DataFrame(list(inv))
        reemplazo = {
            '0105': '0101',
            '0102': '0101',
            '0105': '0101',
            '0202': '0201',
            '0205': '0201',
            '0305': '0301',
            '0402': '0401',
            '0405': '0401'
        }
        # Reemplazar los valores en la columna 'bod' del DataFrame df_inventario
        df_inventario['bod'] = df_inventario['bod'].replace(reemplazo)
        # sumar los valores de inv_saldo por sku, sku_nom y bod
        df_inventario = df_inventario.groupby(['sku', 'sku_nom', 'bod'], as_index=False).agg({'inv_saldo': 'sum'})
        
        # Diccionario de reemplazo
        reemplazos_bod = {
            '0105': '0101',
            '0205': '0201',
            '0305': '0301',
            '0405': '0401'
        }
        
        # eliminar duplicados en df_demanda
        df_demanda_drop = df_demanda.drop_duplicates(subset=['sku', 'sku_nom', 'bod']).reset_index(drop=True)
        
        # Asegúrate de que las columnas relevantes sean tipo string
        df_demanda_drop['bod'] = df_demanda_drop['bod'].astype(str)
        df_inventario['bod'] = df_inventario['bod'].astype(str)
        df_demanda_drop['sku'] = df_demanda_drop['sku'].astype(str)
        df_inventario['sku'] = df_inventario['sku'].astype(str)
        df_demanda_drop['sku_nom'] = df_demanda_drop['sku_nom'].astype(str)
        df_inventario['sku_nom'] = df_inventario['sku_nom'].astype(str)
        
        # Reemplazar los valores en la columna 'bod' del DataFrame df_demanda
        df_demanda_bod = df_demanda_drop.copy()
        df_demanda_bod['bod'] = df_demanda_bod['bod'].replace(reemplazos_bod)
        # Estandariza tipos en ambas tablas antes del merge:
        cols_merge = ['sku', 'bod']
        for col in cols_merge:
            df_demanda_bod[col] = df_demanda_bod[col].astype(str).str.strip()
            df_inventario[col] = df_inventario[col].astype(str).str.strip()
        
        df_demanda_final = pd.merge(
            df_demanda_bod,
            df_inventario[['sku', 'sku_nom', 'bod', 'inv_saldo']],
            on=['sku', 'sku_nom', 'bod'],
            how='left'
        )
        df_demanda_final.rename(columns={'inv_saldo': 'inventario'}, inplace=True)
        # Rellenar con 0 si no hay coincidencia
        df_demanda_final['inventario'] = df_demanda_final['inventario'].fillna(0)
        # Convertir inv_saldo a entero si quieres evitar decimales
        # merged_df['inv_saldo'] = merged_df['inv_saldo'].astype(int)
        
        # Diccionario de reemplazo
        reverse_reemplazos_bod = {
            '0101': '0105',
            '0201': '0205',
            '0301': '0305',
            '0401': '0405'
        }
        df_demanda_final['bod'] = df_demanda_final['bod'].replace(reverse_reemplazos_bod)
        
        (
            df_pronostico_p4
        ) = pm.promedioMovil_4(4)
        (
            df_pronostico_p5
        ) = pm.promedioMovil_5(5)

        (
            df_pronostico_ses
        ) = ses.pronosticoExpSimple(0.5)
        (
            df_pronostico_sed
        ) = sed.pronosticoExpDoble(0.5, 0.5, 1)

        # extraer los datos de df_pronostico_p3 del mes 13
        # df_total = df_pronostico_p3[df_pronostico_p3['mm'] == 13].copy()
        
        # cambiar el nombre de las columnas de df_pronostico_p4 a ECM_P4 y promedio_movil_p4
        df_pronostico_p4.rename(columns={'ECM': 'ECM_P4', 'promedio_movil': 'promedio_movil_p4'}, inplace=True)
        # cambiar el nombre de las columnas de df_pronostico_p5 a ECM_P5
        df_pronostico_p5.rename(columns={'ECM': 'ECM_P5', 'promedio_movil': 'promedio_movil_p5'}, inplace=True)
        # cambiar el nombre de las columnas de df_pronostico_ses a ECM_SES
        df_pronostico_ses.rename(columns={'ECM': 'ECM_SES'}, inplace=True)
        # cambiar el nombre de las columnas de df_pronostico_sed a ECM_SED
        df_pronostico_sed.rename(columns={'ECM': 'ECM_SED'}, inplace=True)
        
        df_total = pd.merge(
            df_demanda_final,
            df_pronostico_p3[df_pronostico_p3['mm'] == 13][['sku', 'sku_nom', 'bod', 'ECM', 'promedio_movil']],
            on=['sku', 'sku_nom', 'bod'],
            how='left'
        )
        df_total = pd.merge(
            df_total,
            df_pronostico_p4[df_pronostico_p4['mm'] == 13][['sku', 'sku_nom', 'bod', 'ECM_P4', 'promedio_movil_p4']],
            on=['sku', 'sku_nom', 'bod'],
            how='left'
        )
        df_total = pd.merge(
            df_total,
            df_pronostico_p5[df_pronostico_p5['mm'] == 13][['sku', 'sku_nom', 'bod', 'ECM_P5', 'promedio_movil_p5']],
            on=['sku', 'sku_nom', 'bod'],
            how='left'
        )
        df_total = pd.merge(
            df_total,
            df_pronostico_ses[df_pronostico_ses['mm'] == 13][['sku', 'sku_nom', 'bod', 'ECM_SES', 'pronostico_ses']],
            on=['sku', 'sku_nom', 'bod'],
            how='left'
        )
        df_total = pd.merge(
            df_total,
            df_pronostico_sed[df_pronostico_sed['mm'] == 13][['sku', 'sku_nom', 'bod', 'ECM_SED', 'pronostico_sed']],
            on=['sku', 'sku_nom', 'bod'],
            how='left'
        )
        
        # eliminar columnas umd, total, precio, promedio_movil, error, errorMAPE, errorMAPEPrima, errorECM, MAD, MAPE, MAPE_Prima
        # df_total = df_total.drop(
        #     columns=[
        #         'total',
        #         'promedio_movil',
        #         'error',
        #         'errorMAPE',
        #         'errorMAPEPrima',
        #         'errorECM',
        #         'MAD',
        #         'MAPE',
        #         'MAPE_Prima'
        #     ]
        # )
        
        # df_total.loc[:,'ECM_P4'] = df_pronostico_p4[df_pronostico_p4['mm'] == 13]['ECM'].values
        # df_total.loc[:,'ECM_P5'] = df_pronostico_p5[df_pronostico_p5['mm'] == 13]['ECM'].values
        # df_total.loc[:,'ECM_SES'] = df_pronostico_ses[df_pronostico_ses['mm'] == 13]['ECM'].values
        # df_total.loc[:,'ECM_SED'] = df_pronostico_sed[df_pronostico_sed['mm'] == 13]['ECM'].values
        
        # añadir columnas para los pronosticos de cada metodo
        # df_total.loc[:,'promedio_movil'] = df_pronostico_p3[df_pronostico_p3['mm'] == 13]['promedio_movil'].values
        # df_total.loc[:,'promedio_movil_p4'] = df_pronostico_p4[df_pronostico_p4['mm'] == 13]['promedio_movil'].values
        # df_total.loc[:,'promedio_movil_p5'] = df_pronostico_p5[df_pronostico_p5['mm'] == 13]['promedio_movil'].values
        # df_total.loc[:,'pronostico_ses'] = df_pronostico_ses[df_pronostico_ses['mm'] == 13]['pronostico_ses'].values
        # df_total.loc[:,'pronostico_sed'] = df_pronostico_sed[df_pronostico_sed['mm'] == 13]['pronostico_sed'].values
        
        # Asegúrate de que todas las columnas estén en formato numérico
        cols_ecm = ['ECM', 'ECM_P4', 'ECM_P5', 'ECM_SES', 'ECM_SED']
        # df_ecm_total[cols_ecm] = df_ecm_total[cols_ecm].replace(',', '.', regex=True).astype(float)

        # Crear la nueva columna con el valor mínimo por fila
        df_total['ECM_MIN'] = df_total[cols_ecm].min(axis=1)
        df_total['ECM_MIN_COL'] = df_total[cols_ecm].idxmin(axis=1)
        
        def obtener_promedio_movil(row):
            if row['ECM_MIN_COL'] == 'ECM':
                return row['promedio_movil']
            elif row['ECM_MIN_COL'] == 'ECM_P4':
                return row['promedio_movil_p4']
            elif row['ECM_MIN_COL'] == 'ECM_P5':
                return row['promedio_movil_p5']
            elif row['ECM_MIN_COL'] == 'ECM_SES':
                return row['pronostico_ses']
            elif row['ECM_MIN_COL'] == 'ECM_SED':
                return row['pronostico_sed']  
            else:
                return None 
        # Aplicar la función fila por fila
        df_total['MEJOR_PRONOSTICO'] = df_total.apply(obtener_promedio_movil, axis=1)
        df_total['MEJOR_PRONOSTICO'] = np.ceil(df_total['MEJOR_PRONOSTICO'])
        
        # df_ecm_total.to_excel("ECM_total.xlsx", index=False)
        # Claves únicas para agrupar (puedes agregar más si es necesario)
        claves = ['sku', 'sku_nom', 'bod']

        # Crear un índice para llevar la cuenta del pronóstico
        index_pronostico = 0

        # Agrupar el DataFrame como está, sin reordenar
        for _, grupo in df_demanda.groupby(claves):
            # Tomar los últimos 4 registros (ya está ordenado)
            ultimos_4 = grupo.tail(4)
            # Verificar si el total es cero en todos los últimos 4
            if (ultimos_4['total'] == 0).all():
                # Asignar 0 a la posición correspondiente del pronóstico
                # pronostico_final[index_pronostico] = 0
                # obtener el sku, el sku_nom y bod quitando duplicados y luego comparar por sku, sku_nom y bod con el DataFrame df_ecm_total y poner un cero en la columna MEJOR_PRONOSTICO correspondiente
                sku = ultimos_4['sku'].iloc[0]
                sku_nom = ultimos_4['sku_nom'].iloc[0]
                bod = ultimos_4['bod'].iloc[0]
                df_total.loc[(df_total['sku'] == sku) & (df_total['sku_nom'] == sku_nom) & (df_total['bod'] == bod), 'MEJOR_PRONOSTICO'] = 0 
            # Aumentar el índice (1 pronóstico por grupo)
            index_pronostico += 1
        
        #---------calcular estadisticas de moda y promedio---------
        def calcular_moda_personalizada(valores):
            modas = multimode(valores)
            if len(modas) == len(set(valores)):
                # No hay moda (todos únicos), retornar el valor más grande
                return max(valores)
            else:
                # Retornar la moda menor (por defecto)
                return modas[0]
        def calcularEstadisticas(grupo, n):
            ultimos_n = grupo.tail(n)
            totales = ultimos_n['total'].tolist()

            moda_val = calcular_moda_personalizada(totales)
            promedio = round(ultimos_n['total'].mean()) if not ultimos_n.empty else None

            fila_resultado = grupo.iloc[[0]].copy()
            fila_resultado['MODA_TOTAL'] = moda_val
            fila_resultado['PROM_TOTAL'] = promedio

            return fila_resultado
        
        df_demanda_mod_pro_p3 = df_demanda.groupby(['sku', 'sku_nom', 'bod'], group_keys=False).apply(calcularEstadisticas, n=9).reset_index(drop=True).copy()
        df_demanda_mod_pro_p4 = df_demanda.groupby(['sku', 'sku_nom', 'bod'], group_keys=False).apply(calcularEstadisticas, n=8).reset_index(drop=True).copy()
        df_demanda_mod_pro_p5 = df_demanda.groupby(['sku', 'sku_nom', 'bod'], group_keys=False).apply(calcularEstadisticas, n=7).reset_index(drop=True).copy()
        
        "NOTA: LA MODA Y EL PROMEDIO EN P3 SON LOS MISMOS VALORES QUE EN SES Y SED. POR ESO NO SE CALCULAN"
        
        # df_demanda_final.to_excel("demanda_final.xlsx", index=False)
        # inventario = df_demanda_final['inv_saldo'].tolist()

        # list_pronostico_final = df_total['MEJOR_PRONOSTICO'].tolist()
        # # Cantidad a comprar para cada producto por 1 mes
    
        # cantidad = []
        # for i in range(len(inventario)):
        #     cantidad.append(list_pronostico_final[i] - inventario[i])
        
        # df_total['bod'] = df_total['bod'].replace(reemplazos_bod)
        
        # # Merge por las columnas clave: sku, sku_nom y bod
        # df_total = pd.merge(
        #     df_total,
        #     df_demanda_final[['sku', 'sku_nom', 'bod', 'inv_saldo']],
        #     on=['sku', 'sku_nom', 'bod'],
        #     how='left'  # o 'inner' si estás seguro que todos existen en ambos
        # )
        
        # Resta de la cantidad a comprar
        df_total['cantidad'] = df_total['MEJOR_PRONOSTICO'] - df_total['inventario']

        # cambiar el nombre de las columnas de moda y promedio a moda_p3 y promedio_p3
        df_demanda_mod_pro_p3.rename(columns={'MODA_TOTAL': 'moda_p3', 'PROM_TOTAL': 'promedio_p3'}, inplace=True)
        df_demanda_mod_pro_p4.rename(columns={'MODA_TOTAL': 'moda_p4', 'PROM_TOTAL': 'promedio_p4'}, inplace=True)
        df_demanda_mod_pro_p5.rename(columns={'MODA_TOTAL': 'moda_p5', 'PROM_TOTAL': 'promedio_p5'}, inplace=True)
        
        df_total = pd.merge(
            df_total,
            df_demanda_mod_pro_p3[['sku', 'sku_nom', 'bod', 'moda_p3', 'promedio_p3']],
            on=['sku', 'sku_nom', 'bod'],
            how='left'
        )
        df_total = pd.merge(
            df_total,
            df_demanda_mod_pro_p4[['sku', 'sku_nom', 'bod', 'moda_p4', 'promedio_p4']],
            on=['sku', 'sku_nom', 'bod'],
            how='left'
        )
        df_total = pd.merge(
            df_total,
            df_demanda_mod_pro_p5[['sku', 'sku_nom', 'bod', 'moda_p5', 'promedio_p5']],
            on=['sku', 'sku_nom', 'bod'],
            how='left'
        )
        
        df_total['cantidadx3'] = (df_total['MEJOR_PRONOSTICO'] * 3) - df_total['inventario']

        tiempo_entrega = LeadTime.objects.all()
        tiempo_entrega = tiempo_entrega.values('marca_nom', 'tiempo_entrega')
        df_tiempo_entrega = pd.DataFrame(list(tiempo_entrega))
        cols_merge = ['marca_nom']
        for col in cols_merge:
            # df_demanda_final[col] = df_demanda_final[col].astype(str).str.strip()
            df_tiempo_entrega[col] = df_tiempo_entrega[col].astype(str).str.strip()

        df_total = pd.merge(
            df_total,
            df_tiempo_entrega[['marca_nom', 'tiempo_entrega']],
            on=['marca_nom'],
            how='left'
        )
        # poner en cero los valores de tiempo_entrega que son nulos
        df_total['tiempo_entrega'] = df_total['tiempo_entrega'].fillna(0)
        
        # Rellenar con 0 si no hay coincidencia
        # df_demanda_final_leadtime['tiempo_entrega'] = df_demanda_final_leadtime['tiempo_entrega'].fillna(0)
        # # extraer tiempo de entrega
        # tiempo_entrega = df_demanda_final_leadtime['tiempo_entrega'].tolist()
        # df_total['tiempo_entrega'] = df_demanda_final_leadtime['tiempo_entrega'].values
        
        z = 1.959 #97.5% de confianza
        dias_inv = 60
        dias_inventario = []
        dias_inventario_final = []
        list_stock = []
        
        desviacion_estandar_p3 = (df_pronostico_p3.groupby(['sku', 'sku_nom', 'bod'])['error'].std().reset_index(name='desviacion_estandar'))
        desviacion_estandar_p4 = (df_pronostico_p4.groupby(['sku', 'sku_nom', 'bod'])['error'].std().reset_index(name='desviacion_estandar'))
        desviacion_estandar_p5 = (df_pronostico_p5.groupby(['sku', 'sku_nom', 'bod'])['error'].std().reset_index(name='desviacion_estandar'))
        desviacion_estandar_ses = (df_pronostico_ses.groupby(['sku', 'sku_nom', 'bod'])['error'].std().reset_index(name='desviacion_estandar'))
        desviacion_estandar_sed = (df_pronostico_sed.groupby(['sku', 'sku_nom', 'bod'])['error'].std().reset_index(name='desviacion_estandar'))

        # cambiar el nombre de las columnas de desviacion_estandar a desviacion_estandar_p3, desviacion_estandar_p4, desviacion_estandar_p5, desviacion_estandar_ses, desviacion_estandar_sed
        desviacion_estandar_p3.rename(columns={'desviacion_estandar': 'desviacion_estandar_p3'}, inplace=True)
        desviacion_estandar_p4.rename(columns={'desviacion_estandar': 'desviacion_estandar_p4'}, inplace=True)
        desviacion_estandar_p5.rename(columns={'desviacion_estandar': 'desviacion_estandar_p5'}, inplace=True)
        desviacion_estandar_ses.rename(columns={'desviacion_estandar': 'desviacion_estandar_ses'}, inplace=True)
        desviacion_estandar_sed.rename(columns={'desviacion_estandar': 'desviacion_estandar_sed'}, inplace=True)
        
        # Unir los DataFrames de desviación estándar al DataFrame df_total
        df_total = pd.merge(
            df_total,
            desviacion_estandar_p3[['sku', 'sku_nom', 'bod', 'desviacion_estandar_p3']],
            on=['sku', 'sku_nom', 'bod'],
            how='left'
        )
        df_total = pd.merge(
            df_total,
            desviacion_estandar_p4[['sku', 'sku_nom', 'bod', 'desviacion_estandar_p4']],
            on=['sku', 'sku_nom', 'bod'],
            how='left'
        )
        df_total = pd.merge(
            df_total,
            desviacion_estandar_p5[['sku', 'sku_nom', 'bod', 'desviacion_estandar_p5']],
            on=['sku', 'sku_nom', 'bod'],
            how='left'
        )
        df_total = pd.merge(
            df_total,
            desviacion_estandar_ses[['sku', 'sku_nom', 'bod', 'desviacion_estandar_ses']],
            on=['sku', 'sku_nom', 'bod'],
            how='left'
        )
        df_total = pd.merge(
            df_total,
            desviacion_estandar_sed[['sku', 'sku_nom', 'bod', 'desviacion_estandar_sed']],
            on=['sku', 'sku_nom', 'bod'],
            how='left'
        )
        # df_total.to_excel("Pronosticos.xlsx", index=False)
        # Calcular el stock de seguridad
        def calcularStockSeguridad(row):
            if row['ECM_MIN_COL'] == 'ECM':
                # obtener el valor de desviación estándar del DataFrame desviacion_estandar_p3
                desviacion_estandar = row['desviacion_estandar_p3']
                mejor_pronostico = int(row['MEJOR_PRONOSTICO'])
                inventario = int(row['inventario'])
                moda = row['moda_p3']
                promedio = row['promedio_p3']
                stock = z * desviacion_estandar * math.sqrt(row['tiempo_entrega'])
                if mejor_pronostico == 0 or moda == 0:
                    stock = 0
                    stock_seguridad = math.ceil(stock + mejor_pronostico - inventario)
                else:
                    stock_seguridad = math.ceil(stock + mejor_pronostico - inventario)
                if promedio != 0:
                    dias_inventario.append(round((stock / promedio) * 30))
                else:
                    dias_inventario.append(0)
                if dias_inventario[-1] > dias_inv:
                    stock_seguridad = math.ceil(promedio + mejor_pronostico - inventario)
                if promedio != 0:
                    dias_inventario_final.append(round((stock_seguridad / promedio) * 30))
                else:
                    dias_inventario_final.append(0)
                list_stock.append(stock)
            elif row['ECM_MIN_COL'] == 'ECM_P4':
                # obtener el valor de desviación estándar del DataFrame desviacion_estandar_p4
                desviacion_estandar = row['desviacion_estandar_p4']
                stock = z * desviacion_estandar * math.sqrt(row['tiempo_entrega'])
                mejor_pronostico = int(row['MEJOR_PRONOSTICO'])
                inventario = int(row['inventario'])
                moda = row['moda_p4']
                promedio = row['promedio_p4']
                if mejor_pronostico == 0 or moda == 0:
                    stock = 0
                    stock_seguridad=math.ceil(stock + mejor_pronostico - inventario)
                else:
                    stock_seguridad=math.ceil(stock + mejor_pronostico - inventario)
                if promedio != 0:
                    dias_inventario.append(round((stock / promedio) * 30))
                else:
                    dias_inventario.append(0)
                if dias_inventario[-1] > dias_inv:
                    stock_seguridad = math.ceil(promedio + mejor_pronostico - inventario)
                if promedio != 0:
                    dias_inventario_final.append(round((stock_seguridad / promedio) * 30))
                else:
                    dias_inventario_final.append(0)
                list_stock.append(stock)
            elif row['ECM_MIN_COL'] == 'ECM_P5':
                # obtener el valor de desviación estándar del DataFrame desviacion_estandar_p5
                desviacion_estandar = row['desviacion_estandar_p5']
                stock = z * desviacion_estandar * math.sqrt(row['tiempo_entrega'])
                mejor_pronostico = int(row['MEJOR_PRONOSTICO'])
                inventario = int(row['inventario'])
                moda = row['moda_p5']
                promedio = row['promedio_p5']
                if mejor_pronostico == 0 or moda == 0:
                    stock = 0
                    stock_seguridad=math.ceil(stock + mejor_pronostico - inventario)
                else:
                    stock_seguridad=math.ceil(stock + mejor_pronostico - inventario)
                if promedio != 0:
                    dias_inventario.append(round((stock / promedio) * 30))
                else:
                    dias_inventario.append(0)
                if dias_inventario[-1] > dias_inv:
                    stock_seguridad = math.ceil(promedio + mejor_pronostico - inventario)
                if promedio != 0:
                    dias_inventario_final.append(round((stock_seguridad / promedio) * 30))
                else:
                    dias_inventario_final.append(0)
                list_stock.append(stock)
            elif row['ECM_MIN_COL'] == 'ECM_SES':
                # obtener el valor de desviación estándar del DataFrame desviacion_estandar_ses
                desviacion_estandar = row['desviacion_estandar_ses']
                stock = z * desviacion_estandar * math.sqrt(row['tiempo_entrega'])
                mejor_pronostico = int(row['MEJOR_PRONOSTICO'])
                inventario = int(row['inventario'])
                moda = row['moda_p3']
                promedio = row['promedio_p3']
                if mejor_pronostico == 0 or moda == 0:
                    stock = 0
                    stock_seguridad=math.ceil(stock + mejor_pronostico - inventario)
                else:
                    stock_seguridad=math.ceil(stock + mejor_pronostico - inventario)
                if promedio != 0:
                    dias_inventario.append(round((stock / promedio) * 30))
                else:
                    dias_inventario.append(0)
                if dias_inventario[-1] > dias_inv:
                    stock_seguridad = math.ceil(promedio + mejor_pronostico - inventario)
                if promedio != 0:
                    dias_inventario_final.append(round((stock_seguridad / promedio) * 30))
                else:
                    dias_inventario_final.append(0)
                list_stock.append(stock)
            else:
                # obtener el valor de desviación estándar del DataFrame desviacion_estandar_sed
                desviacion_estandar = row['desviacion_estandar_sed']
                stock = z * desviacion_estandar * math.sqrt(row['tiempo_entrega'])
                mejor_pronostico = int(row['MEJOR_PRONOSTICO'])
                inventario = int(row['inventario'])
                moda = row['moda_p3']
                promedio = row['promedio_p3']
                if mejor_pronostico == 0 or moda == 0:
                    stock = 0
                    stock_seguridad=math.ceil(stock + mejor_pronostico - inventario)
                else:
                    stock_seguridad=math.ceil(stock + mejor_pronostico - inventario)
                if promedio != 0:
                    dias_inventario.append(round((stock / promedio) * 30))
                else:
                    dias_inventario.append(0)
                if dias_inventario[-1] > dias_inv:
                    stock_seguridad = math.ceil(promedio + mejor_pronostico - inventario)
                if promedio != 0:
                    dias_inventario_final.append(round((stock_seguridad / promedio) * 30))
                else:
                    dias_inventario_final.append(0)
                list_stock.append(stock)
            return stock_seguridad
        df_total['stock_seguridad'] = df_total.apply(calcularStockSeguridad, axis=1)
        # df_total.to_excel("Pronosticos.xlsx", index=False)
        
        # cantidad = df_total['cantidad'].tolist()
        # cantidadx3 = df_total['cantidadx3'].tolist()
        # resetear el index del DataFrame df_total
        
        df_total.reset_index(drop=True, inplace=True)
        
        bodega = df_total['bod'].tolist()
        item = df_total['sku'].tolist()
        codigo = df_total['sku'].tolist()
        producto = df_total['sku_nom'].tolist()
        unimed = df_total['umd'].tolist()
        proveedor = df_total['marca_nom'].tolist()
        sede = df_total['sede'].tolist()
        cantidad = df_total['cantidad'].tolist()
        stock_seguridad = df_total['stock_seguridad'].tolist()
        cantidadx3 = df_total['cantidadx3'].tolist()
        precio = df_total['precio'].tolist()
        
        # obtener el index del DataFrame df_demanda
        id = list(df_total.index + 1)
        fecha_actual = date.today()
        fecha_formateada = fecha_actual.strftime("%Y/%m/%d")
        
        df_pronosticos = pd.DataFrame(
            {   
                "id": id, #0
                "bodega": bodega, #1
                "item": item, #2
                "codigo": codigo, #3
                "producto": producto, #4
                "unimed": unimed, #5
                "lotepro": ".", #6
                "proveedor": proveedor, #7
                "sede": sede, #8
                "cantidad": cantidad, #9
                "stock": stock_seguridad, #10
                "cantidadx3": cantidadx3, #11
                "precio": precio, #12
                "fecha": fecha_formateada, #13
            }
        )
        # df_pronostico_p3.to_excel("pronostico_p3.xlsx", index=False)
        # df_pronostico_p4.to_excel("pronostico_p4.xlsx", index=False)
        # df_pronostico_p5.to_excel("pronostico_p5.xlsx", index=False)
        # df_pronostico_ses.to_excel("pronostico_ses.xlsx", index=False)
        # df_pronostico_sed.to_excel("pronostico_sed.xlsx", index=False)
        # df_total.to_excel("total.xlsx", index=False)
        return (
            df_demanda,
            df_total,
            df_pronosticos,
            df_pronostico_p3,
            df_pronostico_p4,
            df_pronostico_p5,
            df_pronostico_ses,
            df_pronostico_sed
        )
