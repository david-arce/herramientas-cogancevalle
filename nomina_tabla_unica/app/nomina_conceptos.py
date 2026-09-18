"""
Datos de origen de la nómina (tabla `conceptos_nomina`).

  - Qué año se usa como base y cuántos meses tienen datos reales.
  - Importación del Excel de conceptos fijos y variables.
  - Resumen por año para el tablero.

Reglas de año:
  año base      → conceptos de nómina (sueldos, comisiones, horas extra, ...)
  año base - 1  → auxilio de educación (se paga con el dato del año anterior)
"""
import datetime as dt
import io
import re
import unicodedata
from collections import Counter, defaultdict

import pandas as pd
from django.db import transaction
from django.db.models import Count, Max, Q, Sum

from .models_nomina import MESES, ConceptosNomina, ConfiguracionNomina

MESES = list(MESES)

CAMPOS_TEXTO = ('centro_tra', 'nombre_cen', 'codcosto', 'nomcosto', 'tipocpto', 'cuenta',
                'concepto', 'nombre_con', 'cargo', 'nombrecar', 'nombre')
CAMPOS_CODIGO = ('centro_tra', 'codcosto', 'cuenta', 'cargo', 'concepto', 'tipocpto')
COLUMNAS_PLANTILLA = ['CENTRO_TRA', 'NOMBRE_CEN', 'CODCOSTO', 'NOMCOSTO', 'TIPOCPTO', 'CUENTA',
                      'CONCEPTO', 'NOMBRE_CON', 'CARGO', 'NOMBRECAR', 'CEDULA', 'NOMBRE',
                      'FECHA_INGRESO', 'ARLPORC', 'CONCEPTO_F', *[m.upper() for m in MESES], 'TOTAL']

# Encabezado normalizado del Excel → campo del modelo
ALIAS = {
    **{c.upper(): c for c in (*CAMPOS_TEXTO, 'cedula', 'arlporc', 'concepto_f')},
    **{m.upper(): m for m in MESES},
    'SETIEMBRE': 'septiembre', 'SEPT': 'septiembre',
    'ENE': 'enero', 'FEB': 'febrero', 'MAR': 'marzo', 'ABR': 'abril', 'MAY': 'mayo',
    'JUN': 'junio', 'JUL': 'julio', 'AGO': 'agosto', 'SEP': 'septiembre',
    'OCT': 'octubre', 'NOV': 'noviembre', 'DIC': 'diciembre',
    'NOMBRE_CENTRO': 'nombre_cen', 'NOMBRE_COSTO': 'nomcosto', 'NOMBRE_CONCEPTO': 'nombre_con',
    'NOMBRE_CARGO': 'nombrecar', 'ARL': 'arlporc', 'ARL_PORC': 'arlporc',
    'VALOR_FIJO': 'concepto_f', 'DOCUMENTO': 'cedula', 'IDENTIFICACION': 'cedula',
    # fecha de ingreso (en el Excel viene como FECHAINGRE)
    'FECHAINGRE': 'fecha_ingreso', 'FECHA_INGRE': 'fecha_ingreso', 'FECHA_INGRESO': 'fecha_ingreso',
    'FECHA_DE_INGRESO': 'fecha_ingreso', 'INGRESO': 'fecha_ingreso', 'FEC_INGRESO': 'fecha_ingreso',
    # columnas opcionales de año / fecha
    'ANIO': '_anio', 'ANO': '_anio', 'YEAR': '_anio', 'PERIODO': '_anio', 'VIGENCIA': '_anio',
    'FECHA': '_fecha', 'FECHA_CORTE': '_fecha',
}
OBLIGATORIAS = ('cedula', 'concepto')

ANIO_MIN, ANIO_MAX = 2000, 2100


class ErrorImportacion(Exception):
    pass


# ══════════════════════════════════════════════════════════════════════
#  Año base y meses reales
# ══════════════════════════════════════════════════════════════════════

def anios_cargados():
    return list(ConceptosNomina.objects.order_by('-anio')
                .values_list('anio', flat=True).distinct())


def anio_base():
    """Año configurado o, si está en automático, el más reciente cargado."""
    config = ConfiguracionNomina.actual()
    if config.anio_base:
        return config.anio_base
    anios = anios_cargados()
    return anios[0] if anios else dt.date.today().year


