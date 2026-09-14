import numpy as np
import pandas as pd
from django.db.models import Sum
from django.utils import timezone

from .models import BdVentasComercial, PresupuestoComercial

# nivel -> (campos reales en BdVentasComercial, nombres que espera el front)
NIVELES = {
    'general': ([], []),
    'centro': (['nombre_centro_de_operacion'],
               ['nombre_centro_operacion']),
    'centro_segmento': (['nombre_centro_de_operacion', 'nombre_clase_cliente'],
                        ['nombre_centro_operacion', 'segmento']),
    'centro_segmento_linea': (['nombre_centro_de_operacion', 'nombre_clase_cliente', 'nombre_linea_n1'],
                              ['nombre_centro_operacion', 'segmento', 'linea']),
}

CAMPOS_DETALLE = ['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente']
_COL_TODO = '__todo__'

def _a_registros(df):
    """
    Convierte el DataFrame a lista de dicts apta para JSON: inf/-inf y NaN
    se vuelven 0, porque `json.dumps` los escribiría como Infinity/NaN y
    `JSON.parse` del navegador los rechaza.
    """
    if df.empty:
        return []
    df = df.replace([np.inf, -np.inf], np.nan).fillna(0)
    return df.to_dict(orient='records')

def _dims_group(df, dims):
    """groupby([]) revienta en pandas; para el nivel 'general' se usa una
    columna constante que luego se descarta."""
    if dims:
        return df, list(dims)
    df = df.copy()
    df[_COL_TODO] = 1
    return df, [_COL_TODO]


def _historico(campo_valor, dims):
    """Ventas o costos por dims + lapso, ya con year y mes."""
    qs = (BdVentasComercial.objects
          .values(*dims, 'lapso')
          .annotate(suma=Sum(campo_valor)))
    df = pd.DataFrame(list(qs))
    if df.empty:
        return pd.DataFrame(columns=list(dims) + ['lapso', 'year', 'mes', 'suma'])
    df['year'] = df['lapso'] // 100
    df['mes'] = df['lapso'] % 100
    df['suma'] = df['suma'].fillna(0)
    return df


def _r2_por_mes(df, dims):
    """Correlación year vs suma, por dims + mes (en %, igual que antes)."""
    df, claves = _dims_group(df, dims)
    filas = []
    for llave, grupo in df.groupby(claves):
        llave = llave if isinstance(llave, tuple) else (llave,)
        for mes in range(1, 13):
            datos = grupo[grupo['mes'] == mes]
            if len(datos) >= 2 and datos['suma'].std() != 0:
                coef = np.corrcoef(datos['year'], datos['suma'])[0, 1]
                valor = round(coef, 4) * 100
            else:
                valor = 0
            filas.append({**dict(zip(claves, llave)), 'mes': mes, 'r2': valor})
    return pd.DataFrame(filas)


def _totales_anuales(df, dims, columna='suma', nombre='total_year'):
    """Total por dims + year, con variación $ y % contra el año previo."""
    df, claves = _dims_group(df, dims)
    tot = (df.groupby(claves + ['year'])[columna].sum()
             .reset_index().rename(columns={columna: nombre}))
    tot = tot.sort_values(claves + ['year'])
    tot['variacion_valor'] = tot.groupby(claves)[nombre].diff().fillna(0).round()
    tot['variacion_pct'] = (
        (tot.groupby(claves)[nombre].pct_change() * 100)
        .replace([np.inf, -np.inf], 0)
        .fillna(0)
        .round(2)
    )
    return tot

