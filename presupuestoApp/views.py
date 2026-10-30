from collections import defaultdict
import datetime
from functools import lru_cache
import re
import unicodedata
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.urls import reverse
from django.shortcuts import redirect, render
import pandas as pd
from .models import (
    BdVentasComercial,
    ComentarioComparativo,
    Cuenta4Base,
    Cuenta4Presupuestado,
    OrdenCuenta, AgrupacionCuenta,
    PresupuestoGeneralVentas,
    PresupuestoCentroOperacionVentas,
    PresupuestoCentroSegmentoVentas,
    PresupuestoGeneralCostos,
    PresupuestoCentroOperacionCostos,
    PresupuestoCentroSegmentoCostos,
    PresupuestoComercial,
    CuentasContables,
    Cuenta5Base,
    PresupuestoCentroSegLineaCostos,
    PresupuestoCentroSegLineaVentas,
    ConsolidadoTotalBase,
    Cuenta5Presupuestado,
)
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.db.models.functions import Coalesce, Concat, Trim
from django.db.models import Sum, Max, Q, Avg, Value
from django.db import DatabaseError, transaction
import numpy as np
import json
import zlib
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.db import models
from django.core.paginator import Paginator
from .log_cargas import log_carga
from .subtotales import configuracion_para_tablas
from . import filas_calculadas
from django.views.decorators.http import require_http_methods, require_GET, require_POST

# Tarjetas del dashboard de presupuestos por área: (clave de SEDE_CONFIG,
# título, color, ícono de Material Icons). El orden es el de la pantalla.
TARJETAS_DASHBOARD = [
    ("almacen-buga", "Almacen Buga", "#009688", "folder_open"),
    ("almacen-cali", "Almacen Cali", "#2196f3", "note_alt"),
    ("almacen-cartago", "Almacen Cartago", "#ff5722", "label"),
    ("almacen-tulua", "Almacen Tulua", "#673ab7", "group"),
    ("comercial-gastos", "Comercial y Gastos", "#e91e63", "group"),
    ("comunicaciones", "Comunicaciones", "#ff9800", "group"),
    ("contabilidad", "Contabilidad", "#4caf50", "group"),
    ("gerencia", "Gerencia", "#795548", "group"),
    ("gestion-riesgos", "Gestión de riesgos", "#9c27b0", "group"),
    ("gestion-humana", "Gestión humana", "#f44336", "group"),
    ("logistica", "Logística", "#607d8b", "group"),
    ("salud-ocupacional", "Salud ocupacional", "#3f51b5", "group"),
    ("servicios-tecnicos", "Servicios técnicos", "#2196f3", "group"),
    ("tecnologia", "Tecnología", "#3f51b5", "note"),
]


@login_required
def dashboard_home(request):
    USUARIOS_PERMITIDOS= ['admin', 'NICOLAS']
    if request.user.username not in USUARIOS_PERMITIDOS:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    tarjetas = [
        {"clave": clave, "titulo": titulo, "color": color, "icono": icono,
         "url_ver": reverse("presupuesto_sede", args=[clave]),
         "url_subir": reverse("subir_cuenta5_sede", args=[clave]),
         "cuenta5": estado_cuenta5(clave)}
        for clave, titulo, color, icono in TARJETAS_DASHBOARD
    ]
    # Nómina: mismo aviso y botón; su pantalla es el dashboard de nómina.
    tarjetas.append({
        "clave": "nomina", "titulo": "Nómina", "color": "#00838f", "icono": "payments",
        "url_ver": reverse("presupuestoNomina"),
        "url_subir": reverse("subir_cuenta5_nomina"),
        "url_quitar": reverse("quitar_cuenta5_nomina"),
        "url_destinos": reverse("ajustes_destinos_nomina"),
        "cuenta5": estado_cuenta5_nomina(),
    })
    return render(request, 'presupuesto_consolidado/dashboard_presupuestos.html', {
        'tarjetas': tarjetas,
    })

# --------------COMERCIAL------------------------------------
# Las vistas "por línea" (centro+segmento+línea) y el cálculo de
# participación mensual solo usaban BdVentas2025 a propósito (ver
# BUGS_Y_MEJORAS.md 2.13). Con la tabla consolidada, ese mismo criterio
# se aplica como un filtro de año — se deja como constante para que sea
# fácil de cambiar en un solo lugar si el negocio decide usar más años.
def _anio_detalle_linea():
    """Año del detalle por línea. Antes era una constante evaluada al
    importar el módulo, así que no cambiaba al cruzar de año."""
    return timezone.now().year

# ----------------------------------------------------------------------
# Mapeo fijo de código de centro de operación (columna MCNZONA del
# Excel) -> nombre de almacén. Si se abre un nuevo almacén, agregarlo
# aquí — es el único lugar que hay que tocar.
# ----------------------------------------------------------------------
NOMBRES_CENTRO_OPERACION = {
    1: 'ALMACEN TULUA',
    2: 'ALMACEN BUGA',
    3: 'ALMACEN CARTAGO',
    4: 'ALMACEN CALI',
}

# Columnas que debe tener el Excel para poder procesarlo (en mayúsculas,
# como vienen en el archivo de ejemplo).
COLUMNAS_REQUERIDAS = [
    'YYYY', 'MM', 'MCNZONA', 'LINNOMBRE', 'VGRNOMBRE', 'SUBTOTAL', 'COSTO_VTA',
    'VENCEDULA', 'MCNPRODUCT',
]

# El mismo informe también sale con otros nombres de columna (yyyy, mm, zona,
# linea_nom, cliente_grp_nom, ven_cc, sku, ...). Nombre de ese formato ->
# nombre que usa el sistema. Solo se aplica si el archivo NO trae ya la
# columna original, así un archivo del formato original nunca se altera.
ALIAS_COLUMNAS_VENTAS = {
    'ZONA': 'MCNZONA',                 # código de zona/centro (001, 002...)
    'LINEA_NOM': 'LINNOMBRE',
    'CLIENTE_GRP_NOM': 'VGRNOMBRE',    # CLIENTE, PRODUCCION, DISTRIBUIDOR...
    'VEN_CC': 'VENCEDULA',
    'SKU': 'MCNPRODUCT',
    'LINEA': 'PROLINEA',
    'CLIENTE_GRP': 'VINGRUPO',
}


def _normalizar_columnas_ventas(df):
    """Pasa los encabezados a mayúsculas y traduce los del formato alterno."""
    df.columns = [str(c).strip().upper() for c in df.columns]
    renombrar = {alias: original for alias, original in ALIAS_COLUMNAS_VENTAS.items()
                 if alias in df.columns and original not in df.columns}
    return df.rename(columns=renombrar)


def _columnas_utiles_ventas():
    """Encabezados (en mayúsculas) que usa la importación, en los dos formatos."""
    return set(COLUMNAS_REQUERIDAS) | set(ALIAS_COLUMNAS_VENTAS)


def _leer_excel_ventas(archivo, al_avanzar=None):
    """Lee del Excel de ventas solo las columnas que se usan, por partes.

    El informe trae ~55 columnas y puede tener 350.000 filas o más; con
    pd.read_excel eso usa varios GB de memoria y tarda minutos. El lector
    por partes (lector_excel) mantiene la memoria baja.
    """
    from .lector_excel import leer_columnas_xlsx
    utiles = _columnas_utiles_ventas()
    return leer_columnas_xlsx(archivo, lambda c: str(c).strip().upper() in utiles, al_avanzar=al_avanzar)


def _parsear_numeros_co(serie):
    """Versión vectorizada de _parsear_numero_co para una columna completa."""
    if pd.api.types.is_numeric_dtype(serie):
        return pd.to_numeric(serie, errors='coerce').fillna(0.0).astype(float)
    texto = serie.astype(str).str.strip()
    es_numero = serie.apply(lambda v: isinstance(v, (int, float)) and not pd.isna(v))
    convertido = pd.to_numeric(texto.str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
                               errors='coerce')
    directo = pd.to_numeric(serie.where(es_numero), errors='coerce')
    return directo.where(es_numero, convertido).fillna(0.0).astype(float)


def _nombre_columna_para_mensaje(columna):
    alias = [a for a, original in ALIAS_COLUMNAS_VENTAS.items() if original == columna]
    return f"{columna} (o {alias[0].lower()})" if alias else columna

# --------------------------------------------------------------------
# Reglas de depuración: filas que se descartan ANTES de calcular nada.
# --------------------------------------------------------------------
CEDULA_EXCLUIDA = 1116235756
PRODUCTOS_EXCEPCION_S = {'S4', 'S909'}


def _depurar_dataframe(df):
    """
    Aplica las reglas de depuración del Excel antes de cualquier
    transformación o consolidación:

      1) Elimina filas donde VENCEDULA == 1116235756.
      2) Elimina filas donde MCNPRODUCT empieza con 'S', salvo que sea
         exactamente 'S4' o 'S909'.

    Devuelve (df_depurado, resumen) donde `resumen` es un dict con la
    cantidad de filas eliminadas por cada regla, para informarlas en la
    respuesta.
    """
    resumen = {}

    # 1) VENCEDULA == 1116235756 (puede venir como texto o número en el Excel)
    vencedula_num = pd.to_numeric(df['VENCEDULA'], errors='coerce')
    mascara_cedula = vencedula_num == CEDULA_EXCLUIDA
    resumen['eliminados_por_cedula'] = int(mascara_cedula.sum())
    df = df[~mascara_cedula]

    # 2) MCNPRODUCT que empieza con 'S', excepto 'S4' y 'S909'
    producto = df['MCNPRODUCT'].astype(str).str.strip().str.upper()
    mascara_producto = producto.str.startswith('S') & ~producto.isin(PRODUCTOS_EXCEPCION_S)
    resumen['eliminados_por_producto_s'] = int(mascara_producto.sum())
    df = df[~mascara_producto]

    resumen['filas_restantes'] = len(df)
    return df, resumen


def _parsear_numero_co(valor):
    """
    El Excel trae los valores numéricos en formato colombiano/europeo
    como texto: '.' para miles y ',' para decimales
    (p. ej. "-93.626,00" -> -93626.00). Esta función los convierte a
    float sin importar si pandas ya los interpretó como número o los
    dejó como texto.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip()
    if texto == '':
        return 0.0
    texto = texto.replace('.', '').replace(',', '.')
    try:
        return float(texto)
    except ValueError:
        return 0.0


def _nombre_centro_operacion(codigo):
    """1 -> ALMACEN TULUA, 2 -> ALMACEN BUGA, 3 -> ALMACEN CARTAGO, 4 -> ALMACEN CALI."""
    try:
        codigo_int = int(codigo)
    except (TypeError, ValueError):
        return None
    return NOMBRES_CENTRO_OPERACION.get(codigo_int)


def _limpiar_clase_cliente(valor):
    """Segmento tal como viene en el Excel, solo sin espacios sobrantes.

    Ya no se renombra (antes CLIENTE -> CLIENTES y PRODUCCION -> PRODUCTOR);
    la migración 0051 pasó los datos guardados a los nombres del Excel.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    return str(valor).strip()

def _lapso_actual():
    """Lapso (AAAAMM) del mes en curso. Todo lapso >= a este se considera incompleto."""
    hoy = timezone.now()
    return hoy.year * 100 + hoy.month

def _replicar_meses_faltantes(anio):
    """
    Completa el año `anio` copiando los registros del mismo mes del año
    anterior (mismo centro, nombre_linea_n1 y nombre_clase_cliente).

    Se regeneran siempre los meses >= al mes en curso (el actual y los
    futuros, que nunca tienen dato real) y además cualquier mes anterior
    que haya quedado sin ningún registro.
    """
    lapso_corte = _lapso_actual()
    lapsos_anio = [anio * 100 + m for m in range(1, 13)]

    con_datos = set(
        BdVentasComercial.objects
        .filter(lapso__in=lapsos_anio)
        .values_list('lapso', flat=True)
    )
    objetivo = [l for l in lapsos_anio if l >= lapso_corte or l not in con_datos]
    if not objetivo:
        return {}

    # Se borra lo que haya en esos meses (replicas viejas) y se regenera.
    BdVentasComercial.objects.filter(lapso__in=objetivo).delete()

    nuevos, resumen = [], {}
    for lapso in objetivo:
        base = list(BdVentasComercial.objects.filter(lapso=lapso - 100))
        resumen[lapso] = len(base)
        for r in base:
            nuevos.append(BdVentasComercial(
                lapso=lapso,
                centro_de_operacion=r.centro_de_operacion,
                nombre_centro_de_operacion=r.nombre_centro_de_operacion,
                nombre_linea_n1=r.nombre_linea_n1,
                nombre_clase_cliente=r.nombre_clase_cliente,
                valor_neto=r.valor_neto,
                valor_costo=r.valor_costo,
            ))

    if nuevos:
        BdVentasComercial.objects.bulk_create(nuevos, batch_size=1000)
    return resumen

def _importar_ventas_desde_df(df):
    """Depura, consolida y guarda el DataFrame del informe de ventas.

    Devuelve (respuesta, código HTTP). La usan la petición directa y el
    proceso en segundo plano.
    """
    # Normalizar encabezados (espacios, minúsculas) y aceptar los dos
    # formatos del informe: el original (MCNZONA, LINNOMBRE, VGRNOMBRE...)
    # y el alterno (zona, linea_nom, cliente_grp_nom, ven_cc, sku...).
    df = _normalizar_columnas_ventas(df)

    faltantes = [_nombre_columna_para_mensaje(c) for c in COLUMNAS_REQUERIDAS if c not in df.columns]
    if faltantes:
        return {
            'status': 'error',
            'mensaje': f'Faltan columnas en el Excel: {", ".join(faltantes)}',
        }, 400

    filas_leidas = len(df)
    if filas_leidas == 0:
        return {'status': 'error', 'mensaje': 'El archivo no tiene filas'}, 400

    # --------------------------------------------------------------
    # 0) Depurar ANTES de calcular nada: quitar la cédula excluida y
    #    los productos "S..." que no están en la lista de excepciones.
    # --------------------------------------------------------------
    df, resumen_depuracion = _depurar_dataframe(df)

    if len(df) == 0:
        return {
            'status': 'error',
            'mensaje': (
                f'Después de depurar (cédula excluida: {resumen_depuracion["eliminados_por_cedula"]}, '
                f'productos "S" excluidos: {resumen_depuracion["eliminados_por_producto_s"]}) '
                'no quedó ninguna fila para procesar.'
            ),
        }, 400

    # --------------------------------------------------------------
    # 1) lapso = año*100 + mes (junta YYYY y MM del Excel, igual
    #    formato que ya usa el resto del sistema).
    # --------------------------------------------------------------
    df['lapso'] = (
        pd.to_numeric(df['YYYY'], errors='coerce').fillna(0).astype(int) * 100
        + pd.to_numeric(df['MM'], errors='coerce').fillna(0).astype(int)
    )
    # --------------------------------------------------------------
    # 1.b) Descartar meses incompletos: solo se importan lapsos
    #      ANTERIORES al mes en curso (el mes actual todavía no cerró).
    # --------------------------------------------------------------
    lapso_corte = _lapso_actual()
    mascara_incompletos = df['lapso'] >= lapso_corte
    lapsos_descartados = sorted(int(l) for l in df.loc[mascara_incompletos, 'lapso'].unique())
    filas_descartadas_por_mes = int(mascara_incompletos.sum())
    df = df[~mascara_incompletos]

    if len(df) == 0:
        return {
            'status': 'error',
            'mensaje': (
                f'Todas las filas quedaron fuera: el archivo solo trae meses '
                f'incompletos ({lapsos_descartados}). Solo se importan meses '
                f'cerrados (hasta {lapso_corte - 1 if lapso_corte % 100 > 1 else (lapso_corte // 100 - 1) * 100 + 12}).'
            ),
        }, 400
    # --------------------------------------------------------------
    # 2) centro_de_operacion = MCNZONA
    # 3) nombre_centro_de_operacion = mapeo fijo 1-4
    # --------------------------------------------------------------
    df['centro_de_operacion'] = pd.to_numeric(df['MCNZONA'], errors='coerce')
    df['nombre_centro_de_operacion'] = df['centro_de_operacion'].apply(_nombre_centro_operacion)

    # --------------------------------------------------------------
    # 4) nombre_linea_n1 = LINNOMBRE
    # --------------------------------------------------------------
    df['nombre_linea_n1'] = df['LINNOMBRE'].astype(str).str.strip()

    # --------------------------------------------------------------
    # 5) nombre_clase_cliente = VGRNOMBRE, con la conversión pedida
    # --------------------------------------------------------------
    df['nombre_clase_cliente'] = df['VGRNOMBRE'].apply(_limpiar_clase_cliente)

    # --------------------------------------------------------------
    # 6) valor_neto = SUBTOTAL   7) valor_costo = COSTO_VTA
    # --------------------------------------------------------------
    df['valor_neto'] = _parsear_numeros_co(df['SUBTOTAL'])
    df['valor_costo'] = _parsear_numeros_co(df['COSTO_VTA'])

    # Filas cuyo código de centro no está en el mapeo 1-4: se importan
    # igual (para no perder ventas), pero se informan al usuario.
    centros_sin_mapear = sorted(
        df.loc[df['nombre_centro_de_operacion'].isna(), 'centro_de_operacion'].dropna().unique().tolist()
    )

    # --------------------------------------------------------------
    # 8) Consolidar por año+mes (lapso). El Excel viene detallado por
    #    año/mes/día y documento; aquí se resume a un registro por
    #    lapso+centro+línea+segmento, que es como trabaja el resto
    #    del sistema.
    # --------------------------------------------------------------
    columnas_agrupacion = [
        'lapso', 'centro_de_operacion', 'nombre_centro_de_operacion',
        'nombre_linea_n1', 'nombre_clase_cliente',
    ]
    df_consolidado = (
        df.groupby(columnas_agrupacion, dropna=False)[['valor_neto', 'valor_costo']]
        .sum()
        .reset_index()
    )

    lapsos_importados = sorted(int(l) for l in df_consolidado['lapso'].unique().tolist())

    # Reemplaza los datos existentes de esos mismos meses (evita
    # duplicar si se vuelve a subir el mismo Excel, o una versión
    # corregida del mismo mes), en una transacción atómica para no
    # dejar la tabla a medias si algo falla a mitad de camino.
    with transaction.atomic():
        BdVentasComercial.objects.filter(lapso__in=lapsos_importados).delete()
        BdVentasComercial.objects.bulk_create([
            BdVentasComercial(
                lapso=int(row['lapso']),
                centro_de_operacion=(
                    int(row['centro_de_operacion']) if pd.notna(row['centro_de_operacion']) else None
                ),
                nombre_centro_de_operacion=row['nombre_centro_de_operacion'],
                nombre_linea_n1=row['nombre_linea_n1'],
                nombre_clase_cliente=row['nombre_clase_cliente'],
                valor_neto=float(row['valor_neto']),
                valor_costo=float(row['valor_costo']),
            )
            for _, row in df_consolidado.iterrows()
        ])
        # Completar el año con la copia del año anterior
        anio_objetivo = lapso_corte // 100
        resumen_replica = _replicar_meses_faltantes(anio_objetivo)

    mensaje = (
        f"✅ {filas_leidas} filas leídas del Excel. Depuración: "
        f"{resumen_depuracion['eliminados_por_cedula']} eliminada(s) por cédula excluida, "
        f"{resumen_depuracion['eliminados_por_producto_s']} eliminada(s) por producto 'S...' "
        f"(quedaron {resumen_depuracion['filas_restantes']} filas). "
        f"Consolidadas en {len(df_consolidado)} registros para los meses {lapsos_importados}."
    )
    if centros_sin_mapear:
        mensaje += (
            f" ⚠️ Hay {len(centros_sin_mapear)} código(s) de centro de operación "
            f"sin nombre asignado: {centros_sin_mapear}. Esas filas se importaron "
            f"sin 'nombre_centro_de_operacion' — revisar NOMBRES_CENTRO_OPERACION "
            f"si corresponden a un almacén nuevo."
        )
    if filas_descartadas_por_mes:
        mensaje += (
            f" ⏭️ Se ignoraron {filas_descartadas_por_mes} fila(s) de meses "
            f"incompletos {lapsos_descartados} (solo se cargan meses cerrados)."
        )
    if resumen_replica:
        detalle = ", ".join(f"{l}: {n}" for l, n in sorted(resumen_replica.items()))
        mensaje += f" 🔁 Meses completados con datos del año anterior → {detalle}."

    return {
        'status': 'ok',
        'mensaje': mensaje,
        'filas_leidas': filas_leidas,
        'depuracion': resumen_depuracion,
        'registros_consolidados': len(df_consolidado),
        'lapsos': lapsos_importados,
        'centros_sin_mapear': centros_sin_mapear,
        'meses_replicados': resumen_replica,
        'lapsos_descartados': lapsos_descartados,
    }, 200


# --------------------------------------------------------------------
# Importación en segundo plano. El informe puede tener cientos de miles
# de filas: procesarlo dentro de la petición supera el tiempo que el
# servidor espera (502). La petición solo guarda el archivo y responde;
# el navegador consulta el estado hasta que termina. El estado se guarda
# en un archivo JSON en la carpeta temporal para que cualquier worker de
# gunicorn lo pueda leer.
# --------------------------------------------------------------------
import os as _os
import shutil as _shutil
import tempfile as _tempfile
import threading as _threading
import uuid as _uuid
from django.conf import settings as _settings


def _carpeta_importaciones():
    carpeta = _os.path.join(_tempfile.gettempdir(), 'importaciones_ventas_comercial')
    _os.makedirs(carpeta, exist_ok=True)
    return carpeta


def _ruta_estado(trabajo):
    if not re.fullmatch(r'[0-9a-f]{32}', trabajo or ''):
        return None
    return _os.path.join(_carpeta_importaciones(), f'{trabajo}.json')


def _guardar_estado(trabajo, datos):
    ruta = _ruta_estado(trabajo)
    temporal = ruta + '.tmp'
    with open(temporal, 'w', encoding='utf-8') as fh:
        json.dump(datos, fh, ensure_ascii=False, default=str)
    _os.replace(temporal, ruta)              # escritura atómica


def _limpiar_importaciones_viejas(horas=24):
    limite = timezone.now().timestamp() - horas * 3600
    carpeta = _carpeta_importaciones()
    for nombre in _os.listdir(carpeta):
        ruta = _os.path.join(carpeta, nombre)
        try:
            if _os.path.getmtime(ruta) < limite:
                _os.remove(ruta)
        except OSError:
            pass


def _leer_e_importar_ventas(archivo, al_avanzar=None):
    try:
        df = _leer_excel_ventas(archivo, al_avanzar=al_avanzar)
    except Exception as e:
        return {'status': 'error', 'mensaje': f'No se pudo leer el archivo: {e}'}, 400
    return _importar_ventas_desde_df(df)


def _procesar_importacion(trabajo, ruta_archivo):
    from django.db import connection as _conexion
    inicio = timezone.now()

    def avance(n):
        _guardar_estado(trabajo, {'status': 'procesando', 'filas': n,
                                  'mensaje': f'Leyendo el archivo… {n:,} filas'.replace(',', '.')})
    try:
        with open(ruta_archivo, 'rb') as fh:
            respuesta, codigo = _leer_e_importar_ventas(fh, al_avanzar=avance)
        respuesta['codigo'] = codigo
        respuesta['segundos'] = round((timezone.now() - inicio).total_seconds())
        _guardar_estado(trabajo, respuesta)
    except Exception as e:                                         # noqa: BLE001
        _guardar_estado(trabajo, {'status': 'error', 'codigo': 500,
                                  'mensaje': f'Error al procesar el archivo: {e}'})
    finally:
        try:
            _os.remove(ruta_archivo)
        except OSError:
            pass
        _conexion.close()


