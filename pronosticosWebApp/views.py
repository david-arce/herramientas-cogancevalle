from datetime import datetime, timedelta
import hashlib
from io import BytesIO
import logging
import time
from django.shortcuts import render, HttpResponse
from django.http.response import JsonResponse
from django.views.decorators.http import require_GET
import pandas as pd
from .models import Producto
from django.views.decorators.csrf import csrf_exempt
import json
import requests
from django.contrib.auth.decorators import login_required
from pronosticosWebApp.pronosticos.promedioMovil import PronosticoMovil as pm
from pronosticosWebApp.pronosticos.pronosticos import Pronosticos
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied
from pronosticosWebApp.models import PronosticoMoviln3, PronosticoMoviln4, PronosticoMoviln5, PronosticoSes, PronosticoSed, Demanda, PronosticoFinal

logger = logging.getLogger(__name__)

# Create your views here.
@login_required
@permission_required('pronosticosWebApp.view_demanda', raise_exception=True)
def dashboard(request):
    df_demanda = pd.DataFrame(list(Demanda.objects.all().values()))
    df_demanda = df_demanda.drop(columns=['id'])
    # Ordenar directamente por 'sku', 'sede' y 'mm' sin agrupar
    # global sku, sku_nom, marca_nom, sede
    df_demanda = df_demanda.sort_values(by=['sku', 'sede', 'mm']).reset_index(drop=True)
    sku = df_demanda['sku'].unique().tolist()  # Obtener los valores únicos de 'sku'
    sku_nom = df_demanda['sku_nom'].unique().tolist()  # Obtener los valores únicos de 'sku_nom'
    marca_nom = df_demanda['marca_nom'].unique().tolist()  # Obtener los valores únicos de 'marca_nom'
    sede = df_demanda['sede'].unique().tolist()  # Obtener los valores únicos de 'sede'
    context = {
        'items': sku,
        'proveedores': marca_nom,
        'productos': sku_nom,
        'sedes': sede,
    }
    return render(request, "pronosticosWebApp/pronosticos.html", context)

