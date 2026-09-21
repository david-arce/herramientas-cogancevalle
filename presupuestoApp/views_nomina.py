"""
Vistas del presupuesto de nómina.

Antes: ~150 funciones generadas (tabla principal, auxiliar, guardar,
guardar_temp, subir, borrar, cargar... × 18 conceptos) y 36 templates.
Ahora: 8 vistas que reciben el concepto en la URL y un solo template.

Toda la lógica de cálculo está en nomina_motor.py.
"""
import datetime as dt
import json

import pandas as pd
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from . import nomina_conceptos as origen
from . import nomina_motor as nomina
from .models import ParametrosPresupuestos
from .models_nomina import ConceptosNomina

TODOS = 'todos'   # slug de la vista consolidada (todos los conceptos juntos)

# Destinos habituales del panel de distribución (vista consolidada).
# Se pueden agregar otros desde la pantalla.
DESTINOS = [
    {'etiqueta': 'Ventas Tuluá', 'centro': 'ALMACEN TULUA', 'area': 'VENTAS GASTOS DE PERSONAL'},
    {'etiqueta': 'Ventas Buga', 'centro': 'ALMACEN BUGA', 'area': 'VENTAS GASTOS DE PERSONAL'},
    {'etiqueta': 'Ventas Cartago', 'centro': 'ALMACEN CARTAGO', 'area': 'VENTAS GASTOS DE PERSONAL'},
    {'etiqueta': 'Ventas Cali', 'centro': 'ALMACEN CALI', 'area': 'VENTAS GASTOS DE PERSONAL'},
    {'etiqueta': 'Administración', 'centro': 'ALMACEN TULUA', 'area': 'ADMINISTRACION DE PERSONAL'},
    {'etiqueta': 'AT-1 (convenio)', 'centro': 'ALMACEN TULUA', 'area': 'ASISTENCIA TECNICA CONVENIO'},
    {'etiqueta': 'AT-4 (propia)', 'centro': 'ALMACEN TULUA', 'area': 'ASISTENCIA TECNICA PROPIA'},
]

# Valores habituales de cada porcentaje, para avisar si uno queda muy fuera de rango
RANGOS_PARAMETROS = {
    'incremento_salarial': (0, 30), 'incremento_ipc': (0, 30), 'incremento_comisiones': (0, 30),
    'auxilio_transporte': (0, 30), 'cesantias': (5, 12), 'intereses_cesantias': (8, 15),
    'prima': (5, 12), 'vacaciones': (2, 8),
}

CAMPOS_PARAMETROS = {
    'incrementoSalarial': 'incremento_salarial',
    'incrementoIPC': 'incremento_ipc',
    'auxilioTransporte': 'auxilio_transporte',
    'cesantias': 'cesantias',
    'interesesCesantias': 'intereses_cesantias',
    'prima': 'prima',
    'vacaciones': 'vacaciones',
    'salarioMinimo': 'salario_minimo',
    'incrementoComisiones': 'incremento_comisiones',
}



# ══════════════════════════════════════════════════════════════════════
#  Utilidades
# ══════════════════════════════════════════════════════════════════════

def _concepto_o_404(tipo):
    try:
        return nomina.obtener(tipo)
    except KeyError:
        raise Http404(f'Concepto de nómina desconocido: {tipo}')


def _error(mensaje, codigo=400):
    return JsonResponse({'status': 'error', 'msg': mensaje}, status=codigo)


def _pesos(valor):
    """12345678 -> '12.345.678'"""
    return f'{int(round(valor or 0)):,}'.replace(',', '.')


def _nombres(slugs):
    return [nomina.CONCEPTOS[s].etiqueta for s in slugs]


def _listas():
    """Opciones de los desplegables en una sola consulta (sin caché de proceso,
    para que un cargo nuevo aparezca en todos los workers)."""
    centros, areas, cargos = set(), set(), set()
    for centro, area, cargo in (ConceptosNomina.objects
                                .values_list('nombre_cen', 'nomcosto', 'nombrecar').distinct()):
        centros.add(centro)
        areas.add(area)
        cargos.add(cargo)
    ordenar = lambda valores: sorted(v for v in valores if v)  # noqa: E731
    return {'centros': ordenar(centros), 'areas': ordenar(areas), 'cargos': ordenar(cargos)}


