from collections import defaultdict
from decimal import Decimal
from itertools import chain
from pyexpat.errors import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
import pandas as pd
from .models import Producto, BdPresupuesto1, BdPresupuesto2, BdPresupuesto3, TablaAuxiliar, Nom010ConceptosVariables, PresupuestoNomina, PresupuestoNominaAux, Nom016ConceptosFijos, ConceptosFijosYVariables, PresupuestoComisiones, PresupuestoComisionesAux, PresupuestoHorasExtra, PresupuestoHorasExtraAux, PresupuestoMediosTransporte, PresupuestoMediosTransporteAux, PresupuestoAuxilioTransporte, PresupuestoAuxilioTransporteAux, PresupuestoAyudaTransporte, PresupuestoAyudaTransporteAux, PresupuestoCesantias, PresupuestoCesantiasAux, PresupuestoPrima, PresupuestoPrimaAux, PresupuestoVacaciones, PresupuestoVacacionesAux, PresupuestoBonificaciones, PresupuestoBonificacionesAux, PresupuestoAprendiz, PresupuestoAprendizAux, PresupuestoAuxilioMovilidad, PresupuestoAuxilioMovilidadAux, PresupuestoSeguridadSocial, PresupuestoSeguridadSocialAux, PresupuestoInteresesCesantias, PresupuestoInteresesCesantiasAux, PresupuestoBonificacionesFoco, PresupuestoBonificacionesFocoAux, PresupuestoAuxilioEducacion, PresupuestoAuxilioEducacionAux, ConceptoAuxilioEducacion, PresupuestoBonosKyrovet, PresupuestoBonosKyrovetAux
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.db.models.functions import Concat
from django.db.models import Sum, Max
import numpy as np
import json
from django.utils import timezone

def exportar_excel_presupuestos(request):
    # Obtener datos de cada tabla
    nomina = list(PresupuestoNomina.objects.values())
    comisiones = list(PresupuestoComisiones.objects.values())
    horas_extra = list(PresupuestoHorasExtra.objects.values())
    auxlio_transporte = list(PresupuestoAuxilioTransporte.objects.values())
    medios_transporte = list(PresupuestoMediosTransporte.objects.values())
    ayuda_transporte = list(PresupuestoAyudaTransporte.objects.values())
    cesantias = list(PresupuestoCesantias.objects.values())
    intereses_cesantias = list(PresupuestoInteresesCesantias.objects.values())  
    prima = list(PresupuestoPrima.objects.values())
    vacaciones = list(PresupuestoVacaciones.objects.values())
    bonificaciones = list(PresupuestoBonificaciones.objects.values())
    auxilio_movilidad = list(PresupuestoAuxilioMovilidad.objects.values())
    aprendiz = list(PresupuestoAprendiz.objects.values())

    # Crear DataFrames con columna de origen
    def prepare_df(data, origen):
        df = pd.DataFrame(data)
        if not df.empty:
            df["origen"] = origen
            # 🔹 Asegurar que no haya datetime con timezone
            for col in df.select_dtypes(include=["datetimetz"]).columns:
                df[col] = df[col].dt.tz_localize(None)
        return df

    df_nomina = prepare_df(nomina, "Nómina")
    df_comisiones = prepare_df(comisiones, "Comisiones")
    df_horas_extra = prepare_df(horas_extra, "Horas Extra")
    df_auxilio_transporte = prepare_df(auxlio_transporte, "Auxilio Transporte")
    df_medios_transporte = prepare_df(medios_transporte, "Medios Transporte")
    df_ayuda_transporte = prepare_df(ayuda_transporte, "Ayuda Transporte")
    df_cesantias = prepare_df(cesantias, "Cesantías")
    df_intereses_cesantias = prepare_df(intereses_cesantias, "Intereses Cesantías")
    df_prima = prepare_df(prima, "Prima")
    df_vacaciones = prepare_df(vacaciones, "Vacaciones")
    df_bonificaciones = prepare_df(bonificaciones, "Bonificaciones")
    df_auxilio_movilidad = prepare_df(auxilio_movilidad, "Auxilio Movilidad")
    df_aprendiz = prepare_df(aprendiz, "Aprendiz")

    # Concatenar todos en un solo DataFrame
    df_final = pd.concat(
        [df_nomina, df_comisiones, df_horas_extra, df_auxilio_transporte, df_medios_transporte, df_ayuda_transporte, df_cesantias, df_intereses_cesantias, df_prima, df_vacaciones, df_bonificaciones, df_auxilio_movilidad, df_aprendiz],
        ignore_index=True
    )

    # Crear la respuesta HTTP para Excel
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="Presupuestos_Todo.xlsx"'

    # Exportar a una sola hoja
    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        df_final.to_excel(writer, sheet_name="Presupuestos", index=False)

    return response

def presupuesto(request):
    # ventas = BdPresupuesto1.objects.values('nombre_linea_n1','lapso').distinct()
    # obtener la suma de cada mes y nombre_linea_n1 es decir, si el lapso es 202001 retornar la suma
    # de los productos que pertenecen a la linea_n1
    bd1 = BdPresupuesto1.objects.values('nombre_linea_n1', 'lapso').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'suma')
    bd2 = BdPresupuesto2.objects.values('nombre_linea_n1', 'lapso').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'suma')
    bd3 = BdPresupuesto3.objects.values('nombre_linea_n1', 'lapso').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'suma')
    
    df1 = pd.DataFrame(list(bd1))
    df2 = pd.DataFrame(list(bd2))
    df3 = pd.DataFrame(list(bd3))
    
    df_lapso_2020_2021 = df1.groupby('lapso')['suma'].sum().reset_index()
    df_lapso_2024 = df2.groupby('lapso')['suma'].sum().reset_index()
    df_lapso_2022_2023 = df3.groupby('lapso')['suma'].sum().reset_index()
    df_lapso_total = pd.concat([df_lapso_2020_2021, df_lapso_2024, df_lapso_2022_2023], ignore_index=True)

    # CALUCLAR PREDICCIÓN PARA 2025 POR CADA MES -----------------------------------------
    # Extraer año y mes
    df_lapso_total['año'] = df_lapso_total['lapso'] // 100
    df_lapso_total['mes'] = df_lapso_total['lapso'] % 100

    # Lista para almacenar predicciones
    predicciones_2025 = []

    # Hacer predicción para cada mes
    for mes in range(1, 13):
        datos_mes = df_lapso_total[df_lapso_total['mes'] == mes]
        
        # Datos para regresión
        x = datos_mes['año'].values
        y = datos_mes['suma'].values

        if len(x) >= 2:  # Se necesita al menos 2 puntos para ajustar una recta
            a, b = np.polyfit(x, y, 1)  # Ajuste lineal
            y_pred = a * 2025 + b
            predicciones_2025.append({'lapso': 2025 * 100 + mes, 'suma': round(y_pred)})

    # Crear DataFrame con predicciones
    df_pred_2025 = pd.DataFrame(predicciones_2025)
    # print(df_pred_2025)
    # (Opcional) Unir con el DataFrame original y ordenar por lapso
    df_proyeccion_centro_operacion = pd.concat([df_lapso_total[['lapso', 'suma']], df_pred_2025], ignore_index=True)
    df_proyeccion_centro_operacion = df_proyeccion_centro_operacion.sort_values('lapso').reset_index(drop=True)


    # Concatenar los dataframes para el dinamismo
    df_dinamismo = pd.concat([df1, df3, df2], ignore_index=True)
    
    # Extraer el año desde 'lapso'
    df_dinamismo['year'] = df_dinamismo['lapso'] // 100

    # Agrupar por nombre de producto, año, y sumar
    df_agrupado = df_dinamismo.groupby(['nombre_linea_n1', 'year'])['suma'].sum().reset_index()

    # (Opcional) Ordenar resultados
    df_agrupado = df_agrupado.sort_values(by=['nombre_linea_n1', 'year'])
    
    # PREDICCION PARA 2025 POR PRONOSTICO LINEAL -----------------------------------------
    # Lista para almacenar resultados
    predicciones = []

    # Agrupar por producto
    for nombre, grupo in df_agrupado.groupby('nombre_linea_n1'):
        x = grupo['year'].values
        y = grupo['suma'].values
        
        if len(x) >= 2:
            # Ajuste lineal
            a, b = np.polyfit(x, y, 1)
            y_pred = a * 2025 + b
            predicciones.append({
                'nombre_linea_n1': nombre,
                'year': 2025,
                'suma': round(y_pred)
            })

    # Crear DataFrame con predicciones
    df_pred_2025_pro_lineal = pd.DataFrame(predicciones)
    df_final_pronostico = pd.concat([df_agrupado, df_pred_2025_pro_lineal], ignore_index=True)
    df_final_pronostico = df_final_pronostico.sort_values(by=['nombre_linea_n1', 'year']).reset_index(drop=True)
    
    # R2 ----------------------------------------------
    # Lista para almacenar resultados
    correlaciones = []

    # Agrupar por producto
    for nombre, grupo in df_final_pronostico.groupby('nombre_linea_n1'):
        x = grupo['year'].values
        y = grupo['suma'].values

        if len(x) >= 2:
            coef = np.corrcoef(x, y)[0, 1]
            coef_abs_pct = abs(coef) * 100  # valor absoluto en porcentaje
            correlaciones.append({
                'nombre_linea_n1': nombre,
                'R2': round(coef_abs_pct, 2)  # ej. 87.32%
            })

    # Crear DataFrame con los coeficientes
    df_correlaciones = pd.DataFrame(correlaciones)

    # calcular variacion porcentual entre 2024 y 2025
    df_2024 = df_final_pronostico[df_final_pronostico['year'] == 2024][['nombre_linea_n1', 'suma']].rename(columns={'suma': 'suma_2024'})
    df_2025 = df_final_pronostico[df_final_pronostico['year'] == 2025][['nombre_linea_n1', 'suma']].rename(columns={'suma': 'suma_2025'})
    df_variacion = pd.merge(df_2024, df_2025, on='nombre_linea_n1')
    df_variacion['variacion_pct'] = ((df_variacion['suma_2025'] - df_variacion['suma_2024']) / df_variacion['suma_2024']) * 100
    df_variacion['variacion_pct'] = df_variacion['variacion_pct'].round(2)
    
    # calcular variacion en valor en pesos entre 2024 y 2025
    df_variacion['variacion_valor'] = df_variacion['suma_2025'] - df_variacion['suma_2024']
    
    # calcular variacion mes, es decir, dividir la variacion_valor entre 12
    df_variacion['variacion_mes'] = (df_variacion['variacion_valor'] / 12).round().astype(int)
    
    # calcular variacion precios, es decir, tomar el año anterior(2024) y multiplicarlo por el 2%
    df_variacion['variacion_precios'] = (df_variacion['suma_2024'] * 0.02).round().astype(int)
    
    # calcular crecimiento comercial, es decir, restar la variacion_pct y la variacion_precios
    df_variacion['crecimiento_comercial'] = (df_variacion['variacion_valor'] - df_variacion['variacion_precios']).round().astype(int) 
    
    # calcular crecimiento comercial mes, es decir, dividir el crecimiento_comercial entre 12
    df_variacion['crecimiento_comercial_mes'] = (df_variacion['crecimiento_comercial'] / 12).round().astype(int)
    
    print(df_variacion)
    
    # unir con el df_final_pronostico
    data = pd.merge(df_final_pronostico, df_correlaciones, on='nombre_linea_n1', how='left')
    # print(data)
    # df.to_excel('ventas.xlsx', index=False)
    # Convertir a lista de diccionarios para pasar al template
    data = data.to_dict(orient='records')
    return render(request, 'presupuesto_ventas/presupuesto_ventas.html', {'data': data})

