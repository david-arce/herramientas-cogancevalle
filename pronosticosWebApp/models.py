# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Demanda(models.Model):
    codcmc_c50 = models.IntegerField(db_column='CODCMC.C50', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    producto_c15 = models.IntegerField(db_column='PRODUCTO.C15', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    proveedor = models.CharField(db_column='PROVEEDOR', blank=True, null=True)  # Field name made lowercase.
    nombre_c100 = models.CharField(db_column='NOMBRE.C100', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    unimed_c4 = models.CharField(db_column='UNIMED.C4', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    precio_unitario_n20 = models.FloatField(db_column='PRECIO_UNITARIO.N20', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    bodega_c5 = models.IntegerField(db_column='BODEGA.C5', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    sede = models.CharField(db_column='SEDE', blank=True, null=True)  # Field name made lowercase.
    noviembre = models.IntegerField(db_column='NOVIEMBRE', blank=True, null=True)  # Field name made lowercase.
    diciembre = models.IntegerField(db_column='DICIEMBRE', blank=True, null=True)  # Field name made lowercase.
    enero = models.IntegerField(db_column='ENERO', blank=True, null=True)  # Field name made lowercase.
    febrero = models.IntegerField(db_column='FEBRERO', blank=True, null=True)  # Field name made lowercase.
    marzo = models.IntegerField(db_column='MARZO', blank=True, null=True)  # Field name made lowercase.
    abril = models.IntegerField(db_column='ABRIL', blank=True, null=True)  # Field name made lowercase.
    mayo = models.IntegerField(db_column='MAYO', blank=True, null=True)  # Field name made lowercase.
    junio = models.IntegerField(db_column='JUNIO', blank=True, null=True)  # Field name made lowercase.
    julio = models.IntegerField(db_column='JULIO', blank=True, null=True)  # Field name made lowercase.
    agosto = models.IntegerField(db_column='AGOSTO', blank=True, null=True)  # Field name made lowercase.
    septiembre = models.IntegerField(db_column='SEPTIEMBRE', blank=True, null=True)  # Field name made lowercase.
    octubre = models.IntegerField(db_column='OCTUBRE', blank=True, null=True)  # Field name made lowercase.
    inventario = models.IntegerField(db_column='INVENTARIO', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'demanda'