# importar ventas comercial
@csrf_exempt
def importar_bd_ventas_comercial(request):
    """
    Recibe el Excel de ventas detalladas, lo depura/transforma según
    las reglas de negocio, lo consolida por año+mes+centro+línea+segmento
    y reemplaza en `BdVentasComercial` los meses (lapsos) que vengan en
    el archivo (para poder re-subir un Excel corregido sin duplicar).

    Por defecto el archivo se procesa en segundo plano: responde
    {'status': 'procesando', 'url_estado': ...} y el navegador consulta
    esa URL. Con IMPORTAR_VENTAS_EN_SEGUNDO_PLANO = False (pruebas) se
    procesa y responde en la misma petición.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido'}, status=405)

    archivo = request.FILES.get('file')
    if not archivo:
        return JsonResponse({'status': 'error', 'mensaje': 'No se recibió ningún archivo'}, status=400)

    if not getattr(_settings, 'IMPORTAR_VENTAS_EN_SEGUNDO_PLANO', True):
        respuesta, codigo = _leer_e_importar_ventas(archivo)
        return JsonResponse(respuesta, status=codigo)

    _limpiar_importaciones_viejas()
    trabajo = _uuid.uuid4().hex
    ruta_archivo = _os.path.join(_carpeta_importaciones(), f'{trabajo}.excel')
    with open(ruta_archivo, 'wb') as destino:
        for parte in archivo.chunks():
            destino.write(parte)
    _guardar_estado(trabajo, {'status': 'procesando', 'filas': 0, 'mensaje': 'Leyendo el archivo…'})
    _threading.Thread(target=_procesar_importacion, args=(trabajo, ruta_archivo),
                      name=f'importar-ventas-{trabajo[:8]}', daemon=True).start()
    return JsonResponse({
        'status': 'procesando',
        'trabajo': trabajo,
        'url_estado': reverse('estado_importar_bd_ventas_comercial', args=[trabajo]),
    }, status=202)


def estado_importar_bd_ventas_comercial(request, trabajo):
    """Estado de una importación en segundo plano."""
    ruta = _ruta_estado(trabajo)
    if not ruta or not _os.path.exists(ruta):
        return JsonResponse({'status': 'error', 'mensaje': (
            'No se encontró la importación (el servidor pudo reiniciarse). Vuelva a subir el archivo.')},
            status=404)
    with open(ruta, encoding='utf-8') as fh:
        datos = json.load(fh)
    return JsonResponse(datos, status=200)


def vista_importar_bd_ventas_comercial(request):
    anio = timezone.now().year
    return render(request, 'presupuesto_comercial/importar_ventas_comercial.html', {
        'anios_reemplazo': [anio - 1, anio, anio + 1],
        'anio_actual': anio,
    })


# --------------------------------------------------------------------
# Reemplazar un año completo con un resumen ZONA / SEGMENTO / LINEA x mes
# --------------------------------------------------------------------
MESES_RESUMEN = ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 'JULIO',
                 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']
CAMPOS_REEMPLAZO = {'valor_neto': 'valor neto', 'valor_costo': 'valor costo'}


def _encabezado_resumen(texto):
    texto = unicodedata.normalize('NFKD', str(texto or '')).encode('ascii', 'ignore').decode()
    texto = ' '.join(texto.upper().split())
    return 'SEPTIEMBRE' if texto == 'SETIEMBRE' else texto


def _numero_resumen(serie):
    """Valores del resumen: ' 13.221.110 ', ' -   ' (= 0), '(1.500)' (= -1500) o números."""
    def limpiar(v):
        if isinstance(v, str):
            t = v.strip().replace('$', '').replace(' ', '')
            if t in ('', '-'):
                return 0
            if t.startswith('(') and t.endswith(')'):
                t = '-' + t[1:-1]
            return t
        return v
    return _parsear_numeros_co(serie.map(limpiar).astype(object))


def _leer_resumen_anual(archivo):
    """DataFrame (centro, nombre_centro, segmento, linea, mes 1..12) y avisos."""
    from .lector_excel import leer_columnas_xlsx
    df = leer_columnas_xlsx(archivo, lambda c: True)
    df.columns = [_encabezado_resumen(c) for c in df.columns]
    faltantes = [c for c in ['ZONA', 'SEGMENTO', 'LINEA'] + MESES_RESUMEN if c not in df.columns]
    if faltantes:
        raise ValueError(f'Faltan columnas en el Excel: {", ".join(faltantes)}')

    avisos = []
    datos = pd.DataFrame({
        'centro_de_operacion': pd.to_numeric(df['ZONA'], errors='coerce'),
        'nombre_clase_cliente': df['SEGMENTO'].apply(_limpiar_clase_cliente),
        'nombre_linea_n1': df['LINEA'].map(lambda v: str(v).strip() if v is not None and not pd.isna(v) else ''),
    })
    for n, mes in enumerate(MESES_RESUMEN, 1):
        datos[n] = _numero_resumen(df[mes])

    # Filas sin zona, segmento o línea (títulos, totales al final): se ignoran
    validas = datos['centro_de_operacion'].notna() & datos['nombre_linea_n1'].ne('') & \
        datos['nombre_clase_cliente'].notna()
    if (~validas).sum():
        avisos.append(f'{int((~validas).sum())} fila(s) sin zona, segmento o línea se ignoraron')
    if 'TOTAL' in df.columns:
        diferencia = (datos[list(range(1, 13))].sum(axis=1) - _numero_resumen(df['TOTAL'])).abs()
        descuadres = int((diferencia[validas] > 1).sum())
        if descuadres:
            avisos.append(f'{descuadres} fila(s) donde la suma de los meses no da la columna TOTAL '
                          f'(se usaron los meses)')
    datos = datos[validas].copy()
    datos['centro_de_operacion'] = datos['centro_de_operacion'].astype(int)
    datos['nombre_centro_de_operacion'] = datos['centro_de_operacion'].apply(_nombre_centro_operacion)
    claves = ['centro_de_operacion', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'nombre_linea_n1']
    datos = datos.groupby(claves, dropna=False)[list(range(1, 13))].sum().reset_index()
    sin_mapear = sorted(datos.loc[datos['nombre_centro_de_operacion'].isna(), 'centro_de_operacion'].unique().tolist())
    if sin_mapear:
        avisos.append(f'zona(s) sin nombre de almacén: {sin_mapear} (revisar NOMBRES_CENTRO_OPERACION)')
    return datos, avisos


def reemplazar_anio_ventas(datos, anio, campo):
    """Reemplaza `campo` (valor_neto o valor_costo) de todo el año `anio`.

    Se borran todos los registros del año y se vuelven a crear uno por
    (mes, zona, segmento, línea): el campo elegido sale del archivo y el
    otro campo se conserva con lo que tenía antes esa misma combinación,
    para que subir el resumen de ventas no borre los costos (ni al revés).
    """
    otro = 'valor_costo' if campo == 'valor_neto' else 'valor_neto'
    lapsos = [anio * 100 + m for m in range(1, 13)]
    clave = lambda r: (r['lapso'], r['centro_de_operacion'], r['nombre_clase_cliente'], r['nombre_linea_n1'])  # noqa: E731

    registros = {}
    for r in datos.to_dict('records'):
        for mes in range(1, 13):
            fila = {'lapso': anio * 100 + mes, 'centro_de_operacion': r['centro_de_operacion'],
                    'nombre_centro_de_operacion': r['nombre_centro_de_operacion'],
                    'nombre_clase_cliente': r['nombre_clase_cliente'], 'nombre_linea_n1': r['nombre_linea_n1']}
            fila[campo], fila[otro] = float(r[mes]), 0.0
            registros[clave(fila)] = fila

    with transaction.atomic():
        anteriores = (BdVentasComercial.objects.filter(lapso__in=lapsos)
                      .values('lapso', 'centro_de_operacion', 'nombre_centro_de_operacion',
                              'nombre_clase_cliente', 'nombre_linea_n1')
                      .annotate(campo_antes=Sum(campo), otro_antes=Sum(otro)))
        total_antes = 0.0
        for a in anteriores:
            total_antes += a['campo_antes'] or 0
            fila = registros.get(clave(a))
            if fila is None:      # combinación que no viene en el archivo: queda en 0 en el campo elegido
                fila = registros[clave(a)] = {
                    'lapso': a['lapso'], 'centro_de_operacion': a['centro_de_operacion'],
                    'nombre_centro_de_operacion': a['nombre_centro_de_operacion'],
                    'nombre_clase_cliente': a['nombre_clase_cliente'], 'nombre_linea_n1': a['nombre_linea_n1'],
                    campo: 0.0, otro: 0.0}
            fila[otro] += a['otro_antes'] or 0
        borrados, _ = BdVentasComercial.objects.filter(lapso__in=lapsos).delete()
        nuevos = [BdVentasComercial(**f) for f in registros.values() if f[campo] or f[otro]]
        BdVentasComercial.objects.bulk_create(nuevos, batch_size=1000)

    return {
        'borrados': borrados,
        'creados': len(nuevos),
        'total_antes': round(total_antes),
        'total_nuevo': round(sum(f[campo] for f in registros.values())),
    }


@require_POST
def importar_resumen_anual_ventas(request):
    """Sube el resumen ZONA / SEGMENTO / LINEA / ENERO..DICIEMBRE y reemplaza el año elegido."""
    archivo = request.FILES.get('file')
    if not archivo:
        return JsonResponse({'status': 'error', 'mensaje': 'No se recibió ningún archivo'}, status=400)
    campo = request.POST.get('campo', '')
    if campo not in CAMPOS_REEMPLAZO:
        return JsonResponse({'status': 'error', 'mensaje': 'Elija si el archivo es valor neto o valor costo'},
                            status=400)
    try:
        anio = int(request.POST.get('anio', ''))
    except ValueError:
        anio = 0
    if not 2000 <= anio <= 2100:
        return JsonResponse({'status': 'error', 'mensaje': 'Elija el año a reemplazar'}, status=400)

    try:
        datos, avisos = _leer_resumen_anual(archivo)
    except Exception as e:                                         # noqa: BLE001
        return JsonResponse({'status': 'error', 'mensaje': f'No se pudo leer el archivo: {e}'}, status=400)
    if datos.empty:
        return JsonResponse({'status': 'error', 'mensaje': 'El archivo no tiene filas con zona, segmento y línea'},
                            status=400)

    with log_carga('ventas_resumen_anual', request, anio=anio, campo=campo) as info:
        r = reemplazar_anio_ventas(datos, anio, campo)
        info.update(combinaciones=len(datos), **r)
    fmt = lambda v: f'{v:,.0f}'.replace(',', '.')  # noqa: E731
    mensaje = (f"✅ {CAMPOS_REEMPLAZO[campo].capitalize()} de {anio} reemplazado: "
               f"{len(datos)} combinaciones zona/segmento/línea del archivo. "
               f"Total {CAMPOS_REEMPLAZO[campo]} del año: antes ${fmt(r['total_antes'])}, "
               f"ahora ${fmt(r['total_nuevo'])}. "
               f"Se borraron {r['borrados']} registros y se crearon {r['creados']}.")
    if avisos:
        mensaje += ' ⚠️ ' + '; '.join(avisos) + '.'
    return JsonResponse({'status': 'ok', 'mensaje': mensaje, **r, 'anio': anio, 'campo': campo})


def obtener_ventas_agrupadas(campo_valor, campos_agrupacion, anio=None, anio_desde=None):
    """
    Reemplaza el bloque repetido de "bd2020 ... bd2025 -> concat" que
    aparecía en cada vista de "cargar_presupuesto_*". Con la tabla
    consolidada, esto es una única consulta con GROUP BY.

    Parameters
    ----------
    campo_valor : str
        'valor_neto' para ventas o 'valor_costo' para costos.
    campos_agrupacion : list[str]
        Los campos por los que se debe agrupar, ni más ni menos que
        los que el resultado final necesita. Ejemplos reales de este
        proyecto:
          - Presupuesto general:               ['lapso']
          - Presupuesto por centro:             ['nombre_centro_de_operacion', 'lapso']
          - Presupuesto centro+segmento:        ['nombre_centro_de_operacion', 'nombre_clase_cliente', 'lapso']
          - Presupuesto centro+segmento+línea:  ['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'lapso']
        OJO (ver BUGS_Y_MEJORAS.md, punto 2.6): en BdVentasComercial
        existen DOS campos de centro distintos: 'centro_de_operacion'
        (código numérico) y 'nombre_centro_de_operacion' (nombre). Usar
        siempre el nombre salvo que se necesite explícitamente el código.
        Lo mismo aplica a 'linea_n1'/'nombre_linea_n1' y
        'clase_cliente'/'nombre_clase_cliente': ahora son códigos
        numéricos separados de su nombre legible.
    anio : int | None
        Si se indica, filtra solo los registros de ese año exacto
        (lapso entre `anio*100+1` y `anio*100+12`).
    anio_desde : int | None
        Si se indica (y `anio` es None), filtra desde ese año en
        adelante (lapso >= `anio_desde*100+1`). Útil para "solo el año
        actual y el anterior", sin traer todo el histórico de la base
        de datos para luego descartarlo en pandas (mismo tipo de bug
        que 2.10, ver BUGS_Y_MEJORAS.md 2.16).

    Returns
    -------
    pandas.DataFrame con columnas: *campos_agrupacion, suma
    """
    qs = BdVentasComercial.objects.all()
    if anio is not None:
        qs = qs.filter(lapso__gte=anio * 100 + 1, lapso__lte=anio * 100 + 12)
    elif anio_desde is not None:
        qs = qs.filter(lapso__gte=anio_desde * 100 + 1)

    qs = qs.values(*campos_agrupacion).annotate(suma=Sum(campo_valor)).values(*campos_agrupacion, 'suma')
    df = pd.DataFrame(list(qs))

    if df.empty:
        return pd.DataFrame(columns=list(campos_agrupacion) + ['suma'])

    return df

def obtener_ventas_agrupadas_por_lapso(campo_valor, anio=None):
    """
    Atajo para el caso más simple: `obtener_ventas_agrupadas(campo_valor, ['lapso'])`,
    usado por el "presupuesto general" (ventas y costos).

    Con la tabla consolidada ya NO hace falta el "groupby('lapso') de
    seguridad" que tenía la versión anterior (existía por si un mismo
    `lapso` se repetía entre las tablas por año; ahora solo hay una
    tabla, así que el GROUP BY de la base de datos es suficiente).
    """
    return obtener_ventas_agrupadas(campo_valor, ['lapso'], anio=anio)

def extraer_anio_mes(df, columna_lapso='lapso'):
    """lapso = año*100 + mes (p. ej. 202503 -> 2025, mes 3)."""
    df = df.copy()
    df['year'] = df[columna_lapso] // 100
    df['mes'] = df[columna_lapso] % 100
    return df

def _merge_costos(df, df_costos, on, columnas):
    """
    merge que no revienta si la tabla de costos está vacía: en ese caso
    pd.DataFrame([]) no tiene columnas y pd.merge(on='year') lanza KeyError.
    """
    if df_costos.empty:
        for col in columnas:
            df[col] = 0
        return df
    return pd.merge(df, df_costos, on=on, how='left')

def indice_por_clave(queryset_values, campos_clave):
    """
    Convierte un queryset .values(...) en un diccionario indexado por
    una tupla de campos, para hacer lookups O(1).

    Sustituye el patrón:
        next((x for x in lista if x['campo'] == valor), None)
    que se repetía dentro de bucles en las funciones
    "actualizar_presupuesto_*" y que es O(n) por búsqueda (es decir,
    O(n^2) en total dentro de un bucle) -- ver BUGS_Y_MEJORAS.md punto 4.
    """
    indice = {}
    for item in queryset_values:
        clave = tuple(item[c] for c in campos_clave)
        indice[clave] = item
    return indice

@login_required
def base_comercial(request):
    # Quién entra: "admin" + los usuarios con Comercial asignado (Ajustes → Asignación de presupuestos).
    from .views_asignaciones import puede_entrar
    if not puede_entrar(request.user, "comercial"):
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    return render(request, 'presupuesto_comercial/base_presupuesto_comercial.html')

# ------------------------------------------PRESUPUESTO GENERAL VENTAS-----------------------------------------------------
def cargar_presupuesto_general_ventas(request):
    year_actual = timezone.now().year
    year_siguiente = year_actual + 1

    df_lapso_total = obtener_ventas_agrupadas_por_lapso('valor_neto')
    df_lapso_total = extraer_anio_mes(df_lapso_total)

    df_por_anio = df_lapso_total.groupby('year')['suma'].sum().reset_index()
    df_por_anio = df_por_anio.sort_values('year').reset_index(drop=True)
    df_por_anio['variacion_pesos'] = df_por_anio['suma'].diff().round().astype('Int64').fillna(0)
    df_por_anio['variacion_pct'] = (df_por_anio['suma'].pct_change() * 100).round(2).fillna(0)
    df_por_anio = df_por_anio.rename(columns={'suma': 'total'})

    df_costos = pd.DataFrame(list(
        PresupuestoGeneralCostos.objects.values('year', 'total_year')
    )).rename(columns={'total_year': 'total_year_costos'})
    df_por_anio = _merge_costos(df_por_anio, df_costos, 'year', ['total_year_costos'])

    correlaciones = []
    for mes in range(1, 13):
        datos_mes = df_lapso_total[df_lapso_total['mes'] == mes]
        if len(datos_mes) >= 2 and datos_mes['suma'].std() != 0:
            coef = np.corrcoef(datos_mes['year'], datos_mes['suma'])[0, 1]
        else:
            coef = np.nan
        correlaciones.append({'mes': mes, 'coef_correlacion': round(coef, 4) * 100 if not np.isnan(coef) else None})
    df_correl = pd.DataFrame(correlaciones)

    df_proyeccion = pd.merge(df_lapso_total, df_correl, on='mes', how='left')
    df_proyeccion['suma'] = df_proyeccion['suma'].round().astype(int)
    df_proyeccion = pd.merge(
        df_proyeccion,
        df_por_anio[['year', 'total', 'total_year_costos', 'variacion_pesos', 'variacion_pct']],
        on='year', how='left',
    )
    df_proyeccion['utilidad_pct'] = (
        (1 - (df_proyeccion['total_year_costos'] / df_proyeccion['total'])) * 100
    ).replace([np.inf, -np.inf], 0).fillna(0).round(2)
    df_proyeccion['utilidad_valor'] = (
        df_proyeccion['total'] - df_proyeccion['total_year_costos']
    ).round().astype(int)

    # 12 meses del año siguiente en cero (igual que el original)
    meses_siguiente = pd.DataFrame([{
        'lapso': year_siguiente * 100 + m, 'year': year_siguiente, 'mes': m, 'suma': 0,
        'coef_correlacion': 0, 'total': 0, 'total_year_costos': 0,
        'variacion_pesos': 0, 'variacion_pct': 0, 'utilidad_pct': 0, 'utilidad_valor': 0,
    } for m in range(1, 13)])
    df_proyeccion = pd.concat([df_proyeccion, meses_siguiente], ignore_index=True)

    with transaction.atomic():
        PresupuestoGeneralVentas.objects.all().delete()
        PresupuestoGeneralVentas.objects.bulk_create([
            PresupuestoGeneralVentas(
                year=int(row['year']), mes=int(row['mes']), total=int(row['suma']),
                r2=row['coef_correlacion'] or 0, total_year=row['total'] or 0,
                total_year_costos=row['total_year_costos'] or 0,
                variacion_valor=row['variacion_pesos'] or 0, variacion_pct=row['variacion_pct'] or 0,
                utilidad_pct=row['utilidad_pct'] or 0, utilidad_valor=row['utilidad_valor'] or 0,
            )
            for _, row in df_proyeccion.iterrows()
        ])

    return JsonResponse(list(PresupuestoGeneralVentas.objects.values()), safe=False)

from . import calculo

def obtener_presupuesto_general_ventas(request):
    return JsonResponse(calculo.construir_ventas('general'), safe=False)

def vista_presupuesto_general_ventas(request):
    return render(request, 'presupuesto_comercial/presupuesto_general_ventas.html')

# --------------------------PRESUPUESTO POR CENTRO OPERACION VENTAS------------------------
def cargar_presupuesto_centro_ventas(request):
    year_actual = timezone.now().year
    year_siguiente = year_actual + 1

    df_centro_operacion = obtener_ventas_agrupadas(
        'valor_neto', ['nombre_centro_de_operacion', 'lapso']
    ).rename(columns={'nombre_centro_de_operacion': 'nombre_centro_operacion'})
    df_centro_operacion = extraer_anio_mes(df_centro_operacion)

    df_proyeccion = df_centro_operacion[['nombre_centro_operacion', 'lapso', 'suma']].copy()
    df_proyeccion = df_proyeccion.sort_values(['nombre_centro_operacion', 'lapso']).reset_index(drop=True)
    df_proyeccion = extraer_anio_mes(df_proyeccion)

    correlaciones_centro = []
    for centro, grupo in df_proyeccion.groupby('nombre_centro_operacion'):
        for mes in range(1, 13):
            datos_mes = grupo[grupo["mes"] == mes]
            if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
                coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
            else:
                coef = np.nan
            correlaciones_centro.append({
                "nombre_centro_operacion": centro, "mes": mes,
                "coef_correlacion": round(coef, 4) * 100 if not np.isnan(coef) else None,
            })
    df_correl = pd.DataFrame(correlaciones_centro)
    df_proyeccion = pd.merge(df_proyeccion, df_correl, on=['nombre_centro_operacion', 'mes'], how='left')
    df_proyeccion['suma'] = df_proyeccion['suma'].round().astype(int)

    df_total_year_centro = (
        df_proyeccion.groupby(['nombre_centro_operacion', 'year'])['suma'].sum()
        .reset_index().rename(columns={'suma': 'total_year'})
    )
    df_total_year_centro['variacion_pesos'] = (
        df_total_year_centro.groupby('nombre_centro_operacion')['total_year'].diff().round().astype('Int64')
    )
    df_total_year_centro['variacion_pct'] = (
        df_total_year_centro.groupby('nombre_centro_operacion')['total_year'].pct_change() * 100
    ).round(2)
    df_total_year_centro[['variacion_pesos', 'variacion_pct']] = (
        df_total_year_centro[['variacion_pesos', 'variacion_pct']].fillna(0)
    )

    df_costos = pd.DataFrame(list(
        PresupuestoCentroOperacionCostos.objects.values("year", "nombre_centro_operacion", "total_year")
    )).rename(columns={"total_year": "total_year_costos"})
    df_total_year_centro = _merge_costos(
        df_total_year_centro, df_costos,
        ['nombre_centro_operacion', 'year'], ['total_year_costos'],
    )

    df_proyeccion = pd.merge(
        df_proyeccion,
        df_total_year_centro[['nombre_centro_operacion', 'year', 'total_year', 'total_year_costos', 'variacion_pesos', 'variacion_pct']],
        on=["nombre_centro_operacion", "year"], how='left',
    )

    df_proyeccion['utilidad_pct'] = (
        (1 - (df_proyeccion['total_year_costos'] / df_proyeccion['total_year'])) * 100
    ).replace([np.inf, -np.inf], 0).fillna(0).round(2)
    df_proyeccion['utilidad_valor'] = (
        df_proyeccion['total_year'] - df_proyeccion['total_year_costos']
    ).round().astype(int)

    centros_existentes = df_proyeccion["nombre_centro_operacion"].dropna().unique()
    filas_siguiente = [{
        "lapso": year_siguiente * 100 + m, "nombre_centro_operacion": centro,
        "year": year_siguiente, "mes": m, "suma": 0, "coef_correlacion": 0,
        "total_year": 0, "total_year_costos": 0, "variacion_pesos": 0, "variacion_pct": 0,
        "utilidad_pct": 0, "utilidad_valor": 0,
    } for centro in centros_existentes for m in range(1, 13)]
    df_proyeccion = pd.concat([df_proyeccion, pd.DataFrame(filas_siguiente)], ignore_index=True)

    with transaction.atomic():
        PresupuestoCentroOperacionVentas.objects.all().delete()
        PresupuestoCentroOperacionVentas.objects.bulk_create([
            PresupuestoCentroOperacionVentas(
                nombre_centro_operacion=row['nombre_centro_operacion'],
                year=int(row['year']), mes=int(row['mes']), total=int(row['suma']),
                r2=row['coef_correlacion'] if row['coef_correlacion'] is not None else 0,
                total_year=row['total_year'] if row['total_year'] is not None else 0,
                total_year_costos=row['total_year_costos'] if row['total_year_costos'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0,
                utilidad_pct=row['utilidad_pct'] if row['utilidad_pct'] is not None else 0,
                utilidad_valor=row['utilidad_valor'] if row['utilidad_valor'] is not None else 0,
            )
            for _, row in df_proyeccion.iterrows()
        ])

    return JsonResponse(list(PresupuestoCentroOperacionVentas.objects.values()), safe=False)
 
def obtener_presupuesto_centro_ventas(request):
    return JsonResponse(calculo.construir_ventas('centro'), safe=False)

def vista_presupuesto_centro_ventas(request):
    return render(request, 'presupuesto_comercial/presupuesto_centro_ventas.html') 

#---------------PRESUPUESTO POR CENTRO OPERACION - SEGMENTO VENTAS--------
def cargar_presupuesto_centro_segmento_ventas(request):
    year_actual = timezone.now().year 
    year_siguiente = year_actual + 1

    df_cs = obtener_ventas_agrupadas(
        'valor_neto', ['nombre_clase_cliente', 'nombre_centro_de_operacion', 'lapso']
    )
    df_cs = extraer_anio_mes(df_cs)

    df_proyeccion = df_cs[['nombre_centro_de_operacion', 'nombre_clase_cliente', 'lapso', 'suma']].copy()
    df_proyeccion = df_proyeccion.sort_values(
        ['nombre_centro_de_operacion', 'nombre_clase_cliente', 'lapso']
    ).reset_index(drop=True)
    df_proyeccion = extraer_anio_mes(df_proyeccion)

    correlaciones = []
    for (centro, segmento), grupo in df_proyeccion.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente']):
        for mes in range(1, 13):
            datos_mes = grupo[grupo["mes"] == mes]
            if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
                coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
            else:
                coef = 0
            correlaciones.append({
                "nombre_centro_de_operacion": centro, "nombre_clase_cliente": segmento, "mes": mes,
                "coef_correlacion": round(coef, 4) * 100 if not np.isnan(coef) else None,
            })
    df_correl = pd.DataFrame(correlaciones)
    df_proyeccion = pd.merge(
        df_proyeccion, df_correl, on=['nombre_centro_de_operacion', 'nombre_clase_cliente', 'mes'], how='left'
    )
    df_proyeccion['suma'] = df_proyeccion['suma'].round().astype(int)

    df_total_year = (
        df_proyeccion.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'])['suma'].sum()
        .reset_index().rename(columns={'suma': 'total_year'})
    )
    df_total_year['variacion_pesos'] = (
        df_total_year.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente'])['total_year']
        .diff().round().astype('Int64')
    )
    df_total_year['variacion_pct'] = (
        df_total_year.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente'])['total_year']
        .pct_change() * 100
    ).round(2)
    df_total_year[['variacion_pesos', 'variacion_pct']] = df_total_year[['variacion_pesos', 'variacion_pct']].fillna(0)

    df_costos = pd.DataFrame(list(
        PresupuestoCentroSegmentoCostos.objects.values("year", "nombre_centro_operacion", "segmento", "total_year")
    )).rename(columns={"total_year": "total_year_costos"})
    if df_costos.empty:
        df_total_year['total_year_costos'] = 0
    else:
        df_total_year = pd.merge(
            df_total_year, df_costos,
            left_on=["nombre_centro_de_operacion", "nombre_clase_cliente", "year"],
            right_on=["nombre_centro_operacion", "segmento", "year"], how="left",
        ).drop(columns=["nombre_centro_operacion", "segmento"], errors="ignore")

    df_proyeccion = pd.merge(
        df_proyeccion,
        df_total_year[['nombre_centro_de_operacion', 'nombre_clase_cliente', 'year', 'total_year', 'total_year_costos', 'variacion_pesos', 'variacion_pct']],
        on=["nombre_centro_de_operacion", "nombre_clase_cliente", "year"], how="left",
    )

    df_proyeccion['utilidad_pct'] = (
        (1 - (df_proyeccion['total_year_costos'] / df_proyeccion['total_year'])) * 100
    ).replace([np.inf, -np.inf], 0).fillna(0).round(2)
    df_proyeccion['utilidad_valor'] = (
        df_proyeccion['total_year'] - df_proyeccion['total_year_costos']
    ).round().astype(int)

    centros = df_proyeccion["nombre_centro_de_operacion"].dropna().unique()
    segmentos = df_proyeccion["nombre_clase_cliente"].dropna().unique()
    filas_siguiente = [{
        "lapso": year_siguiente * 100 + m,
        "nombre_centro_de_operacion": centro, "nombre_clase_cliente": segmento,
        "year": year_siguiente, "mes": m, "suma": 0, "coef_correlacion": 0,
        "total_year": 0, "total_year_costos": 0, "variacion_pesos": 0, "variacion_pct": 0,
        "utilidad_pct": 0, "utilidad_valor": 0,
    } for centro in centros for segmento in segmentos for m in range(1, 13)]
    df_proyeccion = pd.concat([df_proyeccion, pd.DataFrame(filas_siguiente)], ignore_index=True)

    with transaction.atomic():
        PresupuestoCentroSegmentoVentas.objects.all().delete()
        PresupuestoCentroSegmentoVentas.objects.bulk_create([
            PresupuestoCentroSegmentoVentas(
                nombre_centro_operacion=row['nombre_centro_de_operacion'],
                segmento=row['nombre_clase_cliente'],
                year=int(row['year']), mes=int(row['mes']), total=int(row['suma']),
                r2=row['coef_correlacion'] if row['coef_correlacion'] is not None else 0,
                total_year=row['total_year'] if row['total_year'] is not None else 0,
                total_year_costos=row['total_year_costos'] if row['total_year_costos'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0,
                utilidad_pct=row['utilidad_pct'] if row['utilidad_pct'] is not None else 0,
                utilidad_valor=row['utilidad_valor'] if row['utilidad_valor'] is not None else 0,
            )
            for _, row in df_proyeccion.iterrows()
        ])

    return JsonResponse(list(PresupuestoCentroSegmentoVentas.objects.values()), safe=False)

def obtener_presupuesto_centro_segmento_ventas(request):
    return JsonResponse(calculo.construir_ventas('centro_segmento'), safe=False)

def vista_presupuesto_centro_segmento_ventas(request):
    return render(request, 'presupuesto_comercial/presupuesto_centro_segmento_ventas.html')

#-----------PRESUPUESTO GENERAL COSTOS
def cargar_presupuesto_general_costos(request):
    year_actual = timezone.now().year
    year_siguiente = year_actual + 1

    df_lapso_total = obtener_ventas_agrupadas_por_lapso('valor_costo')
    df_lapso_total = extraer_anio_mes(df_lapso_total)

    df_por_year_mes = df_lapso_total.groupby(["year", "mes"])["suma"].sum().reset_index()

    predicciones = []
    for mes in range(1, 13):
        datos_mes = df_por_year_mes[df_por_year_mes["mes"] == mes]
        x = datos_mes["year"].values
        y = datos_mes["suma"].values
        if len(x) >= 2:
            a, b = np.polyfit(x, y, 1)
            y_pred = a * year_siguiente + b
            predicciones.append({
                "year": year_siguiente, "mes": mes,
                "suma_pred": round(y_pred), "lapso": year_siguiente * 100 + mes,
            })
    df_pred = pd.DataFrame(predicciones)

    partes = [df_lapso_total[['lapso', 'suma']]]
    if not df_pred.empty:
        partes.append(df_pred[['lapso', 'suma_pred']].rename(columns={'suma_pred': 'suma'}))
    df_proyeccion = pd.concat(partes, ignore_index=True)
    df_proyeccion = extraer_anio_mes(df_proyeccion)

    correlaciones = []
    for mes in range(1, 13):
        datos_mes = df_proyeccion[df_proyeccion["mes"] == mes]
        if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
            coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
        else:
            coef = np.nan
        correlaciones.append({"mes": mes, "coef_correlacion": round(coef, 4) * 100 if not np.isnan(coef) else None})
    df_correl = pd.DataFrame(correlaciones)

    df_proyeccion = pd.merge(df_proyeccion, df_correl, on='mes', how='left')
    df_proyeccion['suma'] = df_proyeccion['suma'].round().astype(int)

    df_por_anio = df_proyeccion.groupby("year")["suma"].sum().reset_index().sort_values("year").reset_index(drop=True)
    df_por_anio["variacion_pesos"] = df_por_anio["suma"].diff().round().astype('Int64').fillna(0)
    df_por_anio["variacion_pct"] = (df_por_anio["suma"].pct_change() * 100).round(2).fillna(0)
    df_por_anio = df_por_anio.rename(columns={'suma': 'total'})

    df_proyeccion = pd.merge(
        df_proyeccion, df_por_anio[['year', 'total', 'variacion_pesos', 'variacion_pct']],
        on='year', how='left',
    )

    with transaction.atomic():
        PresupuestoGeneralCostos.objects.all().delete()
        PresupuestoGeneralCostos.objects.bulk_create([
            PresupuestoGeneralCostos(
                year=int(row['year']), mes=int(row['mes']), total=int(row['suma']),
                r2=row['coef_correlacion'] if row['coef_correlacion'] is not None else 0,
                total_year=row['total'] if row['total'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0,
            )
            for _, row in df_proyeccion.iterrows()
        ])

    return JsonResponse(list(PresupuestoGeneralCostos.objects.values()), safe=False)

def obtener_presupuesto_general_costos(request):
    return JsonResponse(calculo.construir_costos('general'), safe=False)

def vista_presupuesto_general_costos(request):
    return render(request, 'presupuesto_comercial/presupuesto_general_costos.html')

#-----------PRESUPUESTO POR CENTRO OPERACION - COSTOS
def cargar_presupuesto_centro_costos(request):
    year_actual = timezone.now().year
    year_siguiente = year_actual + 1

    df_centro_operacion = obtener_ventas_agrupadas(
        'valor_costo', ['nombre_centro_de_operacion', 'lapso']
    )
    df_centro_operacion = extraer_anio_mes(df_centro_operacion)

    predicciones_centro = []
    for centro, grupo in df_centro_operacion.groupby('nombre_centro_de_operacion'):
        for mes in range(1, 13):
            datos_mes = grupo[grupo['mes'] == mes]
            x = datos_mes['year'].values
            y = datos_mes['suma'].values
            if len(x) >= 2:
                a, b = np.polyfit(x, y, 1)
                y_pred = a * year_siguiente + b
                predicciones_centro.append({
                    'nombre_centro_de_operacion': centro,
                    'lapso': year_siguiente * 100 + mes, 'suma': round(y_pred),
                })
    df_pred = pd.DataFrame(predicciones_centro)

    partes = [df_centro_operacion[['nombre_centro_de_operacion', 'lapso', 'suma']]]
    if not df_pred.empty:
        partes.append(df_pred)
    df_proyeccion = pd.concat(partes, ignore_index=True)
    df_proyeccion = df_proyeccion.sort_values(['nombre_centro_de_operacion', 'lapso']).reset_index(drop=True)
    df_proyeccion = extraer_anio_mes(df_proyeccion)

    correlaciones_centro = []
    for centro, grupo in df_proyeccion.groupby('nombre_centro_de_operacion'):
        for mes in range(1, 13):
            datos_mes = grupo[grupo["mes"] == mes]
            if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
                coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
            else:
                coef = np.nan
            correlaciones_centro.append({
                "nombre_centro_de_operacion": centro, "mes": mes,
                "coef_correlacion": round(coef, 4) * 100 if not np.isnan(coef) else None,
            })
    df_correl = pd.DataFrame(correlaciones_centro)
    df_proyeccion = pd.merge(df_proyeccion, df_correl, on=['nombre_centro_de_operacion', 'mes'], how='left')
    df_proyeccion['suma'] = df_proyeccion['suma'].round().astype(int)

    df_total_year_centro = (
        df_proyeccion.groupby(['nombre_centro_de_operacion', 'year'])['suma'].sum()
        .reset_index().rename(columns={'suma': 'total_year'})
    )
    df_total_year_centro['variacion_pesos'] = (
        df_total_year_centro.groupby('nombre_centro_de_operacion')['total_year'].diff().round().astype('Int64')
    )
    df_total_year_centro['variacion_pct'] = (
        df_total_year_centro.groupby('nombre_centro_de_operacion')['total_year'].pct_change() * 100
    ).round(2)
    df_total_year_centro[['variacion_pesos', 'variacion_pct']] = (
        df_total_year_centro[['variacion_pesos', 'variacion_pct']].fillna(0)
    )

    df_proyeccion = pd.merge(
        df_proyeccion,
        df_total_year_centro[['nombre_centro_de_operacion', 'year', 'total_year', 'variacion_pesos', 'variacion_pct']],
        on=['nombre_centro_de_operacion', 'year'], how='left',
    )

    with transaction.atomic():
        PresupuestoCentroOperacionCostos.objects.all().delete()
        PresupuestoCentroOperacionCostos.objects.bulk_create([
            PresupuestoCentroOperacionCostos(
                nombre_centro_operacion=row['nombre_centro_de_operacion'],
                year=int(row['year']), mes=int(row['mes']), total=int(row['suma']),
                r2=row['coef_correlacion'] if row['coef_correlacion'] is not None else 0,
                total_year=row['total_year'] if row['total_year'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0,
            )
            for _, row in df_proyeccion.iterrows()
        ])

    return JsonResponse(list(PresupuestoCentroOperacionCostos.objects.values()), safe=False)

def obtener_presupuesto_centro_costos(request):
    return JsonResponse(calculo.construir_costos('centro'), safe=False)

def vista_presupuesto_centro_costos(request):
    return render(request, 'presupuesto_comercial/presupuesto_centro_costos.html')

#--------------------------PRESUPUESTO CENTRO OPERACION - SEGMENTO COSTOS---------------
def cargar_presupuesto_centro_segmento_costos(request):
    year_actual = timezone.now().year
    year_siguiente = year_actual + 1

    df_cs = obtener_ventas_agrupadas(
        'valor_costo', ['nombre_clase_cliente', 'nombre_centro_de_operacion', 'lapso']
    )
    df_cs = extraer_anio_mes(df_cs)

    predicciones = []
    for (centro, segmento), grupo in df_cs.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente']):
        for mes in range(1, 13):
            datos_mes = grupo[grupo['mes'] == mes]
            x = datos_mes['year'].values
            y = datos_mes['suma'].values
            if len(x) >= 2:
                a, b = np.polyfit(x, y, 1)
                y_pred = a * year_siguiente + b
                predicciones.append({
                    'nombre_centro_de_operacion': centro, 'nombre_clase_cliente': segmento,
                    'lapso': year_siguiente * 100 + mes, 'suma': round(y_pred),
                })
    df_pred = pd.DataFrame(predicciones)

    partes = [df_cs[['nombre_centro_de_operacion', 'nombre_clase_cliente', 'lapso', 'suma']]]
    if not df_pred.empty:
        partes.append(df_pred)
    df_proyeccion = pd.concat(partes, ignore_index=True)
    df_proyeccion = df_proyeccion.sort_values(
        ['nombre_centro_de_operacion', 'nombre_clase_cliente', 'lapso']
    ).reset_index(drop=True)
    df_proyeccion = extraer_anio_mes(df_proyeccion)

    correlaciones = []
    for (centro, segmento), grupo in df_proyeccion.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente']):
        for mes in range(1, 13):
            datos_mes = grupo[grupo["mes"] == mes]
            if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
                coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
            else:
                coef = 0
            correlaciones.append({
                "nombre_centro_de_operacion": centro, "nombre_clase_cliente": segmento, "mes": mes,
                "coef_correlacion": round(coef, 4) * 100 if not np.isnan(coef) else None,
            })
    df_correl = pd.DataFrame(correlaciones)
    df_proyeccion = pd.merge(
        df_proyeccion, df_correl, on=['nombre_centro_de_operacion', 'nombre_clase_cliente', 'mes'], how='left'
    )
    df_proyeccion['suma'] = df_proyeccion['suma'].round().astype(int)

    df_total_year = (
        df_proyeccion.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'])['suma'].sum()
        .reset_index().rename(columns={'suma': 'total_year'})
    )
    df_total_year['variacion_pesos'] = (
        df_total_year.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente'])['total_year']
        .diff().round().astype('Int64')
    )
    df_total_year['variacion_pct'] = (
        df_total_year.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente'])['total_year']
        .pct_change() * 100
    ).round(2)
    df_total_year[['variacion_pesos', 'variacion_pct']] = df_total_year[['variacion_pesos', 'variacion_pct']].fillna(0)

    df_proyeccion = pd.merge(
        df_proyeccion,
        df_total_year[['nombre_centro_de_operacion', 'nombre_clase_cliente', 'year', 'total_year', 'variacion_pesos', 'variacion_pct']],
        on=['nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'], how='left',
    )

    with transaction.atomic():
        PresupuestoCentroSegmentoCostos.objects.all().delete()
        PresupuestoCentroSegmentoCostos.objects.bulk_create([
            PresupuestoCentroSegmentoCostos(
                nombre_centro_operacion=row['nombre_centro_de_operacion'],
                segmento=row['nombre_clase_cliente'],
                year=int(row['year']), mes=int(row['mes']), total=int(row['suma']),
                r2=row['coef_correlacion'] if row['coef_correlacion'] is not None else 0,
                total_year=row['total_year'] if row['total_year'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0,
            )
            for _, row in df_proyeccion.iterrows()
        ])

    return JsonResponse(list(PresupuestoCentroSegmentoCostos.objects.values()), safe=False)

def obtener_presupuesto_centro_segmento_costos(request):
    return JsonResponse(calculo.construir_costos('centro_segmento'), safe=False)

def vista_presupuesto_centro_segmento_costos(request):
    return render(request, 'presupuesto_comercial/presupuesto_centro_segmento_costos.html')

# --------------------------PRESUPUESTO CENTRO OPERACION - SEGMENTO - LINEA COSTOS---------------
def cargar_presupuesto_centro_segmento_linea_costos(request):
    df_merged = aux_presupuesto_centro_segmento_linea_costos()

    with transaction.atomic():
        PresupuestoCentroSegLineaCostos.objects.all().delete()
        PresupuestoCentroSegLineaCostos.objects.bulk_create([
            PresupuestoCentroSegLineaCostos(
                linea=row['nombre_linea_n1'],
                nombre_centro_operacion=row['nombre_centro_de_operacion'],
                segmento=row['nombre_clase_cliente'],
                year=int(row['year']), mes=int(row['mes']), total=int(row['suma']),
                total_year=row['total_year'] if row['total_year'] is not None else 0,
            )
            for _, row in df_merged.iterrows()
        ])

    return JsonResponse(list(PresupuestoCentroSegLineaCostos.objects.values()), safe=False)

def obtener_presupuesto_centro_segmento_linea_costos(request):
    return JsonResponse(calculo.construir_costos('centro_segmento_linea'), safe=False)


def aux_presupuesto_centro_segmento_linea_costos():
    """
    Detalle mensual de costos por línea+centro+segmento del año
    `_anio_detalle_linea`, con el total anual (`total_year`) ya unido.
    La usan tanto la vista de costos como la de ventas (para calcular
    la utilidad).
    """
    df = obtener_ventas_agrupadas(
        'valor_costo',
        ['nombre_linea_n1', 'nombre_clase_cliente', 'nombre_centro_de_operacion', 'lapso'],
        anio=_anio_detalle_linea(),
    )
    df = extraer_anio_mes(df)
    df = df.sort_values(
        ['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'lapso']
    ).reset_index(drop=True)
    df['suma'] = df['suma'].round().astype(int)

    df_total_year = (
        df.groupby(['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'])['suma']
        .sum().reset_index().rename(columns={'suma': 'total_year'})
    )
    return df.merge(
        df_total_year,
        on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'],
        how='left',
    )

def vista_presupuesto_centro_segmento_linea_costos(request):
    return render(request, 'presupuesto_comercial/presupuesto_centro_segmento_linea_costos.html')

# --------------------------PRESUPUESTO CENTRO OPERACION - SEGMENTO - LINEA VENTAS---------------
def cargar_presupuesto_centro_segmento_linea_ventas(request):
    year_siguiente = _anio_detalle_linea() + 1  # antes: literal "2026"

    df = obtener_ventas_agrupadas(
        'valor_neto',
        ['nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente'],
        anio=_anio_detalle_linea(),
    )
    if df.empty:
        return JsonResponse([], safe=False)
    df = extraer_anio_mes(df)

    df_total_anual = (
        df.groupby(['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'])['suma']
        .sum().reset_index().rename(columns={'suma': 'total_year'})
    )
    df_total_year = df.merge(
        df_total_anual,
        on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'],
        how='left',
    )
    df_total_year = df_total_year.sort_values(
        ['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year']
    )
    df_total_year['variacion_pesos'] = (
        df_total_year.groupby(['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente'])['total_year']
        .diff().fillna(0).round().astype('Int64')
    )
    df_total_year['variacion_pct'] = (
        df_total_year.groupby(['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente'])['total_year']
        .pct_change().fillna(0) * 100
    ).round(2)

    df_costos = aux_presupuesto_centro_segmento_linea_costos().rename(columns={'total_year': 'total_year_costos'})
    df_merged = df_total_year.merge(
        df_costos[
            ['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year', 'total_year_costos']
        ].drop_duplicates(),
        on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'],
        how='left',
    )
    df_merged['total_year_costos'] = df_merged['total_year_costos'].fillna(0)

    df_merged['utilidad_pct'] = (
        (1 - (df_merged['total_year_costos'] / df_merged['total_year'])) * 100
    ).replace([np.inf, -np.inf], 0).fillna(0).round(2)
    df_merged['utilidad_valor'] = (df_merged['total_year'] - df_merged['total_year_costos']).round().astype(int)

    centros = df['nombre_centro_de_operacion'].unique()
    segmentos = df['nombre_clase_cliente'].unique()
    lineas = df['nombre_linea_n1'].unique()
    filas_siguiente = [{
        "lapso": year_siguiente * 100 + mes,
        "nombre_linea_n1": linea, "nombre_centro_de_operacion": centro, "nombre_clase_cliente": segmento,
        "year": year_siguiente, "mes": mes, "suma": 0, "total_year": 0, "total_year_costos": 0,
        "variacion_pesos": 0, "variacion_pct": 0, "utilidad_pct": 0, "utilidad_valor": 0, "total_proyectado": 0,
    } for linea in lineas for centro in centros for segmento in segmentos for mes in range(1, 13)]
    df_final_linea = pd.concat([df_merged, pd.DataFrame(filas_siguiente)], ignore_index=True)
    df_final_linea = df_final_linea.fillna(0)

    with transaction.atomic():
        PresupuestoCentroSegLineaVentas.objects.all().delete()
        PresupuestoCentroSegLineaVentas.objects.bulk_create([
            PresupuestoCentroSegLineaVentas(
                linea=row['nombre_linea_n1'],
                nombre_centro_operacion=row['nombre_centro_de_operacion'],
                segmento=row['nombre_clase_cliente'],
                year=int(row['year']), mes=int(row['mes']), total=int(row['suma']),
                total_year=row['total_year'] if row['total_year'] is not None else 0,
                total_year_costos=row['total_year_costos'] if row['total_year_costos'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0,
                utilidad_valor=row['utilidad_valor'] if row['utilidad_valor'] is not None else 0,
                utilidad_pct=row['utilidad_pct'] if row['utilidad_pct'] is not None else 0.0,
            )
            for _, row in df_final_linea.iterrows()
        ])

    return JsonResponse(list(PresupuestoCentroSegLineaVentas.objects.values()), safe=False)

def obtener_presupuesto_centro_segmento_linea_ventas(request):
    return JsonResponse(calculo.construir_ventas('centro_segmento_linea'), safe=False)

def vista_presupuesto_centro_segmento_linea_ventas(request):
    return render(request, 'presupuesto_comercial/presupuesto_centro_segmento_linea_ventas.html')

#----------------PRESUPUESTO COMERCIAL PRINCIPAL-----------------------
def _pronostico_por_linea_centro_segmento(campo_valor, anio_inicio=2020):
    """
    Lógica compartida entre `aux_presupuesto_comercial_costos` y
    `cargar_presupuesto_comercial` (antes casi 80 líneas duplicadas
    entre las dos): arma el histórico por línea+centro+segmento+año
    desde `anio_inicio` hasta el año actual, rellena los años faltantes
    con 0, y calcula R² y variaciones año contra año.

    `anio_inicio` por defecto es 2020 (todo el histórico), pero
    `cargar_presupuesto_comercial` lo llama con `year_actual - 1`
    porque, para la proyección del presupuesto comercial, solo hace
    falta comparar el año actual contra el anterior — no todo el
    histórico (ver BUGS_Y_MEJORAS.md 2.16).
    """
    year_actual = timezone.now().year

    df = obtener_ventas_agrupadas(
        campo_valor,
        ['nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente'],
        anio_desde=anio_inicio,
    )
    df = extraer_anio_mes(df)
    COLUMNAS_PRONOSTICO = [
        'nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente',
        'year', 'suma', 'R2', 'suma_anterior', 'variacion_pct', 'variacion_valor',
        'variacion_mes', 'variacion_precios', 'crecimiento_comercial',
        'crecimiento_comercial_mes',
    ]
    if df.empty:
        # Sin ventas en el rango pedido: se devuelve la estructura vacía pero
        # con todas las columnas, para que los merge() de más abajo y los de
        # calcular_comercial() no fallen con KeyError.
        return pd.DataFrame(columns=COLUMNAS_PRONOSTICO)
    df_agrupado = (
        df.groupby(['nombre_linea_n1', 'year', 'nombre_centro_de_operacion', 'nombre_clase_cliente'])['suma']
        .sum().reset_index().sort_values(by=['nombre_linea_n1', 'year'])
    )

    # FIX bug 2.4: antes "range(2020, 2026)" hardcodeado en cargar_presupuesto_comercial.
    anios = list(range(anio_inicio, year_actual + 1))
    df_completo = pd.MultiIndex.from_product(
        [
            df_agrupado['nombre_linea_n1'].unique(),
            df_agrupado['nombre_centro_de_operacion'].unique(),
            df_agrupado['nombre_clase_cliente'].unique(),
            anios,
        ],
        names=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'],
    ).to_frame(index=False)
    df_final = df_completo.merge(
        df_agrupado, on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'], how='left'
    )
    df_final['suma'] = df_final['suma'].fillna(0)

    correlaciones = []
    for (nombre, centro, clase), grupo in df_final.groupby(
        ['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente']
    ):
        x = grupo['year'].values
        y = grupo['suma'].values
        if len(x) >= 2 and np.std(y) != 0 and np.std(x) != 0:
            coef_abs_pct = abs(np.corrcoef(x, y)[0, 1]) * 100
        else:
            coef_abs_pct = 0.0
        correlaciones.append({
            'nombre_linea_n1': nombre, 'nombre_centro_de_operacion': centro,
            'nombre_clase_cliente': clase, 'R2': round(coef_abs_pct, 2),
        })
    df_correlaciones = pd.DataFrame(correlaciones)
    if df_correlaciones.empty:
        df_final['R2'] = 0.0
    else:
        df_final = pd.merge(
            df_final, df_correlaciones,
            on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente'], how='left',
        )

    df_final['suma_anterior'] = df_final.groupby(
        ['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente']
    )['suma'].shift(1)
    df_final['variacion_pct'] = np.where(
        df_final['suma_anterior'] == 0, 0,
        ((df_final['suma'] - df_final['suma_anterior']) / df_final['suma_anterior']) * 100,
    ).round(2)
    df_final['variacion_valor'] = (df_final['suma'] - df_final['suma_anterior']).fillna(0)
    df_final['variacion_mes'] = (df_final['variacion_valor'] / 12).round().astype(int)
    df_final['variacion_precios'] = (df_final['suma_anterior'] * 0.02).round().fillna(0).astype(int)
    df_final['crecimiento_comercial'] = (
        df_final['variacion_valor'] - df_final['variacion_precios']
    ).round().astype(int)
    df_final['crecimiento_comercial_mes'] = (df_final['crecimiento_comercial'] / 12).round().astype(int)

    cols_variaciones = [
        'variacion_pct', 'variacion_valor', 'variacion_mes', 'variacion_precios',
        'crecimiento_comercial', 'crecimiento_comercial_mes',
    ]
    df_final[cols_variaciones] = df_final[cols_variaciones].fillna(0)

    return df_final

def aux_presupuesto_comercial_costos():
    """
    Pronóstico de costos por línea+centro+segmento, comparando el año
    actual contra el anterior (ver bug 2.16: antes traía 2020..año
    actual completo aunque solo se usaba el año actual).
    """
    year_actual = timezone.now().year
    return _pronostico_por_linea_centro_segmento('valor_costo', anio_inicio=year_actual - 1)

def _guardar_crecimientos(nuevos, year_actual):
    """Guarda {(linea, centro, clase): crecimiento %} del año actual.

    La usan la edición en pantalla y la subida del Excel, así las dos guardan
    igual: si la combinación no tiene fila se crea, y si la tabla quedó con la
    misma combinación repetida (filas viejas), se actualizan TODAS las copias
    (antes la subida del Excel cambiaba solo una y la pantalla podía leer otra).
    Devuelve cuántas combinaciones cambiaron de verdad.
    """
    clave = lambda linea, centro, clase: (str(linea or ""), str(centro or ""), str(clase or ""))  # noqa: E731
    with transaction.atomic():
        existentes = defaultdict(list)
        for p in PresupuestoComercial.objects.select_for_update().filter(year=year_actual):
            existentes[clave(p.linea, p.nombre_centro_de_operacion, p.nombre_clase_cliente)].append(p)
        actualizar, crear, cambios = [], [], 0
        for (linea, centro, clase), valor in nuevos.items():
            filas = existentes.get((linea, centro, clase))
            if not filas:
                crear.append(PresupuestoComercial(
                    linea=linea, year=year_actual, nombre_centro_de_operacion=centro,
                    nombre_clase_cliente=clase, crecimiento_ventas=valor))
                cambios += 1
                continue
            distintas = [p for p in filas if p.crecimiento_ventas != valor]
            for p in distintas:
                p.crecimiento_ventas = valor
            actualizar.extend(distintas)
            cambios += bool(distintas)
        PresupuestoComercial.objects.bulk_update(actualizar, ["crecimiento_ventas"], batch_size=500)
        PresupuestoComercial.objects.bulk_create(crear, batch_size=500)
    return cambios


@csrf_exempt
def guardar_presupuesto_comercial(request):
    """Guarda el % de crecimiento de ventas de las filas recibidas (solo año actual).

    La pantalla envía SOLO las filas que cambiaron (antes mandaba la tabla
    completa y se hacían 2 consultas por fila: con miles de filas el guardado
    tardaba tanto que se quedaba en "Guardando…").

    Es seguro repetir el mismo envío (el navegador reintenta si el servidor no
    responde): deja exactamente los mismos valores.
    Responde `cambios` = cuántos crecimientos cambiaron de verdad; la pantalla
    usa ese dato para recalcular el presupuesto de ventas solo cuando hace falta.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "mensaje": "Método no permitido"}, status=405)
    try:
        data = json.loads(request.body)
        if not isinstance(data, list):
            raise ValueError("Se esperaba una lista de filas")
        year_actual = timezone.now().year
        clave = lambda linea, centro, clase: (str(linea or ""), str(centro or ""), str(clase or ""))

        nuevos = {}
        for row in data:
            if int(row.get("year", 0)) != year_actual:
                continue          # solo el año actual es editable
            nuevos[clave(row["linea"], row.get("nombre_centro_de_operacion"),
                          row.get("nombre_clase_cliente"))] = float(row.get("crecimiento_ventas") or 0)

        cambios = _guardar_crecimientos(nuevos, year_actual)
        return JsonResponse({"status": "ok", "mensaje": "Crecimientos guardados ✅",
                             "recibidas": len(nuevos), "cambios": cambios})
    except DatabaseError:
        # Base de datos no disponible (p. ej. durante un despliegue): el navegador reintenta.
        return JsonResponse({"status": "error", "reintentar": True,
                             "mensaje": "La base de datos no está disponible en este momento"}, status=503)
    except (ValueError, TypeError, KeyError) as e:
        return JsonResponse({"status": "error", "mensaje": f"Datos inválidos: {e}"}, status=400)

