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
        df_demanda = df_demanda.sort_values(by=['yyyy', 'mm'])  # Asegurar orden temporal
        def calcular_pronostico(df):
            
            df = df.sort_values(by=['mm'])  # Orden temporal
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
                'sede': ultima_fila['sede'],
                'total': np.nan,
            }
            df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)

            pronostico_shifted = [np.nan] + pronostico[0:-1]  # Desplaza hacia abajo
            pronostico_shifted.append(atenuado[-1] + p * tendencia[-1])  # mes 13
            df['pronostico'] = pronostico_shifted

            # Calcular errores
            df['abs_error'] = abs(df['total'] - df['pronostico'])

            df['errorMAPE'] = np.where(
                df['total'] == 0,
                1,
                df['abs_error'] / df['total']
            )

            df['errorMAPEPrima'] = np.where(
                df['pronostico'] == 0,
                1,
                df['abs_error'] / df['pronostico']
            )

            df['errorECM'] = df['abs_error'] ** 2

            # Excluir el primer mes del cálculo de métricas (asumiendo orden por año/mes ya hecho)
            errores_validos = df.iloc[1:-1]  # Excluye primer mes y fila del mes 13

            # Calcular métricas para el mes 13
            df['MAD'] = np.nan
            df['MAPE'] = np.nan
            df['MAPE_Prima'] = np.nan
            df['ECM'] = np.nan

            df.loc[df['mm'] == 13, 'MAD'] = errores_validos['abs_error'].mean()
            df.loc[df['mm'] == 13, 'MAPE'] = errores_validos['errorMAPE'].mean() * 100
            df.loc[df['mm'] == 13, 'MAPE_Prima'] = errores_validos['errorMAPEPrima'].mean() * 100
            df.loc[df['mm'] == 13, 'ECM'] = errores_validos['errorECM'].mean()

            return df

        # Aplicar a cada grupo
        df_resultado = df_demanda.groupby(['sku', 'sede'], group_keys=False).apply(calcular_pronostico)
        df_resultado = df_resultado.reset_index(drop=True)

        # df_resultado.to_excel('suavizacion_exp_doble.xlsx', index=False)  # Guardar resultados en Excel
        # Extraer métricas finales (solo fila mes 13)
        MAD = df_resultado['MAD'].dropna().tolist()
        MAPE = df_resultado['MAPE'].dropna().tolist()
        MAPE_prima = df_resultado['MAPE_Prima'].dropna().tolist()
        ECM = df_resultado['ECM'].dropna().tolist()
        
        '''
        df_demanda = pd.DataFrame(pm.getDataBD()) # Se convierten los productos en un DataFrame de pandas para su manipulación
        meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    
        # Filtrar columnas que contienen meses (sin importar mayúsculas o minúsculas)
        columnas_meses = [col for col in df_demanda.columns if any(mes in col.lower() for mes in meses)]
        cantidadMeses = len(columnas_meses)
        
        # Seleccionar solo las columnas de meses
        demanda = df_demanda[columnas_meses].copy()
        
        valores_demanda = demanda.values.flatten().tolist()
        
        #CALCULO DEL VALOR ATENUADO
        #alpha*Dt+(1-alpha)*(At-1+Tt-1) valor atenuado
        #beta*(At-At-1)+(1-beta)*Tt-1 valor de la tendencia
        valores_tendencia = []
        valores_atenuado = []
        for i in range(0, len(valores_demanda), cantidadMeses):
            grupo = valores_demanda[i:i+(cantidadMeses)]
            valores_tendencia.append(0)
            for item in range(len(grupo)):
                if item == 0:
                    valores_atenuado.append(grupo[item])
                else:
                    valores_atenuado.append(alpha*grupo[item] + (1-alpha)*(valores_atenuado[-1] + valores_tendencia[-1]))
                    valores_tendencia.append(beta*(valores_atenuado[-1] - valores_atenuado[-2]) + (1-beta)*valores_tendencia[-1])
    
        # print('valores atenuado: ',valores_atenuado[:30])
        # print('valores tendencia: ', valores_tendencia[:30])
    
        #CALCULO DEL PRONOSTICO EXPONENTIAL DOBLE
        #Ft = At + p*Tt
        pronostico_sed = [valores_atenuado[i] + p * valores_tendencia[i] for i in range(len(valores_atenuado))]
        # print('pronostico_sed: ',pronostico_sed[:20])
        
        # Extraer valores del mes siguiente para agregar al DataFrame demanda
        valores_mes_siguiente = pronostico_sed[cantidadMeses-1::cantidadMeses]
        # print(valores_mes_siguiente[:20])

        # Asignar los valores del pronostico al siguiente mes y se agrega al dataframe demanda
        demanda['pronostico'] = valores_mes_siguiente
        
        lista_nombre_columnas = demanda.columns.to_list()[1:]  #lista de los nombres de las columnas, es decir, los meses
        # Dividir la lista de valores en segmentos 
        segmentos_valores = [pronostico_sed[i:i+(cantidadMeses)] for i in range(0, len(pronostico_sed), cantidadMeses)]
        # Crear un DataFrame con los segmentos de valores y los nombres de las columnas 
        df_pronostico_sed = pd.DataFrame(segmentos_valores, columns=lista_nombre_columnas)
        # print(df_pronostico_sed)
        
        #lista de pronosticos para el siguiente mes
        lista_pronosticos = demanda.iloc[:, cantidadMeses].values.tolist()
        
        errores, erroresMape, erroresMapePrima, erroresCuadraticoMedio = [], [], [], []
        MAD=[] #mean absolute deviation
        MAPE=[] #mean absolute percentage error
        MAPE_prima=[] #mean absolute percentage error prima
        EMC=[] #error cuadratico medio

        pronostico_doble_listOflist = [pronostico_sed[i:i+cantidadMeses] for i in range(0, len(pronostico_sed), cantidadMeses)]
        #guarda los errores en una lista 
        for i in demanda.index:
            for j in range(1, cantidadMeses):
                errores.append(demanda.iloc[i, j] - pronostico_doble_listOflist[i][j-1])
        erroresAbs = np.abs(errores) #errores absolutos |e|

        total_meses_pronostico = cantidadMeses - 1 #total de meses a pronosticar menos el siguiente
        #CALCULO DEL MAD(MEAN ABSOLUTE DEVIATION) 
        MAD = [np.mean(erroresAbs[i:i+total_meses_pronostico]) for i in range(0, len(erroresAbs), total_meses_pronostico)]
        # print("MAD: ", MAD[:5])
        
        #CALCULO DEL MAPE(MEAN ABSOLUTE PERCENTAGE ERROR)
        valores_demanda_mape = (demanda.iloc[:,1:cantidadMeses].values)
        valores_demanda_mape = valores_demanda_mape.flatten().tolist()
        #guardar erroresMape |e|/xt(demanda) en una lista para poder operar con ellos
        errores_mape = [ea / vd if vd != 0 else 1 for ea, vd in zip(erroresAbs, valores_demanda_mape)]
        MAPE = [np.mean(errores_mape[i:i+total_meses_pronostico]) * 100 for i in range(0, len(errores_mape), total_meses_pronostico)]
        # print('MAPE: ',MAPE[:5])
        
        #CALCULO DEL MAPE' (MAPE PRIMA)
        # Crear una nueva lista sin los elementos en los indices a eliminar
        pronostico_ses_filtrado = [pronostico_sed[i] for i in range(len(pronostico_sed)) if (i + 1) % cantidadMeses != 0]
        
        #guardar erroresMapePrima |e|/Mt(promedio_movil)
        errores_mape_prima = [ea / psf if psf != 0 else 1 for ea, psf in zip(erroresAbs, pronostico_ses_filtrado)]
        MAPE_prima = [np.mean(errores_mape_prima[i:i+total_meses_pronostico]) * 100 for i in range(0, len(errores_mape_prima), total_meses_pronostico)]
        # print('MAPE_PRIMA: ', MAPE_prima[:5])
        
        #EMC(CALCULO DEL ERROR CUADRATICO MEDIO) |e|^2
        EMC = [np.mean(np.square(erroresAbs[i:i+total_meses_pronostico])) for i in range(0, len(erroresAbs), total_meses_pronostico)]
        # print('EMC: ', EMC[:5])
        del df_demanda
        '''
        return MAD, MAPE, MAPE_prima, ECM,# df_pronostico_sed, lista_pronosticos
    
    
    def prueba():
        start_time = time.perf_counter()
        MAD, MAPE, MAPE_prima, ECM, df_pronostico_sed, lista_pronosticos, lista_pronosticos_redondeo = PronosticoExpDoble.pronosticoExpDoble(0.5, 0.5, 1)
        
        # print("MAD: ", MAD[:5])
        # print("MAPE: ", MAPE[:5])
        # print("MAPE_PRIMA: ", MAPE_prima[:5])
        # print("ECM: ", ECM[:5])
        # print("Pronostico: ", lista_pronosticos[:5])
        # print("Pronostico redondeo: ", lista_pronosticos_redondeo[:5])
        
        # serie = pd.concat([pd.Series(productos), pd.Series(MAD), pd.Series(MAPE)], axis=1)
        # serie.columns = ["Productos", "MAD", "Mejor pronostico"]
        # df = pd.DataFrame({"Items": items, "Proveedor": proveedor, "Productos": productos, "Sede": sede,"MAD": MAD, "MAPE": MAPE, "MAPE_Prima": MAPE_prima, "ECM": ECM, "Pronostico": lista_pronosticos, "Pronostico_redondeo": lista_pronosticos_redondeo})
    
        # # Especifica la ruta del archivo Excel donde deseas guardar el DataFrame
        # ruta_archivo_excel = 'suavizacion_exp_doble.xlsx'

        # # Usa el método to_excel() para guardar el DataFrame en el archivo Excel
        # df.to_excel(ruta_archivo_excel, index=False)  # Si no deseas incluir el índice en el archivo Excel, puedes establecer index=False
        end_time = time.perf_counter()
        print(f"Tiempo de ejecución: {end_time - start_time} segundos")

# PronosticoExpDoble.prueba()        

