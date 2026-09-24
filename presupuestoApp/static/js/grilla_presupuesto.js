/* =====================================================================
 * Grilla de presupuesto tipo Excel, reutilizable.
 *
 * La usan dos pantallas:
 *   - El área, sobre su presupuesto en edición.
 *   - El aprobador, sobre una versión ya enviada.
 * Ambas comparten edición, relleno, copiar/pegar, deshacer, IPC, export,
 * plantilla e importación. Lo único que cambia son las URLs de lectura y
 * guardado y los botones propios de cada pantalla.
 *
 * Uso:
 *   const grilla = GrillaPresupuesto.init({
 *       sede: "almacen-tulua",
 *       urlObtener: "/...", urlGuardar: "/...", urlCuentas: "/...",
 *       soloLectura: false,
 *       onCargado(filas) {},
 *   });
 *   grilla.cambiarFuente(urlObtener, urlGuardar);  // cambiar de versión
 *   await grilla.vaciarColaDeGuardado();           // antes de subir/aprobar
 * ===================================================================== */
(function (global) {
"use strict";

const MESES = ["enero","febrero","marzo","abril","mayo","junio",
               "julio","agosto","septiembre","octubre","noviembre","diciembre"];

// Config de columnas: UNA sola fuente de verdad para header, celdas,
// validación, export y cálculo de total.
const COLUMNS = [
    { key: "_check", label: "", type: "check", locked: false, width: 30 },
    { key: "_acciones", label: "Acciones", type: "acciones", locked: true, width: 60 },
    { key: "nombre_cen", label: "Nombre asignación del gasto", type: "select-centro" },
    { key: "cuenta", label: "Cuenta", type: "text", locked: true },
    { key: "cuenta_mayor", label: "Cuenta Mayor", type: "select-cuenta" },
    { key: "detalle_cuenta", label: "Detalle Cuenta", type: "text" },
    ...MESES.map(m => ({ key: m, label: m[0].toUpperCase() + m.slice(1), type: "number" })),
    { key: "total", label: "Total", type: "number", locked: true },
    { key: "comentario", label: "Comentario", type: "text" },
];

// La selección tipo Excel se mueve solo dentro de las columnas de datos.
const COL_INI = COLUMNS.findIndex(c => c.type !== "check" && c.type !== "acciones");
const COL_FIN = COLUMNS.length - 1;

const OPCIONES_NOMBRE_CENTRO = {
    "ALMACEN TULUA":    { codigoCosto: "020202", centro: "001" },
    "ALMACEN BUGA":     { codigoCosto: "020200", centro: "002" },
    "ALMACEN CARTAGO":  { codigoCosto: "020202", centro: "003" },
    "ALMACEN CALI":     { codigoCosto: "020202", centro: "004" },
    "ADMINISTRACIÓN":   { codigoCosto: "0102",   centro: "001" },
    "SEVICIOS TÉCNICOS":{ codigoCosto: "020302", centro: "001" },
};
const EXCLUIR_CUENTAS = ["51","52","5105","5110","54","541001","541003","541006",
    "5410","541019","541027","541033","541095"];

// Filas en blanco que se agregan debajo de los datos al exportar, para que las
// listas desplegables y la autosuma queden disponibles más allá de lo cargado.
const EXPORT_FILAS_EXTRA = 200;

const PLANTILLA_HEADERS = [
    "Nombre asignación del gasto",
    "Cuenta Mayor",
    "Detalle Cuenta",
    ...MESES.map(m => m[0].toUpperCase() + m.slice(1)),
    "Total",
    "Comentario",
];
const PLANTILLA_FILAS_VACIAS = 200;
const COL_MES_INICIO = 4;                               // D: Enero
const COL_MES_FIN = COL_MES_INICIO + MESES.length - 1;  // O: Diciembre
const COL_TOTAL = COL_MES_FIN + 1;                      // P: Total

// ---------------------------------------------------------------------
// Utilidades sin estado
// ---------------------------------------------------------------------
function csrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : "";
}
function fmt(n) {
    if (n === null || n === undefined || n === "" || isNaN(n)) return n ?? "";
    return new Intl.NumberFormat('es-ES').format(n);
}
function colLetter(n) {
    let s = "";
    while (n > 0) {
        const m = (n - 1) % 26;
        s = String.fromCharCode(65 + m) + s;
        n = Math.floor((n - 1) / 26);
    }
    return s;
}
// Acepta lo que suele venir de Excel: separadores de miles, signo y espacios.
function parseNumero(valor) {
    if (typeof valor === "number") return Number.isFinite(valor) ? Math.round(valor) : 0;
    let t = String(valor ?? "").trim();
    if (t === "") return 0;
    const negativo = /^\(.*\)$/.test(t) || t.startsWith("-");
    t = t.replace(/[^0-9]/g, "");
    if (t === "") return 0;
    const n = parseInt(t, 10);
    return negativo ? -n : n;
}
function validarValorEntero(valorCrudo) {
    if (valorCrudo === "" || valorCrudo === null || valorCrudo === undefined) {
        return { valido: true, valor: 0 };
    }
    if (typeof valorCrudo === "number") {
        if (!Number.isFinite(valorCrudo) || !Number.isInteger(valorCrudo)) {
            return { valido: false, valor: 0 };
        }
        return { valido: true, valor: valorCrudo };
    }
    const texto = String(valorCrudo).trim();
    if (texto === "") return { valido: true, valor: 0 };
    if (!/^-?\d+$/.test(texto)) return { valido: false, valor: 0 };
    return { valido: true, valor: parseInt(texto, 10) };
}
function escaparHtml(texto) {
    const div = document.createElement("div");
    div.textContent = String(texto ?? "");
    return div.innerHTML;
}
// escaparHtml no convierte comillas: un texto con " rompía el value="…".
function escaparAttr(texto) {
    return escaparHtml(texto).replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
function showToast(message, type = "success", duration = 3000) {
    const container = document.getElementById("toastContainer");
    if (!container) return null;
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add("show"));
    setTimeout(() => { toast.classList.remove("show"); setTimeout(() => toast.remove(), 400); }, duration);
    return toast;
}
function descargarBuffer(buffer, nombre) {
    const blob = new Blob([buffer], { type: "application/octet-stream" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = nombre;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}
async function apiGet(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`GET ${url} -> ${res.status}`);
    return res.json();
}
async function apiPost(url, body) {
    const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
        body: JSON.stringify(body),
    });
    return res.json();
}
async function bloquearFilaEncabezado(hoja) {
    const totalCols = hoja.columnCount;
    hoja.getRow(1).eachCell({ includeEmpty: true }, cell => { cell.protection = { locked: true }; });
    for (let r = 2; r <= hoja.rowCount; r++) {
        for (let c = 1; c <= totalCols; c++) hoja.getCell(r, c).protection = { locked: false };
    }
    await hoja.protect("", { selectLockedCells: true, selectUnlockedCells: true });
}

// Contador de modales abiertos: mientras haya uno abierto la grilla ignora
// los atajos de teclado.
let modalesAbiertos = 0;
function abrirModal(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.style.display = "block";
    modalesAbiertos++;
}
function cerrarModal(id) {
    const el = document.getElementById(id);
    if (!el) return;
    if (el.style.display === "block") modalesAbiertos = Math.max(0, modalesAbiertos - 1);
    el.style.display = "none";
}
document.addEventListener("click", (e) => {
    const btn = e.target.closest(".btn-cancel[data-modal]");
    if (btn) cerrarModal(btn.dataset.modal);
});