def _ultimo_mes_con_datos(anio):
    """Índice (1‑12) del último mes que tiene algún valor en ese año."""
    sumas = ConceptosNomina.objects.filter(anio=anio).aggregate(
        **{f'n_{m}': Count('id', filter=~Q(**{m: 0})) for m in MESES})
    ultimo = 0
    for i, mes in enumerate(MESES, start=1):
        if sumas[f'n_{mes}']:
            ultimo = i
    return ultimo


def meses_detectados(anio):
    """Meses reales de un año: el de su fecha de corte, o el último con datos."""
    corte = ConceptosNomina.objects.filter(anio=anio).aggregate(f=Max('fecha_corte'))['f']
    if corte and corte.year == anio:
        return corte.month
    return _ultimo_mes_con_datos(anio)


def meses_reales(anio):
    """Cuántos meses (desde enero) se toman como histórico para ese año."""
    config = ConfiguracionNomina.actual()
    if config.meses_reales and anio == anio_base():
        return max(1, min(12, config.meses_reales))
    return meses_detectados(anio)


def resumen_anios():
    base = anio_base()
    filas = (ConceptosNomina.objects.values('anio')
             .annotate(filas=Count('id'), personas=Count('cedula', distinct=True),
                       sin_cuenta=Count('id', filter=Q(cuenta='') & ~Q(nomcosto='')),
                       con_ingreso=Count('id', filter=~Q(fecha_ingreso=None)),
                       nomcostos=Count('nomcosto', distinct=True, filter=~Q(nomcosto='')),
                       total=Sum('total'), corte=Max('fecha_corte'), cargado=Max('cargado'))
             .order_by('-anio'))
    salida = []
    for f in filas:
        usos = []
        if f['anio'] == base:
            usos.append('Conceptos de nómina')
        if f['anio'] == base - 1:
            usos.append('Auxilio de educación')
        n = meses_detectados(f['anio'])
        salida.append({**f, 'meses': n, 'hasta': MESES[n - 1].capitalize() if n else '—',
                       'usos': usos})
    return salida


def guardar_configuracion(anio=None, meses=None):
    config = ConfiguracionNomina.actual()
    config.anio_base = anio or None
    config.meses_reales = meses or None
    config.save()
    return config


# ══════════════════════════════════════════════════════════════════════
#  Importación de Excel
# ══════════════════════════════════════════════════════════════════════

def _normalizar_encabezado(valor):
    texto = unicodedata.normalize('NFKD', str(valor)).encode('ascii', 'ignore').decode()
    texto = re.sub(r'[^A-Za-z0-9]+', '_', texto).strip('_').upper()
    return texto


def _es_vacio(valor):
    if valor is None:
        return True
    if isinstance(valor, str):
        return not valor.strip()
    try:
        return bool(pd.isna(valor))
    except (TypeError, ValueError):
        return False


def _texto(valor):
    if _es_vacio(valor):
        return ''
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    texto = str(valor).strip()
    return texto[:-2] if re.fullmatch(r'-?\d+\.0', texto) else texto


def _codigo(valor):
    """'1' → '001' (Excel suele perder los ceros de los códigos numéricos)."""
    texto = _texto(valor)
    return texto.zfill(3) if texto.isdigit() and len(texto) < 3 else texto


def _numero(valor):
    if _es_vacio(valor):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace('$', '').replace(' ', '')
    if ',' in texto and '.' in texto:            # 1.234.567,89
        texto = texto.replace('.', '').replace(',', '.')
    elif ',' in texto:                           # 1234,5  ó  1,234,567
        partes = texto.split(',')
        texto = texto.replace(',', '.') if len(partes) == 2 and len(partes[1]) != 3 \
            else texto.replace(',', '')
    elif texto.count('.') > 1:                   # 1.234.567
        texto = texto.replace('.', '')
    try:
        return float(texto)
    except ValueError:
        return 0.0


def _entero(valor):
    return int(round(_numero(valor)))


def _cedula(valor):
    digitos = re.sub(r'\D', '', _texto(valor))
    return int(digitos) if digitos else None


def _fecha(valor):
    if _es_vacio(valor):
        return None
    if isinstance(valor, dt.datetime):
        return valor.date()
    if isinstance(valor, dt.date):
        return valor
    fecha = pd.to_datetime(str(valor), dayfirst=True, errors='coerce')
    return None if pd.isna(fecha) else fecha.date()


