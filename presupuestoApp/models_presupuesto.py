"""
Presupuesto de gastos por área: UNA sola tabla para todas las áreas y etapas.

Antes había 42 modelos idénticos (3 por cada una de las 14 áreas):
    PresupuestoXxx          -> versiones subidas   (etapa = "proyectado")
    PresupuestoXxxAux       -> borrador editable   (etapa = "auxiliar")
    PresupuestoXxxAprobado  -> presupuesto aprobado (etapa = "aprobado")

Ahora cada registro dice a qué área y a qué etapa pertenece. Agregar un área
nueva ya no requiere modelos ni migraciones: solo su entrada en SEDE_CONFIG
(views_presupuesto_areas.py).

Almacenamiento VERTICAL
-----------------------
La tabla ya no tiene una columna por mes. Cada línea de presupuesto (lo que el
usuario ve como UNA fila de la grilla) se guarda como 12 registros, uno por
mes, identificados por:

    area + etapa + version + linea  -> la línea de presupuesto
    fecha                           -> primer día del mes (AAAA-01-01, AAAA-02-01, ...)
    valor                           -> el valor de ese mes

El total ya no se guarda: es la suma de los 12 valores y se calcula al leer.

La grilla sigue viéndose HORIZONTAL (una columna por mes). La conversión entre
ambos formatos vive aquí, en un solo lugar:

    PresupuestoArea.objects.de(area, etapa).horizontal()   vertical  -> horizontal
    filas_verticales(filas, area=..., etapa=...)          horizontal -> vertical
"""
import datetime

from django.db import models
from django.utils import timezone
from django.db.models import Count, Max

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
NUMERO_MES = {mes: i for i, mes in enumerate(MESES, start=1)}

# Campos que describen la línea de presupuesto (se repiten en sus 12 meses).
CAMPOS_LINEA = [
    "mcnzona", "zonnombre", "mcnccosto", "responsable", "mcncuenta",
    "ctanombre", "mcndetalle", "sede_distribucion", "proveedor", "comentario",
]

# Forma HORIZONTAL de una línea (la que usan la grilla, el Excel y la API).
CAMPOS_PRESUPUESTO = [
    "mcnzona", "zonnombre", "mcnccosto", "responsable", "mcncuenta",
    "ctanombre", "mcndetalle", "sede_distribucion", "proveedor",
    *MESES, "total", "comentario",
]
CAMPOS_NUMERICOS = ["mcncuenta", "sede_distribucion", *MESES, "total"]


def anio_presupuesto():
    """Año del presupuesto que se está elaborando: SIEMPRE el siguiente al actual.

    Es automático (no hay que cambiar nada en el código al pasar de año) y es
    la única fuente de verdad del año en todo el presupuesto por áreas.
    """
    return timezone.localdate().year + 1


def anio_elaboracion():
    """Año en que se elabora el presupuesto (el actual): datos base y plazos."""
    return anio_presupuesto() - 1


def fecha_mes(anio, mes):
    """Primer día del mes. `mes` puede ser el número (1-12) o el nombre ('enero')."""
    numero = NUMERO_MES[mes] if isinstance(mes, str) else int(mes)
    return datetime.date(int(anio), numero, 1)


class PresupuestoAreaQuerySet(models.QuerySet):
    def de(self, area, etapa):
        """Registros de un área en una etapa: PresupuestoArea.objects.de('logistica', 'aprobado')."""
        return self.filter(area=area, etapa=etapa)

    def versiones(self):
        """Lista ordenada de versiones distintas (sin nulos)."""
        return list(
            self.exclude(version__isnull=True)
            .order_by("version")
            .values_list("version", flat=True)
            .distinct()
        )

    def ultima_version(self):
        """Solo los registros de la versión más reciente (vacío si no hay versiones)."""
        maxima = self.aggregate(maxima=Max("version"))["maxima"]
        return self.none() if maxima is None else self.filter(version=maxima)

    def cantidad_lineas(self):
        """Cuántas líneas (filas de la grilla) hay, no cuántos registros mensuales."""
        return self.aggregate(n=Count("linea", distinct=True))["n"]

    def horizontal(self):
        """Pivota a una fila por línea con una columna por mes (+ total).

        Pensado para un solo conjunto área/etapa/versión (así lo usan las
        vistas); si el queryset mezcla varios, las líneas se separan por
        (area, etapa, version, linea).
        """
        campos = ["area", "etapa", "version", "fecha_version", "linea", "fecha", "valor", *CAMPOS_LINEA]
        registros = self.order_by("area", "etapa", "version", "linea", "fecha", "id").values(*campos)

        lineas = {}
        for r in registros:
            clave = (r["area"], r["etapa"], r["version"], r["linea"])
            fila = lineas.get(clave)
            if fila is None:
                fila = {
                    "linea": r["linea"],
                    "anio": r["fecha"].year,
                    **{c: r[c] for c in CAMPOS_LINEA},
                    **{m: 0 for m in MESES},
                    "version": r["version"],
                    "fecha_version": r["fecha_version"],
                }
                lineas[clave] = fila
            fila[MESES[r["fecha"].month - 1]] = r["valor"] or 0

        salida = list(lineas.values())
        for fila in salida:
            fila["total"] = sum(fila[m] for m in MESES)
        return salida


