from collections import defaultdict
import datetime
from decimal import Decimal
from itertools import chain
from pyexpat.errors import messages
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
import pandas as pd
from .models import BdVentas2020, BdVentas2021, BdVentas2022, BdVentas2023, BdVentas2024, BdVentas2025, ParametrosPresupuestos, PresupuestoSueldos, PresupuestoSueldosAux, ConceptosFijosYVariables, PresupuestoComisiones, PresupuestoComisionesAux, PresupuestoHorasExtra, PresupuestoHorasExtraAux, PresupuestoMediosTransporte, PresupuestoMediosTransporteAux, PresupuestoAuxilioTransporte, PresupuestoAuxilioTransporteAux, PresupuestoAyudaTransporte, PresupuestoAyudaTransporteAux, PresupuestoCesantias, PresupuestoCesantiasAux, PresupuestoPrima, PresupuestoPrimaAux, PresupuestoVacaciones, PresupuestoVacacionesAux, PresupuestoBonificaciones, PresupuestoBonificacionesAux, PresupuestoAprendiz, PresupuestoAprendizAux, PresupuestoBolsaConsumibles, PresupuestoBolsaConsumiblesAux, PresupuestoAuxilioTBCKIT, PresupuestoAuxilioTCBKITAux, PresupuestoSeguridadSocial, PresupuestoSeguridadSocialAux, PresupuestoInteresesCesantias, PresupuestoInteresesCesantiasAux, PresupuestoBonificacionesFoco, PresupuestoBonificacionesFocoAux, PresupuestoAuxilioEducacion, PresupuestoAuxilioEducacionAux, ConceptoAuxilioEducacion, PresupuestoBonosKyrovet, PresupuestoBonosKyrovetAux, PresupuestoGeneralVentas, PresupuestoCentroOperacionVentas, PresupuestoCentroSegmentoVentas, PresupuestoGeneralCostos, PresupuestoCentroOperacionCostos, PresupuestoCentroSegmentoCostos, PresupuestoComercial, Plantillagastos2025, PresupuestoTecnologia, PresupuestoTecnologiaAux, CuentasContables, PresupuestotecnologiaAprobado, PresupuestoOcupacional, PresupuestoOcupacionalAux, PresupuestoOcupacionalAprobado, PresupuestoServiciosTecnicos, PresupuestoServiciosTecnicosAux, PresupuestoServiciosTecnicosAprobado, PresupuestoLogistica, PresupuestoLogisticaAux, PresupuestoLogisticaAprobado, PresupuestoGestionRiesgos, PresupuestoGestionRiesgosAux, PresupuestoGestionRiesgosAprobado, PresupuestoGH, PresupuestoGHAux, PresupuestoGHAprobado, PresupuestoAlmacenTulua, PresupuestoAlmacenTuluaAux, PresupuestoAlmacenTuluaAprobado, PresupuestoAlmacenBuga, PresupuestoAlmacenBugaAux, PresupuestoAlmacenBugaAprobado, PresupuestoAlmacenCartago, PresupuestoAlmacenCartagoAux, PresupuestoAlmacenCartagoAprobado, PresupuestoAlmacenCali, PresupuestoAlmacenCaliAux, PresupuestoAlmacenCaliAprobado, PresupuestoComunicaciones, PresupuestoComunicacionesAux, PresupuestoComunicacionesAprobado, PresupuestoComercialCostos, PresupuestoComercialCostosAux, PresupuestoComercialCostosAprobado, PresupuestoContabilidad, PresupuestoContabilidadAux, PresupuestoContabilidadAprobado, PresupuestoGerencia, PresupuestoGerenciaAux, PresupuestoGerenciaAprobado, Cuenta5, Cuenta5Base
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.db.models.functions import Concat
from django.db.models import Sum, Max, Q
from django.db import transaction
import numpy as np
import json
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.db import models
from django.core.paginator import Paginator

