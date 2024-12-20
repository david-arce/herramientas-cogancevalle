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
    mcnproduct = models.CharField(db_column='MCNPRODUCT', blank=True, null=True)  # item
    marnombre = models.CharField(db_column='MARNOMBRE', blank=True, null=True)  # proveedor
    pronombre = models.CharField(db_column='PRONOMBRE', blank=True, null=True)  # descripcion
    mcnbodega = models.FloatField(db_column='MCNBODEGA', blank=True, null=True)  # bodega
    docfecha = models.DateField(db_column='DOCFECHA', blank=True, null=True)  # fecha

    class Meta:
        managed = False 
        db_table = 'venta'

class Inv06(models.Model):
    mcncuenta = models.IntegerField(db_column='MCNCUENTA', blank=True, null=True)  # cuenta
    promarca = models.IntegerField(db_column='PROMARCA', blank=True, null=True)  # marca
    marnombre = models.CharField(db_column='MARNOMBRE', blank=True, null=True)  # laboratorio
    mcnproduct = models.IntegerField(db_column='MCNPRODUCT', blank=True, null=True)  # item producto
    pronombre = models.CharField(db_column='PRONOMBRE', blank=True, null=True)  # descripcion
    fecvence = models.DateField(db_column='FECVENCE', blank=True, null=True)  # fecha vencimiento
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

    class Meta:
        db_table = 'tarea'
        verbose_name = 'Tarea'
        verbose_name_plural = 'Tareas'

    def __str__(self):
        username = self.usuario.username if self.usuario and self.usuario.username else "Unknown User"
        marnombre = self.producto.marnombre if self.producto and self.producto.marnombre else "Unknown Product"
        observacion = self.observacion if self.observacion else "No Observations"
        return f"{username} - {marnombre} - {self.conteo} - {observacion}"