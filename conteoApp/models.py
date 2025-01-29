# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models
from django.contrib.auth.models import User

class Venta(models.Model):
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
        db_table = "venta_diaria"
        managed = False # desactiva las migraciones


class Inv06(models.Model):
    mcncuenta = models.IntegerField(db_column='MCNCUENTA', blank=True, null=True)  # cuenta
    promarca = models.IntegerField(db_column='PROMARCA', blank=True, null=True)  # marca
    marnombre = models.CharField(db_column='MARNOMBRE', blank=True, null=True)  # laboratorio
    mcnproduct = models.IntegerField(db_column='MCNPRODUCT', blank=True, null=True)  # item producto
    pronombre = models.CharField(db_column='PRONOMBRE', blank=True, null=True)  # descripcion
    fecvence = models.CharField(db_column='FECVENCE', blank=True, null=True)  # fecha vencimiento
    mcnbodega = models.IntegerField(db_column='MCNBODEGA', blank=True, null=True)  # bodega
    bodnombre = models.CharField(db_column='BODNOMBRE', blank=True, null=True)  # nombre bodega
    saldo = models.IntegerField(db_column='SALDO', blank=True, null=True)  # saldo
    vrunit = models.FloatField(db_column='VRUNIT', blank=True, null=True)  # valor unitario
    vrtotal = models.FloatField(db_column='VRTOTAL', blank=True, null=True)  # valor total
    
    class Meta:
        managed = False
        db_table = 'inv06'

class Tarea(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    producto = models.ForeignKey(Inv06, on_delete=models.CASCADE)
    conteo = models.IntegerField(null=True, blank=True)
    fecha_asignacion = models.DateField(auto_now_add=True)
    observacion = models.TextField(null=True, blank=True)
    diferencia = models.IntegerField(null=True, blank=True) 
    consolidado = models.FloatField(null=True, blank=True, default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'tarea'
        verbose_name = 'Tarea'
        verbose_name_plural = 'Tareas'

    def __str__(self):
        username = self.usuario.username if self.usuario and self.usuario.username else "Unknown User"
        marnombre = self.producto.marnombre if self.producto and self.producto.marnombre else "Unknown Product"
        observacion = self.observacion if self.observacion else "No Observations"
        return f"{username} - {marnombre} - {self.conteo} - {observacion}"