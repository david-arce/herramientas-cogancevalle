"""Destinos de nómina: Ajustes → Destinos de nómina.

Las partes de la nómina con centro de costo 020301 deben tener destino (un
código AT/VT, p. ej. AT-00001) antes de subir la nómina a Cuenta 5
presupuestado. Al subir, el destino va en la columna mcndestino de esos
registros; con él, el consolidado los ubica en la fila que corresponde (ver
calcular_movimientos en views.py: AT propia → 6, convenios → 7).

  - El reparto NO se escribe aquí: sale de la distribución de nómina, que ya
    parte las filas de cada persona por centro/área (p. ej. 5 % ASISTENCIA
    TECNICA PROPIA y 5 % ASISTENCIA TECNICA CONVENIO). Cada parte hereda el
    centro de costo de su área.
  - Aquí se elige un destino por cada área de la persona que tenga 020301.
  - La persona es su cédula (sin cédula, su nombre).
  - Los destinos se eligen de la lista de códigos AT/VT que conoce el sistema.
  - Si a alguna parte le falta destino, la subida de nómina se bloquea.

Cargos comerciales (asesor comercial, auxiliar comercial y asistente técnico
comercial): en la misma pantalla se elige un destino por persona, de la lista
fija VT-00001 … VT-00027. Al subir, va en mcndestino de sus filas con cargo
comercial que no sean 020301 (esas llevan el destino de su área). Se guarda en
DestinoNomina con el área AREA_COMERCIAL. Que falte no bloquea la subida.
"""
import re
import unicodedata
from collections import Counter, defaultdict

from django.db import transaction
from django.db.models import Max
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render

from .models import AgrupacionCuenta
from .models_nomina import DestinoNomina, DistribucionNomina, PresupuestoNominaMes

CODCOSTO_CON_DESTINO = "020301"
_PATRON_DESTINO = re.compile(r"^(AT|VT)-\d+$")
SEPARADOR = "||"     # nombre del campo del formulario: destino::<persona>||<área>

# Cargos comerciales: un destino VT por persona
CARGOS_COMERCIALES = ("ASESOR COMERCIAL", "AUXILIAR COMERCIAL", "ASISTENTE TECNICO COMERCIAL")
DESTINOS_COMERCIALES = tuple(f"VT-{n:05d}" for n in range(1, 28))      # VT-00001 … VT-00027
AREA_COMERCIAL = "*CARGO COMERCIAL*"   # 'area' en DestinoNomina (no choca con un área real)
PREFIJO_COMERCIAL = "comercial::"      # nombre del campo del formulario: comercial::<persona>


def _codcosto(valor):
    """'020301', ' 020301 ' o 20301 (sin el cero) -> '020301'."""
    texto = str(valor or "").strip()
    return texto.zfill(6) if texto.isdigit() else texto


def requiere_destino(codcosto):
    return _codcosto(codcosto) == CODCOSTO_CON_DESTINO


def clave_persona(cedula, nombre=""):
    cedula = str(cedula or "").strip()
    if cedula.endswith(".0"):
        cedula = cedula[:-2]
    if cedula:
        return cedula
    return "SIN CEDULA: " + " ".join(str(nombre or "").upper().split())


def clave_area(area):
    """Área normalizada: sin tildes, mayúsculas, espacios simples."""
    texto = unicodedata.normalize("NFKD", str(area or "")).encode("ascii", "ignore").decode()
    return " ".join(texto.upper().split())


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
    """{(persona, área normalizada): destino} de todas las asignaciones guardadas."""
    return {(persona, area): destino for persona, area, destino
            in DestinoNomina.objects.values_list("persona", "area", "destino")}


def _distribucion_por_persona():
    """{cédula: {área normalizada: [(centro, %)]}} de la distribución de nómina."""
    salida = defaultdict(lambda: defaultdict(list))
    qs = DistribucionNomina.objects.all()
    if any(f.name == "activa" for f in DistribucionNomina._meta.get_fields()):
        qs = qs.filter(activa=True)      # una distribución desactivada no reparte
    for cedula, centro, area, pct in qs.values_list("cedula", "centro", "area", "porcentaje"):
        salida[clave_persona(cedula)][clave_area(area)].append((centro, pct))
    return salida


