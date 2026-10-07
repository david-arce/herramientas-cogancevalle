"""
URL única de presupuesto + asignación de presupuestos por usuario.

  /mi-presupuesto/
      La ÚNICA URL que se le comparte a todos. Según quién inicie sesión:
        · aprobador                   -> dashboard de presupuestos
        · un presupuesto asignado     -> directo a su plantilla
        · varios / plazo cerrado      -> pantalla para elegir (o consultar)
        · ninguno                     -> aviso: pídele al administrador que te asigne

  Ajustes → Asignación de presupuestos  (solo el aprobador)
      Lista los usuarios y los presupuestos y permite asignar / quitar.

Las asignaciones viven en la tabla presupuesto_asignacion (AsignacionPresupuesto)
y son también las que dan permiso de entrar a cada presupuesto.
"""
import json

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from .models_presupuesto import AsignacionPresupuesto, tiene_asignacion
from .views_presupuesto_areas import APROBADORES, SEDE_CONFIG, _es_aprobador, fecha_limite_edicion

# ---------------------------------------------------------------------------
# Catálogo de presupuestos que se pueden asignar
# ---------------------------------------------------------------------------
# clave -> label, grupo, a dónde lleva y quién entra siempre (sin asignación).
# Las áreas salen de SEDE_CONFIG: un área nueva aparece aquí sola.
GRUPO_AREAS = "Presupuesto por área"
GRUPO_OTROS = "Otros presupuestos"


def _catalogo():
    catalogo = {}
    for clave, config in sorted(SEDE_CONFIG.items(), key=lambda kv: kv[1]["label"]):
        catalogo[clave] = {
            "label": config["label"],
            "grupo": GRUPO_AREAS,
            "url": ("tabla_auxiliar_sede", [clave]),
            "siempre": set(APROBADORES),
            "es_area": True,
        }
    catalogo["nomina"] = {
        "label": "Nómina", "grupo": GRUPO_OTROS,
        "url": ("presupuestoNomina", []), "siempre": {"admin"}, "es_area": False,
    }
    catalogo["comercial"] = {
        "label": "Comercial (ventas)", "grupo": GRUPO_OTROS,
        "url": ("baseComercial", []), "siempre": {"admin"}, "es_area": False,
    }
    return catalogo


PRESUPUESTOS_ASIGNABLES = _catalogo()


def puede_entrar(usuario, presupuesto):
    """Permiso de entrar a un presupuesto: los fijos del catálogo + los asignados."""
    info = PRESUPUESTOS_ASIGNABLES[presupuesto]
    return bool(usuario.is_authenticated and (
        usuario.username in info["siempre"] or tiene_asignacion(usuario, presupuesto)
    ))


def _asignados(usuario):
    """Claves asignadas al usuario, en el orden del catálogo."""
    claves = set(
        AsignacionPresupuesto.objects.filter(usuario=usuario).values_list("presupuesto", flat=True)
    )
    return [c for c in PRESUPUESTOS_ASIGNABLES if c in claves]


def _destino(clave, hoy):
    """A dónde lleva un presupuesto asignado y si hoy se puede editar."""
    info = PRESUPUESTOS_ASIGNABLES[clave]
    nombre_url, args = info["url"]
    destino = {
        "clave": clave,
        "label": info["label"],
        "grupo": info["grupo"],
        "url": reverse(nombre_url, args=args),
        "editable": True,
        "fecha_limite": None,
        "dias": None,
    }
    if info["es_area"]:
        limite, _ = fecha_limite_edicion(clave)
        destino["fecha_limite"] = limite
        destino["dias"] = (limite - hoy).days
        if hoy > limite:
            # Plazo cerrado: ya no puede editar, pero sí consultar lo aprobado.
            destino["editable"] = False
            destino["url"] = reverse("presupuesto_aprobado_sede", args=[clave])
    return destino


