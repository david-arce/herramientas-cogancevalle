/* ==========================================================================
 * presupuesto_distribucion.js
 * Panel "Distribución por persona" de la vista consolidada de nómina.
 * La distribución se guarda por cédula y el servidor la aplica a todos los
 * conceptos de la persona (views_nomina.nomina_distribucion_*).
 * ========================================================================== */
(function () {
  'use strict';

  const $ = (sel) => document.querySelector(sel);
  const escapar = (v) => String(v == null ? '' : v).replace(/[&<>"']/g,
    c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const pct = (n) => (Math.round(n * 100) / 100).toLocaleString('es-CO') + '%';

  function iniciar() {
    const panel = $('#panelDistribucion');
    const tabla = window.tablaNomina;
    if (!panel || !tabla) return;

    const config = PT.listaJSON('pt-config') || {};
    const listas = PT.listaJSON('pt-listas') || {};
    const urls = config.urls || {};

    const cuerpoDestinos = $('#ndDestinos');
    const suma = $('#ndSuma');
    const chips = $('#ndSeleccion');
    const btnAplicar = $('#ndAplicar');
    const btnQuitar = $('#ndQuitar');
    const buscar = $('#ndBuscar');
    const datalist = $('#ndPersonas');
    let distribuciones = [];
    let personas = new Map();   // cedula -> nombre (de la tabla)

    // ------------------------------------------------------------ personas
    const cedulasSeleccionadas = () => {
      const mapa = new Map();
      tabla.filasSeleccionadas().forEach(f => {
        const ced = String(f.cedula || '').trim();
        if (ced && !mapa.has(ced)) mapa.set(ced, f.nombre || '');
      });
      return mapa;
    };

    const seleccionarPersona = (cedula, agregar = true) => {
      const filas = tabla.filas.filter(f => String(f.cedula) === String(cedula));
      if (!filas.length) { PT.toast('No hay filas de esa persona en la tabla ⚠️', 'warning'); return; }
      if (!agregar) tabla.seleccion.clear();
      filas.forEach(f => tabla.seleccion.add(f));
      tabla.pintar();
    };

    const quitarPersona = (cedula) => {
      tabla.filas.filter(f => String(f.cedula) === String(cedula)).forEach(f => tabla.seleccion.delete(f));
      tabla.pintar();
    };

    const refrescarPersonas = () => {
      personas = new Map();
      tabla.filas.forEach(f => {
        const ced = String(f.cedula || '').trim();
        if (ced && !personas.has(ced)) personas.set(ced, f.nombre || '');
      });
      datalist.innerHTML = [...personas].sort((a, b) => a[1].localeCompare(b[1]))
        .map(([ced, nom]) => `<option value="${escapar(nom)} · ${escapar(ced)}"></option>`).join('');
    };

    const pintarSeleccion = () => {
      const sel = cedulasSeleccionadas();
      chips.innerHTML = sel.size
        ? [...sel].map(([ced, nom]) => {
            const conReparto = distribuciones.some(d => d.cedula === ced);
            return `<span class="nd-chip${conReparto ? ' nd-chip--con' : ''}" title="${conReparto ? 'Ya tiene distribución' : ''}">
                      ${escapar(nom || 'Sin nombre')} <small>${escapar(ced)}</small>
                      <button type="button" data-quitar="${escapar(ced)}" aria-label="Quitar">×</button></span>`;
          }).join('')
        : '<span class="nd-vacio">Ninguna persona seleccionada</span>';
      const hay = sel.size > 0;
      btnQuitar.disabled = !hay || ![...sel.keys()].some(c => distribuciones.some(d => d.cedula === c));
      actualizarSuma(hay);
    };

    chips.addEventListener('click', (e) => {
      const b = e.target.closest('[data-quitar]');
      if (b) quitarPersona(b.dataset.quitar);
    });

    const agregarDesdeBuscador = () => {
      const texto = buscar.value.trim();
      if (!texto) return;
      const porCedula = texto.split('·').pop().trim();
      let cedula = personas.has(porCedula) ? porCedula : null;
      if (!cedula) {
        const t = texto.toUpperCase();
        const coincidencias = [...personas].filter(([ced, nom]) => ced.includes(texto) || (nom || '').toUpperCase().includes(t));
        if (coincidencias.length === 1) cedula = coincidencias[0][0];
        else if (coincidencias.length > 1) { PT.toast(`${coincidencias.length} coincidencias: elija una de la lista`, 'warning'); return; }
      }
      if (!cedula) { PT.toast('Persona no encontrada ⚠️', 'warning'); return; }
      seleccionarPersona(cedula);
      buscar.value = '';
    };
    $('#ndAgregarPersona').addEventListener('click', agregarDesdeBuscador);
    buscar.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); agregarDesdeBuscador(); } });
    buscar.addEventListener('change', () => { if (buscar.value.includes('·')) agregarDesdeBuscador(); });
    $('#ndLimpiar').addEventListener('click', () => { tabla.seleccion.clear(); tabla.pintar(); });

    // ------------------------------------------------------------ destinos
    const opciones = (lista, valor) => ['<option value="">—</option>']
      .concat((lista || []).map(v => `<option value="${escapar(v)}" ${v === valor ? 'selected' : ''}>${escapar(v)}</option>`))
      .join('');

    const agregarDestino = (centro = '', area = '', porcentaje = '') => {
      const tr = document.createElement('tr');
      tr.dataset.libre = '';
      tr.innerHTML = `
        <td class="nd-etiqueta">Otro</td>
        <td><select data-centro>${opciones(listas.centros, centro)}</select></td>
        <td><select data-area>${opciones(listas.areas, area)}</select></td>
        <td class="nd-pct"><input type="number" min="0" max="100" step="0.01" inputmode="decimal" placeholder="0" value="${porcentaje}"></td>
        <td><button type="button" class="nd-quitar-destino" title="Quitar destino" aria-label="Quitar destino">×</button></td>`;
      cuerpoDestinos.appendChild(tr);
      return tr;
    };
    $('#ndOtroDestino').addEventListener('click', () => agregarDestino().querySelector('select').focus());
    cuerpoDestinos.addEventListener('click', (e) => {
      if (e.target.closest('.nd-quitar-destino')) { e.target.closest('tr').remove(); actualizarSuma(); }
    });
    cuerpoDestinos.addEventListener('input', () => actualizarSuma());
    cuerpoDestinos.addEventListener('change', () => actualizarSuma());

    const leerDestinos = () => [...cuerpoDestinos.querySelectorAll('tr')].map(tr => {
      const centro = tr.querySelector('[data-centro]');
      const area = tr.querySelector('[data-area]');
      return {
        centro: centro ? (centro.value !== undefined ? centro.value : centro.dataset.centro) : '',
        area: area ? (area.value !== undefined ? area.value : area.dataset.area) : '',
        porcentaje: parseFloat(tr.querySelector('input').value) || 0,
        fila: tr
      };
    });

    function actualizarSuma(haySeleccion = cedulasSeleccionadas().size > 0) {
      const destinos = leerDestinos();
      const total = destinos.reduce((a, d) => a + d.porcentaje, 0);
      const incompletos = destinos.some(d => d.porcentaje > 0 && !d.area);
      destinos.forEach(d => d.fila.classList.toggle('nd-activo', d.porcentaje > 0));
      suma.textContent = pct(total);
      const ok = Math.abs(total - 100) < 0.01;
      suma.className = 'nd-suma ' + (ok ? 'nd-suma--ok' : total > 100 ? 'nd-suma--mal' : '');
      suma.title = incompletos ? 'Hay destinos sin área' : '';
      btnAplicar.disabled = !(ok && haySeleccion && !incompletos);
    }

    const cargarEnFormulario = (reparto) => {
      cuerpoDestinos.querySelectorAll('tr[data-libre]').forEach(tr => tr.remove());
      cuerpoDestinos.querySelectorAll('tr[data-fijo] input').forEach(i => { i.value = ''; });
      reparto.forEach(r => {
        const fijo = [...cuerpoDestinos.querySelectorAll('tr[data-fijo]')].find(tr =>
          tr.querySelector('[data-centro]').dataset.centro === r.centro &&
          tr.querySelector('[data-area]').dataset.area === r.area);
        if (fijo) fijo.querySelector('input').value = r.porcentaje;
        else agregarDestino(r.centro, r.area, r.porcentaje);
      });
      actualizarSuma();
    };

    // ------------------------------------------------------------ vigentes
    const pintarVigentes = () => {
      $('#ndContador').textContent = distribuciones.length;
      $('#ndVigentes').innerHTML = distribuciones.length
        ? distribuciones.map(d => `
            <tr>
              <td>${escapar(d.nombre || '—')}</td>
              <td class="nd-suave">${escapar(d.cedula)}</td>
              <td>${d.reparto.map(r => `<span class="nd-reparto"><b>${pct(r.porcentaje)}</b> ${escapar(r.centro || 'Sin centro')} · ${escapar(r.area)}</span>`).join('')}</td>
              <td class="nd-acciones">
                <button type="button" class="pt-btn" data-editar="${escapar(d.cedula)}">Editar</button>
                <button type="button" class="pt-btn pt-btn--suave-peligro" data-quitar-dist="${escapar(d.cedula)}">Quitar</button>
              </td>
            </tr>`).join('')
        : '<tr><td colspan="4" class="nd-vacio">No hay distribuciones. Cada persona queda en su centro y área de origen.</td></tr>';
    };

    const cargarVigentes = async () => {
      try {
        const r = await PT.pedir(urls.distribuciones);
        distribuciones = r.data || [];
      } catch (e) { distribuciones = []; PT.toast('No se pudieron leer las distribuciones ❌', 'error'); }
      pintarVigentes();
      pintarSeleccion();
    };

    $('#ndVigentes').addEventListener('click', (e) => {
      const editar = e.target.closest('[data-editar]');
      const quitar = e.target.closest('[data-quitar-dist]');
      if (editar) {
        const d = distribuciones.find(x => x.cedula === editar.dataset.editar);
        seleccionarPersona(d.cedula, false);
        cargarEnFormulario(d.reparto);
        panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      if (quitar) enviar(urls.quitarDistribucion, { cedulas: [quitar.dataset.quitarDist] }, quitar,
        '¿Quitar la distribución de esta persona? Sus filas vuelven a su centro y área de origen.');
    });

    // ------------------------------------------------------------ servidor
    async function enviar(url, datos, boton, pregunta) {
      if (tabla.sinGuardar && !confirm('Hay cambios sin guardar en la tabla. ¿Continuar?')) return;
      if (pregunta && !confirm(pregunta)) return;
      await PT.conSpinner(boton, async () => {
        try {
          const r = await PT.enviarJSON(url, datos);
          distribuciones = r.distribuciones || distribuciones;
          await tabla.cargar();
          refrescarPersonas();
          datos.cedulas.forEach(c => seleccionarPersona(c));
          pintarVigentes();
          PT.toast(r.msg, 'success', 8000);
        } catch (e) { PT.toast('❌ ' + e.message, 'error', 8000); }
      });
    }

    btnAplicar.addEventListener('click', () => {
      const sel = cedulasSeleccionadas();
      const reparto = leerDestinos().filter(d => d.porcentaje > 0)
        .map(({ centro, area, porcentaje }) => ({ centro, area, porcentaje }));
      const yaTienen = [...sel.keys()].filter(c => distribuciones.some(d => d.cedula === c)).length;
      enviar(urls.distribuir, { cedulas: [...sel.keys()], reparto }, btnAplicar,
        `¿Aplicar esta distribución a ${sel.size} persona(s)?` +
        (yaTienen ? `\n${yaTienen} ya tiene(n) una distribución y se reemplazará.` : ''));
    });

    btnQuitar.addEventListener('click', () => {
      const cedulas = [...cedulasSeleccionadas().keys()].filter(c => distribuciones.some(d => d.cedula === c));
      enviar(urls.quitarDistribucion, { cedulas }, btnQuitar,
        `¿Quitar la distribución de ${cedulas.length} persona(s)? Vuelven a su centro y área de origen.`);
    });

    // ------------------------------------------------------------ arranque
    // los datos de la tabla llegan después: se refresca el buscador cuando cambian
    let filasConocidas = null;
    tabla.cfg.alSeleccionar = () => {
      if (filasConocidas !== tabla.filas) { filasConocidas = tabla.filas; refrescarPersonas(); }
      pintarSeleccion();
    };
    refrescarPersonas();
    cargarVigentes();
    actualizarSuma(false);
  }

  document.addEventListener('DOMContentLoaded', iniciar);
})();
