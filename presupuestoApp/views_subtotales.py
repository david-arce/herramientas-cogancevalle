"""
Ajustes → Filas calculadas (solo el aprobador).

Edita qué cuentas suma cada fila calculada del Consolidado / Presupuestado /
Comparativo (Otros Ingresos, Gastos por Servicios, Gastos de Administración...).
Ver subtotales.py.
"""
import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from .agrupacion_cuentas import cargar_reglas
from .filas_calculadas import es_calculada
from .models import OrdenCuenta, SubtotalCuentas
from .subtotales import POR_CLAVE, configuracion_subtotales, limpiar_codigos, suma_cuenta, validar
from .views_presupuesto_areas import _es_aprobador


def _sin_permiso_json():
    return JsonResponse({"ok": False, "msg": "Sin permisos"}, status=403)


def _cuerpo(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _para_json(config):
    salida = []
    for clave, c in config.items():
        actualizado = timezone.localtime(c["actualizado"]).strftime("%d/%m/%Y %H:%M") if c["actualizado"] else ""
        salida.append({**c, "clave": clave, "actualizado": actualizado})
    return salida


def _filas_tabla():
    """[(código, nombre, visible_total, visible_sede)] de las filas que muestran las tablas."""
    filas = list(OrdenCuenta.objects.order_by("orden", "id")
                 .values_list("mcncuenta", "ctanombre", "visible_total", "visible_sede"))
    if not filas:
        from .views import ORDEN_SEDE_FALLBACK, ORDEN_TOTAL_FALLBACK   # orden por defecto si la tabla está vacía
        en_sede = set(ORDEN_SEDE_FALLBACK)
        filas = [(c, "", True, c in en_sede) for c in ORDEN_TOTAL_FALLBACK]
    # Las filas calculadas (CALC-...) no son cuentas: no se suman en otra fila calculada
    return [f for f in filas if not es_calculada(f[0])]


def _analizar(clave, cuentas, prefijos):
    """Qué filas de la tabla sumaría la fila calculada y qué conviene advertir."""
    cfg = {"cuentas": cuentas, "prefijos": prefijos}
    otras = {k: v for k, v in configuracion_subtotales().items() if k != clave}
    filas_tabla = _filas_tabla()
    en_tabla = {c for c, *_ in filas_tabla}

    filas = []
    for codigo, nombre, vis_total, vis_sede in filas_tabla:
        if not suma_cuenta(cfg, codigo):
            continue
        tambien = [o["nombre"] for o in otras.values() if suma_cuenta(o, codigo)]
        filas.append({
            "cuenta": codigo, "nombre": nombre or "",
            "exacta": codigo in cuentas,
            "oculta": "" if vis_total and vis_sede else (
                "oculta en Total Base" if not vis_total and vis_sede else
                "solo en Total Base" if vis_total else "oculta en todas las pestañas"),
            "tambien": tambien,
        })

    avisos = []
    reglas = cargar_reglas()
    for c in cuentas:
        if c in en_tabla:
            continue
        destino = reglas.agrupar(c)
        if destino != c:
            avisos.append(f"{c} no sale como fila propia: se agrupa en la fila {destino} "
                          f"(Agrupación de cuentas). Agrega {destino} en su lugar.")
        else:
            avisos.append(f"{c} no está en Orden de cuentas: no aparece en las tablas, así que no se suma.")
    for p in prefijos:
        if not any(codigo.startswith(p) for codigo in en_tabla):
            avisos.append(f"Ninguna fila de Orden de cuentas empieza por {p}.")
    dobles = [f["cuenta"] for f in filas if f["tambien"]]
    if dobles:
        avisos.append("Se suman también en otra fila calculada (revisa que no se cuenten dos veces): "
                      + ", ".join(dobles[:15]) + ("…" if len(dobles) > 15 else ""))
    return filas, avisos


# ---------------------------------------------------------------------------
# Pantalla
# ---------------------------------------------------------------------------
@login_required
def ajustes_filas_calculadas(request):
    if not _es_aprobador(request):
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    return render(request, "ajustes/filas_calculadas.html", {
        "datos": {
            "filas": _para_json(configuracion_subtotales()),
            "urls": {
                "guardar": reverse("guardar_fila_calculada"),
                "restaurar": reverse("restaurar_fila_calculada"),
                "vista_previa": reverse("vista_previa_fila_calculada"),
            },
        },
    })


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
def _leer(request):
    """(datos, clave, respuesta_de_error)"""
    if not _es_aprobador(request):
        return None, None, _sin_permiso_json()
    if request.method != "POST":
        return None, None, JsonResponse({"ok": False, "msg": "Método no permitido"}, status=405)
    datos = _cuerpo(request)
    if datos is None:
        return None, None, JsonResponse({"ok": False, "msg": "Datos inválidos"}, status=400)
    clave = str(datos.get("clave") or "")
    if clave not in POR_CLAVE:
        return None, None, JsonResponse({"ok": False, "msg": "Esa fila calculada no existe"}, status=404)
    return datos, clave, None


@login_required
def guardar_fila_calculada(request):
    """POST {clave, cuentas: [...], prefijos: [...]}"""
    datos, clave, error = _leer(request)
    if error:
        return error
    cuentas = limpiar_codigos(datos.get("cuentas"))
    prefijos = limpiar_codigos(datos.get("prefijos"))
    errores = validar(cuentas, prefijos)
    if errores:
        return JsonResponse({"ok": False, "msg": errores[0], "errores": errores}, status=400)

    SubtotalCuentas.objects.update_or_create(
        clave=clave,
        defaults={"cuentas": cuentas, "prefijos": prefijos, "actualizado_por": request.user.username},
    )
    _, avisos = _analizar(clave, cuentas, prefijos)
    msg = f"{POR_CLAVE[clave]['nombre']} guardada ✅"
    if not cuentas and not prefijos:
        msg += " · no suma ninguna cuenta: quedará en 0"
    return JsonResponse({"ok": True, "msg": msg, "avisos": avisos,
                         "filas": _para_json(configuracion_subtotales())})


@login_required
def restaurar_fila_calculada(request):
    """POST {clave}: vuelve a las cuentas por defecto."""
    _, clave, error = _leer(request)
    if error:
        return error
    SubtotalCuentas.objects.filter(clave=clave).delete()
    return JsonResponse({"ok": True, "msg": f"{POR_CLAVE[clave]['nombre']}: se restauraron las cuentas por defecto",
                         "filas": _para_json(configuracion_subtotales())})


@login_required
def vista_previa_fila_calculada(request):
    """POST {clave, cuentas, prefijos} -> filas de la tabla que se sumarían."""
    datos, clave, error = _leer(request)
    if error:
        return error
    cuentas = limpiar_codigos(datos.get("cuentas"))
    prefijos = limpiar_codigos(datos.get("prefijos"))
    errores = validar(cuentas, prefijos)
    filas, avisos = _analizar(clave, cuentas, prefijos)
    return JsonResponse({"ok": True, "filas": filas, "avisos": avisos, "errores": errores})
