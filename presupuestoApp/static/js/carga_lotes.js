/* carga_lotes.js — subida por lotes de los Excel de Cuenta 4 / Cuenta 5 con
 * una ventana de progreso.
 *
 *   const loader = CargaLotes.loader("Cargando Cuenta 5");
 *   loader.fase("Leyendo el archivo…");
 *   await CargaLotes.pintar();                 // deja que el navegador dibuje antes de un trabajo pesado
 *   const total = await CargaLotes.enviar(filas, url, { loader, etiqueta: "Cuenta 5" });
 *   loader.exito(`${total} registros cargados`);   // o loader.error("…", ["detalle", …])
 *
 * Qué hace para que la subida sea rápida:
 *   - Manda las filas como listas ({columnas, filas}) en vez de objetos: no repite
 *     los 26 nombres de columna en cada fila (la mitad del tamaño o menos).
 *   - Comprime cada lote con gzip si el navegador lo permite (CompressionStream).
 *   - Arma lotes de hasta 5.000 filas sin pasar de ~1,5 MB sin comprimir, por debajo
 *     del límite por petición de Django (DATA_UPLOAD_MAX_MEMORY_SIZE = 2,5 MB).
 *   - Los lotes van en orden, uno tras otro, para que queden guardados en el
 *     mismo orden del Excel.
 */
