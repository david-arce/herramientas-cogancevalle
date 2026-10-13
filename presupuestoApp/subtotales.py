"""
Filas calculadas del Consolidado (Ejecutado) / Presupuestado / Comparativo:
qué cuentas suma cada una.

Son las filas que no tienen cuenta propia (VENTAS NETAS, GASTOS DE
ADMINISTRACIÓN, OTROS INGRESOS, GASTOS POR SERVICIOS...) y las partes con que
se arman los márgenes y resultados (costo de ventas, descuentos y
bonificaciones). Antes las cuentas estaban escritas en el JavaScript de cada
plantilla; ahora se guardan en la tabla SubtotalCuentas y se editan en
Ajustes → Filas calculadas.

    configuracion_subtotales()
      -> {"OtrosIngresos": {"nombre": "Otros Ingresos", "cuentas": [...], "prefijos": [...],
                            "personalizado": False}, ...}

Las plantillas reciben ese diccionario (json_script "configSubtotales") y
static/js/subtotales.js hace las sumas con él.

Una cuenta entra en la fila si:
  - está en `cuentas` (igual al código de la fila de la tabla), o
  - empieza por alguno de los `prefijos`.
"""
import re

from .models import SubtotalCuentas

PATRON_CODIGO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
MAX_CODIGOS = 300

# Orden = orden en que se muestran en Ajustes. Los valores por defecto son
# exactamente los que estaban en las plantillas (no cambian los resultados).
CATALOGO = [
    {
        "clave": "VentasNetas",
        "nombre": "Ventas Netas",
        "fila": "VENTAS NETAS",
        "descripcion": "Ingresos por ventas descontando el pronto pago. Es la base de todos los porcentajes.",
        "donde": "Todas las pestañas",
        "cuentas": [],
        "prefijos": ["1", "2", "41750201"],
    },
    {
        "clave": "CostoVentas",
        "nombre": "Costo de Ventas",
        "fila": None,
        "descripcion": "Se resta de las Ventas Netas para el Margen Bruto y da el % Costo de Ventas.",
        "donde": "Todas las pestañas",
        "cuentas": [],
        "prefijos": ["613522"],
    },
    {
        "clave": "AjustesMargenContribucion",
        "nombre": "Descuentos y bonificaciones",
        "fila": None,
        "descripcion": "Se suman al Margen Bruto para obtener el Margen de Contribución.",
        "donde": "Todas las pestañas",
        "cuentas": [],
        "prefijos": ["4240900101", "4240909502"],
    },
    {
        "clave": "54",
        "nombre": "Gastos de Ventas",
        "fila": "GASTOS DE VENTAS",
        "descripcion": "Se resta para la Utilidad Operacional.",
        "donde": "Todas las pestañas",
        "cuentas": [],
        "prefijos": ["54"],
    },
    {
        "clave": "51",
        "nombre": "Gastos de Administración",
        "fila": "GASTOS DE ADMINISTRACIÓN",
        "descripcion": "Se resta para la Utilidad Operacional. La fila solo se muestra en Total Base.",
        "donde": "Todas las pestañas (la fila, solo en Total Base)",
        "cuentas": [],
        "prefijos": ["51"],
    },
    {
        "clave": "GastosFinancieros",
        "nombre": "Gastos Financieros",
        "fila": "Gastos Financieros",
        "descripcion": "Gastos bancarios, contribuciones e intereses. Se restan en Excedentes o Pérdida Neta.",
        "donde": "Total Base (Ejecutado y Presupuestado)",
        "cuentas": [],
        "prefijos": ["521005", "521015", "521020", "3", "615035"],
    },
    {
        "clave": "AsistenciaTecnica",
        "nombre": "Asistencia Técnica",
        "fila": "ASISTENCIA TECNICA",
        "descripcion": "Ingresos de los programas y convenios. Parte de los Ingresos por Servicios.",
        "donde": "Total Base (Ejecutado y Presupuestado)",
        "cuentas": [],
        "prefijos": ["AT", "VT"],
    },
    {
        "clave": "OtrosIngresos",
        "nombre": "Otros Ingresos",
        "fila": "OTROS INGRESOS",
        "descripcion": "Ingresos no operacionales: patrocinios, proyecto aftosa, venta de activos, etc. "
                       "Parte de los Ingresos por Servicios.",
        "donde": "Total Base (Ejecutado y Presupuestado)",
        "cuentas": [
            "41659505", "41659501", "422004", "422507", "422529",
            "4240900202", "4240900301", "4240900401",
            "4240909501", "4240909503", "4240909901", "4", "420560",
        ],
        "prefijos": [],
    },
    {
        "clave": "GastosPorServicios",
        "nombre": "Gastos por Servicios",
        "fila": "GASTOS POR SERVICIOS",
        "descripcion": "Gastos de los proyectos y programas de servicios. Se restan en Excedentes o Pérdida Neta.",
        "donde": "Total Base (Ejecutado y Presupuestado)",
        "cuentas": ["5", "6", "7", "8", "5230"],
        "prefijos": [],
    },
]
POR_CLAVE = {c["clave"]: c for c in CATALOGO}


