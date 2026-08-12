/* ══════════════════════════════════════════════════════════════════
   CONSTANTES
══════════════════════════════════════════════════════════════════ */
const MESES = [
    'Enero','Febrero','Marzo','Abril','Mayo','Junio',
    'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'
];

const FMT = new Intl.NumberFormat('es-ES', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
});

function fmt(n) {
    if (n === 0 || n === null || n === undefined) return '-';
    return FMT.format(n);
}

/* ══════════════════════════════════════════════════════════════════
   ESTADO GLOBAL
══════════════════════════════════════════════════════════════════ */
let datosOriginales = [];
let sortCol = null;
let sortDir = 'asc';

/* ══════════════════════════════════════════════════════════════════
   TOAST
══════════════════════════════════════════════════════════════════ */
function showToast(msg, tipo = 'info') {
    const div = document.createElement('div');
    div.className = `toast toast-${tipo}`;
    div.textContent = msg;
    document.getElementById('toastContainer').appendChild(div);
    requestAnimationFrame(() => requestAnimationFrame(() => div.classList.add('show')));
    setTimeout(() => {
        div.classList.remove('show');
        setTimeout(() => div.remove(), 350);
    }, 4000);
}

/* ══════════════════════════════════════════════════════════════════
   RENDERIZADO
══════════════════════════════════════════════════════════════════ */
function renderTabla(data) {
    const tbody = document.getElementById('consolidadoBody');
    tbody.innerHTML = '';

    if (!data || data.length === 0) {
        tbody.innerHTML = `<tr class="empty-row"><td colspan="16">Sin datos disponibles.</td></tr>`;
        actualizarFooter([]);
        actualizarStats([]);
        return;
    }

    data.forEach(fila => {
        const tr = document.createElement('tr');

        // Celdas de texto
        ['mcncuenta', 'mcnccosto', 'zonnombre', 'ctanombre'].forEach(key => {
            const td = document.createElement('td');
            td.textContent = fila[key] || '';
            tr.appendChild(td);
        });

        // Celdas numéricas por mes
        MESES.forEach(mes => {
            const td = document.createElement('td');
            td.className = 'num';
            const v = parseFloat(fila[mes]) || 0;
            td.textContent = fmt(v);
            if (v !== 0) td.classList.add(v > 0 ? 'pos' : 'neg');
            tr.appendChild(td);
        });

        tbody.appendChild(tr);
    });

    actualizarFooter(data);
    actualizarStats(data);
    aplicarBusqueda();
}

/* ══════════════════════════════════════════════════════════════════
   FOOTER Y STATS
══════════════════════════════════════════════════════════════════ */
function actualizarFooter(data) {
    MESES.forEach(mes => {
        const total = data.reduce((s, r) => s + (parseFloat(r[mes]) || 0), 0);
        const el = document.getElementById(`ft-${mes}`);
        if (el) el.textContent = fmt(total);
    });
}

function actualizarStats(data) {
    document.getElementById('statFilas').textContent = data.length;
    const total = data.reduce((s, r) => {
        return s + MESES.reduce((ms, mes) => ms + (parseFloat(r[mes]) || 0), 0);
    }, 0);
    document.getElementById('statTotal').textContent = '$' + FMT.format(total);
}

/* ══════════════════════════════════════════════════════════════════
   CARGA DE DATOS
══════════════════════════════════════════════════════════════════ */
async function cargarDatos() {
    document.getElementById('loadingOverlay').classList.add('active');
    document.getElementById('consolidadoBody').innerHTML =
        `<tr class="empty-row"><td colspan="16">⏳ Cargando...</td></tr>`;
    try {
        const resp = await fetch(url_obtener_consolidado_tulua);
        const json = await resp.json();
        if (json.error) { showToast('Error: ' + json.error, 'error'); return; }
        datosOriginales = json.data || [];
        renderTabla(datosOriginales);
    } catch (e) {
        showToast('Error al cargar datos: ' + e.message, 'error');
        document.getElementById('consolidadoBody').innerHTML =
            `<tr class="empty-row"><td colspan="16">❌ Error al cargar datos.</td></tr>`;
    } finally {
        document.getElementById('loadingOverlay').classList.remove('active');
    }
}

/* ══════════════════════════════════════════════════════════════════
   BÚSQUEDA GLOBAL
══════════════════════════════════════════════════════════════════ */
function aplicarBusqueda() {
    const q = document.getElementById('globalSearch').value.toLowerCase().trim();
    document.querySelectorAll('#consolidadoBody tr').forEach(tr => {
        if (tr.classList.contains('empty-row')) return;
        if (!q) { tr.classList.remove('hidden-search'); return; }
        const texto = Array.from(tr.querySelectorAll('td')).slice(0, 4)
            .map(td => td.textContent.toLowerCase()).join(' ');
        tr.classList.toggle('hidden-search', !texto.includes(q));
    });
}
document.getElementById('globalSearch').addEventListener('input', aplicarBusqueda);

/* ══════════════════════════════════════════════════════════════════
   ORDENAMIENTO
══════════════════════════════════════════════════════════════════ */
document.querySelectorAll('thead th.sortable').forEach(th => {
    th.addEventListener('click', () => {
        const col = th.dataset.col;
        sortDir = (sortCol === col && sortDir === 'asc') ? 'desc' : 'asc';
        sortCol = col;
        document.querySelectorAll('thead th').forEach(t =>
            t.classList.remove('sorted-asc', 'sorted-desc')
        );
        th.classList.add(sortDir === 'asc' ? 'sorted-asc' : 'sorted-desc');

        const sorted = [...datosOriginales].sort((a, b) => {
            const isNum = MESES.includes(col);
            const av = isNum ? (parseFloat(a[col]) || 0) : String(a[col] || '').toLowerCase();
            const bv = isNum ? (parseFloat(b[col]) || 0) : String(b[col] || '').toLowerCase();
            if (av < bv) return sortDir === 'asc' ? -1 : 1;
            if (av > bv) return sortDir === 'asc' ?  1 : -1;
            return 0;
        });
        renderTabla(sorted);
    });
});

/* ══════════════════════════════════════════════════════════════════
   RECARGAR / EXPORTAR
══════════════════════════════════════════════════════════════════ */
document.getElementById('recargarBtn').addEventListener('click', cargarDatos);

document.getElementById('exportarBtn').addEventListener('click', () => {
    if (!datosOriginales.length) { showToast('Sin datos para exportar', 'error'); return; }

    const headers = ['Cuenta', 'Centro Costo', 'Zona', 'Nombre Cuenta', ...MESES];
    const rows = datosOriginales.map(r => [
        r.mcncuenta  || '',
        r.mcnccosto  || '',
        r.zonnombre  || '',
        r.ctanombre  || '',
        ...MESES.map(m => r[m] || 0)
    ]);

    const csv  = [headers, ...rows].map(r => r.join(';')).join('\n');
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const a    = document.createElement('a');
    a.href     = URL.createObjectURL(blob);
    a.download = `consolidado_tulua_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    showToast('📥 CSV exportado', 'success');
});

/* ══════════════════════════════════════════════════════════════════
   INIT
══════════════════════════════════════════════════════════════════ */
cargarDatos();