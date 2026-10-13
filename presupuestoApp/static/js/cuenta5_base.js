/* cuenta5.js — tabla HTML nativa, sin DataTables */

"use strict";

// ─── Utilidades ───────────────────────────────────────────────
function getCookie(name) {
  for (const c of document.cookie.split(";")) {
    const [k, v] = c.trim().split("=");
    if (k === name) return decodeURIComponent(v);
  }
  return null;
}

function fmt(value) {
  if (value === null || value === undefined || value === "") return "";
  const n = Number(value);
  if (!isNaN(n) && value !== "") return new Intl.NumberFormat("es-ES").format(n);
  return value;
}

// ─── Valor usado por los filtros (permite agrupar) ───────────
// La fecha se filtra por MES ("Enero 2026"), igual que en Presupuestado.
const MESES_LARGOS = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                      "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];

function monthKey(v) {
  if (v === null || v === undefined || v === "") return "";
  const m = String(v).match(/^(\d{4})-(\d{2})/);
  return m ? `${m[1]}-${m[2]}` : String(v);
}
function monthLabel(key) {
  const m = String(key).match(/^(\d{4})-(\d{2})$/);
  return m ? `${MESES_LARGOS[+m[2] - 1]} ${m[1]}` : (key === "" ? "(Vacío)" : key);
}

// Columnas con agrupación especial
const FILTER_VALUE_GETTERS = { mcnfecha: monthKey };

function getFilterValue(row, col) {
  const g = FILTER_VALUE_GETTERS[col];
  const raw = row[col];
  if (g) return g(raw);
  return raw === null || raw === undefined ? "" : String(raw);
}

function showToast(msg, type = "success", duration = 3000) {
  const c = document.getElementById("toastContainer");
  const t = document.createElement("div");
  t.className = `c5-toast c5-toast-${type}`;
  t.textContent = msg;
  c.appendChild(t);
  requestAnimationFrame(() => t.classList.add("c5-toast-show"));
  setTimeout(() => {
    t.classList.remove("c5-toast-show");
    setTimeout(() => t.remove(), 400);
  }, duration);
}

function openModal(id)  { document.getElementById(id).style.display = "flex"; }
function closeModal(id) { document.getElementById(id).style.display = "none"; }

// ─── Columnas ─────────────────────────────────────────────────
const COLUMNS = [
  { key: "mcncuenta",  label: "MCNCUENTA",  num: false },
  { key: "mcnfecha",   label: "MCNFECHA",   num: false },
  { key: "mcntipodoc", label: "MCNTIPODOC", num: false },
  { key: "mcnnumedoc", label: "MCNNUMEDOC", num: true  },
  { key: "mcnvincula", label: "MCNVINCULA", num: false },
  { key: "vinnombre",  label: "VINNOMBRE",  num: false },
  { key: "mcnsucvin",  label: "MCNSUCVIN",  num: false },
  { key: "saldoant",   label: "SALDOANT",   num: true  },
  { key: "mcnvaldebi", label: "MCNVALDEBI", num: true  },
  { key: "mcnvalcred", label: "MCNVALCRED", num: true  },
  { key: "saldonew",   label: "SALDONEW",   num: true  },
  { key: "mcnsucurs",  label: "MCNSUCURS",  num: false },
  { key: "mcnccosto",  label: "MCNCCOSTO",  num: false },
  { key: "mcndestino", label: "MCNDESTINO", num: false },
  { key: "mcndetalle", label: "MCNDETALLE", num: false },
  { key: "mcnzona",    label: "MCNZONA",    num: false },
  { key: "cconombre",  label: "CCONOMBRE",  num: false },
  { key: "dnonombre",  label: "DNONOMBRE",  num: false },
  { key: "zonnombre",  label: "ZONNOMBRE",  num: false },
  { key: "mcnempresa", label: "MCNEMPRESA", num: true  },
  { key: "mcnclase",   label: "MCNCLASE",   num: false },
  { key: "mcnvinkey",  label: "MCNVINKEY",  num: false },
  { key: "tpreg",      label: "TPREG",      num: true  },
  { key: "ctanombre",  label: "CTANOMBRE",  num: false },
  { key: "docdetalle", label: "DOCDETALLE", num: false },
  { key: "infdetalle", label: "INFDETALLE", num: false },
];

// Columnas que tienen filtro Excel (deben coincidir con data-filter en el HTML)
const FILTER_COLS = ["mcncuenta", "mcnfecha", "mcnccosto", "mcndestino", "mcnzona", "ctanombre"];