class PresupuestoArea(models.Model):
    class Etapa(models.TextChoices):
        AUXILIAR = "auxiliar", "Auxiliar (borrador editable)"
        PROYECTADO = "proyectado", "Proyectado (versiones subidas)"
        APROBADO = "aprobado", "Aprobado"

    area = models.CharField(max_length=40)        # clave de SEDE_CONFIG: 'almacen-tulua', 'tecnologia', ...
    etapa = models.CharField(max_length=12, choices=Etapa.choices)
    version = models.PositiveIntegerField(blank=True, null=True)  # None en la etapa auxiliar
    fecha_version = models.DateField(blank=True, null=True)       # cuándo se subió / aprobó la versión
    linea = models.PositiveIntegerField()         # agrupa los 12 meses de una misma fila de la grilla

    # ── Campos de negocio de la línea ──
    mcnzona = models.CharField(blank=True, null=True)           # centro de trabajo (antes centro_tra)
    zonnombre = models.CharField(blank=True, null=True)         # nombre del centro (antes nombre_cen)
    mcnccosto = models.CharField(blank=True, null=True)         # centro de costo (antes codcosto)
    responsable = models.CharField(blank=True, null=True)
    mcncuenta = models.BigIntegerField(blank=True, null=True)   # cuenta contable (antes cuenta)
    ctanombre = models.CharField(blank=True, null=True)         # nombre de la cuenta (antes cuenta_mayor)
    mcndetalle = models.CharField(blank=True, null=True)        # detalle (antes detalle_cuenta)
    sede_distribucion = models.FloatField(blank=True, null=True)
    proveedor = models.CharField(blank=True, null=True)
    comentario = models.TextField(blank=True, null=True)

    # ── El dato mensual ──
    fecha = models.DateField()                    # primer día del mes presupuestado
    valor = models.BigIntegerField(default=0)

    objects = PresupuestoAreaQuerySet.as_manager()

    class Meta:
        db_table = "presupuesto_area"
        indexes = [
            models.Index(fields=["area", "etapa", "version"], name="presup_area_etapa_ver_idx"),
            models.Index(fields=["fecha"], name="presup_area_fecha_idx"),
        ]

    def __str__(self):
        v = f" v{self.version}" if self.version is not None else ""
        return f"{self.area} / {self.etapa}{v} / L{self.linea} / {self.fecha:%Y-%m} / {self.mcncuenta or ''}"


def filas_verticales(filas, *, area, etapa, version=None, fecha_version=None, anio=None):
    """Convierte filas horizontales (una columna por mes) en registros verticales.

    Cada fila produce 12 PresupuestoArea (sin guardar), numerados como línea
    1, 2, 3... en el orden recibido. El año se toma de fila["anio"] si viene
    (así se conserva al reeditar), si no de `anio` o de anio_presupuesto()
    (automático: año siguiente al actual).
    """
    anio_defecto = anio or anio_presupuesto()
    registros = []
    for linea, fila in enumerate(filas, start=1):
        anio_fila = fila.get("anio") or anio_defecto
        comunes = {c: fila.get(c) for c in CAMPOS_LINEA}
        for mes in MESES:
            registros.append(PresupuestoArea(
                area=area, etapa=etapa, version=version, fecha_version=fecha_version,
                linea=linea, fecha=fecha_mes(anio_fila, mes), valor=fila.get(mes) or 0,
                **comunes,
            ))
    return registros


class PlazoEdicionArea(models.Model):
    """Fecha límite hasta la que el ÁREA puede editar su presupuesto.

    Se configura en Ajustes → Plazos de edición. Si un área no tiene fila aquí
    se usa el plazo automático (ver views_presupuesto_areas.fecha_limite_edicion).
    El aprobador nunca tiene fecha límite.
    """
    area = models.CharField(max_length=40, unique=True)     # clave de SEDE_CONFIG
    fecha_limite = models.DateField()                       # último día en que se puede editar
    actualizado_por = models.CharField(max_length=150, blank=True, default="")
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "presupuesto_plazo_edicion"

    def __str__(self):
        return f"{self.area}: hasta {self.fecha_limite:%d/%m/%Y}"
