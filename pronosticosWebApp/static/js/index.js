let dataTable;
let dataTableIsInitialized = false;
let selectedRowData = null;
let productosData = null; // Variable global para almacenar los datos

// updateData();
window.addEventListener('load', async () => {
    uploadData();
});

const handleRowClick = (data) => {
    // const filteredData = data.slice(1);  // Eliminar el primer elemento (indice de la tabla)
    selectedRowData = data;
    console.log("Selected row data:", selectedRowData);
};

document.getElementById('send-data').addEventListener('click', async () => {
    try {
        const response = await fetch('/send_data/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'), // Necesario para CSRF en Django
            },
            body: JSON.stringify({ selectedRows: selectedRowData }),
        });
        const result = await response.json();
        console.log(result);
        if (result.status === "success") {
            await initChart(); // Volver a cargar el gráfico después de enviar los datos
        }
    } catch (e) {
        console.error("Error sending data: ", e);
        alert("Por favor selecciona una fila de la tabla para generar la gráfica");
    }
});

// Función para exportar datos visibles del DataTable
document.getElementById('export-visible').addEventListener('click', function () {
    // Crear un nuevo libro de trabajo
    const wb = XLSX.utils.book_new();

    // Obtener todos los datos actualmente filtrados y visibles en el DataTable
    const filteredData = dataTable.rows({ filter: 'applied' }).data().toArray();
    console.log("Datos filtrados:", filteredData);

    // Índices de las columnas que deseas exportar (empezando desde 0)
    const columnsToExport = [0, 2, 3, 4, 5, 6, 7, 10, 11, 12, 13]; // columnas a exportar
    // const columnsToExport2 = [0, 1, 2, 3, 4, 5]; // nombre columnas 

    // Recolectar encabezados de las columnas seleccionadas
    const headers = ['REG.N12', 'BODEGA.C5', 'PRODUCTO.C15', 'CODCMC.C50', 'NOMBRE.C100', 'UNIMED.C4', 'LOTEPRO.C12', 'CANTIDAD.N20', 'CANTIDAD.N20', 'PRECIO_UNITARIO.N20', 'FECHAENTREGA.C10'];
    // $('#datatable-productos thead th').each(function (index) {
    //     if (columnsToExport2.includes(index)) {
    //         headers.push($(this).text());
    //     }
    // });

    // Convertir los datos filtrados en un formato adecuado para la exportación
    const exportData = [headers]; // Incluir encabezados como la primera fila
    filteredData.forEach(row => {
        const rowData = [];
        columnsToExport.forEach((colIndex) => {
            rowData.push(row[colIndex]);
        });
        exportData.push(rowData);
    });

    // Crear una nueva hoja de trabajo con los datos filtrados
    const ws = XLSX.utils.aoa_to_sheet(exportData);

    // Añadir la hoja de trabajo al libro
    XLSX.utils.book_append_sheet(wb, ws, 'Datos_Productos');

    //obtener fecha actual 
    const fechaActual = new Date();
    const year = fechaActual.getFullYear();
    const mes = String(fechaActual.getMonth() + 1).padStart(2, '0'); // Los meses empiezan en 0
    const dia = String(fechaActual.getDate()).padStart(2, '0');

    const fechaFormateada = `${dia}/${mes}/${year}`;
    const nombreArchivo = `Datos_filtrados_${fechaFormateada}.xlsx`;
    // Guardar el archivo Excel
    XLSX.writeFile(wb, nombreArchivo);
});

// Función para exportar todos los datos del DataTable
// document.getElementById('export-all').addEventListener('click', function () {
//     // Índices de las columnas que deseas exportar (empezando desde 0)
//     const columnsToExport = [0, 2, 3, 4, 5, 6, 7, 10, 11, 12, 13];
    
//     // Obtener todos los datos del json productosData
//     const data = productosData.productos.map(producto => { 
//         return [
//             producto.id,
//             producto.bodega,
//             producto.item,
//             producto.codigo,
//             producto.producto,
//             producto.unimed,
//             producto.lotepro,
//             producto.cantidad,
//             producto.cantidad_2_meses,
//             producto.precio,
//             producto.fechaentrega,
//         ];
//     });