// ─── Estado global ────────────────────────────────────────────
let allRows          = [];  // todos los registros cargados del servidor
let filteredRows     = [];  // resultado tras búsqueda + filtros Excel
let currentPage      = 1;
let perPage          = 50;
let sortCol          = null;
let sortDir          = "asc";
let searchQuery      = "";

// ─── Arranque ─────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  bindUI();
  loadData();

  // Escuchar evento del módulo de filtros Excel (del template)
  document.addEventListener("c5:filtros-aplicados", () => {
    applyFilterAndRender();
  });
});

// ─── Cargar datos ─────────────────────────────────────────────
function loadData() {
  const tbody = document.getElementById("c5Tbody");
  tbody.innerHTML = `<tr class="c5-loading-row"><td colspan="28">Cargando datos…</td></tr>`;

  const formData = new FormData();
  formData.append("draw", 1);
  formData.append("start", 0);
  formData.append("length", 999999);
  formData.append("search[value]", "");

  return fetch(url_obtener_cuenta5_base, {
    method: "POST",
    headers: { "X-CSRFToken": getCookie("csrftoken") },
    body: formData,
  })
    .then(r => r.json())
    .then(json => {
      allRows = json.data || [];
      feedFilterValues();       // <── cargar valores únicos en los dropdowns
      applyFilterAndRender();
    })
    .catch(err => {
      tbody.innerHTML = `<tr><td colspan="28" class="c5-error">Error al cargar datos.</td></tr>`;
      console.error(err);
    });
}

// ─── Alimentar valores únicos en el módulo C5Filters ──────────
function feedFilterValues() {
  if (!window.C5Filters) return;

  FILTER_COLS.forEach(col => {
    // Recoger todos los valores únicos no nulos de esa columna
    const unique = [...new Set(
      allRows
        .filter(row => row[col] !== null && row[col] !== undefined)
        .map(row => getFilterValue(row, col))
    )];
    let labels = null;
    if (FILTER_VALUE_GETTERS[col] === monthKey) {
      labels = {};
      unique.forEach(v => { labels[v] = monthLabel(v); });
    }
    C5Filters.setValues(col, unique, labels);
  });
}

// ─── Filtrar + ordenar + renderizar ───────────────────────────
function applyFilterAndRender() {
  const q = searchQuery.trim().toLowerCase();

  // 1. Obtener filtros Excel activos
  const excelFilters = window.C5Filters ? C5Filters.getParams() : {};
  // excelFilters = { mcncuenta: ["510506","510507"], mcnzona: ["NORTE"], ... }

  // 2. Filtrar sobre allRows
  filteredRows = allRows.filter(row => {
    // 2a. Búsqueda libre (searchInput)
    if (q) {
      const matchSearch = COLUMNS.some(col => {
        const v = row[col.key];
        return v !== null && v !== undefined && String(v).toLowerCase().includes(q);
      });
      if (!matchSearch) return false;
    }

    // 2b. Filtros Excel — cada columna activa debe coincidir
    for (const [col, allowed] of Object.entries(excelFilters)) {
      if (!allowed || allowed.length === 0) continue;
      if (!allowed.includes(getFilterValue(row, col))) return false;
    }

    return true;
  });

  // 3. Ordenamiento
  if (sortCol !== null) {
    const col = COLUMNS[sortCol];
    filteredRows.sort((a, b) => {
      let va = a[col.key], vb = b[col.key];
      if (col.num) {
        va = parseFloat(va) || 0;
        vb = parseFloat(vb) || 0;
      } else {
        va = String(va ?? "").toLowerCase();
        vb = String(vb ?? "").toLowerCase();
      }
      if (va < vb) return sortDir === "asc" ? -1 : 1;
      if (va > vb) return sortDir === "asc" ?  1 : -1;
      return 0;
    });
  }

  currentPage = 1;
  renderTable();
  renderPagination();
  renderInfo();
}

