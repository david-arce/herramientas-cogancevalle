let tablaProductos = null; // tabla nativa (tabla.js)
let grafica = null;        // gráfica SVG (grafica.js)
let selectedRowData = null;
let productosData = null; // Variable global para almacenar los datos
let categ3PorId = {};     // id de pronóstico -> categ3_nom (solo para exportar)
let metodoPorId = {};     // id de pronóstico -> método de pronóstico seleccionado (solo para exportar)
// Cache del mapeo proveedor|sku -> col_base, cargado desde la BD
let multiplosConfigCache = null;
async function loadMultiplosConfig() {
    if (multiplosConfigCache) return multiplosConfigCache;
    const response = await fetch('/config_proveedor_sku/');
    const data = await response.json();
    multiplosConfigCache = data.config;
    return multiplosConfigCache;
}
// Función reutilizable: arma los query params a partir de los filtros seleccionados
function buildFilterParams() {
    const params = new URLSearchParams();

    getSelectedValues('select-options-items', 'select-all-items')
        .forEach(v => params.append('item', v));
    getSelectedValues('select-options-proveedores', 'select-all-proveedores')
        .forEach(v => params.append('proveedor', v));
    getSelectedValues('select-options-productos', 'select-all-productos')
        .forEach(v => params.append('producto', v));
    getSelectedValues('select-options-sedes', 'select-all-sedes')
        .forEach(v => params.append('sede', v));

    return params;
}
// Meses digitados en el filtro (acepta 3.5 o 3,5 = 3 meses y 15 días).
// Devuelve null si el valor no es válido.
const MESES_MAXIMO = 36;
function getMesesPronostico() {
    const texto = document.getElementById('meses-input').value.trim().replace(',', '.');
    if (texto === '') return 1;
    if (!/^\d+(\.\d+)?$/.test(texto)) return null;
    const meses = Number(texto);
    if (!(meses > 0) || meses > MESES_MAXIMO) return null;
    return meses;
}
// Texto de la columna: "CANTIDAD 3.5 MESES" / "CANTIDAD 1 MES"
function etiquetaMeses(meses) {
    const n = String(meses).replace('.', ',');
    return `CANTIDAD ${n} ${meses === 1 ? 'MES' : 'MESES'}`;
}
let mesesConsultados = 1;   // meses usados en la última búsqueda (para encabezado y Excel)

// Texto de ayuda: convierte los meses digitados a "X meses y Y días" (1 mes = 30 días).
// Es solo visual; el cálculo real lo hace el servidor con el número digitado.
function describirMeses(meses) {
    let enteros = Math.floor(meses);
    let dias = Math.round((meses - enteros) * 30);
    if (dias === 30) { enteros += 1; dias = 0; }   // p. ej. 2.99 -> 3 meses
    const partes = [];
    if (enteros > 0) partes.push(`${enteros} ${enteros === 1 ? 'mes' : 'meses'}`);
    if (dias > 0) partes.push(`${dias} ${dias === 1 ? 'día' : 'días'}`);
    return partes.length ? partes.join(' y ') : 'menos de 1 día';
}

function actualizarEquivalenciaMeses() {
    const destino = document.getElementById('meses-equivalencia');
    const meses = getMesesPronostico();
    if (meses === null) {
        destino.textContent = `Valor no válido (mayor a 0 y hasta ${MESES_MAXIMO})`;
        destino.classList.add('invalido');
    } else {
        destino.textContent = `Se pronosticarán: ${describirMeses(meses)}`;
        destino.classList.remove('invalido');
    }
}
// Función de lookup: exacto primero, luego comodín
function getMultiplo(config, proveedor, producto) {
    const exactKey    = `${proveedor}|${producto}`;
    const wildcardKey = `${proveedor}|*`;
    if (config[exactKey]    !== undefined) return config[exactKey];
    if (config[wildcardKey] !== undefined) return config[wildcardKey];
    return '';
}
const handleRowClick = (data) => {
    // const filteredData = data.slice(1);  // Eliminar el primer elemento (indice de la tabla)
    selectedRowData = data;
    console.log("Selected row data:", selectedRowData);
};

