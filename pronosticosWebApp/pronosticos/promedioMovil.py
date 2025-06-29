from datetime import date, datetime, timedelta
from django.db.models import Sum, Case, When, IntegerField, Value, CharField, ExpressionWrapper, DecimalField, F
import pandas as pd
import numpy as np
import time
from pronosticosWebApp.models import Producto

class PronosticoMovil:
    
    def __init__(self):
        pass
    
    def getDataBD():
        #obtener todos los productos flitrando por año y mes
        # print('Obteniendo datos de la base de datos...')
        # Obtener todos los productos
        # productos = Producto.objects.all().values()
        # Filtrar productos por año y mes
        # productos = Producto.objects.filter(yyyy=2025, mm=3).values()
        
        # # convertir productos a dataframe
        # df_productos = pd.DataFrame(productos)
        # df_productos.to_excel('productos.xlsx', index=False)
        # print('Datos obtenidos y guardados en productos.xlsx')
        # 1. Obtener el último día del mes anterior al actual
        hoy = date.today()
        primer_dia_mes_actual = date(hoy.year, hoy.month, 1)
        ultimo_dia_mes_anterior = primer_dia_mes_actual - timedelta(days=1)

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
        
        # precios
        precios_ultimos_12_meses_tulua = list(
            Producto.objects
            .filter(
                fecha__gte=fecha_inicio.strftime("%Y%m%d"),  # Filtrar desde la fecha inicial
                fecha__lte=ultimo_dia_mes_anterior.strftime("%Y%m%d"),  # Hasta la fecha máxima
                bod__in=['0101', '0102', '0105','0180']  # Solo las bodegas de Tuluá
            )
            .annotate(
                bod_agrupada=Value("0105", output_field=CharField()),  # Nueva columna para reemplazar la bodega
                sede=Value("Tuluá", output_field=CharField()),
                precio=Case(
                    When(
                        cantidad=0,
                        then=ExpressionWrapper(
                            F('costo_ult'),
                            output_field=IntegerField()
                        )
                    ),
                    default=ExpressionWrapper(
                        F('costo_ult') / F('cantidad'),
                        output_field=IntegerField()
                    ),
                    output_field=IntegerField()
                )
            )
            .values('yyyy', 'mm', 'sku', 'sku_nom', 'marca_nom', 'bod_agrupada', 'umd', 'sede', 'precio')  # usamos bod_agrupada
            .annotate(total=Sum('cantidad'))
            .order_by('yyyy', 'mm') 
        )
        # df_precios = pd.DataFrame(precios_ultimos_12_meses_tulua)
        # df_precios.to_excel('precios.xlsx', index=False)
        # print('terminado precios')
        
        ventas_ultimos_12_meses_tulua = list(
            Producto.objects
            .filter(
                fecha__gte=fecha_inicio.strftime("%Y%m%d"),  # Filtrar desde la fecha inicial
                fecha__lte=ultimo_dia_mes_anterior.strftime("%Y%m%d"),  # Hasta la fecha máxima
                bod__in=['0101', '0102', '0105','0180']  # Solo las bodegas de Tuluá
            )
            .annotate(
                bod_agrupada=Value("0105", output_field=CharField()),  # Nueva columna para reemplazar la bodega
                sede=Value("Tuluá", output_field=CharField())
            )
            .values('yyyy', 'mm', 'sku', 'sku_nom', 'marca_nom', 'bod_agrupada', 'umd', 'sede')  # usamos bod_agrupada
            .annotate(total=Sum('cantidad'))
            .order_by('yyyy', 'mm') 
        )
     
        precios_ultimos_12_meses_buga = list(
            Producto.objects
            .filter(
                fecha__gte=fecha_inicio.strftime("%Y%m%d"),  # Filtrar desde la fecha inicial
                fecha__lte=ultimo_dia_mes_anterior.strftime("%Y%m%d"),  # Hasta la fecha máxima
                bod__in=['0201','0202','0205','0212','0280','0240']  # Solo las bodegas de Tuluá
            ).annotate(
                bod_agrupada=Value("0205", output_field=CharField()),  # Nueva columna para reemplazar la bodega
                sede=Value("Buga", output_field=CharField()),
                precio=Case(
                    When(
                        cantidad=0,
                        then=ExpressionWrapper(
                            F('costo_ult'),
                            output_field=IntegerField()
                        )
                    ),
                    default=ExpressionWrapper(
                        F('costo_ult') / F('cantidad'),
                        output_field=IntegerField()
                    ),
                    output_field=IntegerField()
                )
            )
            .values('yyyy', 'mm', 'sku', 'sku_nom', 'marca_nom', 'bod_agrupada', 'umd', 'sede', 'precio')
            .annotate(total=Sum('cantidad'))
            .order_by('yyyy', 'mm')  # Orden descendente (más reciente primero)
        )
        
        ventas_ultimos_12_meses_buga = list(
            Producto.objects
            .filter(
                fecha__gte=fecha_inicio.strftime("%Y%m%d"),  # Filtrar desde la fecha inicial
                fecha__lte=ultimo_dia_mes_anterior.strftime("%Y%m%d"),  # Hasta la fecha máxima
                bod__in=['0201','0202','0205','0212','0280','0240']  # Solo las bodegas de Tuluá
            ).annotate(
                bod_agrupada=Value("0205", output_field=CharField()),  # Nueva columna para reemplazar la bodega
                sede=Value("Buga", output_field=CharField())
            )
            .values('yyyy', 'mm', 'sku', 'sku_nom', 'marca_nom', 'bod_agrupada', 'umd', 'sede')
            .annotate(total=Sum('cantidad'))
            .order_by('yyyy', 'mm')  # Orden descendente (más reciente primero)
        )
        
        precios_ultimos_12_meses_cartago = list(
            Producto.objects
            .filter(
                fecha__gte=fecha_inicio.strftime("%Y%m%d"),  # Filtrar desde la fecha inicial
                fecha__lte=ultimo_dia_mes_anterior.strftime("%Y%m%d"),  # Hasta la fecha máxima
                bod__in=['0301','0302','0305','0380','0333']  # Solo las bodegas de Tuluá
            ).annotate(
                bod_agrupada=Value("0305", output_field=CharField()),  # Nueva columna para reemplazar la bodega
                sede=Value("Cartago", output_field=CharField()),
                precio=Case(
                    When(
                        cantidad=0,
                        then=ExpressionWrapper(
                            F('costo_ult'),
                            output_field=IntegerField()
                        )
                    ),
                    default=ExpressionWrapper(
                        F('costo_ult') / F('cantidad'),
                        output_field=IntegerField()
                    ),
                    output_field=IntegerField()
                )
            )
            .values('yyyy', 'mm', 'sku', 'sku_nom', 'marca_nom', 'bod_agrupada', 'umd', 'sede', 'precio')
            .annotate(total=Sum('cantidad'))
            .order_by('yyyy', 'mm')  # Orden descendente (más reciente primero)
        )  
        
        ventas_ultimos_12_meses_cartago = list(
            Producto.objects
            .filter(
                fecha__gte=fecha_inicio.strftime("%Y%m%d"),  # Filtrar desde la fecha inicial
                fecha__lte=ultimo_dia_mes_anterior.strftime("%Y%m%d"),  # Hasta la fecha máxima
                bod__in=['0301','0302','0305','0380','0333']  # Solo las bodegas de Tuluá
            ).annotate(
                bod_agrupada=Value("0305", output_field=CharField()),  # Nueva columna para reemplazar la bodega
                sede=Value("Cartago", output_field=CharField())
            )
            .values('yyyy', 'mm', 'sku', 'sku_nom', 'marca_nom', 'bod_agrupada', 'umd', 'sede')
            .annotate(total=Sum('cantidad'))
            .order_by('yyyy', 'mm')  # Orden descendente (más reciente primero)
        )

        precio_ultimos_12_meses_cali = list(
            Producto.objects
            .filter(
                fecha__gte=fecha_inicio.strftime("%Y%m%d"),  # Filtrar desde la fecha inicial
                fecha__lte=ultimo_dia_mes_anterior.strftime("%Y%m%d"),  # Hasta la fecha máxima
                bod__in=['0401','0402','0405','0480']  
            ).annotate(
                bod_agrupada=Value("0405", output_field=CharField()),  # Nueva columna para reemplazar la bodega
                sede=Value("Cali", output_field=CharField()),
                precio=Case(
                    When(
                        cantidad=0,
                        then=ExpressionWrapper(
                            F('costo_ult'),
                            output_field=IntegerField()
                        )
                    ),
                    default=ExpressionWrapper(
                        F('costo_ult') / F('cantidad'),
                        output_field=IntegerField()
                    ),
                    output_field=IntegerField()
                )
            )
            .values('yyyy', 'mm', 'sku', 'sku_nom', 'marca_nom', 'bod_agrupada', 'umd', 'sede', 'precio')
            .annotate(total=Sum('cantidad'))
            .order_by('yyyy', 'mm')  # Orden descendente (más reciente primero)
        )
        
        ventas_ultimos_12_meses_cali = list(
            Producto.objects
            .filter(
                fecha__gte=fecha_inicio.strftime("%Y%m%d"),  # Filtrar desde la fecha inicial
                fecha__lte=ultimo_dia_mes_anterior.strftime("%Y%m%d"),  # Hasta la fecha máxima
                bod__in=['0401','0402','0405','0480']  # Solo las bodegas de Tuluá
            ).annotate(
                bod_agrupada=Value("0405", output_field=CharField()),  # Nueva columna para reemplazar la bodega
                sede=Value("Cali", output_field=CharField())
            )
            .values('yyyy', 'mm', 'sku', 'sku_nom', 'marca_nom', 'bod_agrupada', 'umd', 'sede')
            .annotate(total=Sum('cantidad'))
            .order_by('yyyy', 'mm')  # Orden descendente (más reciente primero)
        )
        
        # unir listas de precios
        precios_ultimos_12_meses = precios_ultimos_12_meses_tulua + precios_ultimos_12_meses_buga + precios_ultimos_12_meses_cartago + precio_ultimos_12_meses_cali
        
        # Crear diccionario con el precio más reciente
        precios_dict = {}
        for p in precios_ultimos_12_meses:
            clave = (p['sku'], p['sku_nom'], p['marca_nom'])
            fecha_actual = (int(p['yyyy']), int(p['mm']))
            
            if clave not in precios_dict or fecha_actual > precios_dict[clave]['fecha']:
                precios_dict[clave] = {
                    'precio': p['precio'],
                    'fecha': fecha_actual
                }
        # Si quieres solo el precio final sin la fecha:
        precios_dict = {k: v['precio'] for k, v in precios_dict.items()}
        
        # with open("salida.txt", "w", encoding="utf-8") as f:
        #     f.write(str(precios_dict))
        # print('terminado txt')
        
        # Ahora agregamos precio a las ventas
        ventas_final_tulua = []
        for venta in ventas_ultimos_12_meses_tulua:
            clave = (venta['sku'], venta['sku_nom'], venta['marca_nom'])
            venta['precio'] = precios_dict.get(clave, None)  # Si no hay precio, dejar en None
            ventas_final_tulua.append(venta)
        
        # ahora agregamos precio a las ventas de buga
        ventas_final_buga = []
        for venta in ventas_ultimos_12_meses_buga:
            clave = (venta['sku'], venta['sku_nom'], venta['marca_nom'])
            venta['precio'] = precios_dict.get(clave, None)
            ventas_final_buga.append(venta)
        
        # ahora agregamos precio a las ventas de cali
        ventas_final_cali = []
        for venta in ventas_ultimos_12_meses_cali:
            clave = (venta['sku'], venta['sku_nom'], venta['marca_nom'])
            venta['precio'] = precios_dict.get(clave, None)
            ventas_final_cali.append(venta)
        
        # ahora agregamos precio a las ventas de cartago
        ventas_final_cartago = []
        for venta in ventas_ultimos_12_meses_cartago:
            clave = (venta['sku'], venta['sku_nom'], venta['marca_nom'])
            venta['precio'] = precios_dict.get(clave, None)
            ventas_final_cartago.append(venta)
       
        #tulua
        dict_tulua = {}
        for venta in ventas_final_tulua:
            y = venta['yyyy']
            m = venta['mm']
            sku = venta['sku']
            sku_nom = venta['sku_nom']
            marca_nom = venta['marca_nom']
            bod = venta['bod_agrupada']
            umd = venta['umd']
            total = venta['total'] or 0
            dict_tulua[(y, m, sku, sku_nom, marca_nom, bod, umd)] = total
        
        # Supongamos que tienes un set con todos los SKUs (o podrías iterar por cada queryset y hacer un union)
        skus_tulua = set((item['sku'], item['sku_nom'], item['marca_nom'], item['bod_agrupada'], item['umd'], item['sede'], item['precio']) for item in ventas_final_tulua)
        # Lista final de datos rellenados
        resultado_tulua = []
        for (sku, sku_nom, marca_nom, bod, umd, sede, precio) in skus_tulua:
            for (anio, mes) in lista_meses:
                total = dict_tulua.get((anio, mes, sku, sku_nom, marca_nom, bod, umd), 0)
                resultado_tulua.append({
                    'yyyy': anio,
                    'mm': mes,
                    'sku': sku,
                    'sku_nom': sku_nom,
                    'marca_nom': marca_nom,
                    'bod': bod,
                    'umd': umd,
                    'total': total,
                    'sede': sede,
                    'precio': precio,
                })   
        # buga
        dict_buga = {}
        for venta in ventas_final_buga:
            y = venta['yyyy']
            m = venta['mm']
            sku = venta['sku']
            sku_nom = venta['sku_nom']
            marca_nom = venta['marca_nom']
            bod = venta['bod_agrupada']
            umd = venta['umd']
            total = venta['total'] or 0
            dict_buga[(y, m, sku, sku_nom, marca_nom, bod, umd)] = total
        
        # Supongamos que tienes un set con todos los SKUs (o podrías iterar por cada queryset y hacer un union)
        skus_buga = set((item['sku'], item['sku_nom'], item['marca_nom'], item['bod_agrupada'], item['umd'], item['sede'], item['precio']) for item in ventas_final_buga)
        # Lista final de datos rellenados
        resultado_buga = []
        for (sku, sku_nom, marca_nom, bod, umd, sede, precio) in skus_buga:
            for (anio, mes) in lista_meses:
                total = dict_buga.get((anio, mes, sku, sku_nom, marca_nom, bod, umd), 0)
                resultado_buga.append({
                    'yyyy': anio,
                    'mm': mes,
                    'sku': sku,
                    'sku_nom': sku_nom,
                    'marca_nom': marca_nom,
                    'bod': bod,
                    'umd': umd,
                    'total': total,
                    'sede': sede,
                    'precio': precio,
                })    
        
        # cartago
        dict_cartago = {}
        for venta in ventas_final_cartago:
            y = venta['yyyy']
            m = venta['mm']
            sku = venta['sku']
            sku_nom = venta['sku_nom']
            marca_nom = venta['marca_nom']
            bod = venta['bod_agrupada']
            umd = venta['umd']
            total = venta['total'] or 0
            dict_cartago[(y, m, sku, sku_nom, marca_nom, bod, umd)] = total
        
        # Supongamos que tienes un set con todos los SKUs (o podrías iterar por cada queryset y hacer un union)
        skus_cartago = set((item['sku'], item['sku_nom'], item['marca_nom'], item['bod_agrupada'], item['umd'], item['sede'], item['precio']) for item in ventas_final_cartago)
        # Lista final de datos rellenados
        resultado_cartago = []
        for (sku, sku_nom, marca_nom, bod, umd, sede, precio) in skus_cartago:
            for (anio, mes) in lista_meses:
                total = dict_cartago.get((anio, mes, sku, sku_nom, marca_nom, bod, umd), 0)
                resultado_cartago.append({
                    'yyyy': anio,
                    'mm': mes,
                    'sku': sku,
                    'sku_nom': sku_nom,
                    'marca_nom': marca_nom,
                    'bod': bod,
                    'umd': umd,
                    'total': total,
                    'sede': sede,
                    'precio': precio,
                })    
        
        # cali
        dict_cali = {}
        for venta in ventas_final_cali:
            y = venta['yyyy']
            m = venta['mm']
            sku = venta['sku']
            sku_nom = venta['sku_nom']
            marca_nom = venta['marca_nom']
            bod = venta['bod_agrupada']
            umd = venta['umd']
            total = venta['total'] or 0
            dict_cali[(y, m, sku, sku_nom, marca_nom, bod, umd)] = total
        
        # Supongamos que tienes un set con todos los SKUs (o podrías iterar por cada queryset y hacer un union)
        skus_cali = set((item['sku'], item['sku_nom'], item['marca_nom'], item['bod_agrupada'], item['umd'], item['sede'], item['precio']) for item in ventas_final_cali)
        # Lista final de datos rellenados
        resultado_cali = []
        for (sku, sku_nom, marca_nom, bod, umd, sede, precio) in skus_cali:
            for (anio, mes) in lista_meses:
                total = dict_cali.get((anio, mes, sku, sku_nom, marca_nom, bod, umd), 0)
                resultado_cali.append({
                    'yyyy': anio,
                    'mm': mes,
                    'sku': sku,
                    'sku_nom': sku_nom,
                    'marca_nom': marca_nom,
                    'bod': bod,
                    'umd': umd,
                    'total': total,
                    'sede': sede,
                    'precio': precio,
                })    
        
        final = resultado_tulua + resultado_buga + resultado_cartago + resultado_cali
        df_demanda = pd.DataFrame(final)
        df_demanda = df_demanda[df_demanda['sku'].astype(str).str.isdigit()]
        # rellenar con cero la columna de precio si es nulo
        df_demanda['precio'] = df_demanda['precio'].fillna(0)
        
        # obtener registros por sku
        # df_demanda = df_demanda.head(100)
        return df_demanda
        
    def promedioMovil_3(n):
        print('Calculando pronóstico de promedio móvil n=3...')
                
        df_demanda = pd.DataFrame(PronosticoMovil.getDataBD()) # Se convierten los productos en un DataFrame de pandas para su manipulación
        # Ordenar directamente por 'sku', 'sede' y 'mm' sin agrupar
        # df_demanda = df_demanda.sort_values(by=['sku', 'sede', 'mm']).reset_index(drop=True)
        sku = []
        marca_nom = []
        sku_nom = []
        bod = []
        umd = []
        sede = []
        precio = []
        
        # Función para calcular el pronóstico y errores por grupo
        def calcular_pronostico(df):
            # df = df.sort_values(by=['mm'])  # Asegurar orden temporal dentro del grupo
            
            # Obtener el último año y mes
            ultimo_anio = df.iloc[-1]['yyyy']
            ultimo_mes = df.iloc[-1]['mm']

            # Crear una nueva fila con el mes 13
            nueva_fila = {
                'yyyy': ultimo_anio,
                'mm': 13,  # Identificar el pronóstico con mes 13
                'sku': df.iloc[-1]['sku'],
                'sku_nom': df.iloc[-1]['sku_nom'],
                'marca_nom': df.iloc[-1]['marca_nom'],
                'bod': df.iloc[-1]['bod'],
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
            
            sku.append(df.iloc[0]['sku'])
            marca_nom.append(df.iloc[0]['marca_nom'])
            sku_nom.append(df.iloc[0]['sku_nom'])
            bod.append(df.iloc[0]['bod'])
            umd.append(df.iloc[0]['umd'])
            sede.append(df.iloc[0]['sede'])
            precio.append(df.iloc[0]['precio'])
            
            return df
        # Aplicar la función a cada combinación de SKU y sede
        df_resultado = df_demanda.groupby(['sku', 'sku_nom', 'sede'], group_keys=False).apply(calcular_pronostico)
        
        # Reiniciar el índice después del groupby
        df_resultado = df_resultado.reset_index(drop=True)
        
        # crea una lista con la columna MAD del dataframe omitiendo los nulos
        # MAD = df_resultado['MAD'].dropna().tolist()
        
        return df_resultado, df_demanda  #demanda, promedio_movil, lista_pronosticos
    
    def promedioMovil_4(n):
        print('Calculando pronóstico de promedio móvil n=4...')
        df_demanda = pd.DataFrame(PronosticoMovil.getDataBD()) # Se convierten los productos en un DataFrame de pandas para su manipulación
        # Función para calcular el pronóstico y errores por grupo
        def calcular_pronostico(df):
            # df = df.sort_values(by=['mm'])  # Asegurar orden temporal dentro del grupo
            
            # Obtener el último año y mes
            ultimo_anio = df.iloc[-1]['yyyy']
            ultimo_mes = df.iloc[-1]['mm']

            # Crear una nueva fila con el mes 13
            nueva_fila = {
                'yyyy': ultimo_anio,
                'mm': 13,  # Identificar el pronóstico con mes 13
                'sku': df.iloc[-1]['sku'],
                'sku_nom': df.iloc[-1]['sku_nom'],
                'marca_nom': df.iloc[-1]['marca_nom'],
                'bod': df.iloc[-1]['bod'],
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
        df_resultado = df_demanda.groupby(['sku', 'sku_nom', 'sede'], group_keys=False).apply(calcular_pronostico)
        # Reiniciar el índice después del groupby
        df_resultado = df_resultado.reset_index(drop=True)
        # df_resultado.to_excel('ventasMAD.xlsx', index=False)
        
        return df_resultado #promedio_movil, lista_pronosticos
    
    def promedioMovil_5(n):
        print('Calculando pronóstico de promedio móvil n=5...')
        df_demanda = pd.DataFrame(PronosticoMovil.getDataBD()) # Se convierten los productos en un DataFrame de pandas para su manipulación
        # Función para calcular el pronóstico y errores por grupo
        def calcular_pronostico(df):
            # df = df.sort_values(by=['mm'])  # Asegurar orden temporal dentro del grupo
            
            # Obtener el último año y mes
            ultimo_anio = df.iloc[-1]['yyyy']
            ultimo_mes = df.iloc[-1]['mm']

            # Crear una nueva fila con el mes 13
            nueva_fila = {
                'yyyy': ultimo_anio,
                'mm': 13,  # Identificar el pronóstico con mes 13
                'sku': df.iloc[-1]['sku'],
                'sku_nom': df.iloc[-1]['sku_nom'],
                'marca_nom': df.iloc[-1]['marca_nom'],
                'bod': df.iloc[-1]['bod'],
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
        df_resultado = df_demanda.groupby(['sku', 'sku_nom', 'sede'], group_keys=False).apply(calcular_pronostico)
        # Reiniciar el índice después del groupby
        df_resultado = df_resultado.reset_index(drop=True)
        # df_resultado.to_excel('ventasMAD.xlsx', index=False)
        
        return df_resultado #promedio_movil, lista_pronosticos