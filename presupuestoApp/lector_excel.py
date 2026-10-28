"""Lectura de Excel (.xlsx) grandes por partes, con poca memoria.

`pd.read_excel` arma en memoria todas las celdas del archivo antes de
devolver algo: con el informe de ventas (≈350.000 filas × 55 columnas)
usa varios GB y tarda minutos, y el servidor termina cortando la petición
(error 502). Aquí el XML de la hoja se recorre fila por fila y solo se
guardan las columnas pedidas, así la memoria se mantiene baja (decenas de
MB) sin importar el tamaño del archivo.

Los .xls (formato viejo, no es un zip) se leen con pandas como antes.
"""
import zipfile

import pandas as pd
from lxml import etree

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
NS_REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'


def _indice_columna(referencia):
    """'A1' -> 0, 'AB12' -> 27."""
    indice = 0
    for letra in referencia:
        if letra.isdigit():
            break
        indice = indice * 26 + (ord(letra.upper()) - 64)
    return indice - 1


def _textos_compartidos(zf):
    if 'xl/sharedStrings.xml' not in zf.namelist():
        return []
    textos = []
    with zf.open('xl/sharedStrings.xml') as fh:
        for _, si in etree.iterparse(fh, tag=NS + 'si'):
            # solo el texto visible (<t>), sin la pronunciación fonética (<rPh>)
            textos.append(''.join(t.text or '' for t in si.iter(NS + 't')
                                  if t.getparent().tag != NS + 'rPh'))
            si.clear()
    return textos


def _ruta_primera_hoja(zf):
    """Ruta del XML de la primera hoja según workbook.xml (no siempre es sheet1.xml)."""
    try:
        libro = etree.fromstring(zf.read('xl/workbook.xml'))
        hoja = libro.find(f'{NS}sheets/{NS}sheet')
        rid = hoja.get(NS_REL + 'id')
        rels = etree.fromstring(zf.read('xl/_rels/workbook.xml.rels'))
        for rel in rels:
            if rel.get('Id') == rid:
                destino = rel.get('Target').lstrip('/')
                return destino if destino.startswith('xl/') else 'xl/' + destino
    except (KeyError, AttributeError, etree.XMLSyntaxError):
        pass
    hojas = sorted(n for n in zf.namelist() if n.startswith('xl/worksheets/sheet'))
    if not hojas:
        raise ValueError('El archivo no tiene hojas')
    return hojas[0]


def _valor(celda, compartidos):
    tipo = celda.get('t')
    if tipo == 'inlineStr':
        return ''.join(t.text or '' for t in celda.iter(NS + 't'))
    v = celda.find(NS + 'v')
    if v is None or v.text is None:
        return None
    if tipo == 's':
        return compartidos[int(v.text)]
    if tipo in ('str', 'e', 'd'):
        return v.text
    if tipo == 'b':
        return v.text == '1'
    numero = float(v.text)
    return int(numero) if numero.is_integer() else numero


def leer_columnas_xlsx(archivo, es_util, al_avanzar=None, cada=50000):
    """DataFrame con las columnas del archivo cuyo encabezado cumpla `es_util`.

    archivo: ruta o archivo abierto (.xlsx). La primera fila son los encabezados.
    al_avanzar(n): se llama cada `cada` filas leídas (para mostrar avance).
    """
    if not zipfile.is_zipfile(archivo):                 # .xls viejo
        if hasattr(archivo, 'seek'):
            archivo.seek(0)
        return pd.read_excel(archivo, usecols=es_util)
    if hasattr(archivo, 'seek'):
        archivo.seek(0)

    with zipfile.ZipFile(archivo) as zf:
        compartidos = _textos_compartidos(zf)
        columnas = None            # {índice de columna: nombre}
        datos = {}
        n = 0
        with zf.open(_ruta_primera_hoja(zf)) as fh:
            for _, fila in etree.iterparse(fh, tag=NS + 'row'):
                posicion = -1
                valores = {}
                for celda in fila.iter(NS + 'c'):
                    ref = celda.get('r')
                    posicion = _indice_columna(ref) if ref else posicion + 1
                    if columnas is None or posicion in columnas:
                        valores[posicion] = _valor(celda, compartidos)
                if columnas is None:
                    columnas = {i: str(v).strip() for i, v in valores.items()
                                if v is not None and es_util(str(v).strip())}
                    datos = {i: [] for i in columnas}
                elif any(v is not None and v != '' for v in valores.values()):   # salta filas vacías
                    for i, lista in datos.items():
                        lista.append(valores.get(i))
                    n += 1
                    if al_avanzar and n % cada == 0:
                        al_avanzar(n)
                # liberar lo ya leído
                fila.clear()
                while fila.getprevious() is not None:
                    del fila.getparent()[0]

    if columnas is None:
        return pd.DataFrame()
    return pd.DataFrame({columnas[i]: datos[i] for i in columnas})
