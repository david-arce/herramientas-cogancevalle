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


def _anio_presupuesto():
    from .models_presupuesto import anio_presupuesto
    return anio_presupuesto()


class _CamposLineaNomina(models.Model):
    """Campos que describen una fila de nómina (comunes a la tabla y a la vista)."""
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
    # Cuenta contable. Sale de ConceptosNomina según el área (NOMCOSTO) y el
    # concepto; se asigna sola al crear la fila o al cambiarle el área.
    cuenta = models.CharField(max_length=30, blank=True, default='')
    # Centro de costo (CODCOSTO de ConceptosNomina). Igual que la cuenta, sale
    # del área (NOMCOSTO) y se asigna solo al crear la fila o al cambiarle el área.
    codcosto = models.CharField(max_length=30, blank=True, default='')

    # Antes: "salario_base" en sueldos/aprendiz y "base" en transporte/kyrovet.
    base = models.BigIntegerField(default=0)
    # Fracción de la persona que corresponde a esta fila. Al distribuir una
    # fila en varios centros/áreas cada copia guarda su porcentaje aquí, así
    # sigue recalculándose sola cuando cambian los parámetros.
    factor = models.FloatField(default=1)
    # Valores de origen (los que llegaron de ConceptosFijosYVariables) sobre
    # los que se aplica la fórmula. Permite recalcular sin acumular incrementos.
    historico = models.JSONField(default=dict, blank=True)

    origen = models.CharField(max_length=10, choices=ORIGENES, default=ORIGEN_MANUAL)
    # Identifica de qué fila de origen salió una fila calculada. Si alguien la
    # edita, la clave se conserva y el motor ya no genera otra para lo mismo.
    clave = models.CharField(max_length=255, blank=True, default='')
    # Centro y área de donde viene la fila antes de aplicar la distribución por
    # persona (DistribucionNomina). Permiten deshacer o cambiar el reparto.
    centro_origen = models.CharField(max_length=150, blank=True, default='')
    area_origen = models.CharField(max_length=150, blank=True, default='')
    # Conceptos calculados (slugs) que NO deben tener en cuenta esta fila.
    # Vacío = la fila actualiza todo lo que depende de su concepto.
    excluir_de = models.JSONField(default=list, blank=True)

    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    actualizado_por = models.CharField(max_length=150, blank=True, default='')

    class Meta:
        abstract = True


class PresupuestoNominaMes(_CamposLineaNomina):
    """TABLA presupuesto_nomina, guardada en VERTICAL.

    Cada fila de nómina (lo que la pantalla muestra como UNA fila con 12
    meses) son 12 registros de esta tabla, uno por mes:

        linea -> identifica la fila (es el "id" que ven la pantalla y el motor)
        fecha -> primer día del mes (AAAA-01-01 ... AAAA-12-01)
        valor -> valor de ese mes

    El total no se guarda: es la suma de los 12 valores.
    No se escribe directamente: el motor y la pantalla usan PresupuestoNomina
    (la vista horizontal) y la base de datos reparte los cambios aquí.
    """
    linea = models.BigIntegerField()
    fecha = models.DateField()
    valor = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_nomina'
        ordering = ['linea', 'fecha']
        indexes = [
            models.Index(fields=['tipo', 'origen'], name='nomina_tipo_origen_idx'),
            models.Index(fields=['tipo', 'cedula'], name='nomina_tipo_cedula_idx'),
            models.Index(fields=['linea', 'fecha'], name='nomina_linea_fecha_idx'),
            models.Index(fields=['fecha'], name='nomina_fecha_idx'),
        ]

    def __str__(self):
        return f'{self.tipo} · L{self.linea} · {self.fecha:%Y-%m} · {self.valor}'


