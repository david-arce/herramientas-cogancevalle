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
let allRows            = [];  // todos los registros cargados del servidor
let filteredRows       = [];  // resultado tras búsqueda + filtros Excel
let currentPage        = 1;
let perPage            = 50;
let searchQuery        = "";

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
  tbody.innerHTML = `<tr class="c5-loading-row"><td colspan="26">Cargando datos…</td></tr>`;

  const formData = new FormData();
  formData.append("draw", 1);
  formData.append("start", 0);
  formData.append("length", 999999);
  formData.append("search[value]", "");

  fetch(url_obtener_cuenta5_presupuestado, {
    method: "POST",
    headers: { "X-CSRFToken": getCookie("csrftoken") },
    body: formData,
  })
    .then(r => r.json())
    .then(json => {
      allRows = json.data || [];
      feedFilterValues();
      applyFilterAndRender();
    })
    .catch(err => {
      tbody.innerHTML = `<tr><td colspan="26" class="c5-error">Error al cargar datos.</td></tr>`;
      console.error(err);
    });
}

// ─── Alimentar valores únicos en el módulo C5Filters ──────────
function feedFilterValues() {
  if (!window.C5Filters) return;
  FILTER_COLS.forEach(col => {
    const set = new Set();
    allRows.forEach(row => set.add(getFilterValue(row, col)));
    const values = [...set];
    let labels = null;
    if (col === "mcnfecha") {
      labels = {};
      values.forEach(v => { labels[v] = monthLabel(v); });
    }
    C5Filters.setValues(col, values, labels);
  });
}

// ─── Filtrar + ordenar + renderizar ───────────────────────────
function applyFilterAndRender() {
  const q = searchQuery.trim().toLowerCase();
  const excelFilters = window.C5Filters ? C5Filters.getParams() : {};

  filteredRows = allRows.filter(row => {
    if (q) {
      const matchSearch = COLUMNS.some(col => {
        const v = row[col.key];
        return v !== null && v !== undefined && String(v).toLowerCase().includes(q);
      });
      if (!matchSearch) return false;
    }
    for (const [col, allowed] of Object.entries(excelFilters)) {
      if (!allowed || allowed.length === 0) continue;
      if (!allowed.includes(getFilterValue(row, col))) return false;
    }
    return true;
  });

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
    tbody.innerHTML = `<tr><td colspan="26" class="c5-empty">Sin resultados.</td></tr>`;
    renderTotals();
    return;
  }

  const frag = document.createDocumentFragment();
  slice.forEach((row, pageIdx) => {
    const tr = document.createElement("tr");

    COLUMNS.forEach(col => {
      const td = document.createElement("td");
      td.className = col.num ? "c5-num" : "";
      td.textContent = col.num ? fmt(row[col.key]) : (row[col.key] ?? "");
      tr.appendChild(td);
    });

    tr.addEventListener("click", () => {
      document.querySelectorAll("#c5Tbody tr.c5-active").forEach(r => r.classList.remove("c5-active"));
      tr.classList.add("c5-active");
    });

    frag.appendChild(tr);
  });

  tbody.innerHTML = "";
  tbody.appendChild(frag);
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

  const numCols = new Set(COLUMNS.filter(c => c.num).map(c => c.key));
  const sums = {};
  numCols.forEach(k => { sums[k] = 0; });
  filteredRows.forEach(r => {
    numCols.forEach(k => {
      const v = parseFloat(r[k]);
      if (!isNaN(v)) sums[k] += v;
    });
  });

  const cells = COLUMNS.map((col, i) =>
    i === 0        ? `<td class="c5-total-label">TOTAL</td>`
  : col.num        ? `<td class="c5-num">${fmt(sums[col.key].toFixed(2))}</td>`
                   : `<td></td>`);
  row.innerHTML = cells.join("");
}

const CHUNK = 2000;   // ~1,2 MB por lote

