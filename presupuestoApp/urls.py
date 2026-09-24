from django.urls import path
from . import views
from .urls_nomina import urlpatterns as urls_nomina

urlpatterns = [
    *urls_nomina,
    
    path('dashboard/', views.dashboard_home, name='dashboardPresupuesto'), 
    path('cuenta5/', views.cuenta5, name='cuenta5'),
    path('obtener-cuenta5-base/', views.obtener_cuenta5_base, name='obtener_cuenta5_base'),
    path("subir_excel_cuenta5/", views.subir_excel_cuenta5, name="subir_excel_cuenta5"),
    path("borrar_cuenta5_base/", views.borrar_cuenta5_base, name="borrar_cuenta5_base"),
    # OBTENER, SUBIR Y BORRAR PRESUPUESTO CONSOLIDADO
    path("subir_excel_cuenta5_presupuestado/", views.subir_excel_cuenta5_presupuestado, name="subir_excel_cuenta5_presupuestado"),
    path('cuenta5-presupuestado/', views.cuenta5_presupuestado, name='cuenta5_presupuestado'),
    path('obtener-cuenta5-presupuestado/', views.obtener_cuenta5_presupuestado, name='obtener_cuenta5_presupuestado'),
    path("borrar_cuenta5_presupuestado/", views.borrar_cuenta5_presupuestado, name="borrar_cuenta5_presupuestado"),
    
    # obtener y subir cuenta 4 base
    path('cuenta4/', views.cuenta4, name='cuenta4'),
    path('obtener-cuenta4-base/', views.obtener_cuenta4_base, name='obtener_cuenta4_base'),
    path("subir_excel_cuenta4/", views.subir_excel_cuenta4, name="subir_excel_cuenta4"),
    path("borrar_cuenta4_base/", views.borrar_cuenta4_base, name="borrar_cuenta4_base"),
    # obtener y subir cuenta 4 presupuestado
    path('cuenta4-presupuestado/', views.cuenta4_presupuestado, name='cuenta4_presupuestado'),
    path('obtener-cuenta4-presupuestado/', views.obtener_cuenta4_presupuestado, name='obtener_cuenta4_presupuestado'),
    path("subir_excel_cuenta4_presupuestado/", views.subir_excel_cuenta4_presupuestado, name="subir_excel_cuenta4_presupuestado"),
    path("borrar_cuenta4_presupuestado/", views.borrar_cuenta4_presupuestado, name="borrar_cuenta4_presupuestado"),
    
    path('exportar-excel-presupuestos/', views.exportar_excel_presupuestos, name='exportar_excel_presupuestos'),
    path('presupuesto-ventas/', views.base_comercial, name='baseComercial'), 
    
    # Presupuesto general ventas 
    path('presupuesto-general-ventas/', views.vista_presupuesto_general_ventas, name='presupuestoGeneralVentas'), 
    path('obtener-presupuesto-general-ventas/', views.obtener_presupuesto_general_ventas, name='obtener_presupuesto_general_ventas'),
    path('cargar-presupuesto-general-ventas/', views.cargar_presupuesto_general_ventas, name='cargar_presupuesto_general_ventas'),
    path('actualizar-presupuesto-general-ventas/', views.actualizar_presupuesto_general_ventas, name='actualizar_presupuesto_general_ventas'),
    
    # presupuesto centro ventas
    path('presupuesto-centro-ventas/', views.vista_presupuesto_centro_ventas, name='presupuestoCentroVentas'), 
    path('obtener-presupuesto-centro-ventas/', views.obtener_presupuesto_centro_ventas, name='obtener_presupuesto_centro_ventas'),
    path('cargar-presupuesto-centro-ventas/', views.cargar_presupuesto_centro_ventas, name='cargar_presupuesto_centro_ventas'),
    path('actualizar-presupuesto-centro-ventas/', views.actualizar_presupuesto_centro_ventas, name='actualizar_presupuesto_centro_ventas'),
    
    # presupuesto centro - segmento ventas
    path('presupuesto-centro-segmento-ventas/', views.vista_presupuesto_centro_segmento_ventas, name='presupuestoCentroSegmentoVentas'), 
    path('obtener-presupuesto-centro-segmento-ventas/', views.obtener_presupuesto_centro_segmento_ventas, name='obtener_presupuesto_centro_segmento_ventas'),
    path('cargar-presupuesto-centro-segmento-ventas/', views.cargar_presupuesto_centro_segmento_ventas, name='cargar_presupuesto_centro_segmento_ventas'),
    path('actualizar-presupuesto-centro-segmento-ventas/', views.actualizar_presupuesto_centro_segmento_ventas, name='actualizar_presupuesto_centro_segmento_ventas'),
    
    # presupuesto general costos
    path('presupuesto-general-costos/', views.vista_presupuesto_general_costos, name='presupuestoGeneralCostos'), 
    path('obtener-presupuesto-general-costos/', views.obtener_presupuesto_general_costos, name='obtener_presupuesto_general_costos'),
    path('cargar-presupuesto-general-costos/', views.cargar_presupuesto_general_costos, name='cargar_presupuesto_general_costos'),
    
    # presupuesto centro costos
    path('presupuesto-centro-costos/', views.vista_presupuesto_centro_costos, name='presupuestoCentroCostos'), 
    path('obtener-presupuesto-centro-costos/', views.obtener_presupuesto_centro_costos, name='obtener_presupuesto_centro_costos'),
    path('cargar-presupuesto-centro-costos/', views.cargar_presupuesto_centro_costos, name='cargar_presupuesto_centro_costos'),
    
    # presupuesto centro-segmento costos
    path('presupuesto-centro-segmento-costos/', views.vista_presupuesto_centro_segmento_costos, name='presupuestoCentroSegmentoCostos'), 
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
    
    path('importar-bd-ventas-comercial/', views.importar_bd_ventas_comercial, name='importar_bd_ventas_comercial'),
    path('vista-importar-ventas/', views.vista_importar_bd_ventas_comercial, name='vistaImportarVentas'),
    
    path('obtener-comparativo-anual/', views.obtener_comparativo_anual, name='obtener_comparativo_anual'),
    path('vista-comparativo-anual/', views.vista_comparativo_anual, name='vistaComparativoAnual'),
   
    # presupuesto comercial
    path('presupuesto-comercial/', views.vista_presupuesto_comercial, name='presupuestoComercial'),
    path('guardar-presupuesto-comercial/', views.guardar_presupuesto_comercial, name='guardar_presupuesto_comercial'),
    path('obtener-presupuesto-comercial/', views.obtener_presupuesto_comercial, name='obtener_presupuesto_comercial'),
    
    #-----------------------------PRESUPUESTO GENERAL--------------------------------
    #----CUENTAS CONTABLES---------
    path('seleccion-cuentas-contables/', views.seleccion_cuentas_contables, name='seleccionCuentasContables'),
    
    # ── Ajustes: orden de cuentas ──
    path('ajustes/orden-cuentas/', views.ajustes_orden_cuentas, name='ajustes_orden_cuentas'),
    path('ajustes/orden-cuentas/listar/', views.listar_orden_cuentas, name='listar_orden_cuentas'),
    path('ajustes/orden-cuentas/sincronizar/', views.sincronizar_orden_cuentas, name='sincronizar_orden_cuentas'),
    path('ajustes/orden-cuentas/guardar/', views.guardar_orden_cuentas, name='guardar_orden_cuentas'),
    path('ajustes/orden-cuentas/eliminar/', views.eliminar_orden_cuenta, name='eliminar_orden_cuenta'),
    
    # -------------- PRESUPUESTO POR SEDE (genérico, escalable) --------------
    # Para agregar Buga/Cartago/Cali: solo agrega su entrada en SEDE_CONFIG
    # (views_presupuesto_sedes.py). Estas 9 rutas les sirven automáticamente.
    path('presupuesto/<str:sede>/', views.presupuesto_sede, name='presupuesto_sede'),
    path('presupuesto/<str:sede>/obtener/', views.obtener_presupuesto_sede, name='obtener_presupuesto_sede'),
    path('presupuesto/<str:sede>/aprobado/', views.presupuesto_aprobado_sede, name='presupuesto_aprobado_sede'),
    path('presupuesto/<str:sede>/aprobado/obtener/', views.obtener_presupuesto_aprobado_sede, name='obtener_presupuesto_aprobado_sede'),
    path('presupuesto/<str:sede>/auxiliar/', views.tabla_auxiliar_sede, name='tabla_auxiliar_sede'),
    path('presupuesto/<str:sede>/auxiliar/obtener/', views.obtener_temp_sede, name='obtener_temp_sede'),
    path('presupuesto/<str:sede>/auxiliar/cargar-base/', views.cargar_base_sede, name='cargar_base_sede'),
    path('presupuesto/<str:sede>/auxiliar/guardar/', views.guardar_temp_sede, name='guardar_temp_sede'),
    path('presupuesto/<str:sede>/subir/', views.subir_presupuesto_sede, name='subir_presupuesto_sede'),
    path('presupuesto/<str:sede>/borrar/', views.borrar_presupuesto_sede, name='borrar_presupuesto_sede'),
    
    # consolidado general 
    path('obtener-consolidado/', views.obtener_consolidado, name='obtener_consolidado'),
    path('consolidado/general/', views.consolidado_general, name='consolidado_general'),
    
    # PRESUPUESTADO
    path('obtener-presupuestado/', views.obtener_presupuestado, name='obtener_presupuestado'),
    path('presupuestado/general/', views.presupuestado_general, name='presupuestado_general'),
    
    # urls.py
    path('ventas/generar/', views.generar_presupuesto_ventas_view, name='generar_presupuesto_ventas'),
    
    # TABLA DINAMICA ------------------------------
    path('obtener-valores-filtros/', views.obtener_valores_filtros, name='obtener_valores_filtros'),
    path('obtener-tabla-dinamica-flexible/', views.obtener_tabla_dinamica_flexible, name='obtener_tabla_dinamica_flexible'),
    path('tabla-dinamica/', views.tabla_dinamica_view, name='tabla_dinamica'),
    path('obtener-registros-detalle/', views.obtener_registros_detalle,  name='obtener_registros_detalle'),
    path('editar-registro/<int:registro_id>/', views.editar_registro, name='editar_registro'),
    path('eliminar-registro/<int:registro_id>/', views.eliminar_registro, name='eliminar_registro'),
    path('obtener-registros-nivel/',  views.obtener_registros_nivel,  name='obtener_registros_nivel'),
    path('renombrar-nivel/',          views.renombrar_nivel,           name='renombrar_nivel'),
    path('eliminar-nivel/', views.eliminar_nivel, name='eliminar_nivel'),
    path('redistribuir-mes/', views.redistribuir_mes, name='redistribuir_mes'),
    path('aplicar-inflacion/', views.aplicar_inflacion, name='aplicar_inflacion'),
    # ── Página de carga ──────────────────────────────────────-----------------------------------
    path(
        'consolidado-base/carga/',
        views.vista_carga_consolidado_base,   # view del template
        name='vista_carga_consolidado_base',
    ),
 
    # ── API endpoints ────
    path(
        'cargar_consolidado_total_base/',
        views.cargar_consolidado_total_base,
        name='cargar_consolidado_total_base',
    ),
    path(
        'obtener_consolidado_total_base_raw/',
        views.obtener_consolidado_total_base_raw,
        name='obtener_consolidado_total_base_raw',
    ),
    path(
        'borrar_consolidado_total_base/',
        views.borrar_consolidado_total_base,
        name='borrar_consolidado_total_base',
    ),
    path(
        'eliminar_fila_consolidado_total_base/',
        views.eliminar_fila_consolidado_total_base,
        name='eliminar_fila_consolidado_total_base',
    ),
    
    # ── Comparativo general: 4 sedes + total, con comentarios ──
    path('comparativo/general/', views.comparativo_general, name='comparativo_general'),
 
    # ── Comentarios del comparativo (uno por sede + fila) ──
    # IMPORTANTE: 'guardar/' debe ir ANTES que '<str:sede>/', si no Django
    # matchea el patrón dinámico primero y toma "guardar" como si fuera
    # el nombre de una sede (por eso daba 405 Method Not Allowed en el POST).
    path('comparativo/comentarios/guardar/', views.guardar_comentario_comparativo,
         name='guardar_comentario_comparativo'),
    path('comparativo/comentarios/<str:sede>/', views.obtener_comentarios_comparativo,
         name='obtener_comentarios_comparativo'),
    
    path('presupuesto/<str:sede>/version/<int:version>/guardar/', views.guardar_version_sede, name='guardar_version_sede'),
    path('presupuesto/<str:sede>/version/<int:version>/aprobar/', views.aprobar_version_sede, name='aprobar_version_sede'),
    
    #------------------PRESUPUESTO CONSOLIDADO---------------------------
    path('<str:area>/', views.presupuesto_consolidado, name='presupuesto_consolidado'),
    path('<str:area>/obtener-presupuesto-consolidado/', views.obtener_presupuesto_consolidado, name='obtener_presupuesto_consolidado'),
    path('<str:area>/guardar/', views.guardar_presupuesto_consolidado, name='guardar_presupuesto_consolidado'),
]