//     // Recolectar encabezados de las columnas seleccionadas
//     const headers = ['REG.N12', 'BODEGA.C5', 'PRODUCTO.C15', 'CODCMC.C50', 'NOMBRE.C100', 'UNIMED.C4', 'LOTEPRO.C12', 'CANTIDAD.N20', 'CANTIDAD.N20', 'PRECIO_UNITARIO.N20', 'FECHAENTREGA.C10'];

//     // Recolectar todos los datos en formato Array of Arrays
//     const exportData = [headers];
//     data.forEach(row => {
//         const rowData = [];
//         columnsToExport.forEach(colIndex => {
//             rowData.push(row[colIndex]);
//         });
//         exportData.push(rowData);
//     });

//     // Crear hoja de cálculo
//     const wb = XLSX.utils.book_new();
//     const ws = XLSX.utils.aoa_to_sheet(exportData);
//     XLSX.utils.book_append_sheet(wb, ws, 'Datos_Productos');
//     XLSX.writeFile(wb, 'Datos_Productos.xlsx');
// });

// Añadir el evento para actualizar los datos
// async function updateData(){
//     const myElement = document.getElementById('chart');
//     myElement.style.display = 'none';
//     productosData = null; // Limpiar los datos almacenados
//     if (!productosData) {
//         const loader = document.querySelector('.spinner-border');
//         try {
//             loader.style.display = 'block';
//             const response = await fetch('/lista/');
//             productosData = await response.json();
//         } catch (error) {
//             console.error('Error al obtener los datos:', error);
//         } finally {
//             loader.style.display = 'none';
//         }
//     }
// };

// Actualizar cada 10 segundos
// setInterval(updateData, 2000);

// función para cargar los datos
async function uploadData() {
    productosData = null; // Limpiar los datos almacenados
    if (!productosData) {
        const loader = document.querySelector('.spinner-border');
        try {
            loader.style.display = 'block';
            const response = await fetch('/lista/');
            productosData = await response.json();
        } catch (error) {
            console.error('Error al obtener los datos:', error);
        } finally {
            loader.style.display = 'none';
        }
    }
};

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

const dataTableOptions = {
    dom: 'Brtip', // Agregar el control de paneles de búsqueda
    buttons: [
        {
            extend: 'pageLength',
            text: 'Mostrar',
            //className: 'btn btn-info',
            titleAttr: 'Paginación',
        },
    ],
    select: true,
    language: {
        "select": {
            "rows": {
                "1": "1 fila seleccionada",
                "_": "%d filas seleccionadas"
            }
        },
        "processing": "Procesando...",
        "lengthMenu": "Mostrar _MENU_ registros",
        "zeroRecords": "No se encontraron resultados",
        "emptyTable": "Ningún dato disponible en esta tabla",
        "infoEmpty": "Mostrando registros del 0 al 0 de un total de 0 registros",
        "infoFiltered": "(filtrado de un total de _MAX_ registros)",
        "search": "Buscar:",
        "loadingRecords": "Cargando...",
        "info": "Mostrando _START_ a _END_ de _TOTAL_ registros",
    },

    columnDefs: [
        { className: 'centered', targets: '_all' },
        { targets: [0, 1, 2, 4, 6, 7, 12, 13], visible: false, searchable: false },
    ],
};

const initDataTable = async (datos) => {
    if (dataTableIsInitialized) dataTable.destroy();

    // await listProductos();
    //dataTable = $('#datatable-productos').DataTable(dataTableOptions);
    const loader = document.querySelector('.spinner-border');
    try {
        loader.style.display = 'block';
        await listProductos(datos);
        dataTable = $('#datatable-productos').DataTable({
            ...dataTableOptions,

            createdRow: function (row, data, dataIndex) {
                $(row).click(function () {
                    handleRowClick(data);
                });
            }
        });
    } catch (e) {
        alert(e);
    } finally {
        // Ocultar el loader
        // document.getElementById('loader').style.display = 'none';
        loader.style.display = 'none';
    }

    // Handle click outside the table to deselect the row
    // $(document).on('click', function (e) {
    //     const container = $("#datatable-productos");
    //     if (!container.is(e.target) && container.has(e.target).length === 0) {
    //         dataTable.rows().deselect();
    //         selectedRowData = null; // Clear the selected row data
    //     }
    // });

    dataTableIsInitialized = true;
};

