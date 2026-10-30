"""Destinos de nómina: Ajustes → Destinos de nómina.

Las personas de nómina con centro de costo 020301 deben tener destino (códigos
AT/VT, p. ej. AT-00001) antes de subir la nómina a Cuenta 5 presupuestado. Al
subir, el destino va en la columna mcndestino de sus registros; con él, el
consolidado las ubica en la fila que corresponde (ver calcular_movimientos en
views.py: AT propia → 6, convenios → 7).

  - Una persona puede tener uno o varios destinos, cada uno con su porcentaje;
    entre todos deben sumar 100 %. Al subir, cada registro mensual se reparte
    entre sus destinos sin perder pesos (ver repartir).
  - La persona es su cédula (sin cédula, su nombre).
  - Los destinos se eligen de la lista de códigos AT/VT que conoce el sistema.
  - Si alguna persona no tiene destinos, o no suman 100 %, la subida se bloquea.
"""
import math
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
_TOLERANCIA = 0.01   # en puntos porcentuales


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


def reparto_completo(reparto):
    """True si hay al menos un destino y los porcentajes suman 100."""
    return bool(reparto) and abs(sum(p for _, p in reparto) - 100) <= _TOLERANCIA


def repartir(valor, reparto):
    """Reparte un valor entero entre [(destino, %)] sin perder pesos.

    Cada destino recibe su parte redondeada hacia abajo y los pesos que sobran
    se dan a los de mayor fracción (método del mayor residuo), así la suma da
    exactamente `valor`. Funciona igual con valores negativos.
    """
    valor = int(round(valor))
    if len(reparto) == 1:
        return [(reparto[0][0], valor)]
    signo = -1 if valor < 0 else 1
    absoluto = abs(valor)
    exactos = [absoluto * p / 100 for _, p in reparto]
    partes = [math.floor(x) for x in exactos]
    sobran = absoluto - sum(partes)
    orden = sorted(range(len(reparto)), key=lambda i: exactos[i] - partes[i], reverse=True)
    for i in orden[:sobran]:
        partes[i] += 1
    return [(destino, signo * parte) for (destino, _), parte in zip(reparto, partes)]


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


def destinos_asignados():
    """{persona: [(destino, porcentaje), ...]} de todas las asignaciones guardadas."""
    repartos = defaultdict(list)
    for persona, destino, pct in (DestinoNomina.objects.order_by("persona", "-porcentaje", "destino")
                                  .values_list("persona", "destino", "porcentaje")):
        repartos[persona].append((destino, pct))
    return dict(repartos)


def personas_020301():
    """Personas con registros de nómina en 020301 que se subirían a Cuenta 5
    (valor distinto de 0 y con cuenta), con sus destinos asignados."""
    filas = (PresupuestoNominaMes.objects
             .filter(codcosto__contains="20301").exclude(valor=0).exclude(cuenta="")
             .values_list("cedula", "nombre", "cargo", "centro", "area", "codcosto"))
    datos = defaultdict(lambda: {"nombres": Counter(), "cargos": Counter(), "centros": Counter(),
                                 "areas": Counter(), "cedula": "", "registros": 0})
    for cedula, nombre, cargo, centro, area, codcosto in filas:
        if not requiere_destino(codcosto):
            continue
        d = datos[clave_persona(cedula, nombre)]
        d["cedula"] = (cedula or "").strip()
        d["nombres"][nombre] += 1
        d["cargos"][cargo] += 1
        d["centros"][centro] += 1
        d["areas"][area] += 1
        d["registros"] += 1

    asignados = destinos_asignados()
    mas_comun = lambda c: c.most_common(1)[0][0] if c else ""  # noqa: E731
    personas = []
    for clave, d in datos.items():
        reparto = asignados.get(clave, [])
        personas.append({
            "persona": clave,
            "cedula": d["cedula"],
            "nombre": mas_comun(d["nombres"]),
            "cargo": mas_comun(d["cargos"]),
            "centro": mas_comun(d["centros"]),
            "area": mas_comun(d["areas"]),
            "registros": d["registros"],
            "destinos": reparto,
            "suma": round(sum(p for _, p in reparto), 2),
            "completo": reparto_completo(reparto),
        })
    return sorted(personas, key=lambda p: (p["nombre"], p["persona"]))


