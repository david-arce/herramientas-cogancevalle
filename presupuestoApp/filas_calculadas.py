"""
Filas calculadas (subtotales) del Ejecutado / Presupuestado / Comparativo con un
código propio, para que estén en Orden de cuentas como cualquier otra fila:

    CALC-VENTAS-NETAS, CALC-MARGEN-BRUTO, CALC-UTILIDAD-OPERACIONAL, ...

En Orden de cuentas se pueden mover (su posición en las tablas es la de la
lista), renombrar y ocultar por pestaña (Total / Sede), igual que una cuenta.
Cómo se calcula cada una está en static/js/filas_calculadas.js y las cuentas
que suman en Ajustes → Filas calculadas (subtotales.py).

ubicar(codigos) agrega a una lista de Orden de cuentas las filas calculadas
que falten, en el mismo lugar donde las ponían antes las tablas (Total Base).
"""

PREFIJO = "CALC-"

# codigo, tipo (el que usan las tablas), nombre por defecto, ¿se muestra en las sedes?
FILAS = [
    ("CALC-VENTAS-NETAS",             "VentasNetas",            "VENTAS NETAS",              True),
    ("CALC-GASTOS-VENTAS",            "54",                     "GASTOS DE VENTAS",          True),
    ("CALC-GASTOS-ADMINISTRACION",    "51",                     "GASTOS DE ADMINISTRACIÓN",  False),
    ("CALC-PCT-COSTO-VENTAS",         "PctCostoVentas",         "% Costo de Ventas",         True),
    ("CALC-MARGEN-BRUTO",             "MargenBruto",            "Margen Bruto",              True),
    ("CALC-PCT-MARGEN-BRUTO",         "PctMargenBruto",         "% Margen Bruto",            True),
    ("CALC-MARGEN-CONTRIBUCION",      "MargenContribucion",     "Margen de Contribución",    True),
    ("CALC-PCT-MARGEN-CONTRIBUCION",  "PctMargenContribucion",  "% Margen de Contribución",  True),
    ("CALC-UTILIDAD-OPERACIONAL",     "UtilidadOperacional",    "Utilidad Operacional",      True),
    ("CALC-PCT-UTILIDAD-OPERACIONAL", "PctUtilidadOperacional", "% Utilidad Operacional",    True),
    ("CALC-GASTOS-FINANCIEROS",       "GastosFinancieros",      "Gastos Financieros",        False),
    ("CALC-INGRESOS-SERVICIOS",       "IngresosPorServicios",   "INGRESOS POR SERVICIOS",    False),
    ("CALC-ASISTENCIA-TECNICA",       "AsistenciaTecnica",      "ASISTENCIA TECNICA",        False),
    ("CALC-OTROS-INGRESOS",           "OtrosIngresos",          "OTROS INGRESOS",            False),
    ("CALC-GASTOS-SERVICIOS",         "GastosPorServicios",     "GASTOS POR SERVICIOS",      False),
    ("CALC-EXCEDENTES",               "ExcedentesPerdidaNeta",  "EXCEDENTES O PERDIDA NETA", True),
    ("CALC-PCT-EXCEDENTES",           "PctExcedentes",          "% Excedente o Pérdida",     True),
]
CODIGOS = {f[0] for f in FILAS}
NOMBRES = {f[0]: f[2] for f in FILAS}
EN_SEDE = {f[0] for f in FILAS if f[3]}

# Dónde iban antes (las reglas fijas de la pestaña Total Base). Cada bloque se
# ubica respecto a las cuentas de la lista; si la cuenta de referencia no está,
# el bloque va al final (Ventas Netas, al principio).
_BLOQUES = [
    ({"antes_de_prefijo": "1", "si_no": "inicio"},          ["CALC-VENTAS-NETAS"]),
    ({"antes_de_prefijo": "54"},                            ["CALC-GASTOS-VENTAS"]),
    ({"antes_de_prefijo": "51"},                            ["CALC-GASTOS-ADMINISTRACION"]),
    ({"antes_de": "5"},                                     ["CALC-GASTOS-SERVICIOS"]),
    ({"despues_de": "613522"},                              ["CALC-PCT-COSTO-VENTAS", "CALC-MARGEN-BRUTO",
                                                             "CALC-PCT-MARGEN-BRUTO"]),
    ({"despues_de": "4240909502"},                          ["CALC-MARGEN-CONTRIBUCION", "CALC-PCT-MARGEN-CONTRIBUCION"]),
    ({"despues_del_ultimo": ["51"]},                        ["CALC-UTILIDAD-OPERACIONAL", "CALC-PCT-UTILIDAD-OPERACIONAL",
                                                             "CALC-GASTOS-FINANCIEROS"]),
    ({"despues_de": "615035"},                              ["CALC-INGRESOS-SERVICIOS", "CALC-ASISTENCIA-TECNICA"]),
    ({"despues_del_ultimo": ["AT", "VT"]},                  ["CALC-OTROS-INGRESOS"]),
    ({"despues_de": "5230"},                                ["CALC-EXCEDENTES", "CALC-PCT-EXCEDENTES"]),
]


def es_calculada(codigo):
    return str(codigo or "") in CODIGOS


def _umbral(ancla, lista):
    """Posición (puede ser x.5) donde va el bloque dentro de `lista`."""
    cuentas = [c if not es_calculada(c) else None for c in lista]
    i, despues = -1, False
    if "antes_de_prefijo" in ancla:
        i = next((n for n, c in enumerate(cuentas) if c and c.startswith(ancla["antes_de_prefijo"])), -1)
    elif "antes_de" in ancla:
        i = cuentas.index(ancla["antes_de"]) if ancla["antes_de"] in cuentas else -1
    elif "despues_de" in ancla:
        i = cuentas.index(ancla["despues_de"]) if ancla["despues_de"] in cuentas else -1
        despues = True
    elif "despues_del_ultimo" in ancla:
        for n, c in enumerate(cuentas):
            if c and any(c.startswith(p) for p in ancla["despues_del_ultimo"]):
                i = n
        despues = True
    if i < 0:
        return -1 if ancla.get("si_no") == "inicio" else float("inf")
    return i + 0.5 if despues else i


def ubicar(codigos):
    """La lista con las filas calculadas que falten insertadas en su lugar por defecto.

    No mueve nada de lo que ya está (ni las filas calculadas que el usuario ya ubicó).
    """
    lista = [str(c) for c in codigos]
    presentes = set(lista)
    pendientes = []
    for n, (ancla, codigos_bloque) in enumerate(_BLOQUES):
        faltan = [c for c in codigos_bloque if c not in presentes]
        if faltan:
            pendientes.append((_umbral(ancla, lista), n, faltan))
    pendientes.sort(key=lambda p: (p[0], p[1]))

    resultado, k = [], 0
    for i, c in enumerate(lista):
        while k < len(pendientes) and pendientes[k][0] <= i:
            resultado.extend(pendientes[k][2]); k += 1
        resultado.append(c)
    while k < len(pendientes):
        resultado.extend(pendientes[k][2]); k += 1
    return resultado
