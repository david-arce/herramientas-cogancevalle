"""
Ajustes → Agrupación de cuentas (solo el aprobador).

Edita la tabla AgrupacionCuenta: qué cuentas se suman en cada fila del
Consolidado / Presupuestado / Comparativo y el nombre de cada fila.
"""
import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max, Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from .agrupacion_cuentas import PATRON_CODIGO, PATRON_CUENTA, ReglasCuentas, filas_reglas
from .models import (
    AgrupacionCuenta, ComentarioComparativo, ConsolidadoTotalBase, Cuenta5Base, Cuenta5Presupuestado, CuentasContables,
    OrdenCuenta,
)
from .views_presupuesto_areas import _es_aprobador

# Cuentas clave (ventas, descuentos, costo de ventas): se reconocen aparte y
# nunca se agrupan. Mismo listado que ALIAS_CUENTAS_CLAVE en views.py.
CUENTAS_CLAVE = {"1", "2", "41750201", "613522"}

# Filas cuyo código NO se puede cambiar, con el motivo:
#  - las producen reglas fijas del cálculo (centro de costo / destino),
#  - o las pantallas de Consolidado, Presupuestado y Comparativo las usan por
#    su código para ubicar subtotales (Utilidad operacional, Excedentes...).
CODIGOS_FIJOS = {
    "5": "lo genera la regla del centro de costo 02040…",
    "6": "lo genera la regla de Asistencia Técnica Propia",
    "7": "lo genera la regla de Asistencia Técnica Convenios",
    "8": "lo genera la regla del centro de costo 0203…",
    "5105": "lo genera la regla del centro de costo 0101",
    "5405": "lo genera la regla del centro de costo 020201",
    "5230": "las tablas ubican los Excedentes y los gastos por servicios con este código",
    "5415": "las tablas ubican la Utilidad operacional después de esta fila",
    "615035": "las tablas ubican los ingresos por servicios después de esta fila",
    **{c: "es una cuenta clave (ventas / costo de ventas)" for c in CUENTAS_CLAVE},
}


def motivo_codigo_fijo(fila):
    """Por qué no se puede cambiar el código de la fila, o "" si sí se puede."""
    if fila.codigo in CODIGOS_FIJOS:
        return CODIGOS_FIJOS[fila.codigo]
    if not (fila.cuentas or fila.prefijos):
        return "la fila solo pone nombre: su código es la cuenta o el destino que llega del cálculo"
    return ""
MAX_VISTA_PREVIA = 500


def _sin_permiso_json():
    return JsonResponse({"ok": False, "msg": "Sin permisos"}, status=403)


