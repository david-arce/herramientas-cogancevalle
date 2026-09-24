"""
Presupuesto de gastos por área: UNA sola tabla para todas las áreas y etapas.

Antes había 42 modelos idénticos (3 por cada una de las 14 áreas):
    PresupuestoXxx          -> versiones subidas   (etapa = "proyectado")
    PresupuestoXxxAux       -> borrador editable   (etapa = "auxiliar")
    PresupuestoXxxAprobado  -> presupuesto aprobado (etapa = "aprobado")

Ahora cada registro dice a qué área y a qué etapa pertenece. Agregar un área
nueva ya no requiere modelos ni migraciones: solo su entrada en SEDE_CONFIG
(views_presupuesto_areas.py).
"""
from django.db import models
from django.db.models import Max

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

# Campos de negocio (los mismos que tenían los 42 modelos antiguos).
CAMPOS_PRESUPUESTO = [
    "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta",
    "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor",
    *MESES, "total", "comentario",
]
CAMPOS_NUMERICOS = ["cuenta", "sede_distribucion", *MESES, "total"]


class PresupuestoAreaQuerySet(models.QuerySet):
    def de(self, area, etapa):
        """Filas de un área en una etapa: PresupuestoArea.objects.de('logistica', 'aprobado')."""
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
        """Solo las filas de la versión más reciente (vacío si no hay versiones)."""
        maxima = self.aggregate(maxima=Max("version"))["maxima"]
        return self.none() if maxima is None else self.filter(version=maxima)


class PresupuestoArea(models.Model):
    class Etapa(models.TextChoices):
        AUXILIAR = "auxiliar", "Auxiliar (borrador editable)"
        PROYECTADO = "proyectado", "Proyectado (versiones subidas)"
        APROBADO = "aprobado", "Aprobado"

    area = models.CharField(max_length=40)        # clave de SEDE_CONFIG: 'almacen-tulua', 'tecnologia', ...
    etapa = models.CharField(max_length=12, choices=Etapa.choices)
    version = models.PositiveIntegerField(blank=True, null=True)  # None en la etapa auxiliar
    fecha = models.DateField(blank=True, null=True)

    # ── Campos de negocio (mismos tipos que los modelos antiguos, para no perder datos) ──
    centro_tra = models.CharField(blank=True, null=True)
    nombre_cen = models.CharField(blank=True, null=True)
    codcosto = models.CharField(blank=True, null=True)
    responsable = models.CharField(blank=True, null=True)
    cuenta = models.BigIntegerField(blank=True, null=True)
    cuenta_mayor = models.CharField(blank=True, null=True)
    detalle_cuenta = models.CharField(blank=True, null=True)
    sede_distribucion = models.FloatField(blank=True, null=True)
    proveedor = models.CharField(blank=True, null=True)
    enero = models.BigIntegerField(blank=True, null=True)
    febrero = models.BigIntegerField(blank=True, null=True)
    marzo = models.BigIntegerField(blank=True, null=True)
    abril = models.BigIntegerField(blank=True, null=True)
    mayo = models.BigIntegerField(blank=True, null=True)
    junio = models.BigIntegerField(blank=True, null=True)
    julio = models.BigIntegerField(blank=True, null=True)
    agosto = models.BigIntegerField(blank=True, null=True)
    septiembre = models.BigIntegerField(blank=True, null=True)
    octubre = models.BigIntegerField(blank=True, null=True)
    noviembre = models.BigIntegerField(blank=True, null=True)
    diciembre = models.BigIntegerField(blank=True, null=True)
    total = models.BigIntegerField(blank=True, null=True)
    comentario = models.TextField(blank=True, null=True)

    objects = PresupuestoAreaQuerySet.as_manager()

    class Meta:
        db_table = "presupuesto_area"
        indexes = [
            models.Index(fields=["area", "etapa", "version"], name="presup_area_etapa_ver_idx"),
        ]

    def __str__(self):
        v = f" v{self.version}" if self.version is not None else ""
        return f"{self.area} / {self.etapa}{v} / {self.cuenta or ''}"