# =====================================================================
# NUEVO: comparativo año anterior vs año actual (para visualizar
# crecimiento). No depende de `PresupuestoComercial` — la calcula al
# vuelo desde `BdVentasComercial`, porque `PresupuestoComercial` ahora
# solo guarda el año actual (ver bug 2.16) y no serviría para comparar.
# =====================================================================
def obtener_comparativo_anual(request):
    """
    Ventas y costos por línea+centro+segmento, año anterior vs año
    actual, con variación $ y % y margen de cada año — para el template
    de comparativo de crecimiento.
    """
    year_actual = timezone.now().year
    year_anterior = year_actual - 1

    df_ventas = _pronostico_por_linea_centro_segmento('valor_neto', anio_inicio=year_anterior)
    df_costos = _pronostico_por_linea_centro_segmento('valor_costo', anio_inicio=year_anterior)

    columnas_base = ['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente']

    df_ventas = df_ventas[df_ventas['year'] == year_actual][
        columnas_base + ['suma', 'suma_anterior', 'variacion_valor', 'variacion_pct']
    ].rename(columns={
        'suma': 'ventas_actual', 'suma_anterior': 'ventas_anterior',
        'variacion_valor': 'variacion_valor_ventas', 'variacion_pct': 'variacion_pct_ventas',
    })

    df_costos = df_costos[df_costos['year'] == year_actual][
        columnas_base + ['suma', 'suma_anterior', 'variacion_valor', 'variacion_pct']
    ].rename(columns={
        'suma': 'costos_actual', 'suma_anterior': 'costos_anterior',
        'variacion_valor': 'variacion_valor_costos', 'variacion_pct': 'variacion_pct_costos',
    })

    df = pd.merge(df_ventas, df_costos, on=columnas_base, how='outer').fillna(0)

    df['margen_pct_anterior'] = (
        (1 - (df['costos_anterior'] / df['ventas_anterior'])) * 100
    ).replace([np.inf, -np.inf], 0).fillna(0).round(2)
    df['margen_pct_actual'] = (
        (1 - (df['costos_actual'] / df['ventas_actual'])) * 100
    ).replace([np.inf, -np.inf], 0).fillna(0).round(2)

    for col in ['ventas_anterior', 'ventas_actual', 'variacion_valor_ventas',
                'costos_anterior', 'costos_actual', 'variacion_valor_costos']:
        df[col] = df[col].round().astype(int)

    df = df.rename(columns={
        'nombre_linea_n1': 'linea',
        'nombre_centro_de_operacion': 'centro',
        'nombre_clase_cliente': 'segmento',
    })

    return JsonResponse({
        'year_anterior': year_anterior,
        'year_actual': year_actual,
        'data': df.to_dict(orient='records'),
    })

