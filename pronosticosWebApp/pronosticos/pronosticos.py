from pronosticosWebApp.pronosticos.promedioMovil import PronosticoMovil as pm
from pronosticosWebApp.pronosticos.suavizacionExpSimple import PronosticoExpSimple as ses
from pronosticosWebApp.pronosticos.suavizacionExpDoble import PronosticoExpDoble as sed
import pandas as pd

class Pronosticos:
    
    def __init__(self):
        pass
    
    def pronosticos():
        MAD, MAPE, MAPE_prima, ECM, df_demanda, df_promedio_movil, lista_pronostico_movil, lista_pronosticos_redondeo_movil, datos_excel = pm.promedioMovil(5) #se hace el llamado a la función de pronosticoMovil
        items, proveedor, productos, sede = pm.productos()
        MAD1, MAPE1, MAPE_prima1, ECM1, df_pronostico_ses, lista_pronostico_ses, lista_pronosticos_redondeo_ses = ses.pronosticoExpSimple(0.5)
        MAD2, MAPE2, MAPE_prima2, ECM2, df_pronostico_sed, lista_pronostico_sed, lista_pronosticos_redondeo_sed = sed.pronosticoExpDoble(0.5, 0.5, 1)

        mejor_ECM = []
        origen_ECM = []
        for valores in zip(ECM, ECM1, ECM2):
            min_valor = min(valores)
            mejor_ECM.append(min_valor)
            indice_origen = valores.index(min_valor)
            origen_ECM.append(indice_origen)

        #asigna a la lista de pronostico seleccionado el mejor pronostico segun la lista orgien_ECM
        pronostico_seleccionado = []
        for item in origen_ECM:
            if item == 0:
                pronostico_seleccionado.append('Promedio movil')
            elif item == 1:
                pronostico_seleccionado.append('SES')
            else:
                pronostico_seleccionado.append('SED')
            
        i = 0
        pronostico_final=[]
        for valores in zip(lista_pronostico_movil, lista_pronostico_ses, lista_pronostico_sed):
            pronostico_final.append(round((valores[origen_ECM[i]])))
            i += 1
        i = 0
        pronostico_final_redondeado=[]
        for valores in zip(lista_pronosticos_redondeo_movil, lista_pronosticos_redondeo_ses, lista_pronosticos_redondeo_sed):
            pronostico_final_redondeado.append(valores[origen_ECM[i]])
            i += 1
        
        i = 0
        MAD_final=[]
        for valores in zip(MAD, MAD1, MAD2):
            MAD_final.append(round((valores[origen_ECM[i]]), 2))
            i += 1
        i = 0
        MAPE_final=[]
        for valores in zip(MAPE, MAPE1, MAPE2):
            MAPE_final.append(round((valores[origen_ECM[i]]),2))
            i += 1
        i = 0
        MAPE_PRIMA_final=[]
        for valores in zip(MAPE_prima, MAPE_prima1, MAPE_prima2):
            MAPE_PRIMA_final.append(round((valores[origen_ECM[i]]),2))
            i += 1
        i = 0
        ECM_final=[]
        for valores in zip(ECM, ECM1, ECM2):
            ECM_final.append(round((valores[origen_ECM[i]]),2))
            i += 1
        
        # serie = pd.Series(pronostico_final, index=productos) #serie sin el nombre las columnas
        serie = pd.concat([pd.Series(productos), pd.Series(pronostico_final)], axis=1)
        serie.columns = ["Producto", "Mejor pronostico"]
        
        df_pronosticos = pd.DataFrame({"Items": items, "Proveedor": proveedor, "Productos": productos, "Sede": sede, "MAD": MAD_final, "MAPE": MAPE_final, "MAPE_PRIMA": MAPE_PRIMA_final,"ECM":ECM_final, "Pronostico": pronostico_final, "Pronostico_2_meses": pronostico_final_redondeado, "Pronostico_seleccionado": pronostico_seleccionado})
        
        # Especifica la ruta del archivo Excel donde deseas guardar el DataFrame
        # ruta_archivo_excel = 'Pronosticos.xlsx'

        # # Usa el método to_excel() para guardar el DataFrame en el archivo Excel
        # df_pronosticos.to_excel(ruta_archivo_excel, index=False)  # Si no deseas incluir el índice en el archivo Excel, puedes establecer index=False
        
        return df_demanda, df_promedio_movil, df_pronostico_ses, df_pronostico_sed, df_pronosticos

    def prueba():
        mejor_ECM, origen_ECM, serie, MAD, MAPE, MAPE_prima, ECM, demanda, promedio_movil, lista_pronostico_movil, datos_excel, MAD1, MAPE1, MAPE_prima1, ECM1, df_pronostico_ses, MAD2, MAPE2, MAPE_prima2, ECM2, df_pronostico_sed, pronostico_final, MAD_final, MAPE_final, MAPE_PRIMA_final, ECM_final, pronostico_seleccionado, df_pronosticos, pronostico_final_redondeado = Pronosticos.pronosticos()
        items, proveedor, productos, sede = pm.productos()
        
        df = pd.DataFrame({"Items": items, "Proveedor": proveedor, "Productos": productos, "Sede": sede, "MAD": MAD_final, "MAPE": MAPE_final, "MAPE_PRIMA": MAPE_PRIMA_final,"ECM":ECM_final, "Mejor pronostico": pronostico_final, "Pronostico_redondeo": pronostico_final_redondeado, "Pronostico Seleccionado": pronostico_seleccionado})
        
        # Especifica la ruta del archivo Excel donde deseas guardar el DataFrame
        ruta_archivo_excel = 'Pronosticos.xlsx'

        # Usa el método to_excel() para guardar el DataFrame en el archivo Excel
        df.to_excel(ruta_archivo_excel, index=False)  # Si no deseas incluir el índice en el archivo Excel, puedes establecer index=False
        
# Pronosticos.pronosticos()