def dashboard(request):
    return render(request, 'presupuestoApp/dashboard.html')

def presupuestoNomina(request):
   # Obtiene el único registro (o lo crea vacío la primera vez)
    parametros, created = TablaAuxiliar.objects.get_or_create(id=1)

    if request.method == "POST" and request.headers.get("x-requested-with") == "XMLHttpRequest":
        # Actualizar con los valores enviados desde AJAX
        parametros.incremento_salarial = request.POST.get("incrementoSalarial") or None
        parametros.incremento_ipc = request.POST.get("incrementoIPC") or None
        parametros.auxilio_transporte = request.POST.get("auxilioTransporte") or None
        parametros.cesantias = request.POST.get("cesantias") or None
        parametros.intereses_cesantias = request.POST.get("interesesCesantias") or None
        parametros.prima = request.POST.get("prima") or None
        parametros.vacaciones = request.POST.get("vacaciones") or None
        parametros.salario_minimo = request.POST.get("salarioMinimo") or None
        parametros.incremento_comisiones = request.POST.get("incrementoComisiones") or None
        parametros.save()
        return JsonResponse({"status": "ok", "msg": "Parámetros actualizados correctamente ✅"})

    return render(request, "presupuesto_nomina/dashboard_nomina.html", {"parametros": parametros})


def presupuesto_sueldos(request):
    # obtener los valores de nomina unicos
    # nomina = Nom005Salarios.objects.values('cedula','nombre','nombre_car','nombre_cco','nombre_cen','salario').distinct()
    return render(request, "presupuesto_nomina/presupuesto_nomina.html")

def obtener_nomina_temp(request):
    data = list(PresupuestoNominaAux.objects.values())
    return JsonResponse(data, safe=False)

def tabla_auxiliar_sueldos(request):
    # obtener el incremento salarial desde la tabla auxiliar
    parametros = TablaAuxiliar.objects.first()
    incremento_salarial = parametros.incremento_salarial if parametros else 0
    salario = parametros.salario_minimo if parametros else 0
    return render(request, "presupuesto_nomina/aux_presupuesto_nomina.html", {'incrementoSalarial': incremento_salarial, 'salarioMinimo': salario})

def cargar_nomina_base(request):
    """
    Llena la tabla auxiliar con datos de ConceptosFijosYVariables
    """
    PresupuestoNominaAux.objects.all().delete()  # limpia tabla temporal
    base_data = ConceptosFijosYVariables.objects.values(
        "cedula","nombre","nombrecar","nomcosto","nombre_cen","concepto_f", "nombre_con"
    )

    # filtrar solo concepto = 001
    base_data = base_data.filter(concepto="001")
    
    for row in base_data:
        PresupuestoNominaAux.objects.create(
            cedula=row["cedula"],
            nombre=row["nombre"],
            cargo=row["nombrecar"],
            area=row["nomcosto"],
            centro=row["nombre_cen"],
            concepto=row["nombre_con"],
            salario_base=row["concepto_f"],
            enero=row["concepto_f"],
            febrero=row["concepto_f"],
        )

    return JsonResponse({"status": "ok"})

def guardar_nomina_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto",
                "salario_base", "enero", "febrero", "marzo", "abril", "mayo",
                "junio", "julio", "agosto", "septiembre", "octubre",
                "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoNominaAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "salario_base","enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoNominaAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoNominaAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def subir_presupuesto_sueldos(request):
    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "msg": "Método no permitido"
        }, status=405)

    temporales = PresupuestoNominaAux.objects.all()
    if not temporales.exists():
        return JsonResponse({
            "success": False,
            "msg": "No hay datos temporales para subir ❌"
        }, status=400)

    # Calcular versión siguiente
    ultima_version = PresupuestoNomina.objects.aggregate(Max("version"))["version__max"] or 0
    nueva_version = ultima_version + 1

    # Obtener todos los registros existentes de esta versión
    cedula_concepto_existentes = set(
        PresupuestoNomina.objects.filter(version=nueva_version)
        .values_list("cedula", "concepto")
    )

    # Preparar lista de objetos a crear
    registros_a_crear = []
    for temp in temporales:
        key = (temp.cedula, temp.concepto)
        if key not in cedula_concepto_existentes:
            registros_a_crear.append(
                PresupuestoNomina(
                    cedula=temp.cedula,
                    nombre=temp.nombre,
                    centro=temp.centro,
                    area=temp.area,
                    cargo=temp.cargo,
                    concepto=temp.concepto,
                    salario_base=temp.salario_base,
                    enero=temp.enero,
                    febrero=temp.febrero,
                    marzo=temp.marzo,
                    abril=temp.abril,
                    mayo=temp.mayo,
                    junio=temp.junio,
                    julio=temp.julio,
                    agosto=temp.agosto,
                    septiembre=temp.septiembre,
                    octubre=temp.octubre,
                    noviembre=temp.noviembre,
                    diciembre=temp.diciembre,
                    total=temp.total,
                    version=nueva_version,
                    fecha_carga=timezone.now()
                )
            )

    if not registros_a_crear:
        return JsonResponse({
            "success": False,
            "msg": "Todos los registros ya existían ❌"
        }, status=400)

    # Guardar todos los registros de una sola vez
    PresupuestoNomina.objects.bulk_create(registros_a_crear)

    return JsonResponse({
        "success": True,
        "msg": f"Presupuesto subido como versión {nueva_version} ✅ ({len(registros_a_crear)} nuevos registros)"
    })
def listar_versiones():
    return (
        PresupuestoNomina.objects
        .values("version")
        .annotate(fecha=Max("fecha_carga"))
        .order_by("-version")
    )

def obtener_presupuesto_sueldos(request):
    data = list(PresupuestoNomina.objects.values())
    return JsonResponse({"data": data}, safe=False)

@csrf_exempt
def borrar_presupuesto_sueldos(request):
    if request.method == "POST":
        PresupuestoNomina.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