def personas_020301():
    """Personas con registros de nómina en 020301 que se subirían a Cuenta 5
    (valor distinto de 0 y con cuenta), cada una con sus partes por área:

      {persona, cedula, nombre, cargo, distribuida,
       partes: [{area, area_clave, centros, porcentaje, destino}], completo}

    `porcentaje` es el de la distribución de nómina para esa área (None si la
    persona no tiene distribución: todo su costo está en esa área).
    """
    filas = (PresupuestoNominaMes.objects
             .filter(codcosto__contains="20301").exclude(valor=0).exclude(cuenta="")
             .values_list("cedula", "nombre", "cargo", "centro", "area", "codcosto"))
    datos = defaultdict(lambda: {"nombres": Counter(), "cargos": Counter(), "cedula": "",
                                 "areas": defaultdict(lambda: {"nombre": Counter(), "centros": set()})})
    for cedula, nombre, cargo, centro, area, codcosto in filas:
        if not requiere_destino(codcosto):
            continue
        d = datos[clave_persona(cedula, nombre)]
        d["cedula"] = clave_persona(cedula) if str(cedula or "").strip() else ""
        d["nombres"][nombre] += 1
        d["cargos"][cargo] += 1
        a = d["areas"][clave_area(area)]
        a["nombre"][area] += 1
        if centro:
            a["centros"].add(centro)

    asignados = destinos_asignados()
    distribucion = _distribucion_por_persona()
    mas_comun = lambda c: c.most_common(1)[0][0] if c else ""  # noqa: E731
    personas = []
    for clave, d in datos.items():
        reparto = distribucion.get(clave, {})
        partes = []
        for area_clave, a in sorted(d["areas"].items()):
            en_distribucion = reparto.get(area_clave, [])
            partes.append({
                "area": mas_comun(a["nombre"]),
                "area_clave": area_clave,
                "centros": sorted(a["centros"]),
                "porcentaje": round(sum(p for _, p in en_distribucion), 4) if en_distribucion else None,
                "destino": asignados.get((clave, area_clave), ""),
            })
        personas.append({
            "persona": clave,
            "cedula": d["cedula"],
            "nombre": mas_comun(d["nombres"]),
            "cargo": mas_comun(d["cargos"]),
            "distribuida": bool(reparto),
            "partes": partes,
            "completo": all(p["destino"] for p in partes),
        })
    return sorted(personas, key=lambda p: (p["nombre"], p["persona"]))


def es_cargo_comercial(cargo):
    """'Asesor Comercial', 'ASISTENTE TÉCNICO COMERCIAL II'… (sin tildes, empieza por el cargo)."""
    clave = clave_area(cargo)
    return any(clave.startswith(c) for c in CARGOS_COMERCIALES)


def opciones_destino_comercial():
    """[(codigo, nombre)] VT-00001 … VT-00027, con el nombre de Agrupación de cuentas si lo tiene."""
    nombres = {(codigo or "").strip().upper(): nombre for codigo, nombre
               in AgrupacionCuenta.objects.filter(codigo__istartswith="VT-").values_list("codigo", "nombre")}
    return [(c, nombres.get(c, "")) for c in DESTINOS_COMERCIALES]


def destinos_comerciales():
    """{persona: destino} de los cargos comerciales."""
    return dict(DestinoNomina.objects.filter(area=AREA_COMERCIAL).values_list("persona", "destino"))


def personas_comerciales():
    """Personas con cargo comercial en la nómina que se subiría a Cuenta 5
    (valor distinto de 0 y con cuenta):

      {persona, cedula, nombre, cargo, areas, centros, destino}
    """
    filas = (PresupuestoNominaMes.objects
             .filter(cargo__icontains="COMERCIAL").exclude(valor=0).exclude(cuenta="")
             .values_list("cedula", "nombre", "cargo", "centro", "area"))
    datos = defaultdict(lambda: {"nombres": Counter(), "cargos": Counter(), "cedula": "",
                                 "areas": Counter(), "centros": set()})
    for cedula, nombre, cargo, centro, area in filas:
        if not es_cargo_comercial(cargo):
            continue
        d = datos[clave_persona(cedula, nombre)]
        d["cedula"] = clave_persona(cedula) if str(cedula or "").strip() else ""
        d["nombres"][nombre] += 1
        d["cargos"][cargo] += 1
        if area:
            d["areas"][area] += 1
        if centro:
            d["centros"].add(centro)

    asignados = destinos_comerciales()
    mas_comun = lambda c: c.most_common(1)[0][0] if c else ""  # noqa: E731
    personas = [{
        "persona": clave,
        "cedula": d["cedula"],
        "nombre": mas_comun(d["nombres"]),
        "cargo": mas_comun(d["cargos"]),
        "areas": sorted(d["areas"]),
        "centros": sorted(d["centros"]),
        "destino": asignados.get(clave, ""),
    } for clave, d in datos.items()]
    return sorted(personas, key=lambda p: (p["nombre"], p["persona"]))


