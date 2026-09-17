"""
Tabla única del presupuesto de nómina.

Sustituye a las 34 tablas anteriores (PresupuestoSueldos + PresupuestoSueldosAux,
PresupuestoComisiones + PresupuestoComisionesAux, ...). Todos los conceptos
compartían los mismos campos, así que ahora viven en una sola tabla y se
distinguen por `tipo` ('sueldos', 'comisiones', 'cesantias', ...).

Ya no hay tabla "auxiliar" y tabla "definitiva": se edita directamente aquí.
Cada fila sabe si su valor lo calcula el sistema o lo fijó una persona:

  origen = 'sistema'  → el motor (nomina_motor.py) la recalcula cada vez que
                        cambia algo de lo que depende (otra tabla o un parámetro).
  origen = 'manual'   → alguien la editó o la agregó a mano; el motor la respeta
                        y no la sobrescribe hasta que se pida "Restablecer cálculo".
"""
from django.db import models

MESES = (
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
)


class PresupuestoNomina(models.Model):
    ORIGEN_SISTEMA = 'sistema'
    ORIGEN_MANUAL = 'manual'
    ORIGENES = [(ORIGEN_SISTEMA, 'Calculado'), (ORIGEN_MANUAL, 'Manual')]

    tipo = models.CharField(max_length=40, db_index=True)

    cedula = models.CharField(max_length=20, blank=True, default='')
    nombre = models.CharField(max_length=150, blank=True, default='')
    centro = models.CharField(max_length=150, blank=True, default='')
    area = models.CharField(max_length=150, blank=True, default='')
    cargo = models.CharField(max_length=150, blank=True, default='')
    concepto = models.CharField(max_length=80, blank=True, default='')

    # Antes: "salario_base" en sueldos/aprendiz y "base" en transporte/kyrovet.
    base = models.BigIntegerField(default=0)
    # Fracción de la persona que corresponde a esta fila. Al distribuir una
    # fila en varios centros/áreas cada copia guarda su porcentaje aquí, así
    # sigue recalculándose sola cuando cambian los parámetros.
    factor = models.FloatField(default=1)
    # Valores de origen (los que llegaron de ConceptosFijosYVariables) sobre
    # los que se aplica la fórmula. Permite recalcular sin acumular incrementos.
    historico = models.JSONField(default=dict, blank=True)

    enero = models.BigIntegerField(default=0)
    febrero = models.BigIntegerField(default=0)
    marzo = models.BigIntegerField(default=0)
    abril = models.BigIntegerField(default=0)
    mayo = models.BigIntegerField(default=0)
    junio = models.BigIntegerField(default=0)
    julio = models.BigIntegerField(default=0)
    agosto = models.BigIntegerField(default=0)
    septiembre = models.BigIntegerField(default=0)
    octubre = models.BigIntegerField(default=0)
    noviembre = models.BigIntegerField(default=0)
    diciembre = models.BigIntegerField(default=0)
    total = models.BigIntegerField(default=0)

    origen = models.CharField(max_length=10, choices=ORIGENES, default=ORIGEN_MANUAL)
    # Identifica de qué fila de origen salió una fila calculada. Si alguien la
    # edita, la clave se conserva y el motor ya no genera otra para lo mismo.
    clave = models.CharField(max_length=255, blank=True, default='')
    # Centro y área de donde viene la fila antes de aplicar la distribución por
    # persona (DistribucionNomina). Permiten deshacer o cambiar el reparto.
    centro_origen = models.CharField(max_length=150, blank=True, default='')
    area_origen = models.CharField(max_length=150, blank=True, default='')

    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    actualizado_por = models.CharField(max_length=150, blank=True, default='')

    class Meta:
        db_table = 'presupuesto_nomina'
        ordering = ['tipo', 'id']
        indexes = [
            models.Index(fields=['tipo', 'origen'], name='nomina_tipo_origen_idx'),
            models.Index(fields=['tipo', 'cedula'], name='nomina_tipo_cedula_idx'),
        ]

    def __str__(self):
        return f'{self.tipo} · {self.cedula or self.area} · {self.concepto}'

    def calcular_total(self):
        self.total = sum(getattr(self, mes) or 0 for mes in MESES)
        return self.total

    def save(self, *args, **kwargs):
        self.calcular_total()
        super().save(*args, **kwargs)


# ══════════════════════════════════════════════════════════════════════
#  Datos de origen de la nómina (antes: ConceptosFijosYVariables +
#  ConceptoAuxilioEducacion)
# ══════════════════════════════════════════════════════════════════════

