let dataTable;
let dataTableIsInitialized = false;
let selectedRowData = null;
let productosData = null; // Variable global para almacenar los datos

const handleRowClick = (data) => {
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

    // Índices de las columnas que deseas exportar (empezando desde 0)
    const columnsToExport = [1, 2, 3, 4, 9, 10]; // Cambia estos valores según tus necesidades
    const columnsToExport2 = [0, 1, 2, 3, 4, 5]; // nombre columnas visibles en el datatable

    // Recolectar encabezados de las columnas seleccionadas
    const headers = [];
    $('#datatable-productos thead th').each(function (index) {
        if (columnsToExport2.includes(index)) {
            headers.push($(this).text());
        }
    });

    // Convertir los datos filtrados en un formato adecuado para la exportación
    const exportData = [headers]; // Incluir encabezados como la primera fila
    filteredData.forEach(row => {
        const rowData = [];
        columnsToExport.forEach(colIndex => {
            rowData.push(row[colIndex]);
        });
        exportData.push(rowData);
    });

    // Crear una nueva hoja de trabajo con los datos filtrados
    const ws = XLSX.utils.aoa_to_sheet(exportData);

    // Añadir la hoja de trabajo al libro
    XLSX.utils.book_append_sheet(wb, ws, 'Datos_Productos');

    // Guardar el archivo Excel
    XLSX.writeFile(wb, 'Datos_Productos_Filtrados.xlsx');
});

// Función para exportar todos los datos del DataTable
document.getElementById('export-all').addEventListener('click', function () {
    // Índices de las columnas que deseas exportar (empezando desde 0)
    const columnsToExport = [1, 2, 3, 4, 9, 10]; // Cambia estos valores según tus necesidades
    const columnsToExport2 = [0, 1, 2, 3, 4, 5]; // nombre columnas visibles en el datatable
    // Obtener todos los datos del DataTable
    const data = dataTable.rows().data().toArray();

    // Recolectar encabezados de las columnas seleccionadas
    const headers = [];
    $('#datatable-productos thead th').each(function (index) {
        if (columnsToExport2.includes(index)) {
            headers.push($(this).text());
        }
    });

    // Recolectar todos los datos en formato Array of Arrays
    const exportData = [headers];
    data.forEach(row => {
        const rowData = [];
        columnsToExport.forEach(colIndex => {
            rowData.push(row[colIndex]);
        });
        exportData.push(rowData);
    });

    // Crear hoja de cálculo
    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.aoa_to_sheet(exportData);
    XLSX.utils.book_append_sheet(wb, ws, 'Datos_Productos');
    XLSX.writeFile(wb, 'Datos_Productos.xlsx');
});

// Añadir el evento para actualizar los datos
document.getElementById('update-data').addEventListener('click', async () => {
    const myElement = document.getElementById('chart');
    myElement.style.display = 'none';
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

});

// ------------------------------------------------------------------------------------
// Arreglos para almacenar las selecciones
let selectedItems = [];
let selectedProveedores = [];
let selectedProductos = [];
let selectedSedes = [];

document.getElementById('search').addEventListener('click', async () => {

    // Función para filtrar por Items
    function filterByItems(data, items) {
        //convertir a entero
        items = items.map(Number);
        return data.productos.filter(producto => items.includes(producto.Items));
    }
    // Función para filtrar por Proveedor
    function filterByProveedor(data, proveedores) {
        return data.productos.filter(producto => proveedores.includes(producto.Proveedor));
    }
    // Función para filtrar por Productos
    function filterByProductos(data, productos) {
        return data.productos.filter(producto => productos.includes(producto.Productos));
    }
    // Función para filtrar por Sede
    function filterBySede(data, sedes) {
        return data.productos.filter(producto => sedes.includes(producto.Sede));
    }

    //filtrar por item, proovedor, producto o sede
    function filterBy(data, items, proveedores, productos, sedes) {
        // Convertir arrays de selección a números (para el filtro de Items)
        items = items.map(Number);

        // Filtrar los productos que coincidan con todos los criterios seleccionados
        return data.productos.filter(producto => {
            // Verificar que el producto cumpla con todos los criterios seleccionados
            const matchItems = items.length === 0 || items.includes(producto.Items);
            const matchProveedores = proveedores.length === 0 || proveedores.includes(producto.Proveedor);
            const matchProductos = productos.length === 0 || productos.includes(producto.Productos);
            const matchSedes = sedes.length === 0 || sedes.includes(producto.Sede);

            return matchItems && matchProveedores && matchProductos && matchSedes;
        });
    }

    const dataFilter = filterBy(productosData, selectedItems, selectedProveedores, selectedProductos, selectedSedes);
    //convertir a json y asignar
    const datos = { "productos": dataFilter };
    console.log("Filtros aplicados:", datos);

    // console.log("Filtrado por Items:", filteredByItems);
    await initDataTable(datos);

});

