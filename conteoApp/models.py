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
    mcnproduct = models.CharField(db_column='MCNPRODUCT', blank=True, null=True)  # Field name made lowercase.
    marnombre = models.CharField(db_column='MARNOMBRE', blank=True, null=True)  # Field name made lowercase.
    pronombre = models.CharField(db_column='PRONOMBRE', blank=True, null=True)  # Field name made lowercase.
    docfecha = models.DateField(db_column='DOCFECHA', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'venta'

class Tarea(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    producto = models.ForeignKey(Venta, on_delete=models.CASCADE)
    conteo = models.IntegerField(null=True, blank=True)
    fecha_asignacion = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=255, choices=[('pendiente', 'Pendiente'), ('completada', 'Completada')], default='pendiente')

    class Meta:
        db_table = 'tarea'
        verbose_name = 'Tarea'
        verbose_name_plural = 'Tareas'

    def __str__(self):
        return self.usuario.username