def _cuerpo(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _lista():
    """Todas las filas, con el nombre que les da Orden de cuentas (si tiene)."""
    orden = dict(OrdenCuenta.objects.values_list("mcncuenta", "ctanombre"))
    filas = []
    for a in AgrupacionCuenta.objects.order_by("codigo"):
        nombre_orden = (orden.get(a.codigo) or "").strip()
        filas.append({
            "id": a.id,
            "codigo": a.codigo,
            "nombre": a.nombre,
            "cuentas": a.cuentas or [],
            "prefijos": a.prefijos or [],
            "en_orden": a.codigo in orden,
            "codigo_fijo": motivo_codigo_fijo(a),
            "nombre_orden": nombre_orden if nombre_orden and nombre_orden != a.nombre else "",
            "actualizado": timezone.localtime(a.actualizado).strftime("%d/%m/%Y %H:%M"),
            "actualizado_por": a.actualizado_por,
        })
    return filas


def _respuesta(msg, **extra):
    return JsonResponse({
        "ok": True, "msg": msg, "filas": _lista(),
        "orden_vacia": not OrdenCuenta.objects.exists(), **extra,
    })


def _lista_codigos(valor):
    """Acepta lista o texto ("541009, 541033 54103301") -> lista limpia sin repetidos."""
    if isinstance(valor, str):
        valor = valor.replace(",", " ").replace(";", " ").split()
    salida = []
    for v in valor or []:
        v = str(v).strip()
        if v and v not in salida:
            salida.append(v)
    return salida


def _validar(datos, actual=None):
    """(datos limpios, errores). `actual` es la AgrupacionCuenta que se edita."""
    errores = []
    codigo = str(datos.get("codigo") or "").strip()
    nombre = str(datos.get("nombre") or "").strip()
    cuentas = _lista_codigos(datos.get("cuentas"))
    prefijos = _lista_codigos(datos.get("prefijos"))

    if actual is not None and (not codigo or codigo == actual.codigo):
        codigo = actual.codigo                      # no cambia
    elif actual is not None and motivo_codigo_fijo(actual):
        errores.append(f"El código {actual.codigo} no se puede cambiar: {motivo_codigo_fijo(actual)}.")
        codigo = actual.codigo
    elif actual is not None and codigo[:2] != actual.codigo[:2]:
        # Las tablas suman los subtotales por los primeros dígitos (54 = gastos de
        # ventas, 51 = administración...): cambiarlos movería la fila de subtotal.
        errores.append(f"El código nuevo debe empezar por «{actual.codigo[:2]}», como el actual, "
                       "para que la fila siga sumando en el mismo subtotal.")
    elif not codigo:
        errores.append("Escribe el código de la fila.")
    elif len(codigo) > 60 or not PATRON_CODIGO.match(codigo):
        errores.append("El código solo puede tener letras, números, guion o guion bajo (máx. 60).")
    elif AgrupacionCuenta.objects.filter(codigo=codigo).exclude(pk=getattr(actual, "pk", None)).exists():
        errores.append(f"Ya existe una fila con el código {codigo}.")
    elif actual is not None and OrdenCuenta.objects.filter(mcncuenta=codigo).exists():
        errores.append(f"El código {codigo} ya está en Orden de cuentas como otra fila; usa otro código.")

    if not nombre:
        errores.append("Escribe el nombre de la fila.")
    elif len(nombre) > 255:
        errores.append("El nombre es muy largo (máx. 255 caracteres).")

    for etiqueta, lista in (("cuenta", cuentas), ("prefijo", prefijos)):
        for c in lista:
            if not PATRON_CUENTA.match(c):
                errores.append(f"«{c}» no es válido: las {etiqueta}s son solo números.")
            elif c.startswith("4"):
                errores.append(f"«{c}»: las cuentas que empiezan por 4 no se agrupan.")
            elif c in CUENTAS_CLAVE:
                errores.append(f"«{c}» es una cuenta clave (ventas / costo de ventas) y no se agrupa.")
    for p in prefijos:
        if PATRON_CUENTA.match(p) and len(p) < 2:
            errores.append(f"El prefijo «{p}» es muy corto: agruparía casi todas las cuentas.")

    # Una cuenta exacta o un prefijo no pueden estar en dos filas.
    otras = AgrupacionCuenta.objects.exclude(pk=actual.pk) if actual else AgrupacionCuenta.objects.all()
    for o in otras.only("codigo", "cuentas", "prefijos"):
        for c in set(cuentas) & set(o.cuentas or []):
            errores.append(f"La cuenta {c} ya se suma en la fila {o.codigo}.")
        for p in set(prefijos) & set(o.prefijos or []):
            errores.append(f"El prefijo {p} ya se usa en la fila {o.codigo}.")

    return {"codigo": codigo, "nombre": nombre, "cuentas": cuentas, "prefijos": prefijos}, errores


# ---------------------------------------------------------------------------
# Pantalla
# ---------------------------------------------------------------------------
@login_required
def ajustes_agrupacion_cuentas(request):
    if not _es_aprobador(request):
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    return render(request, "ajustes/agrupacion_cuentas.html", {
        "datos": {
            "filas": _lista(),
            "orden_vacia": not OrdenCuenta.objects.exists(),
            "urls": {
                "guardar": reverse("guardar_agrupacion_cuenta"),
                "eliminar": reverse("eliminar_agrupacion_cuenta"),
                "vista_previa": reverse("vista_previa_agrupacion_cuenta"),
                "orden": reverse("ajustes_orden_cuentas"),
            },
        },
    })


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@login_required
def guardar_agrupacion_cuenta(request):
    """POST {id?, codigo, nombre, cuentas: [...], prefijos: [...]}"""
    if not _es_aprobador(request):
        return _sin_permiso_json()
    if request.method != "POST":
        return JsonResponse({"ok": False, "msg": "Método no permitido"}, status=405)
    datos = _cuerpo(request)
    if datos is None:
        return JsonResponse({"ok": False, "msg": "Datos inválidos"}, status=400)

    actual = None
    if datos.get("id"):
        try:
            actual = AgrupacionCuenta.objects.get(pk=int(datos["id"]))
        except (ValueError, TypeError, AgrupacionCuenta.DoesNotExist):
            return JsonResponse({"ok": False, "msg": "Esa fila ya no existe"}, status=404)

    with transaction.atomic():
        limpio, errores = _validar(datos, actual)
        if errores:
            return JsonResponse({"ok": False, "msg": errores[0], "errores": errores}, status=400)

        if actual:
            anterior = actual.codigo
            for campo in ("codigo", "nombre", "cuentas", "prefijos"):
                setattr(actual, campo, limpio[campo])
            actual.actualizado_por = request.user.username
            actual.save()
            msg = f"Fila {actual.codigo} guardada ✅"
            if anterior != actual.codigo:
                # El código es la llave de la fila en Orden de cuentas (posición,
                # visibilidad) y en los comentarios del Comparativo: se lleva todo.
                OrdenCuenta.objects.filter(mcncuenta=anterior).update(mcncuenta=actual.codigo)
                comentarios = ComentarioComparativo.objects.filter(fila_key=anterior).update(
                    fila_key=actual.codigo, mcncuenta=actual.codigo)
                msg = f"Código cambiado: {anterior} → {actual.codigo} ✅ (también en Orden de cuentas"
                msg += f" y {comentarios} comentario(s) del Comparativo)" if comentarios else ")"
            # Un solo nombre por fila: Orden de cuentas muestra el mismo.
            OrdenCuenta.objects.filter(mcncuenta=actual.codigo).update(ctanombre=actual.nombre)
            return _respuesta(msg)

        AgrupacionCuenta.objects.create(**limpio, actualizado_por=request.user.username)
        # Para que la fila nueva salga en las tablas debe estar en Orden de cuentas.
        agregada_orden = False
        if OrdenCuenta.objects.exists() and not OrdenCuenta.objects.filter(mcncuenta=limpio["codigo"]).exists():
            ultimo = OrdenCuenta.objects.aggregate(m=Max("orden"))["m"] or 0
            OrdenCuenta.objects.create(
                mcncuenta=limpio["codigo"], ctanombre=limpio["nombre"], orden=ultimo + 10,
                visible_total=True, visible_sede=True,
            )
            agregada_orden = True
        else:
            OrdenCuenta.objects.filter(mcncuenta=limpio["codigo"]).update(ctanombre=limpio["nombre"])

    msg = f"Fila {limpio['codigo']} creada ✅"
    if agregada_orden:
        msg += " · se agregó al final de Orden de cuentas"
    return _respuesta(msg, agregada_orden=agregada_orden)


@login_required
def eliminar_agrupacion_cuenta(request):
    """POST {id}. Las cuentas que sumaba vuelven a salir cada una por separado."""
    if not _es_aprobador(request):
        return _sin_permiso_json()
    if request.method != "POST":
        return JsonResponse({"ok": False, "msg": "Método no permitido"}, status=405)
    datos = _cuerpo(request) or {}
    try:
        fila = AgrupacionCuenta.objects.get(pk=int(datos.get("id")))
    except (ValueError, TypeError, AgrupacionCuenta.DoesNotExist):
        return JsonResponse({"ok": False, "msg": "Esa fila ya no existe"}, status=404)
    codigo = fila.codigo
    fila.delete()
    return _respuesta(f"Fila {codigo} eliminada")


def _cuentas_existentes(cuentas, prefijos):
    """{cuenta: nombre} de las cuentas conocidas (catálogo + movimientos) que coinciden."""
    if not cuentas and not prefijos:
        return {}
    encontradas = {}
    fuentes = (
        (CuentasContables, "cuenta", "nom_cuenta"),
        (Cuenta5Base, "mcncuenta", "ctanombre"),
        (Cuenta5Presupuestado, "mcncuenta", "ctanombre"),
        (ConsolidadoTotalBase, "mcncuenta", "ctanombre"),
    )
    for modelo, campo_cta, campo_nom in fuentes:
        filtro = Q()
        if cuentas:
            filtro |= Q(**{f"{campo_cta}__in": [int(c) for c in cuentas] if campo_cta == "cuenta" else cuentas})
        for p in prefijos:
            filtro |= Q(**{f"{campo_cta}__startswith": p})
        try:
            with transaction.atomic():      # savepoint: si la tabla no existe no daña la transacción
                pares = list(
                    modelo.objects.filter(filtro).values_list(campo_cta, campo_nom).distinct()[:MAX_VISTA_PREVIA * 4]
                )
            for cta, nom in pares:
                cta = str(cta or "").strip()
                if cta and (cta not in encontradas or (not encontradas[cta] and nom)):
                    encontradas[cta] = (nom or "").strip()
        except Exception:
            continue    # tabla externa que no existe en este ambiente
    for c in cuentas:            # las exactas se muestran aunque aún no tengan movimientos
        encontradas.setdefault(c, "")
    return encontradas


@login_required
def vista_previa_agrupacion_cuenta(request):
    """POST {id?, codigo, cuentas, prefijos} -> qué cuentas caerían en la fila."""
    if not _es_aprobador(request):
        return _sin_permiso_json()
    if request.method != "POST":
        return JsonResponse({"ok": False, "msg": "Método no permitido"}, status=405)
    datos = _cuerpo(request) or {}
    codigo = str(datos.get("codigo") or "").strip() or "(nueva)"
    cuentas = [c for c in _lista_codigos(datos.get("cuentas")) if PATRON_CUENTA.match(c)]
    prefijos = [p for p in _lista_codigos(datos.get("prefijos")) if PATRON_CUENTA.match(p)]
    try:
        excluir = int(datos.get("id")) if datos.get("id") else None
    except (TypeError, ValueError):
        excluir = None

    reglas = ReglasCuentas(filas_reglas(excluir_id=excluir) + [
        {"codigo": codigo, "nombre": "", "cuentas": cuentas, "prefijos": prefijos},
    ])
    nombres = dict(AgrupacionCuenta.objects.values_list("codigo", "nombre"))
    filas = []
    for cuenta, nombre in sorted(_cuentas_existentes(cuentas, prefijos).items()):
        if cuenta.startswith("4") or cuenta in CUENTAS_CLAVE:
            continue
        tipo, destino, prefijo = reglas.regla(cuenta)
        filas.append({
            "cuenta": cuenta,
            "nombre": nombre,
            "aqui": destino == codigo,
            "motivo": "cuenta exacta" if tipo == "exacta" else (f"empieza por {prefijo}" if prefijo else ""),
            "destino": destino,
            "destino_nombre": nombres.get(destino, ""),
        })
    return JsonResponse({
        "ok": True,
        "filas": filas[:MAX_VISTA_PREVIA],
        "total": len(filas),
        "aqui": sum(f["aqui"] for f in filas),
        "recortado": len(filas) > MAX_VISTA_PREVIA,
    })