// Función para manejar el cambio de selección
function handleSelectChange(event, selectedArray) {
    // Obtener los valores seleccionados
    const selectedValues = Array.from(event.target.selectedOptions).map(option => option.value);

    //comprobar que se esten seleccionando valores


    // Actualizar el arreglo correspondiente
    // selectedArray.length = 0; // Vaciar el arreglo actual
    selectedArray.push(...selectedValues); // Añadir los valores seleccionados

    //imprimir el arreglo de filtros
    console.log("Filtros aplicados:", selectedArray);
}

document.getElementById('show').addEventListener('click', () => {
    console.log("Filtros items:", selectedItems);
    console.log("Filtros proveedores:", selectedProveedores);
    console.log("Filtros productos:", selectedProductos);
    console.log("Filtros sedes:", selectedSedes);
});

// Asociar el evento `change` a cada elemento `<select>`
// document.getElementById('item').addEventListener('change', (event) => {
//     handleSelectChange(event, selectedItems);
// });
// document.getElementById('proveedor').addEventListener('change', (event) => {
//     handleSelectChange(event, selectedProveedores);
// });
// document.getElementById('producto').addEventListener('change', (event) => {
//     handleSelectChange(event, selectedProductos);
// });
// document.getElementById('sede').addEventListener('change', (event) => {
//     handleSelectChange(event, selectedSedes);
// });

// verificar que se esten seleccionando valores de un filtro
// const item = document.getElementById('item').addEventListener('change', (event) => {
//     if (event.target.selectedOptions.length > 0) {
//         console.log('Items seleccionados:', event.target.selectedOptions.length);
//     } else {
//         console.log('No se han seleccionado items');
//     }
// });
// const proveedor = document.getElementById('proveedor').addEventListener('change', (event) => {
//     console.log('item', item);

//     if (event.target.selectedOptions.length > 0) {
//         console.log('Proveedores seleccionados:', event.target.selectedOptions.length);
//     } else {
//         console.log('No se han seleccionado proveedores');
//     }
// });


// Guardar selecciones cada vez que cambien
document.getElementById('item').addEventListener('change', (event) => {
    const items = Array.from(event.target.selectedOptions).map(option => option.value);
    localStorage.setItem('items', JSON.stringify(items));
    selectedItems = localStorage.getItem('items');
    console.log('item', localStorage.getItem('items'));
    console.log('proveedor', localStorage.getItem('proveedores'));
});
document.getElementById('proveedor').addEventListener('change', (event) => {
    const proveedores = Array.from(event.target.selectedOptions).map(option => option.value);
    localStorage.setItem('proveedores', JSON.stringify(proveedores));
    selectedProveedores = localStorage.getItem('proveedores');
    console.log('item', localStorage.getItem('items'));
    console.log('proveedor', localStorage.getItem('proveedores'));
});

function restoreSelections() {
    
    //eliminar los valores del localstorage
    localStorage.removeItem('items');
    localStorage.removeItem('proveedores');

    console.log("Selecciones restauradas desde localStorage.");
}


document.getElementById('clear').addEventListener('click', () => {
    
    console.log('item', localStorage.getItem('items'));
    console.log('proveedor', localStorage.getItem('proveedores'));
    // Limpiar selecciones
    restoreSelections();
    console.log('item', localStorage.getItem('items'));
    console.log('proveedor', localStorage.getItem('proveedores'));
});

//------------------------------------------------------------------------------------
// Añadir el evento para la búsqueda de filtros
document.addEventListener('DOMContentLoaded', function () {
    setupSearch('items-search', 'item');
    setupSearch('proveedor-search', 'proveedor');
    setupSearch('producto-search', 'producto');
    setupSearch('sede-search', 'sede');
});

