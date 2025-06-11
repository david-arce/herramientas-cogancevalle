import time
import pandas as pd
import numpy as np
from pronosticosWebApp.pronosticos.promedioMovil import PronosticoMovil as pm

class PronosticoExpSimple:
    
    def __init__(self):
        pass
    
    def pronosticoExpSimple(alpha):
        print('Calculando suavización exponencial simple...')
        
        df_demanda = pd.DataFrame(pm.getDataBD())  # Cargar datos
        df_demanda = df_demanda.sort_values(by=['yyyy', 'mm'])  # Asegurar orden temporal
        
        def calcular_pronostico(df):
            df = df.sort_values(by=['mm'])

            ultimo_anio = df.iloc[-1]['yyyy']
            ultimo_mes = df.iloc[-1]['mm']

            nueva_fila = {
                'yyyy': ultimo_anio,
                'mm': 13,
                'sku': df.iloc[-1]['sku'],
                'sku_nom': df.iloc[-1]['sku_nom'],
                'sede': df.iloc[-1]['sede'],
                'total': np.nan,
            }

            df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)

            # Inicializar pronóstico con el primer valor real
            pronosticos = [df.loc[0, 'total']]
            for i in range(1, len(df)):
                if pd.isna(df.loc[i - 1, 'total']):
                    pronosticos.append(pronosticos[-1])
                else:
                    nuevo_f = pronosticos[-1] + alpha * (df.loc[i - 1, 'total'] - pronosticos[-1])
                    pronosticos.append(nuevo_f)

            df['pronostico_ses'] = pronosticos

            # Calcular errores
            df['error'] = abs(df['total'] - df['pronostico_ses'])

            df['errorMAPE'] = np.where(
                np.isnan(df['error']),
                np.nan,
                np.where(df['total'] == 0, 1, df['error'] / df['total'])
            )

            df['errorMAPEPrima'] = np.where(
                np.isnan(df['error']),
                np.nan,
                np.where(df['pronostico_ses'] == 0, 1, df['error'] / df['pronostico_ses'])
            )

            df['errorECM'] = df['error'] ** 2

            # Asignar métricas solo a la fila de mes 13
            df.loc[df['mm'] == 13, 'MAD'] = df['error'].iloc[1:].mean()
            df.loc[df['mm'] == 13, 'MAPE'] = df['errorMAPE'].iloc[1:].mean() * 100
            df.loc[df['mm'] == 13, 'MAPE_Prima'] = df['errorMAPEPrima'].iloc[1:].mean() * 100
            df.loc[df['mm'] == 13, 'ECM'] = df['errorECM'].iloc[1:].mean()


            return df

        # Aplicar SES por grupo
        df_resultado = df_demanda.groupby(['sku', 'sku_nom', 'sede'], group_keys=False).apply(calcular_pronostico)
        df_resultado = df_resultado.reset_index(drop=True)
        # Extraer métricas finales
        MAD = df_resultado['MAD'].dropna().tolist()
        MAPE = df_resultado['MAPE'].dropna().tolist()
        MAPE_prima = df_resultado['MAPE_Prima'].dropna().tolist()
        ECM = df_resultado['ECM'].dropna().tolist()
        # df_resultado.to_excel('suavizacion_exp_simple.xlsx', index=False)  # Guardar resultados en Excel
        
        return MAD, MAPE, MAPE_prima, ECM, df_resultado #df_pronostico_ses, lista_pronosticos

    def prueba():
        start_time = time.perf_counter()
        MAD, MAPE, MAPE_prima, ECM, df_pronostico_ses, lista_pronosticos, lista_pronosticos_redondeo = PronosticoExpSimple.pronosticoExpSimple(0.5)

        # serie = pd.concat([pd.Series(productos), pd.Series(MAD), pd.Series(MAPE)], axis=1)
        # serie.columns = ["Productos", "MAD", "Mejor pronostico"]
        # df = pd.DataFrame({"Items": items, "Proveedor": proveedor, "Productos": productos, "Sede": sede, "MAD": MAD, "MAPE": MAPE, "MAPE_Prima": MAPE_prima, "ECM": ECM, "Pronostico": lista_pronosticos, "Pronostico_redondeo": lista_pronosticos_redondeo})
    
        # # Especifica la ruta del archivo Excel donde deseas guardar el DataFrame
        # ruta_archivo_excel = 'suavizacion_exp_simple.xlsx'

        # # Usa el método to_excel() para guardar el DataFrame en el archivo Excel
        # df.to_excel(ruta_archivo_excel, index=False)  # Si no deseas incluir el índice en el archivo Excel, puedes establecer index=False
        end_time = time.perf_counter()
        print(f"Tiempo de ejecución: {end_time - start_time} segundos")

# PronosticoExpSimple.prueba()