// =====================================================================
// init
// =====================================================================
function init(opciones) {
    const OPC = Object.assign({
        sede: "", urlObtener: "", urlGuardar: "", urlCuentas: "",
        soloLectura: false, nombreExport: "presupuesto", onCargado: null,
    }, opciones);

    let rows = [];
    let mapaCuentaMayor = {};
    let sel = null;                 // { r1, c1, r2, c2 } → (r1,c1) es el ancla
    let editingInput = null;
    let editando = null;            // { rowIndex, colKey, td }
    let rangoCopiado = null;        // { r0, c0, r1, c1, cortar }
    let arrastre = null;            // { tipo: "seleccion"|"relleno", base?, destino? }

    const $ = (id) => document.getElementById(id);
    const puedeEditar = () => !OPC.soloLectura;

    // -----------------------------------------------------------------
    // Guardado automático
    // -----------------------------------------------------------------
    const AUTOSAVE_DEBOUNCE_MS = 800;
    let autoSaveTimer = null;
    let autoSaveEnCurso = null;
    let autoSaveDatosPendientes = false;

    function setAutoSaveStatus(estado, texto) {
        const el = $("autoSaveStatus");
        if (!el) return;
        el.classList.remove("saving", "saved", "error");
        el.classList.add(estado);
        const txt = $("autoSaveStatusText");
        if (txt) txt.textContent = texto;
    }

    function programarGuardadoAutomatico() {
        if (!puedeEditar()) return;
        setAutoSaveStatus("saving", "Cambios sin guardar…");
        clearTimeout(autoSaveTimer);
        autoSaveTimer = setTimeout(() => { autoSaveTimer = null; ejecutarGuardadoAutomatico(); }, AUTOSAVE_DEBOUNCE_MS);
    }

    function ejecutarGuardadoAutomatico() {
        if (!puedeEditar()) return Promise.resolve();
        if (autoSaveEnCurso) {          // ya hay uno en vuelo: se reprograma al terminar
            autoSaveDatosPendientes = true;
            return autoSaveEnCurso;
        }
        setAutoSaveStatus("saving", "Guardando…");
        autoSaveEnCurso = (async () => {
            try {
                const payload = rows.map(r => { const { _checked, ...resto } = r; return resto; });
                const resp = await apiPost(OPC.urlGuardar, payload);
                if (resp.status === "ok") {
                    setAutoSaveStatus("saved", "Todo guardado");
                } else {
                    setAutoSaveStatus("error", "Error al guardar ❌");
                    showToast(resp.message || "Error al guardar ❌", "error");
                }
            } catch (e) {
                setAutoSaveStatus("error", "Error al guardar ❌");
                showToast("Error al guardar ❌", "error");
            } finally {
                autoSaveEnCurso = null;
                if (autoSaveDatosPendientes) {
                    autoSaveDatosPendientes = false;
                    programarGuardadoAutomatico();
                }
            }
        })();
        return autoSaveEnCurso;
    }

    // Fuerza que todo lo pendiente llegue al servidor (antes de subir/aprobar).
    async function vaciarColaDeGuardado() {
        if (!puedeEditar()) return;
        clearTimeout(autoSaveTimer);
        autoSaveTimer = null;
        if (autoSaveEnCurso) await autoSaveEnCurso;
        autoSaveDatosPendientes = false;
        await ejecutarGuardadoAutomatico();
    }

    window.addEventListener("beforeunload", (e) => {
        if (autoSaveTimer || autoSaveEnCurso) { e.preventDefault(); e.returnValue = ""; }
    });

    // -----------------------------------------------------------------
    // Historial: deshacer / rehacer
    // -----------------------------------------------------------------
    const HISTORIAL_MAX = 60;
    let pilaDeshacer = [];
    let pilaRehacer = [];

    function instantanea() {
        pilaDeshacer.push(JSON.stringify(rows));
        if (pilaDeshacer.length > HISTORIAL_MAX) pilaDeshacer.shift();
        pilaRehacer.length = 0;
        actualizarBotonesHistorial();
    }
    function restaurar(desde, hacia) {
        if (desde.length === 0) return;
        hacia.push(JSON.stringify(rows));
        rows = JSON.parse(desde.pop());
        rows.forEach(r => { if (r._checked === undefined) r._checked = false; });
        limitarSeleccion();
        render();
        actualizarBotonesHistorial();
        programarGuardadoAutomatico();
    }
    function deshacer() { if (puedeEditar()) restaurar(pilaDeshacer, pilaRehacer); }
    function rehacer() { if (puedeEditar()) restaurar(pilaRehacer, pilaDeshacer); }
    function actualizarBotonesHistorial() {
        const d = $("deshacerBtn"), r = $("rehacerBtn");
        if (d) d.disabled = pilaDeshacer.length === 0;
        if (r) r.disabled = pilaRehacer.length === 0;
    }

    // -----------------------------------------------------------------
    // Carga de datos
    // -----------------------------------------------------------------
    async function cargarOpcionesCuenta() {
        try {
            const resp = await apiGet(OPC.urlCuentas);
            mapaCuentaMayor = resp.cuentas_dict || {};
        } catch (e) { showToast("No se pudieron cargar las cuentas contables ❌", "error"); }
    }

    async function cargarDatos() {
        const resp = await apiGet(OPC.urlObtener);
        rows = Array.isArray(resp) ? resp : (resp.data || []);
        rows.forEach(r => { r._checked = false; });
        pilaDeshacer.length = 0;
        pilaRehacer.length = 0;
        actualizarBotonesHistorial();
        sel = null;
        render();
        if (rows.length) seleccionar(0, COL_INI);
        setAutoSaveStatus("saved", OPC.soloLectura ? "Solo lectura" : "Todo guardado");
        if (typeof OPC.onCargado === "function") OPC.onCargado(rows);
    }

    // -----------------------------------------------------------------
    // Render
    // -----------------------------------------------------------------
    function renderHeader() {
        const headerRow = $("gridHeaderRow");
        headerRow.innerHTML = "";
        COLUMNS.forEach((col, ci) => {
            const th = document.createElement("th");
            th.dataset.colIndex = ci;
            if (col.key === "_check") {
                th.innerHTML = `<input type="checkbox" id="checkAllIPC" title="Seleccionar todo">`;
            } else {
                th.textContent = col.label;
            }
            headerRow.appendChild(th);
        });
    }

    function render() {
        const tbody = $("gridBody");
        const frag = document.createDocumentFragment();
        rows.forEach((row, rowIndex) => {
            const tr = document.createElement("tr");
            tr.dataset.rowIndex = rowIndex;
            COLUMNS.forEach((col, ci) => tr.appendChild(renderCell(row, rowIndex, col, ci)));
            frag.appendChild(tr);
        });
        tbody.innerHTML = "";
        tbody.appendChild(frag);
        syncCheckAllState();
        programarTotales();
        pintarSeleccion();
    }

    // Fila de totales al pie. Se recalcula como máximo una vez por cuadro de
    // animación: operaciones como el IPC repintan cientos de filas seguidas y
    // no tiene sentido sumar la tabla completa por cada una.
    let totalesPendientes = false;
    function programarTotales() {
        if (totalesPendientes) return;
        totalesPendientes = true;
        requestAnimationFrame(() => { totalesPendientes = false; renderTotales(); });
    }
    function renderTotales() {
        const fila = $("gridFooterRow");
        if (!fila) return;
        const sumas = {};
        COLUMNS.forEach(c => { if (c.type === "number") sumas[c.key] = 0; });
        rows.forEach(r => { for (const k in sumas) sumas[k] += parseFloat(r[k]) || 0; });

        fila.innerHTML = COLUMNS.map((col, ci) => {
            if (ci === COL_INI) {
                return `<td class="total-etiqueta">TOTAL · ${rows.length} fila${rows.length === 1 ? "" : "s"}</td>`;
            }
            if (col.type === "number") {
                const clase = col.key === "total" ? "numeric total-general" : "numeric";
                return `<td class="${clase}">${fmt(sumas[col.key])}</td>`;
            }
            return "<td></td>";
        }).join("");
    }

    function renderCell(row, rowIndex, col, colIdx) {
        const td = document.createElement("td");
        td.dataset.rowIndex = rowIndex;
        td.dataset.colKey = col.key;
        td.dataset.colIndex = colIdx;

        if (col.key === "_check") {
            td.innerHTML = `<input type="checkbox" class="row-check" ${row._checked ? "checked" : ""}>`;
            return td;
        }
        if (col.key === "_acciones") {
            td.innerHTML = puedeEditar()
                ? `<button class="dupBtn" title="Duplicar fila">📑</button><button class="delBtn" title="Eliminar fila">❌</button>`
                : "";
            return td;
        }

        td.classList.add(col.locked || !puedeEditar() ? "locked" : "editable");
        if (col.type === "number") td.classList.add("numeric");
        td.textContent = col.type === "number" ? fmt(row[col.key]) : (row[col.key] ?? "");
        return td;
    }

    // Repinta solo una fila: reconstruir toda la tabla en cada edición hacía
    // perder el scroll y la selección.
    function pintarFila(rowIndex) {
        const row = rows[rowIndex];
        if (!row) return;
        COLUMNS.forEach((col, ci) => {
            const td = tdDe(rowIndex, ci);
            if (!td || td.classList.contains("editing")) return;
            if (col.type === "check") {
                const cb = td.querySelector("input");
                if (cb) cb.checked = !!row._checked;
                return;
            }
            if (col.type === "acciones") return;
            td.textContent = col.type === "number" ? fmt(row[col.key]) : (row[col.key] ?? "");
        });
        programarTotales();
    }

    function syncCheckAllState() {
        const total = rows.length;
        const marcados = rows.filter(r => r._checked).length;
        const checkAll = $("checkAllIPC");
        if (!checkAll) return;
        checkAll.checked = total > 0 && marcados === total;
        checkAll.indeterminate = marcados > 0 && marcados < total;
    }

    // -----------------------------------------------------------------
    // Selección tipo Excel
    // -----------------------------------------------------------------
    function tdDe(r, c) {
        return document.querySelector(`#gridBody td[data-row-index="${r}"][data-col-index="${c}"]`);
    }
    function rangoNormalizado(s = sel) {
        if (!s) return null;
        return {
            r0: Math.min(s.r1, s.r2), r1: Math.max(s.r1, s.r2),
            c0: Math.min(s.c1, s.c2), c1: Math.max(s.c1, s.c2),
        };
    }
    function clampFila(r) { return Math.max(0, Math.min(rows.length - 1, r)); }
    function clampCol(c) { return Math.max(COL_INI, Math.min(COL_FIN, c)); }
    function limitarSeleccion() {
        if (!sel) return;
        if (rows.length === 0) { sel = null; return; }
        sel = { r1: clampFila(sel.r1), c1: clampCol(sel.c1), r2: clampFila(sel.r2), c2: clampCol(sel.c2) };
    }

    function seleccionar(r, c, extender = false) {
        if (rows.length === 0) return;
        r = clampFila(r); c = clampCol(c);
        if (!extender || !sel) sel = { r1: r, c1: c, r2: r, c2: c };
        else { sel.r2 = r; sel.c2 = c; }
        pintarSeleccion();
        const td = tdDe(sel.r2, sel.c2);
        if (td) td.scrollIntoView({ block: "nearest", inline: "nearest" });
    }

    function posicionarOverlay(el, r0, c0, r1, c1) {
        const a = tdDe(r0, c0), b = tdDe(r1, c1);
        if (!a || !b) { el.style.display = "none"; return; }
        el.style.display = "block";
        el.style.left = a.offsetLeft + "px";
        el.style.top = a.offsetTop + "px";
        el.style.width = (b.offsetLeft + b.offsetWidth - a.offsetLeft) + "px";
        el.style.height = (b.offsetTop + b.offsetHeight - a.offsetTop) + "px";
    }

    function pintarSeleccion() {
        const ov = $("overlaySel");
        if (!sel || rows.length === 0) {
            ov.style.display = "none";
            pintarCopiado();
            actualizarBarraEstado();
            return;
        }
        const { r0, r1, c0, c1 } = rangoNormalizado();
        posicionarOverlay(ov, r0, c0, r1, c1);

        document.querySelectorAll("#gridBody tr.fila-activa").forEach(t => t.classList.remove("fila-activa"));
        const tr = document.querySelector(`#gridBody tr[data-row-index="${sel.r1}"]`);
        if (tr) tr.classList.add("fila-activa");
        document.querySelectorAll("#gridHeaderRow th").forEach(th => {
            const i = parseInt(th.dataset.colIndex, 10);
            th.classList.toggle("col-activa", i >= c0 && i <= c1);
        });

        pintarCopiado();
        actualizarBarraEstado();
    }

    function pintarCopiado() {
        const ov = $("overlayCopia");
        if (!rangoCopiado) { ov.style.display = "none"; return; }
        posicionarOverlay(ov, rangoCopiado.r0, rangoCopiado.c0, rangoCopiado.r1, rangoCopiado.c1);
    }

    function actualizarBarraEstado() {
        const celdaEl = $("estadoCelda");
        if (!celdaEl) return;
        const recEl = $("estadoRecuento"), sumEl = $("estadoSuma"), promEl = $("estadoPromedio");
        if (!sel) { celdaEl.textContent = "—"; recEl.textContent = sumEl.textContent = promEl.textContent = ""; return; }

        const { r0, r1, c0, c1 } = rangoNormalizado();
        const filas = r1 - r0 + 1, cols = c1 - c0 + 1;
        const ref = `${COLUMNS[sel.c1].label} · fila ${sel.r1 + 1}`;
        celdaEl.innerHTML = `<b>${escaparHtml(ref)}</b>` + (filas * cols > 1 ? ` (${filas}×${cols})` : "");

        let n = 0, suma = 0;
        for (let r = r0; r <= r1; r++) {
            for (let c = c0; c <= c1; c++) {
                if (COLUMNS[c].type !== "number") continue;
                const v = parseFloat(rows[r][COLUMNS[c].key]);
                if (!isNaN(v)) { n++; suma += v; }
            }
        }
        recEl.textContent = n ? `Recuento: ${n}` : "";
        sumEl.innerHTML = n ? `Suma: <b>${fmt(suma)}</b>` : "";
        promEl.textContent = n ? `Promedio: ${fmt(Math.round(suma / n))}` : "";
    }

    window.addEventListener("resize", pintarSeleccion);

    // -----------------------------------------------------------------
    // Lectura / escritura de celdas (única puerta de entrada a los datos)
    // -----------------------------------------------------------------
    function recalcularTotal(row) {
        row.total = MESES.reduce((acc, m) => acc + (parseFloat(row[m]) || 0), 0);
    }

    function valorTextoCelda(row, col) {
        if (col.key === "cuenta_mayor") {
            return row.cuenta ? `${row.cuenta} - ${row.cuenta_mayor || ""}` : (row.cuenta_mayor || "");
        }
        if (col.type === "number") return row[col.key] ?? 0;
        return row[col.key] ?? "";
    }

    // Escribe respetando las reglas de negocio (código de costo, centro de
    // trabajo, recálculo del total). Devuelve true si escribió.
    function aplicarValor(row, colKey, valor) {
        const col = COLUMNS.find(c => c.key === colKey);
        if (!col || col.locked || col.type === "check" || col.type === "acciones") return false;

        if (colKey === "cuenta_mayor") {
            const crudo = String(valor ?? "").trim();
            if (crudo === "") { row.cuenta = ""; row.cuenta_mayor = ""; return true; }
            let codigo = crudo.split(" - ")[0].trim();
            if (mapaCuentaMayor[codigo] === undefined) {
                // Pudo haberse pegado el nombre de la cuenta en vez del código
                const porNombre = Object.keys(mapaCuentaMayor)
                    .find(k => String(mapaCuentaMayor[k] || "").toUpperCase() === crudo.toUpperCase());
                if (!porNombre) return false;
                codigo = porNombre;
            }
            row.cuenta = codigo;
            row.cuenta_mayor = mapaCuentaMayor[codigo] || "";
            if (["510531", "51059503"].includes(codigo)) row.codcosto = "0101";
            if (["540531", "54059503"].includes(codigo)) row.codcosto = "020201";
            return true;
        }
        if (colKey === "nombre_cen") {
            const crudo = String(valor ?? "").trim();
            if (crudo === "") { row.nombre_cen = ""; row.codcosto = ""; row.centro_tra = ""; return true; }
            const clave = Object.keys(OPCIONES_NOMBRE_CENTRO).find(k => k.toUpperCase() === crudo.toUpperCase());
            if (!clave) return false;
            row.nombre_cen = clave;
            row.codcosto = OPCIONES_NOMBRE_CENTRO[clave].codigoCosto;
            row.centro_tra = OPCIONES_NOMBRE_CENTRO[clave].centro;
            return true;
        }
        if (col.type === "number") {
            row[colKey] = parseNumero(valor);
            if (MESES.includes(colKey)) recalcularTotal(row);
            return true;
        }
        row[colKey] = String(valor ?? "").toUpperCase();
        return true;
    }

    // -----------------------------------------------------------------
    // Edición de celda
    // -----------------------------------------------------------------
    // Coloca el cursor en el carácter más cercano al clic, midiendo el ancho
    // real del texto con la misma fuente del input.
    function posicionarCursorPorX(input, clientX) {
        const texto = input.value;
        if (!texto) return;
        const rect = input.getBoundingClientRect();
        const cs = getComputedStyle(input);
        const ctx = posicionarCursorPorX._ctx ||
            (posicionarCursorPorX._ctx = document.createElement("canvas").getContext("2d"));
        ctx.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;

        const anchoTexto = ctx.measureText(texto).width;
        const padIzq = parseFloat(cs.paddingLeft) || 0;
        const padDer = parseFloat(cs.paddingRight) || 0;
        let origen;
        if (cs.textAlign === "right" || cs.textAlign === "end") origen = rect.right - padDer - anchoTexto;
        else if (cs.textAlign === "center") origen = rect.left + (rect.width - anchoTexto) / 2;
        else origen = rect.left + padIzq;

        const x = clientX - origen + input.scrollLeft;
        let idx = texto.length;
        for (let i = 0; i < texto.length; i++) {
            const izq = ctx.measureText(texto.slice(0, i)).width;
            const der = ctx.measureText(texto.slice(0, i + 1)).width;
            if (x < (izq + der) / 2) { idx = i; break; }
        }
        input.setSelectionRange(idx, idx);
    }

    function iniciarEdicion(r, c, valorInicial = null, clickX = null) {
        if (!puedeEditar()) return;
        const col = COLUMNS[c];
        const td = tdDe(r, c);
        if (!td || !col || col.locked || col.type === "check" || col.type === "acciones") return;
        const row = rows[r];
        td.classList.add("editing");
        editando = { rowIndex: r, colKey: col.key, colIdx: c, td };

        const esSelect = col.type === "select-cuenta" || col.type === "select-centro";

        if (col.type === "select-cuenta") td.innerHTML = renderSelectCuentaMayor(row);
        else if (col.type === "select-centro") td.innerHTML = renderSelectNombreCentro();
        else {
            const val = valorInicial ?? (row[col.key] ?? "");
            td.innerHTML = `<input type="text" value="${escaparAttr(val)}">`;
        }

        const input = td.querySelector("input, select");

        if (esSelect) {
            // El valor actual se fija por DOM: el setter .value hace la coerción
            // string/number, así que sirve aunque row.cuenta venga como number.
            const actual = col.key === "cuenta_mayor" ? row.cuenta : row.nombre_cen;
            if (actual !== null && actual !== undefined && actual !== "") input.value = String(actual);
            if (valorInicial) {
                const letra = String(valorInicial).toUpperCase();
                const op = Array.from(input.options).find(o => o.text.toUpperCase().startsWith(letra));
                if (op) input.value = op.value;
            }
        }

        input.focus();
        editingInput = input;

        // Cursor como en Excel: nunca se resalta todo el contenido.
        if (input.tagName === "INPUT") {
            if (clickX !== null && valorInicial === null) posicionarCursorPorX(input, clickX);
            else input.setSelectionRange(input.value.length, input.value.length);
        }

        if (col.type === "number") {
            // Se permite el signo menos al inicio y solo se reasigna .value si
            // hubo caracteres inválidos (asignarlo siempre mandaba el cursor al final).
            input.addEventListener("input", () => {
                const antes = input.value;
                const pos = input.selectionStart;
                const neg = antes.trim().startsWith("-");
                const limpio = (neg ? "-" : "") + antes.replace(/[^0-9]/g, "");
                if (limpio === antes) return;
                input.value = limpio;
                const nuevo = Math.max(0, pos - (antes.length - limpio.length));
                input.setSelectionRange(nuevo, nuevo);
            });
        } else if (input.tagName === "INPUT") {
            input.addEventListener("input", () => {
                const mayus = input.value.toUpperCase();
                if (mayus === input.value) return;
                const pos = input.selectionStart, fin = input.selectionEnd;
                input.value = mayus;
                input.setSelectionRange(pos, fin);
            });
        }

        input.addEventListener("keydown", manejarTeclaEnEdicion);
        input.addEventListener("blur", () => { if (editingInput === input) cerrarEdicion(false); });
        if (input.tagName === "SELECT") {
            input.addEventListener("change", () => cerrarEdicion(false));
            if (typeof input.showPicker === "function") { try { input.showPicker(); } catch (_) {} }
        }
    }

    function renderSelectCuentaMayor(row) {
        let opciones = Object.keys(mapaCuentaMayor);
        const esAdmin = (row.nombre_cen || "").toUpperCase() === "ADMINISTRACIÓN";
        opciones = opciones.filter(o => esAdmin ? o.startsWith("51") : !o.startsWith("51"));
        opciones = opciones.filter(o => !EXCLUIR_CUENTAS.includes(o));

        // row.cuenta llega como number desde el backend; las claves del mapa
        // son strings, así que se normaliza antes de comparar.
        const actual = (row.cuenta !== null && row.cuenta !== undefined) ? String(row.cuenta) : "";
        if (actual && !opciones.includes(actual) && mapaCuentaMayor[actual] !== undefined) {
            opciones.push(actual); // dato legado: no se pierde silenciosamente
        }
        opciones.sort((a, b) => a.localeCompare(b, 'es', { numeric: true }));
        return `<select><option value=""></option>` + opciones.map(o =>
            `<option value="${escaparAttr(o)}">${escaparHtml(o)} - ${escaparHtml(mapaCuentaMayor[o] || "")}</option>`
        ).join("") + `</select>`;
    }
    function renderSelectNombreCentro() {
        return `<select><option value=""></option>` + Object.keys(OPCIONES_NOMBRE_CENTRO).map(o =>
            `<option value="${escaparAttr(o)}">${escaparHtml(o)}</option>`
        ).join("") + `</select>`;
    }

    function cerrarEdicion(cancelar = false) {
        if (!editando || !editingInput) { editingInput = null; editando = null; return; }
        const { rowIndex, colKey, td } = editando;
        const input = editingInput;
        editingInput = null;
        editando = null;

        let huboCambio = false;
        if (!cancelar) {
            const antes = JSON.stringify(rows[rowIndex]);
            instantanea();
            const ok = aplicarValor(rows[rowIndex], colKey, input.value);
            if (!ok || JSON.stringify(rows[rowIndex]) === antes) {
                pilaDeshacer.pop();                      // no cambió nada: no ensuciar el historial
                actualizarBotonesHistorial();
                if (!ok && input.value !== "") showToast("Ese valor no es válido para la columna ❌", "error");
            } else {
                huboCambio = true;
            }
        }

        td.classList.remove("editing");
        pintarFila(rowIndex);
        pintarSeleccion();
        if (huboCambio) programarGuardadoAutomatico();
    }

    function manejarTeclaEnEdicion(e) {
        if (!editando) return;
        const { rowIndex, colIdx } = editando;
        if (e.key === "Escape") { e.preventDefault(); cerrarEdicion(true); focoGrilla(); return; }
        if (e.key === "Enter") {
            e.preventDefault(); cerrarEdicion(false); seleccionar(rowIndex + 1, colIdx); focoGrilla(); return;
        }
        if (e.key === "Tab") {
            e.preventDefault(); cerrarEdicion(false);
            seleccionar(rowIndex, colIdx + (e.shiftKey ? -1 : 1)); focoGrilla(); return;
        }
    }

    function focoGrilla() { $("gridContainer").focus({ preventScroll: true }); }

    // -----------------------------------------------------------------
    // Mouse: selección por arrastre y manija de relleno
    // -----------------------------------------------------------------
    $("gridBody").addEventListener("mousedown", (e) => {
        if (e.button !== 0) return;
        const td = e.target.closest("td");
        if (!td || td.dataset.colIndex === undefined) return;
        const c = parseInt(td.dataset.colIndex, 10);
        const r = parseInt(td.dataset.rowIndex, 10);
        if (c < COL_INI) return;                       // columnas de check/acciones
        if (td.classList.contains("editing")) return;  // clic dentro del editor

        if (editingInput) cerrarEdicion(false);
        e.preventDefault();
        seleccionar(r, c, e.shiftKey);
        if (!e.shiftKey) {
            arrastre = { tipo: "seleccion" };
            document.body.classList.add("arrastrando");
        }
        focoGrilla();
    });

    $("fillHandle").addEventListener("mousedown", (e) => {
        if (!sel || !puedeEditar()) return;
        e.preventDefault();
        e.stopPropagation();
        arrastre = { tipo: "relleno", base: rangoNormalizado(), destino: rangoNormalizado(), ctrl: e.ctrlKey || e.metaKey };
        document.body.classList.add("arrastrando");
    });

    $("fillHandle").addEventListener("dblclick", (e) => {
        e.preventDefault();
        rellenarHastaFinDeDatos();
    });

    document.addEventListener("mousemove", (e) => {
        if (!arrastre) return;
        autoScroll(e);
        const td = document.elementFromPoint(e.clientX, e.clientY)?.closest?.("td");
        if (!td || td.dataset.colIndex === undefined) return;
        const r = clampFila(parseInt(td.dataset.rowIndex, 10));
        const c = clampCol(parseInt(td.dataset.colIndex, 10));

        if (arrastre.tipo === "seleccion") {
            if (sel.r2 === r && sel.c2 === c) return;   // nada cambió: no repintar
            sel.r2 = r; sel.c2 = c;
            pintarSeleccion();
        } else {
            const destino = calcularDestinoRelleno(arrastre.base, r, c);
            const d = arrastre.destino;
            if (d && d.r0 === destino.r0 && d.r1 === destino.r1 && d.c0 === destino.c0 && d.c1 === destino.c1) return;
            arrastre.destino = destino;
            posicionarOverlay($("overlayRelleno"), destino.r0, destino.c0, destino.r1, destino.c1);
        }
    });

    document.addEventListener("mouseup", (e) => {
        if (!arrastre) return;
        const tipo = arrastre.tipo, destino = arrastre.destino, base = arrastre.base;
        const ctrl = arrastre.ctrl || e.ctrlKey || e.metaKey;
        arrastre = null;
        document.body.classList.remove("arrastrando");
        $("overlayRelleno").style.display = "none";
        if (tipo === "relleno" && destino) {
            aplicarRelleno(base, destino, ctrl);
            sel = { r1: destino.r0, c1: destino.c0, r2: destino.r1, c2: destino.c1 };
            pintarSeleccion();
        }
    });

    // El relleno se extiende en UN solo eje (el de mayor recorrido), como Excel.
    function calcularDestinoRelleno(base, r, c) {
        const dAbajo = r - base.r1, dArriba = base.r0 - r;
        const dDer = c - base.c1, dIzq = base.c0 - c;
        const vert = Math.max(dAbajo, dArriba, 0);
        const horiz = Math.max(dDer, dIzq, 0);
        if (vert === 0 && horiz === 0) return { ...base };
        if (vert >= horiz) {
            return dAbajo >= dArriba
                ? { r0: base.r0, r1: base.r1 + dAbajo, c0: base.c0, c1: base.c1 }
                : { r0: base.r0 - dArriba, r1: base.r1, c0: base.c0, c1: base.c1 };
        }
        return dDer >= dIzq
            ? { r0: base.r0, r1: base.r1, c0: base.c0, c1: base.c1 + dDer }
            : { r0: base.r0, r1: base.r1, c0: base.c0 - dIzq, c1: base.c1 };
    }

    function autoScroll(e) {
        const cont = $("gridContainer");
        const rect = cont.getBoundingClientRect();
        const margen = 28, paso = 22;
        if (e.clientY > rect.bottom - margen) cont.scrollTop += paso;
        else if (e.clientY < rect.top + margen) cont.scrollTop -= paso;
        if (e.clientX > rect.right - margen) cont.scrollLeft += paso;
        else if (e.clientX < rect.left + margen) cont.scrollLeft -= paso;
    }

    // -----------------------------------------------------------------
    // Series de relleno (copiar vs. continuar la serie, como Excel)
    // -----------------------------------------------------------------
    function esNumerico(v) {
        if (typeof v === "number") return Number.isFinite(v);
        const t = String(v ?? "").trim();
        return t !== "" && /^-?\d+([.,]\d+)?$/.test(t);
    }
    function aNumero(v) { return typeof v === "number" ? v : parseFloat(String(v).replace(",", ".")); }

    function generarSerie(base, cantidad, invertirCtrl, forzarCopia = false) {
        const salida = [];
        if (forzarCopia) {
            for (let i = 0; i < cantidad; i++) salida.push(base[i % base.length]);
            return salida;
        }
        const todosNum = base.length > 0 && base.every(esNumerico);

        if (todosNum) {
            const nums = base.map(aNumero);
            const incrementar = base.length > 1 ? !invertirCtrl : !!invertirCtrl;
            if (!incrementar) {
                for (let i = 0; i < cantidad; i++) salida.push(nums[i % nums.length]);
                return salida;
            }
            let paso = 1;
            if (nums.length > 1) {
                const diffs = nums.slice(1).map((v, i) => v - nums[i]);
                const uniforme = diffs.every(d => d === diffs[0]);
                paso = uniforme ? diffs[0] : pendienteRegresion(nums);
            }
            const ultimo = nums[nums.length - 1];
            for (let i = 0; i < cantidad; i++) salida.push(Math.round(ultimo + paso * (i + 1)));
            return salida;
        }

        // Texto terminado en número: "SEDE 1" → "SEDE 2" (Ctrl invierte a copiar)
        if (base.length === 1) {
            const texto = String(base[0] ?? "");
            const m = texto.match(/^(.*?)(\d+)(\s*)$/);
            const incrementar = m && !invertirCtrl;
            for (let i = 0; i < cantidad; i++) {
                if (incrementar) {
                    const num = String(parseInt(m[2], 10) + i + 1).padStart(m[2].length, "0");
                    salida.push(`${m[1]}${num}${m[3]}`);
                } else salida.push(texto);
            }
            return salida;
        }
        for (let i = 0; i < cantidad; i++) salida.push(base[i % base.length]);
        return salida;
    }
    function pendienteRegresion(nums) {
        const n = nums.length;
        const mediaX = (n - 1) / 2;
        const mediaY = nums.reduce((a, b) => a + b, 0) / n;
        let num = 0, den = 0;
        nums.forEach((y, i) => { num += (i - mediaX) * (y - mediaY); den += (i - mediaX) ** 2; });
        return den === 0 ? 0 : num / den;
    }

    function aplicarRelleno(base, destino, ctrl, forzarCopia = false) {
        if (!puedeEditar() || !base || !destino) return;
        const hayCambio = destino.r0 !== base.r0 || destino.r1 !== base.r1 ||
                          destino.c0 !== base.c0 || destino.c1 !== base.c1;
        if (!hayCambio) return;
        instantanea();

        const filasTocadas = new Set();
        let escrituras = 0, rechazos = 0;

        const escribir = (r, c, valor) => {
            const col = COLUMNS[c];
            if (!col || col.locked) return;
            if (aplicarValor(rows[r], col.key, valor)) { escrituras++; filasTocadas.add(r); }
            else rechazos++;
        };

        if (destino.r1 > base.r1 || destino.r0 < base.r0) {
            const haciaAbajo = destino.r1 > base.r1;
            for (let c = base.c0; c <= base.c1; c++) {
                const col = COLUMNS[c];
                let valoresBase = [];
                for (let r = base.r0; r <= base.r1; r++) valoresBase.push(valorTextoCelda(rows[r], col));
                if (!haciaAbajo) valoresBase = valoresBase.slice().reverse();
                const cantidad = haciaAbajo ? destino.r1 - base.r1 : base.r0 - destino.r0;
                const serie = generarSerie(valoresBase, cantidad, ctrl, forzarCopia);
                for (let i = 0; i < cantidad; i++) {
                    escribir(haciaAbajo ? base.r1 + 1 + i : base.r0 - 1 - i, c, serie[i]);
                }
            }
        } else {
            const haciaDerecha = destino.c1 > base.c1;
            for (let r = base.r0; r <= base.r1; r++) {
                let valoresBase = [];
                for (let c = base.c0; c <= base.c1; c++) valoresBase.push(valorTextoCelda(rows[r], COLUMNS[c]));
                if (!haciaDerecha) valoresBase = valoresBase.slice().reverse();
                const cantidad = haciaDerecha ? destino.c1 - base.c1 : base.c0 - destino.c0;
                const serie = generarSerie(valoresBase, cantidad, ctrl, forzarCopia);
                for (let i = 0; i < cantidad; i++) {
                    escribir(r, haciaDerecha ? base.c1 + 1 + i : base.c0 - 1 - i, serie[i]);
                }
            }
        }

        if (escrituras === 0) {
            pilaDeshacer.pop();
            actualizarBotonesHistorial();
            if (rechazos) showToast("No se pudo rellenar: los valores no aplican a esas columnas ❌", "error");
            return;
        }
        filasTocadas.forEach(pintarFila);
        if (rechazos) showToast(`Relleno aplicado. ${rechazos} celda(s) se omitieron por ser de otro tipo`, "success");
        programarGuardadoAutomatico();
    }

    // Doble clic en la manija: rellena hacia abajo hasta donde llega el bloque
    // de datos vecino (misma heurística de Excel).
    function rellenarHastaFinDeDatos() {
        if (!sel || !puedeEditar()) return;
        const base = rangoNormalizado();
        const colRef = base.c0 > COL_INI ? base.c0 - 1 : base.c1 + 1;
        if (colRef < COL_INI || colRef > COL_FIN) return;
        const key = COLUMNS[colRef].key;
        let ultima = base.r1;
        while (ultima + 1 < rows.length) {
            const v = rows[ultima + 1][key];
            if (v === "" || v === null || v === undefined || v === 0) break;
            ultima++;
        }
        if (ultima === base.r1) { showToast("No hay datos vecinos hasta dónde rellenar", "error"); return; }
        const destino = { ...base, r1: ultima };
        aplicarRelleno(base, destino, false);
        sel = { r1: destino.r0, c1: destino.c0, r2: destino.r1, c2: destino.c1 };
        pintarSeleccion();
    }

    // -----------------------------------------------------------------
    // Copiar / cortar / pegar rangos (compatible con Excel)
    // -----------------------------------------------------------------
    function textoDeSeleccion() {
        const { r0, r1, c0, c1 } = rangoNormalizado();
        const lineas = [];
        for (let r = r0; r <= r1; r++) {
            const celdas = [];
            for (let c = c0; c <= c1; c++) celdas.push(valorTextoCelda(rows[r], COLUMNS[c]));
            lineas.push(celdas.join("\t"));
        }
        return lineas.join("\n");
    }

    // Solo se intercepta cuando el foco NO está en un campo ajeno a la tabla
    // (si no, escribir en "IPC %" empezaba a editar celdas).
    function eventoDeLaGrilla(e) {
        if (modalesAbiertos > 0) return false;
        const t = e.target;
        if (t && t.closest && t.closest("input, select, textarea") && !t.closest("#gridBody")) return false;
        return !!sel;
    }

    document.addEventListener("copy", (e) => {
        if (!eventoDeLaGrilla(e) || editingInput) return;
        e.preventDefault();
        e.clipboardData.setData("text/plain", textoDeSeleccion());
        rangoCopiado = { ...rangoNormalizado(), cortar: false };
        pintarCopiado();
    });

    document.addEventListener("cut", (e) => {
        if (!eventoDeLaGrilla(e) || editingInput) return;
        e.preventDefault();
        e.clipboardData.setData("text/plain", textoDeSeleccion());
        rangoCopiado = { ...rangoNormalizado(), cortar: puedeEditar() };
        pintarCopiado();
    });

    document.addEventListener("paste", (e) => {
        if (!eventoDeLaGrilla(e) || editingInput || !puedeEditar()) return;
        const texto = e.clipboardData.getData("text/plain");
        if (texto === null || texto === undefined) return;
        e.preventDefault();
        pegarTexto(texto);
    });

    function pegarTexto(texto) {
        let bloque = texto.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n").map(l => l.split("\t"));
        while (bloque.length > 1 && bloque[bloque.length - 1].every(v => v === "")) bloque.pop();
        if (bloque.length === 0) return;

        const destino = rangoNormalizado();
        const altoBloque = bloque.length, anchoBloque = Math.max(...bloque.map(f => f.length));
        const altoSel = destino.r1 - destino.r0 + 1, anchoSel = destino.c1 - destino.c0 + 1;

        // Como en Excel: si el destino es más grande y múltiplo del bloque, se
        // repite el bloque para cubrirlo; si no, se pega una sola vez.
        let filasDestino = altoBloque, colsDestino = anchoBloque;
        if (altoSel % altoBloque === 0 && anchoSel % anchoBloque === 0 && (altoSel > altoBloque || anchoSel > anchoBloque)) {
            filasDestino = altoSel; colsDestino = anchoSel;
        }

        instantanea();

        // Si hace falta, se agregan filas nuevas al final en vez de recortar.
        const filasNecesarias = destino.r0 + filasDestino - rows.length;
        let filasAgregadas = 0;
        for (let i = 0; i < filasNecesarias; i++) { rows.push(nuevaFilaVacia()); filasAgregadas++; }

        let escrituras = 0, rechazos = 0;
        for (let i = 0; i < filasDestino; i++) {
            for (let j = 0; j < colsDestino; j++) {
                const c = destino.c0 + j;
                if (c > COL_FIN) continue;
                const col = COLUMNS[c];
                if (col.locked) continue;
                const valor = (bloque[i % altoBloque][j % anchoBloque]) ?? "";
                if (aplicarValor(rows[destino.r0 + i], col.key, valor)) escrituras++;
                else rechazos++;
            }
        }

        // Cortar: se limpia el origen (solo si sigue siendo un rango de esta tabla)
        if (rangoCopiado && rangoCopiado.cortar) {
            for (let r = rangoCopiado.r0; r <= rangoCopiado.r1 && r < rows.length; r++) {
                for (let c = rangoCopiado.c0; c <= rangoCopiado.c1; c++) {
                    const dentroDestino = r >= destino.r0 && r < destino.r0 + filasDestino &&
                                          c >= destino.c0 && c < destino.c0 + colsDestino;
                    if (dentroDestino || COLUMNS[c].locked) continue;
                    aplicarValor(rows[r], COLUMNS[c].key, COLUMNS[c].type === "number" ? 0 : "");
                }
            }
            rangoCopiado = null;
        }

        if (escrituras === 0 && filasAgregadas === 0) {
            pilaDeshacer.pop();
            actualizarBotonesHistorial();
            showToast("Nada que pegar: los valores no aplican a esas columnas ❌", "error");
            return;
        }

        sel = { r1: destino.r0, c1: destino.c0,
                r2: Math.min(rows.length - 1, destino.r0 + filasDestino - 1),
                c2: Math.min(COL_FIN, destino.c0 + colsDestino - 1) };
        render();
        let msg = `Pegado: ${escrituras} celda(s)`;
        if (filasAgregadas) msg += ` · ${filasAgregadas} fila(s) nueva(s)`;
        if (rechazos) msg += ` · ${rechazos} omitida(s)`;
        showToast(msg + " ✅", rechazos ? "error" : "success");
        programarGuardadoAutomatico();
    }

    // -----------------------------------------------------------------
    // Teclado sobre la grilla
    // -----------------------------------------------------------------
    function borrarSeleccion() {
        if (!puedeEditar()) return;
        const { r0, r1, c0, c1 } = rangoNormalizado();
        instantanea();
        let cambios = 0;
        for (let r = r0; r <= r1; r++) {
            for (let c = c0; c <= c1; c++) {
                const col = COLUMNS[c];
                if (col.locked) continue;
                if (aplicarValor(rows[r], col.key, col.type === "number" ? 0 : "")) cambios++;
            }
            pintarFila(r);
        }
        if (!cambios) { pilaDeshacer.pop(); actualizarBotonesHistorial(); return; }
        programarGuardadoAutomatico();
    }

    // Ctrl+D / Ctrl+R: replica la primera fila (o columna) del rango en el resto.
    function rellenarDentroDeSeleccion(eje) {
        const { r0, r1, c0, c1 } = rangoNormalizado();
        if (eje === "abajo" && r1 === r0) return;
        if (eje === "derecha" && c1 === c0) return;
        const base = eje === "abajo" ? { r0, r1: r0, c0, c1 } : { r0, r1, c0, c1: c0 };
        aplicarRelleno(base, { r0, r1, c0, c1 }, false, true); // forzarCopia
    }

    // Ctrl+flecha: salta al borde del bloque de datos de esa columna/fila.
    function saltarABorde(r, c, dr, dc) {
        const key = COLUMNS[c].key;
        const vacio = v => v === "" || v === null || v === undefined || v === 0;
        if (dr !== 0) {
            let i = r;
            const partiaVacio = vacio(rows[i][key]);
            while (i + dr >= 0 && i + dr < rows.length) {
                const sig = vacio(rows[i + dr][key]);
                if (partiaVacio ? !sig : sig) { if (partiaVacio) i += dr; break; }
                i += dr;
            }
            return { r: i, c };
        }
        let j = c;
        while (j + dc >= COL_INI && j + dc <= COL_FIN) j += dc;
        return { r, c: j };
    }

    document.addEventListener("keydown", (e) => {
        if (editingInput) return;                 // el editor maneja sus propias teclas
        if (!eventoDeLaGrilla(e)) return;

        const ctrl = e.ctrlKey || e.metaKey;
        const { r1: r, c1: c } = sel;             // ancla = celda activa
        const focoR = sel.r2, focoC = sel.c2;

        if (ctrl && e.key.toLowerCase() === "z") { e.preventDefault(); e.shiftKey ? rehacer() : deshacer(); return; }
        if (ctrl && e.key.toLowerCase() === "y") { e.preventDefault(); rehacer(); return; }
        if (ctrl && e.key.toLowerCase() === "a") {
            e.preventDefault();
            sel = { r1: 0, c1: COL_INI, r2: rows.length - 1, c2: COL_FIN };
            pintarSeleccion();
            return;
        }
        if (ctrl && e.key.toLowerCase() === "d") { e.preventDefault(); rellenarDentroDeSeleccion("abajo"); return; }
        if (ctrl && e.key.toLowerCase() === "r") { e.preventDefault(); rellenarDentroDeSeleccion("derecha"); return; }
        if (ctrl && ["c", "x", "v"].includes(e.key.toLowerCase())) return; // los maneja copy/cut/paste

        const mover = (nr, nc) => { e.preventDefault(); seleccionar(nr, nc, e.shiftKey); };

        // Alt+↓ abre la lista desplegable de la celda (igual que en Excel)
        if (e.altKey && e.key === "ArrowDown") { e.preventDefault(); iniciarEdicion(r, c); return; }
        if (e.altKey) return;

        switch (e.key) {
            case "ArrowDown":
                if (ctrl) { const p = saltarABorde(focoR, focoC, 1, 0); mover(p.r, p.c); }
                else mover(e.shiftKey ? focoR + 1 : r + 1, e.shiftKey ? focoC : c);
                return;
            case "ArrowUp":
                if (ctrl) { const p = saltarABorde(focoR, focoC, -1, 0); mover(p.r, p.c); }
                else mover(e.shiftKey ? focoR - 1 : r - 1, e.shiftKey ? focoC : c);
                return;
            case "ArrowLeft":
                if (ctrl) { const p = saltarABorde(focoR, focoC, 0, -1); mover(p.r, p.c); }
                else mover(e.shiftKey ? focoR : r, e.shiftKey ? focoC - 1 : c - 1);
                return;
            case "ArrowRight":
                if (ctrl) { const p = saltarABorde(focoR, focoC, 0, 1); mover(p.r, p.c); }
                else mover(e.shiftKey ? focoR : r, e.shiftKey ? focoC + 1 : c + 1);
                return;
            case "Tab":
                e.preventDefault(); seleccionar(r, c + (e.shiftKey ? -1 : 1)); return;
            case "Enter":
                e.preventDefault(); seleccionar(r + (e.shiftKey ? -1 : 1), c); return;
            case "F2":
                e.preventDefault(); iniciarEdicion(r, c); return;
            case "Home":
                mover(ctrl ? 0 : r, COL_INI); return;
            case "End":
                mover(ctrl ? rows.length - 1 : r, COL_FIN); return;
            case "PageDown":
                mover(e.shiftKey ? focoR + 20 : r + 20, e.shiftKey ? focoC : c); return;
            case "PageUp":
                mover(e.shiftKey ? focoR - 20 : r - 20, e.shiftKey ? focoC : c); return;
            case "Delete":
            case "Backspace":
                e.preventDefault(); borrarSeleccion(); return;
            case "Escape":
                rangoCopiado = null; pintarCopiado(); return;
        }

        if (!ctrl && !e.altKey && e.key.length === 1) {
            e.preventDefault();
            iniciarEdicion(r, c, e.key === " " ? "" : e.key);
        }
    });

    $("gridBody").addEventListener("dblclick", (e) => {
        const td = e.target.closest("td.editable");
        if (!td || td.classList.contains("editing")) return;
        iniciarEdicion(parseInt(td.dataset.rowIndex, 10), parseInt(td.dataset.colIndex, 10), null, e.clientX);
    });

    // -----------------------------------------------------------------
    // Checkboxes IPC / acciones de fila
    // -----------------------------------------------------------------
    $("gridHeaderRow").addEventListener("change", (e) => {
        if (e.target.id !== "checkAllIPC") return;
        rows.forEach(r => r._checked = e.target.checked);
        rows.forEach((_, i) => pintarFila(i));
    });
    $("gridBody").addEventListener("change", (e) => {
        if (!e.target.classList.contains("row-check")) return;
        const rowIndex = parseInt(e.target.closest("td").dataset.rowIndex, 10);
        rows[rowIndex]._checked = e.target.checked;
        syncCheckAllState();
    });

    let filaAEliminar = null;
    $("gridBody").addEventListener("click", (e) => {
        if (!puedeEditar()) return;
        if (e.target.classList.contains("dupBtn")) {
            const rowIndex = parseInt(e.target.closest("td").dataset.rowIndex, 10);
            instantanea();
            const nueva = { ...rows[rowIndex] };
            MESES.forEach(m => nueva[m] = 0);
            nueva.total = 0;
            nueva._checked = false;
            delete nueva.id;
            rows.splice(rowIndex + 1, 0, nueva);
            render();
            seleccionar(rowIndex + 1, COL_INI);
            const tr = document.querySelector(`#gridBody tr[data-row-index="${rowIndex + 1}"]`);
            if (tr) { tr.classList.add("blink"); setTimeout(() => tr.classList.remove("blink"), 1800); }
            showToast("Fila duplicada 📑", "success");
            programarGuardadoAutomatico();
        }
        if (e.target.classList.contains("delBtn")) {
            filaAEliminar = parseInt(e.target.closest("td").dataset.rowIndex, 10);
            abrirModal("modalEliminar");
        }
    });
    $("confirmEliminarBtn")?.addEventListener("click", () => {
        if (filaAEliminar !== null) {
            instantanea();
            rows.splice(filaAEliminar, 1);
            limitarSeleccion();
            render();
            showToast("Fila eliminada ❌", "error");
            filaAEliminar = null;
            programarGuardadoAutomatico();
        }
        cerrarModal("modalEliminar");
    });

    // -----------------------------------------------------------------
    // Agregar fila vacía
    // -----------------------------------------------------------------
    function nuevaFilaVacia() {
        const nueva = { centro_tra: "", nombre_cen: "", codcosto: "", responsable: "",
            cuenta: "", cuenta_mayor: "", detalle_cuenta: "", sede_distribucion: "", proveedor: "",
            comentario: "", total: 0, _checked: false };
        MESES.forEach(m => nueva[m] = 0);
        return nueva;
    }
    $("agregarFilaBtn")?.addEventListener("click", () => {
        if (!puedeEditar()) return;
        instantanea();
        rows.push(nuevaFilaVacia());
        render();
        seleccionar(rows.length - 1, COL_INI);
        showToast("Fila agregada ✅", "success");
        programarGuardadoAutomatico();
    });

    // -----------------------------------------------------------------
    // Calcular IPC sobre filas seleccionadas
    // -----------------------------------------------------------------
    $("calcularIPCBtn")?.addEventListener("click", () => {
        if (!puedeEditar()) return;
        const valor = $("ipcInput").value;
        if (!valor || isNaN(valor)) { showToast("Debe ingresar un número válido ❌", "error"); return; }
        const factor = 1 + (parseFloat(valor) / 100);
        const marcadas = rows.filter(r => r._checked);
        if (marcadas.length === 0) { showToast("Selecciona al menos una fila ❌", "error"); return; }
        instantanea();
        marcadas.forEach(row => {
            MESES.forEach(m => { row[m] = Math.round((parseFloat(row[m]) || 0) * factor); });
            recalcularTotal(row);
        });
        rows.forEach((_, i) => pintarFila(i));
        showToast("IPC aplicado a filas seleccionadas 📈", "success");
        programarGuardadoAutomatico();
    });

    // -----------------------------------------------------------------
    // Exportar a Excel (ExcelJS: listas desplegables + autosuma)
    // -----------------------------------------------------------------
    function listaCuentasParaPlantilla() {
        return Object.keys(mapaCuentaMayor)
            .filter(o => !EXCLUIR_CUENTAS.includes(o))
            .sort((a, b) => a.localeCompare(b, 'es', { numeric: true }))
            .map(o => `${o} - ${mapaCuentaMayor[o] || ""}`);
    }

    async function exportarExcel() {
        if (Object.keys(mapaCuentaMayor).length === 0) {
            showToast("Las cuentas contables aún se están cargando, intenta de nuevo en un momento ⏳", "error");
            return;
        }
        const cols = COLUMNS.filter(c => c.type !== "check" && c.type !== "acciones" && c.key !== "cuenta");

        const wb = new ExcelJS.Workbook();
        const hoja = wb.addWorksheet("Presupuesto");
        const listas = wb.addWorksheet("Listas");
        listas.state = "hidden";

        const centros = Object.keys(OPCIONES_NOMBRE_CENTRO);
        const cuentas = listaCuentasParaPlantilla();
        centros.forEach((c, i) => { listas.getCell(`A${i + 1}`).value = c; });
        cuentas.forEach((c, i) => { listas.getCell(`B${i + 1}`).value = c; });
        wb.definedNames.add(`Listas!$A$1:$A$${centros.length}`, "ListaCentros");
        wb.definedNames.add(`Listas!$B$1:$B$${cuentas.length}`, "ListaCuentas");

        hoja.addRow(cols.map(c => c.label));
        hoja.getRow(1).eachCell(c => {
            c.font = { bold: true, color: { argb: "FFFFFFFF" } };
            c.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF1F3A93" } };
        });

        const idxNombre = cols.findIndex(c => c.key === "nombre_cen") + 1;
        const idxCuentaMayor = cols.findIndex(c => c.key === "cuenta_mayor") + 1;
        const idxMesInicio = cols.findIndex(c => c.key === MESES[0]) + 1;
        const idxMesFin = cols.findIndex(c => c.key === MESES[MESES.length - 1]) + 1;
        const idxTotal = cols.findIndex(c => c.key === "total") + 1;

        function aplicarListasYAutosuma(filaExcel) {
            const numFila = filaExcel.number;
            if (idxNombre > 0) {
                filaExcel.getCell(idxNombre).dataValidation = {
                    type: "list", allowBlank: true, formulae: ["ListaCentros"],
                    showErrorMessage: true, errorTitle: "Valor inválido",
                    error: "Selecciona un valor de la lista desplegable.",
                };
            }
            if (idxCuentaMayor > 0) {
                filaExcel.getCell(idxCuentaMayor).dataValidation = {
                    type: "list", allowBlank: true, formulae: ["ListaCuentas"],
                    showErrorMessage: true, errorTitle: "Valor inválido",
                    error: "Selecciona un valor de la lista desplegable.",
                };
            }
            if (idxTotal > 0) {
                filaExcel.getCell(idxTotal).value = {
                    formula: `SUM(${colLetter(idxMesInicio)}${numFila}:${colLetter(idxMesFin)}${numFila})`,
                };
            }
        }

        rows.forEach(row => {
            const valores = cols.map(c => {
                if (c.key === "cuenta_mayor") {
                    return row.cuenta ? `${row.cuenta} - ${row.cuenta_mayor || ""}` : (row.cuenta_mayor || "");
                }
                if (c.key === "total") return null; // se llena abajo con fórmula
                return row[c.key] ?? "";
            });
            aplicarListasYAutosuma(hoja.addRow(valores));
        });

        for (let j = 0; j < EXPORT_FILAS_EXTRA; j++) {
            aplicarListasYAutosuma(hoja.addRow(new Array(cols.length).fill("")));
        }

        hoja.columns.forEach(col => { col.width = 22; });
        await bloquearFilaEncabezado(hoja);

        const buffer = await wb.xlsx.writeBuffer();
        descargarBuffer(buffer, `${OPC.nombreExport}.xlsx`);
    }
    $("exportarExcelBtn")?.addEventListener("click", exportarExcel);

    // -----------------------------------------------------------------
    // Plantilla Excel para subir datos
    // -----------------------------------------------------------------
    async function descargarPlantillaExcel() {
        if (Object.keys(mapaCuentaMayor).length === 0) {
            showToast("Las cuentas contables aún se están cargando, intenta de nuevo en un momento ⏳", "error");
            return;
        }
        const wb = new ExcelJS.Workbook();
        const hoja = wb.addWorksheet("Plantilla");
        const listas = wb.addWorksheet("Listas");
        listas.state = "hidden";

        const centros = Object.keys(OPCIONES_NOMBRE_CENTRO);
        const cuentas = listaCuentasParaPlantilla();
        centros.forEach((c, i) => { listas.getCell(`A${i + 1}`).value = c; });
        cuentas.forEach((c, i) => { listas.getCell(`B${i + 1}`).value = c; });
        wb.definedNames.add(`Listas!$A$1:$A$${centros.length}`, "ListaCentros");
        wb.definedNames.add(`Listas!$B$1:$B$${cuentas.length}`, "ListaCuentas");

        hoja.addRow(PLANTILLA_HEADERS);
        hoja.getRow(1).eachCell(c => {
            c.font = { bold: true, color: { argb: "FFFFFFFF" } };
            c.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF1F3A93" } };
        });

        for (let i = 2; i <= PLANTILLA_FILAS_VACIAS + 1; i++) {
            hoja.getCell(`A${i}`).dataValidation = {
                type: "list", allowBlank: true, formulae: ["ListaCentros"],
                showErrorMessage: true, errorTitle: "Valor inválido",
                error: "Selecciona un valor de la lista desplegable.",
            };
            hoja.getCell(`B${i}`).dataValidation = {
                type: "list", allowBlank: true, formulae: ["ListaCuentas"],
                showErrorMessage: true, errorTitle: "Valor inválido",
                error: "Selecciona un valor de la lista desplegable.",
            };
            hoja.getCell(`${colLetter(COL_TOTAL)}${i}`).value = {
                formula: `SUM(${colLetter(COL_MES_INICIO)}${i}:${colLetter(COL_MES_FIN)}${i})`,
            };
        }
        hoja.columns.forEach(col => { col.width = 22; });
        await bloquearFilaEncabezado(hoja);

        const buffer = await wb.xlsx.writeBuffer();
        descargarBuffer(buffer, `plantilla_presupuesto_${OPC.sede}.xlsx`);
    }
    $("descargarPlantillaBtn")?.addEventListener("click", descargarPlantillaExcel);

    // -----------------------------------------------------------------
    // Importar plantilla
    // -----------------------------------------------------------------
    let archivoPlantillaPendiente = null;

    $("importarPlantillaBtn")?.addEventListener("click", () => $("importarPlantillaInput").click());
    $("importarPlantillaInput")?.addEventListener("change", (e) => {
        const file = e.target.files[0];
        e.target.value = "";
        if (!file) return;
        archivoPlantillaPendiente = file;
        abrirModal("modalConfirmarImport");
    });
    $("confirmImportBtn")?.addEventListener("click", async () => {
        cerrarModal("modalConfirmarImport");
        const file = archivoPlantillaPendiente;
        archivoPlantillaPendiente = null;
        if (file) await procesarPlantillaImportada(file);
    });

    function encabezadosValidos(hojaExcel) {
        const filasCrudas = XLSX.utils.sheet_to_json(hojaExcel, { header: 1, defval: "" });
        const encabezados = (filasCrudas[0] || []).map(h => String(h).trim());
        if (encabezados.length < PLANTILLA_HEADERS.length) return false;
        return PLANTILLA_HEADERS.every((esperado, i) => encabezados[i] === esperado);
    }

    async function procesarPlantillaImportada(file) {
        const buffer = await file.arrayBuffer();
        const wbLeida = XLSX.read(buffer, { type: "array" });
        const hoja = wbLeida.Sheets[wbLeida.SheetNames[0]];

        if (!encabezadosValidos(hoja)) {
            showToast("El archivo no tiene las columnas de la plantilla (nombres, orden o cantidad de columnas distintos) ❌", "error");
            return;
        }

        const filas = XLSX.utils.sheet_to_json(hoja, { defval: "" });
        const nuevasFilas = [];
        const errores = [];

        filas.forEach((fila, idx) => {
            const numeroFila = idx + 2;
            const nombreCen = String(fila["Nombre asignación del gasto"] || "").trim();
            const cuentaMayorRaw = String(fila["Cuenta Mayor"] || "").trim();
            const detalleCuenta = String(fila["Detalle Cuenta"] || "").trim();
            const comentario = String(fila["Comentario"] || "").trim();
            const valoresMesesCrudos = MESES.map(m => fila[m[0].toUpperCase() + m.slice(1)]);
            const filaVacia = !nombreCen && !cuentaMayorRaw && !detalleCuenta && !comentario &&
                valoresMesesCrudos.every(v => v === "" || v === null || v === undefined);
            if (filaVacia) return;

            const codigoCuenta = cuentaMayorRaw.split(" - ")[0].trim();
            const centroValido = OPCIONES_NOMBRE_CENTRO[nombreCen];
            const cuentaValida = mapaCuentaMayor[codigoCuenta];

            if (!centroValido) {
                errores.push({ fila: numeroFila, nombreCen, cuentaMayorRaw,
                    motivo: `"${nombreCen || "(vacío)"}" no es un centro válido` });
                return;
            }
            if (cuentaValida === undefined) {
                errores.push({ fila: numeroFila, nombreCen, cuentaMayorRaw,
                    motivo: `"${codigoCuenta || "(vacío)"}" no es una cuenta contable válida` });
                return;
            }

            const esAdmin = nombreCen.toUpperCase() === "ADMINISTRACIÓN";
            if (esAdmin && !codigoCuenta.startsWith("51")) {
                errores.push({ fila: numeroFila, nombreCen, cuentaMayorRaw,
                    motivo: codigoCuenta.startsWith("54")
                        ? "Administración no admite cuentas que inicien con 54"
                        : "Administración solo admite cuentas que inicien con 51" });
                return;
            }

            let mesInvalido = null;
            const valoresMeses = {};
            MESES.forEach((m, i) => {
                const resultado = validarValorEntero(valoresMesesCrudos[i]);
                if (!resultado.valido && !mesInvalido) mesInvalido = m[0].toUpperCase() + m.slice(1);
                valoresMeses[m] = resultado.valor;
            });
            if (mesInvalido) {
                errores.push({ fila: numeroFila, nombreCen, cuentaMayorRaw,
                    motivo: `La columna "${mesInvalido}" debe ser un número entero, sin comas ni puntos` });
                return;
            }

            const nueva = {
                centro_tra: centroValido.centro,
                nombre_cen: nombreCen,
                codcosto: centroValido.codigoCosto,
                responsable: "",
                cuenta: codigoCuenta,
                cuenta_mayor: cuentaValida,
                detalle_cuenta: detalleCuenta,
                sede_distribucion: "",
                proveedor: "",
                comentario: comentario,
                _checked: false,
                ...valoresMeses,
            };
            recalcularTotal(nueva);
            nuevasFilas.push(nueva);
        });

        if (errores.length > 0) {
            mostrarModalErroresImport(errores);
            showToast("La plantilla tiene errores y no se importó ningún dato ❌", "error");
            return;
        }
        if (nuevasFilas.length === 0) {
            showToast("No se encontraron filas con datos para importar", "error");
            return;
        }

        instantanea();   // la importación también se puede deshacer con Ctrl+Z
        rows = nuevasFilas;
        sel = null;
        render();
        seleccionar(0, COL_INI);
        showToast(`Datos anteriores reemplazados: ${nuevasFilas.length} fila(s) importada(s) ✅`, "success");
        programarGuardadoAutomatico();
    }

    function mostrarModalErroresImport(errores) {
        const tbody = $("importErroresBody");
        tbody.innerHTML = errores.map(err => `
            <tr>
                <td>${err.fila}</td>
                <td>${escaparHtml(err.nombreCen || "—")}</td>
                <td>${escaparHtml(err.cuentaMayorRaw || "—")}</td>
                <td>${escaparHtml(err.motivo)}</td>
            </tr>
        `).join("");
        abrirModal("modalImportErrores");
    }

    // -----------------------------------------------------------------
    // Manual, atajos, redimensionar y expandir
    // -----------------------------------------------------------------
    $("verManualBtn")?.addEventListener("click", () => abrirModal("manualModal"));
    $("cerrarManualBtn")?.addEventListener("click", () => cerrarModal("manualModal"));
    $("verAtajosBtn")?.addEventListener("click", () => abrirModal("modalAtajos"));
    $("deshacerBtn")?.addEventListener("click", deshacer);
    $("rehacerBtn")?.addEventListener("click", rehacer);

    (function initResize() {
        const container = $("gridContainer");
        const handle = $("resizeHandle");
        let isResizing = false, startY, startHeight;

        handle?.addEventListener("mousedown", (e) => {
            isResizing = true; startY = e.clientY;
            startHeight = parseInt(getComputedStyle(container).height, 10);
            document.body.style.cursor = "ns-resize"; document.body.style.userSelect = "none";
        });
        document.addEventListener("mousemove", (e) => {
            if (!isResizing) return;
            const newHeight = startHeight + (e.clientY - startY);
            if (newHeight > 150) container.style.height = `${newHeight}px`;
        });
        document.addEventListener("mouseup", () => {
            if (!isResizing) return;
            isResizing = false; document.body.style.cursor = ""; document.body.style.userSelect = "";
            pintarSeleccion();
        });

        let expanded = false, previousHeight = container.style.height;
        $("expandBtn")?.addEventListener("click", () => {
            const btn = $("expandBtn");
            if (!expanded) {
                previousHeight = container.style.height;
                container.style.height = "auto";
                btn.textContent = "Colapsar"; expanded = true;
            } else {
                container.style.height = previousHeight || "65vh";
                btn.textContent = "Expandir"; expanded = false;
            }
            pintarSeleccion();
        });
    })();

    // -----------------------------------------------------------------
    // Arranque
    // -----------------------------------------------------------------
    const cont = $("gridContainer");
    cont.setAttribute("tabindex", "0");
    cont.style.outline = "none";
    renderHeader();
    actualizarBotonesHistorial();
    const listo = Promise.all([cargarOpcionesCuenta(), cargarDatos()]);

    // API pública para la pantalla que la incrusta
    return {
        listo,
        vaciarColaDeGuardado,
        recargar: cargarDatos,
        filas: () => rows,
        hayPendientes: () => !!(autoSaveTimer || autoSaveEnCurso),
        async cambiarFuente(urlObtener, urlGuardar) {
            await vaciarColaDeGuardado();
            OPC.urlObtener = urlObtener;
            if (urlGuardar) OPC.urlGuardar = urlGuardar;
            await cargarDatos();
        },
    };
}

global.GrillaPresupuesto = { init, abrirModal, cerrarModal, showToast, apiPost };

})(window);