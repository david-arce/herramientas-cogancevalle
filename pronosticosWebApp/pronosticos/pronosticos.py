from pronosticosWebApp.pronosticos.promedioMovil import PronosticoMovil as pm
from pronosticosWebApp.pronosticos.suavizacionExpSimple import PronosticoExpSimple as ses
from pronosticosWebApp.pronosticos.suavizacionExpDoble import PronosticoExpDoble as sed
import pandas as pd

class Pronosticos:
    
    def __init__(self):
        pass
    
    def pronosticos():
        MAD_p3, MAPE_p3, MAPE_prima_p3, ECM_p3, demanda_p3, df_promedio_movil_p3, lista_pronostico_p3, lista_pronosticos_redondeo_movil_p3, datos_excel_p3 = pm.promedioMovil_3(3)
        MAD_p4, MAPE_p4, MAPE_prima_p4, ECM_p4, demanda_p4, df_promedio_movil_p4, lista_pronosticos_p4, lista_pronosticos_redondeo_p4, datos_excel_p4 = pm.promedioMovil_4(4)
        MAD_p5, MAPE_p5, MAPE_prima_p5, ECM_p5, demanda_p5, df_promedio_movil_p5, lista_pronosticos_p5, lista_pronosticos_redondeo_p5, datos_excel_p5 = pm.promedioMovil_5(5)
        
        items, proveedor, productos, sede = pm.productos()
        MAD1, MAPE1, MAPE_prima1, ECM1, df_pronostico_ses, lista_pronostico_ses, lista_pronosticos_redondeo_ses = ses.pronosticoExpSimple(0.5)
        MAD2, MAPE2, MAPE_prima2, ECM2, df_pronostico_sed, lista_pronostico_sed, lista_pronosticos_redondeo_sed = sed.pronosticoExpDoble(0.5, 0.5, 1)

        mejor_ECM = []
        origen_ECM = []
        for valores in zip(ECM_p3, ECM_p4, ECM_p5, ECM1, ECM2):
            min_valor = min(valores)
            mejor_ECM.append(min_valor)
            indice_origen = valores.index(min_valor)
            origen_ECM.append(indice_origen)

        #asigna a la lista de pronostico seleccionado el mejor pronostico segun la lista orgien_ECM
        pronostico_seleccionado = [] 
        for item in origen_ECM:
            if item == 0:
                pronostico_seleccionado.append('Promedio movil n=3')
            elif item == 1:
                pronostico_seleccionado.append('Promedio movil n=4')
            elif item == 2:
                pronostico_seleccionado.append('Promedio movil n=5')
            elif item == 3:
                pronostico_seleccionado.append('SES')
            else:
                pronostico_seleccionado.append('SED')
            
        # lista_pronostico_ses = df_pronostico_ses.iloc[:,-1].values.tolist()
        # lista_pronostico_sed = df_pronostico_sed.iloc[:,-1].values.tolist()
        i = 0
        pronostico_final=[]
        for valores in zip(lista_pronostico_p3, lista_pronosticos_p4, lista_pronosticos_p5, lista_pronostico_ses, lista_pronostico_sed):
            pronostico_final.append(round((valores[origen_ECM[i]]), 2))
            i += 1
        i = 0
        pronostico_final_redondeado=[]
        for valores in zip(lista_pronosticos_redondeo_movil_p3, lista_pronosticos_redondeo_p4, lista_pronosticos_redondeo_p5,  lista_pronosticos_redondeo_ses, lista_pronosticos_redondeo_sed):
            pronostico_final_redondeado.append(valores[origen_ECM[i]])
            i += 1
        
        i = 0
        MAD_final=[]
        for valores in zip(MAD_p3, MAD_p4, MAD_p5, MAD1, MAD2):
            MAD_final.append(round((valores[origen_ECM[i]]), 2))
            i += 1
        i = 0
        MAPE_final=[]
        for valores in zip(MAPE_p3, MAPE_p4, MAPE_p5, MAPE1, MAPE2):
            MAPE_final.append(round((valores[origen_ECM[i]]),2))
            i += 1
        i = 0
        MAPE_PRIMA_final=[]
        for valores in zip(MAPE_prima_p3, MAPE_prima_p4, MAPE_prima_p5, MAPE_prima1, MAPE_prima2):
            MAPE_PRIMA_final.append(round((valores[origen_ECM[i]]),2))
            i += 1
        i = 0
        ECM_final=[]
        for valores in zip(ECM_p3, ECM_p4, ECM_p5, ECM1, ECM2):
            ECM_final.append(round((valores[origen_ECM[i]]),2))
            i += 1
        
        # serie = pd.Series(pronostico_final, index=productos) #serie sin el nombre las columnas
        # serie = pd.concat([pd.Series(productos), pd.Series(pronostico_final)], axis=1)
        # serie.columns = ["Producto", "Mejor pronostico"]
        
        df_pronosticos = pd.DataFrame({"Items": items, "Proveedor": proveedor, "Productos": productos, "Sede": sede, "MAD": MAD_final, "MAPE": MAPE_final, "MAPE_PRIMA": MAPE_PRIMA_final,"ECM":ECM_final, "Pronostico": pronostico_final, "Pronostico_2_meses": pronostico_final_redondeado, "Pronostico_seleccionado": pronostico_seleccionado})
        
        # Especifica la ruta del archivo Excel donde deseas guardar el DataFrame
        # ruta_archivo_excel = 'Pronosticos.xlsx'

        # # Usa el método to_excel() para guardar el DataFrame en el archivo Excel
        # df_pronosticos.to_excel(ruta_archivo_excel, index=False)  # Si no deseas incluir el índice en el archivo Excel, puedes establecer index=False
        
        return demanda_p3, df_promedio_movil_p3, df_promedio_movil_p4, df_promedio_movil_p5, df_pronostico_ses, df_pronostico_sed, df_pronosticos

    def prueba():
        mejor_ECM, origen_ECM, serie, MAD, MAPE, MAPE_prima, ECM, demanda, promedio_movil, lista_pronostico_movil, datos_excel, MAD1, MAPE1, MAPE_prima1, ECM1, df_pronostico_ses, MAD2, MAPE2, MAPE_prima2, ECM2, df_pronostico_sed, pronostico_final, MAD_final, MAPE_final, MAPE_PRIMA_final, ECM_final, pronostico_seleccionado, df_pronosticos, pronostico_final_redondeado = Pronosticos.pronosticos()
        items, proveedor, productos, sede = pm.productos()
        
        df = pd.DataFrame({"Items": items, "Proveedor": proveedor, "Productos": productos, "Sede": sede, "MAD": MAD_final, "MAPE": MAPE_final, "MAPE_PRIMA": MAPE_PRIMA_final,"ECM":ECM_final, "Mejor pronostico": pronostico_final, "Pronostico_redondeo": pronostico_final_redondeado, "Pronostico Seleccionado": pronostico_seleccionado})
        
        # Especifica la ruta del archivo Excel donde deseas guardar el DataFrame
        ruta_archivo_excel = 'Pronosticos.xlsx'

        # Usa el método to_excel() para guardar el DataFrame en el archivo Excel
        df.to_excel(ruta_archivo_excel, index=False)  # Si no deseas incluir el índice en el archivo Excel, puedes establecer index=False
        
# Pronosticos.pronosticos()

