from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboardPresupuesto'),
    path('presupuesto-ventas/', views.presupuesto_comercial, name='presupuestoVentas'), 
    path("exportar-excel/", views.exportar_excel_presupuestos, name="exportar_excel"),
    
    path('presupuesto-nomina/', views.presupuestoNomina, name='presupuestoNomina'),
    # sueldos
    path("api/nomina/", views.obtener_presupuesto_sueldos, name="obtener_presupuesto_sueldos"),
    path("presupuesto-sueldos/", views.presupuesto_sueldos, name="sueldos"),
    path("tabla-auxiliar-sueldos/", views.tabla_auxiliar_sueldos, name="tabla_auxiliar_sueldos"), # ruta para la tabla temporal de los sueldos
    path("obtener_nomina_temp/", views.obtener_nomina_temp, name="obtener_nomina_temp"), 
    path("cargar_nomina_base/", views.cargar_nomina_base, name="cargar_nomina_base"),
    path("guardar_nomina_temp/", views.guardar_nomina_temp, name="guardar_nomina_temp"),
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
    path("borrar_presupuesto_comisiones/", views.borrar_presupuesto_comisiones, name="borrar_presupuesto_comisiones"),
    
    # horas extra
    path("horas-extra/", views.horas_extra, name="horas_extra"),
    path("obtener-presupuesto-horas-extra/", views.obtener_presupuesto_horas_extra, name="obtener_presupuesto_horas_extra"),
    path("tabla-auxiliar-horas-extra/", views.tabla_auxiliar_horas_extra, name="tabla_auxiliar_horas_extra"), # ruta para la tabla temporal de las horas extra
    path("obtener-horas-extra-temp/", views.obtener_horas_extra_temp, name="obtener_horas_extra_temp"),
    path("subir-presupuesto-horas-extra/", views.subir_presupuesto_horas_extra, name="subir_presupuesto_horas_extra"),
    path("cargar-horas-extra-base/", views.cargar_horas_extra_base, name="cargar_horas_extra_base"),
    path("guardar-horas-extra-temp/", views.guardar_horas_extra_temp, name="guardar_horas_extra_temp"),
    path("borrar_presupuesto_horas_extra/", views.borrar_presupuesto_horas_extra, name="borrar_presupuesto_horas_extra"),
    
    # auxilio transporte
    path("auxilio-transporte/", views.auxilio_transporte, name="auxilio_transporte"),
    path("obtener-presupuesto-auxilio-transporte/", views.obtener_presupuesto_auxilio_transporte, name="obtener_presupuesto_auxilio_transporte"),
    path("tabla-auxiliar-auxilio-transporte/", views.tabla_auxiliar_auxilio_transporte, name="tabla_auxiliar_auxilio_transporte"), # ruta para la tabla temporal del auxilio de transporte
    path("obtener-auxilio-transporte-temp/", views.obtener_auxilio_transporte_temp, name="obtener_auxilio_transporte_temp"),
    path("subir-presupuesto-auxilio-transporte/", views.subir_presupuesto_auxilio_transporte, name="subir_presupuesto_auxilio_transporte"),
    path("cargar-auxilio-transporte-base/", views.cargar_auxilio_transporte_base, name="cargar_auxilio_transporte_base"),
    path("guardar-auxilio-transporte-temp/", views.guardar_auxilio_transporte_temp, name="guardar_auxilio_transporte_temp"),
    path("borrar_presupuesto_auxilio_transporte/", views.borrar_presupuesto_auxilio_transporte, name="borrar_presupuesto_auxilio_transporte"),
    
    # medios transporte
    path("medios-transporte/", views.medios_transporte, name="medios_transporte"),
    path("obtener-presupuesto-medios-transporte/", views.obtener_presupuesto_medios_transporte, name="obtener_presupuesto_medios_transporte"),
    path("tabla-auxiliar-medios-transporte/", views.tabla_auxiliar_medios_transporte, name="tabla_auxiliar_medios_transporte"), # ruta para la tabla temporal de los medios de transporte
    path("obtener-medios-transporte-temp/", views.obtener_medios_transporte_temp, name="obtener_medios_transporte_temp"),
    path("subir-presupuesto-medios-transporte/", views.subir_presupuesto_medios_transporte, name="subir_presupuesto_medios_transporte"),
    path("cargar-medios-transporte-base/", views.cargar_medios_transporte_base, name="cargar_medios_transporte_base"),
    path("guardar-medios-transporte-temp/", views.guardar_medios_transporte_temp, name="guardar_medios_transporte_temp"),
    path("borrar_presupuesto_medios_transporte/", views.borrar_presupuesto_medios_transporte, name="borrar_presupuesto_medios_transporte"),
    
    # ayuda transporte
    path("ayuda-transporte/", views.ayuda_transporte, name="ayuda_transporte"),
    path("obtener-presupuesto-ayuda-transporte/", views.obtener_presupuesto_ayuda_transporte, name="obtener_presupuesto_ayuda_transporte"),
    path("tabla-auxiliar-ayuda-transporte/", views.tabla_auxiliar_ayuda_transporte, name="tabla_auxiliar_ayuda_transporte"), # ruta para la tabla temporal del auxilio de transporte
    path("obtener-ayuda-transporte-temp/", views.obtener_ayuda_transporte_temp, name="obtener_ayuda_transporte_temp"),
    path("subir-presupuesto-ayuda-transporte/", views.subir_presupuesto_ayuda_transporte, name="subir_presupuesto_ayuda_transporte"),
    path("cargar-ayuda-transporte-base/", views.cargar_ayuda_transporte_base, name="cargar_ayuda_transporte_base"),
    path("guardar-ayuda-transporte-temp/", views.guardar_ayuda_transporte_temp, name="guardar_ayuda_transporte_temp"),
    path("borrar_presupuesto_ayuda_transporte/", views.borrar_presupuesto_ayuda_transporte, name="borrar_presupuesto_ayuda_transporte"),
    
    # cesantias
    path("cesantias/", views.cesantias, name="cesantias"),
    path("obtener-presupuesto-cesantias/", views.obtener_presupuesto_cesantias, name="obtener_presupuesto_cesantias"),
    path("tabla-auxiliar-cesantias/", views.tabla_auxiliar_cesantias, name="tabla_auxiliar_cesantias"), # ruta para la tabla temporal de las cesantias
    path("obtener-cesantias-temp/", views.obtener_cesantias_temp, name="obtener_cesantias_temp"),
    path("subir-presupuesto-cesantias/", views.subir_presupuesto_cesantias, name="subir_presupuesto_cesantias"),
    path("cargar-cesantias-base/", views.cargar_cesantias_base, name="cargar_cesantias_base"),
    path("guardar-cesantias-temp/", views.guardar_cesantias_temp, name="guardar_cesantias_temp"),
    path("borrar_presupuesto_cesantias/", views.borrar_presupuesto_cesantias, name="borrar_presupuesto_cesantias"),
    
    # prima
    path("prima/", views.prima, name="prima"),
    path("obtener-presupuesto-prima/", views.obtener_presupuesto_prima, name="obtener_presupuesto_prima"),
    path("tabla-auxiliar-prima/", views.tabla_auxiliar_prima, name="tabla_auxiliar_prima"), # ruta para la tabla temporal de las primas
    path("obtener-prima-temp/", views.obtener_prima_temp, name="obtener_prima_temp"),
    path("subir-presupuesto-prima/", views.subir_presupuesto_prima, name="subir_presupuesto_prima"),
    path("cargar-prima-base/", views.cargar_prima_base, name="cargar_prima_base"),
    path("guardar-prima-temp/", views.guardar_prima_temp, name="guardar_prima_temp"),
    path("borrar_presupuesto_prima/", views.borrar_presupuesto_prima, name="borrar_presupuesto_prima"),
    
    # vacaciones
    path("vacaciones/", views.vacaciones, name="vacaciones"),
    path("obtener-presupuesto-vacaciones/", views.obtener_presupuesto_vacaciones, name="obtener_presupuesto_vacaciones"),
    path("tabla-auxiliar-vacaciones/", views.tabla_auxiliar_vacaciones, name="tabla_auxiliar_vacaciones"), # ruta para la tabla temporal de las vacaciones
    path("obtener-vacaciones-temp/", views.obtener_vacaciones_temp, name="obtener_vacaciones_temp"),
    path("subir-presupuesto-vacaciones/", views.subir_presupuesto_vacaciones, name="subir_presupuesto_vacaciones"),
    path("cargar-vacaciones-base/", views.cargar_vacaciones_base, name="cargar_vacaciones_base"),
    path("guardar-vacaciones-temp/", views.guardar_vacaciones_temp, name="guardar_vacaciones_temp"),
    path("borrar_presupuesto_vacaciones/", views.borrar_presupuesto_vacaciones, name="borrar_presupuesto_vacaciones"),
    
    # bonificaciones
    path("bonificaciones/", views.bonificaciones, name="bonificaciones"),
    path("obtener-presupuesto-bonificaciones/", views.obtener_presupuesto_bonificaciones, name="obtener_presupuesto_bonificaciones"),
    path("tabla-auxiliar-bonificaciones/", views.tabla_auxiliar_bonificaciones, name="tabla_auxiliar_bonificaciones"), # ruta para la tabla temporal de las bonificaciones
    path("obtener-bonificaciones-temp/", views.obtener_bonificaciones_temp, name="obtener_bonificaciones_temp"),
    path("subir-presupuesto-bonificaciones/", views.subir_presupuesto_bonificaciones, name="subir_presupuesto_bonificaciones"),
    path("cargar-bonificaciones-base/", views.cargar_bonificaciones_base, name="cargar_bonificaciones_base"),
    path("guardar-bonificaciones-temp/", views.guardar_bonificaciones_temp, name="guardar_bonificaciones_temp"),
    path("borrar_presupuesto_bonificaciones/", views.borrar_presupuesto_bonificaciones, name="borrar_presupuesto_bonificaciones"),
    
    # auxilio movilidad (tuberculina)
    path("auxilio-movilidad/", views.auxilio_movilidad, name="auxilio_movilidad"),
    path("obtener-presupuesto-auxilio-movilidad/", views.obtener_presupuesto_auxilio_movilidad, name="obtener_presupuesto_auxilio_movilidad"),
    path("tabla-auxiliar-auxilio-movilidad/", views.tabla_auxiliar_auxilio_movilidad, name="tabla_auxiliar_auxilio_movilidad"), # ruta para la tabla temporal del auxilio de movilidad
    path("obtener-auxilio-movilidad-temp/", views.obtener_auxilio_movilidad_temp, name="obtener_auxilio_movilidad_temp"),
    path("subir-presupuesto-auxilio-movilidad/", views.subir_presupuesto_auxilio_movilidad, name="subir_presupuesto_auxilio_movilidad"),
    path("cargar-auxilio-movilidad-base/", views.cargar_auxilio_movilidad_base, name="cargar_auxilio_movilidad_base"),
    path("guardar-auxilio-movilidad-temp/", views.guardar_auxilio_movilidad_temp, name="guardar_auxilio_movilidad_temp"),
    path("borrar_presupuesto_auxilio_movilidad/", views.borrar_presupuesto_auxilio_movilidad, name="borrar_presupuesto_auxilio_movilidad"),
    
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
    path("borrar_presupuesto_intereses_cesantias/", views.borrar_presupuesto_intereses_cesantias, name="borrar_presupuesto_intereses_cesantias"),
    
    # aprendiz
    path("aprendiz/", views.aprendiz, name="aprendiz"),
    path("obtener-presupuesto-aprendiz/", views.obtener_presupuesto_aprendiz, name="obtener_presupuesto_aprendiz"),
    path("tabla-auxiliar-aprendiz/", views.tabla_auxiliar_aprendiz, name="tabla_auxiliar_aprendiz"), # ruta para la tabla temporal del aprendiz
    path("obtener-aprendiz-temp/", views.obtener_aprendiz_temp, name="obtener_aprendiz_temp"),
    path("subir-presupuesto-aprendiz/", views.subir_presupuesto_aprendiz, name="subir_presupuesto_aprendiz"),
    path("cargar-aprendiz-base/", views.cargar_aprendiz_base, name="cargar_aprendiz_base"),
    path("guardar-aprendiz-temp/", views.guardar_aprendiz_temp, name="guardar_aprendiz_temp"),
    path("borrar_presupuesto_aprendiz/", views.borrar_presupuesto_aprendiz, name="borrar_presupuesto_aprendiz"),
    
    # bonificaciones foco
    path("bonificaciones-foco/", views.bonificaciones_foco, name="bonificaciones_foco"),
    path("obtener-presupuesto-bonificaciones-foco/", views.obtener_presupuesto_bonificaciones_foco, name="obtener_presupuesto_bonificaciones_foco"),
    path("tabla-auxiliar-bonificaciones-foco/", views.tabla_auxiliar_bonificaciones_foco, name="tabla_auxiliar_bonificaciones_foco"), # ruta para la tabla temporal de las bonificaciones foco
    path("obtener-bonificaciones-foco-temp/", views.obtener_bonificaciones_foco_temp, name="obtener_bonificaciones_foco_temp"),
    path("subir-presupuesto-bonificaciones-foco/", views.subir_presupuesto_bonificaciones_foco, name="subir_presupuesto_bonificaciones_foco"),
    path("cargar-bonificaciones-foco-base/", views.cargar_bonificaciones_foco_base, name="cargar_bonificaciones_foco_base"),
    path("guardar-bonificaciones-foco-temp/", views.guardar_bonificaciones_foco_temp, name="guardar_bonificaciones_foco_temp"),
    path("borrar_presupuesto_bonificaciones_foco/", views.borrar_presupuesto_bonificaciones_foco, name="borrar_presupuesto_bonificaciones_foco"),
    
    # auxilio educacion
    path("auxilio-educacion/", views.auxilio_educacion, name="auxilio_educacion"),
    path("obtener-presupuesto-auxilio-educacion/", views.obtener_presupuesto_auxilio_educacion, name="obtener_presupuesto_auxilio_educacion"),
    path("tabla-auxiliar-auxilio-educacion/", views.tabla_auxiliar_auxilio_educacion, name="tabla_auxiliar_auxilio_educacion"), # ruta para la tabla temporal del auxilio de educacion
    path("obtener-auxilio-educacion-temp/", views.obtener_auxilio_educacion_temp, name="obtener_auxilio_educacion_temp"),
    path("subir-presupuesto-auxilio-educacion/", views.subir_presupuesto_auxilio_educacion, name="subir_presupuesto_auxilio_educacion"),
    path("cargar-auxilio-educacion-base/", views.cargar_auxilio_educacion_base, name="cargar_auxilio_educacion_base"),
    path("guardar-auxilio-educacion-temp/", views.guardar_auxilio_educacion_temp, name="guardar_auxilio_educacion_temp"),
    path("borrar_presupuesto_auxilio_educacion/", views.borrar_presupuesto_auxilio_educacion, name="borrar_presupuesto_auxilio_educacion"),
    
    # bonos kyrovet
    path("bonos-kyrovet/", views.bonos_kyrovet, name="bonos_kyrovet"),
    path("obtener-presupuesto-bonos-kyrovet/", views.obtener_presupuesto_bonos_kyrovet, name="obtener_presupuesto_bonos_kyrovet"),
    path("tabla-auxiliar-bonos-kyrovet/", views.tabla_auxiliar_bonos_kyrovet, name="tabla_auxiliar_bonos_kyrovet"), # ruta para la tabla temporal de los bonos kyrovet
    path("obtener-bonos-kyrovet-temp/", views.obtener_bonos_kyrovet_temp, name="obtener_bonos_kyrovet_temp"),
    path("subir-presupuesto-bonos-kyrovet/", views.subir_presupuesto_bonos_kyrovet, name="subir_presupuesto_bonos_kyrovet"),
    path("cargar-bonos-kyrovet-base/", views.cargar_bonos_kyrovet_base, name="cargar_bonos_kyrovet_base"),
    path("guardar-bonos-kyrovet-temp/", views.guardar_bonos_kyrovet_temp, name="guardar_bonos_kyrovet_temp"),
    path("borrar_presupuesto_bonos_kyrovet/", views.borrar_presupuesto_bonos_kyrovet, name="borrar_presupuesto_bonos_kyrovet"),
]