def vista_comparativo_anual(request):
    return render(request, 'presupuesto_comercial/presupuesto_comparativo_anual.html')

# Ajustar para que la suma sea igual a 100
def ajustar_porcentaje(grupo):
    suma_porcentajes = grupo['porcentaje_participacion'].sum()
    diferencia = 100 - suma_porcentajes

    # Si no hay diferencia, se devuelve el grupo sin cambios
    if diferencia == 0:
        return grupo
    
    # Buscar diciembre (mes 12)
    mask_diciembre = grupo['mes'] == 12

    if mask_diciembre.any():
        grupo.loc[mask_diciembre, 'porcentaje_participacion'] += diferencia
    else:
        # Si por algún motivo no existe mes 12, ajustar al último mes disponible
        idx_ultimo = grupo['mes'].idxmax()
        grupo.loc[idx_ultimo, 'porcentaje_participacion'] += diferencia

    return grupo

def _obtener_df_participacion_mensual():
    """
    Qué porcentaje de las ventas anuales de cada (línea, centro, segmento)
    cae en cada mes. La lógica vive en calculo._participacion_mensual, que
    usa bd_ventas_comercial; antes esta función leía BdVentas2025 fijo.
    """
    return calculo._participacion_mensual()

def actualizar_presupuesto_general_ventas(request):
    year_actual = timezone.now().year
    year_siguiente = year_actual + 1

    total_siguiente = PresupuestoComercial.objects.filter(year=year_actual).aggregate(
        total_proyectado=Sum("proyeccion_ventas")
    )["total_proyectado"] or 0
    PresupuestoGeneralVentas.objects.filter(year=year_siguiente).update(total_proyectado=total_siguiente)

    df_final = _obtener_df_participacion_mensual()

    proyecciones_qs = (
        PresupuestoComercial.objects.filter(year=year_actual)
        .values("linea", "nombre_centro_de_operacion", "nombre_clase_cliente")
        .annotate(total_proyectado=Sum("proyeccion_ventas"))
    )
    # FIX: índice O(1) en vez de next(...) sobre la lista completa por cada fila.
    indice_proyecciones = indice_por_clave(
        proyecciones_qs, ["linea", "nombre_centro_de_operacion", "nombre_clase_cliente"]
    )

    for idx, row in df_final.iterrows():
        clave = (row["nombre_linea_n1"], row["nombre_centro_de_operacion"], row["nombre_clase_cliente"])
        proyeccion_item = indice_proyecciones.get(clave)
        total_proyectado = proyeccion_item["total_proyectado"] or 0 if proyeccion_item else 0
        porcentaje = row["porcentaje_participacion"] or 0
        df_final.loc[idx, 'valor_proyectado_mes'] = round((porcentaje / 100) * total_proyectado)

    totales_por_mes_agrupado = df_final.groupby(['year', 'mes'])['valor_proyectado_mes'].sum().reset_index()
    for _, row in totales_por_mes_agrupado.iterrows():
        PresupuestoGeneralVentas.objects.filter(year=year_siguiente, mes=row["mes"]).update(
            total=row["valor_proyectado_mes"] or 0
        )

    total_anual_siguiente = PresupuestoGeneralVentas.objects.filter(year=year_siguiente).aggregate(
        total_year=Sum('total')
    )['total_year'] or 0
    PresupuestoGeneralVentas.objects.filter(year=year_siguiente).update(total_year=total_anual_siguiente)

    # FIX: índices por mes en vez de next(...) (aquí n es pequeño, 12
    # meses, pero se deja consistente con el resto y sin costo extra real).
    indice_costos_mes = indice_por_clave(
        PresupuestoGeneralCostos.objects.filter(year=year_actual).values("mes", "total").distinct(), ["mes"]
    )
    indice_ventas_siguiente_mes = indice_por_clave(
        PresupuestoGeneralVentas.objects.filter(year=year_siguiente).values("mes", "total").distinct(), ["mes"]
    )
    ventas_actuales_por_mes = PresupuestoGeneralVentas.objects.filter(year=year_actual).values("mes", "total").distinct()

    for venta_item in ventas_actuales_por_mes:
        mes = venta_item["mes"]
        total_ventas_mes = venta_item["total"] or 0
        costo_item = indice_costos_mes.get((mes,))
        venta_siguiente_item = indice_ventas_siguiente_mes.get((mes,))
        total_costos_mes = costo_item["total"] or 0 if costo_item else 0

        utilidad_pct_mes = round(1 - (total_costos_mes / total_ventas_mes), 4) if total_ventas_mes else 0
        utilidad_valor_mes = round(venta_siguiente_item["total"] * utilidad_pct_mes) if venta_siguiente_item else 0
        utilidad_pct_mes = utilidad_pct_mes * 100 if total_ventas_mes else 0

        PresupuestoGeneralVentas.objects.filter(year=year_siguiente, mes=mes).update(
            utilidad_valor=utilidad_valor_mes, utilidad_pct=round(utilidad_pct_mes, 2)
        )

    return JsonResponse({"status": "ok", "mensaje": "Presupuesto general de ventas actualizado ✅"})

def actualizar_presupuesto_centro_ventas(request):
    year_actual = timezone.now().year
    year_siguiente = year_actual + 1

    proyecciones_centro_qs = (
        PresupuestoComercial.objects.filter(year=year_actual)
        .values("nombre_centro_de_operacion")
        .annotate(total_proyectado=Sum("proyeccion_ventas"))
    )
    for item in proyecciones_centro_qs:
        PresupuestoCentroOperacionVentas.objects.filter(
            year=year_siguiente, nombre_centro_operacion=item["nombre_centro_de_operacion"]
        ).update(total_proyectado=item["total_proyectado"] or 0)

    df_final = _obtener_df_participacion_mensual()

    proyecciones_qs = (
        PresupuestoComercial.objects.filter(year=year_actual)
        .values("linea", "nombre_centro_de_operacion", "nombre_clase_cliente")
        .annotate(total_proyectado=Sum("proyeccion_ventas"))
    )
    # FIX: índice O(1) en vez de next(...) por cada fila de df_final.
    indice_proyecciones = indice_por_clave(
        proyecciones_qs, ["linea", "nombre_centro_de_operacion", "nombre_clase_cliente"]
    )

    for idx, row in df_final.iterrows():
        clave = (row["nombre_linea_n1"], row["nombre_centro_de_operacion"], row["nombre_clase_cliente"])
        proyeccion_item = indice_proyecciones.get(clave)
        total_proyectado = proyeccion_item["total_proyectado"] or 0 if proyeccion_item else 0
        porcentaje = row["porcentaje_participacion"] or 0
        df_final.loc[idx, 'valor_proyectado_mes'] = round((porcentaje / 100) * total_proyectado)

    totales_por_mes_agrupado = (
        df_final.groupby(['year', 'mes', 'nombre_centro_de_operacion'])['valor_proyectado_mes'].sum().reset_index()
    )
    for _, row in totales_por_mes_agrupado.iterrows():
        PresupuestoCentroOperacionVentas.objects.filter(
            year=year_siguiente, mes=row["mes"], nombre_centro_operacion=row["nombre_centro_de_operacion"]
        ).update(total=row["valor_proyectado_mes"] or 0)

    total_anual_siguiente = (
        PresupuestoCentroOperacionVentas.objects.filter(year=year_siguiente)
        .values('nombre_centro_operacion').annotate(total_year=Sum('total'))
    )
    for item in total_anual_siguiente:
        PresupuestoCentroOperacionVentas.objects.filter(
            year=year_siguiente, nombre_centro_operacion=item['nombre_centro_operacion']
        ).update(total_year=item['total_year'] or 0)

    # FIX: índices por centro+mes en vez de next(...) dentro del bucle.
    indice_costos = indice_por_clave(
        PresupuestoCentroOperacionCostos.objects.filter(year=year_actual)
        .values("mes", "nombre_centro_operacion", "total").distinct(),
        ["mes", "nombre_centro_operacion"],
    )
    indice_ventas_siguiente = indice_por_clave(
        PresupuestoCentroOperacionVentas.objects.filter(year=year_siguiente)
        .values("mes", "nombre_centro_operacion", "total").distinct(),
        ["mes", "nombre_centro_operacion"],
    )
    ventas_actuales = PresupuestoCentroOperacionVentas.objects.filter(year=year_actual).values(
        "mes", "nombre_centro_operacion", "total"
    ).distinct()

    for venta_item in ventas_actuales:
        mes = venta_item["mes"]
        centro = venta_item["nombre_centro_operacion"]
        total_ventas_mes = venta_item["total"] or 0
        costo_item = indice_costos.get((mes, centro))
        venta_siguiente_item = indice_ventas_siguiente.get((mes, centro))
        total_costos_mes = costo_item["total"] or 0 if costo_item else 0

        utilidad_pct_mes = round(1 - (total_costos_mes / total_ventas_mes), 4) if total_ventas_mes else 0
        utilidad_valor_mes = round(venta_siguiente_item["total"] * utilidad_pct_mes) if venta_siguiente_item else 0
        utilidad_pct_mes = utilidad_pct_mes * 100 if total_ventas_mes else 0

        PresupuestoCentroOperacionVentas.objects.filter(
            year=year_siguiente, mes=mes, nombre_centro_operacion=centro
        ).update(utilidad_valor=utilidad_valor_mes, utilidad_pct=round(utilidad_pct_mes, 2))

    return JsonResponse({"status": "ok", "mensaje": "Presupuesto por centro de operación actualizado ✅"})

def actualizar_presupuesto_centro_segmento_ventas(request):
    year_actual = timezone.now().year
    year_siguiente = year_actual + 1

    proyecciones_cs_qs = (
        PresupuestoComercial.objects.filter(year=year_actual)
        .values("nombre_centro_de_operacion", "nombre_clase_cliente")
        .annotate(total_proyectado=Sum("proyeccion_ventas"))
    )
    for item in proyecciones_cs_qs:
        PresupuestoCentroSegmentoVentas.objects.filter(
            year=year_siguiente,
            nombre_centro_operacion=item["nombre_centro_de_operacion"],
            segmento=item["nombre_clase_cliente"],
        ).update(total_proyectado=item["total_proyectado"] or 0)

    df_final = _obtener_df_participacion_mensual()

    proyecciones_qs = (
        PresupuestoComercial.objects.filter(year=year_actual)
        .values("linea", "nombre_centro_de_operacion", "nombre_clase_cliente")
        .annotate(total_proyectado=Sum("proyeccion_ventas"))
    )
    # FIX 1: índice O(1) en vez de next(...) por cada fila de df_final.
    indice_proyecciones = indice_por_clave(
        proyecciones_qs, ["linea", "nombre_centro_de_operacion", "nombre_clase_cliente"]
    )

    for idx, row in df_final.iterrows():
        clave = (row["nombre_linea_n1"], row["nombre_centro_de_operacion"], row["nombre_clase_cliente"])
        proyeccion_item = indice_proyecciones.get(clave)
        total_proyectado = proyeccion_item["total_proyectado"] or 0 if proyeccion_item else 0
        porcentaje = row["porcentaje_participacion"] or 0
        df_final.loc[idx, 'valor_proyectado_mes'] = round((porcentaje / 100) * total_proyectado)

    totales_por_mes_agrupado = (
        df_final.groupby(['year', 'mes', 'nombre_centro_de_operacion', 'nombre_clase_cliente'])
        ['valor_proyectado_mes'].sum().reset_index()
    )
    for _, row in totales_por_mes_agrupado.iterrows():
        PresupuestoCentroSegmentoVentas.objects.filter(
            year=year_siguiente, mes=row["mes"],
            nombre_centro_operacion=row["nombre_centro_de_operacion"],
            segmento=row["nombre_clase_cliente"],
        ).update(total=row["valor_proyectado_mes"] or 0)

    total_anual_siguiente = (
        PresupuestoCentroSegmentoVentas.objects.filter(year=year_siguiente)
        .values('nombre_centro_operacion', 'segmento').annotate(total_year=Sum('total'))
    )
    for item in total_anual_siguiente:
        PresupuestoCentroSegmentoVentas.objects.filter(
            year=year_siguiente,
            nombre_centro_operacion=item['nombre_centro_operacion'], segmento=item['segmento'],
        ).update(total_year=item['total_year'] or 0)

    # FIX 2: índices por (mes, centro, segmento) — este bucle sí podía
    # llegar a cientos de combinaciones, así que era el candidato más
    # real a notarse lento en producción.
    indice_costos = indice_por_clave(
        PresupuestoCentroSegmentoCostos.objects.filter(year=year_actual)
        .values("mes", "nombre_centro_operacion", "segmento", "total").distinct(),
        ["mes", "nombre_centro_operacion", "segmento"],
    )
    indice_ventas_siguiente = indice_por_clave(
        PresupuestoCentroSegmentoVentas.objects.filter(year=year_siguiente)
        .values("mes", "nombre_centro_operacion", "segmento", "total").distinct(),
        ["mes", "nombre_centro_operacion", "segmento"],
    )
    ventas_actuales = PresupuestoCentroSegmentoVentas.objects.filter(year=year_actual).values(
        "mes", "nombre_centro_operacion", "segmento", "total"
    ).distinct()

    for venta_item in ventas_actuales:
        mes = venta_item["mes"]
        centro = venta_item["nombre_centro_operacion"]
        segmento = venta_item["segmento"]
        total_ventas_mes = venta_item["total"] or 0
        costo_item = indice_costos.get((mes, centro, segmento))
        venta_siguiente_item = indice_ventas_siguiente.get((mes, centro, segmento))
        total_costos_mes = costo_item["total"] or 0 if costo_item else 0

        utilidad_pct_mes = round(1 - (total_costos_mes / total_ventas_mes), 4) if total_ventas_mes else 0
        utilidad_valor_mes = round(venta_siguiente_item["total"] * utilidad_pct_mes) if venta_siguiente_item else 0
        utilidad_pct_mes = utilidad_pct_mes * 100 if total_ventas_mes else 0

        PresupuestoCentroSegmentoVentas.objects.filter(
            year=year_siguiente, mes=mes, nombre_centro_operacion=centro, segmento=segmento
        ).update(utilidad_valor=utilidad_valor_mes, utilidad_pct=round(utilidad_pct_mes, 2))

    # Promedio de utilidad (jul-sep) aplicado a oct-dic — igual que el original.
    promedios_utilidad = (
        PresupuestoCentroSegmentoVentas.objects.filter(year=year_siguiente, mes__in=[7, 8, 9])
        .values("nombre_centro_operacion", "segmento").annotate(promedio_utilidad=Avg("utilidad_pct"))
    )
    for p in promedios_utilidad:
        registros_nd = list(PresupuestoCentroSegmentoVentas.objects.filter(
            year=year_siguiente, mes__in=[10, 11, 12],
            nombre_centro_operacion=p["nombre_centro_operacion"], segmento=p["segmento"],
        ))
        promedio_utilidad_pct = p["promedio_utilidad"] or 0
        for registro in registros_nd:
            registro.utilidad_pct = promedio_utilidad_pct
            registro.utilidad_valor = round((registro.total or 0) * (promedio_utilidad_pct / 100))
        # mejora menor: un solo bulk_update en vez de N .save() individuales
        if registros_nd:
            PresupuestoCentroSegmentoVentas.objects.bulk_update(registros_nd, ["utilidad_pct", "utilidad_valor"])

    return JsonResponse({
        "status": "ok", "mensaje": "Presupuesto por centro y segmento actualizado y distribuido por mes ✅",
    })

