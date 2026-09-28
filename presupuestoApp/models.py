# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models
from django.utils import timezone

class Producto(models.Model):
    yyyy = models.IntegerField()
    mm = models.IntegerField()
    dd = models.IntegerField()
    fecha = models.CharField(max_length=50, null=True, blank=True)
    hora = models.CharField(max_length=20, null=True, blank=True)
    clase = models.CharField(max_length=50, null=True, blank=True)
    tipo = models.CharField(max_length=10, null=True, blank=True)
    numero = models.IntegerField(null=True, blank=True)
    ven_cob = models.CharField(max_length=50, null=True, blank=True)
    ven_cc = models.CharField(max_length=50, null=True, blank=True)
    ven_nom = models.CharField(max_length=255, null=True, blank=True)
    ccnit = models.CharField(max_length=50, null=True, blank=True)
    cliente_nom = models.CharField(max_length=255, null=True, blank=True)
    telef = models.CharField(max_length=50, null=True, blank=True)
    ciudad = models.CharField(max_length=50, null=True, blank=True)
    direccion = models.TextField(null=True, blank=True)
    cliente_grp = models.CharField(max_length=50, null=True, blank=True)
    cliente_grp_nom = models.CharField(max_length=255, null=True, blank=True)
    ciudad_nom = models.CharField(max_length=255, null=True, blank=True)
    cliente_creado = models.CharField(max_length=50, null=True, blank=True)
    zona = models.CharField(max_length=50, null=True, blank=True)
    zona_nom = models.CharField(max_length=255, null=True, blank=True)
    bod = models.CharField(max_length=50, null=True, blank=True)
    bod_nom = models.CharField(max_length=255, null=True, blank=True)
    indinv = models.CharField(max_length=10, null=True, blank=True)
    sku = models.CharField(max_length=50, null=True, blank=True)
    umd = models.CharField(max_length=50, null=True, blank=True)
    sku_nom = models.CharField(max_length=255, null=True, blank=True)
    marca = models.CharField(max_length=50, null=True, blank=True)
    marca_nom = models.CharField(max_length=255, null=True, blank=True)
    linea = models.CharField(max_length=50, null=True, blank=True)
    linea_nom = models.CharField(max_length=255, null=True, blank=True)
    categ1 = models.CharField(max_length=50, null=True, blank=True)
    categ1_nom = models.CharField(max_length=255, null=True, blank=True)
    categ2 = models.CharField(max_length=50, null=True, blank=True)
    categ2_nom = models.CharField(max_length=255, null=True, blank=True)
    proveedor = models.CharField(max_length=50, null=True, blank=True)
    proveedor_nom = models.CharField(max_length=255, null=True, blank=True)
    detalle = models.TextField(null=True, blank=True)
    listap = models.TextField(null=True, blank=True)
    metodo_pago = models.CharField(max_length=50, null=True, blank=True)
    iva_porc = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cantidad = models.IntegerField(null=True, blank=True)
    precio_b = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    precio_d = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    dcto1 = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    descuento = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    subtotal = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    iva = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    venta = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    costo_ult = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    costo_pro = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    costo_vta = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "productos"
        managed = False

    def __str__(self):
        return f"Producto {self.numero} - {self.sku_nom}"

class BdVentasComercial(models.Model):
    lapso = models.BigIntegerField(blank=True, null=True, db_index=True)
    centro_de_operacion = models.BigIntegerField(blank=True, null=True)
    nombre_centro_de_operacion = models.CharField(blank=True, null=True)
    linea_n1 = models.CharField(blank=True, null=True)
    nombre_linea_n1 = models.CharField(blank=True, null=True)
    cliente = models.CharField(blank=True, null=True)
    nombre_cliente = models.CharField(blank=True, null=True)
    clase_cliente = models.CharField(blank=True, null=True)
    nombre_clase_cliente = models.CharField(blank=True, null=True)
    valor_costo = models.FloatField(blank=True, null=True)
    valor_neto = models.FloatField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'bd_ventas_comercial'
        indexes = [
            models.Index(fields=['lapso', 'centro_de_operacion']),
        ]