// ─── Renderizar filas de la página actual ─────────────────────
function renderTable() {
  const tbody = document.getElementById("c5Tbody");
  const start = (currentPage - 1) * perPage;
  const slice = filteredRows.slice(start, start + perPage);

  if (slice.length === 0) {
    tbody.innerHTML = `<tr><td colspan="28" class="c5-empty">Sin resultados.</td></tr>`;
    syncCheckAll();
    return;
  }

  const frag = document.createDocumentFragment();
  slice.forEach((row, pageIdx) => {
    const globalIdx = start + pageIdx;
    const tr = document.createElement("tr");
    tr.dataset.idx = globalIdx;

    // Checkbox
    const tdCheck = document.createElement("td");
    tdCheck.className = "c5-col-check";
    const chk = document.createElement("input");
    chk.type = "checkbox";
    chk.className = "row-check";
    tdCheck.appendChild(chk);
    tr.appendChild(tdCheck);

    // Datos
    COLUMNS.forEach(col => {
      const td = document.createElement("td");
      td.className = col.num ? "c5-num" : "";
      td.textContent = col.num ? fmt(row[col.key]) : (row[col.key] ?? "");
      tr.appendChild(td);
    });

    tr.addEventListener("click", e => {
      if (e.target.tagName === "INPUT" || e.target.tagName === "BUTTON") return;
      document.querySelectorAll("#c5Tbody tr.c5-active").forEach(r => r.classList.remove("c5-active"));
      tr.classList.add("c5-active");
    });

    frag.appendChild(tr);
  });

  tbody.innerHTML = "";
  tbody.appendChild(frag);
  syncCheckAll();
  renderTotals();
}

// ─── Paginación ───────────────────────────────────────────────
function renderPagination() {
  const total = Math.ceil(filteredRows.length / perPage) || 1;
  const el = document.getElementById("c5Pagination");
  el.innerHTML = "";

  const mkBtn = (label, page, disabled = false, active = false) => {
    const b = document.createElement("button");
    b.className = "c5-page-btn" + (active ? " c5-page-active" : "");
    b.textContent = label;
    b.disabled = disabled;
    b.addEventListener("click", () => {
      currentPage = page;
      renderTable();
      renderPagination();
      renderInfo();
    });
    return b;
  };

  el.appendChild(mkBtn("«", 1, currentPage === 1));
  el.appendChild(mkBtn("‹", currentPage - 1, currentPage === 1));

  const range = buildPageRange(currentPage, total);
  range.forEach(p => {
    if (p === "…") {
      const span = document.createElement("span");
      span.className = "c5-page-ellipsis";
      span.textContent = "…";
      el.appendChild(span);
    } else {
      el.appendChild(mkBtn(p, p, false, p === currentPage));
    }
  });

  el.appendChild(mkBtn("›", currentPage + 1, currentPage === total));
  el.appendChild(mkBtn("»", total, currentPage === total));
}

function buildPageRange(cur, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const pages = [];
  pages.push(1);
  if (cur > 3) pages.push("…");
  for (let p = Math.max(2, cur - 1); p <= Math.min(total - 1, cur + 1); p++) pages.push(p);
  if (cur < total - 2) pages.push("…");
  pages.push(total);
  return pages;
}

function renderInfo() {
  const start = (currentPage - 1) * perPage + 1;
  const end   = Math.min(currentPage * perPage, filteredRows.length);
  const total = filteredRows.length;
  const el = document.getElementById("c5Info");
  el.textContent = total === 0
    ? "Sin registros"
    : `${new Intl.NumberFormat("es-ES").format(start)}–${new Intl.NumberFormat("es-ES").format(end)} de ${new Intl.NumberFormat("es-ES").format(total)} registros`;
}
// ─── Fila de totales ──────────────────────────────────────────
function renderTotals() {
  const row = document.getElementById("c5TotalRow");
  if (!row) return;

  // Columnas numéricas (índices en COLUMNS)
  const numCols = new Set(COLUMNS.filter(c => c.num).map(c => c.key));

  // Sumar sobre TODOS los filteredRows (no solo la página visible)
  const sums = {};
  numCols.forEach(k => { sums[k] = 0; });
  filteredRows.forEach(r => {
    numCols.forEach(k => {
      const v = parseFloat(r[k]);
      if (!isNaN(v)) sums[k] += v;
    });
  });

  const cells = [];

  // Celda checkbox (vacía)
  cells.push(`<td></td>`);

  // Celda acciones → etiqueta "TOTAL"
  cells.push(`<td class="c5-total-label">TOTAL</td>`);

  // Una celda por columna
  COLUMNS.forEach(col => {
    if (col.num) {
      cells.push(`<td class="c5-num">${fmt(sums[col.key].toFixed(2))}</td>`);
    } else {
      cells.push(`<td></td>`);
    }
  });

  row.innerHTML = cells.join("");
}
// ─── Ordenamiento por columna ─────────────────────────────────
function bindSortHeaders() {
  document.querySelectorAll("#c5Table thead th[data-col]").forEach((th, idx) => {
    th.classList.add("c5-sortable");
    th.addEventListener("click", e => {
      // Ignorar clics sobre el icono de filtro
      if (e.target.classList.contains("c5-filter-icon")) return;

      // 1er clic: ascendente ↑ · 2º clic: descendente ↓ · 3er clic: orden original (sin ordenar)
      if (sortCol !== idx)        { sortCol = idx; sortDir = "asc"; }
      else if (sortDir === "asc") { sortDir = "desc"; }
      else                        { sortCol = null; sortDir = "asc"; }
      document.querySelectorAll("th[data-col]").forEach(h => h.removeAttribute("data-sort"));
      if (sortCol !== null) th.dataset.sort = sortDir;
      applyFilterAndRender();
    });
  });
}