class ConceptosNomina(models.Model):
    """Conceptos fijos y variables de nómina, identificados por año.

    Reemplaza a las dos tablas anteriores, que tenían los mismos campos:
      - conceptos_fijos_y_variables → los datos del año base
      - concepto_auxilio_educacion  → los mismos datos del año anterior
    Ahora ambos viven aquí y se distinguen por `anio`. Se llenan subiendo el
    Excel de nómina desde el tablero (o con el comando migrar_conceptos_nomina).

    Los códigos (centro, costo, cuenta, cargo, concepto) se guardan como texto
    para conservar los ceros a la izquierda ('001', '016', 'E14').
    """
    anio = models.PositiveSmallIntegerField('año', db_index=True)
    # Opcional: hasta qué fecha llegan los datos reales del archivo. Si se
    # indica, define cuántos meses se toman como histórico (ver nomina_conceptos).
    fecha_corte = models.DateField('fecha de corte', null=True, blank=True)

    centro_tra = models.CharField(max_length=30, blank=True, default='')
    nombre_cen = models.CharField(max_length=150, blank=True, default='')
    codcosto = models.CharField(max_length=30, blank=True, default='')
    nomcosto = models.CharField(max_length=150, blank=True, default='')
    tipocpto = models.CharField(max_length=30, blank=True, default='')
    cuenta = models.CharField(max_length=30, blank=True, default='')
    concepto = models.CharField(max_length=30, blank=True, default='', db_index=True)
    nombre_con = models.CharField(max_length=150, blank=True, default='')
    cargo = models.CharField(max_length=30, blank=True, default='')
    nombrecar = models.CharField(max_length=150, blank=True, default='')
    cedula = models.BigIntegerField(null=True, blank=True)
    nombre = models.CharField(max_length=150, blank=True, default='')
    arlporc = models.FloatField(null=True, blank=True)
    concepto_f = models.BigIntegerField(default=0)

    enero = models.BigIntegerField(default=0)
    febrero = models.BigIntegerField(default=0)
    marzo = models.BigIntegerField(default=0)
    abril = models.BigIntegerField(default=0)
    mayo = models.BigIntegerField(default=0)
    junio = models.BigIntegerField(default=0)
    julio = models.BigIntegerField(default=0)
    agosto = models.BigIntegerField(default=0)
    septiembre = models.BigIntegerField(default=0)
    octubre = models.BigIntegerField(default=0)
    noviembre = models.BigIntegerField(default=0)
    diciembre = models.BigIntegerField(default=0)
    total = models.BigIntegerField(default=0)

    archivo = models.CharField(max_length=255, blank=True, default='')
    cargado = models.DateTimeField(auto_now_add=True)
    cargado_por = models.CharField(max_length=150, blank=True, default='')

    class Meta:
        db_table = 'conceptos_nomina'
        verbose_name = 'concepto de nómina'
        verbose_name_plural = 'conceptos de nómina'
        indexes = [
            models.Index(fields=['anio', 'concepto'], name='cnomina_anio_concepto_idx'),
            models.Index(fields=['anio', 'cedula'], name='cnomina_anio_cedula_idx'),
        ]

    def __str__(self):
        return f'{self.anio} · {self.cedula} · {self.concepto} {self.nombre_con}'

    def save(self, *args, **kwargs):
        self.total = sum(getattr(self, mes) or 0 for mes in MESES)
        super().save(*args, **kwargs)


class ConfiguracionNomina(models.Model):
    """Una sola fila (id=1) con las opciones de origen de datos.

    Vacío = automático:
      anio_base    → el año más reciente cargado en ConceptosNomina.
      meses_reales → el último mes con datos de ese año (o el de su fecha de corte).
    """
    anio_base = models.PositiveSmallIntegerField(null=True, blank=True)
    meses_reales = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'configuracion_nomina'

    @classmethod
    def actual(cls):
        return cls.objects.get_or_create(pk=1)[0]


class DistribucionNomina(models.Model):
    """Reparto de una persona entre centros/áreas (se define en la vista consolidada).

    Se aplica a TODOS los conceptos base de la persona (sueldo, comisiones,
    horas extra, ...) y, por cascada, a los derivados (prestaciones, seguridad
    social, ...). También se vuelve a aplicar cada vez que se cargan los
    conceptos desde el Excel, así no hay que repetirla.
    """
    cedula = models.CharField(max_length=20, db_index=True)
    centro = models.CharField(max_length=150, blank=True, default='')
    area = models.CharField(max_length=150)
    porcentaje = models.FloatField()
    actualizado = models.DateTimeField(auto_now=True)
    actualizado_por = models.CharField(max_length=150, blank=True, default='')

    class Meta:
        db_table = 'distribucion_nomina'
        ordering = ['cedula', 'id']
        constraints = [
            models.UniqueConstraint(fields=['cedula', 'centro', 'area'], name='distribucion_nomina_unica'),
        ]

    def __str__(self):
        return f'{self.cedula} → {self.centro} / {self.area}: {self.porcentaje}%'
