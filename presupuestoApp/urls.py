from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_home, name='dashboardPresupuesto'), 
    path('cuenta5/', views.cuenta5, name='cuenta5'),
    path('obtener-cuenta5-base/', views.obtener_cuenta5_base, name='obtener_cuenta5_base'),
    path('cargar-cuenta5-base/', views.cargar_cuenta5_base, name='cargar_cuenta5_base'),
    path("subir_excel_cuenta5/", views.subir_excel_cuenta5, name="subir_excel_cuenta5"),
    path("borrar_cuenta5_base/", views.borrar_cuenta5_base, name="borrar_cuenta5_base"),
    
    path('exportar-excel-presupuestos/', views.exportar_excel_presupuestos, name='exportar_excel_presupuestos'),
    
    path("exportar-excel/", views.exportar_excel_nomina, name="exportar_excel"),
    path('exportar-nomina-vertical/', views.exportar_nomina_vertical, name='exportar_nomina_vertical'),
    path('presupuesto-ventas/', views.base_comercial, name='baseComercial'), 
    
    # Presupuesto general ventas 
    path('presupuesto-general-ventas/', views.vista_presupuesto_general_ventas, name='presupuestoGeneralVentas'), 
    path('guardar-presupuesto-general-ventas/', views.guardar_presupuesto_general_ventas, name='guardar_presupuesto_general_ventas'),
    path('obtener-presupuesto-general-ventas/', views.obtener_presupuesto_general_ventas, name='obtener_presupuesto_general_ventas'),
    path('cargar-presupuesto-general-ventas/', views.cargar_presupuesto_general_ventas, name='cargar_presupuesto_general_ventas'),
    path('actualizar-presupuesto-general-ventas/', views.actualizar_presupuesto_general_ventas, name='actualizar_presupuesto_general_ventas'),
    
    # presupuesto centro ventas
    path('presupuesto-centro-ventas/', views.vista_presupuesto_centro_ventas, name='presupuestoCentroVentas'), 
    path('guardar-presupuesto-centro-ventas/', views.guardar_presupuesto_centro_ventas, name='guardar_presupuesto_centro_ventas'),
    path('obtener-presupuesto-centro-ventas/', views.obtener_presupuesto_centro_ventas, name='obtener_presupuesto_centro_ventas'),
    path('cargar-presupuesto-centro-ventas/', views.cargar_presupuesto_centro_ventas, name='cargar_presupuesto_centro_ventas'),
    path('actualizar-presupuesto-centro-ventas/', views.actualizar_presupuesto_centro_ventas, name='actualizar_presupuesto_centro_ventas'),
    
    # presupuesto centro - segmento ventas
    path('presupuesto-centro-segmento-ventas/', views.vista_presupuesto_centro_segmento_ventas, name='presupuestoCentroSegmentoVentas'), 
    path('guardar-presupuesto-centro-segmento-ventas/', views.guardar_presupuesto_centro_segmento_ventas, name='guardar_presupuesto_centro_segmento_ventas'),
    path('obtener-presupuesto-centro-segmento-ventas/', views.obtener_presupuesto_centro_segmento_ventas, name='obtener_presupuesto_centro_segmento_ventas'),
    path('cargar-presupuesto-centro-segmento-ventas/', views.cargar_presupuesto_centro_segmento_ventas, name='cargar_presupuesto_centro_segmento_ventas'),
    path('actualizar-presupuesto-centro-segmento-ventas/', views.actualizar_presupuesto_centro_segmento_ventas, name='actualizar_presupuesto_centro_segmento_ventas'),
    
    # presupuesto general costos
    path('presupuesto-general-costos/', views.vista_presupuesto_general_costos, name='presupuestoGeneralCostos'), 
    path('guardar-presupuesto-general-costos/', views.guardar_presupuesto_general_costos, name='guardar_presupuesto_general_costos'),
    path('obtener-presupuesto-general-costos/', views.obtener_presupuesto_general_costos, name='obtener_presupuesto_general_costos'),
    path('cargar-presupuesto-general-costos/', views.cargar_presupuesto_general_costos, name='cargar_presupuesto_general_costos'),
    
    # presupuesto centro costos
    path('presupuesto-centro-costos/', views.vista_presupuesto_centro_costos, name='presupuestoCentroCostos'), 
    path('guardar-presupuesto-centro-costos/', views.guardar_presupuesto_centro_costos, name='guardar_presupuesto_centro_costos'),
    path('obtener-presupuesto-centro-costos/', views.obtener_presupuesto_centro_costos, name='obtener_presupuesto_centro_costos'),
    path('cargar-presupuesto-centro-costos/', views.cargar_presupuesto_centro_costos, name='cargar_presupuesto_centro_costos'),
    
    # presupuesto centro-segmento costos
    path('presupuesto-centro-segmento-costos/', views.vista_presupuesto_centro_segmento_costos, name='presupuestoCentroSegmentoCostos'), 
    path('guardar-presupuesto-centro-segmento-costos/', views.guardar_presupuesto_centro_segmento_costos, name='guardar_presupuesto_centro_segmento_costos'),
    path('obtener-presupuesto-centro-segmento-costos/', views.obtener_presupuesto_centro_segmento_costos, name='obtener_presupuesto_centro_segmento_costos'),
    path('cargar-presupuesto-centro-segmento-costos/', views.cargar_presupuesto_centro_segmento_costos, name='cargar_presupuesto_centro_segmento_costos'),
    
    # presupuesto centro - segmento linea costos
    path('cargar-centro-segmento-linea-costos/', views.cargar_presupuesto_centro_segmento_linea_costos, name='cargarCentroSegmentoLineaCostos'),
    path('vista-centro-segmento-linea-costos/', views.vista_presupuesto_centro_segmento_linea_costos, name='vistaPresupuestoCentroSegmentoLineaCostos'),
    path('obtener-presupuesto-centro-segmento-linea-costos/', views.obtener_presupuesto_centro_segmento_linea_costos, name='obtener_presupuesto_centro_segmento_linea_costos'),
    
    # presupuesto centro - segmento linea ventas
    path('cargar-centro-segmento-linea-ventas/', views.cargar_presupuesto_centro_segmento_linea_ventas, name='cargarCentroSegmentoLineaVentas'),
    path('vista-centro-segmento-linea-ventas/', views.vista_presupuesto_centro_segmento_linea_ventas, name='vistaPresupuestoCentroSegmentoLineaVentas'),
    path('obtener-presupuesto-centro-segmento-linea-ventas/', views.obtener_presupuesto_centro_segmento_linea_ventas, name='obtener_presupuesto_centro_segmento_linea_ventas'),
    path('actualizar-presupuesto-centro-segmento-linea-ventas/', views.actualizar_presupuesto_centro_segmento_linea_ventas, name='actualizar_presupuesto_centro_segmento_linea_ventas'),
    
    #importar porcentajes del presupuesto desde excel
    path('importar_crecimiento_ventas/', views.importar_crecimiento_ventas, name='importar_crecimiento_ventas'),
    # exportar crecimiento ventas
    path('exportar-crecimiento-ventas/', views.exportar_crecimiento_ventas, name='exportar_crecimiento_ventas'),
    
    # presupuesto comercial
    path('presupuesto-comercial/', views.vista_presupuesto_comercial, name='presupuestoComercial'),
    path('guardar-presupuesto-comercial/', views.guardar_presupuesto_comercial, name='guardar_presupuesto_comercial'),
    path('obtener-presupuesto-comercial/', views.obtener_presupuesto_comercial, name='obtener_presupuesto_comercial'),
    path('cargar-presupuesto-comercial/', views.cargar_presupuesto_comercial, name='cargar_presupuesto_comercial'),
    
    path('presupuesto-nomina/', views.presupuestoNomina, name='presupuestoNomina'),
    # sueldos
    path("api/nomina/", views.obtener_presupuesto_sueldos, name="obtener_presupuesto_sueldos"),
    path("presupuesto-sueldos/", views.presupuesto_sueldos, name="sueldos"),
    path("tabla-auxiliar-sueldos/", views.tabla_auxiliar_sueldos, name="tabla_auxiliar_sueldos"), # ruta para la tabla temporal de los sueldos
    path("obtener_nomina_temp/", views.obtener_nomina_temp, name="obtener_nomina_temp"), 
    path("cargar_nomina_base/", views.cargar_nomina_base, name="cargar_nomina_base"),
    path("guardar_nomina_temp/", views.guardar_nomina_temp, name="guardar_nomina_temp"),
    path("guardar_nomina/", views.guardar_nomina, name="guardar_nomina"),
    path("subir-presupuesto-sueldos/", views.subir_presupuesto_sueldos, name="subir_presupuesto_sueldos"),
    path("borrar_presupuesto_sueldos/", views.borrar_presupuesto_sueldos, name="borrar_presupuesto_sueldos"),

    # comisiones
    path("comisiones/", views.comisiones, name="comisiones"),
    path("obtener-presupuesto-comisiones/", views.obtener_presupuesto_comisiones, name="obtener_presupuesto_comisiones"),
    path("tabla-auxiliar-comisiones/", views.tabla_auxiliar_comisiones, name="tabla_auxiliar_comisiones"), # ruta para la tabla temporal de las comisiones
    path("obtener-comisiones-temp/", views.obtener_comisiones_temp, name="obtener_comisiones_temp"),
    path("subir-presupuesto-comisiones/", views.subir_presupuesto_comisiones, name="subir_presupuesto_comisiones"),
    path("cargar-comisiones-base/", views.cargar_comisiones_base, name="cargar_comisiones_base"),
    path("guardar-comisiones-temp/", views.guardar_comisiones_temp, name="guardar_comisiones_temp"),
    path("guardar_comisiones/", views.guardar_comisiones, name="guardar_comisiones"),
    path("borrar_presupuesto_comisiones/", views.borrar_presupuesto_comisiones, name="borrar_presupuesto_comisiones"),
    
    # horas extra
    path("horas-extra/", views.horas_extra, name="horas_extra"),
    path("obtener-presupuesto-horas-extra/", views.obtener_presupuesto_horas_extra, name="obtener_presupuesto_horas_extra"),
    path("tabla-auxiliar-horas-extra/", views.tabla_auxiliar_horas_extra, name="tabla_auxiliar_horas_extra"), # ruta para la tabla temporal de las horas extra
    path("obtener-horas-extra-temp/", views.obtener_horas_extra_temp, name="obtener_horas_extra_temp"),
    path("subir-presupuesto-horas-extra/", views.subir_presupuesto_horas_extra, name="subir_presupuesto_horas_extra"),
    path("cargar-horas-extra-base/", views.cargar_horas_extra_base, name="cargar_horas_extra_base"),
    path("guardar-horas-extra-temp/", views.guardar_horas_extra_temp, name="guardar_horas_extra_temp"),
    path("guardar_horas_extra/", views.guardar_horas_extra, name="guardar_horas_extra"),
    path("borrar_presupuesto_horas_extra/", views.borrar_presupuesto_horas_extra, name="borrar_presupuesto_horas_extra"),
    
    # auxilio transporte
    path("auxilio-transporte/", views.auxilio_transporte, name="auxilio_transporte"),
    path("obtener-presupuesto-auxilio-transporte/", views.obtener_presupuesto_auxilio_transporte, name="obtener_presupuesto_auxilio_transporte"),
    path("tabla-auxiliar-auxilio-transporte/", views.tabla_auxiliar_auxilio_transporte, name="tabla_auxiliar_auxilio_transporte"), # ruta para la tabla temporal del auxilio de transporte
    path("obtener-auxilio-transporte-temp/", views.obtener_auxilio_transporte_temp, name="obtener_auxilio_transporte_temp"),
    path("subir-presupuesto-auxilio-transporte/", views.subir_presupuesto_auxilio_transporte, name="subir_presupuesto_auxilio_transporte"),
    path("cargar-auxilio-transporte-base/", views.cargar_auxilio_transporte_base, name="cargar_auxilio_transporte_base"),
    path("guardar-auxilio-transporte-temp/", views.guardar_auxilio_transporte_temp, name="guardar_auxilio_transporte_temp"),
    path("guardar_auxilio_transporte/", views.guardar_auxilio_transporte, name="guardar_auxilio_transporte"),
    path("borrar_presupuesto_auxilio_transporte/", views.borrar_presupuesto_auxilio_transporte, name="borrar_presupuesto_auxilio_transporte"),
    
    # medios transporte
    path("medios-transporte/", views.medios_transporte, name="medios_transporte"),
    path("obtener-presupuesto-medios-transporte/", views.obtener_presupuesto_medios_transporte, name="obtener_presupuesto_medios_transporte"),
    path("tabla-auxiliar-medios-transporte/", views.tabla_auxiliar_medios_transporte, name="tabla_auxiliar_medios_transporte"), # ruta para la tabla temporal de los medios de transporte
    path("obtener-medios-transporte-temp/", views.obtener_medios_transporte_temp, name="obtener_medios_transporte_temp"),
    path("subir-presupuesto-medios-transporte/", views.subir_presupuesto_medios_transporte, name="subir_presupuesto_medios_transporte"),
    path("cargar-medios-transporte-base/", views.cargar_medios_transporte_base, name="cargar_medios_transporte_base"),
    path("guardar-medios-transporte-temp/", views.guardar_medios_transporte_temp, name="guardar_medios_transporte_temp"),
    path("guardar_medios_transporte/", views.guardar_medios_transporte, name="guardar_medios_transporte"),
    path("borrar_presupuesto_medios_transporte/", views.borrar_presupuesto_medios_transporte, name="borrar_presupuesto_medios_transporte"),
    
    # ayuda transporte
    path("ayuda-transporte/", views.ayuda_transporte, name="ayuda_transporte"),
    path("obtener-presupuesto-ayuda-transporte/", views.obtener_presupuesto_ayuda_transporte, name="obtener_presupuesto_ayuda_transporte"),
    path("tabla-auxiliar-ayuda-transporte/", views.tabla_auxiliar_ayuda_transporte, name="tabla_auxiliar_ayuda_transporte"), # ruta para la tabla temporal del auxilio de transporte
    path("obtener-ayuda-transporte-temp/", views.obtener_ayuda_transporte_temp, name="obtener_ayuda_transporte_temp"),
    path("subir-presupuesto-ayuda-transporte/", views.subir_presupuesto_ayuda_transporte, name="subir_presupuesto_ayuda_transporte"),
    path("cargar-ayuda-transporte-base/", views.cargar_ayuda_transporte_base, name="cargar_ayuda_transporte_base"),
    path("guardar-ayuda-transporte-temp/", views.guardar_ayuda_transporte_temp, name="guardar_ayuda_transporte_temp"),
    path("guardar-ayuda-transporte/", views.guardar_ayuda_transporte, name="guardar_ayuda_transporte"),
    path("borrar_presupuesto_ayuda_transporte/", views.borrar_presupuesto_ayuda_transporte, name="borrar_presupuesto_ayuda_transporte"),
    
    # cesantias
    path("cesantias/", views.cesantias, name="cesantias"),
    path("obtener-presupuesto-cesantias/", views.obtener_presupuesto_cesantias, name="obtener_presupuesto_cesantias"),
    path("tabla-auxiliar-cesantias/", views.tabla_auxiliar_cesantias, name="tabla_auxiliar_cesantias"), # ruta para la tabla temporal de las cesantias
    path("obtener-cesantias-temp/", views.obtener_cesantias_temp, name="obtener_cesantias_temp"),
    path("subir-presupuesto-cesantias/", views.subir_presupuesto_cesantias, name="subir_presupuesto_cesantias"),
    path("cargar-cesantias-base/", views.cargar_cesantias_base, name="cargar_cesantias_base"),
    path("guardar-cesantias-temp/", views.guardar_cesantias_temp, name="guardar_cesantias_temp"),
    path("guardar_cesantias/", views.guardar_cesantias, name="guardar_cesantias"),
    path("borrar_presupuesto_cesantias/", views.borrar_presupuesto_cesantias, name="borrar_presupuesto_cesantias"),
    
    # prima
    path("prima/", views.prima, name="prima"),
    path("obtener-presupuesto-prima/", views.obtener_presupuesto_prima, name="obtener_presupuesto_prima"),
    path("tabla-auxiliar-prima/", views.tabla_auxiliar_prima, name="tabla_auxiliar_prima"), # ruta para la tabla temporal de las primas
    path("obtener-prima-temp/", views.obtener_prima_temp, name="obtener_prima_temp"),
    path("subir-presupuesto-prima/", views.subir_presupuesto_prima, name="subir_presupuesto_prima"),
    path("cargar-prima-base/", views.cargar_prima_base, name="cargar_prima_base"),
    path("guardar-prima-temp/", views.guardar_prima_temp, name="guardar_prima_temp"),
    path("guardar_prima/", views.guardar_prima, name="guardar_prima"),
    path("borrar_presupuesto_prima/", views.borrar_presupuesto_prima, name="borrar_presupuesto_prima"),
    
    # vacaciones
    path("vacaciones/", views.vacaciones, name="vacaciones"),
    path("obtener-presupuesto-vacaciones/", views.obtener_presupuesto_vacaciones, name="obtener_presupuesto_vacaciones"),
    path("tabla-auxiliar-vacaciones/", views.tabla_auxiliar_vacaciones, name="tabla_auxiliar_vacaciones"), # ruta para la tabla temporal de las vacaciones
    path("obtener-vacaciones-temp/", views.obtener_vacaciones_temp, name="obtener_vacaciones_temp"),
    path("subir-presupuesto-vacaciones/", views.subir_presupuesto_vacaciones, name="subir_presupuesto_vacaciones"),
    path("cargar-vacaciones-base/", views.cargar_vacaciones_base, name="cargar_vacaciones_base"),
    path("guardar-vacaciones-temp/", views.guardar_vacaciones_temp, name="guardar_vacaciones_temp"),
    path("guardar_vacaciones/", views.guardar_vacaciones, name="guardar_vacaciones"),
    path("borrar_presupuesto_vacaciones/", views.borrar_presupuesto_vacaciones, name="borrar_presupuesto_vacaciones"),
    
    # bonificaciones
    path("bonificaciones/", views.bonificaciones, name="bonificaciones"),
    path("obtener-presupuesto-bonificaciones/", views.obtener_presupuesto_bonificaciones, name="obtener_presupuesto_bonificaciones"),
    path("tabla-auxiliar-bonificaciones/", views.tabla_auxiliar_bonificaciones, name="tabla_auxiliar_bonificaciones"), # ruta para la tabla temporal de las bonificaciones
    path("obtener-bonificaciones-temp/", views.obtener_bonificaciones_temp, name="obtener_bonificaciones_temp"),
    path("subir-presupuesto-bonificaciones/", views.subir_presupuesto_bonificaciones, name="subir_presupuesto_bonificaciones"),
    path("cargar-bonificaciones-base/", views.cargar_bonificaciones_base, name="cargar_bonificaciones_base"),
    path("guardar-bonificaciones-temp/", views.guardar_bonificaciones_temp, name="guardar_bonificaciones_temp"),
    path("guardar_bonificaciones/", views.guardar_bonificaciones, name="guardar_bonificaciones"),
    path("borrar_presupuesto_bonificaciones/", views.borrar_presupuesto_bonificaciones, name="borrar_presupuesto_bonificaciones"),
    
    # auxilio bolsa consumibles
    path("bolsa_consumibles/", views.bolsa_consumibles, name="bolsa_consumibles"),
    path("obtener-presupuesto-bolsa_consumibles/", views.obtener_presupuesto_bolsa_consumibles, name="obtener_presupuesto_bolsa_consumibles"),
    path("tabla-auxiliar-bolsa_consumibles/", views.tabla_auxiliar_bolsa_consumibles, name="tabla_auxiliar_bolsa_consumibles"), # ruta para la tabla temporal del auxilio de movilidad
    path("obtener-bolsa_consumibles-temp/", views.obtener_bolsa_consumibles_temp, name="obtener_bolsa_consumibles_temp"),
    path("subir-presupuesto-bolsa_consumibles/", views.subir_presupuesto_bolsa_consumibles, name="subir_presupuesto_bolsa_consumibles"),
    path("cargar-bolsa_consumibles-base/", views.cargar_bolsa_consumibles_base, name="cargar_bolsa_consumibles_base"),
    path("guardar-bolsa_consumibles-temp/", views.guardar_bolsa_consumibles_temp, name="guardar_bolsa_consumibles_temp"),
    path("guardar_bolsa_consumibles/", views.guardar_bolsa_consumibles, name="guardar_bolsa_consumibles"),
    path("borrar_presupuesto_bolsa_consumibles/", views.borrar_presupuesto_bolsa_consumibles, name="borrar_presupuesto_bolsa_consumibles"),
    
    # auxilio tbckit
    path("auxilio-TBCKIT/", views.auxilio_TBCKIT, name="auxilio_TBCKIT"),
    path("obtener-presupuesto-auxilio-TBCKIT/", views.obtener_presupuesto_auxilio_TBCKIT, name="obtener_presupuesto_auxilio_TBCKIT"),
    path("tabla-auxiliar-auxilio-TBCKIT/", views.tabla_auxiliar_auxilio_TBCKIT, name="tabla_auxiliar_auxilio_TBCKIT"), # ruta para la tabla temporal del auxilio de movilidad
    path("obtener-auxilio-TBCKIT-temp/", views.obtener_auxilio_TBCKIT_temp, name="obtener_auxilio_TBCKIT_temp"),
    path("subir-presupuesto-auxilio-TBCKIT/", views.subir_presupuesto_auxilio_TBCKIT, name="subir_presupuesto_auxilio_TBCKIT"),
    path("cargar-auxilio-TBCKIT-base/", views.cargar_auxilio_TBCKIT_base, name="cargar_auxilio_TBCKIT_base"),
    path("guardar-auxilio-TBCKIT-temp/", views.guardar_auxilio_TBCKIT_temp, name="guardar_auxilio_TBCKIT_temp"),
    path("guardar_auxilio_TBCKIT/", views.guardar_auxilio_TBCKIT, name="guardar_auxilio_TBCKIT"),
    path("borrar_presupuesto_auxilio_TBCKIT/", views.borrar_presupuesto_auxilio_TBCKIT, name="borrar_presupuesto_auxilio_TBCKIT"),
    
    # seguridad social
    path("seguridad-social/", views.seguridad_social, name="seguridad_social"),
    path("obtener-presupuesto-seguridad-social/", views.obtener_presupuesto_seguridad_social, name="obtener_presupuesto_seguridad_social"),
    path("tabla-auxiliar-seguridad-social/", views.tabla_auxiliar_seguridad_social, name="tabla_auxiliar_seguridad_social"), # ruta para la tabla temporal de la seguridad social
    path("obtener-seguridad-social-temp/", views.obtener_seguridad_social_temp, name="obtener_seguridad_social_temp"),
    path("subir-presupuesto-seguridad-social/", views.subir_presupuesto_seguridad_social, name="subir_presupuesto_seguridad_social"),
    path("cargar-seguridad-social-base/", views.cargar_seguridad_social_base, name="cargar_seguridad_social_base"),
    path("guardar-seguridad-social-temp/", views.guardar_seguridad_social_temp, name="guardar_seguridad_social_temp"),
    path("borrar_presupuesto_seguridad_social/", views.borrar_presupuesto_seguridad_social, name="borrar_presupuesto_seguridad_social"),
    
    # intereses de cesantias
    path("intereses-cesantias/", views.intereses_cesantias, name="intereses_cesantias"),
    path("obtener-presupuesto-intereses-cesantias/", views.obtener_presupuesto_intereses_cesantias, name="obtener_presupuesto_intereses_cesantias"),
    path("tabla-auxiliar-intereses-cesantias/", views.tabla_auxiliar_intereses_cesantias, name="tabla_auxiliar_intereses_cesantias"), # ruta para la tabla temporal de los intereses de cesantias
    path("obtener-intereses-cesantias-temp/", views.obtener_intereses_cesantias_temp, name="obtener_intereses_cesantias_temp"),
    path("subir-presupuesto-intereses-cesantias/", views.subir_presupuesto_intereses_cesantias, name="subir_presupuesto_intereses_cesantias"),
    path("cargar-intereses-cesantias-base/", views.cargar_intereses_cesantias_base, name="cargar_intereses_cesantias_base"),
    path("guardar-intereses-cesantias-temp/", views.guardar_intereses_cesantias_temp, name="guardar_intereses_cesantias_temp"),
    path("guardar_intereses_cesantias/", views.guardar_intereses_cesantias, name="guardar_intereses_cesantias"),
    path("borrar_presupuesto_intereses_cesantias/", views.borrar_presupuesto_intereses_cesantias, name="borrar_presupuesto_intereses_cesantias"),
    
    # aprendiz
    path("aprendiz/", views.aprendiz, name="aprendiz"),
    path("obtener-presupuesto-aprendiz/", views.obtener_presupuesto_aprendiz, name="obtener_presupuesto_aprendiz"),
    path("tabla-auxiliar-aprendiz/", views.tabla_auxiliar_aprendiz, name="tabla_auxiliar_aprendiz"), # ruta para la tabla temporal del aprendiz
    path("obtener-aprendiz-temp/", views.obtener_aprendiz_temp, name="obtener_aprendiz_temp"),
    path("subir-presupuesto-aprendiz/", views.subir_presupuesto_aprendiz, name="subir_presupuesto_aprendiz"),
    path("cargar-aprendiz-base/", views.cargar_aprendiz_base, name="cargar_aprendiz_base"),
    path("guardar-aprendiz-temp/", views.guardar_aprendiz_temp, name="guardar_aprendiz_temp"),
    path("guardar_aprendiz/", views.guardar_aprendiz, name="guardar_aprendiz"),
    path("borrar_presupuesto_aprendiz/", views.borrar_presupuesto_aprendiz, name="borrar_presupuesto_aprendiz"),
    
    # bonificaciones foco
    path("bonificaciones-foco/", views.bonificaciones_foco, name="bonificaciones_foco"),
    path("obtener-presupuesto-bonificaciones-foco/", views.obtener_presupuesto_bonificaciones_foco, name="obtener_presupuesto_bonificaciones_foco"),
    path("tabla-auxiliar-bonificaciones-foco/", views.tabla_auxiliar_bonificaciones_foco, name="tabla_auxiliar_bonificaciones_foco"), # ruta para la tabla temporal de las bonificaciones foco
    path("obtener-bonificaciones-foco-temp/", views.obtener_bonificaciones_foco_temp, name="obtener_bonificaciones_foco_temp"),
    path("subir-presupuesto-bonificaciones-foco/", views.subir_presupuesto_bonificaciones_foco, name="subir_presupuesto_bonificaciones_foco"),
    path("cargar-bonificaciones-foco-base/", views.cargar_bonificaciones_foco_base, name="cargar_bonificaciones_foco_base"),
    path("guardar-bonificaciones-foco-temp/", views.guardar_bonificaciones_foco_temp, name="guardar_bonificaciones_foco_temp"),
    path("guardar_bonificaciones_foco/", views.guardar_bonificaciones_foco, name="guardar_bonificaciones_foco"),
    path("borrar_presupuesto_bonificaciones_foco/", views.borrar_presupuesto_bonificaciones_foco, name="borrar_presupuesto_bonificaciones_foco"),
    
    # auxilio educacion
    path("auxilio-educacion/", views.auxilio_educacion, name="auxilio_educacion"),
    path("obtener-presupuesto-auxilio-educacion/", views.obtener_presupuesto_auxilio_educacion, name="obtener_presupuesto_auxilio_educacion"),
    path("tabla-auxiliar-auxilio-educacion/", views.tabla_auxiliar_auxilio_educacion, name="tabla_auxiliar_auxilio_educacion"), # ruta para la tabla temporal del auxilio de educacion
    path("obtener-auxilio-educacion-temp/", views.obtener_auxilio_educacion_temp, name="obtener_auxilio_educacion_temp"),
    path("subir-presupuesto-auxilio-educacion/", views.subir_presupuesto_auxilio_educacion, name="subir_presupuesto_auxilio_educacion"),
    path("cargar-auxilio-educacion-base/", views.cargar_auxilio_educacion_base, name="cargar_auxilio_educacion_base"),
    path("guardar-auxilio-educacion-temp/", views.guardar_auxilio_educacion_temp, name="guardar_auxilio_educacion_temp"),
    path("guardar_auxilio_educacion/", views.guardar_auxilio_educacion, name="guardar_auxilio_educacion"),
    path("borrar_presupuesto_auxilio_educacion/", views.borrar_presupuesto_auxilio_educacion, name="borrar_presupuesto_auxilio_educacion"),
    
    # bonos kyrovet
    path("bonos-kyrovet/", views.bonos_kyrovet, name="bonos_kyrovet"),
    path("obtener-presupuesto-bonos-kyrovet/", views.obtener_presupuesto_bonos_kyrovet, name="obtener_presupuesto_bonos_kyrovet"),
    path("tabla-auxiliar-bonos-kyrovet/", views.tabla_auxiliar_bonos_kyrovet, name="tabla_auxiliar_bonos_kyrovet"), # ruta para la tabla temporal de los bonos kyrovet
    path("obtener-bonos-kyrovet-temp/", views.obtener_bonos_kyrovet_temp, name="obtener_bonos_kyrovet_temp"),
    path("subir-presupuesto-bonos-kyrovet/", views.subir_presupuesto_bonos_kyrovet, name="subir_presupuesto_bonos_kyrovet"),
    path("cargar-bonos-kyrovet-base/", views.cargar_bonos_kyrovet_base, name="cargar_bonos_kyrovet_base"),
    path("guardar-bonos-kyrovet-temp/", views.guardar_bonos_kyrovet_temp, name="guardar_bonos_kyrovet_temp"),
    path("guardar_bonos_kyrovet/", views.guardar_bonos_kyrovet, name="guardar_bonos_kyrovet"),
    path("borrar_presupuesto_bonos_kyrovet/", views.borrar_presupuesto_bonos_kyrovet, name="borrar_presupuesto_bonos_kyrovet"),
    
    #-----------------------------PRESUPUESTO GENERAL--------------------------------
    #----CUENTAS CONTABLES---------
    path('seleccion-cuentas-contables/', views.seleccion_cuentas_contables, name='seleccionCuentasContables'),
    
    #----------PRESUPUESTO TECNOLOGIA---------
    path('presupuesto-tecnologia/', views.presupuesto_tecnologia, name='presupuestoTecnologia'),
    path('obtener-presupuesto-tecnologia/', views.obtener_presupuesto_tecnologia, name='obtener_presupuesto_tecnologia'),
    path('presupuesto-aprobado-tecnologia/', views.presupuesto_aprobado_tecnologia, name='presupuestoAprobadoTecnologia'),
    path('obtener-presupuesto-aprobado-tecnologia/', views.obtener_presupuesto_aprobado_tecnologia, name='obtener_presupuesto_aprobado_tecnologia'),
    path('tabla-auxiliar-tecnologia/', views.tabla_auxiliar_tecnologia, name='tabla_auxiliar_tecnologia'), # ruta para la tabla temporal de la tecnologia
    path('obtener-tecnologia-temp/', views.obtener_tecnologia_temp, name='obtener_tecnologia_temp'),
    path('cargar-tecnologia-base/', views.cargar_tecnologia_base, name='cargar_tecnologia_base'),
    path('guardar-tecnologia-temp/', views.guardar_tecnologia_temp, name='guardar_tecnologia_temp'),
    path('subir-presupuesto-tecnologia/', views.subir_presupuesto_tecnologia, name='subir_presupuesto_tecnologia'),
    path('borrar_presupuesto_tecnologia/', views.borrar_presupuesto_tecnologia, name='borrar_presupuesto_tecnologia'),
    
    #------PRESUPUESTO OCUPACIONAL---------------------------------
    path('presupuesto-ocupacional/', views.presupuesto_ocupacional, name='presupuestoOcupacional'), 
    path('obtener-presupuesto-ocupacional/', views.obtener_presupuesto_ocupacional, name='obtener_presupuesto_ocupacional'),
    path('presupuesto-aprobado-ocupacional/', views.presupuesto_aprobado_ocupacional, name='presupuestoAprobadoOcupacional'), 
    path('obtener-presupuesto-aprobado-ocupacional/', views.obtener_presupuesto_aprobado_ocupacional, name='obtener_presupuesto_aprobado_ocupacional'),
    path('tabla-auxiliar-ocupacional/', views.tabla_auxiliar_ocupacional, name='tabla_auxiliar_ocupacional'), # ruta para la tabla temporal del presupuesto ocupacional
    path('obtener-ocupacional-temp/', views.obtener_ocupacional_temp, name='obtener_ocupacional_temp'),
    path('cargar-ocupacional-base/', views.cargar_ocupacional_base, name='cargar_ocupacional_base'),
    path('guardar-ocupacional-temp/', views.guardar_ocupacional_temp, name='guardar_ocupacional_temp'),
    path('subir-presupuesto-ocupacional/', views.subir_presupuesto_ocupacional, name='subir_presupuesto_ocupacional'),
    path('borrar_presupuesto_ocupacional/', views.borrar_presupuesto_ocupacional, name='borrar_presupuesto_ocupacional'),
    
    #------PRESUPUESTO SERVICIOS TECNICOS---------------------------------
    path('presupuesto-servicios-tecnicos/', views.presupuesto_servicios_tecnicos, name='presupuestoServiciosTecnicos'), 
    path('obtener-presupuesto-servicios-tecnicos/', views.obtener_presupuesto_servicios_tecnicos, name='obtener_presupuesto_servicios_tecnicos'),
    path('presupuesto-aprobado-servicios-tecnicos/', views.presupuesto_aprobado_servicios_tecnicos, name='presupuestoAprobadoServiciosTecnicos'), 
    path('obtener-presupuesto-aprobado-servicios-tecnicos/', views.obtener_presupuesto_aprobado_servicios_tecnicos, name='obtener_presupuesto_aprobado_servicios_tecnicos'),
    path('tabla-auxiliar-servicios-tecnicos/', views.tabla_auxiliar_servicios_tecnicos, name='tabla_auxiliar_servicios_tecnicos'), # ruta para la tabla temporal del presupuesto servicios tecnicos
    path('obtener-servicios-tecnicos-temp/', views.obtener_servicios_tecnicos_temp, name='obtener_servicios_tecnicos_temp'),
    path('cargar-servicios-tecnicos-base/', views.cargar_servicios_tecnicos_base, name='cargar_servicios_tecnicos_base'),
    path('guardar-servicios-tecnicos-temp/', views.guardar_servicios_tecnicos_temp, name='guardar_servicios_tecnicos_temp'),
    path('subir-presupuesto-servicios-tecnicos/', views.subir_presupuesto_servicios_tecnicos, name='subir_presupuesto_servicios_tecnicos'),
    path('borrar_presupuesto_servicios_tecnicos/', views.borrar_presupuesto_servicios_tecnicos, name='borrar_presupuesto_servicios_tecnicos'),
    
    #------PRESUPUESTO LOGISTICA---------------------------------
    path('presupuesto-logistica/', views.presupuesto_logistica, name='presupuestoLogistica'), 
    path('obtener-presupuesto-logistica/', views.obtener_presupuesto_logistica, name='obtener_presupuesto_logistica'),
    path('presupuesto-aprobado-logistica/', views.presupuesto_aprobado_logistica, name='presupuestoAprobadoLogistica'), 
    path('obtener-presupuesto-aprobado-logistica/', views.obtener_presupuesto_aprobado_logistica, name='obtener_presupuesto_aprobado_logistica'),
    path('tabla-auxiliar-logistica/', views.tabla_auxiliar_logistica, name='tabla_auxiliar_logistica'), # ruta para la tabla temporal del presupuesto logistica
    path('obtener-logistica-temp/', views.obtener_logistica_temp, name='obtener_logistica_temp'),
    path('cargar-logistica-base/', views.cargar_logistica_base, name='cargar_logistica_base'),
    path('guardar-logistica-temp/', views.guardar_logistica_temp, name='guardar_logistica_temp'),
    path('subir-presupuesto-logistica/', views.subir_presupuesto_logistica, name='subir_presupuesto_logistica'),
    path('borrar_presupuesto_logistica/', views.borrar_presupuesto_logistica, name='borrar_presupuesto_logistica'),
 
    #----------PRESUPUESTO GESTION DE RIESGOS---------
    path('presupuesto-gestion-riesgos/', views.presupuesto_gestion_riesgos, name='presupuestoGestionRiesgos'), 
    path('obtener-presupuesto-gestion-riesgos/', views.obtener_presupuesto_gestion_riesgos, name='obtener_presupuesto_gestion_riesgos'),
    path('presupuesto-aprobado-gestion-riesgos/', views.presupuesto_aprobado_gestion_riesgos, name='presupuestoAprobadoGestionRiesgos'), 
    path('obtener-presupuesto-aprobado-gestion-riesgos/', views.obtener_presupuesto_aprobado_gestion_riesgos, name='obtener_presupuesto_aprobado_gestion_riesgos'),
    path('tabla-auxiliar-gestion-riesgos/', views.tabla_auxiliar_gestion_riesgos, name='tabla_auxiliar_gestion_riesgos'), # ruta para la tabla temporal de la gestion de riesgos
    path('obtener-gestion-riesgos-temp/', views.obtener_gestion_riesgos_temp, name='obtener_gestion_riesgos_temp'),
    path('cargar-gestion-riesgos-base/', views.cargar_gestion_riesgos_base, name='cargar_gestion_riesgos_base'),
    path('guardar-gestion-riesgos-temp/', views.guardar_gestion_riesgos_temp, name='guardar_gestion_riesgos_temp'),
    path('subir-presupuesto-gestion-riesgos/', views.subir_presupuesto_gestion_riesgos, name='subir_presupuesto_gestion_riesgos'),
    path('borrar_presupuesto_gestion_riesgos/', views.borrar_presupuesto_gestion_riesgos, name='borrar_presupuesto_gestion_riesgos'),
     
    #-----------PRESUPUESTO GH----------------
    path('presupuesto-gh/', views.presupuesto_gh, name='presupuestoGH'), 
    path('obtener-presupuesto-gh/', views.obtener_presupuesto_gh, name='obtener_presupuesto_gh'),
    path('presupuesto-aprobado-gh/', views.presupuesto_aprobado_gh, name='presupuestoAprobadoGH'), 
    path('obtener-presupuesto-aprobado-gh/', views.obtener_presupuesto_aprobado_gh, name='obtener_presupuesto_aprobado_gh'),
    path('tabla-auxiliar-gh/', views.tabla_auxiliar_gh, name='tabla_auxiliar_gh'), # ruta para la tabla temporal del presupuesto gh
    path('obtener-gh-temp/', views.obtener_gh_temp, name='obtener_gh_temp'),
    path('cargar-gh-base/', views.cargar_gh_base, name='cargar_gh_base'),
    path('guardar-gh-temp/', views.guardar_gh_temp, name='guardar_gh_temp'),
    path('subir-presupuesto-gh/', views.subir_presupuesto_gh, name='subir_presupuesto_gh'),
    path('borrar_presupuesto_gh/', views.borrar_presupuesto_gh, name='borrar_presupuesto_gh'),
    
    #-------------PRESUPUESTO ALMACEN TULUA----------------
    path('presupuesto-almacen-tulua/', views.presupuesto_almacen_tulua, name='presupuestoAlmacenTulua'), 
    path('obtener-presupuesto-almacen-tulua/', views.obtener_presupuesto_almacen_tulua, name='obtener_presupuesto_almacen_tulua'),
    path('presupuesto-aprobado-almacen-tulua/', views.presupuesto_aprobado_almacen_tulua, name='presupuestoAprobadoAlmacenTulua'), 
    path('obtener-presupuesto-aprobado-almacen-tulua/', views.obtener_presupuesto_aprobado_almacen_tulua, name='obtener_presupuesto_aprobado_almacen_tulua'),
    path('tabla-auxiliar-almacen-tulua/', views.tabla_auxiliar_almacen_tulua, name='tabla_auxiliar_almacen_tulua'), # ruta para la tabla temporal del presupuesto almacen tulua
    path('obtener-almacen-tulua-temp/', views.obtener_almacen_tulua_temp, name='obtener_almacen_tulua_temp'),
    path('cargar-almacen-tulua-base/', views.cargar_almacen_tulua_base, name='cargar_almacen_tulua_base'),
    path('guardar-almacen-tulua-temp/', views.guardar_almacen_tulua_temp, name='guardar_almacen_tulua_temp'),
    path('subir-presupuesto-almacen-tulua/', views.subir_presupuesto_almacen_tulua, name='subir_presupuesto_almacen_tulua'),
    path('borrar_presupuesto_almacen_tulua/', views.borrar_presupuesto_almacen_tulua, name='borrar_presupuesto_almacen_tulua'),
    
    #-------------PRESUPUESTO ALMACEN BUGA----------------
    path('presupuesto-almacen-buga/', views.presupuesto_almacen_buga, name='presupuestoAlmacenBuga'), 
    path('obtener-presupuesto-almacen-buga/', views.obtener_presupuesto_almacen_buga, name='obtener_presupuesto_almacen_buga'),
    path('presupuesto-aprobado-almacen-buga/', views.presupuesto_aprobado_almacen_buga, name='presupuestoAprobadoAlmacenBuga'), 
    path('obtener-presupuesto-aprobado-almacen-buga/', views.obtener_presupuesto_aprobado_almacen_buga, name='obtener_presupuesto_aprobado_almacen_buga'),
    path('tabla-auxiliar-almacen-buga/', views.tabla_auxiliar_almacen_buga, name='tabla_auxiliar_almacen_buga'), # ruta para la tabla temporal del presupuesto almacen buga
    path('obtener-almacen-buga-temp/', views.obtener_almacen_buga_temp, name='obtener_almacen_buga_temp'),
    path('cargar-almacen-buga-base/', views.cargar_almacen_buga_base, name='cargar_almacen_buga_base'),
    path('guardar-almacen-buga-temp/', views.guardar_almacen_buga_temp, name='guardar_almacen_buga_temp'),
    path('subir-presupuesto-almacen-buga/', views.subir_presupuesto_almacen_buga, name='subir_presupuesto_almacen_buga'),
    path('borrar_presupuesto_almacen_buga/', views.borrar_presupuesto_almacen_buga, name='borrar_presupuesto_almacen_buga'),
    
    #-------------PRESUPUESTO ALMACEN CARTAGO----------------
    path('presupuesto-almacen-cartago/', views.presupuesto_almacen_cartago, name='presupuestoAlmacenCartago'), 
    path('obtener-presupuesto-almacen-cartago/', views.obtener_presupuesto_almacen_cartago, name='obtener_presupuesto_almacen_cartago'),
    path('presupuesto-aprobado-almacen-cartago/', views.presupuesto_aprobado_almacen_cartago, name='presupuestoAprobadoAlmacenCartago'), 
    path('obtener-presupuesto-aprobado-almacen-cartago/', views.obtener_presupuesto_aprobado_almacen_cartago, name='obtener_presupuesto_aprobado_almacen_cartago'),
    path('tabla-auxiliar-almacen-cartago/', views.tabla_auxiliar_almacen_cartago, name='tabla_auxiliar_almacen_cartago'), # ruta para la tabla temporal del presupuesto almacen cartago
    path('obtener-almacen-cartago-temp/', views.obtener_almacen_cartago_temp, name='obtener_almacen_cartago_temp'),
    path('cargar-almacen-cartago-base/', views.cargar_almacen_cartago_base, name='cargar_almacen_cartago_base'),
    path('guardar-almacen-cartago-temp/', views.guardar_almacen_cartago_temp, name='guardar_almacen_cartago_temp'),
    path('subir-presupuesto-almacen-cartago/', views.subir_presupuesto_almacen_cartago, name='subir_presupuesto_almacen_cartago'),
    path('borrar_presupuesto_almacen_cartago/', views.borrar_presupuesto_almacen_cartago, name='borrar_presupuesto_almacen_cartago'),
    
    #-------------PRESUPUESTO ALMACEN CALI----------------
    path('presupuesto-almacen-cali/', views.presupuesto_almacen_cali, name='presupuestoAlmacenCali'), 
    path('obtener-presupuesto-almacen-cali/', views.obtener_presupuesto_almacen_cali, name='obtener_presupuesto_almacen_cali'),
    path('presupuesto-aprobado-almacen-cali/', views.presupuesto_aprobado_almacen_cali, name='presupuestoAprobadoAlmacenCali'), 
    path('obtener-presupuesto-aprobado-almacen-cali/', views.obtener_presupuesto_aprobado_almacen_cali, name='obtener_presupuesto_aprobado_almacen_cali'),
    path('tabla-auxiliar-almacen-cali/', views.tabla_auxiliar_almacen_cali, name='tabla_auxiliar_almacen_cali'), # ruta para la tabla temporal del presupuesto almacen cali
    path('obtener-almacen-cali-temp/', views.obtener_almacen_cali_temp, name='obtener_almacen_cali_temp'),
    path('cargar-almacen-cali-base/', views.cargar_almacen_cali_base, name='cargar_almacen_cali_base'),
    path('guardar-almacen-cali-temp/', views.guardar_almacen_cali_temp, name='guardar_almacen_cali_temp'),
    path('subir-presupuesto-almacen-cali/', views.subir_presupuesto_almacen_cali, name='subir_presupuesto_almacen_cali'),
    path('borrar_presupuesto_almacen_cali/', views.borrar_presupuesto_almacen_cali, name='borrar_presupuesto_almacen_cali'),
    
    #-------------PRESUPUESTO COMUNICACIONES----------------
    path('presupuesto-comunicaciones/', views.presupuesto_comunicaciones, name='presupuestoComunicaciones'), 
    path('obtener-presupuesto-comunicaciones/', views.obtener_presupuesto_comunicaciones, name='obtener_presupuesto_comunicaciones'),
    path('presupuesto-aprobado-comunicaciones/', views.presupuesto_aprobado_comunicaciones, name='presupuestoAprobadoComunicaciones'), 
    path('obtener-presupuesto-aprobado-comunicaciones/', views.obtener_presupuesto_aprobado_comunicaciones, name='obtener_presupuesto_aprobado_comunicaciones'),
    path('tabla-auxiliar-comunicaciones/', views.tabla_auxiliar_comunicaciones, name='tabla_auxiliar_comunicaciones'), # ruta para la tabla temporal del presupuesto comunicaciones
    path('obtener-comunicaciones-temp/', views.obtener_comunicaciones_temp, name='obtener_comunicaciones_temp'),
    path('cargar-comunicaciones-base/', views.cargar_comunicaciones_base, name='cargar_comunicaciones_base'),
    path('guardar-comunicaciones-temp/', views.guardar_comunicaciones_temp, name='guardar_comunicaciones_temp'),
    path('subir-presupuesto-comunicaciones/', views.subir_presupuesto_comunicaciones, name='subir_presupuesto_comunicaciones'),
    path('borrar_presupuesto_comunicaciones/', views.borrar_presupuesto_comunicaciones, name='borrar_presupuesto_comunicaciones'),
    
    #-----------PRESUPUESTO COMERCIAL COSTOS----------------
    path('presupuesto-comercial-costos/', views.presupuesto_comercial_costos, name='presupuestoComercialCostos'),
    path('obtener-presupuesto-comercial-costos/', views.obtener_presupuesto_comercial_costos, name='obtener_presupuesto_comercial_costos'),
    path('presupuesto-aprobado-comercial-costos/', views.presupuesto_aprobado_comercial_costos, name='presupuestoAprobadoComercialCostos'), 
    path('obtener-presupuesto-aprobado-comercial-costos/', views.obtener_presupuesto_aprobado_comercial_costos, name='obtener_presupuesto_aprobado_comercial_costos'),
    path('tabla-auxiliar-comercial-costos/', views.tabla_auxiliar_comercial_costos, name='tabla_auxiliar_comercial_costos'), # ruta para la tabla temporal del presupuesto comercial costos
    path('obtener-comercial-costos-temp/', views.obtener_comercial_costos_temp, name='obtener_comercial_costos_temp'),
    path('cargar-comercial-costos-base/', views.cargar_comercial_costos_base, name='cargar_comercial_costos_base'),
    path('guardar-comercial-costos-temp/', views.guardar_comercial_costos_temp, name='guardar_comercial_costos_temp'),
    path('subir-presupuesto-comercial-costos/', views.subir_presupuesto_comercial_costos, name='subir_presupuesto_comercial_costos'),
    path('borrar_presupuesto_comercial_costos/', views.borrar_presupuesto_comercial_costos, name='borrar_presupuesto_comercial_costos'),
    
    #--------------------PRESUPUESTO CONTABILIDAD---------------------------
    path('presupuesto-contabilidad/', views.presupuesto_contabilidad, name='presupuestoContabilidad'), 
    path('obtener-presupuesto-contabilidad/', views.obtener_presupuesto_contabilidad, name='obtener_presupuesto_contabilidad'),
    path('presupuesto-aprobado-contabilidad/', views.presupuesto_aprobado_contabilidad, name='presupuestoAprobadoContabilidad'), 
    path('obtener-presupuesto-aprobado-contabilidad/', views.obtener_presupuesto_aprobado_contabilidad, name='obtener_presupuesto_aprobado_contabilidad'),
    path('tabla-auxiliar-contabilidad/', views.tabla_auxiliar_contabilidad, name='tabla_auxiliar_contabilidad'), # ruta para la tabla temporal del presupuesto contabilidad
    path('obtener-contabilidad-temp/', views.obtener_contabilidad_temp, name='obtener_contabilidad_temp'),
    path('cargar-contabilidad-base/', views.cargar_contabilidad_base, name='cargar_contabilidad_base'),
    path('guardar-contabilidad-temp/', views.guardar_contabilidad_temp, name='guardar_contabilidad_temp'),
    path('subir-presupuesto-contabilidad/', views.subir_presupuesto_contabilidad, name='subir_presupuesto_contabilidad'),
    path('borrar_presupuesto_contabilidad/', views.borrar_presupuesto_contabilidad, name='borrar_presupuesto_contabilidad'),
    
    #-------------------PRESUPUESTO GERENCIA----------------------------
    path('presupuesto-gerencia/', views.presupuesto_gerencia, name='presupuestoGerencia'),
    path('obtener-presupuesto-gerencia/', views.obtener_presupuesto_gerencia, name='obtener_presupuesto_gerencia'), 
    path('presupuesto-aprobado-gerencia/', views.presupuesto_aprobado_gerencia, name='presupuestoAprobadoGerencia'), 
    path('obtener-presupuesto-aprobado-gerencia/', views.obtener_presupuesto_aprobado_gerencia, name='obtener_presupuesto_aprobado_gerencia'),
    path('tabla-auxiliar-gerencia/', views.tabla_auxiliar_gerencia, name='tabla_auxiliar_gerencia'), # ruta para la tabla temporal del presupuesto gerencia
    path('obtener-gerencia-temp/', views.obtener_gerencia_temp, name='obtener_gerencia_temp'),
    path('cargar-gerencia-base/', views.cargar_gerencia_base, name='cargar_gerencia_base'),
    path('guardar-gerencia-temp/', views.guardar_gerencia_temp, name='guardar_gerencia_temp'),
    path('subir-presupuesto-gerencia/', views.subir_presupuesto_gerencia, name='subir_presupuesto_gerencia'),
    path('borrar_presupuesto_gerencia/', views.borrar_presupuesto_gerencia, name='borrar_presupuesto_gerencia'),
    
    #------------------PRESUPUESTO CONSOLIDADO---------------------------
    path('<str:area>/', views.presupuesto_consolidado, name='presupuesto_consolidado'),
    path('<str:area>/obtener-presupuesto-consolidado/', views.obtener_presupuesto_consolidado, name='obtener_presupuesto_consolidado'),
    path('<str:area>/guardar/', views.guardar_presupuesto_consolidado, name='guardar_presupuesto_consolidado'),
    
]