# -------------------------------COMISIONES---------------------------------
def comisiones(request):
    return render(request, "presupuesto_nomina/comisiones.html")

def obtener_presupuesto_comisiones(request):
    comisiones = list(PresupuestoComisiones.objects.values())
    return JsonResponse({"data": comisiones}, safe=False)

def tabla_auxiliar_comisiones(request):
    # obtener el incremento de comisiones desde la tabla auxiliar
    parametros = TablaAuxiliar.objects.first()
    incremento_comisiones = parametros.incremento_comisiones if parametros else 0
    return render(request, "presupuesto_nomina/aux_comisiones.html", {'incrementoComisiones': incremento_comisiones})

def subir_presupuesto_comisiones(request):
    if request.method == "POST":
        temporales = PresupuestoComisionesAux.objects.all()

        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoComisiones.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de comisiones subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)

def guardar_comisiones_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoComisionesAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoComisionesAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoComisionesAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_comisiones_temp(request):
    data = list(PresupuestoComisionesAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_comisiones_base(request):
    """
    Llena la tabla auxiliar con datos de conceptos
    """
    PresupuestoComisionesAux.objects.all().delete()  # limpia tabla temporal
    base_data = ConceptosFijosYVariables.objects.values(
        "cedula","nombre","nombrecar","nomcosto","nombre_cen", "nombre_con", "enero", "febrero", "marzo", "abril", "mayo",
        "junio", "julio", "agosto", "total"
    )

    # filtrar solo concepto que sea igual a 389
    base_data = base_data.filter(concepto="389")
    
    for row in base_data:
        PresupuestoComisionesAux.objects.create(
            cedula=row["cedula"],
            nombre=row["nombre"],
            cargo=row["nombrecar"],
            area=row["nomcosto"],
            centro=row["nombre_cen"],
            concepto=row["nombre_con"],
            enero=row["enero"] or 0,
            febrero=row["febrero"] or 0,
            marzo=row["marzo"] or 0,
            abril=row["abril"] or 0,
            mayo=row["mayo"] or 0,
            junio=row["junio"] or 0,
            julio=row["julio"] or 0,
            agosto=row["agosto"] or 0,
            total=row["total"] or 0,
        )

        
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_comisiones(request):
    if request.method == "POST":
        PresupuestoComisiones.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de comisiones eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

# -------------------------------HORAS EXTRA---------------------------------
def horas_extra(request):
    return render(request, "presupuesto_nomina/horas_extra.html")

def obtener_presupuesto_horas_extra(request):
    horas_extra = list(PresupuestoHorasExtra.objects.values())
    return JsonResponse({"data": horas_extra}, safe=False)

def tabla_auxiliar_horas_extra(request):
    # obtener el incremento de horas extra desde la tabla auxiliar
    parametros = TablaAuxiliar.objects.first()
    incremento_horas_extra = parametros.incremento_salarial if parametros else 0
    return render(request, "presupuesto_nomina/aux_horas_extra.html", {'incrementoSalarial': incremento_horas_extra})

def subir_presupuesto_horas_extra(request):
    if request.method == "POST":
        temporales = PresupuestoHorasExtraAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoHorasExtra.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de horas extra subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)

def guardar_horas_extra_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoHorasExtraAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoHorasExtraAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoHorasExtraAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_horas_extra_temp(request):
    data = list(PresupuestoHorasExtraAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_horas_extra_base(request):
    """
    Llena la tabla auxiliar con datos de conceptos
    """
    PresupuestoHorasExtraAux.objects.all().delete()  # limpia tabla temporal
    base_data = ConceptosFijosYVariables.objects.values(
        "cedula","nombre","nombrecar","nomcosto","nombre_cen", "nombre_con", "enero", "febrero", "marzo", "abril", "mayo",
        "junio", "julio", "agosto", "total"
    )

    # Filtrar solo los conceptos que necesitamos
    base_data = (
        ConceptosFijosYVariables.objects
        .filter(concepto__in=["114", "110", "111"])
        .values("cedula", "nombre", "nombrecar", "nomcosto", "nombre_cen")  # agrupadores
        .annotate(
            enero=Sum("enero"),
            febrero=Sum("febrero"),
            marzo=Sum("marzo"),
            abril=Sum("abril"),
            mayo=Sum("mayo"),
            junio=Sum("junio"),
            julio=Sum("julio"),
            agosto=Sum("agosto"),
            total=Sum("total"),
        )
    )
    
    for row in base_data:
        PresupuestoHorasExtraAux.objects.create(
            cedula=row["cedula"],
            nombre=row["nombre"],
            cargo=row["nombrecar"],
            area=row["nomcosto"],
            centro=row["nombre_cen"],
            concepto="HORAS EXTRA",
            enero=row["enero"] or 0,
            febrero=row["febrero"] or 0,
            marzo=row["marzo"] or 0,
            abril=row["abril"] or 0,
            mayo=row["mayo"] or 0,
            junio=row["junio"] or 0,
            julio=row["julio"] or 0,
            agosto=row["agosto"] or 0,
            total=row["total"] or 0,
        )

        
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_horas_extra(request):
    if request.method == "POST":
        PresupuestoHorasExtra.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de horas extra eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)
# -------------------------------MEDIOS DE TRANSPORTE---------------------------------
def medios_transporte(request):
    return render(request, "presupuesto_nomina/medios_transporte.html")

def obtener_presupuesto_medios_transporte(request):
    medios_transporte = list(PresupuestoMediosTransporte.objects.values())
    return JsonResponse({"data": medios_transporte}, safe=False)

def tabla_auxiliar_medios_transporte(request):
    # obtener el incremento de medios de transporte desde la tabla auxiliar
    parametros = TablaAuxiliar.objects.first()
    incremento_medios_transporte = parametros.incremento_ipc if parametros else 0
    return render(request, "presupuesto_nomina/aux_medios_transporte.html", {'incrementoIPC': incremento_medios_transporte})

def subir_presupuesto_medios_transporte(request):
    if request.method == "POST":
        temporales = PresupuestoMediosTransporteAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoMediosTransporte.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                base=temp.base,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de medios de transporte subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_medios_transporte_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "base", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoMediosTransporteAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoMediosTransporteAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoMediosTransporteAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_medios_transporte_temp(request):
    data = list(PresupuestoMediosTransporteAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_medios_transporte_base(request):
    """
    Llena la tabla auxiliar con datos de conceptos
    """
    PresupuestoMediosTransporteAux.objects.all().delete()  # limpia tabla temporal
    base_data = ConceptosFijosYVariables.objects.values(
        "cedula","nombre","nombrecar","nomcosto","nombre_cen", "nombre_con", "concepto_f"
    )

    # filtrar solo concepto que sea igual a 389
    base_data = base_data.filter(concepto="011")
    
    for row in base_data:
        PresupuestoMediosTransporteAux.objects.create(
            cedula=row["cedula"],
            nombre=row["nombre"],
            cargo=row["nombrecar"],
            area=row["nomcosto"],
            centro=row["nombre_cen"],
            concepto=row["nombre_con"],
            base=row["concepto_f"] or 0,
            enero=row["concepto_f"] or 0,
            febrero=row["concepto_f"] or 0,
        )

        
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_medios_transporte(request):
    if request.method == "POST":
        PresupuestoMediosTransporte.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de medios de transporte eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)
# -------------------------------AUXILIO DE TRANSPORTE---------------------------------
def auxilio_transporte(request):
    return render(request, "presupuesto_nomina/auxilio_transporte.html")

def obtener_presupuesto_auxilio_transporte(request):
    auxilio_transporte = list(PresupuestoAuxilioTransporte.objects.values())
    return JsonResponse({"data": auxilio_transporte}, safe=False)

def tabla_auxiliar_auxilio_transporte(request):
    # obtener el auxilio de transporte desde la tabla auxiliar
    parametros = TablaAuxiliar.objects.first()
    auxilio_transporte = parametros.auxilio_transporte if parametros else 0
    return render(request, "presupuesto_nomina/aux_auxilio_transporte.html", {'auxilioTransporte': auxilio_transporte})

def subir_presupuesto_auxilio_transporte(request):
    if request.method == "POST":
        temporales = PresupuestoAuxilioTransporteAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoAuxilioTransporte.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                base=temp.base,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de auxilio de transporte subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)

