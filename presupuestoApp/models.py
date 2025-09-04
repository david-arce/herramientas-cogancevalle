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
        managed = False

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

class Nom005Salarios(models.Model):
    cedula = models.IntegerField(db_column='CEDULA', blank=True, null=True)  # Field name made lowercase.
    nombre = models.CharField(db_column='NOMBRE', blank=True, null=True)  # Field name made lowercase.
    apellido1 = models.CharField(db_column='APELLIDO1', blank=True, null=True)  # Field name made lowercase.
    apellido2 = models.CharField(db_column='APELLIDO2', blank=True, null=True)  # Field name made lowercase.
    nombre1 = models.CharField(db_column='NOMBRE1', blank=True, null=True)  # Field name made lowercase.
    nombre2 = models.CharField(db_column='NOMBRE2', blank=True, null=True)  # Field name made lowercase.
    fecha_ingr = models.IntegerField(db_column='FECHA_INGR', blank=True, null=True)  # Field name made lowercase.
    fecha_reti = models.IntegerField(db_column='FECHA_RETI', blank=True, null=True)  # Field name made lowercase.
    salario = models.IntegerField(db_column='SALARIO', blank=True, null=True)  # Field name made lowercase.
    antiguedad = models.IntegerField(db_column='ANTIGUEDAD', blank=True, null=True)  # Field name made lowercase.
    fecha_naci = models.IntegerField(db_column='FECHA_NACI', blank=True, null=True)  # Field name made lowercase.
    edad = models.IntegerField(db_column='EDAD', blank=True, null=True)  # Field name made lowercase.
    sexo = models.CharField(db_column='SEXO', blank=True, null=True)  # Field name made lowercase.
    fec_vacaci = models.IntegerField(db_column='FEC_VACACI', blank=True, null=True)  # Field name made lowercase.
    correo = models.CharField(db_column='CORREO', blank=True, null=True)  # Field name made lowercase.
    activo = models.IntegerField(db_column='ACTIVO', blank=True, null=True)  # Field name made lowercase.
    direccion = models.CharField(db_column='DIRECCION', blank=True, null=True)  # Field name made lowercase.
    dir_tribut = models.CharField(db_column='DIR_TRIBUT', blank=True, null=True)  # Field name made lowercase.
    telefono1 = models.CharField(db_column='TELEFONO1', blank=True, null=True)  # Field name made lowercase.
    telefono2 = models.CharField(db_column='TELEFONO2', blank=True, null=True)  # Field name made lowercase.
    centro_tra = models.IntegerField(db_column='CENTRO_TRA', blank=True, null=True)  # Field name made lowercase.
    nombre_cen = models.CharField(db_column='NOMBRE_CEN', blank=True, null=True)  # Field name made lowercase.
    cargo = models.IntegerField(db_column='CARGO', blank=True, null=True)  # Field name made lowercase.
    nombre_car = models.CharField(db_column='NOMBRE_CAR', blank=True, null=True)  # Field name made lowercase.
    ciudad = models.CharField(db_column='CIUDAD', blank=True, null=True)  # Field name made lowercase.
    barrio = models.CharField(db_column='BARRIO', blank=True, null=True)  # Field name made lowercase.
    ccosto = models.IntegerField(db_column='CCOSTO', blank=True, null=True)  # Field name made lowercase.
    nombre_cco = models.CharField(db_column='NOMBRE_CCO', blank=True, null=True)  # Field name made lowercase.
    destino = models.CharField(db_column='DESTINO', blank=True, null=True)  # Field name made lowercase.
    nombre_des = models.CharField(db_column='NOMBRE_DES', blank=True, null=True)  # Field name made lowercase.
    codigo_con = models.IntegerField(db_column='CODIGO_CON', blank=True, null=True)  # Field name made lowercase.
    contrato = models.CharField(db_column='CONTRATO', blank=True, null=True)  # Field name made lowercase.
    vcto_contr = models.IntegerField(db_column='VCTO_CONTR', blank=True, null=True)  # Field name made lowercase.
    eps = models.CharField(db_column='EPS', blank=True, null=True)  # Field name made lowercase.
    nombre_eps = models.CharField(db_column='NOMBRE_EPS', blank=True, null=True)  # Field name made lowercase.
    afp = models.CharField(db_column='AFP', blank=True, null=True)  # Field name made lowercase.
    nombre_afp = models.CharField(db_column='NOMBRE_AFP', blank=True, null=True)  # Field name made lowercase.
    arl = models.CharField(db_column='ARL', blank=True, null=True)  # Field name made lowercase.
    nombre_arl = models.CharField(db_column='NOMBRE_ARL', blank=True, null=True)  # Field name made lowercase.
    nivel_ries = models.CharField(db_column='NIVEL_RIES', blank=True, null=True)  # Field name made lowercase.
    nombre_niv = models.CharField(db_column='NOMBRE_NIV', blank=True, null=True)  # Field name made lowercase.
    ccf = models.CharField(db_column='CCF', blank=True, null=True)  # Field name made lowercase.
    nombre_ccf = models.CharField(db_column='NOMBRE_CCF', blank=True, null=True)  # Field name made lowercase.
    estado_civ = models.CharField(db_column='ESTADO_CIV', blank=True, null=True)  # Field name made lowercase.
    escolarida = models.CharField(db_column='ESCOLARIDA', blank=True, null=True)  # Field name made lowercase.
    tipo_sangr = models.CharField(db_column='TIPO_SANGR', blank=True, null=True)  # Field name made lowercase.
    estatura = models.IntegerField(db_column='ESTATURA', blank=True, null=True)  # Field name made lowercase.
    peso = models.IntegerField(db_column='PESO', blank=True, null=True)  # Field name made lowercase.
    calzado = models.IntegerField(db_column='CALZADO', blank=True, null=True)  # Field name made lowercase.
    pantalon = models.FloatField(db_column='PANTALON', blank=True, null=True)  # Field name made lowercase.
    camisa = models.FloatField(db_column='CAMISA', blank=True, null=True)  # Field name made lowercase.
    cog_banco = models.CharField(db_column='COG_BANCO', blank=True, null=True)  # Field name made lowercase.
    nombre_bco = models.CharField(db_column='NOMBRE_BCO', blank=True, null=True)  # Field name made lowercase.
    nemcuenta = models.IntegerField(db_column='NEMCUENTA', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'nom005_salarios'

class Nom010ConceptosVariables(models.Model):
    centro_tra = models.IntegerField(db_column='CENTRO_TRA', blank=True, null=True)  # Field name made lowercase.
    nombre_cen = models.CharField(db_column='NOMBRE_CEN', blank=True, null=True)  # Field name made lowercase.
    tipocpto = models.CharField(db_column='TIPOCPTO', blank=True, null=True)  # Field name made lowercase.
    concepto = models.CharField(db_column='CONCEPTO', blank=True, null=True)  # Field name made lowercase.
    nombre_con = models.CharField(db_column='NOMBRE_CON', blank=True, null=True)  # Field name made lowercase.
    cedula = models.IntegerField(db_column='CEDULA', blank=True, null=True)  # Field name made lowercase.
    nombre = models.CharField(db_column='NOMBRE', blank=True, null=True)  # Field name made lowercase.
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
        db_table = 'nom010_conceptos_variables'

class Nom016ConceptosFijos(models.Model):
    centro_tra = models.IntegerField(db_column='CENTRO_TRA', blank=True, null=True)  # Field name made lowercase.
    nombre_cen = models.CharField(db_column='NOMBRE_CEN', blank=True, null=True)  # Field name made lowercase.
    cargo = models.IntegerField(db_column='CARGO', blank=True, null=True)  # Field name made lowercase.
    nombre_car = models.CharField(db_column='NOMBRE_CAR', blank=True, null=True)  # Field name made lowercase.
    cedula = models.IntegerField(db_column='CEDULA', blank=True, null=True)  # Field name made lowercase.
    nombre = models.CharField(db_column='NOMBRE', blank=True, null=True)  # Field name made lowercase.
    fecha_ingr = models.CharField(db_column='FECHA_INGR', blank=True, null=True)  # Field name made lowercase.
    dato = models.FloatField(db_column='DATO', blank=True, null=True)  # Field name made lowercase.
    dato_nombr = models.FloatField(db_column='DATO_NOMBR', blank=True, null=True)  # Field name made lowercase.
    salario = models.IntegerField(db_column='SALARIO', blank=True, null=True)  # Field name made lowercase.
    auxilio = models.IntegerField(db_column='AUXILIO', blank=True, null=True)  # Field name made lowercase.
    destino = models.CharField(db_column='DESTINO', blank=True, null=True)  # Field name made lowercase.
    nombre_des = models.CharField(db_column='NOMBRE_DES', blank=True, null=True)  # Field name made lowercase.
    tipo_emple = models.CharField(db_column='TIPO_EMPLE', blank=True, null=True)  # Field name made lowercase.
    tipo_cargo = models.CharField(db_column='TIPO_CARGO', blank=True, null=True)  # Field name made lowercase.
    concepto = models.IntegerField(db_column='CONCEPTO', blank=True, null=True)  # Field name made lowercase.
    nombre_cpt = models.CharField(db_column='NOMBRE_CPT', blank=True, null=True)  # Field name made lowercase.
    valor = models.IntegerField(db_column='VALOR', blank=True, null=True)  # Field name made lowercase.
    fecha_ini = models.IntegerField(db_column='FECHA_INI', blank=True, null=True)  # Field name made lowercase.
    fecha_fin = models.IntegerField(db_column='FECHA_FIN', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'nom016_conceptos_fijos'
        
class TablaAuxiliar(models.Model):
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
        db_table = 'tabla_auxiliar'