def destino_comercial(destinos, cedula, nombre, cargo):
    """Destino VT de una fila de nómina con cargo comercial (None si no aplica o no tiene)."""
    if not es_cargo_comercial(cargo):
        return None
    return destinos.get(clave_persona(cedula, nombre)) or None


def faltantes():
    """Personas de 020301 con alguna parte (área) sin destino."""
    return [p for p in personas_020301() if not p["completo"]]


def ultimo_cambio():
    """Cuándo se cambió por última vez una asignación (para saber si lo subido quedó viejo)."""
    return DestinoNomina.objects.aggregate(m=Max("actualizado"))["m"]


def _guardar(nuevos, usuario):
    """nuevos = {(persona, área): destino ('' = quitar)}. Solo toca lo que cambió."""
    actuales = destinos_asignados()
    with transaction.atomic():
        for (persona, area), destino in nuevos.items():
            antes = actuales.get((persona, area), "")
            if destino == antes:
                continue
            if not destino:
                DestinoNomina.objects.filter(persona=persona, area=area).delete()
            else:
                # save() actualiza 'actualizado' (auto_now): así lo subido queda desactualizado
                obj, _ = DestinoNomina.objects.get_or_create(persona=persona, area=area,
                                                             defaults={"destino": destino})
                obj.destino, obj.actualizado_por = destino, usuario
                obj.save()


# ---------------------------------------------------------------------------
# Ajustes → Destinos de nómina (solo el aprobador)
# ---------------------------------------------------------------------------
def ajustes_destinos_nomina(request):
    from .views_presupuesto_areas import _es_aprobador
    if not _es_aprobador(request):
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")

    opciones = opciones_destino()
    validos = {c for c, _ in opciones}
    opciones_com = opciones_destino_comercial()
    validos_com = set(DESTINOS_COMERCIALES)
    errores = []
    personas = personas_020301()
    comerciales = personas_comerciales()
    seccion = request.POST.get("seccion") or request.GET.get("seccion") or ""

    if request.method == "POST":
        nuevos = {}
        for p in comerciales:
            campo = PREFIJO_COMERCIAL + p["persona"]
            if campo not in request.POST:
                continue                          # no vino en el formulario: no se toca
            valor = (request.POST.get(campo) or "").strip().upper()
            if valor and valor not in validos_com:
                errores.append(f"{p['nombre'] or p['persona']} ({p['cargo']}): "
                               f"destino {valor} no está en la lista")
            nuevos[(p["persona"], AREA_COMERCIAL)] = valor
        for p in personas:
            for parte in p["partes"]:
                campo = f"destino::{p['persona']}{SEPARADOR}{parte['area_clave']}"
                if campo not in request.POST:
                    continue                      # no vino en el formulario: no se toca
                valor = (request.POST.get(campo) or "").strip().upper()
                if valor and valor not in validos:
                    errores.append(f"{p['nombre'] or p['persona']} ({parte['area']}): "
                                   f"destino {valor} no está en la lista")
                nuevos[(p["persona"], parte["area_clave"])] = valor
        if not errores:
            _guardar(nuevos, request.user.username)
            if seccion == "comerciales":
                return redirect(f"{request.path}?guardado=1&seccion=comerciales#comerciales")
            return redirect(f"{request.path}?guardado=1")

    return render(request, "ajustes/destinos_nomina.html", {
        "personas": personas,
        "opciones": opciones,
        "nombres_destino": dict(opciones),
        "sin_destino": sum(1 for p in personas if not p["completo"]),
        "codcosto": CODCOSTO_CON_DESTINO,
        "separador": SEPARADOR,
        "guardado": request.GET.get("guardado") == "1",
        "errores": errores,
        "seccion": seccion,
        "comerciales": comerciales,
        "opciones_comercial": opciones_com,
        "comerciales_sin_destino": sum(1 for p in comerciales if not p["destino"]),
        "cargos_comerciales": CARGOS_COMERCIALES,
        "prefijo_comercial": PREFIJO_COMERCIAL,
    })