def guardar_auxilio_transporte_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "base", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoAuxilioTransporteAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoAuxilioTransporteAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoAuxilioTransporteAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_auxilio_transporte_temp(request):
    data = list(PresupuestoAuxilioTransporteAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_auxilio_transporte_base(request):
    """
    Llena la tabla auxiliar con datos de conceptos y agrega auxilio de transporte
    cuando el salario mensual consolidado es menor al SMMLV (1.423.500).
    """
    parametros = TablaAuxiliar.objects.first()
    salarioIncremento = parametros.salario_minimo + (parametros.salario_minimo * (parametros.incremento_salarial / 100))
    LIMITE_SMMLV = (salarioIncremento) * 2
    AUXILIO_BASE = 200000
    MESES = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    PresupuestoAuxilioTransporteAux.objects.all().delete()  # limpia tabla temporal
    # Obtener base de empleados
    base_data = ConceptosFijosYVariables.objects.filter(concepto__in=["001", "006"]).values(
        "cedula", "nombre", "nombrecar", "nomcosto", "nombre_cen", "concepto_f"
    )
    
    for row in base_data:
        aux = PresupuestoAuxilioTransporteAux.objects.create(
            cedula=row["cedula"],
            nombre=row["nombre"],
            cargo=row["nombrecar"],
            area=row["nomcosto"],
            centro=row["nombre_cen"],
            concepto="AUXILIO DE TRANSPORTE",
            base=AUXILIO_BASE,
        )

        # 🔹 recorrer meses
        for mes in MESES:
            # Sumar el valor del mes en todas las tablas
            total_mes = 0

            total_mes += PresupuestoMediosTransporte.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0
            total_mes += PresupuestoNomina.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0
            total_mes += PresupuestoComisiones.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0
            total_mes += PresupuestoHorasExtra.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0

            # 🔹 Condición: si la suma < SMMLV, asignar 200000 a ese mes
            if total_mes < LIMITE_SMMLV:
                setattr(aux, mes, AUXILIO_BASE)

            if mes == "marzo":
                salario_base = row["concepto_f"] or 0
                nuevo_salario = salario_base + (salario_base * (parametros.incremento_salarial / 100))
                auxRetroactivo = (nuevo_salario - salario_base) * 2  # retroactivo de enero y febrero
               
                # Sumar el valor del mes en todas las tablas
                total_mes = 0

                total_mes += PresupuestoMediosTransporte.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0
                total_mes += PresupuestoNomina.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0
                total_mes += PresupuestoComisiones.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0
                total_mes += PresupuestoHorasExtra.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0

                total_mes -= auxRetroactivo * 2
                
                # 🔹 Condición: si la suma < SMMLV, asignar 200000 a ese mes
                if total_mes < LIMITE_SMMLV:
                    setattr(aux, mes, AUXILIO_BASE)

        # Guardar cambios
        aux.save()

        
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_auxilio_transporte(request):
    if request.method == "POST":
        PresupuestoAuxilioTransporte.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de auxilio de transporte eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)
# -------------------------------AYUDA AL TRANSPORTE---------------------------------
def ayuda_transporte(request):
    return render(request, "presupuesto_nomina/ayuda_transporte.html")

def obtener_presupuesto_ayuda_transporte(request):
    ayuda_transporte = list(PresupuestoAyudaTransporte.objects.values())
    return JsonResponse({"data": ayuda_transporte}, safe=False)

def tabla_auxiliar_ayuda_transporte(request):
    # obtener la ayuda de transporte desde la tabla auxiliar
    parametros = TablaAuxiliar.objects.first()
    ayuda_transporte = parametros.incremento_ipc if parametros else 0
    return render(request, "presupuesto_nomina/aux_ayuda_transporte.html", {'incrementoIPC': ayuda_transporte})

def subir_presupuesto_ayuda_transporte(request):
    if request.method == "POST":
        temporales = PresupuestoAyudaTransporteAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoAyudaTransporte.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                base=temp.base,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de ayuda de transporte subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_ayuda_transporte_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "base", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoAyudaTransporteAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoAyudaTransporteAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoAyudaTransporteAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_ayuda_transporte_temp(request):
    data = list(PresupuestoAyudaTransporteAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_ayuda_transporte_base(request):
    """
    Llena la tabla auxiliar con datos de conceptos
    """
    PresupuestoAyudaTransporteAux.objects.all().delete()  # limpia tabla temporal
    base_data = ConceptosFijosYVariables.objects.values(
        "cedula","nombre","nombrecar","nomcosto","nombre_cen", "nombre_con", "concepto_f"
    )

    # filtrar solo concepto que sea igual a 389
    base_data = base_data.filter(concepto="013")
    
    for row in base_data:
        PresupuestoAyudaTransporteAux.objects.create(
            cedula=row["cedula"],
            nombre=row["nombre"],
            cargo=row["nombrecar"],
            area=row["nomcosto"],
            centro=row["nombre_cen"],
            concepto=row["nombre_con"],
            base=row["concepto_f"] or 0,
            enero=row["concepto_f"] or 0,
            febrero=row["concepto_f"] or 0,
        )

        
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_ayuda_transporte(request):
    if request.method == "POST":
        PresupuestoAyudaTransporte.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de ayuda de transporte eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

# -----------------------------Cesantias---------------------
def cesantias(request):
    return render(request, "presupuesto_nomina/cesantias.html")

def obtener_presupuesto_cesantias(request):
    cesantias = list(PresupuestoCesantias.objects.values())
    return JsonResponse({"data": cesantias}, safe=False)

def tabla_auxiliar_cesantias(request):
    # obtener el auxilio de transporte desde la tabla auxiliar
    parametros = TablaAuxiliar.objects.first()
    cesantias = parametros.cesantias if parametros else 0
    return render(request, "presupuesto_nomina/aux_cesantias.html", {'cesantias': cesantias})

def subir_presupuesto_cesantias(request):
    if request.method == "POST":
        temporales = PresupuestoCesantiasAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoCesantias.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de cesantías subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)

def guardar_cesantias_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoCesantiasAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoCesantiasAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoCesantiasAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_cesantias_temp(request):
    data = list(PresupuestoCesantiasAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_cesantias_base(request):
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]

    # Limpio la tabla de cesantías antes de recalcular
    PresupuestoCesantiasAux.objects.all().delete()

    # Tomo todos los empleados desde nómina (puede ser tu base principal)
    empleados = PresupuestoNomina.objects.all()
    # Tomo también los aprendices
    aprendices = PresupuestoAprendiz.objects.filter(concepto="SALARIO APRENDIZ REFORMA")
    
    # # Uno empleados y aprendices en una sola lista
    personas = list(empleados) + list(aprendices)
    for emp in personas:
        # Inicializo acumuladores por mes
        data_meses = {mes: 0 for mes in meses}

        # Sumo de nómina
        nomina = PresupuestoNomina.objects.filter(cedula=emp.cedula).first()
        if nomina:
            for mes in meses:
                data_meses[mes] += getattr(nomina, mes, 0)
        
        # Sumo de comisiones
        comision = PresupuestoComisiones.objects.filter(cedula=emp.cedula).first()
        if comision:
            for mes in meses:
                data_meses[mes] += getattr(comision, mes, 0)

        # Sumo de medios de transporte
        medio = PresupuestoMediosTransporte.objects.filter(cedula=emp.cedula).first()
        if medio:
            for mes in meses:
                data_meses[mes] += getattr(medio, mes, 0)

        # Sumo de auxilio transporte
        aux = PresupuestoAuxilioTransporte.objects.filter(cedula=emp.cedula).first()
        if aux:
            for mes in meses:
                data_meses[mes] += getattr(aux, mes, 0)

        # Sumo de horas extra
        extra = PresupuestoHorasExtra.objects.filter(cedula=emp.cedula).first()
        if extra:
            for mes in meses:
                data_meses[mes] += getattr(extra, mes, 0)

        # Creo el registro en cesantías con la suma
        PresupuestoCesantiasAux.objects.create(
            cedula=emp.cedula,
            nombre=emp.nombre,
            centro=emp.centro,
            area=emp.area,
            cargo=emp.cargo,
            concepto="CESANTÍAS",
            **data_meses,
            total=sum(data_meses.values())
        )

    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_cesantias(request):
    if request.method == "POST":
        PresupuestoCesantias.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de cesantías eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

# ------------------------Prima------------------
def prima(request):
    return render(request, "presupuesto_nomina/prima.html")

def obtener_presupuesto_prima(request):
    prima = list(PresupuestoPrima.objects.values())
    return JsonResponse({"data": prima}, safe=False)

def tabla_auxiliar_prima(request):
    # obtener la prima desde la tabla auxiliar
    parametros = TablaAuxiliar.objects.first()
    prima = parametros.prima if parametros else 0
    return render(request, "presupuesto_nomina/aux_prima.html", {'prima': prima})

