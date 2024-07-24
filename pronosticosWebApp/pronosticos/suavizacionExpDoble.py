import pandas as pd
import numpy as np
import time
from pronosticosWebApp.models import Productos

class PronosticoExpDoble:
    
    def __init__(self):
        pass
    
    def pronosticoExpDoble(alpha, beta, p):
        productos_data = list(Productos.objects.values()) # Se obtienen los productos de la base de datos en forma de lista
        df_demanda = pd.DataFrame(productos_data) # Se convierten los productos en un DataFrame de pandas para su manipulación
        print('espere un momento...')
        meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    
        # Filtrar columnas que contienen meses (sin importar mayúsculas o minúsculas)
        columnas_meses = [col for col in df_demanda.columns if any(mes in col.lower() for mes in meses)]
        cantidadMeses = len(columnas_meses)
        
        # Seleccionar solo las columnas de meses
        demanda = df_demanda[columnas_meses].copy()
        
        valores_demanda = demanda.values.flatten().tolist()
        
        #CALCULO DEL VALOR ATENUADO
        #alpha*Dt+(1-alpha)*(At-1+Tt-1) valor atenuado
        #beta*(At-At-1)+(1-beta)*Tt-1 valor de la tendencia
        valores_tendencia = []
        valores_atenuado = []
        for i in range(0, len(valores_demanda), cantidadMeses):
            grupo = valores_demanda[i:i+(cantidadMeses)]
            valores_tendencia.append(0)
            for item in range(len(grupo)):
                if item == 0:
                    valores_atenuado.append(grupo[item])
                else:
                    valores_atenuado.append(alpha*grupo[item] + (1-alpha)*(valores_atenuado[-1] + valores_tendencia[-1]))
                    valores_tendencia.append(beta*(valores_atenuado[-1] - valores_atenuado[-2]) + (1-beta)*valores_tendencia[-1])
    
        # print('valores atenuado: ',valores_atenuado[:30])
        # print('valores tendencia: ', valores_tendencia[:30])
    
        #CALCULO DEL PRONOSTICO EXPONENTIAL DOBLE
        #Ft = At + p*Tt
        pronostico_sed = [valores_atenuado[i] + p * valores_tendencia[i] for i in range(len(valores_atenuado))]
        # print('pronostico_sed: ',pronostico_sed[:20])
        
        # Extraer valores del mes siguiente para agregar al DataFrame demanda
        valores_mes_siguiente = pronostico_sed[cantidadMeses-1::cantidadMeses]
        # print(valores_mes_siguiente[:20])

        # Asignar los valores del pronostico al siguiente mes y se agrega al dataframe demanda
        demanda['MAYO_2'] = valores_mes_siguiente
        
        lista_nombre_columnas = demanda.columns.to_list()[1:]  #lista de los nombres de las columnas, es decir, los meses
        # Dividir la lista de valores en segmentos 
        segmentos_valores = [pronostico_sed[i:i+(cantidadMeses)] for i in range(0, len(pronostico_sed), cantidadMeses)]
        # Crear un DataFrame con los segmentos de valores y los nombres de las columnas 
        df_pronostico_sed = pd.DataFrame(segmentos_valores, columns=lista_nombre_columnas)
        # print(df_pronostico_sed)
        
        #lista de pronosticos para el siguiente mes
        lista_pronosticos = demanda.iloc[:, cantidadMeses].values.tolist()
        #lista de pronosticos redondeado
        lista_pronosticos_redondeo = [round(i*2) for i in lista_pronosticos]
        
        errores, erroresMape, erroresMapePrima, erroresCuadraticoMedio = [], [], [], []
        MAD=[] #mean absolute deviation
        MAPE=[] #mean absolute percentage error
        MAPE_prima=[] #mean absolute percentage error prima
        EMC=[] #error cuadratico medio

        pronostico_doble_listOflist = [pronostico_sed[i:i+cantidadMeses] for i in range(0, len(pronostico_sed), cantidadMeses)]
        #guarda los errores en una lista 
        for i in demanda.index:
            for j in range(1, cantidadMeses):
                errores.append(demanda.iloc[i, j] - pronostico_doble_listOflist[i][j-1])
        erroresAbs = np.abs(errores) #errores absolutos |e|

        total_meses_pronostico = cantidadMeses - 1 #total de meses a pronosticar menos el siguiente
        #CALCULO DEL MAD(MEAN ABSOLUTE DEVIATION) 
        MAD = [np.mean(erroresAbs[i:i+total_meses_pronostico]) for i in range(0, len(erroresAbs), total_meses_pronostico)]
        # print("MAD: ", MAD[:5])
        
        #CALCULO DEL MAPE(MEAN ABSOLUTE PERCENTAGE ERROR)
        valores_demanda_mape = (demanda.iloc[:,1:cantidadMeses].values)
        valores_demanda_mape = valores_demanda_mape.flatten().tolist()
        #guardar erroresMape |e|/xt(demanda) en una lista para poder operar con ellos
        errores_mape = [ea / vd if vd != 0 else 1 for ea, vd in zip(erroresAbs, valores_demanda_mape)]
        MAPE = [np.mean(errores_mape[i:i+total_meses_pronostico]) * 100 for i in range(0, len(errores_mape), total_meses_pronostico)]
        # print('MAPE: ',MAPE[:5])
        
        #CALCULO DEL MAPE' (MAPE PRIMA)
        # Crear una nueva lista sin los elementos en los indices a eliminar
        pronostico_ses_filtrado = [pronostico_sed[i] for i in range(len(pronostico_sed)) if (i + 1) % cantidadMeses != 0]
        
        #guardar erroresMapePrima |e|/Mt(promedio_movil)
        errores_mape_prima = [ea / psf if psf != 0 else 1 for ea, psf in zip(erroresAbs, pronostico_ses_filtrado)]
        MAPE_prima = [np.mean(errores_mape_prima[i:i+total_meses_pronostico]) * 100 for i in range(0, len(errores_mape_prima), total_meses_pronostico)]
        # print('MAPE_PRIMA: ', MAPE_prima[:5])
        
        #EMC(CALCULO DEL ERROR CUADRATICO MEDIO) |e|^2
        EMC = [np.mean(np.square(erroresAbs[i:i+total_meses_pronostico])) for i in range(0, len(erroresAbs), total_meses_pronostico)]
        # print('EMC: ', EMC[:5])
        del productos_data, df_demanda
        return MAD, MAPE, MAPE_prima, EMC, df_pronostico_sed, lista_pronosticos, lista_pronosticos_redondeo
    
    def productos():
        productos_data = list(Productos.objects.values()) # Se obtienen los productos de la base de datos en forma de lista
        df_demanda = pd.DataFrame(productos_data) # Se convierten los productos en un DataFrame de pandas para su manipulación
        items = df_demanda.iloc[:, 1].tolist()
        proveedor = df_demanda.iloc[:,2].tolist()
        productos = df_demanda.iloc[:, 3].tolist()
        sede = df_demanda.iloc[:, 4].tolist()
        del productos_data, df_demanda
        return items, proveedor, productos, sede
    
    def prueba():
        start_time = time.perf_counter()
        MAD, MAPE, MAPE_prima, ECM, df_pronostico_sed, lista_pronosticos, lista_pronosticos_redondeo = PronosticoExpDoble.pronosticoExpDoble(0.5, 0.5, 1)
        items, proveedor, productos, sede = PronosticoExpDoble.productos()
        
        # print("MAD: ", MAD[:5])
        # print("MAPE: ", MAPE[:5])
        # print("MAPE_PRIMA: ", MAPE_prima[:5])
        # print("ECM: ", ECM[:5])
        # print("Pronostico: ", lista_pronosticos[:5])
        # print("Pronostico redondeo: ", lista_pronosticos_redondeo[:5])
        
        # serie = pd.concat([pd.Series(productos), pd.Series(MAD), pd.Series(MAPE)], axis=1)
        # serie.columns = ["Productos", "MAD", "Mejor pronostico"]
        # df = pd.DataFrame({"Items": items, "Proveedor": proveedor, "Productos": productos, "Sede": sede,"MAD": MAD, "MAPE": MAPE, "MAPE_Prima": MAPE_prima, "ECM": ECM, "Pronostico": lista_pronosticos, "Pronostico_redondeo": lista_pronosticos_redondeo})
    
        # # Especifica la ruta del archivo Excel donde deseas guardar el DataFrame
        # ruta_archivo_excel = 'suavizacion_exp_doble.xlsx'

        # # Usa el método to_excel() para guardar el DataFrame en el archivo Excel
        # df.to_excel(ruta_archivo_excel, index=False)  # Si no deseas incluir el índice en el archivo Excel, puedes establecer index=False
        end_time = time.perf_counter()
        print(f"Tiempo de ejecución: {end_time - start_time} segundos")

# PronosticoExpDoble.prueba()        