def exportar_excel_nomina(request):
    # Obtener datos de cada tabla
    nomina = list(PresupuestoSueldos.objects.values())
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
    auxilio_movilidad = list(PresupuestoBolsaConsumibles.objects.values())
    aprendiz = list(PresupuestoAprendiz.objects.values())
    auxilio_TBCKIT = list(PresupuestoAuxilioTBCKIT.objects.values())
    auxilio_educacion = list(PresupuestoAuxilioEducacion.objects.values())
    bonificaciones_foco = list(PresupuestoBonificacionesFoco.objects.values())
    bonos_kyrovet = list(PresupuestoBonosKyrovet.objects.values())
    seguridad_social = list(PresupuestoSeguridadSocial.objects.values())

    # Crear DataFrames con columna de origen
    def prepare_df(data, origen):
        df = pd.DataFrame(data)
        if not df.empty:
            df["origen"] = origen
            # 🔹 Asegurar que no haya datetime con timezone
            for col in df.select_dtypes(include=["datetimetz"]).columns:
                df[col] = df[col].dt.tz_localize(None)
        return df

    df_nomina = prepare_df(nomina, "Nomina")
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
    df_auxilio_TBCKIT = prepare_df(auxilio_TBCKIT, "Auxilio Movilidad")
    df_auxilio_educacion = prepare_df(auxilio_educacion, "Auxilio Educación")
    df_bonificaciones_foco = prepare_df(bonificaciones_foco, "Bonificaciones Foco")
    df_bonos_kyrovet = prepare_df(bonos_kyrovet, "Bonos Kyrovet")
    df_seguridad_social = prepare_df(seguridad_social, "Seguridad Social")

    # Concatenar todos en un solo DataFrame
    df_final = pd.concat(
        [df_nomina, df_comisiones, df_horas_extra, df_auxilio_transporte, df_medios_transporte, df_ayuda_transporte, df_cesantias, df_intereses_cesantias, df_prima, df_vacaciones, df_bonificaciones, df_auxilio_movilidad, df_aprendiz, df_auxilio_TBCKIT, df_auxilio_educacion, df_bonificaciones_foco, df_bonos_kyrovet, df_seguridad_social],
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

@login_required
def dashboard_home(request):
    USUARIOS_PERMITIDOS= ['admin', 'NICOLAS']
    if request.user.username not in USUARIOS_PERMITIDOS:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    return render(request, 'presupuesto_consolidado/dashboard_presupuestos.html')

def exportar_excel_presupuestos(request):
    # Obtener datos de cada tabla
    tecnologia = PresupuestotecnologiaAprobado.objects.values()
    servicios_tecnicos = PresupuestoServiciosTecnicosAprobado.objects.values()
    logistica = PresupuestoLogisticaAprobado.objects.values()
    gestion_riesgos = PresupuestoGestionRiesgosAprobado.objects.values()
    gh = PresupuestoGHAprobado.objects.values()
    almacen_tulua = PresupuestoAlmacenTuluaAprobado.objects.values()
    almacen_buga = PresupuestoAlmacenBugaAprobado.objects.values()
    almacen_cartago = PresupuestoAlmacenCartagoAprobado.objects.values()
    almacen_cali = PresupuestoAlmacenCaliAprobado.objects.values()
    comunicaciones = PresupuestoComunicacionesAprobado.objects.values()
    comercial_costos = PresupuestoComercialCostosAprobado.objects.values()
    contabilidad = PresupuestoContabilidadAprobado.objects.values()
    gerencia = PresupuestoGerenciaAprobado.objects.values()
    
    # filtrar por ultima version todas las tablas
    tecnologia = tecnologia.filter(version=tecnologia.aggregate(Max('version'))['version__max'])
    servicios_tecnicos = servicios_tecnicos.filter(version=servicios_tecnicos.aggregate(Max('version'))['version__max'])
    logistica = logistica.filter(version=logistica.aggregate(Max('version'))['version__max'])
    gestion_riesgos = gestion_riesgos.filter(version=gestion_riesgos.aggregate(Max('version'))['version__max'])
    gh = gh.filter(version=gh.aggregate(Max('version'))['version__max'])
    almacen_tulua = almacen_tulua.filter(version=almacen_tulua.aggregate(Max('version'))['version__max'])
    almacen_buga = almacen_buga.filter(version=almacen_buga.aggregate(Max('version'))['version__max'])
    almacen_cartago = almacen_cartago.filter(version=almacen_cartago.aggregate(Max('version'))['version__max'])
    almacen_cali = almacen_cali.filter(version=almacen_cali.aggregate(Max('version'))['version__max'])
    comunicaciones = comunicaciones.filter(version=comunicaciones.aggregate(Max('version'))['version__max'])
    comercial_costos = comercial_costos.filter(version=comercial_costos.aggregate(Max('version'))['version__max'])
    contabilidad = contabilidad.filter(version=contabilidad.aggregate(Max('version'))['version__max'])
    gerencia = gerencia.filter(version=gerencia.aggregate(Max('version'))['version__max'])
    
    # Crear DataFrames con columna de origen
    def prepare_df(data, origen):
        df = pd.DataFrame(data)
        if not df.empty:
            df["origen"] = origen # Agregar columna de origen
        return df
    df_tecnologia = prepare_df(tecnologia, "Tecnología")
    df_servicios_tecnicos = prepare_df(servicios_tecnicos, "Servicios Técnicos")
    df_logistica = prepare_df(logistica, "Logística")
    df_gestion_riesgos = prepare_df(gestion_riesgos, "Gestión de Riesgos")
    df_gh = prepare_df(gh, "GH")
    df_almacen_tulua = prepare_df(almacen_tulua, "Almacén Tuluá")
    df_almacen_buga = prepare_df(almacen_buga, "Almacén Buga")
    df_almacen_cartago = prepare_df(almacen_cartago, "Almacén Cartago")
    df_almacen_cali = prepare_df(almacen_cali, "Almacén Cali")
    df_comunicaciones = prepare_df(comunicaciones, "Comunicaciones")
    df_comercial_costos = prepare_df(comercial_costos, "Comercial Gastos")
    df_contabilidad = prepare_df(contabilidad, "Contabilidad") 
    df_gerencia = prepare_df(gerencia, "Gerencia")
    
    # Concatenar todos en un solo DataFrame
    df_final = pd.concat(
        [df_tecnologia, df_servicios_tecnicos, df_logistica, df_gestion_riesgos, df_gh, df_almacen_tulua, df_almacen_buga, df_almacen_cartago, df_almacen_cali, df_comunicaciones, df_comercial_costos, df_contabilidad, df_gerencia],
        ignore_index=True
    )
    
    # pivot de columna que son meses a filas (enero, febrero, marzo, abril, mayo, junio, julio, agosto, septiembre, octubre, noviembre, diciembre) 
    meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    df_final = df_final.melt(id_vars=[col for col in df_final.columns if col not in meses], value_vars=meses, var_name='mes', value_name='valor')
    
    # Crear la respuesta HTTP para Excel
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="Presupuestos_Todo.xlsx"'
    # Exportar a una sola hoja
    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        df_final.to_excel(writer, sheet_name="Presupuestos", index=False)
    return response

def exportar_nomina_vertical(request):
    nomina = PresupuestoSueldos.objects.values()
    comisiones = PresupuestoComisiones.objects.values()
    horas_extra = PresupuestoHorasExtra.objects.values()
    auxlio_transporte = PresupuestoAuxilioTransporte.objects.values()
    medios_transporte = PresupuestoMediosTransporte.objects.values()
    ayuda_transporte = PresupuestoAyudaTransporte.objects.values()
    cesantias = PresupuestoCesantias.objects.values()
    intereses_cesantias = PresupuestoInteresesCesantias.objects.values()
    prima = PresupuestoPrima.objects.values()
    vacaciones = PresupuestoVacaciones.objects.values()
    bonificaciones = PresupuestoBonificaciones.objects.values()
    auxilio_movilidad = PresupuestoBolsaConsumibles.objects.values()
    aprendiz = PresupuestoAprendiz.objects.values()
    auxilio_TBCKIT = PresupuestoAuxilioTBCKIT.objects.values()
    auxilio_educacion = PresupuestoAuxilioEducacion.objects.values()
    bonificaciones_foco = PresupuestoBonificacionesFoco.objects.values()
    bonos_kyrovet = PresupuestoBonosKyrovet.objects.values()
    seguridad_social = PresupuestoSeguridadSocial.objects.values()
    
    # crear dataframes con columna de origen
    def prepare_df(data, origen):
        df = pd.DataFrame(data)
        if not df.empty:
            df["origen"] = origen
            # asegurar que no haya datetime con timezone
            for col in df.select_dtypes(include=["datetimetz"]).columns:
                df[col] = df[col].dt.tz_localize(None)
        return df
    
    df_nomina = prepare_df(nomina, "Sueldos")
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
    df_auxilio_TBCKIT = prepare_df(auxilio_TBCKIT, "Auxilio Movilidad")
    df_auxilio_educacion = prepare_df(auxilio_educacion, "Auxilio Educación")
    df_bonificaciones_foco = prepare_df(bonificaciones_foco, "Bonificaciones Foco")
    df_bonos_kyrovet = prepare_df(bonos_kyrovet, "Bonos Kyrovet")
    df_seguridad_social = prepare_df(seguridad_social, "Seguridad Social")
    
    # concatenar todos en un solo dataframe
    df_final = pd.concat(
        [df_nomina, df_comisiones, df_horas_extra, df_auxilio_transporte, df_medios_transporte, df_ayuda_transporte, df_cesantias, df_intereses_cesantias, df_prima, df_vacaciones, df_bonificaciones, df_auxilio_movilidad, df_aprendiz, df_auxilio_TBCKIT, df_auxilio_educacion, df_bonificaciones_foco, df_bonos_kyrovet, df_seguridad_social],
        ignore_index=True
    )
    # pivot de columna que son meses a filas (enero, febrero, marzo, abril, mayo, junio, julio, agosto, septiembre, octubre, noviembre, diciembre)
    meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    df_final = df_final.melt(id_vars=[col for col in df_final.columns if col not in meses], value_vars=meses, var_name='mes', value_name='valor')
    
    # Crear la respuesta HTTP para Excel
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="Presupuesto_Nomina_Vertical.xlsx"'
    # Exportar a una sola hoja
    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        df_final.to_excel(writer, sheet_name="Presupuesto Nómina", index=False)
    return response

@login_required
def base_comercial(request):
    # ✅ Permitir solo a ciertos usuarios por username
    usuarios_permitidos = ['admin', 'AGRAJALE', 'EVALENCIA', 'SCORTES']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    return render(request, 'presupuesto_comercial/base_presupuesto_comercial.html')

# ------------------------------------------PRESUPUESTO GENERAL VENTAS-----------------------------------------------------
def cargar_presupuesto_general_ventas(request):
    # de los productos que pertenecen a la linea_n1
    bd2020 = BdVentas2020.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2021 = BdVentas2021.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2022 = BdVentas2022.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2023 = BdVentas2023.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2024 = BdVentas2024.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2025 = BdVentas2025.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    
    df1 = pd.DataFrame(list(bd2020))
    df2 = pd.DataFrame(list(bd2021))
    df3 = pd.DataFrame(list(bd2022))
    df4 = pd.DataFrame(list(bd2023))
    df5 = pd.DataFrame(list(bd2024))
    df6 = pd.DataFrame(list(bd2025))
    
    year_actual = timezone.now().year
    year_siguiente = timezone.now().year + 1
    
    df_total = pd.concat([df1, df2, df3, df4, df5, df6], ignore_index=True)
    # print(df_total)
    # calcular suma por lapso y centro de operacion
    df_lapso_total = df_total.groupby('lapso')['suma'].sum().reset_index()
    
    # ------------PROYECCION PRESUPUESTO GENERAL - CALUCLAR PREDICCIÓN PARA 2025 POR CADA MES -----------------------------------------
    # Extraer año y mes
    df_lapso_total['year'] = df_lapso_total['lapso'] // 100
    df_lapso_total['mes'] = df_lapso_total['lapso'] % 100
    
    # df_por_year_mes = df_lapso_total.groupby(["year", "mes"])["suma"].sum().reset_index()
    
    # calcular predicción para 2025 por cada mes usando regresión lineal
    # predicciones_2026_general = []
    # # recorrer cada mes (1 a 12)
    # for mes in range(1, 13):
    #     datos_mes = df_por_year_mes[df_por_year_mes["mes"] == mes]

    #     x = datos_mes["year"].values
    #     y = datos_mes["suma"].values

    #     if len(x) >= 2:  # se necesitan al menos 2 años
    #         a, b = np.polyfit(x, y, 1)  # ajuste lineal
    #         y_pred = a * year_siguiente + b
    #         predicciones_2026_general.append({
    #             "year": year_siguiente,
    #             "mes": mes,
    #             "suma_pred": round(y_pred),
    #             "lapso": year_siguiente * 100 + mes
    #         })

    # convertir a dataframe
    # df_pred_2025_general = pd.DataFrame(predicciones_2026_general)
    # unir con df_por_year_mes
    df_proyeccion_general = pd.concat([df_lapso_total[['lapso', 'suma']]], ignore_index=True)
    
    df_proyeccion_general['year'] = df_proyeccion_general['lapso'] // 100
    df_por_año = df_proyeccion_general.groupby("year")["suma"].sum().reset_index()
    df_por_año = df_por_año.sort_values("year").reset_index(drop=True)
    df_por_año["variacion_pesos"] = (df_por_año["suma"].diff()).round().astype('Int64')
    df_por_año["variacion_pct"] = (df_por_año["suma"].pct_change() * 100).round(2)
    df_por_año["variacion_pct"] = df_por_año["variacion_pct"].fillna(0)
    df_por_año["variacion_pesos"] = df_por_año["variacion_pesos"].fillna(0) 
    # renombrar suma por total
    df_por_año = df_por_año.rename(columns={'suma': 'total'})
    
    # ================== COSTOS: total_year ==============================
    costos = PresupuestoGeneralCostos.objects.values("year", "total_year")
    df_costos = pd.DataFrame(list(costos)).rename(columns={"total_year": "total_year_costos"})

    # Merge ventas + costos
    df_por_año = pd.merge(df_por_año, df_costos, on="year", how="left")
    
    #extrer año y mes
    df_proyeccion_general['mes'] = df_proyeccion_general['lapso'] % 100
    # calcular el coeficiente de correlación R2 para la proyección general---
    correlaciones = []
    for mes in range(1, 13):
        datos_mes = df_proyeccion_general[df_proyeccion_general["mes"] == mes]

        if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
            coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
        else:
            coef = np.nan  # si no hay variación, correlación indefinida

        correlaciones.append({
            "mes": mes,
            "coef_correlacion": (round(coef, 4))*100 if not np.isnan(coef) else None
        })
    
    df_correl_por_mes = pd.DataFrame(correlaciones)
    
    # unir con el df_proyeccion_centro_operacion
    df_proyeccion_general = pd.merge(df_proyeccion_general, df_correl_por_mes, on='mes', how='left')
    df_proyeccion_general['suma'] = df_proyeccion_general['suma'].round().astype(int)

    # merge de df_proyeccion_general con df_por_año para agregar las columnas de variacion_pesos y variacion_pct
    df_proyeccion_general = pd.merge(df_proyeccion_general, df_por_año[['year', 'total', 'total_year_costos','variacion_pesos', 'variacion_pct']], on='year', how='left')
    # calcular utilidad por año, 1 - (costos / ventas), el costo está en el df_proyeccion_general y se encuentra en la columna total_year_costos, y las ventas están en la columna total
    df_proyeccion_general['utilidad_pct'] = (1 - (df_proyeccion_general['total_year_costos'] / df_proyeccion_general['total'])) * 100
    df_proyeccion_general['utilidad_pct'] = df_proyeccion_general['utilidad_pct'].round(2)
    # llenar los valores infinitos o NaN con 0
    df_proyeccion_general['utilidad_pct'] = df_proyeccion_general['utilidad_pct'].replace([np.inf, -np.inf], 0).fillna(0)
    # utilidad en valor
    df_proyeccion_general['utilidad_valor'] = df_proyeccion_general['total'] - df_proyeccion_general['total_year_costos']
    df_proyeccion_general['utilidad_valor'] = df_proyeccion_general['utilidad_valor'].round().astype(int)
    
    # 🔹 AGREGAR LOS 12 MESES DE 2026 CON VALORES EN CERO
    meses_2026 = pd.DataFrame([{
        "lapso": 202600 + m,
        "year": 2026,
        "mes": m,
        "suma": 0,
        "coef_correlacion": 0,
        "total": 0,
        "total_year_costos": 0,
        "variacion_pesos": 0,
        "variacion_pct": 0,
        "utilidad_pct": 0,
        "utilidad_valor": 0
    } for m in range(1, 13)])
    # unir con df_proyeccion_general
    df_proyeccion_general = pd.concat([df_proyeccion_general, meses_2026], ignore_index=True)
    # ----------- GUARDAR EN LA BD ------------
    registros = []
    for _, row in df_proyeccion_general.iterrows():
        registros.append(
            PresupuestoGeneralVentas(
                year=int(row['year']),
                mes=int(row['mes']),
                total=int(row['suma']),
                r2=row['coef_correlacion'] if row['coef_correlacion'] is not None else 0,
                total_year=row['total'] if row['total'] is not None else 0,
                total_year_costos=row['total_year_costos'] if row['total_year_costos'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0,
                utilidad_pct=row['utilidad_pct'] if row['utilidad_pct'] is not None else 0,
                utilidad_valor=row['utilidad_valor'] if row['utilidad_valor'] is not None else 0,
            )
        )

    with transaction.atomic():
        # Opcional: limpiar tabla antes de insertar para evitar duplicados
        PresupuestoGeneralVentas.objects.all().delete()
        PresupuestoGeneralVentas.objects.bulk_create(registros)
    
    data = list(PresupuestoGeneralVentas.objects.values())
    return JsonResponse(data, safe=False) 

@csrf_exempt
def guardar_presupuesto_general_ventas(request):
    print("Guardar presupuesto general ventas")
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # 📥 datos editados del DataTable
            df = pd.DataFrame(data)

            # --- asegurarse de que los tipos sean correctos ---
            df["year"] = df["year"].astype(int)
            df["mes"] = df["mes"].astype(int)
            df["total"] = df["total"].astype(int)

            # --- recalcular coeficiente de correlación R² por mes ---
            correlaciones = []
            for mes in range(1, 13):
                datos_mes = df[df["mes"] == mes]

                if len(datos_mes) >= 2 and datos_mes["total"].std() != 0:
                    coef = np.corrcoef(datos_mes["year"], datos_mes["total"])[0, 1]
                else:
                    coef = np.nan

                correlaciones.append({
                    "mes": mes,
                    "coef_correlacion": (round(coef, 4)) * 100 if not np.isnan(coef) else 0
                })

            df_correl = pd.DataFrame(correlaciones)

            # unir correlaciones recalculadas con los datos originales
            df = pd.merge(df, df_correl, on="mes", how="left")

            # --- guardar en la BD ---
            registros = []
            for _, row in df.iterrows():
                registros.append(
                    PresupuestoGeneralVentas(
                        year=int(row["year"]),
                        mes=int(row["mes"]),
                        total=int(row["total"]),
                        r2=row["coef_correlacion"]
                    )
                )

            PresupuestoGeneralVentas.objects.all().delete()
            PresupuestoGeneralVentas.objects.bulk_create(registros)

            data = list(PresupuestoGeneralVentas.objects.values())
            return JsonResponse(data, safe=False)

        except Exception as e:
            return JsonResponse({"status": "error", "mensaje": str(e)}, status=400)

    return JsonResponse({"status": "error", "mensaje": "Método no permitido"}, status=405)

def obtener_presupuesto_general_ventas(request):
    data = list(PresupuestoGeneralVentas.objects.values())
    return JsonResponse(data, safe=False)

def vista_presupuesto_general_ventas(request):
    return render(request, 'presupuesto_comercial/presupuesto_general_ventas.html')

# --------------------------PRESUPUESTO POR CENTRO OPERACION VENTAS------------------------
def cargar_presupuesto_centro_ventas(request):
    # obtener la suma de cada mes y nombre_linea_n1 es decir, si el lapso es 202001 retornar la suma
    # de los productos que pertenecen a la linea_n1
    bd2020 = BdVentas2020.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2021 = BdVentas2021.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2022 = BdVentas2022.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2023 = BdVentas2023.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2024 = BdVentas2024.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2025 = BdVentas2025.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    
    df1 = pd.DataFrame(list(bd2020))
    df2 = pd.DataFrame(list(bd2021))
    df3 = pd.DataFrame(list(bd2022))
    df4 = pd.DataFrame(list(bd2023))
    df5 = pd.DataFrame(list(bd2024))
    df6 = pd.DataFrame(list(bd2025))
    
    year_actual = timezone.now().year
    year_siguiente = timezone.now().year + 1
    
    df_total = pd.concat([df1, df2, df3, df4, df5, df6], ignore_index=True)
    df_centro_operacion = df_total.groupby(['nombre_centro_de_operacion', 'lapso'])['suma'].sum().reset_index()
    df_centro_operacion = df_centro_operacion.rename(columns={"nombre_centro_de_operacion": "nombre_centro_operacion"})
    
    # Extraer año y mes
    df_centro_operacion['year'] = df_centro_operacion['lapso'] // 100
    df_centro_operacion['mes'] = df_centro_operacion['lapso'] % 100
    # Lista para almacenar predicciones por centro de operacion
    # predicciones_2025_centro = []
    # # Hacer predicción para cada centro de operacion y mes
    # for centro, grupo in df_centro_operacion.groupby('nombre_centro_operacion'):
    #     for mes in range(1, 13):
    #         datos_mes = grupo[grupo['mes'] == mes]
            
    #         # Datos para regresión
    #         x = datos_mes['year'].values
    #         y = datos_mes['suma'].values

    #         if len(x) >= 2:  # Se necesita al menos 2 puntos para ajustar una recta
    #             a, b = np.polyfit(x, y, 1)  # Ajuste lineal
    #             y_pred = a * year_siguiente + b
    #             predicciones_2025_centro.append({'nombre_centro_operacion': centro, 'lapso': year_siguiente * 100 + mes, 'suma': round(y_pred)})
    # # Crear DataFrame con predicciones
    # df_pred_2025_centro = pd.DataFrame(predicciones_2025_centro)
    # (Opcional) Unir con el DataFrame original y ordenar por lapso y centro de operacion
    df_proyeccion_centro_operacion = pd.concat([df_centro_operacion[['nombre_centro_operacion', 'lapso', 'suma']]], ignore_index=True)
    df_proyeccion_centro_operacion = df_proyeccion_centro_operacion.sort_values(['nombre_centro_operacion', 'lapso']).reset_index(drop=True)
    # extraer año y mes
    df_proyeccion_centro_operacion['year'] = df_proyeccion_centro_operacion['lapso'] // 100
    df_proyeccion_centro_operacion['mes'] = df_proyeccion_centro_operacion['lapso'] % 100
    
    # calcular el coeficiente de correlación R2 para la proyección por centro de operacion y lapso -----------
    correlaciones_centro = []   
    for centro, grupo in df_proyeccion_centro_operacion.groupby('nombre_centro_operacion'):
        for mes in range(1, 13):
            datos_mes = grupo[grupo["mes"] == mes]

            if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
                coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
            else:
                coef = np.nan  # si no hay variación, correlación indefinida

            correlaciones_centro.append({
                "nombre_centro_operacion": centro,
                "mes": mes,
                "coef_correlacion": (round(coef, 4))*100 if not np.isnan(coef) else None
            })
    df_correl_por_mes_centro = pd.DataFrame(correlaciones_centro)
    # unir con el df_proyeccion_centro_operacion
    df_proyeccion_centro_operacion = pd.merge(df_proyeccion_centro_operacion, df_correl_por_mes_centro, on=['nombre_centro_operacion', 'mes'], how='left')
    df_proyeccion_centro_operacion['suma'] = df_proyeccion_centro_operacion['suma'].round().astype(int)   
    
    # ================= TOTAL_YEAR POR CENTRO ===================
    df_total_year_centro = (
        df_proyeccion_centro_operacion
        .groupby(['nombre_centro_operacion', 'year'])['suma']
        .sum()
        .reset_index()
        .rename(columns={'suma': 'total_year'})
    )
    # Calcular variaciones por centro
    df_total_year_centro['variacion_pesos'] = df_total_year_centro.groupby('nombre_centro_operacion')['total_year'].diff().round().astype('Int64')
    df_total_year_centro['variacion_pct'] = (df_total_year_centro.groupby('nombre_centro_operacion')['total_year'].pct_change() * 100).round(2)

    # Rellenar NaN en la primera fila de cada grupo
    df_total_year_centro[['variacion_pesos', 'variacion_pct']] = df_total_year_centro[['variacion_pesos', 'variacion_pct']].fillna(0)
    
    # ================== COSTOS: total_year ==============================
    costos = PresupuestoCentroOperacionCostos.objects.values("year", "nombre_centro_operacion", "total_year")
    df_costos = pd.DataFrame(list(costos)).rename(columns={"total_year": "total_year_costos"})

    # Merge ventas + costos
    df_total_year_centro = pd.merge(
        df_total_year_centro,
        df_costos,
        on=["nombre_centro_operacion", "year"],
        how="left"
    )
    
    # merge de df_proyeccion_centro_operacion con df_por_año para agregar las columnas de total, variacion_pesos y variacion_pct
    df_proyeccion_centro_operacion = pd.merge(df_proyeccion_centro_operacion, df_total_year_centro[['nombre_centro_operacion','year', 'total_year', 'total_year_costos','variacion_pesos', 'variacion_pct']], on=["nombre_centro_operacion", "year"], how='left')
    
    # calcular utilidad por año, 1 - (costos / ventas), el costo está en el df_proyeccion_general y se encuentra en la columna total_year_costos, y las ventas están en la columna total
    df_proyeccion_centro_operacion['utilidad_pct'] = (1 - (df_proyeccion_centro_operacion['total_year_costos'] / df_proyeccion_centro_operacion['total_year'])) * 100
    df_proyeccion_centro_operacion['utilidad_pct'] = df_proyeccion_centro_operacion['utilidad_pct'].round(2)
    # llenar los valores infinitos o NaN con 0
    df_proyeccion_centro_operacion['utilidad_pct'] = df_proyeccion_centro_operacion['utilidad_pct'].replace([np.inf, -np.inf], 0).fillna(0)
    # utilidad en valor
    df_proyeccion_centro_operacion['utilidad_valor'] = df_proyeccion_centro_operacion['total_year'] - df_proyeccion_centro_operacion['total_year_costos']
    df_proyeccion_centro_operacion['utilidad_valor'] = df_proyeccion_centro_operacion['utilidad_valor'].round().astype(int)
    
    # 🔹 AGREGAR LOS 12 MESES DE 2026 CON VALORES EN CERO POR CADA CENTRO
    centros_existentes = df_proyeccion_centro_operacion["nombre_centro_operacion"].dropna().unique()
    filas_2026 = []

    for centro in centros_existentes:
        for mes in range(1, 13):
            filas_2026.append({
                "lapso": 202600 + mes,
                "nombre_centro_operacion": centro,
                "year": 2026,
                "mes": mes,
                "suma": 0,
                "coef_correlacion": 0,
                "total_year": 0,
                "total_year_costos": 0,
                "variacion_pesos": 0,
                "variacion_pct": 0,
                "utilidad_pct": 0,
                "utilidad_valor": 0
            })

    df_2026 = pd.DataFrame(filas_2026)
    # unir con df_proyeccion_centro_operacion
    df_proyeccion_centro_operacion = pd.concat([df_proyeccion_centro_operacion, df_2026], ignore_index=True)
    # ----------- GUARDAR EN LA BD ------------
    registros = []
    for _, row in df_proyeccion_centro_operacion.iterrows():
        registros.append(
            PresupuestoCentroOperacionVentas(
                nombre_centro_operacion=row['nombre_centro_operacion'],
                year=int(row['year']),
                mes=int(row['mes']),
                total=int(row['suma']),
                r2=row['coef_correlacion'] if row['coef_correlacion'] is not None else 0,
                total_year=row['total_year'] if row['total_year'] is not None else 0,
                total_year_costos=row['total_year_costos'] if row['total_year_costos'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0,
                utilidad_pct=row['utilidad_pct'] if row['utilidad_pct'] is not None else 0,
                utilidad_valor=row['utilidad_valor'] if row['utilidad_valor'] is not None else 0
            )
        )
    
    # Opcional: limpiar tabla antes de insertar para evitar duplicados
    PresupuestoCentroOperacionVentas.objects.all().delete() 
    PresupuestoCentroOperacionVentas.objects.bulk_create(registros)
    
    data = list(PresupuestoCentroOperacionVentas.objects.values())
    return JsonResponse(data, safe=False)
    
@csrf_exempt
def guardar_presupuesto_centro_ventas(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # 📥 datos editados desde DataTable
            df = pd.DataFrame(data)
            # print(data)
            # --- asegurar tipos correctos ---
            df["year"] = df["year"].astype(int)
            df["mes"] = df["mes"].astype(int)
            df["total"] = df["total"].astype(int)
            df["nombre_centro_operacion"] = df["nombre_centro_operacion"].astype(str)

            # --- recalcular R² por centro de operación y mes ---
            correlaciones = []
            for centro, grupo in df.groupby("nombre_centro_operacion"):
                for mes in range(1, 13):
                    datos_mes = grupo[grupo["mes"] == mes]

                    if len(datos_mes) >= 2 and datos_mes["total"].std() != 0:
                        coef = np.corrcoef(datos_mes["year"], datos_mes["total"])[0, 1]
                    else:
                        coef = np.nan

                    correlaciones.append({
                        "nombre_centro_operacion": centro,
                        "mes": mes,
                        "coef_correlacion": (round(coef, 4)) * 100 if not np.isnan(coef) else 0
                    })

            df_correl = pd.DataFrame(correlaciones)

            # unir correlaciones recalculadas con los datos originales
            df = pd.merge(df, df_correl, on=["nombre_centro_operacion", "mes"], how="left")

            # --- guardar en la BD ---
            registros = []
            for _, row in df.iterrows():
                registros.append(
                    PresupuestoCentroOperacionVentas(
                        nombre_centro_operacion=row["nombre_centro_operacion"],
                        year=int(row["year"]),
                        mes=int(row["mes"]),
                        total=int(row["total"]),
                        r2=row["coef_correlacion"]
                    )
                )

            PresupuestoCentroOperacionVentas.objects.all().delete()
            PresupuestoCentroOperacionVentas.objects.bulk_create(registros)

            data = list(PresupuestoCentroOperacionVentas.objects.values())
            return JsonResponse(data, safe=False)

        except Exception as e:
            return JsonResponse({"status": "error", "mensaje": str(e)}, status=400)


def obtener_presupuesto_centro_ventas(request):
    data = list(PresupuestoCentroOperacionVentas.objects.values())
    return JsonResponse(data, safe=False)

def vista_presupuesto_centro_ventas(request):
    return render(request, 'presupuesto_comercial/presupuesto_centro_ventas.html') 

#---------------PRESUPUESTO POR CENTRO OPERACION - SEGMENTO VENTAS--------
def cargar_presupuesto_centro_segmento_ventas(request):
    bd2020 = BdVentas2020.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2021 = BdVentas2021.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2022 = BdVentas2022.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2023 = BdVentas2023.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2024 = BdVentas2024.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2025 = BdVentas2025.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    
    df1 = pd.DataFrame(list(bd2020))
    df2 = pd.DataFrame(list(bd2021))
    df3 = pd.DataFrame(list(bd2022))
    df4 = pd.DataFrame(list(bd2023))
    df5 = pd.DataFrame(list(bd2024))
    df6 = pd.DataFrame(list(bd2025))
    
    year_actual = timezone.now().year
    year_siguiente = timezone.now().year + 1
   
    df_total = pd.concat([df1, df2, df3, df4, df5, df6], ignore_index=True)
    df_centro_operacion_segmento = df_total.groupby(['nombre_clase_cliente', 'nombre_centro_de_operacion', 'lapso'])['suma'].sum().reset_index()
    
    # Extraer año y mes
    df_centro_operacion_segmento['year'] = df_centro_operacion_segmento['lapso'] // 100
    df_centro_operacion_segmento['mes'] = df_centro_operacion_segmento['lapso'] % 100
    '''
    # Lista para almacenar predicciones por centro de operacion y segmento
    predicciones_2025_centro_segmento = []
    # Hacer predicción para cada centro de operacion, segmento y mes
    for (centro, segmento), grupo in df_centro_operacion_segmento.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente']):
        for mes in range(1, 13):
            datos_mes = grupo[grupo['mes'] == mes]
            
            # Datos para regresión
            x = datos_mes['year'].values
            y = datos_mes['suma'].values

            if len(x) >= 2:  # Se necesita al menos 2 puntos para ajustar una recta
                a, b = np.polyfit(x, y, 1)  # Ajuste lineal
                y_pred = a * year_siguiente + b
                predicciones_2025_centro_segmento.append({'nombre_centro_de_operacion': centro, 'nombre_clase_cliente': segmento, 'lapso': year_siguiente * 100 + mes, 'suma': round(y_pred)})
    # Crear DataFrame con predicciones
    df_pred_2025_centro_segmento = pd.DataFrame(predicciones_2025_centro_segmento)
    '''
    # (Opcional) Unir con el DataFrame original y ordenar por lapso, centro de operacion y segmento
    df_proyeccion_centro_operacion_segmento = pd.concat([df_centro_operacion_segmento[['nombre_centro_de_operacion', 'nombre_clase_cliente', 'lapso', 'suma']]], ignore_index=True)
    df_proyeccion_centro_operacion_segmento = df_proyeccion_centro_operacion_segmento.sort_values(['nombre_centro_de_operacion', 'nombre_clase_cliente', 'lapso']).reset_index(drop=True)
    # extraer año y mes
    df_proyeccion_centro_operacion_segmento['year'] = df_proyeccion_centro_operacion_segmento['lapso'] // 100
    df_proyeccion_centro_operacion_segmento['mes'] = df_proyeccion_centro_operacion_segmento['lapso'] % 100
    # ----------------------------calcular el coeficiente de correlación R2 para la proyección por centro de operacion, segmento y lapso ----------------------------
    correlaciones_centro_segmento = []
    for (centro, segmento), grupo in df_proyeccion_centro_operacion_segmento.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente']):
        for mes in range(1, 13):
            datos_mes = grupo[grupo["mes"] == mes]

            if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
                coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
            else:
                coef = 0  # si no hay variación, correlación indefinida

            correlaciones_centro_segmento.append({
                "nombre_centro_de_operacion": centro,
                "nombre_clase_cliente": segmento,
                "mes": mes,
                "coef_correlacion": (round(coef, 4))*100 if not np.isnan(coef) else None
            })
    df_correl_por_mes_centro_segmento = pd.DataFrame(correlaciones_centro_segmento)
    # unir con el df_proyeccion_centro_operacion_segmento
    df_proyeccion_centro_operacion_segmento = pd.merge(df_proyeccion_centro_operacion_segmento, df_correl_por_mes_centro_segmento, on=['nombre_centro_de_operacion', 'nombre_clase_cliente', 'mes'], how='left')
    df_proyeccion_centro_operacion_segmento['suma'] = df_proyeccion_centro_operacion_segmento['suma'].round().astype(int)

    # ================= TOTAL_YEAR POR CENTRO + SEGMENTO ===================
    df_total_year_centro_segmento = (
        df_proyeccion_centro_operacion_segmento
        .groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'])['suma']
        .sum()
        .reset_index()
        .rename(columns={'suma': 'total_year'})
    )
    
    # Variaciones
    df_total_year_centro_segmento['variacion_pesos'] = (
        df_total_year_centro_segmento
        .groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente'])['total_year']
        .diff()
        .round()
        .astype('Int64')
    )
    df_total_year_centro_segmento['variacion_pct'] = (
        df_total_year_centro_segmento
        .groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente'])['total_year']
        .pct_change() * 100
    ).round(2)
    df_total_year_centro_segmento[['variacion_pesos', 'variacion_pct']] = df_total_year_centro_segmento[['variacion_pesos', 'variacion_pct']].fillna(0)

    # ================== COSTOS ==================
    costos = PresupuestoCentroSegmentoCostos.objects.values(
        "year", "nombre_centro_operacion", "segmento", "total_year"
    )
    df_costos = pd.DataFrame(list(costos)).rename(columns={"total_year": "total_year_costos"})

    df_total_year_centro_segmento = pd.merge(
        df_total_year_centro_segmento,
        df_costos,
        left_on=["nombre_centro_de_operacion", "nombre_clase_cliente", "year"],
        right_on=["nombre_centro_operacion", "segmento", "year"],
        how="left"
    ).drop(columns=["nombre_centro_operacion", "segmento"])

    # Merge con proyección
    df_proyeccion_centro_operacion_segmento = pd.merge(
        df_proyeccion_centro_operacion_segmento,
        df_total_year_centro_segmento[['nombre_centro_de_operacion', 'nombre_clase_cliente', 'year', 'total_year', 'total_year_costos','variacion_pesos', 'variacion_pct']],
        on=["nombre_centro_de_operacion", "nombre_clase_cliente", "year"],
        how="left"
    )
   
    # ================== UTILIDAD ==================
    df_proyeccion_centro_operacion_segmento['utilidad_pct'] = (
        1 - (df_proyeccion_centro_operacion_segmento['total_year_costos'] / df_proyeccion_centro_operacion_segmento['total_year'])
    ) * 100
    df_proyeccion_centro_operacion_segmento['utilidad_pct'] = df_proyeccion_centro_operacion_segmento['utilidad_pct'].round(2)
    df_proyeccion_centro_operacion_segmento['utilidad_pct'] = df_proyeccion_centro_operacion_segmento['utilidad_pct'].replace([np.inf, -np.inf], 0).fillna(0)

    df_proyeccion_centro_operacion_segmento['utilidad_valor'] = (
        df_proyeccion_centro_operacion_segmento['total_year'] - df_proyeccion_centro_operacion_segmento['total_year_costos']
    )
    df_proyeccion_centro_operacion_segmento['utilidad_valor'] = df_proyeccion_centro_operacion_segmento['utilidad_valor'].round().astype(int)
    
    # 🔹 AGREGAR LOS 12 MESES DE 2026 CON VALORES EN CERO POR CADA CENTRO + SEGMENTO
    centros_existentes = df_proyeccion_centro_operacion_segmento["nombre_centro_de_operacion"].dropna().unique()
    segmentos_existentes = df_proyeccion_centro_operacion_segmento["nombre_clase_cliente"].dropna().unique()
    filas_2026 = []
    for centro in centros_existentes:
        for segmento in segmentos_existentes:
            for mes in range(1, 13):
                filas_2026.append({
                    "lapso": 202600 + mes,
                    "nombre_centro_de_operacion": centro,
                    "nombre_clase_cliente": segmento,
                    "year": 2026,
                    "mes": mes,
                    "suma": 0,
                    "coef_correlacion": 0,
                    "total_year": 0,
                    "total_year_costos": 0,
                    "variacion_pesos": 0,
                    "variacion_pct": 0,
                    "utilidad_pct": 0,
                    "utilidad_valor": 0
                })
    df_2026 = pd.DataFrame(filas_2026)
    # unir con df_proyeccion_centro_operacion_segmento
    df_proyeccion_centro_operacion_segmento = pd.concat([df_proyeccion_centro_operacion_segmento, df_2026], ignore_index=True)


    # Guardar en la BD -----------------
    registros = []
    for _, row in df_proyeccion_centro_operacion_segmento.iterrows():
        registros.append(
            PresupuestoCentroSegmentoVentas(
                nombre_centro_operacion=row['nombre_centro_de_operacion'],
                segmento=row['nombre_clase_cliente'],
                year=int(row['year']),
                mes=int(row['mes']),
                total=int(row['suma']),
                r2=row['coef_correlacion'] if row['coef_correlacion'] is not None else 0,
                total_year=row['total_year'] if row['total_year'] is not None else 0,
                total_year_costos=row['total_year_costos'] if row['total_year_costos'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0,
                utilidad_pct=row['utilidad_pct'] if row['utilidad_pct'] is not None else 0,
                utilidad_valor=row['utilidad_valor'] if row['utilidad_valor'] is not None else 0
            )
        )
    
    with transaction.atomic():
        # Opcional: limpiar tabla antes de insertar para evitar duplicados
        PresupuestoCentroSegmentoVentas.objects.all().delete()
        PresupuestoCentroSegmentoVentas.objects.bulk_create(registros)
    
    data = list(PresupuestoCentroSegmentoVentas.objects.values())
    return JsonResponse(data, safe=False)

@csrf_exempt
def guardar_presupuesto_centro_segmento_ventas(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # 📥 los datos del DataTable
            df = pd.DataFrame(data)

            # asegurar tipos correctos
            df["year"] = df["year"].astype(int)
            df["mes"] = df["mes"].astype(int)
            df["total"] = df["total"].astype(int)

            # 🔄 recalcular R2 por centro, segmento y mes
            correlaciones = []
            for (centro, segmento), grupo in df.groupby(["nombre_centro_operacion", "segmento"]):
                for mes in range(1, 13):
                    datos_mes = grupo[grupo["mes"] == mes]

                    if len(datos_mes) >= 2 and datos_mes["total"].std() != 0:
                        coef = np.corrcoef(datos_mes["year"], datos_mes["total"])[0, 1]
                    else:
                        coef = np.nan

                    correlaciones.append({
                        "nombre_centro_operacion": centro,
                        "segmento": segmento,
                        "mes": mes,
                        "r2": (round(coef, 4)) * 100 if not np.isnan(coef) else 0
                    })

            df_r2 = pd.DataFrame(correlaciones)

            # unir R2 recalculado con df original
            df_final = pd.merge(
                df,
                df_r2,
                on=["nombre_centro_operacion", "segmento", "mes"],
                how="left"
            )
            df_final["r2"] = df_final["r2_y"].fillna(df_final["r2_x"])  # prioriza recalculado
            df_final = df_final.drop(columns=["r2_x", "r2_y"], errors="ignore")

            # preparar objetos para guardar
            registros = []
            for _, row in df_final.iterrows():
                registros.append(
                    PresupuestoCentroSegmentoVentas(
                        nombre_centro_operacion=row["nombre_centro_operacion"],
                        segmento=row["segmento"],
                        year=int(row["year"]),
                        mes=int(row["mes"]),
                        total=int(row["total"]),
                        r2=float(row["r2"])
                    )
                )

            # limpiar tabla antes de insertar
            PresupuestoCentroSegmentoVentas.objects.all().delete()
            PresupuestoCentroSegmentoVentas.objects.bulk_create(registros)

            data = list(PresupuestoCentroSegmentoVentas.objects.values())
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({"status": "error", "mensaje": str(e)}, status=400)

    return JsonResponse({"status": "error", "mensaje": "Método no permitido"}, status=405)

def obtener_presupuesto_centro_segmento_ventas(request):
    data = list(PresupuestoCentroSegmentoVentas.objects.values())
    return JsonResponse(data, safe=False)

def vista_presupuesto_centro_segmento_ventas(request):
    return render(request, 'presupuesto_comercial/presupuesto_centro_segmento_ventas.html')

#-----------PRESUPUESTO GENERAL COSTOS
def cargar_presupuesto_general_costos(request):
    bd2020 = BdVentas2020.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2021 = BdVentas2021.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2022 = BdVentas2022.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2023 = BdVentas2023.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2024 = BdVentas2024.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2025 = BdVentas2025.objects.values('nombre_linea_n1', 'lapso', 'centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'centro_de_operacion', 'nombre_clase_cliente', 'suma')
    
    df1 = pd.DataFrame(list(bd2020))
    df2 = pd.DataFrame(list(bd2021))
    df3 = pd.DataFrame(list(bd2022))
    df4 = pd.DataFrame(list(bd2023))
    df5 = pd.DataFrame(list(bd2024))
    df6 = pd.DataFrame(list(bd2025))
    
    year_actual = timezone.now().year
    year_siguiente = timezone.now().year + 1
    
    df_total = pd.concat([df1, df2, df3, df4, df5, df6], ignore_index=True)
    
    df_lapso_total = df_total.groupby('lapso')['suma'].sum().reset_index()
    
    # Extraer año y mes
    df_lapso_total['year'] = df_lapso_total['lapso'] // 100
    df_lapso_total['mes'] = df_lapso_total['lapso'] % 100
    # 📌 Suma por año
    # df_por_año = df_lapso_total.groupby("year")["suma"].sum().reset_index()
    # 📌 Suma por mes (todos los años juntos, ej: todos los eneros, febreros, etc.)
    df_por_mes = df_lapso_total.groupby("mes")["suma"].sum().reset_index()
    # suma por año y mes
    df_por_year_mes = df_lapso_total.groupby(["year", "mes"])["suma"].sum().reset_index()
    
    # calcular predicción para 2025 por cada mes usando regresión lineal
    predicciones_2025_general = []
    # recorrer cada mes (1 a 12)
    for mes in range(1, 13):
        datos_mes = df_por_year_mes[df_por_year_mes["mes"] == mes]

        x = datos_mes["year"].values
        y = datos_mes["suma"].values
        if len(x) >= 2:  # se necesitan al menos 2 años
            a, b = np.polyfit(x, y, 1)  # ajuste lineal
            y_pred = a * year_siguiente + b
            predicciones_2025_general.append({
                "year": year_siguiente,
                "mes": mes,
                "suma_pred": round(y_pred),
                "lapso": year_siguiente * 100 + mes
            })

    # convertir a dataframe
    df_pred_2025_general = pd.DataFrame(predicciones_2025_general)
    # unir con df_por_year_mes
    df_proyeccion_general = pd.concat([df_lapso_total[['lapso', 'suma']], df_pred_2025_general[['lapso', 'suma_pred']].rename(columns={'suma_pred': 'suma'})], ignore_index=True)
   
    #extrer año y mes
    df_proyeccion_general['year'] = df_proyeccion_general['lapso'] // 100
    df_proyeccion_general['mes'] = df_proyeccion_general['lapso'] % 100
    # calcular el coeficiente de correlación R2 para la proyección general---
    correlaciones = []
    for mes in range(1, 13):
        datos_mes = df_proyeccion_general[df_proyeccion_general["mes"] == mes]
        if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
            coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
        else:
            coef = np.nan  # si no hay variación, correlación indefinida

        correlaciones.append({
            "mes": mes,
            "coef_correlacion": (round(coef, 4))*100 if not np.isnan(coef) else None
        })
    
    df_correl_por_mes = pd.DataFrame(correlaciones)
    
    # unir con el df_proyeccion_centro_operacion
    df_proyeccion_general = pd.merge(df_proyeccion_general, df_correl_por_mes, on='mes', how='left')
    df_proyeccion_general['suma'] = df_proyeccion_general['suma'].round().astype(int)
    
    df_por_año = df_proyeccion_general.groupby("year")["suma"].sum().reset_index()
    df_por_año = df_por_año.sort_values("year").reset_index(drop=True)
    df_por_año["variacion_pesos"] = (df_por_año["suma"].diff()).round().astype('Int64')
    df_por_año["variacion_pct"] = (df_por_año["suma"].pct_change() * 100).round(2)
    df_por_año["variacion_pct"] = df_por_año["variacion_pct"].fillna(0)
    df_por_año["variacion_pesos"] = df_por_año["variacion_pesos"].fillna(0) 
    # renombrar suma por total
    df_por_año = df_por_año.rename(columns={'suma': 'total'})
    # merge de df_proyeccion_general con df_por_año para agregar las columnas de total, variacion_pesos y variacion_pct
    df_proyeccion_general = pd.merge(df_proyeccion_general, df_por_año[['year', 'total','variacion_pesos', 'variacion_pct']], on='year', how='left')
    # ----------- GUARDAR EN LA BD ------------
    registros = []
    for _, row in df_proyeccion_general.iterrows():
        registros.append(
            PresupuestoGeneralCostos(
                year=int(row['year']),
                mes=int(row['mes']),
                total=int(row['suma']),
                r2=row['coef_correlacion'] if row['coef_correlacion'] is not None else 0,
                total_year=row['total'] if row['total'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0
            )
        )
    # Opcional: limpiar tabla antes de insertar para evitar duplicados
    PresupuestoGeneralCostos.objects.all().delete()
    PresupuestoGeneralCostos.objects.bulk_create(registros)
    
    data = list(PresupuestoGeneralCostos.objects.values())
    return JsonResponse(data, safe=False)

@csrf_exempt
def guardar_presupuesto_general_costos(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # 📥 los datos del DataTable
            df = pd.DataFrame(data)

            # --- asegurarse de que los tipos sean correctos ---
            df["year"] = df["year"].astype(int)
            df["mes"] = df["mes"].astype(int)
            df["total"] = df["total"].astype(int)

            # --- recalcular coeficiente de correlación R² por mes ---
            correlaciones = []
            for mes in range(1, 13):
                datos_mes = df[df["mes"] == mes]

                if len(datos_mes) >= 2 and datos_mes["total"].std() != 0:
                    coef = np.corrcoef(datos_mes["year"], datos_mes["total"])[0, 1]
                else:
                    coef = np.nan

                correlaciones.append({
                    "mes": mes,
                    "coef_correlacion": (round(coef, 4)) * 100 if not np.isnan(coef) else 0
                })

            df_correl = pd.DataFrame(correlaciones)

            # unir correlaciones recalculadas con los datos originales
            df = pd.merge(df, df_correl, on="mes", how="left")

            registros = []
            for _, row in df.iterrows():
                registros.append(
                    PresupuestoGeneralCostos(
                        year=int(row["year"]),
                        mes=int(row["mes"]),
                        total=int(row["total"]),
                        r2=row["coef_correlacion"]
                    )
                )

            # limpiar tabla antes de insertar
            PresupuestoGeneralCostos.objects.all().delete()
            PresupuestoGeneralCostos.objects.bulk_create(registros)

            data = list(PresupuestoGeneralCostos.objects.values())
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({"status": "error", "mensaje": str(e)}, status=400)

    return JsonResponse({"status": "error", "mensaje": "Método no permitido"}, status=405)

def obtener_presupuesto_general_costos(request):
    data = list(PresupuestoGeneralCostos.objects.values())
    return JsonResponse(data, safe=False)

def vista_presupuesto_general_costos(request):
    return render(request, 'presupuesto_comercial/presupuesto_general_costos.html')

#-----------PRESUPUESTO POR CENTRO OPERACION - COSTOS
def cargar_presupuesto_centro_costos(request):
    bd2020 = BdVentas2020.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2021 = BdVentas2021.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2022 = BdVentas2022.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2023 = BdVentas2023.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2024 = BdVentas2024.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2025 = BdVentas2025.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    
    df1 = pd.DataFrame(list(bd2020))
    df2 = pd.DataFrame(list(bd2021))
    df3 = pd.DataFrame(list(bd2022))
    df4 = pd.DataFrame(list(bd2023))
    df5 = pd.DataFrame(list(bd2024))
    df6 = pd.DataFrame(list(bd2025))
    year_actual = timezone.now().year
    year_siguiente = timezone.now().year + 1
    
    df_total = pd.concat([df1, df2, df3, df4, df5, df6], ignore_index=True)
    df_centro_operacion = df_total.groupby(['nombre_centro_de_operacion', 'lapso'])['suma'].sum().reset_index()
    
    # Extraer año y mes
    df_centro_operacion['year'] = df_centro_operacion['lapso'] // 100
    df_centro_operacion['mes'] = df_centro_operacion['lapso'] % 100
    # Lista para almacenar predicciones por centro de operacion
    predicciones_2025_centro = []
    # Hacer predicción para cada centro de operacion y mes
    for centro, grupo in df_centro_operacion.groupby('nombre_centro_de_operacion'):
        for mes in range(1, 13):
            datos_mes = grupo[grupo['mes'] == mes]
            # Datos para regresión
            x = datos_mes['year'].values
            y = datos_mes['suma'].values

            if len(x) >= 2:  # Se necesita al menos 2 puntos para ajustar una recta
                a, b = np.polyfit(x, y, 1)  # Ajuste lineal
                y_pred = a * year_siguiente + b
                predicciones_2025_centro.append({'nombre_centro_de_operacion': centro, 'lapso': year_siguiente * 100 + mes, 'suma': round(y_pred)})
    # Crear DataFrame con predicciones
    df_pred_2025_centro = pd.DataFrame(predicciones_2025_centro)
    # (Opcional) Unir con el DataFrame original y ordenar por lapso y centro de operacion
    df_proyeccion_centro_operacion = pd.concat([df_centro_operacion[['nombre_centro_de_operacion', 'lapso', 'suma']], df_pred_2025_centro], ignore_index=True)
    df_proyeccion_centro_operacion = df_proyeccion_centro_operacion.sort_values(['nombre_centro_de_operacion', 'lapso']).reset_index(drop=True)
    # extraer año y mes
    df_proyeccion_centro_operacion['year'] = df_proyeccion_centro_operacion['lapso'] // 100
    df_proyeccion_centro_operacion['mes'] = df_proyeccion_centro_operacion['lapso'] % 100
    
    # calcular el coeficiente de correlación R2 para la proyección por centro de operacion y lapso -----------
    correlaciones_centro = []   
    for centro, grupo in df_proyeccion_centro_operacion.groupby('nombre_centro_de_operacion'):
        for mes in range(1, 13):
            datos_mes = grupo[grupo["mes"] == mes]

            if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
                coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
            else:
                coef = np.nan  # si no hay variación, correlación indefinida

            correlaciones_centro.append({
                "nombre_centro_de_operacion": centro,
                "mes": mes,
                "coef_correlacion": (round(coef, 4))*100 if not np.isnan(coef) else None
            })
    df_correl_por_mes_centro = pd.DataFrame(correlaciones_centro)
    # unir con el df_proyeccion_centro_operacion
    df_proyeccion_centro_operacion = pd.merge(df_proyeccion_centro_operacion, df_correl_por_mes_centro, on=['nombre_centro_de_operacion', 'mes'], how='left')
    df_proyeccion_centro_operacion['suma'] = df_proyeccion_centro_operacion['suma'].round().astype(int)   
    
    
    # ================= TOTAL_YEAR POR CENTRO ===================
    df_total_year_centro = (
        df_proyeccion_centro_operacion
        .groupby(['nombre_centro_de_operacion', 'year'])['suma']
        .sum()
        .reset_index()
        .rename(columns={'suma': 'total_year'})
    )
    # Calcular variaciones por centro
    df_total_year_centro['variacion_pesos'] = df_total_year_centro.groupby('nombre_centro_de_operacion')['total_year'].diff().round().astype('Int64')
    df_total_year_centro['variacion_pct'] = (df_total_year_centro.groupby('nombre_centro_de_operacion')['total_year'].pct_change() * 100).round(2)

    # Rellenar NaN en la primera fila de cada grupo
    df_total_year_centro[['variacion_pesos', 'variacion_pct']] = df_total_year_centro[['variacion_pesos', 'variacion_pct']].fillna(0)
    # merge de df_proyeccion_centro_operacion con df_por_año para agregar las columnas de total, variacion_pesos y variacion_pct
    df_proyeccion_centro_operacion = pd.merge(
        df_proyeccion_centro_operacion,
        df_total_year_centro[['nombre_centro_de_operacion', 'year', 'total_year','variacion_pesos', 'variacion_pct']],
        on=['nombre_centro_de_operacion','year'],
        how='left'
    )
    # guardar en la bd
    registros = []
    for _, row in df_proyeccion_centro_operacion.iterrows():
        registros.append(
            PresupuestoCentroOperacionCostos(
                nombre_centro_operacion=row['nombre_centro_de_operacion'],
                year=int(row['year']),
                mes=int(row['mes']),
                total=int(row['suma']),
                r2=row['coef_correlacion'] if row['coef_correlacion'] is not None else 0,
                total_year=row['total_year'] if row['total_year'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0
            )
        )
    
    # Opcional: limpiar tabla antes de insertar para evitar duplicados
    PresupuestoCentroOperacionCostos.objects.all().delete()
    PresupuestoCentroOperacionCostos.objects.bulk_create(registros)
    
    data = list(PresupuestoCentroOperacionCostos.objects.values())
    return JsonResponse(data, safe=False)

@csrf_exempt
def guardar_presupuesto_centro_costos(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # 📥 los datos del DataTable
            df = pd.DataFrame(data)

            # --- asegurar tipos correctos ---
            df["year"] = df["year"].astype(int)
            df["mes"] = df["mes"].astype(int)
            df["total"] = df["total"].astype(int)
            df["nombre_centro_operacion"] = df["nombre_centro_operacion"].astype(str)

            # --- recalcular R² por centro de operación y mes ---
            correlaciones = []
            for centro, grupo in df.groupby("nombre_centro_operacion"):
                for mes in range(1, 13):
                    datos_mes = grupo[grupo["mes"] == mes]

                    if len(datos_mes) >= 2 and datos_mes["total"].std() != 0:
                        coef = np.corrcoef(datos_mes["year"], datos_mes["total"])[0, 1]
                    else:
                        coef = np.nan

                    correlaciones.append({
                        "nombre_centro_operacion": centro,
                        "mes": mes,
                        "coef_correlacion": (round(coef, 4)) * 100 if not np.isnan(coef) else 0
                    })

            df_correl = pd.DataFrame(correlaciones)

            # unir correlaciones recalculadas con los datos originales
            df = pd.merge(df, df_correl, on=["nombre_centro_operacion", "mes"], how="left")
            registros = []
            for _, row in df.iterrows():
                registros.append(
                    PresupuestoCentroOperacionCostos(
                        nombre_centro_operacion=row["nombre_centro_operacion"],
                        year=int(row["year"]),
                        mes=int(row["mes"]),
                        total=int(row["total"]),
                        r2=row["coef_correlacion"]
                    )
                )

            # limpiar tabla antes de insertar
            PresupuestoCentroOperacionCostos.objects.all().delete()
            PresupuestoCentroOperacionCostos.objects.bulk_create(registros)

            data = list(PresupuestoCentroOperacionCostos.objects.values())
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({"status": "error", "mensaje": str(e)}, status=400)

    return JsonResponse({"status": "error", "mensaje": "Método no permitido"}, status=405)

def obtener_presupuesto_centro_costos(request):
    data = list(PresupuestoCentroOperacionCostos.objects.values())
    return JsonResponse(data, safe=False)

def vista_presupuesto_centro_costos(request):
    return render(request, 'presupuesto_comercial/presupuesto_centro_costos.html')

#--------------------------PRESUPUESTO CENTRO OPERACION - SEGMENTO COSTOS---------------
def cargar_presupuesto_centro_segmento_costos(request):
    bd2020 = BdVentas2020.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2021 = BdVentas2021.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2022 = BdVentas2022.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2023 = BdVentas2023.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2024 = BdVentas2024.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2025 = BdVentas2025.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    
    df1 = pd.DataFrame(list(bd2020))
    df2 = pd.DataFrame(list(bd2021))
    df3 = pd.DataFrame(list(bd2022))
    df4 = pd.DataFrame(list(bd2023))
    df5 = pd.DataFrame(list(bd2024))
    df6 = pd.DataFrame(list(bd2025))
    year_actual = timezone.now().year
    year_siguiente = timezone.now().year + 1
    
    df_total = pd.concat([df1, df2, df3, df4, df5, df6], ignore_index=True)
    df_centro_operacion_segmento = df_total.groupby(['nombre_clase_cliente', 'nombre_centro_de_operacion', 'lapso'])['suma'].sum().reset_index()
    
    # Extraer año y mes
    df_centro_operacion_segmento['year'] = df_centro_operacion_segmento['lapso'] // 100
    df_centro_operacion_segmento['mes'] = df_centro_operacion_segmento['lapso'] % 100
    # Lista para almacenar predicciones por centro de operacion y segmento
    predicciones_2025_centro_segmento = []
    # Hacer predicción para cada centro de operacion, segmento y mes
    for (centro, segmento), grupo in df_centro_operacion_segmento.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente']):
        for mes in range(1, 13):
            datos_mes = grupo[grupo['mes'] == mes]
            
            # Datos para regresión
            x = datos_mes['year'].values
            y = datos_mes['suma'].values

            if len(x) >= 2:  # Se necesita al menos 2 puntos para ajustar una recta
                a, b = np.polyfit(x, y, 1)  # Ajuste lineal
                y_pred = a * year_siguiente + b
                predicciones_2025_centro_segmento.append({'nombre_centro_de_operacion': centro, 'nombre_clase_cliente': segmento, 'lapso': year_siguiente * 100 + mes, 'suma': round(y_pred)})
    # Crear DataFrame con predicciones
    df_pred_2025_centro_segmento = pd.DataFrame(predicciones_2025_centro_segmento)
    # (Opcional) Unir con el DataFrame original y ordenar por lapso, centro de operacion y segmento
    df_proyeccion_centro_operacion_segmento = pd.concat([df_centro_operacion_segmento[['nombre_centro_de_operacion', 'nombre_clase_cliente', 'lapso', 'suma']], df_pred_2025_centro_segmento], ignore_index=True)
    df_proyeccion_centro_operacion_segmento = df_proyeccion_centro_operacion_segmento.sort_values(['nombre_centro_de_operacion', 'nombre_clase_cliente', 'lapso']).reset_index(drop=True)
    # extraer año y mes
    df_proyeccion_centro_operacion_segmento['year'] = df_proyeccion_centro_operacion_segmento['lapso'] // 100
    df_proyeccion_centro_operacion_segmento['mes'] = df_proyeccion_centro_operacion_segmento['lapso'] % 100
    # ----------------------------calcular el coeficiente de correlación R2 para la proyección por centro de operacion, segmento y lapso ----------------------------
    correlaciones_centro_segmento = []
    for (centro, segmento), grupo in df_proyeccion_centro_operacion_segmento.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente']):
        for mes in range(1, 13):
            datos_mes = grupo[grupo["mes"] == mes]

            if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
                coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
            else:
                coef = 0 # si no hay variación, correlación indefinida

            correlaciones_centro_segmento.append({
                "nombre_centro_de_operacion": centro,
                "nombre_clase_cliente": segmento,
                "mes": mes,
                "coef_correlacion": (round(coef, 4))*100 if not np.isnan(coef) else None
            })
    df_correl_por_mes_centro_segmento = pd.DataFrame(correlaciones_centro_segmento)
    # unir con el df_proyeccion_centro_operacion_segmento
    df_proyeccion_centro_operacion_segmento = pd.merge(df_proyeccion_centro_operacion_segmento, df_correl_por_mes_centro_segmento, on=['nombre_centro_de_operacion', 'nombre_clase_cliente', 'mes'], how='left')
    df_proyeccion_centro_operacion_segmento['suma'] = df_proyeccion_centro_operacion_segmento['suma'].round().astype(int)
    
    # ================= TOTAL_YEAR POR CENTRO Y CLASE CLIENTE ===================
    df_total_year_centro_clase = (
        df_proyeccion_centro_operacion_segmento
        .groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'])['suma']
        .sum()
        .reset_index()
        .rename(columns={'suma': 'total_year'})
    )

    # Calcular variaciones por centro + clase cliente
    df_total_year_centro_clase['variacion_pesos'] = (
        df_total_year_centro_clase
        .groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente'])['total_year']
        .diff()
        .round()
        .astype('Int64')
    )

    df_total_year_centro_clase['variacion_pct'] = (
        df_total_year_centro_clase
        .groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente'])['total_year']
        .pct_change() * 100
    ).round(2)

    # Rellenar NaN en la primera fila de cada grupo
    df_total_year_centro_clase[['variacion_pesos', 'variacion_pct']] = (
        df_total_year_centro_clase[['variacion_pesos', 'variacion_pct']].fillna(0)
    )

    # merge con df_proyeccion_centro_operacion_segmento
    df_proyeccion_centro_operacion_segmento = pd.merge(
        df_proyeccion_centro_operacion_segmento,
        df_total_year_centro_clase[
            ['nombre_centro_de_operacion', 'nombre_clase_cliente', 'year', 'total_year', 'variacion_pesos', 'variacion_pct']
        ],
        on=['nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'],
        how='left'
    )
    # guardar en la bd
    registros = []
    for _, row in df_proyeccion_centro_operacion_segmento.iterrows():
        registros.append(
            PresupuestoCentroSegmentoCostos(
                nombre_centro_operacion=row['nombre_centro_de_operacion'],
                segmento=row['nombre_clase_cliente'],
                year=int(row['year']),
                mes=int(row['mes']),
                total=int(row['suma']),
                r2=row['coef_correlacion'] if row['coef_correlacion'] is not None else 0,
                total_year=row['total_year'] if row['total_year'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0
            )
        )
    
    # Opcional: limpiar tabla antes de insertar para evitar duplicados
    PresupuestoCentroSegmentoCostos.objects.all().delete()
    PresupuestoCentroSegmentoCostos.objects.bulk_create(registros)
    
    data = list(PresupuestoCentroSegmentoCostos.objects.values())
    return JsonResponse(data, safe=False)

@csrf_exempt
def guardar_presupuesto_centro_segmento_costos(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # 📥 los datos del DataTable
            df = pd.DataFrame(data)

            # asegurar tipos correctos
            df["year"] = df["year"].astype(int)
            df["mes"] = df["mes"].astype(int)
            df["total"] = df["total"].astype(int)

            # 🔄 recalcular R2 por centro, segmento y mes
            correlaciones = []
            for (centro, segmento), grupo in df.groupby(["nombre_centro_operacion", "segmento"]):
                for mes in range(1, 13):
                    datos_mes = grupo[grupo["mes"] == mes]

                    if len(datos_mes) >= 2 and datos_mes["total"].std() != 0:
                        coef = np.corrcoef(datos_mes["year"], datos_mes["total"])[0, 1]
                    else:
                        coef = np.nan

                    correlaciones.append({
                        "nombre_centro_operacion": centro,
                        "segmento": segmento,
                        "mes": mes,
                        "r2": (round(coef, 4)) * 100 if not np.isnan(coef) else 0
                    })

            df_r2 = pd.DataFrame(correlaciones)

            # unir R2 recalculado con df original
            df_final = pd.merge(
                df,
                df_r2,
                on=["nombre_centro_operacion", "segmento", "mes"],
                how="left"
            )
            df_final["r2"] = df_final["r2_y"].fillna(df_final["r2_x"])  # prioriza recalculado
            df_final = df_final.drop(columns=["r2_x", "r2_y"], errors="ignore")
            
            registros = []
            for _, row in df_final.iterrows():
                registros.append(
                    PresupuestoCentroSegmentoCostos(
                        nombre_centro_operacion=row["nombre_centro_operacion"],
                        segmento=row["segmento"],
                        year=int(row["year"]),
                        mes=int(row["mes"]),
                        total=int(row["total"]),
                        r2=float(row["r2"])
                    )
                )

            # limpiar tabla antes de insertar
            PresupuestoCentroSegmentoCostos.objects.all().delete()
            PresupuestoCentroSegmentoCostos.objects.bulk_create(registros)

            data = list(PresupuestoCentroSegmentoCostos.objects.values())
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({"status": "error", "mensaje": str(e)}, status=400)

    return JsonResponse({"status": "error", "mensaje": "Método no permitido"}, status=405)

def obtener_presupuesto_centro_segmento_costos(request):
    data = list(PresupuestoCentroSegmentoCostos.objects.values())
    return JsonResponse(data, safe=False)

def vista_presupuesto_centro_segmento_costos(request):
    return render(request, 'presupuesto_comercial/presupuesto_centro_segmento_costos.html')

#----------------PRESUPUESTO COMERCIAL PRINCIPAL-----------------------
def aux_presupuesto_comercial_costos():
    bd2020 = BdVentas2020.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2021 = BdVentas2021.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2022 = BdVentas2022.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2023 = BdVentas2023.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2024 = BdVentas2024.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2025 = BdVentas2025.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_costo')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    
    df1 = pd.DataFrame(list(bd2020))
    df2 = pd.DataFrame(list(bd2021))
    df3 = pd.DataFrame(list(bd2022))
    df4 = pd.DataFrame(list(bd2023))
    df5 = pd.DataFrame(list(bd2024))
    df6 = pd.DataFrame(list(bd2025))
    year_actual = timezone.now().year
    year_siguiente = timezone.now().year + 1
    
    df_total = pd.concat([df1, df2, df3, df4, df5, df6], ignore_index=True)
    # print(df_total)
    # calcular suma por lapso y centro de operacion
    df_lapso_total = df_total.groupby('lapso')['suma'].sum().reset_index()
    # Extraer año y mes
    df_lapso_total['year'] = df_lapso_total['lapso'] // 100
    df_lapso_total['mes'] = df_lapso_total['lapso'] % 100
    #------------------------------------------------------PRONOSTICO FINAL---------------------------------------------------
    # Extraer el año desde 'lapso'
    df_total['year'] = df_total['lapso'] // 100

    # Agrupar por nombre de producto, año, y sumar
    df_agrupado = df_total.groupby(['nombre_linea_n1', 'year', 'nombre_centro_de_operacion', 'nombre_clase_cliente'])['suma'].sum().reset_index()
    # (Opcional) Ordenar resultados
    df_agrupado = df_agrupado.sort_values(by=['nombre_linea_n1', 'year'])
   
    # Definir el rango de años esperado para añadir año faltante y agergarle 0
    year = list(range(2020, year_actual + 1))
    # Crear un dataframe con todas las combinaciones posibles
    df_completo = (
        pd.MultiIndex.from_product(
            [
                df_agrupado['nombre_linea_n1'].unique(), 
                df_agrupado['nombre_centro_de_operacion'].unique(),
                df_agrupado['nombre_clase_cliente'].unique(),
                year],
            names=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year']
        )
        .to_frame(index=False)
    )
    # Unir con tus datos reales
    df_total_fill = df_completo.merge(df_agrupado, on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'], how='left')
    # Rellenar con 0 las sumas faltantes
    df_total_fill['suma'] = df_total_fill['suma'].fillna(0)
    # print(df_total_fill)
    # PREDICCION PARA 2025 POR PRONOSTICO LINEAL -----------------------------------------
    # Lista para almacenar resultados
    # predicciones = []
    # # Agrupar por producto
    # for (nombre, centro, clase), grupo in df_total_fill.groupby( ['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente']):
    #     x = grupo['year'].values
    #     y = grupo['suma'].values
        
    #     if len(x) >= 2:
    #         # Ajuste lineal
    #         a, b = np.polyfit(x, y, 1)
    #         y_pred = a * year_siguiente + b
    #         predicciones.append({
    #             'nombre_linea_n1': nombre,
    #             'nombre_centro_de_operacion': centro,
    #             'nombre_clase_cliente': clase,
    #             'year': year_siguiente,
    #             'suma': round(y_pred)
    #         })

    # # Crear DataFrame con predicciones
    # df_pred_2025_pro_lineal = pd.DataFrame(predicciones)
    # df_final_pronostico = pd.concat([df_total_fill, df_pred_2025_pro_lineal], ignore_index=True)
    # df_final_pronostico = df_final_pronostico.sort_values(by=['nombre_linea_n1', 'year']).reset_index(drop=True)
    
    df_final_pronostico = df_total_fill.copy()
    # R2 ----------------------------------------------
    # Lista para almacenar resultados
    correlaciones = []
    # Agrupar por producto
    for (nombre, centro, clase), grupo in df_final_pronostico.groupby(['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente']):
        x = grupo['year'].values
        y = grupo['suma'].values

        if len(x) >= 2 and np.std(y) != 0 and np.std(x) != 0:  # evitar división por 0
            coef = np.corrcoef(x, y)[0, 1]
            coef_abs_pct = abs(coef) * 100  # valor absoluto en porcentaje
        else:
            coef_abs_pct = 0.0  # o NaN si prefieres marcarlo

        correlaciones.append({
            'nombre_linea_n1': nombre,
            'nombre_centro_de_operacion': centro,
            'nombre_clase_cliente': clase,
            'R2': round(coef_abs_pct, 2)
        })

    # Crear DataFrame con los coeficientes
    df_correlaciones = pd.DataFrame(correlaciones)
    
    # concatenar con el df_final_pronostico
    df_final_pronostico = pd.merge(df_final_pronostico, df_correlaciones, on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente'], how='left')
   
    # --------------------- Calcular variaciones año vs año anterior -------------------------------
    df_final_pronostico['suma_anterior'] = df_final_pronostico.groupby(
        ['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente']
    )['suma'].shift(1)

    # Calcular variación en porcentaje
    df_final_pronostico['variacion_pct'] = np.where(
        df_final_pronostico['suma_anterior'] == 0,
        0,
        ((df_final_pronostico['suma'] - df_final_pronostico['suma_anterior']) / df_final_pronostico['suma_anterior']) * 100
    ).round(2)

    # Calcular variación en valor (pesos)
    df_final_pronostico['variacion_valor'] = (df_final_pronostico['suma'] - df_final_pronostico['suma_anterior']).fillna(0)

    # Variación mensual
    df_final_pronostico['variacion_mes'] = (df_final_pronostico['variacion_valor'] / 12).round().astype(int)

    # Variación por precios (2% del año anterior)
    df_final_pronostico['variacion_precios'] = (df_final_pronostico['suma_anterior'] * 0.02).round().fillna(0).astype(int)

    # Crecimiento comercial (variación - variación precios)
    df_final_pronostico['crecimiento_comercial'] = (df_final_pronostico['variacion_valor'] - df_final_pronostico['variacion_precios']).round().astype(int)

    # Crecimiento comercial mensual
    df_final_pronostico['crecimiento_comercial_mes'] = (df_final_pronostico['crecimiento_comercial'] / 12).round().astype(int)

    # Reemplazar NaN por 0 en variaciones
    cols_variaciones = ['variacion_pct', 'variacion_valor', 'variacion_mes', 'variacion_precios',
                        'crecimiento_comercial', 'crecimiento_comercial_mes']
    df_final_pronostico[cols_variaciones] = df_final_pronostico[cols_variaciones].fillna(0)
    
    # concatenar con el df_final_pronostico
    # df_final_pronostico = pd.merge(df_final_pronostico, df_variacion[['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'variacion_pct', 'variacion_valor', 'variacion_mes', 'variacion_precios', 'crecimiento_comercial', 'crecimiento_comercial_mes']], on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente'], how='left') 
    
    return df_final_pronostico
    

def cargar_presupuesto_comercial(request):
    bd2020 = BdVentas2020.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2021 = BdVentas2021.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2022 = BdVentas2022.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2023 = BdVentas2023.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2024 = BdVentas2024.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    bd2025 = BdVentas2025.objects.values('nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente').annotate(suma=Sum('valor_neto')).values('nombre_linea_n1','lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'suma')
    
    df1 = pd.DataFrame(list(bd2020))
    df2 = pd.DataFrame(list(bd2021))
    df3 = pd.DataFrame(list(bd2022))
    df4 = pd.DataFrame(list(bd2023))
    df5 = pd.DataFrame(list(bd2024))
    df6 = pd.DataFrame(list(bd2025))
    year_actual = timezone.now().year
    year_siguiente = timezone.now().year + 1
   
    df_total = pd.concat([df1, df2, df3, df4, df5, df6], ignore_index=True)
    # print(df_total)
    df_lapso_total = df_total.groupby('lapso')['suma'].sum().reset_index()
    # print(df_lapso_total)
    # Extraer año y mes
    df_lapso_total['year'] = df_lapso_total['lapso'] // 100
    df_lapso_total['mes'] = df_lapso_total['lapso'] % 100
    #------------------------------------------------------PRONOSTICO FINAL---------------------------------------------------
    # Extraer el año desde 'lapso'
    df_total['year'] = df_total['lapso'] // 100

    # Agrupar por nombre de producto, año, y sumar
    df_agrupado = df_total.groupby(['nombre_linea_n1', 'year', 'nombre_centro_de_operacion', 'nombre_clase_cliente'])['suma'].sum().reset_index()
    # (Opcional) Ordenar resultados
    df_agrupado = df_agrupado.sort_values(by=['nombre_linea_n1', 'year'])
   
    # Definir el rango de años esperado para añadir año faltante y agergarle 0
    year = list(range(2020, 2026))
    # Crear un dataframe con todas las combinaciones posibles
    df_completo = (
        pd.MultiIndex.from_product(
            [
                df_agrupado['nombre_linea_n1'].unique(), 
                df_agrupado['nombre_centro_de_operacion'].unique(),
                df_agrupado['nombre_clase_cliente'].unique(),
                year],
            names=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year']
        )
        .to_frame(index=False)
    )
    # Unir con tus datos reales
    df_total_fill = df_completo.merge(df_agrupado, on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'], how='left')
    # Rellenar con 0 las sumas faltantes
    df_total_fill['suma'] = df_total_fill['suma'].fillna(0)
    # print(df_total_fill)
    # PREDICCION PARA 2025 POR PRONOSTICO LINEAL -----------------------------------------
    # Lista para almacenar resultados
    # predicciones = []
    # # Agrupar por producto
    # for (nombre, centro, clase), grupo in df_total_fill.groupby( ['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente']):
    #     x = grupo['year'].values
    #     y = grupo['suma'].values
        
    #     if len(x) >= 2:
    #         # Ajuste lineal
    #         a, b = np.polyfit(x, y, 1)
    #         y_pred = a * year_siguiente + b
    #         predicciones.append({
    #             'nombre_linea_n1': nombre,
    #             'nombre_centro_de_operacion': centro,
    #             'nombre_clase_cliente': clase,
    #             'year': year_siguiente,
    #             'suma': round(y_pred)
    #         })

    # # Crear DataFrame con predicciones
    # df_pred_2025_pro_lineal = pd.DataFrame(predicciones)
    # df_final_pronostico = pd.concat([df_total_fill, df_pred_2025_pro_lineal], ignore_index=True)
    # df_final_pronostico = df_final_pronostico.sort_values(by=['nombre_linea_n1', 'year']).reset_index(drop=True)
    
    df_final_pronostico = df_total_fill.copy()

    # R2 ----------------------------------------------
    # Lista para almacenar resultados
    correlaciones = []
    # Agrupar por producto
    for (nombre, centro, clase), grupo in df_final_pronostico.groupby(['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente']):
        x = grupo['year'].values
        y = grupo['suma'].values

        if len(x) >= 2 and np.std(y) != 0 and np.std(x) != 0:  # evitar división por 0
            coef = np.corrcoef(x, y)[0, 1]
            coef_abs_pct = abs(coef) * 100  # valor absoluto en porcentaje
        else:
            coef_abs_pct = 0.0  # o NaN si prefieres marcarlo

        correlaciones.append({
            'nombre_linea_n1': nombre,
            'nombre_centro_de_operacion': centro,
            'nombre_clase_cliente': clase,
            'R2': round(coef_abs_pct, 2)
        })

    # Crear DataFrame con los coeficientes
    df_correlaciones = pd.DataFrame(correlaciones)
    
    # concatenar con el df_final_pronostico
    df_final_pronostico = pd.merge(df_final_pronostico, df_correlaciones, on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente'], how='left')
   
    # --------------------- Calcular variaciones año vs año anterior -------------------------------
    df_final_pronostico['suma_anterior'] = df_final_pronostico.groupby(
        ['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente']
    )['suma'].shift(1)

    # Calcular variación en porcentaje
    df_final_pronostico['variacion_pct'] = np.where(
        df_final_pronostico['suma_anterior'] == 0,
        0,
        ((df_final_pronostico['suma'] - df_final_pronostico['suma_anterior']) / df_final_pronostico['suma_anterior']) * 100
    ).round(2)

    # Calcular variación en valor (pesos)
    df_final_pronostico['variacion_valor'] = (df_final_pronostico['suma'] - df_final_pronostico['suma_anterior']).fillna(0)

    # Variación mensual
    df_final_pronostico['variacion_mes'] = (df_final_pronostico['variacion_valor'] / 12).round().astype(int)

    # Variación por precios (2% del año anterior)
    df_final_pronostico['variacion_precios'] = (df_final_pronostico['suma_anterior'] * 0.02).round().fillna(0).astype(int)

    # Crecimiento comercial (variación - variación precios)
    df_final_pronostico['crecimiento_comercial'] = (df_final_pronostico['variacion_valor'] - df_final_pronostico['variacion_precios']).round().astype(int)

    # Crecimiento comercial mensual
    df_final_pronostico['crecimiento_comercial_mes'] = (df_final_pronostico['crecimiento_comercial'] / 12).round().astype(int)

    # Reemplazar NaN por 0 en variaciones
    cols_variaciones = ['variacion_pct', 'variacion_valor', 'variacion_mes', 'variacion_precios',
                        'crecimiento_comercial', 'crecimiento_comercial_mes']
    df_final_pronostico[cols_variaciones] = df_final_pronostico[cols_variaciones].fillna(0)
    
    # concatenar con el df_final_pronostico
    # df_final_pronostico = pd.merge(df_final_pronostico, df_variacion[['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'variacion_pct', 'variacion_valor', 'variacion_mes', 'variacion_precios', 'crecimiento_comercial', 'crecimiento_comercial_mes']], on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente'], how='left')

    df_final_pronostico_costos = aux_presupuesto_comercial_costos()
    
    df_final_neto_costos = pd.merge(df_final_pronostico, df_final_pronostico_costos, on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year']) # x= netos y= costos
    df_final_neto_costos = pd.merge(
    df_final_pronostico,
    df_final_pronostico_costos,
    on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'],
    suffixes=('_ventas', '_costos')
    )

    # renombrar para claridad
    df_final_neto_costos = df_final_neto_costos.rename(
        columns={'suma_ventas': 'ventas', 'suma_costos': 'costos'}
    )
    #-------------------UTILIDAD----------------------- 
    # calcular utilidad por año, 1 - (costos / ventas), el costo está en el df_fnal_pronostico_costos es decir la predicción, y las ventas están en el df_fnal_pronostico
    # df_final_neto_costos['utilidad'] = (1 - (df_final_neto_costos['suma_y'] / df_final_neto_costos['suma_x'])) * 100
    # df_final_neto_costos['utilidad'] = df_final_neto_costos['utilidad'].round(2)
    # # llenar los valores infinitos o NaN con 0
    # df_final_neto_costos['utilidad'] = df_final_neto_costos['utilidad'].replace([np.inf, -np.inf], 0).fillna(0)
    # # renombrar columnas
    # df_final_neto_costos = df_final_neto_costos.rename(columns={'suma_x': 'ventas', 'suma_y': 'costos'})    
    # # calcular utilidad en valor
    # df_final_neto_costos['utilidad_valor'] = df_final_neto_costos['ventas'] - df_final_neto_costos['costos']
    
    # ------------------- UTILIDAD SOLO AÑO ACTUAL -----------------------
    # calcular solo para el año actual
    df_final_neto_costos['utilidad_porcentual_actual'] = np.where(
        df_final_neto_costos['year'] == year_actual,
        (1 - (df_final_neto_costos['costos'] / df_final_neto_costos['ventas'])) * 100,
        0
    ).round(2)

    df_final_neto_costos['utilidad_valor_actual'] = np.where(
        df_final_neto_costos['year'] == year_actual,
        df_final_neto_costos['ventas'] - df_final_neto_costos['costos'],
        0
    ).round().astype(int)
    # limpiar NaN e infinitos
    df_final_neto_costos['utilidad_porcentual_actual'] = df_final_neto_costos['utilidad_porcentual_actual'].replace([np.inf, -np.inf], 0).fillna(0)
    df_final_neto_costos['utilidad_valor_actual'] = df_final_neto_costos['utilidad_valor_actual'].fillna(0)

    # crear clave única para mapear utilidad del año actual al siguiente
    # df_actual = df_final_neto_costos[df_final_neto_costos['year'] == year_actual].copy()
    # df_actual['clave'] = df_actual['nombre_linea_n1'] + '|' + df_actual['nombre_centro_de_operacion'] + '|' + df_actual['nombre_clase_cliente']

    # diccionarios para mapear valores
    # utilidad_pct_dict = df_actual.set_index('clave')['utilidad_porcentual_actual'].to_dict()
    # utilidad_val_dict = df_actual.set_index('clave')['utilidad_valor_actual'].to_dict()

    # asignar al año siguiente
    # mask = df_final_neto_costos['year'] == year_siguiente
    # df_final_neto_costos.loc[mask, 'clave'] = df_final_neto_costos.loc[mask, 'nombre_linea_n1'] + '|' + df_final_neto_costos.loc[mask, 'nombre_centro_de_operacion'] + '|' + df_final_neto_costos.loc[mask, 'nombre_clase_cliente']

    # df_final_neto_costos.loc[mask, 'utilidad_porcentual_actual'] = df_final_neto_costos.loc[mask, 'clave'].map(utilidad_pct_dict)
    # df_final_neto_costos.loc[mask, 'utilidad_valor_actual'] = df_final_neto_costos.loc[mask, 'clave'].map(utilidad_val_dict)

    # opcional: eliminar columna clave
    # df_final_neto_costos.drop(columns=['clave'], inplace=True)
    
    # agregar un cero a las columnas vacias
    df_final_neto_costos['variacion_pct_ventas'] = df_final_neto_costos['variacion_pct_ventas'].fillna(0)
    df_final_neto_costos['variacion_valor_ventas'] = df_final_neto_costos['variacion_valor_ventas'].fillna(0)
    df_final_neto_costos['variacion_mes_ventas'] = df_final_neto_costos['variacion_mes_ventas'].fillna(0)
    df_final_neto_costos['variacion_precios_ventas'] = df_final_neto_costos['variacion_precios_ventas'].fillna(0)
    df_final_neto_costos['crecimiento_comercial_ventas'] = df_final_neto_costos['crecimiento_comercial_ventas'].fillna(0)
    df_final_neto_costos['crecimiento_comercial_mes_ventas'] = df_final_neto_costos['crecimiento_comercial_mes_ventas'].fillna(0)

    df_final_neto_costos['variacion_pct_costos'] = df_final_neto_costos['variacion_pct_costos'].fillna(0)
    df_final_neto_costos['variacion_valor_costos'] = df_final_neto_costos['variacion_valor_costos'].fillna(0)
    df_final_neto_costos['variacion_mes_costos'] = df_final_neto_costos['variacion_mes_costos'].fillna(0)
    df_final_neto_costos['variacion_precios_costos'] = df_final_neto_costos['variacion_precios_costos'].fillna(0)
    df_final_neto_costos['crecimiento_comercial_costos'] = df_final_neto_costos['crecimiento_comercial_costos'].fillna(0)
    df_final_neto_costos['crecimiento_comercial_mes_costos'] = df_final_neto_costos['crecimiento_comercial_mes_costos'].fillna(0)
        
    # redondear las columnas que son float a int
    columnas_a_redondear = [
    'ventas', 'costos',
    'variacion_valor_ventas', 'variacion_mes_ventas', 'variacion_precios_ventas',
    'crecimiento_comercial_ventas', 'crecimiento_comercial_mes_ventas',
    'variacion_valor_costos', 'variacion_mes_costos', 'variacion_precios_costos',
    'crecimiento_comercial_costos', 'crecimiento_comercial_mes_costos'
    ]
    df_final_neto_costos[columnas_a_redondear] = df_final_neto_costos[columnas_a_redondear].round().astype(int)
    
    # guardar en la bd
    registros = []
    for _, row in df_final_neto_costos.iterrows():
        registros.append(
            PresupuestoComercial(
                linea=row['nombre_linea_n1'],
                year=int(row['year']),
                nombre_centro_de_operacion=row['nombre_centro_de_operacion'],
                nombre_clase_cliente=row['nombre_clase_cliente'],
                ventas=int(row['ventas']),
                costos=int(row['costos']),
                r2_ventas=float(row['R2_ventas']),
                r2_costos=float(row['R2_costos']),
                variacion_porcentual_ventas=float(row['variacion_pct_ventas']),
                variacion_porcentual_costos=float(row['variacion_pct_costos']),
                variacion_valor_ventas=int(row['variacion_valor_ventas']),
                variacion_valor_costos=int(row['variacion_valor_costos']),
                variacion_mes_ventas=int(row['variacion_mes_ventas']),
                variacion_mes_costos=int(row['variacion_mes_costos']),
                variacion_precios_ventas=int(row['variacion_precios_ventas']),
                variacion_precios_costos=int(row['variacion_precios_costos']),
                crecimiento_comercial_ventas=int(row['crecimiento_comercial_ventas']),
                crecimiento_comercial_costos=int(row['crecimiento_comercial_costos']),
                crecimiento_comercial_mes_ventas=int(row['crecimiento_comercial_mes_ventas']),
                crecimiento_comercial_mes_costos=int(row['crecimiento_comercial_mes_costos']),
                # 👇 Aquí asignamos proyección = ventas si el año es el siguiente
                proyeccion_ventas=int(row['ventas']) if int(row['year']) == year_actual else 0,
                proyeccion_costos=int(row['costos']) if int(row['year']) == year_actual else 0,
                # 👇 utilidad solo para 2025
                utilidad_porcentual_actual=float(row['utilidad_porcentual_actual']),
                utilidad_valor_actual=int(row['utilidad_valor_actual'])
            )
        )
    
    # Opcional: limpiar tabla antes de insertar para evitar duplicados
    PresupuestoComercial.objects.all().delete()
    PresupuestoComercial.objects.bulk_create(registros)
    
    return JsonResponse({"status": "ok", "mensaje": "Datos cargados correctamente ✅"})

@csrf_exempt
def guardar_presupuesto_comercial(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # datos enviados desde DataTable

            # 🔹 Convertir en DataFrame
            df = pd.DataFrame(data)

            # 🔹 Asegurar que campos numéricos sean numéricos (llenar NaN con 0)
            columnas_numericas = [
                "ventas", "costos", "utilidad_valor",
                "utilidad_porcentual", "crecimiento_ventas",
                "crecimiento_costos", "proyeccion_ventas",
                "proyeccion_costos", "variacion_proyectada_valor",
                "variacion_proyectada_porcentual"
            ]
            for col in columnas_numericas:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

            
            # ================== 🔄 Guardar en BD ==================
            registros = []
            for _, row in df.iterrows():
                registros.append(
                    PresupuestoComercial(
                        linea=row["linea"],
                        nombre_centro_de_operacion=row.get("nombre_centro_de_operacion", ""),
                        nombre_clase_cliente=row.get("nombre_clase_cliente", ""),
                        year=int(row["year"]),
                        ventas=int(row["ventas"]),
                        costos=int(row["costos"]),
                        r2_ventas=float(row.get("r2_ventas", 0)),
                        r2_costos=float(row.get("r2_costos", 0)),
                        variacion_porcentual_ventas=float(row.get("variacion_porcentual_ventas", 0)),
                        variacion_porcentual_costos=float(row.get("variacion_porcentual_costos", 0)),
                        variacion_valor_ventas=int(row.get("variacion_valor_ventas", 0)),
                        variacion_valor_costos=int(row.get("variacion_valor_costos", 0)),
                        variacion_mes_ventas=int(row.get("variacion_mes_ventas", 0)),
                        variacion_mes_costos=int(row.get("variacion_mes_costos", 0)),
                        variacion_precios_ventas=int(row.get("variacion_precios_ventas", 0)),
                        variacion_precios_costos=int(row.get("variacion_precios_costos", 0)),
                        crecimiento_comercial_ventas=int(row.get("crecimiento_comercial_ventas", 0)),
                        crecimiento_comercial_costos=int(row.get("crecimiento_comercial_costos", 0)),
                        crecimiento_comercial_mes_ventas=int(row.get("crecimiento_comercial_mes_ventas", 0)),
                        crecimiento_comercial_mes_costos=int(row.get("crecimiento_comercial_mes_costos", 0)),
                        crecimiento_ventas=int(row.get("crecimiento_ventas", 0)),
                        proyeccion_ventas=int(row.get("proyeccion_ventas", 0)),
                        crecimiento_costos=int(row.get("crecimiento_costos", 0)),
                        proyeccion_costos=int(row.get("proyeccion_costos", 0)),
                        utilidad_porcentual=float(row["utilidad_porcentual"]),
                        utilidad_valor=int(row["utilidad_valor"]),
                        utilidad_porcentual_actual=float(row["utilidad_porcentual_actual"]),
                        utilidad_valor_actual=int(row["utilidad_valor_actual"]),
                        variacion_proyectada_porcentual=float(row["variacion_proyectada_porcentual"]),
                        variacion_proyectada_valor=int(row["variacion_proyectada_valor"])
                    )
                )
            
            with transaction.atomic():
                # Limpieza antes de insertar
                PresupuestoComercial.objects.all().delete()
                PresupuestoComercial.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "mensaje": "Cambios guardados y recalculados ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "mensaje": str(e)}, status=400)

    return JsonResponse({"status": "error", "mensaje": "Método no permitido"}, status=405)

def actualizar_presupuesto_general_ventas(request):
    year_actual = timezone.now().year
    year_siguiente = timezone.now().year + 1
    
    # ================== 📊 Agrupar por centro y mes del año siguiente (2026) ==================
    totales_mensuales = (
        PresupuestoCentroOperacionVentas.objects
        .filter(year=year_siguiente)
        .values("mes", "nombre_centro_operacion")
        .annotate(total_mes=Sum("total"))
    )
    # ================== 🔄 Sumar por mes (sin distinguir centro) ==================
    totales_por_mes = (
        PresupuestoCentroOperacionVentas.objects
        .filter(year=year_siguiente)
        .values("mes")
        .annotate(total_mes=Sum("total"))
        .order_by("mes")
    )
    # ================== 🔄 Calcular total anual ==================
    total_anual = sum(item["total_mes"] for item in totales_por_mes)
    # ================== 💾 Actualizar tabla PresupuestoGeneralVentas por año y mes
    for item in totales_por_mes:
        mes = item["mes"]
        total_mes = item["total_mes"] or 0
        PresupuestoGeneralVentas.objects.filter(
            year=year_siguiente,
            mes=mes
        ).update(total=total_mes) 
    
    # ================== 🔄 Actualizar PresupuestoGeneralVentas con total_proyectado ==================
    total_2026 = PresupuestoComercial.objects.filter(year=year_actual).aggregate(
        total_proyectado=Sum("proyeccion_ventas")
    )["total_proyectado"] or 0
    
    PresupuestoGeneralVentas.objects.filter(year=year_siguiente).update(
        total_proyectado=total_2026
    )
    
    return JsonResponse({"status": "ok", "mensaje": "Presupuesto general de ventas actualizado ✅"})

def actualizar_presupuesto_centro_ventas(request):
    year_actual = timezone.now().year
    year_siguiente = timezone.now().year + 1
    # ================== 🔄 Actualizar PresupuestoCentroOperacionVentas con total_proyectado ==================
    proyecciones = (
        PresupuestoComercial.objects.filter(year=year_actual)
        .values("year", "nombre_centro_de_operacion")
        .annotate(total_proyectado=Sum("proyeccion_ventas"))
    )
    
    for item in proyecciones:
        centro = item["nombre_centro_de_operacion"]
        total_proyectado = item["total_proyectado"] or 0

        PresupuestoCentroOperacionVentas.objects.filter(
            year=year_siguiente,
            nombre_centro_operacion=centro
        ).update(total_proyectado=total_proyectado)
    # ================== 📊 Calcular porcentaje de participación por mes ==================
    # Paso 1: agrupar totales por centro y mes (año actual)
    data = (
        PresupuestoCentroOperacionVentas.objects.filter(year=year_actual)
        .values("nombre_centro_operacion", "mes")
        .annotate(total_mes=Sum("total"))
    )

    # Paso 2: agrupar totales anuales por centro
    totales_anuales = (
        PresupuestoCentroOperacionVentas.objects.filter(year=year_actual)
        .values("nombre_centro_operacion")
        .annotate(total_anual=Sum("total"))
    )
    # Convertimos a dict para acceso rápido
    totales_anuales_dict = {
        t["nombre_centro_operacion"]: t["total_anual"] for t in totales_anuales
    }
    # 3️⃣ Totales proyectados por centro (2026)
    proyectados = {
        p["nombre_centro_operacion"]: p["total_proyectado"]
        for p in PresupuestoCentroOperacionVentas.objects.filter(year=year_siguiente)
        .values("nombre_centro_operacion", "total_proyectado")
        .distinct()
    }

    # Paso 3: Calcular porcentaje y actualizar en la base de datos
    for item in data:
        centro = item["nombre_centro_operacion"]
        mes = item["mes"]
        total_mes = item["total_mes"] or 0
        total_anual = totales_anuales_dict.get(centro, 0) or 1  # evitar división por cero
        total_proyectado = proyectados.get(centro, 0) or 1  # evitar división por cero

        porcentaje = (total_mes / total_anual) * 100
        
        # valor proyectado mensual
        valor_proyectado_mes = round((porcentaje / 100) * total_proyectado)
        # Actualizar registro
        PresupuestoCentroOperacionVentas.objects.filter(
            year=year_siguiente,
            nombre_centro_operacion=centro,
            mes=mes
        ).update(total = valor_proyectado_mes)
    
    return JsonResponse({"status": "ok", "mensaje": "Presupuesto por centro de operación actualizado ✅"})

def actualizar_presupuesto_centro_segmento_ventas(request):
    year_actual = timezone.now().year      # 2025
    year_siguiente = year_actual + 1       # 2026

    # ================== 🔄 Actualizar total_proyectado (año siguiente) ==================
    proyecciones = (
        PresupuestoComercial.objects.filter(year=year_actual)
        .values("year", "nombre_centro_de_operacion", "nombre_clase_cliente")
        .annotate(total_proyectado=Sum("proyeccion_ventas"))
    )

    for item in proyecciones:
        centro = item["nombre_centro_de_operacion"]
        segmento = item["nombre_clase_cliente"]
        total_proyectado = item["total_proyectado"] or 0

        PresupuestoCentroSegmentoVentas.objects.filter(
            year=year_siguiente,
            nombre_centro_operacion=centro,
            segmento=segmento
        ).update(total_proyectado=total_proyectado)

    # ================== 📊 Calcular distribución mensual ==================
    # Paso 1️⃣: Totales por centro, segmento y mes (2025)
    data = (
        PresupuestoCentroSegmentoVentas.objects.filter(year=year_actual)
        .values("nombre_centro_operacion", "segmento", "mes")
        .annotate(total_mes=Sum("total"))
    )

    # Paso 2️⃣: Totales por centro, segmento y mes (2025) → base para cálculo de % dentro del mes
    totales_mes_segmento = (
        PresupuestoCentroSegmentoVentas.objects.filter(year=year_actual)
        .values("nombre_centro_operacion", "mes")
        .annotate(total_mes_centro=Sum("total"))
    )
    totales_mes_segmento_dict = {
        (t["nombre_centro_operacion"], t["mes"]): t["total_mes_centro"]
        for t in totales_mes_segmento
    }

    # Paso 3️⃣: Totales proyectados por centro y segmento (2026)
    proyectados = {
        (p["nombre_centro_operacion"], p["segmento"]): p["total_proyectado"]
        for p in PresupuestoCentroSegmentoVentas.objects.filter(year=year_siguiente)
        .values("nombre_centro_operacion", "segmento", "total_proyectado")
        .distinct()
    }

    # Paso 4️⃣: Calcular valor proyectado mensual (2026)
    for item in data:
        centro = item["nombre_centro_operacion"]
        segmento = item["segmento"]
        mes = item["mes"]
        total_mes_segmento = item["total_mes"] or 0
        total_mes_centro = totales_mes_segmento_dict.get((centro, mes), 0) or 1  # evitar división por 0
        total_proyectado = proyectados.get((centro, segmento), 0) or 0

        # proporción de ese segmento dentro del centro en ese mes
        proporcion = (total_mes_segmento / total_mes_centro) 
        # valor proyectado mensual = proporción * total proyectado del centro-segmento
        valor_proyectado_mes = round(total_proyectado * proporcion)
        print("Centro:", centro, "Segmento:", segmento, "Mes:", mes, "Total mes segmento:", total_mes_segmento, "mes centro:", total_mes_centro, "Proporción:", proporcion, "proyectado mes:", valor_proyectado_mes, "total proyectado:", total_proyectado)
        # Actualizar registro correspondiente al año siguiente
        PresupuestoCentroSegmentoVentas.objects.filter(
            year=year_siguiente,
            nombre_centro_operacion=centro,
            segmento=segmento,
            mes=mes
        ).update(total=valor_proyectado_mes)

    return JsonResponse({
        "status": "ok",
        "mensaje": "Presupuesto por centro y segmento actualizado y distribuido por mes ✅"
    })

def obtener_presupuesto_comercial(request):
    data = list(PresupuestoComercial.objects.values())
    return JsonResponse(data, safe=False)

def vista_presupuesto_comercial(request):
    return render(request, 'presupuesto_comercial/presupuesto_comercial_final.html')

#  ---------------------NOMINA-------------------------------------------------------------
def presupuestoNomina(request):
    # Obtener o crear registro de parámetros
    parametros, created = ParametrosPresupuestos.objects.get_or_create(id=1)

    # --- AJAX ---
    if request.method == "POST" and request.headers.get("x-requested-with") == "XMLHttpRequest":
        action = request.POST.get("action")

        # 🔹 Agregar un nuevo nombre de cargo
        if action == "insertar_concepto":
            nombrecar = request.POST.get("nombrecar", "").strip().upper()
            if not nombrecar:
                return JsonResponse({"status": "error", "msg": "Debe ingresar un nombre de cargo"})

            ConceptosFijosYVariables.objects.create(
                nombrecar=nombrecar,
                centro_tra="", nombre_cen="", codcosto="", nomcosto="",
                tipocpto="", cuenta="", concepto="", nombre_con="",
                cargo="", cedula=0, nombre="",
                arlporc=0, concepto_f=0, enero=0, febrero=0, marzo=0,
                abril=0, mayo=0, junio=0, julio=0, agosto=0, septiembre=0,
                total=0
            )
            return JsonResponse({"status": "ok", "msg": f"Cargo '{nombrecar}' agregado correctamente ✅"})

        # 🔹 Agregar un nuevo NOMCOSTO
        elif action == "insertar_nomcosto":
            nomcosto = request.POST.get("nomcosto", "").strip().upper()
            if not nomcosto:
                return JsonResponse({"status": "error", "msg": "Debe ingresar un nombre de costo"})

            ConceptosFijosYVariables.objects.create(
                nomcosto=nomcosto,
                centro_tra="", nombre_cen="", codcosto="",
                tipocpto="", cuenta="", concepto="", nombre_con="",
                cargo="", nombrecar="", cedula=0, nombre="",
                arlporc=0, concepto_f=0, enero=0, febrero=0, marzo=0,
                abril=0, mayo=0, junio=0, julio=0, agosto=0, septiembre=0,
                total=0
            )
            return JsonResponse({"status": "ok", "msg": f"NOMCOSTO '{nomcosto}' agregado correctamente ✅"})

        # 🔹 Actualización de parámetros
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

    # --- Cargar listas desplegables ---
    nombres_cargos = ConceptosFijosYVariables.objects.values_list("nombrecar", flat=True).distinct()
    nombres_costos = ConceptosFijosYVariables.objects.values_list("nomcosto", flat=True).distinct()

    return render(request, "presupuesto_nomina/dashboard_nomina.html", {
        "parametros": parametros,
        "nombres_cargos": [n for n in nombres_cargos if n],
        "nombres_costos": [n for n in nombres_costos if n],
    })
def presupuesto_sueldos(request):
    # 🔹 Obtener valores únicos de ambas tablas
    centros = set(ConceptosFijosYVariables.objects.values_list('nombre_cen', flat=True))
    areas = set(ConceptosFijosYVariables.objects.values_list('nomcosto', flat=True))
    cargos = set(ConceptosFijosYVariables.objects.values_list('nombrecar', flat=True))

    context = {
        'centros': sorted(list(filter(None, centros))),
        'areas': sorted(list(filter(None, areas))),
        'cargos': sorted(list(filter(None, cargos))),
    }

    return render(request, "presupuesto_nomina/presupuesto_nomina.html", context)

def obtener_nomina_temp(request):
    data = list(PresupuestoSueldosAux.objects.values())
    return JsonResponse(data, safe=False)

def tabla_auxiliar_sueldos(request):
    parametros = ParametrosPresupuestos.objects.first()
    incremento_salarial = parametros.incremento_salarial if parametros else 0
    salario = parametros.salario_minimo if parametros else 0

    centros = set(ConceptosFijosYVariables.objects.values_list('nombre_cen', flat=True))
    areas = set(ConceptosFijosYVariables.objects.values_list('nomcosto', flat=True))
    cargos = set(ConceptosFijosYVariables.objects.values_list('nombrecar', flat=True))

    context = {
        'centros': sorted(list(filter(None, centros))),
        'areas': sorted(list(filter(None, areas))),
        'cargos': sorted(list(filter(None, cargos))),
        'incrementoSalarial': incremento_salarial,
        'salarioMinimo': salario,
    }

    return render(request, "presupuesto_nomina/aux_presupuesto_nomina.html", context)

def cargar_nomina_base(request):
    """
    Llena la tabla auxiliar con datos de ConceptosFijosYVariables
    """
    PresupuestoSueldosAux.objects.all().delete()  # limpia tabla temporal
    base_data = ConceptosFijosYVariables.objects.values(
        "cedula","nombre","nombrecar","nomcosto","nombre_cen","concepto_f", "nombre_con"
    )

    # filtrar solo concepto = 001
    base_data = base_data.filter(concepto="001")
    
    for row in base_data:
        PresupuestoSueldosAux.objects.create(
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

                registros.append(PresupuestoSueldosAux(**row_filtrado))

            # Inserción masiva optimizada
            with transaction.atomic():
                PresupuestoSueldosAux.objects.all().delete()
                PresupuestoSueldosAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def guardar_nomina(request):
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

                registros.append(PresupuestoSueldos(**row_filtrado))

            # Inserción masiva optimizada
            with transaction.atomic():
                PresupuestoSueldos.objects.all().delete()
                PresupuestoSueldos.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def subir_presupuesto_sueldos(request):
    if request.method == "POST":
        temporales = PresupuestoSueldosAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        # Convertimos todas las cédulas existentes a string sin espacios
        cedulas_existentes = set(
            str(c).strip() for c in PresupuestoSueldos.objects.values_list("cedula", flat=True)
        )
        creados = 0
        omitidos = 0
        for temp in temporales:
            if temp.cedula in cedulas_existentes:
                omitidos += 1
                continue  # ya existe → no crear

            PresupuestoSueldos.objects.create(
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
                fecha_carga=timezone.now()
            )
            creados += 1

        if creados == 0:
            msg = f"No se agregó ningún registro. ({omitidos} ya existían) ⚠️"
        else:
            msg = f"{creados} registro(s) agregado(s) ✅"

        return JsonResponse({
            "success": True,
            "msg": msg
        })
    
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    

def listar_versiones():
    return (
        PresupuestoSueldos.objects
        .values("version")
        .annotate(fecha=Max("fecha_carga"))
        .order_by("-version")
    )

def obtener_presupuesto_sueldos(request):
    data = list(PresupuestoSueldos.objects.values())
    return JsonResponse({"data": data}, safe=False)

@csrf_exempt
def borrar_presupuesto_sueldos(request):
    if request.method == "POST":
        PresupuestoSueldos.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

# -------------------------------COMISIONES---------------------------------
def comisiones(request):
    # 🔹 Obtener valores únicos de ambas tablas
    centros = set(ConceptosFijosYVariables.objects.values_list('nombre_cen', flat=True))
    areas = set(ConceptosFijosYVariables.objects.values_list('nomcosto', flat=True))
    cargos = set(ConceptosFijosYVariables.objects.values_list('nombrecar', flat=True))
    
    context = {
        'centros': sorted(list(filter(None, centros))),
        'areas': sorted(list(filter(None, areas))),
        'cargos': sorted(list(filter(None, cargos))),
    }
    return render(request, "presupuesto_nomina/comisiones.html", context)

def obtener_presupuesto_comisiones(request):
    comisiones = list(PresupuestoComisiones.objects.values())
    return JsonResponse({"data": comisiones}, safe=False)

def tabla_auxiliar_comisiones(request):
    # obtener el incremento de comisiones desde la tabla auxiliar
    parametros = ParametrosPresupuestos.objects.first()
    incremento_comisiones = parametros.incremento_comisiones if parametros else 0
    centros = set(ConceptosFijosYVariables.objects.values_list('nombre_cen', flat=True))
    areas = set(ConceptosFijosYVariables.objects.values_list('nomcosto', flat=True))
    cargos = set(ConceptosFijosYVariables.objects.values_list('nombrecar', flat=True))
    
    context = {
        'centros': sorted(list(filter(None, centros))),
        'areas': sorted(list(filter(None, areas))),
        'cargos': sorted(list(filter(None, cargos))),
        'incrementoComisiones': incremento_comisiones,
    }
    return render(request, "presupuesto_nomina/aux_comisiones.html", context)

def subir_presupuesto_comisiones(request):
    if request.method == "POST":
        temporales = PresupuestoComisionesAux.objects.all()

        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)
        # obtener las cédulas existentes en la tabla principal
        cedulas_existentes = set(
            PresupuestoComisiones.objects.values_list("cedula", flat=True)
        )
        creados = 0
        omitidos = 0
        for temp in temporales:
            if temp.cedula in cedulas_existentes:
                omitidos += 1
                continue  # ya existe → no crear
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
            creados += 1
        if creados == 0:
            msg = f"No se agregó ningún registro. ({omitidos} ya existían) ⚠️"
        else:
            msg = f"{creados} registro(s) agregado(s) ✅"
        return JsonResponse({
            "success": True,
            "msg": msg
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
            with transaction.atomic():
                PresupuestoComisionesAux.objects.all().delete()
                PresupuestoComisionesAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def guardar_comisiones(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

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

                registros.append(PresupuestoComisiones(**row_filtrado))

            # Inserción masiva optimizada
            with transaction.atomic():
                PresupuestoComisiones.objects.all().delete()
                PresupuestoComisiones.objects.bulk_create(registros)

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
        "junio", "julio", "agosto", "septiembre", "total"
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
            septiembre=row["septiembre"] or 0,
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
    # 🔹 Obtener valores únicos de ambas tablas
    centros = set(ConceptosFijosYVariables.objects.values_list('nombre_cen', flat=True))
    areas = set(ConceptosFijosYVariables.objects.values_list('nomcosto', flat=True))
    cargos = set(ConceptosFijosYVariables.objects.values_list('nombrecar', flat=True))

    context = {
        'centros': sorted(list(filter(None, centros))),
        'areas': sorted(list(filter(None, areas))),
        'cargos': sorted(list(filter(None, cargos))),
    }
    return render(request, "presupuesto_nomina/horas_extra.html", context)

def obtener_presupuesto_horas_extra(request):
    horas_extra = list(PresupuestoHorasExtra.objects.values())
    return JsonResponse({"data": horas_extra}, safe=False)

def tabla_auxiliar_horas_extra(request):
    # obtener el incremento de horas extra desde la tabla auxiliar
    parametros = ParametrosPresupuestos.objects.first()
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
        # obtener las cédulas existentes en la tabla principal
        cedulas_existentes = set(
            PresupuestoHorasExtra.objects.values_list("cedula", flat=True)
        )
        creados = 0
        omitidos = 0
        for temp in temporales:
            if temp.cedula in cedulas_existentes:
                omitidos += 1
                continue  # ya existe → no crear
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
            creados += 1
        if creados == 0:
            msg = f"No se agregó ningún registro. ({omitidos} ya existían) ⚠️"
        else:
            msg = f"{creados} registro(s) agregado(s) ✅"
        return JsonResponse({
            "success": True,
            "msg": msg
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
            with transaction.atomic():
                PresupuestoHorasExtraAux.objects.all().delete()
                PresupuestoHorasExtraAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def guardar_horas_extra(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

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

                registros.append(PresupuestoHorasExtra(**row_filtrado))

            # Inserción masiva optimizada
            with transaction.atomic():
                PresupuestoHorasExtra.objects.all().delete()
                PresupuestoHorasExtra.objects.bulk_create(registros)

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
        "junio", "julio", "agosto", "septiembre", "total"
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
            septiembre=Sum("septiembre"),
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
            septiembre=row["septiembre"] or 0,
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
    # 🔹 Obtener valores únicos de ambas tablas
    centros = set(ConceptosFijosYVariables.objects.values_list('nombre_cen', flat=True))
    areas = set(ConceptosFijosYVariables.objects.values_list('nomcosto', flat=True))
    cargos = set(ConceptosFijosYVariables.objects.values_list('nombrecar', flat=True))

    context = {
        'centros': sorted(list(filter(None, centros))),
        'areas': sorted(list(filter(None, areas))),
        'cargos': sorted(list(filter(None, cargos))),
    }
    return render(request, "presupuesto_nomina/medios_transporte.html", context)

def obtener_presupuesto_medios_transporte(request):
    medios_transporte = list(PresupuestoMediosTransporte.objects.values())
    return JsonResponse({"data": medios_transporte}, safe=False)

def tabla_auxiliar_medios_transporte(request):
    # obtener el incremento de medios de transporte desde la tabla auxiliar
    parametros = ParametrosPresupuestos.objects.first()
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
        # obtener las cédulas existentes en la tabla principal
        cedulas_existentes = set(
            PresupuestoMediosTransporte.objects.values_list("cedula", flat=True)
        )
        creados = 0
        omitidos = 0
        for temp in temporales:
            if temp.cedula in cedulas_existentes:
                omitidos += 1
                continue  # ya existe → no crear
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
            creados += 1
        if creados == 0:
            msg = f"No se agregó ningún registro. ({omitidos} ya existían) ⚠️"
        else:
            msg = f"{creados} registro(s) agregado(s) ✅"
        return JsonResponse({
            "success": True,
            "msg": msg
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
            with transaction.atomic():
                PresupuestoMediosTransporteAux.objects.all().delete()
                PresupuestoMediosTransporteAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def guardar_medios_transporte(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "base", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

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

                registros.append(PresupuestoMediosTransporte(**row_filtrado))

            # Inserción masiva optimizada
            with transaction.atomic():
                PresupuestoMediosTransporte.objects.all().delete()
                PresupuestoMediosTransporte.objects.bulk_create(registros)

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
    # 🔹 Obtener valores únicos de ambas tablas
    centros = set(ConceptosFijosYVariables.objects.values_list('nombre_cen', flat=True))
    areas = set(ConceptosFijosYVariables.objects.values_list('nomcosto', flat=True))
    cargos = set(ConceptosFijosYVariables.objects.values_list('nombrecar', flat=True))

    context = {
        'centros': sorted(list(filter(None, centros))),
        'areas': sorted(list(filter(None, areas))),
        'cargos': sorted(list(filter(None, cargos))),
    }
    return render(request, "presupuesto_nomina/auxilio_transporte.html", context)

def obtener_presupuesto_auxilio_transporte(request):
    auxilio_transporte = list(PresupuestoAuxilioTransporte.objects.values())
    return JsonResponse({"data": auxilio_transporte}, safe=False)

def tabla_auxiliar_auxilio_transporte(request):
    # obtener el auxilio de transporte desde la tabla auxiliar
    parametros = ParametrosPresupuestos.objects.first()
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

        # obtener cedulas de la tabla principal
        cedulas_existentes = set(
            PresupuestoAuxilioTransporte.objects.values_list("cedula", flat=True)
        )
        creados = 0
        omitidos = 0
        
        for temp in temporales:
            if temp.cedula in cedulas_existentes:
                omitidos += 1
                continue  # ya existe → no crear
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
            creados += 1
            
        if creados == 0:
            msg = f"No se agregó ningún registro. ({omitidos} ya existían) ⚠️"
        else:
            msg = f"{creados} registro(s) agregado(s) ✅"
        return JsonResponse({
            "success": True,
            "msg": msg
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
            with transaction.atomic():
                PresupuestoAuxilioTransporteAux.objects.all().delete()
                PresupuestoAuxilioTransporteAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def guardar_auxilio_transporte(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "base", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

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

                registros.append(PresupuestoAuxilioTransporte(**row_filtrado))

            # Inserción masiva optimizada
            with transaction.atomic():
                PresupuestoAuxilioTransporte.objects.all().delete()
                PresupuestoAuxilioTransporte.objects.bulk_create(registros)

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
    parametros = ParametrosPresupuestos.objects.first()
    salarioIncremento = parametros.salario_minimo + (parametros.salario_minimo * (parametros.incremento_salarial / 100))
    LIMITE_SMMLV = (salarioIncremento) * 2
    AUXILIO_BASE = 200000
    MESES = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    PresupuestoAuxilioTransporteAux.objects.all().delete()  # limpia tabla temporal
    # Obtener base de empleados
    # base_data = ConceptosFijosYVariables.objects.filter(concepto__in=["001", "006"]).values(
    #     "cedula", "nombre", "nombrecar", "nomcosto", "nombre_cen", "concepto_f"
    # )
    # Tomo todos los empleados desde nómina (puede ser tu base principal)
    empleados = PresupuestoSueldosAux.objects.all().values(
    "cedula", "nombre", "centro", "area", "cargo", "salario_base"
    )
    # Tomo también los aprendices
    aprendices = PresupuestoAprendizAux.objects.filter(concepto="SALARIO APRENDIZ REFORMA").values(
    "cedula", "nombre", "centro", "area", "cargo", "salario_base"
    )
    # Uno empleados y aprendices en una sola lista
    base_data = list(empleados) + list(aprendices)
    for row in base_data:
        aux = PresupuestoAuxilioTransporteAux.objects.create(
            cedula=row["cedula"],
            nombre=row["nombre"],
            cargo=row["cargo"],
            area=row["area"],
            centro=row["centro"],
            concepto="AUXILIO DE TRANSPORTE",
            base=AUXILIO_BASE,
        )

        # 🔹 recorrer meses
        for mes in MESES:
            
            total_mes = 0
            if mes != "marzo":
                # Sumar el valor del mes en todas las tablas
                total_mes += PresupuestoMediosTransporteAux.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0
                total_mes += PresupuestoSueldosAux.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0
                total_mes += PresupuestoComisionesAux.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0
                total_mes += PresupuestoHorasExtraAux.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0
                total_mes += PresupuestoAprendizAux.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0
                # descargar en un archivo de texto los totales por mes y cédula
                # with open("totales_auxilio_transporte.txt", "a") as f:
                #     f.write(f"Cédula: {row['cedula']} - cargo: {row['cargo']} - Mes: {mes} - Total antes de aux: {total_mes}\n")  
                # 🔹 Condición: si la suma < SMMLV, asignar 200000 a ese mes
                if total_mes < LIMITE_SMMLV:
                    setattr(aux, mes, AUXILIO_BASE)
                # si total_mes es igual a cero poner cero en el mes
                if total_mes == 0:
                    setattr(aux, mes, 0)
            else: 
                # salario = row["salario_base"] or 0
                # if salario < salarioIncremento:
                #     salario = salarioIncremento
                     
                # nuevo_salario = salario + (salario * (parametros.incremento_salarial / 100))
                # auxRetroactivo = (nuevo_salario - salario) * 2  # retroactivo de enero y febrero
              
                mes_temp = "abril"
                total_mes += PresupuestoMediosTransporteAux.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0
                total_mes += PresupuestoSueldosAux.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes_temp))["s"] or 0
                total_mes += PresupuestoComisionesAux.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0
                total_mes += PresupuestoHorasExtraAux.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0
                total_mes += PresupuestoAprendizAux.objects.filter(cedula=row["cedula"]).aggregate(s=Sum(mes))["s"] or 0
                total_mes_marzo = total_mes
                # total_mes_marzo -= auxRetroactivo
                
                # 🔹 Condición: si la suma < SMMLV, asignar 200000 a ese mes
                if total_mes == 0:
                    setattr(aux, mes, 0)
                elif total_mes_marzo < LIMITE_SMMLV:
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
    # 🔹 Obtener valores únicos de ambas tablas
    centros = set(ConceptosFijosYVariables.objects.values_list('nombre_cen', flat=True))
    areas = set(ConceptosFijosYVariables.objects.values_list('nomcosto', flat=True))
    cargos = set(ConceptosFijosYVariables.objects.values_list('nombrecar', flat=True))

    context = {
        'centros': sorted(list(filter(None, centros))),
        'areas': sorted(list(filter(None, areas))),
        'cargos': sorted(list(filter(None, cargos))),
    }
    return render(request, "presupuesto_nomina/ayuda_transporte.html", context)

def obtener_presupuesto_ayuda_transporte(request):
    ayuda_transporte = list(PresupuestoAyudaTransporte.objects.values())
    return JsonResponse({"data": ayuda_transporte}, safe=False)

def tabla_auxiliar_ayuda_transporte(request):
    # obtener la ayuda de transporte desde la tabla auxiliar
    parametros = ParametrosPresupuestos.objects.first()
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
        # obtener las cédulas existentes en la tabla principal
        cedulas_existentes = set(
            PresupuestoAyudaTransporte.objects.values_list("cedula", flat=True)
        )
        creados = 0
        omitidos = 0
        for temp in temporales:
            if temp.cedula in cedulas_existentes:
                omitidos += 1
                continue  # ya existe → no crear
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
            creados += 1
        if creados == 0:
            msg = f"No se agregó ningún registro. ({omitidos} ya existían) ⚠️"
        else:
            msg = f"{creados} registro(s) agregado(s) ✅"
        return JsonResponse({
            "success": True,
            "msg": msg
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
            with transaction.atomic():
                PresupuestoAyudaTransporteAux.objects.all().delete()
                PresupuestoAyudaTransporteAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def guardar_ayuda_transporte(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "base", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

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

                registros.append(PresupuestoAyudaTransporte(**row_filtrado))

            # Inserción masiva optimizada
            with transaction.atomic():
                PresupuestoAyudaTransporte.objects.all().delete()
                PresupuestoAyudaTransporte.objects.bulk_create(registros)

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
    centros = set(ConceptosFijosYVariables.objects.values_list('nombre_cen', flat=True))
    areas = set(ConceptosFijosYVariables.objects.values_list('nomcosto', flat=True))
    cargos = set(ConceptosFijosYVariables.objects.values_list('nombrecar', flat=True))
    context = {
        'centros': sorted(list(filter(None, centros))),
        'areas': sorted(list(filter(None, areas))),
        'cargos': sorted(list(filter(None, cargos))),
    }
    return render(request, "presupuesto_nomina/cesantias.html", context)

def obtener_presupuesto_cesantias(request):
    cesantias = list(PresupuestoCesantias.objects.values())
    return JsonResponse({"data": cesantias}, safe=False)

def tabla_auxiliar_cesantias(request):
    # obtener el auxilio de transporte desde la tabla auxiliar
    parametros = ParametrosPresupuestos.objects.first()
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

        # obtener cedulas de la tabla principal
        cedulas_existentes = set(
            PresupuestoCesantias.objects.values_list("cedula", flat=True)
        )
        creados = 0
        omitidos = 0

        for temp in temporales:
            if temp.cedula in cedulas_existentes:
                omitidos += 1
                continue  # ya existe → no crear
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
            creados += 1
        if creados == 0:
            msg = f"No se agregó ningún registro. ({omitidos} ya existían) ⚠️"
        else:
            msg = f"{creados} registro(s) agregado(s) ✅"
        return JsonResponse({
            "success": True,
            "msg": msg
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
            with transaction.atomic():
                PresupuestoCesantiasAux.objects.all().delete()
                PresupuestoCesantiasAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def guardar_cesantias(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

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

                registros.append(PresupuestoCesantias(**row_filtrado))

            # Inserción masiva optimizada
            with transaction.atomic():
                PresupuestoCesantias.objects.all().delete()
                PresupuestoCesantias.objects.bulk_create(registros)

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
    empleados = PresupuestoSueldosAux.objects.all()
    # Tomo también los aprendices
    aprendices = PresupuestoAprendizAux.objects.filter(concepto="SALARIO APRENDIZ REFORMA")
    
    # # Uno empleados y aprendices en una sola lista
    personas = list(empleados) + list(aprendices)
    for emp in personas:
        # Inicializo acumuladores por mes
        data_meses = {mes: 0 for mes in meses}

        # Sumo de sueldos
        sueldos = PresupuestoSueldosAux.objects.filter(cedula=emp.cedula, area=emp.area).first()
        if sueldos:
            for mes in meses:
                data_meses[mes] += getattr(sueldos, mes, 0)

        # Sumo de comisiones
        comision = PresupuestoComisionesAux.objects.filter(cedula=emp.cedula, area=emp.area).first()
        if comision:
            for mes in meses:
                data_meses[mes] += getattr(comision, mes, 0)
                
        # Sumo de medios de transporte
        medio = PresupuestoMediosTransporteAux.objects.filter(cedula=emp.cedula, area=emp.area).first()
        if medio:
            for mes in meses:
                data_meses[mes] += getattr(medio, mes, 0)

        # Sumo de auxilio transporte
        aux = PresupuestoAuxilioTransporteAux.objects.filter(cedula=emp.cedula, area=emp.area).first()
        if aux:
            for mes in meses:
                data_meses[mes] += getattr(aux, mes, 0)

        # Sumo de horas extra
        extra = PresupuestoHorasExtraAux.objects.filter(cedula=emp.cedula, area=emp.area).first()
        if extra:
            for mes in meses:
                data_meses[mes] += getattr(extra, mes, 0)
        
        # Sumo de aprendices
        aprendiz = PresupuestoAprendizAux.objects.filter(cedula=emp.cedula, area=emp.area).first()
        if aprendiz:
            for mes in meses:
                data_meses[mes] += getattr(aprendiz, mes, 0)

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
    centros = set(ConceptosFijosYVariables.objects.values_list('nombre_cen', flat=True))
    areas = set(ConceptosFijosYVariables.objects.values_list('nomcosto', flat=True))
    cargos = set(ConceptosFijosYVariables.objects.values_list('nombrecar', flat=True))
    context = {
        'centros': sorted(list(filter(None, centros))),
        'areas': sorted(list(filter(None, areas))),
        'cargos': sorted(list(filter(None, cargos))),
    }
    return render(request, "presupuesto_nomina/prima.html", context)

def obtener_presupuesto_prima(request):
    prima = list(PresupuestoPrima.objects.values())
    return JsonResponse({"data": prima}, safe=False)

def tabla_auxiliar_prima(request):
    # obtener la prima desde la tabla auxiliar
    parametros = ParametrosPresupuestos.objects.first()
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
        # obtener cedulas de la tabla principal
        cedulas_existentes = set(
            PresupuestoPrima.objects.values_list("cedula", flat=True)
        )
        creados = 0
        omitidos = 0

        for temp in temporales:
            if temp.cedula in cedulas_existentes:
                omitidos += 1
                continue  # ya existe → no crear
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
            creados += 1
        if creados == 0:
            msg = f"No se agregó ningún registro. ({omitidos} ya existían) ⚠️"
        else:
            msg = f"{creados} registro(s) agregado(s) ✅"
        return JsonResponse({
            "success": True,
            "msg": msg
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
            with transaction.atomic():
                PresupuestoPrimaAux.objects.all().delete()
                PresupuestoPrimaAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def guardar_prima(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

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

                registros.append(PresupuestoPrima(**row_filtrado))

            # Inserción masiva optimizada
            with transaction.atomic():
                PresupuestoPrima.objects.all().delete()
                PresupuestoPrima.objects.bulk_create(registros)

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
    empleados = PresupuestoSueldosAux.objects.all()
    # Tomo también los aprendices
    aprendices = PresupuestoAprendizAux.objects.filter(concepto="SALARIO APRENDIZ REFORMA")
    # Uno empleados y aprendices en una sola lista
    personas = list(empleados) + list(aprendices)
    
    for emp in personas:
        # Inicializo acumuladores por mes
        data_meses = {mes: 0 for mes in meses}

        # Sumo de sueldos
        sueldos = PresupuestoSueldosAux.objects.filter(cedula=emp.cedula, area=emp.area).first()
        if sueldos:
            for mes in meses:
                data_meses[mes] += getattr(sueldos, mes, 0)

        # Sumo de comisiones
        comision = PresupuestoComisionesAux.objects.filter(cedula=emp.cedula, area=emp.area).first()
        if comision:
            for mes in meses:
                data_meses[mes] += getattr(comision, mes, 0)
                
        # Sumo de medios de transporte
        medio = PresupuestoMediosTransporteAux.objects.filter(cedula=emp.cedula, area=emp.area).first()
        if medio:
            for mes in meses:
                data_meses[mes] += getattr(medio, mes, 0)

        # Sumo de auxilio transporte
        aux = PresupuestoAuxilioTransporteAux.objects.filter(cedula=emp.cedula, area=emp.area).first()
        if aux:
            for mes in meses:
                data_meses[mes] += getattr(aux, mes, 0)

        # Sumo de horas extra
        extra = PresupuestoHorasExtraAux.objects.filter(cedula=emp.cedula, area=emp.area).first()
        if extra:
            for mes in meses:
                data_meses[mes] += getattr(extra, mes, 0)
        
        # Sumo de aprendices
        aprendiz = PresupuestoAprendizAux.objects.filter(cedula=emp.cedula, area=emp.area).first()
        if aprendiz:
            for mes in meses:
                data_meses[mes] += getattr(aprendiz, mes, 0)

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
    centros = set(ConceptosFijosYVariables.objects.values_list('nombre_cen', flat=True))
    areas = set(ConceptosFijosYVariables.objects.values_list('nomcosto', flat=True))
    cargos = set(ConceptosFijosYVariables.objects.values_list('nombrecar', flat=True))
    context = {
        'centros': sorted(list(filter(None, centros))),
        'areas': sorted(list(filter(None, areas))),
        'cargos': sorted(list(filter(None, cargos))),
    }
    return render(request, "presupuesto_nomina/vacaciones.html", context)

def obtener_presupuesto_vacaciones(request):
    vacaciones = list(PresupuestoVacaciones.objects.values())
    return JsonResponse({"data": vacaciones}, safe=False)

def tabla_auxiliar_vacaciones(request):
    # obtener la vacaciones desde la tabla auxiliar
    parametros = ParametrosPresupuestos.objects.first()
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
        # obtener cedulas de la tabla principal
        cedulas_existentes = set(
            PresupuestoVacaciones.objects.values_list("cedula", flat=True)
        )
        creados = 0
        omitidos = 0

        for temp in temporales:
            if temp.cedula in cedulas_existentes:
                omitidos += 1
                continue  # ya existe → no crear
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
            creados += 1
        if creados == 0:
            msg = f"No se agregó ningún registro. ({omitidos} ya existían) ⚠️"
        else:
            msg = f"{creados} registro(s) agregado(s) ✅"
        return JsonResponse({
            "success": True,
            "msg": msg
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
            with transaction.atomic():
                PresupuestoVacacionesAux.objects.all().delete()
                PresupuestoVacacionesAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def guardar_vacaciones(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

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

                registros.append(PresupuestoVacaciones(**row_filtrado))

            # Inserción masiva optimizada
            with transaction.atomic():
                PresupuestoVacaciones.objects.all().delete()
                PresupuestoVacaciones.objects.bulk_create(registros)

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
    empleados = PresupuestoSueldosAux.objects.all()
    # Tomo también los aprendices
    aprendices = PresupuestoAprendizAux.objects.filter(concepto="SALARIO APRENDIZ REFORMA")
    # Uno empleados y aprendices en una sola lista
    personas = list(empleados) + list(aprendices)
    for emp in personas:
        # Inicializo acumuladores por mes
        data_meses = {mes: 0 for mes in meses}

        # Sumo de nómina
        for mes in meses:
            data_meses[mes] += getattr(emp, mes, 0)

        # Sumo de comisiones
        comision = PresupuestoComisionesAux.objects.filter(cedula=emp.cedula).first()
        if comision:
            for mes in meses:
                data_meses[mes] += getattr(comision, mes, 0)
                
        # Sumo de medios de transporte
        medio = PresupuestoMediosTransporteAux.objects.filter(cedula=emp.cedula).first()
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
    centros = set(ConceptosFijosYVariables.objects.values_list('nombre_cen', flat=True))
    areas = set(ConceptosFijosYVariables.objects.values_list('nomcosto', flat=True))
    cargos = set(ConceptosFijosYVariables.objects.values_list('nombrecar', flat=True))
    context = {
        'centros': sorted(list(filter(None, centros))),
        'areas': sorted(list(filter(None, areas))),
        'cargos': sorted(list(filter(None, cargos))),
    }
    return render(request, "presupuesto_nomina/bonificaciones.html", context)

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
        # obtener cedulas de la tabla principal
        cedulas_existentes = set(
            PresupuestoBonificaciones.objects.values_list("cedula", flat=True)
        )
        creados = 0
        omitidos = 0
        for temp in temporales:
            if temp.cedula in cedulas_existentes:
                omitidos += 1
                continue  # ya existe → no crear
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
            creados += 1
        if creados == 0:
            msg = f"No se agregó ningún registro. ({omitidos} ya existían) ⚠️"
        else:
            msg = f"{creados} registro(s) agregado(s) ✅"
        return JsonResponse({
            "success": True,
            "msg": msg
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
            with transaction.atomic():
                PresupuestoBonificacionesAux.objects.all().delete()
                PresupuestoBonificacionesAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def guardar_bonificaciones(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

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

                registros.append(PresupuestoBonificaciones(**row_filtrado))

            # Inserción masiva optimizada
            with transaction.atomic():
                PresupuestoBonificaciones.objects.all().delete()
                PresupuestoBonificaciones.objects.bulk_create(registros)

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
    empleados = PresupuestoSueldosAux.objects.all()

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

#------------bolsa consumibles (novedad de nomina extra, consumibles y tuberculina)----------------
def bolsa_consumibles(request):
    centros = set(ConceptosFijosYVariables.objects.values_list('nombre_cen', flat=True))
    areas = set(ConceptosFijosYVariables.objects.values_list('nomcosto', flat=True))
    cargos = set(ConceptosFijosYVariables.objects.values_list('nombrecar', flat=True))
    
    context = {
        'centros': sorted(list(filter(None, centros))),
        'areas': sorted(list(filter(None, areas))),
        'cargos': sorted(list(filter(None, cargos))),
    }
    
    return render(request, "presupuesto_nomina/bolsa_consumibles.html", context)

def obtener_presupuesto_bolsa_consumibles(request):
    auxilio_movilidad = list(PresupuestoBolsaConsumibles.objects.values())
    return JsonResponse({"data": auxilio_movilidad}, safe=False)

def tabla_auxiliar_bolsa_consumibles(request):
    parametros = ParametrosPresupuestos.objects.first()
    incremento_ipc = parametros.incremento_ipc if parametros else 0
    return render(request, "presupuesto_nomina/aux_bolsa_consumibles.html", {'incrementoIPC': incremento_ipc})

def subir_presupuesto_bolsa_consumibles(request):
    if request.method == "POST":
        temporales = PresupuestoBolsaConsumiblesAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)
        # obtener cedulas de la tabla principal
        cedulas_existentes = set(
            PresupuestoBolsaConsumibles.objects.values_list("cedula", flat=True)
        )
        creados = 0
        omitidos = 0
        for temp in temporales:
            if temp.cedula in cedulas_existentes:
                omitidos += 1
                continue  # ya existe → no crear
            PresupuestoBolsaConsumibles.objects.create(
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
            creados += 1
        if creados == 0:
            msg = f"No se agregó ningún registro. ({omitidos} ya existían) ⚠️"
        else:
            msg = f"{creados} registro(s) agregado(s) ✅"
        return JsonResponse({
            "success": True,
            "msg": msg
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_bolsa_consumibles_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

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

                registros.append(PresupuestoBolsaConsumiblesAux(**row_filtrado))

            # Inserción masiva optimizada
            with transaction.atomic():
                PresupuestoBolsaConsumiblesAux.objects.all().delete()
                PresupuestoBolsaConsumiblesAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def guardar_bolsa_consumibles(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

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

                registros.append(PresupuestoBolsaConsumibles(**row_filtrado))

            # Inserción masiva optimizada
            with transaction.atomic():
                PresupuestoBolsaConsumibles.objects.all().delete()
                PresupuestoBolsaConsumibles.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_bolsa_consumibles_temp(request):
    data = list(PresupuestoBolsaConsumiblesAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_bolsa_consumibles_base(request):
    PresupuestoBolsaConsumiblesAux.objects.all().delete()  # limpia tabla temporal
    base_data = ConceptosFijosYVariables.objects.values(
        "cedula","nombre","nombrecar","nomcosto","nombre_cen", "nombre_con", "enero", "febrero", "marzo", "abril", "mayo",
        "junio", "julio", "agosto", "total"
    )

    # filtrar solo concepto que sea igual a 389
    base_data = base_data.filter(concepto="E14")
    
    for row in base_data:
        PresupuestoBolsaConsumiblesAux.objects.create(
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
def borrar_presupuesto_bolsa_consumibles(request):
    if request.method == "POST":
        PresupuestoBolsaConsumibles.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de auxilio de movilidad eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#-----------------------Auxilio TBC y KIT----------------------------
def auxilio_TBCKIT(request):
    centros = set(ConceptosFijosYVariables.objects.values_list('nombre_cen', flat=True))
    areas = set(ConceptosFijosYVariables.objects.values_list('nomcosto', flat=True))
    cargos = set(ConceptosFijosYVariables.objects.values_list('nombrecar', flat=True))
    context = {
        'centros': sorted(list(filter(None, centros))),
        'areas': sorted(list(filter(None, areas))),
        'cargos': sorted(list(filter(None, cargos))),
    }
    return render(request, "presupuesto_nomina/auxilio_TBCKIT.html", context)

def obtener_presupuesto_auxilio_TBCKIT(request):
    auxilio_movilidad = list(PresupuestoAuxilioTBCKIT.objects.values())
    return JsonResponse({"data": auxilio_movilidad}, safe=False)

def tabla_auxiliar_auxilio_TBCKIT(request):
    parametros = ParametrosPresupuestos.objects.first()
    incremento_ipc = parametros.incremento_ipc if parametros else 0
    return render(request, "presupuesto_nomina/aux_auxilio_TBCKIT.html", {'incrementoIPC': incremento_ipc})

def subir_presupuesto_auxilio_TBCKIT(request):
    if request.method == "POST":
        temporales = PresupuestoAuxilioTCBKITAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)
        # obtener cedulas de la tabla principal
        cedulas_existentes = set(
            PresupuestoAuxilioTBCKIT.objects.values_list("cedula", flat=True)
        )
        creados = 0
        omitidos = 0
        for temp in temporales:
            if temp.cedula in cedulas_existentes:
                omitidos += 1
                continue  # ya existe → no crear
            PresupuestoAuxilioTBCKIT.objects.create(
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
            creados += 1
        if creados == 0:
            msg = f"No se agregó ningún registro. ({omitidos} ya existían) ⚠️"
        else:
            msg = f"{creados} registro(s) agregado(s) ✅"
        return JsonResponse({
            "success": True,
            "msg": msg
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_auxilio_TBCKIT_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

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

                registros.append(PresupuestoAuxilioTCBKITAux(**row_filtrado))

            # Inserción masiva optimizada
            with transaction.atomic():
                PresupuestoAuxilioTCBKITAux.objects.all().delete()
                PresupuestoAuxilioTCBKITAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def guardar_auxilio_TBCKIT(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

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

                registros.append(PresupuestoAuxilioTBCKIT(**row_filtrado))

            # Inserción masiva optimizada
            with transaction.atomic():
                PresupuestoAuxilioTBCKIT.objects.all().delete()
                PresupuestoAuxilioTBCKIT.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_auxilio_TBCKIT_temp(request):
    data = list(PresupuestoAuxilioTCBKITAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_auxilio_TBCKIT_base(request):
    PresupuestoAuxilioTCBKITAux.objects.all().delete()  # limpia tabla temporal
    base_data = ConceptosFijosYVariables.objects.values(
        "cedula","nombre","nombrecar","nomcosto","nombre_cen", "nombre_con", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "total"
    )

    # filtrar solo concepto que sea igual a 389
    base_data = base_data.filter(concepto="E14")
    
    for row in base_data:
        PresupuestoAuxilioTCBKITAux.objects.create(
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
            septiembre=row["septiembre"] or 0,
            total=row["total"] or 0,
        )

        
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_auxilio_TBCKIT(request):
    if request.method == "POST":
        PresupuestoAuxilioTBCKIT.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de auxilio de movilidad eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)


# ----------------------------SEGURIDAD SOCIAL---------------------
def seguridad_social(request):
    centros = set(ConceptosFijosYVariables.objects.values_list('nombre_cen', flat=True))
    areas = set(ConceptosFijosYVariables.objects.values_list('nomcosto', flat=True))
    context = {
        'centros': sorted(list(filter(None, centros))),
        'areas': sorted(list(filter(None, areas))),
    }
    return render(request, "presupuesto_nomina/seguridad_social.html", context)

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
        # obtener nombres de la tabla principal
        nombres_existentes = set(
            PresupuestoSeguridadSocial.objects.values_list("nombre", flat=True)
        )
        creados = 0
        omitidos = 0
        for temp in temporales:
            if temp.nombre in nombres_existentes:
                omitidos += 1
                continue  # ya existe → no crear
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
            creados += 1
        if creados == 0:
            msg = f"No se agregó ningún registro. ({omitidos} ya existían) ⚠️"
        else:
            msg = f"{creados} registro(s) agregado(s) ✅"
        return JsonResponse({
            "success": True,
            "msg": msg
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
                "nombre", "centro", "area", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

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
            with transaction.atomic():
                PresupuestoSeguridadSocialAux.objects.all().delete()
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
    # tomar 2 decimales
    arl_porcentajes = {key: round(value, 4) for key, value in arl_porcentajes.items()}
    
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
        "APORTE A.R.L": None,              # 0.93%
        "APORTE SENA": 0.02,                  # 2%
        "APORTE I.C.B.F": 0.03                # 3%
    }

    # Salario mínimo (ajusta según el año correspondiente)
    parametros = ParametrosPresupuestos.objects.first()
    salarioIncremento = parametros.salario_minimo + (parametros.salario_minimo * (parametros.incremento_salarial / 100))
   
    TOPE = (salarioIncremento) * 10
    
    # Limpio tabla antes de recalcular
    PresupuestoSeguridadSocialAux.objects.all().delete()

    # Diccionarios separados para acumulación
    acumulados_generales = defaultdict(lambda: {mes: 0 for mes in meses})  # pensión, cajas, ARL, SENA
    acumulados_salud_icbf = defaultdict(lambda: {mes: 0 for mes in meses})  # solo > 10 SMMLV
    acumulados_aprendiz_salud = defaultdict(lambda: {mes: 0 for mes in meses}) # aprendices con salario aprendiz
   
    empleados = PresupuestoSueldos.objects.all()
    aprendices = PresupuestoAprendiz.objects.all()
    medios = PresupuestoMediosTransporte.objects.all()
    comisiones = PresupuestoComisiones.objects.all()
    horas_extra = PresupuestoHorasExtra.objects.all()
    bandera = False
    # Primero agrupar las bases de sueldos por centro y área
    for emp in empleados:
        key = (emp.centro, emp.area)
        salario_base = emp.salario_base
        nuevo_salario = salario_base + (salario_base * (parametros.incremento_salarial / 100))
        for mes in meses:
            # Base mensual del sueldo
            base_mes = getattr(emp, mes, 0)
            acumulados_generales[key][mes] += base_mes

            if nuevo_salario > TOPE:
                bandera = True
                acumulados_salud_icbf[key][mes] += base_mes
    
    # Luego agrupar los medios de transporte por centro y área
    for medio in medios:
        cc = medio.cedula
        key = (medio.centro, medio.area)
        for mes in meses:
            acumulados_generales[key][mes] += getattr(medio, mes, 0)
           
            if bandera and cc == "31793592":
                acumulados_salud_icbf[key][mes] += getattr(medio, mes, 0)
    
    # Luego agrupar las comisiones por centro y área
    for comi in comisiones:
        cc = comi.cedula
        key = (comi.centro, comi.area)
        for mes in meses:
            acumulados_generales[key][mes] += getattr(comi, mes, 0)
            if bandera and cc == "31793592":
                acumulados_salud_icbf[key][mes] += getattr(comi, mes, 0)
    
    # Luego agrupar las horas extra por centro y área
    for hora in horas_extra:
        cc = hora.cedula
        key = (hora.centro, hora.area)
        for mes in meses:
            acumulados_generales[key][mes] += getattr(hora, mes, 0)
            if bandera and cc == "31793592":
                acumulados_salud_icbf[key][mes] += getattr(hora, mes, 0)
    
    # print("acumulados icbf:", acumulados_salud_icbf)
    # === APRENDICES (tabla aparte) ===
    # cambiar los valores (lo que esta en cero se deja en cero) por el salario minimo incremento
    for apr in aprendices:
        for mes in meses:
            if getattr(apr, mes, 0) > 0:
                setattr(apr, mes, salarioIncremento)
    
    for apr in aprendices:
        cc = apr.cedula
        if apr.concepto == "SALARIO APRENDIZ":
            key = (apr.centro, apr.area)
            for mes in meses:
                acumulados_aprendiz_salud[key][mes] += getattr(apr, mes, 0)
                if bandera and cc == "31793592":
                    acumulados_salud_icbf[key][mes] += getattr(apr, mes, 0)
        if apr.concepto == "SALARIO APRENDIZ REFORMA":
            # además suman a todos los aportes (como parte de la base general)
            key = (apr.centro, apr.area)
            for mes in meses:
                acumulados_generales[key][mes] += getattr(apr, mes, 0)
                if bandera and cc == "31793592":
                    acumulados_salud_icbf[key][mes] += getattr(apr, mes, 0)

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
                porcentaje = arl_porcentajes.get((centro, area), 0.0093)
            else:
                data = data_meses

            valores_mensuales = {mes: data[mes] * porcentaje for mes in meses} 
            PresupuestoSeguridadSocialAux.objects.create(
                nombre="SEGURIDAD SOCIAL",
                centro=centro,
                area=area,
                concepto=concepto,
                **valores_mensuales,
                total=round(sum(valores_mensuales.values()))
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
    centros = set(ConceptosFijosYVariables.objects.values_list('nombre_cen', flat=True))
    areas = set(ConceptosFijosYVariables.objects.values_list('nomcosto', flat=True))
    cargos = set(ConceptosFijosYVariables.objects.values_list('nombrecar', flat=True))
    context = {
        'centros': sorted(list(filter(None, centros))),
        'areas': sorted(list(filter(None, areas))),
        'cargos': sorted(list(filter(None, cargos))),
    }
    return render(request, "presupuesto_nomina/intereses_cesantias.html", context)

def obtener_presupuesto_intereses_cesantias(request):
    intereses_cesantias = list(PresupuestoInteresesCesantias.objects.values())
    return JsonResponse({"data": intereses_cesantias}, safe=False)

def tabla_auxiliar_intereses_cesantias(request):
    # obtener la cesantías desde la tabla auxiliar
    parametros = ParametrosPresupuestos.objects.first()
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

        # obtener cedulas de la tabla principal
        cedulas_existentes = set(
            PresupuestoInteresesCesantias.objects.values_list('cedula', flat=True)
        )
        creados = 0
        omitidos = 0
        for temp in temporales:
            if temp.cedula in cedulas_existentes:
                omitidos += 1
                continue  # omitir si ya existe
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
            creados += 1
        if creados == 0:
            msg = f"No se agregó ningún registro. ({omitidos} ya existían) ⚠️"
        else:
            msg = f"{creados} registro(s) agregado(s) ✅"
        return JsonResponse({
            "success": True,
            "msg": msg
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
            with transaction.atomic():
                PresupuestoInteresesCesantiasAux.objects.all().delete()
                PresupuestoInteresesCesantiasAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def guardar_intereses_cesantias(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

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

                registros.append(PresupuestoInteresesCesantias(**row_filtrado))

            # Inserción masiva optimizada
            with transaction.atomic():
                PresupuestoInteresesCesantias.objects.all().delete()
                PresupuestoInteresesCesantias.objects.bulk_create(registros)

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

    # Parametrización
    parametros = ParametrosPresupuestos.objects.first()
    interesCesantias = parametros.intereses_cesantias if parametros else 0
    print(f"Intereses cesantías parámetro: {interesCesantias}")

    # Limpiar tabla auxiliar antes de recalcular
    PresupuestoInteresesCesantiasAux.objects.all().delete()

    cesantias_qs = PresupuestoCesantiasAux.objects.all()

    # cargar las cesantias en intereses de cesantias auxiliar
    for reg in cesantias_qs:
        PresupuestoInteresesCesantiasAux.objects.create(
            cedula=reg.cedula,
            nombre=reg.nombre,
            centro=reg.centro,
            area=reg.area,
            cargo=reg.cargo,
            concepto="INTERESES CESANTÍAS",
            enero=reg.enero,
            febrero=reg.febrero,
            marzo=reg.marzo,
            abril=reg.abril,
            mayo=reg.mayo,
            junio=reg.junio,
            julio=reg.julio,
            agosto=reg.agosto,
            septiembre=reg.septiembre,
            octubre=reg.octubre,
            noviembre=reg.noviembre,
            diciembre=reg.diciembre,
            total=reg.total,
        )
    
    # for reg in cesantias_qs:
    #     cesantias_base = [getattr(reg, m) or 0 for m in meses]
    #     valores = {}

    #     # Variables de control
    #     suma_cesantias = 0
    #     consecutivo_valores = 0
    #     bloque_activo = False
    #     intereses_acumulados = 0

    #     for i, mes in enumerate(meses):
    #         valor_mes = cesantias_base[i]

    #         if valor_mes == 0:
    #             # Mes sin valor → 0 y termina el bloque
    #             valores[mes] = 0
    #             bloque_activo = False
    #             continue

    #         # Si inicia un nuevo bloque, reiniciar sumatoria, días e intereses
    #         if not bloque_activo:
    #             suma_cesantias = 0
    #             consecutivo_valores = 0
    #             intereses_acumulados = 0  # Reinicia intereses al iniciar bloque
    #             bloque_activo = True

    #         # Acumular dentro del bloque
    #         suma_cesantias += valor_mes
    #         consecutivo_valores += 1

    #         # Días = 30 * posición dentro del bloque
    #         dias = 30 * consecutivo_valores

    #         # Cálculo del interés
    #         interes_teorico = (suma_cesantias * dias * 0.12) / 360
    #         interes_mes = interes_teorico - intereses_acumulados

    #         valores[mes] = interes_mes
    #         intereses_acumulados += interes_mes

    #     # Totalizar y guardar en tabla auxiliar
    #     total = sum(Decimal(valores[m]) for m in meses)
    #     create_kwargs = {m: int(round(float(valores[m]))) for m in meses}

    #     PresupuestoInteresesCesantiasAux.objects.create(
    #         cedula=reg.cedula,
    #         nombre=reg.nombre,
    #         centro=reg.centro,
    #         area=reg.area,
    #         cargo=reg.cargo,
    #         concepto="INTERESES CESANTÍAS",
    #         **create_kwargs,
    #         total=int(round(float(total)))
    #     )

    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_intereses_cesantias(request):
    if request.method == "POST":
        PresupuestoInteresesCesantias.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de intereses de cesantías eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#----------------------------APRENDIZ------------------
def aprendiz(request):
    centros = set(ConceptosFijosYVariables.objects.values_list('nombre_cen', flat=True))
    areas = set(ConceptosFijosYVariables.objects.values_list('nomcosto', flat=True))
    cargos = set(ConceptosFijosYVariables.objects.values_list('nombrecar', flat=True))

    context = {
        'centros': sorted(list(filter(None, centros))),
        'areas': sorted(list(filter(None, areas))),
        'cargos': sorted(list(filter(None, cargos))),
    }
    return render(request, "presupuesto_nomina/aprendiz.html", context)

def obtener_presupuesto_aprendiz(request):
    aprendiz = list(PresupuestoAprendiz.objects.values())
    return JsonResponse({"data": aprendiz}, safe=False)

def tabla_auxiliar_aprendiz(request):
    parametros = ParametrosPresupuestos.objects.first()
    incrementoSalarial = parametros.incremento_salarial if parametros else 0
    centros = set(ConceptosFijosYVariables.objects.values_list('nombre_cen', flat=True))
    areas = set(ConceptosFijosYVariables.objects.values_list('nomcosto', flat=True))
    cargos = set(ConceptosFijosYVariables.objects.values_list('nombrecar', flat=True))

    context = {
        'centros': sorted(list(filter(None, centros))),
        'areas': sorted(list(filter(None, areas))),
        'cargos': sorted(list(filter(None, cargos))),
        'incrementoSalarial': incrementoSalarial,
    }
    return render(request, "presupuesto_nomina/aux_aprendiz.html", context)

def subir_presupuesto_aprendiz(request):
    if request.method == "POST":
        temporales = PresupuestoAprendizAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)
        # obtener cedulas de la tabla principal
        cedulas_existentes = set(
            PresupuestoAprendiz.objects.values_list('cedula', flat=True)
        )
        creados = 0
        omitidos = 0
        for temp in temporales:
            if temp.cedula in cedulas_existentes:
                omitidos += 1
                continue  # omitir si ya existe
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
            creados += 1
        if creados == 0:
            msg = f"No se agregó ningún registro. ({omitidos} ya existían) ⚠️"
        else:
            msg = f"{creados} registro(s) agregado(s) ✅"
        return JsonResponse({
            "success": True,
            "msg": msg
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
            with transaction.atomic():
                PresupuestoAprendizAux.objects.all().delete()
                PresupuestoAprendizAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def guardar_aprendiz(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "salario_base", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

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

                registros.append(PresupuestoAprendiz(**row_filtrado))

            # Inserción masiva optimizada
            with transaction.atomic():
                PresupuestoAprendiz.objects.all().delete()
                PresupuestoAprendiz.objects.bulk_create(registros)

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
    centros = set(ConceptosFijosYVariables.objects.values_list('nombre_cen', flat=True))
    areas = set(ConceptosFijosYVariables.objects.values_list('nomcosto', flat=True))
    cargos = set(ConceptosFijosYVariables.objects.values_list('nombrecar', flat=True))
    context = {
        'centros': sorted(list(filter(None, centros))),
        'areas': sorted(list(filter(None, areas))),
        'cargos': sorted(list(filter(None, cargos))),
    }
    return render(request, "presupuesto_nomina/bonificaciones_foco.html", context)

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
        # obtener cedulas de la tabla principal
        cedulas_existentes = set(
            PresupuestoBonificacionesFoco.objects.values_list('cedula', flat=True)
        )
        creados = 0
        omitidos = 0
        for temp in temporales:
            if temp.cedula in cedulas_existentes:
                omitidos += 1
                continue  # omitir si ya existe
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
            creados += 1
        if creados == 0:
            msg = f"No se agregó ningún registro. ({omitidos} ya existían) ⚠️"
        else:
            msg = f"{creados} registro(s) agregado(s) ✅"
        return JsonResponse({
            "success": True,
            "msg": msg
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
            with transaction.atomic():
                PresupuestoBonificacionesFocoAux.objects.all().delete()
                PresupuestoBonificacionesFocoAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def guardar_bonificaciones_foco(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

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

                registros.append(PresupuestoBonificacionesFoco(**row_filtrado))

            # Inserción masiva optimizada
            with transaction.atomic():
                PresupuestoBonificacionesFoco.objects.all().delete()
                PresupuestoBonificacionesFoco.objects.bulk_create(registros)

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

    parametros = ParametrosPresupuestos.objects.first()
    incrementoIpc = parametros.incremento_ipc if parametros else 0
    incrementoComisiones = parametros.incremento_comisiones if parametros else 0
    
    # agrupamos por persona sumando los meses de enero a junio
    comisiones_agrupadas = (
        PresupuestoComisionesAux.objects
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
        PresupuestoSueldos.objects
        .exclude(cargo__in=cargos_excluidos)
        .values("cedula", "nombre", "centro", "area", "cargo")
        .annotate(total=Sum("total"))
    )
    
    # 2️⃣ Insertar en la tabla de bonificaciones con enero = 220000 + IPC
    for emp in empleados_fijos:
        enero_valor = 220000 * (1 + incrementoIpc / 100)
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
    centros = set(ConceptosFijosYVariables.objects.values_list('nombre_cen', flat=True))
    areas = set(ConceptosFijosYVariables.objects.values_list('nomcosto', flat=True))
    cargos = set(ConceptosFijosYVariables.objects.values_list('nombrecar', flat=True))
    context = {
        'centros': sorted(list(filter(None, centros))),
        'areas': sorted(list(filter(None, areas))),
        'cargos': sorted(list(filter(None, cargos))),
    }
    return render(request, "presupuesto_nomina/auxilio_educacion.html", context)

def obtener_presupuesto_auxilio_educacion(request):
    auxilio_educacion = list(PresupuestoAuxilioEducacion.objects.values())
    return JsonResponse({"data": auxilio_educacion}, safe=False)

def tabla_auxiliar_auxilio_educacion(request):
    parametros = ParametrosPresupuestos.objects.first()
    incremento_ipc = parametros.incremento_ipc if parametros else 0
    return render(request, "presupuesto_nomina/aux_auxilio_educacion.html", {'incrementoIPC': incremento_ipc})

def subir_presupuesto_auxilio_educacion(request):
    if request.method == "POST":
        temporales = PresupuestoAuxilioEducacionAux.objects.all()
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)
        # obtener cedulas de la tabla principal
        cedulas_existentes = set(
            PresupuestoAuxilioEducacion.objects.values_list('cedula', flat=True)
        )
        creados = 0
        omitidos = 0
        for temp in temporales:
            if temp.cedula in cedulas_existentes:
                omitidos += 1
                continue  # omitir si ya existe
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
            creados += 1
        if creados == 0:
            msg = f"No se agregó ningún registro. ({omitidos} ya existían) ⚠️"
        else:
            msg = f"{creados} registro(s) agregado(s) ✅"
        return JsonResponse({
            "success": True,
            "msg": msg
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
            with transaction.atomic():
                PresupuestoAuxilioEducacionAux.objects.all().delete()
                PresupuestoAuxilioEducacionAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def guardar_auxilio_educacion(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

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

                registros.append(PresupuestoAuxilioEducacion(**row_filtrado))

            # Inserción masiva optimizada
            with transaction.atomic():
                PresupuestoAuxilioEducacion.objects.all().delete()
                PresupuestoAuxilioEducacion.objects.bulk_create(registros)

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
    
    for row in base_data:
        PresupuestoAuxilioEducacionAux.objects.create(
            cedula=row["cedula"],
            nombre=row["nombre"],
            cargo=row["nombrecar"],
            area=row["nomcosto"],
            centro=row["nombre_cen"],
            concepto=row["nombre_con"],
            diciembre=row["diciembre"],
            total=row["total"],
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
    centros = set(ConceptosFijosYVariables.objects.values_list('nombre_cen', flat=True))
    areas = set(ConceptosFijosYVariables.objects.values_list('nomcosto', flat=True))
    cargos = set(ConceptosFijosYVariables.objects.values_list('nombrecar', flat=True))
    context = {
        'centros': sorted(list(filter(None, centros))),
        'areas': sorted(list(filter(None, areas))),
        'cargos': sorted(list(filter(None, cargos))),
    }
    return render(request, "presupuesto_nomina/bonos_kyrovet.html", context)

def obtener_presupuesto_bonos_kyrovet(request):
    bonos_kyrovet = list(PresupuestoBonosKyrovet.objects.values())
    return JsonResponse({"data": bonos_kyrovet}, safe=False)

def tabla_auxiliar_bonos_kyrovet(request):
    parametros = ParametrosPresupuestos.objects.first()
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
        # obtener cedulas de la tabla principal
        cedulas_existentes = set(
            PresupuestoBonosKyrovet.objects.values_list('cedula', flat=True)
        )
        creados = 0
        omitidos = 0
        for temp in temporales:
            if temp.cedula in cedulas_existentes:
                omitidos += 1
                continue  # omitir si ya existe
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
            creados += 1
        if creados == 0:
            msg = f"No se agregó ningún registro. ({omitidos} ya existían) ⚠️"
        else:
            msg = f"{creados} registro(s) agregado(s) ✅"
        return JsonResponse({
            "success": True,
            "msg": msg
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
            with transaction.atomic():
                PresupuestoBonosKyrovetAux.objects.all().delete()
                PresupuestoBonosKyrovetAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def guardar_bonos_kyrovet(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "cedula", "nombre", "centro", "area", "cargo", "concepto","base", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            }

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

                registros.append(PresupuestoBonosKyrovet(**row_filtrado))

            # Inserción masiva optimizada
            with transaction.atomic():
                PresupuestoBonosKyrovet.objects.all().delete()
                PresupuestoBonosKyrovet.objects.bulk_create(registros)

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
    base_data = base_data.filter(nombre_con__icontains="BONOS CANASTA KYROVET")
    parametros = ParametrosPresupuestos.objects.first()
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


# -----------------------------PRESUPUESTO GENERAL----------------------------------------------------------------------
#SELECCIÓN DE CUENTAS CONTABLES-----------------
def seleccion_cuentas_contables(request):
    cuentas = list(CuentasContables.objects.values_list('cuenta', flat=True))
    nom_cuentas = list(CuentasContables.objects.values_list('nom_cuenta', flat=True))
 
    # Creamos el diccionario 
    cuentas_dict = dict(zip(cuentas, nom_cuentas))
    return JsonResponse({"cuentas": cuentas, "nom_cuentas": nom_cuentas, "cuentas_dict": cuentas_dict}, safe=False)

# -PRESUPUESTO TECNOLOGIA--------------------------------
@login_required
def presupuesto_tecnologia(request):
    usuarios_permitidos = ['admin', 'TECNOLOGIA']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permiso para acceder a esta página.")
    # 🔹 obtener versiones disponibles
    versiones = (
        PresupuestoTecnologia.objects
        .values_list("version", flat=True)
        .distinct()
        .order_by("version")
    )
    ultima_version = max(versiones) if versiones else 1
    return render(request, "presupuesto_general/presupuesto_tecnologia.html", {"versiones": versiones, "ultima_version": ultima_version})

def obtener_presupuesto_tecnologia(request):
    version = request.GET.get("version")  # 🔥 versión recibida
    qs = PresupuestoTecnologia.objects.all()
    if version:
        qs = qs.filter(version=version)

    data = list(qs.values())
    return JsonResponse({"data": data}, safe=False)

def presupuesto_aprobado_tecnologia(request):
    # obtener la última versión aprobada
    versiones = (
        PresupuestotecnologiaAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    return render(request, "presupuesto_general/presupuesto_aprobado_tecnologia.html", {"ultima_version": ultima_version})

def obtener_presupuesto_aprobado_tecnologia(request):
    # siempre filtrar por la última versión
    versiones = (
        PresupuestotecnologiaAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    qs = PresupuestotecnologiaAprobado.objects.filter(version=ultima_version)
    tecnologia_aprobado = list(qs.values())
    return JsonResponse({"data": tecnologia_aprobado}, safe=False)

def tabla_auxiliar_tecnologia(request):
    # 📌 Definir fecha límite
    fecha_limite = datetime.date(2025, 10, 15)  # <-- cámbiala según lo que necesites
    hoy = datetime.date.today()

    # 🚫 Si ya pasó la fecha, negar acceso
    if hoy > fecha_limite:
        return HttpResponseForbidden("⛔ El acceso a esta vista está bloqueado desde el "
                                     f"{fecha_limite.strftime('%d/%m/%Y')}")

    # ✅ Si aún no llega la fecha, mostrar vista normal
    return render(request, "presupuesto_general/aux_presupuesto_tecnologia.html")

def subir_presupuesto_tecnologia(request):
    if request.method == "POST":
        temporales = PresupuestoTecnologiaAux.objects.all()
        fecha_limite = datetime.date(2025, 10, 30)

        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        # 📌 Fecha actual
        fecha_hoy = timezone.now().date()

        # 📌 Obtener versión global (tomando la última registrada en la tabla principal)
        ultima_version = PresupuestoTecnologia.objects.aggregate(max_ver=models.Max("version"))["max_ver"] or 0
        nueva_version = ultima_version + 1

        for temp in temporales:
            # --- Guardar en tabla principal ---
            obj, created = PresupuestoTecnologia.objects.update_or_create(
                id=temp.id,  
                defaults={
                    "centro_tra": temp.centro_tra,
                    "nombre_cen": temp.nombre_cen,
                    "codcosto": temp.codcosto,
                    "responsable": temp.responsable,
                    "cuenta": temp.cuenta,
                    "cuenta_mayor": temp.cuenta_mayor,
                    "detalle_cuenta": temp.detalle_cuenta,
                    "sede_distribucion": temp.sede_distribucion,
                    "proveedor": temp.proveedor,
                    "enero": temp.enero,
                    "febrero": temp.febrero,
                    "marzo": temp.marzo,
                    "abril": temp.abril,
                    "mayo": temp.mayo,
                    "junio": temp.junio,
                    "julio": temp.julio,
                    "agosto": temp.agosto,
                    "septiembre": temp.septiembre,
                    "octubre": temp.octubre,
                    "noviembre": temp.noviembre,
                    "diciembre": temp.diciembre,
                    "total": temp.total,
                    "comentario": temp.comentario,
                    "version": nueva_version,
                    "fecha": fecha_hoy,
                }
            )

            # --- Guardar en tabla aprobada si aplica ---
            if fecha_hoy <= fecha_limite:
                PresupuestotecnologiaAprobado.objects.update_or_create(
                    id=temp.id,
                    defaults={
                        "centro_tra": temp.centro_tra,
                        "nombre_cen": temp.nombre_cen,
                        "codcosto": temp.codcosto,
                        "responsable": temp.responsable,
                        "cuenta": temp.cuenta,
                        "cuenta_mayor": temp.cuenta_mayor,
                        "detalle_cuenta": temp.detalle_cuenta,
                        "sede_distribucion": temp.sede_distribucion,
                        "proveedor": temp.proveedor,
                        "enero": temp.enero,
                        "febrero": temp.febrero,
                        "marzo": temp.marzo,
                        "abril": temp.abril,
                        "mayo": temp.mayo,
                        "junio": temp.junio,
                        "julio": temp.julio,
                        "agosto": temp.agosto,
                        "septiembre": temp.septiembre,
                        "octubre": temp.octubre,
                        "noviembre": temp.noviembre,
                        "diciembre": temp.diciembre,
                        "total": temp.total,
                        "comentario": temp.comentario,
                        "version": nueva_version,
                        "fecha": fecha_hoy,
                    }
                )

        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de tecnología actualizado ✅ (versión {nueva_version})"
        })

    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_tecnologia_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total", "comentario"
            }

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

                registros.append(PresupuestoTecnologiaAux(**row_filtrado))

            # Inserción masiva optimizada
            with transaction.atomic():
                # Limpiar la tabla antes de guardar
                PresupuestoTecnologiaAux.objects.all().delete()
                PresupuestoTecnologiaAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_tecnologia_temp(request):
    data = list(PresupuestoTecnologiaAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_tecnologia_base(request):
    # limpio tabla auxiliar de tecnología antes de recalcular
    PresupuestoTecnologiaAux.objects.all().delete()
    base_data = Plantillagastos2025.objects.values(
       "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    )
    # filtrar por responsable = 'DIEGO CANO'
    base_data = base_data.filter(responsable__iexact="DIEGO CANO")
    
    for row in base_data:
        PresupuestoTecnologiaAux.objects.create(
            centro_tra=row["centro_tra"],
            nombre_cen=row["nombre_cen"],
            codcosto=row["codcosto"],
            responsable=row["responsable"],
            cuenta=row["cuenta"],
            cuenta_mayor=row["cuenta_mayor"],
            detalle_cuenta=row["detalle_cuenta"],
            sede_distribucion=row["sede_distribucion"],
            proveedor=row["proveedor"],
            enero=row["enero"],
            febrero=row["febrero"],
            marzo=row["marzo"],
            abril=row["abril"],
            mayo=row["mayo"],
            junio=row["junio"],
            julio=row["julio"], 
            agosto=row["agosto"],
            septiembre=row["septiembre"],
            octubre=row["octubre"],
            noviembre=row["noviembre"],
            diciembre=row["diciembre"],
            total=row["enero"] + row["febrero"] + row["marzo"] + row["abril"] + row["mayo"] + row["junio"] + row["julio"] + row["agosto"] + row["septiembre"] + row["octubre"] + row["noviembre"] + row["diciembre"],
            comentario = ""
        )
    
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_tecnologia(request):
    if request.method == "POST":
        PresupuestoTecnologia.objects.all().delete()
        # 📌 Fecha límite (cámbiala según lo que necesites)
        fecha_limite = datetime.date(2025, 10, 30) 
        # borrar también la tabla aprobada si la fecha limite no ha pasado
        if timezone.now().date() <= fecha_limite:
            PresupuestotecnologiaAprobado.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de tecnología eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#--PRESUPUESTO OCUPACIONAL-----------------------------
@login_required
def presupuesto_ocupacional(request):
    usuarios_permitidos = ['admin', 'SALUDOCUPACIONAL']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    # 🔹 obtener versiones disponibles
    versiones = (
        PresupuestoOcupacional.objects
        .values_list("version", flat=True)
        .distinct()
        .order_by("version")
    )
    ultima_version = max(versiones) if versiones else 1
    return render(request, "presupuesto_general/presupuesto_ocupacional.html", {"versiones": versiones, "ultima_version": ultima_version})

def obtener_presupuesto_ocupacional(request):
    version = request.GET.get("version")  # 🔥 versión recibida
    qs = PresupuestoOcupacional.objects.all()
    if version:
        qs = qs.filter(version=version)

    data = list(qs.values())
    return JsonResponse({"data": data}, safe=False)

def presupuesto_aprobado_ocupacional(request):
    # 🔹 obtener última versión disponible
    versiones = (
        PresupuestoOcupacionalAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    return render(request, "presupuesto_general/presupuesto_aprobado_ocupacional.html", {"ultima_version": ultima_version})

def obtener_presupuesto_aprobado_ocupacional(request):
    # 🔥 siempre filtrar por la última versión
    versiones = (
        PresupuestoOcupacionalAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    qs = PresupuestoOcupacionalAprobado.objects.filter(version=ultima_version)

    data = list(qs.values())
    return JsonResponse({"data": data}, safe=False)

def tabla_auxiliar_ocupacional(request):
    # 📌 Definir fecha límite
    fecha_limite = datetime.date(2025, 10, 16)  # <-- cámbiala según lo que necesites
    hoy = datetime.date.today()

    # 🚫 Si ya pasó la fecha, negar acceso
    if hoy > fecha_limite:
        return HttpResponseForbidden("⛔ El acceso a esta vista está bloqueado después del "
                                     f"{fecha_limite.strftime('%d/%m/%Y')}")

    # ✅ Si aún no llega la fecha, mostrar vista normal
    return render(request, "presupuesto_general/aux_presupuesto_ocupacional.html")

def subir_presupuesto_ocupacional(request):
    if request.method == "POST":
        temporales = PresupuestoOcupacionalAux.objects.all()
        fecha_limite = datetime.date(2025, 10, 30)

        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        # 📌 Fecha actual
        fecha_hoy = timezone.now().date()

        # 📌 Obtener versión global (tomando la última registrada en la tabla principal)
        ultima_version = PresupuestoOcupacional.objects.aggregate(max_ver=models.Max("version"))["max_ver"] or 0
        nueva_version = ultima_version + 1

        for temp in temporales:
            # --- Guardar en tabla principal ---
            obj, created = PresupuestoOcupacional.objects.update_or_create(
                id=temp.id,  
                defaults={
                    "centro_tra": temp.centro_tra,
                    "nombre_cen": temp.nombre_cen,
                    "codcosto": temp.codcosto,
                    "responsable": temp.responsable,
                    "cuenta": temp.cuenta,
                    "cuenta_mayor": temp.cuenta_mayor,
                    "detalle_cuenta": temp.detalle_cuenta,
                    "sede_distribucion": temp.sede_distribucion,
                    "proveedor": temp.proveedor,
                    "enero": temp.enero,
                    "febrero": temp.febrero,
                    "marzo": temp.marzo,
                    "abril": temp.abril,
                    "mayo": temp.mayo,
                    "junio": temp.junio,
                    "julio": temp.julio,
                    "agosto": temp.agosto,
                    "septiembre": temp.septiembre,
                    "octubre": temp.octubre,
                    "noviembre": temp.noviembre,
                    "diciembre": temp.diciembre,
                    "total": temp.total,
                    "comentario": temp.comentario,
                    "version": nueva_version,
                    "fecha": fecha_hoy,
                }
            )

            # --- Guardar en tabla aprobada si aplica ---
            if fecha_hoy <= fecha_limite:
                PresupuestoOcupacionalAprobado.objects.update_or_create(
                    id=temp.id,
                    defaults={
                        "centro_tra": temp.centro_tra,
                        "nombre_cen": temp.nombre_cen,
                        "codcosto": temp.codcosto,
                        "responsable": temp.responsable,
                        "cuenta": temp.cuenta,
                        "cuenta_mayor": temp.cuenta_mayor,
                        "detalle_cuenta": temp.detalle_cuenta,
                        "sede_distribucion": temp.sede_distribucion,
                        "proveedor": temp.proveedor,
                        "enero": temp.enero,
                        "febrero": temp.febrero,
                        "marzo": temp.marzo,
                        "abril": temp.abril,
                        "mayo": temp.mayo,  
                        "junio": temp.junio,
                        "julio": temp.julio,
                        "agosto": temp.agosto,
                        "septiembre": temp.septiembre,
                        "octubre": temp.octubre,
                        "noviembre": temp.noviembre,
                        "diciembre": temp.diciembre,
                        "total": temp.total,
                        "comentario": temp.comentario,
                        "version": nueva_version,
                        "fecha": fecha_hoy,
                    }
                )
        return JsonResponse({
            "success": True,    
            "msg": f"Presupuesto ocupacional actualizado ✅ (versión {nueva_version})"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_ocupacional_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total", "comentario"
            }

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

                registros.append(PresupuestoOcupacionalAux(**row_filtrado))

            # ✅ Transacción atómica → si algo falla, no se borra nada
            with transaction.atomic():
                PresupuestoOcupacionalAux.objects.all().delete()
                PresupuestoOcupacionalAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_ocupacional_temp(request):
    data = list(PresupuestoOcupacionalAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_ocupacional_base(request):
    # limpio tabla auxiliar de ocupacional antes de recalcular
    PresupuestoOcupacionalAux.objects.all().delete()
    base_data = Plantillagastos2025.objects.values(
       "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    )
    # filtrar por responsable = 'LUIS FERNANDO VARGAS'
    base_data = base_data.filter(responsable__iexact="WILLIAM")
    
    for row in base_data:
        PresupuestoOcupacionalAux.objects.create(
            centro_tra=row["centro_tra"],
            nombre_cen=row["nombre_cen"],
            codcosto=row["codcosto"],
            responsable=row["responsable"],
            cuenta=row["cuenta"],
            cuenta_mayor=row["cuenta_mayor"],
            detalle_cuenta=row["detalle_cuenta"],
            sede_distribucion=row["sede_distribucion"],
            proveedor=row["proveedor"],
            enero=row["enero"],
            febrero=row["febrero"],
            marzo=row["marzo"],
            abril=row["abril"],
            mayo=row["mayo"],
            junio=row["junio"],
            julio=row["julio"], 
            agosto=row["agosto"],
            septiembre=row["septiembre"],
            octubre=row["octubre"],
            noviembre=row["noviembre"],
            diciembre=row["diciembre"],
            total=row["enero"] + row["febrero"] + row["marzo"] + row["abril"] + row["mayo"] + row["junio"] + row["julio"] + row["agosto"] + row["septiembre"] + row["octubre"] + row["noviembre"] + row["diciembre"],
            comentario = ""
        )
    
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_ocupacional(request):
    if request.method == "POST":
        PresupuestoOcupacional.objects.all().delete()
        # 📌 Fecha límite (cámbiala según lo que necesites)
        fecha_limite = datetime.date(2025, 10, 30) 
        # borrar también la tabla aprobada si la fecha limite no ha pasado
        if timezone.now().date() <= fecha_limite:
            PresupuestoOcupacionalAprobado.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto ocupacional eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#----PRESUPUESTO SERVICIOS TECNICOS-----------------------------
@login_required
def presupuesto_servicios_tecnicos(request):
    usuarios_permitidos = ['admin', 'SERVICIOSTECNICOS']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    # 🔹 obtener versiones disponibles
    versiones = (
        PresupuestoServiciosTecnicos.objects
        .values_list("version", flat=True)
        .distinct()
        .order_by("version")
    )
    ultima_version = max(versiones) if versiones else 1
    return render(request, "presupuesto_general/presupuesto_servicios_tecnicos.html", {"versiones": versiones, "ultima_version": ultima_version})

def obtener_presupuesto_servicios_tecnicos(request):
    version = request.GET.get("version")  # 🔥 versión recibida
    qs = PresupuestoServiciosTecnicos.objects.all()
    if version:
        qs = qs.filter(version=version)

    data = list(qs.values())
    return JsonResponse({"data": data}, safe=False)

def presupuesto_aprobado_servicios_tecnicos(request):
    # 🔹 obtener última versión disponible
    versiones = (
        PresupuestoServiciosTecnicosAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    return render(request, "presupuesto_general/presupuesto_aprobado_servicios_tecnicos.html", {"ultima_version": ultima_version})

def obtener_presupuesto_aprobado_servicios_tecnicos(request):
    # 🔥 siempre filtrar por la última versión
    versiones = (
        PresupuestoServiciosTecnicosAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    qs = PresupuestoServiciosTecnicosAprobado.objects.filter(version=ultima_version)
    data = list(qs.values())
    return JsonResponse({"data": data}, safe=False)

def tabla_auxiliar_servicios_tecnicos(request):
    # 📌 Definir fecha límite
    fecha_limite = datetime.date(2025, 10, 15)  # <-- cámbiala según lo que necesites
    hoy = datetime.date.today()

    # 🚫 Si ya pasó la fecha, negar acceso
    if hoy > fecha_limite:
        return HttpResponseForbidden("⛔ El acceso a esta vista está bloqueado después del "
                                     f"{fecha_limite.strftime('%d/%m/%Y')}")

    # ✅ Si aún no llega la fecha, mostrar vista normal
    return render(request, "presupuesto_general/aux_presupuesto_servicios_tecnicos.html")

def subir_presupuesto_servicios_tecnicos(request):
    if request.method == "POST":
        temporales = PresupuestoServiciosTecnicosAux.objects.all()
        fecha_limite = datetime.date(2025, 10, 30)

        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)

        # 📌 Fecha actual
        fecha_hoy = timezone.now().date()

        # 📌 Obtener versión global (tomando la última registrada en la tabla principal)
        ultima_version = PresupuestoServiciosTecnicos.objects.aggregate(max_ver=models.Max("version"))["max_ver"] or 0
        nueva_version = ultima_version + 1

        for temp in temporales:
            # --- Guardar en tabla principal ---
            obj, created = PresupuestoServiciosTecnicos.objects.update_or_create(
                id=temp.id,  
                defaults={
                    "centro_tra": temp.centro_tra,
                    "nombre_cen": temp.nombre_cen,
                    "codcosto": temp.codcosto,
                    "responsable": temp.responsable,
                    "cuenta": temp.cuenta,
                    "cuenta_mayor": temp.cuenta_mayor,
                    "detalle_cuenta": temp.detalle_cuenta,
                    "sede_distribucion": temp.sede_distribucion,
                    "proveedor": temp.proveedor,
                    "enero": temp.enero,
                    "febrero": temp.febrero,
                    "marzo": temp.marzo,
                    "abril": temp.abril,
                    "mayo": temp.mayo,
                    "junio": temp.junio,
                    "julio": temp.julio,
                    "agosto": temp.agosto,
                    "septiembre": temp.septiembre,
                    "octubre": temp.octubre,
                    "noviembre": temp.noviembre,
                    "diciembre": temp.diciembre,
                    "total": temp.total,
                    "comentario": temp.comentario,
                    "version": nueva_version,
                    "fecha": fecha_hoy,
                }
            )

            # --- Guardar en tabla aprobada si aplica ---
            if fecha_hoy <= fecha_limite:
                PresupuestoServiciosTecnicosAprobado.objects.update_or_create(
                    id=temp.id,
                    defaults={
                        "centro_tra": temp.centro_tra,
                        "nombre_cen": temp.nombre_cen,
                        "codcosto": temp.codcosto,
                        "responsable": temp.responsable,
                        "cuenta": temp.cuenta,
                        "cuenta_mayor": temp.cuenta_mayor,
                        "detalle_cuenta": temp.detalle_cuenta,
                        "sede_distribucion": temp.sede_distribucion,
                        "proveedor": temp.proveedor,
                        "enero": temp.enero,
                        "febrero": temp.febrero,
                        "marzo": temp.marzo,
                        "abril": temp.abril,
                        "mayo": temp.mayo,
                        "junio": temp.junio,
                        "julio": temp.julio,
                        "agosto": temp.agosto,
                        "septiembre": temp.septiembre,
                        "octubre": temp.octubre,
                        "noviembre": temp.noviembre,
                        "diciembre": temp.diciembre,
                        "total": temp.total,
                        "comentario": temp.comentario,
                        "version": nueva_version,
                        "fecha": fecha_hoy,
                    }
                )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto servicios técnicos actualizado ✅ (versión {nueva_version})"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_servicios_tecnicos_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total", "comentario"
            }

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

                registros.append(PresupuestoServiciosTecnicosAux(**row_filtrado))

            with transaction.atomic():
                PresupuestoServiciosTecnicosAux.objects.all().delete()
                PresupuestoServiciosTecnicosAux.objects.bulk_create(registros)

            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_servicios_tecnicos_temp(request):
    data = list(PresupuestoServiciosTecnicosAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_servicios_tecnicos_base(request):
    # limpio tabla auxiliar de servicios técnicos antes de recalcular
    PresupuestoServiciosTecnicosAux.objects.all().delete()
    base_data = Plantillagastos2025.objects.values(
       "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    )
    # filtrar por responsable = 'LUIS FERNANDO VARGAS'
    base_data = base_data.filter(responsable__iexact="JORGE GUERRERO")
    
    for row in base_data:
        PresupuestoServiciosTecnicosAux.objects.create(
            centro_tra=row["centro_tra"],
            nombre_cen=row["nombre_cen"],
            codcosto=row["codcosto"],
            responsable=row["responsable"],
            cuenta=row["cuenta"],
            cuenta_mayor=row["cuenta_mayor"],
            detalle_cuenta=row["detalle_cuenta"],
            sede_distribucion=row["sede_distribucion"],
            proveedor=row["proveedor"],
            enero=row["enero"],
            febrero=row["febrero"],
            marzo=row["marzo"],
            abril=row["abril"],
            mayo=row["mayo"],
            junio=row["junio"],
            julio=row["julio"], 
            agosto=row["agosto"],
            septiembre=row["septiembre"],
            octubre=row["octubre"],
            noviembre=row["noviembre"],
            diciembre=row["diciembre"],
            total=row["enero"] + row["febrero"] + row["marzo"] + row["abril"] + row["mayo"] + row["junio"] + row["julio"] + row["agosto"] + row["septiembre"] + row["octubre"] + row["noviembre"] + row["diciembre"],
            comentario = ""
        )
    
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_servicios_tecnicos(request):
    if request.method == "POST":
        version = request.POST.get("version")  # 🔥 versión enviada desde el frontend

        if not version:
            return JsonResponse({"status": "error", "message": "No se especificó la versión"}, status=400)

        # borrar solo la versión seleccionada
        PresupuestoServiciosTecnicos.objects.filter(version=version).delete()

        # 📌 Fecha límite
        fecha_limite = datetime.date(2025, 10, 30)
        if timezone.now().date() <= fecha_limite:
            PresupuestoServiciosTecnicosAprobado.objects.filter(version=version).delete()

        return JsonResponse({"status": "ok", "message": f"Presupuesto versión {version} eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)


#-----PRESUPUESTO LOGISTICA-----------------------------
@login_required
def presupuesto_logistica(request):
    usuarios_permitidos = ['admin', 'PLOZANO']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    # 🔹 obtener versiones disponibles
    versiones = (
        PresupuestoLogistica.objects
        .values_list("version", flat=True)
        .distinct()
        .order_by("version")
    )
    ultima_version = max(versiones) if versiones else 1
    return render(request, "presupuesto_general/presupuesto_logistica.html", {"versiones": versiones, "ultima_version": ultima_version})

def obtener_presupuesto_logistica(request):
    version = request.GET.get("version")  # 🔥 versión recibida
    qs = PresupuestoLogistica.objects.all()
    if version:
        qs = qs.filter(version=version)

    data = list(qs.values())
    return JsonResponse({"data": data}, safe=False)

def presupuesto_aprobado_logistica(request):
    # 🔹 obtener última versión disponible
    versiones = (
        PresupuestoLogisticaAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    return render(request, "presupuesto_general/presupuesto_aprobado_logistica.html", {"ultima_version": ultima_version})

def obtener_presupuesto_aprobado_logistica(request):
    # 🔥 siempre filtrar por la última versión
    versiones = (
        PresupuestoLogisticaAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    qs = PresupuestoLogisticaAprobado.objects.filter(version=ultima_version)
    logistica_aprobado = list(qs.values())
    return JsonResponse({"data": logistica_aprobado}, safe=False)

def tabla_auxiliar_logistica(request):
    # 📌 Definir fecha límite
    fecha_limite = datetime.date(2025, 10, 17)  # <-- cámbiala según lo que necesites
    hoy = datetime.date.today()
    # 🚫 Si ya pasó la fecha, negar acceso
    if hoy > fecha_limite:
        return HttpResponseForbidden("⛔ El acceso a esta vista está bloqueado después del "
                                        f"{fecha_limite.strftime('%d/%m/%Y')}")
    # ✅ Si aún no llega la fecha, mostrar vista normal
    return render(request, "presupuesto_general/aux_presupuesto_logistica.html")

def subir_presupuesto_logistica(request):
    if request.method == "POST":
        temporales = PresupuestoLogisticaAux.objects.all()
        fecha_limite = datetime.date(2025, 10, 30)
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)
        # 📌 Fecha actual
        fecha_hoy = timezone.now().date()
        # 📌 Obtener versión global (tomando la última registrada en la tabla 
        ultima_version = PresupuestoLogistica.objects.aggregate(max_ver=models.Max("version"))["max_ver"] or 0
        nueva_version = ultima_version + 1
        for temp in temporales:
            # --- Guardar en tabla principal ---
            obj, created = PresupuestoLogistica.objects.update_or_create(
                id=temp.id,
                defaults={
                    "centro_tra": temp.centro_tra,
                    "nombre_cen": temp.nombre_cen,
                    "codcosto": temp.codcosto,
                    "responsable": temp.responsable,
                    "cuenta": temp.cuenta,  
                    "cuenta_mayor": temp.cuenta_mayor,
                    "detalle_cuenta": temp.detalle_cuenta,
                    "sede_distribucion": temp.sede_distribucion,
                    "proveedor": temp.proveedor,
                    "enero": temp.enero,
                    "febrero": temp.febrero,
                    "marzo": temp.marzo,
                    "abril": temp.abril,
                    "mayo": temp.mayo,
                    "junio": temp.junio,
                    "julio": temp.julio,
                    "agosto": temp.agosto,
                    "septiembre": temp.septiembre,
                    "octubre": temp.octubre,
                    "noviembre": temp.noviembre,
                    "diciembre": temp.diciembre,
                    "total": temp.total,
                    "comentario": temp.comentario,
                    "version": nueva_version,
                    "fecha": fecha_hoy,
                }
            )
            # --- Guardar en tabla aprobada si aplica ---
            if fecha_hoy <= fecha_limite:
                PresupuestoLogisticaAprobado.objects.update_or_create(
                    id=temp.id,
                    defaults={
                        "centro_tra": temp.centro_tra,
                        "nombre_cen": temp.nombre_cen,
                        "codcosto": temp.codcosto,
                        "responsable": temp.responsable,
                        "cuenta": temp.cuenta,  
                        "cuenta_mayor": temp.cuenta_mayor,
                        "detalle_cuenta": temp.detalle_cuenta,
                        "sede_distribucion": temp.sede_distribucion,
                        "proveedor": temp.proveedor,
                        "enero": temp.enero,
                        "febrero": temp.febrero,
                        "marzo": temp.marzo,
                        "abril": temp.abril,
                        "mayo": temp.mayo,
                        "junio": temp.junio,
                        "julio": temp.julio,
                        "agosto": temp.agosto,
                        "septiembre": temp.septiembre,
                        "octubre": temp.octubre,
                        "noviembre": temp.noviembre,
                        "diciembre": temp.diciembre,
                        "total": temp.total,
                        "comentario": temp.comentario,
                        "version": nueva_version,
                        "fecha": fecha_hoy,
                    }
                )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de logística actualizado ✅ (versión {nueva_version})"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_logistica_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total", "comentario"
            }
            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}
                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo","junio", "julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0
                registros.append(PresupuestoLogisticaAux(**row_filtrado))
            # ✅ Transacción atómica → si algo falla, no se borra nada
            with transaction.atomic():
                # limpio toda la tabla auxiliar antes de insertar
                PresupuestoLogisticaAux.objects.all().delete()
                PresupuestoLogisticaAux.objects.bulk_create(registros)
            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_logistica_temp(request):
    data = list(PresupuestoLogisticaAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_logistica_base(request):
    # limpio tabla auxiliar de logística antes de recalcular
    PresupuestoLogisticaAux.objects.all().delete()
    base_data = Plantillagastos2025.objects.values(
       "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    )
    # filtrar por responsable = 'LUIS FERNANDO VARGAS'
    base_data = base_data.filter(responsable__iexact="PILAR LOZANO")
    
    for row in base_data:
        PresupuestoLogisticaAux.objects.create(
            centro_tra=row["centro_tra"],
            nombre_cen=row["nombre_cen"],
            codcosto=row["codcosto"],
            responsable=row["responsable"],
            cuenta=row["cuenta"],
            cuenta_mayor=row["cuenta_mayor"],
            detalle_cuenta=row["detalle_cuenta"],
            sede_distribucion=row["sede_distribucion"],
            proveedor=row["proveedor"],
            enero=row["enero"],
            febrero=row["febrero"],
            marzo=row["marzo"],
            abril=row["abril"],
            mayo=row["mayo"],
            junio=row["junio"],
            julio=row["julio"], 
            agosto=row["agosto"],
            septiembre=row["septiembre"],
            octubre=row["octubre"],
            noviembre=row["noviembre"],
            diciembre=row["diciembre"],
            total=row["enero"] + row["febrero"] + row["marzo"] + row["abril"] + row["mayo"] + row["junio"] + row["julio"] + row["agosto"] + row["septiembre"] + row["octubre"] + row["noviembre"] + row["diciembre"],
            comentario = ""
        )
    
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_logistica(request):
    if request.method == "POST":
        version = request.POST.get("version")  # 🔥 versión enviada desde el frontend

        if not version:
            return JsonResponse({"status": "error", "message": "No se especificó la versión"}, status=400)

        # borrar solo la versión seleccionada
        PresupuestoLogistica.objects.filter(version=version).delete()

        # 📌 Fecha límite
        fecha_limite = datetime.date(2025, 10, 30)
        if timezone.now().date() <= fecha_limite:
            PresupuestoLogisticaAprobado.objects.filter(version=version).delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de logística eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)


#---------PRESUPUESTO GESTION DE RIESGOS-----------------------------
@login_required
def presupuesto_gestion_riesgos(request):
    usuarios_permitidos = ['admin', 'GESTIONRIESGOS']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    # 🔹 obtener versiones disponibles
    versiones = (
        PresupuestoGestionRiesgos.objects
        .values_list("version", flat=True)
        .distinct()
        .order_by("version")
    )
    ultima_version = max(versiones) if versiones else 1
    return render(request, "presupuesto_general/presupuesto_gestion_riesgos.html", {"versiones": versiones, "ultima_version": ultima_version})

def obtener_presupuesto_gestion_riesgos(request):
    version = request.GET.get("version")  # 🔥 versión recibida
    qs = PresupuestoGestionRiesgos.objects.all()
    if version:
        qs = qs.filter(version=version)

    data = list(qs.values())
    return JsonResponse({"data": data}, safe=False)

def presupuesto_aprobado_gestion_riesgos(request):
    # 🔹 obtener última versión disponible
    versiones = (
        PresupuestoGestionRiesgosAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    return render(request, "presupuesto_general/presupuesto_aprobado_gestion_riesgos.html", {"ultima_version": ultima_version})

def obtener_presupuesto_aprobado_gestion_riesgos(request):
    # 🔥 siempre filtrar por la última versión
    versiones = (
        PresupuestoGestionRiesgosAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    qs = PresupuestoGestionRiesgosAprobado.objects.filter(version=ultima_version)
    gestion_riesgos_aprobado = list(qs.values())
    return JsonResponse({"data": gestion_riesgos_aprobado}, safe=False)

def tabla_auxiliar_gestion_riesgos(request):
    # 📌 Definir fecha límite
    fecha_limite = datetime.date(2025, 10, 16)  # <-- cámbiala según lo que necesites
    hoy = datetime.date.today()
    # 🚫 Si ya pasó la fecha, negar acceso
    if hoy > fecha_limite:
        return HttpResponseForbidden("⛔ El acceso a esta vista está bloqueado después del "
                                        f"{fecha_limite.strftime('%d/%m/%Y')}")
    # ✅ Si aún no llega la fecha, mostrar vista normal
    return render(request, "presupuesto_general/aux_presupuesto_gestion_riesgos.html")

def subir_presupuesto_gestion_riesgos(request):
    if request.method == "POST":
        temporales = PresupuestoGestionRiesgosAux.objects.all()
        fecha_limite = datetime.date(2025, 10, 30)
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)
        # 📌 Fecha actual
        fecha_hoy = timezone.now().date()
        # 📌 Obtener versión global (tomando la última registrada en la tabla 
        ultima_version = PresupuestoGestionRiesgos.objects.aggregate(max_ver=models.Max("version"))["max_ver"] or 0
        nueva_version = ultima_version + 1
        for temp in temporales:
            # --- Guardar en tabla principal ---
            obj, created = PresupuestoGestionRiesgos.objects.update_or_create(
                id=temp.id,
                defaults={
                    "centro_tra": temp.centro_tra,
                    "nombre_cen": temp.nombre_cen,
                    "codcosto": temp.codcosto,
                    "responsable": temp.responsable,
                    "cuenta": temp.cuenta,  
                    "cuenta_mayor": temp.cuenta_mayor,
                    "detalle_cuenta": temp.detalle_cuenta,
                    "sede_distribucion": temp.sede_distribucion,
                    "proveedor": temp.proveedor,
                    "enero": temp.enero,
                    "febrero": temp.febrero,
                    "marzo": temp.marzo,
                    "abril": temp.abril,
                    "mayo": temp.mayo,
                    "junio": temp.junio,
                    "julio": temp.julio,
                    "agosto": temp.agosto,
                    "septiembre": temp.septiembre,
                    "octubre": temp.octubre,
                    "noviembre": temp.noviembre,
                    "diciembre": temp.diciembre,
                    "total": temp.total,
                    "comentario": temp.comentario,
                    "version": nueva_version,
                    "fecha": fecha_hoy,
                }
            )
            # --- Guardar en tabla aprobada si aplica ---
            if fecha_hoy <= fecha_limite:
                PresupuestoGestionRiesgosAprobado.objects.update_or_create(
                    id=temp.id,
                    defaults={
                        "centro_tra": temp.centro_tra,
                        "nombre_cen": temp.nombre_cen,
                        "codcosto": temp.codcosto,
                        "responsable": temp.responsable,
                        "cuenta": temp.cuenta,  
                        "cuenta_mayor": temp.cuenta_mayor,
                        "detalle_cuenta": temp.detalle_cuenta,
                        "sede_distribucion": temp.sede_distribucion,
                        "proveedor": temp.proveedor,
                        "enero": temp.enero,
                        "febrero": temp.febrero,
                        "marzo": temp.marzo,
                        "abril": temp.abril,
                        "mayo": temp.mayo,
                        "junio": temp.junio,
                        "julio": temp.julio,
                        "agosto": temp.agosto,
                        "septiembre": temp.septiembre,
                        "octubre": temp.octubre,
                        "noviembre": temp.noviembre,
                        "diciembre": temp.diciembre,
                        "total": temp.total,
                        "comentario": temp.comentario,
                        "version": nueva_version,
                        "fecha": fecha_hoy,
                    }
                )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de gestion de riesgos actualizado ✅ (versión {nueva_version})"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_gestion_riesgos_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total", "comentario"
            }
            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}
                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo","junio", "julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0
                registros.append(PresupuestoGestionRiesgosAux(**row_filtrado))
            # ✅ Transacción atómica → si algo falla, no se borra nada
            with transaction.atomic():
                # limpio toda la tabla auxiliar antes de insertar
                PresupuestoGestionRiesgosAux.objects.all().delete()
                PresupuestoGestionRiesgosAux.objects.bulk_create(registros)
            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_gestion_riesgos_temp(request):
    data = list(PresupuestoGestionRiesgosAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_gestion_riesgos_base(request):
    # limpio tabla auxiliar de gestion de riesgos antes de recalcular
    PresupuestoGestionRiesgosAux.objects.all().delete()
    base_data = Plantillagastos2025.objects.values(
       "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    )
    # filtrar por responsable = 'LUIS FERNANDO VARGAS'
    base_data = base_data.filter(responsable__iexact="LINA RICARDO")
    
    for row in base_data:
        PresupuestoGestionRiesgosAux.objects.create(
            centro_tra=row["centro_tra"],
            nombre_cen=row["nombre_cen"],
            codcosto=row["codcosto"],
            responsable=row["responsable"],
            cuenta=row["cuenta"],
            cuenta_mayor=row["cuenta_mayor"],
            detalle_cuenta=row["detalle_cuenta"],
            sede_distribucion=row["sede_distribucion"],
            proveedor=row["proveedor"],
            enero=row["enero"],
            febrero=row["febrero"],
            marzo=row["marzo"],
            abril=row["abril"],
            mayo=row["mayo"],
            junio=row["junio"],
            julio=row["julio"], 
            agosto=row["agosto"],
            septiembre=row["septiembre"],
            octubre=row["octubre"],
            noviembre=row["noviembre"],
            diciembre=row["diciembre"],
            total=row["enero"] + row["febrero"] + row["marzo"] + row["abril"] + row["mayo"] + row["junio"] + row["julio"] + row["agosto"] + row["septiembre"] + row["octubre"] + row["noviembre"] + row["diciembre"],
            comentario = ""
        )
    
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_gestion_riesgos(request):
    if request.method == "POST":
        version = request.POST.get("version")  # 🔥 versión enviada desde el frontend

        if not version:
            return JsonResponse({"status": "error", "message": "No se especificó la versión"}, status=400)

        # borrar solo la versión seleccionada
        PresupuestoGestionRiesgos.objects.filter(version=version).delete()

        # 📌 Fecha límite
        fecha_limite = datetime.date(2025, 10, 30)
        if timezone.now().date() <= fecha_limite:
            PresupuestoGestionRiesgosAprobado.objects.filter(version=version).delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de gestión de riesgos eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)


#--------PRESUPUESTO GH------------------
@login_required
def presupuesto_gh(request):
    usuarios_permitidos = ['admin', 'GESTIONHUMANA']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    # 🔹 obtener versiones disponibles
    versiones = (
        PresupuestoGH.objects
        .values_list("version", flat=True)
        .distinct()
        .order_by("version")
    )
    ultima_version = max(versiones) if versiones else 1
    return render(request, "presupuesto_general/presupuesto_GH.html", {"versiones": versiones, "ultima_version": ultima_version})

def obtener_presupuesto_gh(request):
    version = request.GET.get("version")  #🔥 versión recibida
    qs = PresupuestoGH.objects.all()
    if version:
        qs = qs.filter(version=version)
    
    data = list(qs.values())
    return JsonResponse({"data": data}, safe=False)

def presupuesto_aprobado_gh(request):
    # 🔹 obtener última versión disponible
    versiones = (
        PresupuestoGHAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    return render(request, "presupuesto_general/presupuesto_aprobado_GH.html", {"ultima_version": ultima_version})

def obtener_presupuesto_aprobado_gh(request):
    # 🔥 siempre filtrar por la última versión
    versiones = (
        PresupuestoGHAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    qs = PresupuestoGHAprobado.objects.filter(version=ultima_version)
    gh_aprobado = list(qs.values())
    return JsonResponse({"data": gh_aprobado}, safe=False)

def tabla_auxiliar_gh(request):
    # 📌 Definir fecha límite
    fecha_limite = datetime.date(2025, 10, 15)  # <-- cámbiala según lo que necesites
    hoy = datetime.date.today()
    # 🚫 Si ya pasó la fecha, negar acceso
    if hoy > fecha_limite:
        return HttpResponseForbidden("⛔ El acceso a esta vista está bloqueado despueś del "
                                        f"{fecha_limite.strftime('%d/%m/%Y')}")
    # ✅ Si aún no llega la fecha, mostrar vista normal
    return render(request, "presupuesto_general/aux_presupuesto_GH.html")

def subir_presupuesto_gh(request):
    if request.method == "POST":
        temporales = PresupuestoGHAux.objects.all()
        fecha_limite = datetime.date(2025, 10, 30)
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)
        # 📌 Fecha actual
        fecha_hoy = timezone.now().date()
        # 📌 Obtener versión global (tomando la última registrada en la tabla
        ultima_version = PresupuestoGH.objects.aggregate(max_ver=models.Max("version"))["max_ver"] or 0
        nueva_version = ultima_version + 1
        for temp in temporales:
            # --- Guardar en tabla principal ---
            obj, created = PresupuestoGH.objects.update_or_create(
                id=temp.id,
                defaults={
                    "centro_tra": temp.centro_tra,
                    "nombre_cen": temp.nombre_cen,
                    "codcosto": temp.codcosto,
                    "responsable": temp.responsable,
                    "cuenta": temp.cuenta,  
                    "cuenta_mayor": temp.cuenta_mayor,
                    "detalle_cuenta": temp.detalle_cuenta,
                    "sede_distribucion": temp.sede_distribucion,
                    "proveedor": temp.proveedor,
                    "enero": temp.enero,
                    "febrero": temp.febrero,
                    "marzo": temp.marzo,
                    "abril": temp.abril,
                    "mayo": temp.mayo,
                    "junio": temp.junio,
                    "julio": temp.julio,
                    "agosto": temp.agosto,
                    "septiembre": temp.septiembre,
                    "octubre": temp.octubre,
                    "noviembre": temp.noviembre,
                    "diciembre": temp.diciembre,
                    "total": temp.total,
                    "comentario": temp.comentario,
                    "version": nueva_version,
                    "fecha": fecha_hoy,
                }
            )
            # --- Guardar en tabla aprobada si aplica ---
            if fecha_hoy <= fecha_limite:
                PresupuestoGHAprobado.objects.update_or_create(
                    id=temp.id,
                    defaults={
                        "centro_tra": temp.centro_tra,
                        "nombre_cen": temp.nombre_cen,
                        "codcosto": temp.codcosto,
                        "responsable": temp.responsable,
                        "cuenta": temp.cuenta,  
                        "cuenta_mayor": temp.cuenta_mayor,
                        "detalle_cuenta": temp.detalle_cuenta,
                        "sede_distribucion": temp.sede_distribucion,
                        "proveedor": temp.proveedor,
                        "enero": temp.enero,
                        "febrero": temp.febrero,
                        "marzo": temp.marzo,
                        "abril": temp.abril,
                        "mayo": temp.mayo,
                        "junio": temp.junio,
                        "julio": temp.julio,
                        "agosto": temp.agosto,
                        "septiembre": temp.septiembre,
                        "octubre": temp.octubre,
                        "noviembre": temp.noviembre,
                        "diciembre": temp.diciembre,
                        "total": temp.total,
                        "comentario": temp.comentario,
                        "version": nueva_version,
                        "fecha": fecha_hoy,
                    }
                )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de GH actualizado ✅ (versión {nueva_version})"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)

def guardar_gh_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total", "comentario"
            }
            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}
                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo","junio", "julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0
                registros.append(PresupuestoGHAux(**row_filtrado))
            # ✅ Transacción atómica → si algo falla, no se borra nada
            with transaction.atomic():
                # limpio toda la tabla auxiliar antes de insertar
                PresupuestoGHAux.objects.all().delete()
                PresupuestoGHAux.objects.bulk_create(registros)
            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_gh_temp(request):
    data = list(PresupuestoGHAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_gh_base(request):
    # limpio tabla auxiliar de gh antes de recalcular
    PresupuestoGHAux.objects.all().delete()
    base_data = Plantillagastos2025.objects.values(
       "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    )
    # filtrar por responsable = 'LUIS FERNANDO VARGAS'
    base_data = base_data.filter(responsable__iexact="MARTA GH")
    
    for row in base_data:
        PresupuestoGHAux.objects.create(
            centro_tra=row["centro_tra"],
            nombre_cen=row["nombre_cen"],
            codcosto=row["codcosto"],
            responsable=row["responsable"],
            cuenta=row["cuenta"],
            cuenta_mayor=row["cuenta_mayor"],
            detalle_cuenta=row["detalle_cuenta"],
            sede_distribucion=row["sede_distribucion"],
            proveedor=row["proveedor"],
            enero=row["enero"],
            febrero=row["febrero"],
            marzo=row["marzo"],
            abril=row["abril"],
            mayo=row["mayo"],
            junio=row["junio"],
            julio=row["julio"], 
            agosto=row["agosto"],
            septiembre=row["septiembre"],
            octubre=row["octubre"],
            noviembre=row["noviembre"],
            diciembre=row["diciembre"],
            total=row["enero"] + row["febrero"] + row["marzo"] + row["abril"] + row["mayo"] + row["junio"] + row["julio"] + row["agosto"] + row["septiembre"] + row["octubre"] + row["noviembre"] + row["diciembre"],
            comentario = ""
        )
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_gh(request):
    if request.method == "POST":
        version = request.POST.get("version")  # 🔥 versión
        if not version:
            return JsonResponse({"status": "error", "message": "No se especificó la versión"}, status=400)
        # borrar solo la versión seleccionada
        PresupuestoGH.objects.filter(version=version).delete()
        # 📌 Fecha límite
        fecha_limite = datetime.date(2025, 10, 23)
        if timezone.now().date() <= fecha_limite:
            PresupuestoGHAprobado.objects.filter(version=version).delete()
        return JsonResponse({"status": "ok", "message": f"Presupuesto de GH versión {version} eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)


#-------------PRESUPUESTO ALMACEN TULUA----------------
@login_required
def presupuesto_almacen_tulua(request):
    usuarios_permitidos = ['admin', 'JEFEALMACENTULUA', 'DBENITEZ']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    # 🔹 obtener versiones disponibles
    versiones = (
        PresupuestoAlmacenTulua.objects
        .values_list("version", flat=True)
        .distinct()
        .order_by("version")
    )
    ultima_version = max(versiones) if versiones else 1
    return render(request, "presupuesto_general/presupuesto_almacen_tulua.html", {"versiones": versiones, "ultima_version": ultima_version})

def obtener_presupuesto_almacen_tulua(request):
    version = request.GET.get("version")  #🔥 versión 
    qs = PresupuestoAlmacenTulua.objects.all()
    if version:
        qs = qs.filter(version=version)
    data = list(qs.values())
    return JsonResponse({"data": data}, safe=False)

def presupuesto_aprobado_almacen_tulua(request):
    # 🔹 obtener última versión disponible
    versiones = (
        PresupuestoAlmacenTuluaAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    return render(request, "presupuesto_general/presupuesto_aprobado_almacen_tulua.html", {"ultima_version": ultima_version})

def obtener_presupuesto_aprobado_almacen_tulua(request):
    # 🔥 siempre filtrar por la última versión
    versiones = (
        PresupuestoAlmacenTuluaAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    qs = PresupuestoAlmacenTuluaAprobado.objects.filter(version=ultima_version)
    almacen_tulua_aprobado = list(qs.values())
    return JsonResponse({"data": almacen_tulua_aprobado}, safe=False)   

def tabla_auxiliar_almacen_tulua(request):
    # 📌 Definir fecha límite
    fecha_limite = datetime.date(2025, 10, 15)  # <-- cámbiala según lo que necesites
    hoy = datetime.date.today()
    # 🚫 Si ya pasó la fecha, negar acceso
    if hoy > fecha_limite:
        return HttpResponseForbidden("⛔ El acceso a esta vista está bloqueado después del "
                                        f"{fecha_limite.strftime('%d/%m/%Y')}")
    # ✅ Si aún no llega la fecha, mostrar vista normal
    return render(request, "presupuesto_general/aux_presupuesto_almacen_tulua.html")

def subir_presupuesto_almacen_tulua(request):
    if request.method == "POST":
        temporales = PresupuestoAlmacenTuluaAux.objects.all()
        fecha_limite = datetime.date(2025, 10, 30)
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)
        # 📌 Fecha actual
        fecha_hoy = timezone.now().date()
        # 📌 Obtener versión global (tomando la última registrada en la tabla 
        ultima_version = PresupuestoAlmacenTulua.objects.aggregate(max_ver=models.Max("version"))["max_ver"] or 0
        nueva_version = ultima_version + 1
        for temp in temporales:
            # --- Guardar en tabla principal ---
            obj, created = PresupuestoAlmacenTulua.objects.update_or_create(
                id=temp.id,
                defaults={
                    "centro_tra": temp.centro_tra,
                    "nombre_cen": temp.nombre_cen,
                    "codcosto": temp.codcosto,
                    "responsable": temp.responsable,
                    "cuenta": temp.cuenta,  
                    "cuenta_mayor": temp.cuenta_mayor,
                    "detalle_cuenta": temp.detalle_cuenta,
                    "sede_distribucion": temp.sede_distribucion,
                    "proveedor": temp.proveedor,
                    "enero": temp.enero,
                    "febrero": temp.febrero,
                    "marzo": temp.marzo,
                    "abril": temp.abril,
                    "mayo": temp.mayo,
                    "junio": temp.junio,
                    "julio": temp.julio,
                    "agosto": temp.agosto,
                    "septiembre": temp.septiembre,
                    "octubre": temp.octubre,
                    "noviembre": temp.noviembre,
                    "diciembre": temp.diciembre,
                    "total": temp.total,
                    "comentario": temp.comentario,
                    "version": nueva_version,
                    "fecha": fecha_hoy,
                }
            )
            # --- Guardar en tabla aprobada si aplica ---
            if fecha_hoy <= fecha_limite:
                PresupuestoAlmacenTuluaAprobado.objects.update_or_create(
                    id=temp.id,
                    defaults={
                        "centro_tra": temp.centro_tra,
                        "nombre_cen": temp.nombre_cen,
                        "codcosto": temp.codcosto,
                        "responsable": temp.responsable,
                        "cuenta": temp.cuenta,  
                        "cuenta_mayor": temp.cuenta_mayor,
                        "detalle_cuenta": temp.detalle_cuenta,
                        "sede_distribucion": temp.sede_distribucion,
                        "proveedor": temp.proveedor,
                        "enero": temp.enero,
                        "febrero": temp.febrero,
                        "marzo": temp.marzo,
                        "abril": temp.abril,
                        "mayo": temp.mayo,
                        "junio": temp.junio,
                        "julio": temp.julio,
                        "agosto": temp.agosto,
                        "septiembre": temp.septiembre,
                        "octubre": temp.octubre,
                        "noviembre": temp.noviembre,
                        "diciembre": temp.diciembre,
                        "total": temp.total,
                        "comentario": temp.comentario,
                        "version": nueva_version,
                        "fecha": fecha_hoy,
                    }
                )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de almacén Tuluá actualizado ✅ (versión {nueva_version})"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_almacen_tulua_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total", "comentario"
            }
            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}
                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo","junio", "julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0
                registros.append(PresupuestoAlmacenTuluaAux(**row_filtrado))
            # ✅ Transacción atómica → si algo falla, no se borra nada
            with transaction.atomic():
                # limpio toda la tabla auxiliar antes de insertar
                PresupuestoAlmacenTuluaAux.objects.all().delete()
                PresupuestoAlmacenTuluaAux.objects.bulk_create(registros)
                
            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_almacen_tulua_temp(request):
    data = list(PresupuestoAlmacenTuluaAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_almacen_tulua_base(request):
    # limpio tabla auxiliar de almacen tulua antes de recalcular
    PresupuestoAlmacenTuluaAux.objects.all().delete()
    base_data = Plantillagastos2025.objects.values(
       "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    )
    # filtrar por responsable = 'JEFE ALMACEN TULUA'
    base_data = base_data.filter(responsable__iexact="JEFE ALMACEN TULUA")
    for row in base_data:
        PresupuestoAlmacenTuluaAux.objects.create(
            centro_tra=row["centro_tra"],
            nombre_cen=row["nombre_cen"],
            codcosto=row["codcosto"],
            responsable=row["responsable"],
            cuenta=row["cuenta"],
            cuenta_mayor=row["cuenta_mayor"],
            detalle_cuenta=row["detalle_cuenta"],
            sede_distribucion=row["sede_distribucion"],
            proveedor=row["proveedor"],
            enero=row["enero"],
            febrero=row["febrero"],
            marzo=row["marzo"],
            abril=row["abril"],
            mayo=row["mayo"],
            junio=row["junio"],
            julio=row["julio"],
            agosto=row["agosto"],
            septiembre=row["septiembre"],
            octubre=row["octubre"],
            noviembre=row["noviembre"],
            diciembre=row["diciembre"],
            total=row["enero"] + row["febrero"] + row["marzo"] + row["abril"] + row["mayo"] + row["junio"] + row["julio"] + row["agosto"] + row["septiembre"] + row["octubre"] + row["noviembre"] + row["diciembre"],
            comentario = ""
        )
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_almacen_tulua(request):
    if request.method == "POST":
        version = request.POST.get("version")  # 🔥 versión enviada desde el frontend

        if not version:
            return JsonResponse({"status": "error", "message": "No se especificó la versión"}, status=400)
        # borrar solo la versión seleccionada
        PresupuestoAlmacenTulua.objects.filter(version=version).delete()
        # 📌 Fecha límite
        fecha_limite = datetime.date(2025, 10, 30)
        if timezone.now().date() <= fecha_limite:
            PresupuestoAlmacenTuluaAprobado.objects.filter(version=version).delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de almacén Tuluá eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)


#-------------PRESUPUESTO ALMACEN BUGA----------------
@login_required
def presupuesto_almacen_buga(request):
    usuarios_permitidos = ['admin', 'JEFEALMACENBUGA', 'FDUQUE']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    # 🔹 obtener versiones disponibles
    versiones = (
        PresupuestoAlmacenBuga.objects
        .values_list("version", flat=True)
        .distinct()
        .order_by("version")
    )
    ultima_version = max(versiones) if versiones else 1
    return render(request, "presupuesto_general/presupuesto_almacen_buga.html", {"versiones": versiones, "ultima_version": ultima_version})

def obtener_presupuesto_almacen_buga(request):
    version = request.GET.get("version")  #🔥 versión 
    qs = PresupuestoAlmacenBuga.objects.all()
    if version:
        qs = qs.filter(version=version)
    data = list(qs.values())
    return JsonResponse({"data": data}, safe=False)

def presupuesto_aprobado_almacen_buga(request):
    # obtener última version disponible
    versiones = (
        PresupuestoAlmacenBugaAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    
    return render(request, "presupuesto_general/presupuesto_aprobado_almacen_buga.html", {"ultima_version": ultima_version})

def obtener_presupuesto_aprobado_almacen_buga(request):
    # filtrar por la última versión
    versiones = (
        PresupuestoAlmacenBugaAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    qs = PresupuestoAlmacenBugaAprobado.objects.filter(version=ultima_version)
    data = list(qs.values())
    
    return JsonResponse({"data": data}, safe=False)

def tabla_auxiliar_almacen_buga(request):
    # 📌 Definir fecha límite
    fecha_limite = datetime.date(2025, 10, 15)  # <-- cámbiala según lo que necesites
    hoy = datetime.date.today()
    # 🚫 Si ya pasó la fecha, negar acceso
    if hoy > fecha_limite:
        return HttpResponseForbidden("⛔ El acceso a esta vista está bloqueado después del "
                                        f"{fecha_limite.strftime('%d/%m/%Y')}")
    # ✅ Si aún no llega la fecha, mostrar vista normal
    return render(request, "presupuesto_general/aux_presupuesto_almacen_buga.html")

def subir_presupuesto_almacen_buga(request):
    if request.method == "POST":
        temporales = PresupuestoAlmacenBugaAux.objects.all()
        fecha_limite = datetime.date(2025, 10, 30)
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)
        # 📌 Fecha actual
        fecha_hoy = timezone.now().date()
        # 📌 Obtener versión global (tomando la última registrada en la tabla 
        ultima_version = PresupuestoAlmacenBuga.objects.aggregate(max_ver=models.Max("version"))["max_ver"] or 0
        nueva_version = ultima_version + 1
        for temp in temporales:
            # --- Guardar en tabla principal ---
            obj, created = PresupuestoAlmacenBuga.objects.update_or_create(
                id=temp.id,
                defaults={
                    "centro_tra": temp.centro_tra,
                    "nombre_cen": temp.nombre_cen,
                    "codcosto": temp.codcosto,
                    "responsable": temp.responsable,
                    "cuenta": temp.cuenta,  
                    "cuenta_mayor": temp.cuenta_mayor,
                    "detalle_cuenta": temp.detalle_cuenta,
                    "sede_distribucion": temp.sede_distribucion,
                    "proveedor": temp.proveedor,
                    "enero": temp.enero,
                    "febrero": temp.febrero,
                    "marzo": temp.marzo,
                    "abril": temp.abril,
                    "mayo": temp.mayo,
                    "junio": temp.junio,
                    "julio": temp.julio,
                    "agosto": temp.agosto,
                    "septiembre": temp.septiembre,
                    "octubre": temp.octubre,
                    "noviembre": temp.noviembre,
                    "diciembre": temp.diciembre,
                    "total": temp.total,
                    "comentario": temp.comentario,
                    "version": nueva_version,
                    "fecha": fecha_hoy,
                }
            )
            # --- Guardar en tabla aprobada si aplica ---
            if fecha_hoy <= fecha_limite:
                PresupuestoAlmacenBugaAprobado.objects.update_or_create(
                    id=temp.id,
                    defaults={
                        "centro_tra": temp.centro_tra,
                        "nombre_cen": temp.nombre_cen,
                        "codcosto": temp.codcosto,
                        "responsable": temp.responsable,
                        "cuenta": temp.cuenta,  
                        "cuenta_mayor": temp.cuenta_mayor,
                        "detalle_cuenta": temp.detalle_cuenta,
                        "sede_distribucion": temp.sede_distribucion,
                        "proveedor": temp.proveedor,
                        "enero": temp.enero,
                        "febrero": temp.febrero,
                        "marzo": temp.marzo,
                        "abril": temp.abril,
                        "mayo": temp.mayo,
                        "junio": temp.junio,
                        "julio": temp.julio,
                        "agosto": temp.agosto,
                        "septiembre": temp.septiembre,
                        "octubre": temp.octubre,
                        "noviembre": temp.noviembre,
                        "diciembre": temp.diciembre,
                        "total": temp.total,
                        "comentario": temp.comentario,
                        "version": nueva_version,
                        "fecha": fecha_hoy,
                    }
                )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de almacén Buga actualizado ✅ (versión {nueva_version})"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_almacen_buga_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total", "comentario"
            }
            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}
                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo","junio", "julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0
                registros.append(PresupuestoAlmacenBugaAux(**row_filtrado))
            # ✅ Transacción atómica → si algo falla, no se borra nada
            with transaction.atomic():
                # limpio toda la tabla auxiliar antes de insertar
                PresupuestoAlmacenBugaAux.objects.all().delete()
                PresupuestoAlmacenBugaAux.objects.bulk_create(registros)
            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_almacen_buga_temp(request):
    data = list(PresupuestoAlmacenBugaAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_almacen_buga_base(request):
    # limpio tabla auxiliar de almacen buga antes de recalcular
    PresupuestoAlmacenBugaAux.objects.all().delete()
    base_data = Plantillagastos2025.objects.values(
       "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    )
    # filtrar por responsable = 'JEFE ALMACEN BUGA'
    base_data = base_data.filter(responsable__iexact="JEFE ALMACEN BUGA")
    
    for row in base_data:
        PresupuestoAlmacenBugaAux.objects.create(
            centro_tra=row["centro_tra"],
            nombre_cen=row["nombre_cen"],
            codcosto=row["codcosto"],
            responsable=row["responsable"],
            cuenta=row["cuenta"],
            cuenta_mayor=row["cuenta_mayor"],
            detalle_cuenta=row["detalle_cuenta"],
            sede_distribucion=row["sede_distribucion"],
            proveedor=row["proveedor"],
            enero=row["enero"],
            febrero=row["febrero"],
            marzo=row["marzo"],
            abril=row["abril"],
            mayo=row["mayo"],
            junio=row["junio"],
            julio=row["julio"], 
            agosto=row["agosto"],
            septiembre=row["septiembre"],
            octubre=row["octubre"],
            noviembre=row["noviembre"],
            diciembre=row["diciembre"],
            total=row["enero"] + row["febrero"] + row["marzo"] + row["abril"] + row["mayo"] + row["junio"] + row["julio"] + row["agosto"] + row["septiembre"] + row["octubre"] + row["noviembre"] + row["diciembre"],
            comentario = ""
        )
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_almacen_buga(request):
    if request.method == "POST":
        version = request.POST.get("version")  # 🔥 versión enviada desde el frontend

        if not version:
            return JsonResponse({"status": "error", "message": "No se especificó la versión"}, status=400)
        # borrar solo la versión seleccionada
        PresupuestoAlmacenBuga.objects.filter(version=version).delete()
        # 📌 Fecha límite
        fecha_limite = datetime.date(2025, 10, 30)
        if timezone.now().date() <= fecha_limite:
            PresupuestoAlmacenBugaAprobado.objects.filter(version=version).delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de almacén Buga eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#--------PRESUPUESTO ALMACEN CARTAGO----------------
@login_required
def presupuesto_almacen_cartago(request):
    usuarios_permitidos = ['admin', 'JEFEALMACENCARTAGO', 'CHINCAPI']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    # 🔹 obtener versiones disponibles
    versiones = (
        PresupuestoAlmacenCartago.objects
        .values_list("version", flat=True)
        .distinct()
        .order_by("version")
    )
    ultima_version = max(versiones) if versiones else 1
    return render(request, "presupuesto_general/presupuesto_almacen_cartago.html", {"versiones": versiones, "ultima_version": ultima_version})

def obtener_presupuesto_almacen_cartago(request):
    version = request.GET.get("version")  #🔥 versión 
    qs = PresupuestoAlmacenCartago.objects.all()
    if version:
        qs = qs.filter(version=version)
    data = list(qs.values())
    return JsonResponse({"data": data}, safe=False)

def presupuesto_aprobado_almacen_cartago(request):
    # obtener última version disponible
    versiones = (
        PresupuestoAlmacenCartagoAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    
    return render(request, "presupuesto_general/presupuesto_aprobado_almacen_cartago.html", {"ultima_version": ultima_version})

def obtener_presupuesto_aprobado_almacen_cartago(request):
    # filtrar por la última versión
    versiones = (
        PresupuestoAlmacenCartagoAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    qs = PresupuestoAlmacenCartagoAprobado.objects.filter(version=ultima_version)
    data = list(qs.values())
    
    return JsonResponse({"data": data}, safe=False)

def tabla_auxiliar_almacen_cartago(request):
    # 📌 Definir fecha límite
    fecha_limite = datetime.date(2025, 10, 15)  # <-- cámbiala según lo que necesites
    hoy = datetime.date.today()
    # 🚫 Si ya pasó la fecha, negar acceso
    if hoy > fecha_limite:
        return HttpResponseForbidden("⛔ El acceso a esta vista está bloqueado después del "
                                        f"{fecha_limite.strftime('%d/%m/%Y')}")
    # ✅ Si aún no llega la fecha, mostrar vista normal
    return render(request, "presupuesto_general/aux_presupuesto_almacen_cartago.html")

def subir_presupuesto_almacen_cartago(request):
    if request.method == "POST":
        temporales = PresupuestoAlmacenCartagoAux.objects.all()
        fecha_limite = datetime.date(2025, 10, 30)
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)
        # 📌 Fecha actual
        fecha_hoy = timezone.now().date()
        # 📌 Obtener versión global (tomando la última registrada en la tabla 
        ultima_version = PresupuestoAlmacenCartago.objects.aggregate(max_ver=models.Max("version"))["max_ver"] or 0
        nueva_version = ultima_version + 1
        for temp in temporales:
            # --- Guardar en tabla principal ---
            obj, created = PresupuestoAlmacenCartago.objects.update_or_create(
                id=temp.id,
                defaults={
                    "centro_tra": temp.centro_tra,
                    "nombre_cen": temp.nombre_cen,
                    "codcosto": temp.codcosto,
                    "responsable": temp.responsable,
                    "cuenta": temp.cuenta,  
                    "cuenta_mayor": temp.cuenta_mayor,
                    "detalle_cuenta": temp.detalle_cuenta,
                    "sede_distribucion": temp.sede_distribucion,
                    "proveedor": temp.proveedor,
                    "enero": temp.enero,
                    "febrero": temp.febrero,
                    "marzo": temp.marzo,
                    "abril": temp.abril,
                    "mayo": temp.mayo,
                    "junio": temp.junio,
                    "julio": temp.julio,
                    "agosto": temp.agosto,
                    "septiembre": temp.septiembre,
                    "octubre": temp.octubre,
                    "noviembre": temp.noviembre,
                    "diciembre": temp.diciembre,
                    "total": temp.total,
                    "comentario": temp.comentario,
                    "version": nueva_version,
                    "fecha": fecha_hoy,
                }
            )
            # --- Guardar en tabla aprobada si aplica ---
            if fecha_hoy <= fecha_limite:
                PresupuestoAlmacenCartagoAprobado.objects.update_or_create(
                    id=temp.id,
                    defaults={
                        "centro_tra": temp.centro_tra,
                        "nombre_cen": temp.nombre_cen,
                        "codcosto": temp.codcosto,
                        "responsable": temp.responsable,
                        "cuenta": temp.cuenta,  
                        "cuenta_mayor": temp.cuenta_mayor,
                        "detalle_cuenta": temp.detalle_cuenta,
                        "sede_distribucion": temp.sede_distribucion,
                        "proveedor": temp.proveedor,
                        "enero": temp.enero,
                        "febrero": temp.febrero,
                        "marzo": temp.marzo,
                        "abril": temp.abril,
                        "mayo": temp.mayo,
                        "junio": temp.junio,
                        "julio": temp.julio,
                        "agosto": temp.agosto,
                        "septiembre": temp.septiembre,
                        "octubre": temp.octubre,
                        "noviembre": temp.noviembre,
                        "diciembre": temp.diciembre,
                        "total": temp.total,
                        "comentario": temp.comentario,
                        "version": nueva_version,
                        "fecha": fecha_hoy,
                    }
                )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de almacén Cartago actualizado ✅ (versión {nueva_version})"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_almacen_cartago_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total", "comentario"
            }
            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}
                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo","junio", "julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0
                registros.append(PresupuestoAlmacenCartagoAux(**row_filtrado))
            # ✅ Transacción atómica → si algo falla, no se borra nada
            with transaction.atomic():
                # limpio toda la tabla auxiliar antes de insertar
                PresupuestoAlmacenCartagoAux.objects.all().delete()
                PresupuestoAlmacenCartagoAux.objects.bulk_create(registros)
            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_almacen_cartago_temp(request):
    data = list(PresupuestoAlmacenCartagoAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_almacen_cartago_base(request):
    # limpio tabla auxiliar de almacen cartago antes de recalcular
    PresupuestoAlmacenCartagoAux.objects.all().delete()
    base_data = Plantillagastos2025.objects.values(
       "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    )
    # filtrar por responsable = 'JEFE ALMACEN CARTAGO'
    base_data = base_data.filter(responsable__iexact="CLAUDIA H")
    
    for row in base_data:
        PresupuestoAlmacenCartagoAux.objects.create(
            centro_tra=row["centro_tra"],
            nombre_cen=row["nombre_cen"],
            codcosto=row["codcosto"],
            responsable=row["responsable"],
            cuenta=row["cuenta"],
            cuenta_mayor=row["cuenta_mayor"],
            detalle_cuenta=row["detalle_cuenta"],
            sede_distribucion=row["sede_distribucion"],
            proveedor=row["proveedor"],
            enero=row["enero"],
            febrero=row["febrero"],
            marzo=row["marzo"],
            abril=row["abril"],
            mayo=row["mayo"],
            junio=row["junio"],
            julio=row["julio"], 
            agosto=row["agosto"],
            septiembre=row["septiembre"],
            octubre=row["octubre"],
            noviembre=row["noviembre"],
            diciembre=row["diciembre"],
            total=row["enero"] + row["febrero"] + row["marzo"] + row["abril"] + row["mayo"] + row["junio"] + row["julio"] + row["agosto"] + row["septiembre"] + row["octubre"] + row["noviembre"] + row["diciembre"],
            comentario = ""
        )
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_almacen_cartago(request):
    if request.method == "POST":
        version = request.POST.get("version")  # 🔥 versión enviada desde el frontend

        if not version:
            return JsonResponse({"status": "error", "message": "No se especificó la versión"}, status=400)
        # borrar solo la versión seleccionada
        PresupuestoAlmacenCartago.objects.filter(version=version).delete()
        # 📌 Fecha límite
        fecha_limite = datetime.date(2025, 10, 30)
        if timezone.now().date() <= fecha_limite:
            PresupuestoAlmacenCartagoAprobado.objects.filter(version=version).delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de almacén Cartago eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#----------PRESUPUESTO ALMACEN CALI----------------
@login_required
def presupuesto_almacen_cali(request):
    usuarios_permitidos = ['admin', 'JEFEALMACENCALI', 'LAMAYA']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    # 🔹 obtener versiones disponibles
    versiones = (
        PresupuestoAlmacenCali.objects
        .values_list("version", flat=True)
        .distinct()
        .order_by("version")
    )
    ultima_version = max(versiones) if versiones else 1
    return render(request, "presupuesto_general/presupuesto_almacen_cali.html", {"versiones": versiones, "ultima_version": ultima_version})

def obtener_presupuesto_almacen_cali(request):
    version = request.GET.get("version")  #🔥 versión 
    qs = PresupuestoAlmacenCali.objects.all()
    if version:
        qs = qs.filter(version=version)
    data = list(qs.values())
    return JsonResponse({"data": data}, safe=False)

def presupuesto_aprobado_almacen_cali(request):
    # obtener última version disponible
    versiones = (
        PresupuestoAlmacenCaliAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    
    return render(request, "presupuesto_general/presupuesto_aprobado_almacen_cali.html", {"ultima_version": ultima_version})

def obtener_presupuesto_aprobado_almacen_cali(request):
    # filtrar por la última versión
    versiones = (
        PresupuestoAlmacenCaliAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    qs = PresupuestoAlmacenCaliAprobado.objects.filter(version=ultima_version)
    data = list(qs.values())
    
    return JsonResponse({"data": data}, safe=False)

def tabla_auxiliar_almacen_cali(request):
    # 📌 Definir fecha límite
    fecha_limite = datetime.date(2025, 10, 15)  # <-- cámbiala según lo que necesites
    hoy = datetime.date.today()
    # 🚫 Si ya pasó la fecha, negar acceso
    if hoy > fecha_limite:
        return HttpResponseForbidden("⛔ El acceso a esta vista está bloqueado después del "
                                        f"{fecha_limite.strftime('%d/%m/%Y')}")
    # ✅ Si aún no llega la fecha, mostrar vista normal
    return render(request, "presupuesto_general/aux_presupuesto_almacen_cali.html")

def subir_presupuesto_almacen_cali(request):
    if request.method == "POST":
        temporales = PresupuestoAlmacenCaliAux.objects.all()
        fecha_limite = datetime.date(2025, 10, 30)
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)
        # 📌 Fecha actual
        fecha_hoy = timezone.now().date()
        # 📌 Obtener versión global (tomando la última registrada en la tabla 
        ultima_version = PresupuestoAlmacenCali.objects.aggregate(max_ver=models.Max("version"))["max_ver"] or 0
        nueva_version = ultima_version + 1
        for temp in temporales:
            # --- Guardar en tabla principal ---
            obj, created = PresupuestoAlmacenCali.objects.update_or_create(
                id=temp.id,
                defaults={
                    "centro_tra": temp.centro_tra,
                    "nombre_cen": temp.nombre_cen,
                    "codcosto": temp.codcosto,
                    "responsable": temp.responsable,
                    "cuenta": temp.cuenta,  
                    "cuenta_mayor": temp.cuenta_mayor,
                    "detalle_cuenta": temp.detalle_cuenta,
                    "sede_distribucion": temp.sede_distribucion,
                    "proveedor": temp.proveedor,
                    "enero": temp.enero,
                    "febrero": temp.febrero,
                    "marzo": temp.marzo,
                    "abril": temp.abril,
                    "mayo": temp.mayo,
                    "junio": temp.junio,
                    "julio": temp.julio,
                    "agosto": temp.agosto,
                    "septiembre": temp.septiembre,
                    "octubre": temp.octubre,
                    "noviembre": temp.noviembre,
                    "diciembre": temp.diciembre,
                    "total": temp.total,
                    "comentario": temp.comentario,
                    "version": nueva_version,
                    "fecha": fecha_hoy,
                }
            )
            # --- Guardar en tabla aprobada si aplica ---
            if fecha_hoy <= fecha_limite:
                PresupuestoAlmacenCaliAprobado.objects.update_or_create(
                    id=temp.id,
                    defaults={
                        "centro_tra": temp.centro_tra,
                        "nombre_cen": temp.nombre_cen,
                        "codcosto": temp.codcosto,
                        "responsable": temp.responsable,
                        "cuenta": temp.cuenta,  
                        "cuenta_mayor": temp.cuenta_mayor,
                        "detalle_cuenta": temp.detalle_cuenta,
                        "sede_distribucion": temp.sede_distribucion,
                        "proveedor": temp.proveedor,
                        "enero": temp.enero,
                        "febrero": temp.febrero,
                        "marzo": temp.marzo,
                        "abril": temp.abril,
                        "mayo": temp.mayo,
                        "junio": temp.junio,
                        "julio": temp.julio,
                        "agosto": temp.agosto,
                        "septiembre": temp.septiembre,
                        "octubre": temp.octubre,
                        "noviembre": temp.noviembre,
                        "diciembre": temp.diciembre,
                        "total": temp.total,
                        "comentario": temp.comentario,
                        "version": nueva_version,
                        "fecha": fecha_hoy,
                    }
                )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de almacén Cali actualizado ✅ (versión {nueva_version})"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_almacen_cali_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total", "comentario"
            }
            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}
                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo","junio", "julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0
                registros.append(PresupuestoAlmacenCaliAux(**row_filtrado))
            # ✅ Transacción atómica → si algo falla, no se borra nada
            with transaction.atomic():
                # limpio toda la tabla auxiliar antes de insertar
                PresupuestoAlmacenCaliAux.objects.all().delete()
                PresupuestoAlmacenCaliAux.objects.bulk_create(registros)
            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_almacen_cali_temp(request):
    data = list(PresupuestoAlmacenCaliAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_almacen_cali_base(request):
    # limpio tabla auxiliar de almacen cali antes de recalcular
    PresupuestoAlmacenCaliAux.objects.all().delete()
    base_data = Plantillagastos2025.objects.values(
       "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    )
    # filtrar por responsable = 'JEFE ALMACEN CALI'
    base_data = base_data.filter(responsable__iexact="JEFE ALMACEN CALI")
    
    for row in base_data:
        PresupuestoAlmacenCaliAux.objects.create(
            centro_tra=row["centro_tra"],
            nombre_cen=row["nombre_cen"],
            codcosto=row["codcosto"],
            responsable=row["responsable"],
            cuenta=row["cuenta"],
            cuenta_mayor=row["cuenta_mayor"],
            detalle_cuenta=row["detalle_cuenta"],
            sede_distribucion=row["sede_distribucion"],
            proveedor=row["proveedor"],
            enero=row["enero"],
            febrero=row["febrero"],
            marzo=row["marzo"],
            abril=row["abril"],
            mayo=row["mayo"],
            junio=row["junio"],
            julio=row["julio"], 
            agosto=row["agosto"],
            septiembre=row["septiembre"],
            octubre=row["octubre"],
            noviembre=row["noviembre"],
            diciembre=row["diciembre"],
            total=row["enero"] + row["febrero"] + row["marzo"] + row["abril"] + row["mayo"] + row["junio"] + row["julio"] + row["agosto"] + row["septiembre"] + row["octubre"] + row["noviembre"] + row["diciembre"],
            comentario = ""
        )
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_almacen_cali(request):
    if request.method == "POST":
        version = request.POST.get("version")  # 🔥 versión enviada desde el frontend

        if not version:
            return JsonResponse({"status": "error", "message": "No se especificó la versión"}, status=400)
        # borrar solo la versión seleccionada
        PresupuestoAlmacenCali.objects.filter(version=version).delete()
        # 📌 Fecha límite
        fecha_limite = datetime.date(2025, 10, 30)
        if timezone.now().date() <= fecha_limite:
            PresupuestoAlmacenCaliAprobado.objects.filter(version=version).delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de almacén Cali eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#-----------------PRESUPUESTO COMUNICACIONES-------------------
@login_required
def presupuesto_comunicaciones(request):
    usuarios_permitidos = ['admin', 'COMUNICACIONES']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    # 🔹 obtener versiones disponibles
    versiones = (
        PresupuestoComunicaciones.objects
        .values_list("version", flat=True)
        .distinct()
        .order_by("version")
    )
    ultima_version = max(versiones) if versiones else 1
    return render(request, "presupuesto_general/presupuesto_comunicaciones.html", {"versiones": versiones, "ultima_version": ultima_version})

def obtener_presupuesto_comunicaciones(request):
    version = request.GET.get("version")  #🔥 versión 
    qs = PresupuestoComunicaciones.objects.all()
    if version:
        qs = qs.filter(version=version)
    data = list(qs.values())
    return JsonResponse({"data": data}, safe=False)

def presupuesto_aprobado_comunicaciones(request):
    # obtener última version disponible
    versiones = (
        PresupuestoComunicacionesAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    
    return render(request, "presupuesto_general/presupuesto_aprobado_comunicaciones.html", {"ultima_version": ultima_version})

def obtener_presupuesto_aprobado_comunicaciones(request):
    # filtrar por la última versión
    versiones = (
        PresupuestoComunicacionesAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    qs = PresupuestoComunicacionesAprobado.objects.filter(version=ultima_version)
    data = list(qs.values())
    
    return JsonResponse({"data": data}, safe=False)

def tabla_auxiliar_comunicaciones(request):
    usuarios_permitidos = ['admin', 'COMUNICACIONES']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    # 📌 Definir fecha límite
    fecha_limite = datetime.date(2025, 10, 8)  # <-- cámbiala según lo que necesites
    hoy = datetime.date.today()
    # 🚫 Si ya pasó la fecha, negar acceso
    if hoy > fecha_limite:
        return HttpResponseForbidden("⛔ El acceso a esta vista está bloqueado después del "
                                        f"{fecha_limite.strftime('%d/%m/%Y')}")
    # ✅ Si aún no llega la fecha, mostrar vista normal
    return render(request, "presupuesto_general/aux_presupuesto_comunicaciones.html")

def subir_presupuesto_comunicaciones(request):
    if request.method == "POST":
        temporales = PresupuestoComunicacionesAux.objects.all()
        fecha_limite = datetime.date(2025, 10, 30)
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)
        # 📌 Fecha actual
        fecha_hoy = timezone.now().date()
        # 📌 Obtener versión global (tomando la última registrada en la tabla 
        ultima_version = PresupuestoComunicaciones.objects.aggregate(max_ver=models.Max("version"))["max_ver"] or 0
        nueva_version = ultima_version + 1
        for temp in temporales:
            # --- Guardar en tabla principal ---
            obj, created = PresupuestoComunicaciones.objects.update_or_create(
                id=temp.id,
                defaults={
                    "centro_tra": temp.centro_tra,
                    "nombre_cen": temp.nombre_cen,
                    "codcosto": temp.codcosto,
                    "responsable": temp.responsable,
                    "cuenta": temp.cuenta,  
                    "cuenta_mayor": temp.cuenta_mayor,
                    "detalle_cuenta": temp.detalle_cuenta,
                    "sede_distribucion": temp.sede_distribucion,
                    "proveedor": temp.proveedor,
                    "enero": temp.enero,
                    "febrero": temp.febrero,
                    "marzo": temp.marzo,
                    "abril": temp.abril,
                    "mayo": temp.mayo,
                    "junio": temp.junio,
                    "julio": temp.julio,
                    "agosto": temp.agosto,
                    "septiembre": temp.septiembre,
                    "octubre": temp.octubre,
                    "noviembre": temp.noviembre,
                    "diciembre": temp.diciembre,
                    "total": temp.total,
                    "comentario": temp.comentario,
                    "version": nueva_version,
                    "fecha": fecha_hoy,
                }
            )
            # --- Guardar en tabla aprobada si aplica ---
            if fecha_hoy <= fecha_limite:
                PresupuestoComunicacionesAprobado.objects.update_or_create(
                    id=temp.id,
                    defaults={
                        "centro_tra": temp.centro_tra,
                        "nombre_cen": temp.nombre_cen,
                        "codcosto": temp.codcosto,
                        "responsable": temp.responsable,
                        "cuenta": temp.cuenta,  
                        "cuenta_mayor": temp.cuenta_mayor,
                        "detalle_cuenta": temp.detalle_cuenta,
                        "sede_distribucion": temp.sede_distribucion,
                        "proveedor": temp.proveedor,
                        "enero": temp.enero,
                        "febrero": temp.febrero,
                        "marzo": temp.marzo,
                        "abril": temp.abril,
                        "mayo": temp.mayo,
                        "junio": temp.junio,
                        "julio": temp.julio,
                        "agosto": temp.agosto,
                        "septiembre": temp.septiembre,
                        "octubre": temp.octubre,
                        "noviembre": temp.noviembre,
                        "diciembre": temp.diciembre,
                        "total": temp.total,
                        "comentario": temp.comentario,
                        "version": nueva_version,
                        "fecha": fecha_hoy,
                    }
                )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de comunicaciones actualizado ✅ (versión {nueva_version})"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_comunicaciones_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total", "comentario"
            }
            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}
                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo","junio", "julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0
                registros.append(PresupuestoComunicacionesAux(**row_filtrado))
            # ✅ Transacción atómica → si algo falla, no se borra nada
            with transaction.atomic():
                # limpio toda la tabla auxiliar antes de insertar
                PresupuestoComunicacionesAux.objects.all().delete()
                PresupuestoComunicacionesAux.objects.bulk_create(registros)
            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_comunicaciones_temp(request):
    data = list(PresupuestoComunicacionesAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_comunicaciones_base(request):
    # limpio tabla auxiliar de comunicaciones antes de recalcular
    PresupuestoComunicacionesAux.objects.all().delete()
    base_data = Plantillagastos2025.objects.values(
       "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    )
    # filtrar por responsable = 'JEFE COMUNICACIONES'
    base_data = base_data.filter(responsable__iexact="CARLOS USMAN")
    
    for row in base_data:
        PresupuestoComunicacionesAux.objects.create(
            centro_tra=row["centro_tra"],
            nombre_cen=row["nombre_cen"],
            codcosto=row["codcosto"],
            responsable=row["responsable"],
            cuenta=row["cuenta"],
            cuenta_mayor=row["cuenta_mayor"],
            detalle_cuenta=row["detalle_cuenta"],
            sede_distribucion=row["sede_distribucion"],
            proveedor=row["proveedor"],
            enero=row["enero"],
            febrero=row["febrero"],
            marzo=row["marzo"],
            abril=row["abril"],
            mayo=row["mayo"],
            junio=row["junio"],
            julio=row["julio"], 
            agosto=row["agosto"],
            septiembre=row["septiembre"],
            octubre=row["octubre"],
            noviembre=row["noviembre"],
            diciembre=row["diciembre"],
            total=row["enero"] + row["febrero"] + row["marzo"] + row["abril"] + row["mayo"] + row["junio"] + row["julio"] + row["agosto"] + row["septiembre"] + row["octubre"] + row["noviembre"] + row["diciembre"],
            comentario = ""
        )
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_comunicaciones(request):
    if request.method == "POST":
        version = request.POST.get("version")  # 🔥 versión enviada desde el frontend

        if not version:
            return JsonResponse({"status": "error", "message": "No se especificó la versión"}, status=400)
        # borrar solo la versión seleccionada
        PresupuestoComunicaciones.objects.filter(version=version).delete()
        # 📌 Fecha límite
        fecha_limite = datetime.date(2025, 10, 30)
        if timezone.now().date() <= fecha_limite:
            PresupuestoComunicacionesAprobado.objects.filter(version=version).delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de comunicaciones eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#---------------PRESUPUESTO COMERCIAL COSTOS-------------------
@login_required
def presupuesto_comercial_costos(request):
    usuarios_permitidos = ['admin', 'COMERCIALCOSTOS', 'EVALENCIA', 'SCORTES']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    # 🔹 obtener versiones disponibles
    versiones = (
        PresupuestoComercialCostos.objects
        .values_list("version", flat=True)
        .distinct()
        .order_by("version")
    )
    ultima_version = max(versiones) if versiones else 1
    return render(request, "presupuesto_general/presupuesto_comercial_costos.html", {"versiones": versiones, "ultima_version": ultima_version})

def obtener_presupuesto_comercial_costos(request):
    version = request.GET.get("version")  #🔥 versión 
    qs = PresupuestoComercialCostos.objects.all()
    if version:
        qs = qs.filter(version=version)
    data = list(qs.values())
    return JsonResponse({"data": data}, safe=False)

def presupuesto_aprobado_comercial_costos(request):
    # obtener última version disponible
    versiones = (
        PresupuestoComercialCostosAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    
    return render(request, "presupuesto_general/presupuesto_aprobado_comercial_costos.html", {"ultima_version": ultima_version})

def obtener_presupuesto_aprobado_comercial_costos(request):
    # filtrar por la última versión
    versiones = (
        PresupuestoComercialCostosAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    qs = PresupuestoComercialCostosAprobado.objects.filter(version=ultima_version)
    data = list(qs.values())
    
    return JsonResponse({"data": data}, safe=False)

def tabla_auxiliar_comercial_costos(request):
    # 📌 Definir fecha límite
    fecha_limite = datetime.date(2025, 10, 8)  # <-- cámbiala según lo que necesites
    hoy = datetime.date.today()
    # 🚫 Si ya pasó la fecha, negar acceso
    if hoy > fecha_limite:
        return HttpResponseForbidden("⛔ El acceso a esta vista está bloqueado después del "
                                        f"{fecha_limite.strftime('%d/%m/%Y')}")
    # ✅ Si aún no llega la fecha, mostrar vista normal
    return render(request, "presupuesto_general/aux_presupuesto_comercial_costos.html")

def subir_presupuesto_comercial_costos(request):
    if request.method == "POST":
        temporales = PresupuestoComercialCostosAux.objects.all()
        fecha_limite = datetime.date(2025, 10, 30)
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)
        # 📌 Fecha actual
        fecha_hoy = timezone.now().date()
        # 📌 Obtener versión global (tomando la última registrada en la tabla 
        ultima_version = PresupuestoComercialCostos.objects.aggregate(max_ver=models.Max("version"))["max_ver"] or 0
        nueva_version = ultima_version + 1
        for temp in temporales:
            # --- Guardar en tabla principal ---
            obj, created = PresupuestoComercialCostos.objects.update_or_create(
                id=temp.id,
                defaults={
                    "centro_tra": temp.centro_tra,
                    "nombre_cen": temp.nombre_cen,
                    "codcosto": temp.codcosto,
                    "responsable": temp.responsable,
                    "cuenta": temp.cuenta,  
                    "cuenta_mayor": temp.cuenta_mayor,
                    "detalle_cuenta": temp.detalle_cuenta,
                    "sede_distribucion": temp.sede_distribucion,
                    "proveedor": temp.proveedor,
                    "enero": temp.enero,
                    "febrero": temp.febrero,
                    "marzo": temp.marzo,
                    "abril": temp.abril,
                    "mayo": temp.mayo,
                    "junio": temp.junio,
                    "julio": temp.julio,
                    "agosto": temp.agosto,
                    "septiembre": temp.septiembre,
                    "octubre": temp.octubre,
                    "noviembre": temp.noviembre,
                    "diciembre": temp.diciembre,
                    "total": temp.total,
                    "comentario": temp.comentario,
                    "version": nueva_version,
                    "fecha": fecha_hoy,
                }
            )
            # --- Guardar en tabla aprobada si aplica ---
            if fecha_hoy <= fecha_limite:
                PresupuestoComercialCostosAprobado.objects.update_or_create(
                    id=temp.id,
                    defaults={
                        "centro_tra": temp.centro_tra,
                        "nombre_cen": temp.nombre_cen,
                        "codcosto": temp.codcosto,
                        "responsable": temp.responsable,
                        "cuenta": temp.cuenta,  
                        "cuenta_mayor": temp.cuenta_mayor,
                        "detalle_cuenta": temp.detalle_cuenta,
                        "sede_distribucion": temp.sede_distribucion,
                        "proveedor": temp.proveedor,
                        "enero": temp.enero,
                        "febrero": temp.febrero,
                        "marzo": temp.marzo,
                        "abril": temp.abril,
                        "mayo": temp.mayo,
                        "junio": temp.junio,
                        "julio": temp.julio,
                        "agosto": temp.agosto,
                        "septiembre": temp.septiembre,
                        "octubre": temp.octubre,
                        "noviembre": temp.noviembre,
                        "diciembre": temp.diciembre,
                        "total": temp.total,
                        "comentario": temp.comentario,
                        "version": nueva_version,
                        "fecha": fecha_hoy,
                    }
                )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de comercial costos actualizado ✅ (versión {nueva_version})"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_comercial_costos_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total", "comentario"
            }
            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}
                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo","junio", "julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0
                registros.append(PresupuestoComercialCostosAux(**row_filtrado))
            # ✅ Transacción atómica → si algo falla, no se borra nada
            with transaction.atomic():
                # limpio toda la tabla auxiliar antes de insertar
                PresupuestoComercialCostosAux.objects.all().delete()
                PresupuestoComercialCostosAux.objects.bulk_create(registros)
            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_comercial_costos_temp(request):
    data = list(PresupuestoComercialCostosAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_comercial_costos_base(request):
    # limpio tabla auxiliar de comercial costos antes de recalcular
    PresupuestoComercialCostosAux.objects.all().delete()
    base_data = Plantillagastos2025.objects.values(
       "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    )
    # filtrar por responsable = 'JEFE COMERCIAL COSTOS'
    base_data = base_data.filter(
    Q(responsable__iexact="COMERCIALES") |
    Q(responsable__iexact="GERARDO y EDUAR")
)
    
    for row in base_data:
        PresupuestoComercialCostosAux.objects.create(
            centro_tra=row["centro_tra"],
            nombre_cen=row["nombre_cen"],
            codcosto=row["codcosto"],
            responsable=row["responsable"],
            cuenta=row["cuenta"],
            cuenta_mayor=row["cuenta_mayor"],
            detalle_cuenta=row["detalle_cuenta"],
            sede_distribucion=row["sede_distribucion"],
            proveedor=row["proveedor"],
            enero=row["enero"],
            febrero=row["febrero"],
            marzo=row["marzo"],
            abril=row["abril"],
            mayo=row["mayo"],
            junio=row["junio"],
            julio=row["julio"], 
            agosto=row["agosto"],
            septiembre=row["septiembre"],
            octubre=row["octubre"],
            noviembre=row["noviembre"],
            diciembre=row["diciembre"],
            total=row["enero"] + row["febrero"] + row["marzo"] + row["abril"] + row["mayo"] + row["junio"] + row["julio"] + row["agosto"] + row["septiembre"] + row["octubre"] + row["noviembre"] + row["diciembre"],
            comentario = ""
        )
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_comercial_costos(request):
    if request.method == "POST":
        version = request.POST.get("version")  # 🔥 versión enviada desde el frontend

        if not version:
            return JsonResponse({"status": "error", "message": "No se especificó la versión"}, status=400)
        # borrar solo la versión seleccionada
        PresupuestoComercialCostos.objects.filter(version=version).delete()
        # 📌 Fecha límite
        fecha_limite = datetime.date(2025, 10, 30)
        if timezone.now().date() <= fecha_limite:
            PresupuestoComercialCostosAprobado.objects.filter(version=version).delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de comercial costos eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#--------------PRESUPUESTO CONTABILIDAD-------------------
@login_required
def presupuesto_contabilidad(request):
    usuarios_permitidos = ['admin', 'CONTABILIDAD']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    # 🔹 obtener versiones disponibles
    versiones = (
        PresupuestoContabilidad.objects
        .values_list("version", flat=True)
        .distinct()
        .order_by("version")
    )
    ultima_version = max(versiones) if versiones else 1
    return render(request, "presupuesto_general/presupuesto_contabilidad.html", {"versiones": versiones, "ultima_version": ultima_version})

def obtener_presupuesto_contabilidad(request):
    version = request.GET.get("version")  #🔥 versión 
    qs = PresupuestoContabilidad.objects.all()
    if version:
        qs = qs.filter(version=version)
    data = list(qs.values())
    return JsonResponse({"data": data}, safe=False)

def presupuesto_aprobado_contabilidad(request):
    # obtener última version disponible
    versiones = (
        PresupuestoContabilidadAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    
    return render(request, "presupuesto_general/presupuesto_aprobado_contabilidad.html", {"ultima_version": ultima_version})

def obtener_presupuesto_aprobado_contabilidad(request):
    # filtrar por la última versión
    versiones = (
        PresupuestoContabilidadAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    qs = PresupuestoContabilidadAprobado.objects.filter(version=ultima_version)
    data = list(qs.values())
    
    return JsonResponse({"data": data}, safe=False)

def tabla_auxiliar_contabilidad(request):
    # 📌 Definir fecha límite
    fecha_limite = datetime.date(2025, 10, 22)  # <-- cámbiala según lo que necesites
    hoy = datetime.date.today()
    # 🚫 Si ya pasó la fecha, negar acceso
    if hoy > fecha_limite:
        return HttpResponseForbidden("⛔ El acceso a esta vista está bloqueado después del "
                                        f"{fecha_limite.strftime('%d/%m/%Y')}")
    # ✅ Si aún no llega la fecha, mostrar vista normal
    return render(request, "presupuesto_general/aux_presupuesto_contabilidad.html")

def subir_presupuesto_contabilidad(request):
    if request.method == "POST":
        temporales = PresupuestoContabilidadAux.objects.all()
        fecha_limite = datetime.date(2025, 10, 30)
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)
        # 📌 Fecha actual
        fecha_hoy = timezone.now().date()
        # 📌 Obtener versión global (tomando la última registrada en la tabla 
        ultima_version = PresupuestoContabilidad.objects.aggregate(max_ver=models.Max("version"))["max_ver"] or 0
        nueva_version = ultima_version + 1
        for temp in temporales:
            # --- Guardar en tabla principal ---
            obj, created = PresupuestoContabilidad.objects.update_or_create(
                id=temp.id,
                defaults={
                    "centro_tra": temp.centro_tra,
                    "nombre_cen": temp.nombre_cen,
                    "codcosto": temp.codcosto,
                    "responsable": temp.responsable,
                    "cuenta": temp.cuenta,  
                    "cuenta_mayor": temp.cuenta_mayor,
                    "detalle_cuenta": temp.detalle_cuenta,
                    "sede_distribucion": temp.sede_distribucion,
                    "proveedor": temp.proveedor,
                    "enero": temp.enero,
                    "febrero": temp.febrero,
                    "marzo": temp.marzo,
                    "abril": temp.abril,
                    "mayo": temp.mayo,
                    "junio": temp.junio,
                    "julio": temp.julio,
                    "agosto": temp.agosto,
                    "septiembre": temp.septiembre,
                    "octubre": temp.octubre,
                    "noviembre": temp.noviembre,
                    "diciembre": temp.diciembre,
                    "total": temp.total,
                    "comentario": temp.comentario,
                    "version": nueva_version,
                    "fecha": fecha_hoy,
                }
            )
            # --- Guardar en tabla aprobada si aplica ---
            if fecha_hoy <= fecha_limite:
                PresupuestoContabilidadAprobado.objects.update_or_create(
                    id=temp.id,
                    defaults={
                        "centro_tra": temp.centro_tra,
                        "nombre_cen": temp.nombre_cen,
                        "codcosto": temp.codcosto,
                        "responsable": temp.responsable,
                        "cuenta": temp.cuenta,
                        "cuenta_mayor": temp.cuenta_mayor,
                        "detalle_cuenta": temp.detalle_cuenta,
                        "sede_distribucion": temp.sede_distribucion,
                        "proveedor": temp.proveedor,
                        "enero": temp.enero,
                        "febrero": temp.febrero,
                        "marzo": temp.marzo,
                        "abril": temp.abril,
                        "mayo": temp.mayo,
                        "junio": temp.junio,
                        "julio": temp.julio,
                        "agosto": temp.agosto,
                        "septiembre": temp.septiembre,
                        "octubre": temp.octubre,
                        "noviembre": temp.noviembre,
                        "diciembre": temp.diciembre,
                        "total": temp.total,
                        "comentario": temp.comentario,
                        "version": nueva_version,
                        "fecha": fecha_hoy,
                    }
                )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de contabilidad actualizado ✅ (versión {nueva_version})"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_contabilidad_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total", "comentario"
            }
            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}
                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo","junio", "julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0
                registros.append(PresupuestoContabilidadAux(**row_filtrado))
            # ✅ Transacción atómica → si algo falla, no se borra nada
            with transaction.atomic():
                # limpio toda la tabla auxiliar antes de insertar
                PresupuestoContabilidadAux.objects.all().delete()
                PresupuestoContabilidadAux.objects.bulk_create(registros)
            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_contabilidad_temp(request):
    data = list(PresupuestoContabilidadAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_contabilidad_base(request):
    # limpio tabla auxiliar de contabilidad antes de recalcular
    PresupuestoContabilidadAux.objects.all().delete()
    base_data = Plantillagastos2025.objects.values(
       "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    )
    # filtrar por responsable = 'JEFE CONTABILIDAD'
    base_data = base_data.filter(responsable__iexact="CONTABILIDAD")
    
    for row in base_data:
        PresupuestoContabilidadAux.objects.create(
            centro_tra=row["centro_tra"],
            nombre_cen=row["nombre_cen"],
            codcosto=row["codcosto"],
            responsable=row["responsable"],
            cuenta=row["cuenta"],
            cuenta_mayor=row["cuenta_mayor"],
            detalle_cuenta=row["detalle_cuenta"],
            sede_distribucion=row["sede_distribucion"],
            proveedor=row["proveedor"],
            enero=row["enero"],
            febrero=row["febrero"],
            marzo=row["marzo"],
            abril=row["abril"],
            mayo=row["mayo"],
            junio=row["junio"],
            julio=row["julio"], 
            agosto=row["agosto"],
            septiembre=row["septiembre"],
            octubre=row["octubre"],
            noviembre=row["noviembre"],
            diciembre=row["diciembre"],
            total=row["enero"] + row["febrero"] + row["marzo"] + row["abril"] + row["mayo"] + row["junio"] + row["julio"] + row["agosto"] + row["septiembre"] + row["octubre"] + row["noviembre"] + row["diciembre"],
            comentario = ""
        )
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_contabilidad(request):
    if request.method == "POST":
        version = request.POST.get("version")  # 🔥 versión enviada desde el frontend

        if not version:
            return JsonResponse({"status": "error", "message": "No se especificó la versión"}, status=400)
        # borrar solo la versión seleccionada
        PresupuestoContabilidad.objects.filter(version=version).delete()
        # 📌 Fecha límite
        fecha_limite = datetime.date(2025, 10, 30)
        if timezone.now().date() <= fecha_limite:
            PresupuestoContabilidadAprobado.objects.filter(version=version).delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de contabilidad eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

#-------------PRESUPUESTO GERENCIA---------------------------
@login_required
def presupuesto_gerencia(request):
    usuarios_permitidos = ['admin', 'GERENCIA']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    # 🔹 obtener versiones disponibles
    versiones = (
        PresupuestoGerencia.objects
        .values_list("version", flat=True)
        .distinct()
        .order_by("version")
    )
    ultima_version = max(versiones) if versiones else 1
    return render(request, "presupuesto_general/presupuesto_gerencia.html", {"versiones": versiones, "ultima_version": ultima_version})

def obtener_presupuesto_gerencia(request):
    version = request.GET.get("version")  #🔥 versión 
    qs = PresupuestoGerencia.objects.all()
    if version:
        qs = qs.filter(version=version)
    data = list(qs.values())
    return JsonResponse({"data": data}, safe=False)

def presupuesto_aprobado_gerencia(request):
    # obtener última version disponible
    versiones = (
        PresupuestoGerenciaAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    
    return render(request, "presupuesto_general/presupuesto_aprobado_gerencia.html", {"ultima_version": ultima_version})

def obtener_presupuesto_aprobado_gerencia(request):
    # filtrar por la última versión
    versiones = (
        PresupuestoGerenciaAprobado.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    qs = PresupuestoGerenciaAprobado.objects.filter(version=ultima_version)
    data = list(qs.values())
    
    return JsonResponse({"data": data}, safe=False)

def tabla_auxiliar_gerencia(request):
    # 📌 Definir fecha límite
    fecha_limite = datetime.date(2025, 10, 16)  # <-- cámbiala según lo que necesites
    hoy = datetime.date.today()
    # 🚫 Si ya pasó la fecha, negar acceso
    if hoy > fecha_limite:
        return HttpResponseForbidden("⛔ El acceso a esta vista está bloqueado después del "
                                        f"{fecha_limite.strftime('%d/%m/%Y')}")
    # ✅ Si aún no llega la fecha, mostrar vista normal
    return render(request, "presupuesto_general/aux_presupuesto_gerencia.html")

def subir_presupuesto_gerencia(request):
    if request.method == "POST":
        temporales = PresupuestoGerenciaAux.objects.all()
        fecha_limite = datetime.date(2025, 10, 30)
        if not temporales.exists():
            return JsonResponse({
                "success": False,
                "msg": "No hay datos temporales para subir ❌"
            }, status=400)
        # 📌 Fecha actual
        fecha_hoy = timezone.now().date()
        # 📌 Obtener versión global (tomando la última registrada en la tabla 
        ultima_version = PresupuestoGerencia.objects.aggregate(max_ver=models.Max("version"))["max_ver"] or 0
        nueva_version = ultima_version + 1
        for temp in temporales:
            # --- Guardar en tabla principal ---
            obj, created = PresupuestoGerencia.objects.update_or_create(
                id=temp.id,
                defaults={
                    "centro_tra": temp.centro_tra,
                    "nombre_cen": temp.nombre_cen,
                    "codcosto": temp.codcosto,
                    "responsable": temp.responsable,
                    "cuenta": temp.cuenta,  
                    "cuenta_mayor": temp.cuenta_mayor,
                    "detalle_cuenta": temp.detalle_cuenta,
                    "sede_distribucion": temp.sede_distribucion,
                    "proveedor": temp.proveedor,
                    "enero": temp.enero,
                    "febrero": temp.febrero,
                    "marzo": temp.marzo,
                    "abril": temp.abril,
                    "mayo": temp.mayo,
                    "junio": temp.junio,
                    "julio": temp.julio,
                    "agosto": temp.agosto,
                    "septiembre": temp.septiembre,
                    "octubre": temp.octubre,
                    "noviembre": temp.noviembre,
                    "diciembre": temp.diciembre,
                    "total": temp.total,
                    "comentario": temp.comentario,
                    "version": nueva_version,
                    "fecha": fecha_hoy,
                }
            )
            # --- Guardar en tabla aprobada si aplica ---
            if fecha_hoy <= fecha_limite:
                PresupuestoGerenciaAprobado.objects.update_or_create(
                    id=temp.id,
                    defaults={
                        "centro_tra": temp.centro_tra,
                        "nombre_cen": temp.nombre_cen,
                        "codcosto": temp.codcosto,
                        "responsable": temp.responsable,
                        "cuenta": temp.cuenta,
                        "cuenta_mayor": temp.cuenta_mayor,
                        "detalle_cuenta": temp.detalle_cuenta,
                        "sede_distribucion": temp.sede_distribucion,
                        "proveedor": temp.proveedor,
                        "enero": temp.enero,
                        "febrero": temp.febrero,
                        "marzo": temp.marzo,
                        "abril": temp.abril,
                        "mayo": temp.mayo,
                        "junio": temp.junio,
                        "julio": temp.julio,
                        "agosto": temp.agosto,
                        "septiembre": temp.septiembre,
                        "octubre": temp.octubre,
                        "noviembre": temp.noviembre,
                        "diciembre": temp.diciembre,
                        "total": temp.total,
                        "comentario": temp.comentario,
                        "version": nueva_version,   
                        "fecha": fecha_hoy,
                    }
                )
        return JsonResponse({
            "success": True,
            "msg": f"Presupuesto de gerencia actualizado ✅ (versión {nueva_version})"
        })
    return JsonResponse({
        "success": False,
        "msg": "Método no permitido"
    }, status=405)
    
def guardar_gerencia_temp(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            # Definir los campos válidos en el modelo temporal
            campos_validos = {
                "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total", "comentario"
            }
            registros = []
            for row in data:
                # Filtrar solo los campos válidos
                row_filtrado = {k: row.get(k) for k in campos_validos}
                # Reemplazar None por 0 en numéricos
                for mes in [
                    "enero","febrero","marzo","abril","mayo","junio", "julio","agosto","septiembre","octubre",
                    "noviembre","diciembre","total"
                ]:
                    if row_filtrado.get(mes) in [None, ""]:
                        row_filtrado[mes] = 0
                registros.append(PresupuestoGerenciaAux(**row_filtrado))
            # ✅ Transacción atómica → si algo falla, no se borra nada
            with transaction.atomic():
                # limpio toda la tabla auxiliar antes de insertar
                PresupuestoGerenciaAux.objects.all().delete()
                PresupuestoGerenciaAux.objects.bulk_create(registros)
            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

def obtener_gerencia_temp(request):
    data = list(PresupuestoGerenciaAux.objects.values())
    return JsonResponse(data, safe=False)

def cargar_gerencia_base(request):
    # limpio tabla auxiliar de gerencia antes de recalcular
    PresupuestoGerenciaAux.objects.all().delete()
    base_data = Plantillagastos2025.objects.values(
       "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    )
    # filtrar por responsable = 'GERENCIA'
    base_data = base_data.filter(responsable__iexact="GERENCIA")
    
    for row in base_data:
        PresupuestoGerenciaAux.objects.create(
            centro_tra=row["centro_tra"],
            nombre_cen=row["nombre_cen"],
            codcosto=row["codcosto"],
            responsable=row["responsable"],
            cuenta=row["cuenta"],
            cuenta_mayor=row["cuenta_mayor"],
            detalle_cuenta=row["detalle_cuenta"],
            sede_distribucion=row["sede_distribucion"],
            proveedor=row["proveedor"],
            enero=row["enero"],
            febrero=row["febrero"],
            marzo=row["marzo"],
            abril=row["abril"],
            mayo=row["mayo"],
            junio=row["junio"],
            julio=row["julio"], 
            agosto=row["agosto"],
            septiembre=row["septiembre"],
            octubre=row["octubre"],
            noviembre=row["noviembre"],
            diciembre=row["diciembre"],
            total=row["enero"] + row["febrero"] + row["marzo"] + row["abril"] + row["mayo"] + row["junio"] + row["julio"] + row["agosto"] + row["septiembre"] + row["octubre"] + row["noviembre"] + row["diciembre"],
            comentario = ""
        )
    return JsonResponse({"status": "ok"})

@csrf_exempt
def borrar_presupuesto_gerencia(request):
    if request.method == "POST":
        version = request.POST.get("version")  # 🔥 versión enviada desde el frontend

        if not version:
            return JsonResponse({"status": "error", "message": "No se especificó la versión"}, status=400)
        # borrar solo la versión seleccionada
        PresupuestoGerencia.objects.filter(version=version).delete()
        # 📌 Fecha límite
        fecha_limite = datetime.date(2025, 10, 30)
        if timezone.now().date() <= fecha_limite:
            PresupuestoGerenciaAprobado.objects.filter(version=version).delete()
        return JsonResponse({"status": "ok", "message": "Presupuesto de gerencia eliminado"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)


#--------------------PRESUPUESTO CONSOLIDADO-----------------------
def presupuesto_consolidado(request, area):
    templates = {
        'almacen-buga': 'presupuesto_consolidado/presupuesto_almacen_buga.html',
        'almacen-cali': 'presupuesto_consolidado/presupuesto_almacen_cali.html',
        'almacen-cartago': 'presupuesto_consolidado/presupuesto_almacen_cartago.html',
        'almacen-tulua': 'presupuesto_consolidado/presupuesto_almacen_tulua.html',
        'comercial-costos': 'presupuesto_consolidado/presupuesto_comercial_costos.html',
        'comunicaciones': 'presupuesto_consolidado/presupuesto_comunicaciones.html',
        'contabilidad': 'presupuesto_consolidado/presupuesto_contabilidad.html',
        'gerencia': 'presupuesto_consolidado/presupuesto_gerencia.html',
        'gestion-riesgos': 'presupuesto_consolidado/presupuesto_gestion_riesgos.html',
        'gh': 'presupuesto_consolidado/presupuesto_GH.html',
        'logistica': 'presupuesto_consolidado/presupuesto_logistica.html',
        'ocupacional': 'presupuesto_consolidado/presupuesto_ocupacional.html',
        'servicios-tecnicos': 'presupuesto_consolidado/presupuesto_servicios_tecnicos.html',
        'tecnologia': 'presupuesto_consolidado/presupuesto_tecnologia.html',
        
    }

    template = templates.get(area)
    if not template:
        return HttpResponseForbidden("⛔ Área no válida.")

    return render(request, template)

def obtener_presupuesto_consolidado(request, area):
    modelos = {
        'almacen-buga': PresupuestoAlmacenBugaAprobado, 
        'almacen-cali': PresupuestoAlmacenCaliAprobado,
        'almacen-cartago': PresupuestoAlmacenCartagoAprobado,
        'almacen-tulua': PresupuestoAlmacenTuluaAprobado,
        'comercial-costos': PresupuestoComercialCostosAprobado,
        'comunicaciones': PresupuestoComunicacionesAprobado,    
        'contabilidad': PresupuestoContabilidadAprobado,
        'gerencia': PresupuestoGerenciaAprobado,
        'gestion-riesgos': PresupuestoGestionRiesgosAprobado,
        'gh': PresupuestoGHAprobado,
        'logistica': PresupuestoLogisticaAprobado,
        'ocupacional': PresupuestoOcupacionalAprobado,
        'servicios-tecnicos': PresupuestoServiciosTecnicosAprobado,
        'tecnologia': PresupuestotecnologiaAprobado,
    }
    modelo = modelos.get(area)
    if not modelo:
        return HttpResponseForbidden("⛔ Área no válida.")
    # filtrar por la última versión
    versiones = (
        modelo.objects
        .values_list("version", flat=True)
        .distinct()
    )
    ultima_version = max(versiones) if versiones else 1
    qs = modelo.objects.filter(version=ultima_version)
    data = list(qs.values())
    return JsonResponse({"data": data}, safe=False)

def guardar_presupuesto_consolidado(request, area):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

    try:
        # Cargar datos enviados
        data = json.loads(request.body.decode("utf-8"))

        # Campos comunes válidos
        campos_validos = {
            "centro_tra", "nombre_cen", "codcosto", "responsable",
            "cuenta", "cuenta_mayor", "detalle_cuenta", "sede_distribucion", 
            "proveedor", "enero", "febrero", "marzo", "abril", "mayo", "junio", 
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", 
            "total", "comentario"
        }

        # Diccionario: área → modelo correspondiente
        modelos = {
            'almacen-buga': PresupuestoAlmacenBugaAprobado, 
            'almacen-cali': PresupuestoAlmacenCaliAprobado,
            'almacen-cartago': PresupuestoAlmacenCartagoAprobado,
            'almacen-tulua': PresupuestoAlmacenTuluaAprobado,
            'comercial-costos': PresupuestoComercialCostosAprobado,
            'comunicaciones': PresupuestoComunicacionesAprobado,
            'contabilidad': PresupuestoContabilidadAprobado,
            'gerencia': PresupuestoGerenciaAprobado,
            'gestion-riesgos': PresupuestoGestionRiesgosAprobado,
            'gh': PresupuestoGHAprobado,
            'logistica': PresupuestoLogisticaAprobado,
            'ocupacional': PresupuestoOcupacionalAprobado,
            'servicios-tecnicos': PresupuestoServiciosTecnicosAprobado,
            'tecnologia': PresupuestotecnologiaAprobado,
        }

        modelo = modelos.get(area)
        if not modelo:
            return HttpResponseForbidden("⛔ Área no válida.")

        registros = []
        for row in data:
            row_filtrado = {k: row.get(k) for k in campos_validos}

            # Reemplazar None o vacío por 0 en numéricos
            for mes in [
                "enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre", "total"
            ]:
                if row_filtrado.get(mes) in [None, ""]:
                    row_filtrado[mes] = 0

            registros.append(modelo(**row_filtrado))

        # Guardar dentro de una transacción
        with transaction.atomic():
            modelo.objects.all().delete()  # Limpia tabla auxiliar del área
            modelo.objects.bulk_create(registros)

        return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)
    

#---------------------Obtener, editar y guardar cuanta 5--------------
@login_required
def cuenta5(request):
    usuarios_permitidos = ['admin', 'NICOLAS']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    return render(request, "presupuesto_consolidado/cuenta5.html")

@csrf_exempt
def obtener_cuenta5_base(request):
    try:
        params = request.POST or request.GET  # funciona con ambos métodos
        draw = int(params.get('draw') or 1)
        start = int(params.get('start') or 0)
        length = int(params.get('length') or 50)

        queryset = Cuenta5Base.objects.all()
        total = queryset.count()

        paginator = Paginator(queryset, length)
        page_number = start // length + 1
        page = paginator.get_page(page_number)

        data = list(page.object_list.values())

        return JsonResponse({
            'draw': draw,
            'recordsTotal': total,
            'recordsFiltered': total,
            'data': data
        })

    except Exception as e:
        print(f"❌ Error en obtener_cuenta5_base: {e}")
        return JsonResponse({'error': str(e)}, status=500) 
def cargar_cuenta5_base(request):
    # limpio tabla cuenta 5 antes de recalcular
    Cuenta5Base.objects.all().delete()
    base_data = Cuenta5.objects.values("mcncuenta", "mcnfecha", "mcntipodoc", "mcnnumedoc", "mcnvincula", "vinnombre", "mcnvaldebi", "mcnvalcred", "saldonew", "mcnsucurs", "mcnccosto", "mcndestino", "mcndetalle", "mcnzona", "cconombre", "dnonombre", "zonnombre", "mcnempresa", "mcnclase", "mcnvinkey", "tpreg", "ctanombre", "docdetalle", "infdetalle")
    for row in base_data:   
        Cuenta5Base.objects.create(
            mcncuenta=row["mcncuenta"],
            mcnfecha=row["mcnfecha"],
            mcntipodoc=row["mcntipodoc"],
            mcnnumedoc=row["mcnnumedoc"],
            mcnvincula=row["mcnvincula"],
            vinnombre=row["vinnombre"],
            mcnvaldebi=row["mcnvaldebi"],
            mcnvalcred=row["mcnvalcred"],
            saldonew=row["saldonew"],
            mcnsucurs=row["mcnsucurs"],
            mcnccosto=row["mcnccosto"],
            mcndestino=row["mcndestino"],
            mcndetalle=row["mcndetalle"],
            mcnzona=row["mcnzona"],
            cconombre=row["cconombre"],
            dnonombre=row["dnonombre"],
            zonnombre=row["zonnombre"],
            mcnempresa=row["mcnempresa"],
            mcnclase=row["mcnclase"],
            mcnvinkey=row["mcnvinkey"],
            tpreg=row["tpreg"],
            ctanombre=row["ctanombre"],
            docdetalle=row["docdetalle"],
            infdetalle=row["infdetalle"],
        )
    return JsonResponse({"status": "ok", "msg": f"{base_data.count()} filas cargadas desde la base ✅"})

def guardar_cuenta5(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            registros = []
            for row in data:
                registros.append(Cuenta5Base(
                    mcncuenta=row.get("mcncuenta"),
                    mcnfecha=row.get("mcnfecha"),
                    mcntipodoc=row.get("mcntipodoc"),
                    mcnnumedoc=row.get("mcnnumedoc"),
                    mcnvincula=row.get("mcnvincula"),
                    vinnombre=row.get("vinnombre"),
                    mcnvaldebi=row.get("mcnvaldebi") or 0,
                    mcnvalcred=row.get("mcnvalcred") or 0,
                    saldonew=row.get("saldonew") or 0,
                    mcnsucurs=row.get("mcnsucurs"),
                    mcncosto=row.get("mcncosto"),
                    mcndestino=row.get("mcndestino"),
                    mcndetalle=row.get("mcndetalle"),
                    mcnzona=row.get("mcnzona"),
                    cconombre=row.get("cconombre"),
                    dnonombre=row.get("dnonombre"),
                    zonnombre=row.get("zonnombre"),
                    mcnempresa=row.get("mcnempresa"),
                    mcnclase=row.get("mcnclase"),
                    mcnvinkey=row.get("mcnvinkey"),
                    tpreg=row.get("tpreg"),
                    ctanombre=row.get("ctanombre"),
                    docdetalle=row.get("docdetalle"),
                    infdetalle=row.get("infdetalle"),
                ))
            # ✅ Transacción atómica → si algo falla, no se borra nada
            with transaction.atomic():
                Cuenta5Base.objects.all().delete()
                Cuenta5Base.objects.bulk_create(registros)
            return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

@csrf_exempt
def subir_excel_cuenta5(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            registros = data.get("registros", [])
            insertados = 0

            with transaction.atomic():
                for r in registros:
                    Cuenta5Base.objects.create(**r)
                    insertados += 1

            return JsonResponse({"status": "ok", "insertados": insertados})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    else:
        return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

@csrf_exempt
def borrar_cuenta5_base(request):
    if request.method == "POST":
        Cuenta5Base.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Datos de cuenta 5 eliminados"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