def subir_presupuesto_prima(request):
    if request.method == "POST":
        temporales = PresupuestoPrimaAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoPrima.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de prima subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_prima_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoPrimaAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoPrimaAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoPrimaAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_prima_temp(request):
    data = list(PresupuestoPrimaAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_prima_base(request):
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]

    # Limpio la tabla de cesantías antes de recalcular
    PresupuestoPrimaAux.objects.all().delete()

    # Tomo todos los empleados desde nómina (puede ser tu base principal)
    empleados = PresupuestoNomina.objects.all()
    # Tomo también los aprendices
    aprendices = PresupuestoAprendiz.objects.filter(concepto="SALARIO APRENDIZ REFORMA")
    # Uno empleados y aprendices en una sola lista
    personas = list(empleados) + list(aprendices)
    for emp in personas:
        # Inicializo acumuladores por mes
        data_meses = {mes: 0 for mes in meses}

        # Sumo de nómina
        for mes in meses:
            data_meses[mes] += getattr(emp, mes, 0)

        # Sumo de comisiones
        comision = PresupuestoComisiones.objects.filter(cedula=emp.cedula).first()
        if comision:
            for mes in meses:
                data_meses[mes] += getattr(comision, mes, 0)
                
        # Sumo de medios de transporte
        medio = PresupuestoMediosTransporte.objects.filter(cedula=emp.cedula).first()
        if medio:
            for mes in meses:
                data_meses[mes] += getattr(medio, mes, 0)

        # Sumo de auxilio transporte
        aux = PresupuestoAuxilioTransporte.objects.filter(cedula=emp.cedula).first()
        if aux:
            for mes in meses:
                data_meses[mes] += getattr(aux, mes, 0)

        # Sumo de horas extra
        extra = PresupuestoHorasExtra.objects.filter(cedula=emp.cedula).first()
        if extra:
            for mes in meses:
                data_meses[mes] += getattr(extra, mes, 0)

        # Creo el registro en cesantías con la suma
        PresupuestoPrimaAux.objects.create(
            cedula=emp.cedula,
            nombre=emp.nombre,
            centro=emp.centro,
            area=emp.area,
            cargo=emp.cargo,
            concepto="PRIMA LEGAL",
            **data_meses,
            total=sum(data_meses.values())
        )

    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_prima(request):
    if request.method == "POST":
        PresupuestoPrima.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de prima eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

# ------------------------Vacaciones------------------
def vacaciones(request):
    return render(request, "presupuesto_nomina/vacaciones.html")

def obtener_presupuesto_vacaciones(request):
    vacaciones = list(PresupuestoVacaciones.objects.values())
    return JsonResponse({"data": vacaciones}, safe=False)

def tabla_auxiliar_vacaciones(request):
    # obtener la vacaciones desde la tabla auxiliar
    parametros = TablaAuxiliar.objects.first()
    vacaciones = parametros.vacaciones if parametros else 0
    return render(request, "presupuesto_nomina/aux_vacaciones.html", {'vacaciones': vacaciones})

def subir_presupuesto_vacaciones(request):
    if request.method == "POST":
        temporales = PresupuestoVacacionesAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoVacaciones.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de vacaciones subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_vacaciones_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoVacacionesAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoVacacionesAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoVacacionesAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_vacaciones_temp(request):
    data = list(PresupuestoVacacionesAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_vacaciones_base(request):
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]

    # Limpio la tabla de cesantías antes de recalcular
    PresupuestoVacacionesAux.objects.all().delete()

    # Tomo todos los empleados desde nómina (puede ser tu base principal)
    empleados = PresupuestoNomina.objects.all()
    # Tomo también los aprendices
    aprendices = PresupuestoAprendiz.objects.filter(concepto="SALARIO APRENDIZ REFORMA")
    # Uno empleados y aprendices en una sola lista
    personas = list(empleados) + list(aprendices)
    for emp in personas:
        # Inicializo acumuladores por mes
        data_meses = {mes: 0 for mes in meses}

        # Sumo de nómina
        for mes in meses:
            data_meses[mes] += getattr(emp, mes, 0)

        # Sumo de comisiones
        comision = PresupuestoComisiones.objects.filter(cedula=emp.cedula).first()
        if comision:
            for mes in meses:
                data_meses[mes] += getattr(comision, mes, 0)
                
        # Sumo de medios de transporte
        medio = PresupuestoMediosTransporte.objects.filter(cedula=emp.cedula).first()
        if medio:
            for mes in meses:
                data_meses[mes] += getattr(medio, mes, 0)

        # Creo el registro en cesantías con la suma
        PresupuestoVacacionesAux.objects.create(
            cedula=emp.cedula,
            nombre=emp.nombre,
            centro=emp.centro,
            area=emp.area,
            cargo=emp.cargo,
            concepto="VACACIONES",
            **data_meses,
            total=sum(data_meses.values())
        )

    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_vacaciones(request):
    if request.method == "POST":
        PresupuestoVacaciones.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de vacaciones eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#----------------------------BONIFICACIONES----------------------
def bonificaciones(request):
    return render(request, "presupuesto_nomina/bonificaciones.html")

def obtener_presupuesto_bonificaciones(request):
    bonificaciones = list(PresupuestoBonificaciones.objects.values())
    return JsonResponse({"data": bonificaciones}, safe=False)

def tabla_auxiliar_bonificaciones(request):
    return render(request, "presupuesto_nomina/aux_bonificaciones.html")

def subir_presupuesto_bonificaciones(request):
    if request.method == "POST":
        temporales = PresupuestoBonificacionesAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoBonificaciones.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de bonificaciones subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_bonificaciones_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoBonificacionesAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoBonificacionesAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoBonificacionesAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_bonificaciones_temp(request):
    data = list(PresupuestoBonificacionesAux.objects.values())
    return JsonResponse(data, safe=False)

# para la carga de bonificaciones se toma el valor de cada mes de la nomina se divide entre 2 y luego entre 12
def cargar_bonificaciones_base(request):
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]

    # Limpio la tabla de bonificaciones antes de recalcular
    PresupuestoBonificacionesAux.objects.all().delete()

    # Tomo todos los empleados desde nómina (puede ser tu base principal)
    empleados = PresupuestoNomina.objects.all()

    for emp in empleados:
        # Inicializo acumuladores por mes
        data_meses = {mes: 0 for mes in meses}

        # Sumo de nómina y calculo bonificación
        for mes in meses:
            valor_mes = getattr(emp, mes, 0)
            bonificacion_mes = (valor_mes / 2) / 12  # Bonificación es la mitad del salario anual dividido entre 12
            data_meses[mes] += bonificacion_mes

        # Creo el registro en bonificaciones con la suma
        PresupuestoBonificacionesAux.objects.create(
            cedula=emp.cedula,
            nombre=emp.nombre,
            centro=emp.centro,
            area=emp.area,
            cargo=emp.cargo,
            concepto="BONIFICACIÓN",
            **data_meses,
            total=sum(data_meses.values())
        )

    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_bonificaciones(request):
    if request.method == "POST":
        PresupuestoBonificaciones.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de bonificaciones eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#------------auxilio movilidad (novedad de nomina extra, consumibles y tuberculina)----------------
def auxilio_movilidad(request):
    return render(request, "presupuesto_nomina/auxilio_movilidad.html")

def obtener_presupuesto_auxilio_movilidad(request):
    auxilio_movilidad = list(PresupuestoAuxilioMovilidad.objects.values())
    return JsonResponse({"data": auxilio_movilidad}, safe=False)

def tabla_auxiliar_auxilio_movilidad(request):
    parametros = TablaAuxiliar.objects.first()
    incremento_ipc = parametros.incremento_ipc if parametros else 0
    return render(request, "presupuesto_nomina/aux_auxilio_movilidad.html", {'incrementoIPC': incremento_ipc})