def _urls(tipo, derivado=False, permite_manual=False):
    urls = {
        'datos': reverse('nomina_datos', args=[tipo]),
        'cargarBase': reverse('nomina_cargar', args=[tipo]),
        'inicio': reverse('presupuestoNomina'),
        'consolidado': reverse('nomina_tabla', args=[TODOS]),
    }
    if not derivado or permite_manual:
        urls['guardar'] = reverse('nomina_guardar', args=[tipo])
    if not derivado:      # los calculados no se vacían: se recalculan
        urls['borrar'] = reverse('nomina_borrar', args=[tipo])
    return urls


# ══════════════════════════════════════════════════════════════════════
#  Tablero y parámetros
# ══════════════════════════════════════════════════════════════════════

@login_required
def presupuestoNomina(request):
    params, _ = ParametrosPresupuestos.objects.get_or_create(id=1)

    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        accion = request.POST.get('action')

        if accion == 'foco_sin_comision':
            n = nomina.guardar_foco_sin_comision(request.POST.getlist('cedulas'),
                                                 request.user.get_username())
            return JsonResponse({'status': 'ok', 'msg': f'{n} persona(s) se calculan como sin comisión '
                                                        '· bonificación foco recalculada ✅'})

        altas = {'insertar_concepto': ('nombrecar', 'cargo'), 'insertar_nomcosto': ('nomcosto', 'costo')}
        if accion in altas:
            campo, etiqueta = altas[accion]
            valor = ' '.join(request.POST.get(campo, '').upper().split())
            if not valor:
                return JsonResponse({'status': 'error', 'msg': f'Debe ingresar un nombre de {etiqueta}'})
            extra, msg = {}, f"'{valor}' agregado correctamente ✅"
            if campo == 'nomcosto':
                # cada NOMCOSTO corresponde a una cuenta
                cuenta = request.POST.get('cuenta', '').strip()
                actual = nomina.cuenta_para(nomina.mapa_cuentas(origen.anio_base()), valor)
                if actual and cuenta and cuenta != actual:
                    return JsonResponse({'status': 'error',
                                         'msg': f"'{valor}' ya existe con la cuenta {actual}"})
                if actual and not cuenta:
                    return JsonResponse({'status': 'error',
                                         'msg': f"'{valor}' ya existe (cuenta {actual})"})
                if not cuenta:
                    return JsonResponse({'status': 'error', 'msg': 'Indique la cuenta del NOMCOSTO'})
                extra['cuenta'] = cuenta
                msg = f"'{valor}' agregado con la cuenta {cuenta} ✅"
            # fila vacía solo para que el nombre aparezca en los desplegables
            ConceptosNomina.objects.create(anio=origen.anio_base(), archivo='(alta manual)',
                                           cargado_por=request.user.get_username(),
                                           **{campo: valor}, **extra)
            if campo == 'nomcosto':
                n = nomina.asignar_cuentas()
                if n:
                    msg += f' · {n} filas de nómina con esa área recibieron la cuenta'
            return JsonResponse({'status': 'ok', 'msg': msg, 'texto': f"{valor} · {extra['cuenta']}"
                                 if extra else valor})

        for variable, campo in CAMPOS_PARAMETROS.items():
            setattr(params, campo, request.POST.get(variable) or None)
        params.save()
        # Cambiar un parámetro afecta a todo: se recalcula el presupuesto completo.
        nomina.recalcular_todo()
        return JsonResponse({'status': 'ok',
                             'msg': 'Parámetros guardados y presupuesto recalculado ✅'})

    listas = _listas()
    cuentas = nomina.mapa_cuentas(origen.anio_base())
    resumen = nomina.resumen()
    for fila in resumen:
        fila['total_fmt'] = _pesos(fila['total'])
    grupos = [
        {'nombre': grupo, 'conceptos': [r for r in resumen if r['grupo'] == grupo]}
        for grupo in nomina.GRUPOS
    ]
    marcados = set(nomina.FocoSinComision.objects.values_list('cedula', flat=True))
    foco = [{'cedula': cedula, 'nombre': nombre, 'marcado': cedula in marcados}
            for cedula, nombre in nomina.personas_que_comisionan()]
    avisos = [f'{nomina.ETIQUETAS_PARAMETRO[campo]}: {getattr(params, campo):g}'
              for campo, (bajo, alto) in RANGOS_PARAMETROS.items()
              if getattr(params, campo, None) and not bajo <= getattr(params, campo) <= alto]
    config = origen.ConfiguracionNomina.actual()
    anio_base = origen.anio_base()
    return render(request, 'presupuesto_nomina/dashboard_nomina.html', {
        'parametros': params,
        'avisos_parametros': avisos,
        'foco_personas': foco,
        'foco_marcados': len(marcados),
        'origen': {
            'anios': origen.resumen_anios(),
            'anio_base': anio_base,
            'anio_educacion': anio_base - 1,
            'meses_reales': origen.meses_reales(anio_base),
            'mes_reales_nombre': (nomina.MESES[origen.meses_reales(anio_base) - 1].capitalize()
                                  if origen.meses_reales(anio_base) else '—'),
            'config_anio': config.anio_base,
            'config_meses': config.meses_reales,
            'anio_sugerido': dt.date.today().year,
            'meses': [(i, m.capitalize()) for i, m in enumerate(nomina.MESES, start=1)],
        },
        'nombres_cargos': listas['cargos'],
        'nombres_costos': [(area, nomina.cuenta_para(cuentas, area)) for area in listas['areas']],
        'grupos': grupos,
        'total_general': _pesos(sum(r['total'] for r in resumen)),
    })