class PresupuestoNomina(_CamposLineaNomina):
    """VISTA presupuesto_nomina_lineas: la tabla vertical vista en HORIZONTAL.

    Una fila por línea con una columna por mes y el total, que es como
    trabajan el motor de cálculo (nomina_motor.py) y la pantalla. Se puede
    leer, crear, actualizar y borrar como una tabla normal: unos disparadores
    de PostgreSQL (migración 0034) convierten cada operación en los 12
    registros de presupuesto_nomina.
    """
    # Año del presupuesto: automático (año siguiente al actual) en filas nuevas.
    anio = models.IntegerField(default=_anio_presupuesto)

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
    total = models.BigIntegerField(default=0)       # calculado (la vista lo suma)

    class Meta:
        managed = False
        db_table = 'presupuesto_nomina_lineas'
        ordering = ['tipo', 'id']

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
    # FECHAINGRE del Excel (llega como número de serie de Excel: 44167 = 31/12/2020)
    fecha_ingreso = models.DateField('fecha de ingreso', null=True, blank=True)
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
    # Confirmación de que el presupuesto de nómina está listo. Mientras no esté
    # confirmado no se puede subir a Cuenta 5 presupuestado.
    listo = models.BooleanField(default=False)
    listo_por = models.CharField(max_length=150, blank=True, default='')
    listo_en = models.DateTimeField(null=True, blank=True)

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

    `activa` permite desactivar el reparto sin borrarlo: mientras está
    desactivado las filas de la persona vuelven a su centro/área de origen, y
    al activarlo de nuevo se reparten otra vez con los mismos porcentajes.
    """
    cedula = models.CharField(max_length=20, db_index=True)
    centro = models.CharField(max_length=150, blank=True, default='')
    area = models.CharField(max_length=150)
    porcentaje = models.FloatField()
    activa = models.BooleanField(default=True)
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


class ArlCargoNomina(models.Model):
    """ARL elegida para un cargo en seguridad social de asistencia técnica
    (propia y convenio), donde se calcula por persona.

    Un mismo cargo puede venir con varios ARLPORC en el Excel: aquí se elige
    cuál usar. Se aplica a quien NO trae ARL propia en el Excel (la de la
    persona manda). `cargo` se guarda normalizado (sin tildes, en mayúsculas).
    `porcentaje` va como en el Excel (2.436 = 2,436 %).
    """
    cargo = models.CharField(max_length=150, unique=True)
    porcentaje = models.FloatField()
    actualizado = models.DateTimeField(auto_now=True)
    actualizado_por = models.CharField(max_length=150, blank=True, default='')

    class Meta:
        db_table = 'arl_cargo_nomina'
        ordering = ['cargo']

    def __str__(self):
        return f'{self.cargo}: {self.porcentaje}%'


class FocoSinComision(models.Model):
    """Personas que comisionan pero cuya bonificación foco NO se calcula con
    el promedio de comisiones, sino como la de quienes no comisionan."""
    cedula = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=150, blank=True, default='')
    actualizado = models.DateTimeField(auto_now=True)
    actualizado_por = models.CharField(max_length=150, blank=True, default='')

    class Meta:
        db_table = 'foco_sin_comision'
        ordering = ['nombre', 'cedula']

    def __str__(self):
        return f'{self.cedula} {self.nombre}'


class CorreccionPersonaNomina(models.Model):
    """Corrección de la cédula y/o el nombre de una persona.

    Los datos de origen (ConceptosNomina) traen la cédula y el nombre tal como
    vienen del Excel. Si en el presupuesto se corrigen (por ejemplo, en
    Sueldos), la corrección se aplica a TODOS los conceptos y se guarda aquí
    para que cada vez que se vuelva a cargar desde Conceptos la persona siga
    apareciendo con la cédula y el nombre corregidos.
    """
    cedula_origen = models.CharField('cédula en los datos de origen', max_length=20, unique=True)
    cedula = models.CharField('cédula correcta', max_length=20)
    nombre = models.CharField('nombre correcto', max_length=150, blank=True, default='')
    actualizado = models.DateTimeField(auto_now=True)
    actualizado_por = models.CharField(max_length=150, blank=True, default='')

    class Meta:
        db_table = 'correccion_persona_nomina'
        ordering = ['cedula_origen']
        verbose_name = 'corrección de persona (nómina)'
        verbose_name_plural = 'correcciones de personas (nómina)'

    def __str__(self):
        return f'{self.cedula_origen} → {self.cedula} {self.nombre}'


class FilaEliminadaNomina(models.Model):
    """Fila que vino de Conceptos y se eliminó en la pantalla del concepto.

    Al volver a cargar desde Conceptos (o recargar todo) esa fila NO se vuelve
    a crear. `llave` es la cédula de la persona o, en los conceptos sin cédula,
    'centro|área|concepto'. Deshacer la eliminación (o "Volver a cargar" en el
    tablero) borra el registro.
    """
    tipo = models.CharField(max_length=40)
    llave = models.CharField(max_length=400)
    nombre = models.CharField(max_length=150, blank=True, default='')
    eliminado = models.DateTimeField(auto_now=True)
    eliminado_por = models.CharField(max_length=150, blank=True, default='')

    class Meta:
        db_table = 'fila_eliminada_nomina'
        ordering = ['tipo', 'nombre', 'llave']
        constraints = [models.UniqueConstraint(fields=['tipo', 'llave'], name='fila_eliminada_nomina_unica')]
        verbose_name = 'fila eliminada (nómina)'
        verbose_name_plural = 'filas eliminadas (nómina)'

    def __str__(self):
        return f'{self.tipo} · {self.llave} {self.nombre}'


class FocoCargoInforme(models.Model):
    """Cargos cuya bonificación foco NO se calcula con la base general: se toma
    directamente el valor de cada persona en el informe (concepto E17 del Excel
    del año base), mes a mes, más el incremento de IPC."""
    cargo = models.CharField(max_length=150, unique=True)
    actualizado = models.DateTimeField(auto_now=True)
    actualizado_por = models.CharField(max_length=150, blank=True, default='')

    class Meta:
        db_table = 'foco_cargo_informe'
        ordering = ['cargo']

    def __str__(self):
        return self.cargo