def actualizar_presupuesto_centro_segmento_linea_ventas(request):
    year_actual = timezone.now().year
    year_siguiente = year_actual + 1

    proyecciones_csl_qs = (
        PresupuestoComercial.objects.filter(year=year_actual)
        .values("nombre_centro_de_operacion", "nombre_clase_cliente", "linea")
        .annotate(total_proyectado=Sum("proyeccion_ventas"))
    )
    for item in proyecciones_csl_qs:
        PresupuestoCentroSegLineaVentas.objects.filter(
            year=year_siguiente,
            nombre_centro_operacion=item["nombre_centro_de_operacion"],
            segmento=item["nombre_clase_cliente"],
            linea=item["linea"],
        ).update(total_proyectado=item["total_proyectado"] or 0)

    df_final = _obtener_df_participacion_mensual()

    proyecciones_qs = (
        PresupuestoComercial.objects.filter(year=year_actual)
        .values("linea", "nombre_centro_de_operacion", "nombre_clase_cliente")
        .annotate(total_proyectado=Sum("proyeccion_ventas"))
    )
    # FIX 1: índice O(1) en vez de next(...) por cada fila de df_final.
    indice_proyecciones = indice_por_clave(
        proyecciones_qs, ["linea", "nombre_centro_de_operacion", "nombre_clase_cliente"]
    )

    for idx, row in df_final.iterrows():
        clave = (row["nombre_linea_n1"], row["nombre_centro_de_operacion"], row["nombre_clase_cliente"])
        proyeccion_item = indice_proyecciones.get(clave)
        total_proyectado = proyeccion_item["total_proyectado"] or 0 if proyeccion_item else 0
        porcentaje = row["porcentaje_participacion"] or 0
        df_final.loc[idx, 'valor_proyectado_mes'] = round((porcentaje / 100) * total_proyectado)

    totales_por_mes_agrupado = (
        df_final.groupby(['year', 'mes', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'nombre_linea_n1'])
        ['valor_proyectado_mes'].sum().reset_index()
    )
    for _, row in totales_por_mes_agrupado.iterrows():
        PresupuestoCentroSegLineaVentas.objects.filter(
            year=year_siguiente, mes=row["mes"],
            nombre_centro_operacion=row["nombre_centro_de_operacion"],
            segmento=row["nombre_clase_cliente"], linea=row["nombre_linea_n1"],
        ).update(total=row["valor_proyectado_mes"] or 0)

    total_anual_siguiente = (
        PresupuestoCentroSegLineaVentas.objects.filter(year=year_siguiente)
        .values('nombre_centro_operacion', 'segmento', 'linea').annotate(total_year=Sum('total'))
    )
    for item in total_anual_siguiente:
        PresupuestoCentroSegLineaVentas.objects.filter(
            year=year_siguiente, nombre_centro_operacion=item['nombre_centro_operacion'],
            segmento=item['segmento'], linea=item['linea'],
        ).update(total_year=item['total_year'] or 0)

    # FIX 2: índices por (mes, centro, segmento, línea) — el bucle con
    # más combinaciones posibles de las 4 vistas "actualizar_*".
    indice_costos = indice_por_clave(
        PresupuestoCentroSegLineaCostos.objects.filter(year=year_actual)
        .values("mes", "nombre_centro_operacion", "segmento", "linea", "total").distinct(),
        ["mes", "nombre_centro_operacion", "segmento", "linea"],
    )
    indice_ventas_siguiente = indice_por_clave(
        PresupuestoCentroSegLineaVentas.objects.filter(year=year_siguiente)
        .values("mes", "nombre_centro_operacion", "segmento", "linea", "total").distinct(),
        ["mes", "nombre_centro_operacion", "segmento", "linea"],
    )
    ventas_actuales = PresupuestoCentroSegLineaVentas.objects.filter(year=year_actual).values(
        "mes", "nombre_centro_operacion", "segmento", "linea", "total"
    ).distinct()

    for venta_item in ventas_actuales:
        mes = venta_item["mes"]
        centro = venta_item["nombre_centro_operacion"]
        segmento = venta_item["segmento"]
        linea = venta_item["linea"]
        total_ventas_mes = venta_item["total"] or 0
        costo_item = indice_costos.get((mes, centro, segmento, linea))
        venta_siguiente_item = indice_ventas_siguiente.get((mes, centro, segmento, linea))
        total_costos_mes = costo_item["total"] or 0 if costo_item else 0

        utilidad_pct_mes = round(1 - (total_costos_mes / total_ventas_mes), 4) if total_ventas_mes else 0
        utilidad_valor_mes = round(venta_siguiente_item["total"] * utilidad_pct_mes) if venta_siguiente_item else 0
        utilidad_pct_mes = utilidad_pct_mes * 100 if total_ventas_mes else 0

        PresupuestoCentroSegLineaVentas.objects.filter(
            year=year_siguiente, mes=mes, nombre_centro_operacion=centro, segmento=segmento, linea=linea,
        ).update(utilidad_valor=utilidad_valor_mes, utilidad_pct=round(utilidad_pct_mes, 2))

    # Promedio de utilidad (jul-sep) aplicado a oct-dic — igual que el original.
    promedios_utilidad = (
        PresupuestoCentroSegLineaVentas.objects.filter(year=year_siguiente, mes__in=[7, 8, 9])
        .values("nombre_centro_operacion", "segmento", "linea")
        .annotate(promedio_utilidad=Avg("utilidad_pct"))
    )
    for p in promedios_utilidad:
        registros_ond = list(PresupuestoCentroSegLineaVentas.objects.filter(
            year=year_siguiente, mes__in=[10, 11, 12],
            nombre_centro_operacion=p["nombre_centro_operacion"],
            segmento=p["segmento"], linea=p["linea"],
        ))
        promedio_utilidad_pct = p["promedio_utilidad"] or 0
        for registro in registros_ond:
            registro.utilidad_pct = promedio_utilidad_pct
            registro.utilidad_valor = round((registro.total or 0) * (promedio_utilidad_pct / 100))
        if registros_ond:
            PresupuestoCentroSegLineaVentas.objects.bulk_update(registros_ond, ["utilidad_pct", "utilidad_valor"])

    return JsonResponse({
        "status": "ok", "mensaje": "Presupuesto por centro, segmento y línea actualizado y distribuido por mes ✅",
    })
   
@csrf_exempt
def importar_crecimiento_ventas(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'error': 'No se recibió archivo'}, status=400)

    try:
        df = pd.read_excel(file)
    except Exception as e:
        return JsonResponse({'error': f'Error al leer el archivo: {str(e)}'}, status=400)

    columnas_requeridas = [
        'linea',
        'año',
        'centro de operación',
        'clase cliente',
        'crecimiento ventas proyectado'
    ]
    faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if faltantes:
        return JsonResponse({'error': f'Faltan columnas en el Excel: {", ".join(faltantes)}'}, status=400)

    # 🔹 Limpieza y normalización
    df = df[columnas_requeridas].dropna(subset=['linea', 'año', 'centro de operación', 'clase cliente'])
    df['linea'] = df['linea'].astype(str).str.strip()
    df['centro de operación'] = df['centro de operación'].astype(str).str.strip()
    df['clase cliente'] = df['clase cliente'].astype(str).str.strip()

    try:
        df['año'] = df['año'].astype(int)
    except ValueError:
        return JsonResponse({'error': 'La columna "año" debe contener solo números enteros'}, status=400)

    try:
        # celda vacía = sin crecimiento (0), no NaN
        df['crecimiento ventas proyectado'] = df['crecimiento ventas proyectado'].astype(float).fillna(0)
    except ValueError:
        return JsonResponse({'error': 'La columna "crecimiento ventas proyectado" debe ser numérica'}, status=400)

    # Se guarda igual que la edición en pantalla (solo el año actual, que es el
    # editable): si la combinación no tenía fila se crea (antes se descartaba
    # como "no encontrada") y si estaba repetida se actualizan todas las copias.
    # Lo demás (proyección, márgenes) se calcula al vuelo en calcular_comercial.
    year_actual = timezone.now().year
    otro_anio = int((df['año'] != year_actual).sum())
    df = df[df['año'] == year_actual]
    nuevos = {}
    for _, row in df.iterrows():
        nuevos[(row['linea'], row['centro de operación'], row['clase cliente'])] = \
            float(row['crecimiento ventas proyectado'])
    cambios = _guardar_crecimientos(nuevos, year_actual)

    mensaje = (f"{len(nuevos)} combinaciones de {year_actual} leídas del archivo; "
               f"{cambios} con crecimiento nuevo o distinto.")
    if otro_anio:
        mensaje += f" ⚠️ {otro_anio} fila(s) de otro año se ignoraron (solo se edita {year_actual})."

    return JsonResponse({'mensaje': mensaje})

def exportar_crecimiento_ventas(request):
    """Excel base para cargar crecimientos: las MISMAS filas que muestra la
    pantalla de proyección (línea+centro+segmento con datos en el año actual),
    una por combinación, con el crecimiento guardado (0 si no tiene).

    Antes se listaba la tabla presupuesto_comercial tal cual: traía filas de
    versiones anteriores (líneas que ya no están en el año actual) y
    combinaciones repetidas.
    """
    year_actual = timezone.now().year
    df = calculo.calcular_comercial()
    if df.empty:
        return HttpResponse("No hay datos para exportar", status=400)

    df = (df[['linea', 'year', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'crecimiento_ventas']]
          .sort_values(['linea', 'nombre_centro_de_operacion', 'nombre_clase_cliente'])
          .rename(columns={
              'year': 'año',
              'nombre_centro_de_operacion': 'centro de operación',
              'nombre_clase_cliente': 'clase cliente',
              'crecimiento_ventas': 'crecimiento ventas proyectado',
          }))
    df['año'] = df['año'].astype(int)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="crecimiento_ventas_{year_actual}.xlsx"'
    df.to_excel(response, index=False)
    return response

def obtener_presupuesto_comercial(request):
    return JsonResponse(calculo._a_registros(calculo.calcular_comercial()), safe=False)

def vista_presupuesto_comercial(request):
    return render(request, 'presupuesto_comercial/presupuesto_comercial_final.html')

#  ---------------------NOMINA-------------------------------------------------------------
#  La nómina usa ahora una sola tabla (PresupuestoNomina). Las vistas están en
#  views_nomina.py, la lógica en nomina_motor.py y las rutas en urls_nomina.py.


# -----------------------------PRESUPUESTO GENERAL----------------------------------------------------------------------
#SELECCIÓN DE CUENTAS CONTABLES-----------------
def seleccion_cuentas_contables(request):
    cuentas = list(CuentasContables.objects.values_list('cuenta', flat=True))
    nom_cuentas = list(CuentasContables.objects.values_list('nom_cuenta', flat=True))
 
    # Creamos el diccionario 
    cuentas_dict = dict(zip(cuentas, nom_cuentas))
    return JsonResponse({"cuentas": cuentas, "nom_cuentas": nom_cuentas, "cuentas_dict": cuentas_dict}, safe=False)


# ---------------------------------------------------------------------------
# Configuración centralizada por sede
# ---------------------------------------------------------------------------
from .models_presupuesto import anio_elaboracion, anio_presupuesto  # noqa: E402
from .views_presupuesto_areas import (  # noqa: F401
    SEDE_CONFIG, exportar_excel_presupuestos, presupuesto_sede, obtener_presupuesto_sede,
    presupuesto_aprobado_sede, obtener_presupuesto_aprobado_sede, tabla_auxiliar_sede,
    presupuesto_preaprobado_sede, obtener_presupuesto_preaprobado_sede, actualizar_borrador_sede,
    obtener_temp_sede, guardar_temp_sede, cargar_base_sede, subir_presupuesto_sede,
    borrar_presupuesto_sede, presupuesto_consolidado, obtener_presupuesto_consolidado,
    guardar_presupuesto_consolidado, guardar_version_sede, aprobar_version_sede,
    subir_cuenta5_sede, quitar_cuenta5_sede, estado_cuenta5, ajustes_plazos_edicion,
    subir_cuenta5_nomina, quitar_cuenta5_nomina, estado_cuenta5_nomina,
)

# ---------------------------------------------------------------------------
# Subida por lotes de los Excel de Cuenta 4 / Cuenta 5 (base y presupuestado)
# ---------------------------------------------------------------------------
# Cada petición trae un lote (hasta ~5.000 filas) en uno de dos formatos:
#   {"columnas": ["mcncuenta", ...], "filas": [["510506", ...], ...]}   (compacto, el actual)
#   {"registros": [{"mcncuenta": "510506", ...}, ...]}                  (el anterior)
# y puede venir comprimido con gzip (cabecera X-Compresion: gzip).
#
# Antes se guardaba fila por fila con objects.create(): un INSERT por fila, y con
# la base de datos remota (~45 ms por consulta) 40.000 filas tardaban ~30 min.
# Ahora se guardan con bulk_create en tandas de 1.000: unas pocas consultas por lote.
MAX_DESCOMPRIMIDO = 64 * 1024 * 1024     # tope al descomprimir un lote (64 MB)
TANDA_BULK = 1000


def _cuerpo_lote(request):
    cuerpo = request.body
    if (request.headers.get("X-Compresion") or "").lower() == "gzip":
        d = zlib.decompressobj(16 + zlib.MAX_WBITS)
        cuerpo = d.decompress(cuerpo, MAX_DESCOMPRIMIDO)
        if d.unconsumed_tail:
            raise ValueError("El lote es demasiado grande.")
    return json.loads(cuerpo)


def _registros_lote(datos, modelo):
    """Lista de dicts {campo: valor} validando que las columnas existan en el modelo."""
    permitidos = {f.name for f in modelo._meta.concrete_fields if not f.primary_key}
    if "columnas" in datos:
        columnas = [str(c) for c in datos.get("columnas") or []]
        desconocidas = [c for c in columnas if c not in permitidos]
        if desconocidas:
            raise ValueError(f"Columnas desconocidas: {', '.join(desconocidas)}")
        registros = []
        for n, fila in enumerate(datos.get("filas") or [], start=1):
            if not isinstance(fila, list) or len(fila) != len(columnas):
                raise ValueError(f"La fila {n} del lote no tiene {len(columnas)} valores.")
            registros.append(dict(zip(columnas, fila)))
        return registros
    registros = datos.get("registros") or []
    desconocidas = sorted({k for r in registros for k in r} - permitidos)
    if desconocidas:
        raise ValueError(f"Columnas desconocidas: {', '.join(desconocidas)}")
    return registros


def _subir_lote_excel(request, modelo, nombre_log):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)
    try:
        with log_carga(nombre_log, request, lote=request.headers.get("X-Lote")) as info:
            registros = _registros_lote(_cuerpo_lote(request), modelo)
            info["recibidos"] = len(registros)
            objetos = [modelo(**r) for r in registros]
            with transaction.atomic():
                modelo.objects.bulk_create(objetos, batch_size=TANDA_BULK)
            info["registros"] = len(objetos)
        return JsonResponse({"status": "ok", "insertados": len(objetos)})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


#---------------------Obtener, editar y guardar cuanta 5--------------
def excel_serial_to_date(serial):
    if serial is None:
        return None
    try:
        base_date = datetime.datetime(1899, 12, 30)
        return (base_date + datetime.timedelta(days=int(serial))).date().isoformat()
    except Exception:
        return None

def date_to_excel_serial(value):
    """'YYYY-MM-DD' | date | int  ->  serial Excel (int) o None."""
    if value in (None, ''):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        v = value.strip()
        if v.isdigit():
            return int(v)
        try:
            fecha = datetime.datetime.strptime(v, '%Y-%m-%d').date()
        except ValueError:
            return None
    elif isinstance(value, datetime.date):
        fecha = value
    else:
        return None
    return (fecha - datetime.date(1899, 12, 30)).days

@login_required
def cuenta5(request):
    usuarios_permitidos = ['admin', 'NICOLAS']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    return render(request, "presupuesto_consolidado/cuenta5_base.html")

@csrf_exempt
def obtener_cuenta5_base(request):
    try:
        params = request.POST or request.GET  # funciona con ambos métodos
        draw = int(params.get('draw') or 1)
        start = int(params.get('start') or 0)
        length = int(params.get('length') or 50)

        queryset = Cuenta5Base.objects.all()
        total = queryset.count()

        paginator = Paginator(queryset, length)
        page_number = start // length + 1
        page = paginator.get_page(page_number)

        data = list(page.object_list.values())

        # 🔹 Convertir fecha Excel a fecha normal
        for row in data:
            row['mcnfecha'] = excel_serial_to_date(row.get('mcnfecha'))
        
        return JsonResponse({
            'draw': draw,
            'recordsTotal': total,
            'recordsFiltered': total,
            'data': data
        })

    except Exception as e:
        print(f"❌ Error en obtener_cuenta5_base: {e}")
        return JsonResponse({'error': str(e)}, status=500) 
    
@csrf_exempt
def subir_excel_cuenta5(request):
    return _subir_lote_excel(request, Cuenta5Base, "cuenta5_base")

@csrf_exempt
def borrar_cuenta5_base(request):
    if request.method == "POST":
        Cuenta5Base.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Datos de cuenta 5 eliminados"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

# SUBIR Y BORRAR CUENTA 5 PRESUPUESTADO -------------------------------
@login_required
def cuenta5_presupuestado(request):
    usuarios_permitidos = ['admin', 'NICOLAS']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    return render(request, "presupuestado/cuenta5_presupuestado.html")

@csrf_exempt
def obtener_cuenta5_presupuestado(request):
    try:
        params = request.POST or request.GET  # funciona con ambos métodos
        draw = int(params.get('draw') or 1)
        start = int(params.get('start') or 0)
        length = int(params.get('length') or 50)

        queryset = Cuenta5Presupuestado.objects.all()
        total = queryset.count()

        paginator = Paginator(queryset, length)
        page_number = start // length + 1
        page = paginator.get_page(page_number)

        data = list(page.object_list.values())

        # 🔹 Convertir fecha Excel a fecha normal
        for row in data:
            row['mcnfecha'] = excel_serial_to_date(row.get('mcnfecha'))
        
        return JsonResponse({
            'draw': draw,
            'recordsTotal': total,
            'recordsFiltered': total,
            'data': data
        })

    except Exception as e:
        print(f"❌ Error en obtener_cuenta5_base: {e}")
        return JsonResponse({'error': str(e)}, status=500) 
  
@csrf_exempt
def subir_excel_cuenta5_presupuestado(request):
    return _subir_lote_excel(request, Cuenta5Presupuestado, "cuenta5_presupuestado")

@csrf_exempt
def borrar_cuenta5_presupuestado(request):
    if request.method == "POST":
        Cuenta5Presupuestado.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Datos de cuenta 5 eliminados"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)
 
 
# CUENTA 4-----------------------------------
@login_required
def cuenta4(request):
    usuarios_permitidos = ['admin', 'NICOLAS']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    return render(request, "presupuesto_consolidado/cuenta4_base.html")

@csrf_exempt
def obtener_cuenta4_base(request):
    try:
        params = request.POST or request.GET  # funciona con ambos métodos
        draw = int(params.get('draw') or 1)
        start = int(params.get('start') or 0)
        length = int(params.get('length') or 50)

        queryset = Cuenta4Base.objects.all()
        total = queryset.count()

        paginator = Paginator(queryset, length)
        page_number = start // length + 1
        page = paginator.get_page(page_number)

        data = list(page.object_list.values())

        # 🔹 Convertir fecha Excel a fecha normal
        for row in data:
            row['mcnfecha'] = excel_serial_to_date(row.get('mcnfecha'))
        
        return JsonResponse({
            'draw': draw,
            'recordsTotal': total,
            'recordsFiltered': total,
            'data': data
        })

    except Exception as e:
        print(f"❌ Error en obtener_cuenta4_base: {e}")
        return JsonResponse({'error': str(e)}, status=500) 
    
@csrf_exempt
def subir_excel_cuenta4(request):
    return _subir_lote_excel(request, Cuenta4Base, "cuenta4_base")

@csrf_exempt
def borrar_cuenta4_base(request):
    if request.method == "POST":
        Cuenta4Base.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Datos de cuenta 4 eliminados"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

# SUBIR Y BORRAR CUENTA 5 PRESUPUESTADO -------------------------------
@login_required
def cuenta4_presupuestado(request):
    usuarios_permitidos = ['admin', 'NICOLAS']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    return render(request, "presupuestado/cuenta4_presupuestado.html")

@csrf_exempt
def obtener_cuenta4_presupuestado(request):
    try:
        params = request.POST or request.GET  # funciona con ambos métodos
        draw = int(params.get('draw') or 1)
        start = int(params.get('start') or 0)
        length = int(params.get('length') or 50)

        queryset = Cuenta4Presupuestado.objects.all()
        total = queryset.count()

        paginator = Paginator(queryset, length)
        page_number = start // length + 1
        page = paginator.get_page(page_number)

        data = list(page.object_list.values())

        # 🔹 Convertir fecha Excel a fecha normal
        for row in data:
            row['mcnfecha'] = excel_serial_to_date(row.get('mcnfecha'))
        
        return JsonResponse({
            'draw': draw,
            'recordsTotal': total,
            'recordsFiltered': total,
            'data': data
        })

    except Exception as e:
        print(f"❌ Error en obtener_cuenta4_base: {e}")
        return JsonResponse({'error': str(e)}, status=500) 
  
@csrf_exempt
def subir_excel_cuenta4_presupuestado(request):
    return _subir_lote_excel(request, Cuenta4Presupuestado, "cuenta4_presupuestado")

@csrf_exempt
def borrar_cuenta4_presupuestado(request):
    if request.method == "POST":
        Cuenta4Presupuestado.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Datos de cuenta 4 eliminados"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)
  

# NOTA: añadir a los imports del views.py
from itertools import chain

# ══════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN COMPARTIDA  (a nivel de módulo: se construye una
#  sola vez, no en cada request)
# ══════════════════════════════════════════════════════════════════

MESES_ES = {
    1: 'Enero',      2: 'Febrero',  3: 'Marzo',     4: 'Abril',
    5: 'Mayo',       6: 'Junio',    7: 'Julio',     8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
}
MESES_COLS = list(MESES_ES.values())

# sede -> zona contable + nombre en ConsolidadoTotalBase
SEDE_CONFIG_CONSOLIDADO = {
    'cali':    {'zona': ['004', 4], 'nombre': 'CALI'},
    'tulua':   {'zona': ['001', 1], 'nombre': 'TULUA'},
    'buga':    {'zona': ['002', 2], 'nombre': 'BUGA'},
    'cartago': {'zona': ['003', 3], 'nombre': 'CARTAGO'},
    'total':   None,                       # None → sin filtro, todas las sedes
}

# Alias para no romper el front ni las URLs actuales
ALIAS_SEDE = {
    'consolidado':   'total',
    'presupuestado': 'total',
    'total_base':    'total',
}

# origen -> modelos de detalle. Las cuentas 5x y las 4x viven en tablas
# distintas. El mismo string se usa para filtrar ConsolidadoTotalBase.origen
ORIGENES = {
    'ejecutado': {
        'cuenta5': Cuenta5Base,
        'cuenta4': Cuenta4Base,
    },
    'presupuestado': {
        'cuenta5': Cuenta5Presupuestado,
        'cuenta4': Cuenta4Presupuestado,
    },
}

# Campos que necesita el motor de ambas tablas de detalle
CAMPOS_DETALLE_CONTABLE = ('mcncuenta', 'mcnccosto', 'mcnfecha',
                  'mcnvaldebi', 'mcnvalcred', 'mcndestino', 'ctanombre')

CUENTAS_OMITIR = ['521020']

# ── Cuentas clave: se reconocen por número o, si no viene bien, por nombre ──
NOMBRES_CUENTAS_CLAVE = {
    '1':        'Ventas a crédito',
    '2':        'Ventas a contado',
    '41750201': 'Descuentos otorgados x pto pago',
    '613522':   'Costo de ventas',
}

