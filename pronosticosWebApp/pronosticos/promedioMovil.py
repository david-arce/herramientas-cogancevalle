from datetime import date, datetime, timedelta
from django.db.models import Sum, Case, When, IntegerField, Value, CharField
import pandas as pd
import numpy as np
import time
from pronosticosWebApp.models import Producto

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

        ''' # 4. Filtrar productos de los últimos 12 meses y de las bodegas de Tuluá
        ventas_ultimos_12_meses = list(
            Producto.objects
            .filter(
                fecha__gte=fecha_inicio.strftime("%Y%m%d"),  # Filtrar desde la fecha inicial
                fecha__lte=ultimo_dia_mes_anterior.strftime("%Y%m%d"),  # Hasta la fecha máxima
                bod__in=['0101', '0102', '0105', '0201','0202','0205','0301','0302','0305','0401','0402','0405']  # Solo las bodegas de Tuluá
            )
            .values('yyyy', 'mm', 'sku', 'sku_nom', 'marca_nom')
            .annotate( tulua=Sum(
                Case(When(bod__in=['0101', '0102', '0105'], then='cantidad'), output_field=IntegerField())
                ),
                buga=Sum(
                    Case(When(bod__in=['0201', '0202', '0205'], then='cantidad'), output_field=IntegerField())
                ),
                cartago=Sum(
                    Case(When(bod__in=['0301', '0302', '0305'], then='cantidad'), output_field=IntegerField())
                ),
                cali=Sum(
                    Case(When(bod__in=['0401', '0402', '0405'], then='cantidad'), output_field=IntegerField())
                ))
            .order_by('-yyyy', '-mm')  # Orden descendente (más reciente primero)
        ) '''
        
        
        # 4. Obtener todos los productos únicos en el rango de fechas
        productos_unicos = Producto.objects.filter(
            fecha__gte=fecha_inicio.strftime("%Y%m%d"),
            fecha__lte=ultimo_dia_mes_anterior.strftime("%Y%m%d"),
        ).values_list('sku', 'sku_nom', 'marca_nom').distinct()
        # 5. Generar un rango de meses
        rango_meses = [
            (fecha_inicio.year + (fecha_inicio.month + i - 1) // 12, (fecha_inicio.month + i - 1) % 12 + 1)
            for i in range(12)
        ]
        # 6. Crear una estructura con todos los productos y meses inicializando con 0
        ventas_completas = []
        for sku, sku_nom, marca_nom in productos_unicos:
            for anio, mes in rango_meses:
                ventas_completas.append({
                    'yyyy': anio,
                    'mm': mes,
                    'sku': sku,
                    'sku_nom': sku_nom,
                    'marca_nom': marca_nom,
                    'total': 0,  # Inicializamos en 0
                    'sede': '',  # Se agregará en cada consulta según la bodega
                })
        # 7. Función para actualizar ventas de cada sede
        def obtener_ventas_bodega(bodegas, sede_nombre):
            ventas = Producto.objects.filter(
                fecha__gte=fecha_inicio.strftime("%Y%m%d"),
                fecha__lte=ultimo_dia_mes_anterior.strftime("%Y%m%d"),
                bod__in=bodegas
            ).values('yyyy', 'mm', 'sku', 'sku_nom', 'marca_nom').annotate(
                total=Sum('cantidad'),
                sede=Value(sede_nombre, output_field=CharField())
            ).order_by('yyyy', 'mm')

            # Convertimos a diccionario para fácil acceso
            ventas_dict = {(v['yyyy'], v['mm'], v['sku']): v for v in ventas}

            # Llenamos la lista ventas_completas con los valores obtenidos
            for venta in ventas_completas:
                if (venta['yyyy'], venta['mm'], venta['sku']) in ventas_dict:
                    venta['total'] = ventas_dict[(venta['yyyy'], venta['mm'], venta['sku'])]['total']
                    venta['sede'] = sede_nombre

        # 8. Ejecutar la función para cada sede
        obtener_ventas_bodega(['0101', '0102', '0105'], "Tuluá")
        obtener_ventas_bodega(['0201', '0202', '0205'], "Buga")
        obtener_ventas_bodega(['0301', '0302', '0305'], "Cartago")
        obtener_ventas_bodega(['0401', '0402', '0405'], "Cali")

        # 9. Lista final con ventas, donde los productos que no tenían datos aparecen con '0'
        ventas_ultimos_12_meses = ventas_completas    
        pd_ventas = pd.DataFrame(ventas_ultimos_12_meses)
        pd_ventas.to_excel('ventas_ultimos_12_meses.xlsx', index=False)
        
        # ventas_ultimos_12_meses_tulua = list(
        #     Producto.objects
        #     .filter(
        #         fecha__gte=fecha_inicio.strftime("%Y%m%d"),  # Filtrar desde la fecha inicial
        #         fecha__lte=ultimo_dia_mes_anterior.strftime("%Y%m%d"),  # Hasta la fecha máxima
        #         bod__in=['0101', '0102', '0105']  # Solo las bodegas de Tuluá
        #     )
        #     .values('yyyy', 'mm', 'sku', 'sku_nom', 'marca_nom')
        #     .annotate(total=Sum('cantidad'), sede=Value("Tuluá", output_field=CharField()))
        #     .order_by('yyyy', 'mm')  # Orden descendente (más reciente primero)
        # )
        # ventas_ultimos_12_meses_buga = list(
        #     Producto.objects
        #     .filter(
        #         fecha__gte=fecha_inicio.strftime("%Y%m%d"),  # Filtrar desde la fecha inicial
        #         fecha__lte=ultimo_dia_mes_anterior.strftime("%Y%m%d"),  # Hasta la fecha máxima
        #         bod__in=['0201','0202','0205']  # Solo las bodegas de Tuluá
        #     )
        #     .values('yyyy', 'mm', 'sku', 'sku_nom', 'marca_nom')
        #     .annotate(total=Sum('cantidad'), sede=Value("Buga", output_field=CharField()))
        #     .order_by('yyyy', 'mm')  # Orden descendente (más reciente primero)
        # )
        # ventas_ultimos_12_meses_cartago = list(
        #     Producto.objects
        #     .filter(
        #         fecha__gte=fecha_inicio.strftime("%Y%m%d"),  # Filtrar desde la fecha inicial
        #         fecha__lte=ultimo_dia_mes_anterior.strftime("%Y%m%d"),  # Hasta la fecha máxima
        #         bod__in=['0301','0302','0305']  # Solo las bodegas de Tuluá
        #     )
        #     .values('yyyy', 'mm', 'sku', 'sku_nom', 'marca_nom')
        #     .annotate(total=Sum('cantidad'), sede=Value("cartago", output_field=CharField()))
        #     .order_by('yyyy', 'mm')  # Orden descendente (más reciente primero)
        # )
        # ventas_ultimos_12_meses_cali = list(
        #     Producto.objects
        #     .filter(
        #         fecha__gte=fecha_inicio.strftime("%Y%m%d"),  # Filtrar desde la fecha inicial
        #         fecha__lte=ultimo_dia_mes_anterior.strftime("%Y%m%d"),  # Hasta la fecha máxima
        #         bod__in=['0401','0402','0405']  # Solo las bodegas de Tuluá
        #     )
        #     .values('yyyy', 'mm', 'sku', 'sku_nom', 'marca_nom')
        #     .annotate(total=Sum('cantidad'), sede=Value("cali", output_field=CharField()))
        #     .order_by('yyyy', 'mm')  # Orden descendente (más reciente primero)
        # )
        
        # #unir las dos listas
        # ventas_ultimos_12_meses = ventas_ultimos_12_meses_tulua + ventas_ultimos_12_meses_buga + ventas_ultimos_12_meses_cartago + ventas_ultimos_12_meses_cali
        # ventas_ultimos_12_meses = ventas_ultimos_12_meses
        # pd_ventas = pd.DataFrame(ventas_ultimos_12_meses)
        # pd_ventas.to_excel('ventas_ultimos_12_meses.xlsx', index=False)
        
        # 5. Crear un DataFrame de pandas con los datos de ventas
        # df_demanda = pd.DataFrame(ventas_ultimos_12_meses)
        print(df_demanda)
        ''' # Se filtran los productos de la sede de Tuluá
        venta_tulua_mes1 = df_demanda[(df_demanda['mm'] == 1) & (df_demanda['bod'].isin(['0101','0102','0105','0180']))].groupby(['sku', 'sku_nom', 'marca_nom']).agg({'cantidad': 'sum'}).reset_index() 
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
        venta_tulua_mes12 = df_demanda[(df_demanda['mm'] == 12) & (df_demanda['bod'].isin(['0101','0102','0105','0180']))].groupby(['sku', 'sku_nom', 'marca_nom']).agg({'cantidad': 'sum'}).reset_index()
         '''
       
        
       
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