async function enviarPorLotes(valid, url) {
  let total = 0;
  const lotes = Math.ceil(valid.length / CHUNK);

  for (let i = 0; i < lotes; i++) {
    const lote = valid.slice(i * CHUNK, (i + 1) * CHUNK);

    const r = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({ registros: lote }),
    });

    const d = await r.json();
    if (!r.ok || d.status !== "ok") {
      throw new Error(`Lote ${i + 1}/${lotes}: ${d.message || r.status}`);
    }

    total += d.insertados;
    showToast(`Lote ${i + 1}/${lotes} — ${total} registros`, "success", 1200);
  }
  return total;
}
function isoToExcelSerial(v) {
  if (v === null || v === undefined || v === "") return "";
  const m = String(v).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return v;                       // ya era serial u otro formato
  const utc = Date.UTC(+m[1], +m[2] - 1, +m[3]);
  return Math.round(utc / 86400000) + 25569;   // epoch → serial 1900
}
function exportarDatosExcel() {
  if (!filteredRows.length) { showToast("No hay datos para exportar", "error"); return; }
  const headers = COLUMNS.map(c => c.label);
  const aoa = [headers, ...filteredRows.map(r =>
    COLUMNS.map(c => c.key === "mcnfecha" ? isoToExcelSerial(r[c.key]) : (r[c.key] ?? ""))
  )];
  const ws = XLSX.utils.aoa_to_sheet(aoa);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Cuenta5");
  XLSX.writeFile(wb, `cuenta5_presupuestado_${new Date().toISOString().slice(0,10)}.xlsx`);
  showToast(`${filteredRows.length} filas exportadas`, "success");
}
// ─── Enlazar todos los eventos de UI ──────────────────────────
function bindUI() {
  document.getElementById("btnExportarExcel").addEventListener("click", exportarDatosExcel);

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

  // ── Borrar cuenta completa (con confirmación escrita) ──────
  const inputConfirmBorrar = document.getElementById("inputConfirmBorrar");
  const btnConfirmBorrar   = document.getElementById("confirmEliminarCuenta");

  document.getElementById("btnBorrar").addEventListener("click", () => {
    inputConfirmBorrar.value = "";
    btnConfirmBorrar.disabled = true;
    document.getElementById("borrarCuentaConteo").textContent =
      new Intl.NumberFormat("es-ES").format(allRows.length);
    openModal("modalEliminarCuenta");
    setTimeout(() => inputConfirmBorrar.focus(), 100);
  });

  inputConfirmBorrar.addEventListener("input", () => {
    btnConfirmBorrar.disabled = inputConfirmBorrar.value.trim().toUpperCase() !== "ELIMINAR";
  });

  document.getElementById("cancelEliminarCuenta").addEventListener("click", () => closeModal("modalEliminarCuenta"));

  btnConfirmBorrar.addEventListener("click", () => {
    if (inputConfirmBorrar.value.trim().toUpperCase() !== "ELIMINAR") return;
    closeModal("modalEliminarCuenta");
    fetch(url_borrar_cuenta5_presupuestado, {
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
    const btn     = document.getElementById("btnCargarExcel");
    spinner.style.display = "inline-block";
    btn.disabled = true;

    const file = e.target.files[0];
    if (!file) { spinner.style.display = "none"; btn.disabled = false; return; }

    const reader = new FileReader();
    reader.onload = function(ev) {
      try {
        const data = new Uint8Array(ev.target.result);
        const wb   = XLSX.read(data, { type: "array" });
        const ws   = wb.Sheets[wb.SheetNames[0]];
        const json = XLSX.utils.sheet_to_json(ws, { defval: null });

        if (!json.length) {
          alert("El archivo está vacío o no tiene datos.");
          spinner.style.display = "none"; btn.disabled = false; return;
        }

        const required = COLUMNS.map(c => c.label);
        const missing  = required.filter(h => !(h in json[0]));
        if (missing.length) {
          alert("Faltan columnas obligatorias:\n" + missing.join(", "));
          spinner.style.display = "none"; btn.disabled = false; return;
        }

        const errores = [];
        const valid   = [];

        json.forEach((row, i) => {
          try {
            valid.push({
              mcncuenta:  parseStr(row.MCNCUENTA),
              mcnfecha:   parseNumF(row.MCNFECHA),
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
          alert("Errores encontrados:\n" + errores.slice(0, 10).join("\n") +
            (errores.length > 10 ? `\n…y ${errores.length - 10} más` : ""));
          spinner.style.display = "none"; btn.disabled = false; return;
        }

        enviarPorLotes(valid, "/presupuesto/subir_excel_cuenta5_presupuestado/")
          .then(total => {
            showToast(`${total} registros cargados`, "success");
            loadData();
          })
          .catch(err => showToast("Error: " + err.message, "error", 8000))
          .finally(() => {
            spinner.style.display = "none";
            btn.disabled = false;
            e.target.value = "";
          });

      } catch (err) {
        alert("Error leyendo el archivo: " + err.message);
        spinner.style.display = "none"; btn.disabled = false;
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