// ─── Checkboxes ───────────────────────────────────────────────
function syncCheckAll() {
  const all  = document.querySelectorAll(".row-check");
  const chkd = document.querySelectorAll(".row-check:checked");
  const master = document.getElementById("checkAll");
  if (!all.length)              { master.checked = false; master.indeterminate = false; return; }
  if (chkd.length === 0)        { master.checked = false; master.indeterminate = false; }
  else if (chkd.length === all.length) { master.checked = true; master.indeterminate = false; }
  else                          { master.checked = false; master.indeterminate = true; }
}

// Subida por lotes con ventana de progreso (static/js/carga_lotes.js)
function enviarPorLotes(valid, url, loader) {
  return CargaLotes.enviar(valid, url, { loader, etiqueta: "Cuenta 5" });
}

// ─── Enlazar todos los eventos de UI ─────────────────────────
function bindUI() {
  bindSortHeaders();

  // Búsqueda libre
  let searchTimer;
  document.getElementById("searchInput").addEventListener("input", e => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      searchQuery = e.target.value;
      applyFilterAndRender();
    }, 250);
  });

  // Filas por página
  document.getElementById("perPageSelect").addEventListener("change", e => {
    perPage = parseInt(e.target.value, 10);
    applyFilterAndRender();
  });

  // Checkbox maestro
  document.getElementById("checkAll").addEventListener("change", e => {
    document.querySelectorAll(".row-check").forEach(c => c.checked = e.target.checked);
  });

  // Delegación checkboxes individuales
  document.getElementById("c5Tbody").addEventListener("change", e => {
    if (e.target.classList.contains("row-check")) syncCheckAll();
  });

  // ── Borrar cuenta completa ─────────────────────────────────
  document.getElementById("btnBorrar").addEventListener("click", () => openModal("modalEliminarCuenta"));
  document.getElementById("cancelEliminarCuenta").addEventListener("click", () => closeModal("modalEliminarCuenta"));
  document.getElementById("confirmEliminarCuenta").addEventListener("click", () => {
    closeModal("modalEliminarCuenta");
    fetch(url_borrar_cuenta5_base, {
      method: "POST",
      headers: { "X-CSRFToken": getCookie("csrftoken") },
    })
      .then(r => r.json())
      .then(() => {
        allRows = [];
        if (window.C5Filters) C5Filters.clear();
        feedFilterValues();
        applyFilterAndRender();
        showToast("Presupuesto eliminado correctamente", "success");
      })
      .catch(() => showToast("Error al borrar", "error"));
  });

  // ── Exportar plantilla vacía ───────────────────────────────
  document.getElementById("exportarPlantillaBtn").addEventListener("click", () => {
    const headers = COLUMNS.map(c => c.label);
    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.aoa_to_sheet([headers]);
    XLSX.utils.book_append_sheet(wb, ws, "Plantilla");
    XLSX.writeFile(wb, "plantilla_base_presupuesto.xlsx");
  });

  // ── Cargar Excel ──────────────────────────────────────────
  document.getElementById("btnCargarExcel").addEventListener("click", () => {
    document.getElementById("inputExcel").click();
  });

  document.getElementById("inputExcel").addEventListener("change", function(e) {
    const spinner = document.getElementById("spinnerCargar");
    const btn = document.getElementById("btnCargarExcel");
    spinner.style.display = "inline-block";
    btn.disabled = true;

    const file = e.target.files[0];
    if (!file) { spinner.style.display = "none"; btn.disabled = false; return; }

    const loader   = CargaLotes.loader(`Cargando ${file.name}`);
    const terminar = () => { spinner.style.display = "none"; btn.disabled = false; e.target.value = ""; };
    const fallar   = (texto, detalles, nota) => { loader.error(texto, detalles, nota); terminar(); };
    loader.fase("Leyendo el archivo…");

    const reader = new FileReader();
    reader.onerror = () => fallar("No se pudo leer el archivo.");
    reader.onload = async function(ev) {
      try {
        loader.fase("Leyendo las filas del Excel…");
        await CargaLotes.pintar();          // que se vea el loader antes del trabajo pesado
        const data = new Uint8Array(ev.target.result);
        const wb   = XLSX.read(data, { type: "array" });
        const ws   = wb.Sheets[wb.SheetNames[0]];
        const json = XLSX.utils.sheet_to_json(ws, { defval: null });

        if (!json.length) {
          fallar("El archivo está vacío o no tiene datos."); return;
        }

        const required = COLUMNS.map(c => c.label);
        const missing  = required.filter(h => !(h in json[0]));
        if (missing.length) {
          fallar("Faltan columnas obligatorias en el archivo:", missing); return;
        }

        loader.fase(`Revisando ${CargaLotes.formato(json.length)} filas…`);
        await CargaLotes.pintar();

        const errores = [];
        const valid   = [];

        json.forEach((row, i) => {
          try {
            valid.push({
              mcncuenta:  parseStr(row.MCNCUENTA),
              mcnfecha:   parseFechaExcel(row.MCNFECHA),
              mcntipodoc: parseStr(row.MCNTIPODOC),
              mcnnumedoc: parseInt_(row.MCNNUMEDOC),
              mcnvincula: parseStr(row.MCNVINCULA),
              vinnombre:  parseStr(row.VINNOMBRE),
              mcnsucvin:  parseStr(row.MCNSUCVIN),
              saldoant:   parseInt_(row.SALDOANT),
              mcnvaldebi: parseNumF(row.MCNVALDEBI),
              mcnvalcred: parseNumF(row.MCNVALCRED),
              saldonew:   parseNumF(row.SALDONEW),
              mcnsucurs:  parseStr(row.MCNSUCURS),
              mcnccosto:  parseStr(row.MCNCCOSTO),
              mcndestino: parseStr(row.MCNDESTINO),
              mcndetalle: parseStr(row.MCNDETALLE),
              mcnzona:    parseStr(row.MCNZONA),
              cconombre:  parseStr(row.CCONOMBRE),
              dnonombre:  parseStr(row.DNONOMBRE),
              zonnombre:  parseStr(row.ZONNOMBRE),
              mcnempresa: parseStr(row.MCNEMPRESA),
              mcnclase:   parseStr(row.MCNCLASE),
              mcnvinkey:  parseStr(row.MCNVINKEY),
              tpreg:      parseInt_(row.TPREG),
              ctanombre:  parseStr(row.CTANOMBRE),
              docdetalle: parseStr(row.DOCDETALLE),
              infdetalle: parseStr(row.INFDETALLE),
            });
          } catch (err) {
            errores.push(`Fila ${i + 2}: ${err.message}`);
          }
        });

        if (errores.length) {
          fallar(`Hay ${errores.length} fila(s) con errores; no se subió nada.`,
            errores.slice(0, 10).concat(errores.length > 10 ? [`…y ${errores.length - 10} más`] : []));
          return;
        }

        try {
          const total = await enviarPorLotes(valid, "/presupuesto/subir_excel_cuenta5/", loader);
          loader.fase("Actualizando la tabla…");
          await loadData();
          loader.exito(`${CargaLotes.formato(total)} registros cargados`);
          showToast(`${total} registros cargados`, "success");
        } catch (err) {
          if (err.guardados) loadData();      // que la tabla muestre lo que sí alcanzó a guardarse
          fallar("La carga se detuvo. " + err.message, null, err.guardados
            ? `Alcanzaron a guardarse ${CargaLotes.formato(err.guardados)} registros de los lotes anteriores. ` +
              "Para no duplicarlos, borra la cuenta y vuelve a cargar el archivo completo."
            : "No se guardó ningún registro.");
          return;
        }
        terminar();

      } catch (err) {
        fallar("Error leyendo el archivo: " + err.message);
      }
    };

    reader.readAsArrayBuffer(file);
  });
}

// ─── Helpers de parseo ────────────────────────────────────────
function parseStr(v) {
  return v === null ? null : String(v);
}
function parseNumF(v) {
  if (v === null || v === "") return null;
  const n = parseFloat(v);
  if (isNaN(n)) throw new Error(`Número decimal esperado, recibido: ${v}`);
  return n;
}
function parseInt_(v) {
  if (v === null || v === "") return null;
  const n = Number(v);
  if (!Number.isInteger(n)) throw new Error(`Entero esperado, recibido: ${v}`);
  return n;
}