const listProductos = async (datos) => {
    const loader = document.querySelector('.spinner-border');
    try {
        loader.style.display = 'block';
        // Mostrar el loader
        // document.getElementById('loader').style.display = 'block';

        //obtener fecha actual en formato yyyy-mm-dd
        const fechaActual = new Date();
        const year = fechaActual.getFullYear();
        const mes = String(fechaActual.getMonth() + 1).padStart(2, '0'); // Los meses empiezan en 0
        const dia = String(fechaActual.getDate()).padStart(2, '0');

        const fechaFormateada = `${year}/${mes}/${dia}`;

        let content = ``;
        datos.productos.forEach((producto, index) => {
            content += `
                <tr>
                    <td>${index + 1}</td>
                    <td>${producto.id}</td>
                    <td>${producto.bodega}</td>
                    <td>${producto.item}</td>
                    <td>${producto.codigo}</td>
                    <td>${producto.producto}</td>
                    <td>${producto.unimed}</td>
                    <td>${producto.lotepro}</td>
                    <td>${producto.proveedor}</td>
                    <td>${producto.sede}</td>
                    <td>${producto.cantidad}</td>
                    <td>${producto.cantidad_2_meses}</td>
                    <td>${producto.precio}</td>
                    <td>${fechaFormateada}</td>
                </tr>
            `;
        });
        const table = document.getElementById('tableBody_productos');
        table.innerHTML = content;
    } catch (e) {
        alert(e);
    } finally {
        // Ocultar el loader
        // document.getElementById('loader').style.display = 'none';
        loader.style.display = 'none';
    }
};

//GRAFICO
const getOptionChart = async () => {
    try {
        const response = await fetch('/chart/');
        return await response.json();
    } catch (e) {
        alert(e)
    }
};

const initChart = async () => {
    const myChart = echarts.init(document.getElementById('chart'));
    const myElement = document.getElementById('chart');
    myElement.style.display = 'block';
    myChart.setOption(await getOptionChart());
    myChart.resize();
};

document.getElementById('search').addEventListener('click', async () => {
    
    const selectedItems = getSelectedValues('select-options-items', 'select-all-items');
    const selectedProveedores = getSelectedValues('select-options-proveedores', 'select-all-proveedores');
    const selectedProductos = getSelectedValues('select-options-productos', 'select-all-productos');
    const selectedSedes = getSelectedValues('select-options-sedes', 'select-all-sedes');
    
    function filter(data, items, proveedores, productos, sedes) {
        // Convertir arrays de selección a números (para el filtro de Items)
        items = items.map(Number);

        // Filtrar los productos que coincidan con todos los criterios seleccionados
        return data.productos.filter(producto => {
            // Verificar que el producto cumpla con todos los criterios seleccionados
            const matchItems = items.length === 0 || items.includes(producto.item);
            const matchProveedores = proveedores.length === 0 || proveedores.includes(producto.proveedor);
            const matchProductos = productos.length === 0 || productos.includes(producto.producto);
            const matchSedes = sedes.length === 0 || sedes.includes(producto.sede);

            return matchItems && matchProveedores && matchProductos && matchSedes;
        });
    }
    const dataFilter = filter(productosData, selectedItems, selectedProveedores, selectedProductos, selectedSedes);
    //convertir a json y asignar
    const datos = { "productos": dataFilter };
    console.log("Filtros aplicados:", datos);

    await initDataTable(datos);
});

document.addEventListener('DOMContentLoaded', () => {
    setupFilter('item-search', 'select-all-items');
    setupFilter('proveedor-search', 'select-all-proveedores');
    setupFilter('producto-search', 'select-all-productos');
    setupFilter('sede-search', 'select-all-sedes');
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

    document.getElementById('cancel').addEventListener('click', () => {
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


//configurar modo oscuro
// document.getElementById('mode-toggle').addEventListener('click', function () {
//     document.body.classList.toggle('dark-mode');
//     document.body.classList.toggle('light-mode');
//     const tables = document.querySelectorAll('.table');
//     tables.forEach(table => {
//         table.classList.toggle('dark-mode');
//         table.classList.toggle('light-mode');
//     });
//     const charts = document.querySelectorAll('.chart');
//     charts.forEach(chart => {
//         chart.classList.toggle('dark-mode');
//         chart.classList.toggle('light-mode');
//     });
//     // Cambiar el texto del botón
//     if (document.body.classList.contains('dark-mode')) {
//         this.textContent = 'Modo Claro';
//     } else {
//         this.textContent = 'Modo Oscuro';
//     }
// });
