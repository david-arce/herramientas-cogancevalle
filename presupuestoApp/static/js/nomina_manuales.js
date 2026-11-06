/* ==========================================================================
 * nomina_manuales.js
 * Ventana de "Recalcular": muestra las filas MANUALES (persona y concepto)
 * con su valor y el que tendrían recalculadas, para elegir cuáles se
 * recalculan también. Las que se dejan sin marcar conservan su valor y se
 * recuerdan desmarcadas para la próxima vez.
 *
 *   const datos = await PT.formManuales(url)   // FormData listo, o null si canceló
 *
 * `url` es la misma del botón: con previa=1 devuelve {grupos}; luego se le
 * envía el FormData con recalcular=<id>… y no_recalcular=<id>….
 * ========================================================================== */
(function (global) {
  'use strict';
  const PT = global.PT;
  const esc = (v) => String(v == null ? '' : v).replace(/[&<>"']/g,
    c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const pesos = (v) => '$' + Math.round(v || 0).toLocaleString('es-CO');

  let dlg = null;

  function crear() {
    dlg = document.createElement('dialog');
    dlg.className = 'pt-dialogo pt-dialogo--ancho';
    dlg.id = 'dlgManuales';
    dlg.setAttribute('aria-labelledby', 'dlgManualesTitulo');
    dlg.innerHTML = `
      <form method="dialog" class="pt-dialogo__caja">
        <header class="pt-dialogo__cabecera">
          <h3 id="dlgManualesTitulo">Filas manuales: ¿recalcularlas también?</h3>
          <p class="pt-dialogo__sub">Estas filas se escribieron o editaron a mano y el cálculo no las toca.
            Las marcadas vuelven a ser <strong>calculadas</strong> (pierden el valor manual);
            las desmarcadas conservan su valor y la próxima vez saldrán desmarcadas.
            Las de <strong>⚠️</strong> quedarían en 0 o se quitarían (no tienen datos de origen): salen desmarcadas.</p>
        </header>
        <div class="pt-dialogo__cuerpo">
          <div class="rm-barra">
            <input type="search" class="rm-buscar" placeholder="Buscar nombre, cédula, concepto, área…"
                   aria-label="Buscar filas" autocomplete="off">
            <div class="da-atajos">
              <button type="button" class="pt-btn pt-btn--enlace" data-rm="todas">Recalcular todas</button>
              <button type="button" class="pt-btn pt-btn--enlace" data-rm="ninguna">Ninguna</button>
            </div>
          </div>
          <div class="rm-grupos"></div>
        </div>
        <footer class="pt-dialogo__pie rm-pie">
          <span class="rm-resumen" role="status"></span>
          <button type="submit" class="pt-btn" value="cancelar">Cancelar</button>
          <button type="submit" class="pt-btn pt-btn--primario" value="aceptar">Recalcular</button>
        </footer>
      </form>`;
    document.body.appendChild(dlg);

    dlg.addEventListener('change', (e) => { if (e.target.matches('.rm-fila input')) resumen(); });
    dlg.querySelector('.rm-buscar').addEventListener('input', (e) => {
      const q = e.target.value.trim().toLowerCase();
      dlg.querySelectorAll('.rm-fila').forEach(tr => { tr.hidden = !!q && !tr.dataset.buscar.includes(q); });
      dlg.querySelectorAll('.rm-tabla').forEach(t => {
        t.hidden = !t.querySelector('.rm-fila:not([hidden])');
      });
    });
    dlg.querySelectorAll('[data-rm]').forEach(b => b.addEventListener('click', () => {
      dlg.querySelectorAll('.rm-fila:not([hidden]) input')       // respeta la búsqueda
        .forEach(i => { i.checked = b.dataset.rm === 'todas'; });
      resumen();
    }));
  }

  function resumen() {
    let n = 0, total = 0, antes = 0, despues = 0;
    dlg.querySelectorAll('.rm-fila').forEach(tr => {
      const marcada = tr.querySelector('input').checked;
      const manual = +tr.dataset.total;
      const calculado = tr.dataset.calculado === '' ? 0 : +tr.dataset.calculado;
      total += 1; antes += manual; despues += marcada ? calculado : manual;
      if (marcada) n += 1;
      tr.classList.toggle('rm-fila--fuera', !marcada);
    });
    dlg.querySelector('.rm-resumen').textContent =
      `${n} de ${total} se recalculan · ${pesos(antes)} → ${pesos(despues)}`;
  }

  function pintar(grupos) {
    dlg.querySelector('.rm-buscar').value = '';
    dlg.querySelector('.rm-grupos').innerHTML = grupos.map(g => `
      <table class="rm-tabla">
        <caption>${esc(g.etiqueta)} <small>${g.filas.length} fila${g.filas.length === 1 ? '' : 's'} manual${g.filas.length === 1 ? '' : 'es'}</small></caption>
        <thead><tr><th class="rm-check">Recalcular</th><th>Persona</th><th>Área · centro</th>
          <th class="num">Valor manual</th><th class="num">Recalculado</th></tr></thead>
        <tbody>${g.filas.map(f => {
          const sale = f.total_calculado === null || f.total_calculado === undefined;
          return `
          <tr class="rm-fila${f.pierde_valor ? ' rm-fila--alerta' : ''}" data-total="${f.total}" data-calculado="${sale ? '' : f.total_calculado}"
              data-buscar="${esc([f.nombre, f.cedula, f.cargo, f.area, f.centro, f.concepto, g.etiqueta].join(' ').toLowerCase())}">
            <td class="rm-check"><input type="checkbox" value="${f.id}" ${f.recalcular ? 'checked' : ''}
                aria-label="Recalcular ${esc(g.etiqueta)} de ${esc(f.nombre)}"></td>
            <td><div class="rm-nombre">${esc(f.nombre) || '(sin nombre)'}</div>
                <div class="rm-sub">${f.cedula ? 'CC ' + esc(f.cedula) : 'Sin cédula'}${f.cargo ? ' · ' + esc(f.cargo) : ''}</div></td>
            <td><div>${esc(f.area) || '—'}</div><div class="rm-sub">${esc(f.centro)}</div></td>
            <td class="num">${pesos(f.total)}</td>
            <td class="num rm-nuevo">${sale
              ? '<span class="rm-sale" title="El cálculo no cubre a esta persona en este centro/área: la fila se quita">⚠️ sale del cálculo</span>'
              : (f.pierde_valor
                  ? `<span class="rm-sale" title="No tiene datos de origen (salario base o histórico): recalculada queda en 0">⚠️ ${pesos(f.total_calculado)}</span>`
                  : pesos(f.total_calculado))}</td>
          </tr>`;
        }).join('')}</tbody>
      </table>`).join('');
    resumen();
  }

  /** Muestra la ventana; devuelve {recalcular, no_recalcular} (ids) o null si se cancela. */
  async function elegirManuales(url) {
    const previa = new FormData();
    previa.append('previa', '1');
    const r = await PT.pedir(url, { method: 'POST', body: previa });
    const grupos = (r && r.grupos) || [];
    if (!grupos.length) return { recalcular: [], no_recalcular: [] };
    if (!dlg) crear();
    pintar(grupos);
    dlg.returnValue = '';
    dlg.showModal();
    return new Promise(resolver => {
      dlg.addEventListener('close', () => {
        if (dlg.returnValue !== 'aceptar') return resolver(null);
        const casillas = [...dlg.querySelectorAll('.rm-fila input')];
        resolver({
          recalcular: casillas.filter(i => i.checked).map(i => i.value),
          no_recalcular: casillas.filter(i => !i.checked).map(i => i.value),
        });
      }, { once: true });
    });
  }

  /** FormData para el botón (recalcular=… / no_recalcular=… / elegido=1), o null si se canceló. */
  async function formManuales(url) {
    const eleccion = await elegirManuales(url);
    if (eleccion === null) {
      PT.toast('No se recalculó nada', 'info');
      return null;
    }
    const datos = new FormData();
    datos.append('elegido', '1');
    eleccion.recalcular.forEach(id => datos.append('recalcular', id));
    eleccion.no_recalcular.forEach(id => datos.append('no_recalcular', id));
    return datos;
  }

  PT.elegirManuales = elegirManuales;
  PT.formManuales = formManuales;
})(window);
