# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models

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

    def __str__(self):
        return f"Producto {self.numero} - {self.sku_nom}"

class BdPresupuesto1(models.Model):
    lapso = models.IntegerField(db_column='Lapso', blank=True, null=True)  # Field name made lowercase.
    centro_de_operacion = models.IntegerField(db_column='Centro de Operacion', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_centro_de_operacion = models.CharField(db_column='Nombre Centro de Operacion', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cliente = models.CharField(db_column='Cliente', blank=True, null=True)  # Field name made lowercase.
    nombre_cliente = models.CharField(db_column='Nombre Cliente', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    clase_cliente = models.IntegerField(db_column='Clase Cliente', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_clase_cliente = models.CharField(db_column='Nombre Clase Cliente', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    criterio_item_1 = models.FloatField(db_column='Criterio Item 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_criterio_item_1 = models.CharField(db_column='Nombre Criterio Item 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    item = models.IntegerField(db_column='Item', blank=True, null=True)  # Field name made lowercase.
    nombre_item = models.CharField(db_column='Nombre Item', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    linea_n1 = models.IntegerField(db_column='Linea N1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_linea_n1 = models.CharField(db_column='Nombre Linea N1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cantidad_1 = models.FloatField(db_column='Cantidad 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    valor_neto = models.IntegerField(db_column='Valor Neto', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.

    class Meta:
        managed = False
        db_table = 'bd_presupuesto_1'


class BdPresupuesto2(models.Model):
    lapso = models.IntegerField(db_column='Lapso', blank=True, null=True)  # Field name made lowercase.
    centro_de_operacion = models.IntegerField(db_column='Centro de Operacion', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_centro_de_operacion = models.CharField(db_column='Nombre Centro de Operacion', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    criterio_item_1 = models.IntegerField(db_column='Criterio Item 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_criterio_item_1 = models.CharField(db_column='Nombre Criterio Item 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    item = models.CharField(db_column='Item', blank=True, null=True)  # Field name made lowercase.
    nombre_item = models.CharField(db_column='Nombre Item', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    linea_n1 = models.IntegerField(db_column='Linea N1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_linea_n1 = models.CharField(db_column='Nombre Linea N1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cantidad_1 = models.FloatField(db_column='Cantidad 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    valor_neto = models.IntegerField(db_column='Valor Neto', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    valor_costo = models.FloatField(db_column='Valor Costo', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_clase_cliente = models.CharField(db_column='Nombre Clase Cliente', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cliente = models.CharField(db_column='Cliente', blank=True, null=True)  # Field name made lowercase.
    nombre_cliente = models.CharField(db_column='Nombre Cliente', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.

    class Meta:
        managed = False
        db_table = 'bd_presupuesto_2'

class BdPresupuesto3(models.Model):
    lapso = models.IntegerField(db_column='Lapso', blank=True, null=True)  # Field name made lowercase.
    centro_de_operacion = models.IntegerField(db_column='Centro de Operacion', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_centro_de_operacion = models.CharField(db_column='Nombre Centro de Operacion', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cliente = models.CharField(db_column='Cliente', blank=True, null=True)  # Field name made lowercase.
    nombre_cliente = models.CharField(db_column='Nombre Cliente', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    clase_cliente = models.IntegerField(db_column='Clase Cliente', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_clase_cliente = models.CharField(db_column='Nombre Clase Cliente', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    criterio_item_1 = models.FloatField(db_column='Criterio Item 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_criterio_item_1 = models.CharField(db_column='Nombre Criterio Item 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    item = models.IntegerField(db_column='Item', blank=True, null=True)  # Field name made lowercase.
    nombre_item = models.CharField(db_column='Nombre Item', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    linea_n1 = models.IntegerField(db_column='Linea N1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_linea_n1 = models.CharField(db_column='Nombre Linea N1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cantidad_1 = models.FloatField(db_column='Cantidad 1', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    valor_neto = models.IntegerField(db_column='Valor Neto', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.

    class Meta:
        managed = False
        db_table = 'bd_presupuesto_3'

class BdPresupuestoNomina(models.Model):
    cedula = models.CharField(max_length=50, blank=True, null=True)
    nombre = models.CharField(max_length=255, blank=True, null=True)
    nombre_cen = models.CharField(max_length=255, blank=True, null=True)
    nombre_car = models.CharField(max_length=255, blank=True, null=True)
    salario = models.IntegerField(blank=True, null=True)
    auxilio = models.IntegerField(blank=True, null=True)
    nombre_des = models.CharField(max_length=255, blank=True, null=True)
    tipo_cargo = models.CharField(max_length=50, blank=True, null=True)
    nombre_cpt = models.CharField(max_length=255, blank=True, null=True)
    valor = models.IntegerField(blank=True, null=True)
    
    class Meta:
        managed = False
        db_table = 'bd_presupuesto_nomina'