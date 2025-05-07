from django.contrib import admin
from .models import Venta, Tarea, UserCity

# Register your models here.
admin.site.register(Venta)
admin.site.register(Tarea)
admin.site.register(UserCity)