def calcular_comercial():
    """
    Año actual por línea+centro+segmento: ventas, costos, R², variaciones,
    y la proyección resultante de aplicar los crecimientos guardados.
    Lo único que se lee de PresupuestoComercial son los crecimientos.
    """
    from .views import _pronostico_por_linea_centro_segmento  # ya existente

    year_actual = timezone.now().year

    df_v = _pronostico_por_linea_centro_segmento('valor_neto', anio_inicio=year_actual - 1)
    df_c = _pronostico_por_linea_centro_segmento('valor_costo', anio_inicio=year_actual - 1)
    if df_v.empty or df_c.empty:
        return pd.DataFrame()
    df = pd.merge(df_v, df_c, on=CAMPOS_DETALLE + ['year'], suffixes=('_ventas', '_costos'))
    df = df.rename(columns={'suma_ventas': 'ventas', 'suma_costos': 'costos'})
    df = df[df['year'] == year_actual].reset_index(drop=True)
    if df.empty:
        return df

    # Crecimientos guardados por el usuario (lo único persistido)
    guardados = {
        (g['linea'], g['nombre_centro_de_operacion'], g['nombre_clase_cliente']): g
        for g in PresupuestoComercial.objects.filter(year=year_actual).values(
            'linea', 'nombre_centro_de_operacion', 'nombre_clase_cliente',
            'crecimiento_ventas')
    }

    def _crec_ventas(row):
        item = guardados.get((row['nombre_linea_n1'],
                              row['nombre_centro_de_operacion'],
                              row['nombre_clase_cliente']))
        return float(item['crecimiento_ventas'] or 0) if item else 0.0

    df['crecimiento_ventas'] = df.apply(_crec_ventas, axis=1)
    df['proyeccion_ventas'] = (df['ventas'] * (1 + df['crecimiento_ventas'] / 100)).round().astype(int)

    df['utilidad_valor_actual'] = (df['ventas'] - df['costos']).round().astype(int)
    df['utilidad_porcentual_actual'] = ((1 - df['costos'] / df['ventas']) * 100) \
        .replace([np.inf, -np.inf], 0).fillna(0).round(2)

    # Margen proyectado: ventas proyectadas contra el costo real actual.
    df['utilidad_valor'] = (df['proyeccion_ventas'] - df['costos']).round().astype(int)
    df['utilidad_porcentual'] = ((1 - df['costos'] / df['proyeccion_ventas']) * 100) \
        .replace([np.inf, -np.inf], 0).fillna(0).round(2)

    df['variacion_proyectada_valor'] = df['utilidad_valor'] - df['utilidad_valor_actual']
    df['variacion_proyectada_porcentual'] = (
        df['utilidad_porcentual'] - df['utilidad_porcentual_actual']).round(2)
    
    return df.rename(columns={
        'nombre_linea_n1': 'linea',
        'R2_ventas': 'r2_ventas', 
        'R2_costos': 'r2_costos',
        'variacion_pct_ventas': 'variacion_porcentual_ventas',
        'variacion_pct_costos': 'variacion_porcentual_costos',
        'variacion_valor_ventas': 'variacion_valor_ventas',
        'variacion_valor_costos': 'variacion_valor_costos',
        'variacion_mes_ventas': 'variacion_mes_ventas',
        'variacion_mes_costos': 'variacion_mes_costos',
        'variacion_precios_ventas': 'variacion_precios_ventas',
        'variacion_precios_costos': 'variacion_precios_costos',
    })

def _participacion_mensual(anio=None):
    """
    % de las ventas anuales de cada (línea, centro, segmento) que cae en
    cada mes. Usa el año pedido; si no tiene datos, cae al último año
    disponible que sea anterior (antes solo probaba anio - 1).
    """
    from .views import ajustar_porcentaje

    columnas_vacias = CAMPOS_DETALLE + [
        'year', 'mes', 'suma', 'total_anual', 'porcentaje_participacion']

    df = _historico('valor_neto', CAMPOS_DETALLE)
    if df.empty:
        return pd.DataFrame(columns=columnas_vacias)

    anio = anio or timezone.now().year
    disponibles = [a for a in sorted(df['year'].unique()) if a <= anio]
    if not disponibles:
        return pd.DataFrame(columns=columnas_vacias)

    df = df[df['year'] == disponibles[-1]]

    agr = df.groupby(CAMPOS_DETALLE + ['year', 'mes'])['suma'].sum().reset_index()
    totales = (agr.groupby(CAMPOS_DETALLE + ['year'])['suma'].sum()
                  .reset_index().rename(columns={'suma': 'total_anual'}))
    agr = agr.merge(totales, on=CAMPOS_DETALLE + ['year'], how='left')
    agr['porcentaje_participacion'] = (
        agr['suma'] / agr['total_anual'] * 100).fillna(0).round().astype(int)
    return agr.groupby(CAMPOS_DETALLE + ['year'], group_keys=False).apply(ajustar_porcentaje)

def _proyeccion_mensual_detalle():
    """
    Proyección del año siguiente repartida por mes, al máximo detalle.
    Cualquier nivel más grueso se obtiene sumando este resultado — que es
    exactamente lo que hacían los cuatro `actualizar_presupuesto_*`.
    """
    part = _participacion_mensual()
    comercial = calcular_comercial()
    if part.empty or comercial.empty:
        return pd.DataFrame(columns=CAMPOS_DETALLE + ['mes', 'valor_proyectado_mes'])

    proy = (comercial.groupby(['linea', 'nombre_centro_de_operacion', 'nombre_clase_cliente'])
            ['proyeccion_ventas'].sum().reset_index()
            .rename(columns={'linea': 'nombre_linea_n1'}))

    df = part.merge(proy, on=CAMPOS_DETALLE, how='left')
    df['proyeccion_ventas'] = df['proyeccion_ventas'].fillna(0)
    df['valor_proyectado_mes'] = (
        df['porcentaje_participacion'] / 100 * df['proyeccion_ventas']).round()
    return df