# Variantes aceptadas del nombre (se comparan normalizadas: sin tildes,
# sin puntuación y en minúsculas). Agrega aquí otras formas si aparecen.
ALIAS_CUENTAS_CLAVE = {
    '1':        ['ventas a credito', 'ventas credito', 'venta a credito', 'venta credito'],
    '2':        ['ventas a contado', 'ventas contado', 'venta a contado', 'venta contado',
                 'ventas de contado'],
    '41750201': ['descuentos otorgados x pto pago', 'descuentos otorgados por pronto pago',
                 'descuentos otorgados pronto pago', 'descuento otorgado x pto pago',
                 'descuentos x pronto pago', 'descuentos por pronto pago'],
    '613522':   ['costo de ventas', 'costos de ventas', 'costo de venta', 'costo ventas'],
}

# Palabra para pre-filtrar en BD (luego se valida el nombre exacto en Python)
PALABRA_BUSQUEDA_CLAVE = {'1': 'venta', '2': 'venta', '41750201': 'descuento', '613522': 'costo'}


def normalizar_nombre_cuenta(texto):
    texto = unicodedata.normalize('NFKD', str(texto or ''))
    texto = ''.join(ch for ch in texto if not unicodedata.combining(ch))
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', texto.lower()).split())

_CUENTA_POR_ALIAS = {
    normalizar_nombre_cuenta(alias): cuenta
    for cuenta, lista in ALIAS_CUENTAS_CLAVE.items()
    for alias in lista
}

def resolver_cuenta_clave(cuenta, nombre):
    """
    Si la cuenta ya es una cuenta clave la devuelve igual. Si no, busca por
    nombre: 'Ventas a crédito' -> '1', 'Costo de ventas' -> '613522', etc.
    Si el nombre no coincide devuelve la cuenta original.
    """
    cuenta = str(cuenta or '').strip()
    if cuenta in ALIAS_CUENTAS_CLAVE:
        return cuenta
    return _CUENTA_POR_ALIAS.get(normalizar_nombre_cuenta(nombre), cuenta)

def q_cuentas_clave(cuentas=None):
    """Q amplio (por número o por palabra en el nombre) para pre-filtrar en BD."""
    cuentas = list(cuentas or ALIAS_CUENTAS_CLAVE)
    q = Q(mcncuenta__in=cuentas)
    palabras = {PALABRA_BUSQUEDA_CLAVE[c] for c in cuentas if c in PALABRA_BUSQUEDA_CLAVE}
    for palabra in palabras:
        q |= Q(ctanombre__icontains=palabra)
    return q

ASISTENCIA_TECNICA = {
    "AT-00004", "AT-00008", "AT-00010", "AT-00013", "AT-00014",
    "AT-00015", "AT-00016", "AT-00019", "AT-00020", "AT-00021",
    "AT-00022", "AT-00023", "AT-00024", "AT-00026", "AT-00028",
    "AT-00029", "AT-00030", "AT-00032", "VT-00025", "AT-00003",
}
ASISTENCIA_TECNICA_PROPIA    = {'AT-00001', 'AT-00002', 'AT-00005'}
ASISTENCIA_TECNICA_CONVENIOS = {'AT-00003', 'AT-00004', 'AT-00006'}

# Agrupación de cuentas ("54100207_54100211", "empieza por 5230", ...) y los
# nombres de cada fila: ya NO están aquí. Viven en la tabla AgrupacionCuenta y
# se editan en Ajustes → Agrupación de cuentas (ver agrupacion_cuentas.py).
from .agrupacion_cuentas import cargar_reglas  # noqa: E402

# ══════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════

def normalizar_sede(sede):
    """Devuelve la clave canónica de SEDE_CONFIG_CONSOLIDADO o None si es inválida."""
    sede = (sede or 'total').lower()
    sede = ALIAS_SEDE.get(sede, sede)
    return sede if sede in SEDE_CONFIG_CONSOLIDADO else None


def filtros_sede(sede):
    """(filtro_detalle, filtro_consolidado) para la sede indicada."""
    cfg = SEDE_CONFIG_CONSOLIDADO[sede]
    if cfg is None:
        return {}, {}
    return {'mcnzona__in': cfg['zona']}, {'sede__icontains': cfg['nombre']}


def aplicar_agrupaciones(cuenta, costo, reglas=None):
    """Fila en la que se suma una cuenta.

    Las reglas por centro de costo siguen aquí; las de cuentas (exactas y
    "empieza por") salen de Ajustes → Agrupación de cuentas. Pasa `reglas`
    (cargar_reglas()) cuando se llama dentro de un bucle.
    """
    if cuenta.startswith('4'):
        return cuenta

    if costo.startswith('02040'):                         cuenta = '5'
    if costo == '020201' and cuenta.startswith('5405'):   cuenta = '5405'
    if costo == '0101':                                   cuenta = '5105'

    return (reglas or cargar_reglas()).agrupar(cuenta)


def _mes_desde_serial(valor):
    """Fecha en serial Excel (Cuenta5*) -> nombre de mes, o None."""
    fecha = excel_serial_to_date(valor)
    if not fecha:
        return None
    return MESES_ES[datetime.datetime.strptime(fecha, '%Y-%m-%d').date().month]


def _mes_desde_fecha(valor):
    """Fecha date o str (ConsolidadoTotalBase) -> nombre de mes, o None."""
    if not valor:
        return None
    if isinstance(valor, str):
        valor = datetime.datetime.strptime(valor, '%Y-%m-%d').date()
    return MESES_ES[valor.month]


def _nombres_cuentas(*modelos):
    """Diccionario cuenta -> nombre, tomando el primero no vacío."""
    cuentas_dict = {}
    fuentes = list(modelos) + [ConsolidadoTotalBase]
    for modelo in fuentes:
        for c in modelo.objects.values('mcncuenta', 'ctanombre').distinct():
            cta, nom = c['mcncuenta'], (c['ctanombre'] or '').strip()
            if cta and nom and cta not in cuentas_dict:
                cuentas_dict[cta] = nom
    return cuentas_dict


# ══════════════════════════════════════════════════════════════════
#  MOTOR ÚNICO DE CÁLCULO
# ══════════════════════════════════════════════════════════════════

def calcular_movimientos(origen='ejecutado', sede='total'):
    """
    Motor único para ejecutado y presupuestado.

    origen: 'ejecutado' | 'presupuestado'
    sede:   'cali' | 'tulua' | 'buga' | 'cartago' | 'total'
    """
    try:
        modelos = ORIGENES[origen]
        sede = normalizar_sede(sede)
        if sede is None:
            raise ValueError('Sede inválida')

        filtro_detalle, filtro_consolidado = filtros_sede(sede)

        # Cuentas 5x (y cualquier otra que no empiece por 4)
        queryset_5 = (
            modelos['cuenta5'].objects
            .filter(**filtro_detalle)
            .exclude(mcncuenta__in=CUENTAS_OMITIR)
            .values(*CAMPOS_DETALLE_CONTABLE)
        )

        # Cuentas 4x desde su propia tabla + cuentas clave reconocidas por nombre.
        # Las cuentas de ventas (1, 2, 41750201) del PRESUPUESTADO las genera
        # generar_presupuesto_ventas en ConsolidadoTotalBase; si se tomaran
        # también del detalle contable quedarían sumadas dos veces.
        zonas_generadas = set()
        if origen == 'presupuestado':
            sedes_generadas = (
                ConsolidadoTotalBase.objects
                .filter(origen='presupuestado', mcncuenta__in=list(CUENTAS_VENTAS))
                .values_list('sede', flat=True).distinct()
            )
            for s in sedes_generadas:
                cfg = SEDE_CONFIG_CONSOLIDADO.get((s or '').strip().lower())
                if cfg:
                    zonas_generadas.update(str(z) for z in cfg['zona'])

        queryset_4 = (
            modelos['cuenta4'].objects
            .filter(**filtro_detalle)
            .filter(Q(mcncuenta__startswith='4') | q_cuentas_clave())
            .values(*CAMPOS_DETALLE_CONTABLE, 'mcnzona')
        )

        queryset_consolidado = (
            ConsolidadoTotalBase.objects
            .filter(**filtro_consolidado, origen=origen)
            .values('mcncuenta', 'mcnccosto', 'mcnfecha', 'valor', 'ctanombre')
        )

        consolidado = defaultdict(lambda: {'total_debito': 0, 'total_credito': 0, 'total_valor': 0})
        reglas = cargar_reglas()   # Ajustes → Agrupación de cuentas (una consulta)

        # ── detalle (cuentas 5 + cuentas 4) ───────────────────────
        for tabla, queryset in (('cuenta5', queryset_5), ('cuenta4', queryset_4)):
            for row in queryset:
                mes = _mes_desde_serial(row['mcnfecha'])
                if not mes:
                    continue

                costo   = row['mcnccosto'] or 'SIN COSTO'
                destino = row['mcndestino'] or 'SIN DESTINO'
                destino_norm = destino.strip().upper()
                cuenta  = resolver_cuenta_clave(row['mcncuenta'], row['ctanombre']) or 'SIN CUENTA'
                
                if (tabla == 'cuenta4' and cuenta in CUENTAS_VENTAS
                        and str(row.get('mcnzona') or '') in zonas_generadas):
                    continue   # esta sede ya tiene la cuenta generada
                if cuenta in ALIAS_CUENTAS_CLAVE:
                    pass  # cuenta clave: se conserva, no se reagrupa
                elif tabla == 'cuenta4' and not cuenta.startswith('4'):
                    continue  # vino solo por el pre-filtro de nombre y no es clave
                elif cuenta.startswith('4'):
                    # Ingresos AT se agrupan por destino; el resto por cuenta
                    if destino_norm in ASISTENCIA_TECNICA:
                        cuenta = destino_norm
                else:
                    cuenta = aplicar_agrupaciones(cuenta, costo, reglas)
                    if destino_norm in ASISTENCIA_TECNICA_PROPIA:
                        cuenta = '6'
                    elif destino_norm in ASISTENCIA_TECNICA_CONVENIOS:
                        cuenta = '7'
                    elif costo.startswith('0203'):
                        cuenta = '8'

                acc = consolidado[(mes, cuenta, costo, destino)]
                acc['total_debito']  += row['mcnvaldebi'] or 0
                acc['total_credito'] += row['mcnvalcred'] or 0

        # ── ConsolidadoTotalBase ──────────────────────────────────
        for row in queryset_consolidado:
            mes = _mes_desde_fecha(row['mcnfecha'])
            if not mes:
                continue
            costo  = row['mcnccosto'] or 'SIN COSTO'
            cuenta = resolver_cuenta_clave(row['mcncuenta'], row['ctanombre']) or 'SIN CUENTA'
            if cuenta not in ALIAS_CUENTAS_CLAVE:
                cuenta = aplicar_agrupaciones(cuenta, costo, reglas)
            consolidado[(mes, cuenta, costo, 'SIN DESTINO')]['total_valor'] += row['valor'] or 0

        # ── armado de registros ───────────────────────────────────
        cuentas_dict = _nombres_cuentas(modelos['cuenta5'], modelos['cuenta4'])
        registros = defaultdict(lambda: {'mcncuenta': '', 'ctanombre': '', 'meses': {}})

        for (mes, cuenta, _costo, _destino), vals in consolidado.items():
            if cuenta in ASISTENCIA_TECNICA or cuenta.startswith('4'):
                saldo = vals['total_credito'] - vals['total_debito'] + vals['total_valor']
            else:
                saldo = vals['total_debito'] - vals['total_credito'] + vals['total_valor']

            especial = reglas.nombre(cuenta)
            if especial:
                nombre = especial                       # ya viene bien escrito
            else:
                crudo = cuentas_dict.get(cuenta) or NOMBRES_CUENTAS_CLAVE.get(cuenta) or 'SIN NOMBRE'
                # Solo se normaliza lo que viene TODO EN MAYÚSCULAS desde la base
                nombre = crudo.capitalize() if crudo.isupper() else crudo

            reg = registros[cuenta]
            reg['mcncuenta'] = cuenta
            reg['ctanombre'] = nombre
            reg['meses'][mes] = round(reg['meses'].get(mes, 0) + saldo)

        return {'success': True, 'data': registros}

    except Exception as e:
        print(f"❌ Error en calcular_movimientos({origen}, {sede}): {e}")
        return {'success': False, 'error': str(e)}

# Wrappers por compatibilidad (si los llamas desde otros módulos)
def calcular_consolidado(sede='total'):
    return calcular_movimientos('ejecutado', sede)


def calcular_presupuestado(sede='total'):
    return calcular_movimientos('presupuestado', sede)


# ══════════════════════════════════════════════════════════════════
#  VISTA GENÉRICA
# ══════════════════════════════════════════════════════════════════

def _responder_movimientos(request, origen):
    sede = normalizar_sede(request.GET.get('sede'))
    if sede is None:
        return JsonResponse({'error': f"Sede inválida: {request.GET.get('sede')}"}, status=400)

    resultado = calcular_movimientos(origen, sede)
    if not resultado['success']:
        return JsonResponse({'error': resultado.get('error', 'Error')}, status=500)

    ORDEN_PERSONALIZADO = obtener_orden_cuentas('total' if sede == 'total' else 'sede')
    NOMBRES = nombres_personalizados()

    filas = []
    for row in resultado['data'].values():
        if row['mcncuenta'] not in ORDEN_PERSONALIZADO:
            continue
        entry = {
            'mcncuenta': row['mcncuenta'],
            'ctanombre': NOMBRES.get(row['mcncuenta'], row['ctanombre']),
            **{m: 0 for m in MESES_COLS},
            'total': 0,
        }
        for mes, valor in row['meses'].items():
            if mes in entry:
                entry[mes] = valor
                entry['total'] += valor
        filas.append(entry)

    posicion = {cta: i for i, cta in enumerate(ORDEN_PERSONALIZADO)}
    filas.sort(key=lambda item: posicion[item['mcncuenta']])

    # Nombre de las filas calculadas (CALC-...): el de Orden de cuentas o el de por defecto
    calculadas = {c: NOMBRES.get(c) or filas_calculadas.NOMBRES[c]
                  for c in ORDEN_PERSONALIZADO if filas_calculadas.es_calculada(c)}

    return JsonResponse({'data': filas,
                         'orden': ORDEN_PERSONALIZADO,
                         'calculadas': calculadas,
                         'recordsTotal': len(filas),
                         'recordsFiltered': len(filas)})


def obtener_consolidado(request):
    """?sede=cali|tulua|buga|cartago|total   (default: total)"""
    return _responder_movimientos(request, 'ejecutado')


def obtener_presupuestado(request):
    """?sede=cali|tulua|buga|cartago|total   (default: total)"""
    return _responder_movimientos(request, 'presupuestado')


# ═══════════════════════════════════════════════════════════════
#  ORDEN PERSONALIZADO DE CUENTAS
# ═══════════════════════════════════════════════════════════════

# Listas actuales del código: solo se usan como semilla / fallback.
ORDEN_TOTAL_FALLBACK = [
    '1','2','41750201','613522','4240900101','4240909502',
    '5405','541001','54100201','54100202','54100204','54100205','54100206',
    '54100207_54100211','541003','541005','541006','541009_541033',
    '541010','541011','54101201','54101202','54101203','54101204',
    '541013','541014','541015_541016','541018','541023','541024','541027',
    '541029','541032','541035','54109501','54109502','54109503','54109504',
    '54109505','54109506','54109507','54109508','54109509','54109510',
    '5415','542005','54100203','54100211',
    '5105','511001','511002','511003','511005','511006','511009','511010',
    '511011','511012','511013','511015_511016','511018','511019','511020',
    '511021','511022','511023','511024','511026','511027','511031','511033',
    '511035','51109502','51109501_51109502','511512','511534',
    '521005','521015','521020','3','615035',
    'AT-00004','AT-00005','AT-00007','AT-00008','AT-00010','AT-00013',
    'AT-00014','AT-00015','AT-00016','AT-00019','AT-00020','AT-00021',
    'AT-00022','AT-00023','AT-00024','AT-00026','AT-00028','AT-00029',
    'AT-00030','AT-00032','VT-00001','VT-00025','AT-00003',
    '41659505','41659501','422004','422507','422529','4240900202','420560',
    '4240900301','4240900401','4240909501','4240909503','4240909901','41750105',
    '5','6','7','8','5230',
]
_CUENTAS_SEDE_FALLBACK = set(ORDEN_TOTAL_FALLBACK[:ORDEN_TOTAL_FALLBACK.index('542005') + 1])
# Las filas calculadas (CALC-...) van en su lugar por defecto dentro de la lista.
ORDEN_TOTAL_FALLBACK = filas_calculadas.ubicar(ORDEN_TOTAL_FALLBACK)
ORDEN_SEDE_FALLBACK = [c for c in ORDEN_TOTAL_FALLBACK
                       if c in _CUENTAS_SEDE_FALLBACK or c in filas_calculadas.EN_SEDE]


def obtener_orden_cuentas(ambito='total'):
    """Lista ordenada de códigos de cuenta. ambito: 'total' | 'sede'."""
    qs = OrdenCuenta.objects.all()
    qs = qs.filter(visible_sede=True) if ambito == 'sede' else qs.filter(visible_total=True)
    orden = list(qs.order_by('orden', 'id').values_list('mcncuenta', flat=True))
    if orden:
        return orden
    return ORDEN_SEDE_FALLBACK if ambito == 'sede' else ORDEN_TOTAL_FALLBACK


def nombres_personalizados():
    """{ mcncuenta: ctanombre } solo para las que tengan nombre definido."""
    return {
        c: n for c, n in OrdenCuenta.objects.exclude(ctanombre='')
                                            .values_list('mcncuenta', 'ctanombre')
    }


def _cuentas_detectadas():
    """Cuentas que realmente pueden aparecer en las tablas, ya agrupadas."""
    detectadas, alguno_ok = {}, False
    for fn, arg in ((calcular_consolidado, 'consolidado'),
                    (calcular_presupuestado, 'presupuestado')):
        res = fn(arg)
        if res.get('success'):
            alguno_ok = True
            for cta, row in res['data'].items():
                nombre = row.get('ctanombre') or ''
                if nombre == 'SIN NOMBRE':
                    nombre = ''
                if cta and not detectadas.get(cta):
                    detectadas[cta] = nombre
    return detectadas if alguno_ok else None


@login_required
def ajustes_orden_cuentas(request):
    if request.user.username not in ['admin', 'NICOLAS']:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    return render(request, 'ajustes/orden_cuentas.html')


def nombres_por_defecto(codigos, detectadas=None):
    """{código: nombre} para cada fila, en este orden de prioridad:

      1. Ajustes → Agrupación de cuentas (nombre de la fila)
      2. el nombre con que sale hoy en el consolidado/presupuestado (detectadas)
      3. cuentas clave (Ventas a crédito, Costo de ventas, ...)
      4. el catálogo de cuentas contables (cuentas_contables)
    Lo que viene TODO EN MAYÚSCULAS se deja con mayúscula inicial, como en las tablas.
    """
    codigos = [str(c) for c in codigos]
    reglas = cargar_reglas()
    detectadas = detectadas or {}
    catalogo = {}
    numericos = [int(c) for c in codigos if c.isdigit()]
    if numericos:
        try:
            with transaction.atomic():      # savepoint: la tabla externa puede no existir
                for cta, nom in CuentasContables.objects.filter(cuenta__in=numericos).values_list('cuenta', 'nom_cuenta'):
                    if nom and str(cta) not in catalogo:
                        catalogo[str(cta)] = nom.strip()
        except Exception:
            pass
    nombres = {}
    for c in codigos:
        nombre = (reglas.nombre(c) or detectadas.get(c) or NOMBRES_CUENTAS_CLAVE.get(c)
                  or filas_calculadas.NOMBRES.get(c) or catalogo.get(c) or '').strip()
        if nombre.isupper() and not filas_calculadas.es_calculada(c):
            nombre = nombre.capitalize()
        nombres[c] = nombre
    return nombres


@require_GET
def listar_orden_cuentas(request):
    data = list(
        OrdenCuenta.objects.order_by('orden', 'id')
        .values('id', 'mcncuenta', 'ctanombre', 'orden', 'visible_total', 'visible_sede')
    )
    # Nombre que se usa si la fila no tiene uno escrito (se muestra de guía).
    sugeridos = nombres_por_defecto([d['mcncuenta'] for d in data])
    for d in data:
        d['sugerido'] = sugeridos.get(d['mcncuenta'], '')
        d['calculada'] = filas_calculadas.es_calculada(d['mcncuenta'])
    return JsonResponse({'success': True, 'data': data, 'total': len(data)})