def faltantes():
    """Personas de 020301 sin destinos o cuyo reparto no suma 100 %."""
    return [p for p in personas_020301() if not p["completo"]]


def registros_extra(personas=None):
    """Registros de más que crea el reparto al subir (una persona con 3 destinos
    convierte cada registro en 3). Lo usa el estado de la tarjeta para comparar."""
    personas = personas_020301() if personas is None else personas
    return sum(p["registros"] * (len(p["destinos"]) - 1) for p in personas if p["completo"])


def ultimo_cambio():
    """Cuándo se cambió por última vez una asignación (para saber si lo subido quedó viejo)."""
    return DestinoNomina.objects.aggregate(m=Max("actualizado"))["m"]


def _numero(texto):
    texto = str(texto or "").strip().replace("%", "").replace(",", ".")
    if not texto:
        return None
    try:
        return float(texto)
    except ValueError:
        return float("nan")


def _leer_formulario(request, personas, validos):
    """{persona: [(destino, %)]} del formulario y la lista de errores."""
    nuevos, errores = {}, []
    for persona, p in personas.items():
        nombre = p["nombre"] or persona
        destinos = request.POST.getlist(f"destino::{persona}")
        porcentajes = request.POST.getlist(f"porcentaje::{persona}")
        reparto, vistos = [], set()
        for i, destino in enumerate(destinos):
            destino = (destino or "").strip().upper()
            pct = _numero(porcentajes[i] if i < len(porcentajes) else "")
            if not destino and pct is None:
                continue                                # fila vacía
            if not destino:
                errores.append(f"{nombre}: falta elegir el destino de un {pct:g} %")
                continue
            if destino not in validos:
                errores.append(f"{nombre}: destino {destino} no está en la lista")
                continue
            if destino in vistos:
                errores.append(f"{nombre}: {destino} está repetido")
                continue
            if pct is None and len([d for d in destinos if (d or "").strip()]) == 1:
                pct = 100.0                             # un solo destino sin % = 100 %
            if pct is None or math.isnan(pct) or pct <= 0 or pct > 100:
                errores.append(f"{nombre}: el porcentaje de {destino} debe estar entre 0 y 100")
                continue
            vistos.add(destino)
            reparto.append((destino, round(pct, 4)))
        if reparto and not reparto_completo(reparto):
            errores.append(f"{nombre}: los porcentajes suman {sum(x for _, x in reparto):g} %, deben sumar 100 %")
        nuevos[persona] = reparto
    return nuevos, errores


def _guardar(nuevos, usuario):
    """Reemplaza las asignaciones de cada persona. Solo toca lo que cambió, así
    'actualizado' solo se mueve si de verdad cambió algo."""
    actuales = destinos_asignados()
    with transaction.atomic():
        for persona, reparto in nuevos.items():
            antes = sorted(actuales.get(persona, []))
            if sorted(reparto) == antes:
                continue
            DestinoNomina.objects.filter(persona=persona).delete()
            DestinoNomina.objects.bulk_create([
                DestinoNomina(persona=persona, destino=d, porcentaje=pct, actualizado_por=usuario)
                for d, pct in reparto])


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
    personas = personas_020301()

    if request.method == "POST":
        nuevos, errores = _leer_formulario(request, {p["persona"]: p for p in personas}, validos)
        if not errores:
            _guardar(nuevos, request.user.username)
            return redirect(f"{request.path}?guardado=1")
        # Con errores no se guarda nada y se muestra lo que se envió para corregirlo.
        for p in personas:
            p["destinos"] = [(d, pct) for d, pct in nuevos.get(p["persona"], [])] or p["destinos"]

    for p in personas:
        # Para la plantilla: filas de destino y el % ya formateado
        p["filas"] = [{"destino": d, "porcentaje": f"{pct:g}"} for d, pct in p["destinos"]] or \
                     [{"destino": "", "porcentaje": ""}]
    return render(request, "ajustes/destinos_nomina.html", {
        "personas": personas,
        "opciones": opciones,
        "nombres_destino": dict(opciones),
        "sin_destino": sum(1 for p in personas if not p["completo"]),
        "codcosto": CODCOSTO_CON_DESTINO,
        "guardado": request.GET.get("guardado") == "1",
        "errores": errores,
    })