class Plantillagastos2025(models.Model):
    centro_tra = models.CharField(db_column='CENTRO_TRA', blank=True, null=True)  # Field name made lowercase.
    nombre_cen = models.CharField(db_column='NOMBRE_CEN', blank=True, null=True)  # Field name made lowercase.
    codcosto = models.CharField(db_column='CODCOSTO', blank=True, null=True)  # Field name made lowercase.
    responsable = models.CharField(db_column='RESPONSABLE', blank=True, null=True)  # Field name made lowercase.
    cuenta = models.BigIntegerField(db_column='CUENTA', blank=True, null=True)  # Field name made lowercase.
    cuenta_mayor = models.CharField(db_column='CUENTA MAYOR', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    detalle_cuenta = models.CharField(db_column='DETALLE CUENTA', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    sede_distribucion = models.FloatField(db_column='SEDE  DISTRIBUCION', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    proveedor = models.CharField(blank=True, null=True)
    enero = models.BigIntegerField(blank=True, null=True)
    febrero = models.BigIntegerField(blank=True, null=True)
    marzo = models.BigIntegerField(blank=True, null=True)
    abril = models.FloatField(blank=True, null=True)
    mayo = models.BigIntegerField(blank=True, null=True)
    junio = models.BigIntegerField(blank=True, null=True)
    julio = models.BigIntegerField(blank=True, null=True)
    agosto = models.FloatField(blank=True, null=True)
    septiembre = models.FloatField(blank=True, null=True)
    octubre = models.FloatField(blank=True, null=True)
    noviembre = models.FloatField(blank=True, null=True)
    diciembre = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'plantillagastos2025'

class CuentasContables(models.Model):
    cuenta = models.BigIntegerField(blank=True, null=True)
    nom_cuenta = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cuentas_contables'
        
class ParametrosPresupuestos(models.Model):
    incremento_salarial = models.FloatField(blank=True, null=True)
    incremento_ipc = models.FloatField(blank=True, null=True)
    auxilio_transporte = models.FloatField(blank=True, null=True)
    cesantias = models.FloatField(blank=True, null=True)
    intereses_cesantias = models.FloatField(blank=True, null=True)
    prima = models.FloatField(blank=True, null=True)
    vacaciones = models.FloatField(blank=True, null=True)
    salario_minimo = models.FloatField(blank=True, null=True)
    incremento_comisiones = models.FloatField(blank=True, null=True)
    
    class Meta:
        db_table = 'parametros_presupuestos'

class Cuenta5(models.Model):
    mcncuenta = models.CharField(db_column='MCNCUENTA', blank=True, null=True)  # Field name made lowercase.
    mcnfecha = models.FloatField(db_column='MCNFECHA', blank=True, null=True)  # Field name made lowercase.
    mcntipodoc = models.CharField(db_column='MCNTIPODOC', blank=True, null=True)  # Field name made lowercase.
    mcnnumedoc = models.BigIntegerField(db_column='MCNNUMEDOC', blank=True, null=True)  # Field name made lowercase.
    mcnvincula = models.FloatField(db_column='MCNVINCULA', blank=True, null=True)  # Field name made lowercase.
    vinnombre = models.CharField(db_column='VINNOMBRE', blank=True, null=True)  # Field name made lowercase.
    mcnsucvin = models.CharField(db_column='MCNSUCVIN', blank=True, null=True)  # Field name made lowercase.
    saldoant = models.BigIntegerField(db_column='SALDOANT', blank=True, null=True)  # Field name made lowercase.
    mcnvaldebi = models.FloatField(db_column='MCNVALDEBI', blank=True, null=True)  # Field name made lowercase.
    mcnvalcred = models.FloatField(db_column='MCNVALCRED', blank=True, null=True)  # Field name made lowercase.
    saldonew = models.FloatField(db_column='SALDONEW', blank=True, null=True)  # Field name made lowercase.
    mcnsucurs = models.CharField(db_column='MCNSUCURS', blank=True, null=True)  # Field name made lowercase.
    mcnccosto = models.CharField(db_column='MCNCCOSTO', blank=True, null=True)  # Field name made lowercase.
    mcndestino = models.CharField(db_column='MCNDESTINO', blank=True, null=True)  # Field name made lowercase.
    mcndetalle = models.CharField(db_column='MCNDETALLE', blank=True, null=True)  # Field name made lowercase.
    mcnzona = models.CharField(db_column='MCNZONA', blank=True, null=True)  # Field name made lowercase.
    cconombre = models.CharField(db_column='CCONOMBRE', blank=True, null=True)  # Field name made lowercase.
    dnonombre = models.CharField(db_column='DNONOMBRE', blank=True, null=True)  # Field name made lowercase.
    zonnombre = models.CharField(db_column='ZONNOMBRE', blank=True, null=True)  # Field name made lowercase.
    mcnempresa = models.CharField(db_column='MCNEMPRESA', blank=True, null=True)  # Field name made lowercase.
    mcnclase = models.CharField(db_column='MCNCLASE', blank=True, null=True)  # Field name made lowercase.
    mcnvinkey = models.CharField(db_column='MCNVINKEY', blank=True, null=True)  # Field name made lowercase.
    tpreg = models.BigIntegerField(db_column='TPREG', blank=True, null=True)  # Field name made lowercase.
    ctanombre = models.CharField(db_column='CTANOMBRE', blank=True, null=True)  # Field name made lowercase.
    docdetalle = models.CharField(db_column='DOCDETALLE', blank=True, null=True)  # Field name made lowercase.
    infdetalle = models.CharField(db_column='INFDETALLE', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'cuenta5'

#----------------------------------------------------------------------------
# TABLAS PARA PRESUPUESTO COMERCIAL----------------------------------------
class PresupuestoComercial(models.Model):
    linea = models.CharField(max_length=100)
    year = models.IntegerField()
    nombre_centro_de_operacion = models.CharField(max_length=100, null=True, blank=True)
    nombre_clase_cliente = models.CharField(max_length=100, null=True, blank=True)
    ventas = models.BigIntegerField(default=0)
    costos = models.BigIntegerField(default=0)
    r2_ventas = models.FloatField(default=0)
    r2_costos = models.FloatField(default=0)
    variacion_porcentual_ventas = models.FloatField(default=0)
    variacion_porcentual_costos = models.FloatField(default=0)
    variacion_valor_ventas = models.BigIntegerField(default=0)
    variacion_valor_costos = models.BigIntegerField(default=0)
    variacion_mes_ventas = models.BigIntegerField(default=0)
    variacion_mes_costos = models.BigIntegerField(default=0)
    variacion_precios_ventas = models.BigIntegerField(default=0)
    variacion_precios_costos = models.BigIntegerField(default=0)
    crecimiento_comercial_ventas = models.BigIntegerField(default=0)
    crecimiento_comercial_costos = models.BigIntegerField(default=0)
    crecimiento_comercial_mes_ventas = models.BigIntegerField(default=0)
    crecimiento_comercial_mes_costos = models.BigIntegerField(default=0)
    crecimiento_ventas = models.FloatField(default=0)
    proyeccion_ventas = models.BigIntegerField(default=0)
    crecimiento_costos = models.FloatField(default=0)
    proyeccion_costos = models.BigIntegerField(default=0)
    utilidad_porcentual = models.FloatField(default=0)
    utilidad_valor = models.BigIntegerField(default=0)
    utilidad_porcentual_actual = models.FloatField(default=0)
    utilidad_valor_actual = models.BigIntegerField(default=0)
    variacion_proyectada_porcentual = models.FloatField(default=0)
    variacion_proyectada_valor = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_comercial'
    
class PresupuestoGeneralVentas(models.Model):
    year = models.IntegerField()
    mes = models.IntegerField()
    total = models.BigIntegerField(default=0)
    r2 = models.FloatField(default=0)
    total_year = models.BigIntegerField(default=0)
    total_year_costos = models.BigIntegerField(default=0)
    variacion_pct = models.FloatField(default=0)
    variacion_valor = models.BigIntegerField(default=0)
    utilidad_pct = models.FloatField(default=0)
    utilidad_valor = models.BigIntegerField(default=0)
    total_proyectado = models.BigIntegerField(default=0)
    
    class Meta:
        db_table = 'presupuesto_general_ventas'
        
class PresupuestoGeneralCostos(models.Model):
    year = models.IntegerField()
    mes = models.IntegerField()
    total = models.BigIntegerField(default=0)
    r2 = models.FloatField(default=0)
    total_year = models.BigIntegerField(default=0)
    variacion_pct = models.FloatField(default=0)
    variacion_valor = models.BigIntegerField(default=0)
    utilidad_pct = models.FloatField(default=0)
    utilidad_valor = models.BigIntegerField(default=0)
    
    class Meta:
        db_table = 'presupuesto_general_costos'
        
class PresupuestoCentroOperacionVentas(models.Model):
    year = models.IntegerField()
    mes = models.IntegerField()
    nombre_centro_operacion = models.CharField(max_length=100, null=True, blank=True)
    total = models.BigIntegerField(default=0)
    r2 = models.FloatField(default=0)
    total_year = models.BigIntegerField(default=0)
    total_year_costos = models.BigIntegerField(default=0)
    variacion_pct = models.FloatField(default=0)
    variacion_valor = models.BigIntegerField(default=0)
    utilidad_pct = models.FloatField(default=0)
    utilidad_valor = models.BigIntegerField(default=0)
    total_proyectado = models.BigIntegerField(default=0)
    
    class Meta:
        db_table = 'presupuesto_centro_operacion_ventas'

class PresupuestoCentroOperacionCostos(models.Model):
    year = models.IntegerField()
    mes = models.IntegerField()
    nombre_centro_operacion = models.CharField(max_length=100, null=True, blank=True)
    total = models.BigIntegerField(default=0)
    r2 = models.FloatField(default=0)
    total_year = models.BigIntegerField(default=0)
    variacion_pct = models.FloatField(default=0)
    variacion_valor = models.BigIntegerField(default=0)
    utilidad_pct = models.FloatField(default=0)
    utilidad_valor = models.BigIntegerField(default=0)
    
    class Meta:
        db_table = 'presupuesto_centro_operacion_costos'
        
class PresupuestoCentroSegmentoVentas(models.Model):
    year = models.IntegerField()
    mes = models.IntegerField()
    nombre_centro_operacion = models.CharField(max_length=100, null=True, blank=True)
    segmento = models.CharField(max_length=100)
    total = models.BigIntegerField(default=0)
    r2 = models.FloatField(default=0)
    total_year = models.BigIntegerField(default=0)
    total_year_costos = models.BigIntegerField(default=0)
    variacion_pct = models.FloatField(default=0)
    variacion_valor = models.BigIntegerField(default=0)
    utilidad_pct = models.FloatField(default=0)
    utilidad_valor = models.BigIntegerField(default=0)
    total_proyectado = models.BigIntegerField(default=0)
    
    class Meta:
        db_table = 'presupuesto_centro_segmento_ventas'
        
class PresupuestoCentroSegmentoCostos(models.Model):
    year = models.IntegerField()
    mes = models.IntegerField()
    nombre_centro_operacion = models.CharField(max_length=100, null=True, blank=True)
    segmento = models.CharField(max_length=100)
    total = models.BigIntegerField(default=0)
    r2 = models.FloatField(default=0)
    total_year = models.BigIntegerField(default=0)
    variacion_pct = models.FloatField(default=0)
    variacion_valor = models.BigIntegerField(default=0)
    utilidad_pct = models.FloatField(default=0)
    utilidad_valor = models.BigIntegerField(default=0)
    
    class Meta:
        db_table = 'presupuesto_centro_segmento_costos'
        
class PresupuestoCentroSegLineaVentas(models.Model):
    year = models.IntegerField()
    mes = models.IntegerField()
    nombre_centro_operacion = models.CharField(max_length=100, null=True, blank=True)
    segmento = models.CharField(max_length=100)
    linea = models.CharField(max_length=100)
    total = models.BigIntegerField(default=0)
    r2 = models.FloatField(default=0)
    total_year = models.BigIntegerField(default=0)
    total_year_costos = models.BigIntegerField(default=0)
    variacion_pct = models.FloatField(default=0)
    variacion_valor = models.BigIntegerField(default=0)
    utilidad_pct = models.FloatField(default=0)
    utilidad_valor = models.BigIntegerField(default=0)
    total_proyectado = models.BigIntegerField(default=0)
    
    class Meta:
        db_table = 'presupuesto_centro_seg_linea_ventas'

class PresupuestoCentroSegLineaCostos(models.Model):
    year = models.IntegerField()
    mes = models.IntegerField()
    nombre_centro_operacion = models.CharField(max_length=100, null=True, blank=True)
    segmento = models.CharField(max_length=100)
    linea = models.CharField(max_length=100)
    total = models.BigIntegerField(default=0)
    r2 = models.FloatField(default=0)
    total_year = models.BigIntegerField(default=0)
    variacion_pct = models.FloatField(default=0)
    variacion_valor = models.BigIntegerField(default=0)
    utilidad_pct = models.FloatField(default=0)
    utilidad_valor = models.BigIntegerField(default=0)
    
    class Meta:
        db_table = 'presupuesto_centro_seg_linea_costos'

  
#-------Cuenta 5 base-------------
class Cuenta5Base(models.Model):
    mcncuenta = models.CharField(db_column='MCNCUENTA', blank=True, null=True)  # Field name made lowercase.
    mcnfecha = models.FloatField(db_column='MCNFECHA', blank=True, null=True)  # Field name made lowercase.
    mcntipodoc = models.CharField(db_column='MCNTIPODOC', blank=True, null=True)  # Field name made lowercase.
    mcnnumedoc = models.BigIntegerField(db_column='MCNNUMEDOC', blank=True, null=True)  # Field name made lowercase.
    mcnvincula = models.CharField(db_column='MCNVINCULA', blank=True, null=True)  # Field name made lowercase.
    vinnombre = models.CharField(db_column='VINNOMBRE', blank=True, null=True)  # Field name made lowercase.
    mcnsucvin = models.CharField(db_column='MCNSUCVIN', blank=True, null=True)  # Field name made lowercase.
    saldoant = models.BigIntegerField(db_column='SALDOANT', blank=True, null=True)  # Field name made lowercase.
    mcnvaldebi = models.FloatField(db_column='MCNVALDEBI', blank=True, null=True)  # Field name made lowercase.
    mcnvalcred = models.FloatField(db_column='MCNVALCRED', blank=True, null=True)  # Field name made lowercase.
    saldonew = models.FloatField(db_column='SALDONEW', blank=True, null=True)  # Field name made lowercase.
    mcnsucurs = models.CharField(db_column='MCNSUCURS', blank=True, null=True)  # Field name made lowercase.
    mcnccosto = models.CharField(db_column='MCNCCOSTO', blank=True, null=True)  # Field name made lowercase.
    mcndestino = models.CharField(db_column='MCNDESTINO', blank=True, null=True)  # Field name made lowercase.
    mcndetalle = models.CharField(db_column='MCNDETALLE', blank=True, null=True)  # Field name made lowercase.
    mcnzona = models.CharField(db_column='MCNZONA', blank=True, null=True)  # Field name made lowercase.
    cconombre = models.CharField(db_column='CCONOMBRE', blank=True, null=True)  # Field name made lowercase.
    dnonombre = models.CharField(db_column='DNONOMBRE', blank=True, null=True)  # Field name made lowercase.
    zonnombre = models.CharField(db_column='ZONNOMBRE', blank=True, null=True)  # Field name made lowercase.
    mcnempresa = models.CharField(db_column='MCNEMPRESA', blank=True, null=True)  # Field name made lowercase.
    mcnclase = models.CharField(db_column='MCNCLASE', blank=True, null=True)  # Field name made lowercase.
    mcnvinkey = models.CharField(db_column='MCNVINKEY', blank=True, null=True)  # Field name made lowercase.
    tpreg = models.BigIntegerField(db_column='TPREG', blank=True, null=True)  # Field name made lowercase.
    ctanombre = models.CharField(db_column='CTANOMBRE', blank=True, null=True)  # Field name made lowercase.
    docdetalle = models.CharField(db_column='DOCDETALLE', blank=True, null=True)  # Field name made lowercase.
    infdetalle = models.CharField(db_column='INFDETALLE', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        db_table = 'cuenta_5_base'

class ConsolidadoTotalBase(models.Model):
    mcncuenta = models.CharField(blank=True, null=True)
    mcnccosto = models.CharField(blank=True, null=True)
    ctanombre = models.CharField(blank=True, null=True)
    mcnfecha = models.DateField(blank=True, null=True)
    valor = models.BigIntegerField(blank=True, null=True)
    total_anual = models.BigIntegerField(blank=True, null=True)
    sede = models.CharField(blank=True, null=True)
    origen = models.CharField(blank=True, null=True)
    
    class Meta:
        db_table = 'consolidado_total_base'
        
#-------Cuenta 5 presupuestado-------------
class Cuenta5Presupuestado(models.Model):
    mcncuenta = models.CharField(db_column='MCNCUENTA', blank=True, null=True)  # Field name made lowercase.
    mcnfecha = models.FloatField(db_column='MCNFECHA', blank=True, null=True)  # Field name made lowercase.
    mcntipodoc = models.CharField(db_column='MCNTIPODOC', blank=True, null=True)  # Field name made lowercase.
    mcnnumedoc = models.BigIntegerField(db_column='MCNNUMEDOC', blank=True, null=True)  # Field name made lowercase.
    mcnvincula = models.CharField(db_column='MCNVINCULA', blank=True, null=True)  # Field name made lowercase.
    vinnombre = models.CharField(db_column='VINNOMBRE', blank=True, null=True)  # Field name made lowercase.
    mcnsucvin = models.CharField(db_column='MCNSUCVIN', blank=True, null=True)  # Field name made lowercase.
    saldoant = models.BigIntegerField(db_column='SALDOANT', blank=True, null=True)  # Field name made lowercase.
    mcnvaldebi = models.FloatField(db_column='MCNVALDEBI', blank=True, null=True)  # Field name made lowercase.
    mcnvalcred = models.FloatField(db_column='MCNVALCRED', blank=True, null=True)  # Field name made lowercase.
    saldonew = models.FloatField(db_column='SALDONEW', blank=True, null=True)  # Field name made lowercase.
    mcnsucurs = models.CharField(db_column='MCNSUCURS', blank=True, null=True)  # Field name made lowercase.
    mcnccosto = models.CharField(db_column='MCNCCOSTO', blank=True, null=True)  # Field name made lowercase.
    mcndestino = models.CharField(db_column='MCNDESTINO', blank=True, null=True)  # Field name made lowercase.
    mcndetalle = models.CharField(db_column='MCNDETALLE', blank=True, null=True)  # Field name made lowercase.
    mcnzona = models.CharField(db_column='MCNZONA', blank=True, null=True)  # Field name made lowercase.
    cconombre = models.CharField(db_column='CCONOMBRE', blank=True, null=True)  # Field name made lowercase.
    dnonombre = models.CharField(db_column='DNONOMBRE', blank=True, null=True)  # Field name made lowercase.
    zonnombre = models.CharField(db_column='ZONNOMBRE', blank=True, null=True)  # Field name made lowercase.
    mcnempresa = models.CharField(db_column='MCNEMPRESA', blank=True, null=True)  # Field name made lowercase.
    mcnclase = models.CharField(db_column='MCNCLASE', blank=True, null=True)  # Field name made lowercase.
    mcnvinkey = models.CharField(db_column='MCNVINKEY', blank=True, null=True)  # Field name made lowercase.
    tpreg = models.BigIntegerField(db_column='TPREG', blank=True, null=True)  # Field name made lowercase.
    ctanombre = models.CharField(db_column='CTANOMBRE', blank=True, null=True)  # Field name made lowercase.
    docdetalle = models.CharField(db_column='DOCDETALLE', blank=True, null=True)  # Field name made lowercase.
    infdetalle = models.CharField(db_column='INFDETALLE', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        db_table = 'cuenta_5_presupuestado'

#-------Cuenta 4 base-------------
class Cuenta4Base(models.Model):
    mcncuenta = models.CharField(db_column='MCNCUENTA', blank=True, null=True)  # Field name made lowercase.
    mcnfecha = models.FloatField(db_column='MCNFECHA', blank=True, null=True)  # Field name made lowercase.
    mcntipodoc = models.CharField(db_column='MCNTIPODOC', blank=True, null=True)  # Field name made lowercase.
    mcnnumedoc = models.BigIntegerField(db_column='MCNNUMEDOC', blank=True, null=True)  # Field name made lowercase.
    mcnvincula = models.CharField(db_column='MCNVINCULA', blank=True, null=True)  # Field name made lowercase.
    vinnombre = models.CharField(db_column='VINNOMBRE', blank=True, null=True)  # Field name made lowercase.
    mcnsucvin = models.CharField(db_column='MCNSUCVIN', blank=True, null=True)  # Field name made lowercase.
    saldoant = models.BigIntegerField(db_column='SALDOANT', blank=True, null=True)  # Field name made lowercase.
    mcnvaldebi = models.FloatField(db_column='MCNVALDEBI', blank=True, null=True)  # Field name made lowercase.
    mcnvalcred = models.FloatField(db_column='MCNVALCRED', blank=True, null=True)  # Field name made lowercase.
    saldonew = models.FloatField(db_column='SALDONEW', blank=True, null=True)  # Field name made lowercase.
    mcnsucurs = models.CharField(db_column='MCNSUCURS', blank=True, null=True)  # Field name made lowercase.
    mcnccosto = models.CharField(db_column='MCNCCOSTO', blank=True, null=True)  # Field name made lowercase.
    mcndestino = models.CharField(db_column='MCNDESTINO', blank=True, null=True)  # Field name made lowercase.
    mcndetalle = models.CharField(db_column='MCNDETALLE', blank=True, null=True)  # Field name made lowercase.
    mcnzona = models.CharField(db_column='MCNZONA', blank=True, null=True)  # Field name made lowercase.
    cconombre = models.CharField(db_column='CCONOMBRE', blank=True, null=True)  # Field name made lowercase.
    dnonombre = models.CharField(db_column='DNONOMBRE', blank=True, null=True)  # Field name made lowercase.
    zonnombre = models.CharField(db_column='ZONNOMBRE', blank=True, null=True)  # Field name made lowercase.
    mcnempresa = models.CharField(db_column='MCNEMPRESA', blank=True, null=True)  # Field name made lowercase.
    mcnclase = models.CharField(db_column='MCNCLASE', blank=True, null=True)  # Field name made lowercase.
    mcnvinkey = models.CharField(db_column='MCNVINKEY', blank=True, null=True)  # Field name made lowercase.
    tpreg = models.BigIntegerField(db_column='TPREG', blank=True, null=True)  # Field name made lowercase.
    ctanombre = models.CharField(db_column='CTANOMBRE', blank=True, null=True)  # Field name made lowercase.
    docdetalle = models.CharField(db_column='DOCDETALLE', blank=True, null=True)  # Field name made lowercase.
    infdetalle = models.CharField(db_column='INFDETALLE', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        db_table = 'cuenta_4_base'
        
#-------Cuenta 4 presupuestado-------------
class Cuenta4Presupuestado(models.Model):
    mcncuenta = models.CharField(db_column='MCNCUENTA', blank=True, null=True)  # Field name made lowercase.
    mcnfecha = models.FloatField(db_column='MCNFECHA', blank=True, null=True)  # Field name made lowercase.
    mcntipodoc = models.CharField(db_column='MCNTIPODOC', blank=True, null=True)  # Field name made lowercase.
    mcnnumedoc = models.BigIntegerField(db_column='MCNNUMEDOC', blank=True, null=True)  # Field name made lowercase.
    mcnvincula = models.CharField(db_column='MCNVINCULA', blank=True, null=True)  # Field name made lowercase.
    vinnombre = models.CharField(db_column='VINNOMBRE', blank=True, null=True)  # Field name made lowercase.
    mcnsucvin = models.CharField(db_column='MCNSUCVIN', blank=True, null=True)  # Field name made lowercase.
    saldoant = models.BigIntegerField(db_column='SALDOANT', blank=True, null=True)  # Field name made lowercase.
    mcnvaldebi = models.FloatField(db_column='MCNVALDEBI', blank=True, null=True)  # Field name made lowercase.
    mcnvalcred = models.FloatField(db_column='MCNVALCRED', blank=True, null=True)  # Field name made lowercase.
    saldonew = models.FloatField(db_column='SALDONEW', blank=True, null=True)  # Field name made lowercase.
    mcnsucurs = models.CharField(db_column='MCNSUCURS', blank=True, null=True)  # Field name made lowercase.
    mcnccosto = models.CharField(db_column='MCNCCOSTO', blank=True, null=True)  # Field name made lowercase.
    mcndestino = models.CharField(db_column='MCNDESTINO', blank=True, null=True)  # Field name made lowercase.
    mcndetalle = models.CharField(db_column='MCNDETALLE', blank=True, null=True)  # Field name made lowercase.
    mcnzona = models.CharField(db_column='MCNZONA', blank=True, null=True)  # Field name made lowercase.
    cconombre = models.CharField(db_column='CCONOMBRE', blank=True, null=True)  # Field name made lowercase.
    dnonombre = models.CharField(db_column='DNONOMBRE', blank=True, null=True)  # Field name made lowercase.
    zonnombre = models.CharField(db_column='ZONNOMBRE', blank=True, null=True)  # Field name made lowercase.
    mcnempresa = models.CharField(db_column='MCNEMPRESA', blank=True, null=True)  # Field name made lowercase.
    mcnclase = models.CharField(db_column='MCNCLASE', blank=True, null=True)  # Field name made lowercase.
    mcnvinkey = models.CharField(db_column='MCNVINKEY', blank=True, null=True)  # Field name made lowercase.
    tpreg = models.BigIntegerField(db_column='TPREG', blank=True, null=True)  # Field name made lowercase.
    ctanombre = models.CharField(db_column='CTANOMBRE', blank=True, null=True)  # Field name made lowercase.
    docdetalle = models.CharField(db_column='DOCDETALLE', blank=True, null=True)  # Field name made lowercase.
    infdetalle = models.CharField(db_column='INFDETALLE', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        db_table = 'cuenta_4_presupuestado'

# ---------------------------------------------------------------------------
# Un comentario por (sede, fila). "fila_key" identifica la fila:
#   - Para una cuenta normal: el código de cuenta (mcncuenta), ej. "541001"
#   - Para una fila calculada (VENTAS NETAS, Margen Bruto, etc.): el
#     identificador interno que ya usa el JS del comparativo (tipoTotal),
#     ej. "VentasNetas", "54", "MargenBruto", "PctUtilidadOperacional", etc.
# Esto permite comentar tanto cuentas puntuales como los totales calculados.

class ComentarioComparativo(models.Model):
    sede = models.CharField(max_length=30)          # tulua | buga | cartago | cali | consolidado
    fila_key = models.CharField(max_length=50)       # código de cuenta o identificador de total
    mcncuenta = models.CharField(max_length=50, blank=True, null=True)
    ctanombre = models.CharField(max_length=255, blank=True, null=True)
    comentario = models.TextField(blank=True, null=True)
    actualizado_por = models.CharField(max_length=150, blank=True, null=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'comparativo_comentarios'
        unique_together = ('sede', 'fila_key')

    def __str__(self):
        return f"{self.sede} / {self.fila_key}"

# tabla para definir el orden y nombre personalizado de las cuentas en las tablas de Consolidado / Presupuestado / Comparativo
class OrdenCuenta(models.Model):
    """Orden y nombre personalizado de las cuentas en las tablas
    de Consolidado / Presupuestado / Comparativo."""
    mcncuenta     = models.CharField(max_length=60, unique=True)
    ctanombre     = models.CharField(max_length=255, blank=True, default='')
    orden         = models.PositiveIntegerField(default=0, db_index=True)
    visible_total = models.BooleanField(default=True)   # vista "Total Base" / consolidado
    visible_sede  = models.BooleanField(default=False)  # vistas por sede

    class Meta:
        ordering = ['orden', 'id']
        verbose_name = 'Orden de cuenta'
        verbose_name_plural = 'Orden de cuentas'

    def __str__(self):
        return f'{self.orden:05d} · {self.mcncuenta} — {self.ctanombre}'


# ── Nómina: tabla única ────────────────────────────────────────────────
from .models_nomina import PresupuestoNomina  # noqa: E402,F401
from .models_presupuesto import PresupuestoArea  # noqa