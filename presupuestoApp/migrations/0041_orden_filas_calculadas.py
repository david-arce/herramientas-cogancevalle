# Agrega a Orden de cuentas las filas calculadas (subtotales) con un código
# propio CALC-..., para poder moverlas, renombrarlas y ocultarlas como cualquier
# otra fila:
#
#   CALC-VENTAS-NETAS, CALC-MARGEN-BRUTO, CALC-UTILIDAD-OPERACIONAL, ...
#
# Se insertan donde hoy las ponen las tablas (pestaña Total Base), sin mover
# nada de lo que ya está, y la lista se renumera de 10 en 10.
#   Total = Sí en todas.  Sede = Sí en las que hoy salen en las pestañas por sede.
# Si Orden de cuentas está vacía no se hace nada: las tablas usan el orden por
# defecto (que ya las incluye) y "Sincronizar" las agrega al poblar la lista.
#
# Reversible: al revertir se borran las filas CALC-.

from django.db import migrations

# Copia congelada de filas_calculadas.py (código, nombre, ¿en sedes?)
FILAS = [
    ("CALC-VENTAS-NETAS", "VENTAS NETAS", True),
    ("CALC-GASTOS-VENTAS", "GASTOS DE VENTAS", True),
    ("CALC-GASTOS-ADMINISTRACION", "GASTOS DE ADMINISTRACIÓN", False),
    ("CALC-PCT-COSTO-VENTAS", "% Costo de Ventas", True),
    ("CALC-MARGEN-BRUTO", "Margen Bruto", True),
    ("CALC-PCT-MARGEN-BRUTO", "% Margen Bruto", True),
    ("CALC-MARGEN-CONTRIBUCION", "Margen de Contribución", True),
    ("CALC-PCT-MARGEN-CONTRIBUCION", "% Margen de Contribución", True),
    ("CALC-UTILIDAD-OPERACIONAL", "Utilidad Operacional", True),
    ("CALC-PCT-UTILIDAD-OPERACIONAL", "% Utilidad Operacional", True),
    ("CALC-GASTOS-FINANCIEROS", "Gastos Financieros", False),
    ("CALC-INGRESOS-SERVICIOS", "INGRESOS POR SERVICIOS", False),
    ("CALC-ASISTENCIA-TECNICA", "ASISTENCIA TECNICA", False),
    ("CALC-OTROS-INGRESOS", "OTROS INGRESOS", False),
    ("CALC-GASTOS-SERVICIOS", "GASTOS POR SERVICIOS", False),
    ("CALC-EXCEDENTES", "EXCEDENTES O PERDIDA NETA", True),
    ("CALC-PCT-EXCEDENTES", "% Excedente o Pérdida", True),
]
CODIGOS = {f[0] for f in FILAS}

BLOQUES = [
    ({"antes_de_prefijo": "1", "si_no": "inicio"}, ["CALC-VENTAS-NETAS"]),
    ({"antes_de_prefijo": "54"}, ["CALC-GASTOS-VENTAS"]),
    ({"antes_de_prefijo": "51"}, ["CALC-GASTOS-ADMINISTRACION"]),
    ({"antes_de": "5"}, ["CALC-GASTOS-SERVICIOS"]),
    ({"despues_de": "613522"}, ["CALC-PCT-COSTO-VENTAS", "CALC-MARGEN-BRUTO", "CALC-PCT-MARGEN-BRUTO"]),
    ({"despues_de": "4240909502"}, ["CALC-MARGEN-CONTRIBUCION", "CALC-PCT-MARGEN-CONTRIBUCION"]),
    ({"despues_del_ultimo": ["51"]}, ["CALC-UTILIDAD-OPERACIONAL", "CALC-PCT-UTILIDAD-OPERACIONAL",
                                      "CALC-GASTOS-FINANCIEROS"]),
    ({"despues_de": "615035"}, ["CALC-INGRESOS-SERVICIOS", "CALC-ASISTENCIA-TECNICA"]),
    ({"despues_del_ultimo": ["AT", "VT"]}, ["CALC-OTROS-INGRESOS"]),
    ({"despues_de": "5230"}, ["CALC-EXCEDENTES", "CALC-PCT-EXCEDENTES"]),
]


def _umbral(ancla, lista):
    cuentas = [c if c not in CODIGOS else None for c in lista]
    i, despues = -1, False
    if "antes_de_prefijo" in ancla:
        i = next((n for n, c in enumerate(cuentas) if c and c.startswith(ancla["antes_de_prefijo"])), -1)
    elif "antes_de" in ancla:
        i = cuentas.index(ancla["antes_de"]) if ancla["antes_de"] in cuentas else -1
    elif "despues_de" in ancla:
        i = cuentas.index(ancla["despues_de"]) if ancla["despues_de"] in cuentas else -1
        despues = True
    else:
        for n, c in enumerate(cuentas):
            if c and any(c.startswith(p) for p in ancla["despues_del_ultimo"]):
                i = n
        despues = True
    if i < 0:
        return -1 if ancla.get("si_no") == "inicio" else float("inf")
    return i + 0.5 if despues else i


def _ubicar(lista):
    presentes = set(lista)
    pendientes = []
    for n, (ancla, codigos) in enumerate(BLOQUES):
        faltan = [c for c in codigos if c not in presentes]
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


def agregar(apps, schema_editor):
    OrdenCuenta = apps.get_model("presupuestoApp", "OrdenCuenta")
    filas = list(OrdenCuenta.objects.order_by("orden", "id"))
    if not filas:
        return
    por_codigo = {o.mcncuenta: o for o in filas}
    codigos = _ubicar([o.mcncuenta for o in filas])
    datos = {f[0]: f for f in FILAS}
    for c in codigos:
        if c not in por_codigo:
            _, nombre, en_sede = datos[c]
            por_codigo[c] = OrdenCuenta.objects.create(
                mcncuenta=c, ctanombre=nombre, orden=0, visible_total=True, visible_sede=en_sede)
    for i, c in enumerate(codigos):
        o = por_codigo[c]
        if o.orden != (i + 1) * 10:
            o.orden = (i + 1) * 10
            o.save(update_fields=["orden"])


def quitar(apps, schema_editor):
    OrdenCuenta = apps.get_model("presupuestoApp", "OrdenCuenta")
    OrdenCuenta.objects.filter(mcncuenta__in=CODIGOS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("presupuestoApp", "0040_subtotal_cuentas"),
    ]

    operations = [
        migrations.RunPython(agregar, quitar),
    ]