@login_required
@require_POST
def sincronizar_orden_cuentas(request):
    """Crea las cuentas que aún no estén en la tabla (al final de la lista).
    Si la tabla está vacía, la siembra con el orden que hay hoy en el código."""
    try:
        detectadas = _cuentas_detectadas()
        if detectadas is None:
            return JsonResponse({'success': False, 'error':
                'No se pudo calcular el consolidado para detectar las cuentas; revisa el registro del servidor.'},
                status=500)
        existentes = set(OrdenCuenta.objects.values_list('mcncuenta', flat=True))
        creadas = 0

        with transaction.atomic():
            if not existentes:
                en_sede = set(ORDEN_SEDE_FALLBACK)
                OrdenCuenta.objects.bulk_create([
                    OrdenCuenta(
                        mcncuenta=cta,
                        ctanombre=detectadas.get(cta, ''),
                        orden=(i + 1) * 10,
                        visible_total=True,
                        visible_sede=cta in en_sede,
                    ) for i, cta in enumerate(ORDEN_TOTAL_FALLBACK)
                ])
                creadas = len(ORDEN_TOTAL_FALLBACK)
                existentes = set(ORDEN_TOTAL_FALLBACK)

            ultimo = OrdenCuenta.objects.aggregate(m=models.Max('orden'))['m'] or 0
            nuevas = []
            for cta, nombre in detectadas.items():
                if cta not in existentes:
                    ultimo += 10
                    nuevas.append(OrdenCuenta(
                        mcncuenta=cta, ctanombre=nombre, orden=ultimo,
                        visible_total=True, visible_sede=False,
                    ))
            OrdenCuenta.objects.bulk_create(nuevas)
            creadas += len(nuevas)

            # Filas calculadas (CALC-...) que falten: se insertan en su lugar por defecto
            # y se renumera la lista sin cambiar el orden de lo que ya estaba.
            filas = list(OrdenCuenta.objects.order_by('orden', 'id'))
            codigos = filas_calculadas.ubicar([o.mcncuenta for o in filas])
            if len(codigos) != len(filas):
                por_codigo = {o.mcncuenta: o for o in filas}
                faltan = [OrdenCuenta(mcncuenta=c, ctanombre=filas_calculadas.NOMBRES[c], orden=0,
                                      visible_total=True, visible_sede=c in filas_calculadas.EN_SEDE)
                          for c in codigos if c not in por_codigo]
                OrdenCuenta.objects.bulk_create(faltan)
                creadas += len(faltan)
                por_codigo.update({o.mcncuenta: o for o in faltan})
                todas = []
                for i, c in enumerate(codigos):
                    o = OrdenCuenta.objects.get(mcncuenta=c) if por_codigo[c].pk is None else por_codigo[c]
                    o.orden = (i + 1) * 10
                    todas.append(o)
                OrdenCuenta.objects.bulk_update(todas, ['orden'], batch_size=500)

            # Completa el nombre de las filas que lo tengan vacío (no toca los ya escritos).
            vacias = list(OrdenCuenta.objects.filter(ctanombre=''))
            sugeridos = nombres_por_defecto([o.mcncuenta for o in vacias], detectadas)
            con_nombre = []
            for o in vacias:
                if sugeridos.get(o.mcncuenta):
                    o.ctanombre = sugeridos[o.mcncuenta]
                    con_nombre.append(o)
            OrdenCuenta.objects.bulk_update(con_nombre, ['ctanombre'], batch_size=500)

        return JsonResponse({
            'success': True, 'creadas': creadas, 'nombres': len(con_nombre),
            'sin_nombre': len(vacias) - len(con_nombre),
            'total': OrdenCuenta.objects.count(),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def guardar_orden_cuentas(request):
    """Recibe la lista completa en el orden final:
       { "cuentas": [ {mcncuenta, ctanombre, visible_total, visible_sede}, ... ] }"""
    try:
        body = json.loads(request.body)
        filas = body.get('cuentas', [])
        if not filas:
            return JsonResponse({'success': False, 'error': 'Sin cuentas'}, status=400)

        with transaction.atomic():
            for i, f in enumerate(filas):
                cta = str(f.get('mcncuenta', '') or '').strip()
                if not cta:
                    continue
                nombre = str(f.get('ctanombre', '') or '').strip()
                OrdenCuenta.objects.update_or_create(
                    mcncuenta=cta,
                    defaults={
                        'orden': (i + 1) * 10,
                        'ctanombre': nombre,
                        'visible_total': bool(f.get('visible_total', True)),
                        'visible_sede': bool(f.get('visible_sede', False)),
                    },
                )
                # Un solo nombre por fila: si la fila está en Agrupación de cuentas, se iguala allá.
                if nombre:
                    AgrupacionCuenta.objects.filter(codigo=cta).exclude(nombre=nombre).update(
                        nombre=nombre, actualizado_por=request.user.username)
        return JsonResponse({'success': True, 'guardadas': len(filas)})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def eliminar_orden_cuenta(request):
    try:
        pk = json.loads(request.body).get('id')
        OrdenCuenta.objects.filter(pk=pk).delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ══════════════════════════════════════════════════════════════════
#  VISTA GENÉRICA — reemplaza todas las obtener_presupuestado_*
# ══════════════════════════════════════════════════════════════════


# FIN CALCULAR Y OBTENER PRESUPUESTADO -----------------
# CONSOLIDADO GENERAL
@login_required
def consolidado_general(request):
    usuarios_permitidos = ['admin', 'NICOLAS']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    return render(request, "presupuesto_consolidado/consolidado_general.html",
                  {'subtotales': configuracion_para_tablas()})

# PRESUPUESTO GENERAL
@login_required
def presupuestado_general(request):
    usuarios_permitidos = ['admin', 'NICOLAS']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    return render(request, "presupuestado/presupuestado_general.html",
                  {'subtotales': configuracion_para_tablas()})

# TABLA DINÁMICA FLEXIBLE
# Filtros de la tabla dinámica. Se aplican IGUAL en la tabla, en las listas de
# los filtros, en los registros del detalle y en redistribuir / inflación, para
# que lo que se ve y lo que se modifica sean siempre los mismos registros.
TD_FILTROS = ('mcncuenta', 'mcnzona', 'mcndestino', 'mcnccosto', 'ctanombre', 'responsable')
# Búsqueda general (parámetro "q"): texto contenido en cualquiera de estos campos.
TD_CAMPOS_BUSQUEDA = ('mcncuenta', 'ctanombre', 'vinnombre', 'mcndetalle', 'responsable')


def _td_filtrar(qs, fuente, campos=TD_FILTROS, excluir=()):
    """Aplica a `qs` los filtros de la tabla dinámica que vengan en `fuente`.

    `fuente` puede ser request.GET (valores "a,b,c") o el dict "filtros" del
    body JSON (listas). "q" es la búsqueda general.
    """
    for campo in campos:
        if campo in excluir:
            continue
        valores = fuente.get(campo)
        if isinstance(valores, str):
            valores = [v.strip() for v in valores.split(',')]
        valores = [v for v in (valores or []) if v not in (None, '')]
        if valores:
            qs = qs.filter(**{f'{campo}__in': valores})
    q = str(fuente.get('q') or '').strip()
    if q:
        condicion = Q()
        for campo in TD_CAMPOS_BUSQUEDA:
            condicion |= Q(**{f'{campo}__icontains': q})
        qs = qs.filter(condicion)
    return qs


@login_required
def obtener_tabla_dinamica_flexible(request):
    """
    ▼ Ahora también filtra por ctanombre si se envía en los parámetros GET.
    """
    try:
        group_by_param = request.GET.get('group_by', 'ctanombre,vinnombre,mcndetalle')
        campos_agrupacion = [campo.strip() for campo in group_by_param.split(',')]
 
        campos_validos = ['ctanombre', 'vinnombre', 'mcndetalle', 'mcncuenta']
        campos_agrupacion = [c for c in campos_agrupacion if c in campos_validos]
 
        if not campos_agrupacion:
            return JsonResponse({'error': 'No se especificaron campos válidos para agrupar'}, status=400)
 
        campos_select = list(set(campos_agrupacion + [
            'mcnfecha', 'mcnvaldebi', 'mcnvalcred',
            'mcncuenta', 'mcnzona', 'mcndestino', 'mcnccosto'
        ]))
 
        # Filtros (cuenta, zona, destino, costo, nombre cuenta, responsable) + búsqueda general
        queryset = _td_filtrar(Cuenta5Presupuestado.objects.all(), request.GET).values(*campos_select)
 
        tabla_dinamica = defaultdict(lambda: {
            **{campo: '' for campo in campos_agrupacion},
            'enero': 0, 'febrero': 0, 'marzo': 0, 'abril': 0,
            'mayo': 0, 'junio': 0, 'julio': 0, 'agosto': 0,
            'septiembre': 0, 'octubre': 0, 'noviembre': 0, 'diciembre': 0,
            'total': 0
        })
 
        MESES_ES = {
            1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
            5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
            9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
        }
 
        for row in queryset:
            fecha = excel_serial_to_date(row['mcnfecha'])
            if not fecha:
                continue
            fecha = datetime.datetime.strptime(fecha, '%Y-%m-%d').date()
            mes = MESES_ES[fecha.month]
 
            key_values = []
            for campo in campos_agrupacion:
                valor = row.get(campo) or f'SIN_{campo.upper()}'
                key_values.append(valor)
            key = tuple(key_values)
 
            saldo = (row['mcnvaldebi'] or 0) - (row['mcnvalcred'] or 0)
 
            for i, campo in enumerate(campos_agrupacion):
                tabla_dinamica[key][campo] = key_values[i]
 
            tabla_dinamica[key][mes] += saldo
            tabla_dinamica[key]['total'] += saldo
 
        for key in tabla_dinamica:
            for mes in MESES_ES.values():
                tabla_dinamica[key][mes] = round(tabla_dinamica[key][mes])
            tabla_dinamica[key]['total'] = round(tabla_dinamica[key]['total'])
 
        result = list(tabla_dinamica.values())
        result.sort(key=lambda x: tuple(x[campo] for campo in campos_agrupacion))
 
        return JsonResponse({
            'data': result,
            'recordsTotal': len(result),
            'recordsFiltered': len(result),
            'grouped_by': campos_agrupacion
        })
 
    except Exception as e:
        print(f"❌ Error en obtener_tabla_dinamica_flexible: {e}")
        return JsonResponse({'error': str(e)}, status=500)

def obtener_valores_filtros(request):
    """
    Retorna valores únicos disponibles para cada campo de filtro,
    teniendo en cuenta los filtros activos en los demás campos (filtrado en cascada).
    Ahora soporta también el campo ctanombre.
    """
    try:
        campo = request.GET.get('campo', '')
        if campo not in TD_FILTROS:
            return JsonResponse({'error': 'Campo no válido'}, status=400)

        # Filtros de los OTROS campos (no del que se consulta) + búsqueda general
        queryset = _td_filtrar(Cuenta5Presupuestado.objects.all(), request.GET, excluir=(campo,))
 
        valores = (
            queryset
            .values_list(campo, flat=True)
            .distinct()
            .order_by(campo)
        )
        valores = [v for v in valores if v]
 
        return JsonResponse({'valores': list(valores)})
 
    except Exception as e:
        print(f"❌ Error en obtener_valores_filtros: {e}")
        return JsonResponse({'error': str(e)}, status=500)
 
def tabla_dinamica_view(request):
    return render(request, 'presupuesto_consolidado/tabla_dinamica.html')

@require_http_methods(["GET"])
def obtener_registros_detalle(request):
    try:
        ctanombre  = request.GET.get('ctanombre', '')
        vinnombre  = request.GET.get('vinnombre', '')
        mcndetalle = request.GET.get('mcndetalle', '')

        if not ctanombre or not vinnombre or not mcndetalle:
            return JsonResponse({'error': 'Faltan parámetros obligatorios'}, status=400)

        queryset = Cuenta5Presupuestado.objects.filter(
            ctanombre=ctanombre,
            vinnombre=vinnombre,
            mcndetalle=mcndetalle,
        )

        # Mismos filtros de la tabla (ctanombre ya viene fijo por el nivel) + búsqueda general
        queryset = _td_filtrar(queryset, request.GET, excluir=('ctanombre',))

        registros = []
        for obj in queryset:
            registros.append({
                'id':         obj.pk,
                'mcnfecha':   obj.mcnfecha,
                'mcndetalle': obj.mcndetalle,
                'mcnvaldebi': float(obj.mcnvaldebi or 0),
                'mcnvalcred': float(obj.mcnvalcred or 0),
                'mcncuenta':  obj.mcncuenta,
                'mcnzona':    obj.mcnzona,
                'mcndestino': obj.mcndestino,
                'mcnccosto':  obj.mcnccosto,
                'ctanombre':  obj.ctanombre,
                'vinnombre':  obj.vinnombre,
                'responsable': obj.responsable,
            })

        return JsonResponse({'registros': registros, 'total': len(registros)})

    except Exception as e:
        print(f"❌ Error en obtener_registros_detalle: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["PUT", "PATCH"])
def editar_registro(request, registro_id):
    """
    Edita un registro individual de Cuenta5Base.
    Body JSON con los campos a actualizar.
    """
    try:
        obj = Cuenta5Presupuestado.objects.get(pk=registro_id)
    except Cuenta5Presupuestado.DoesNotExist:
        return JsonResponse({'error': 'Registro no encontrado'}, status=404)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    # Campos editables
    campos_editables = [
        'mcnfecha', 'mcndetalle', 'mcnvaldebi', 'mcnvalcred',
        'mcncuenta', 'mcnzona', 'mcndestino', 'mcnccosto',
        'ctanombre', 'vinnombre',
    ]

    for campo in campos_editables:
        if campo in body:
            setattr(obj, campo, body[campo])

    obj.save()

    return JsonResponse({
        'success': True,
        'message': f'Registro {registro_id} actualizado correctamente',
        'id': obj.pk,
    })

@csrf_exempt
@require_http_methods(["DELETE"])
def eliminar_registro(request, registro_id):
    """
    Elimina un registro individual de Cuenta5Base.
    """
    try:
        obj = Cuenta5Presupuestado.objects.get(pk=registro_id)
    except Cuenta5Presupuestado.DoesNotExist:
        return JsonResponse({'error': 'Registro no encontrado'}, status=404)

    obj.delete()

    return JsonResponse({
        'success': True,
        'message': f'Registro {registro_id} eliminado correctamente',
    })

@require_http_methods(["GET"])
def obtener_registros_nivel(request):
    try:
        nivel     = request.GET.get('nivel', '')
        ctanombre = request.GET.get('ctanombre', '')

        if not nivel or not ctanombre:
            return JsonResponse({'error': 'Faltan parámetros obligatorios'}, status=400)

        queryset = Cuenta5Presupuestado.objects.filter(ctanombre=ctanombre)

        if nivel == 'vinculo':
            vinnombre = request.GET.get('vinnombre', '')
            if not vinnombre:
                return JsonResponse({'error': 'Falta vinnombre'}, status=400)
            queryset = queryset.filter(vinnombre=vinnombre)

        # Mismos filtros de la tabla (ctanombre ya viene fijo por el nivel) + búsqueda general
        queryset = _td_filtrar(queryset, request.GET, excluir=('ctanombre',))

        registros = []
        for obj in queryset:
            registros.append({
                'id':         obj.pk,
                'mcnfecha':   obj.mcnfecha,
                'mcndetalle': obj.mcndetalle,
                'mcnvaldebi': float(obj.mcnvaldebi or 0),
                'mcnvalcred': float(obj.mcnvalcred or 0),
                'mcncuenta':  obj.mcncuenta,
                'mcnzona':    obj.mcnzona,
                'mcndestino': obj.mcndestino,
                'mcnccosto':  obj.mcnccosto,
                'ctanombre':  obj.ctanombre,
                'vinnombre':  obj.vinnombre,
                'responsable': obj.responsable,
            })

        return JsonResponse({'registros': registros, 'total': len(registros)})

    except Exception as e:
        print(f"❌ Error en obtener_registros_nivel: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["PUT", "PATCH"])
def renombrar_nivel(request):
    """
    Renombra en masa ctanombre o vinnombre en todos los registros que coincidan.
    Body JSON:
    - nivel: 'cuenta' o 'vinculo'
    - ctanombre_actual: valor actual
    - vinnombre_actual: valor actual (solo si nivel='vinculo')
    - ctanombre_nuevo: nuevo valor (solo si nivel='cuenta')
    - vinnombre_nuevo: nuevo valor (solo si nivel='vinculo')
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    nivel          = body.get('nivel', '')
    ctanombre_actual = body.get('ctanombre_actual', '')

    if not nivel or not ctanombre_actual:
        return JsonResponse({'error': 'Faltan parámetros'}, status=400)

    try:
        if nivel == 'cuenta':
            nuevo = body.get('ctanombre_nuevo', '').strip()
            if not nuevo:
                return JsonResponse({'error': 'Falta ctanombre_nuevo'}, status=400)
            count = Cuenta5Presupuestado.objects.filter(ctanombre=ctanombre_actual).update(ctanombre=nuevo)
            return JsonResponse({'success': True, 'actualizados': count, 'nuevo': nuevo})

        elif nivel == 'vinculo':
            vinnombre_actual = body.get('vinnombre_actual', '')
            nuevo = body.get('vinnombre_nuevo', '').strip()
            if not vinnombre_actual or not nuevo:
                return JsonResponse({'error': 'Faltan vinnombre_actual o vinnombre_nuevo'}, status=400)
            count = Cuenta5Presupuestado.objects.filter(
                ctanombre=ctanombre_actual,
                vinnombre=vinnombre_actual
            ).update(vinnombre=nuevo)
            return JsonResponse({'success': True, 'actualizados': count, 'nuevo': nuevo})

        else:
            return JsonResponse({'error': 'Nivel inválido'}, status=400)

    except Exception as e:
        print(f"❌ Error en renombrar_nivel: {e}")
        return JsonResponse({'error': str(e)}, status=500)

def _mes_de_serial(serial):
    """Serial Excel -> número de mes (1-12) o None."""
    fecha = excel_serial_to_date(serial)
    if not fecha:
        return None
    return datetime.datetime.strptime(fecha, '%Y-%m-%d').date().month


@csrf_exempt
@require_POST
def redistribuir_mes(request):
    """
    Redistribuye proporcionalmente un nuevo total mensual sobre los registros
    reales de Cuenta5Presupuestado. Garantiza que la suma final == nuevo_total.

    Body JSON:
      nivel: 'cuenta' | 'vinculo' | 'detalle'
      ctanombre, vinnombre, mcndetalle, mes (1-12), nuevo_total,
      filtros: {mcncuenta: [], mcnzona: [], mcndestino: [], mcnccosto: [], responsable: [], q: ''}
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    nivel      = body.get('nivel')
    ctanombre  = body.get('ctanombre') or ''
    vinnombre  = body.get('vinnombre') or ''
    mcndetalle = body.get('mcndetalle') or ''

    if nivel not in ('cuenta', 'vinculo', 'detalle') or not ctanombre:
        return JsonResponse({'error': 'Nivel o cuenta inválidos'}, status=400)

    try:
        mes = int(body.get('mes'))
        nuevo_total = int(round(float(body.get('nuevo_total'))))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'mes o nuevo_total inválidos'}, status=400)

    if not 1 <= mes <= 12:
        return JsonResponse({'error': 'Mes fuera de rango'}, status=400)

    qs = Cuenta5Presupuestado.objects.filter(ctanombre=ctanombre)
    if nivel in ('vinculo', 'detalle'):
        qs = qs.filter(vinnombre=vinnombre)
    if nivel == 'detalle':
        qs = qs.filter(mcndetalle=mcndetalle)

    # Mismos filtros que usa la tabla, para que el universo coincida
    qs = _td_filtrar(qs, body.get('filtros') or {}, excluir=('ctanombre',))

    registros = [r for r in qs if _mes_de_serial(r.mcnfecha) == mes]
    if not registros:
        return JsonResponse(
            {'error': 'No hay registros en ese mes para el nivel seleccionado. '
                      'No es posible distribuir el valor.'},
            status=400,
        )

    saldos = [(r.mcnvaldebi or 0) - (r.mcnvalcred or 0) for r in registros]
    total_actual = sum(saldos)
    n = len(registros)

    asignaciones = []
    acumulado = 0
    for i, (reg, saldo) in enumerate(zip(registros, saldos)):
        if i == n - 1:
            valor = nuevo_total - acumulado       # el último absorbe el residuo
        else:
            prop = (saldo / total_actual) if total_actual else (1 / n)
            valor = int(round(nuevo_total * prop))
            acumulado += valor
        asignaciones.append((reg, valor))

    with transaction.atomic():
        for reg, valor in asignaciones:
            # Saldo = débito - crédito. Normalizamos para que siempre cuadre.
            reg.mcnvaldebi = valor if valor >= 0 else 0
            reg.mcnvalcred = 0 if valor >= 0 else -valor
            reg.save(update_fields=['mcnvaldebi', 'mcnvalcred'])

    return JsonResponse({
        'success': True,
        'actualizados': n,
        'total_aplicado': nuevo_total,
        'total_anterior': total_actual,
    })

@csrf_exempt
@require_POST
def aplicar_inflacion(request):
    """
    Aplica un % de inflación al saldo de los registros de VARIOS nodos de la
    jerarquía a la vez. Los registros se deduplican por PK, así que aunque un
    objetivo quede contenido en otro, la inflación se aplica una sola vez.

    Body JSON:
      porcentaje: float (5 = +5%, -3.5 = -3.5%)
      meses: [1..12]  (opcional; por defecto todos)
      objetivos: [{nivel:'cuenta'|'vinculo'|'detalle',
                   ctanombre, vinnombre, mcndetalle}, ...]
      filtros: {mcncuenta: [], mcnzona: [], mcndestino: [], mcnccosto: [], responsable: [], q: ''}
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    objetivos = body.get('objetivos') or []
    if not objetivos:
        return JsonResponse({'error': 'No se seleccionó ninguna fila'}, status=400)

    try:
        porcentaje = float(body.get('porcentaje'))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Porcentaje inválido'}, status=400)

    if porcentaje < -100:
        return JsonResponse({'error': 'El porcentaje no puede ser menor a -100%'}, status=400)

    try:
        meses = {int(m) for m in (body.get('meses') or range(1, 13))}
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Meses inválidos'}, status=400)
    meses = {m for m in meses if 1 <= m <= 12}
    if not meses:
        return JsonResponse({'error': 'Debe indicar al menos un mes'}, status=400)

    # ── Un OR por cada objetivo seleccionado ──────────────────────────────
    condicion = Q()
    for o in objetivos:
        nivel     = o.get('nivel')
        ctanombre = o.get('ctanombre') or ''
        if nivel not in ('cuenta', 'vinculo', 'detalle') or not ctanombre:
            return JsonResponse({'error': f'Objetivo inválido: {o}'}, status=400)

        q = Q(ctanombre=ctanombre)
        if nivel in ('vinculo', 'detalle'):
            q &= Q(vinnombre=o.get('vinnombre') or '')
        if nivel == 'detalle':
            q &= Q(mcndetalle=o.get('mcndetalle') or '')
        condicion |= q

    qs = Cuenta5Presupuestado.objects.filter(condicion)

    # Mismos filtros de la tabla, para que el universo coincida con lo visible
    qs = _td_filtrar(qs, body.get('filtros') or {}, excluir=('ctanombre',))

    # distinct() + dict por PK: blindaje contra doble aplicación
    unicos = {}
    for r in qs.distinct():
        if _mes_de_serial(r.mcnfecha) in meses:
            unicos[r.pk] = r
    registros = list(unicos.values())

    if not registros:
        return JsonResponse(
            {'error': 'No hay registros en los meses seleccionados para las filas elegidas.'},
            status=400,
        )

    factor = 1 + porcentaje / 100.0
    total_ant = total_nue = 0

    with transaction.atomic():
        for reg in registros:
            saldo = (reg.mcnvaldebi or 0) - (reg.mcnvalcred or 0)
            nuevo = int(round(saldo * factor))
            total_ant += saldo
            total_nue += nuevo
            reg.mcnvaldebi = nuevo if nuevo >= 0 else 0
            reg.mcnvalcred = 0 if nuevo >= 0 else -nuevo
        Cuenta5Presupuestado.objects.bulk_update(
            registros, ['mcnvaldebi', 'mcnvalcred'], batch_size=500
        )

    return JsonResponse({
        'success': True,
        'actualizados': len(registros),
        'objetivos': len(objetivos),
        'porcentaje': porcentaje,
        'meses': sorted(meses),
        'total_anterior': total_ant,
        'total_nuevo': total_nue,
    })
    
@csrf_exempt
@require_http_methods(["DELETE"])
def eliminar_nivel(request):
    """
    Elimina en masa todos los registros de un nivel jerárquico.
    Parámetros GET:
    - nivel: 'cuenta' o 'vinculo'
    - ctanombre: requerido siempre
    - vinnombre: requerido si nivel='vinculo'
    """
    try:
        nivel     = request.GET.get('nivel', '')
        ctanombre = request.GET.get('ctanombre', '')

        if not nivel or not ctanombre:
            return JsonResponse({'error': 'Faltan parámetros'}, status=400)

        queryset = Cuenta5Presupuestado.objects.filter(ctanombre=ctanombre)

        if nivel == 'vinculo':
            vinnombre = request.GET.get('vinnombre', '')
            if not vinnombre:
                return JsonResponse({'error': 'Falta vinnombre'}, status=400)
            queryset = queryset.filter(vinnombre=vinnombre)
        elif nivel != 'cuenta':
            return JsonResponse({'error': 'Nivel inválido'}, status=400)

        count, _ = queryset.delete()
        return JsonResponse({'success': True, 'eliminados': count})

    except Exception as e:
        print(f"❌ Error en eliminar_nivel: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────
# GET /presupuesto/consolidado-base/carga/
# Renderiza el template de carga
# ─────────────────────────────────────────────────────────────
# Sedes que ofrece el formulario de carga, en orden y con su etiqueta.
# Se derivan de SEDE_CONFIG_CONSOLIDADO para no mantener una lista aparte.
SEDES_CARGA = [
    ('tulua',   'Tuluá'),
    ('buga',    'Buga'),
    ('cartago', 'Cartago'),
    ('cali',    'Cali'),
]
ORIGENES_CARGA = [
    ('ejecutado',     'Ejecutado'),
    ('presupuestado', 'Presupuestado'),
]
# ─────────────────────────────────────────────────────────────
# Opciones válidas
# ─────────────────────────────────────────────────────────────
SEDES_VALIDAS = {s for s, _ in SEDES_CARGA} | {''}
ORIGENES_VALIDOS = {o for o, _ in ORIGENES_CARGA} | {''}


def vista_carga_consolidado_base(request):
    anio_actual = timezone.now().year
    return render(request, 'presupuesto_consolidado/carga_consolidado_base.html', {
        'sedes': SEDES_CARGA,
        'origenes': ORIGENES_CARGA,
        'anio_actual': anio_actual,
        # El presupuesto siempre se arma para el año siguiente
        'anio_presupuesto': anio_actual + 1,
        'anio_min': anio_actual - 10,
        'anio_max': anio_actual + 5,
    })


# ─────────────────────────────────────────────────────────────
# POST /presupuesto/cargar_consolidado_total_base/
# Recibe lista de registros y hace upsert (insert or update)
# ─────────────────────────────────────────────────────────────
@require_POST
def cargar_consolidado_total_base(request):
    try:
        body     = json.loads(request.body)
        registros = body.get('registros', [])

        if not registros:
            return JsonResponse({'success': False, 'error': 'Sin registros'}, status=400)

        # ── Validar sede y origen a nivel de lote ──────────────
        sede   = str(body.get('sede',   '') or '').strip().lower()
        origen = str(body.get('origen', '') or '').strip().lower()

        if sede not in SEDES_VALIDAS:
            return JsonResponse(
                {'success': False, 'error': f"Sede inválida. Opciones: {', '.join(sorted(SEDES_VALIDAS))}"},
                status=400,
            )
        if origen not in ORIGENES_VALIDOS:
            return JsonResponse(
                {'success': False, 'error': f"Origen inválido. Opciones: {', '.join(sorted(ORIGENES_VALIDOS))}"},
                status=400,
            )

        insertados  = 0
        actualizados = 0

        for r in registros:
            # Normalizar fecha
            fecha_raw = r.get('mcnfecha')
            if not fecha_raw:
                continue
            try:
                fecha = datetime.datetime.strptime(str(fecha_raw).strip(), '%Y-%m-%d').date()
            except ValueError:
                continue

            mcncuenta   = str(r.get('mcncuenta',  '') or '').strip()
            mcnccosto   = str(r.get('mcnccosto',  '0') or '0').strip()
            ctanombre   = str(r.get('ctanombre',  '') or '').strip()
            valor       = _to_bigint(r.get('valor'))
            total_anual = _to_bigint(r.get('total_anual'))

            if not mcncuenta:
                continue

            # Upsert: clave única = (mcncuenta, mcnccosto, mcnfecha, sede, origen)
            obj, created = ConsolidadoTotalBase.objects.update_or_create(
                mcncuenta=mcncuenta,
                mcnccosto=mcnccosto,
                mcnfecha=fecha,
                sede=sede,
                origen=origen,
                defaults={
                    'ctanombre':   ctanombre,
                    'valor':       valor,
                    'total_anual': total_anual,
                },
            )
            if created:
                insertados += 1
            else:
                actualizados += 1

        return JsonResponse({
            'success':     True,
            'insertados':  insertados,
            'actualizados': actualizados,
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────
# GET /presupuesto/obtener_consolidado_total_base_raw/
# Devuelve todos los registros en bruto para el historial
# ─────────────────────────────────────────────────────────────
@require_GET
def obtener_consolidado_total_base_raw(request):
    try:
        # Filtros opcionales por sede y/o origen vía query params
        sede   = request.GET.get('sede',   '').strip().lower() or None
        origen = request.GET.get('origen', '').strip().lower() or None

        qs = ConsolidadoTotalBase.objects.all()
        if sede:
            qs = qs.filter(sede=sede)
        if origen:
            qs = qs.filter(origen=origen)

        qs = qs.order_by('mcncuenta', 'mcnfecha').values(
            'id', 'mcncuenta', 'mcnccosto', 'ctanombre',
            'mcnfecha', 'valor', 'total_anual', 'sede', 'origen',
        )

        data = [
            {
                'id':          row['id'],
                'mcncuenta':   row['mcncuenta']   or '',
                'mcnccosto':   row['mcnccosto']   or '',
                'ctanombre':   row['ctanombre']   or '',
                'mcnfecha':    str(row['mcnfecha']) if row['mcnfecha'] else '',
                'valor':       row['valor'],
                'total_anual': row['total_anual'],
                'sede':        row['sede']        or '',
                'origen':      row['origen']      or '',
            }
            for row in qs
        ]
        return JsonResponse({'success': True, 'data': data})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────
# POST /presupuesto/borrar_consolidado_total_base/
# Acepta filtros opcionales sede y/o origen; sin filtros borra todo
# ─────────────────────────────────────────────────────────────
@require_POST
def borrar_consolidado_total_base(request):
    try:
        body   = json.loads(request.body) if request.body else {}
        sede   = str(body.get('sede',   '') or '').strip().lower() or None
        origen = str(body.get('origen', '') or '').strip().lower() or None

        qs = ConsolidadoTotalBase.objects.all()
        if sede:
            if sede not in SEDES_VALIDAS:
                return JsonResponse(
                    {'success': False, 'error': f"Sede inválida. Opciones: {', '.join(sorted(SEDES_VALIDAS))}"},
                    status=400,
                )
            # Sin importar mayúsculas ni espacios en lo guardado (p. ej. "TULUA ").
            qs = qs.annotate(_sede=Trim('sede')).filter(_sede__iexact=sede)
        if origen:
            if origen not in ORIGENES_VALIDOS:
                return JsonResponse(
                    {'success': False, 'error': f"Origen inválido. Opciones: {', '.join(sorted(ORIGENES_VALIDOS))}"},
                    status=400,
                )
            qs = qs.annotate(_origen=Trim('origen')).filter(_origen__iexact=origen)

        eliminados, _ = ConsolidadoTotalBase.objects.filter(pk__in=qs.values('pk')).delete()
        return JsonResponse({'success': True, 'eliminados': eliminados})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ─────────────────────────────────────────────────────────────
# POST /presupuesto/eliminar_fila_consolidado_total_base/
# ─────────────────────────────────────────────────────────────
@require_POST
def eliminar_fila_consolidado_total_base(request):
    try:
        body = json.loads(request.body)
        pk   = body.get('id')
        if not pk:
            return JsonResponse({'success': False, 'error': 'id requerido'}, status=400)
        eliminados, _ = ConsolidadoTotalBase.objects.filter(pk=pk).delete()
        if not eliminados:
            return JsonResponse({'success': False, 'error': 'Registro no encontrado'}, status=404)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ─────────────────────────────────────────────────────────────
# POST /presupuesto/eliminar_filtrado_consolidado_total_base/
# Elimina TODO lo que cumple los filtros del historial (no solo las filas
# que se ven en pantalla, que se cortan en 1.000), en una sola consulta.
#
# Body JSON:
#   accion:   "contar" (no borra, solo devuelve cuántos) | "eliminar"
#   esperado: (con "eliminar") el número que se le mostró al usuario; si los
#             datos cambiaron entre contar y eliminar, no se borra nada (409).
#   filtros:  solo los filtros ACTIVOS. Una lista vacía significa "ninguno"
#             (no coincide nada), igual que en la pantalla.
#       sede, origen, mcnfecha (AAAA-MM-DD), mcncuenta, ctanombre: [valores]
#       q:   texto contenido en "cuenta nombre" (la caja de búsqueda)
#       ids: [ids] (casillas marcadas)
# ─────────────────────────────────────────────────────────────
CTB_FILTROS_TEXTO = ('sede', 'origen', 'mcncuenta', 'ctanombre')


def _ctb_filtrar(filtros):
    """QuerySet de ConsolidadoTotalBase con los mismos criterios del historial."""
    qs = ConsolidadoTotalBase.objects.all()
    for campo in CTB_FILTROS_TEXTO:
        if campo in filtros:
            valores = [str(v).strip() for v in (filtros.get(campo) or [])]
            # La pantalla compara el valor sin espacios a los lados: aquí igual.
            qs = qs.annotate(**{f'_f_{campo}': Trim(campo)}).filter(**{f'_f_{campo}__in': valores})
    if 'mcnfecha' in filtros:
        fechas = []
        for v in filtros.get('mcnfecha') or []:
            try:
                fechas.append(datetime.date.fromisoformat(str(v).strip()))
            except ValueError:
                raise ValueError(f'Fecha inválida en el filtro: {v}')
        qs = qs.filter(mcnfecha__in=fechas)
    if 'ids' in filtros:
        qs = qs.filter(pk__in=[int(i) for i in (filtros.get('ids') or [])])
    q = str(filtros.get('q') or '').strip()
    if q:
        qs = qs.annotate(_f_texto=Concat(Coalesce('mcncuenta', Value('')), Value(' '),
                                         Coalesce('ctanombre', Value(''))))
        qs = qs.filter(_f_texto__icontains=q)
    return qs


@login_required
@require_POST
def eliminar_filtrado_consolidado_total_base(request):
    try:
        body = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)

    filtros = body.get('filtros') or {}
    accion = body.get('accion', 'contar')
    if accion not in ('contar', 'eliminar'):
        return JsonResponse({'success': False, 'error': 'Acción inválida'}, status=400)

    try:
        qs = _ctb_filtrar(filtros)
    except (TypeError, ValueError) as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

    if accion == 'contar':
        return JsonResponse({'success': True, 'total': qs.count()})

    try:
        esperado = int(body.get('esperado'))
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Falta "esperado" (cuántos se confirmaron)'}, status=400)

    with log_carga('eliminar_consolidado_base', request, filtros=sorted(filtros)) as info, transaction.atomic():
        ids = list(qs.values_list('pk', flat=True))
        if len(ids) != esperado:
            info['resultado'] = 'cambio_de_datos'
            return JsonResponse({
                'success': False,
                'error': (f'Los datos cambiaron: ahora hay {len(ids)} registros con esos filtros '
                          f'(se confirmaron {esperado}). No se eliminó nada; revisa e intenta de nuevo.'),
                'total': len(ids),
            }, status=409)
        eliminados, _ = ConsolidadoTotalBase.objects.filter(pk__in=ids).delete()
        info['registros'] = eliminados

    return JsonResponse({'success': True, 'eliminados': eliminados})


# ─────────────────────────────────────────────────────────────
# Utilidad interna
# ─────────────────────────────────────────────────────────────
def _to_bigint(value):
    if value is None or value == '':
        return None
    if isinstance(value, (int, float)):
        return int(value)
    texto = str(value).strip()
    # Formato colombiano ("1.234.567,89") solo si trae coma decimal
    if ',' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    try:
        return int(float(texto))
    except (ValueError, TypeError):
        return None

# ---------------------------------------------------------------------------
# AÑADIR A views.py
# ---------------------------------------------------------------------------
# Requiere que arriba del archivo ya existan (si no, añadirlos):
#   from django.views.decorators.http import require_GET, require_POST
#   from .models import ComentarioComparativo   (o el import equivalente
#       si tu archivo usa "from .models import *")
# ---------------------------------------------------------------------------

SEDES_COMPARATIVO = {'tulua', 'buga', 'cartago', 'cali', 'consolidado'}


@login_required
def comparativo_general(request):
    """
    Página única de comparativo: pestañas para las 4 sedes + el total,
    con columna de comentarios editable y guardado automático.
    """
    usuarios_permitidos = ['admin', 'NICOLAS']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    # Consolidado = año en curso (ejecutado); Presupuestado = año siguiente.
    # Salen de las mismas funciones que usa el presupuesto por áreas.
    anio_c, anio_p = anio_elaboracion(), anio_presupuesto()
    return render(request, "comparativo/comparativo_general.html", {
        'subtotales': configuracion_para_tablas(),
        'sufijo_consolidado': f"-{anio_c % 100:02d}",
        'sufijo_presupuestado': f"-{anio_p % 100:02d}",
    })


@require_GET
def obtener_comentarios_comparativo(request, sede):
    """
    Devuelve todos los comentarios guardados para una sede, como un
    diccionario { fila_key: comentario }.
    """
    sede = (sede or '').strip().lower()
    if sede not in SEDES_COMPARATIVO:
        return JsonResponse({'error': f'Sede inválida: {sede}'}, status=400)

    data = {
        c.fila_key: (c.comentario or '')
        for c in ComentarioComparativo.objects.filter(sede=sede)
    }
    return JsonResponse({'data': data})


@login_required
@require_POST
def guardar_comentario_comparativo(request):
    """
    Crea o actualiza el comentario de una fila específica dentro de una sede.
    Body JSON esperado:
        {
            "sede": "tulua",
            "fila_key": "541001",
            "comentario": "texto libre...",
            "mcncuenta": "541001",       (opcional, solo referencia)
            "ctanombre": "Honorarios"    (opcional, solo referencia)
        }
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)

    sede = str(body.get('sede', '')).strip().lower()
    fila_key = str(body.get('fila_key', '')).strip()
    comentario = body.get('comentario', '') or ''
    mcncuenta = str(body.get('mcncuenta', '') or '')
    ctanombre = str(body.get('ctanombre', '') or '')

    if sede not in SEDES_COMPARATIVO:
        return JsonResponse({'success': False, 'error': f'Sede inválida: {sede}'}, status=400)
    if not fila_key:
        return JsonResponse({'success': False, 'error': 'fila_key es obligatorio'}, status=400)

    usuario = request.user.username if request.user.is_authenticated else ''

    obj, _ = ComentarioComparativo.objects.update_or_create(
        sede=sede,
        fila_key=fila_key,
        defaults={
            'comentario': comentario,
            'mcncuenta': mcncuenta,
            'ctanombre': ctanombre,
            'actualizado_por': usuario,
        },
    )
    return JsonResponse({'success': True, 'fila_key': fila_key, 'comentario': obj.comentario})


# ══════════════════════════════════════════════════════════════════
#  PRESUPUESTO DE VENTAS POR SEDE  (cuentas 1, 2, 41750201)
#
#  Por cada sede (tulua, buga, cartago, cali):
#  1. Toma el EJECUTADO de esa sede en ConsolidadoTotalBase.
#  2. Por cada mes: VENTAS NETAS = cuenta 1 + cuenta 2 + cuenta 41750201
#     participación(cuenta) = valor(cuenta) / VENTAS NETAS
#  3. valor = proyección del centro de operación en ese mes × participación
#     (proyección = tabla "Proyección presupuesto centro operación - Ventas").
#     Así crédito + contado + descuentos = la proyección del mes.
#  4. Guarda en ConsolidadoTotalBase con la sede y origen='presupuestado'.
#
#  Pegar al FINAL de views.py, reemplazando la versión anterior.
#  Necesita que ya estén definidos más arriba: calculo, MESES_ES,
#  SEDE_CONFIG_CONSOLIDADO, NOMBRES_CENTRO_OPERACION (todos existen hoy).
# ══════════════════════════════════════════════════════════════════

from django.db import connection

# Entero fijo cualquiera: identifica el candado de este proceso en PostgreSQL
LOCK_PRESUPUESTO_VENTAS = 874231001

CUENTAS_VENTAS = {
    '1':        'Ventas a crédito',
    '2':        'Ventas a contado',
    '41750201': 'Descuentos otorgados x pto pago',
}



def repartir_proyeccion(proyeccion, participacion):
    """Reparte la proyección de un mes entre las cuentas de ventas.

    valor(cuenta) = proyección × participación(cuenta)
    (los descuentos tienen participación negativa, así que quedan negativos).

    Las participaciones suman 1, así que los valores suman la proyección; los
    pesos que se pierden al redondear se le asignan a la cuenta de mayor peso
    para que la suma sea EXACTA.

    Ej. Tuluá enero: 1.238.511.267 × 61,6236 % = 763.215.019 (ventas a crédito).
    """
    valores = {cta: round(proyeccion * pct) for cta, pct in participacion.items()}
    if valores:
        residuo = round(proyeccion) - sum(valores.values())
        if residuo:
            mayor = max(participacion, key=lambda c: abs(participacion[c]))
            valores[mayor] += residuo
    return valores

# sede (ConsolidadoTotalBase) -> nombre_centro_de_operacion (BdVentasComercial)
# Se arma con los códigos de zona que ya existen, así no hay un tercer mapeo que mantener:
#   tulua -> 1 -> ALMACEN TULUA, buga -> 2 -> ALMACEN BUGA, ...
SEDE_CENTRO_OPERACION = {
    sede: NOMBRES_CENTRO_OPERACION[cfg['zona'][1]]
    for sede, cfg in SEDE_CONFIG_CONSOLIDADO.items()
    if cfg is not None
}


def _proyeccion_ventas_por_centro():
    """
    {nombre_centro_de_operacion: {mes: valor}} del año siguiente.
    Es la misma fuente que calculo.construir_ventas('centro') usa para las
    filas del año siguiente, así que los valores coinciden con la tabla
    "Proyección presupuesto centro operación - Ventas".
    """
    detalle = calculo._proyeccion_mensual_detalle()
    if detalle.empty:
        return {}

    agrupado = (
        detalle.groupby(['nombre_centro_de_operacion', 'mes'])['valor_proyectado_mes']
        .sum().fillna(0).round()
    )
    resultado = defaultdict(dict)
    for (centro, mes), valor in agrupado.items():
        resultado[centro][int(mes)] = int(valor)
    return resultado


def _participacion_ventas_sede(anio_base, sede):
    """
    {mes: {cuenta: porcentaje}} del ejecutado de una sede.
    participación = valor de la cuenta / VENTAS NETAS (cuentas 1 + 2 + 41750201).
    Las cuentas se reconocen por número o por nombre.
    """
    nombre = SEDE_CONFIG_CONSOLIDADO[sede]['nombre']
    filas = (
        ConsolidadoTotalBase.objects
        .filter(origen='ejecutado', mcnfecha__year=anio_base, sede__icontains=nombre)
        .filter(q_cuentas_clave(CUENTAS_VENTAS))
        .values('mcnfecha__month', 'mcncuenta', 'ctanombre', 'valor')
    )

    por_mes = defaultdict(lambda: dict.fromkeys(CUENTAS_VENTAS, 0))
    anual = dict.fromkeys(CUENTAS_VENTAS, 0)
    for f in filas:
        cta = resolver_cuenta_clave(f['mcncuenta'], f['ctanombre'])
        if cta not in CUENTAS_VENTAS:
            continue
        valor = f['valor'] or 0
        por_mes[f['mcnfecha__month']][cta] += valor
        anual[cta] += valor

    def a_porcentaje(valores):
        ventas_netas = sum(valores.values())
        if not ventas_netas:
            return None
        return {cta: val / ventas_netas for cta, val in valores.items()}

    participacion_anual = a_porcentaje(anual)
    if participacion_anual is None:
        return None

    return {
        mes: (a_porcentaje(por_mes[mes]) if mes in por_mes else None) or participacion_anual
        for mes in range(1, 13)
    }

def _anio_base_sede(sede, anio_pedido=None):
    """
    Último año con ventas ejecutadas de ESA sede. Antes se usaba un único
    año global (el máximo entre todas las sedes), así que si una sede iba
    más adelantada que el resto, las demás quedaban sin participación.
    `anio_pedido` actúa como tope: nunca se usa un año posterior.
    """
    nombre = SEDE_CONFIG_CONSOLIDADO[sede]['nombre']
    qs = (
        ConsolidadoTotalBase.objects
        .filter(origen='ejecutado', mcnfecha__isnull=False, sede__icontains=nombre)
        .filter(q_cuentas_clave(CUENTAS_VENTAS))
    )
    if anio_pedido:
        qs = qs.filter(mcnfecha__year__lte=anio_pedido)

    anios = sorted({
        fecha.year for cta, nom, fecha in
        qs.values_list('mcncuenta', 'ctanombre', 'mcnfecha').iterator()
        if resolver_cuenta_clave(cta, nom) in CUENTAS_VENTAS
    })
    return anios[-1] if anios else None

def generar_presupuesto_ventas(anio_base=None):
    """
    anio_base: año del ejecutado del que se toma la participación.
               Si es None se usa el último año con ventas ejecutadas.
    El año del presupuesto es el mismo que proyecta calculo.construir_ventas
    (año actual + 1).
    Idempotente: borra lo generado antes para ese año y lo vuelve a crear.
    """
    anio_ppto = timezone.now().year + 1

    proyeccion = _proyeccion_ventas_por_centro()
    if not proyeccion:
        year_actual = timezone.now().year
        hay_recientes = BdVentasComercial.objects.filter(lapso__gte=(year_actual - 1) * 100 + 1).exists()
        if not hay_recientes:
            raise ValueError(
                f'No hay ventas en bd_ventas_comercial desde {year_actual - 1}. '
                f'Vuelve a importar el Excel de ventas comercial para poder proyectar {anio_ppto}.'
            )
        raise ValueError(f'No hay proyección de ventas por centro de operación para {anio_ppto}')

    nuevos, procesadas, omitidas = [], [], {}
    participacion_resp, detalle_resp, anios_usados = {}, {}, {}

    for sede, centro in SEDE_CENTRO_OPERACION.items():
        anio_sede = _anio_base_sede(sede, anio_base)
        if anio_sede is None:
            omitidas[sede] = (
                f'sin ventas ejecutadas hasta {anio_base}' if anio_base
                else 'sin ventas ejecutadas en ConsolidadoTotalBase'
            )
            continue
        participacion = _participacion_ventas_sede(anio_sede, sede)
        if participacion is None:
            omitidas[sede] = f'sin ventas ejecutadas en {anio_sede}'
            continue

        proy_centro = proyeccion.get(centro, {})
        faltantes = [MESES_ES[m] for m in range(1, 13) if m not in proy_centro]
        if faltantes:
            omitidas[sede] = f"sin proyección de {centro} para: {', '.join(faltantes)}"
            continue

        # ── cálculo: cada cuenta = proyección del mes × su participación ──
        #   ej.: crédito 61,62 %, contado 38,90 %, descuentos -0,53 %
        #        → la suma de las tres es la proyección del mes
        valores = {cta: {} for cta in CUENTAS_VENTAS}
        for mes in range(1, 13):
            for cta, valor in repartir_proyeccion(proy_centro[mes], participacion[mes]).items():
                valores[cta][mes] = valor

        for cta, meses in valores.items():
            total_anual = sum(meses.values())
            for mes, valor in meses.items():
                nuevos.append(ConsolidadoTotalBase(
                    mcncuenta=cta,
                    mcnccosto=None,      # sin centro de costo: evita reagrupaciones (ej. 0101 → 5105)
                    ctanombre=CUENTAS_VENTAS[cta],
                    mcnfecha=datetime.date(anio_ppto, mes, 1),
                    valor=valor,
                    total_anual=total_anual,
                    sede=sede,           # tulua | buga | cartago | cali
                    origen='presupuestado',
                ))

        procesadas.append(sede)
        anios_usados[sede] = anio_sede
        participacion_resp[sede] = {
            MESES_ES[m]: {cta: round(p * 100, 4) for cta, p in pcts.items()}
            for m, pcts in participacion.items()
        }
        detalle_resp[sede] = {
            'centro_operacion': centro,
            'proyeccion': {MESES_ES[m]: v for m, v in sorted(proy_centro.items())},
            'cuentas': {
                cta: {MESES_ES[m]: v for m, v in meses.items()}
                for cta, meses in valores.items()
            },
        }

    if not procesadas:
        raise ValueError(
            'No se pudo generar ninguna sede → '
            + '; '.join(f'{s}: {motivo}' for s, motivo in omitidas.items())
        )

    # Se borra lo generado antes para las sedes procesadas y también las filas
    # con sede='TOTAL' que dejaba la versión anterior (si no, el total se duplica).
    filtro_sede = Q()
    for s in procesadas + ['total']:
        filtro_sede |= Q(sede__iexact=s)

    with transaction.atomic():
        if connection.vendor == 'postgresql':      # el candado solo existe en PostgreSQL
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_xact_lock(%s)', [LOCK_PRESUPUESTO_VENTAS])

        previas = (
            ConsolidadoTotalBase.objects
            .filter(filtro_sede, origen='presupuestado', mcnfecha__year=anio_ppto)
            .filter(q_cuentas_clave(CUENTAS_VENTAS))
            .values_list('id', 'mcncuenta', 'ctanombre')
        )
        ids = [pk for pk, cta, nom in previas if resolver_cuenta_clave(cta, nom) in CUENTAS_VENTAS]
        ConsolidadoTotalBase.objects.filter(id__in=ids).delete()
        ConsolidadoTotalBase.objects.bulk_create(nuevos)

    return {
        'anio_base': anios_usados,
        'anio_presupuesto': anio_ppto,
        'registros': len(nuevos),
        'sedes_procesadas': procesadas,
        'sedes_omitidas': omitidas,
        'participacion': participacion_resp,
        'detalle': detalle_resp,
    }


# ══════════════════════════════════════════════════════════════════
#  VISTA
# ══════════════════════════════════════════════════════════════════

@login_required
@require_POST
def generar_presupuesto_ventas_view(request):
    """POST  { "anio_base": 2026 }   (opcional)"""
    if request.user.username not in ['admin', 'NICOLAS']:
        return JsonResponse({'success': False, 'error': 'Sin permisos'}, status=403)
    # Queda en el log del servidor (logger presupuestoApp.cargas): INICIO, FIN
    # con la duración, o ERROR con el traceback. Un INICIO sin FIN ni ERROR
    # indica que el servidor cortó la petición por tiempo (timeout del worker).
    try:
        body = json.loads(request.body or '{}')
        anio = body.get('anio_base')
        with log_carga('presupuesto_ventas', request, anio_base=anio) as info:
            resultado = generar_presupuesto_ventas(int(anio) if anio else None)
            info.update(registros=resultado['registros'],
                        sedes=','.join(resultado['sedes_procesadas']),
                        omitidas=','.join(resultado['sedes_omitidas']))
        return JsonResponse({'success': True, **resultado})
    except (ValueError, json.JSONDecodeError) as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except DatabaseError as e:
        # Base de datos no disponible (p. ej. durante un despliegue): el navegador reintenta.
        return JsonResponse({'success': False, 'reintentar': True,
                             'error': f'La base de datos no está disponible: {e}'}, status=503)
    except Exception as e:
        # Error del cálculo: reintentar no lo arregla, así que se avisa de una vez
        # (antes se veía como "servidor no disponible" y se reintentaba 3 minutos).
        return JsonResponse({'success': False, 'reintentar': False,
                             'error': f'Error al generar el presupuesto de ventas: {e}'}, status=500)
