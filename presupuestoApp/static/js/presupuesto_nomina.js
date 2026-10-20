/* ==========================================================================
 * presupuesto_nomina.js
 * Arma la pantalla de cualquier concepto de nómina a partir de la
 * configuración que envía la vista (views_nomina.nomina_tabla).
 * Reemplaza los 36 templates que antes repetían este mismo código.
 * ========================================================================== */
(function (global) {
  'use strict';

  const escapar = (v) => String(v == null ? '' : v).replace(/[&<>"']/g,
    c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  /**
   * Diálogo "qué se actualiza con esta fila".
   * detalle: [{slug, etiqueta, depende: [slugs], dependeNombres}] en orden de cálculo.
   * abrir({titulo, sub, boton, excluir}) → Promise<string[] | null> (slugs excluidos)
   */
  function crearDialogoActualiza(slugConcepto, detalle, crearEn = []) {
    const dlg = document.getElementById('dlgActualiza');
    if (!dlg || !detalle.length) return null;
    const lista = dlg.querySelector('#dlgActualizaLista');
    const seccionCrear = dlg.querySelector('#dlgCrearEn');
    const listaCrear = dlg.querySelector('#dlgCrearEnLista');
    if (listaCrear) {
      listaCrear.innerHTML = crearEn.map(d => `
        <li><label>
          <input type="checkbox" value="${escapar(d.slug)}">
          <span class="da-nombre">${escapar(d.etiqueta)}</span>
          <small class="da-dep">se crea con los meses en 0</small>
        </label></li>`).join('');
      dlg.querySelectorAll('[data-marcar-crear]').forEach(b => b.addEventListener('click', () => {
        listaCrear.querySelectorAll('input').forEach(c => { c.checked = b.dataset.marcarCrear === 'todos'; });
      }));
    }

    lista.innerHTML = detalle.map(d => `
      <li data-slug="${escapar(d.slug)}">
        <label>
          <input type="checkbox" value="${escapar(d.slug)}" checked>
          <span class="da-nombre">${escapar(d.etiqueta)}</span>
          <small class="da-dep">se calcula con ${escapar((d.dependeNombres || []).join(', '))}</small>
        </label>
      </li>`).join('');

    const casillas = () => [...lista.querySelectorAll('input[type="checkbox"]')];

    // Un concepto que solo se alimenta de conceptos desmarcados no puede recibir la fila
    const coherencia = () => {
      const activos = new Set([slugConcepto]);
      detalle.forEach(d => {
        const caja = lista.querySelector(`input[value="${d.slug}"]`);
        const alcanzable = d.depende.some(x => activos.has(x));
        caja.disabled = !alcanzable;
        caja.closest('li').classList.toggle('da-bloqueado', !alcanzable);
        if (!alcanzable) caja.checked = false;
        if (caja.checked) activos.add(d.slug);
      });
    };
    lista.addEventListener('change', coherencia);

    dlg.querySelectorAll('[data-marcar]').forEach(b => b.addEventListener('click', () => {
      casillas().forEach(c => { c.disabled = false; c.checked = b.dataset.marcar === 'todos'; });
      coherencia();
    }));

    /** Devuelve null (canceló) o {excluir: [slugs], crearEn: [slugs]}. */
    return function abrir({ titulo, sub, boton, excluir = [], conCrear = false }) {
      if (seccionCrear) {
        seccionCrear.hidden = !(conCrear && crearEn.length);
        listaCrear.querySelectorAll('input').forEach(c => { c.checked = false; });
      }
      dlg.querySelector('#dlgActualizaTitulo').textContent = titulo;
      dlg.querySelector('#dlgActualizaSub').textContent = sub;
      dlg.querySelector('#dlgActualizaAceptar').textContent = boton;
      casillas().forEach(c => { c.disabled = false; c.checked = !excluir.includes(c.value); });
      coherencia();
      dlg.returnValue = '';
      dlg.showModal();
      return new Promise(resolve => {
        dlg.addEventListener('close', () => {
          if (dlg.returnValue !== 'aceptar') { resolve(null); return; }
          resolve({
            excluir: casillas().filter(c => !c.checked).map(c => c.value),
            crearEn: conCrear && listaCrear
              ? [...listaCrear.querySelectorAll('input:checked')].map(c => c.value) : [],
          });
        }, { once: true });
      });
    };
  }

  function iniciarPaginaNomina() {
    const config = PT.listaJSON('pt-config') || {};
    const listas = PT.listaJSON('pt-listas') || {};
    const soloLectura = !!config.soloLectura;
    const estado = document.querySelector('[data-rol="estado"]');
    const detalle = config.afectaDetalle || [];
    const nombreDe = (slug) => (detalle.find(d => d.slug === slug) || {}).etiqueta || slug;
    const crearEn = config.crearEnDetalle || [];
    const nombreDe2 = (slug) => (crearEn.find(d => d.slug === slug) || {}).etiqueta || slug;
    const abrirDialogo = soloLectura ? null : crearDialogoActualiza(config.slug, detalle, crearEn);

    const tabla = new PT.TablaPresupuesto({
      montaje: '#tabla',
      urlDatos: config.urls.datos,
      columnas: PT.Columnas.estandar({
        cedula: config.conCedula !== false,
        cargo: config.conCedula !== false,
        base: config.tituloBase || null,
        opciones: soloLectura ? {} : listas,
        tipo: config.slug === 'todos',
        codcosto: false   // el código de costo no se muestra (sale del área y se sigue guardando)
      }),
      editable: !soloLectura,
      seleccionable: !soloLectura || !!config.seleccionable,
      acciones: soloLectura ? [] : (config.conCedula === false
        ? ['duplicar', 'eliminar']
        : ['duplicar', 'copiar', 'eliminar']),
      // Filtros tipo Excel en la cabecera de todas las columnas de texto
      filtros: null,
      // Guardado automático (sin botón Guardar), como los presupuestos generales
      urlGuardar: soloLectura ? null : config.urls.guardar,
      claveRespaldo: `nomina|${config.usuario || ''}|${config.slug}`,
      indicador: estado,
      botonesHistorial: {
        deshacer: document.querySelector('[data-rol="deshacer"]'),
        rehacer: document.querySelector('[data-rol="rehacer"]'),
      },
      nombreArchivo: 'presupuesto_nomina_' + config.slug,
      conceptoNuevo: config.conceptoNuevo || '',
      accionesExtra: abrirDialogo ? [{
        rol: 'actualiza',
        icono: '🔗',
        // manuales + filas agregadas en pantalla aunque se les haya restablecido el cálculo
        mostrar: (fila) => fila.origen === 'manual' || PT.TablaPresupuesto.esPropia(fila),
        clase: (fila) => (fila.excluir_de || []).length ? 'pt-accion--aviso' : '',
        titulo: (fila) => (fila.excluir_de || []).length
          ? 'No actualiza: ' + fila.excluir_de.map(nombreDe).join(', ')
          : 'Actualiza todos los conceptos que dependen de este'
      }] : [],
      alAccion: async (rol, fila) => {
        if (rol !== 'actualiza') return;
        const eleccion = await abrirDialogo({
          titulo: 'Qué actualiza esta fila',
          sub: [fila.nombre, fila.cedula, fila.area].filter(Boolean).join(' · ') || 'Fila agregada',
          boton: 'Aplicar',
          excluir: fila.excluir_de || []
        });
        if (eleccion === null) return;
        const excluir = eleccion.excluir;
        tabla.antesDeCambiar();
        fila.excluir_de = excluir;
        tabla.pintar();
        tabla.marcarCambios();
        PT.toast('Cambio aplicado; se guarda y recalcula solo ✅');
      }
    });

    const agregar = abrirDialogo ? async () => {
      const eleccion = await abrirDialogo({
        titulo: `Agregar persona en ${config.etiqueta}`,
        sub: 'Elija qué conceptos se deben actualizar automáticamente con esta persona.',
        boton: 'Agregar fila',
        excluir: [],
        conCrear: true
      });
      if (eleccion === null) return;
      const { excluir, crearEn: crear } = eleccion;
      tabla.agregarFila(crear.length ? { excluir_de: excluir, crear_en: crear } : { excluir_de: excluir });
      const partes = [];
      if (excluir.length) partes.push(`No actualizará: ${excluir.map(nombreDe).join(', ')}`);
      if (crear.length) partes.push(`Al escribir la cédula se creará en cero en: ${crear.map(nombreDe2).join(', ')}`);
      PT.toast(partes.length ? `Fila agregada. ${partes.join(' · ')}` : 'Fila agregada ✅', 'success', 7000);
    } : undefined;

    PT.conectarBarra(tabla, config.urls, { agregar });

    // Valor base editable del concepto (p. ej. base del auxilio de transporte)
    const entradaBase = document.getElementById('baseEditable');
    const botonBase = document.querySelector('[data-rol="guardar-base"]');
    if (entradaBase && botonBase && config.baseEditable) {
      let guardado = entradaBase.value;
      const guardarBase = () => {
        // pesos: los puntos son separadores de miles (249.095 = 249095)
        const texto = entradaBase.value.trim().replace(/[.\s$]/g, '').replace(',', '.');
        const valor = Number(texto);
        if (!texto || !/^\d+(\.\d+)?$/.test(texto) || !(valor > 0)) {
          PT.toast('Escriba un valor mayor que 0 (solo números) ⚠️', 'warning');
          entradaBase.focus();
          return;
        }
        PT.conSpinner(botonBase, async () => {
          try {
            const r = await PT.enviarJSON(config.baseEditable.url, { valor });
            if (Array.isArray(r.data)) tabla.setDatos(r.data);
            entradaBase.value = guardado = String(Math.round(r.valor));
            entradaBase.classList.remove('pt-cambiado');
            PT.toast(r.msg, 'success', 6000);
          } catch (e) { PT.toast('No se pudo guardar la base ❌ ' + e.message, 'error', 6000); }
        });
      };
      botonBase.addEventListener('click', guardarBase);
      entradaBase.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); guardarBase(); }
        if (e.key === 'Escape') { entradaBase.value = guardado; entradaBase.classList.remove('pt-cambiado'); }
      });
      entradaBase.addEventListener('input', () => entradaBase.classList.toggle('pt-cambiado', entradaBase.value !== guardado));
    }

    // Ctrl/Cmd + S: no hace falta (se guarda solo), pero envía ya lo pendiente.
    if (!soloLectura && tabla.cola) {
      document.addEventListener('keydown', async (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
          e.preventDefault();
          if (await tabla.guardarAhora()) PT.toast('Todo guardado ✅');
        }
      });
    }

    global.tablaNomina = tabla;   // lo usa presupuesto_distribucion.js (y sirve para depurar)
  }

  document.addEventListener('DOMContentLoaded', iniciarPaginaNomina);
})(window);