document.getElementById('send-data').addEventListener('click', async () => {
    if (!selectedRowData) {
        alert("Por favor selecciona una fila de la tabla para generar la gráfica");
        return;
    }
    const modal = document.getElementById("processingModal");
    try {
        modal.style.display = "block";  // Mostrar el modal
        await initChart(selectedRowData);
    } catch (e) {
        console.error("Error al generar la gráfica: ", e);
        alert("No se pudo generar el gráfico. Intenta de nuevo.");
    } finally {
        modal.style.display = "none";  // Ocultar el modal
    }
});


document.getElementById('export-visible').addEventListener('click', async function () {
    const wb = Excel.crearLibro();
    // Filas de la tabla en el orden actual (copias, no modifica la tabla)
    const filteredData = tablaProductos ? tablaProductos.filasVisibles() : [];
    // Cargar el mapeo desde la BD (una sola vez, cacheado)
    const multiplosConfig = await loadMultiplosConfig();
    
    const toInt = (v) => {
        const n = parseInt(v, 10);
        return Number.isFinite(n) ? n : 0;
    };
    const updatedData = filteredData.map(row => {
        row[9]  = toInt(row[9]);
        row[10] = toInt(row[10]);
        row[11] = toInt(row[11]);
        row[12] = toInt(row[12]);
        row[15] = toInt(row[15]);
        return row;
    });

    const columnsToExport = [0, 1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13];

    const headers = [
        'REG.N12', 'BODEGA.C5', 'PRODUCTO.C15', 'CODCMC.C50', 'NOMBRE.C100',
        'UNIMED.C4', 'LOTEPRO.C12', 'CANTIDAD.N20', 'CANTIDAD.N20',
        'CANTIDAD.N20', 'AUTOMATIZACION.C20', 'PRECIO_UNITARIO.N20', 'FECHAENTREGA.C10',
        'DETALLE.C255', 'CATEG3_NOM.C255',
        `${etiquetaMeses(mesesConsultados).replace(/ /g, '_').replace(',', '.')}.N20`,
        'PRONOSTICO_SELECCIONADO.C60',
    ];

    const exportData = [headers];
    let index = 1;
    const hoy = new Date();
    const fechaEntrega = `${hoy.getFullYear()}/${String(hoy.getMonth() + 1).padStart(2, '0')}/${String(hoy.getDate()).padStart(2, '0')}`;
    updatedData.forEach(row => {
        const rowData = [];
        columnsToExport.forEach((colIndex, i) => {
            if (i === 0) {
                rowData.push(index++);
            } else if (i <= 9) {
                // Columnas hasta CANTIDAD.N20 (índice 9 en columnsToExport = col 11 real)
                rowData.push(row[colIndex]);
            }
        });

        // Índice de columna de la tabla según la col_base configurada
        //  9 = CANTIDAD 1 MES  |  10 = STOCK  |  11 = CANTIDAD 3 MESES
        const COL_BASE_INDEX = {
            'cantidad':        9,
            'stock_seguridad': 10,
            'cantidadx3':      11,
        };

        const proveedor = String(row[7]).trim();
        const producto  = String(row[2]).trim();
        const colBase   = getMultiplo(multiplosConfig, proveedor, producto);

        const idxCol = COL_BASE_INDEX[colBase];
        // Si no hay configuración o el valor no es numérico → 0, nunca vacío
        const valorMultiplo = (idxCol !== undefined) ? toInt(row[idxCol]) : 0;

        // AUTOMATIZACION va antes de PRECIO_UNITARIO (índice 12 en la tabla)
        rowData.push(valorMultiplo);         // AUTOMATIZACION.C20
        rowData.push(row[12]);               // PRECIO_UNITARIO.N20
        rowData.push(fechaEntrega);               // FECHAENTREGA.C10

        // Columna DETALLE
        const detalle = row[14] !== undefined && row[14] !== null ? row[14] : '';
        rowData.push(detalle);

        // Columna CATEG3_NOM
        const categ3 = categ3PorId[String(row[0]).trim()] ?? '';
        rowData.push(categ3);

        // Columna CANTIDAD N MESES (según los meses digitados en el filtro)
        rowData.push(row[15]);

        // Pronóstico seleccionado (método con menor ECM)
        rowData.push(metodoPorId[String(row[0]).trim()] ?? '');

        exportData.push(rowData);
    });

    Excel.agregarHoja(wb, 'Datos_Productos', exportData);

    //agregar hojas de traslados entre sedes ────────────────────────
    try {
        const params = buildFilterParams();
        const response = await fetch(`/traslados_resumen_json/?${params.toString()}`);
        const data = await response.json();

        Object.entries(data.hojas || {}).forEach(([sedeOrigen, hoja]) => {
            const filas = [hoja.headers];

            if (hoja.rows.length > 0) {
                hoja.rows.forEach(row => filas.push(row));
            } else {
                filas.push([`No se realizaron traslados desde ${sedeOrigen}`]);
            }

            const nombreHoja = `Traslados_${sedeOrigen}`
                .replace(/[:\\/?*\[\]]/g, '')
                .substring(0, 31);

            Excel.agregarHoja(wb, nombreHoja, filas);
        });
    } catch (error) {
        console.error('Error al obtener el reporte de traslados:', error);
        alert('No se pudo incluir el reporte de traslados en el Excel. Se exportará solo con los datos de productos.');
    }
    const fechaActual = new Date();
    const year = fechaActual.getFullYear();
    const mes = String(fechaActual.getMonth() + 1).padStart(2, '0');
    const dia = String(fechaActual.getDate()).padStart(2, '0');
    const fechaFormateada = `${dia}/${mes}/${year}`;
    const nombreArchivo = `Datos_filtrados_${fechaFormateada}.xlsx`;

    Excel.descargar(wb, nombreArchivo);
});

