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

La tabla se guarda en VERTICAL (un registro por línea y mes, con su fecha),
pero la API entrega y recibe filas HORIZONTALES (una columna por mes), que es
como las muestra la grilla. La conversión está en models_presupuesto.py.
"""
import datetime
import json
import re

import pandas as pd
from django.contrib.auth.decorators import login_required
from django.db import connection, transaction
from django.db.models import Count, F, Max, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import Cuenta5Presupuestado
from .models_presupuesto import (
    CAMPOS_LINEA, CAMPOS_NUMERICOS, CAMPOS_PRESUPUESTO, MESES, PlazoEdicionArea, PresupuestoArea,
    anio_elaboracion, fecha_mes, filas_verticales,
)

AUXILIAR = PresupuestoArea.Etapa.AUXILIAR
PROYECTADO = PresupuestoArea.Etapa.PROYECTADO
APROBADO = PresupuestoArea.Etapa.APROBADO

# Plantilla de gastos base: tablas externas "plantillagastosAAAA", una por año
# (plantillagastos2025, plantillagastos2026, ...). El año se elige solo: la del
# año en que se elabora el presupuesto o, si aún no existe, la más reciente.
# Columna en la tabla externa -> campo de presupuesto_area.
PATRON_TABLA_PLANTILLA = re.compile(r"^plantillagastos(\d{4})$")
PLANTILLA_COLUMNAS = {
    "CENTRO_TRA": "mcnzona",
    "NOMBRE_CEN": "zonnombre",
    "CODCOSTO": "mcnccosto",
    "RESPONSABLE": "responsable",
    "CUENTA": "mcncuenta",
    "CUENTA MAYOR": "ctanombre",
    "DETALLE CUENTA": "mcndetalle",
    "SEDE  DISTRIBUCION": "sede_distribucion",
    "proveedor": "proveedor",
    **{m: m for m in MESES},
}

# Quienes revisan y aprueban los presupuestos de todas las áreas.
APROBADORES = {"admin", "NICOLAS"}

# ---------------------------------------------------------------------------
# Configuración por área (única fuente de verdad)
# ---------------------------------------------------------------------------
# Fecha límite de edición de cada ÁREA (el aprobador no tiene fecha límite):
#   1. La que se configure en Ajustes → Plazos de edición (PlazoEdicionArea).
#   2. Si no hay, el plazo automático: (mes, día) SIN año; el año es el actual,
#      así cada año se renueva sin tocar el código.
FECHA_LIMITE_DEFAULT = (10, 30)
LIMITE_AUX_15 = (10, 15)
LIMITE_AUX_08 = (10, 8)


def _plazo(mes_dia):
    """(mes, día) -> fecha de este ciclo de presupuesto."""
    mes, dia = mes_dia
    return datetime.date(anio_elaboracion(), mes, dia)


def _area(label, responsable, usuarios, limite_auxiliar):
    return {
        "label": label,
        "usuarios_permitidos": {*APROBADORES, *usuarios},
        "responsable_filtro": responsable,
        "fecha_limite_auxiliar": limite_auxiliar,
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


def fecha_limite_automatica(area):
    """Plazo automático del área (se usa cuando no hay uno configurado)."""
    return _plazo(SEDE_CONFIG[area].get("fecha_limite_auxiliar", FECHA_LIMITE_DEFAULT))


def fecha_limite_edicion(area):
    """(fecha límite, configurada?) para que el ÁREA edite su presupuesto."""
    configurada = (
        PlazoEdicionArea.objects.filter(area=area).values_list("fecha_limite", flat=True).first()
    )
    if configurada:
        return configurada, True
    return fecha_limite_automatica(area), False


def _plazo_vencido(request, area):
    """None si puede editar; si no, la fecha en que se cerró. El aprobador nunca queda bloqueado."""
    if _es_aprobador(request):
        return None
    limite, _ = fecha_limite_edicion(area)
    return limite if timezone.localdate() > limite else None


def _respuesta_plazo_cerrado(limite, clave="message", **extra):
    return JsonResponse({
        "status": "error", "success": False, **extra,
        clave: f"El plazo de edición cerró el {limite:%d/%m/%Y} ⛔",
    }, status=403)


def _tabla_plantilla():
    """(tabla, año) de la plantilla de gastos a usar, o (None, None) si no hay ninguna.

    Prefiere la del año en que se elabora el presupuesto; si todavía no se ha
    creado, usa la más reciente anterior (y si solo hay posteriores, la última).
    """
    anios = sorted(
        int(m.group(1))
        for t in connection.introspection.table_names()
        if (m := PATRON_TABLA_PLANTILLA.match(t))
    )
    if not anios:
        return None, None
    objetivo = anio_elaboracion()
    anteriores = [a for a in anios if a <= objetivo]
    anio = anteriores[-1] if anteriores else anios[-1]
    return f"plantillagastos{anio}", anio


def _leer_plantilla(tabla, responsable):
    qn = connection.ops.quote_name
    columnas = ", ".join(qn(c) for c in PLANTILLA_COLUMNAS)
    with connection.cursor() as cur:
        cur.execute(
            f"SELECT {columnas} FROM {qn(tabla)} WHERE UPPER({qn('RESPONSABLE')}) = UPPER(%s)",
            [responsable],
        )
        return [dict(zip(PLANTILLA_COLUMNAS.values(), fila)) for fila in cur.fetchall()]


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
        # filas = líneas de la grilla (cada una tiene 12 registros, uno por mes)
        .annotate(fecha=Max("fecha_version"), filas=Count("linea", distinct=True))
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


def _entero(valor):
    """Valor mensual como entero ('1500', 1500.0 y 1500 dan 1500)."""
    return int(float(valor))


def _limpiar_fila(row):
    """Deja solo los campos de negocio, pone 0 en numéricos vacíos y recalcula el total.

    Conserva "anio" si la fila lo trae (filas que ya existían), para que al
    volver a guardar sus meses sigan en el mismo año.
    """
    fila = {campo: row.get(campo) for campo in CAMPOS_PRESUPUESTO}
    for campo in CAMPOS_NUMERICOS:
        if fila[campo] in (None, ""):
            fila[campo] = 0
    for mes in MESES:
        fila[mes] = _entero(fila[mes])
    fila["total"] = sum(fila[m] for m in MESES)
    if row.get("anio"):
        fila["anio"] = int(row["anio"])
    return fila


def _nuevas(area, etapa, filas, version=None, fecha_version=None):
    """Filas horizontales -> registros verticales (12 por fila), sin guardar."""
    return filas_verticales(
        filas, area=area, etapa=etapa, version=version, fecha_version=fecha_version
    )


def _copiar(qs, etapa, version, fecha_version):
    """Copia registros verticales a otra etapa/versión conservando línea y fecha de cada mes."""
    campos = ["area", "linea", "fecha", "valor", *CAMPOS_LINEA]
    return [
        PresupuestoArea(etapa=etapa, version=version, fecha_version=fecha_version, **r)
        for r in qs.order_by("linea", "fecha").values(*campos)
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

    cerrado = _plazo_vencido(request, sede)
    if cerrado:
        return HttpResponseForbidden(
            "⛔ El plazo para editar este presupuesto cerró el "
            f"{cerrado.strftime('%d/%m/%Y')}"
        )

    versiones = _resumen_versiones(sede)
    fecha_limite, _ = fecha_limite_edicion(sede)
    return render(request, "presupuesto_general/aux_presupuesto_almacen_sede.html", {
        "sede": sede,
        "sede_label": config["label"],
        "ultima_version": versiones[-1] if versiones else None,
        "fecha_limite": fecha_limite,
        "sin_limite": _es_aprobador(request),
    })


def obtener_temp_sede(request, sede):
    if not _config_sede(sede):
        return JsonResponse({"error": "Sede no configurada"}, status=404)
    return JsonResponse(_filas(sede, AUXILIAR).horizontal(), safe=False)


@login_required
def guardar_temp_sede(request, sede):
    config = _config_sede(sede)
    if not config:
        return JsonResponse({"status": "error", "message": "Sede no configurada"}, status=404)
    if not _usuario_autorizado(request, config):
        return JsonResponse({"status": "error", "message": "Sin permisos"}, status=403)
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)
    cerrado = _plazo_vencido(request, sede)
    if cerrado:
        return _respuesta_plazo_cerrado(cerrado)

    try:
        data = json.loads(request.body.decode("utf-8"))
        filas = [_limpiar_fila(row) for row in data]
        registros = _nuevas(sede, AUXILIAR, filas)
        with transaction.atomic():
            _filas(sede, AUXILIAR).delete()      # solo el borrador de ESTA área
            PresupuestoArea.objects.bulk_create(registros, batch_size=500)
        return JsonResponse({"status": "ok", "msg": f"{len(filas)} filas guardadas ✅"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@login_required
def cargar_base_sede(request, sede):
    config = _config_sede(sede)
    if not config:
        return JsonResponse({"status": "error", "message": "Sede no configurada"}, status=404)
    if not _usuario_autorizado(request, config):
        return JsonResponse({"status": "error", "message": "Sin permisos"}, status=403)
    cerrado = _plazo_vencido(request, sede)
    if cerrado:
        return _respuesta_plazo_cerrado(cerrado)

    tabla, anio_base = _tabla_plantilla()
    if not tabla:
        return JsonResponse(
            {"status": "error", "message": "No hay ninguna plantilla de gastos (plantillagastosAAAA) cargada"},
            status=404,
        )
    filas = [
        _limpiar_fila({**row, "comentario": ""})
        for row in _leer_plantilla(tabla, config["responsable_filtro"])
    ]

    with transaction.atomic():
        _filas(sede, AUXILIAR).delete()
        PresupuestoArea.objects.bulk_create(_nuevas(sede, AUXILIAR, filas), batch_size=500)

    return JsonResponse({
        "status": "ok",
        "msg": f"{len(filas)} filas cargadas desde plantilla {anio_base} 📂",
        "anio_plantilla": anio_base,
    })


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
    cerrado = _plazo_vencido(request, sede)
    if cerrado:
        return _respuesta_plazo_cerrado(cerrado, clave="msg")

    hoy = timezone.localdate()
    with transaction.atomic():
        # select_for_update bloquea el borrador del área: dos envíos simultáneos
        # no pueden obtener el mismo número de versión.
        borrador = _filas(sede, AUXILIAR)
        if not list(borrador.select_for_update().values_list("id", flat=True)):
            return JsonResponse({"success": False, "msg": "No hay datos para subir ❌"}, status=400)

        nueva_version = (_ultima_version(sede, PROYECTADO, APROBADO) or 0) + 1
        PresupuestoArea.objects.bulk_create(
            _copiar(borrador, PROYECTADO, nueva_version, hoy), batch_size=500
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
    return JsonResponse({"data": qs.horizontal()})


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
            fecha_version = qs.aggregate(f=Max("fecha_version"))["f"]
            qs.delete()
            PresupuestoArea.objects.bulk_create(
                _nuevas(sede, PROYECTADO, filas, version, fecha_version), batch_size=500
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

    hoy = timezone.localdate()        # el aprobador no tiene fecha límite

    with transaction.atomic():
        proyectada = _filas(sede, PROYECTADO).filter(version=version)
        registros = _copiar(proyectada, APROBADO, version, hoy)
        if not registros:
            return JsonResponse({"success": False, "msg": "Esa versión no existe ❌"}, status=404)
        _filas(sede, APROBADO).filter(version=version).delete()
        PresupuestoArea.objects.bulk_create(registros, batch_size=500)

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
    return JsonResponse({"data": _filas(sede, APROBADO).ultima_version().horizontal()})


# ---------------------------------------------------------------------------
# Exportar todos los aprobados (última versión de cada área)
# ---------------------------------------------------------------------------
def exportar_excel_presupuestos(request):
    marcos = []
    for area, config in SEDE_CONFIG.items():
        filas = _filas(area, APROBADO).ultima_version().horizontal()
        if not filas:
            continue
        df = pd.DataFrame(filas)
        df["origen"] = config["label"]
        # Una fila por línea y mes (formato largo), igual que se guarda en la tabla.
        fijas = [c for c in df.columns if c not in MESES]
        df = df.melt(id_vars=fijas, value_vars=MESES, var_name="mes", value_name="valor")
        df["fecha"] = [fecha_mes(a, m) for a, m in zip(df["anio"], df["mes"])]
        marcos.append(df.sort_values(["linea", "fecha"], kind="stable"))

    df = pd.concat(marcos, ignore_index=True) if marcos else pd.DataFrame()

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
    return JsonResponse({"data": _filas(clave, APROBADO).ultima_version().horizontal()})


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
                _nuevas(clave, APROBADO, filas, version, timezone.localdate()), batch_size=500
            )
        return JsonResponse({"status": "ok", "msg": f"{len(filas)} filas guardadas ✅"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)

# ---------------------------------------------------------------------------
# Enviar el presupuesto aprobado de un área a Cuenta 5 presupuestado
# ---------------------------------------------------------------------------
# Cada registro mensual (línea x mes, valor distinto de 0) de la ÚLTIMA versión
# aprobada se convierte en un movimiento de cuenta_5_presupuestado:
#
#   mcncuenta   <- mcncuenta             mcnfecha   <- fecha (serial Excel)
#   mcnvaldebi  <- valor si es >= 0      mcnvalcred <- -valor si es < 0
#   mcnccosto, mcnzona, zonnombre, ctanombre, mcndetalle  <- iguales
#   vinnombre   <- vacío (no tiene relación con presupuesto_area)
#   comentario, responsable  <- de la línea (responsable vacío = el del área)
#
# Subir otra vez REEMPLAZA lo que esa área tenía (no duplica). Los registros
# cargados por Excel (sin origen_area) no se tocan.
EXCEL_EPOCA = datetime.date(1899, 12, 30)

ESTADOS_CUENTA5 = {
    "sin_aprobar": "Sin versión aprobada",
    "pendiente": "Pendiente de subir",
    "desactualizado": "Desactualizado",
    "subido": "Subido a Cuenta 5",
}


def _serial_excel(fecha):
    return float((fecha - EXCEL_EPOCA).days)


def _movimientos_cuenta5(area, config, ahora):
    """Registros Cuenta5Presupuestado (sin guardar) de la última versión aprobada.

    Devuelve (registros, version, lineas_sin_cuenta).
    """
    aprobada = _filas(area, APROBADO).ultima_version()
    registros, sin_cuenta, version = [], set(), None
    for r in aprobada.exclude(valor=0).order_by("linea", "fecha").values(
        "version", "linea", "fecha", "valor", *CAMPOS_LINEA
    ):
        version = r["version"]
        if not r["mcncuenta"]:
            sin_cuenta.add(r["linea"])
            continue
        valor = r["valor"]
        registros.append(Cuenta5Presupuestado(
            mcncuenta=str(r["mcncuenta"]),
            mcnfecha=_serial_excel(r["fecha"]),
            mcnvaldebi=float(valor) if valor >= 0 else 0.0,
            mcnvalcred=0.0 if valor >= 0 else float(-valor),
            mcnccosto=r["mcnccosto"],
            mcnzona=r["mcnzona"],
            zonnombre=r["zonnombre"],
            ctanombre=r["ctanombre"],
            mcndetalle=r["mcndetalle"],
            comentario=r["comentario"] or None,
            responsable=(r["responsable"] or "").strip() or config["responsable_filtro"],
            origen_area=area,
            origen_version=r["version"],
            origen_subido=ahora,
        ))
    if version is None:
        version = aprobada.values_list("version", flat=True).first()
    return registros, version, len(sin_cuenta)


def estado_cuenta5(area):
    """Si la última versión aprobada del área ya está en Cuenta 5 presupuestado.

    "subido" exige que coincidan la versión, la cantidad de movimientos y el
    total; así también se detecta una versión re-aprobada con cambios.
    """
    aprobada = _filas(area, APROBADO).ultima_version().exclude(valor=0).exclude(mcncuenta=0)
    aprobada = aprobada.exclude(mcncuenta__isnull=True)
    ap = aprobada.aggregate(
        version=Max("version"), n=Count("id"), total=Coalesce(Sum("valor"), 0),
        fecha=Max("fecha_version"),
    )
    if ap["version"] is None:
        ap["version"] = _ultima_version(area, APROBADO)
    sub = Cuenta5Presupuestado.objects.filter(origen_area=area).aggregate(
        version=Max("origen_version"), n=Count("id"), subido=Max("origen_subido"),
        total=Coalesce(Sum(F("mcnvaldebi") - F("mcnvalcred")), 0.0),
    )

    if ap["version"] is None:
        estado = "sin_aprobar"
    elif not sub["n"]:
        estado = "pendiente"
    elif (sub["version"] == ap["version"] and sub["n"] == ap["n"]
          and round(sub["total"]) == ap["total"]):
        estado = "subido"
    else:
        estado = "desactualizado"

    subido = timezone.localtime(sub["subido"]) if sub["subido"] else None
    if estado == "sin_aprobar":
        detalle = "Aprueba una versión para poder subirla"
    elif estado == "pendiente":
        detalle = f"v{ap['version']} aprobada, aún no está en Cuenta 5"
    elif estado == "subido":
        detalle = f"v{sub['version']} · {subido:%d/%m/%Y %H:%M}"
    elif sub["version"] != ap["version"]:
        detalle = f"En Cuenta 5: v{sub['version']} · aprobada: v{ap['version']}"
    else:
        detalle = f"v{ap['version']} cambió después de subirla"

    return {
        "area": area,
        "estado": estado,
        "texto": ESTADOS_CUENTA5[estado],
        "detalle": detalle,
        "version_aprobada": ap["version"],
        "version_subida": sub["version"],
        "registros_subidos": sub["n"],
        "subido": subido.strftime("%d/%m/%Y %H:%M") if subido else None,
    }


@login_required
def subir_cuenta5_sede(request, sede):
    """Sube (o reemplaza) la última versión aprobada del área en Cuenta 5 presupuestado."""
    config = _config_sede(sede)
    if not config:
        return JsonResponse({"success": False, "msg": "Área no configurada"}, status=404)
    if not _es_aprobador(request):
        return JsonResponse({"success": False, "msg": "Solo el aprobador puede subir a Cuenta 5"}, status=403)
    if request.method != "POST":
        return JsonResponse({"success": False, "msg": "Método no permitido"}, status=405)

    with transaction.atomic():
        registros, version, sin_cuenta = _movimientos_cuenta5(sede, config, timezone.now())
        if version is None:
            return JsonResponse({
                "success": False,
                "msg": f"{config['label']} no tiene una versión aprobada ❌",
                "estado": estado_cuenta5(sede),
            }, status=400)
        reemplazados, _ = Cuenta5Presupuestado.objects.filter(origen_area=sede).delete()
        Cuenta5Presupuestado.objects.bulk_create(registros, batch_size=1000)

    msg = f"{config['label']} v{version}: {len(registros)} registros subidos a Cuenta 5 ✅"
    if reemplazados:
        msg += f" (reemplazó {reemplazados} anteriores)"
    if sin_cuenta:
        msg += f" · {sin_cuenta} fila(s) sin cuenta contable no se subieron"
    return JsonResponse({
        "success": True, "msg": msg, "registros": len(registros),
        "reemplazados": reemplazados, "sin_cuenta": sin_cuenta,
        "estado": estado_cuenta5(sede),
    })


# ---------------------------------------------------------------------------
# Ajustes → Plazos de edición (solo el aprobador)
# ---------------------------------------------------------------------------
@login_required
def ajustes_plazos_edicion(request):
    if not _es_aprobador(request):
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")

    errores = []
    if request.method == "POST":
        nuevos = {}
        for area, config in SEDE_CONFIG.items():
            valor = (request.POST.get(f"fecha_{area}") or "").strip()
            if not valor:
                nuevos[area] = None
                continue
            try:
                nuevos[area] = datetime.date.fromisoformat(valor)
            except ValueError:
                errores.append(f"{config['label']}: fecha inválida ({valor})")
        if not errores:
            with transaction.atomic():
                for area, fecha in nuevos.items():
                    if fecha is None:
                        PlazoEdicionArea.objects.filter(area=area).delete()
                    else:
                        PlazoEdicionArea.objects.update_or_create(
                            area=area,
                            defaults={"fecha_limite": fecha, "actualizado_por": request.user.username},
                        )
            return redirect(f"{request.path}?guardado=1")

    hoy = timezone.localdate()
    configuradas = dict(PlazoEdicionArea.objects.values_list("area", "fecha_limite"))
    filas = []
    for area, config in sorted(SEDE_CONFIG.items(), key=lambda kv: kv[1]["label"]):
        automatica = fecha_limite_automatica(area)
        configurada = configuradas.get(area)
        efectiva = configurada or automatica
        filas.append({
            "area": area,
            "label": config["label"],
            "configurada": configurada,
            "automatica": automatica,
            "efectiva": efectiva,
            "abierto": hoy <= efectiva,
            "dias": (efectiva - hoy).days,
        })
    return render(request, "ajustes/plazos_edicion.html", {
        "filas": filas,
        "hoy": hoy,
        "guardado": request.GET.get("guardado") == "1",
        "errores": errores,
    })