def subir_presupuesto_auxilio_movilidad(request):
    if request.method == "POST":
        temporales = PresupuestoAuxilioMovilidadAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoAuxilioMovilidad.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de auxilio de movilidad subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_auxilio_movilidad_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoAuxilioMovilidadAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoAuxilioMovilidadAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoAuxilioMovilidadAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_auxilio_movilidad_temp(request):
    data = list(PresupuestoAuxilioMovilidadAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_auxilio_movilidad_base(request):
    PresupuestoAuxilioMovilidadAux.objects.all().delete()  # limpia tabla temporal
    base_data = ConceptosFijosYVariables.objects.values(
        "cedula","nombre","nombrecar","nomcosto","nombre_cen", "nombre_con", "enero", "febrero", "marzo", "abril", "mayo",
        "junio", "julio", "agosto", "total"
    )

    # filtrar solo concepto que sea igual a 389
    base_data = base_data.filter(concepto="E14")
    
    for row in base_data:
        PresupuestoAuxilioMovilidadAux.objects.create(
            cedula=row["cedula"],
            nombre=row["nombre"],
            cargo=row["nombrecar"],
            area=row["nomcosto"],
            centro=row["nombre_cen"],
            concepto=row["nombre_con"],
            enero=row["enero"] or 0,
            febrero=row["febrero"] or 0,
            marzo=row["marzo"] or 0,
            abril=row["abril"] or 0,
            mayo=row["mayo"] or 0,
            junio=row["junio"] or 0,
            julio=row["julio"] or 0,
            agosto=row["agosto"] or 0,
            total=row["total"] or 0,
        )

        
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_auxilio_movilidad(request):
    if request.method == "POST":
        PresupuestoAuxilioMovilidad.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de auxilio de movilidad eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

# ----------------------------SEGURIDAD SOCIAL---------------------
def seguridad_social(request):
    return render(request, "presupuesto_nomina/seguridad_social.html")

def obtener_presupuesto_seguridad_social(request):
    seguridad_social = list(PresupuestoSeguridadSocial.objects.values())
    return JsonResponse({"data": seguridad_social}, safe=False)

def tabla_auxiliar_seguridad_social(request):
    return render(request, "presupuesto_nomina/aux_seguridad_social.html")

def subir_presupuesto_seguridad_social(request):
    if request.method == "POST":
        temporales = PresupuestoSeguridadSocialAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoSeguridadSocial.objects.create(
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                concepto=temp.concepto,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de seguridad social subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_seguridad_social_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoSeguridadSocialAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoSeguridadSocialAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoSeguridadSocialAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_seguridad_social_temp(request):
    data = list(PresupuestoSeguridadSocialAux.objects.values())
    return JsonResponse(data, safe=False)

# para obtener la seguridad social se debe agrupar las tablas de nomina, comisiones, horas extra y medios de transporte por sede(centro) y por area y sumar los valores de cada mes
from django.db.models import Avg
def cargar_seguridad_social_base(request):
    # Promedios agrupados por sede y área
    promedios_arl = ConceptosFijosYVariables.objects.values(
        "nombre_cen", "nomcosto"
    ).annotate(
        promedio_arl=Avg("arlporc")
    )
    
    # Diccionario: {(sede, area): promedio_arl}
    arl_porcentajes = {
        (item["nombre_cen"], item["nomcosto"]): (item["promedio_arl"] / 100.0)
        for item in promedios_arl if item["promedio_arl"] is not None
    }
    
    # imprimir el diccionario
    print(arl_porcentajes)
    
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]

    # Diccionario de conceptos con su porcentaje
    conceptos = {
        "APORTE PENSIÓN": 0.12,               # 12%
        "APORTE SALUD": 0.085,                # 8.5%
        "APORTE CAJAS DE COMPENSACIÓN": 0.04, # 4%
        "APORTE A.R.L": None,              # 0.931%
        "APORTE SENA": 0.02,                  # 2%
        "APORTE I.C.B.F": 0.03                # 3%
    }

    # Salario mínimo (ajusta según el año correspondiente)
    parametros = TablaAuxiliar.objects.first()
    salarioIncremento = parametros.salario_minimo + (parametros.salario_minimo * (parametros.incremento_salarial / 100))
    TOPE = (salarioIncremento) * 10
    
    # Limpio tabla antes de recalcular
    PresupuestoSeguridadSocialAux.objects.all().delete()

    # Diccionarios separados para acumulación
    acumulados_generales = defaultdict(lambda: {mes: 0 for mes in meses})  # pensión, cajas, ARL, SENA
    acumulados_salud_icbf = defaultdict(lambda: {mes: 0 for mes in meses})  # solo > 10 SMMLV
    acumulados_aprendiz_salud = defaultdict(lambda: {mes: 0 for mes in meses}) # aprendices con salario aprendiz

    empleados = PresupuestoNomina.objects.all()
    aprendices = PresupuestoAprendiz.objects.all()
    
    for emp in empleados:
        key = (emp.centro, emp.area)

        # Calcular base mensual del empleado (nomina + comision + medio + extra)
        base_empleado = {mes: getattr(emp, mes, 0) for mes in meses}

        # Comisiones
        comision = PresupuestoComisiones.objects.filter(cedula=emp.cedula).first()
        if comision:
            for mes in meses:
                base_empleado[mes] += getattr(comision, mes, 0)

        # Medios de transporte
        medio = PresupuestoMediosTransporte.objects.filter(cedula=emp.cedula).first()
        if medio:
            for mes in meses:
                base_empleado[mes] += getattr(medio, mes, 0)

        # Horas extra
        extra = PresupuestoHorasExtra.objects.filter(cedula=emp.cedula).first()
        if extra:
            for mes in meses:
                base_empleado[mes] += getattr(extra, mes, 0)

        
        # Sumar a los acumulados
        # → siempre suman a pensión, cajas, ARL y SENA
        for mes in meses:
            acumulados_generales[key][mes] += base_empleado[mes]

        salario_base = emp.salario_base
        nuevo_salario = salario_base + (salario_base * (parametros.incremento_salarial / 100))
        
        # → si excede los 10 SMMLV, también suma a salud e ICBF
        if nuevo_salario > TOPE:
            for mes in meses:
                acumulados_salud_icbf[key][mes] += base_empleado[mes]

    # === APRENDICES (tabla aparte) ===
    for apr in aprendices:
        if apr.concepto == "SALARIO APRENDIZ":
            key = (apr.centro, apr.area)
            for mes in meses:
                acumulados_aprendiz_salud[key][mes] += getattr(apr, mes, 0)
        if apr.concepto == "SALARIO APRENDIZ REFORMA":
            # además suman a todos los aportes (como parte de la base general)
            key = (apr.centro, apr.area)
            for mes in meses:
                acumulados_generales[key][mes] += getattr(apr, mes, 0)

    # Crear registros en la tabla
    for (centro, area), data_meses in acumulados_generales.items():
        for concepto, porcentaje in conceptos.items():
            if concepto in ["APORTE SALUD", "APORTE SENA", "APORTE I.C.B.F"]:
                data = None

                # 1. Si hay empleados > 10 SMMLV
                if (centro, area) in acumulados_salud_icbf:
                    data = acumulados_salud_icbf[(centro, area)]

                # 2. Si son aprendices con SALARIO APRENDIZ → solo para SALUD
                if concepto == "APORTE SALUD" and (centro, area) in acumulados_aprendiz_salud:
                    aprendiz_data = acumulados_aprendiz_salud[(centro, area)]
                    if data:
                        data = {mes: data[mes] + aprendiz_data[mes] for mes in meses}
                    else:
                        data = aprendiz_data

                    # sobrescribo el porcentaje SOLO para aprendices
                    porcentaje = 0.125 

                # Si no aplica, salto
                if not data:
                    continue
            elif concepto == "APORTE A.R.L":
                # Los aprendices con SALARIO APRENDIZ también deben aportar ARL
                data = data_meses.copy()
                if (centro, area) in acumulados_aprendiz_salud:
                    aprendiz_data = acumulados_aprendiz_salud[(centro, area)]
                    data = {mes: data[mes] + aprendiz_data[mes] for mes in meses}
                # aquí reemplazamos el porcentaje fijo con el promedio real
                porcentaje = arl_porcentajes.get((centro, area), 0.00931)
            else:
                data = data_meses

            valores_mensuales = {mes: round(data[mes] * porcentaje, 2) for mes in meses}
            PresupuestoSeguridadSocialAux.objects.create(
                nombre="SEGURIDAD SOCIAL",
                centro=centro,
                area=area,
                concepto=concepto,
                **valores_mensuales,
                total=round(sum(valores_mensuales.values()), 2)
            )
    # === AGRUPAR POR ÁREA LOS DE ASISTENCIA TÉCNICA ===
    asistencia = (
        PresupuestoSeguridadSocialAux.objects
        .filter(area__in=["ASISTENCIA TECNICA PROPIA", "ASISTENCIA TECNICA CONVENIO"])
        .values("area", "concepto")  # agrupamos por área y concepto
        .annotate(
            enero=Sum("enero"),
            febrero=Sum("febrero"),
            marzo=Sum("marzo"),
            abril=Sum("abril"),
            mayo=Sum("mayo"),
            junio=Sum("junio"),
            julio=Sum("julio"),
            agosto=Sum("agosto"),
            septiembre=Sum("septiembre"),
            octubre=Sum("octubre"),
            noviembre=Sum("noviembre"),
            diciembre=Sum("diciembre"),
            total=Sum("total"),
        )
    )
    
    # Insertar en la tabla como "ASISTENCIA TECNICA AGRUPADA"
    for item in asistencia:
        PresupuestoSeguridadSocialAux.objects.create(
            nombre="SEGURIDAD SOCIAL",
            centro="",  # omitimos centro
            area=item["area"],  # mantenemos el nombre de área original (PROPIA o CONVENIO)
            concepto=item["concepto"],
            enero=item["enero"] or 0,
            febrero=item["febrero"] or 0,
            marzo=item["marzo"] or 0,
            abril=item["abril"] or 0,
            mayo=item["mayo"] or 0,
            junio=item["junio"] or 0,
            julio=item["julio"] or 0,
            agosto=item["agosto"] or 0,
            septiembre=item["septiembre"] or 0,
            octubre=item["octubre"] or 0,
            noviembre=item["noviembre"] or 0,
            diciembre=item["diciembre"] or 0,
            total=item["total"] or 0,
        )
    # 2. Eliminamos las filas originales (con centro)
    PresupuestoSeguridadSocialAux.objects.filter(
        area__in=["ASISTENCIA TECNICA PROPIA", "ASISTENCIA TECNICA CONVENIO"]
    ).exclude(centro="").delete()
    

    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_seguridad_social(request):
    if request.method == "POST":
        PresupuestoSeguridadSocial.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de seguridad social eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#--------------------------INTERESES DE CESANTIAS----------------------
def intereses_cesantias(request):
    return render(request, "presupuesto_nomina/intereses_cesantias.html")

def obtener_presupuesto_intereses_cesantias(request):
    intereses_cesantias = list(PresupuestoInteresesCesantias.objects.values())
    return JsonResponse({"data": intereses_cesantias}, safe=False)

def tabla_auxiliar_intereses_cesantias(request):
    # obtener la cesantías desde la tabla auxiliar
    parametros = TablaAuxiliar.objects.first()
    interesesCesantias = parametros.intereses_cesantias if parametros else 0
    return render(request, "presupuesto_nomina/aux_intereses_cesantias.html", {'interesesCesantias': interesesCesantias})

def subir_presupuesto_intereses_cesantias(request):
    if request.method == "POST":
        temporales = PresupuestoInteresesCesantiasAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoInteresesCesantias.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de intereses de cesantías subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_intereses_cesantias_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoInteresesCesantiasAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoInteresesCesantiasAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoInteresesCesantiasAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_intereses_cesantias_temp(request):
    data = list(PresupuestoInteresesCesantiasAux.objects.values())
    return JsonResponse(data, safe=False)

# para la carga de intereses de cesantías se toma el valor de cada mes de la tabla de cesantias, esto para enero o sea el primer mes y para el mes siguiente se toma el valor de enero, se multiplica por el 200% y se suma el valor del mes anterior, esto hasta completar los 12 meses
def cargar_intereses_cesantias_base(request):
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]

    # parametrización
    parametros = TablaAuxiliar.objects.first()
    interesCesantias = parametros.intereses_cesantias if parametros else 0
    print(f"Intereses cesantías parámetro: {interesCesantias}")

    # limpio tabla auxiliar de intereses antes de recalcular
    PresupuestoInteresesCesantiasAux.objects.all().delete()

    # recorro cada registro de cesantías (por persona / fila)
    cesantias_qs = PresupuestoCesantias.objects.all()
    for reg in cesantias_qs:
        # monto base: enero del registro de cesantías
        base_enero = reg.enero or 0
        
        # si base_enero es 0, todos los meses serán 0; evitamos trabajo innecesario
        if base_enero == 0:
            valores = {m: 0 for m in meses}
        else:
            # enero_aux = enero_base * (1 + p)
            enero_aux = int(base_enero * interesCesantias / 100)

            # paso constante que se suma cada mes: enero_aux * p
            paso = (enero_aux * 2)

            valores = {}
            # enero = enero_aux
            valores["enero"] = enero_aux

            # iteración para febrero..diciembre
            anterior = enero_aux
            for i in range(1, len(meses)):
                actual = (anterior + paso)
                valores[meses[i]] = actual
                anterior = actual

        # suma total
        total = sum(Decimal(valores[m]) for m in meses)

        # si tu modelo usa IntegerField (como pareciera) convierto a int:
        # si prefieres decimales, elimina las conversiones a int y guarda Decimal/float
        create_kwargs = {m: int(round(float(valores[m]))) for m in meses}

        PresupuestoInteresesCesantiasAux.objects.create(
            cedula=reg.cedula,
            nombre=reg.nombre,
            centro=reg.centro,
            area=reg.area,
            cargo=reg.cargo,
            concepto="INTERESES CESANTÍAS",
            **create_kwargs,
            total=int(round(float(total)))
        )

    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_intereses_cesantias(request):
    if request.method == "POST":
        PresupuestoInteresesCesantias.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de intereses de cesantías eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#----------------------------APRENDIZ------------------
