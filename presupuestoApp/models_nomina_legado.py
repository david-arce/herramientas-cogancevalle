"""
Modelos ANTIGUOS de nómina (34 tablas). Solo existen para que Django no borre
las tablas antes de copiar los datos con:

    python manage.py migrar_nomina_tabla_unica

Después de migrar: borrar este archivo, quitar su import al final de
models.py, ejecutar makemigrations + migrate (eso elimina las tablas).
"""
from django.db import models
from django.utils import timezone

class PresupuestoSueldos(models.Model):
    cedula = models.IntegerField()
    nombre = models.CharField(max_length=255)
    centro = models.CharField(max_length=255)
    area = models.CharField(max_length=255)
    cargo = models.CharField(max_length=255)
    concepto = models.CharField(max_length=255)
    salario_base = models.IntegerField()
    enero = models.IntegerField()
    febrero = models.IntegerField()
    marzo = models.IntegerField()
    abril = models.IntegerField()
    mayo = models.IntegerField()
    junio = models.IntegerField()
    julio = models.IntegerField()
    agosto = models.IntegerField()
    septiembre = models.IntegerField()
    octubre = models.IntegerField()
    noviembre = models.IntegerField()
    diciembre = models.IntegerField()
    total = models.BigIntegerField(default=0)
    # 🔹 Campos de control
    version = models.IntegerField(default=1)
    fecha_carga = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'presupuesto_sueldos'


class PresupuestoSueldosAux(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50, default="SALARIO")
    salario_base = models.IntegerField(default=0)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_sueldos_auxiliar'


class PresupuestoComisiones(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50, default="COMISIONES")
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_comisiones'


class PresupuestoComisionesAux(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50, default="COMISIONES")
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_comisiones_auxiliar'


class PresupuestoHorasExtra(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_horas_extra'


class PresupuestoHorasExtraAux(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50, default="HORAS EXTRA")
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_horas_extra_auxiliar'


class PresupuestoAuxilioTransporte(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50)
    base = models.IntegerField(default=0)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_auxilio_transporte'


class PresupuestoAuxilioTransporteAux(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50, default="AUXILIO TRANSPORTE")
    base = models.IntegerField(default=0)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_auxilio_transporte_auxiliar'


class PresupuestoMediosTransporte(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50)
    base = models.IntegerField(default=0)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_medios_transporte'


class PresupuestoMediosTransporteAux(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50, default="MEDIOS DE TRANSPORTE")
    base = models.IntegerField(default=0)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_medios_transporte_auxiliar'


class PresupuestoAyudaTransporte(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50)
    base = models.IntegerField(default=0)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_ayuda_transporte'


class PresupuestoAyudaTransporteAux(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50, default="AYUDA TRANSPORTE")
    base = models.IntegerField(default=0)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_ayuda_transporte_auxiliar'


class PresupuestoCesantias(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_cesantias'


class PresupuestoCesantiasAux(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50, default="CESANTIAS")
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_cesantias_auxiliar'


class PresupuestoInteresesCesantias(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_intereses_cesantias'


class PresupuestoInteresesCesantiasAux(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50, default="INTERESES CESANTIAS")
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_intereses_cesantias_auxiliar'


class PresupuestoPrima(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_prima'


class PresupuestoPrimaAux(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50, default="PRIMA")
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_prima_auxiliar'


class PresupuestoVacaciones(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_vacaciones'


class PresupuestoVacacionesAux(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50, default="VACACIONES")
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_vacaciones_auxiliar'


class PresupuestoBonificaciones(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_bonificaciones'


class PresupuestoBonificacionesAux(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50, default="BONIFICACIONES")
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_bonificaciones_auxiliar'


class PresupuestoSeguridadSocial(models.Model):
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_seguridad_social'


class PresupuestoSeguridadSocialAux(models.Model):
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50, default="SEGURIDAD SOCIAL")
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_seguridad_social_auxiliar'


class PresupuestoAprendiz(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50)
    salario_base = models.IntegerField(default=0)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_aprendiz'


class PresupuestoAprendizAux(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50, default="APRENDIZ")
    salario_base = models.IntegerField(default=0)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_aprendiz_auxiliar'


class PresupuestoBolsaConsumibles(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_bolsa_consumibles'


class PresupuestoBolsaConsumiblesAux(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_bolsa_consumibles_auxiliar'


class PresupuestoAuxilioTBCKIT(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_auxilio_tbckit'


class PresupuestoAuxilioTCBKITAux(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_auxilio_tbckit_auxiliar'


class PresupuestoBonificacionesFoco(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_bonificaciones_foco'


class PresupuestoBonificacionesFocoAux(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50, default="BONIFICACIONES FOCO")
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_bonificaciones_foco_auxiliar'


class PresupuestoAuxilioEducacion(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_auxilio_educacion'


class PresupuestoAuxilioEducacionAux(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50, default="AUXILIO EDUCACION")
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_auxilio_educacion_auxiliar'


class PresupuestoBonosKyrovet(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50)
    base = models.IntegerField(default=0)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_bonos_kyrovet'


class PresupuestoBonosKyrovetAux(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50, default="BONOS CANASTA KYROVET")
    base = models.IntegerField(default=0)
    enero = models.IntegerField(default=0)
    febrero = models.IntegerField(default=0)
    marzo = models.IntegerField(default=0)
    abril = models.IntegerField(default=0)
    mayo = models.IntegerField(default=0)
    junio = models.IntegerField(default=0)
    julio = models.IntegerField(default=0)
    agosto = models.IntegerField(default=0)
    septiembre = models.IntegerField(default=0)
    octubre = models.IntegerField(default=0)
    noviembre = models.IntegerField(default=0)
    diciembre = models.IntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_bonos_kyrovet_auxiliar'


