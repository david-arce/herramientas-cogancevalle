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
  function crearDialogoActualiza(slugConcepto, detalle) {
    const dlg = document.getElementById('dlgActualiza');
    if (!dlg || !detalle.length) return null;
    const lista = dlg.querySelector('#dlgActualizaLista');

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

    return function abrir({ titulo, sub, boton, excluir = [] }) {
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
          resolve(casillas().filter(c => !c.checked).map(c => c.value));
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
    const abrirDialogo = soloLectura ? null : crearDialogoActualiza(config.slug, detalle);

    const tabla = new PT.TablaPresupuesto({
      montaje: '#tabla',
      urlDatos: config.urls.datos,
      columnas: PT.Columnas.estandar({
        cedula: config.conCedula !== false,
        cargo: config.conCedula !== false,
        base: config.tituloBase || null,
        opciones: soloLectura ? {} : listas,
        tipo: config.slug === 'todos'
      }),
      editable: !soloLectura,
      seleccionable: !soloLectura || !!config.seleccionable,
      acciones: soloLectura ? [] : (config.conCedula === false
        ? ['duplicar', 'eliminar']
        : ['duplicar', 'copiar', 'eliminar']),
      filtros: config.slug === 'todos'
        ? ['tipo_nombre', 'nombre', 'centro', 'area']
        : (config.conCedula === false ? ['centro', 'area', 'concepto'] : ['nombre', 'centro', 'area']),
      nombreArchivo: 'presupuesto_nomina_' + config.slug,
      accionesExtra: abrirDialogo ? [{
        rol: 'actualiza',
        icono: '🔗',
        mostrar: (fila) => fila.origen === 'manual',
        clase: (fila) => (fila.excluir_de || []).length ? 'pt-accion--aviso' : '',
        titulo: (fila) => (fila.excluir_de || []).length
          ? 'No actualiza: ' + fila.excluir_de.map(nombreDe).join(', ')
          : 'Actualiza todos los conceptos que dependen de este'
      }] : [],
      alAccion: async (rol, fila) => {
        if (rol !== 'actualiza') return;
        const excluir = await abrirDialogo({
          titulo: 'Qué actualiza esta fila',
          sub: [fila.nombre, fila.cedula, fila.area].filter(Boolean).join(' · ') || 'Fila manual',
          boton: 'Aplicar',
          excluir: fila.excluir_de || []
        });
        if (excluir === null) return;
        fila.excluir_de = excluir;
        tabla.pintar();
        tabla.marcarCambios();
        PT.toast('Cambio listo. Guarde para recalcular ✅');
      },
      alCambiar: (pendiente) => {
        if (!estado) return;
        estado.hidden = !pendiente;
      }
    });

    const agregar = abrirDialogo ? async () => {
      const excluir = await abrirDialogo({
        titulo: `Agregar persona en ${config.etiqueta}`,
        sub: 'Elija qué conceptos se deben actualizar automáticamente con esta persona.',
        boton: 'Agregar fila',
        excluir: []
      });
      if (excluir === null) return;
      tabla.agregarFila({ excluir_de: excluir });
      PT.toast(excluir.length
        ? `Fila agregada. No actualizará: ${excluir.map(nombreDe).join(', ')}`
        : 'Fila agregada ✅', 'success', 5000);
    } : undefined;

    PT.conectarBarra(tabla, soloLectura ? { inicio: config.urls.inicio } : config.urls, { agregar });

    // Ctrl/Cmd + S guarda
    if (!soloLectura) {
      document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
          e.preventDefault();
          const boton = document.querySelector('[data-rol="guardar"]');
          if (boton) boton.click();
        }
      });
    }

    global.tablaNomina = tabla;   // lo usa presupuesto_distribucion.js (y sirve para depurar)
  }

  document.addEventListener('DOMContentLoaded', iniciarPaginaNomina);
})(window);