def limpiar_codigos(valor):
    """Lista o texto ("541009, 541033 at-00003") -> lista sin repetidos, en mayúsculas."""
    if isinstance(valor, str):
        valor = re.split(r"[\s,;]+", valor)
    salida = []
    for v in valor or []:
        v = str(v).strip().upper()
        if v and v not in salida:
            salida.append(v)
    return salida


def validar(cuentas, prefijos):
    errores = []
    if len(cuentas) + len(prefijos) > MAX_CODIGOS:
        errores.append(f"Son demasiadas cuentas (máx. {MAX_CODIGOS} entre cuentas y prefijos).")
    for etiqueta, lista in (("cuenta", cuentas), ("prefijo", prefijos)):
        for c in lista:
            if len(c) > 60 or not PATRON_CODIGO.match(c):
                errores.append(f"«{c}» no es un {etiqueta} válido: solo letras, números, guion o guion bajo.")
    for c in set(cuentas) & set(prefijos):
        errores.append(f"«{c}» está como cuenta exacta y como prefijo; déjalo en uno solo.")
    return errores


def suma_cuenta(cfg, codigo):
    """True si la fila calculada `cfg` suma la cuenta `codigo` de la tabla."""
    codigo = str(codigo or "")
    return bool(codigo) and (codigo in cfg["cuentas"] or any(codigo.startswith(p) for p in cfg["prefijos"]))


def configuracion_subtotales():
    """{clave: {nombre, fila, descripcion, donde, cuentas, prefijos, personalizado, ...}} en el orden del catálogo."""
    guardadas = {s.clave: s for s in SubtotalCuentas.objects.all()}
    salida = {}
    for c in CATALOGO:
        g = guardadas.get(c["clave"])
        salida[c["clave"]] = {
            "nombre": c["nombre"],
            "fila": c["fila"],
            "descripcion": c["descripcion"],
            "donde": c["donde"],
            "cuentas": list(g.cuentas or []) if g else list(c["cuentas"]),
            "prefijos": list(g.prefijos or []) if g else list(c["prefijos"]),
            "por_defecto": {"cuentas": list(c["cuentas"]), "prefijos": list(c["prefijos"])},
            "personalizado": g is not None,
            "actualizado": g.actualizado if g else None,
            "actualizado_por": g.actualizado_por if g else "",
        }
    return salida


def configuracion_para_tablas():
    """Solo lo que necesitan las tablas (va embebido en la página)."""
    return {
        clave: {"nombre": c["nombre"], "cuentas": c["cuentas"], "prefijos": c["prefijos"]}
        for clave, c in configuracion_subtotales().items()
    }
