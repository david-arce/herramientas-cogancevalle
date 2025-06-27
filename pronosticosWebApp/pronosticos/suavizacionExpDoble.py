import pandas as pd
import numpy as np
import time
from pronosticosWebApp.pronosticos.promedioMovil import PronosticoMovil as pm

class PronosticoExpDoble:
    
    def __init__(self):
        pass
    
    def pronosticoExpDoble(alpha, beta, p):
        print('Calculando suavización exponencial doble...')
        
        df_demanda = pd.DataFrame(pm.getDataBD())  # Asumimos que tiene columnas: sku, sede, yyyy, mm, total
        # df_demanda = df_demanda.sort_values(by=['yyyy', 'mm'])  # Asegurar orden temporal
        def calcular_pronostico(df):
            
            # df = df.sort_values(by=['mm'])  # Orden temporal
            valores = df['total'].values
            n = len(valores)
            
            atenuado = [valores[0]]
            tendencia = [0]
            pronostico = [valores[0]]  # primer pronóstico igual al primer valor
            
            # Cálculo de suavización doble
            for t in range(1, n):
                at = alpha * valores[t] + (1 - alpha) * (atenuado[-1] + tendencia[-1])
                tt = beta * (at - atenuado[-1]) + (1 - beta) * tendencia[-1]
                atenuado.append(at)
                tendencia.append(tt)
                pronostico.append(at + p * tt)
            
            # Agregar fila de pronóstico para el siguiente mes (mes 13)
            ultimo_anio = df.iloc[-1]['yyyy']
            ultima_fila = df.iloc[-1]
            nueva_fila = {
                'yyyy': ultimo_anio,
                'mm': 13,
                'sku': ultima_fila['sku'],
                'sku_nom': ultima_fila['sku_nom'],
                'marca_nom': df.iloc[-1]['marca_nom'],
                'bod': df.iloc[-1]['bod'],
                'sede': ultima_fila['sede'],
                'total': np.nan,
            }
            df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)

            pronostico_shifted = [np.nan] + pronostico[0:-1]  # Desplaza hacia abajo
            pronostico_shifted.append(atenuado[-1] + p * tendencia[-1])  # mes 13
            df['pronostico_sed'] = pronostico_shifted

            # Calcular errores
            df['error'] = abs(df['total'] - df['pronostico_sed'])

            df['errorMAPE'] = np.where(
                df['total'] == 0,
                1,
                df['error'] / df['total']
            )

            df['errorMAPEPrima'] = np.where(
                df['pronostico_sed'] == 0,
                1,
                df['error'] / df['pronostico_sed']
            )

            df['errorECM'] = df['error'] ** 2

            # Excluir el primer mes del cálculo de métricas (asumiendo orden por año/mes ya hecho)
            errores_validos = df.iloc[1:-1]  # Excluye primer mes y fila del mes 13

            # Calcular métricas para el mes 13
            df['MAD'] = np.nan
            df['MAPE'] = np.nan
            df['MAPE_Prima'] = np.nan
            df['ECM'] = np.nan

            df.loc[df['mm'] == 13, 'MAD'] = errores_validos['error'].mean()
            df.loc[df['mm'] == 13, 'MAPE'] = errores_validos['errorMAPE'].mean() * 100
            df.loc[df['mm'] == 13, 'MAPE_Prima'] = errores_validos['errorMAPEPrima'].mean() * 100
            df.loc[df['mm'] == 13, 'ECM'] = errores_validos['errorECM'].mean()

            return df

        # Aplicar a cada grupo
        df_resultado = df_demanda.groupby(['sku', 'sku_nom', 'sede'], group_keys=False).apply(calcular_pronostico)
        df_resultado = df_resultado.reset_index(drop=True)

        return df_resultado # df_pronostico_sed, lista_pronosticos
    