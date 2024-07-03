from django.db import models


class Productos(models.Model):
    item = models.BigIntegerField(db_column='ITEM', primary_key=True)  # Field name made lowercase.
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
        managed = True
        db_table = 'productos'
        unique_together = (('item', 'sede'),) #clave primaria compuesta