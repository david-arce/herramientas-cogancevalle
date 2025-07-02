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
        print(f'Calculando pronóstico de promedio móvil n={n}...')
        # 1. Cargo datos y ordeno
        df_demanda = pd.DataFrame(PronosticoMovil.getDataBD())
        df = (
            df_demanda
            .sort_values(['sku','sku_nom','sede','yyyy','mm'])
            .reset_index(drop=True)
        )
        # 2. Promedio móvil (window=n, desplazado 1 mes)
        df['promedio_movil'] = (
            df
            .groupby(['sku','sku_nom','sede'])['total']
            .transform(lambda x: x.rolling(window=n).mean().shift(1))
        )
        # 3. Errores y versiones para MAPE, ECM, etc.
        df['error'] = (df['total'] - df['promedio_movil']).abs()
        df['errorMAPE'] = np.where(
            df['error'].isna(), 
            np.nan,
            np.where(df['total']==0, 1, df['error']/df['total'])
        )
        df['errorMAPEPrima'] = np.where(
            df['error'].isna(),
            np.nan,
            np.where(df['promedio_movil']==0, 1, df['error']/df['promedio_movil'])
        )
        df['errorECM'] = df['error']**2

        # 4. Agrego todas las métricas de grupo en un solo agg()
        agg = (
            df
            .groupby(['sku','sku_nom','sede'])
            .agg(
                mad=('error','mean'),
                mape=('errorMAPE','mean'),
                mape_prima=('errorMAPEPrima','mean'),
                ecm=('errorECM','mean')
            )
            .reset_index()
        )
        # 5. Calculo el pronóstico (sin shift) para el mes “13”:
        #    rolling(window=n).mean().iloc[-1] == promedio de los últimos n totales
        forecast = (
            df
            .groupby(['sku','sku_nom','sede'])['total']
            .apply(lambda x: x.rolling(window=n).mean().iloc[-1])
            .reset_index(name='promedio_movil')
        )
        # 6. Cojo los datos “constantes” de cada grupo en su última fila histórica
        last = (
            df
            .groupby(['sku','sku_nom','sede'])
            .agg(
                marca_nom=('marca_nom','last'),
                bod       =('bod','last'),
                yyyy      =('yyyy','last')
            )
            .reset_index()
        )
        # 7. Construyo el DataFrame de pronósticos (mes 13) y metadatos
        df_forecast = (
            last
            .merge(forecast, on=['sku','sku_nom','sede'])
            .merge(agg,      on=['sku','sku_nom','sede'])
        )
        df_forecast['mm'] = 13
        df_forecast['total'] = np.nan
        # Campos de error todos NaN en mes 13
        for c in ['error','errorMAPE','errorMAPEPrima','errorECM']:
            df_forecast[c] = np.nan

        # Renombro y ajusto escalas
        df_forecast = df_forecast.rename(columns={'mad':'MAD','ecm':'ECM'})
        df_forecast['MAPE']       = df_forecast['mape'] * 100
        df_forecast['MAPE_Prima'] = df_forecast['mape_prima'] * 100
        df_forecast = df_forecast.drop(columns=['mape','mape_prima'])

        # 8. Concateno todo y ordeno igual que antes
        cols = [
            'yyyy','mm','sku','sku_nom','marca_nom','bod','umd',
            'total','sede','promedio_movil','error','errorMAPE','errorMAPEPrima','errorECM',
            'MAD','MAPE','MAPE_Prima','ECM'
        ]
        df_result = (
            pd.concat([df, df_forecast], ignore_index=True)
            .sort_values(['sku','sku_nom','sede','yyyy','mm'])
            .reset_index(drop=True)
        )[cols]
        return df_result, df_demanda
    
    def promedioMovil_4(n):
        print(f'Calculando pronóstico de promedio móvil n={n}...')
        # 1. Cargo datos y ordeno
        df_demanda = pd.DataFrame(PronosticoMovil.getDataBD())
        df = (
            df_demanda
            .sort_values(['sku','sku_nom','sede','yyyy','mm'])
            .reset_index(drop=True)
        )
        # 2. Promedio móvil (window=n, desplazado 1 mes)
        df['promedio_movil'] = (
            df
            .groupby(['sku','sku_nom','sede'])['total']
            .transform(lambda x: x.rolling(window=n).mean().shift(1))
        )
        # 3. Errores y versiones para MAPE, ECM, etc.
        df['error'] = (df['total'] - df['promedio_movil']).abs()
        df['errorMAPE'] = np.where(
            df['error'].isna(), 
            np.nan,
            np.where(df['total']==0, 1, df['error']/df['total'])
        )
        df['errorMAPEPrima'] = np.where(
            df['error'].isna(),
            np.nan,
            np.where(df['promedio_movil']==0, 1, df['error']/df['promedio_movil'])
        )
        df['errorECM'] = df['error']**2

        # 4. Agrego todas las métricas de grupo en un solo agg()
        agg = (
            df
            .groupby(['sku','sku_nom','sede'])
            .agg(
                mad=('error','mean'),
                mape=('errorMAPE','mean'),
                mape_prima=('errorMAPEPrima','mean'),
                ecm=('errorECM','mean')
            )
            .reset_index()
        )
        # 5. Calculo el pronóstico (sin shift) para el mes “13”:
        #    rolling(window=n).mean().iloc[-1] == promedio de los últimos n totales
        forecast = (
            df
            .groupby(['sku','sku_nom','sede'])['total']
            .apply(lambda x: x.rolling(window=n).mean().iloc[-1])
            .reset_index(name='promedio_movil')
        )
        # 6. Cojo los datos “constantes” de cada grupo en su última fila histórica
        last = (
            df
            .groupby(['sku','sku_nom','sede'])
            .agg(
                marca_nom=('marca_nom','last'),
                bod       =('bod','last'),
                yyyy      =('yyyy','last')
            )
            .reset_index()
        )
        # 7. Construyo el DataFrame de pronósticos (mes 13) y metadatos
        df_forecast = (
            last
            .merge(forecast, on=['sku','sku_nom','sede'])
            .merge(agg,      on=['sku','sku_nom','sede'])
        )
        df_forecast['mm'] = 13
        df_forecast['total'] = np.nan
        # Campos de error todos NaN en mes 13
        for c in ['error','errorMAPE','errorMAPEPrima','errorECM']:
            df_forecast[c] = np.nan

        # Renombro y ajusto escalas
        df_forecast = df_forecast.rename(columns={'mad':'MAD','ecm':'ECM'})
        df_forecast['MAPE']       = df_forecast['mape'] * 100
        df_forecast['MAPE_Prima'] = df_forecast['mape_prima'] * 100
        df_forecast = df_forecast.drop(columns=['mape','mape_prima'])

        # 8. Concateno todo y ordeno igual que antes
        cols = [
            'yyyy','mm','sku','sku_nom','marca_nom','bod','umd',
            'total','sede','promedio_movil','error','errorMAPE','errorMAPEPrima','errorECM',
            'MAD','MAPE','MAPE_Prima','ECM'
        ]
        df_result = (
            pd.concat([df, df_forecast], ignore_index=True)
            .sort_values(['sku','sku_nom','sede','yyyy','mm'])
            .reset_index(drop=True)
        )[cols]
        return df_result
    
    def promedioMovil_5(n):
        print(f'Calculando pronóstico de promedio móvil n={n}...')
        # 1. Cargo datos y ordeno
        df_demanda = pd.DataFrame(PronosticoMovil.getDataBD())
        df = (
            df_demanda
            .sort_values(['sku','sku_nom','sede','yyyy','mm'])
            .reset_index(drop=True)
        )
        # 2. Promedio móvil (window=n, desplazado 1 mes)
        df['promedio_movil'] = (
            df
            .groupby(['sku','sku_nom','sede'])['total']
            .transform(lambda x: x.rolling(window=n).mean().shift(1))
        )
        # 3. Errores y versiones para MAPE, ECM, etc.
        df['error'] = (df['total'] - df['promedio_movil']).abs()
        df['errorMAPE'] = np.where(
            df['error'].isna(), 
            np.nan,
            np.where(df['total']==0, 1, df['error']/df['total'])
        )
        df['errorMAPEPrima'] = np.where(
            df['error'].isna(),
            np.nan,
            np.where(df['promedio_movil']==0, 1, df['error']/df['promedio_movil'])
        )
        df['errorECM'] = df['error']**2

        # 4. Agrego todas las métricas de grupo en un solo agg()
        agg = (
            df
            .groupby(['sku','sku_nom','sede'])
            .agg(
                mad=('error','mean'),
                mape=('errorMAPE','mean'),
                mape_prima=('errorMAPEPrima','mean'),
                ecm=('errorECM','mean')
            )
            .reset_index()
        )
        # 5. Calculo el pronóstico (sin shift) para el mes “13”:
        #    rolling(window=n).mean().iloc[-1] == promedio de los últimos n totales
        forecast = (
            df
            .groupby(['sku','sku_nom','sede'])['total']
            .apply(lambda x: x.rolling(window=n).mean().iloc[-1])
            .reset_index(name='promedio_movil')
        )
        # 6. Cojo los datos “constantes” de cada grupo en su última fila histórica
        last = (
            df
            .groupby(['sku','sku_nom','sede'])
            .agg(
                marca_nom=('marca_nom','last'),
                bod       =('bod','last'),
                yyyy      =('yyyy','last')
            )
            .reset_index()
        )
        # 7. Construyo el DataFrame de pronósticos (mes 13) y metadatos
        df_forecast = (
            last
            .merge(forecast, on=['sku','sku_nom','sede'])
            .merge(agg,      on=['sku','sku_nom','sede'])
        )
        df_forecast['mm'] = 13
        df_forecast['total'] = np.nan
        # Campos de error todos NaN en mes 13
        for c in ['error','errorMAPE','errorMAPEPrima','errorECM']:
            df_forecast[c] = np.nan

        # Renombro y ajusto escalas
        df_forecast = df_forecast.rename(columns={'mad':'MAD','ecm':'ECM'})
        df_forecast['MAPE']       = df_forecast['mape'] * 100
        df_forecast['MAPE_Prima'] = df_forecast['mape_prima'] * 100
        df_forecast = df_forecast.drop(columns=['mape','mape_prima'])

        # 8. Concateno todo y ordeno igual que antes
        cols = [
            'yyyy','mm','sku','sku_nom','marca_nom','bod','umd',
            'total','sede','precio','promedio_movil','error','errorMAPE','errorMAPEPrima','errorECM',
            'MAD','MAPE','MAPE_Prima','ECM'
        ]
        df_result = (
            pd.concat([df, df_forecast], ignore_index=True)
            .sort_values(['sku','sku_nom','sede','yyyy','mm'])
            .reset_index(drop=True)
        )[cols]
        return df_result