# ══════════════════════════════════════════════════════════════════════
#  Datos de origen (conceptos_nomina): Excel, año base, meses reales
# ══════════════════════════════════════════════════════════════════════

def _entero_o_none(valor):
    try:
        return int(valor) if str(valor or '').strip() else None
    except ValueError:
        return None


@login_required
@require_POST
def nomina_origen_subir(request):
    archivo = request.FILES.get('archivo')
    if not archivo:
        return _error('Seleccione el archivo de Excel')
    if not archivo.name.lower().endswith(('.xlsx', '.xlsm', '.xls', '.csv')):
        return _error('El archivo debe ser .xlsx, .xls o .csv')

    fecha_corte = None
    if request.POST.get('fecha_corte'):
        try:
            fecha_corte = dt.date.fromisoformat(request.POST['fecha_corte'])
        except ValueError:
            return _error('Fecha de corte inválida')

    try:
        r = origen.importar(
            archivo,
            anio=_entero_o_none(request.POST.get('anio')),
            fecha_corte=fecha_corte,
            reemplazar=True,           # los datos de ese año siempre se reemplazan
            usuario=request.user.get_username(),
            hoja=request.POST.get('hoja') or None,
        )
    except origen.ErrorImportacion as exc:
        return _error(str(exc))

    partes = [f"{r['filas']} filas cargadas para {', '.join(map(str, r['anios']))} ✅"]
    if r['borradas']:
        partes.append(f"se reemplazaron {r['borradas']} filas anteriores")
    for anio, n in r['meses'].items():
        partes.append(f"{anio}: datos hasta {nomina.MESES[n - 1] if n else '—'}")
    if r['omitidas']:
        partes.append(f"{r['omitidas']} filas vacías omitidas")
    if r['ignoradas']:
        partes.append('columnas no reconocidas: ' + ', '.join(r['ignoradas'][:8]))
    if not r['con_columna_cuenta']:
        partes.append('el archivo no trae columna CUENTA')
    if r['cuentas_completadas']:
        partes.append(f"{r['cuentas_completadas']} filas sin cuenta la tomaron de su NOMCOSTO")
    if r['sin_cuenta']:
        partes.append(f"⚠️ {r['sin_cuenta']} filas quedaron sin cuenta (su NOMCOSTO no tiene ninguna)")

    recargados = None
    if request.POST.get('recargar') == '1':
        recargados = nomina.recargar_bases()
        partes.append(f"presupuesto recargado ({recargados.get('_manuales', 0)} filas manuales conservadas)")
    else:
        # sin recargar valores, el presupuesto igual toma las cuentas nuevas
        n = nomina.asignar_cuentas()
        if n:
            partes.append(f'{n} filas del presupuesto con cuenta actualizada')
    return JsonResponse({'status': 'ok', 'msg': ' · '.join(partes),
                         'resultado': r, 'recargados': recargados})


