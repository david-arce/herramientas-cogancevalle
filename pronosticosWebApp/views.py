import logging
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

logger = logging.getLogger(__name__)

# Create your views here.
@login_required
@permission_required('pronosticosWebApp.view_demanda', raise_exception=True)
def dashboard(request):
    df_demanda = pd.DataFrame(pm.getDataBD()) # Se convierten los productos en un DataFrame de pandas para su manipulación
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
        # sku = selected_rows[2]
        # sku_nom = selected_rows[4]
        # bod = selected_rows[1]
        # sede = selected_rows[8]
        # marca_nom = selected_rows[7]
        request.session['sku'] = selected_rows[2]  # Guardar sku en la sesión
        request.session['sku_nom'] = selected_rows[4]  # Guardar sku_nom
        request.session['bod'] = selected_rows[1]  # Guardar bod en la sesión
        request.session['sede'] = selected_rows[8]  # Guardar sede en
        request.session['marca_nom'] = selected_rows[7]  # Guardar marca_nom en la sesión
        
        # list_df_demanda = df_demanda[
        #     (df_demanda['sku'] == sku) & 
        #     (df_demanda['sku_nom'] == sku_nom) & 
        #     (df_demanda['bod'] == bod)
        # ].sort_values(by=['yyyy','mm'])
        # list_demanda = list_df_demanda['total'].tolist()  # Obtener la lista de demanda
        # df_pronosticos_p3['promedio_movil'] = df_pronosticos_p3['promedio_movil'].fillna(0)
        # df_pronostico_p4['promedio_movil_p4'] = df_pronostico_p4['promedio_movil_p4'].fillna(0)
        # df_pronostico_p5['promedio_movil_p5'] = df_pronostico_p5['promedio_movil_p5'].fillna(0)
        # df_pronostico_ses['pronostico_ses'] = df_pronostico_ses['pronostico_ses'].fillna(0)
        # df_pronostico_sed['pronostico_sed'] = df_pronostico_sed['pronostico_sed'].fillna(0)
        # # Obtener los promedios móviles y pronósticos
        # def obtener_lista(df, columna, sku, sku_nom, bod):
        #     return df[
        #         (df['sku'] == sku) &
        #         (df['sku_nom'] == sku_nom) &
        #         (df['bod'] == bod)
        #     ][columna].tolist()
            
        # list_promedio_movil_3 = obtener_lista(df_pronosticos_p3, 'promedio_movil', sku, sku_nom, bod)
        # list_promedio_movil_4 = obtener_lista(df_pronostico_p4, 'promedio_movil_p4', sku, sku_nom, bod)
        # list_promedio_movil_5 = obtener_lista(df_pronostico_p5, 'promedio_movil_p5', sku, sku_nom, bod)
        # list_ses = obtener_lista(df_pronostico_ses, 'pronostico_ses', sku, sku_nom, bod)
        # list_sed = obtener_lista(df_pronostico_sed, 'pronostico_sed', sku, sku_nom, bod)

        # # convertir los valores a enteros
        # list_promedio_movil_3 = [int(x) for x in list_promedio_movil_3]
        # list_promedio_movil_4 = [int(x) for x in list_promedio_movil_4]
        # list_promedio_movil_5 = [int(x) for x in list_promedio_movil_5]
        # list_ses = [int(x) for x in list_ses]
        # list_sed = [int(x) for x in list_sed]
        
        return JsonResponse({"status": "success", "message": "Datos recibidos correctamente"}) 
    else:
        return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

# @require_GET
def lista_productos():
    global df_demanda, df_total, df_pronosticos, df_pronostico_p3, df_pronostico_p4, df_pronostico_p5, df_pronostico_ses, df_pronostico_sed
    df_demanda, df_total, df_pronosticos, df_pronostico_p3, df_pronostico_p4, df_pronostico_p5, df_pronostico_ses, df_pronostico_sed = Pronosticos.pronosticos()
   
    # Convertir el DataFrame a JSON
    df_pronosticos_json = df_pronosticos.to_dict(orient='records')
    global data
    data = {
        "productos": df_pronosticos_json,
    }
    return

def demanda(request):
    return JsonResponse(data, safe=False)