def aprendiz(request):
    return render(request, "presupuesto_nomina/aprendiz.html")

def obtener_presupuesto_aprendiz(request):
    aprendiz = list(PresupuestoAprendiz.objects.values())
    return JsonResponse({"data": aprendiz}, safe=False)

def tabla_auxiliar_aprendiz(request):
    parametros = TablaAuxiliar.objects.first()
    incrementoSalarial = parametros.incremento_salarial if parametros else 0
    return render(request, "presupuesto_nomina/aux_aprendiz.html", {'incrementoSalarial': incrementoSalarial})

def subir_presupuesto_aprendiz(request):
    if request.method == "POST":
        temporales = PresupuestoAprendizAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoAprendiz.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                salario_base=temp.salario_base,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de aprendices subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)  
    
def guardar_aprendiz_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "salario_base", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoAprendizAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoAprendizAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoAprendizAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_aprendiz_temp(request):
    data = list(PresupuestoAprendizAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_aprendiz_base(request):
    PresupuestoAprendizAux.objects.all().delete()  # limpia tabla temporal
    base_data = ConceptosFijosYVariables.objects.values(
        "cedula","nombre","nombrecar","nomcosto","nombre_cen", "nombre_con", "concepto_f")
    
    # filtrar solo concepto que sea igual a 003 y 006
    base_data = base_data.filter(concepto__in=["003", "006"])
    
    for row in base_data:
        PresupuestoAprendizAux.objects.create(
            cedula=row["cedula"],
            nombre=row["nombre"],
            cargo=row["nombrecar"],
            area=row["nomcosto"],
            centro=row["nombre_cen"],
            concepto=row["nombre_con"],
            salario_base=row["concepto_f"],
        )
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_aprendiz(request):
    if request.method == "POST":
        PresupuestoAprendiz.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de aprendices eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#--------------------------BONIFICACIONES FOCO----------------------
def bonificaciones_foco(request):
    return render(request, "presupuesto_nomina/bonificaciones_foco.html")

def obtener_presupuesto_bonificaciones_foco(request):
    bonificaciones_foco = list(PresupuestoBonificacionesFoco.objects.values())
    return JsonResponse({"data": bonificaciones_foco}, safe=False)

def tabla_auxiliar_bonificaciones_foco(request):
    return render(request, "presupuesto_nomina/aux_bonificaciones_foco.html")

def subir_presupuesto_bonificaciones_foco(request):
    if request.method == "POST":
        temporales = PresupuestoBonificacionesFocoAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoBonificacionesFoco.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de bonificaciones subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_bonificaciones_foco_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoBonificacionesFocoAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoBonificacionesFocoAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoBonificacionesFocoAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_bonificaciones_foco_temp(request):
    data = list(PresupuestoBonificacionesFocoAux.objects.values())
    return JsonResponse(data, safe=False)

# para la carga de bonificaciones foco se el valor total del mes de la tabla comisiones y se agrega al mes correspondiente en la tabla temporal de bonificaciones foco

def cargar_bonificaciones_foco_base(request):
    # limpio tabla auxiliar de bonificaciones antes de recalcular
    PresupuestoBonificacionesFocoAux.objects.all().delete()

    parametros = TablaAuxiliar.objects.first()
    incrementoComisiones = parametros.incremento_comisiones if parametros else 0

    
    # agrupamos por persona sumando los meses de enero a junio
    comisiones_agrupadas = (
        PresupuestoComisiones.objects
        .values("cedula", "nombre", "centro", "area", "cargo")
        .annotate(
            total=Sum("total"),        # total de todos los meses
            total_ene_jun=Sum("enero") + Sum("febrero") + Sum("marzo") + Sum("abril") + Sum("mayo") + Sum("junio"),
            enero=Sum("enero"),
            febrero=Sum("febrero"),
            marzo=Sum("marzo"),
            abril=Sum("abril"),
            mayo=Sum("mayo"),
            junio=Sum("junio"),
            julio=Sum("julio"),
            agosto=Sum("agosto"),
            septiembre=Sum("septiembre"),
            octubre=Sum("octubre"),
            noviembre=Sum("noviembre"),
            diciembre=Sum("diciembre"),
        )
    )

    for com in comisiones_agrupadas:
        # -------------------------
        # Cálculo para enero usando total anual / 12
        if com["total"] > 0:
            # Ajustar cada mes según incrementoComisiones
            incremento_factor = 1 + (incrementoComisiones / 100)
            enero_base = (com["enero"] or 0) / incremento_factor
            febrero_base = (com["febrero"] or 0) / incremento_factor
            marzo_base = (com["marzo"] or 0) / incremento_factor
            abril_base = (com["abril"] or 0) / incremento_factor
            mayo_base = (com["mayo"] or 0) / incremento_factor
            junio_base = (com["junio"] or 0) / incremento_factor
            julio_base = (com["julio"] or 0) / incremento_factor
            agosto_base = (com["agosto"] or 0) / incremento_factor
            septiembre_base = (com["septiembre"] or 0) / incremento_factor
            octubre_base = (com["octubre"] or 0) / incremento_factor
            noviembre_base = (com["noviembre"] or 0) / incremento_factor
            diciembre_base = (com["diciembre"] or 0) / incremento_factor
            total_ajustado = (
                enero_base + febrero_base + marzo_base + abril_base +
                mayo_base + junio_base + julio_base + agosto_base +
                septiembre_base + octubre_base + noviembre_base + diciembre_base
            )
            enero_valor = total_ajustado / 12

        # -------------------------
        # Cálculo para julio: promedio ene-jun / 2
        julio_valor = 0
        if com["total_ene_jun"] > 0:
            promedio_ene_jun = com["total_ene_jun"] / 6
            julio_valor = promedio_ene_jun / 2

        PresupuestoBonificacionesFocoAux.objects.create(
            cedula=com["cedula"],
            nombre=com["nombre"],
            centro=com["centro"],
            area=com["area"],
            cargo=com["cargo"],
            concepto="BONIFICACIÓN FOCO",
            enero=enero_valor,
            febrero=0,
            marzo=0,
            abril=0,
            mayo=0,
            junio=0,
            julio=julio_valor,
            agosto=0,
            septiembre=0,
            octubre=0,
            noviembre=0,
            diciembre=0,
            total=enero_valor + julio_valor,  # suma lo de enero y julio
        )
    
    # 2️⃣ Empleados de ConceptosFijosYVariables filtrando COMISIONES y excluyendo ciertos cargos
    cargos_excluidos = [
        "ASESOR COMERCIAL",
        "AUXILIAR COMERCIAL",
        "JEFE DE ALMACEN",
        "DIRECTOR COMERCIAL SUBDISTRIBUCION Y DIGITAL",
        "DIRECTOR COMERCIAL GRANDES ESPECIES Y PUNTO VENTA",
    ]
    
    empleados_fijos = (
        PresupuestoNomina.objects
        .exclude(cargo__in=cargos_excluidos)
        .values("cedula", "nombre", "centro", "area", "cargo")
        .annotate(total=Sum("total"))
    )
    
    # 2️⃣ Insertar en la tabla de bonificaciones con enero = 220000 + IPC
    for emp in empleados_fijos:
        enero_valor = 220000 * (1 + incrementoComisiones / 100)
        PresupuestoBonificacionesFocoAux.objects.create(
            cedula=emp["cedula"],
            nombre=emp["nombre"],
            centro=emp["centro"],
            area=emp["area"],
            cargo=emp["cargo"],
            concepto="BONIFICACIÓN FOCO",
            enero=enero_valor,
            febrero=0,
            marzo=0,
            abril=0,
            mayo=0,
            junio=0,
            julio=0,
            agosto=0,
            septiembre=0,
            octubre=0,
            noviembre=0,
            diciembre=0,
            total=enero_valor,  # solo enero por ahora
        )


    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_bonificaciones_foco(request):
    if request.method == "POST":
        PresupuestoBonificacionesFoco.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de bonificaciones foco eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#------------------------AUXILIO EDUCACION----------------------
def auxilio_educacion(request):
    return render(request, "presupuesto_nomina/auxilio_educacion.html")

def obtener_presupuesto_auxilio_educacion(request):
    auxilio_educacion = list(PresupuestoAuxilioEducacion.objects.values())
    return JsonResponse({"data": auxilio_educacion}, safe=False)

def tabla_auxiliar_auxilio_educacion(request):
    return render(request, "presupuesto_nomina/aux_auxilio_educacion.html")

def subir_presupuesto_auxilio_educacion(request):
    if request.method == "POST":
        temporales = PresupuestoAuxilioEducacionAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoAuxilioEducacion.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de auxilio de educación subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)