async function uploadData() {
    const params = buildFilterParams();

    if (!params.toString()) {
        alert('Selecciona al menos un filtro antes de buscar.');
        return null;
    }

    const meses = getMesesPronostico();
    if (meses === null) {
        alert(`Digita una cantidad de meses válida (mayor a 0 y hasta ${MESES_MAXIMO}). Ej: 3.5 = 3 meses y 15 días.`);
        document.getElementById('meses-input').focus();
        return null;
    }
    params.append('meses', meses);

    const loader = document.getElementById('loader');
    try {
        loader.style.display = 'block';
        const response = await fetch(`/lista/?${params.toString()}`);
        return await response.json();
    } catch (error) {
        console.error('Error al obtener los datos:', error);
        return null;
    } finally {
        loader.style.display = 'none';
    }
}

// Helper function to get CSRF token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Columnas ocultas en pantalla (siguen disponibles para exportar y para la gráfica)
const COLUMNAS_OCULTAS = [0, 1, 3, 5, 6, 12, 13, 14];

const initDataTable = async (datos) => {
    const loader = document.getElementById('loader');
    try {
        loader.style.display = 'block';
        if (!tablaProductos) {
            tablaProductos = new TablaPronosticos('#datatable-productos', {
                columnasOcultas: COLUMNAS_OCULTAS,
                alSeleccionar: handleRowClick,
            });
        }
        selectedRowData = null;   // la tabla nueva no tiene fila seleccionada
        mesesConsultados = Number(datos.meses) || 1;
        document.getElementById('th-cantidad-n').textContent = etiquetaMeses(mesesConsultados);
        tablaProductos.cargar(listProductos(datos));
    } catch (e) {
        alert(e);
    } finally {
        loader.style.display = 'none';
    }
};