# ---------------------------------------------------------------------------
# La URL única
# ---------------------------------------------------------------------------
@login_required
def mi_presupuesto(request):
    if _es_aprobador(request):
        return redirect("dashboardPresupuesto")

    hoy = timezone.localdate()
    destinos = [_destino(c, hoy) for c in _asignados(request.user)]

    # Un solo presupuesto y abierto: directo a la plantilla, sin pantallas intermedias.
    if len(destinos) == 1 and destinos[0]["editable"]:
        return redirect(destinos[0]["url"])

    return render(request, "asignaciones/mi_presupuesto.html", {
        "destinos": destinos,
        "hoy": hoy,
    })


# ---------------------------------------------------------------------------
# Ajustes → Asignación de presupuestos (solo el aprobador)
# ---------------------------------------------------------------------------
def _usuarios():
    User = get_user_model()
    return (
        User.objects.filter(is_active=True)
        .order_by("username")
        .only("id", "username", "first_name", "last_name", "email", "last_login", "is_superuser")
    )


def _lista_asignaciones():
    return [
        {"usuario": u, "presupuesto": p}
        for u, p in AsignacionPresupuesto.objects.filter(
            usuario__is_active=True, presupuesto__in=PRESUPUESTOS_ASIGNABLES,
        ).order_by("usuario_id", "presupuesto").values_list("usuario_id", "presupuesto")
    ]


@login_required
def ajustes_asignaciones(request):
    if not _es_aprobador(request):
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")

    usuarios = [
        {
            "id": u.id,
            "username": u.username,
            "nombre": f"{u.first_name} {u.last_name}".strip(),
            "email": u.email,
            "ultimo_ingreso": (
                timezone.localtime(u.last_login).strftime("%d/%m/%Y") if u.last_login else None
            ),
            "aprobador": u.username in APROBADORES,
        }
        for u in _usuarios()
    ]
    presupuestos = [
        {"clave": c, "label": info["label"], "grupo": info["grupo"], "siempre": sorted(info["siempre"])}
        for c, info in PRESUPUESTOS_ASIGNABLES.items()
    ]
    return render(request, "ajustes/asignaciones.html", {
        "url_unica": request.build_absolute_uri(reverse("mi_presupuesto")),
        "datos": {
            "usuarios": usuarios,
            "presupuestos": presupuestos,
            "asignaciones": _lista_asignaciones(),
            "url_guardar": reverse("guardar_asignacion"),
        },
    })


@login_required
def guardar_asignacion(request):
    """POST {usuario, presupuesto, accion: "asignar" | "quitar"} -> todas las asignaciones."""
    if not _es_aprobador(request):
        return JsonResponse({"ok": False, "msg": "Sin permisos"}, status=403)
    if request.method != "POST":
        return JsonResponse({"ok": False, "msg": "Método no permitido"}, status=405)

    try:
        datos = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "msg": "Datos inválidos"}, status=400)

    clave = datos.get("presupuesto")
    accion = datos.get("accion")
    if clave not in PRESUPUESTOS_ASIGNABLES:
        return JsonResponse({"ok": False, "msg": "Presupuesto no válido"}, status=400)
    if accion not in ("asignar", "quitar"):
        return JsonResponse({"ok": False, "msg": "Acción no válida"}, status=400)
    try:
        usuario = get_user_model().objects.get(pk=int(datos.get("usuario")), is_active=True)
    except (TypeError, ValueError, get_user_model().DoesNotExist):
        return JsonResponse({"ok": False, "msg": "Usuario no encontrado"}, status=404)

    label = PRESUPUESTOS_ASIGNABLES[clave]["label"]
    with transaction.atomic():
        if accion == "asignar":
            _, creada = AsignacionPresupuesto.objects.get_or_create(
                usuario=usuario, presupuesto=clave,
                defaults={"asignado_por": request.user.username},
            )
            msg = (f"{label} asignado a {usuario.username} ✅" if creada
                   else f"{usuario.username} ya tenía {label}")
        else:
            AsignacionPresupuesto.objects.filter(usuario=usuario, presupuesto=clave).delete()
            msg = f"{label} quitado a {usuario.username}"

    return JsonResponse({"ok": True, "msg": msg, "asignaciones": _lista_asignaciones()})
