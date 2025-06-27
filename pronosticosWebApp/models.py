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
        db_table = "productos_venta"

    def __str__(self):
        return f"Producto {self.numero} - {self.sku_nom}"


# class Inventario(models.Model):
#     cta = models.CharField(max_length=50)
#     marca = models.CharField(max_length=50)
#     marca_nom = models.CharField(max_length=100)
#     sku = models.CharField(max_length=50)
#     sku_nom = models.CharField(max_length=200)
#     lpt = models.CharField(max_length=8)  
#     bod = models.CharField(max_length=10)
#     bod_nom = models.CharField(max_length=100)
#     inv_saldo = models.IntegerField(null=True, blank=True)
#     inv_trsto = models.IntegerField(null=True, blank=True)
#     vlr_unit = models.DecimalField(max_digits=20, decimal_places=2)
#     vlr_total = models.DecimalField(max_digits=20, decimal_places=2)

#     class Meta:
#         db_table = "inventario"

class LeadTime(models.Model):
    sku = models.IntegerField(null=True, blank=True)
    sku_nom = models.CharField(max_length=200)
    marca_nom = models.CharField(max_length=100)
    bod = models.IntegerField(null=True, blank=True)
    tiempo_entrega = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leadtime"