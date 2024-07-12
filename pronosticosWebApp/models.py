# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Productos(models.Model):
    id = models.BigIntegerField(db_column='ID', primary_key=True)  # Field name made lowercase.
    item = models.BigIntegerField(db_column='ITEM', blank=True, null=True)  # Field name made lowercase.
    proveedor = models.TextField(db_column='PROVEEDOR', blank=True, null=True)  # Field name made lowercase.
    descripción = models.TextField(db_column='DESCRIPCIÓN', blank=True, null=True)  # Field name made lowercase.
    sede = models.TextField(db_column='SEDE', blank=True, null=True)  # Field name made lowercase.
    mayo = models.BigIntegerField(db_column='MAYO', blank=True, null=True)  # Field name made lowercase.
    junio = models.BigIntegerField(db_column='JUNIO', blank=True, null=True)  # Field name made lowercase.
    julio = models.BigIntegerField(db_column='JULIO', blank=True, null=True)  # Field name made lowercase.
    agosto = models.BigIntegerField(db_column='AGOSTO', blank=True, null=True)  # Field name made lowercase.
    septiembre = models.BigIntegerField(db_column='SEPTIEMBRE', blank=True, null=True)  # Field name made lowercase.
    octubre = models.BigIntegerField(db_column='OCTUBRE', blank=True, null=True)  # Field name made lowercase.
    noviembre = models.BigIntegerField(db_column='NOVIEMBRE', blank=True, null=True)  # Field name made lowercase.
    diciembre = models.BigIntegerField(db_column='DICIEMBRE', blank=True, null=True)  # Field name made lowercase.
    enero = models.BigIntegerField(db_column='ENERO', blank=True, null=True)  # Field name made lowercase.
    febrero = models.BigIntegerField(db_column='FEBRERO', blank=True, null=True)  # Field name made lowercase.
    marzo = models.BigIntegerField(db_column='MARZO', blank=True, null=True)  # Field name made lowercase.
    abril = models.BigIntegerField(db_column='ABRIL', blank=True, null=True)  # Field name made lowercase.
    total = models.BigIntegerField(db_column='TOTAL', blank=True, null=True)  # Field name made lowercase.
    promedio = models.FloatField(db_column='PROMEDIO', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'productos'