@csrf_exempt
@login_required
def send_data(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        global selected_rows
        selected_rows = data.get('selectedRows', [])
        request.session['sku'] = selected_rows[2]  # Guardar sku en la sesión
        request.session['sku_nom'] = selected_rows[4]  # Guardar sku_nom
        request.session['bod'] = selected_rows[1]  # Guardar bod en la sesión
        request.session['sede'] = selected_rows[8]  # Guardar sede en
        request.session['marca_nom'] = selected_rows[7]  # Guardar marca_nom en la sesión
        
        return JsonResponse({"status": "success", "message": "Datos recibidos correctamente"}) 
    else:
        return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

@login_required
def demanda(request):
    qs = PronosticoFinal.objects.all()

    # Leer filtros desde query params
    items      = request.GET.getlist('item')       # ?item=X&item=Y
    proveedores = request.GET.getlist('proveedor')
    productos  = request.GET.getlist('producto')
    sedes      = request.GET.getlist('sede')
    
    if items:
        qs = qs.filter(item__in=items)
    if proveedores:
        qs = qs.filter(proveedor__in=proveedores)
    if productos:
        qs = qs.filter(producto__in=productos)
    if sedes:
        qs = qs.filter(sede__in=sedes)

    data = list(qs.values(
        'id', 'bodega', 'item', 'codigo', 'producto', 'unimed',
        'lotepro', 'proveedor', 'sede', 'cantidad',
        'stock', 'cantidadx3', 'precio', 'fecha'
    ))
    return JsonResponse({"productos": data})

def short_hash(valor: str, length: int = 6) -> str:
    return hashlib.md5(valor.encode()).hexdigest()[:length]

# exportar a excel elanco
@login_required
def export_elanco(request):
    hoy = datetime.now().date()
    primer_dia_mes_actual = hoy.replace(day=1)
    ultimo_dia_mes_anterior = primer_dia_mes_actual - timedelta(days=1)
    primer_dia_mes_anterior = ultimo_dia_mes_anterior.replace(day=1)

    fecha_inicio = primer_dia_mes_anterior.strftime("%Y%m%d")
    fecha_fin = ultimo_dia_mes_anterior.strftime("%Y%m%d")

    productos = Producto.objects.filter(
        fecha__range=(fecha_inicio, fecha_fin),
        marca__in=["0004"],
    )
    salida = []
    for p in productos:
        ven_cob_val = short_hash(p.ven_cob)
        ven_nom_val = "vendedor_" + ven_cob_val

        if p.tpper == 1:
            ccnit_val = short_hash(p.ccnit)
            ccnit_nom_val = "cliente_" + ccnit_val
        else:
            ccnit_val = p.ccnit
            ccnit_nom_val = p.cliente_nom

        dopr_ven = "venta" if p.tipo in ["A4", "B2", "C3", "T1"] else "devolución"

        fecha_formateada = p.fecha
        if isinstance(p.fecha, str) and len(p.fecha) == 8:
            fecha_formateada = f"{p.fecha[6:]}/{p.fecha[4:6]}/{p.fecha[:4]}"

        venta_formateada = f"{abs(p.venta):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        salida.append({
            "Distributor SAP Code": "50045719",
            "Distributor Name": "COOP GANA DEL CTRO Y NTE VALLE",
            "Customer CNPJ or CPF": ccnit_val,
            "Company Name or Customer Name": ccnit_nom_val,
            "Customer State": "Colombia",
            "Customer City": "Colombia",
            "Date of Invoice": fecha_formateada,
            "Invoice Number": p.numero,
            "Distributor Product Code": p.sku,
            "Distributor Product Name": p.sku_nom,
            "Product Sold Quantity": abs(p.cantidad),
            "Value": venta_formateada,
            "Sales Operations Classification": dopr_ven,
            "CFOP Number": p.zona,
            "Zone Code Sales": ven_cob_val,
            "Sales Zone Distribtuor": ven_nom_val,
            "State or Producer Registration Number": "",
            "Customer Grouping": "Natural" if p.tpper == 1 else "Juridica",
            "Customer ZIP Code": p.ciudad,
            "Customer Address": "" if p.tpper == 1 else p.direccion,
            "Customer Phone": "" if p.tpper == 1 else p.telef,
            "Customer Email": "",
            "BU divisions": "",
            "Shop Type that made the purchase": "",
        })

    buffer = BytesIO()
    pd.DataFrame(salida).to_excel(buffer, index=False)
    buffer.seek(0)

    nombre_archivo = f"elanco_{fecha_inicio}_{fecha_fin}.xlsx"
    response = HttpResponse(
        buffer.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{nombre_archivo}"'
    return response

@csrf_exempt
@login_required
def get_chart(request):
    # 1) Parámetros de sesión
    sku       = request.session.get('sku')
    sku_nom   = request.session.get('sku_nom')
    bod       = request.session.get('bod')
    sede      = request.session.get('sede')
    marca_nom = request.session.get('marca_nom')

    if not all([sku, sku_nom, bod]):
        return JsonResponse({
            "status": "error",
            "message": "Selecciona una fila antes de generar la gráfica"
        }, status=400)

    filtros = {
        'sku': sku,
        'sku_nom': sku_nom,
        'bod': bod,
    }

    # 2) Consultas ligeras: values_list trae sólo la columna que necesitas
    list_demanda = list(
        Demanda.objects
        .filter(**filtros)
        .order_by('yyyy','mm')
        .values_list('total', flat=True)
    )

    list_prom3 = list(
        PronosticoMoviln3.objects
        .filter(**filtros)
        .order_by('yyyy','mm')
        .values_list('promedio_movil', flat=True)
    )

    list_prom4 = list(
        PronosticoMoviln4.objects
        .filter(**filtros)
        .order_by('yyyy','mm')
        .values_list('promedio_movil', flat=True)
    )

    list_prom5 = list(
        PronosticoMoviln5.objects
        .filter(**filtros)
        .order_by('yyyy','mm')
        .values_list('promedio_movil', flat=True)
    )

    list_ses = list(
        PronosticoSes.objects
        .filter(**filtros)
        .order_by('yyyy','mm')
        .values_list('pronostico_ses', flat=True)
    )

    list_sed = list(
        PronosticoSed.objects
        .filter(**filtros)
        .order_by('yyyy','mm')
        .values_list('pronostico_sed', flat=True)
    )
    # Convertir los valores a enteros
    list_prom3 = [int(x) for x in list_prom3]
    list_prom4 = [int(x) for x in list_prom4]
    list_prom5 = [int(x) for x in list_prom5]
    list_ses = [int(x) for x in list_ses]
    list_sed = [int(x) for x in list_sed]

    # 3) Obtener los meses (números) via la misma consulta de demanda
    meses_nums = list(
        Demanda.objects
        .filter(**filtros)
        .order_by('yyyy','mm')
        .values_list('mm', flat=True)
    )

    nombres = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
               'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
    list_meses = [nombres[m-1] for m in meses_nums]
    list_meses.append('Pronóstico')

    # 4) Armar el JSON de ECharts
    chart = {
        "title": {
            "text": "Pronósticos",
            "subtext": f"Producto: {sku_nom} | Sede: {sede} | Proveedor: {marca_nom}"
        },
        "tooltip": {"trigger": "axis"},
        "legend": {
            "data": [
                "Demanda", "Promedio móvil n=3", "Promedio móvil n=4",
                "Promedio móvil n=5", "Suavización simple", "Suavización doble"
            ]
        },
        "grid": {"left":"3%","right":"4%","bottom":"3%","containLabel":True},
        "toolbox": {"feature":{"saveAsImage":{}}},
        "xAxis": {"type":"category","boundaryGap":False,"data":list_meses},
        "yAxis": {"type":"value"},
        "series": [
            {"name":"Demanda",             "type":"line","data":list_demanda},
            {"name":"Promedio móvil n=3",  "type":"line","data":list_prom3},
            {"name":"Promedio móvil n=4",  "type":"line","data":list_prom4},
            {"name":"Promedio móvil n=5",  "type":"line","data":list_prom5},
            {"name":"Suavización simple",  "type":"line","data":list_ses},
            {"name":"Suavización doble",   "type":"line","data":list_sed},
        ]
    }
    return JsonResponse(chart)