def get_chart(request):
    
    """
    Construye el diccionario de ECharts usando los datos que
    vive en la sesión del usuario.
    """
    # --- 1. Recuperar parámetros de la sesión -------------------------------
    sku       = request.session.get('sku')
    sku_nom   = request.session.get('sku_nom')
    bod       = request.session.get('bod')
    sede      = request.session.get('sede')
    marca_nom = request.session.get('marca_nom')

    if not all([sku, sku_nom, bod]):
        return JsonResponse({"status": "error",
                             "message": "Selecciona una fila antes de generar la gráfica"}, status=400)
    
    # --- 2. Filtrar los datos de la demanda -------------------------------
    list_df_demanda = df_demanda[
            (df_demanda['sku'] == sku) & 
            (df_demanda['sku_nom'] == sku_nom) & 
            (df_demanda['bod'] == bod)
    ].sort_values(by=['yyyy','mm'])
    list_demanda = list_df_demanda['total'].tolist()  # Obtener la lista de demanda
    df_pronostico_p3['promedio_movil'] = df_pronostico_p3['promedio_movil'].fillna(0)
    df_pronostico_p4['promedio_movil_p4'] = df_pronostico_p4['promedio_movil_p4'].fillna(0)
    df_pronostico_p5['promedio_movil_p5'] = df_pronostico_p5['promedio_movil_p5'].fillna(0)
    df_pronostico_ses['pronostico_ses'] = df_pronostico_ses['pronostico_ses'].fillna(0)
    df_pronostico_sed['pronostico_sed'] = df_pronostico_sed['pronostico_sed'].fillna(0)
    
    # Obtener los promedios móviles y pronósticos
    def obtener_lista(df, columna, sku, sku_nom, bod):
        return df[
            (df['sku'] == sku) &
            (df['sku_nom'] == sku_nom) &
            (df['bod'] == bod)
        ][columna].tolist()
        
    list_promedio_movil_3 = obtener_lista(df_pronostico_p3, 'promedio_movil', sku, sku_nom, bod)
    list_promedio_movil_4 = obtener_lista(df_pronostico_p4, 'promedio_movil_p4', sku, sku_nom, bod)
    list_promedio_movil_5 = obtener_lista(df_pronostico_p5, 'promedio_movil_p5', sku, sku_nom, bod)
    list_ses = obtener_lista(df_pronostico_ses, 'pronostico_ses', sku, sku_nom, bod)
    list_sed = obtener_lista(df_pronostico_sed, 'pronostico_sed', sku, sku_nom, bod)

    # convertir los valores a enteros
    list_promedio_movil_3 = [int(x) for x in list_promedio_movil_3]
    list_promedio_movil_4 = [int(x) for x in list_promedio_movil_4]
    list_promedio_movil_5 = [int(x) for x in list_promedio_movil_5]
    list_ses = [int(x) for x in list_ses]
    list_sed = [int(x) for x in list_sed]
    # if selected_index is None:
    #     return JsonResponse({"status": "error", "message": "Por favor selecciona una fila de la tabla para generar la gráfica"}, status=400)
    
    # obtener los datos de la demanda-------------------------------
    # Filtrar el primer grupo completo (mes 1 a 12)
    primer_grupo = df_demanda[
        (df_demanda['sku'] == df_demanda.iloc[0]['sku']) &
        (df_demanda['sku_nom'] == df_demanda.iloc[0]['sku_nom']) &
        (df_demanda['bod'] == df_demanda.iloc[0]['bod'])
    ].sort_values(by=['yyyy','mm'])
    list_meses = primer_grupo['mm'].tolist()
    # obtener los meses por nombre
    meses = [
        'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
    ]
    # Reemplazar los números de mes por sus nombres de la list_meses
    list_meses = [meses[mes - 1] for mes in list_meses]
    list_meses.append('Pronóstico')  # Agregar 'Pronóstico' al final de la lista
    
    xAxis = list_meses  # Asignar los meses a xAxis
    chart = {
        "title": {"text": "Pronósticos", 
                  "subtext": "Pronóstico del producto: {} \nde la sede: {}, del proveedor: {}".format(sku_nom, sede, marca_nom)},
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

# generar token
def get_token():
    url_auth = "https://saaserpzn1a.qualitycolombia.com.co:58090/auth/token"
    credentials = {
        "username": "cogancevalle_01cmc",
        "password": "EDGNHSPRSGDKLK59R6412G41HJ5UKSL3RT64E3693A6563LOT4DRJ45RVVMGBAAE"
    }
    try:
        response = requests.post(url_auth, json=credentials)
        response.raise_for_status()  # Lanza un error si el código no es 200
        token = response.text.strip()  # Obtiene el token directamente como texto
        print(f"Token obtenido: {token}")
        return token
    except requests.exceptions.HTTPError as e:
        print(f"Error HTTP: {response.status_code} - {response.text}")
        raise Exception("No se pudo obtener el token")
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener el token: {e}")
        raise Exception("No se pudo obtener el token")

# guardas los productos en la base de datos
def guardar_productos(request):
    URL_API = "https://saaserpzn1a.qualitycolombia.com.co:58090/6h9VMm3poIkt/saas/api/execute"
    
    try:
        TOKEN = get_token()
        
        headers = {
            "Authorization": f"Bearer {TOKEN}",  # Cambia 'Bearer' si la API usa otro esquema de autorización
            "Content-Type": "application/json"  # Indica que el cuerpo será JSON
        }
        
        # Cuerpo (body) en formato JSON requerido por la API
        body = {
            "token":81,
            "company":"6h9VMm3poIkt",
            "appuser":"mngapicovalle01",
            "pwd":"R45SKFJH361A",
            "mnguser":"mngapi",
            "service":"MSVT01T6DHD",
            "entity":"HK1A010G1J34",
            "data":{"fechaini":"20241201","fechafin":"20241231"}
        }
        
        # Intenta realizar la solicitud GET a la API
        response = requests.post(URL_API, json=body, headers=headers)
        if response.status_code == 201:
            # se utiliza el método json() para extraer los datos en formato JSON de la respuesta y se almacenan en la variable productos
            productos = response.json()
            data = response.json().get("data", [])
            logger.info(f"Datos obtenidos: {len(data)}")
            df = pd.DataFrame(data)  # Convertir los datos a un DataFrame de pandas
            # print(df)
            # df.to_excel("ventas_marzo_2025.xlsx", index=False)  # Guardar el DataFrame en un archivo Excel
            print(f"Datos obtenidos: {len(data)}")
            productos_guardados = []
            sku_existentes = set(Producto.objects.values_list('sku', flat=True))  # Obtener los SKUs existentes en la base de datos
            numeros_existentes = set(Producto.objects.values_list('numero', flat=True))  # Obtener los números existentes en la base de datos
            fechas_existentes = set(Producto.objects.values_list('fecha', flat=True))  # Obtener las fechas existentes en la base de datos
            
            # Itera sobre los datos y guarda cada producto en la base de datos
            for item in data:
                # Verificar si el SKU, número y fecha ya existen en la base de datos
                if item['fecha'] in fechas_existentes and item['sku'] in sku_existentes and item['numero'] in numeros_existentes:
                    continue  # Si ya existe, no lo guarda
                # Crear instancia del modelo a partir del diccionario
                producto = Producto(
                    yyyy=item["yyyy"],
                    mm=item["mm"],
                    dd=item["dd"],
                    fecha=item["fecha"],
                    hora=item["hora"],
                    clase=item["clase"],
                    tipo=item["tipo"],
                    numero=item["numero"],
                    ven_cob=item["ven_cob"],
                    ven_cc=item["ven_cc"],
                    ven_nom=item["ven_nom"],
                    ccnit=item["ccnit"],
                    cliente_nom=item["cliente_nom"],
                    telef=item["telef"],
                    ciudad=item["ciudad"],
                    direccion=item["direccion"],
                    cliente_grp=item["cliente_grp"],
                    cliente_grp_nom=item["cliente_grp_nom"],
                    ciudad_nom=item["ciudad_nom"],
                    cliente_creado=item["cliente_creado"],
                    zona=item["zona"],
                    zona_nom=item["zona_nom"],
                    bod=item["bod"],
                    bod_nom=item["bod_nom"],
                    indinv=item["indinv"],
                    sku=item["sku"],
                    umd=item["umd"],
                    sku_nom=item["sku_nom"],
                    marca=item["marca"],
                    marca_nom=item["marca_nom"],
                    linea=item["linea"],
                    linea_nom=item["linea_nom"],
                    categ1=item["categ1"],
                    categ1_nom=item["categ1_nom"],
                    categ2=item["categ2"],
                    categ2_nom=item["categ2_nom"],
                    proveedor=item["proveedor"],
                    proveedor_nom=item["proveedor_nom"],
                    detalle=item["detalle"],
                    listap=item["listap"],
                    metodo_pago=item["metodo_pago"],
                    iva_porc=item["iva_porc"],
                    cantidad=item["cantidad"],
                    precio_b=item["precio_b"],
                    precio_d=item["precio_d"],
                    dcto1=item["dcto1"],
                    descuento=item["descuento"],
                    subtotal=item["subtotal"],
                    iva=item["iva"],
                    venta=item["venta"],
                    costo_ult=item["costo_ult"],
                    costo_pro=item["costo_pro"],
                    costo_vta=item["costo_vta"]
                )
                productos_guardados.append(producto)
            Producto.objects.bulk_create(productos_guardados)  # Guarda el objeto en la base de datos
            logger.info(f"Productos guardados: {len(productos_guardados)}")
            print(f"Productos guardados: {len(productos_guardados)}")
            #vaciar la lista de productos guardados
            productos_guardados = []
        else:
            # En caso de un código de respuesta no exitoso. Manejo de errores HTTP
            print(f"Error en la solicitud: {response.status_code}")
            productos = []
    except requests.RequestException as e:
        # Manejar errores de solicitud, por ejemplo, problemas de red
        print(f"Error en la solicitud: {e}")
        productos = []
    return HttpResponse("ok")