def guardar_auxilio_educacion_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoAuxilioEducacionAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoAuxilioEducacionAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoAuxilioEducacionAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)


def obtener_auxilio_educacion_temp(request):
    data = list(PresupuestoAuxilioEducacionAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_auxilio_educacion_base(request):
    # limpio tabla auxiliar de auxilio educación antes de recalcular
    PresupuestoAuxilioEducacionAux.objects.all().delete()
    base_data = ConceptoAuxilioEducacion.objects.values(
        "cedula","nombre","nombrecar","nomcosto","nombre_cen","diciembre", "nombre_con", "total"
    )
    # filtrar solo concepto = 001
    base_data = base_data.filter(concepto="016")
    
    parametros = TablaAuxiliar.objects.first()
    incrementoIPC = parametros.incremento_ipc if parametros else 0
    
    for row in base_data:
        diciembreIncremento = row["diciembre"] * (1 + incrementoIPC / 100)
        PresupuestoAuxilioEducacionAux.objects.create(
            cedula=row["cedula"],
            nombre=row["nombre"],
            cargo=row["nombrecar"],
            area=row["nomcosto"],
            centro=row["nombre_cen"],
            concepto=row["nombre_con"],
            diciembre=diciembreIncremento,
            total=diciembreIncremento,
        )
    
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_auxilio_educacion(request):
    if request.method == "POST":
        PresupuestoAuxilioEducacion.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de auxilio de educación eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#------------------------BONOS KYROVET----------------------
def bonos_kyrovet(request):
    return render(request, "presupuesto_nomina/bonos_kyrovet.html")

def obtener_presupuesto_bonos_kyrovet(request):
    bonos_kyrovet = list(PresupuestoBonosKyrovet.objects.values())
    return JsonResponse({"data": bonos_kyrovet}, safe=False)

def tabla_auxiliar_bonos_kyrovet(request):
    parametros = TablaAuxiliar.objects.first()
    incrementoIPC = parametros.incremento_ipc if parametros else 0
    return render(request, "presupuesto_nomina/aux_bonos_kyrovet.html", {'incrementoIPC': incrementoIPC})

def subir_presupuesto_bonos_kyrovet(request):
    if request.method == "POST":
        temporales = PresupuestoBonosKyrovetAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        for temp in temporales:
            PresupuestoBonosKyrovet.objects.create(
                cedula=temp.cedula,
                nombre=temp.nombre,
                centro=temp.centro,
                area = temp.area,
                cargo=temp.cargo,
                concepto=temp.concepto,
                base=temp.base,
                enero=temp.enero,
                febrero=temp.febrero,
                marzo=temp.marzo,
                abril=temp.abril,
                mayo=temp.mayo,
                junio=temp.junio,
                julio=temp.julio,
                agosto=temp.agosto,
                septiembre=temp.septiembre,
                octubre=temp.octubre,
                noviembre=temp.noviembre,
                diciembre=temp.diciembre,
                total=temp.total,
            )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de bonos Kyrovet subido ✅"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_bonos_kyrovet_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto","base", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

            # Limpiar la tabla antes de guardar
            PresupuestoBonosKyrovetAux.objects.all().delete()

            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}

                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo",
                    "junio","julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0

                registros.append(PresupuestoBonosKyrovetAux(**row_filtrado))

            # Inserción masiva optimizada
            PresupuestoBonosKyrovetAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_bonos_kyrovet_temp(request):
    data = list(PresupuestoBonosKyrovetAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_bonos_kyrovet_base(request):
    # limpio tabla auxiliar de bonos kyrovet antes de recalcular
    PresupuestoBonosKyrovetAux.objects.all().delete()
    base_data = ConceptosFijosYVariables.objects.values(
        "cedula","nombre","nombrecar","nomcosto","nombre_cen", "nombre_con", "concepto_f"
    )
    # filtrar solo concepto = 001
    base_data = base_data.filter(nombre_con="BONO CANASTA KYROVET")
    parametros = TablaAuxiliar.objects.first()
    incrementoIPC = parametros.incremento_ipc if parametros else 0
   
    for row in base_data:
        febreroIncremento = row["concepto_f"] * (1 + incrementoIPC / 100)
        PresupuestoBonosKyrovetAux.objects.create(
            cedula=row["cedula"],
            nombre=row["nombre"],
            cargo=row["nombrecar"],
            area=row["nomcosto"],
            centro=row["nombre_cen"],
            concepto=row["nombre_con"],
            base=row["concepto_f"],
            febrero=febreroIncremento,
            total=febreroIncremento,
        )
    
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_bonos_kyrovet(request):
    if request.method == "POST":
        PresupuestoBonosKyrovet.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de bonos Kyrovet eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)