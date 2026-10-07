"""
Reglas de agrupación y nombres de las filas del Consolidado / Presupuestado /
Comparativo, leídas de la tabla AgrupacionCuenta (Ajustes → Agrupación de cuentas).

    reglas = cargar_reglas()
    reglas.agrupar("54100208")   -> "54100207_54100211"   (cuenta exacta)
    reglas.agrupar("52300501")   -> "5230"                (empieza por 5230)
    reglas.agrupar("541010")     -> "541010"              (no se agrupa)
    reglas.nombre("5230")        -> "Gastos no Operacionales-IVA obsequios"

Prioridad: primero las cuentas exactas; si no, el prefijo MÁS LARGO que coincida.
"""
import re

from .models import AgrupacionCuenta

PATRON_CODIGO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
PATRON_CUENTA = re.compile(r"^\d+$")


class ReglasCuentas:
    def __init__(self, filas):
        self.exactas = {}       # cuenta -> código de la fila
        self.prefijos = []      # [(prefijo, código)] del más largo al más corto
        self.nombres = {}       # código -> nombre
        for f in filas:
            codigo = f["codigo"]
            if f.get("nombre"):
                self.nombres[codigo] = f["nombre"]
            for cuenta in f.get("cuentas") or []:
                self.exactas.setdefault(str(cuenta), codigo)
            for prefijo in f.get("prefijos") or []:
                self.prefijos.append((str(prefijo), codigo))
        self.prefijos.sort(key=lambda pc: len(pc[0]), reverse=True)

    def agrupar(self, cuenta):
        """Código de la fila donde se suma la cuenta (o la misma cuenta)."""
        destino = self.exactas.get(cuenta)
        if destino is not None:
            return destino
        for prefijo, codigo in self.prefijos:
            if cuenta.startswith(prefijo):
                return codigo
        return cuenta

    def regla(self, cuenta):
        """Por qué cae donde cae: ('exacta' | 'prefijo' | None, código, prefijo)."""
        if cuenta in self.exactas:
            return "exacta", self.exactas[cuenta], None
        for prefijo, codigo in self.prefijos:
            if cuenta.startswith(prefijo):
                return "prefijo", codigo, prefijo
        return None, cuenta, None

    def nombre(self, codigo):
        return self.nombres.get(codigo)


def filas_reglas(excluir_id=None):
    qs = AgrupacionCuenta.objects.all()
    if excluir_id:
        qs = qs.exclude(pk=excluir_id)
    return list(qs.order_by("codigo").values("codigo", "nombre", "cuentas", "prefijos"))


def cargar_reglas():
    """Reglas vigentes (una consulta; se llama una vez por cálculo)."""
    return ReglasCuentas(filas_reglas())
