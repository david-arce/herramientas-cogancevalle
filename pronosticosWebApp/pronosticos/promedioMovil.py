from datetime import date, datetime, timedelta
from django.db.models import Sum, Case, When, IntegerField, Value, CharField
import pandas as pd
import numpy as np
import time
from pronosticosWebApp.models import Producto
from collections import defaultdict

class PronosticoMovil:
    
    def __init__(self):
        pass
    
    def getDataBD():
        
        # 1. Obtener la fecha más reciente en la base de datos
        ultima_fecha_str = Producto.objects.order_by('-fecha').values_list('fecha', flat=True).first()
        if not ultima_fecha_str:
            print("No hay datos disponibles.")
            exit()

        # Convertir la fecha de string a objeto date (asumiendo formato 'YYYYMMDD')
        ultima_fecha = datetime.strptime(ultima_fecha_str, "%Y%m%d").date()

        # 2. Obtener el último día del mes anterior
        primer_dia_mes_actual = date(ultima_fecha.year, ultima_fecha.month, 1)
        ultimo_dia_mes_anterior = primer_dia_mes_actual - timedelta(days=1)
        
        # 3. Obtener la fecha de inicio (primer día del mes hace 11 meses)
        meses_atras = 11
        anio_inicio = ultimo_dia_mes_anterior.year
        mes_inicio = ultimo_dia_mes_anterior.month

        for _ in range(meses_atras):
            mes_inicio -= 1
            if mes_inicio == 0:  # Si llegamos a enero, retrocedemos un año
                mes_inicio = 12
                anio_inicio -= 1

        fecha_inicio = date(anio_inicio, mes_inicio, 1)  # Primer día del mes 12 contando hacia atrás
        
        def generar_lista_meses(fecha_inicio, fecha_fin):
            lista_meses = []
            
            # Nos aseguramos de empezar siempre en el primer día del mes de fecha_inicio
            current_date = date(fecha_inicio.year, fecha_inicio.month, 1)
            
            # Avanzamos mes a mes hasta sobrepasar la fecha_fin
            while current_date <= fecha_fin:
                lista_meses.append((current_date.year, current_date.month))
                # Calculamos el siguiente mes
                next_month = current_date.month + 1
                next_year = current_date.year
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                current_date = date(next_year, next_month, 1)
            
            return lista_meses
       
        lista_meses = generar_lista_meses(fecha_inicio, ultimo_dia_mes_anterior)
        
        ventas_ultimos_12_meses_tulua = list(
            Producto.objects
            .filter(
                fecha__gte=fecha_inicio.strftime("%Y%m%d"),  # Filtrar desde la fecha inicial
                fecha__lte=ultimo_dia_mes_anterior.strftime("%Y%m%d"),  # Hasta la fecha máxima
                bod__in=['0101', '0102', '0105']  # Solo las bodegas de Tuluá
            )
            .values('yyyy', 'mm', 'sku', 'sku_nom', 'marca_nom')
            .annotate(total=Sum('cantidad'), sede=Value("Tuluá", output_field=CharField()))
            .order_by('yyyy', 'mm')  # Orden descendente (más reciente primero)
        )
        ventas_ultimos_12_meses_buga = list(
            Producto.objects
            .filter(
                fecha__gte=fecha_inicio.strftime("%Y%m%d"),  # Filtrar desde la fecha inicial
                fecha__lte=ultimo_dia_mes_anterior.strftime("%Y%m%d"),  # Hasta la fecha máxima
                bod__in=['0201','0202','0205']  # Solo las bodegas de Tuluá
            )
            .values('yyyy', 'mm', 'sku', 'sku_nom', 'marca_nom')
            .annotate(total=Sum('cantidad'), sede=Value("Buga", output_field=CharField()))
            .order_by('yyyy', 'mm')  # Orden descendente (más reciente primero)
        )
        ventas_ultimos_12_meses_cartago = list(
            Producto.objects
            .filter(
                fecha__gte=fecha_inicio.strftime("%Y%m%d"),  # Filtrar desde la fecha inicial
                fecha__lte=ultimo_dia_mes_anterior.strftime("%Y%m%d"),  # Hasta la fecha máxima
                bod__in=['0301','0302','0305']  # Solo las bodegas de Tuluá
            )
            .values('yyyy', 'mm', 'sku', 'sku_nom', 'marca_nom')
            .annotate(total=Sum('cantidad'), sede=Value("cartago", output_field=CharField()))
            .order_by('yyyy', 'mm')  # Orden descendente (más reciente primero)
        )
        ventas_ultimos_12_meses_cali = list(
            Producto.objects
            .filter(
                fecha__gte=fecha_inicio.strftime("%Y%m%d"),  # Filtrar desde la fecha inicial
                fecha__lte=ultimo_dia_mes_anterior.strftime("%Y%m%d"),  # Hasta la fecha máxima
                bod__in=['0401','0402','0405']  # Solo las bodegas de Tuluá
            )
            .values('yyyy', 'mm', 'sku', 'sku_nom', 'marca_nom')
            .annotate(total=Sum('cantidad'), sede=Value("cali", output_field=CharField()))
            .order_by('yyyy', 'mm')  # Orden descendente (más reciente primero)
        )
        #tulua
        dict_tulua = {}
        for venta in ventas_ultimos_12_meses_tulua:
            y = venta['yyyy']
            m = venta['mm']
            sku = venta['sku']
            sku_nom = venta['sku_nom']
            marca_nom = venta['marca_nom']
            total = venta['total'] or 0
            dict_tulua[(y, m, sku, sku_nom, marca_nom)] = total
        
        # Supongamos que tienes un set con todos los SKUs (o podrías iterar por cada queryset y hacer un union)
        skus_tulua = set((item['sku'], item['sku_nom'], item['marca_nom']) for item in ventas_ultimos_12_meses_tulua)
        # Lista final de datos rellenados
        resultado_tulua = []
        for (sku, sku_nom, marca_nom) in skus_tulua:
            for (anio, mes) in lista_meses:
                total = dict_tulua.get((anio, mes, sku, sku_nom, marca_nom), 0)
                resultado_tulua.append({
                    'yyyy': anio,
                    'mm': mes,
                    'sku': sku,
                    'sku_nom': sku_nom,
                    'marca_nom': marca_nom,
                    'total': total,
                    'sede': 'Tuluá'
                })   
        # buga
        dict_buga = {}
        for venta in ventas_ultimos_12_meses_buga:
            y = venta['yyyy']
            m = venta['mm']
            sku = venta['sku']
            sku_nom = venta['sku_nom']
            marca_nom = venta['marca_nom']
            total = venta['total'] or 0
            dict_buga[(y, m, sku, sku_nom, marca_nom)] = total
        
        # Supongamos que tienes un set con todos los SKUs (o podrías iterar por cada queryset y hacer un union)
        skus_buga = set((item['sku'], item['sku_nom'], item['marca_nom']) for item in ventas_ultimos_12_meses_buga)
        # Lista final de datos rellenados
        resultado_buga = []
        for (sku, sku_nom, marca_nom) in skus_buga:
            for (anio, mes) in lista_meses:
                total = dict_buga.get((anio, mes, sku, sku_nom, marca_nom), 0)
                resultado_buga.append({
                    'yyyy': anio,
                    'mm': mes,
                    'sku': sku,
                    'sku_nom': sku_nom,
                    'marca_nom': marca_nom,
                    'total': total,
                    'sede': 'Buga'
                })    
        
        # cartago
        dict_cartago = {}
        for venta in ventas_ultimos_12_meses_cartago:
            y = venta['yyyy']
            m = venta['mm']
            sku = venta['sku']
            sku_nom = venta['sku_nom']
            marca_nom = venta['marca_nom']
            total = venta['total'] or 0
            dict_cartago[(y, m, sku, sku_nom, marca_nom)] = total
        
        # Supongamos que tienes un set con todos los SKUs (o podrías iterar por cada queryset y hacer un union)
        skus_cartago = set((item['sku'], item['sku_nom'], item['marca_nom']) for item in ventas_ultimos_12_meses_cartago)
        # Lista final de datos rellenados
        resultado_cartago = []
        for (sku, sku_nom, marca_nom) in skus_cartago:
            for (anio, mes) in lista_meses:
                total = dict_cartago.get((anio, mes, sku, sku_nom, marca_nom), 0)
                resultado_cartago.append({
                    'yyyy': anio,
                    'mm': mes,
                    'sku': sku,
                    'sku_nom': sku_nom,
                    'marca_nom': marca_nom,
                    'total': total,
                    'sede': 'Cartago'
                })    
        
        # cali
        dict_cali = {}
        for venta in ventas_ultimos_12_meses_cali:
            y = venta['yyyy']
            m = venta['mm']
            sku = venta['sku']
            sku_nom = venta['sku_nom']
            marca_nom = venta['marca_nom']
            total = venta['total'] or 0
            dict_cali[(y, m, sku, sku_nom, marca_nom)] = total
        
        # Supongamos que tienes un set con todos los SKUs (o podrías iterar por cada queryset y hacer un union)
        skus_cali = set((item['sku'], item['sku_nom'], item['marca_nom']) for item in ventas_ultimos_12_meses_cali)
        # Lista final de datos rellenados
        resultado_cali = []
        for (sku, sku_nom, marca_nom) in skus_cali:
            for (anio, mes) in lista_meses:
                total = dict_cali.get((anio, mes, sku, sku_nom, marca_nom), 0)
                resultado_cali.append({
                    'yyyy': anio,
                    'mm': mes,
                    'sku': sku,
                    'sku_nom': sku_nom,
                    'marca_nom': marca_nom,
                    'total': total,
                    'sede': 'Cali'
                })    
        
        final = resultado_tulua + resultado_buga + resultado_cartago + resultado_cali
        df_demanda = pd.DataFrame(final)
        df_demanda = df_demanda[df_demanda['sku'].astype(str).str.isdigit()]
        # obtener registros por sku
        df_demanda = df_demanda[df_demanda['sku'] == '100']
        
        return df_demanda
        
    def promedioMovil_3(n):
        print('Calculando pronóstico de promedio móvil n=3...')
                
        df_demanda = pd.DataFrame(PronosticoMovil.getDataBD()) # Se convierten los productos en un DataFrame de pandas para su manipulación
        print(df_demanda)
        # Función para calcular el pronóstico y errores por grupo
        def calcular_pronostico(df):
            df = df.sort_values(by=['mm'])  # Asegurar orden temporal dentro del grupo
            
            # Obtener el último año y mes
            ultimo_anio = df.iloc[-1]['yyyy']
            ultimo_mes = df.iloc[-1]['mm']

            # Crear una nueva fila con el mes 13
            nueva_fila = {
                'yyyy': ultimo_anio,
                'mm': 13,  # Identificar el pronóstico con mes 13
                'sku': df.iloc[-1]['sku'],
                'sku_nom': df.iloc[-1]['sku_nom'],
                'sede': df.iloc[-1]['sede'],
                'total': np.nan,
            }

            # Agregar la fila al DataFrame
            df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)
            
            # Calcular promedio móvil de 3 meses con desplazamiento (para no usar el mes actual en el cálculo)
            df['promedio_movil'] = df['total'].rolling(window=n).mean().shift(1)
            
            # Calcular error absoluto
            df['error'] = abs(df['total'] - df['promedio_movil'])
            
            # Calcular errores para MAPE y MAPE prima
            df['errorMAPE'] = np.where(
            np.isnan(df['error']),  # Si el error es NaN
            np.nan,  
            np.where(df['total'] == 0,  # Si el total es 0
                    1, 
                    df['error'] / df['total'])  # Si no, hacer la división normal
            )
            # calcular errores para calcular el MAPE prima dividiendo el error entre el promedio movil y condicionarlo si el el resultado da cero poner un uno
            df['errorMAPEPrima'] = np.where(
                np.isnan(df['error']),  # Si el error es NaN
                np.nan,
                np.where(df['promedio_movil'] == 0,  # Si el total es 0
                        1, 
                        df['error'] / df['promedio_movil'])
            )
            # Calcular ECM (Error Cuadrático Medio)
            df['errorECM'] = df['error'] ** 2
            
            # calcular MAD con el promedio del error
            mad = df['error'].mean()
            df['MAD'] = np.nan  # Inicializar columna con NaN
            df.loc[df['mm'] == 13, 'MAD'] = mad  # Solo colocar MAD en el mes 13 (última fila)
            
            # Calcular MAPE y MAPE prima
            mape = df['errorMAPE'].mean() * 100
            df['MAPE'] = np.nan  # Inicializar columna con NaN
            df.loc[df['mm'] == 13, 'MAPE'] = mape  # Solo colocar MAPE en el mes 13 (última fila)
            
            mape_prima = df['errorMAPEPrima'].mean() * 100
            df['MAPE_Prima'] = np.nan
            df.loc[df['mm'] == 13, 'MAPE_Prima'] = mape_prima
            
            # Calcular ECM
            ecm = df['errorECM'].mean()
            df['ECM'] = np.nan
            df.loc[df['mm'] == 13, 'ECM'] = ecm
            
            return df
        # Aplicar la función a cada combinación de SKU y sede
        df_resultado = df_demanda.groupby(['sku', 'sede'], group_keys=False).apply(calcular_pronostico)
        # Reiniciar el índice después del groupby
        df_resultado = df_resultado.reset_index(drop=True)
        # df_resultado.to_excel('ventasMAD.xlsx', index=False)
        
        # crea una lista con la columna MAD del dataframe omitiendo los nulos
        MAD = df_resultado['MAD'].dropna().tolist()
        # crea una lista con la columna MAPE del dataframe omitiendo los nulos
        MAPE = df_resultado['MAPE'].dropna().tolist()
        # crea una lista con la columna MAPE prima del dataframe omitiendo los nulos
        MAPE_prima = df_resultado['MAPE_Prima'].dropna().tolist()
        # crea una lista con la columna ECM del dataframe omitiendo los nulos
        ECM = df_resultado['ECM'].dropna().tolist()
        
        #-----------------------------------------------------------------------------------------------------------------
        '''
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
        '''
        return MAD, MAPE, MAPE_prima, ECM, #demanda, promedio_movil, lista_pronosticos
    
    def promedioMovil_4(n):
        print('Calculando pronóstico de promedio móvil n=4...')
        df_demanda = pd.DataFrame(PronosticoMovil.getDataBD()) # Se convierten los productos en un DataFrame de pandas para su manipulación
        # Función para calcular el pronóstico y errores por grupo
        def calcular_pronostico(df):
            df = df.sort_values(by=['mm'])  # Asegurar orden temporal dentro del grupo
            
            # Obtener el último año y mes
            ultimo_anio = df.iloc[-1]['yyyy']
            ultimo_mes = df.iloc[-1]['mm']

            # Crear una nueva fila con el mes 13
            nueva_fila = {
                'yyyy': ultimo_anio,
                'mm': 13,  # Identificar el pronóstico con mes 13
                'sku': df.iloc[-1]['sku'],
                'sku_nom': df.iloc[-1]['sku_nom'],
                'sede': df.iloc[-1]['sede'],
                'total': np.nan,
            }

            # Agregar la fila al DataFrame
            df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)
            
            # Calcular promedio móvil de 3 meses con desplazamiento (para no usar el mes actual en el cálculo)
            df['promedio_movil'] = df['total'].rolling(window=n).mean().shift(1)
            
            # Calcular error absoluto
            df['error'] = abs(df['total'] - df['promedio_movil'])
            
            # Calcular errores para MAPE y MAPE prima
            df['errorMAPE'] = np.where(
            np.isnan(df['error']),  # Si el error es NaN
            np.nan,  
            np.where(df['total'] == 0,  # Si el total es 0
                    1, 
                    df['error'] / df['total'])  # Si no, hacer la división normal
            )
            # calcular errores para calcular el MAPE prima dividiendo el error entre el promedio movil y condicionarlo si el el resultado da cero poner un uno
            df['errorMAPEPrima'] = np.where(
                np.isnan(df['error']),  # Si el error es NaN
                np.nan,
                np.where(df['promedio_movil'] == 0,  # Si el total es 0
                        1, 
                        df['error'] / df['promedio_movil'])
            )
            # Calcular ECM (Error Cuadrático Medio)
            df['errorECM'] = df['error'] ** 2
            
            # calcular MAD con el promedio del error
            mad = df['error'].mean()
            df['MAD'] = np.nan  # Inicializar columna con NaN
            df.loc[df['mm'] == 13, 'MAD'] = mad  # Solo colocar MAD en el mes 13 (última fila)
            
            # Calcular MAPE y MAPE prima
            mape = df['errorMAPE'].mean() * 100
            df['MAPE'] = np.nan  # Inicializar columna con NaN
            df.loc[df['mm'] == 13, 'MAPE'] = mape  # Solo colocar MAPE en el mes 13 (última fila)
            
            mape_prima = df['errorMAPEPrima'].mean() * 100
            df['MAPE_Prima'] = np.nan
            df.loc[df['mm'] == 13, 'MAPE_Prima'] = mape_prima
            
            # Calcular ECM
            ecm = df['errorECM'].mean()
            df['ECM'] = np.nan
            df.loc[df['mm'] == 13, 'ECM'] = ecm
            
            return df
        # Aplicar la función a cada combinación de SKU y sede
        df_resultado = df_demanda.groupby(['sku', 'sede'], group_keys=False).apply(calcular_pronostico)
        # Reiniciar el índice después del groupby
        df_resultado = df_resultado.reset_index(drop=True)
        # df_resultado.to_excel('ventasMAD.xlsx', index=False)
        
        # crea una lista con la columna MAD del dataframe omitiendo los nulos
        MAD = df_resultado['MAD'].dropna().tolist()
        # crea una lista con la columna MAPE del dataframe omitiendo los nulos
        MAPE = df_resultado['MAPE'].dropna().tolist()
        # crea una lista con la columna MAPE prima del dataframe omitiendo los nulos
        MAPE_prima = df_resultado['MAPE_Prima'].dropna().tolist()
        # crea una lista con la columna ECM del dataframe omitiendo los nulos
        ECM = df_resultado['ECM'].dropna().tolist()
        
        return MAD, MAPE, MAPE_prima, ECM, #promedio_movil, lista_pronosticos
    
    def promedioMovil_5(n):
        print('Calculando pronóstico de promedio móvil n=5...')
        df_demanda = pd.DataFrame(PronosticoMovil.getDataBD()) # Se convierten los productos en un DataFrame de pandas para su manipulación
        # Función para calcular el pronóstico y errores por grupo
        def calcular_pronostico(df):
            df = df.sort_values(by=['mm'])  # Asegurar orden temporal dentro del grupo
            
            # Obtener el último año y mes
            ultimo_anio = df.iloc[-1]['yyyy']
            ultimo_mes = df.iloc[-1]['mm']

            # Crear una nueva fila con el mes 13
            nueva_fila = {
                'yyyy': ultimo_anio,
                'mm': 13,  # Identificar el pronóstico con mes 13
                'sku': df.iloc[-1]['sku'],
                'sku_nom': df.iloc[-1]['sku_nom'],
                'sede': df.iloc[-1]['sede'],
                'total': np.nan,
            }

            # Agregar la fila al DataFrame
            df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)
            
            # Calcular promedio móvil de 3 meses con desplazamiento (para no usar el mes actual en el cálculo)
            df['promedio_movil'] = df['total'].rolling(window=n).mean().shift(1)
            
            # Calcular error absoluto
            df['error'] = abs(df['total'] - df['promedio_movil'])
            
            # Calcular errores para MAPE y MAPE prima
            df['errorMAPE'] = np.where(
            np.isnan(df['error']),  # Si el error es NaN
            np.nan,  
            np.where(df['total'] == 0,  # Si el total es 0
                    1, 
                    df['error'] / df['total'])  # Si no, hacer la división normal
            )
            # calcular errores para calcular el MAPE prima dividiendo el error entre el promedio movil y condicionarlo si el el resultado da cero poner un uno
            df['errorMAPEPrima'] = np.where(
                np.isnan(df['error']),  # Si el error es NaN
                np.nan,
                np.where(df['promedio_movil'] == 0,  # Si el total es 0
                        1, 
                        df['error'] / df['promedio_movil'])
            )
            # Calcular ECM (Error Cuadrático Medio)
            df['errorECM'] = df['error'] ** 2
            
            # calcular MAD con el promedio del error
            mad = df['error'].mean()
            df['MAD'] = np.nan  # Inicializar columna con NaN
            df.loc[df['mm'] == 13, 'MAD'] = mad  # Solo colocar MAD en el mes 13 (última fila)
            
            # Calcular MAPE y MAPE prima
            mape = df['errorMAPE'].mean() * 100
            df['MAPE'] = np.nan  # Inicializar columna con NaN
            df.loc[df['mm'] == 13, 'MAPE'] = mape  # Solo colocar MAPE en el mes 13 (última fila)
            
            mape_prima = df['errorMAPEPrima'].mean() * 100
            df['MAPE_Prima'] = np.nan
            df.loc[df['mm'] == 13, 'MAPE_Prima'] = mape_prima
            
            # Calcular ECM
            ecm = df['errorECM'].mean()
            df['ECM'] = np.nan
            df.loc[df['mm'] == 13, 'ECM'] = ecm
            
            return df
        # Aplicar la función a cada combinación de SKU y sede
        df_resultado = df_demanda.groupby(['sku', 'sede'], group_keys=False).apply(calcular_pronostico)
        # Reiniciar el índice después del groupby
        df_resultado = df_resultado.reset_index(drop=True)
        # df_resultado.to_excel('ventasMAD.xlsx', index=False)
        
        # crea una lista con la columna MAD del dataframe omitiendo los nulos
        MAD = df_resultado['MAD'].dropna().tolist()
        # crea una lista con la columna MAPE del dataframe omitiendo los nulos
        MAPE = df_resultado['MAPE'].dropna().tolist()
        # crea una lista con la columna MAPE prima del dataframe omitiendo los nulos
        MAPE_prima = df_resultado['MAPE_Prima'].dropna().tolist()
        # crea una lista con la columna ECM del dataframe omitiendo los nulos
        ECM = df_resultado['ECM'].dropna().tolist()
        
        return MAD, MAPE, MAPE_prima, ECM, #promedio_movil, lista_pronosticos
    
    def productos():
        df_demanda = pd.DataFrame(PronosticoMovil.getDataBD()) # Se convierten los productos en un DataFrame de pandas para su manipulación
        # id = df_demanda['id'].tolist()
        items = df_demanda['sku'].tolist()
        proveedor = df_demanda['marca_nom'].tolist()
        productos = df_demanda['sku_nom'].tolist()
        sede = df_demanda['sede'].tolist()
        del df_demanda
        return items, proveedor, productos, sede
        
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