// Función para configurar la búsqueda de elementos en una lista
function setupSearch(inputId, listId) {
    const searchInput = document.getElementById(inputId);
    const resultList = document.getElementById(listId);
    const items = resultList.getElementsByTagName('option');

    searchInput.addEventListener('keyup', function () {
        const filter = searchInput.value.toUpperCase();

        for (let i = 0; i < items.length; i++) {
            const item = items[i];
            const txtValue = item.textContent || item.innerText;

            if (txtValue.toUpperCase().includes(filter)) {
                item.style.display = "";
            } else {
                item.style.display = "none";
            }
        }
    });
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

const dataTableOptions = {
    dom: 'Brtip', // Agregar el control de paneles de búsqueda B: Buttons, r: processing, t: tabla, i: información, p: paginación
    buttons: [
        {
            extend: 'pageLength',
            text: 'Paginación',
            //className: 'btn btn-info',
            titleAttr: 'Paginación',
        },
    ],
    select: true,
    language: {
        "searchPanes": {
            "clearMessage": "Borrar todo",
            "collapse": {
                "0": "Paneles de búsqueda",
                "_": "Paneles de búsqueda (%d)"
            },
            "count": "{total}",
            "countFiltered": "{shown} ({total})",
            "emptyPanes": "Sin paneles de búsqueda",
            "loadMessage": "Cargando paneles de búsqueda",
            "title": "Filtros Activos - %d",
            "showMessage": "Mostrar Todo",
            "collapseMessage": "Ocultar Todo"
        },
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
        { targets: [0, 5, 6, 7, 8, 11], visible: false, searchable: false },
    ],
};

const initDataTable = async (datos) => {
    if (dataTableIsInitialized) dataTable.destroy();

    // await listProductos();
    //dataTable = $('#datatable-productos').DataTable(dataTableOptions);

    await listProductos(datos);
    dataTable = $('#datatable-productos').DataTable({
        ...dataTableOptions,

        createdRow: function (row, data, dataIndex) {
            $(row).click(function () {
                handleRowClick(data);
            });
        }
    });

    // Handle click outside the table to deselect the row
    $(document).on('click', function (e) {
        const container = $("#datatable-productos");
        if (!container.is(e.target) && container.has(e.target).length === 0) {
            dataTable.rows().deselect();
            selectedRowData = null; // Clear the selected row data
        }
    });

    dataTableIsInitialized = true;
};

const listProductos = async (datos) => {
    const loader = document.querySelector('.spinner-border');
    try {
        // Mostrar el loader
        // document.getElementById('loader').style.display = 'block';
        loader.style.display = 'block';


        let content = ``;
        datos.productos.forEach((producto, index) => {
            content += `
                <tr>
                    <td>${index + 1}</td>
                    <td>${producto.Items}</td>
                    <td>${producto.Proveedor}</td>
                    <td>${producto.Productos}</td>
                    <td>${producto.Sede}</td>
                    <td>${producto.MAD}</td>
                    <td>${producto.MAPE}</td>
                    <td>${producto.MAPE_PRIMA}</td>
                    <td>${producto.ECM}</td>
                    <td>${producto.Pronostico}</td>
                    <td>${producto.Pronostico_2_meses}</td>
                    <td>${producto.Pronostico_seleccionado}</td>
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

window.addEventListener('load', async () => {
    // await initDataTable();
});

//configurar modo oscuro
document.getElementById('mode-toggle').addEventListener('click', function () {
    document.body.classList.toggle('dark-mode');
    document.body.classList.toggle('light-mode');
    const tables = document.querySelectorAll('.table');
    tables.forEach(table => {
        table.classList.toggle('dark-mode');
        table.classList.toggle('light-mode');
    });
    const charts = document.querySelectorAll('.chart');
    charts.forEach(chart => {
        chart.classList.toggle('dark-mode');
        chart.classList.toggle('light-mode');
    });
    // Cambiar el texto del botón
    if (document.body.classList.contains('dark-mode')) {
        this.textContent = 'Modo Claro';
    } else {
        this.textContent = 'Modo Oscuro';
    }
});