"""Destinos de nómina: Ajustes → Destinos de nómina.

Las personas de nómina con centro de costo 020301 deben tener un destino (un
código AT/VT, p. ej. AT-00001) antes de subir la nómina a Cuenta 5
presupuestado. Al subir, ese destino va en la columna mcndestino de sus
registros; con él, el consolidado las ubica en la fila que corresponde (ver
calcular_movimientos en views.py: AT propia → 6, convenios → 7).

  - Un destino por persona (la persona es su cédula; sin cédula, su nombre).
  - Los destinos se eligen de la lista de códigos AT/VT que conoce el sistema.
  - Si falta el destino de alguna persona, la subida de nómina se bloquea.
"""
import re
from collections import Counter, defaultdict

from django.db import transaction
from django.db.models import Max
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render

from .models import AgrupacionCuenta
from .models_nomina import DestinoNomina, PresupuestoNominaMes

CODCOSTO_CON_DESTINO = "020301"
_PATRON_DESTINO = re.compile(r"^(AT|VT)-\d+$")


def _codcosto(valor):
    """'020301', ' 020301 ' o 20301 (sin el cero) -> '020301'."""
    texto = str(valor or "").strip()
    return texto.zfill(6) if texto.isdigit() else texto


def requiere_destino(codcosto):
    return _codcosto(codcosto) == CODCOSTO_CON_DESTINO


def clave_persona(cedula, nombre=""):
    cedula = str(cedula or "").strip()
    if cedula:
        return cedula
    return "SIN CEDULA: " + " ".join(str(nombre or "").upper().split())


def opciones_destino():
    """[(codigo, nombre)] de los destinos AT/VT que conoce el sistema, ordenados.

    Son los códigos fijos del consolidado (views.ASISTENCIA_TECNICA*) más los
    AT/VT que existan en Ajustes → Agrupación de cuentas, con su nombre.
    """
    from . import views   # import tardío: views importa este módulo indirectamente
    codigos = set(views.ASISTENCIA_TECNICA) | set(views.ASISTENCIA_TECNICA_PROPIA) \
        | set(views.ASISTENCIA_TECNICA_CONVENIOS)
    nombres = {}
    for codigo, nombre in AgrupacionCuenta.objects.values_list("codigo", "nombre"):
        codigo = (codigo or "").strip().upper()
        if _PATRON_DESTINO.match(codigo):
            codigos.add(codigo)
            nombres[codigo] = nombre
    return [(c, nombres.get(c, "")) for c in sorted(codigos)]


def personas_020301():
    """Personas con registros de nómina en 020301 que se subirían a Cuenta 5
    (valor distinto de 0 y con cuenta), con su destino asignado (o "")."""
    filas = (PresupuestoNominaMes.objects
             .filter(codcosto__contains="20301").exclude(valor=0).exclude(cuenta="")
             .values_list("cedula", "nombre", "cargo", "centro", "area", "codcosto"))
    datos = defaultdict(lambda: {"nombres": Counter(), "cargos": Counter(), "centros": Counter(),
                                 "areas": Counter(), "cedula": ""})
    for cedula, nombre, cargo, centro, area, codcosto in filas:
        if not requiere_destino(codcosto):
            continue
        d = datos[clave_persona(cedula, nombre)]
        d["cedula"] = (cedula or "").strip()
        d["nombres"][nombre] += 1
        d["cargos"][cargo] += 1
        d["centros"][centro] += 1
        d["areas"][area] += 1

    asignados = dict(DestinoNomina.objects.values_list("persona", "destino"))
    mas_comun = lambda c: c.most_common(1)[0][0] if c else ""  # noqa: E731
    personas = [{
        "persona": clave,
        "cedula": d["cedula"],
        "nombre": mas_comun(d["nombres"]),
        "cargo": mas_comun(d["cargos"]),
        "centro": mas_comun(d["centros"]),
        "area": mas_comun(d["areas"]),
        "destino": asignados.get(clave, ""),
    } for clave, d in datos.items()]
    return sorted(personas, key=lambda p: (p["nombre"], p["persona"]))


def destinos_asignados():
    """{persona: destino} de todas las asignaciones guardadas."""
    return dict(DestinoNomina.objects.values_list("persona", "destino"))


def faltantes():
    """Personas de 020301 sin destino asignado."""
    return [p for p in personas_020301() if not p["destino"]]


def ultimo_cambio():
    """Cuándo se cambió por última vez una asignación (para saber si lo subido quedó viejo)."""
    return DestinoNomina.objects.aggregate(m=Max("actualizado"))["m"]


# ---------------------------------------------------------------------------
# Ajustes → Destinos de nómina (solo el aprobador)
# ---------------------------------------------------------------------------
def ajustes_destinos_nomina(request):
    from .views_presupuesto_areas import _es_aprobador
    if not _es_aprobador(request):
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")

    opciones = opciones_destino()
    validos = {c for c, _ in opciones}
    errores = []

    if request.method == "POST":
        personas = {p["persona"]: p for p in personas_020301()}
        nuevos = {}
        for persona, p in personas.items():
            valor = (request.POST.get(f"destino::{persona}") or "").strip().upper()
            if valor and valor not in validos:
                errores.append(f"{p['nombre'] or persona}: destino {valor} no está en la lista")
            nuevos[persona] = valor
        if not errores:
            with transaction.atomic():
                for persona, destino in nuevos.items():
                    if not destino:
                        DestinoNomina.objects.filter(persona=persona).delete()
                        continue
                    obj = DestinoNomina.objects.filter(persona=persona).first()
                    if obj is None:
                        DestinoNomina.objects.create(persona=persona, destino=destino,
                                                     actualizado_por=request.user.username)
                    elif obj.destino != destino:   # solo se toca lo que cambió
                        obj.destino = destino
                        obj.actualizado_por = request.user.username
                        obj.save(update_fields=["destino", "actualizado", "actualizado_por"])
            return redirect(f"{request.path}?guardado=1")

    personas = personas_020301()
    return render(request, "ajustes/destinos_nomina.html", {
        "personas": personas,
        "opciones": opciones,
        "nombres_destino": dict(opciones),
        "sin_destino": sum(1 for p in personas if not p["destino"]),
        "codcosto": CODCOSTO_CON_DESTINO,
        "guardado": request.GET.get("guardado") == "1",
        "errores": errores,
    })
