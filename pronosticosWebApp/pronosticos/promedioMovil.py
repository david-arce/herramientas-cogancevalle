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
        return list(Producto.objects.order_by('id').values()[:100]) # Se obtienen los productos de la base de datos en forma de lista
        
    def promedioMovil_3(n):
        print('Calculando pronóstico de promedio móvil...')
        df_demanda = pd.DataFrame(PronosticoMovil.getDataBD()) # Se convierten los productos en un DataFrame de pandas para su manipulación
        
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
        dict_tulua = {}
        for venta in ventas_ultimos_12_meses_tulua:
            y = venta['yyyy']
            m = venta['mm']
            sku = venta['sku']
            total = venta['total'] or 0
            dict_tulua[(y, m, sku)] = total
        
        # Supongamos que tienes un set con todos los SKUs (o podrías iterar por cada queryset y hacer un union)
        skus_tulua = set(item['sku'] for item in ventas_ultimos_12_meses_tulua)
        # Lista final de datos rellenados
        resultado_tulua = []
        for sku in skus_tulua:
            for (anio, mes) in lista_meses:
                total = dict_tulua.get((anio, mes, sku), 0)
                resultado_tulua.append({
                    'yyyy': anio,
                    'mm': mes,
                    'sku': sku,
                    'total': total,
                    'sede': 'Tuluá'
                })    
        
        # buga
        dict_buga = {}
        for venta in ventas_ultimos_12_meses_buga:
            y = venta['yyyy']
            m = venta['mm']
            sku = venta['sku']
            total = venta['total'] or 0
            dict_buga[(y, m, sku)] = total
        
        # Supongamos que tienes un set con todos los SKUs (o podrías iterar por cada queryset y hacer un union)
        skus_buga = set(item['sku'] for item in ventas_ultimos_12_meses_buga)
        # Lista final de datos rellenados
        resultado_buga = []
        for sku in skus_buga:
            for (anio, mes) in lista_meses:
                total = dict_buga.get((anio, mes, sku), 0)
                resultado_buga.append({
                    'yyyy': anio,
                    'mm': mes,
                    'sku': sku,
                    'total': total,
                    'sede': 'Buga'
                })    
        
        # cartago
        dict_cartago = {}
        for venta in ventas_ultimos_12_meses_cartago:
            y = venta['yyyy']
            m = venta['mm']
            sku = venta['sku']
            total = venta['total'] or 0
            dict_cartago[(y, m, sku)] = total
        
        # Supongamos que tienes un set con todos los SKUs (o podrías iterar por cada queryset y hacer un union)
        skus_cartago = set(item['sku'] for item in ventas_ultimos_12_meses_cartago)
        # Lista final de datos rellenados
        resultado_cartago = []
        for sku in skus_cartago:
            for (anio, mes) in lista_meses:
                total = dict_cartago.get((anio, mes, sku), 0)
                resultado_cartago.append({
                    'yyyy': anio,
                    'mm': mes,
                    'sku': sku,
                    'total': total,
                    'sede': 'Cartago'
                })    
        
        # cali
        dict_cali = {}
        for venta in ventas_ultimos_12_meses_cali:
            y = venta['yyyy']
            m = venta['mm']
            sku = venta['sku']
            total = venta['total'] or 0
            dict_cali[(y, m, sku)] = total
        
        # Supongamos que tienes un set con todos los SKUs (o podrías iterar por cada queryset y hacer un union)
        skus_cali = set(item['sku'] for item in ventas_ultimos_12_meses_cali)
        # Lista final de datos rellenados
        resultado_cali = []
        for sku in skus_cali:
            for (anio, mes) in lista_meses:
                total = dict_cali.get((anio, mes, sku), 0)
                resultado_cali.append({
                    'yyyy': anio,
                    'mm': mes,
                    'sku': sku,
                    'total': total,
                    'sede': 'Cali'
                })    
        
        final = resultado_tulua + resultado_buga + resultado_cartago + resultado_cali
        # df = pd.DataFrame(final)
        # df.to_excel('ventas_ultimos_12_meses.xlsx', index=False)
        
        
        #-----------------------------------------------------------------------------------------------------------------
        
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
