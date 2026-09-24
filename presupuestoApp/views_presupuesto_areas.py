"""
Presupuesto de gastos por área sobre la tabla única PresupuestoArea.

Flujo (dos roles, dos pantallas):

  ÁREA        una sola vista editable (etapa "auxiliar") + botón "Subir
              presupuesto", que congela lo editado como una versión nueva
              (etapa "proyectado").

  APROBADOR   entra desde el dashboard, elige una versión enviada, la edita
              con las mismas herramientas y la aprueba (copia a la etapa
              "aprobado"). Es el único que puede borrar versiones.

Las etapas "proyectado" y "aprobado" ya no se le muestran al área.
"""
import datetime
import json

import pandas as pd
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Max
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import Plantillagastos2025
from .models_presupuesto import CAMPOS_NUMERICOS, CAMPOS_PRESUPUESTO, MESES, PresupuestoArea

AUXILIAR = PresupuestoArea.Etapa.AUXILIAR
PROYECTADO = PresupuestoArea.Etapa.PROYECTADO
APROBADO = PresupuestoArea.Etapa.APROBADO

CAMPOS_BASE_PLANTILLA = [c for c in CAMPOS_PRESUPUESTO if c not in ("total", "comentario")]
CAMPOS_SALIDA = ["id", *CAMPOS_PRESUPUESTO, "version", "fecha"]

# Quienes revisan y aprueban los presupuestos de todas las áreas.
APROBADORES = {"admin", "NICOLAS"}

# ---------------------------------------------------------------------------
# Configuración por área (única fuente de verdad)
# ---------------------------------------------------------------------------
FECHA_LIMITE_DEFAULT = datetime.date(2025, 10, 30)
LIMITE_AUX_15 = datetime.date(2027, 10, 15)
LIMITE_AUX_08 = datetime.date(2027, 10, 8)
LIMITE_APROBADO = datetime.date(2027, 10, 30)


def _area(label, responsable, usuarios, limite_auxiliar, limite_aprobado=LIMITE_APROBADO):
    return {
        "label": label,
        "usuarios_permitidos": {*APROBADORES, *usuarios},
        "responsable_filtro": responsable,
        "fecha_limite_auxiliar": limite_auxiliar,
        "fecha_limite_aprobado": limite_aprobado,
    }


SEDE_CONFIG = {
    "almacen-tulua": _area("Almacén Tuluá", "JEFE ALMACEN TULUA", {"JEFEALMACENTULUA", "DBENITEZ"}, LIMITE_AUX_15),
    "almacen-buga": _area("Almacén Buga", "JEFE ALMACEN BUGA", {"JEFEALMACENBUGA", "FDUQUE"}, LIMITE_AUX_15),
    "almacen-cartago": _area("Almacén Cartago", "JEFE ALMACEN CARTAGO", {"JEFEALMACENCARTAGO", "CHINCAPI"}, LIMITE_AUX_15),
    "almacen-cali": _area("Almacén Cali", "JEFE ALMACEN CALI", {"JEFEALMACENCALI", "LAMAYA"}, LIMITE_AUX_15),
    "comunicaciones": _area("Comunicaciones y Mercadeo", "CARLOS USMAN", {"COMUNICACIONES"}, LIMITE_AUX_08),
    "comercial-costos": _area("Comercial y Costos", "EVALENCIA", {"COMERCIALCOSTOS", "EVALENCIA"}, LIMITE_AUX_08),
    "contabilidad": _area("Contabilidad", "CONTABILIDAD", {"CONTABILIDAD"}, LIMITE_AUX_08),
    "gerencia": _area("Gerencia", "GERENCIA", {"GERENCIA"}, LIMITE_AUX_08),
    "gestion-humana": _area("Gestión Humana", "MARTA GH", {"GESTIONHUMANA"}, LIMITE_AUX_15),
    "gestion-riesgos": _area("Gestión de Riesgos", "LINA RICARDO", {"GESTIONRIESGOS"}, LIMITE_AUX_15),
    "logistica": _area("Logística", "PILAR LOZANO", {"PLOZANO"}, LIMITE_AUX_15),
    "servicios-tecnicos": _area("Servicios Técnicos", "JORGE GUERRERO", {"SERVICIOSTECNICOS"}, LIMITE_AUX_15),
    "salud-ocupacional": _area("Salud Ocupacional", "SALUD OCUPACIONAL", {"SALUDOCUPACIONAL"}, LIMITE_AUX_15),
    "tecnologia": _area("Tecnología", "DIEGO CANO", {"TECNOLOGIA"}, LIMITE_AUX_15),
}