// Convierte la respuesta de /lista/ en filas (mismo orden de columnas que el <thead>)
const listProductos = (datos) => {
    // categ3_nom no se muestra en la tabla; se guarda por id para la exportación
    categ3PorId = {};
    metodoPorId = {};
    datos.productos.forEach(p => {
        categ3PorId[String(p.id)] = p.categ3_nom ?? '';
        metodoPorId[String(p.id)] = p.metodo_pronostico ?? '';
    });

    return datos.productos.map(producto => [
        `${producto.id}`,
        `${producto.bodega}`,
        `${producto.item}`,
        `${producto.codigo}`,
        `${producto.producto}`,
        `${producto.unimed}`,
        `${producto.lotepro}`,
        `${producto.proveedor}`,
        `${producto.sede}`,
        `${producto.cantidad}`,
        `${producto.stock}`,
        `${producto.cantidadx3}`,
        `${producto.precio}`,
        `${producto.fecha}`,
        `${producto.detalle ?? ''}`,
        `${producto.cantidad_n ?? ''}`,
    ]);
};

//GRAFICO
// La fila seleccionada se envía en la URL: así siempre se grafica ese producto
// (antes dependía de la sesión del servidor y podía quedar el producto anterior).
const getOptionChart = async (fila) => {
    const params = new URLSearchParams({
        bod:       fila[1],
        sku:       fila[2],
        sku_nom:   fila[4],
        marca_nom: fila[7],
        sede:      fila[8],
    });
    const response = await fetch(`/chart/?${params.toString()}`, { cache: 'no-store' });
    const datos = await response.json();
    if (!response.ok) throw new Error(datos.message || `Error ${response.status}`);
    return datos;
};

const initChart = async (fila) => {
    const opciones = await getOptionChart(fila);
    const myElement = document.getElementById('chart');
    myElement.style.display = 'block';
    if (!grafica) grafica = new GraficaLineas(myElement);
    grafica.dibujar(opciones);
};

document.getElementById('search').addEventListener('click', async () => {
    const datos = await uploadData();
    if (datos) {
        await initDataTable(datos);
    }
});

document.addEventListener('DOMContentLoaded', () => {
    setupFilter('item-search', 'select-all-items');
    setupFilter('proveedor-search', 'select-all-proveedores');
    setupFilter('producto-search', 'select-all-productos');
    setupFilter('sede-search', 'select-all-sedes');

    const inputMeses = document.getElementById('meses-input');
    inputMeses.addEventListener('input', actualizarEquivalenciaMeses);
    actualizarEquivalenciaMeses();
});

// Función para obtener todos los valores seleccionados de los checkboxes de un filtro
function getSelectedValues(selectId, selectAll) {
    const checkboxes = document.querySelectorAll('.' + selectId + ' input[type="checkbox"]:not(#' + selectAll + ')');
    const selectedValues = [];
    
    checkboxes.forEach(function (checkbox) {
        if (checkbox.checked) {
            selectedValues.push(checkbox.value);
        }
    });
    return selectedValues;
}

function cleanSelectedValues(selectId, selectAll) {
    const checkboxes = document.querySelectorAll('.' + selectId + ' input[type="checkbox"]:not(#' + selectAll + ')');
    const selectAllCheckbox = document.getElementById(selectAll);
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    selectAllCheckbox.checked = false;
};

document.getElementById('clean-filter-item').addEventListener('click', () => {
    cleanSelectedValues('select-options-items', 'select-all-items');
});
document.getElementById('clean-filter-proveedor').addEventListener('click', () => {
    cleanSelectedValues('select-options-proveedores', 'select-all-proveedores');
});
document.getElementById('clean-filter-producto').addEventListener('click', () => {
    cleanSelectedValues('select-options-productos', 'select-all-productos');
});
document.getElementById('clean-filter-sede').addEventListener('click', () => {
    cleanSelectedValues('select-options-sedes', 'select-all-sedes');
});

