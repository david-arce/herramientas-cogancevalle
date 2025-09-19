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

class BdVentas2020(models.Model):
    lapso = models.BigIntegerField(db_column='Lapso', blank=True, null=True)  # Field name made lowercase.
    centro_de_operacion = models.BigIntegerField(db_column='Centro de Operacion', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_centro_de_operacion = models.CharField(db_column='Nombre Centro de Operacion', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    criterio_item_1 = models.FloatField(db_column='Criterio Item 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_criterio_item_1 = models.CharField(db_column='Nombre Criterio Item 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    item = models.BigIntegerField(db_column='Item', blank=True, null=True)  # Field name made lowercase.
    nombre_item = models.CharField(db_column='Nombre Item', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    linea_n1 = models.BigIntegerField(db_column='Linea N1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_linea_n1 = models.CharField(db_column='Nombre Linea N1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cliente = models.CharField(db_column='Cliente', blank=True, null=True)  # Field name made lowercase.
    nombre_cliente = models.CharField(db_column='Nombre Cliente', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    clase_cliente = models.BigIntegerField(db_column='Clase Cliente', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_clase_cliente = models.CharField(db_column='Nombre Clase Cliente', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cantidad_1 = models.FloatField(db_column='Cantidad 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    valor_costo = models.FloatField(db_column='Valor Costo', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    valor_neto = models.BigIntegerField(db_column='Valor Neto', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.

    class Meta:
        managed = False
        db_table = 'bd_ventas_2020'

class BdVentas2021(models.Model):
    lapso = models.BigIntegerField(db_column='Lapso', blank=True, null=True)  # Field name made lowercase.
    centro_de_operacion = models.BigIntegerField(db_column='Centro de Operacion', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_centro_de_operacion = models.CharField(db_column='Nombre Centro de Operacion', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    criterio_item_1 = models.FloatField(db_column='Criterio Item 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_criterio_item_1 = models.CharField(db_column='Nombre Criterio Item 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    item = models.BigIntegerField(db_column='Item', blank=True, null=True)  # Field name made lowercase.
    nombre_item = models.CharField(db_column='Nombre Item', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    linea_n1 = models.BigIntegerField(db_column='Linea N1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_linea_n1 = models.CharField(db_column='Nombre Linea N1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cliente = models.CharField(db_column='Cliente', blank=True, null=True)  # Field name made lowercase.
    nombre_cliente = models.CharField(db_column='Nombre Cliente', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    clase_cliente = models.BigIntegerField(db_column='Clase Cliente', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_clase_cliente = models.CharField(db_column='Nombre Clase Cliente', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cantidad_1 = models.FloatField(db_column='Cantidad 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    valor_costo = models.FloatField(db_column='Valor Costo', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    valor_neto = models.BigIntegerField(db_column='Valor Neto', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.

    class Meta:
        managed = False
        db_table = 'bd_ventas_2021'

class BdVentas2022(models.Model):
    lapso = models.BigIntegerField(db_column='Lapso', blank=True, null=True)  # Field name made lowercase.
    centro_de_operacion = models.BigIntegerField(db_column='Centro de Operacion', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_centro_de_operacion = models.CharField(db_column='Nombre Centro de Operacion', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    criterio_item_1 = models.FloatField(db_column='Criterio Item 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_criterio_item_1 = models.CharField(db_column='Nombre Criterio Item 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    item = models.BigIntegerField(db_column='Item', blank=True, null=True)  # Field name made lowercase.
    nombre_item = models.CharField(db_column='Nombre Item', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    linea_n1 = models.BigIntegerField(db_column='Linea N1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_linea_n1 = models.CharField(db_column='Nombre Linea N1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cliente = models.CharField(db_column='Cliente', blank=True, null=True)  # Field name made lowercase.
    nombre_cliente = models.CharField(db_column='Nombre Cliente', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    clase_cliente = models.BigIntegerField(db_column='Clase Cliente', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_clase_cliente = models.CharField(db_column='Nombre Clase Cliente', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cantidad_1 = models.FloatField(db_column='Cantidad 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    valor_costo = models.FloatField(db_column='Valor Costo', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    valor_neto = models.BigIntegerField(db_column='Valor Neto', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.

    class Meta:
        managed = False
        db_table = 'bd_ventas_2022'
 
class BdVentas2023(models.Model):
    lapso = models.BigIntegerField(db_column='Lapso', blank=True, null=True)  # Field name made lowercase.
    centro_de_operacion = models.BigIntegerField(db_column='Centro de Operacion', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_centro_de_operacion = models.CharField(db_column='Nombre Centro de Operacion', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    criterio_item_1 = models.FloatField(db_column='Criterio Item 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_criterio_item_1 = models.CharField(db_column='Nombre Criterio Item 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    item = models.BigIntegerField(db_column='Item', blank=True, null=True)  # Field name made lowercase.
    nombre_item = models.CharField(db_column='Nombre Item', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    linea_n1 = models.BigIntegerField(db_column='Linea N1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_linea_n1 = models.CharField(db_column='Nombre Linea N1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cliente = models.CharField(db_column='Cliente', blank=True, null=True)  # Field name made lowercase.
    nombre_cliente = models.CharField(db_column='Nombre Cliente', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    clase_cliente = models.BigIntegerField(db_column='Clase Cliente', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_clase_cliente = models.CharField(db_column='Nombre Clase Cliente', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cantidad_1 = models.FloatField(db_column='Cantidad 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    valor_costo = models.FloatField(db_column='Valor Costo', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    valor_neto = models.BigIntegerField(db_column='Valor Neto', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.

    class Meta:
        managed = False
        db_table = 'bd_ventas_2023'

class BdVentas2024(models.Model):
    lapso = models.BigIntegerField(db_column='Lapso', blank=True, null=True)  # Field name made lowercase.
    centro_de_operacion = models.BigIntegerField(db_column='Centro de Operacion', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_centro_de_operacion = models.CharField(db_column='Nombre Centro de Operacion', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    criterio_item_1 = models.FloatField(db_column='Criterio Item 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_criterio_item_1 = models.CharField(db_column='Nombre Criterio Item 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    item = models.BigIntegerField(db_column='Item', blank=True, null=True)  # Field name made lowercase.
    nombre_item = models.CharField(db_column='Nombre Item', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    linea_n1 = models.BigIntegerField(db_column='Linea N1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_linea_n1 = models.CharField(db_column='Nombre Linea N1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cliente = models.CharField(db_column='Cliente', blank=True, null=True)  # Field name made lowercase.
    nombre_cliente = models.CharField(db_column='Nombre Cliente', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    clase_cliente = models.BigIntegerField(db_column='Clase Cliente', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_clase_cliente = models.CharField(db_column='Nombre Clase Cliente', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cantidad_1 = models.FloatField(db_column='Cantidad 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    valor_costo = models.FloatField(db_column='Valor Costo', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    valor_neto = models.BigIntegerField(db_column='Valor Neto', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.

    class Meta:
        managed = False
        db_table = 'bd_ventas_2024'

 
class ConceptosFijosYVariables(models.Model):
    centro_tra = models.IntegerField(db_column='CENTRO_TRA', blank=True, null=True)  # Field name made lowercase.
    nombre_cen = models.CharField(db_column='NOMBRE_CEN', blank=True, null=True)  # Field name made lowercase.
    codcosto = models.IntegerField(db_column='CODCOSTO', blank=True, null=True)  # Field name made lowercase.
    nomcosto = models.CharField(db_column='NOMCOSTO', blank=True, null=True)  # Field name made lowercase.
    tipocpto = models.CharField(db_column='TIPOCPTO', blank=True, null=True)  # Field name made lowercase.
    cuenta = models.IntegerField(db_column='CUENTA', blank=True, null=True)  # Field name made lowercase.
    concepto = models.CharField(db_column='CONCEPTO', blank=True, null=True)  # Field name made lowercase.
    nombre_con = models.CharField(db_column='NOMBRE_CON', blank=True, null=True)  # Field name made lowercase.
    cargo = models.IntegerField(db_column='CARGO', blank=True, null=True)  # Field name made lowercase.
    nombrecar = models.CharField(db_column='NOMBRECAR', blank=True, null=True)  # Field name made lowercase.
    cedula = models.IntegerField(db_column='CEDULA', blank=True, null=True)  # Field name made lowercase.
    nombre = models.CharField(db_column='NOMBRE', blank=True, null=True)  # Field name made lowercase.
    arlporc = models.FloatField(db_column='ARLPORC', blank=True, null=True)  # Field name made lowercase.
    concepto_f = models.IntegerField(db_column='CONCEPTO_F', blank=True, null=True)  # Field name made lowercase.
    enero = models.IntegerField(db_column='ENERO', blank=True, null=True)  # Field name made lowercase.
    febrero = models.IntegerField(db_column='FEBRERO', blank=True, null=True)  # Field name made lowercase.
    marzo = models.IntegerField(db_column='MARZO', blank=True, null=True)  # Field name made lowercase.
    abril = models.IntegerField(db_column='ABRIL', blank=True, null=True)  # Field name made lowercase.
    mayo = models.IntegerField(db_column='MAYO', blank=True, null=True)  # Field name made lowercase.
    junio = models.IntegerField(db_column='JUNIO', blank=True, null=True)  # Field name made lowercase.
    julio = models.IntegerField(db_column='JULIO', blank=True, null=True)  # Field name made lowercase.
    agosto = models.IntegerField(db_column='AGOSTO', blank=True, null=True)  # Field name made lowercase.
    septiembre = models.IntegerField(db_column='SEPTIEMBRE', blank=True, null=True)  # Field name made lowercase.
    total = models.IntegerField(db_column='TOTAL', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'conceptos_fijos_y_variables'
        
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

class PresupuestoAuxilioMovilidad(models.Model):
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
        db_table = 'presupuesto_auxilio_movilidad'

class PresupuestoAuxilioMovilidadAux(models.Model):
    cedula = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    centro = models.CharField(max_length=150, null=True, blank=True)
    area = models.CharField(max_length=150, null=True, blank=True)
    cargo = models.CharField(max_length=150, null=True, blank=True)
    concepto = models.CharField(max_length=50, default="AUXILIO MOVILIDAD")
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
        db_table = 'presupuesto_auxilio_movilidad_auxiliar'
        
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
        
class ConceptoAuxilioEducacion(models.Model):
    centro_tra = models.BigIntegerField(db_column='CENTRO_TRA', blank=True, null=True)  # Field name made lowercase.
    nombre_cen = models.CharField(db_column='NOMBRE_CEN', blank=True, null=True)  # Field name made lowercase.
    codcosto = models.BigIntegerField(db_column='CODCOSTO', blank=True, null=True)  # Field name made lowercase.
    nomcosto = models.CharField(db_column='NOMCOSTO', blank=True, null=True)  # Field name made lowercase.
    tipocpto = models.CharField(db_column='TIPOCPTO', blank=True, null=True)  # Field name made lowercase.
    cuenta = models.BigIntegerField(db_column='CUENTA', blank=True, null=True)  # Field name made lowercase.
    concepto = models.CharField(db_column='CONCEPTO', blank=True, null=True)  # Field name made lowercase.
    nombre_con = models.CharField(db_column='NOMBRE_CON', blank=True, null=True)  # Field name made lowercase.
    cargo = models.BigIntegerField(db_column='CARGO', blank=True, null=True)  # Field name made lowercase.
    nombrecar = models.CharField(db_column='NOMBRECAR', blank=True, null=True)  # Field name made lowercase.
    cedula = models.BigIntegerField(db_column='CEDULA', blank=True, null=True)  # Field name made lowercase.
    nombre = models.CharField(db_column='NOMBRE', blank=True, null=True)  # Field name made lowercase.
    arlporc = models.FloatField(db_column='ARLPORC', blank=True, null=True)  # Field name made lowercase.
    concepto_f = models.BigIntegerField(db_column='CONCEPTO_F', blank=True, null=True)  # Field name made lowercase.
    enero = models.BigIntegerField(db_column='ENERO', blank=True, null=True)  # Field name made lowercase.
    febrero = models.BigIntegerField(db_column='FEBRERO', blank=True, null=True)  # Field name made lowercase.
    marzo = models.BigIntegerField(db_column='MARZO', blank=True, null=True)  # Field name made lowercase.
    abril = models.BigIntegerField(db_column='ABRIL', blank=True, null=True)  # Field name made lowercase.
    mayo = models.BigIntegerField(db_column='MAYO', blank=True, null=True)  # Field name made lowercase.
    junio = models.BigIntegerField(db_column='JUNIO', blank=True, null=True)  # Field name made lowercase.
    julio = models.BigIntegerField(db_column='JULIO', blank=True, null=True)  # Field name made lowercase.
    agosto = models.BigIntegerField(db_column='AGOSTO', blank=True, null=True)  # Field name made lowercase.
    septiembre = models.BigIntegerField(db_column='SEPTIEMBRE', blank=True, null=True)  # Field name made lowercase.
    octubre = models.BigIntegerField(db_column='OCTUBRE', blank=True, null=True)  # Field name made lowercase.
    noviembre = models.BigIntegerField(db_column='NOVIEMBRE', blank=True, null=True)  # Field name made lowercase.
    diciembre = models.BigIntegerField(db_column='DICIEMBRE', blank=True, null=True)  # Field name made lowercase.
    total = models.BigIntegerField(db_column='TOTAL', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'concepto_auxilio_educacion'

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
        
# TABLAS PARA PRESUPUESTO DE VENTAS
class PresupuestoComercial(models.Model):
    linea = models.CharField(max_length=100)
    year = models.IntegerField()
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
    utilidad_porcentual = models.FloatField(default=0)
    utilidad_valor = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'presupuesto_comercial'
    
class PresupuestoGeneralVentas(models.Model):
    year = models.IntegerField()
    mes = models.IntegerField()
    total = models.BigIntegerField(default=0)
    r2 = models.FloatField(default=0)
    
    class Meta:
        db_table = 'presupuesto_general_ventas'
        
class PresupuestoGeneralCostos(models.Model):
    year = models.IntegerField()
    mes = models.IntegerField()
    total = models.BigIntegerField(default=0)
    r2 = models.FloatField(default=0)
    
    class Meta:
        db_table = 'presupuesto_general_costos'
        
class PresupuestoCentroOperacionVentas(models.Model):
    year = models.IntegerField()
    mes = models.IntegerField()
    centro_operacion = models.IntegerField()
    total = models.BigIntegerField(default=0)
    r2 = models.FloatField(default=0)
    
    class Meta:
        db_table = 'presupuesto_centro_operacion_ventas'

class PresupuestoCentroOperacionCostos(models.Model):
    year = models.IntegerField()
    mes = models.IntegerField()
    centro_operacion = models.IntegerField()
    total = models.BigIntegerField(default=0)
    r2 = models.FloatField(default=0)
    
    class Meta:
        db_table = 'presupuesto_centro_operacion_costos'
        
class PresupuestoCentroSegmentoVentas(models.Model):
    year = models.IntegerField()
    mes = models.IntegerField()
    centro_operacion = models.IntegerField()
    segmento = models.CharField(max_length=100)
    total = models.BigIntegerField(default=0)
    r2 = models.FloatField(default=0)
    
    class Meta:
        db_table = 'presupuesto_centro_segmento_ventas'
        
class PresupuestoCentroSegmentoCostos(models.Model):
    year = models.IntegerField()
    mes = models.IntegerField()
    centro_operacion = models.IntegerField()
    segmento = models.CharField(max_length=100)
    total = models.BigIntegerField(default=0)
    r2 = models.FloatField(default=0)
    
    class Meta:
        db_table = 'presupuesto_centro_segmento_costos'
        
