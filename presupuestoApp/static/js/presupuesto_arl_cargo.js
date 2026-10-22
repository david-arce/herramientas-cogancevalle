/* ==========================================================================
 * presupuesto_arl_cargo.js
 * Panel "ARL por cargo · Asistencia técnica" de la pantalla de Seguridad social.
 * Cada cargo puede tener varias ARL en el Excel: aquí se elige cuál usar
 * (views_nomina.nomina_arl_cargo*). La ARL propia de la persona siempre manda.
 * ========================================================================== */
(function () {
  'use strict';

  const escapar = (v) => String(v == null ? '' : v).replace(/[&<>"']/g,
    c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const pct = (n) => Number(n).toLocaleString('es-CO', { maximumFractionDigits: 4 }) + ' %';
  const mismo = (a, b) => a != null && b != null && Math.abs(Number(a) - Number(b)) < 1e-9;

  function iniciar() {
    const panel = document.getElementById('panelArlCargo');
    const cuerpo = document.getElementById('acCargos');
    const tabla = window.tablaNomina;
    if (!panel || !cuerpo) return;
    const urls = (PT.listaJSON('pt-config') || {}).urls || {};
    let cargos = [];

    const opcionesDe = (c) => {
      const auto = c.automatica != null ? `Automática (${pct(c.automatica)})` : 'Automática (promedio del centro)';
      const lista = [`<option value="">${escapar(auto)}</option>`];
      c.opciones.forEach(o => {
        lista.push(`<option value="${o.porcentaje}" ${mismo(o.porcentaje, c.elegida) ? 'selected' : ''}>` +
                   `${escapar(pct(o.porcentaje))} · ${o.personas} persona${o.personas === 1 ? '' : 's'}</option>`);
      });
      // Elegida que ya no está entre las del Excel: se sigue mostrando
      if (c.elegida != null && !c.opciones.some(o => mismo(o.porcentaje, c.elegida))) {
        lista.push(`<option value="${c.elegida}" selected>${escapar(pct(c.elegida))} · ya no está en el Excel</option>`);
      }
      return lista.join('');
    };

    const pintar = () => {
      cuerpo.innerHTML = cargos.length
        ? cargos.map(c => {
            const sinEfecto = c.sin_arl === 0;
            const varias = c.opciones.length > 1;
            return `
              <tr class="${c.elegida != null ? 'ac-elegida' : ''}">
                <td><strong>${escapar(c.cargo)}</strong>${varias ? ' <span class="ac-varias" title="Este cargo tiene varias ARL en el Excel">varias ARL</span>' : ''}</td>
                <td class="ac-num">${c.personas}</td>
                <td class="ac-num${sinEfecto ? ' nd-suave' : ''}" title="${sinEfecto ? 'Todas traen su ARL en el Excel: la elección no cambia nada' : ''}">${c.sin_arl}</td>
                <td><select data-cargo="${escapar(c.cargo)}" aria-label="ARL para ${escapar(c.cargo)}">${opcionesDe(c)}</select></td>
              </tr>`;
          }).join('')
        : '<tr><td colspan="4" class="nd-vacio">No hay personas en asistencia técnica propia o convenio.</td></tr>';
    };

    const cargar = async () => {
      try {
        cargos = (await PT.pedir(urls.arlCargos)).data || [];
      } catch (e) {
        cargos = [];
        PT.toast('No se pudieron leer las ARL por cargo ❌', 'error');
      }
      pintar();
    };

    cuerpo.addEventListener('change', async (e) => {
      const select = e.target.closest('select[data-cargo]');
      if (!select) return;
      select.disabled = true;
      try {
        const r = await PT.enviarJSON(urls.guardarArlCargo, {
          cargo: select.dataset.cargo,
          porcentaje: select.value === '' ? null : Number(select.value)
        });
        cargos = r.cargos || cargos;
        if (tabla && typeof tabla.cargar === 'function') await tabla.cargar();
        PT.toast(r.msg, 'success', 8000);
      } catch (err) {
        PT.toast('❌ ' + err.message, 'error', 8000);
      }
      pintar();
    });

    cargar();
  }

  document.addEventListener('DOMContentLoaded', iniciar);
})();