(function (global) {
  "use strict";

  const MAX_FILAS_LOTE = 5000;
  const MAX_CHARS_LOTE = 1500000;
  const NF = new Intl.NumberFormat("es-CO");

  const pintar = () => new Promise(r => requestAnimationFrame(() => setTimeout(r, 0)));

  function getCookie(name) {
    for (const c of document.cookie.split(";")) {
      const [k, v] = c.trim().split("=");
      if (k === name) return decodeURIComponent(v);
    }
    return null;
  }

  function reloj(ms) {
    const s = Math.max(0, Math.round(ms / 1000));
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  }

  /* ── Estilos (se inyectan una sola vez) ─────────────────────── */
  function estilos() {
    if (document.getElementById("cl-estilos")) return;
    const css = `
      .cl-fondo { position: fixed; inset: 0; background: rgba(17,24,39,.45); z-index: 10060;
                  display: flex; align-items: center; justify-content: center; padding: 16px; }
      .cl-caja { background: #fff; color: #1f2937; border-radius: 12px; width: min(460px, 100%);
                 box-shadow: 0 20px 60px rgba(0,0,0,.25); padding: 20px 22px; font: 14px/1.45 system-ui, sans-serif; }
      .cl-titulo { display: flex; align-items: center; gap: 10px; font-weight: 600; font-size: 16px; margin: 0 0 4px; }
      .cl-girando { width: 18px; height: 18px; border: 2.5px solid #c7d2fe; border-top-color: #4f46e5;
                    border-radius: 50%; animation: cl-giro .8s linear infinite; flex: none; }
      @keyframes cl-giro { to { transform: rotate(360deg); } }
      .cl-icono { width: 20px; height: 20px; border-radius: 50%; display: inline-flex; align-items: center;
                  justify-content: center; color: #fff; font-size: 13px; flex: none; }
      .cl-fase { color: #4b5563; margin: 0 0 12px; min-height: 20px; }
      .cl-barra { height: 10px; background: #eef2ff; border-radius: 999px; overflow: hidden; }
      .cl-barra > div { height: 100%; width: 0; background: #4f46e5; border-radius: 999px; transition: width .25s ease; }
      .cl-barra.indeterminada > div { width: 35%; animation: cl-ir 1.1s ease-in-out infinite; }
      @keyframes cl-ir { 0% { transform: translateX(-100%); } 100% { transform: translateX(290%); } }
      .cl-datos { display: flex; justify-content: space-between; gap: 8px; margin-top: 8px; font-size: 13px; color: #374151;
                  font-variant-numeric: tabular-nums; flex-wrap: wrap; }
      .cl-datos b { color: #111827; }
      .cl-tiempo { color: #6b7280; font-size: 12.5px; margin-top: 2px; font-variant-numeric: tabular-nums; }
      .cl-detalle { margin: 10px 0 0; padding: 8px 10px 8px 26px; background: #fdecea; color: #8a1c1c; border-radius: 8px;
                    font-size: 13px; max-height: 180px; overflow: auto; }
      .cl-nota { margin-top: 10px; padding: 8px 10px; border-radius: 8px; background: #fff8d6; color: #6b4e00; font-size: 13px; }
      .cl-pie { display: flex; justify-content: flex-end; margin-top: 14px; }
      .cl-pie[hidden] { display: none; }   /* sin esto, display:flex anula hidden */
      .cl-pie button { border: none; background: #4f46e5; color: #fff; border-radius: 6px; padding: 7px 16px;
                       font: inherit; cursor: pointer; }
      .cl-caja.ok .cl-barra > div { background: #16a34a; }
      .cl-caja.mal .cl-barra > div { background: #dc2626; }
    `;
    const tag = document.createElement("style");
    tag.id = "cl-estilos";
    tag.textContent = css;
    document.head.appendChild(tag);
  }

  /* ── Ventana de progreso ────────────────────────────────────── */
  function loader(titulo) {
    estilos();
    const fondo = document.createElement("div");
    fondo.className = "cl-fondo";
    fondo.innerHTML = `
      <div class="cl-caja" role="dialog" aria-modal="true" aria-labelledby="cl-titulo">
        <div class="cl-titulo"><span class="cl-girando" aria-hidden="true"></span><span id="cl-titulo"></span></div>
        <div class="cl-fase" aria-live="polite"></div>
        <div class="cl-barra indeterminada" role="progressbar" aria-valuemin="0" aria-valuemax="100"><div></div></div>
        <div class="cl-datos"><span class="cl-cuenta"></span><span class="cl-pct"></span></div>
        <div class="cl-tiempo"></div>
        <div class="cl-extra"></div>
        <div class="cl-pie" hidden><button type="button">Cerrar</button></div>
      </div>`;
    document.body.appendChild(fondo);
    const $ = s => fondo.querySelector(s);
    $("#cl-titulo").textContent = titulo;
    const inicio = performance.now();
    let activo = true;

    // Evita cerrar o recargar la página a mitad de la subida
    const alSalir = e => { if (activo) { e.preventDefault(); e.returnValue = ""; } };
    window.addEventListener("beforeunload", alSalir);

    const cerrar = () => {
      activo = false;
      window.removeEventListener("beforeunload", alSalir);
      fondo.remove();
    };
    $(".cl-pie button").addEventListener("click", cerrar);

    function terminar(clase, simbolo, color) {
      activo = false;
      window.removeEventListener("beforeunload", alSalir);
      $(".cl-caja").classList.add(clase);
      const g = $(".cl-girando");
      const ic = document.createElement("span");
      ic.className = "cl-icono"; ic.textContent = simbolo; ic.style.background = color; ic.setAttribute("aria-hidden", "true");
      g.replaceWith(ic);
      $(".cl-barra").classList.remove("indeterminada");
      $(".cl-pie").hidden = false;
      $(".cl-pie button").focus();
    }

    return {
      fase(texto, indeterminada = true) {
        $(".cl-fase").textContent = texto;
        $(".cl-barra").classList.toggle("indeterminada", indeterminada);
      },
      progreso(hechos, total, detalle) {
        const pct = total ? Math.floor((hechos / total) * 100) : 0;
        const barra = $(".cl-barra");
        barra.classList.remove("indeterminada");
        barra.firstElementChild.style.width = pct + "%";
        barra.setAttribute("aria-valuenow", String(pct));
        $(".cl-cuenta").innerHTML = `<b>${NF.format(hechos)}</b> de ${NF.format(total)} registros`;
        $(".cl-pct").textContent = pct + "%";
        const trans = performance.now() - inicio;
        const restante = hechos > 0 && hechos < total ? (trans / hechos) * (total - hechos) : null;
        $(".cl-tiempo").textContent = [detalle, `${reloj(trans)} transcurrido`,
          restante !== null ? `~${reloj(restante)} restante` : ""].filter(Boolean).join(" · ");
      },
      exito(texto) {
        $(".cl-fase").textContent = texto;
        $(".cl-barra").firstElementChild.style.width = "100%";
        $(".cl-tiempo").textContent = `Tiempo total: ${reloj(performance.now() - inicio)}`;
        terminar("ok", "✓", "#16a34a");
        $(".cl-pie button").textContent = "Aceptar";
        setTimeout(() => { if (fondo.isConnected) cerrar(); }, 4000);
      },
      error(texto, detalles, nota) {
        $(".cl-fase").textContent = texto;
        $(".cl-tiempo").textContent = `Se detuvo a los ${reloj(performance.now() - inicio)}`;
        const extra = $(".cl-extra");
        extra.replaceChildren();
        if (detalles && detalles.length) {
          const ul = document.createElement("ul");
          ul.className = "cl-detalle";
          detalles.forEach(d => { const li = document.createElement("li"); li.textContent = d; ul.appendChild(li); });
          extra.appendChild(ul);
        }
        if (nota) {
          const n = document.createElement("div");
          n.className = "cl-nota"; n.textContent = nota;
          extra.appendChild(n);
        }
        terminar("mal", "!", "#dc2626");
      },
      cerrar,
    };
  }

  /* ── Lotes ──────────────────────────────────────────────────── */
  function armarLotes(registros) {
    // Columnas = todas las que aparecen en los registros, en el orden del primero
    const columnas = [];
    const vistas = new Set();
    registros.forEach(r => Object.keys(r).forEach(k => { if (!vistas.has(k)) { vistas.add(k); columnas.push(k); } }));

    const lotes = [];
    let actual = [], chars = 0;
    for (const r of registros) {
      const fila = columnas.map(c => (r[c] === undefined ? null : r[c]));
      const largo = JSON.stringify(fila).length + 1;
      if (actual.length && (actual.length >= MAX_FILAS_LOTE || chars + largo > MAX_CHARS_LOTE)) {
        lotes.push(actual); actual = []; chars = 0;
      }
      actual.push(fila); chars += largo;
    }
    if (actual.length) lotes.push(actual);
    return { columnas, lotes };
  }

  const PUEDE_GZIP = typeof global.CompressionStream === "function";

  async function cuerpo(texto) {
    if (!PUEDE_GZIP) return { body: texto, gzip: false };
    try {
      const stream = new Blob([texto]).stream().pipeThrough(new CompressionStream("gzip"));
      return { body: await new Response(stream).blob(), gzip: true };
    } catch (e) {
      return { body: texto, gzip: false };
    }
  }

  async function enviar(registros, url, opciones = {}) {
    const { loader: ld, etiqueta = "Carga" } = opciones;
    const { columnas, lotes } = armarLotes(registros);
    const totalFilas = registros.length;
    const t0 = performance.now();
    const seg = desde => ((performance.now() - desde) / 1000).toFixed(2);
    let total = 0;

    console.info(`[${etiqueta}] INICIO carga: ${totalFilas} registros en ${lotes.length} lote(s) → ${url}` +
                 (PUEDE_GZIP ? " (gzip)" : ""));
    if (ld) { ld.fase("Subiendo los datos al servidor…", false); ld.progreso(0, totalFilas, `Lote 1 de ${lotes.length}`); }

    for (let i = 0; i < lotes.length; i++) {
      const tLote = performance.now();
      const { body, gzip } = await cuerpo(JSON.stringify({ columnas, filas: lotes[i] }));
      const headers = {
        "Content-Type": gzip ? "application/octet-stream" : "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
        "X-Lote": `${i + 1}/${lotes.length}`,   // aparece en el log del servidor
      };
      if (gzip) headers["X-Compresion"] = "gzip";

      let r, d;
      try {
        r = await fetch(url, { method: "POST", headers, body });
        d = await r.json().catch(() => ({ status: "error", message: `Respuesta inválida del servidor (HTTP ${r.status})` }));
      } catch (e) {
        d = { status: "error", message: "No hubo conexión con el servidor" };
      }
      if (!r || !r.ok || d.status !== "ok") {
        console.error(`[${etiqueta}] ERROR en lote ${i + 1}/${lotes.length} tras ${seg(t0)} s:`, d.message || (r && r.status));
        const err = new Error(`Lote ${i + 1} de ${lotes.length}: ${d.message || (r && r.status)}`);
        err.guardados = total;
        throw err;
      }

      total += d.insertados;
      console.info(`[${etiqueta}] Lote ${i + 1}/${lotes.length}: ${d.insertados} registros en ${seg(tLote)} s (acumulado ${total})`);
      if (ld) ld.progreso(total, totalFilas, i + 1 < lotes.length ? `Lote ${i + 2} de ${lotes.length}` : "Último lote listo");
    }
    console.info(`[${etiqueta}] FIN carga: ${total} registros en ${seg(t0)} s`);
    return total;
  }

  global.CargaLotes = { loader, enviar, pintar, armarLotes, formato: n => NF.format(n) };
})(window);
