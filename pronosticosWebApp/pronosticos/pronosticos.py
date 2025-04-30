import numpy as np
from pronosticosWebApp.pronosticos.promedioMovil import PronosticoMovil as pm
from pronosticosWebApp.pronosticos.suavizacionExpSimple import (
    PronosticoExpSimple as ses,
)
from pronosticosWebApp.pronosticos.suavizacionExpDoble import PronosticoExpDoble as sed
import pandas as pd
import math
from pronosticosWebApp.pronosticos.promedioMovil import PronosticoMovil as pm
import statistics


class Pronosticos:

    def __init__(self):
        pass

    def datos():
        df_demanda = pd.DataFrame(pm.getDataBD())  # Se convierten los productos en un DataFrame de pandas para su manipulación
        # id = df_demanda["id"].tolist()
        item = df_demanda["sku"].tolist()
        proveedor = df_demanda["marca_nom"].tolist()
        producto = df_demanda["sku_nom"].tolist()
        bodega = df_demanda["bod"].tolist()
        codigo = df_demanda["sku"].tolist()
        unimed = df_demanda["umd"].tolist()
        # precio = df_demanda["precio_unitario_n20"].tolist()
        sede = df_demanda["sede"].tolist()
        del df_demanda
        return  item, proveedor, producto, bodega, codigo, unimed, sede

    def pronosticos():
        
        (
            MAD_p3,
            MAPE_p3,
            MAPE_prima_p3,
            ECM_p3,
            item,
            proveedor,
            producto,
            bodega,
            codigo,
            unimed,
            sede,
            df_pronostico_p3,
            df_demanda
        ) = pm.promedioMovil_3(3)
        
        # df_pronostico_p3.to_excel("df_pronostico_p3.xlsx", index=False)
        
        (
            MAD_p4,
            MAPE_p4,
            MAPE_prima_p4,
            ECM_p4,
            df_pronostico_p4
        ) = pm.promedioMovil_4(4)
        (
            MAD_p5,
            MAPE_p5,
            MAPE_prima_p5,
            ECM_p5,
            df_pronostico_p5
        ) = pm.promedioMovil_5(5)

        # id, items, proveedor, productos, sede = pm.productos()
        (
            MAD1,
            MAPE1,
            MAPE_prima1,
            ECM1,
            df_pronostico_ses
        ) = ses.pronosticoExpSimple(0.5)
        (
            MAD2,
            MAPE2,
            MAPE_prima2,
            ECM2,
            df_pronostico_sed
        ) = sed.pronosticoExpDoble(0.5, 0.5, 1)

        mejor_ECM = []
        origen_ECM = []
        for valores in zip(ECM_p3, ECM_p4, ECM_p5, ECM1, ECM2):
            min_valor = min(valores)
            mejor_ECM.append(min_valor)
            indice_origen = valores.index(min_valor)
            origen_ECM.append(indice_origen)

        # asigna a la lista de pronostico seleccionado el mejor pronostico segun la lista orgien_ECM
        pronostico_seleccionado = []
        for item in origen_ECM:
            if item == 0:
                pronostico_seleccionado.append("Promedio movil n=3")
            elif item == 1:
                pronostico_seleccionado.append("Promedio movil n=4")
            elif item == 2:
                pronostico_seleccionado.append("Promedio movil n=5")
            elif item == 3:
                pronostico_seleccionado.append("SES")
            else:
                pronostico_seleccionado.append("SED")

        # obtener una lista de los pronosticos por cada dataframe
        # retorna una lista de pronosticos del promedio movil que está en la columna llamanda 'promedio_movil'
        lista_pronostico_p3 = df_pronostico_p3[df_pronostico_p3['mm'] == 13]["promedio_movil"].dropna().tolist()
        lista_pronosticos_p4 = df_pronostico_p4[df_pronostico_p4['mm'] == 13]["promedio_movil"].dropna().tolist()
        lista_pronosticos_p5 = df_pronostico_p5[df_pronostico_p5['mm'] == 13]["promedio_movil"].dropna().tolist()
        lista_pronostico_ses = df_pronostico_ses[df_pronostico_ses['mm'] == 13]["pronostico_ses"].dropna().tolist()
        lista_pronostico_sed = df_pronostico_sed[df_pronostico_sed['mm'] == 13]["pronostico_sed"].dropna().tolist()
        
        i = 0
        pronostico_final = []
        for valores in zip(
            lista_pronostico_p3,
            lista_pronosticos_p4,
            lista_pronosticos_p5,
            lista_pronostico_ses,
            lista_pronostico_sed,
        ):    
            pronostico_final.append(math.ceil(valores[origen_ECM[i]]))
            i += 1
        
        # Claves únicas para agrupar (puedes agregar más si es necesario)
        claves = ['sku', 'sede']

        # Crear un índice para llevar la cuenta del pronóstico
        index_pronostico = 0

        # Agrupar el DataFrame como está, sin reordenar
        for _, grupo in df_demanda.groupby(claves):
            # Tomar los últimos 4 registros (ya está ordenado)
            ultimos_4 = grupo.tail(4)
            # Verificar si el total es cero en todos los últimos 4
            if (ultimos_4['total'] == 0).all():
                # Asignar 0 a la posición correspondiente del pronóstico
                pronostico_final[index_pronostico] = 0
            
            # Aumentar el índice (1 pronóstico por grupo)
            index_pronostico += 1
        
        # quitar ultima columna a la demanda_p3
        # demanda = demanda.iloc[:, :-1]
        
        # # extraer los ultimos 4 meses de la demanda
        # df_ultimos_4meses = demanda.iloc[:,8:]
        # # Iterar por el DataFrame para verificar filas con todos ceros
        # # Iterar sobre el DataFrame y la lista de pronósticos al mismo tiempo
        # for index, (row, pronostico) in enumerate(zip(df_ultimos_4meses.iterrows(), pronostico_final)):
        #     _, row_data = row  # Extrae la fila actual de row
        #     if (row_data[:-1] == 0).all():  # Verifica si todas las columnas de meses tienen cero
        #         pronostico_final[index] = 0  # Cambia el pronóstico a 0 si la fila tiene todos ceros
        
        i = 0
        MAD_final = []
        for valores in zip(MAD_p3, MAD_p4, MAD_p5, MAD1, MAD2):
            MAD_final.append(round((valores[origen_ECM[i]]), 2))
            i += 1
        i = 0
        MAPE_final = []
        for valores in zip(MAPE_p3, MAPE_p4, MAPE_p5, MAPE1, MAPE2):
            MAPE_final.append(round((valores[origen_ECM[i]]), 2))
            i += 1
        i = 0
        MAPE_PRIMA_final = []
        for valores in zip(
            MAPE_prima_p3, MAPE_prima_p4, MAPE_prima_p5, MAPE_prima1, MAPE_prima2
        ):
            MAPE_PRIMA_final.append(round((valores[origen_ECM[i]]), 2))
            i += 1
        i = 0
        ECM_final = []
        for valores in zip(ECM_p3, ECM_p4, ECM_p5, ECM1, ECM2):
            ECM_final.append(round((valores[origen_ECM[i]]), 2))
            i += 1

        # id, item, proveedor, producto, bodega, codigo, unimed, precio, sede = (
        #     Pronosticos.datos()
        # )
        
        df_demanda = pd.DataFrame(pm.getDataBD())
        # extraer inventario
        inventario = df_demanda['inventario'].tolist()
        
        # Cantidad a comprar para cada producto por 1 mes
        cantidad = []
        for i in range(len(inventario)):
            cantidad.append(pronostico_final[i] - inventario[i])

        # nueva lista con la cantidad multiplicada por 2
        cantidadx2 = []
        for i in range(len(cantidad)):
            prox2 = pronostico_final[i] * 2
            cantidadx2.append(prox2 - inventario[i])

        '''
        # extraer tiempo de entrega
        tiempo_entrega = df_demanda['tiempo_entrega'].tolist()
        # extraer desviación estándar del tiempo de reposición
        desviacion_tiempo_reposicion = df_demanda['desviación_te'].tolist()
       
        z = 1.959
        dias_inventario = []
        dias_inventario_final = []
        cantidadx2 = []
        lis_stock = []
        # calculo del stock de seguridad
        for index, pronostico in enumerate(pronostico_seleccionado):
            if 'Promedio movil n=3' in pronostico:
                error_pronostico = np.abs((df_promedio_movil_p3.iloc[index, 3:12].values - demanda.iloc[index, 3:12].values)).tolist()
                # desviación estandar de una muestra
                desviacion_estandar = np.std(error_pronostico, ddof=1)
                stock = z * desviacion_estandar * math.sqrt(tiempo_entrega[index])
                list_moda_demanda = (demanda.iloc[index, 3:12].values.tolist())
                moda_demanda = statistics.mode(list_moda_demanda)
                if pronostico_final[index] == 0 or moda_demanda == 0:
                    cantidadx2.append(math.ceil(stock + pronostico_final[index] - inventario[index]))
                else:
                    cantidadx2.append(math.ceil(stock + pronostico_final[index] - inventario[index]))
                promedio_demanda=(demanda.iloc[index, 3:12].mean())
                promedio_demanda = round(promedio_demanda)
                if promedio_demanda != 0:
                    dias_inventario.append(round((stock / promedio_demanda) * 30))
                    # extraer el valor que se acaba de añadir a la lista dias_inventario
                else:
                    dias_inventario.append(0)
                if dias_inventario[-1] > 30:
                    cantidadx2[-1] = math.ceil(promedio_demanda + pronostico_final[index] - inventario[index])
                if promedio_demanda != 0:
                    dias_inventario_final.append(round((cantidadx2[-1] / promedio_demanda) * 30))
                else:
                    dias_inventario_final.append(0)
                lis_stock.append(stock)
            elif 'Promedio movil n=4' in pronostico:
                error_pronostico = np.abs((df_promedio_movil_p4.iloc[index, 4:12].values - demanda.iloc[index, 4:12].values)).tolist()
                desviacion_estandar = np.std(error_pronostico, ddof=1)
                stock = z * desviacion_estandar * math.sqrt(tiempo_entrega[index])
                list_moda_demanda = (demanda.iloc[index, 4:12].values.tolist())
                moda_demanda = statistics.mode(list_moda_demanda)
                if pronostico_final[index] == 0 or moda_demanda == 0:
                    cantidadx2.append(math.ceil(stock + pronostico_final[index] - inventario[index]))
                else:
                    cantidadx2.append(math.ceil(stock + pronostico_final[index] - inventario[index]))
                promedio_demanda=(demanda.iloc[index, 4:12].mean())
                promedio_demanda = round(promedio_demanda)
                if promedio_demanda != 0:
                    # new_stock = cantidadx2[-1]
                    dias_inventario.append(round((stock / promedio_demanda) * 30))
                else:
                    dias_inventario.append(0)
                if dias_inventario[-1] > 30:
                    cantidadx2[-1] = math.ceil(promedio_demanda + pronostico_final[index] - inventario[index])
                if promedio_demanda != 0:
                    dias_inventario_final.append(round((cantidadx2[-1] / promedio_demanda) * 30))
                else:
                    dias_inventario_final.append(0)
                lis_stock.append(stock) 
            elif 'Promedio movil n=5' in pronostico:
                error_pronostico = np.abs((df_promedio_movil_p5.iloc[index, 5:12].values - demanda.iloc[index, 5:12].values)).tolist()
                desviacion_estandar = np.std(error_pronostico, ddof=1)
                stock = z * desviacion_estandar * math.sqrt(tiempo_entrega[index])
                list_moda_demanda = (demanda.iloc[index, 5:12].values.tolist())
                moda_demanda = statistics.mode(list_moda_demanda)
                if pronostico_final[index] == 0 or moda_demanda == 0:
                    # stock = 0
                    cantidadx2.append(math.ceil(stock + pronostico_final[index] - inventario[index]))
                else:
                    cantidadx2.append(math.ceil(stock + pronostico_final[index] - inventario[index]))
                promedio_demanda=(demanda.iloc[index, 5:12].mean())
                promedio_demanda = round(promedio_demanda)
                if promedio_demanda != 0:
                    # new_stock = cantidadx2[-1]
                    dias_inventario.append(round((stock / promedio_demanda) * 30))
                else:
                    dias_inventario.append(0)
                if dias_inventario[-1] > 30:
                    cantidadx2[-1] = math.ceil(promedio_demanda + pronostico_final[index] - inventario[index])
                if promedio_demanda != 0:
                    dias_inventario_final.append(round((cantidadx2[-1] / promedio_demanda) * 30))
                else:
                    dias_inventario_final.append(0)
                lis_stock.append(stock)
            elif 'SES' in pronostico:
                error_pronostico = np.abs((df_pronostico_ses.iloc[index, 3:12].values - demanda.iloc[index, 3:12].values)).tolist()
                desviacion_estandar = np.std(error_pronostico, ddof=1)
                stock = z * desviacion_estandar * math.sqrt(tiempo_entrega[index])
                list_moda_demanda = (demanda.iloc[index, 3:12].values.tolist())
                moda_demanda = statistics.mode(list_moda_demanda)
                if pronostico_final[index] == 0 or moda_demanda == 0:
                    cantidadx2.append(math.ceil(stock + pronostico_final[index] - inventario[index]))
                else:
                    cantidadx2.append(math.ceil(stock + pronostico_final[index] - inventario[index]))
                promedio_demanda=(demanda.iloc[index, 3:12].mean())
                promedio_demanda = round(promedio_demanda)
                if promedio_demanda != 0:
                    # new_stock = cantidadx2[-1]
                    dias_inventario.append(round((stock / promedio_demanda) * 30))
                else:
                    dias_inventario.append(0)
                if dias_inventario[-1] > 30:
                    cantidadx2[-1] = math.ceil(promedio_demanda + pronostico_final[index] - inventario[index])
                if promedio_demanda != 0:
                    dias_inventario_final.append(round((cantidadx2[-1] / promedio_demanda) * 30))
                else:
                    dias_inventario_final.append(0)
                lis_stock.append(stock)
            else:
                error_pronostico = np.abs((df_pronostico_sed.iloc[index, 3:12].values - demanda.iloc[index, 3:12].values)).tolist()
                desviacion_estandar = np.std(error_pronostico, ddof=1)
                stock = z * desviacion_estandar * math.sqrt(tiempo_entrega[index])
                list_moda_demanda = (demanda.iloc[index, 3:12].values.tolist())
                moda_demanda = statistics.mode(list_moda_demanda)
                if pronostico_final[index] == 0 or moda_demanda == 0:
                    cantidadx2.append(math.ceil(stock + pronostico_final[index] - inventario[index]))
                else:
                    cantidadx2.append(math.ceil(stock + pronostico_final[index] - inventario[index]))
                promedio_demanda=(demanda.iloc[index, 3:12].mean())
                promedio_demanda = round(promedio_demanda)
                if promedio_demanda != 0:
                    # new_stock = cantidadx2[-1]
                    dias_inventario.append(round((stock / promedio_demanda) * 30))
                else:
                    dias_inventario.append(0)
                if dias_inventario[-1] > 30:
                    cantidadx2[-1] = math.ceil(promedio_demanda + pronostico_final[index] - inventario[index])
                if promedio_demanda != 0:
                    dias_inventario_final.append(round((cantidadx2[-1] / promedio_demanda) * 30))
                else:
                    dias_inventario_final.append(0)
                lis_stock.append(stock)
        '''
        df_pronosticos = pd.DataFrame(
            {   
                "id": id, #1
                "bodega": bodega, #2
                "item": item, #3
                "codigo": codigo, #4
                "producto": producto, #5
                "unimed": unimed, #6
                "lotepro": ".", #7
                "proveedor": proveedor, #7
                "sede": sede, #8
                "cantidad": cantidad, #9
                "stock_de_seguridad": cantidadx2, #10
                "precio": precio, #11
            }
        )
        
        # Agregar un cero a la izquierda a todos los datos de la columna 'bodega'
        df_pronosticos['bodega'] = df_pronosticos['bodega'].apply(lambda x: str(x).zfill(len(str(x)) + 1))
        
        # Especifica la ruta del archivo Excel donde deseas guardar el DataFrame
        # ruta_archivo_excel = "Pronosticos.xlsx"

        # # Usa el método to_excel() para guardar el DataFrame en el archivo Excel
        # df_pronosticos.to_excel(ruta_archivo_excel, index=False) 
        
        return (
            demanda,
            df_promedio_movil_p3,
            df_promedio_movil_p4,
            df_promedio_movil_p5,
            df_pronostico_ses,
            df_pronostico_sed,
            df_pronosticos,
        )

    def prueba():
        (
            pronostico_seleccionado,
            pronostico_final_redondeado,
        ) = Pronosticos.pronosticos()
        items, proveedor, productos, sede = pm.productos()

        df = pd.DataFrame(
            {
                "Items": items,
                "Proveedor": proveedor,
                "Productos": productos,
                "Sede": sede,
                "Pronostico_redondeo": pronostico_final_redondeado,
                "Pronostico Seleccionado": pronostico_seleccionado,
            }
        )

        # Especifica la ruta del archivo Excel donde deseas guardar el DataFrame
        ruta_archivo_excel = "Pronosticos.xlsx"

        # Usa el método to_excel() para guardar el DataFrame en el archivo Excel
        df.to_excel(ruta_archivo_excel, index=False)  # Si no deseas incluir el índice en el archivo Excel, puedes establecer index=False


# Pronosticos.pronosticos()