function setupFilter(searchInputId, selectAllId) {
    const searchInput = document.getElementById(searchInputId);
    const selectAllCheckbox = document.getElementById(selectAllId);
    const checkboxes = selectAllCheckbox.parentNode.parentNode.querySelectorAll('input[type="checkbox"]:not(#' + selectAllId + ')');
    // const checkboxes = document.querySelectorAll('.select-options input[type="checkbox"]:not(#' + selectAllId + ')');
    
    // Función para seleccionar/deseleccionar todas las opciones
    selectAllCheckbox.addEventListener('change', (e) => {
        checkboxes.forEach(checkbox => {
            checkbox.checked = e.target.checked;
        });
    });

    // Si todas las opciones están seleccionadas, marca "Seleccionar todo"
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', () => {
            const allChecked = Array.from(checkboxes).every(cb => cb.checked);
            selectAllCheckbox.checked = allChecked;
        });
    });
    
    // Filtrar las opciones de acuerdo a la búsqueda
    searchInput.addEventListener('keyup', () => {
        const filter = searchInput.value.toLowerCase();
        checkboxes.forEach(checkbox => {
            const label = checkbox.parentNode;
            const text = label.textContent.toLowerCase();
            
            if (text.includes(filter)) {
                label.style.display = "";
            } else {
                label.style.display = "none";
            }
        });
    });

    document.getElementById('clean-filters-button').addEventListener('click', () => {
        // Puedes añadir lógica para cancelar la selección si es necesario
        checkboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
        selectAllCheckbox.checked = false;
    });
};

document.getElementById('clean-filter-item').addEventListener('click', function () {
    const input = document.getElementById('item-search');
    input.value = ''; // Borra el texto del input
    input.focus(); // Vuelve el foco al input
    // Mostrar todas las opciones después de limpiar el input
    const checkboxes = document.querySelectorAll('.select-options-items input[type="checkbox"]:not(#select-all-items)');
    checkboxes.forEach(checkbox => {
        const label = checkbox.parentNode;
        label.style.display = ""; // Mostrar todas las opciones
    });
});
document.getElementById('clean-filter-proveedor').addEventListener('click', function () {
    const input = document.getElementById('proveedor-search');
    input.value = ''; // Borra el texto del input
    input.focus(); // Vuelve el foco al input
    // Mostrar todas las opciones después de limpiar el input
    const checkboxes = document.querySelectorAll('.select-options-proveedores input[type="checkbox"]:not(#select-all-proveedores)');
    checkboxes.forEach(checkbox => {
        const label = checkbox.parentNode;
        label.style.display = ""; // Mostrar todas las opciones
    });
});
document.getElementById('clean-filter-producto').addEventListener('click', function () {
    const input = document.getElementById('producto-search');
    input.value = ''; // Borra el texto del input
    input.focus(); // Vuelve el foco al input
    // Mostrar todas las opciones después de limpiar el input
    const checkboxes = document.querySelectorAll('.select-options-productos input[type="checkbox"]:not(#select-all-productos)');
    checkboxes.forEach(checkbox => {
        const label = checkbox.parentNode;
        label.style.display = ""; // Mostrar todas las opciones
    });
});
document.getElementById('clean-filter-sede').addEventListener('click', function () {
    const input = document.getElementById('sede-search');
    input.value = ''; // Borra el texto del input
    input.focus(); // Vuelve el foco al input
    // Mostrar todas las opciones después de limpiar el input
    const checkboxes = document.querySelectorAll('.select-options-sedes input[type="checkbox"]:not(#select-all-sedes)');
    checkboxes.forEach(checkbox => {
        const label = checkbox.parentNode;
        label.style.display = ""; // Mostrar todas las opciones
    });
});
