from pronosticosWebApp.pronosticos.promedioMovil import PronosticoMovil as pm
from pronosticosWebApp.pronosticos.suavizacionExpSimple import (
    PronosticoExpSimple as ses,
)
from pronosticosWebApp.pronosticos.suavizacionExpDoble import PronosticoExpDoble as sed
import pandas as pd
import math
from pronosticosWebApp.pronosticos.promedioMovil import PronosticoMovil as pm


class Pronosticos:

    def __init__(self):
        pass

    def datos():
        df_demanda = pd.DataFrame(pm.getDataBD())  # Se convierten los productos en un DataFrame de pandas para su manipulación
        id = df_demanda["id"].tolist()
        item = df_demanda["producto_c15"].tolist()
        proveedor = df_demanda["proveedor"].tolist()
        producto = df_demanda["nombre_c100"].tolist()
        bodega = df_demanda["bodega_c5"].tolist()
        codigo = df_demanda["codcmc_c50"].tolist()
        unimed = df_demanda["unimed_c4"].tolist()
        precio = df_demanda["precio_unitario_n20"].tolist()
        sede = df_demanda["sede"].tolist()
        del df_demanda
        return id, item, proveedor, producto, bodega, codigo, unimed, precio, sede

    def pronosticos():
        (
            MAD_p3,
            MAPE_p3,
            MAPE_prima_p3,
            ECM_p3,
            demanda_p3,
            df_promedio_movil_p3,
            lista_pronostico_p3,
        ) = pm.promedioMovil_3(3)
        (
            MAD_p4,
            MAPE_p4,
            MAPE_prima_p4,
            ECM_p4,
            df_promedio_movil_p4,
            lista_pronosticos_p4,
        ) = pm.promedioMovil_4(4)
        (
            MAD_p5,
            MAPE_p5,
            MAPE_prima_p5,
            ECM_p5,
            df_promedio_movil_p5,
            lista_pronosticos_p5,
        ) = pm.promedioMovil_5(5)

        # id, items, proveedor, productos, sede = pm.productos()
        (
            MAD1,
            MAPE1,
            MAPE_prima1,
            ECM1,
            df_pronostico_ses,
            lista_pronostico_ses,
        ) = ses.pronosticoExpSimple(0.5)
        (
            MAD2,
            MAPE2,
            MAPE_prima2,
            ECM2,
            df_pronostico_sed,
            lista_pronostico_sed,
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

        # extraer los ultimos 4 meses de la demanda
        df_ultimos_4meses = demanda_p3.iloc[:,8:-1]
        # Iterar por el DataFrame para verificar filas con todos ceros
        # Iterar sobre el DataFrame y la lista de pronósticos al mismo tiempo
        for index, (row, pronostico) in enumerate(zip(df_ultimos_4meses.iterrows(), pronostico_final)):
            _, row_data = row  # Extrae la fila actual de row
            if (row_data[:-1] == 0).all():  # Verifica si todas las columnas de meses tienen cero
                pronostico_final[index] = 0  # Cambia el pronóstico a 0 si la fila tiene todos ceros
    
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

        id, item, proveedor, producto, bodega, codigo, unimed, precio, sede = (
            Pronosticos.datos()
        )
        
        df_demanda = pd.DataFrame(pm.getDataBD())
        # extraer inventario
        inventario = df_demanda['inventario'].tolist()
        # extraer pronostico
        listPronostico = pronostico_final
        
        cantidad = []
        for i in range(len(inventario)):
            cantidad.append(listPronostico[i] - inventario[i])

        # nueva lista con la cantidad multiplicada por 2
        cantidadx2 = []
        for i in range(len(cantidad)):
            prox2 = listPronostico[i] * 2
            cantidadx2.append(prox2 - inventario[i])
            
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
                "cantidad_2_meses": cantidadx2, #10
                "precio": precio, #11
            }
        )
        
        # Agregar un cero a la izquierda a todos los datos de la columna 'bodega'
        df_pronosticos['bodega'] = df_pronosticos['bodega'].apply(lambda x: str(x).zfill(len(str(x)) + 1))
        
        # df_pronosticos = pd.DataFrame({"id": id, "Items": item, "Proveedor": proveedor, "Productos": productos, "Sede": sede, "MAD": MAD_final, "MAPE": MAPE_final, "MAPE_PRIMA": MAPE_PRIMA_final,"ECM":ECM_final, "Pronostico": pronostico_final, "Pronostico_2_meses": pronostico_final_redondeado, "Pronostico_seleccionado": pronostico_seleccionado})
        
        return (
            demanda_p3,
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
        df.to_excel(
            ruta_archivo_excel, index=False
        )  # Si no deseas incluir el índice en el archivo Excel, puedes establecer index=False


# Pronosticos.pronosticos()
