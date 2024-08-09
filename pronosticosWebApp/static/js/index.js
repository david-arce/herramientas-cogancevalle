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
    productosData = null; // Limpiar los datos almacenados
    await initDataTable(); // Volver a inicializar la tabla con datos nuevos
});

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
    dom: 'PBfrtip', // Agregar el control de paneles de búsqueda
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
    searchPanes: {
        cascadePanes: true
    },
    columnDefs: [
        {
            searchPanes: {
                show: false,
            },
            targets: [0, 5, 6, 7, 8, 9, 10, 11]
        },
        { className: 'centered', targets: '_all' },
        { targets: [0, 5, 6, 7, 8, 11], visible: false, searchable: false },
    ],
};

const initDataTable = async () => {
    if (dataTableIsInitialized) dataTable.destroy();

    // await listProductos();
    //dataTable = $('#datatable-productos').DataTable(dataTableOptions);

    await listProductos();
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

const listProductos = async () => {
    const loader = document.querySelector('.spinner-border');
    try {
        // Mostrar el loader
        // document.getElementById('loader').style.display = 'block';
        loader.style.display = 'block';

        if (!productosData) {  // Si los datos aún no se han cargado
            const response = await fetch('http://127.0.0.1:8000/lista/');
            productosData = await response.json();
        }

        let content = ``;
        productosData.productos.forEach((producto, index) => {
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
        const response = await fetch('http://127.0.0.1:8000/chart/');
        return await response.json();
    } catch (e) {
        alert(e)
    }
};

const initChart = async () => {
    const myChart = echarts.init(document.getElementById('chart'));

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