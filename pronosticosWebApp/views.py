from django.shortcuts import render
from django.http.response import JsonResponse
from django.views.decorators.http import require_GET
from .models import Demanda
from django.views.decorators.csrf import csrf_exempt
import json

from pronosticosWebApp.pronosticos.promedioMovil import PronosticoMovil as pm
from pronosticosWebApp.pronosticos.pronosticos import Pronosticos


list_demanda, list_promedio_movil, list_ses, list_sed = [], [], [], []
# Create your views here.
def dashboard(request):
    items = Demanda.objects.values_list('producto_c15', flat=True).distinct()
    proveedores = Demanda.objects.values_list('proveedor', flat=True).distinct()
    productos = Demanda.objects.values_list('nombre_c100', flat=True).distinct()
    sedes = Demanda.objects.values_list('sede', flat=True).distinct()

    context = {
        'items': items,
        'proveedores': proveedores,
        'productos': productos,
        'sedes': sedes,
    }
    return render(request, "index.html", context)

@csrf_exempt
def send_data(request):
    
    if request.method == 'POST':
        data = json.loads(request.body)
        global selected_rows
        selected_rows = data.get('selectedRows', [])
        #retornar el indice de la tabla menos 1
        global selected_index
        selected_index = int(selected_rows[0]) - 1
        
        return JsonResponse({"status": "success", "message": "Datos recibidos correctamente"}) 
    else:
        return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)
# def lista(request):
#     productos = Productos.objects.values('item', 'proveedor', 'descripción', 'sede', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre', 'enero', 'febrero', 'marzo', 'abril', 'total', 'promedio')
#     return render(request, 'template.html', {'productos': productos})


# @require_GET
def lista_productos():
    global df_demanda, df_promedio_movil_p3, df_promedio_movil_p4, df_promedio_movil_p5, df_pronostico_ses, df_pronostico_sed, df_pronosticos
    global items, proveedor, productos, sede
    
    df_demanda, df_promedio_movil_p3, df_promedio_movil_p4, df_promedio_movil_p5, df_pronostico_ses, df_pronostico_sed, df_pronosticos = Pronosticos.pronosticos()
    id, items, proveedor, productos, sede = pm.productos()
    
    # Convertir el DataFrame a JSON
    df_pronosticos_json = df_pronosticos.to_dict(orient='records')
    global data
    data = {
        "productos": df_pronosticos_json,
    }
    return 

def demanda(request):
    return JsonResponse(data, safe=False)

def meses():
  # productos = list(Productos.objects.values_list('descripción', flat=True))
  # data = {"productos": productos}
  nombres_columnas = [field.name for field in Demanda._meta.get_fields()]
  # Definir los campos a eliminar
  meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
  
  # Filtrar los nombres de las columnas
  nombres_columnas = [col for col in nombres_columnas if col in meses]
  #agregar un valor mas a la lista
  nombres_columnas.append('Pronóstico')
  return nombres_columnas

def get_chart(request):
    
    if selected_index is None:
        return JsonResponse({"status": "error", "message": "Por favor selecciona una fila de la tabla para generar la gráfica"}, status=400)
    # list_demanda, list_promedio_movil, list_ses, list_sed = grafica(selected_index)
    
    global list_demanda, list_promedio_movil_3, list_promedio_movil_4, list_promedio_movil_5, list_ses, list_sed
    list_demanda = df_demanda.iloc[selected_index][:-1].fillna(0).astype(int).tolist()
    list_promedio_movil_3 = df_promedio_movil_p3.iloc[selected_index].fillna(0).astype(int).tolist()
    list_promedio_movil_4 = df_promedio_movil_p4.iloc[selected_index].fillna(0).astype(int).tolist()
    list_promedio_movil_5 = df_promedio_movil_p5.iloc[selected_index].fillna(0).astype(int).tolist()
    list_ses = df_pronostico_ses.iloc[selected_index].fillna(0).astype(int).tolist()
    list_sed = df_pronostico_sed.iloc[selected_index].fillna(0).astype(int).tolist()
    list_sed.insert(0, '')
    # list_demanda = [1,2,3,4]
    # list_promedio_movil = [2,3,4,5]
    # list_ses = [3,4,5,6]
    # list_sed = [4,5,6,7]
    xAxis = meses()
    chart = {
        "title": {"text": "Pronósticos", 
                  "subtext": "Pronóstico del producto: {} \nde la sede: {}, del proveedor: {}".format(productos[selected_index], sede[selected_index], proveedor[selected_index])},
        "tooltip": {"trigger": "axis"},
        "legend": {
            "data": ["Demanda", "Promedio móvil n=3","Promedio móvil n=4","Promedio móvil n=5", "Suavización simple", "Suaización doble"]
        },
        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
        "toolbox": {"feature": {"saveAsImage": {}}},
        "xAxis": {
            "type": "category",
            "boundaryGap": False,
            "data": xAxis,
        },
        "yAxis": {"type": "value"},
        "series": [
            {
                "name": "Demanda",
                "type": "line",
                "data": list_demanda,
            },
            {
                "name": "Promedio móvil n=3",
                "type": "line",
                "data": list_promedio_movil_3,
            },
            {
                "name": "Promedio móvil n=4",
                "type": "line",
                "data": list_promedio_movil_4,
            },
            {
                "name": "Promedio móvil n=5",
                "type": "line",
                "data": list_promedio_movil_5,
            },
            {
                "name": "Suavización simple",
                "type": "line",
                "data": list_ses,
            },
            {
                "name": "Suaización doble",
                "type": "line",
                "data": list_sed,
            },
        ],
    }
    return JsonResponse(chart)
