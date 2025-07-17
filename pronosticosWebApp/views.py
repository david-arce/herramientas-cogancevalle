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

def demanda(request):
    df_pronosticos = pd.DataFrame(list(PronosticoFinal.objects.all().values()))
    # Convertir el DataFrame a JSON
    df_pronosticos_json = df_pronosticos.to_dict(orient='records')
    data = {
        "productos": df_pronosticos_json,
    }
    return JsonResponse(data, safe=False)

# @csrf_exempt
# @login_required
# def get_chart(request):
#     inicio = time.time()
#     df_demanda = pd.DataFrame(list(Demanda.objects.all().values()))
#     df_pronostico_p3 = pd.DataFrame(list(PronosticoMoviln3.objects.all().values()))
#     df_pronostico_p4 = pd.DataFrame(list(PronosticoMoviln4.objects.all().values()))
#     df_pronostico_p5 = pd.DataFrame(list(PronosticoMoviln5.objects.all().values()))
#     df_pronostico_ses = pd.DataFrame(list(PronosticoSes.objects.all().values()))
#     df_pronostico_sed = pd.DataFrame(list(PronosticoSed.objects.all().values()))
#     fin = time.time()
#     print(f"Tiempo de carga de datos: {fin - inicio} segundos")
#     df_demanda = df_demanda.drop(columns=['id'])
#     df_pronostico_p3 = df_pronostico_p3.drop(columns=['id'])
#     df_pronostico_p4 = df_pronostico_p4.drop(columns=['id'])
#     df_pronostico_p5 = df_pronostico_p5.drop(columns=['id'])
#     df_pronostico_ses = df_pronostico_ses.drop(columns=['id'])
#     df_pronostico_sed = df_pronostico_sed.drop(columns=['id'])
#     """
#     Construye el diccionario de ECharts usando los datos que
#     vive en la sesión del usuario.
#     """
#     # --- 1. Recuperar parámetros de la sesión -------------------------------
#     sku       = request.session.get('sku')
#     sku_nom   = request.session.get('sku_nom')
#     bod       = request.session.get('bod')
#     sede      = request.session.get('sede')
#     marca_nom = request.session.get('marca_nom')
    
#     if not all([sku, sku_nom, bod]):
#         return JsonResponse({"status": "error",
#                              "message": "Selecciona una fila antes de generar la gráfica"}, status=400)
    
#     # --- 2. Filtrar los datos de la demanda -------------------------------
#     list_df_demanda = df_demanda[
#             (df_demanda['sku'] == sku) & 
#             (df_demanda['sku_nom'] == sku_nom) & 
#             (df_demanda['bod'] == bod)
#     ].sort_values(by=['yyyy','mm'])
#     list_demanda = list_df_demanda['total'].tolist()  # Obtener la lista de demanda
    
#     # Obtener los promedios móviles y pronósticos
#     def obtener_lista(df, columna, sku, sku_nom, bod):
#         return df[
#             (df['sku'] == sku) &
#             (df['sku_nom'] == sku_nom) &
#             (df['bod'] == bod)
#         ][columna].tolist()
        
#     list_promedio_movil_3 = obtener_lista(df_pronostico_p3, 'promedio_movil', sku, sku_nom, bod)
#     list_promedio_movil_4 = obtener_lista(df_pronostico_p4, 'promedio_movil', sku, sku_nom, bod)
#     list_promedio_movil_5 = obtener_lista(df_pronostico_p5, 'promedio_movil', sku, sku_nom, bod)
#     list_ses = obtener_lista(df_pronostico_ses, 'pronostico_ses', sku, sku_nom, bod)
#     list_sed = obtener_lista(df_pronostico_sed, 'pronostico_sed', sku, sku_nom, bod)

#     # convertir los valores a enteros
#     list_promedio_movil_3 = [int(x) for x in list_promedio_movil_3]
#     list_promedio_movil_4 = [int(x) for x in list_promedio_movil_4]
#     list_promedio_movil_5 = [int(x) for x in list_promedio_movil_5]
#     list_ses = [int(x) for x in list_ses]
#     list_sed = [int(x) for x in list_sed]
#     # if selected_index is None:
#     #     return JsonResponse({"status": "error", "message": "Por favor selecciona una fila de la tabla para generar la gráfica"}, status=400)
    
#     # obtener los datos de la demanda-------------------------------
#     # Filtrar el primer grupo completo (mes 1 a 12)
#     primer_grupo = df_demanda[
#         (df_demanda['sku'] == df_demanda.iloc[0]['sku']) &
#         (df_demanda['sku_nom'] == df_demanda.iloc[0]['sku_nom']) &
#         (df_demanda['bod'] == df_demanda.iloc[0]['bod'])
#     ].sort_values(by=['yyyy','mm'])
#     list_meses = primer_grupo['mm'].tolist()
#     # obtener los meses por nombre
#     meses = [
#         'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
#         'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
#     ]
#     # Reemplazar los números de mes por sus nombres de la list_meses
#     list_meses = [meses[mes - 1] for mes in list_meses]
#     list_meses.append('Pronóstico')  # Agregar 'Pronóstico' al final de la lista
    
#     xAxis = list_meses  # Asignar los meses a xAxis
#     chart = {
#         "title": {"text": "Pronósticos", 
#                   "subtext": "Pronóstico del producto: {} \nde la sede: {}, del proveedor: {}".format(sku_nom, sede, marca_nom)},
#         "tooltip": {"trigger": "axis"},
#         "legend": {
#             "data": ["Demanda", "Promedio móvil n=3","Promedio móvil n=4","Promedio móvil n=5", "Suavización simple", "Suaización doble"]
#         },
#         "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
#         "toolbox": {"feature": {"saveAsImage": {}}},
#         "xAxis": {
#             "type": "category",
#             "boundaryGap": False,
#             "data": xAxis,
#         },
#         "yAxis": {"type": "value"},
#         "series": [
#             {
#                 "name": "Demanda",
#                 "type": "line",
#                 "data": list_demanda,
#             },
#             {
#                 "name": "Promedio móvil n=3",
#                 "type": "line",
#                 "data": list_promedio_movil_3,
#             },
#             {
#                 "name": "Promedio móvil n=4",
#                 "type": "line",
#                 "data": list_promedio_movil_4,
#             },
#             {
#                 "name": "Promedio móvil n=5",
#                 "type": "line",
#                 "data": list_promedio_movil_5,
#             },
#             {
#                 "name": "Suavización simple",
#                 "type": "line",
#                 "data": list_ses,
#             },
#             {
#                 "name": "Suaización doble",
#                 "type": "line",
#                 "data": list_sed,
#             },
#         ],
#     }
#     return JsonResponse(chart)

@csrf_exempt
@login_required
def get_chart(request):
    inicio = time.time()
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

    fin = time.time()
    print(f"Tiempo de carga de datos: {fin - inicio:.2f} s")

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