EXCEL_CERO = dt.date(1899, 12, 30)     # día 0 del calendario de Excel


def _fecha_excel(valor):
    """Fecha que puede venir como número de serie de Excel (44167 → 31/12/2020)."""
    if _es_vacio(valor):
        return None
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        dias = int(round(float(valor)))
        if not 1 <= dias <= 80000:        # fuera del rango razonable de fechas
            return None
        return EXCEL_CERO + dt.timedelta(days=dias)
    texto = _texto(valor)
    if re.fullmatch(r'\d{4,6}', texto):   # el mismo número, pero escrito como texto
        return _fecha_excel(int(texto))
    return _fecha(valor)


def _anio_de(valor):
    if _es_vacio(valor):
        return None
    fecha = _fecha(valor) if not isinstance(valor, (int, float)) else None
    anio = fecha.year if fecha else _entero(valor)
    return anio if ANIO_MIN <= anio <= ANIO_MAX else None


def leer_archivo(archivo, hoja=None):
    """DataFrame con encabezados ya traducidos a campos del modelo."""
    nombre = (getattr(archivo, 'name', '') or '').lower()
    contenido = archivo.read()
    try:
        if nombre.endswith('.csv'):
            texto = contenido.decode('utf-8-sig', errors='replace')
            separador = ';' if texto[:2000].count(';') > texto[:2000].count(',') else ','
            df = pd.read_csv(io.StringIO(texto), sep=separador, dtype=object)
        else:
            df = pd.read_excel(io.BytesIO(contenido), sheet_name=hoja or 0, dtype=object)
    except ImportError as exc:
        raise ErrorImportacion(f'Falta una librería para leer el archivo ({exc}). '
                               'Para .xls instale xlrd, o guarde el archivo como .xlsx.')
    except Exception as exc:                      # noqa: BLE001
        raise ErrorImportacion(f'No se pudo leer el archivo: {exc}')

    # El encabezado puede no estar en la primera fila (títulos arriba)
    if not _tiene_obligatorias(df.columns):
        for i in range(min(15, len(df))):
            if _tiene_obligatorias(df.iloc[i].tolist()):
                df.columns = df.iloc[i].tolist()
                df = df.iloc[i + 1:]
                break

    columnas, desconocidas = {}, []
    for original in df.columns:
        campo = ALIAS.get(_normalizar_encabezado(original))
        if campo and campo not in columnas.values():
            columnas[original] = campo
        elif not str(original).startswith('Unnamed') and campo is None:
            desconocidas.append(str(original))
    df = df[list(columnas)].rename(columns=columnas)

    faltan = [c.upper() for c in OBLIGATORIAS if c not in df.columns]
    if faltan:
        raise ErrorImportacion('El archivo no tiene las columnas obligatorias: ' + ', '.join(faltan))
    if not any(m in df.columns for m in MESES) and 'concepto_f' not in df.columns:
        raise ErrorImportacion('El archivo no tiene columnas de meses (ENERO…DICIEMBRE) ni CONCEPTO_F.')
    return df, desconocidas


def _tiene_obligatorias(encabezados):
    campos = {ALIAS.get(_normalizar_encabezado(e)) for e in encabezados if not _es_vacio(e)}
    return all(c in campos for c in OBLIGATORIAS)


def clave_nomcosto(valor):
    """NOMCOSTO normalizado: sin tildes, mayúsculas y espacios simples."""
    texto = unicodedata.normalize('NFKD', _texto(valor)).encode('ascii', 'ignore').decode()
    return ' '.join(texto.upper().split())


def completar_cuentas(registros):
    """Pone la cuenta a los registros que no la traen, según su NOMCOSTO.

    Primero usa las cuentas del mismo archivo; si el NOMCOSTO no tiene ninguna
    ahí, usa la de los datos ya cargados (cualquier año, la más reciente).
    Devuelve (completadas, sin_cuenta).
    """
    del_archivo = defaultdict(Counter)
    for r in registros:
        if r.cuenta and r.nomcosto:
            del_archivo[clave_nomcosto(r.nomcosto)][r.cuenta] += 1

    guardadas = {}
    faltan = {clave_nomcosto(r.nomcosto) for r in registros if not r.cuenta and r.nomcosto}
    faltan -= set(del_archivo)
    if faltan:
        for nomcosto, cuenta in (ConceptosNomina.objects.exclude(cuenta='').exclude(nomcosto='')
                                 .order_by('-anio').values_list('nomcosto', 'cuenta')):
            guardadas.setdefault(clave_nomcosto(nomcosto), cuenta)

    completadas = sin_cuenta = 0
    for r in registros:
        if r.cuenta or not r.nomcosto:
            continue
        clave = clave_nomcosto(r.nomcosto)
        cuenta = (del_archivo[clave].most_common(1)[0][0] if clave in del_archivo
                  else guardadas.get(clave, ''))
        if cuenta:
            r.cuenta = cuenta
            completadas += 1
        else:
            sin_cuenta += 1
    return completadas, sin_cuenta