def construir_ventas(nivel):
    """
    Devuelve las filas (year, mes, dims, total, total_year, márgenes...)
    de una vista de ventas: histórico real + año siguiente proyectado,
    todo calculado al vuelo. Unifica `cargar_*` y `actualizar_*`.
    """
    dims, salida = NIVELES[nivel]
    year_actual = timezone.now().year
    year_siguiente = year_actual + 1

    hist_v = _historico('valor_neto', dims)
    if hist_v.empty:
        return []
    hist_c = _historico('valor_costo', dims)

    base, claves = _dims_group(hist_v, dims)
    df = base.groupby(claves + ['year', 'mes'])['suma'].sum().reset_index()

    # ---- Año siguiente: participación mensual x proyección ----
    detalle = _proyeccion_mensual_detalle()
    if not detalle.empty:
        det, _ = _dims_group(detalle, dims)
        sig = (det.groupby(claves + ['mes'])['valor_proyectado_mes'].sum()
                  .reset_index().rename(columns={'valor_proyectado_mes': 'suma'}))
        sig['year'] = year_siguiente
        df = pd.concat([df, sig[claves + ['year', 'mes', 'suma']]], ignore_index=True)

    df['suma'] = df['suma'].fillna(0).round().astype(int)

    # ---- Totales anuales, variaciones, R² ----
    tot_v = _totales_anuales(df, dims)
    tot_c = _totales_anuales(hist_c, dims, nombre='total_year_costos')[
        claves + ['year', 'total_year_costos']]
    df = df.merge(tot_v, on=claves + ['year'], how='left') \
           .merge(tot_c, on=claves + ['year'], how='left')
    df['total_year_costos'] = df['total_year_costos'].fillna(0)

    r2 = _r2_por_mes(df[df['year'] <= year_actual], dims)
    if not r2.empty:
        df = df.merge(r2, on=claves + ['mes'], how='left')
    df['r2'] = df.get('r2', 0)
    df['r2'] = df['r2'].fillna(0)

    # ---- Margen mensual: el % real del año actual aplicado al siguiente ----
    margen = hist_v[hist_v['year'] == year_actual]
    margen, _ = _dims_group(margen, dims)
    margen = margen.groupby(claves + ['mes'])['suma'].sum().reset_index()
    costo_mes = hist_c[hist_c['year'] == year_actual]
    costo_mes, _ = _dims_group(costo_mes, dims)
    costo_mes = (costo_mes.groupby(claves + ['mes'])['suma'].sum()
                 .reset_index().rename(columns={'suma': 'costo'}))
    margen = margen.merge(costo_mes, on=claves + ['mes'], how='left')
    margen['costo'] = margen['costo'].fillna(0)
    margen['margen_pct'] = ((1 - margen['costo'] / margen['suma']) * 100) \
        .replace([np.inf, -np.inf], 0).fillna(0).round(2)

    df = df.merge(margen[claves + ['mes', 'margen_pct']], on=claves + ['mes'], how='left')
    df['margen_pct'] = df['margen_pct'].fillna(0)
    df['utilidad_pct'] = np.where(df['year'] == year_siguiente, df['margen_pct'], 0).round(2)
    df['utilidad_valor'] = (df['suma'] * df['utilidad_pct'] / 100).round().astype(int)

    # ---- Total proyectado anual (columna del front) ----
    proy_total = df[df['year'] == year_siguiente].groupby(claves)['suma'].sum().to_dict()
    df['total_proyectado'] = df.apply(
        lambda r: proy_total.get(tuple(r[c] for c in claves) if len(claves) > 1
                                 else r[claves[0]], 0), axis=1)

    df = df.rename(columns={'suma': 'total', **dict(zip(dims, salida))})
    df = df.drop(columns=[_COL_TODO, 'margen_pct'], errors='ignore')
    return _a_registros(df)


def construir_costos(nivel):
    """Igual que `construir_ventas` pero para costos: histórico + año
    siguiente estimado por regresión lineal (np.polyfit), como antes."""
    dims, salida = NIVELES[nivel]
    year_siguiente = timezone.now().year + 1

    hist = _historico('valor_costo', dims)
    if hist.empty:
        return []

    base, claves = _dims_group(hist, dims)
    df = base.groupby(claves + ['year', 'mes'])['suma'].sum().reset_index()

    predicciones = []
    for llave, grupo in df.groupby(claves):
        llave = llave if isinstance(llave, tuple) else (llave,)
        for mes in range(1, 13):
            datos = grupo[grupo['mes'] == mes]
            if len(datos) >= 2:
                a, b = np.polyfit(datos['year'].values, datos['suma'].values, 1)
                predicciones.append({**dict(zip(claves, llave)), 'year': year_siguiente,
                                     'mes': mes, 'suma': round(a * year_siguiente + b)})
    if predicciones:
        df = pd.concat([df, pd.DataFrame(predicciones)], ignore_index=True)

    df['suma'] = df['suma'].fillna(0).round().astype(int)
    df = df.merge(_totales_anuales(df, dims), on=claves + ['year'], how='left')

    r2 = _r2_por_mes(df, dims)
    if not r2.empty:
        df = df.merge(r2, on=claves + ['mes'], how='left')
    df['r2'] = df.get('r2', 0)

    df = df.rename(columns={'suma': 'total', **dict(zip(dims, salida))})
    df = df.drop(columns=[_COL_TODO], errors='ignore')
    return _a_registros(df)