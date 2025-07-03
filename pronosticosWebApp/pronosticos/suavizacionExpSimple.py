import time
import pandas as pd
import numpy as np
from pronosticosWebApp.pronosticos.promedioMovil import PronosticoMovil as pm

class PronosticoExpSimple:
    
    def __init__(self):
        pass
    
    def pronosticoExpSimple(df_demanda, alpha):
        print(f'Calculando suavización exponencial simple α={alpha}...')
        df = (
            df_demanda
            .sort_values(['sku', 'sku_nom', 'sede', 'yyyy', 'mm'])
            .reset_index(drop=True)
        )

        # 2) Cálculo de la media móvil exponencial (ewm) para cada grupo
        #    m_t = α·y_t + (1−α)·m_{t−1}, con m_0 = y_0
        df['m'] = df.groupby(['sku','sku_nom','sede'])['total'] \
                    .transform(lambda x: x.ewm(alpha=alpha, adjust=False).mean())

        # 3) Pronóstico SES por desplazamiento de 1 período
        df['pronostico_ses'] = df.groupby(['sku','sku_nom','sede'])['m'].shift(1)
        #    y para la primera fila de cada grupo, pron = valor real inicial
        is_first = df.groupby(['sku','sku_nom','sede']).cumcount() == 0
        df.loc[is_first, 'pronostico_ses'] = df.loc[is_first, 'total']

        # 4) Calculo de errores
        df['error'] = (df['total'] - df['pronostico_ses']).abs()
        df['errorMAPE'] = np.where(
            df['error'].isna(),
            np.nan,
            np.where(df['total'] == 0, 1, df['error'] / df['total'])
        )
        df['errorMAPEPrima'] = np.where(
            df['error'].isna(),
            np.nan,
            np.where(df['pronostico_ses'] == 0, 1, df['error'] / df['pronostico_ses'])
        )
        df['errorECM'] = df['error'] ** 2

        # 5) Agrego métricas por grupo usando sumas, conteos y first
        gb = df.groupby(['sku','sku_nom','sede'])
        cnt        = gb['error'].count()
        sum_err    = gb['error'].sum()
        first_err  = gb['error'].first()
        sum_mape   = gb['errorMAPE'].sum()
        first_mape = gb['errorMAPE'].first()
        sum_mapp   = gb['errorMAPEPrima'].sum()
        first_mapp = gb['errorMAPEPrima'].first()
        sum_ecm    = gb['errorECM'].sum()
        # first_ecm es cero siempre (errorECM inicial = 0), no es necesario restarlo

        agg = pd.DataFrame({
            'MAD':         (sum_err  - first_err) / (cnt - 1),
            'MAPE':      ((sum_mape - first_mape) / (cnt - 1)) * 100,
            'MAPE_Prima': ((sum_mapp - first_mapp) / (cnt - 1)) * 100,
            'ECM':         sum_ecm  / (cnt - 1)
        }).reset_index()

        # 6) Pronóstico para mes 13: es el último valor de "m" para cada grupo
        m_last = gb['m'].last().reset_index(name='pronostico_ses')

        # 7) Metadatos constantes: última marca, bodega y año
        meta = gb.agg({
            'marca_nom': 'last',
            'bod':       'last',
            'yyyy':      'last'
        }).reset_index()

        # 8) Construyo el DataFrame de pronósticos (mes 13)
        df_f = (
            meta
            .merge(m_last, on=['sku','sku_nom','sede'])
            .merge(agg,    on=['sku','sku_nom','sede'])
        )
        df_f['mm']    = 13
        df_f['total'] = np.nan
        # pongo NaN en todas las columnas de error
        for c in ['error','errorMAPE','errorMAPEPrima','errorECM']:
            df_f[c] = np.nan

        # 9) Limpio columna auxiliar y concateno todo
        df = df.drop(columns=['m'])
        cols = [
            'yyyy','mm','sku','sku_nom','marca_nom','bod','umd',
            'total','sede','precio','pronostico_ses','error','errorMAPE','errorMAPEPrima','errorECM',
            'MAD','MAPE','MAPE_Prima','ECM'
        ]
        df_result = pd.concat([df, df_f], ignore_index=True) \
                    .sort_values(['sku','sku_nom','sede','yyyy','mm']) \
                    .reset_index(drop=True)[cols]
        return df_result

   