def importar(archivo, anio, fecha_corte=None, reemplazar=True, usuario='', hoja=None):
    """Carga el Excel en conceptos_nomina.

    anio         año que se asigna a las filas (si el archivo trae una columna
                 AÑO/FECHA con valor, ese valor tiene prioridad en su fila).
    fecha_corte  opcional: hasta dónde llegan los datos reales.
    reemplazar   True → borra antes los datos de los años que trae el archivo.
    """
    if fecha_corte and not anio:
        anio = fecha_corte.year
    if not anio or not ANIO_MIN <= int(anio) <= ANIO_MAX:
        raise ErrorImportacion('Indique el año al que corresponden los datos.')
    anio = int(anio)

    df, desconocidas = leer_archivo(archivo, hoja)
    nombre_archivo = getattr(archivo, 'name', '')[:255]
    registros, omitidas, anios = [], 0, set()

    for fila in df.to_dict('records'):
        cedula = _cedula(fila.get('cedula'))
        concepto = _codigo(fila.get('concepto'))
        if cedula is None and not concepto:
            omitidas += 1                    # filas vacías o de totales
            continue

        anio_fila = _anio_de(fila.get('_anio')) or \
            (_fecha(fila.get('_fecha')).year if _fecha(fila.get('_fecha')) else None) or anio
        anios.add(anio_fila)
        corte = fecha_corte if anio_fila == anio else None

        datos = {c: (_codigo if c in CAMPOS_CODIGO else _texto)(fila.get(c))
                 for c in CAMPOS_TEXTO}
        datos['nombre_cen'] = datos['nombre_cen'].upper()
        datos['nomcosto'] = datos['nomcosto'].upper()
        datos['nombrecar'] = datos['nombrecar'].upper()
        arl = fila.get('arlporc')
        registro = ConceptosNomina(
            anio=anio_fila, fecha_corte=corte, cedula=cedula,
            fecha_ingreso=_fecha_excel(fila.get('fecha_ingreso')),
            arlporc=None if _es_vacio(arl) else _numero(arl),
            concepto_f=_entero(fila.get('concepto_f')),
            archivo=nombre_archivo, cargado_por=usuario,
            **datos, **{m: _entero(fila.get(m)) for m in MESES},
        )
        registro.total = sum(getattr(registro, m) for m in MESES)
        registros.append(registro)

    if not registros:
        raise ErrorImportacion('El archivo no tiene filas con cédula o concepto.')

    # La cuenta va ligada al NOMCOSTO: se completa en las filas que no la traen
    cuentas_completadas, sin_cuenta = completar_cuentas(registros)

    with transaction.atomic():
        borradas = 0
        if reemplazar:
            borradas, _ = ConceptosNomina.objects.filter(anio__in=anios).delete()
        ConceptosNomina.objects.bulk_create(registros, batch_size=2000)

    return {
        'filas': len(registros), 'omitidas': omitidas, 'borradas': borradas,
        'anios': sorted(anios), 'ignoradas': desconocidas,
        'con_columna_cuenta': 'cuenta' in df.columns,
        'cuentas_completadas': cuentas_completadas, 'sin_cuenta': sin_cuenta,
        'meses': {a: meses_detectados(a) for a in sorted(anios)},
    }


def borrar_anio(anio):
    return ConceptosNomina.objects.filter(anio=anio).delete()[0]


def plantilla_excel():
    """Bytes de un .xlsx vacío con las columnas esperadas."""
    salida = io.BytesIO()
    with pd.ExcelWriter(salida, engine='openpyxl') as writer:
        pd.DataFrame(columns=COLUMNAS_PLANTILLA).to_excel(writer, sheet_name='Conceptos', index=False)
    return salida.getvalue()
