let dataTable;
let dataTableIsInitialized = false;
let selectedRowData = null;

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
    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.table_to_sheet(document.getElementById('datatable-productos'));
    XLSX.utils.book_append_sheet(wb, ws, 'Datos_Productos');
    XLSX.writeFile(wb, 'Datos_Productos.xlsx');
});

// Función para exportar todos los datos del DataTable
document.getElementById('export-all').addEventListener('click', function () {
    // Obtener todos los datos del DataTable
    const data = dataTable.rows().data().toArray();

    // Recolectar encabezados
    const headers = [];
    $('#datatable-productos thead th').each(function () {
        headers.push($(this).text());
    });

    // Recolectar todos los datos en formato Array of Arrays
    const exportData = [headers];
    data.forEach(row => {
        const rowData = [];
        for (let key in row) {
            if (row.hasOwnProperty(key)) {
                rowData.push(row[key]);
            }
        }
        exportData.push(rowData);
    });

    // Crear hoja de cálculo
    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.aoa_to_sheet(exportData);
    XLSX.utils.book_append_sheet(wb, ws, 'Datos_Productos');
    XLSX.writeFile(wb, 'Datos_Productos.xlsx');
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
    columnDefs: [
        { className: 'centered', targets: '_all' },
    ],
    select: true,
    // dom: 'Bfrtip', // Agregar el control de botones
    // buttons: [
    //     {
    //         extend: 'pageLength',
    //         text: 'Paginación',
    //         className: 'btn btn-info',
    //         titleAttr: 'Paginación',
    //     },
    // ],

};

const initDataTable = async () => {
    if (dataTableIsInitialized) dataTable.destroy();

    // await listProductos();
    // dataTable = $('#datatable-productos').DataTable(dataTableOptions);

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
    try {
        // Mostrar el loader
        document.getElementById('loader').style.display = 'block';

        const response = await fetch('http://127.0.0.1:8000/lista/');
        const data = await response.json();

        let content = ``;
        data.productos.forEach((producto, index) => {
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
        document.getElementById('loader').style.display = 'none';
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
    // await initChart();
    await initDataTable();
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