from collections import defaultdict
import datetime
from decimal import Decimal, ROUND_DOWN
from itertools import chain
from pyexpat.errors import messages
import re
import unicodedata
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
import pandas as pd
from .models import BdVentas2020, BdVentas2021, BdVentas2022, BdVentas2023, BdVentas2024, BdVentas2025, BdVentasComercial, ComentarioComparativo, Cuenta4Base, Cuenta4Presupuestado, OrdenCuenta, ParametrosPresupuestos, PresupuestoSueldos, PresupuestoSueldosAux, ConceptosFijosYVariables, PresupuestoComisiones, PresupuestoComisionesAux, PresupuestoHorasExtra, PresupuestoHorasExtraAux, PresupuestoMediosTransporte, PresupuestoMediosTransporteAux, PresupuestoAuxilioTransporte, PresupuestoAuxilioTransporteAux, PresupuestoAyudaTransporte, PresupuestoAyudaTransporteAux, PresupuestoCesantias, PresupuestoCesantiasAux, PresupuestoPrima, PresupuestoPrimaAux, PresupuestoVacaciones, PresupuestoVacacionesAux, PresupuestoBonificaciones, PresupuestoBonificacionesAux, PresupuestoAprendiz, PresupuestoAprendizAux, PresupuestoBolsaConsumibles, PresupuestoBolsaConsumiblesAux, PresupuestoAuxilioTBCKIT, PresupuestoAuxilioTCBKITAux, PresupuestoSeguridadSocial, PresupuestoSeguridadSocialAux, PresupuestoInteresesCesantias, PresupuestoInteresesCesantiasAux, PresupuestoBonificacionesFoco, PresupuestoBonificacionesFocoAux, PresupuestoAuxilioEducacion, PresupuestoAuxilioEducacionAux, ConceptoAuxilioEducacion, PresupuestoBonosKyrovet, PresupuestoBonosKyrovetAux, PresupuestoGeneralVentas, PresupuestoCentroOperacionVentas, PresupuestoCentroSegmentoVentas, PresupuestoGeneralCostos, PresupuestoCentroOperacionCostos, PresupuestoCentroSegmentoCostos, PresupuestoComercial, Plantillagastos2025, PresupuestoTecnologia, PresupuestoTecnologiaAux, CuentasContables, PresupuestotecnologiaAprobado, PresupuestoOcupacional, PresupuestoOcupacionalAux, PresupuestoOcupacionalAprobado, PresupuestoServiciosTecnicos, PresupuestoServiciosTecnicosAux, PresupuestoServiciosTecnicosAprobado, PresupuestoLogistica, PresupuestoLogisticaAux, PresupuestoLogisticaAprobado, PresupuestoGestionRiesgos, PresupuestoGestionRiesgosAux, PresupuestoGestionRiesgosAprobado, PresupuestoGH, PresupuestoGHAux, PresupuestoGHAprobado, PresupuestoAlmacenTulua, PresupuestoAlmacenTuluaAux, PresupuestoAlmacenTuluaAprobado, PresupuestoAlmacenBuga, PresupuestoAlmacenBugaAux, PresupuestoAlmacenBugaAprobado, PresupuestoAlmacenCartago, PresupuestoAlmacenCartagoAux, PresupuestoAlmacenCartagoAprobado, PresupuestoAlmacenCali, PresupuestoAlmacenCaliAux, PresupuestoAlmacenCaliAprobado, PresupuestoComunicaciones, PresupuestoComunicacionesAux, PresupuestoComunicacionesAprobado, PresupuestoComercialCostos, PresupuestoComercialCostosAux, PresupuestoComercialCostosAprobado, PresupuestoContabilidad, PresupuestoContabilidadAux, PresupuestoContabilidadAprobado, PresupuestoGerencia, PresupuestoGerenciaAux, PresupuestoGerenciaAprobado, Cuenta5, Cuenta5Base, PresupuestoCentroSegLineaCostos, PresupuestoCentroSegLineaVentas, ConsolidadoTotalBase, Cuenta5Presupuestado
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
import calendar
from django.db.models.functions import ExtractMonth, ExtractYear
from django.views.decorators.http import require_http_methods, require_GET, require_POST

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
    salud_ocupacional = PresupuestoOcupacionalAprobado.objects.values()
    
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
    salud_ocupacional = salud_ocupacional.filter(version=salud_ocupacional.aggregate(Max('version'))['version__max'])
    
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
    df_salud_ocupacional = prepare_df(salud_ocupacional, "Salud Ocupacional")
    
    # Concatenar todos en un solo DataFrame
    df_final = pd.concat(
        [df_tecnologia, df_servicios_tecnicos, df_logistica, df_gestion_riesgos, df_gh, df_almacen_tulua, df_almacen_buga, df_almacen_cartago, df_almacen_cali, df_comunicaciones, df_comercial_costos, df_contabilidad, df_gerencia, df_salud_ocupacional],
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

# --------------COMERCIAL------------------------------------
# Las vistas "por línea" (centro+segmento+línea) y el cálculo de
# participación mensual solo usaban BdVentas2025 a propósito (ver
# BUGS_Y_MEJORAS.md 2.13). Con la tabla consolidada, ese mismo criterio
# se aplica como un filtro de año — se deja como constante para que sea
# fácil de cambiar en un solo lugar si el negocio decide usar más años.
def _anio_detalle_linea():
    """Año del detalle por línea. Antes era una constante evaluada al
    importar el módulo, así que no cambiaba al cruzar de año."""
    return timezone.now().year

# ----------------------------------------------------------------------
# Mapeo fijo de código de centro de operación (columna MCNZONA del
# Excel) -> nombre de almacén. Si se abre un nuevo almacén, agregarlo
# aquí — es el único lugar que hay que tocar.
# ----------------------------------------------------------------------
NOMBRES_CENTRO_OPERACION = {
    1: 'ALMACEN TULUA',
    2: 'ALMACEN BUGA',
    3: 'ALMACEN CARTAGO',
    4: 'ALMACEN CALI',
}

# Columnas que debe tener el Excel para poder procesarlo (en mayúsculas,
# como vienen en el archivo de ejemplo).
COLUMNAS_REQUERIDAS = [
    'YYYY', 'MM', 'MCNZONA', 'LINNOMBRE', 'VGRNOMBRE', 'SUBTOTAL', 'COSTO_VTA',
    'VENCEDULA', 'MCNPRODUCT',
]

# --------------------------------------------------------------------
# Reglas de depuración: filas que se descartan ANTES de calcular nada.
# --------------------------------------------------------------------
CEDULA_EXCLUIDA = 1116235756
PRODUCTOS_EXCEPCION_S = {'S4', 'S909'}


def _depurar_dataframe(df):
    """
    Aplica las reglas de depuración del Excel antes de cualquier
    transformación o consolidación:

      1) Elimina filas donde VENCEDULA == 1116235756.
      2) Elimina filas donde MCNPRODUCT empieza con 'S', salvo que sea
         exactamente 'S4' o 'S909'.

    Devuelve (df_depurado, resumen) donde `resumen` es un dict con la
    cantidad de filas eliminadas por cada regla, para informarlas en la
    respuesta.
    """
    resumen = {}

    # 1) VENCEDULA == 1116235756 (puede venir como texto o número en el Excel)
    vencedula_num = pd.to_numeric(df['VENCEDULA'], errors='coerce')
    mascara_cedula = vencedula_num == CEDULA_EXCLUIDA
    resumen['eliminados_por_cedula'] = int(mascara_cedula.sum())
    df = df[~mascara_cedula]

    # 2) MCNPRODUCT que empieza con 'S', excepto 'S4' y 'S909'
    producto = df['MCNPRODUCT'].astype(str).str.strip().str.upper()
    mascara_producto = producto.str.startswith('S') & ~producto.isin(PRODUCTOS_EXCEPCION_S)
    resumen['eliminados_por_producto_s'] = int(mascara_producto.sum())
    df = df[~mascara_producto]

    resumen['filas_restantes'] = len(df)
    return df, resumen


def _parsear_numero_co(valor):
    """
    El Excel trae los valores numéricos en formato colombiano/europeo
    como texto: '.' para miles y ',' para decimales
    (p. ej. "-93.626,00" -> -93626.00). Esta función los convierte a
    float sin importar si pandas ya los interpretó como número o los
    dejó como texto.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip()
    if texto == '':
        return 0.0
    texto = texto.replace('.', '').replace(',', '.')
    try:
        return float(texto)
    except ValueError:
        return 0.0


def _nombre_centro_operacion(codigo):
    """1 -> ALMACEN TULUA, 2 -> ALMACEN BUGA, 3 -> ALMACEN CARTAGO, 4 -> ALMACEN CALI."""
    try:
        codigo_int = int(codigo)
    except (TypeError, ValueError):
        return None
    return NOMBRES_CENTRO_OPERACION.get(codigo_int)


def _convertir_clase_cliente(valor):
    """
    CLIENTE -> CLIENTES, PRODUCCION -> PRODUCTOR (no distingue
    mayúsculas/minúsculas ni espacios extra). Cualquier otro valor se
    conserva tal cual (recortado), para no perder datos silenciosamente
    si el Excel trae una categoría distinta a las dos esperadas.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    texto = str(valor).strip()
    texto_normalizado = texto.upper()
    if texto_normalizado == 'CLIENTE':
        return 'CLIENTES'
    if texto_normalizado == 'PRODUCCION':
        return 'PRODUCTOR'
    return texto

def _lapso_actual():
    """Lapso (AAAAMM) del mes en curso. Todo lapso >= a este se considera incompleto."""
    hoy = timezone.now()
    return hoy.year * 100 + hoy.month

def _replicar_meses_faltantes(anio):
    """
    Completa el año `anio` copiando los registros del mismo mes del año
    anterior (mismo centro, nombre_linea_n1 y nombre_clase_cliente).

    Se regeneran siempre los meses >= al mes en curso (el actual y los
    futuros, que nunca tienen dato real) y además cualquier mes anterior
    que haya quedado sin ningún registro.
    """
    lapso_corte = _lapso_actual()
    lapsos_anio = [anio * 100 + m for m in range(1, 13)]

    con_datos = set(
        BdVentasComercial.objects
        .filter(lapso__in=lapsos_anio)
        .values_list('lapso', flat=True)
    )
    objetivo = [l for l in lapsos_anio if l >= lapso_corte or l not in con_datos]
    if not objetivo:
        return {}

    # Se borra lo que haya en esos meses (replicas viejas) y se regenera.
    BdVentasComercial.objects.filter(lapso__in=objetivo).delete()

    nuevos, resumen = [], {}
    for lapso in objetivo:
        base = list(BdVentasComercial.objects.filter(lapso=lapso - 100))
        resumen[lapso] = len(base)
        for r in base:
            nuevos.append(BdVentasComercial(
                lapso=lapso,
                centro_de_operacion=r.centro_de_operacion,
                nombre_centro_de_operacion=r.nombre_centro_de_operacion,
                nombre_linea_n1=r.nombre_linea_n1,
                nombre_clase_cliente=r.nombre_clase_cliente,
                valor_neto=r.valor_neto,
                valor_costo=r.valor_costo,
            ))

    if nuevos:
        BdVentasComercial.objects.bulk_create(nuevos, batch_size=1000)
    return resumen

# importar ventas comercial
@csrf_exempt
def importar_bd_ventas_comercial(request):
    """
    Recibe el Excel de ventas detalladas, lo depura/transforma según
    las reglas de negocio, lo consolida por año+mes+centro+línea+segmento
    y reemplaza en `BdVentasComercial` los meses (lapsos) que vengan en
    el archivo (para poder re-subir un Excel corregido sin duplicar).
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido'}, status=405)

    archivo = request.FILES.get('file')
    if not archivo:
        return JsonResponse({'status': 'error', 'mensaje': 'No se recibió ningún archivo'}, status=400)

    try:
        df = pd.read_excel(archivo)
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': f'No se pudo leer el archivo: {e}'}, status=400)

    # Normalizar encabezados (por si vienen con espacios o en minúsculas)
    df.columns = [str(c).strip().upper() for c in df.columns]

    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
    if faltantes:
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Faltan columnas en el Excel: {", ".join(faltantes)}',
        }, status=400)

    filas_leidas = len(df)
    if filas_leidas == 0:
        return JsonResponse({'status': 'error', 'mensaje': 'El archivo no tiene filas'}, status=400)

    # --------------------------------------------------------------
    # 0) Depurar ANTES de calcular nada: quitar la cédula excluida y
    #    los productos "S..." que no están en la lista de excepciones.
    # --------------------------------------------------------------
    df, resumen_depuracion = _depurar_dataframe(df)

    if len(df) == 0:
        return JsonResponse({
            'status': 'error',
            'mensaje': (
                f'Después de depurar (cédula excluida: {resumen_depuracion["eliminados_por_cedula"]}, '
                f'productos "S" excluidos: {resumen_depuracion["eliminados_por_producto_s"]}) '
                'no quedó ninguna fila para procesar.'
            ),
        }, status=400)

    # --------------------------------------------------------------
    # 1) lapso = año*100 + mes (junta YYYY y MM del Excel, igual
    #    formato que ya usa el resto del sistema).
    # --------------------------------------------------------------
    df['lapso'] = (
        pd.to_numeric(df['YYYY'], errors='coerce').fillna(0).astype(int) * 100
        + pd.to_numeric(df['MM'], errors='coerce').fillna(0).astype(int)
    )
    # --------------------------------------------------------------
    # 1.b) Descartar meses incompletos: solo se importan lapsos
    #      ANTERIORES al mes en curso (el mes actual todavía no cerró).
    # --------------------------------------------------------------
    lapso_corte = _lapso_actual()
    mascara_incompletos = df['lapso'] >= lapso_corte
    lapsos_descartados = sorted(int(l) for l in df.loc[mascara_incompletos, 'lapso'].unique())
    filas_descartadas_por_mes = int(mascara_incompletos.sum())
    df = df[~mascara_incompletos]

    if len(df) == 0:
        return JsonResponse({
            'status': 'error',
            'mensaje': (
                f'Todas las filas quedaron fuera: el archivo solo trae meses '
                f'incompletos ({lapsos_descartados}). Solo se importan meses '
                f'cerrados (hasta {lapso_corte - 1 if lapso_corte % 100 > 1 else (lapso_corte // 100 - 1) * 100 + 12}).'
            ),
        }, status=400)
    # --------------------------------------------------------------
    # 2) centro_de_operacion = MCNZONA
    # 3) nombre_centro_de_operacion = mapeo fijo 1-4
    # --------------------------------------------------------------
    df['centro_de_operacion'] = pd.to_numeric(df['MCNZONA'], errors='coerce')
    df['nombre_centro_de_operacion'] = df['centro_de_operacion'].apply(_nombre_centro_operacion)

    # --------------------------------------------------------------
    # 4) nombre_linea_n1 = LINNOMBRE
    # --------------------------------------------------------------
    df['nombre_linea_n1'] = df['LINNOMBRE'].astype(str).str.strip()

    # --------------------------------------------------------------
    # 5) nombre_clase_cliente = VGRNOMBRE, con la conversión pedida
    # --------------------------------------------------------------
    df['nombre_clase_cliente'] = df['VGRNOMBRE'].apply(_convertir_clase_cliente)

    # --------------------------------------------------------------
    # 6) valor_neto = SUBTOTAL   7) valor_costo = COSTO_VTA
    # --------------------------------------------------------------
    df['valor_neto'] = df['SUBTOTAL'].apply(_parsear_numero_co)
    df['valor_costo'] = df['COSTO_VTA'].apply(_parsear_numero_co)

    # Filas cuyo código de centro no está en el mapeo 1-4: se importan
    # igual (para no perder ventas), pero se informan al usuario.
    centros_sin_mapear = sorted(
        df.loc[df['nombre_centro_de_operacion'].isna(), 'centro_de_operacion'].dropna().unique().tolist()
    )

    # --------------------------------------------------------------
    # 8) Consolidar por año+mes (lapso). El Excel viene detallado por
    #    año/mes/día y documento; aquí se resume a un registro por
    #    lapso+centro+línea+segmento, que es como trabaja el resto
    #    del sistema.
    # --------------------------------------------------------------
    columnas_agrupacion = [
        'lapso', 'centro_de_operacion', 'nombre_centro_de_operacion',
        'nombre_linea_n1', 'nombre_clase_cliente',
    ]
    df_consolidado = (
        df.groupby(columnas_agrupacion, dropna=False)[['valor_neto', 'valor_costo']]
        .sum()
        .reset_index()
    )

    lapsos_importados = sorted(int(l) for l in df_consolidado['lapso'].unique().tolist())

    # Reemplaza los datos existentes de esos mismos meses (evita
    # duplicar si se vuelve a subir el mismo Excel, o una versión
    # corregida del mismo mes), en una transacción atómica para no
    # dejar la tabla a medias si algo falla a mitad de camino.
    with transaction.atomic():
        BdVentasComercial.objects.filter(lapso__in=lapsos_importados).delete()
        BdVentasComercial.objects.bulk_create([
            BdVentasComercial(
                lapso=int(row['lapso']),
                centro_de_operacion=(
                    int(row['centro_de_operacion']) if pd.notna(row['centro_de_operacion']) else None
                ),
                nombre_centro_de_operacion=row['nombre_centro_de_operacion'],
                nombre_linea_n1=row['nombre_linea_n1'],
                nombre_clase_cliente=row['nombre_clase_cliente'],
                valor_neto=float(row['valor_neto']),
                valor_costo=float(row['valor_costo']),
            )
            for _, row in df_consolidado.iterrows()
        ])
        # Completar el año con la copia del año anterior
        anio_objetivo = lapso_corte // 100
        resumen_replica = _replicar_meses_faltantes(anio_objetivo)

    mensaje = (
        f"✅ {filas_leidas} filas leídas del Excel. Depuración: "
        f"{resumen_depuracion['eliminados_por_cedula']} eliminada(s) por cédula excluida, "
        f"{resumen_depuracion['eliminados_por_producto_s']} eliminada(s) por producto 'S...' "
        f"(quedaron {resumen_depuracion['filas_restantes']} filas). "
        f"Consolidadas en {len(df_consolidado)} registros para los meses {lapsos_importados}."
    )
    if centros_sin_mapear:
        mensaje += (
            f" ⚠️ Hay {len(centros_sin_mapear)} código(s) de centro de operación "
            f"sin nombre asignado: {centros_sin_mapear}. Esas filas se importaron "
            f"sin 'nombre_centro_de_operacion' — revisar NOMBRES_CENTRO_OPERACION "
            f"si corresponden a un almacén nuevo."
        )
    if filas_descartadas_por_mes:
        mensaje += (
            f" ⏭️ Se ignoraron {filas_descartadas_por_mes} fila(s) de meses "
            f"incompletos {lapsos_descartados} (solo se cargan meses cerrados)."
        )
    if resumen_replica:
        detalle = ", ".join(f"{l}: {n}" for l, n in sorted(resumen_replica.items()))
        mensaje += f" 🔁 Meses completados con datos del año anterior → {detalle}."

    return JsonResponse({
        'status': 'ok',
        'mensaje': mensaje,
        'filas_leidas': filas_leidas,
        'depuracion': resumen_depuracion,
        'registros_consolidados': len(df_consolidado),
        'lapsos': lapsos_importados,
        'centros_sin_mapear': centros_sin_mapear,
        'meses_replicados': resumen_replica,
        'lapsos_descartados': lapsos_descartados,
    })

def vista_importar_bd_ventas_comercial(request):
    return render(request, 'presupuesto_comercial/importar_ventas_comercial.html')


def obtener_ventas_agrupadas(campo_valor, campos_agrupacion, anio=None, anio_desde=None):
    """
    Reemplaza el bloque repetido de "bd2020 ... bd2025 -> concat" que
    aparecía en cada vista de "cargar_presupuesto_*". Con la tabla
    consolidada, esto es una única consulta con GROUP BY.

    Parameters
    ----------
    campo_valor : str
        'valor_neto' para ventas o 'valor_costo' para costos.
    campos_agrupacion : list[str]
        Los campos por los que se debe agrupar, ni más ni menos que
        los que el resultado final necesita. Ejemplos reales de este
        proyecto:
          - Presupuesto general:               ['lapso']
          - Presupuesto por centro:             ['nombre_centro_de_operacion', 'lapso']
          - Presupuesto centro+segmento:        ['nombre_centro_de_operacion', 'nombre_clase_cliente', 'lapso']
          - Presupuesto centro+segmento+línea:  ['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'lapso']
        OJO (ver BUGS_Y_MEJORAS.md, punto 2.6): en BdVentasComercial
        existen DOS campos de centro distintos: 'centro_de_operacion'
        (código numérico) y 'nombre_centro_de_operacion' (nombre). Usar
        siempre el nombre salvo que se necesite explícitamente el código.
        Lo mismo aplica a 'linea_n1'/'nombre_linea_n1' y
        'clase_cliente'/'nombre_clase_cliente': ahora son códigos
        numéricos separados de su nombre legible.
    anio : int | None
        Si se indica, filtra solo los registros de ese año exacto
        (lapso entre `anio*100+1` y `anio*100+12`).
    anio_desde : int | None
        Si se indica (y `anio` es None), filtra desde ese año en
        adelante (lapso >= `anio_desde*100+1`). Útil para "solo el año
        actual y el anterior", sin traer todo el histórico de la base
        de datos para luego descartarlo en pandas (mismo tipo de bug
        que 2.10, ver BUGS_Y_MEJORAS.md 2.16).

    Returns
    -------
    pandas.DataFrame con columnas: *campos_agrupacion, suma
    """
    qs = BdVentasComercial.objects.all()
    if anio is not None:
        qs = qs.filter(lapso__gte=anio * 100 + 1, lapso__lte=anio * 100 + 12)
    elif anio_desde is not None:
        qs = qs.filter(lapso__gte=anio_desde * 100 + 1)

    qs = qs.values(*campos_agrupacion).annotate(suma=Sum(campo_valor)).values(*campos_agrupacion, 'suma')
    df = pd.DataFrame(list(qs))

    if df.empty:
        return pd.DataFrame(columns=list(campos_agrupacion) + ['suma'])

    return df

def obtener_ventas_agrupadas_por_lapso(campo_valor, anio=None):
    """
    Atajo para el caso más simple: `obtener_ventas_agrupadas(campo_valor, ['lapso'])`,
    usado por el "presupuesto general" (ventas y costos).

    Con la tabla consolidada ya NO hace falta el "groupby('lapso') de
    seguridad" que tenía la versión anterior (existía por si un mismo
    `lapso` se repetía entre las tablas por año; ahora solo hay una
    tabla, así que el GROUP BY de la base de datos es suficiente).
    """
    return obtener_ventas_agrupadas(campo_valor, ['lapso'], anio=anio)

def extraer_anio_mes(df, columna_lapso='lapso'):
    """lapso = año*100 + mes (p. ej. 202503 -> 2025, mes 3)."""
    df = df.copy()
    df['year'] = df[columna_lapso] // 100
    df['mes'] = df[columna_lapso] % 100
    return df

def _merge_costos(df, df_costos, on, columnas):
    """
    merge que no revienta si la tabla de costos está vacía: en ese caso
    pd.DataFrame([]) no tiene columnas y pd.merge(on='year') lanza KeyError.
    """
    if df_costos.empty:
        for col in columnas:
            df[col] = 0
        return df
    return pd.merge(df, df_costos, on=on, how='left')

def indice_por_clave(queryset_values, campos_clave):
    """
    Convierte un queryset .values(...) en un diccionario indexado por
    una tupla de campos, para hacer lookups O(1).

    Sustituye el patrón:
        next((x for x in lista if x['campo'] == valor), None)
    que se repetía dentro de bucles en las funciones
    "actualizar_presupuesto_*" y que es O(n) por búsqueda (es decir,
    O(n^2) en total dentro de un bucle) -- ver BUGS_Y_MEJORAS.md punto 4.
    """
    indice = {}
    for item in queryset_values:
        clave = tuple(item[c] for c in campos_clave)
        indice[clave] = item
    return indice

@login_required
def base_comercial(request):
    # ✅ Permitir solo a ciertos usuarios por username
    usuarios_permitidos = ['admin', 'AGRAJALE', 'EVALENCIA', 'SCORTES']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    return render(request, 'presupuesto_comercial/base_presupuesto_comercial.html')

# ------------------------------------------PRESUPUESTO GENERAL VENTAS-----------------------------------------------------
def cargar_presupuesto_general_ventas(request):
    year_actual = timezone.now().year
    year_siguiente = year_actual + 1

    df_lapso_total = obtener_ventas_agrupadas_por_lapso('valor_neto')
    df_lapso_total = extraer_anio_mes(df_lapso_total)

    df_por_anio = df_lapso_total.groupby('year')['suma'].sum().reset_index()
    df_por_anio = df_por_anio.sort_values('year').reset_index(drop=True)
    df_por_anio['variacion_pesos'] = df_por_anio['suma'].diff().round().astype('Int64').fillna(0)
    df_por_anio['variacion_pct'] = (df_por_anio['suma'].pct_change() * 100).round(2).fillna(0)
    df_por_anio = df_por_anio.rename(columns={'suma': 'total'})

    df_costos = pd.DataFrame(list(
        PresupuestoGeneralCostos.objects.values('year', 'total_year')
    )).rename(columns={'total_year': 'total_year_costos'})
    df_por_anio = _merge_costos(df_por_anio, df_costos, 'year', ['total_year_costos'])

    correlaciones = []
    for mes in range(1, 13):
        datos_mes = df_lapso_total[df_lapso_total['mes'] == mes]
        if len(datos_mes) >= 2 and datos_mes['suma'].std() != 0:
            coef = np.corrcoef(datos_mes['year'], datos_mes['suma'])[0, 1]
        else:
            coef = np.nan
        correlaciones.append({'mes': mes, 'coef_correlacion': round(coef, 4) * 100 if not np.isnan(coef) else None})
    df_correl = pd.DataFrame(correlaciones)

    df_proyeccion = pd.merge(df_lapso_total, df_correl, on='mes', how='left')
    df_proyeccion['suma'] = df_proyeccion['suma'].round().astype(int)
    df_proyeccion = pd.merge(
        df_proyeccion,
        df_por_anio[['year', 'total', 'total_year_costos', 'variacion_pesos', 'variacion_pct']],
        on='year', how='left',
    )
    df_proyeccion['utilidad_pct'] = (
        (1 - (df_proyeccion['total_year_costos'] / df_proyeccion['total'])) * 100
    ).replace([np.inf, -np.inf], 0).fillna(0).round(2)
    df_proyeccion['utilidad_valor'] = (
        df_proyeccion['total'] - df_proyeccion['total_year_costos']
    ).round().astype(int)

    # 12 meses del año siguiente en cero (igual que el original)
    meses_siguiente = pd.DataFrame([{
        'lapso': year_siguiente * 100 + m, 'year': year_siguiente, 'mes': m, 'suma': 0,
        'coef_correlacion': 0, 'total': 0, 'total_year_costos': 0,
        'variacion_pesos': 0, 'variacion_pct': 0, 'utilidad_pct': 0, 'utilidad_valor': 0,
    } for m in range(1, 13)])
    df_proyeccion = pd.concat([df_proyeccion, meses_siguiente], ignore_index=True)

    with transaction.atomic():
        PresupuestoGeneralVentas.objects.all().delete()
        PresupuestoGeneralVentas.objects.bulk_create([
            PresupuestoGeneralVentas(
                year=int(row['year']), mes=int(row['mes']), total=int(row['suma']),
                r2=row['coef_correlacion'] or 0, total_year=row['total'] or 0,
                total_year_costos=row['total_year_costos'] or 0,
                variacion_valor=row['variacion_pesos'] or 0, variacion_pct=row['variacion_pct'] or 0,
                utilidad_pct=row['utilidad_pct'] or 0, utilidad_valor=row['utilidad_valor'] or 0,
            )
            for _, row in df_proyeccion.iterrows()
        ])

    return JsonResponse(list(PresupuestoGeneralVentas.objects.values()), safe=False)

from . import calculo

def obtener_presupuesto_general_ventas(request):
    return JsonResponse(calculo.construir_ventas('general'), safe=False)

def vista_presupuesto_general_ventas(request):
    return render(request, 'presupuesto_comercial/presupuesto_general_ventas.html')

# --------------------------PRESUPUESTO POR CENTRO OPERACION VENTAS------------------------
def cargar_presupuesto_centro_ventas(request):
    year_actual = timezone.now().year
    year_siguiente = year_actual + 1

    df_centro_operacion = obtener_ventas_agrupadas(
        'valor_neto', ['nombre_centro_de_operacion', 'lapso']
    ).rename(columns={'nombre_centro_de_operacion': 'nombre_centro_operacion'})
    df_centro_operacion = extraer_anio_mes(df_centro_operacion)

    df_proyeccion = df_centro_operacion[['nombre_centro_operacion', 'lapso', 'suma']].copy()
    df_proyeccion = df_proyeccion.sort_values(['nombre_centro_operacion', 'lapso']).reset_index(drop=True)
    df_proyeccion = extraer_anio_mes(df_proyeccion)

    correlaciones_centro = []
    for centro, grupo in df_proyeccion.groupby('nombre_centro_operacion'):
        for mes in range(1, 13):
            datos_mes = grupo[grupo["mes"] == mes]
            if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
                coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
            else:
                coef = np.nan
            correlaciones_centro.append({
                "nombre_centro_operacion": centro, "mes": mes,
                "coef_correlacion": round(coef, 4) * 100 if not np.isnan(coef) else None,
            })
    df_correl = pd.DataFrame(correlaciones_centro)
    df_proyeccion = pd.merge(df_proyeccion, df_correl, on=['nombre_centro_operacion', 'mes'], how='left')
    df_proyeccion['suma'] = df_proyeccion['suma'].round().astype(int)

    df_total_year_centro = (
        df_proyeccion.groupby(['nombre_centro_operacion', 'year'])['suma'].sum()
        .reset_index().rename(columns={'suma': 'total_year'})
    )
    df_total_year_centro['variacion_pesos'] = (
        df_total_year_centro.groupby('nombre_centro_operacion')['total_year'].diff().round().astype('Int64')
    )
    df_total_year_centro['variacion_pct'] = (
        df_total_year_centro.groupby('nombre_centro_operacion')['total_year'].pct_change() * 100
    ).round(2)
    df_total_year_centro[['variacion_pesos', 'variacion_pct']] = (
        df_total_year_centro[['variacion_pesos', 'variacion_pct']].fillna(0)
    )

    df_costos = pd.DataFrame(list(
        PresupuestoCentroOperacionCostos.objects.values("year", "nombre_centro_operacion", "total_year")
    )).rename(columns={"total_year": "total_year_costos"})
    df_total_year_centro = _merge_costos(
        df_total_year_centro, df_costos,
        ['nombre_centro_operacion', 'year'], ['total_year_costos'],
    )

    df_proyeccion = pd.merge(
        df_proyeccion,
        df_total_year_centro[['nombre_centro_operacion', 'year', 'total_year', 'total_year_costos', 'variacion_pesos', 'variacion_pct']],
        on=["nombre_centro_operacion", "year"], how='left',
    )

    df_proyeccion['utilidad_pct'] = (
        (1 - (df_proyeccion['total_year_costos'] / df_proyeccion['total_year'])) * 100
    ).replace([np.inf, -np.inf], 0).fillna(0).round(2)
    df_proyeccion['utilidad_valor'] = (
        df_proyeccion['total_year'] - df_proyeccion['total_year_costos']
    ).round().astype(int)

    centros_existentes = df_proyeccion["nombre_centro_operacion"].dropna().unique()
    filas_siguiente = [{
        "lapso": year_siguiente * 100 + m, "nombre_centro_operacion": centro,
        "year": year_siguiente, "mes": m, "suma": 0, "coef_correlacion": 0,
        "total_year": 0, "total_year_costos": 0, "variacion_pesos": 0, "variacion_pct": 0,
        "utilidad_pct": 0, "utilidad_valor": 0,
    } for centro in centros_existentes for m in range(1, 13)]
    df_proyeccion = pd.concat([df_proyeccion, pd.DataFrame(filas_siguiente)], ignore_index=True)

    with transaction.atomic():
        PresupuestoCentroOperacionVentas.objects.all().delete()
        PresupuestoCentroOperacionVentas.objects.bulk_create([
            PresupuestoCentroOperacionVentas(
                nombre_centro_operacion=row['nombre_centro_operacion'],
                year=int(row['year']), mes=int(row['mes']), total=int(row['suma']),
                r2=row['coef_correlacion'] if row['coef_correlacion'] is not None else 0,
                total_year=row['total_year'] if row['total_year'] is not None else 0,
                total_year_costos=row['total_year_costos'] if row['total_year_costos'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0,
                utilidad_pct=row['utilidad_pct'] if row['utilidad_pct'] is not None else 0,
                utilidad_valor=row['utilidad_valor'] if row['utilidad_valor'] is not None else 0,
            )
            for _, row in df_proyeccion.iterrows()
        ])

    return JsonResponse(list(PresupuestoCentroOperacionVentas.objects.values()), safe=False)
 
def obtener_presupuesto_centro_ventas(request):
    return JsonResponse(calculo.construir_ventas('centro'), safe=False)

def vista_presupuesto_centro_ventas(request):
    return render(request, 'presupuesto_comercial/presupuesto_centro_ventas.html') 

#---------------PRESUPUESTO POR CENTRO OPERACION - SEGMENTO VENTAS--------
def cargar_presupuesto_centro_segmento_ventas(request):
    year_actual = timezone.now().year 
    year_siguiente = year_actual + 1

    df_cs = obtener_ventas_agrupadas(
        'valor_neto', ['nombre_clase_cliente', 'nombre_centro_de_operacion', 'lapso']
    )
    df_cs = extraer_anio_mes(df_cs)

    df_proyeccion = df_cs[['nombre_centro_de_operacion', 'nombre_clase_cliente', 'lapso', 'suma']].copy()
    df_proyeccion = df_proyeccion.sort_values(
        ['nombre_centro_de_operacion', 'nombre_clase_cliente', 'lapso']
    ).reset_index(drop=True)
    df_proyeccion = extraer_anio_mes(df_proyeccion)

    correlaciones = []
    for (centro, segmento), grupo in df_proyeccion.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente']):
        for mes in range(1, 13):
            datos_mes = grupo[grupo["mes"] == mes]
            if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
                coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
            else:
                coef = 0
            correlaciones.append({
                "nombre_centro_de_operacion": centro, "nombre_clase_cliente": segmento, "mes": mes,
                "coef_correlacion": round(coef, 4) * 100 if not np.isnan(coef) else None,
            })
    df_correl = pd.DataFrame(correlaciones)
    df_proyeccion = pd.merge(
        df_proyeccion, df_correl, on=['nombre_centro_de_operacion', 'nombre_clase_cliente', 'mes'], how='left'
    )
    df_proyeccion['suma'] = df_proyeccion['suma'].round().astype(int)

    df_total_year = (
        df_proyeccion.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'])['suma'].sum()
        .reset_index().rename(columns={'suma': 'total_year'})
    )
    df_total_year['variacion_pesos'] = (
        df_total_year.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente'])['total_year']
        .diff().round().astype('Int64')
    )
    df_total_year['variacion_pct'] = (
        df_total_year.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente'])['total_year']
        .pct_change() * 100
    ).round(2)
    df_total_year[['variacion_pesos', 'variacion_pct']] = df_total_year[['variacion_pesos', 'variacion_pct']].fillna(0)

    df_costos = pd.DataFrame(list(
        PresupuestoCentroSegmentoCostos.objects.values("year", "nombre_centro_operacion", "segmento", "total_year")
    )).rename(columns={"total_year": "total_year_costos"})
    if df_costos.empty:
        df_total_year['total_year_costos'] = 0
    else:
        df_total_year = pd.merge(
            df_total_year, df_costos,
            left_on=["nombre_centro_de_operacion", "nombre_clase_cliente", "year"],
            right_on=["nombre_centro_operacion", "segmento", "year"], how="left",
        ).drop(columns=["nombre_centro_operacion", "segmento"], errors="ignore")

    df_proyeccion = pd.merge(
        df_proyeccion,
        df_total_year[['nombre_centro_de_operacion', 'nombre_clase_cliente', 'year', 'total_year', 'total_year_costos', 'variacion_pesos', 'variacion_pct']],
        on=["nombre_centro_de_operacion", "nombre_clase_cliente", "year"], how="left",
    )

    df_proyeccion['utilidad_pct'] = (
        (1 - (df_proyeccion['total_year_costos'] / df_proyeccion['total_year'])) * 100
    ).replace([np.inf, -np.inf], 0).fillna(0).round(2)
    df_proyeccion['utilidad_valor'] = (
        df_proyeccion['total_year'] - df_proyeccion['total_year_costos']
    ).round().astype(int)

    centros = df_proyeccion["nombre_centro_de_operacion"].dropna().unique()
    segmentos = df_proyeccion["nombre_clase_cliente"].dropna().unique()
    filas_siguiente = [{
        "lapso": year_siguiente * 100 + m,
        "nombre_centro_de_operacion": centro, "nombre_clase_cliente": segmento,
        "year": year_siguiente, "mes": m, "suma": 0, "coef_correlacion": 0,
        "total_year": 0, "total_year_costos": 0, "variacion_pesos": 0, "variacion_pct": 0,
        "utilidad_pct": 0, "utilidad_valor": 0,
    } for centro in centros for segmento in segmentos for m in range(1, 13)]
    df_proyeccion = pd.concat([df_proyeccion, pd.DataFrame(filas_siguiente)], ignore_index=True)

    with transaction.atomic():
        PresupuestoCentroSegmentoVentas.objects.all().delete()
        PresupuestoCentroSegmentoVentas.objects.bulk_create([
            PresupuestoCentroSegmentoVentas(
                nombre_centro_operacion=row['nombre_centro_de_operacion'],
                segmento=row['nombre_clase_cliente'],
                year=int(row['year']), mes=int(row['mes']), total=int(row['suma']),
                r2=row['coef_correlacion'] if row['coef_correlacion'] is not None else 0,
                total_year=row['total_year'] if row['total_year'] is not None else 0,
                total_year_costos=row['total_year_costos'] if row['total_year_costos'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0,
                utilidad_pct=row['utilidad_pct'] if row['utilidad_pct'] is not None else 0,
                utilidad_valor=row['utilidad_valor'] if row['utilidad_valor'] is not None else 0,
            )
            for _, row in df_proyeccion.iterrows()
        ])

    return JsonResponse(list(PresupuestoCentroSegmentoVentas.objects.values()), safe=False)

def obtener_presupuesto_centro_segmento_ventas(request):
    return JsonResponse(calculo.construir_ventas('centro_segmento'), safe=False)

def vista_presupuesto_centro_segmento_ventas(request):
    return render(request, 'presupuesto_comercial/presupuesto_centro_segmento_ventas.html')

#-----------PRESUPUESTO GENERAL COSTOS
def cargar_presupuesto_general_costos(request):
    year_actual = timezone.now().year
    year_siguiente = year_actual + 1

    df_lapso_total = obtener_ventas_agrupadas_por_lapso('valor_costo')
    df_lapso_total = extraer_anio_mes(df_lapso_total)

    df_por_year_mes = df_lapso_total.groupby(["year", "mes"])["suma"].sum().reset_index()

    predicciones = []
    for mes in range(1, 13):
        datos_mes = df_por_year_mes[df_por_year_mes["mes"] == mes]
        x = datos_mes["year"].values
        y = datos_mes["suma"].values
        if len(x) >= 2:
            a, b = np.polyfit(x, y, 1)
            y_pred = a * year_siguiente + b
            predicciones.append({
                "year": year_siguiente, "mes": mes,
                "suma_pred": round(y_pred), "lapso": year_siguiente * 100 + mes,
            })
    df_pred = pd.DataFrame(predicciones)

    partes = [df_lapso_total[['lapso', 'suma']]]
    if not df_pred.empty:
        partes.append(df_pred[['lapso', 'suma_pred']].rename(columns={'suma_pred': 'suma'}))
    df_proyeccion = pd.concat(partes, ignore_index=True)
    df_proyeccion = extraer_anio_mes(df_proyeccion)

    correlaciones = []
    for mes in range(1, 13):
        datos_mes = df_proyeccion[df_proyeccion["mes"] == mes]
        if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
            coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
        else:
            coef = np.nan
        correlaciones.append({"mes": mes, "coef_correlacion": round(coef, 4) * 100 if not np.isnan(coef) else None})
    df_correl = pd.DataFrame(correlaciones)

    df_proyeccion = pd.merge(df_proyeccion, df_correl, on='mes', how='left')
    df_proyeccion['suma'] = df_proyeccion['suma'].round().astype(int)

    df_por_anio = df_proyeccion.groupby("year")["suma"].sum().reset_index().sort_values("year").reset_index(drop=True)
    df_por_anio["variacion_pesos"] = df_por_anio["suma"].diff().round().astype('Int64').fillna(0)
    df_por_anio["variacion_pct"] = (df_por_anio["suma"].pct_change() * 100).round(2).fillna(0)
    df_por_anio = df_por_anio.rename(columns={'suma': 'total'})

    df_proyeccion = pd.merge(
        df_proyeccion, df_por_anio[['year', 'total', 'variacion_pesos', 'variacion_pct']],
        on='year', how='left',
    )

    with transaction.atomic():
        PresupuestoGeneralCostos.objects.all().delete()
        PresupuestoGeneralCostos.objects.bulk_create([
            PresupuestoGeneralCostos(
                year=int(row['year']), mes=int(row['mes']), total=int(row['suma']),
                r2=row['coef_correlacion'] if row['coef_correlacion'] is not None else 0,
                total_year=row['total'] if row['total'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0,
            )
            for _, row in df_proyeccion.iterrows()
        ])

    return JsonResponse(list(PresupuestoGeneralCostos.objects.values()), safe=False)

def obtener_presupuesto_general_costos(request):
    return JsonResponse(calculo.construir_costos('general'), safe=False)

def vista_presupuesto_general_costos(request):
    return render(request, 'presupuesto_comercial/presupuesto_general_costos.html')

#-----------PRESUPUESTO POR CENTRO OPERACION - COSTOS
def cargar_presupuesto_centro_costos(request):
    year_actual = timezone.now().year
    year_siguiente = year_actual + 1

    df_centro_operacion = obtener_ventas_agrupadas(
        'valor_costo', ['nombre_centro_de_operacion', 'lapso']
    )
    df_centro_operacion = extraer_anio_mes(df_centro_operacion)

    predicciones_centro = []
    for centro, grupo in df_centro_operacion.groupby('nombre_centro_de_operacion'):
        for mes in range(1, 13):
            datos_mes = grupo[grupo['mes'] == mes]
            x = datos_mes['year'].values
            y = datos_mes['suma'].values
            if len(x) >= 2:
                a, b = np.polyfit(x, y, 1)
                y_pred = a * year_siguiente + b
                predicciones_centro.append({
                    'nombre_centro_de_operacion': centro,
                    'lapso': year_siguiente * 100 + mes, 'suma': round(y_pred),
                })
    df_pred = pd.DataFrame(predicciones_centro)

    partes = [df_centro_operacion[['nombre_centro_de_operacion', 'lapso', 'suma']]]
    if not df_pred.empty:
        partes.append(df_pred)
    df_proyeccion = pd.concat(partes, ignore_index=True)
    df_proyeccion = df_proyeccion.sort_values(['nombre_centro_de_operacion', 'lapso']).reset_index(drop=True)
    df_proyeccion = extraer_anio_mes(df_proyeccion)

    correlaciones_centro = []
    for centro, grupo in df_proyeccion.groupby('nombre_centro_de_operacion'):
        for mes in range(1, 13):
            datos_mes = grupo[grupo["mes"] == mes]
            if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
                coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
            else:
                coef = np.nan
            correlaciones_centro.append({
                "nombre_centro_de_operacion": centro, "mes": mes,
                "coef_correlacion": round(coef, 4) * 100 if not np.isnan(coef) else None,
            })
    df_correl = pd.DataFrame(correlaciones_centro)
    df_proyeccion = pd.merge(df_proyeccion, df_correl, on=['nombre_centro_de_operacion', 'mes'], how='left')
    df_proyeccion['suma'] = df_proyeccion['suma'].round().astype(int)

    df_total_year_centro = (
        df_proyeccion.groupby(['nombre_centro_de_operacion', 'year'])['suma'].sum()
        .reset_index().rename(columns={'suma': 'total_year'})
    )
    df_total_year_centro['variacion_pesos'] = (
        df_total_year_centro.groupby('nombre_centro_de_operacion')['total_year'].diff().round().astype('Int64')
    )
    df_total_year_centro['variacion_pct'] = (
        df_total_year_centro.groupby('nombre_centro_de_operacion')['total_year'].pct_change() * 100
    ).round(2)
    df_total_year_centro[['variacion_pesos', 'variacion_pct']] = (
        df_total_year_centro[['variacion_pesos', 'variacion_pct']].fillna(0)
    )

    df_proyeccion = pd.merge(
        df_proyeccion,
        df_total_year_centro[['nombre_centro_de_operacion', 'year', 'total_year', 'variacion_pesos', 'variacion_pct']],
        on=['nombre_centro_de_operacion', 'year'], how='left',
    )

    with transaction.atomic():
        PresupuestoCentroOperacionCostos.objects.all().delete()
        PresupuestoCentroOperacionCostos.objects.bulk_create([
            PresupuestoCentroOperacionCostos(
                nombre_centro_operacion=row['nombre_centro_de_operacion'],
                year=int(row['year']), mes=int(row['mes']), total=int(row['suma']),
                r2=row['coef_correlacion'] if row['coef_correlacion'] is not None else 0,
                total_year=row['total_year'] if row['total_year'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0,
            )
            for _, row in df_proyeccion.iterrows()
        ])

    return JsonResponse(list(PresupuestoCentroOperacionCostos.objects.values()), safe=False)

def obtener_presupuesto_centro_costos(request):
    return JsonResponse(calculo.construir_costos('centro'), safe=False)

def vista_presupuesto_centro_costos(request):
    return render(request, 'presupuesto_comercial/presupuesto_centro_costos.html')

#--------------------------PRESUPUESTO CENTRO OPERACION - SEGMENTO COSTOS---------------
def cargar_presupuesto_centro_segmento_costos(request):
    year_actual = timezone.now().year
    year_siguiente = year_actual + 1

    df_cs = obtener_ventas_agrupadas(
        'valor_costo', ['nombre_clase_cliente', 'nombre_centro_de_operacion', 'lapso']
    )
    df_cs = extraer_anio_mes(df_cs)

    predicciones = []
    for (centro, segmento), grupo in df_cs.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente']):
        for mes in range(1, 13):
            datos_mes = grupo[grupo['mes'] == mes]
            x = datos_mes['year'].values
            y = datos_mes['suma'].values
            if len(x) >= 2:
                a, b = np.polyfit(x, y, 1)
                y_pred = a * year_siguiente + b
                predicciones.append({
                    'nombre_centro_de_operacion': centro, 'nombre_clase_cliente': segmento,
                    'lapso': year_siguiente * 100 + mes, 'suma': round(y_pred),
                })
    df_pred = pd.DataFrame(predicciones)

    partes = [df_cs[['nombre_centro_de_operacion', 'nombre_clase_cliente', 'lapso', 'suma']]]
    if not df_pred.empty:
        partes.append(df_pred)
    df_proyeccion = pd.concat(partes, ignore_index=True)
    df_proyeccion = df_proyeccion.sort_values(
        ['nombre_centro_de_operacion', 'nombre_clase_cliente', 'lapso']
    ).reset_index(drop=True)
    df_proyeccion = extraer_anio_mes(df_proyeccion)

    correlaciones = []
    for (centro, segmento), grupo in df_proyeccion.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente']):
        for mes in range(1, 13):
            datos_mes = grupo[grupo["mes"] == mes]
            if len(datos_mes) >= 2 and datos_mes["suma"].std() != 0:
                coef = np.corrcoef(datos_mes["year"], datos_mes["suma"])[0, 1]
            else:
                coef = 0
            correlaciones.append({
                "nombre_centro_de_operacion": centro, "nombre_clase_cliente": segmento, "mes": mes,
                "coef_correlacion": round(coef, 4) * 100 if not np.isnan(coef) else None,
            })
    df_correl = pd.DataFrame(correlaciones)
    df_proyeccion = pd.merge(
        df_proyeccion, df_correl, on=['nombre_centro_de_operacion', 'nombre_clase_cliente', 'mes'], how='left'
    )
    df_proyeccion['suma'] = df_proyeccion['suma'].round().astype(int)

    df_total_year = (
        df_proyeccion.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'])['suma'].sum()
        .reset_index().rename(columns={'suma': 'total_year'})
    )
    df_total_year['variacion_pesos'] = (
        df_total_year.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente'])['total_year']
        .diff().round().astype('Int64')
    )
    df_total_year['variacion_pct'] = (
        df_total_year.groupby(['nombre_centro_de_operacion', 'nombre_clase_cliente'])['total_year']
        .pct_change() * 100
    ).round(2)
    df_total_year[['variacion_pesos', 'variacion_pct']] = df_total_year[['variacion_pesos', 'variacion_pct']].fillna(0)

    df_proyeccion = pd.merge(
        df_proyeccion,
        df_total_year[['nombre_centro_de_operacion', 'nombre_clase_cliente', 'year', 'total_year', 'variacion_pesos', 'variacion_pct']],
        on=['nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'], how='left',
    )

    with transaction.atomic():
        PresupuestoCentroSegmentoCostos.objects.all().delete()
        PresupuestoCentroSegmentoCostos.objects.bulk_create([
            PresupuestoCentroSegmentoCostos(
                nombre_centro_operacion=row['nombre_centro_de_operacion'],
                segmento=row['nombre_clase_cliente'],
                year=int(row['year']), mes=int(row['mes']), total=int(row['suma']),
                r2=row['coef_correlacion'] if row['coef_correlacion'] is not None else 0,
                total_year=row['total_year'] if row['total_year'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0,
            )
            for _, row in df_proyeccion.iterrows()
        ])

    return JsonResponse(list(PresupuestoCentroSegmentoCostos.objects.values()), safe=False)

def obtener_presupuesto_centro_segmento_costos(request):
    return JsonResponse(calculo.construir_costos('centro_segmento'), safe=False)

def vista_presupuesto_centro_segmento_costos(request):
    return render(request, 'presupuesto_comercial/presupuesto_centro_segmento_costos.html')

# --------------------------PRESUPUESTO CENTRO OPERACION - SEGMENTO - LINEA COSTOS---------------
def cargar_presupuesto_centro_segmento_linea_costos(request):
    df_merged = aux_presupuesto_centro_segmento_linea_costos()

    with transaction.atomic():
        PresupuestoCentroSegLineaCostos.objects.all().delete()
        PresupuestoCentroSegLineaCostos.objects.bulk_create([
            PresupuestoCentroSegLineaCostos(
                linea=row['nombre_linea_n1'],
                nombre_centro_operacion=row['nombre_centro_de_operacion'],
                segmento=row['nombre_clase_cliente'],
                year=int(row['year']), mes=int(row['mes']), total=int(row['suma']),
                total_year=row['total_year'] if row['total_year'] is not None else 0,
            )
            for _, row in df_merged.iterrows()
        ])

    return JsonResponse(list(PresupuestoCentroSegLineaCostos.objects.values()), safe=False)

def obtener_presupuesto_centro_segmento_linea_costos(request):
    return JsonResponse(calculo.construir_costos('centro_segmento_linea'), safe=False)


def aux_presupuesto_centro_segmento_linea_costos():
    """
    Detalle mensual de costos por línea+centro+segmento del año
    `_anio_detalle_linea`, con el total anual (`total_year`) ya unido.
    La usan tanto la vista de costos como la de ventas (para calcular
    la utilidad).
    """
    df = obtener_ventas_agrupadas(
        'valor_costo',
        ['nombre_linea_n1', 'nombre_clase_cliente', 'nombre_centro_de_operacion', 'lapso'],
        anio=_anio_detalle_linea(),
    )
    df = extraer_anio_mes(df)
    df = df.sort_values(
        ['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'lapso']
    ).reset_index(drop=True)
    df['suma'] = df['suma'].round().astype(int)

    df_total_year = (
        df.groupby(['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'])['suma']
        .sum().reset_index().rename(columns={'suma': 'total_year'})
    )
    return df.merge(
        df_total_year,
        on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'],
        how='left',
    )

def vista_presupuesto_centro_segmento_linea_costos(request):
    return render(request, 'presupuesto_comercial/presupuesto_centro_segmento_linea_costos.html')

# --------------------------PRESUPUESTO CENTRO OPERACION - SEGMENTO - LINEA VENTAS---------------
def cargar_presupuesto_centro_segmento_linea_ventas(request):
    year_siguiente = _anio_detalle_linea() + 1  # antes: literal "2026"

    df = obtener_ventas_agrupadas(
        'valor_neto',
        ['nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente'],
        anio=_anio_detalle_linea(),
    )
    if df.empty:
        return JsonResponse([], safe=False)
    df = extraer_anio_mes(df)

    df_total_anual = (
        df.groupby(['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'])['suma']
        .sum().reset_index().rename(columns={'suma': 'total_year'})
    )
    df_total_year = df.merge(
        df_total_anual,
        on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'],
        how='left',
    )
    df_total_year = df_total_year.sort_values(
        ['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year']
    )
    df_total_year['variacion_pesos'] = (
        df_total_year.groupby(['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente'])['total_year']
        .diff().fillna(0).round().astype('Int64')
    )
    df_total_year['variacion_pct'] = (
        df_total_year.groupby(['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente'])['total_year']
        .pct_change().fillna(0) * 100
    ).round(2)

    df_costos = aux_presupuesto_centro_segmento_linea_costos().rename(columns={'total_year': 'total_year_costos'})
    df_merged = df_total_year.merge(
        df_costos[
            ['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year', 'total_year_costos']
        ].drop_duplicates(),
        on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'],
        how='left',
    )
    df_merged['total_year_costos'] = df_merged['total_year_costos'].fillna(0)

    df_merged['utilidad_pct'] = (
        (1 - (df_merged['total_year_costos'] / df_merged['total_year'])) * 100
    ).replace([np.inf, -np.inf], 0).fillna(0).round(2)
    df_merged['utilidad_valor'] = (df_merged['total_year'] - df_merged['total_year_costos']).round().astype(int)

    centros = df['nombre_centro_de_operacion'].unique()
    segmentos = df['nombre_clase_cliente'].unique()
    lineas = df['nombre_linea_n1'].unique()
    filas_siguiente = [{
        "lapso": year_siguiente * 100 + mes,
        "nombre_linea_n1": linea, "nombre_centro_de_operacion": centro, "nombre_clase_cliente": segmento,
        "year": year_siguiente, "mes": mes, "suma": 0, "total_year": 0, "total_year_costos": 0,
        "variacion_pesos": 0, "variacion_pct": 0, "utilidad_pct": 0, "utilidad_valor": 0, "total_proyectado": 0,
    } for linea in lineas for centro in centros for segmento in segmentos for mes in range(1, 13)]
    df_final_linea = pd.concat([df_merged, pd.DataFrame(filas_siguiente)], ignore_index=True)
    df_final_linea = df_final_linea.fillna(0)

    with transaction.atomic():
        PresupuestoCentroSegLineaVentas.objects.all().delete()
        PresupuestoCentroSegLineaVentas.objects.bulk_create([
            PresupuestoCentroSegLineaVentas(
                linea=row['nombre_linea_n1'],
                nombre_centro_operacion=row['nombre_centro_de_operacion'],
                segmento=row['nombre_clase_cliente'],
                year=int(row['year']), mes=int(row['mes']), total=int(row['suma']),
                total_year=row['total_year'] if row['total_year'] is not None else 0,
                total_year_costos=row['total_year_costos'] if row['total_year_costos'] is not None else 0,
                variacion_valor=row['variacion_pesos'] if row['variacion_pesos'] is not None else 0,
                variacion_pct=row['variacion_pct'] if row['variacion_pct'] is not None else 0,
                utilidad_valor=row['utilidad_valor'] if row['utilidad_valor'] is not None else 0,
                utilidad_pct=row['utilidad_pct'] if row['utilidad_pct'] is not None else 0.0,
            )
            for _, row in df_final_linea.iterrows()
        ])

    return JsonResponse(list(PresupuestoCentroSegLineaVentas.objects.values()), safe=False)

def obtener_presupuesto_centro_segmento_linea_ventas(request):
    return JsonResponse(calculo.construir_ventas('centro_segmento_linea'), safe=False)

def vista_presupuesto_centro_segmento_linea_ventas(request):
    return render(request, 'presupuesto_comercial/presupuesto_centro_segmento_linea_ventas.html')

#----------------PRESUPUESTO COMERCIAL PRINCIPAL-----------------------
def _pronostico_por_linea_centro_segmento(campo_valor, anio_inicio=2020):
    """
    Lógica compartida entre `aux_presupuesto_comercial_costos` y
    `cargar_presupuesto_comercial` (antes casi 80 líneas duplicadas
    entre las dos): arma el histórico por línea+centro+segmento+año
    desde `anio_inicio` hasta el año actual, rellena los años faltantes
    con 0, y calcula R² y variaciones año contra año.

    `anio_inicio` por defecto es 2020 (todo el histórico), pero
    `cargar_presupuesto_comercial` lo llama con `year_actual - 1`
    porque, para la proyección del presupuesto comercial, solo hace
    falta comparar el año actual contra el anterior — no todo el
    histórico (ver BUGS_Y_MEJORAS.md 2.16).
    """
    year_actual = timezone.now().year

    df = obtener_ventas_agrupadas(
        campo_valor,
        ['nombre_linea_n1', 'lapso', 'nombre_centro_de_operacion', 'nombre_clase_cliente'],
        anio_desde=anio_inicio,
    )
    df = extraer_anio_mes(df)
    COLUMNAS_PRONOSTICO = [
        'nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente',
        'year', 'suma', 'R2', 'suma_anterior', 'variacion_pct', 'variacion_valor',
        'variacion_mes', 'variacion_precios', 'crecimiento_comercial',
        'crecimiento_comercial_mes',
    ]
    if df.empty:
        # Sin ventas en el rango pedido: se devuelve la estructura vacía pero
        # con todas las columnas, para que los merge() de más abajo y los de
        # calcular_comercial() no fallen con KeyError.
        return pd.DataFrame(columns=COLUMNAS_PRONOSTICO)
    df_agrupado = (
        df.groupby(['nombre_linea_n1', 'year', 'nombre_centro_de_operacion', 'nombre_clase_cliente'])['suma']
        .sum().reset_index().sort_values(by=['nombre_linea_n1', 'year'])
    )

    # FIX bug 2.4: antes "range(2020, 2026)" hardcodeado en cargar_presupuesto_comercial.
    anios = list(range(anio_inicio, year_actual + 1))
    df_completo = pd.MultiIndex.from_product(
        [
            df_agrupado['nombre_linea_n1'].unique(),
            df_agrupado['nombre_centro_de_operacion'].unique(),
            df_agrupado['nombre_clase_cliente'].unique(),
            anios,
        ],
        names=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'],
    ).to_frame(index=False)
    df_final = df_completo.merge(
        df_agrupado, on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'year'], how='left'
    )
    df_final['suma'] = df_final['suma'].fillna(0)

    correlaciones = []
    for (nombre, centro, clase), grupo in df_final.groupby(
        ['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente']
    ):
        x = grupo['year'].values
        y = grupo['suma'].values
        if len(x) >= 2 and np.std(y) != 0 and np.std(x) != 0:
            coef_abs_pct = abs(np.corrcoef(x, y)[0, 1]) * 100
        else:
            coef_abs_pct = 0.0
        correlaciones.append({
            'nombre_linea_n1': nombre, 'nombre_centro_de_operacion': centro,
            'nombre_clase_cliente': clase, 'R2': round(coef_abs_pct, 2),
        })
    df_correlaciones = pd.DataFrame(correlaciones)
    if df_correlaciones.empty:
        df_final['R2'] = 0.0
    else:
        df_final = pd.merge(
            df_final, df_correlaciones,
            on=['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente'], how='left',
        )

    df_final['suma_anterior'] = df_final.groupby(
        ['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente']
    )['suma'].shift(1)
    df_final['variacion_pct'] = np.where(
        df_final['suma_anterior'] == 0, 0,
        ((df_final['suma'] - df_final['suma_anterior']) / df_final['suma_anterior']) * 100,
    ).round(2)
    df_final['variacion_valor'] = (df_final['suma'] - df_final['suma_anterior']).fillna(0)
    df_final['variacion_mes'] = (df_final['variacion_valor'] / 12).round().astype(int)
    df_final['variacion_precios'] = (df_final['suma_anterior'] * 0.02).round().fillna(0).astype(int)
    df_final['crecimiento_comercial'] = (
        df_final['variacion_valor'] - df_final['variacion_precios']
    ).round().astype(int)
    df_final['crecimiento_comercial_mes'] = (df_final['crecimiento_comercial'] / 12).round().astype(int)

    cols_variaciones = [
        'variacion_pct', 'variacion_valor', 'variacion_mes', 'variacion_precios',
        'crecimiento_comercial', 'crecimiento_comercial_mes',
    ]
    df_final[cols_variaciones] = df_final[cols_variaciones].fillna(0)

    return df_final

def aux_presupuesto_comercial_costos():
    """
    Pronóstico de costos por línea+centro+segmento, comparando el año
    actual contra el anterior (ver bug 2.16: antes traía 2020..año
    actual completo aunque solo se usaba el año actual).
    """
    year_actual = timezone.now().year
    return _pronostico_por_linea_centro_segmento('valor_costo', anio_inicio=year_actual - 1)

@csrf_exempt
def guardar_presupuesto_comercial(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "mensaje": "Método no permitido"}, status=405)
    try:
        data = json.loads(request.body)
        year_actual = timezone.now().year
        with transaction.atomic():
            for row in data:
                if int(row.get("year", 0)) != year_actual:
                    continue          # solo el año actual es editable
                PresupuestoComercial.objects.update_or_create(
                    linea=row["linea"], year=year_actual,
                    nombre_centro_de_operacion=row.get("nombre_centro_de_operacion", ""),
                    nombre_clase_cliente=row.get("nombre_clase_cliente", ""),
                    defaults={
                        "crecimiento_ventas": float(row.get("crecimiento_ventas") or 0),
                    },
                )
        return JsonResponse({"status": "ok", "mensaje": "Crecimientos guardados ✅"})
    except Exception as e:
        return JsonResponse({"status": "error", "mensaje": str(e)}, status=400)
    
# =====================================================================
# NUEVO: comparativo año anterior vs año actual (para visualizar
# crecimiento). No depende de `PresupuestoComercial` — la calcula al
# vuelo desde `BdVentasComercial`, porque `PresupuestoComercial` ahora
# solo guarda el año actual (ver bug 2.16) y no serviría para comparar.
# =====================================================================
def obtener_comparativo_anual(request):
    """
    Ventas y costos por línea+centro+segmento, año anterior vs año
    actual, con variación $ y % y margen de cada año — para el template
    de comparativo de crecimiento.
    """
    year_actual = timezone.now().year
    year_anterior = year_actual - 1

    df_ventas = _pronostico_por_linea_centro_segmento('valor_neto', anio_inicio=year_anterior)
    df_costos = _pronostico_por_linea_centro_segmento('valor_costo', anio_inicio=year_anterior)

    columnas_base = ['nombre_linea_n1', 'nombre_centro_de_operacion', 'nombre_clase_cliente']

    df_ventas = df_ventas[df_ventas['year'] == year_actual][
        columnas_base + ['suma', 'suma_anterior', 'variacion_valor', 'variacion_pct']
    ].rename(columns={
        'suma': 'ventas_actual', 'suma_anterior': 'ventas_anterior',
        'variacion_valor': 'variacion_valor_ventas', 'variacion_pct': 'variacion_pct_ventas',
    })

    df_costos = df_costos[df_costos['year'] == year_actual][
        columnas_base + ['suma', 'suma_anterior', 'variacion_valor', 'variacion_pct']
    ].rename(columns={
        'suma': 'costos_actual', 'suma_anterior': 'costos_anterior',
        'variacion_valor': 'variacion_valor_costos', 'variacion_pct': 'variacion_pct_costos',
    })

    df = pd.merge(df_ventas, df_costos, on=columnas_base, how='outer').fillna(0)

    df['margen_pct_anterior'] = (
        (1 - (df['costos_anterior'] / df['ventas_anterior'])) * 100
    ).replace([np.inf, -np.inf], 0).fillna(0).round(2)
    df['margen_pct_actual'] = (
        (1 - (df['costos_actual'] / df['ventas_actual'])) * 100
    ).replace([np.inf, -np.inf], 0).fillna(0).round(2)

    for col in ['ventas_anterior', 'ventas_actual', 'variacion_valor_ventas',
                'costos_anterior', 'costos_actual', 'variacion_valor_costos']:
        df[col] = df[col].round().astype(int)

    df = df.rename(columns={
        'nombre_linea_n1': 'linea',
        'nombre_centro_de_operacion': 'centro',
        'nombre_clase_cliente': 'segmento',
    })

    return JsonResponse({
        'year_anterior': year_anterior,
        'year_actual': year_actual,
        'data': df.to_dict(orient='records'),
    })

def vista_comparativo_anual(request):
    return render(request, 'presupuesto_comercial/presupuesto_comparativo_anual.html')

# Ajustar para que la suma sea igual a 100
def ajustar_porcentaje(grupo):
    suma_porcentajes = grupo['porcentaje_participacion'].sum()
    diferencia = 100 - suma_porcentajes

    # Si no hay diferencia, se devuelve el grupo sin cambios
    if diferencia == 0:
        return grupo
    
    # Buscar diciembre (mes 12)
    mask_diciembre = grupo['mes'] == 12

    if mask_diciembre.any():
        grupo.loc[mask_diciembre, 'porcentaje_participacion'] += diferencia
    else:
        # Si por algún motivo no existe mes 12, ajustar al último mes disponible
        idx_ultimo = grupo['mes'].idxmax()
        grupo.loc[idx_ultimo, 'porcentaje_participacion'] += diferencia

    return grupo

def _obtener_df_participacion_mensual():
    """
    Qué porcentaje de las ventas anuales de cada (línea, centro, segmento)
    cae en cada mes. La lógica vive en calculo._participacion_mensual, que
    usa bd_ventas_comercial; antes esta función leía BdVentas2025 fijo.
    """
    return calculo._participacion_mensual()

def actualizar_presupuesto_general_ventas(request):
    year_actual = timezone.now().year
    year_siguiente = year_actual + 1

    total_siguiente = PresupuestoComercial.objects.filter(year=year_actual).aggregate(
        total_proyectado=Sum("proyeccion_ventas")
    )["total_proyectado"] or 0
    PresupuestoGeneralVentas.objects.filter(year=year_siguiente).update(total_proyectado=total_siguiente)

    df_final = _obtener_df_participacion_mensual()

    proyecciones_qs = (
        PresupuestoComercial.objects.filter(year=year_actual)
        .values("linea", "nombre_centro_de_operacion", "nombre_clase_cliente")
        .annotate(total_proyectado=Sum("proyeccion_ventas"))
    )
    # FIX: índice O(1) en vez de next(...) sobre la lista completa por cada fila.
    indice_proyecciones = indice_por_clave(
        proyecciones_qs, ["linea", "nombre_centro_de_operacion", "nombre_clase_cliente"]
    )

    for idx, row in df_final.iterrows():
        clave = (row["nombre_linea_n1"], row["nombre_centro_de_operacion"], row["nombre_clase_cliente"])
        proyeccion_item = indice_proyecciones.get(clave)
        total_proyectado = proyeccion_item["total_proyectado"] or 0 if proyeccion_item else 0
        porcentaje = row["porcentaje_participacion"] or 0
        df_final.loc[idx, 'valor_proyectado_mes'] = round((porcentaje / 100) * total_proyectado)

    totales_por_mes_agrupado = df_final.groupby(['year', 'mes'])['valor_proyectado_mes'].sum().reset_index()
    for _, row in totales_por_mes_agrupado.iterrows():
        PresupuestoGeneralVentas.objects.filter(year=year_siguiente, mes=row["mes"]).update(
            total=row["valor_proyectado_mes"] or 0
        )

    total_anual_siguiente = PresupuestoGeneralVentas.objects.filter(year=year_siguiente).aggregate(
        total_year=Sum('total')
    )['total_year'] or 0
    PresupuestoGeneralVentas.objects.filter(year=year_siguiente).update(total_year=total_anual_siguiente)

    # FIX: índices por mes en vez de next(...) (aquí n es pequeño, 12
    # meses, pero se deja consistente con el resto y sin costo extra real).
    indice_costos_mes = indice_por_clave(
        PresupuestoGeneralCostos.objects.filter(year=year_actual).values("mes", "total").distinct(), ["mes"]
    )
    indice_ventas_siguiente_mes = indice_por_clave(
        PresupuestoGeneralVentas.objects.filter(year=year_siguiente).values("mes", "total").distinct(), ["mes"]
    )
    ventas_actuales_por_mes = PresupuestoGeneralVentas.objects.filter(year=year_actual).values("mes", "total").distinct()

    for venta_item in ventas_actuales_por_mes:
        mes = venta_item["mes"]
        total_ventas_mes = venta_item["total"] or 0
        costo_item = indice_costos_mes.get((mes,))
        venta_siguiente_item = indice_ventas_siguiente_mes.get((mes,))
        total_costos_mes = costo_item["total"] or 0 if costo_item else 0

        utilidad_pct_mes = round(1 - (total_costos_mes / total_ventas_mes), 4) if total_ventas_mes else 0
        utilidad_valor_mes = round(venta_siguiente_item["total"] * utilidad_pct_mes) if venta_siguiente_item else 0
        utilidad_pct_mes = utilidad_pct_mes * 100 if total_ventas_mes else 0

        PresupuestoGeneralVentas.objects.filter(year=year_siguiente, mes=mes).update(
            utilidad_valor=utilidad_valor_mes, utilidad_pct=round(utilidad_pct_mes, 2)
        )

    return JsonResponse({"status": "ok", "mensaje": "Presupuesto general de ventas actualizado ✅"})

def actualizar_presupuesto_centro_ventas(request):
    year_actual = timezone.now().year
    year_siguiente = year_actual + 1

    proyecciones_centro_qs = (
        PresupuestoComercial.objects.filter(year=year_actual)
        .values("nombre_centro_de_operacion")
        .annotate(total_proyectado=Sum("proyeccion_ventas"))
    )
    for item in proyecciones_centro_qs:
        PresupuestoCentroOperacionVentas.objects.filter(
            year=year_siguiente, nombre_centro_operacion=item["nombre_centro_de_operacion"]
        ).update(total_proyectado=item["total_proyectado"] or 0)

    df_final = _obtener_df_participacion_mensual()

    proyecciones_qs = (
        PresupuestoComercial.objects.filter(year=year_actual)
        .values("linea", "nombre_centro_de_operacion", "nombre_clase_cliente")
        .annotate(total_proyectado=Sum("proyeccion_ventas"))
    )
    # FIX: índice O(1) en vez de next(...) por cada fila de df_final.
    indice_proyecciones = indice_por_clave(
        proyecciones_qs, ["linea", "nombre_centro_de_operacion", "nombre_clase_cliente"]
    )

    for idx, row in df_final.iterrows():
        clave = (row["nombre_linea_n1"], row["nombre_centro_de_operacion"], row["nombre_clase_cliente"])
        proyeccion_item = indice_proyecciones.get(clave)
        total_proyectado = proyeccion_item["total_proyectado"] or 0 if proyeccion_item else 0
        porcentaje = row["porcentaje_participacion"] or 0
        df_final.loc[idx, 'valor_proyectado_mes'] = round((porcentaje / 100) * total_proyectado)

    totales_por_mes_agrupado = (
        df_final.groupby(['year', 'mes', 'nombre_centro_de_operacion'])['valor_proyectado_mes'].sum().reset_index()
    )
    for _, row in totales_por_mes_agrupado.iterrows():
        PresupuestoCentroOperacionVentas.objects.filter(
            year=year_siguiente, mes=row["mes"], nombre_centro_operacion=row["nombre_centro_de_operacion"]
        ).update(total=row["valor_proyectado_mes"] or 0)

    total_anual_siguiente = (
        PresupuestoCentroOperacionVentas.objects.filter(year=year_siguiente)
        .values('nombre_centro_operacion').annotate(total_year=Sum('total'))
    )
    for item in total_anual_siguiente:
        PresupuestoCentroOperacionVentas.objects.filter(
            year=year_siguiente, nombre_centro_operacion=item['nombre_centro_operacion']
        ).update(total_year=item['total_year'] or 0)

    # FIX: índices por centro+mes en vez de next(...) dentro del bucle.
    indice_costos = indice_por_clave(
        PresupuestoCentroOperacionCostos.objects.filter(year=year_actual)
        .values("mes", "nombre_centro_operacion", "total").distinct(),
        ["mes", "nombre_centro_operacion"],
    )
    indice_ventas_siguiente = indice_por_clave(
        PresupuestoCentroOperacionVentas.objects.filter(year=year_siguiente)
        .values("mes", "nombre_centro_operacion", "total").distinct(),
        ["mes", "nombre_centro_operacion"],
    )
    ventas_actuales = PresupuestoCentroOperacionVentas.objects.filter(year=year_actual).values(
        "mes", "nombre_centro_operacion", "total"
    ).distinct()

    for venta_item in ventas_actuales:
        mes = venta_item["mes"]
        centro = venta_item["nombre_centro_operacion"]
        total_ventas_mes = venta_item["total"] or 0
        costo_item = indice_costos.get((mes, centro))
        venta_siguiente_item = indice_ventas_siguiente.get((mes, centro))
        total_costos_mes = costo_item["total"] or 0 if costo_item else 0

        utilidad_pct_mes = round(1 - (total_costos_mes / total_ventas_mes), 4) if total_ventas_mes else 0
        utilidad_valor_mes = round(venta_siguiente_item["total"] * utilidad_pct_mes) if venta_siguiente_item else 0
        utilidad_pct_mes = utilidad_pct_mes * 100 if total_ventas_mes else 0

        PresupuestoCentroOperacionVentas.objects.filter(
            year=year_siguiente, mes=mes, nombre_centro_operacion=centro
        ).update(utilidad_valor=utilidad_valor_mes, utilidad_pct=round(utilidad_pct_mes, 2))

    return JsonResponse({"status": "ok", "mensaje": "Presupuesto por centro de operación actualizado ✅"})

def actualizar_presupuesto_centro_segmento_ventas(request):
    year_actual = timezone.now().year
    year_siguiente = year_actual + 1

    proyecciones_cs_qs = (
        PresupuestoComercial.objects.filter(year=year_actual)
        .values("nombre_centro_de_operacion", "nombre_clase_cliente")
        .annotate(total_proyectado=Sum("proyeccion_ventas"))
    )
    for item in proyecciones_cs_qs:
        PresupuestoCentroSegmentoVentas.objects.filter(
            year=year_siguiente,
            nombre_centro_operacion=item["nombre_centro_de_operacion"],
            segmento=item["nombre_clase_cliente"],
        ).update(total_proyectado=item["total_proyectado"] or 0)

    df_final = _obtener_df_participacion_mensual()

    proyecciones_qs = (
        PresupuestoComercial.objects.filter(year=year_actual)
        .values("linea", "nombre_centro_de_operacion", "nombre_clase_cliente")
        .annotate(total_proyectado=Sum("proyeccion_ventas"))
    )
    # FIX 1: índice O(1) en vez de next(...) por cada fila de df_final.
    indice_proyecciones = indice_por_clave(
        proyecciones_qs, ["linea", "nombre_centro_de_operacion", "nombre_clase_cliente"]
    )

    for idx, row in df_final.iterrows():
        clave = (row["nombre_linea_n1"], row["nombre_centro_de_operacion"], row["nombre_clase_cliente"])
        proyeccion_item = indice_proyecciones.get(clave)
        total_proyectado = proyeccion_item["total_proyectado"] or 0 if proyeccion_item else 0
        porcentaje = row["porcentaje_participacion"] or 0
        df_final.loc[idx, 'valor_proyectado_mes'] = round((porcentaje / 100) * total_proyectado)

    totales_por_mes_agrupado = (
        df_final.groupby(['year', 'mes', 'nombre_centro_de_operacion', 'nombre_clase_cliente'])
        ['valor_proyectado_mes'].sum().reset_index()
    )
    for _, row in totales_por_mes_agrupado.iterrows():
        PresupuestoCentroSegmentoVentas.objects.filter(
            year=year_siguiente, mes=row["mes"],
            nombre_centro_operacion=row["nombre_centro_de_operacion"],
            segmento=row["nombre_clase_cliente"],
        ).update(total=row["valor_proyectado_mes"] or 0)

    total_anual_siguiente = (
        PresupuestoCentroSegmentoVentas.objects.filter(year=year_siguiente)
        .values('nombre_centro_operacion', 'segmento').annotate(total_year=Sum('total'))
    )
    for item in total_anual_siguiente:
        PresupuestoCentroSegmentoVentas.objects.filter(
            year=year_siguiente,
            nombre_centro_operacion=item['nombre_centro_operacion'], segmento=item['segmento'],
        ).update(total_year=item['total_year'] or 0)

    # FIX 2: índices por (mes, centro, segmento) — este bucle sí podía
    # llegar a cientos de combinaciones, así que era el candidato más
    # real a notarse lento en producción.
    indice_costos = indice_por_clave(
        PresupuestoCentroSegmentoCostos.objects.filter(year=year_actual)
        .values("mes", "nombre_centro_operacion", "segmento", "total").distinct(),
        ["mes", "nombre_centro_operacion", "segmento"],
    )
    indice_ventas_siguiente = indice_por_clave(
        PresupuestoCentroSegmentoVentas.objects.filter(year=year_siguiente)
        .values("mes", "nombre_centro_operacion", "segmento", "total").distinct(),
        ["mes", "nombre_centro_operacion", "segmento"],
    )
    ventas_actuales = PresupuestoCentroSegmentoVentas.objects.filter(year=year_actual).values(
        "mes", "nombre_centro_operacion", "segmento", "total"
    ).distinct()

    for venta_item in ventas_actuales:
        mes = venta_item["mes"]
        centro = venta_item["nombre_centro_operacion"]
        segmento = venta_item["segmento"]
        total_ventas_mes = venta_item["total"] or 0
        costo_item = indice_costos.get((mes, centro, segmento))
        venta_siguiente_item = indice_ventas_siguiente.get((mes, centro, segmento))
        total_costos_mes = costo_item["total"] or 0 if costo_item else 0

        utilidad_pct_mes = round(1 - (total_costos_mes / total_ventas_mes), 4) if total_ventas_mes else 0
        utilidad_valor_mes = round(venta_siguiente_item["total"] * utilidad_pct_mes) if venta_siguiente_item else 0
        utilidad_pct_mes = utilidad_pct_mes * 100 if total_ventas_mes else 0

        PresupuestoCentroSegmentoVentas.objects.filter(
            year=year_siguiente, mes=mes, nombre_centro_operacion=centro, segmento=segmento
        ).update(utilidad_valor=utilidad_valor_mes, utilidad_pct=round(utilidad_pct_mes, 2))

    # Promedio de utilidad (jul-sep) aplicado a oct-dic — igual que el original.
    promedios_utilidad = (
        PresupuestoCentroSegmentoVentas.objects.filter(year=year_siguiente, mes__in=[7, 8, 9])
        .values("nombre_centro_operacion", "segmento").annotate(promedio_utilidad=Avg("utilidad_pct"))
    )
    for p in promedios_utilidad:
        registros_nd = list(PresupuestoCentroSegmentoVentas.objects.filter(
            year=year_siguiente, mes__in=[10, 11, 12],
            nombre_centro_operacion=p["nombre_centro_operacion"], segmento=p["segmento"],
        ))
        promedio_utilidad_pct = p["promedio_utilidad"] or 0
        for registro in registros_nd:
            registro.utilidad_pct = promedio_utilidad_pct
            registro.utilidad_valor = round((registro.total or 0) * (promedio_utilidad_pct / 100))
        # mejora menor: un solo bulk_update en vez de N .save() individuales
        if registros_nd:
            PresupuestoCentroSegmentoVentas.objects.bulk_update(registros_nd, ["utilidad_pct", "utilidad_valor"])

    return JsonResponse({
        "status": "ok", "mensaje": "Presupuesto por centro y segmento actualizado y distribuido por mes ✅",
    })

def actualizar_presupuesto_centro_segmento_linea_ventas(request):
    year_actual = timezone.now().year
    year_siguiente = year_actual + 1

    proyecciones_csl_qs = (
        PresupuestoComercial.objects.filter(year=year_actual)
        .values("nombre_centro_de_operacion", "nombre_clase_cliente", "linea")
        .annotate(total_proyectado=Sum("proyeccion_ventas"))
    )
    for item in proyecciones_csl_qs:
        PresupuestoCentroSegLineaVentas.objects.filter(
            year=year_siguiente,
            nombre_centro_operacion=item["nombre_centro_de_operacion"],
            segmento=item["nombre_clase_cliente"],
            linea=item["linea"],
        ).update(total_proyectado=item["total_proyectado"] or 0)

    df_final = _obtener_df_participacion_mensual()

    proyecciones_qs = (
        PresupuestoComercial.objects.filter(year=year_actual)
        .values("linea", "nombre_centro_de_operacion", "nombre_clase_cliente")
        .annotate(total_proyectado=Sum("proyeccion_ventas"))
    )
    # FIX 1: índice O(1) en vez de next(...) por cada fila de df_final.
    indice_proyecciones = indice_por_clave(
        proyecciones_qs, ["linea", "nombre_centro_de_operacion", "nombre_clase_cliente"]
    )

    for idx, row in df_final.iterrows():
        clave = (row["nombre_linea_n1"], row["nombre_centro_de_operacion"], row["nombre_clase_cliente"])
        proyeccion_item = indice_proyecciones.get(clave)
        total_proyectado = proyeccion_item["total_proyectado"] or 0 if proyeccion_item else 0
        porcentaje = row["porcentaje_participacion"] or 0
        df_final.loc[idx, 'valor_proyectado_mes'] = round((porcentaje / 100) * total_proyectado)

    totales_por_mes_agrupado = (
        df_final.groupby(['year', 'mes', 'nombre_centro_de_operacion', 'nombre_clase_cliente', 'nombre_linea_n1'])
        ['valor_proyectado_mes'].sum().reset_index()
    )
    for _, row in totales_por_mes_agrupado.iterrows():
        PresupuestoCentroSegLineaVentas.objects.filter(
            year=year_siguiente, mes=row["mes"],
            nombre_centro_operacion=row["nombre_centro_de_operacion"],
            segmento=row["nombre_clase_cliente"], linea=row["nombre_linea_n1"],
        ).update(total=row["valor_proyectado_mes"] or 0)

    total_anual_siguiente = (
        PresupuestoCentroSegLineaVentas.objects.filter(year=year_siguiente)
        .values('nombre_centro_operacion', 'segmento', 'linea').annotate(total_year=Sum('total'))
    )
    for item in total_anual_siguiente:
        PresupuestoCentroSegLineaVentas.objects.filter(
            year=year_siguiente, nombre_centro_operacion=item['nombre_centro_operacion'],
            segmento=item['segmento'], linea=item['linea'],
        ).update(total_year=item['total_year'] or 0)

    # FIX 2: índices por (mes, centro, segmento, línea) — el bucle con
    # más combinaciones posibles de las 4 vistas "actualizar_*".
    indice_costos = indice_por_clave(
        PresupuestoCentroSegLineaCostos.objects.filter(year=year_actual)
        .values("mes", "nombre_centro_operacion", "segmento", "linea", "total").distinct(),
        ["mes", "nombre_centro_operacion", "segmento", "linea"],
    )
    indice_ventas_siguiente = indice_por_clave(
        PresupuestoCentroSegLineaVentas.objects.filter(year=year_siguiente)
        .values("mes", "nombre_centro_operacion", "segmento", "linea", "total").distinct(),
        ["mes", "nombre_centro_operacion", "segmento", "linea"],
    )
    ventas_actuales = PresupuestoCentroSegLineaVentas.objects.filter(year=year_actual).values(
        "mes", "nombre_centro_operacion", "segmento", "linea", "total"
    ).distinct()

    for venta_item in ventas_actuales:
        mes = venta_item["mes"]
        centro = venta_item["nombre_centro_operacion"]
        segmento = venta_item["segmento"]
        linea = venta_item["linea"]
        total_ventas_mes = venta_item["total"] or 0
        costo_item = indice_costos.get((mes, centro, segmento, linea))
        venta_siguiente_item = indice_ventas_siguiente.get((mes, centro, segmento, linea))
        total_costos_mes = costo_item["total"] or 0 if costo_item else 0

        utilidad_pct_mes = round(1 - (total_costos_mes / total_ventas_mes), 4) if total_ventas_mes else 0
        utilidad_valor_mes = round(venta_siguiente_item["total"] * utilidad_pct_mes) if venta_siguiente_item else 0
        utilidad_pct_mes = utilidad_pct_mes * 100 if total_ventas_mes else 0

        PresupuestoCentroSegLineaVentas.objects.filter(
            year=year_siguiente, mes=mes, nombre_centro_operacion=centro, segmento=segmento, linea=linea,
        ).update(utilidad_valor=utilidad_valor_mes, utilidad_pct=round(utilidad_pct_mes, 2))

    # Promedio de utilidad (jul-sep) aplicado a oct-dic — igual que el original.
    promedios_utilidad = (
        PresupuestoCentroSegLineaVentas.objects.filter(year=year_siguiente, mes__in=[7, 8, 9])
        .values("nombre_centro_operacion", "segmento", "linea")
        .annotate(promedio_utilidad=Avg("utilidad_pct"))
    )
    for p in promedios_utilidad:
        registros_ond = list(PresupuestoCentroSegLineaVentas.objects.filter(
            year=year_siguiente, mes__in=[10, 11, 12],
            nombre_centro_operacion=p["nombre_centro_operacion"],
            segmento=p["segmento"], linea=p["linea"],
        ))
        promedio_utilidad_pct = p["promedio_utilidad"] or 0
        for registro in registros_ond:
            registro.utilidad_pct = promedio_utilidad_pct
            registro.utilidad_valor = round((registro.total or 0) * (promedio_utilidad_pct / 100))
        if registros_ond:
            PresupuestoCentroSegLineaVentas.objects.bulk_update(registros_ond, ["utilidad_pct", "utilidad_valor"])

    return JsonResponse({
        "status": "ok", "mensaje": "Presupuesto por centro, segmento y línea actualizado y distribuido por mes ✅",
    })
   
@csrf_exempt
def importar_crecimiento_ventas(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'error': 'No se recibió archivo'}, status=400)

    try:
        df = pd.read_excel(file)
    except Exception as e:
        return JsonResponse({'error': f'Error al leer el archivo: {str(e)}'}, status=400)

    columnas_requeridas = [
        'linea',
        'año',
        'centro de operación',
        'clase cliente',
        'crecimiento ventas proyectado'
    ]
    faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if faltantes:
        return JsonResponse({'error': f'Faltan columnas en el Excel: {", ".join(faltantes)}'}, status=400)

    # 🔹 Limpieza y normalización
    df = df[columnas_requeridas].dropna(subset=['linea', 'año', 'centro de operación', 'clase cliente'])
    df['linea'] = df['linea'].astype(str).str.strip()
    df['centro de operación'] = df['centro de operación'].astype(str).str.strip()
    df['clase cliente'] = df['clase cliente'].astype(str).str.strip()

    try:
        df['año'] = df['año'].astype(int)
    except ValueError:
        return JsonResponse({'error': 'La columna "año" debe contener solo números enteros'}, status=400)

    try:
        df['crecimiento ventas proyectado'] = df['crecimiento ventas proyectado'].astype(float)
    except ValueError:
        return JsonResponse({'error': 'La columna "crecimiento ventas proyectado" debe ser numérica'}, status=400)

    actualizados = 0
    no_encontrados = []

    with transaction.atomic():
        for _, row in df.iterrows():
            obj = PresupuestoComercial.objects.filter(
                linea=row['linea'],
                year=row['año'],
                nombre_centro_de_operacion=row['centro de operación'],
                nombre_clase_cliente=row['clase cliente']
            ).first()

            if obj:
                crecimiento = row['crecimiento ventas proyectado']
                obj.crecimiento_ventas = crecimiento

                # 🔹 Calcular proyección de ventas
                proyeccion_ventas = obj.ventas + (obj.ventas * (crecimiento / 100))
                obj.proyeccion_ventas = round(proyeccion_ventas)

                # 🔹 Calcular utilidad proyectada
                utilidad_valor = obj.proyeccion_ventas - obj.proyeccion_costos
                obj.utilidad_valor = round(utilidad_valor)

                # 🔹 Calcular utilidad porcentual
                obj.utilidad_porcentual = (
                    (utilidad_valor / obj.proyeccion_ventas) * 100 if obj.proyeccion_ventas != 0 else 0
                )

                # 🔹 Calcular variaciones proyectadas
                obj.variacion_proyectada_valor = obj.utilidad_valor - obj.utilidad_valor_actual
                obj.variacion_proyectada_porcentual = (
                    obj.utilidad_porcentual - obj.utilidad_porcentual_actual
                )

                obj.save(update_fields=[
                    'crecimiento_ventas',
                    'proyeccion_ventas',
                    'utilidad_valor',
                    'utilidad_porcentual',
                    'variacion_proyectada_valor',
                    'variacion_proyectada_porcentual'
                ])
                actualizados += 1
            else:
                no_encontrados.append({
                    'linea': row['linea'],
                    'año': row['año'],
                    'centro': row['centro de operación'],
                    'clase': row['clase cliente']
                })

    mensaje = f"✅ {actualizados} registros actualizados correctamente."
    if no_encontrados:
        mensaje += f" ⚠️ {len(no_encontrados)} filas no se encontraron en la base de datos."

    return JsonResponse({'mensaje': mensaje})

def exportar_crecimiento_ventas(request):
    year_actual = timezone.now().year

    # 🔹 Consultar datos del año actual con el nuevo campo incluido
    qs = PresupuestoComercial.objects.filter(year=year_actual).values(
        'linea',
        'year',
        'nombre_centro_de_operacion',
        'nombre_clase_cliente',
        'crecimiento_ventas',
    )

    if not qs.exists():
        return HttpResponse("No hay datos para exportar", status=400)

    # 🔹 Convertir a DataFrame
    df = pd.DataFrame(qs)

    # Renombrar columnas para el Excel final
    df.rename(columns={
        'year': 'año',
        'nombre_centro_de_operacion': 'centro de operación',
        'nombre_clase_cliente': 'clase cliente',
        'crecimiento_ventas': 'crecimiento ventas proyectado',
    }, inplace=True)

    # 🔹 Crear archivo Excel
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="crecimiento_ventas_2025.xlsx"'

    df.to_excel(response, index=False)

    return response

def obtener_presupuesto_comercial(request):
    return JsonResponse(calculo._a_registros(calculo.calcular_comercial()), safe=False)

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
    
    # agrupar por area PROYECTO AFTOSA GASTOS DE PERSONAL
    aftosa = (PresupuestoSeguridadSocialAux.objects
        .filter(area__in=["PROYECTO AFTOSA GASTOS DE PERSONAL"])
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
    
    # insertar AFTOSA
    for item in aftosa:
        PresupuestoSeguridadSocialAux.objects.create(
            nombre="SEGURIDAD SOCIAL",
            centro="",  # omitimos centro
            area=item["area"],  # mantenemos el nombre de área original
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
        area__in=["PROYECTO AFTOSA GASTOS DE PERSONAL"]
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


# ---------------------------------------------------------------------------
# Configuración centralizada por sede
# ---------------------------------------------------------------------------
 
FECHA_LIMITE_DEFAULT = datetime.date(2025, 10, 30)
 
def _fecha_limite_auxiliar(config):
    return config.get("fecha_limite_auxiliar", FECHA_LIMITE_DEFAULT)
 
def _fecha_limite_aprobado(config):
    return config.get("fecha_limite_aprobado", FECHA_LIMITE_DEFAULT)
 
# Campos de negocio compartidos por los 3 modelos (temp/oficial/aprobado)
# de cada sede. Se define una sola vez para no repetir la lista 3+ veces.
CAMPOS_PRESUPUESTO = [
    "centro_tra", "nombre_cen", "codcosto", "responsable", "cuenta",
    "cuenta_mayor", "detalle_cuenta", "sede_distribucion", "proveedor",
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    "total", "comentario",
]
MESES = CAMPOS_PRESUPUESTO[9:21]
CAMPOS_BASE_PLANTILLA = [c for c in CAMPOS_PRESUPUESTO if c not in ("total", "comentario")]
CAMPOS_NUMERICOS = ["cuenta", "sede_distribucion"] + MESES + ["total"]
SEDE_CONFIG = {
    "almacen-tulua": {
        "label": "Almacén Tuluá",
        "usuarios_permitidos": {"admin", "JEFEALMACENTULUA", "DBENITEZ", "NICOLAS"},
        "responsable_filtro": "JEFE ALMACEN TULUA",
        "model_oficial": PresupuestoAlmacenTulua,
        "model_aprobado": PresupuestoAlmacenTuluaAprobado,
        "model_temp": PresupuestoAlmacenTuluaAux,
        "fecha_limite_auxiliar": datetime.date(2027, 10, 15),  
        "fecha_limite_aprobado": datetime.date(2027, 10, 30),
    },
    "almacen-buga": {
        "label": "Almacén Buga",
        "usuarios_permitidos": {"admin", "JEFEALMACENBUGA", "FDUQUE", "NICOLAS"},
        "responsable_filtro": "JEFE ALMACEN BUGA",
        "model_oficial": PresupuestoAlmacenBuga,
        "model_aprobado": PresupuestoAlmacenBugaAprobado,
        "model_temp": PresupuestoAlmacenBugaAux,
        "fecha_limite_auxiliar": datetime.date(2027, 10, 15),  
        "fecha_limite_aprobado": datetime.date(2027, 10, 30),
    },
    "almacen-cartago": {
        "label": "Almacén Cartago",
        "usuarios_permitidos": {"admin", "JEFEALMACENCARTAGO", "CHINCAPI", "NICOLAS"},
        "responsable_filtro": "JEFE ALMACEN CARTAGO",
        "model_oficial": PresupuestoAlmacenCartago,
        "model_aprobado": PresupuestoAlmacenCartagoAprobado,
        "model_temp": PresupuestoAlmacenCartagoAux,
        "fecha_limite_auxiliar": datetime.date(2027, 10, 15),
        "fecha_limite_aprobado": datetime.date(2027, 10, 30),
    },
    "almacen-cali": {
        "label": "Almacén Cali",
        "usuarios_permitidos": {"admin", "JEFEALMACENCALI", "LAMAYA", "NICOLAS"},
        "responsable_filtro": "JEFE ALMACEN CALI",
        "model_oficial": PresupuestoAlmacenCali,
        "model_aprobado": PresupuestoAlmacenCaliAprobado,
        "model_temp": PresupuestoAlmacenCaliAux,
        "fecha_limite_auxiliar": datetime.date(2027, 10, 15),
        "fecha_limite_aprobado": datetime.date(2027, 10, 30),
    },
    "comunicaciones": {
        "label": "Comunicaciones y Mercadeo",
        "usuarios_permitidos": {"admin", "COMUNICACIONES", "NICOLAS"},
        "responsable_filtro": "CARLOS USMAN",
        "model_oficial": PresupuestoComunicaciones,
        "model_aprobado": PresupuestoComunicacionesAprobado,
        "model_temp": PresupuestoComunicacionesAux,
        "fecha_limite_auxiliar": datetime.date(2027, 10, 8),
        "fecha_limite_aprobado": datetime.date(2027, 10, 30),
    },
    "comercial-costos": {
        "label": "Comercial y Costos",
        "usuarios_permitidos": {"admin", "COMERCIALCOSTOS", "EVALENCIA", "NICOLAS"},
        "responsable_filtro": "EVALENCIA",
        "model_oficial": PresupuestoComercialCostos,
        "model_aprobado": PresupuestoComercialCostosAprobado,
        "model_temp": PresupuestoComercialCostosAux,
        "fecha_limite_auxiliar": datetime.date(2027, 10, 8),
        "fecha_limite_aprobado": datetime.date(2027, 10, 30),
    },
    "contabilidad": {
        "label": "Contabilidad",
        "usuarios_permitidos": {"admin", "CONTABILIDAD", "NICOLAS"},
        "responsable_filtro": "CONTABILIDAD",
        "model_oficial": PresupuestoContabilidad,
        "model_aprobado": PresupuestoContabilidadAprobado,
        "model_temp": PresupuestoContabilidadAux,
        "fecha_limite_auxiliar": datetime.date(2027, 10, 8),
        "fecha_limite_aprobado": datetime.date(2027, 10, 30),
    },
    "gerencia": {
        "label": "Gerencia",
        "usuarios_permitidos": {"admin", "GERENCIA", "NICOLAS"},
        "responsable_filtro": "GERENCIA",
        "model_oficial": PresupuestoGerencia,
        "model_aprobado": PresupuestoGerenciaAprobado,
        "model_temp": PresupuestoGerenciaAux,
        "fecha_limite_auxiliar": datetime.date(2027, 10, 8),
        "fecha_limite_aprobado": datetime.date(2027, 10, 30),
    },
    "gestion-humana": {
        "label": "Gestión Humana",
        "usuarios_permitidos": {"admin", "GESTIONHUMANA", "NICOLAS"},
        "responsable_filtro": "MARTA GH",
        "model_oficial": PresupuestoGH,
        "model_aprobado": PresupuestoGHAprobado,
        "model_temp": PresupuestoGHAux,
        "fecha_limite_auxiliar": datetime.date(2027, 10, 15),
        "fecha_limite_aprobado": datetime.date(2027, 10, 30),
    },
    "gestion-riesgos": {
        "label": "Gestión de Riesgos",
        "usuarios_permitidos": {"admin", "GESTIONRIESGOS", "NICOLAS"},
        "responsable_filtro": "LINA RICARDO",
        "model_oficial": PresupuestoGestionRiesgos,
        "model_aprobado": PresupuestoGestionRiesgosAprobado,
        "model_temp": PresupuestoGestionRiesgosAux,
        "fecha_limite_auxiliar": datetime.date(2027, 10, 15),
        "fecha_limite_aprobado": datetime.date(2027, 10, 30),
    },
    "logistica": {
        "label": "Logística",
        "usuarios_permitidos": {"admin", "PLOZANO", "NICOLAS"},
        "responsable_filtro": "PILAR LOZANO",
        "model_oficial": PresupuestoLogistica,
        "model_aprobado": PresupuestoLogisticaAprobado,
        "model_temp": PresupuestoLogisticaAux,
        "fecha_limite_auxiliar": datetime.date(2027, 10, 15),
        "fecha_limite_aprobado": datetime.date(2027, 10, 30),
    },
    "servicios-tecnicos": {
        "label": "Servicios Técnicos",
        "usuarios_permitidos": {"admin", "SERVICIOSTECNICOS", "NICOLAS"},
        "responsable_filtro": "JORGE GUERRERO",
        "model_oficial": PresupuestoServiciosTecnicos,
        "model_aprobado": PresupuestoServiciosTecnicosAprobado,
        "model_temp": PresupuestoServiciosTecnicosAux,
        "fecha_limite_auxiliar": datetime.date(2027, 10, 15),
        "fecha_limite_aprobado": datetime.date(2027, 10, 30),
    },
    "salud-ocupacional": {
        "label": "Salud Ocupacional",
        "usuarios_permitidos": {"admin", "SALUDOCUPACIONAL", "NICOLAS"},
        "responsable_filtro": "SALUD OCUPACIONAL",
        "model_oficial": PresupuestoOcupacional,
        "model_aprobado": PresupuestoOcupacionalAprobado,
        "model_temp": PresupuestoOcupacionalAux,
        "fecha_limite_auxiliar": datetime.date(2027, 10, 15),
        "fecha_limite_aprobado": datetime.date(2027, 10, 30),
    },
    "tecnologia": {
        "label": "Tecnología",
        "usuarios_permitidos": {"admin", "TECNOLOGIA", "NICOLAS"},
        "responsable_filtro": "DIEGO CANO",
        "model_oficial": PresupuestoTecnologia,
        "model_aprobado": PresupuestotecnologiaAprobado,
        "model_temp": PresupuestoTecnologiaAux,
        "fecha_limite_auxiliar": datetime.date(2027, 10, 15),
        "fecha_limite_aprobado": datetime.date(2027, 10, 30),
    },
}
 
def _config_sede(sede):
    """Devuelve la configuración de la sede o None si no existe."""
    return SEDE_CONFIG.get(sede)
 
def _usuario_autorizado(request, config):
    return request.user.username in config["usuarios_permitidos"]
 
def _defaults_desde_temp(temp_obj, version, fecha):
    """Construye el dict `defaults` para update_or_create a partir de un
    registro temporal. Se reutiliza para la tabla oficial y la aprobada,
    en vez de escribir el mismo dict de 19 campos dos veces."""
    data = {campo: getattr(temp_obj, campo) for campo in CAMPOS_PRESUPUESTO}
    data["version"] = version
    data["fecha"] = fecha
    return data
# FIN DE CONFIGURACIÓN CENTRALIZADA POR SEDE---------------------------------------

# ---------------------------------------------------------------------------
# Vistas genéricas (una sola implementación para todas las sedes)
# ---------------------------------------------------------------------------
@login_required
def presupuesto_sede(request, sede):
    config = _config_sede(sede)
    if not config:
        return HttpResponseForbidden("⛔ Sede no configurada.")
    if not _usuario_autorizado(request, config):
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
 
    versiones = list(
        config["model_oficial"].objects
        .values_list("version", flat=True)
        .distinct()
        .order_by("version")
    )
    ultima_version = max(versiones) if versiones else 1
    return render(request, "presupuesto_general/presupuesto_sede_readonly.html", {
        "sede": sede,
        "sede_label": config["label"],
        "modo": "proyectado",
        "versiones": versiones,
        "ultima_version": ultima_version,
    })
 
 
def obtener_presupuesto_sede(request, sede):
    config = _config_sede(sede)
    if not config:
        return JsonResponse({"error": "Sede no configurada"}, status=404)
 
    version = request.GET.get("version")
    qs = config["model_oficial"].objects.all()
    if version:
        qs = qs.filter(version=version)
    return JsonResponse({"data": list(qs.values())}, safe=False)
  
def presupuesto_aprobado_sede(request, sede):
    config = _config_sede(sede)
    if not config:
        return HttpResponseForbidden("⛔ Sede no configurada.")
 
    versiones = config["model_aprobado"].objects.values_list("version", flat=True).distinct()
    ultima_version = max(versiones) if versiones else 1
    return render(request, "presupuesto_general/presupuesto_sede_readonly.html", {
        "sede": sede,
        "sede_label": config["label"],
        "modo": "aprobado",
        "ultima_version": ultima_version,
    })
 
def obtener_presupuesto_aprobado_sede(request, sede):
    config = _config_sede(sede)
    if not config:
        return JsonResponse({"error": "Sede no configurada"}, status=404)
 
    versiones = config["model_aprobado"].objects.values_list("version", flat=True).distinct()
    ultima_version = max(versiones) if versiones else 1
    qs = config["model_aprobado"].objects.filter(version=ultima_version)
    return JsonResponse({"data": list(qs.values())}, safe=False)
 
@login_required
def tabla_auxiliar_sede(request, sede):
    config = _config_sede(sede)
    if not config:
        return HttpResponseForbidden("⛔ Sede no configurada.")
    if not _usuario_autorizado(request, config):
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
 
    fecha_limite = _fecha_limite_auxiliar(config)
    hoy = timezone.now().date()
    if hoy > fecha_limite:
        return HttpResponseForbidden(
            "⛔ El acceso a esta vista está bloqueado después del "
            f"{fecha_limite.strftime('%d/%m/%Y')}"
        )
    return render(request, "presupuesto_general/aux_presupuesto_almacen_sede.html", {
        "sede": sede,
        "sede_label": config["label"],
    })
 
def obtener_temp_sede(request, sede):
    config = _config_sede(sede)
    if not config:
        return JsonResponse({"error": "Sede no configurada"}, status=404)
    return JsonResponse(list(config["model_temp"].objects.values()), safe=False)
 
@login_required
def guardar_temp_sede(request, sede):
    config = _config_sede(sede)
    if not config:
        return JsonResponse({"status": "error", "message": "Sede no configurada"}, status=404)
    if not _usuario_autorizado(request, config):
        return JsonResponse({"status": "error", "message": "Sin permisos"}, status=403)
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)
 
    try:
        data = json.loads(request.body.decode("utf-8"))
        model_temp = config["model_temp"]
        registros = []
        for row in data:
            row_filtrado = {campo: row.get(campo) for campo in CAMPOS_PRESUPUESTO}
            for campo in CAMPOS_NUMERICOS:
                if row_filtrado.get(campo) in (None, ""):
                    row_filtrado[campo] = 0
            registros.append(model_temp(**row_filtrado))
 
        with transaction.atomic():
            model_temp.objects.all().delete()
            model_temp.objects.bulk_create(registros)
 
        return JsonResponse({"status": "ok", "msg": f"{len(registros)} filas guardadas ✅"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)
 
@login_required
def cargar_base_sede(request, sede):
    config = _config_sede(sede)
    if not config:
        return JsonResponse({"status": "error", "message": "Sede no configurada"}, status=404)
    if not _usuario_autorizado(request, config):
        return JsonResponse({"status": "error", "message": "Sin permisos"}, status=403)
 
    model_temp = config["model_temp"]
    base_qs = Plantillagastos2025.objects.filter(
        responsable__iexact=config["responsable_filtro"]
    ).values(*CAMPOS_BASE_PLANTILLA)
 
    nuevos = []
    for row in base_qs:
        fila = dict(row)
        fila["total"] = sum(fila[m] for m in MESES)
        fila["comentario"] = ""
        nuevos.append(model_temp(**fila))
 
    with transaction.atomic():
        model_temp.objects.all().delete()
        model_temp.objects.bulk_create(nuevos)
 
    return JsonResponse({"status": "ok", "msg": f"{len(nuevos)} filas cargadas desde plantilla 📂"})
 
@login_required
def subir_presupuesto_sede(request, sede):
    config = _config_sede(sede)
    if not config:
        return JsonResponse({"success": False, "msg": "Sede no configurada"}, status=404)
    if not _usuario_autorizado(request, config):
        return JsonResponse({"success": False, "msg": "Sin permisos"}, status=403)
    if request.method != "POST":
        return JsonResponse({"success": False, "msg": "Método no permitido"}, status=405)
 
    model_temp = config["model_temp"]
    model_oficial = config["model_oficial"]
    model_aprobado = config["model_aprobado"]
 
    temporales = model_temp.objects.all()
    if not temporales.exists():
        return JsonResponse({"success": False, "msg": "No hay datos temporales para subir ❌"}, status=400)
 
    fecha_hoy = timezone.now().date()
    fecha_limite_aprobado = _fecha_limite_aprobado(config)
    ultima_version = model_oficial.objects.aggregate(max_ver=models.Max("version"))["max_ver"] or 0
    nueva_version = ultima_version + 1
 
    with transaction.atomic():
        for temp in temporales:
            defaults = _defaults_desde_temp(temp, nueva_version, fecha_hoy)
            model_oficial.objects.update_or_create(id=temp.id, defaults=defaults)
            if fecha_hoy <= fecha_limite_aprobado:
                model_aprobado.objects.update_or_create(id=temp.id, defaults=defaults)
 
    return JsonResponse({
        "success": True,
        "msg": f"Presupuesto de {config['label']} actualizado ✅ (versión {nueva_version})",
    })
 
@login_required
def borrar_presupuesto_sede(request, sede):
    config = _config_sede(sede)
    if not config:
        return JsonResponse({"status": "error", "message": "Sede no configurada"}, status=404)
    if not _usuario_autorizado(request, config):
        return JsonResponse({"status": "error", "message": "Sin permisos"}, status=403)
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)
 
    version = request.POST.get("version")
    if not version:
        return JsonResponse({"status": "error", "message": "No se especificó la versión"}, status=400)
 
    config["model_oficial"].objects.filter(version=version).delete()
    if timezone.now().date() <= _fecha_limite_aprobado(config):
        config["model_aprobado"].objects.filter(version=version).delete()
 
    return JsonResponse({"status": "ok", "message": f"Presupuesto de {config['label']} eliminado"})
 


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
def excel_serial_to_date(serial):
    if serial is None:
        return None
    try:
        base_date = datetime.datetime(1899, 12, 30)
        return (base_date + datetime.timedelta(days=int(serial))).date().isoformat()
    except Exception:
        return None

def date_to_excel_serial(value):
    """'YYYY-MM-DD' | date | int  ->  serial Excel (int) o None."""
    if value in (None, ''):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        v = value.strip()
        if v.isdigit():
            return int(v)
        try:
            fecha = datetime.datetime.strptime(v, '%Y-%m-%d').date()
        except ValueError:
            return None
    elif isinstance(value, datetime.date):
        fecha = value
    else:
        return None
    return (fecha - datetime.date(1899, 12, 30)).days

@login_required
def cuenta5(request):
    usuarios_permitidos = ['admin', 'NICOLAS']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    return render(request, "presupuesto_consolidado/cuenta5_base.html")

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

        # 🔹 Convertir fecha Excel a fecha normal
        for row in data:
            row['mcnfecha'] = excel_serial_to_date(row.get('mcnfecha'))
        
        return JsonResponse({
            'draw': draw,
            'recordsTotal': total,
            'recordsFiltered': total,
            'data': data
        })

    except Exception as e:
        print(f"❌ Error en obtener_cuenta5_base: {e}")
        return JsonResponse({'error': str(e)}, status=500) 
    
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

# SUBIR Y BORRAR CUENTA 5 PRESUPUESTADO -------------------------------
@login_required
def cuenta5_presupuestado(request):
    usuarios_permitidos = ['admin', 'NICOLAS']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    return render(request, "presupuestado/cuenta5_presupuestado.html")

@csrf_exempt
def obtener_cuenta5_presupuestado(request):
    try:
        params = request.POST or request.GET  # funciona con ambos métodos
        draw = int(params.get('draw') or 1)
        start = int(params.get('start') or 0)
        length = int(params.get('length') or 50)

        queryset = Cuenta5Presupuestado.objects.all()
        total = queryset.count()

        paginator = Paginator(queryset, length)
        page_number = start // length + 1
        page = paginator.get_page(page_number)

        data = list(page.object_list.values())

        # 🔹 Convertir fecha Excel a fecha normal
        for row in data:
            row['mcnfecha'] = excel_serial_to_date(row.get('mcnfecha'))
        
        return JsonResponse({
            'draw': draw,
            'recordsTotal': total,
            'recordsFiltered': total,
            'data': data
        })

    except Exception as e:
        print(f"❌ Error en obtener_cuenta5_base: {e}")
        return JsonResponse({'error': str(e)}, status=500) 
  
@csrf_exempt
def subir_excel_cuenta5_presupuestado(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            registros = data.get("registros", [])
            insertados = 0

            with transaction.atomic():
                for r in registros:
                    Cuenta5Presupuestado.objects.create(**r)
                    insertados += 1

            return JsonResponse({"status": "ok", "insertados": insertados})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    else:
        return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

@csrf_exempt
def borrar_cuenta5_presupuestado(request):
    if request.method == "POST":
        Cuenta5Presupuestado.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Datos de cuenta 5 eliminados"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)
 
 
# CUENTA 4-----------------------------------
@login_required
def cuenta4(request):
    usuarios_permitidos = ['admin', 'NICOLAS']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    return render(request, "presupuesto_consolidado/cuenta4_base.html")

@csrf_exempt
def obtener_cuenta4_base(request):
    try:
        params = request.POST or request.GET  # funciona con ambos métodos
        draw = int(params.get('draw') or 1)
        start = int(params.get('start') or 0)
        length = int(params.get('length') or 50)

        queryset = Cuenta4Base.objects.all()
        total = queryset.count()

        paginator = Paginator(queryset, length)
        page_number = start // length + 1
        page = paginator.get_page(page_number)

        data = list(page.object_list.values())

        # 🔹 Convertir fecha Excel a fecha normal
        for row in data:
            row['mcnfecha'] = excel_serial_to_date(row.get('mcnfecha'))
        
        return JsonResponse({
            'draw': draw,
            'recordsTotal': total,
            'recordsFiltered': total,
            'data': data
        })

    except Exception as e:
        print(f"❌ Error en obtener_cuenta4_base: {e}")
        return JsonResponse({'error': str(e)}, status=500) 
    
@csrf_exempt
def subir_excel_cuenta4(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            registros = data.get("registros", [])
            insertados = 0

            with transaction.atomic():
                for r in registros:
                    Cuenta4Base.objects.create(**r)
                    insertados += 1

            return JsonResponse({"status": "ok", "insertados": insertados})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    else:
        return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

@csrf_exempt
def borrar_cuenta4_base(request):
    if request.method == "POST":
        Cuenta4Base.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Datos de cuenta 4 eliminados"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

# SUBIR Y BORRAR CUENTA 5 PRESUPUESTADO -------------------------------
@login_required
def cuenta4_presupuestado(request):
    usuarios_permitidos = ['admin', 'NICOLAS']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    return render(request, "presupuestado/cuenta4_presupuestado.html")

@csrf_exempt
def obtener_cuenta4_presupuestado(request):
    try:
        params = request.POST or request.GET  # funciona con ambos métodos
        draw = int(params.get('draw') or 1)
        start = int(params.get('start') or 0)
        length = int(params.get('length') or 50)

        queryset = Cuenta4Presupuestado.objects.all()
        total = queryset.count()

        paginator = Paginator(queryset, length)
        page_number = start // length + 1
        page = paginator.get_page(page_number)

        data = list(page.object_list.values())

        # 🔹 Convertir fecha Excel a fecha normal
        for row in data:
            row['mcnfecha'] = excel_serial_to_date(row.get('mcnfecha'))
        
        return JsonResponse({
            'draw': draw,
            'recordsTotal': total,
            'recordsFiltered': total,
            'data': data
        })

    except Exception as e:
        print(f"❌ Error en obtener_cuenta4_base: {e}")
        return JsonResponse({'error': str(e)}, status=500) 
  
@csrf_exempt
def subir_excel_cuenta4_presupuestado(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            registros = data.get("registros", [])
            insertados = 0

            with transaction.atomic():
                for r in registros:
                    Cuenta4Presupuestado.objects.create(**r)
                    insertados += 1

            return JsonResponse({"status": "ok", "insertados": insertados})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    else:
        return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)

@csrf_exempt
def borrar_cuenta4_presupuestado(request):
    if request.method == "POST":
        Cuenta4Presupuestado.objects.all().delete()
        return JsonResponse({"status": "ok", "message": "Datos de cuenta 4 eliminados"})
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)
  

# NOTA: añadir a los imports del views.py
from itertools import chain

# ══════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN COMPARTIDA  (a nivel de módulo: se construye una
#  sola vez, no en cada request)
# ══════════════════════════════════════════════════════════════════

MESES_ES = {
    1: 'Enero',      2: 'Febrero',  3: 'Marzo',     4: 'Abril',
    5: 'Mayo',       6: 'Junio',    7: 'Julio',     8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
}
MESES_COLS = list(MESES_ES.values())

# sede -> zona contable + nombre en ConsolidadoTotalBase
SEDE_CONFIG_CONSOLIDADO = {
    'cali':    {'zona': ['004', 4], 'nombre': 'CALI'},
    'tulua':   {'zona': ['001', 1], 'nombre': 'TULUA'},
    'buga':    {'zona': ['002', 2], 'nombre': 'BUGA'},
    'cartago': {'zona': ['003', 3], 'nombre': 'CARTAGO'},
    'total':   None,                       # None → sin filtro, todas las sedes
}

# Alias para no romper el front ni las URLs actuales
ALIAS_SEDE = {
    'consolidado':   'total',
    'presupuestado': 'total',
    'total_base':    'total',
}

# origen -> modelos de detalle. Las cuentas 5x y las 4x viven en tablas
# distintas. El mismo string se usa para filtrar ConsolidadoTotalBase.origen
ORIGENES = {
    'ejecutado': {
        'cuenta5': Cuenta5Base,
        'cuenta4': Cuenta4Base,
    },
    'presupuestado': {
        'cuenta5': Cuenta5Presupuestado,
        'cuenta4': Cuenta4Presupuestado,
    },
}

# Campos que necesita el motor de ambas tablas de detalle
CAMPOS_DETALLE_CONTABLE = ('mcncuenta', 'mcnccosto', 'mcnfecha',
                  'mcnvaldebi', 'mcnvalcred', 'mcndestino', 'ctanombre')

CUENTAS_OMITIR = ['521020']

# ── Cuentas clave: se reconocen por número o, si no viene bien, por nombre ──
NOMBRES_CUENTAS_CLAVE = {
    '1':        'Ventas a crédito',
    '2':        'Ventas a contado',
    '41750201': 'Descuentos otorgados x pto pago',
    '613522':   'Costo de ventas',
}

# Variantes aceptadas del nombre (se comparan normalizadas: sin tildes,
# sin puntuación y en minúsculas). Agrega aquí otras formas si aparecen.
ALIAS_CUENTAS_CLAVE = {
    '1':        ['ventas a credito', 'ventas credito', 'venta a credito', 'venta credito'],
    '2':        ['ventas a contado', 'ventas contado', 'venta a contado', 'venta contado',
                 'ventas de contado'],
    '41750201': ['descuentos otorgados x pto pago', 'descuentos otorgados por pronto pago',
                 'descuentos otorgados pronto pago', 'descuento otorgado x pto pago',
                 'descuentos x pronto pago', 'descuentos por pronto pago'],
    '613522':   ['costo de ventas', 'costos de ventas', 'costo de venta', 'costo ventas'],
}

# Palabra para pre-filtrar en BD (luego se valida el nombre exacto en Python)
PALABRA_BUSQUEDA_CLAVE = {'1': 'venta', '2': 'venta', '41750201': 'descuento', '613522': 'costo'}


def normalizar_nombre_cuenta(texto):
    texto = unicodedata.normalize('NFKD', str(texto or ''))
    texto = ''.join(ch for ch in texto if not unicodedata.combining(ch))
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', texto.lower()).split())

_CUENTA_POR_ALIAS = {
    normalizar_nombre_cuenta(alias): cuenta
    for cuenta, lista in ALIAS_CUENTAS_CLAVE.items()
    for alias in lista
}

def resolver_cuenta_clave(cuenta, nombre):
    """
    Si la cuenta ya es una cuenta clave la devuelve igual. Si no, busca por
    nombre: 'Ventas a crédito' -> '1', 'Costo de ventas' -> '613522', etc.
    Si el nombre no coincide devuelve la cuenta original.
    """
    cuenta = str(cuenta or '').strip()
    if cuenta in ALIAS_CUENTAS_CLAVE:
        return cuenta
    return _CUENTA_POR_ALIAS.get(normalizar_nombre_cuenta(nombre), cuenta)

def q_cuentas_clave(cuentas=None):
    """Q amplio (por número o por palabra en el nombre) para pre-filtrar en BD."""
    cuentas = list(cuentas or ALIAS_CUENTAS_CLAVE)
    q = Q(mcncuenta__in=cuentas)
    palabras = {PALABRA_BUSQUEDA_CLAVE[c] for c in cuentas if c in PALABRA_BUSQUEDA_CLAVE}
    for palabra in palabras:
        q |= Q(ctanombre__icontains=palabra)
    return q

ASISTENCIA_TECNICA = {
    "AT-00004", "AT-00008", "AT-00010", "AT-00013", "AT-00014",
    "AT-00015", "AT-00016", "AT-00019", "AT-00020", "AT-00021",
    "AT-00022", "AT-00023", "AT-00024", "AT-00026", "AT-00028",
    "AT-00029", "AT-00030", "AT-00032", "VT-00025", "AT-00003",
}
ASISTENCIA_TECNICA_PROPIA    = {'AT-00001', 'AT-00002', 'AT-00005'}
ASISTENCIA_TECNICA_CONVENIOS = {'AT-00003', 'AT-00004', 'AT-00006'}

# destino -> cuentas que se agrupan en él (se invierte a lookup O(1))
_GRUPOS = {
    '54100207_54100211': ['54100207', '54100208', '54100209', '54100210', '54100211'],
    '541009_541033':     ['541009', '541033', '54103301', '54103302'],
    '541015_541016':     ['541015', '541016'],
    '511015_511016':     ['511015', '511016'],
    '51109501_51109502': ['51109501', '51109502'],
}
AGRUPACIONES_EXACTAS = {c: destino for destino, cuentas in _GRUPOS.items() for c in cuentas}

PREFIJOS_AGRUPADOS = ('5230', '541003', '541005', '541006', '541024', '541027', '5415')

NOMBRES_ESPECIALES = {
    '541001': 'Honorarios', '54100207_54100211': 'Tasas Bomberil-otras',
    '541003': 'Arrendamientos', '541005': 'Seguros',
    '541006': 'Mantenimiento y Reparaciónes',
    '541009_541033': 'Adecuación e Instalaciones-Reparac locat',
    '541015_541016': 'Utiles - Papelería- Fotocopias',
    '541024': 'Gastos Legales', '541027': 'Gastos de Viaje',
    '5415': 'Depreciación', '511015_511016': 'Papelería y Utiles de Oficina',
    '5405': 'Gastos de Personal', '5105': 'Gastos de Personal',
    '51109501_51109502': 'Gastos de Fondos Sociales',
    '5': 'Proyecto de Aftosa', '6': 'Asistencia Técnica Propia',
    '7': 'Asistencia Técnica Convenios',
    '8': 'Asistencia Técnica Otros - Capacitaciones',
    '5230': 'Gastos no Operacionales-IVA obsequios',
    '521015': 'Gastos Contribución 4 x1000', '615035': 'Intereses',
    'AT-00003': 'Convenio Elanco', 'AT-00004': 'Apoyo ciclo aftosa Virbac',
    'AT-00005': 'Convenio Proalba-Santa Lucía', 'AT-00007': 'Convenio Tecnoquímicas',
    'AT-00008': 'Seminario ambiental',
    'AT-00010': 'Jornada de actualización en reproducción',
    'AT-00013': 'Curso de gestión empresarial', 'AT-00014': 'Curso de mayordomía',
    'AT-00015': 'Ecografo Bovino', 'AT-00016': 'Curso de Inseminación',
    'AT-00019': 'Brucelosis-Tuberculosis', 'AT-00020': 'Programa ambiental',
    'AT-00021': 'Chequeo reproductivo', 'AT-00022': 'Curso de Bromatología',
    'AT-00023': 'Capacitación software ganadero', 'AT-00024': 'Atencion urgencias',
    'AT-00026': 'Taller atención básica equipos de ordeño',
    'AT-00028': 'Mantenimiento equipo técnico-Diplomado',
    'AT-00029': 'Taller en bienestar y sanidad bovina',
    'AT-00030': 'Seminario productividad láctea',
    'AT-00032': 'Servicio de imágenes con dron',
    'VT-00025': 'Convenio Tecnoquímicas', '41659505': 'Proyecto de Aftosa',
    '41659501': 'Patrocinio de eventos', '420560': 'Venta PPE (moto)',
}

# ══════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════

def normalizar_sede(sede):
    """Devuelve la clave canónica de SEDE_CONFIG_CONSOLIDADO o None si es inválida."""
    sede = (sede or 'total').lower()
    sede = ALIAS_SEDE.get(sede, sede)
    return sede if sede in SEDE_CONFIG_CONSOLIDADO else None


def filtros_sede(sede):
    """(filtro_detalle, filtro_consolidado) para la sede indicada."""
    cfg = SEDE_CONFIG_CONSOLIDADO[sede]
    if cfg is None:
        return {}, {}
    return {'mcnzona__in': cfg['zona']}, {'sede__icontains': cfg['nombre']}


def aplicar_agrupaciones(cuenta, costo):
    if cuenta.startswith('4'):
        return cuenta

    if costo.startswith('02040'):                         cuenta = '5'
    if costo == '020201' and cuenta.startswith('5405'):   cuenta = '5405'
    if costo == '0101':                                   cuenta = '5105'
    if cuenta.startswith('541001'):                       cuenta = '541001'

    if cuenta in AGRUPACIONES_EXACTAS:
        return AGRUPACIONES_EXACTAS[cuenta]

    for prefijo in PREFIJOS_AGRUPADOS:
        if cuenta.startswith(prefijo):
            return prefijo

    return cuenta


def _mes_desde_serial(valor):
    """Fecha en serial Excel (Cuenta5*) -> nombre de mes, o None."""
    fecha = excel_serial_to_date(valor)
    if not fecha:
        return None
    return MESES_ES[datetime.datetime.strptime(fecha, '%Y-%m-%d').date().month]


def _mes_desde_fecha(valor):
    """Fecha date o str (ConsolidadoTotalBase) -> nombre de mes, o None."""
    if not valor:
        return None
    if isinstance(valor, str):
        valor = datetime.datetime.strptime(valor, '%Y-%m-%d').date()
    return MESES_ES[valor.month]


def _nombres_cuentas(*modelos):
    """Diccionario cuenta -> nombre, tomando el primero no vacío."""
    cuentas_dict = {}
    fuentes = list(modelos) + [ConsolidadoTotalBase]
    for modelo in fuentes:
        for c in modelo.objects.values('mcncuenta', 'ctanombre').distinct():
            cta, nom = c['mcncuenta'], (c['ctanombre'] or '').strip()
            if cta and nom and cta not in cuentas_dict:
                cuentas_dict[cta] = nom
    return cuentas_dict


# ══════════════════════════════════════════════════════════════════
#  MOTOR ÚNICO DE CÁLCULO
# ══════════════════════════════════════════════════════════════════

def calcular_movimientos(origen='ejecutado', sede='total'):
    """
    Motor único para ejecutado y presupuestado.

    origen: 'ejecutado' | 'presupuestado'
    sede:   'cali' | 'tulua' | 'buga' | 'cartago' | 'total'
    """
    try:
        modelos = ORIGENES[origen]
        sede = normalizar_sede(sede)
        if sede is None:
            raise ValueError('Sede inválida')

        filtro_detalle, filtro_consolidado = filtros_sede(sede)

        # Cuentas 5x (y cualquier otra que no empiece por 4)
        queryset_5 = (
            modelos['cuenta5'].objects
            .filter(**filtro_detalle)
            .exclude(mcncuenta__in=CUENTAS_OMITIR)
            .values(*CAMPOS_DETALLE_CONTABLE)
        )

        # Cuentas 4x desde su propia tabla + cuentas clave reconocidas por nombre.
        # Las cuentas de ventas (1, 2, 41750201) del PRESUPUESTADO las genera
        # generar_presupuesto_ventas en ConsolidadoTotalBase; si se tomaran
        # también del detalle contable quedarían sumadas dos veces.
        zonas_generadas = set()
        if origen == 'presupuestado':
            sedes_generadas = (
                ConsolidadoTotalBase.objects
                .filter(origen='presupuestado', mcncuenta__in=list(CUENTAS_VENTAS))
                .values_list('sede', flat=True).distinct()
            )
            for s in sedes_generadas:
                cfg = SEDE_CONFIG_CONSOLIDADO.get((s or '').strip().lower())
                if cfg:
                    zonas_generadas.update(str(z) for z in cfg['zona'])

        queryset_4 = (
            modelos['cuenta4'].objects
            .filter(**filtro_detalle)
            .filter(Q(mcncuenta__startswith='4') | q_cuentas_clave())
            .values(*CAMPOS_DETALLE_CONTABLE, 'mcnzona')
        )

        queryset_consolidado = (
            ConsolidadoTotalBase.objects
            .filter(**filtro_consolidado, origen=origen)
            .values('mcncuenta', 'mcnccosto', 'mcnfecha', 'valor', 'ctanombre')
        )

        consolidado = defaultdict(lambda: {'total_debito': 0, 'total_credito': 0, 'total_valor': 0})

        # ── detalle (cuentas 5 + cuentas 4) ───────────────────────
        for tabla, queryset in (('cuenta5', queryset_5), ('cuenta4', queryset_4)):
            for row in queryset:
                mes = _mes_desde_serial(row['mcnfecha'])
                if not mes:
                    continue

                costo   = row['mcnccosto'] or 'SIN COSTO'
                destino = row['mcndestino'] or 'SIN DESTINO'
                destino_norm = destino.strip().upper()
                cuenta  = resolver_cuenta_clave(row['mcncuenta'], row['ctanombre']) or 'SIN CUENTA'
                
                if (tabla == 'cuenta4' and cuenta in CUENTAS_VENTAS
                        and str(row.get('mcnzona') or '') in zonas_generadas):
                    continue   # esta sede ya tiene la cuenta generada
                if cuenta in ALIAS_CUENTAS_CLAVE:
                    pass  # cuenta clave: se conserva, no se reagrupa
                elif tabla == 'cuenta4' and not cuenta.startswith('4'):
                    continue  # vino solo por el pre-filtro de nombre y no es clave
                elif cuenta.startswith('4'):
                    # Ingresos AT se agrupan por destino; el resto por cuenta
                    if destino_norm in ASISTENCIA_TECNICA:
                        cuenta = destino_norm
                else:
                    cuenta = aplicar_agrupaciones(cuenta, costo)
                    if destino_norm in ASISTENCIA_TECNICA_PROPIA:
                        cuenta = '6'
                    elif destino_norm in ASISTENCIA_TECNICA_CONVENIOS:
                        cuenta = '7'
                    elif costo.startswith('0203'):
                        cuenta = '8'

                acc = consolidado[(mes, cuenta, costo, destino)]
                acc['total_debito']  += row['mcnvaldebi'] or 0
                acc['total_credito'] += row['mcnvalcred'] or 0

        # ── ConsolidadoTotalBase ──────────────────────────────────
        for row in queryset_consolidado:
            mes = _mes_desde_fecha(row['mcnfecha'])
            if not mes:
                continue
            costo  = row['mcnccosto'] or 'SIN COSTO'
            cuenta = resolver_cuenta_clave(row['mcncuenta'], row['ctanombre']) or 'SIN CUENTA'
            if cuenta not in ALIAS_CUENTAS_CLAVE:
                cuenta = aplicar_agrupaciones(cuenta, costo)
            consolidado[(mes, cuenta, costo, 'SIN DESTINO')]['total_valor'] += row['valor'] or 0

        # ── armado de registros ───────────────────────────────────
        cuentas_dict = _nombres_cuentas(modelos['cuenta5'], modelos['cuenta4'])
        registros = defaultdict(lambda: {'mcncuenta': '', 'ctanombre': '', 'meses': {}})

        for (mes, cuenta, _costo, _destino), vals in consolidado.items():
            if cuenta in ASISTENCIA_TECNICA or cuenta.startswith('4'):
                saldo = vals['total_credito'] - vals['total_debito'] + vals['total_valor']
            else:
                saldo = vals['total_debito'] - vals['total_credito'] + vals['total_valor']

            especial = NOMBRES_ESPECIALES.get(cuenta)
            if especial:
                nombre = especial                       # ya viene bien escrito
            else:
                crudo = cuentas_dict.get(cuenta) or NOMBRES_CUENTAS_CLAVE.get(cuenta) or 'SIN NOMBRE'
                # Solo se normaliza lo que viene TODO EN MAYÚSCULAS desde la base
                nombre = crudo.capitalize() if crudo.isupper() else crudo

            reg = registros[cuenta]
            reg['mcncuenta'] = cuenta
            reg['ctanombre'] = nombre
            reg['meses'][mes] = round(reg['meses'].get(mes, 0) + saldo)

        return {'success': True, 'data': registros}

    except Exception as e:
        print(f"❌ Error en calcular_movimientos({origen}, {sede}): {e}")
        return {'success': False, 'error': str(e)}

# Wrappers por compatibilidad (si los llamas desde otros módulos)
def calcular_consolidado(sede='total'):
    return calcular_movimientos('ejecutado', sede)


def calcular_presupuestado(sede='total'):
    return calcular_movimientos('presupuestado', sede)


# ══════════════════════════════════════════════════════════════════
#  VISTA GENÉRICA
# ══════════════════════════════════════════════════════════════════

def _responder_movimientos(request, origen):
    sede = normalizar_sede(request.GET.get('sede'))
    if sede is None:
        return JsonResponse({'error': f"Sede inválida: {request.GET.get('sede')}"}, status=400)

    resultado = calcular_movimientos(origen, sede)
    if not resultado['success']:
        return JsonResponse({'error': resultado.get('error', 'Error')}, status=500)

    ORDEN_PERSONALIZADO = obtener_orden_cuentas('total' if sede == 'total' else 'sede')
    NOMBRES = nombres_personalizados()

    filas = []
    for row in resultado['data'].values():
        if row['mcncuenta'] not in ORDEN_PERSONALIZADO:
            continue
        entry = {
            'mcncuenta': row['mcncuenta'],
            'ctanombre': NOMBRES.get(row['mcncuenta'], row['ctanombre']),
            **{m: 0 for m in MESES_COLS},
            'total': 0,
        }
        for mes, valor in row['meses'].items():
            if mes in entry:
                entry[mes] = valor
                entry['total'] += valor
        filas.append(entry)

    posicion = {cta: i for i, cta in enumerate(ORDEN_PERSONALIZADO)}
    filas.sort(key=lambda item: posicion[item['mcncuenta']])

    return JsonResponse({'data': filas,
                         'orden': ORDEN_PERSONALIZADO,
                         'recordsTotal': len(filas),
                         'recordsFiltered': len(filas)})


def obtener_consolidado(request):
    """?sede=cali|tulua|buga|cartago|total   (default: total)"""
    return _responder_movimientos(request, 'ejecutado')


def obtener_presupuestado(request):
    """?sede=cali|tulua|buga|cartago|total   (default: total)"""
    return _responder_movimientos(request, 'presupuestado')


# ═══════════════════════════════════════════════════════════════
#  ORDEN PERSONALIZADO DE CUENTAS
# ═══════════════════════════════════════════════════════════════

# Listas actuales del código: solo se usan como semilla / fallback.
ORDEN_TOTAL_FALLBACK = [
    '1','2','41750201','613522','4240900101','4240909502',
    '5405','541001','54100201','54100202','54100204','54100205','54100206',
    '54100207_54100211','541003','541005','541006','541009_541033',
    '541010','541011','54101201','54101202','54101203','54101204',
    '541013','541014','541015_541016','541018','541023','541024','541027',
    '541029','541032','541035','54109501','54109502','54109503','54109504',
    '54109505','54109506','54109507','54109508','54109509','54109510',
    '5415','542005','54100203','54100211',
    '5105','511001','511002','511003','511005','511006','511009','511010',
    '511011','511012','511013','511015_511016','511018','511019','511020',
    '511021','511022','511023','511024','511026','511027','511031','511033',
    '511035','51109502','51109501_51109502','511512','511534',
    '521005','521015','521020','3','615035',
    'AT-00004','AT-00005','AT-00007','AT-00008','AT-00010','AT-00013',
    'AT-00014','AT-00015','AT-00016','AT-00019','AT-00020','AT-00021',
    'AT-00022','AT-00023','AT-00024','AT-00026','AT-00028','AT-00029',
    'AT-00030','AT-00032','VT-00001','VT-00025','AT-00003',
    '41659505','41659501','422004','422507','422529','4240900202','420560',
    '4240900301','4240900401','4240909501','4240909503','4240909901','41750105',
    '5','6','7','8','5230',
]
ORDEN_SEDE_FALLBACK = ORDEN_TOTAL_FALLBACK[:ORDEN_TOTAL_FALLBACK.index('542005') + 1]


def obtener_orden_cuentas(ambito='total'):
    """Lista ordenada de códigos de cuenta. ambito: 'total' | 'sede'."""
    qs = OrdenCuenta.objects.all()
    qs = qs.filter(visible_sede=True) if ambito == 'sede' else qs.filter(visible_total=True)
    orden = list(qs.order_by('orden', 'id').values_list('mcncuenta', flat=True))
    if orden:
        return orden
    return ORDEN_SEDE_FALLBACK if ambito == 'sede' else ORDEN_TOTAL_FALLBACK


def nombres_personalizados():
    """{ mcncuenta: ctanombre } solo para las que tengan nombre definido."""
    return {
        c: n for c, n in OrdenCuenta.objects.exclude(ctanombre='')
                                            .values_list('mcncuenta', 'ctanombre')
    }


def _cuentas_detectadas():
    """Cuentas que realmente pueden aparecer en las tablas, ya agrupadas."""
    detectadas = {}
    for fn, arg in ((calcular_consolidado, 'consolidado'),
                    (calcular_presupuestado, 'presupuestado')):
        res = fn(arg)
        if res.get('success'):
            for cta, row in res['data'].items():
                if cta and cta not in detectadas:
                    detectadas[cta] = row.get('ctanombre') or ''
    return detectadas


@login_required
def ajustes_orden_cuentas(request):
    if request.user.username not in ['admin', 'NICOLAS']:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    return render(request, 'ajustes/orden_cuentas.html')


@require_GET
def listar_orden_cuentas(request):
    data = list(
        OrdenCuenta.objects.order_by('orden', 'id')
        .values('id', 'mcncuenta', 'ctanombre', 'orden', 'visible_total', 'visible_sede')
    )
    return JsonResponse({'success': True, 'data': data, 'total': len(data)})


@login_required
@require_POST
def sincronizar_orden_cuentas(request):
    """Crea las cuentas que aún no estén en la tabla (al final de la lista).
    Si la tabla está vacía, la siembra con el orden que hay hoy en el código."""
    try:
        detectadas = _cuentas_detectadas()
        existentes = set(OrdenCuenta.objects.values_list('mcncuenta', flat=True))
        creadas = 0

        with transaction.atomic():
            if not existentes:
                en_sede = set(ORDEN_SEDE_FALLBACK)
                OrdenCuenta.objects.bulk_create([
                    OrdenCuenta(
                        mcncuenta=cta,
                        ctanombre=detectadas.get(cta, ''),
                        orden=(i + 1) * 10,
                        visible_total=True,
                        visible_sede=cta in en_sede,
                    ) for i, cta in enumerate(ORDEN_TOTAL_FALLBACK)
                ])
                creadas = len(ORDEN_TOTAL_FALLBACK)
                existentes = set(ORDEN_TOTAL_FALLBACK)

            ultimo = OrdenCuenta.objects.aggregate(m=models.Max('orden'))['m'] or 0
            nuevas = []
            for cta, nombre in detectadas.items():
                if cta not in existentes:
                    ultimo += 10
                    nuevas.append(OrdenCuenta(
                        mcncuenta=cta, ctanombre=nombre, orden=ultimo,
                        visible_total=True, visible_sede=False,
                    ))
            OrdenCuenta.objects.bulk_create(nuevas)
            creadas += len(nuevas)

        return JsonResponse({
            'success': True, 'creadas': creadas,
            'total': OrdenCuenta.objects.count(),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def guardar_orden_cuentas(request):
    """Recibe la lista completa en el orden final:
       { "cuentas": [ {mcncuenta, ctanombre, visible_total, visible_sede}, ... ] }"""
    try:
        body = json.loads(request.body)
        filas = body.get('cuentas', [])
        if not filas:
            return JsonResponse({'success': False, 'error': 'Sin cuentas'}, status=400)

        with transaction.atomic():
            for i, f in enumerate(filas):
                cta = str(f.get('mcncuenta', '') or '').strip()
                if not cta:
                    continue
                OrdenCuenta.objects.update_or_create(
                    mcncuenta=cta,
                    defaults={
                        'orden': (i + 1) * 10,
                        'ctanombre': str(f.get('ctanombre', '') or '').strip(),
                        'visible_total': bool(f.get('visible_total', True)),
                        'visible_sede': bool(f.get('visible_sede', False)),
                    },
                )
        return JsonResponse({'success': True, 'guardadas': len(filas)})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def eliminar_orden_cuenta(request):
    try:
        pk = json.loads(request.body).get('id')
        OrdenCuenta.objects.filter(pk=pk).delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ══════════════════════════════════════════════════════════════════
#  VISTA GENÉRICA — reemplaza todas las obtener_presupuestado_*
# ══════════════════════════════════════════════════════════════════


# FIN CALCULAR Y OBTENER PRESUPUESTADO -----------------
# CONSOLIDADO GENERAL
@login_required
def consolidado_general(request):
    usuarios_permitidos = ['admin', 'NICOLAS']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    return render(request, "presupuesto_consolidado/consolidado_general.html")

# PRESUPUESTO GENERAL
@login_required
def presupuestado_general(request):
    usuarios_permitidos = ['admin', 'NICOLAS']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    return render(request, "presupuestado/presupuestado_general.html")

# TABLA DINÁMICA FLEXIBLE
@login_required
def obtener_tabla_dinamica_flexible(request):
    """
    ▼ Ahora también filtra por ctanombre si se envía en los parámetros GET.
    """
    try:
        group_by_param = request.GET.get('group_by', 'ctanombre,vinnombre,mcndetalle')
        campos_agrupacion = [campo.strip() for campo in group_by_param.split(',')]
 
        campos_validos = ['ctanombre', 'vinnombre', 'mcndetalle', 'mcncuenta']
        campos_agrupacion = [c for c in campos_agrupacion if c in campos_validos]
 
        if not campos_agrupacion:
            return JsonResponse({'error': 'No se especificaron campos válidos para agrupar'}, status=400)
 
        campos_select = list(set(campos_agrupacion + [
            'mcnfecha', 'mcnvaldebi', 'mcnvalcred',
            'mcncuenta', 'mcnzona', 'mcndestino', 'mcnccosto'
        ]))
 
        queryset = Cuenta5Presupuestado.objects.values(*campos_select)
 
        filtro_cuenta    = request.GET.get('mcncuenta',  '')
        filtro_zona      = request.GET.get('mcnzona',    '')
        filtro_destino   = request.GET.get('mcndestino', '')
        filtro_costo     = request.GET.get('mcnccosto',  '')
        filtro_ctanombre = request.GET.get('ctanombre',  '')   # ▼ nuevo
 
        if filtro_cuenta:
            queryset = queryset.filter(mcncuenta__in=[c.strip() for c in filtro_cuenta.split(',')])
        if filtro_zona:
            queryset = queryset.filter(mcnzona__in=[z.strip() for z in filtro_zona.split(',')])
        if filtro_destino:
            queryset = queryset.filter(mcndestino__in=[d.strip() for d in filtro_destino.split(',')])
        if filtro_costo:
            queryset = queryset.filter(mcnccosto__in=[c.strip() for c in filtro_costo.split(',')])
        # ▼ Filtrar por ctanombre si viene en el request
        if filtro_ctanombre:
            queryset = queryset.filter(ctanombre__in=[c.strip() for c in filtro_ctanombre.split(',')])
 
        tabla_dinamica = defaultdict(lambda: {
            **{campo: '' for campo in campos_agrupacion},
            'enero': 0, 'febrero': 0, 'marzo': 0, 'abril': 0,
            'mayo': 0, 'junio': 0, 'julio': 0, 'agosto': 0,
            'septiembre': 0, 'octubre': 0, 'noviembre': 0, 'diciembre': 0,
            'total': 0
        })
 
        MESES_ES = {
            1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
            5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
            9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
        }
 
        for row in queryset:
            fecha = excel_serial_to_date(row['mcnfecha'])
            if not fecha:
                continue
            fecha = datetime.datetime.strptime(fecha, '%Y-%m-%d').date()
            mes = MESES_ES[fecha.month]
 
            key_values = []
            for campo in campos_agrupacion:
                valor = row.get(campo) or f'SIN_{campo.upper()}'
                key_values.append(valor)
            key = tuple(key_values)
 
            saldo = (row['mcnvaldebi'] or 0) - (row['mcnvalcred'] or 0)
 
            for i, campo in enumerate(campos_agrupacion):
                tabla_dinamica[key][campo] = key_values[i]
 
            tabla_dinamica[key][mes] += saldo
            tabla_dinamica[key]['total'] += saldo
 
        for key in tabla_dinamica:
            for mes in MESES_ES.values():
                tabla_dinamica[key][mes] = round(tabla_dinamica[key][mes])
            tabla_dinamica[key]['total'] = round(tabla_dinamica[key]['total'])
 
        result = list(tabla_dinamica.values())
        result.sort(key=lambda x: tuple(x[campo] for campo in campos_agrupacion))
 
        return JsonResponse({
            'data': result,
            'recordsTotal': len(result),
            'recordsFiltered': len(result),
            'grouped_by': campos_agrupacion
        })
 
    except Exception as e:
        print(f"❌ Error en obtener_tabla_dinamica_flexible: {e}")
        return JsonResponse({'error': str(e)}, status=500)

def obtener_valores_filtros(request):
    """
    Retorna valores únicos disponibles para cada campo de filtro,
    teniendo en cuenta los filtros activos en los demás campos (filtrado en cascada).
    Ahora soporta también el campo ctanombre.
    """
    try:
        campo = request.GET.get('campo', '')
        # ▼ ctanombre agregado a campos válidos
        campos_validos = ['mcncuenta', 'mcnzona', 'mcndestino', 'mcnccosto', 'ctanombre']
 
        if campo not in campos_validos:
            return JsonResponse({'error': 'Campo no válido'}, status=400)
 
        queryset = Cuenta5Presupuestado.objects.all()
 
        # Aplicar los filtros de los OTROS campos (no del campo que se consulta)
        filtro_cuenta   = request.GET.get('mcncuenta',  '')
        filtro_zona     = request.GET.get('mcnzona',    '')
        filtro_destino  = request.GET.get('mcndestino', '')
        filtro_costo    = request.GET.get('mcnccosto',  '')
        filtro_ctanombre = request.GET.get('ctanombre', '')   # ▼ nuevo
 
        if filtro_cuenta and campo != 'mcncuenta':
            queryset = queryset.filter(mcncuenta__in=[c.strip() for c in filtro_cuenta.split(',')])
        if filtro_zona and campo != 'mcnzona':
            queryset = queryset.filter(mcnzona__in=[z.strip() for z in filtro_zona.split(',')])
        if filtro_destino and campo != 'mcndestino':
            queryset = queryset.filter(mcndestino__in=[d.strip() for d in filtro_destino.split(',')])
        if filtro_costo and campo != 'mcnccosto':
            queryset = queryset.filter(mcnccosto__in=[c.strip() for c in filtro_costo.split(',')])
        # ▼ Aplicar filtro ctanombre en cascada (solo si no es el campo que se consulta)
        if filtro_ctanombre and campo != 'ctanombre':
            queryset = queryset.filter(ctanombre__in=[c.strip() for c in filtro_ctanombre.split(',')])
 
        valores = (
            queryset
            .values_list(campo, flat=True)
            .distinct()
            .order_by(campo)
        )
        valores = [v for v in valores if v]
 
        return JsonResponse({'valores': list(valores)})
 
    except Exception as e:
        print(f"❌ Error en obtener_valores_filtros: {e}")
        return JsonResponse({'error': str(e)}, status=500)
 
def tabla_dinamica_view(request):
    return render(request, 'presupuesto_consolidado/tabla_dinamica.html')

@require_http_methods(["GET"])
def obtener_registros_detalle(request):
    try:
        ctanombre  = request.GET.get('ctanombre', '')
        vinnombre  = request.GET.get('vinnombre', '')
        mcndetalle = request.GET.get('mcndetalle', '')

        if not ctanombre or not vinnombre or not mcndetalle:
            return JsonResponse({'error': 'Faltan parámetros obligatorios'}, status=400)

        queryset = Cuenta5Presupuestado.objects.filter(
            ctanombre=ctanombre,
            vinnombre=vinnombre,
            mcndetalle=mcndetalle,
        )

        # ✅ Soportar múltiples valores separados por coma
        for campo, param in [
            ('mcncuenta',  'mcncuenta'),
            ('mcnzona',    'mcnzona'),
            ('mcndestino', 'mcndestino'),
            ('mcnccosto',  'mcnccosto'),
        ]:
            valor = request.GET.get(param, '')
            if valor:
                valores = [v.strip() for v in valor.split(',')]
                queryset = queryset.filter(**{f'{campo}__in': valores})

        registros = []
        for obj in queryset:
            registros.append({
                'id':         obj.pk,
                'mcnfecha':   obj.mcnfecha,
                'mcndetalle': obj.mcndetalle,
                'mcnvaldebi': float(obj.mcnvaldebi or 0),
                'mcnvalcred': float(obj.mcnvalcred or 0),
                'mcncuenta':  obj.mcncuenta,
                'mcnzona':    obj.mcnzona,
                'mcndestino': obj.mcndestino,
                'mcnccosto':  obj.mcnccosto,
                'ctanombre':  obj.ctanombre,
                'vinnombre':  obj.vinnombre,
            })

        return JsonResponse({'registros': registros, 'total': len(registros)})

    except Exception as e:
        print(f"❌ Error en obtener_registros_detalle: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["PUT", "PATCH"])
def editar_registro(request, registro_id):
    """
    Edita un registro individual de Cuenta5Base.
    Body JSON con los campos a actualizar.
    """
    try:
        obj = Cuenta5Presupuestado.objects.get(pk=registro_id)
    except Cuenta5Presupuestado.DoesNotExist:
        return JsonResponse({'error': 'Registro no encontrado'}, status=404)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    # Campos editables
    campos_editables = [
        'mcnfecha', 'mcndetalle', 'mcnvaldebi', 'mcnvalcred',
        'mcncuenta', 'mcnzona', 'mcndestino', 'mcnccosto',
        'ctanombre', 'vinnombre',
    ]

    for campo in campos_editables:
        if campo in body:
            setattr(obj, campo, body[campo])

    obj.save()

    return JsonResponse({
        'success': True,
        'message': f'Registro {registro_id} actualizado correctamente',
        'id': obj.pk,
    })

@csrf_exempt
@require_http_methods(["DELETE"])
def eliminar_registro(request, registro_id):
    """
    Elimina un registro individual de Cuenta5Base.
    """
    try:
        obj = Cuenta5Presupuestado.objects.get(pk=registro_id)
    except Cuenta5Presupuestado.DoesNotExist:
        return JsonResponse({'error': 'Registro no encontrado'}, status=404)

    obj.delete()

    return JsonResponse({
        'success': True,
        'message': f'Registro {registro_id} eliminado correctamente',
    })

@require_http_methods(["GET"])
def obtener_registros_nivel(request):
    try:
        nivel     = request.GET.get('nivel', '')
        ctanombre = request.GET.get('ctanombre', '')

        if not nivel or not ctanombre:
            return JsonResponse({'error': 'Faltan parámetros obligatorios'}, status=400)

        queryset = Cuenta5Presupuestado.objects.filter(ctanombre=ctanombre)

        if nivel == 'vinculo':
            vinnombre = request.GET.get('vinnombre', '')
            if not vinnombre:
                return JsonResponse({'error': 'Falta vinnombre'}, status=400)
            queryset = queryset.filter(vinnombre=vinnombre)

        # ✅ Soportar múltiples valores separados por coma
        for campo, param in [
            ('mcncuenta',  'mcncuenta'),
            ('mcnzona',    'mcnzona'),
            ('mcndestino', 'mcndestino'),
            ('mcnccosto',  'mcnccosto'),
        ]:
            valor = request.GET.get(param, '')
            if valor:
                valores = [v.strip() for v in valor.split(',')]
                queryset = queryset.filter(**{f'{campo}__in': valores})

        registros = []
        for obj in queryset:
            registros.append({
                'id':         obj.pk,
                'mcnfecha':   obj.mcnfecha,
                'mcndetalle': obj.mcndetalle,
                'mcnvaldebi': float(obj.mcnvaldebi or 0),
                'mcnvalcred': float(obj.mcnvalcred or 0),
                'mcncuenta':  obj.mcncuenta,
                'mcnzona':    obj.mcnzona,
                'mcndestino': obj.mcndestino,
                'mcnccosto':  obj.mcnccosto,
                'ctanombre':  obj.ctanombre,
                'vinnombre':  obj.vinnombre,
            })

        return JsonResponse({'registros': registros, 'total': len(registros)})

    except Exception as e:
        print(f"❌ Error en obtener_registros_nivel: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["PUT", "PATCH"])
def renombrar_nivel(request):
    """
    Renombra en masa ctanombre o vinnombre en todos los registros que coincidan.
    Body JSON:
    - nivel: 'cuenta' o 'vinculo'
    - ctanombre_actual: valor actual
    - vinnombre_actual: valor actual (solo si nivel='vinculo')
    - ctanombre_nuevo: nuevo valor (solo si nivel='cuenta')
    - vinnombre_nuevo: nuevo valor (solo si nivel='vinculo')
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    nivel          = body.get('nivel', '')
    ctanombre_actual = body.get('ctanombre_actual', '')

    if not nivel or not ctanombre_actual:
        return JsonResponse({'error': 'Faltan parámetros'}, status=400)

    try:
        if nivel == 'cuenta':
            nuevo = body.get('ctanombre_nuevo', '').strip()
            if not nuevo:
                return JsonResponse({'error': 'Falta ctanombre_nuevo'}, status=400)
            count = Cuenta5Presupuestado.objects.filter(ctanombre=ctanombre_actual).update(ctanombre=nuevo)
            return JsonResponse({'success': True, 'actualizados': count, 'nuevo': nuevo})

        elif nivel == 'vinculo':
            vinnombre_actual = body.get('vinnombre_actual', '')
            nuevo = body.get('vinnombre_nuevo', '').strip()
            if not vinnombre_actual or not nuevo:
                return JsonResponse({'error': 'Faltan vinnombre_actual o vinnombre_nuevo'}, status=400)
            count = Cuenta5Presupuestado.objects.filter(
                ctanombre=ctanombre_actual,
                vinnombre=vinnombre_actual
            ).update(vinnombre=nuevo)
            return JsonResponse({'success': True, 'actualizados': count, 'nuevo': nuevo})

        else:
            return JsonResponse({'error': 'Nivel inválido'}, status=400)

    except Exception as e:
        print(f"❌ Error en renombrar_nivel: {e}")
        return JsonResponse({'error': str(e)}, status=500)

def _mes_de_serial(serial):
    """Serial Excel -> número de mes (1-12) o None."""
    fecha = excel_serial_to_date(serial)
    if not fecha:
        return None
    return datetime.datetime.strptime(fecha, '%Y-%m-%d').date().month


@csrf_exempt
@require_POST
def redistribuir_mes(request):
    """
    Redistribuye proporcionalmente un nuevo total mensual sobre los registros
    reales de Cuenta5Presupuestado. Garantiza que la suma final == nuevo_total.

    Body JSON:
      nivel: 'cuenta' | 'vinculo' | 'detalle'
      ctanombre, vinnombre, mcndetalle, mes (1-12), nuevo_total,
      filtros: {mcncuenta: [], mcnzona: [], mcndestino: [], mcnccosto: []}
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    nivel      = body.get('nivel')
    ctanombre  = body.get('ctanombre') or ''
    vinnombre  = body.get('vinnombre') or ''
    mcndetalle = body.get('mcndetalle') or ''

    if nivel not in ('cuenta', 'vinculo', 'detalle') or not ctanombre:
        return JsonResponse({'error': 'Nivel o cuenta inválidos'}, status=400)

    try:
        mes = int(body.get('mes'))
        nuevo_total = int(round(float(body.get('nuevo_total'))))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'mes o nuevo_total inválidos'}, status=400)

    if not 1 <= mes <= 12:
        return JsonResponse({'error': 'Mes fuera de rango'}, status=400)

    qs = Cuenta5Presupuestado.objects.filter(ctanombre=ctanombre)
    if nivel in ('vinculo', 'detalle'):
        qs = qs.filter(vinnombre=vinnombre)
    if nivel == 'detalle':
        qs = qs.filter(mcndetalle=mcndetalle)

    # Mismos filtros que usa la tabla, para que el universo coincida
    filtros = body.get('filtros') or {}
    for campo in ('mcncuenta', 'mcnzona', 'mcndestino', 'mcnccosto'):
        valores = [v for v in (filtros.get(campo) or []) if v not in (None, '')]
        if valores:
            qs = qs.filter(**{f'{campo}__in': valores})

    registros = [r for r in qs if _mes_de_serial(r.mcnfecha) == mes]
    if not registros:
        return JsonResponse(
            {'error': 'No hay registros en ese mes para el nivel seleccionado. '
                      'No es posible distribuir el valor.'},
            status=400,
        )

    saldos = [(r.mcnvaldebi or 0) - (r.mcnvalcred or 0) for r in registros]
    total_actual = sum(saldos)
    n = len(registros)

    asignaciones = []
    acumulado = 0
    for i, (reg, saldo) in enumerate(zip(registros, saldos)):
        if i == n - 1:
            valor = nuevo_total - acumulado       # el último absorbe el residuo
        else:
            prop = (saldo / total_actual) if total_actual else (1 / n)
            valor = int(round(nuevo_total * prop))
            acumulado += valor
        asignaciones.append((reg, valor))

    with transaction.atomic():
        for reg, valor in asignaciones:
            # Saldo = débito - crédito. Normalizamos para que siempre cuadre.
            reg.mcnvaldebi = valor if valor >= 0 else 0
            reg.mcnvalcred = 0 if valor >= 0 else -valor
            reg.save(update_fields=['mcnvaldebi', 'mcnvalcred'])

    return JsonResponse({
        'success': True,
        'actualizados': n,
        'total_aplicado': nuevo_total,
        'total_anterior': total_actual,
    })

@csrf_exempt
@require_POST
def aplicar_inflacion(request):
    """
    Aplica un % de inflación al saldo de los registros de VARIOS nodos de la
    jerarquía a la vez. Los registros se deduplican por PK, así que aunque un
    objetivo quede contenido en otro, la inflación se aplica una sola vez.

    Body JSON:
      porcentaje: float (5 = +5%, -3.5 = -3.5%)
      meses: [1..12]  (opcional; por defecto todos)
      objetivos: [{nivel:'cuenta'|'vinculo'|'detalle',
                   ctanombre, vinnombre, mcndetalle}, ...]
      filtros: {mcncuenta: [], mcnzona: [], mcndestino: [], mcnccosto: []}
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    objetivos = body.get('objetivos') or []
    if not objetivos:
        return JsonResponse({'error': 'No se seleccionó ninguna fila'}, status=400)

    try:
        porcentaje = float(body.get('porcentaje'))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Porcentaje inválido'}, status=400)

    if porcentaje < -100:
        return JsonResponse({'error': 'El porcentaje no puede ser menor a -100%'}, status=400)

    try:
        meses = {int(m) for m in (body.get('meses') or range(1, 13))}
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Meses inválidos'}, status=400)
    meses = {m for m in meses if 1 <= m <= 12}
    if not meses:
        return JsonResponse({'error': 'Debe indicar al menos un mes'}, status=400)

    # ── Un OR por cada objetivo seleccionado ──────────────────────────────
    condicion = Q()
    for o in objetivos:
        nivel     = o.get('nivel')
        ctanombre = o.get('ctanombre') or ''
        if nivel not in ('cuenta', 'vinculo', 'detalle') or not ctanombre:
            return JsonResponse({'error': f'Objetivo inválido: {o}'}, status=400)

        q = Q(ctanombre=ctanombre)
        if nivel in ('vinculo', 'detalle'):
            q &= Q(vinnombre=o.get('vinnombre') or '')
        if nivel == 'detalle':
            q &= Q(mcndetalle=o.get('mcndetalle') or '')
        condicion |= q

    qs = Cuenta5Presupuestado.objects.filter(condicion)

    # Mismos filtros de la tabla, para que el universo coincida con lo visible
    filtros = body.get('filtros') or {}
    for campo in ('mcncuenta', 'mcnzona', 'mcndestino', 'mcnccosto'):
        valores = [v for v in (filtros.get(campo) or []) if v not in (None, '')]
        if valores:
            qs = qs.filter(**{f'{campo}__in': valores})

    # distinct() + dict por PK: blindaje contra doble aplicación
    unicos = {}
    for r in qs.distinct():
        if _mes_de_serial(r.mcnfecha) in meses:
            unicos[r.pk] = r
    registros = list(unicos.values())

    if not registros:
        return JsonResponse(
            {'error': 'No hay registros en los meses seleccionados para las filas elegidas.'},
            status=400,
        )

    factor = 1 + porcentaje / 100.0
    total_ant = total_nue = 0

    with transaction.atomic():
        for reg in registros:
            saldo = (reg.mcnvaldebi or 0) - (reg.mcnvalcred or 0)
            nuevo = int(round(saldo * factor))
            total_ant += saldo
            total_nue += nuevo
            reg.mcnvaldebi = nuevo if nuevo >= 0 else 0
            reg.mcnvalcred = 0 if nuevo >= 0 else -nuevo
        Cuenta5Presupuestado.objects.bulk_update(
            registros, ['mcnvaldebi', 'mcnvalcred'], batch_size=500
        )

    return JsonResponse({
        'success': True,
        'actualizados': len(registros),
        'objetivos': len(objetivos),
        'porcentaje': porcentaje,
        'meses': sorted(meses),
        'total_anterior': total_ant,
        'total_nuevo': total_nue,
    })
    
@csrf_exempt
@require_http_methods(["DELETE"])
def eliminar_nivel(request):
    """
    Elimina en masa todos los registros de un nivel jerárquico.
    Parámetros GET:
    - nivel: 'cuenta' o 'vinculo'
    - ctanombre: requerido siempre
    - vinnombre: requerido si nivel='vinculo'
    """
    try:
        nivel     = request.GET.get('nivel', '')
        ctanombre = request.GET.get('ctanombre', '')

        if not nivel or not ctanombre:
            return JsonResponse({'error': 'Faltan parámetros'}, status=400)

        queryset = Cuenta5Presupuestado.objects.filter(ctanombre=ctanombre)

        if nivel == 'vinculo':
            vinnombre = request.GET.get('vinnombre', '')
            if not vinnombre:
                return JsonResponse({'error': 'Falta vinnombre'}, status=400)
            queryset = queryset.filter(vinnombre=vinnombre)
        elif nivel != 'cuenta':
            return JsonResponse({'error': 'Nivel inválido'}, status=400)

        count, _ = queryset.delete()
        return JsonResponse({'success': True, 'eliminados': count})

    except Exception as e:
        print(f"❌ Error en eliminar_nivel: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────
# GET /presupuesto/consolidado-base/carga/
# Renderiza el template de carga
# ─────────────────────────────────────────────────────────────
# Sedes que ofrece el formulario de carga, en orden y con su etiqueta.
# Se derivan de SEDE_CONFIG_CONSOLIDADO para no mantener una lista aparte.
SEDES_CARGA = [
    ('tulua',   'Tuluá'),
    ('buga',    'Buga'),
    ('cartago', 'Cartago'),
    ('cali',    'Cali'),
]
ORIGENES_CARGA = [
    ('ejecutado',     'Ejecutado'),
    ('presupuestado', 'Presupuestado'),
]
# ─────────────────────────────────────────────────────────────
# Opciones válidas
# ─────────────────────────────────────────────────────────────
SEDES_VALIDAS = {s for s, _ in SEDES_CARGA} | {''}
ORIGENES_VALIDOS = {o for o, _ in ORIGENES_CARGA} | {''}


def vista_carga_consolidado_base(request):
    anio_actual = timezone.now().year
    return render(request, 'presupuesto_consolidado/carga_consolidado_base.html', {
        'sedes': SEDES_CARGA,
        'origenes': ORIGENES_CARGA,
        'anio_actual': anio_actual,
        # El presupuesto siempre se arma para el año siguiente
        'anio_presupuesto': anio_actual + 1,
        'anio_min': anio_actual - 10,
        'anio_max': anio_actual + 5,
    })


# ─────────────────────────────────────────────────────────────
# POST /presupuesto/cargar_consolidado_total_base/
# Recibe lista de registros y hace upsert (insert or update)
# ─────────────────────────────────────────────────────────────
@require_POST
def cargar_consolidado_total_base(request):
    try:
        body     = json.loads(request.body)
        registros = body.get('registros', [])

        if not registros:
            return JsonResponse({'success': False, 'error': 'Sin registros'}, status=400)

        # ── Validar sede y origen a nivel de lote ──────────────
        sede   = str(body.get('sede',   '') or '').strip().lower()
        origen = str(body.get('origen', '') or '').strip().lower()

        if sede not in SEDES_VALIDAS:
            return JsonResponse(
                {'success': False, 'error': f"Sede inválida. Opciones: {', '.join(sorted(SEDES_VALIDAS))}"},
                status=400,
            )
        if origen not in ORIGENES_VALIDOS:
            return JsonResponse(
                {'success': False, 'error': f"Origen inválido. Opciones: {', '.join(sorted(ORIGENES_VALIDOS))}"},
                status=400,
            )

        insertados  = 0
        actualizados = 0

        for r in registros:
            # Normalizar fecha
            fecha_raw = r.get('mcnfecha')
            if not fecha_raw:
                continue
            try:
                fecha = datetime.datetime.strptime(str(fecha_raw).strip(), '%Y-%m-%d').date()
            except ValueError:
                continue

            mcncuenta   = str(r.get('mcncuenta',  '') or '').strip()
            mcnccosto   = str(r.get('mcnccosto',  '0') or '0').strip()
            ctanombre   = str(r.get('ctanombre',  '') or '').strip()
            valor       = _to_bigint(r.get('valor'))
            total_anual = _to_bigint(r.get('total_anual'))

            if not mcncuenta:
                continue

            # Upsert: clave única = (mcncuenta, mcnccosto, mcnfecha, sede, origen)
            obj, created = ConsolidadoTotalBase.objects.update_or_create(
                mcncuenta=mcncuenta,
                mcnccosto=mcnccosto,
                mcnfecha=fecha,
                sede=sede,
                origen=origen,
                defaults={
                    'ctanombre':   ctanombre,
                    'valor':       valor,
                    'total_anual': total_anual,
                },
            )
            if created:
                insertados += 1
            else:
                actualizados += 1

        return JsonResponse({
            'success':     True,
            'insertados':  insertados,
            'actualizados': actualizados,
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────
# GET /presupuesto/obtener_consolidado_total_base_raw/
# Devuelve todos los registros en bruto para el historial
# ─────────────────────────────────────────────────────────────
@require_GET
def obtener_consolidado_total_base_raw(request):
    try:
        # Filtros opcionales por sede y/o origen vía query params
        sede   = request.GET.get('sede',   '').strip().lower() or None
        origen = request.GET.get('origen', '').strip().lower() or None

        qs = ConsolidadoTotalBase.objects.all()
        if sede:
            qs = qs.filter(sede=sede)
        if origen:
            qs = qs.filter(origen=origen)

        qs = qs.order_by('mcncuenta', 'mcnfecha').values(
            'id', 'mcncuenta', 'mcnccosto', 'ctanombre',
            'mcnfecha', 'valor', 'total_anual', 'sede', 'origen',
        )

        data = [
            {
                'id':          row['id'],
                'mcncuenta':   row['mcncuenta']   or '',
                'mcnccosto':   row['mcnccosto']   or '',
                'ctanombre':   row['ctanombre']   or '',
                'mcnfecha':    str(row['mcnfecha']) if row['mcnfecha'] else '',
                'valor':       row['valor'],
                'total_anual': row['total_anual'],
                'sede':        row['sede']        or '',
                'origen':      row['origen']      or '',
            }
            for row in qs
        ]
        return JsonResponse({'success': True, 'data': data})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────
# POST /presupuesto/borrar_consolidado_total_base/
# Acepta filtros opcionales sede y/o origen; sin filtros borra todo
# ─────────────────────────────────────────────────────────────
@require_POST
def borrar_consolidado_total_base(request):
    try:
        body   = json.loads(request.body) if request.body else {}
        sede   = str(body.get('sede',   '') or '').strip().lower() or None
        origen = str(body.get('origen', '') or '').strip().lower() or None

        qs = ConsolidadoTotalBase.objects.all()
        if sede:
            if sede not in SEDES_VALIDAS:
                return JsonResponse(
                    {'success': False, 'error': f"Sede inválida. Opciones: {', '.join(sorted(SEDES_VALIDAS))}"},
                    status=400,
                )
            qs = qs.filter(sede=sede)
        if origen:
            if origen not in ORIGENES_VALIDOS:
                return JsonResponse(
                    {'success': False, 'error': f"Origen inválido. Opciones: {', '.join(sorted(ORIGENES_VALIDOS))}"},
                    status=400,
                )
            qs = qs.filter(origen=origen)

        eliminados, _ = qs.delete()
        return JsonResponse({'success': True, 'eliminados': eliminados})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ─────────────────────────────────────────────────────────────
# POST /presupuesto/eliminar_fila_consolidado_total_base/
# ─────────────────────────────────────────────────────────────
@require_POST
def eliminar_fila_consolidado_total_base(request):
    try:
        body = json.loads(request.body)
        pk   = body.get('id')
        if not pk:
            return JsonResponse({'success': False, 'error': 'id requerido'}, status=400)
        eliminados, _ = ConsolidadoTotalBase.objects.filter(pk=pk).delete()
        if not eliminados:
            return JsonResponse({'success': False, 'error': 'Registro no encontrado'}, status=404)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ─────────────────────────────────────────────────────────────
# Utilidad interna
# ─────────────────────────────────────────────────────────────
def _to_bigint(value):
    if value is None or value == '':
        return None
    if isinstance(value, (int, float)):
        return int(value)
    texto = str(value).strip()
    # Formato colombiano ("1.234.567,89") solo si trae coma decimal
    if ',' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    try:
        return int(float(texto))
    except (ValueError, TypeError):
        return None

# ---------------------------------------------------------------------------
# AÑADIR A views.py
# ---------------------------------------------------------------------------
# Requiere que arriba del archivo ya existan (si no, añadirlos):
#   from django.views.decorators.http import require_GET, require_POST
#   from .models import ComentarioComparativo   (o el import equivalente
#       si tu archivo usa "from .models import *")
# ---------------------------------------------------------------------------

SEDES_COMPARATIVO = {'tulua', 'buga', 'cartago', 'cali', 'consolidado'}


@login_required
def comparativo_general(request):
    """
    Página única de comparativo: pestañas para las 4 sedes + el total,
    con columna de comentarios editable y guardado automático.
    """
    usuarios_permitidos = ['admin', 'NICOLAS']
    if request.user.username not in usuarios_permitidos:
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    return render(request, "comparativo/comparativo_general.html")


@require_GET
def obtener_comentarios_comparativo(request, sede):
    """
    Devuelve todos los comentarios guardados para una sede, como un
    diccionario { fila_key: comentario }.
    """
    sede = (sede or '').strip().lower()
    if sede not in SEDES_COMPARATIVO:
        return JsonResponse({'error': f'Sede inválida: {sede}'}, status=400)

    data = {
        c.fila_key: (c.comentario or '')
        for c in ComentarioComparativo.objects.filter(sede=sede)
    }
    return JsonResponse({'data': data})


@login_required
@require_POST
def guardar_comentario_comparativo(request):
    """
    Crea o actualiza el comentario de una fila específica dentro de una sede.
    Body JSON esperado:
        {
            "sede": "tulua",
            "fila_key": "541001",
            "comentario": "texto libre...",
            "mcncuenta": "541001",       (opcional, solo referencia)
            "ctanombre": "Honorarios"    (opcional, solo referencia)
        }
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)

    sede = str(body.get('sede', '')).strip().lower()
    fila_key = str(body.get('fila_key', '')).strip()
    comentario = body.get('comentario', '') or ''
    mcncuenta = str(body.get('mcncuenta', '') or '')
    ctanombre = str(body.get('ctanombre', '') or '')

    if sede not in SEDES_COMPARATIVO:
        return JsonResponse({'success': False, 'error': f'Sede inválida: {sede}'}, status=400)
    if not fila_key:
        return JsonResponse({'success': False, 'error': 'fila_key es obligatorio'}, status=400)

    usuario = request.user.username if request.user.is_authenticated else ''

    obj, _ = ComentarioComparativo.objects.update_or_create(
        sede=sede,
        fila_key=fila_key,
        defaults={
            'comentario': comentario,
            'mcncuenta': mcncuenta,
            'ctanombre': ctanombre,
            'actualizado_por': usuario,
        },
    )
    return JsonResponse({'success': True, 'fila_key': fila_key, 'comentario': obj.comentario})


# ══════════════════════════════════════════════════════════════════
#  PRESUPUESTO DE VENTAS POR SEDE  (cuentas 1, 2, 41750201)
#
#  Por cada sede (tulua, buga, cartago, cali):
#  1. Toma el EJECUTADO de esa sede en ConsolidadoTotalBase.
#  2. Por cada mes: VENTAS NETAS = cuenta 1 + cuenta 2 + cuenta 41750201
#     participación(cuenta) = valor(cuenta) / VENTAS NETAS
#  3. valor = proyección del centro de operación en ese mes * (1 + participación)
#     (proyección = tabla "Proyección presupuesto centro operación - Ventas")
#  4. Guarda en ConsolidadoTotalBase con la sede y origen='presupuestado'.
#
#  Pegar al FINAL de views.py, reemplazando la versión anterior.
#  Necesita que ya estén definidos más arriba: calculo, MESES_ES,
#  SEDE_CONFIG_CONSOLIDADO, NOMBRES_CENTRO_OPERACION (todos existen hoy).
# ══════════════════════════════════════════════════════════════════

from django.db import connection

# Entero fijo cualquiera: identifica el candado de este proceso en PostgreSQL
LOCK_PRESUPUESTO_VENTAS = 874231001

CUENTAS_VENTAS = {
    '1':        'Ventas a crédito',
    '2':        'Ventas a contado',
    '41750201': 'Descuentos otorgados x pto pago',
}

# Cuentas que restan en VENTAS NETAS: su participación es negativa y el
# presupuesto se calcula como proyección × participación (queda negativo).
CUENTAS_DESCUENTO = {'41750201'}

# sede (ConsolidadoTotalBase) -> nombre_centro_de_operacion (BdVentasComercial)
# Se arma con los códigos de zona que ya existen, así no hay un tercer mapeo que mantener:
#   tulua -> 1 -> ALMACEN TULUA, buga -> 2 -> ALMACEN BUGA, ...
SEDE_CENTRO_OPERACION = {
    sede: NOMBRES_CENTRO_OPERACION[cfg['zona'][1]]
    for sede, cfg in SEDE_CONFIG_CONSOLIDADO.items()
    if cfg is not None
}


def _proyeccion_ventas_por_centro():
    """
    {nombre_centro_de_operacion: {mes: valor}} del año siguiente.
    Es la misma fuente que calculo.construir_ventas('centro') usa para las
    filas del año siguiente, así que los valores coinciden con la tabla
    "Proyección presupuesto centro operación - Ventas".
    """
    detalle = calculo._proyeccion_mensual_detalle()
    if detalle.empty:
        return {}

    agrupado = (
        detalle.groupby(['nombre_centro_de_operacion', 'mes'])['valor_proyectado_mes']
        .sum().fillna(0).round()
    )
    resultado = defaultdict(dict)
    for (centro, mes), valor in agrupado.items():
        resultado[centro][int(mes)] = int(valor)
    return resultado


def _participacion_ventas_sede(anio_base, sede):
    """
    {mes: {cuenta: porcentaje}} del ejecutado de una sede.
    participación = valor de la cuenta / VENTAS NETAS (cuentas 1 + 2 + 41750201).
    Las cuentas se reconocen por número o por nombre.
    """
    nombre = SEDE_CONFIG_CONSOLIDADO[sede]['nombre']
    filas = (
        ConsolidadoTotalBase.objects
        .filter(origen='ejecutado', mcnfecha__year=anio_base, sede__icontains=nombre)
        .filter(q_cuentas_clave(CUENTAS_VENTAS))
        .values('mcnfecha__month', 'mcncuenta', 'ctanombre', 'valor')
    )

    por_mes = defaultdict(lambda: dict.fromkeys(CUENTAS_VENTAS, 0))
    anual = dict.fromkeys(CUENTAS_VENTAS, 0)
    for f in filas:
        cta = resolver_cuenta_clave(f['mcncuenta'], f['ctanombre'])
        if cta not in CUENTAS_VENTAS:
            continue
        valor = f['valor'] or 0
        por_mes[f['mcnfecha__month']][cta] += valor
        anual[cta] += valor

    def a_porcentaje(valores):
        ventas_netas = sum(valores.values())
        if not ventas_netas:
            return None
        return {cta: val / ventas_netas for cta, val in valores.items()}

    participacion_anual = a_porcentaje(anual)
    if participacion_anual is None:
        return None

    return {
        mes: (a_porcentaje(por_mes[mes]) if mes in por_mes else None) or participacion_anual
        for mes in range(1, 13)
    }

def _anio_base_sede(sede, anio_pedido=None):
    """
    Último año con ventas ejecutadas de ESA sede. Antes se usaba un único
    año global (el máximo entre todas las sedes), así que si una sede iba
    más adelantada que el resto, las demás quedaban sin participación.
    `anio_pedido` actúa como tope: nunca se usa un año posterior.
    """
    nombre = SEDE_CONFIG_CONSOLIDADO[sede]['nombre']
    qs = (
        ConsolidadoTotalBase.objects
        .filter(origen='ejecutado', mcnfecha__isnull=False, sede__icontains=nombre)
        .filter(q_cuentas_clave(CUENTAS_VENTAS))
    )
    if anio_pedido:
        qs = qs.filter(mcnfecha__year__lte=anio_pedido)

    anios = sorted({
        fecha.year for cta, nom, fecha in
        qs.values_list('mcncuenta', 'ctanombre', 'mcnfecha').iterator()
        if resolver_cuenta_clave(cta, nom) in CUENTAS_VENTAS
    })
    return anios[-1] if anios else None

def generar_presupuesto_ventas(anio_base=None):
    """
    anio_base: año del ejecutado del que se toma la participación.
               Si es None se usa el último año con ventas ejecutadas.
    El año del presupuesto es el mismo que proyecta calculo.construir_ventas
    (año actual + 1).
    Idempotente: borra lo generado antes para ese año y lo vuelve a crear.
    """
    anio_ppto = timezone.now().year + 1

    proyeccion = _proyeccion_ventas_por_centro()
    if not proyeccion:
        year_actual = timezone.now().year
        hay_recientes = BdVentasComercial.objects.filter(lapso__gte=(year_actual - 1) * 100 + 1).exists()
        if not hay_recientes:
            raise ValueError(
                f'No hay ventas en bd_ventas_comercial desde {year_actual - 1}. '
                f'Vuelve a importar el Excel de ventas comercial para poder proyectar {anio_ppto}.'
            )
        raise ValueError(f'No hay proyección de ventas por centro de operación para {anio_ppto}')

    nuevos, procesadas, omitidas = [], [], {}
    participacion_resp, detalle_resp, anios_usados = {}, {}, {}

    for sede, centro in SEDE_CENTRO_OPERACION.items():
        anio_sede = _anio_base_sede(sede, anio_base)
        if anio_sede is None:
            omitidas[sede] = (
                f'sin ventas ejecutadas hasta {anio_base}' if anio_base
                else 'sin ventas ejecutadas en ConsolidadoTotalBase'
            )
            continue
        participacion = _participacion_ventas_sede(anio_sede, sede)
        if participacion is None:
            omitidas[sede] = f'sin ventas ejecutadas en {anio_sede}'
            continue

        proy_centro = proyeccion.get(centro, {})
        faltantes = [MESES_ES[m] for m in range(1, 13) if m not in proy_centro]
        if faltantes:
            omitidas[sede] = f"sin proyección de {centro} para: {', '.join(faltantes)}"
            continue

        # ── cálculo ───────────────────────────────────────────────
        #   ventas (1, 2):        proyección × (1 + participación)
        #   descuentos (41750201): proyección × participación  → negativo
        #   ej.: -29.151.316 / 1.085.596.428 = -2,685 %  →  proyección × -2,685 %
        valores = {cta: {} for cta in CUENTAS_VENTAS}
        for mes in range(1, 13):
            base = proy_centro[mes]
            for cta, pct in participacion[mes].items():
                if cta in CUENTAS_DESCUENTO:
                    valores[cta][mes] = round(base * pct)
                else:
                    valores[cta][mes] = round(base * (1 + pct))

        for cta, meses in valores.items():
            total_anual = sum(meses.values())
            for mes, valor in meses.items():
                nuevos.append(ConsolidadoTotalBase(
                    mcncuenta=cta,
                    mcnccosto=None,      # sin centro de costo: evita reagrupaciones (ej. 0101 → 5105)
                    ctanombre=CUENTAS_VENTAS[cta],
                    mcnfecha=datetime.date(anio_ppto, mes, 1),
                    valor=valor,
                    total_anual=total_anual,
                    sede=sede,           # tulua | buga | cartago | cali
                    origen='presupuestado',
                ))

        procesadas.append(sede)
        anios_usados[sede] = anio_sede
        participacion_resp[sede] = {
            MESES_ES[m]: {cta: round(p * 100, 4) for cta, p in pcts.items()}
            for m, pcts in participacion.items()
        }
        detalle_resp[sede] = {
            'centro_operacion': centro,
            'proyeccion': {MESES_ES[m]: v for m, v in sorted(proy_centro.items())},
            'cuentas': {
                cta: {MESES_ES[m]: v for m, v in meses.items()}
                for cta, meses in valores.items()
            },
        }

    if not procesadas:
        raise ValueError(
            'No se pudo generar ninguna sede → '
            + '; '.join(f'{s}: {motivo}' for s, motivo in omitidas.items())
        )

    # Se borra lo generado antes para las sedes procesadas y también las filas
    # con sede='TOTAL' que dejaba la versión anterior (si no, el total se duplica).
    filtro_sede = Q()
    for s in procesadas + ['total']:
        filtro_sede |= Q(sede__iexact=s)

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(%s)', [LOCK_PRESUPUESTO_VENTAS])

        previas = (
            ConsolidadoTotalBase.objects
            .filter(filtro_sede, origen='presupuestado', mcnfecha__year=anio_ppto)
            .filter(q_cuentas_clave(CUENTAS_VENTAS))
            .values_list('id', 'mcncuenta', 'ctanombre')
        )
        ids = [pk for pk, cta, nom in previas if resolver_cuenta_clave(cta, nom) in CUENTAS_VENTAS]
        ConsolidadoTotalBase.objects.filter(id__in=ids).delete()
        ConsolidadoTotalBase.objects.bulk_create(nuevos)

    return {
        'anio_base': anios_usados,
        'anio_presupuesto': anio_ppto,
        'registros': len(nuevos),
        'sedes_procesadas': procesadas,
        'sedes_omitidas': omitidas,
        'participacion': participacion_resp,
        'detalle': detalle_resp,
    }


# ══════════════════════════════════════════════════════════════════
#  VISTA
# ══════════════════════════════════════════════════════════════════

@login_required
@require_POST
def generar_presupuesto_ventas_view(request):
    """POST  { "anio_base": 2026 }   (opcional)"""
    if request.user.username not in ['admin', 'NICOLAS']:
        return JsonResponse({'success': False, 'error': 'Sin permisos'}, status=403)
    try:
        body = json.loads(request.body or '{}')
        anio = body.get('anio_base')
        resultado = generar_presupuesto_ventas(int(anio) if anio else None)
        return JsonResponse({'success': True, **resultado})
    except (ValueError, json.JSONDecodeError) as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