# Las URLs del consolidado usan otras claves para dos áreas.
ALIAS_AREA_CONSOLIDADO = {"gh": "gestion-humana", "ocupacional": "salud-ocupacional"}

TEMPLATES_CONSOLIDADO = {
    "almacen-buga": "presupuesto_consolidado/presupuesto_almacen_buga.html",
    "almacen-cali": "presupuesto_consolidado/presupuesto_almacen_cali.html",
    "almacen-cartago": "presupuesto_consolidado/presupuesto_almacen_cartago.html",
    "almacen-tulua": "presupuesto_consolidado/presupuesto_almacen_tulua.html",
    "comercial-costos": "presupuesto_consolidado/presupuesto_comercial_costos.html",
    "comunicaciones": "presupuesto_consolidado/presupuesto_comunicaciones.html",
    "contabilidad": "presupuesto_consolidado/presupuesto_contabilidad.html",
    "gerencia": "presupuesto_consolidado/presupuesto_gerencia.html",
    "gestion-riesgos": "presupuesto_consolidado/presupuesto_gestion_riesgos.html",
    "gh": "presupuesto_consolidado/presupuesto_GH.html",
    "logistica": "presupuesto_consolidado/presupuesto_logistica.html",
    "ocupacional": "presupuesto_consolidado/presupuesto_ocupacional.html",
    "servicios-tecnicos": "presupuesto_consolidado/presupuesto_servicios_tecnicos.html",
    "tecnologia": "presupuesto_consolidado/presupuesto_tecnologia.html",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _config_sede(sede):
    return SEDE_CONFIG.get(sede)


def _usuario_autorizado(request, config):
    return request.user.username in config["usuarios_permitidos"]


def _es_aprobador(request):
    return request.user.is_authenticated and request.user.username in APROBADORES


def _fecha_limite_auxiliar(config):
    return config.get("fecha_limite_auxiliar", FECHA_LIMITE_DEFAULT)


def _fecha_limite_aprobado(config):
    return config.get("fecha_limite_aprobado", FECHA_LIMITE_DEFAULT)


def _area_consolidado(area):
    clave = ALIAS_AREA_CONSOLIDADO.get(area, area)
    return clave if clave in SEDE_CONFIG else None


def _filas(area, etapa):
    return PresupuestoArea.objects.de(area, etapa)


def _ultima_version(area, *etapas):
    return (
        PresupuestoArea.objects.filter(area=area, etapa__in=etapas)
        .aggregate(maxima=Max("version"))["maxima"]
    )


def _resumen_versiones(area):
    """Versiones enviadas por el área, con fecha, cantidad de filas y si están aprobadas."""
    aprobadas = set(
        _filas(area, APROBADO).exclude(version__isnull=True).values_list("version", flat=True)
    )
    resumen = (
        _filas(area, PROYECTADO)
        .exclude(version__isnull=True)
        .values("version")
        .annotate(fecha=Max("fecha"), filas=Count("id"))
        .order_by("version")
    )
    return [
        {
            "numero": r["version"],
            "fecha": r["fecha"],
            "filas": r["filas"],
            "aprobada": r["version"] in aprobadas,
        }
        for r in resumen
    ]


def _limpiar_fila(row):
    """Deja solo los campos de negocio, pone 0 en numéricos vacíos y recalcula el total."""
    fila = {campo: row.get(campo) for campo in CAMPOS_PRESUPUESTO}
    for campo in CAMPOS_NUMERICOS:
        if fila[campo] in (None, ""):
            fila[campo] = 0
    fila["total"] = sum(int(fila[m]) for m in MESES)
    return fila


def _nuevas(area, etapa, filas, version=None, fecha=None):
    return [
        PresupuestoArea(area=area, etapa=etapa, version=version, fecha=fecha, **fila)
        for fila in filas
    ]


def _cuerpo_json(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {}


# ---------------------------------------------------------------------------
# Vista del área: una sola pantalla para editar y subir
# ---------------------------------------------------------------------------
@login_required
def tabla_auxiliar_sede(request, sede):
    config = _config_sede(sede)
    if not config:
        return HttpResponseForbidden("⛔ Sede no configurada.")
    if not _usuario_autorizado(request, config):
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")

    fecha_limite = _fecha_limite_auxiliar(config)
    if timezone.now().date() > fecha_limite:
        return HttpResponseForbidden(
            "⛔ El acceso a esta vista está bloqueado después del "
            f"{fecha_limite.strftime('%d/%m/%Y')}"
        )

    versiones = _resumen_versiones(sede)
    return render(request, "presupuesto_general/aux_presupuesto_almacen_sede.html", {
        "sede": sede,
        "sede_label": config["label"],
        "ultima_version": versiones[-1] if versiones else None,
    })


def obtener_temp_sede(request, sede):
    if not _config_sede(sede):
        return JsonResponse({"error": "Sede no configurada"}, status=404)
    filas = _filas(sede, AUXILIAR).order_by("id").values("id", *CAMPOS_PRESUPUESTO)
    return JsonResponse(list(filas), safe=False)


@login_required
def guardar_temp_sede(request, sede):
    config = _config_sede(sede)
    if not config:
        return JsonResponse({"status": "error", "message": "Sede no configurada"}, status=404)
    if not _usuario_autorizado(request, config):
        return JsonResponse({"status": "error", "message": "Sin permisos"}, status=403)
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)
    if timezone.now().date() > _fecha_limite_auxiliar(config):
        return JsonResponse({"status": "error", "message": "El plazo de edición ya cerró"}, status=403)

    try:
        data = json.loads(request.body.decode("utf-8"))
        registros = _nuevas(sede, AUXILIAR, [_limpiar_fila(row) for row in data])
        with transaction.atomic():
            _filas(sede, AUXILIAR).delete()      # solo el borrador de ESTA área
            PresupuestoArea.objects.bulk_create(registros, batch_size=500)
        return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@login_required
def cargar_base_sede(request, sede):
    config = _config_sede(sede)
    if not config:
        return JsonResponse({"status": "error", "message": "Sede no configurada"}, status=404)
    if not _usuario_autorizado(request, config):
        return JsonResponse({"status": "error", "message": "Sin permisos"}, status=403)

    base_qs = Plantillagastos2025.objects.filter(
        responsable__iexact=config["responsable_filtro"]
    ).values(*CAMPOS_BASE_PLANTILLA)
    filas = [_limpiar_fila({**row, "comentario": ""}) for row in base_qs]

    with transaction.atomic():
        _filas(sede, AUXILIAR).delete()
        PresupuestoArea.objects.bulk_create(_nuevas(sede, AUXILIAR, filas), batch_size=500)

    return JsonResponse({"status": "ok", "msg": f"{len(filas)} filas cargadas desde plantilla 📂"})


@login_required
def subir_presupuesto_sede(request, sede):
    """El área envía lo que tiene editado como una versión nueva, para revisión."""
    config = _config_sede(sede)
    if not config:
        return JsonResponse({"success": False, "msg": "Sede no configurada"}, status=404)
    if not _usuario_autorizado(request, config):
        return JsonResponse({"success": False, "msg": "Sin permisos"}, status=403)
    if request.method != "POST":
        return JsonResponse({"success": False, "msg": "Método no permitido"}, status=405)

    hoy = timezone.now().date()
    with transaction.atomic():
        # select_for_update bloquea el borrador del área: dos envíos simultáneos
        # no pueden obtener el mismo número de versión.
        filas = list(
            _filas(sede, AUXILIAR).select_for_update().order_by("id").values(*CAMPOS_PRESUPUESTO)
        )
        if not filas:
            return JsonResponse({"success": False, "msg": "No hay datos para subir ❌"}, status=400)

        nueva_version = (_ultima_version(sede, PROYECTADO, APROBADO) or 0) + 1
        PresupuestoArea.objects.bulk_create(
            _nuevas(sede, PROYECTADO, filas, nueva_version, hoy), batch_size=500
        )

    return JsonResponse({
        "success": True,
        "msg": f"Versión {nueva_version} enviada para aprobación ✅",
        "version": nueva_version,
    })


# ---------------------------------------------------------------------------
# Vista del aprobador: revisar, editar y aprobar versiones
# ---------------------------------------------------------------------------
@login_required
def presupuesto_sede(request, sede):
    config = _config_sede(sede)
    if not config:
        return HttpResponseForbidden("⛔ Sede no configurada.")
    if not _es_aprobador(request):
        # El área tiene una sola pantalla: se la enviamos directamente.
        if _usuario_autorizado(request, config):
            return redirect("tabla_auxiliar_sede", sede=sede)
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")

    versiones = _resumen_versiones(sede)
    return render(request, "presupuesto_general/revision_presupuesto_sede.html", {
        "sede": sede,
        "sede_label": config["label"],
        "versiones": versiones,
        "version_actual": versiones[-1]["numero"] if versiones else None,
    })


@login_required
def obtener_presupuesto_sede(request, sede):
    config = _config_sede(sede)
    if not config:
        return JsonResponse({"error": "Sede no configurada"}, status=404)
    if not (_es_aprobador(request) or _usuario_autorizado(request, config)):
        return JsonResponse({"error": "Sin permisos"}, status=403)

    qs = _filas(sede, PROYECTADO)
    version = request.GET.get("version")
    if version:
        try:
            qs = qs.filter(version=int(version))
        except ValueError:
            return JsonResponse({"error": "Versión inválida"}, status=400)
    else:
        qs = qs.ultima_version()
    return JsonResponse({"data": list(qs.order_by("id").values(*CAMPOS_SALIDA))})


@login_required
def guardar_version_sede(request, sede, version):
    """Autoguardado de los ajustes que hace el aprobador sobre una versión."""
    config = _config_sede(sede)
    if not config:
        return JsonResponse({"status": "error", "message": "Sede no configurada"}, status=404)
    if not _es_aprobador(request):
        return JsonResponse({"status": "error", "message": "Solo el aprobador puede editar versiones"}, status=403)
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
        filas = [_limpiar_fila(row) for row in data]
        with transaction.atomic():
            qs = _filas(sede, PROYECTADO).filter(version=version)
            if not qs.exists():
                return JsonResponse({"status": "error", "message": "Esa versión no existe"}, status=404)
            fecha = qs.aggregate(f=Max("fecha"))["f"]
            qs.delete()
            PresupuestoArea.objects.bulk_create(
                _nuevas(sede, PROYECTADO, filas, version, fecha), batch_size=500
            )
        return JsonResponse({"status": "ok", "msg": f"{len(filas)} filas guardadas ✅"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@login_required
def aprobar_version_sede(request, sede, version):
    """Copia una versión revisada a la etapa aprobada."""
    config = _config_sede(sede)
    if not config:
        return JsonResponse({"success": False, "msg": "Sede no configurada"}, status=404)
    if not _es_aprobador(request):
        return JsonResponse({"success": False, "msg": "Solo el aprobador puede aprobar"}, status=403)
    if request.method != "POST":
        return JsonResponse({"success": False, "msg": "Método no permitido"}, status=405)

    hoy = timezone.now().date()
    if hoy > _fecha_limite_aprobado(config):
        return JsonResponse({
            "success": False,
            "msg": f"El plazo de aprobación cerró el {_fecha_limite_aprobado(config).strftime('%d/%m/%Y')} ❌",
        }, status=403)

    with transaction.atomic():
        filas = list(
            _filas(sede, PROYECTADO).filter(version=version).order_by("id").values(*CAMPOS_PRESUPUESTO)
        )
        if not filas:
            return JsonResponse({"success": False, "msg": "Esa versión no existe ❌"}, status=404)
        _filas(sede, APROBADO).filter(version=version).delete()
        PresupuestoArea.objects.bulk_create(
            _nuevas(sede, APROBADO, filas, version, hoy), batch_size=500
        )

    return JsonResponse({
        "success": True,
        "msg": f"Versión {version} de {config['label']} aprobada ✅",
    })


@login_required
def borrar_presupuesto_sede(request, sede):
    """Borra una versión (proyectada y su aprobación). Solo el aprobador."""
    config = _config_sede(sede)
    if not config:
        return JsonResponse({"status": "error", "message": "Sede no configurada"}, status=404)
    if not _es_aprobador(request):
        return JsonResponse({"status": "error", "message": "Solo el aprobador puede borrar versiones"}, status=403)
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

    version = _cuerpo_json(request).get("version") or request.POST.get("version")
    try:
        version = int(version)
    except (TypeError, ValueError):
        return JsonResponse({"status": "error", "message": "No se especificó la versión"}, status=400)

    borradas, _ = PresupuestoArea.objects.filter(
        area=sede, etapa__in=[PROYECTADO, APROBADO], version=version
    ).delete()
    if not borradas:
        return JsonResponse({"status": "error", "message": "Esa versión no existe"}, status=404)

    return JsonResponse({
        "status": "ok",
        "message": f"Versión {version} de {config['label']} eliminada",
    })


# ---------------------------------------------------------------------------
# Aprobado (solo lectura)
# ---------------------------------------------------------------------------
@login_required
def presupuesto_aprobado_sede(request, sede):
    config = _config_sede(sede)
    if not config:
        return HttpResponseForbidden("⛔ Sede no configurada.")
    if not (_es_aprobador(request) or _usuario_autorizado(request, config)):
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")

    return render(request, "presupuesto_general/presupuesto_sede_readonly.html", {
        "sede": sede,
        "sede_label": config["label"],
        "ultima_version": _ultima_version(sede, APROBADO) or "—",
    })


def obtener_presupuesto_aprobado_sede(request, sede):
    if not _config_sede(sede):
        return JsonResponse({"error": "Sede no configurada"}, status=404)
    filas = _filas(sede, APROBADO).ultima_version().order_by("id").values(*CAMPOS_SALIDA)
    return JsonResponse({"data": list(filas)})


# ---------------------------------------------------------------------------
# Exportar todos los aprobados (última versión de cada área)
# ---------------------------------------------------------------------------
def exportar_excel_presupuestos(request):
    marcos = []
    for area, config in SEDE_CONFIG.items():
        filas = list(_filas(area, APROBADO).ultima_version().order_by("id").values(*CAMPOS_SALIDA))
        if not filas:
            continue
        df = pd.DataFrame(filas)
        df["origen"] = config["label"]
        marcos.append(df)

    df = pd.concat(marcos, ignore_index=True) if marcos else pd.DataFrame()
    if not df.empty:
        fijas = [c for c in df.columns if c not in MESES]
        df = df.melt(id_vars=fijas, value_vars=MESES, var_name="mes", value_name="valor")

    respuesta = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    respuesta["Content-Disposition"] = 'attachment; filename="Presupuestos_Todo.xlsx"'
    with pd.ExcelWriter(respuesta, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Presupuestos", index=False)
    return respuesta


# ---------------------------------------------------------------------------
# Presupuesto consolidado (vistas por área del aprobado)
# ---------------------------------------------------------------------------
def presupuesto_consolidado(request, area):
    template = TEMPLATES_CONSOLIDADO.get(area)
    if not template:
        return HttpResponseForbidden("⛔ Área no válida.")
    return render(request, template)


def obtener_presupuesto_consolidado(request, area):
    clave = _area_consolidado(area)
    if not clave:
        return HttpResponseForbidden("⛔ Área no válida.")
    filas = _filas(clave, APROBADO).ultima_version().order_by("id").values(*CAMPOS_SALIDA)
    return JsonResponse({"data": list(filas)})


def guardar_presupuesto_consolidado(request, area):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

    clave = _area_consolidado(area)
    if not clave:
        return HttpResponseForbidden("⛔ Área no válida.")
    if not _es_aprobador(request):
        return JsonResponse({"status": "error", "message": "Sin permisos"}, status=403)

    try:
        data = json.loads(request.body.decode("utf-8"))
        filas = [_limpiar_fila(row) for row in data]
        with transaction.atomic():
            # Se reemplaza la versión aprobada vigente conservando su número.
            version = _ultima_version(clave, APROBADO) or 1
            _filas(clave, APROBADO).filter(version=version).delete()
            PresupuestoArea.objects.bulk_create(
                _nuevas(clave, APROBADO, filas, version, timezone.now().date()), batch_size=500
            )
        return JsonResponse({"status": "ok", "msg": f"{len(filas)} filas guardadas ✅"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)