from django.shortcuts import render, HttpResponse
from django.http.response import JsonResponse
from django.views.decorators.http import require_GET
from .models import Producto
from django.views.decorators.csrf import csrf_exempt
import json
from django.contrib.auth.decorators import login_required
from pronosticosWebApp.pronosticos.promedioMovil import PronosticoMovil as pm
from pronosticosWebApp.pronosticos.pronosticos import Pronosticos
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied
import requests


list_demanda, list_promedio_movil, list_ses, list_sed = [], [], [], []
# Create your views here.
@login_required
@permission_required('pronosticosWebApp.view_demanda', raise_exception=True)
def dashboard(request):
    # items = Demanda.objects.values_list('producto_c15', flat=True).distinct()
    # proveedores = Demanda.objects.values_list('proveedor', flat=True).distinct()
    # productos = Demanda.objects.values_list('nombre_c100', flat=True).distinct()
    # sedes = Demanda.objects.values_list('sede', flat=True).distinct()

    # context = {
    #     'items': items,
    #     'proveedores': proveedores,
    #     'productos': productos,
    #     'sedes': sedes,
    # }
    # return render(request, "pronosticosWebApp/pronosticos.html", context)
    return

@csrf_exempt
def send_data(request):
    
    if request.method == 'POST':
        data = json.loads(request.body)
        global selected_rows
        selected_rows = data.get('selectedRows', [])
        #retornar el indice de la tabla menos 1
        global selected_index
        selected_index = int(selected_rows[1]) - 1
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
#   nombres_columnas = [field.name for field in Demanda._meta.get_fields()]
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
    list_demanda = df_demanda.iloc[selected_index].fillna(0).astype(int).tolist()
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

# # generar token
# def get_token():
#     url_auth = "https://saaserpzn1a.qualitycolombia.com.co:58090/auth/token"
#     credentials = {
#         "username": "cogancevalle_01cmc",
#         "password": "EDGNHSPRSGDKLK59R6412G41HJ5UKSL3RT64E3693A6563LOT4DRJ45RVVMGBAAE"
#     }
#     try:
#         response = requests.post(url_auth, json=credentials)
#         response.raise_for_status()  # Lanza un error si el código no es 200
#         token = response.text.strip()  # Obtiene el token directamente como texto
#         print(f"Token obtenido: {token}")
#         return token
#     except requests.exceptions.HTTPError as e:
#         print(f"Error HTTP: {response.status_code} - {response.text}")
#         raise Exception("No se pudo obtener el token")
#     except requests.exceptions.RequestException as e:
#         print(f"Error al obtener el token: {e}")
#         raise Exception("No se pudo obtener el token")

# # guardas los productos en la base de datos
# def guardar_productos(request):
#     URL_API = "https://saaserpzn1a.qualitycolombia.com.co:58090/6h9VMm3poIkt/saas/api/execute"
    
#     try:
#         TOKEN = get_token()
        
#         headers = {
#             "Authorization": f"Bearer {TOKEN}",  # Cambia 'Bearer' si la API usa otro esquema de autorización
#             "Content-Type": "application/json"  # Indica que el cuerpo será JSON
#         }
        
#         # Cuerpo (body) en formato JSON requerido por la API
#         body = {
#             "token":81,
#             "company":"6h9VMm3poIkt",
#             "appuser":"mngapicovalle01",
#             "pwd":"R45SKFJH361A",
#             "mnguser":"mngapi",
#             "service":"MSVT01T6DHD",
#             "entity":"HK1A010G1J34",
#             "data":{"fechaini":"20241101","fechafin":"20241130"}
#         }
        
#         # Intenta realizar la solicitud GET a la API
#         response = requests.post(URL_API, json=body, headers=headers)
#         if response.status_code == 201:
#             # se utiliza el método json() para extraer los datos en formato JSON de la respuesta y se almacenan en la variable productos
#             productos = response.json()
#             data = response.json().get("data", [])
#             productos_guardados = []
            
#             # Itera sobre los datos y guarda cada producto en la base de datos
#             for item in data:
#                 # Crear instancia del modelo a partir del diccionario
                
#                 producto = Producto(
#                     yyyy=item["yyyy"],
#                     mm=item["mm"],
#                     dd=item["dd"],
#                     fecha=item["fecha"],
#                     hora=item["hora"],
#                     clase=item["clase"],
#                     tipo=item["tipo"],
#                     numero=item["numero"],
#                     ven_cob=item["ven_cob"],
#                     ven_cc=item["ven_cc"],
#                     ven_nom=item["ven_nom"],
#                     ccnit=item["ccnit"],
#                     cliente_nom=item["cliente_nom"],
#                     telef=item["telef"],
#                     ciudad=item["ciudad"],
#                     direccion=item["direccion"],
#                     cliente_grp=item["cliente_grp"],
#                     cliente_grp_nom=item["cliente_grp_nom"],
#                     ciudad_nom=item["ciudad_nom"],
#                     cliente_creado=item["cliente_creado"],
#                     zona=item["zona"],
#                     zona_nom=item["zona_nom"],
#                     bod=item["bod"],
#                     bod_nom=item["bod_nom"],
#                     indinv=item["indinv"],
#                     sku=item["sku"],
#                     umd=item["umd"],
#                     sku_nom=item["sku_nom"],
#                     marca=item["marca"],
#                     marca_nom=item["marca_nom"],
#                     linea=item["linea"],
#                     linea_nom=item["linea_nom"],
#                     categ1=item["categ1"],
#                     categ1_nom=item["categ1_nom"],
#                     categ2=item["categ2"],
#                     categ2_nom=item["categ2_nom"],
#                     proveedor=item["proveedor"],
#                     proveedor_nom=item["proveedor_nom"],
#                     detalle=item["detalle"],
#                     listap=item["listap"],
#                     metodo_pago=item["metodo_pago"],
#                     iva_porc=item["iva_porc"],
#                     cantidad=item["cantidad"],
#                     precio_b=item["precio_b"],
#                     precio_d=item["precio_d"],
#                     dcto1=item["dcto1"],
#                     descuento=item["descuento"],
#                     subtotal=item["subtotal"],
#                     iva=item["iva"],
#                     venta=item["venta"],
#                     costo_ult=item["costo_ult"],
#                     costo_pro=item["costo_pro"],
#                     costo_vta=item["costo_vta"]
#                 )
#                 productos_guardados.append(producto)
#             Producto.objects.bulk_create(productos_guardados)  # Guarda el objeto en la base de datos
#             #vaciar la lista de productos guardados
#             productos_guardados = []
#         else:
#             # En caso de un código de respuesta no exitoso. Manejo de errores HTTP
#             print(f"Error en la solicitud: {response.status_code}")
#             productos = []
#     except requests.RequestException as e:
#         # Manejar errores de solicitud, por ejemplo, problemas de red
#         print(f"Error en la solicitud: {e}")
#         productos = []
#     return HttpResponse("ok")
