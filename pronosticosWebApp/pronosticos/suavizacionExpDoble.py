import pandas as pd
import numpy as np
import time
from pronosticosWebApp.pronosticos.promedioMovil import PronosticoMovil as pm

class PronosticoExpDoble:
    
    def __init__(self):
        pass
    
    def pronosticoExpDoble(df_demanda, alpha, beta, p):
        print('Calculando suavización exponencial doble...')
        df_demanda = (
            df_demanda
            .sort_values(['sku', 'sku_nom', 'sede', 'yyyy', 'mm'])
            .reset_index(drop=True)
        )
        resultados = []
        # Iteramos sobre cada combinación única de sku, sku_nom y sede
        for (sku, sku_nom, sede), grupo in df_demanda.groupby(['sku', 'sku_nom', 'sede'], sort=False):
            # Aseguramos orden temporal
            grupo = grupo.sort_values(['yyyy', 'mm'])
            
            # Extraemos arrays base
            years = grupo['yyyy'].values
            months = grupo['mm'].values
            bods = grupo['bod'].values
            marcas = grupo['marca_nom'].values
            total = grupo['total'].values
            precio = grupo['precio'].values
            n = total.shape[0]

            # Pre-alocación para suavización
            atenuado   = np.empty(n, dtype=float)
            tendencia  = np.empty(n, dtype=float)
            pronostico = np.empty(n, dtype=float)

            # Inicialización
            atenuado[0]   = total[0]
            tendencia[0]  = 0.0
            pronostico[0] = total[0]

            # Cálculo secuencial
            for t in range(1, n):
                at = alpha * total[t] + (1 - alpha) * (atenuado[t-1] + tendencia[t-1])
                tt = beta  * (at - atenuado[t-1])   + (1 - beta)  * tendencia[t-1]
                atenuado[t]   = at
                tendencia[t]  = tt
                pronostico[t] = at + p * tt

            # Pronóstico desplazado + fila mes 13
            pron_shift = np.empty(n+1, dtype=float)
            pron_shift[0]     = np.nan
            pron_shift[1:n]   = pronostico[:-1]
            pron_shift[n]     = atenuado[-1] + p * tendencia[-1]

            # Extensión de arrays para métricas
            total_ext = np.concatenate([total, [np.nan]])
            error     = np.abs(total_ext - pron_shift)
            errECM    = error**2

            errMAPE = np.ones_like(error)
            np.divide(error, total_ext, out=errMAPE, where=(total_ext != 0))

            errMAPEP = np.ones_like(error)
            np.divide(error, pron_shift, out=errMAPEP, where=(pron_shift != 0))
            # Métricas basadas en todos los meses excepto el primero y el nuevo
            idx_valid = slice(1, n)
            mad       = error[idx_valid].mean()
            mape      = errMAPE[idx_valid].mean()    * 100
            mape_p    = errMAPEP[idx_valid].mean()   * 100
            ecm       = errECM[idx_valid].mean()

            # Construcción de DataFrame en bloque
            yyyy_ext    = np.concatenate([years, [years[-1]]])
            mm_ext      = np.concatenate([months, [13]])
            sku_ext     = np.full(n+1, sku,     dtype=object)
            sku_nom_ext = np.full(n+1, sku_nom, dtype=object)
            sede_ext    = np.full(n+1, sede,    dtype=object)
            precio_ext = np.concatenate([precio, [precio[-1]]])
            bod_ext     = np.concatenate([bods, [bods[-1]]])
            marca_ext   = np.concatenate([marcas, [marcas[-1]]])

            dfg = pd.DataFrame({
                'yyyy':           yyyy_ext,
                'mm':             mm_ext,
                'sku':            sku_ext,
                'sku_nom':        sku_nom_ext,
                'marca_nom':      marca_ext,
                'bod':            bod_ext,
                'sede':           sede_ext,
                'total':          total_ext,
                'precio':         precio_ext,
                'pronostico_sed': pron_shift,
                'error':          error,
                'errorMAPE':      errMAPE,
                'errorMAPEPrima': errMAPEP,
                'errorECM':       errECM
            })

            # Incluir columnas de métricas solo en el mes 13
            dfg['MAD']         = np.nan
            dfg['MAPE']        = np.nan
            dfg['MAPE_Prima']  = np.nan
            dfg['ECM']         = np.nan
            mask13 = dfg['mm'] == 13
            dfg.loc[mask13, ['MAD','MAPE','MAPE_Prima','ECM']] = mad, mape, mape_p, ecm

            resultados.append(dfg)

        df_resultado = pd.concat(resultados, ignore_index=True)
        return df_resultado