@login_required
@require_POST
def nomina_origen_config(request):
    anio = _entero_o_none(request.POST.get('anio_base'))
    meses = _entero_o_none(request.POST.get('meses_reales'))
    if meses is not None and not 1 <= meses <= 12:
        return _error('Los meses reales deben estar entre 1 y 12')
    origen.guardar_configuracion(anio, meses)
    msg = 'Configuración guardada ✅'
    if request.POST.get('recargar') == '1':
        nomina.recargar_bases()
        msg += ' · presupuesto recargado y recalculado'
    else:
        msg += ' · se aplica al volver a cargar los conceptos'
    return JsonResponse({'status': 'ok', 'msg': msg})


@login_required
@require_POST
def nomina_origen_borrar(request):
    anio = _entero_o_none(request.POST.get('anio'))
    if not anio:
        return _error('Indique el año a borrar')
    n = origen.borrar_anio(anio)
    return JsonResponse({'status': 'ok', 'msg': f'{n} filas del {anio} eliminadas ✅'})


@login_required
@require_POST
def nomina_recargar_bases(request):
    conteo = nomina.recargar_bases()
    repetidos = conteo.pop('_repetidos', 0)
    manuales = conteo.pop('_manuales', 0)
    bloqueadas = conteo.pop('_bloqueadas', 0)
    total = sum(conteo.values())
    msg = (f'{total} filas cargadas desde Conceptos {origen.anio_base()} '
           'y todo el presupuesto recalculado ✅')
    if manuales:
        msg += f' · {manuales} filas propias conservadas'
    if bloqueadas:
        msg += f' · {bloqueadas} persona(s) conservan su fila editada'
    if repetidos:
        msg += f' · {repetidos} repetidas omitidas (la misma persona en otra sede)'
    return JsonResponse({'status': 'ok', 'conteo': conteo, 'msg': msg})


