import pandas as pd
import numpy as np
import time
from pronosticosWebApp.models import Producto

class PronosticoMovil:
    
    def __init__(self):
        pass
    
    def getDataBD():
        return list(Producto.objects.order_by('id').values()) # Se obtienen los productos de la base de datos en forma de lista
        
    def promedioMovil_3(n):
        print('Calculando pronóstico de promedio móvil...')
        df_demanda = pd.DataFrame(PronosticoMovil.getDataBD()) # Se convierten los productos en un DataFrame de pandas para su manipulación
        
        # Se filtran los productos de la sede de Tuluá y mes 1
        venta_tulua_mes1 = df_demanda[(df_demanda['mm'] == 1) & (df_demanda['bod'].isin(['0101','0102','0105','0180']))].groupby(['sku', 'sku_nom', 'marca_nom']).agg({'cantidad': 'sum'}).reset_index()
        # cambiar el nombre de la columna cantidad a 
        venta_tulua_mes2 = df_demanda[(df_demanda['mm'] == 2) & (df_demanda['bod'].isin(['0101','0102','0105','0180']))].groupby(['sku', 'sku_nom', 'marca_nom']).agg({'cantidad': 'sum'}).reset_index()
        venta_tulua_mes3 = df_demanda[(df_demanda['mm'] == 3) & (df_demanda['bod'].isin(['0101','0102','0105','0180']))].groupby(['sku', 'sku_nom', 'marca_nom']).agg({'cantidad': 'sum'}).reset_index()
        venta_tulua_mes4 = df_demanda[(df_demanda['mm'] == 4) & (df_demanda['bod'].isin(['0101','0102','0105','0180']))].groupby(['sku', 'sku_nom', 'marca_nom']).agg({'cantidad': 'sum'}).reset_index()
        venta_tulua_mes5 = df_demanda[(df_demanda['mm'] == 5) & (df_demanda['bod'].isin(['0101','0102','0105','0180']))].groupby(['sku', 'sku_nom', 'marca_nom']).agg({'cantidad': 'sum'}).reset_index()
        venta_tulua_mes6 = df_demanda[(df_demanda['mm'] == 6) & (df_demanda['bod'].isin(['0101','0102','0105','0180']))].groupby(['sku', 'sku_nom', 'marca_nom']).agg({'cantidad': 'sum'}).reset_index()
        venta_tulua_mes7 = df_demanda[(df_demanda['mm'] == 7) & (df_demanda['bod'].isin(['0101','0102','0105','0180']))].groupby(['sku', 'sku_nom', 'marca_nom']).agg({'cantidad': 'sum'}).reset_index()
        venta_tulua_mes8 = df_demanda[(df_demanda['mm'] == 8) & (df_demanda['bod'].isin(['0101','0102','0105','0180']))].groupby(['sku', 'sku_nom', 'marca_nom']).agg({'cantidad': 'sum'}).reset_index()
        venta_tulua_mes9 = df_demanda[(df_demanda['mm'] == 9) & (df_demanda['bod'].isin(['0101','0102','0105','0180']))].groupby(['sku', 'sku_nom', 'marca_nom']).agg({'cantidad': 'sum'}).reset_index()
        venta_tulua_mes10 = df_demanda[(df_demanda['mm'] == 10) & (df_demanda['bod'].isin(['0101','0102','0105','0180']))].groupby(['sku', 'sku_nom', 'marca_nom']).agg({'cantidad': 'sum'}).reset_index()
        venta_tulua_mes11 = df_demanda[(df_demanda['mm'] == 11) & (df_demanda['bod'].isin(['0101','0102','0105','0180']))].groupby(['sku', 'sku_nom', 'marca_nom']).agg({'cantidad': 'sum'}).reset_index()
        
        venta_buga = df_demanda[df_demanda['tipo'] == 'B2'].groupby('sku_nom')['cantidad'].sum().reset_index()
        venta_cartago = df_demanda[df_demanda['tipo'] == 'C3'].groupby('sku_nom')['cantidad'].sum().reset_index()
        venta_cali = df_demanda[df_demanda['tipo'] == 'A4'].groupby('sku_nom')['cantidad'].sum().reset_index()
        
        # Se unen todos lo dataframes de ventas de Tuluá en un solo dataframe conservando sus columnas
        
        demanda_total = pd.concat([venta_tulua_mes1, venta_tulua_mes2, venta_tulua_mes3, venta_tulua_mes4,
                                   venta_tulua_mes5, venta_tulua_mes6, venta_tulua_mes7, venta_tulua_mes8,
                                   venta_tulua_mes9, venta_tulua_mes10, venta_tulua_mes11], ignore_index=True)
        
        # print(demanda_total)
        demanda_total.to_excel('demanda.xlsx', index=False)
        # coincidencias_tulua_mes1.to_excel('coincidencias_tulua.xlsx', index=False)
        # print(coincidencias_tulua_mes1)

        
        meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        
        # Filtrar columnas que contienen meses (sin importar mayúsculas o minúsculas)
        columnas_meses = [col for col in df_demanda.columns if any(mes in col.lower() for mes in meses)]
        cantidadMeses = len(columnas_meses)
        
        # Seleccionar solo las columnas de meses
        demanda = df_demanda[columnas_meses].copy()
        
        demanda['pronostico'] = 0 # Se agrega una columna para el siguiente mes
        promedio_movil = demanda.T.rolling(window=n).mean().shift(1).T # Se calcula el promedio móvil de las ventas 
        print('\n')
        
        # calculo del stock de seguridad
        # error_pronostico = np.abs((promedio_movil.iloc[:, n:cantidadMeses].values - demanda.iloc[:, n:cantidadMeses].values)).tolist()
    
        # desviación estandar de una muestra
        # desviacion_estandar = [np.std(error_pronostico, ddof=1) for error_pronostico in error_pronostico]
        # print(desviacion_estandar)
        
        errores, erroresMape, erroresMapePrima, erroresCuadraticoMedio = [], [], [], []
        MAD=[] #mean absolute deviation
        MAPE=[] #mean absolute percentage error
        MAPE_prima=[] #mean absolute percentage error prima
        ECM=[] #error cuadratico medio
        
        # Optimización del cálculo de errores utilizando operaciones vectorizadas
        errores = (demanda.iloc[:, n:cantidadMeses].values - promedio_movil.iloc[:, n:cantidadMeses].values).flatten()
        # errores = (demanda.iloc[:, n:cantidadMeses].values - promedio_movil.values).flatten()
        # print(errores[:10])
        erroresAbs = np.abs(errores)
        # print(erroresAbs[:10])
        
        #lista de pronosticos para el siguiente mes
        lista_pronosticos = [promedio_movil.iloc[i, cantidadMeses] for i in promedio_movil.index]
        
        total_meses_pronostico = (demanda.shape[1] - 1) - n #total de meses a pronosticar menos el siguiente
    
        #CALCULO DEL MAD(MEAN ABSOLUTE DEVIATION) 
        for i in range(0, len(erroresAbs), total_meses_pronostico):
            grupo = erroresAbs[i:i+(total_meses_pronostico)]
            MAD.append(sum(grupo)/len(grupo))
        # print(MAD[:5])
            
        # CALCULO DEL MAPE (MEAN ABSOLUTE PERCENTAGE ERROR)
        valores_demanda = demanda.iloc[:, n:cantidadMeses].values.flatten()
        erroresMape = [(ea / vd if vd != 0 else 1) for ea, vd in zip(erroresAbs, valores_demanda)]
        MAPE = [np.mean(erroresMape[i:i+total_meses_pronostico]) * 100 for i in range(0, len(erroresMape), total_meses_pronostico)]
        # print(MAPE[:5])    
        
        # CALCULO DEL MAPE' (MEAN ABSOLUTE PERCENTAGE ERROR PRIMA)
        valores_pronosticoMovil = promedio_movil.iloc[:, n:cantidadMeses].values.flatten()
        erroresMapePrima = [(ea / vp if vp != 0 else 1) for ea, vp in zip(erroresAbs, valores_pronosticoMovil)]
        MAPE_prima = [np.mean(erroresMapePrima[i:i+total_meses_pronostico]) * 100 for i in range(0, len(erroresMapePrima), total_meses_pronostico)]
        # print(MAPE_prima[:5])
        
        # CALCULO DEL ECM (ERROR CUADRATICO MEDIO)
        erroresCuadraticoMedio = erroresAbs ** 2
        ECM = [np.mean(erroresCuadraticoMedio[i:i+total_meses_pronostico]) for i in range(0, len(erroresCuadraticoMedio), total_meses_pronostico)]
        # print(ECM[:5])
        
        return MAD, MAPE, MAPE_prima, ECM, demanda, promedio_movil, lista_pronosticos
    
    def promedioMovil_4(n):
        df_demanda = pd.DataFrame(PronosticoMovil.getDataBD()) # Se convierten los productos en un DataFrame de pandas para su manipulación
        meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    
        # Filtrar columnas que contienen meses (sin importar mayúsculas o minúsculas)
        columnas_meses = [col for col in df_demanda.columns if any(mes in col.lower() for mes in meses)]
        cantidadMeses = len(columnas_meses)
        
        # Seleccionar solo las columnas de meses
        demanda = df_demanda[columnas_meses].copy()

        demanda['pronostico'] = 0 # Se agrega una columna para el siguiente mes
        promedio_movil = demanda.T.rolling(window=n).mean().shift(1).T # Se calcula el promedio móvil de las ventas 
        print('\n')
    
        errores, erroresMape, erroresMapePrima, erroresCuadraticoMedio = [], [], [], []
        MAD=[] #mean absolute deviation
        MAPE=[] #mean absolute percentage error
        MAPE_prima=[] #mean absolute percentage error prima
        ECM=[] #error cuadratico medio
        
        # Optimización del cálculo de errores utilizando operaciones vectorizadas
        errores = (demanda.iloc[:, n:cantidadMeses].values - promedio_movil.iloc[:, n:cantidadMeses].values).flatten()
        # print(errores[:10])
        erroresAbs = np.abs(errores)
        # print(erroresAbs[:10])
        
        #lista de pronosticos para el siguiente mes
        lista_pronosticos = [promedio_movil.iloc[i, cantidadMeses] for i in promedio_movil.index]
        
        total_meses_pronostico = (demanda.shape[1] - 1) - n #total de meses a pronosticar menos el siguiente
        
        #CALCULO DEL MAD(MEAN ABSOLUTE DEVIATION) 
        for i in range(0, len(erroresAbs), total_meses_pronostico):
            grupo = erroresAbs[i:i+(total_meses_pronostico)]
            MAD.append(sum(grupo)/len(grupo))
        # print(MAD[:5])
            
        # CALCULO DEL MAPE (MEAN ABSOLUTE PERCENTAGE ERROR)
        valores_demanda = demanda.iloc[:, n:cantidadMeses].values.flatten()
        erroresMape = [(ea / vd if vd != 0 else 1) for ea, vd in zip(erroresAbs, valores_demanda)]
        MAPE = [np.mean(erroresMape[i:i+total_meses_pronostico]) * 100 for i in range(0, len(erroresMape), total_meses_pronostico)]
        # print(MAPE[:5])    
        
        # CALCULO DEL MAPE' (MEAN ABSOLUTE PERCENTAGE ERROR PRIMA)
        valores_pronosticoMovil = promedio_movil.iloc[:, n:cantidadMeses].values.flatten()
        erroresMapePrima = [(ea / vp if vp != 0 else 1) for ea, vp in zip(erroresAbs, valores_pronosticoMovil)]
        MAPE_prima = [np.mean(erroresMapePrima[i:i+total_meses_pronostico]) * 100 for i in range(0, len(erroresMapePrima), total_meses_pronostico)]
        # print(MAPE_prima[:5])
        
        # CALCULO DEL ECM (ERROR CUADRATICO MEDIO)
        erroresCuadraticoMedio = erroresAbs ** 2
        ECM = [np.mean(erroresCuadraticoMedio[i:i+total_meses_pronostico]) for i in range(0, len(erroresCuadraticoMedio), total_meses_pronostico)]
        # print(ECM[:5])
        
        return MAD, MAPE, MAPE_prima, ECM, promedio_movil, lista_pronosticos
    
    def promedioMovil_5(n):
        df_demanda = pd.DataFrame(PronosticoMovil.getDataBD()) # Se convierten los productos en un DataFrame de pandas para su manipulación
        meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    
        # Filtrar columnas que contienen meses (sin importar mayúsculas o minúsculas)
        columnas_meses = [col for col in df_demanda.columns if any(mes in col.lower() for mes in meses)]
        cantidadMeses = len(columnas_meses)
        
        # Seleccionar solo las columnas de meses
        demanda = df_demanda[columnas_meses].copy()

        demanda['pronostico'] = 0 # Se agrega una columna para el siguiente mes
        promedio_movil = demanda.T.rolling(window=n).mean().shift(1).T # Se calcula el promedio móvil de las ventas 
        print('\n')
    
        errores, erroresMape, erroresMapePrima, erroresCuadraticoMedio = [], [], [], []
        MAD=[] #mean absolute deviation
        MAPE=[] #mean absolute percentage error
        MAPE_prima=[] #mean absolute percentage error prima
        ECM=[] #error cuadratico medio
        
        # Optimización del cálculo de errores utilizando operaciones vectorizadas
        errores = (demanda.iloc[:, n:cantidadMeses].values - promedio_movil.iloc[:, n:cantidadMeses].values).flatten()
        # print(errores[:10])
        erroresAbs = np.abs(errores)
        # print(erroresAbs[:10])
        
        #lista de pronosticos para el siguiente mes
        lista_pronosticos = [promedio_movil.iloc[i, cantidadMeses] for i in promedio_movil.index]
        
        total_meses_pronostico = (demanda.shape[1] - 1) - n #total de meses a pronosticar menos el siguiente
        
        #CALCULO DEL MAD(MEAN ABSOLUTE DEVIATION) 
        for i in range(0, len(erroresAbs), total_meses_pronostico):
            grupo = erroresAbs[i:i+(total_meses_pronostico)]
            MAD.append(sum(grupo)/len(grupo))
        # print(MAD[:5])
            
        # CALCULO DEL MAPE (MEAN ABSOLUTE PERCENTAGE ERROR)
        valores_demanda = demanda.iloc[:, n:cantidadMeses].values.flatten()
        erroresMape = [(ea / vd if vd != 0 else 1) for ea, vd in zip(erroresAbs, valores_demanda)]
        MAPE = [np.mean(erroresMape[i:i+total_meses_pronostico]) * 100 for i in range(0, len(erroresMape), total_meses_pronostico)]
        # print(MAPE[:5])    
        
        # CALCULO DEL MAPE' (MEAN ABSOLUTE PERCENTAGE ERROR PRIMA)
        valores_pronosticoMovil = promedio_movil.iloc[:, n:cantidadMeses].values.flatten()
        erroresMapePrima = [(ea / vp if vp != 0 else 1) for ea, vp in zip(erroresAbs, valores_pronosticoMovil)]
        MAPE_prima = [np.mean(erroresMapePrima[i:i+total_meses_pronostico]) * 100 for i in range(0, len(erroresMapePrima), total_meses_pronostico)]
        # print(MAPE_prima[:5])
        
        # CALCULO DEL ECM (ERROR CUADRATICO MEDIO)
        erroresCuadraticoMedio = erroresAbs ** 2
        ECM = [np.mean(erroresCuadraticoMedio[i:i+total_meses_pronostico]) for i in range(0, len(erroresCuadraticoMedio), total_meses_pronostico)]
        # print(ECM[:5])
        
        return MAD, MAPE, MAPE_prima, ECM, promedio_movil, lista_pronosticos
    
    def productos():
        df_demanda = pd.DataFrame(PronosticoMovil.getDataBD()) # Se convierten los productos en un DataFrame de pandas para su manipulación
        id = df_demanda['id'].tolist()
        items = df_demanda['producto_c15'].tolist()
        proveedor = df_demanda['proveedor'].tolist()
        productos = df_demanda['nombre_c100'].tolist()
        sede = df_demanda['sede'].tolist()
        del df_demanda
        return id, items, proveedor, productos, sede
        
    #funcion para probar el pronostico
    def prueba():
        start_time = time.perf_counter()
        # MAD, MAPE, MAPE_prima, ECM, demanda, promedio_movil, lista_pronosticos, lista_pronosticos_redondeo, df_demanda = PronosticoMovil.promedioMovil(5)
        id, items, proveedor, productos, sede = PronosticoMovil.productos()
        
        # serie = pd.concat([pd.Series(productos), pd.Series(MAD), pd.Series(MAPE)], axis=1)
        # serie.columns = ["Productos", "MAD", "Mejor pronostico"]
        # df = pd.DataFrame({"Items": items, "Proveedor": proveedor, "Productos": productos, "Sede":sede, "MAD": MAD, "MAPE": MAPE, "MAPE_Prima": MAPE_prima, "ECM": ECM, "Pronostico": lista_pronosticos, "Pronostico redondeado": lista_pronosticos_redondeo})
    
        # # Especifica la ruta del archivo Excel donde deseas guardar el DataFrame
        # ruta_archivo_excel = 'pronosticos_movil.xlsx'

        # # Usa el método to_excel() para guardar el DataFrame en el archivo Excel
        # df.to_excel(ruta_archivo_excel, index=False)  # Si no deseas incluir el índice en el archivo Excel, puedes establecer index=False
        end_time = time.perf_counter()
        print(f"Tiempo de ejecución: {end_time - start_time} segundos")

# PronosticoMovil.prueba()