@login_required
@require_GET
def nomina_origen_plantilla(request):
    respuesta = HttpResponse(
        origen.plantilla_excel(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    respuesta['Content-Disposition'] = 'attachment; filename="Plantilla_Conceptos_Nomina.xlsx"'
    return respuesta


@login_required
@require_GET
def nomina_origen_exportar(request, anio):
    campos = ['anio', 'fecha_corte', *[c.lower() for c in origen.COLUMNAS_PLANTILLA]]
    df = pd.DataFrame(list(ConceptosNomina.objects.filter(anio=anio).order_by('id').values(*campos)))
    if not df.empty:
        df.columns = [c.upper() for c in df.columns]
    return _respuesta_excel(df, f'Conceptos_Nomina_{anio}.xlsx', str(anio))


# ══════════════════════════════════════════════════════════════════════
#  Distribución por persona (vista consolidada)
# ══════════════════════════════════════════════════════════════════════

def _json(request):
    try:
        cuerpo = json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return None
    return cuerpo if isinstance(cuerpo, dict) else None


def _mensaje_distribucion(r, accion):
    return (f"{accion} para {r['personas']} persona(s) · {r['filas']} filas repartidas "
            '· todos los conceptos recalculados ✅')


@login_required
@require_GET
def nomina_distribucion(request):
    return JsonResponse({'data': nomina.listar_distribuciones()})


@login_required
@require_POST
def nomina_distribucion_aplicar(request):
    cuerpo = _json(request)
    if cuerpo is None:
        return _error('JSON inválido')
    try:
        r = nomina.guardar_distribucion(cuerpo.get('cedulas') or [], cuerpo.get('reparto') or [],
                                        request.user.get_username())
    except ValueError as exc:
        return _error(str(exc))
    return JsonResponse({'status': 'ok', 'msg': _mensaje_distribucion(r, 'Distribución aplicada'),
                         'resultado': r, 'distribuciones': nomina.listar_distribuciones()})


@login_required
@require_POST
def nomina_distribucion_quitar(request):
    cuerpo = _json(request)
    if cuerpo is None:
        return _error('JSON inválido')
    cedulas = cuerpo.get('cedulas') or []
    if not cedulas:
        return _error('Seleccione al menos una persona')
    r = nomina.quitar_distribucion(cedulas, request.user.get_username())
    return JsonResponse({'status': 'ok',
                         'msg': _mensaje_distribucion(r, 'Distribución quitada (vuelve a su centro/área de origen)'),
                         'resultado': r, 'distribuciones': nomina.listar_distribuciones()})


@login_required
@require_POST
def nomina_recalcular_todo(request):
    nomina.recalcular_todo()
    return JsonResponse({'status': 'ok', 'msg': 'Todo el presupuesto de nómina fue recalculado ✅'})


@login_required
@require_GET
def nomina_resumen(request):
    return JsonResponse({'data': nomina.resumen()})


# ══════════════════════════════════════════════════════════════════════
#  Tabla de un concepto (o de todos)
# ══════════════════════════════════════════════════════════════════════

@login_required
def nomina_tabla(request, tipo):
    params = nomina.Parametros.cargar()

    if tipo == TODOS:
        config = {
            'slug': TODOS, 'etiqueta': 'Presupuesto de nómina consolidado',
            'soloLectura': True, 'seleccionable': True, 'conCedula': True, 'tituloBase': 'Base',
            'conDistribucion': True, 'destinos': DESTINOS,
            'urls': {'datos': reverse('nomina_datos', args=[TODOS]),
                     'inicio': reverse('presupuestoNomina'),
                     'distribuciones': reverse('nomina_distribucion'),
                     'distribuir': reverse('nomina_distribucion_aplicar'),
                     'quitarDistribucion': reverse('nomina_distribucion_quitar')},
            'parametros': [], 'depende': [], 'afecta': [],
        }
        return render(request, 'presupuesto_nomina/tabla_concepto.html',
                      {'config': config, 'titulo': config['etiqueta'], 'listas': _listas()})

    c = _concepto_o_404(tipo)
    config = {
        'slug': c.slug,
        'etiqueta': c.etiqueta,
        'derivado': c.derivado,
        # los calculados son de solo lectura, salvo los que admiten filas a mano
        'soloLectura': c.derivado and not c.permite_manual,
        'soloAgregar': c.derivado and c.permite_manual,
        'conCedula': c.con_cedula,
        'conPegar': c.con_pegar,
        'tituloBase': c.titulo_base,
        # concepto que se pone solo al crear una fila en esta pantalla
        'conceptoNuevo': (c.carga or {}).get('concepto') or c.etiqueta.upper(),
        'parametros': [{'etiqueta': nomina.ETIQUETAS_PARAMETRO[p], 'valor': getattr(params, p)}
                       for p in c.parametros],
        'depende': _nombres(c.depende),
        'afecta': _nombres(nomina.afectados_por(c.slug)),
        # para el diálogo "qué se actualiza con esta fila"
        'afectaDetalle': [
            {'slug': d, 'etiqueta': nomina.CONCEPTOS[d].etiqueta, 'depende': list(nomina.CONCEPTOS[d].depende),
             'dependeNombres': _nombres(s for s in nomina.CONCEPTOS[d].depende
                                        if s == c.slug or s in nomina.afectados_por(c.slug))}
            for d in nomina.afectados_por(c.slug)
        ],
        'urls': _urls(c.slug, c.derivado, c.permite_manual),
    }
    return render(request, 'presupuesto_nomina/tabla_concepto.html', {
        'config': config,
        'titulo': f'Presupuesto nómina - {c.etiqueta}',
        'listas': _listas(),
    })


@login_required
@require_GET
def nomina_datos(request, tipo):
    if tipo != TODOS:
        _concepto_o_404(tipo)
    return JsonResponse({'data': nomina.listar(None if tipo == TODOS else tipo)})


def _respuesta_cambio(tipo, mensaje, recalculados, **extra):
    if recalculados:
        mensaje += ' · Actualizado también: ' + ', '.join(_nombres(recalculados))
    return JsonResponse({
        'status': 'ok', 'msg': mensaje,
        'recalculados': _nombres(recalculados),
        'data': nomina.listar(tipo),
        **extra,
    })


@login_required
@require_POST
def nomina_guardar(request, tipo):
    _concepto_o_404(tipo)
    try:
        cuerpo = json.loads(request.body.decode('utf-8') or '[]')
    except (ValueError, UnicodeDecodeError):
        return _error('JSON inválido')
    filas = cuerpo.get('filas') if isinstance(cuerpo, dict) else cuerpo
    if not isinstance(filas, list):
        return _error('Se esperaba una lista de filas')

    try:
        resumen, recalculados = nomina.guardar(tipo, filas, request.user.get_username())
    except ValueError as exc:
        return _error(str(exc))
    except Exception as exc:                      # noqa: BLE001
        return _error(f'No se pudo guardar: {exc}', 500)

    mensaje = (f"Guardado ✅ ({resumen.get('creadas', 0)} nuevas, "
               f"{resumen.get('actualizadas', 0)} actualizadas, "
               f"{resumen.get('eliminadas', 0)} eliminadas)")
    if resumen.get('calculadas'):
        mensaje += f" · {resumen['calculadas']} filas calculadas sin cambios"
    return _respuesta_cambio(tipo, mensaje, recalculados, resumen=resumen)


@login_required
@require_POST
def nomina_cargar(request, tipo):
    c = _concepto_o_404(tipo)
    try:
        creadas, recalculados, repetidos, conservadas, bloqueadas = nomina.cargar_base(tipo)
    except Exception as exc:                      # noqa: BLE001
        return _error(f'No se pudo cargar: {exc}', 500)
    origen = 'calculadas' if c.derivado else 'cargadas desde Conceptos'
    mensaje = f'{creadas} filas {origen} ✅'
    if conservadas:
        mensaje += f' · {conservadas} filas propias conservadas'
    if bloqueadas:
        mensaje += f' · {bloqueadas} persona(s) conservan su fila editada en lugar de la calculada'
    if repetidos:
        mensaje += f' · {repetidos} repetidas omitidas (la misma persona en otra sede)'
    return _respuesta_cambio(tipo, mensaje, recalculados)


@login_required
@require_POST
def nomina_borrar(request, tipo):
    c = _concepto_o_404(tipo)
    eliminadas, recalculados = nomina.borrar(tipo)
    mensaje = (f'Concepto recalculado: {eliminadas} filas ✅' if c.derivado
               else f'{eliminadas} filas eliminadas ✅')
    return _respuesta_cambio(tipo, mensaje, recalculados)


# ══════════════════════════════════════════════════════════════════════
#  Exportación a Excel (una sola consulta: ya está todo en una tabla)
# ══════════════════════════════════════════════════════════════════════

def _dataframe_nomina(vertical):
    filas = nomina.listar()
    if not filas:
        return pd.DataFrame()
    df = pd.DataFrame(filas).drop(columns=['historico', 'clave', 'tipo'], errors='ignore')
    if 'excluir_de' in df.columns:
        df['excluir_de'] = df['excluir_de'].apply(
            lambda v: ', '.join(nomina.CONCEPTOS[x].etiqueta for x in (v or []) if x in nomina.CONCEPTOS))
        df = df.rename(columns={'excluir_de': 'no_actualiza'})
    df = df.rename(columns={'tipo_nombre': 'origen_concepto'})
    for columna in df.select_dtypes(include=['datetimetz']).columns:
        df[columna] = df[columna].dt.tz_localize(None)
    if vertical:
        fijas = [c for c in df.columns if c not in nomina.MESES]
        df = df.melt(id_vars=fijas, value_vars=nomina.MESES, var_name='mes', value_name='valor')
    return df


def _respuesta_excel(df, nombre_archivo, hoja):
    respuesta = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    with pd.ExcelWriter(respuesta, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=hoja, index=False)
    return respuesta


@login_required
def exportar_excel_nomina(request):
    """Una fila por registro, con los 12 meses en columnas."""
    return _respuesta_excel(_dataframe_nomina(False), 'Presupuesto_Nomina.xlsx', 'Presupuesto')


@login_required
def exportar_nomina_vertical(request):
    """Una fila por registro y mes (formato largo, para tablas dinámicas)."""
    return _respuesta_excel(_dataframe_nomina(True),
                            'Presupuesto_Nomina_Vertical.xlsx', 'Presupuesto Nómina')
