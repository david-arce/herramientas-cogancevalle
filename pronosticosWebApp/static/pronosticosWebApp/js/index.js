let dataTable;
let dataTableIsInitialized = false;
let selectedRowData = null;
let productosData = null; // Variable global para almacenar los datos

const handleRowClick = (data) => {
    // const filteredData = data.slice(1);  // Eliminar el primer elemento (indice de la tabla)
    selectedRowData = data;
    console.log("Selected row data:", selectedRowData);
};

document.getElementById('send-data').addEventListener('click', async () => {
    try {
        const modal = document.getElementById("processingModal");
        modal.style.display = "block";  // Mostrar el modal
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
            modal.style.display = "none";  // Ocultar el modal
        }
        else {
            modal.style.display = "none";  // Ocultar el modal
            alert("No se pudo generar el gráfico. Intenta de nuevo.");
        }
    } catch (e) {
        console.error("Error sending data: ", e);
        modal.style.display = "none";
        alert("Por favor selecciona una fila de la tabla para generar la gráfica");
    }
});

// Función para exportar datos visibles del DataTable
document.getElementById('export-visible').addEventListener('click', function () {
    // Crear un nuevo libro de trabajo
    const wb = XLSX.utils.book_new();

    // Obtener todos los datos actualmente filtrados y visibles en el DataTable
    const filteredData = dataTable.rows({ filter: 'applied' }).data().toArray();

    // Recorrer los datos filtrados y cambiar los valores en los índices 10, 11 y 12 a enteros
    const updatedData = filteredData.map(row => {
        row[9] = parseInt(row[9], 10);  // Convertir a entero el índice 9
        row[10] = parseInt(row[10], 10);  // Convertir a entero el índice 10
        row[11] = parseInt(row[11], 10);  // Convertir a entero el índice 11
        row[12] = parseInt(row[12], 10);  // Convertir a entero el índice 12
        return row;
    });

    // Índices de las columnas que deseas exportar (empezando desde 0)
    const columnsToExport = [0, 1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13]; // columnas a exportar
    // const columnsToExport2 = [0, 1, 2, 3, 4, 5]; // nombre columnas 

    // Recolectar encabezados de las columnas seleccionadas
    const headers = ['REG.N12', 'BODEGA.C5', 'PRODUCTO.C15', 'CODCMC.C50', 'NOMBRE.C100', 'UNIMED.C4', 'LOTEPRO.C12', 'CANTIDAD.N20', 'CANTIDAD.N20', 'CANTIDAD.N20', 'PRECIO_UNITARIO.N20', 'FECHAENTREGA.C10'];
    // $('#datatable-productos thead th').each(function (index) {
    //     if (columnsToExport2.includes(index)) {
    //         headers.push($(this).text());
    //     }
    // });

    // Convertir los datos filtrados en un formato adecuado para la exportación
    const exportData = [headers]; // Incluir encabezados como la primera fila
    let index = 1; // Iniciar índice desde 1
    updatedData.forEach(row => {
        const rowData = [];
        columnsToExport.forEach((colIndex, i) => {
            if (i === 0) {
                // Primera columna: índice reiniciado
                rowData.push(index++);
            } else {
                rowData.push(row[colIndex]);
            }
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

/*
document.getElementById('export-visible').addEventListener('click', function () {
    const wb = XLSX.utils.book_new();
    const filteredData = dataTable.rows({ filter: 'applied' }).data().toArray();

    const updatedData = filteredData.map(row => {
        row[9] = parseInt(row[9], 10);
        row[10] = parseInt(row[10], 10);
        row[11] = parseInt(row[11], 10);
        row[12] = parseInt(row[12], 10);
        return row;
    });

    const columnsToExport = [0, 1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13];

    const headers = [
        'REG.N12', 'BODEGA.C5', 'PRODUCTO.C15', 'CODCMC.C50', 'NOMBRE.C100',
        'UNIMED.C4', 'LOTEPRO.C12', 'CANTIDAD.N20', 'CANTIDAD.N20',
        'CANTIDAD.N20', 'PRECIO_UNITARIO.N20', 'FECHAENTREGA.C10',
        'MULTIPLO_BASE.C20'  // nueva columna
    ];

    // Diccionario de múltiplos (misma estructura que MULTIPLOS_BASE_COL en Python)
    const MULTIPLOS_BASE_COL = {
        // Comodines - todos stock_seguridad
        'ALL VET|*':             'stock_seguridad',
        'BIOS|*':                'stock_seguridad',
        'FAB. Y MERCADEO|*':     'stock_seguridad',
        'FERCON|*':              'stock_seguridad',
        'FERRAGRO|*':             'stock_seguridad',
        'HERRADURA LA MONTANA|*':'stock_seguridad',
        'INSMEVET|*':            'stock_seguridad',
        'LHAURA|*':              'stock_seguridad',
        'QUIMPAC|*':             'stock_seguridad',
        'RENTASAL|*':            'stock_seguridad',
        'VITALES|*':             'stock_seguridad',
        
    // ALL VET
    'ALL VET|11485': 'stock_seguridad',
    'ALL VET|11267': 'stock_seguridad',
    'ALL VET|12120': 'stock_seguridad',
    'ALL VET|12121': 'stock_seguridad',
    'ALL VET|11268': 'stock_seguridad',
    'ALL VET|11852': 'stock_seguridad',
    'ALL VET|11269': 'stock_seguridad',
    'ALL VET|11484': 'stock_seguridad',
    'ALL VET|11851': 'stock_seguridad',
    'ALL VET|11334': 'stock_seguridad',
    'ALL VET|11333': 'stock_seguridad',
    'ALL VET|11270': 'stock_seguridad',
    'ALL VET|11271': 'stock_seguridad',
    'ALL VET|11272': 'stock_seguridad',
    'ALL VET|11319': 'stock_seguridad',
    'ALL VET|11312': 'stock_seguridad',
    'ALL VET|11273': 'stock_seguridad',
    'ALL VET|11274': 'stock_seguridad',
    'ALL VET|11276': 'stock_seguridad',
    'ALL VET|11275': 'stock_seguridad',
    'ALL VET|12196': 'stock_seguridad',
    'ALL VET|11970': 'stock_seguridad',
    'ALL VET|11331': 'stock_seguridad',
    'ALL VET|11332': 'stock_seguridad',
    'ALL VET|11850': 'stock_seguridad',
    'ALL VET|11277': 'stock_seguridad',
    'ALL VET|11323': 'stock_seguridad',

    // BIOS
    'BIOS|4721': 'stock_seguridad',
    'BIOS|3889': 'stock_seguridad',
    'BIOS|5185': 'stock_seguridad',
    'BIOS|3890': 'stock_seguridad',
    'BIOS|10392': 'stock_seguridad',
    'BIOS|3891': 'stock_seguridad',
    'BIOS|11584': 'stock_seguridad',

    // FAB. Y MERCADEO
    'FAB. Y MERCADEO|3892': 'stock_seguridad',
    'FAB. Y MERCADEO|5550': 'stock_seguridad',
    'FAB. Y MERCADEO|4459': 'stock_seguridad',
    'FAB. Y MERCADEO|4460': 'stock_seguridad',
    'FAB. Y MERCADEO|4458': 'stock_seguridad',
    'FAB. Y MERCADEO|6502': 'stock_seguridad',
    'FAB. Y MERCADEO|5552': 'stock_seguridad',
    'FAB. Y MERCADEO|6239': 'stock_seguridad',
    'FAB. Y MERCADEO|5551': 'stock_seguridad',
    'FAB. Y MERCADEO|6238': 'stock_seguridad',

    // FERCON
    'FERCON|8855': 'stock_seguridad',
    'FERCON|8848': 'stock_seguridad',
    'FERCON|8801': 'stock_seguridad',
    'FERCON|1448': 'stock_seguridad',
    'FERCON|1449': 'stock_seguridad',
    'FERCON|4884': 'stock_seguridad',
    'FERCON|8854': 'stock_seguridad',
    'FERCON|1450': 'stock_seguridad',
    'FERCON|8764': 'stock_seguridad',
    'FERCON|9206': 'stock_seguridad',
    'FERCON|9210': 'stock_seguridad',
    'FERCON|2675': 'stock_seguridad',
    'FERCON|2676': 'stock_seguridad',
    'FERCON|9592': 'stock_seguridad',
    'FERCON|4284': 'stock_seguridad',
    'FERCON|5785': 'stock_seguridad',
    'FERCON|2678': 'stock_seguridad',
    'FERCON|8891': 'stock_seguridad',
    'FERCON|10631': 'stock_seguridad',
    'FERCON|9475': 'stock_seguridad',
    'FERCON|2674': 'stock_seguridad',
    'FERCON|9209': 'stock_seguridad',
    'FERCON|9594': 'stock_seguridad',
    'FERCON|8897': 'stock_seguridad',
    'FERCON|8892': 'stock_seguridad',
    'FERCON|8898': 'stock_seguridad',
    'FERCON|10161': 'stock_seguridad',
    'FERCON|8899': 'stock_seguridad',
    'FERCON|8909': 'stock_seguridad',
    'FERCON|8907': 'stock_seguridad',
    'FERCON|8908': 'stock_seguridad',
    'FERCON|8906': 'stock_seguridad',
    'FERCON|9250': 'stock_seguridad',
    'FERCON|9595': 'stock_seguridad',
    'FERCON|5786': 'stock_seguridad',
    'FERCON|8902': 'stock_seguridad',
    'FERCON|9205': 'stock_seguridad',
    'FERCON|2686': 'stock_seguridad',
    'FERCON|4278': 'stock_seguridad',
    'FERCON|9596': 'stock_seguridad',
    'FERCON|5790': 'stock_seguridad',
    'FERCON|9249': 'stock_seguridad',
    'FERCON|9629': 'stock_seguridad',
    'FERCON|8893': 'stock_seguridad',
    'FERCON|8903': 'stock_seguridad',
    'FERCON|8904': 'stock_seguridad',
    'FERCON|8905': 'stock_seguridad',
    'FERCON|1458': 'stock_seguridad',
    'FERCON|1468': 'stock_seguridad',
    'FERCON|2682': 'stock_seguridad',
    'FERCON|4491': 'stock_seguridad',
    'FERCON|8939': 'stock_seguridad',
    'FERCON|8900': 'stock_seguridad',
    'FERCON|8894': 'stock_seguridad',
    'FERCON|4287': 'stock_seguridad',
    'FERCON|9597': 'stock_seguridad',
    'FERCON|8895': 'stock_seguridad',
    'FERCON|9208': 'stock_seguridad',
    'FERCON|8941': 'stock_seguridad',
    'FERCON|9683': 'stock_seguridad',
    'FERCON|9598': 'stock_seguridad',
    'FERCON|9204': 'stock_seguridad',
    'FERCON|4886': 'stock_seguridad',
    'FERCON|9599': 'stock_seguridad',
    'FERCON|9396': 'stock_seguridad',
    'FERCON|4494': 'stock_seguridad',
    'FERCON|8901': 'stock_seguridad',

    // FERRAGRO - 3 MESES
    'FERRAGRO|3219': 'cantidadx3',
    'FERRAGRO|3226': 'cantidadx3',
    'FERRAGRO|3221': 'cantidadx3',
    'FERRAGRO|3224': 'cantidadx3',
    'FERRAGRO|3237': 'cantidadx3',
    'FERRAGRO|3227': 'cantidadx3',
    'FERRAGRO|1738': 'cantidadx3',
    'FERRAGRO|11398': 'cantidadx3',
    'FERRAGRO|1739': 'cantidadx3',
    'FERRAGRO|11614': 'cantidadx3',
    'FERRAGRO|1151': 'cantidadx3',
    'FERRAGRO|1152': 'cantidadx3',
    'FERRAGRO|1153': 'cantidadx3',
    'FERRAGRO|1154': 'cantidadx3',
    'FERRAGRO|1150': 'cantidadx3',
    'FERRAGRO|2356': 'cantidadx3',
    'FERRAGRO|3250': 'cantidadx3',

    // FERRAGRO - SS
    'FERRAGRO|2361': 'stock_seguridad',
    'FERRAGRO|2372': 'stock_seguridad',
    'FERRAGRO|4783': 'stock_seguridad',
    'FERRAGRO|4784': 'stock_seguridad',
    'FERRAGRO|2342': 'stock_seguridad',
    'FERRAGRO|4785': 'stock_seguridad',
    'FERRAGRO|2343': 'stock_seguridad',
    'FERRAGRO|3938': 'stock_seguridad',
    'FERRAGRO|1492': 'stock_seguridad',
    'FERRAGRO|6392': 'stock_seguridad',
    'FERRAGRO|5562': 'stock_seguridad',
    'FERRAGRO|5563': 'stock_seguridad',
    'FERRAGRO|5564': 'stock_seguridad',
    'FERRAGRO|5565': 'stock_seguridad',
    'FERRAGRO|5566': 'stock_seguridad',
    'FERRAGRO|5567': 'stock_seguridad',
    'FERRAGRO|5568': 'stock_seguridad',
    'FERRAGRO|5569': 'stock_seguridad',
    'FERRAGRO|12184': 'stock_seguridad',
    'FERRAGRO|12185': 'stock_seguridad',
    'FERRAGRO|3228': 'stock_seguridad',
    'FERRAGRO|11247': 'stock_seguridad',
    'FERRAGRO|2344': 'stock_seguridad',
    'FERRAGRO|2345': 'stock_seguridad',
    'FERRAGRO|8062': 'stock_seguridad',
    'FERRAGRO|5373': 'stock_seguridad',
    'FERRAGRO|7947': 'stock_seguridad',
    'FERRAGRO|3232': 'stock_seguridad',
    'FERRAGRO|3256': 'stock_seguridad',
    'FERRAGRO|2378': 'stock_seguridad',
    'FERRAGRO|3233': 'stock_seguridad',
    'FERRAGRO|3234': 'stock_seguridad',
    'FERRAGRO|8018': 'stock_seguridad',
    'FERRAGRO|11573': 'stock_seguridad',
    'FERRAGRO|10535': 'stock_seguridad',
    'FERRAGRO|11049': 'stock_seguridad',
    'FERRAGRO|6339': 'stock_seguridad',
    'FERRAGRO|11965': 'stock_seguridad',
    'FERRAGRO|11847': 'stock_seguridad',
    'FERRAGRO|3212': 'stock_seguridad',
    'FERRAGRO|3213': 'stock_seguridad',
    'FERRAGRO|3211': 'stock_seguridad',
    'FERRAGRO|3209': 'stock_seguridad',
    'FERRAGRO|3208': 'stock_seguridad',
    'FERRAGRO|3235': 'stock_seguridad',
    'FERRAGRO|3236': 'stock_seguridad',
    'FERRAGRO|11991': 'stock_seguridad',
    'FERRAGRO|3238': 'stock_seguridad',
    'FERRAGRO|11964': 'stock_seguridad',
    'FERRAGRO|3202': 'stock_seguridad',
    'FERRAGRO|11248': 'stock_seguridad',
    'FERRAGRO|3203': 'stock_seguridad',
    'FERRAGRO|7225': 'stock_seguridad',
    'FERRAGRO|7226': 'stock_seguridad',
    'FERRAGRO|7227': 'stock_seguridad',
    'FERRAGRO|5331': 'stock_seguridad',
    'FERRAGRO|6267': 'stock_seguridad',
    'FERRAGRO|3239': 'stock_seguridad',
    'FERRAGRO|3240': 'stock_seguridad',
    'FERRAGRO|11829': 'stock_seguridad',
    'FERRAGRO|2359': 'stock_seguridad',
    'FERRAGRO|2360': 'stock_seguridad',
    'FERRAGRO|2348': 'stock_seguridad',
    'FERRAGRO|2379': 'stock_seguridad',
    'FERRAGRO|2349': 'stock_seguridad',
    'FERRAGRO|2351': 'stock_seguridad',
    'FERRAGRO|3257': 'stock_seguridad',
    'FERRAGRO|3694': 'stock_seguridad',
    'FERRAGRO|3242': 'stock_seguridad',
    'FERRAGRO|3244': 'stock_seguridad',
    'FERRAGRO|3245': 'stock_seguridad',
    'FERRAGRO|3247': 'stock_seguridad',
    'FERRAGRO|12242': 'stock_seguridad',
    'FERRAGRO|8474': 'stock_seguridad',
    'FERRAGRO|11744': 'stock_seguridad',
    'FERRAGRO|12241': 'stock_seguridad',
    'FERRAGRO|3251': 'stock_seguridad',
    'FERRAGRO|3254': 'stock_seguridad',
    'FERRAGRO|3255': 'stock_seguridad',

    // HERRADURA LA MONTANA
    'HERRADURA LA MONTANA|2639': 'stock_seguridad',
    'HERRADURA LA MONTANA|6585': 'stock_seguridad',
    'HERRADURA LA MONTANA|2640': 'stock_seguridad',
    'HERRADURA LA MONTANA|7701': 'stock_seguridad',
    'HERRADURA LA MONTANA|11089': 'stock_seguridad',
    'HERRADURA LA MONTANA|11191': 'stock_seguridad',
    'HERRADURA LA MONTANA|6879': 'stock_seguridad',
    'HERRADURA LA MONTANA|6880': 'stock_seguridad',
    'HERRADURA LA MONTANA|6881': 'stock_seguridad',
    'HERRADURA LA MONTANA|6882': 'stock_seguridad',
    'HERRADURA LA MONTANA|6883': 'stock_seguridad',
    'HERRADURA LA MONTANA|6884': 'stock_seguridad',
    'HERRADURA LA MONTANA|6885': 'stock_seguridad',
    'HERRADURA LA MONTANA|6886': 'stock_seguridad',
    'HERRADURA LA MONTANA|6887': 'stock_seguridad',
    'HERRADURA LA MONTANA|6907': 'stock_seguridad',
    'HERRADURA LA MONTANA|6953': 'stock_seguridad',
    'HERRADURA LA MONTANA|6903': 'stock_seguridad',
    'HERRADURA LA MONTANA|6905': 'stock_seguridad',
    'HERRADURA LA MONTANA|6870': 'stock_seguridad',
    'HERRADURA LA MONTANA|6900': 'stock_seguridad',
    'HERRADURA LA MONTANA|6868': 'stock_seguridad',
    'HERRADURA LA MONTANA|6901': 'stock_seguridad',
    'HERRADURA LA MONTANA|6869': 'stock_seguridad',
    'HERRADURA LA MONTANA|6878': 'stock_seguridad',
    'HERRADURA LA MONTANA|6871': 'stock_seguridad',
    'HERRADURA LA MONTANA|6872': 'stock_seguridad',
    'HERRADURA LA MONTANA|6873': 'stock_seguridad',
    'HERRADURA LA MONTANA|6874': 'stock_seguridad',
    'HERRADURA LA MONTANA|6875': 'stock_seguridad',
    'HERRADURA LA MONTANA|6876': 'stock_seguridad',
    'HERRADURA LA MONTANA|6877': 'stock_seguridad',
    'HERRADURA LA MONTANA|11090': 'stock_seguridad',
    'HERRADURA LA MONTANA|11091': 'stock_seguridad',
    'HERRADURA LA MONTANA|11048': 'stock_seguridad',
    'HERRADURA LA MONTANA|4645': 'stock_seguridad',
    'HERRADURA LA MONTANA|2638': 'stock_seguridad',
    'HERRADURA LA MONTANA|9174': 'stock_seguridad',

    // INSMEVET - 3 MESES
    'INSMEVET|8071': 'cantidadx3',
    'INSMEVET|8551': 'cantidadx3',
    'INSMEVET|8552': 'cantidadx3',
    'INSMEVET|8553': 'cantidadx3',
    'INSMEVET|8744': 'cantidadx3',
    'INSMEVET|8554': 'cantidadx3',
    'INSMEVET|5447': 'cantidadx3',
    'INSMEVET|5452': 'cantidadx3',
    'INSMEVET|5454': 'cantidadx3',
    'INSMEVET|5453': 'cantidadx3',
    'INSMEVET|5450': 'cantidadx3',
    'INSMEVET|5457': 'cantidadx3',
    'INSMEVET|5446': 'cantidadx3',
    'INSMEVET|5449': 'cantidadx3',
    'INSMEVET|5887': 'cantidadx3',
    'INSMEVET|5448': 'cantidadx3',
    'INSMEVET|5451': 'cantidadx3',
    'INSMEVET|7572': 'cantidadx3',
    'INSMEVET|5501': 'cantidadx3',
    'INSMEVET|4481': 'cantidadx3',
    'INSMEVET|8555': 'cantidadx3',
    'INSMEVET|8557': 'cantidadx3',
    'INSMEVET|8556': 'cantidadx3',
    'INSMEVET|8558': 'cantidadx3',
    'INSMEVET|2874': 'cantidadx3',
    'INSMEVET|87': 'cantidadx3',

    // INSMEVET - SS
    'INSMEVET|1692': 'stock_seguridad',
    'INSMEVET|4388': 'stock_seguridad',
    'INSMEVET|8065': 'stock_seguridad',
    'INSMEVET|3326': 'stock_seguridad',
    'INSMEVET|7220': 'stock_seguridad',
    'INSMEVET|6848': 'stock_seguridad',
    'INSMEVET|12183': 'stock_seguridad',
    'INSMEVET|8348': 'stock_seguridad',
    'INSMEVET|751': 'stock_seguridad',
    'INSMEVET|4675': 'stock_seguridad',
    'INSMEVET|4761': 'stock_seguridad',
    'INSMEVET|9866': 'stock_seguridad',
    'INSMEVET|2363': 'stock_seguridad',
    'INSMEVET|2895': 'stock_seguridad',
    'INSMEVET|666': 'stock_seguridad',
    'INSMEVET|5383': 'stock_seguridad',
    'INSMEVET|9380': 'stock_seguridad',
    'INSMEVET|10249': 'stock_seguridad',
    'INSMEVET|10250': 'stock_seguridad',
    'INSMEVET|7219': 'stock_seguridad',
    'INSMEVET|8176': 'stock_seguridad',
    'INSMEVET|8177': 'stock_seguridad',
    'INSMEVET|8178': 'stock_seguridad',
    'INSMEVET|8179': 'stock_seguridad',
    'INSMEVET|8650': 'stock_seguridad',
    'INSMEVET|9261': 'stock_seguridad',
    'INSMEVET|12125': 'stock_seguridad',
    'INSMEVET|8180': 'stock_seguridad',
    'INSMEVET|8181': 'stock_seguridad',
    'INSMEVET|8182': 'stock_seguridad',
    'INSMEVET|8183': 'stock_seguridad',
    'INSMEVET|8184': 'stock_seguridad',
    'INSMEVET|8185': 'stock_seguridad',
    'INSMEVET|8186': 'stock_seguridad',
    'INSMEVET|8187': 'stock_seguridad',
    'INSMEVET|8189': 'stock_seguridad',
    'INSMEVET|8190': 'stock_seguridad',
    'INSMEVET|8191': 'stock_seguridad',
    'INSMEVET|10265': 'stock_seguridad',
    'INSMEVET|8329': 'stock_seguridad',
    'INSMEVET|8330': 'stock_seguridad',
    'INSMEVET|8331': 'stock_seguridad',
    'INSMEVET|8332': 'stock_seguridad',
    'INSMEVET|8356': 'stock_seguridad',
    'INSMEVET|8443': 'stock_seguridad',
    'INSMEVET|8517': 'stock_seguridad',
    'INSMEVET|8913': 'stock_seguridad',
    'INSMEVET|11771': 'stock_seguridad',
    'INSMEVET|11794': 'stock_seguridad',
    'INSMEVET|10167': 'stock_seguridad',
    'INSMEVET|8188': 'stock_seguridad',
    'INSMEVET|8328': 'stock_seguridad',
    'INSMEVET|10435': 'stock_seguridad',
    'INSMEVET|9983': 'stock_seguridad',
    'INSMEVET|10373': 'stock_seguridad',
    'INSMEVET|11042': 'stock_seguridad',
    'INSMEVET|11742': 'stock_seguridad',
    'INSMEVET|11057': 'stock_seguridad',
    'INSMEVET|10646': 'stock_seguridad',
    'INSMEVET|10647': 'stock_seguridad',
    'INSMEVET|10897': 'stock_seguridad',
    'INSMEVET|10898': 'stock_seguridad',
    'INSMEVET|10899': 'stock_seguridad',
    'INSMEVET|10900': 'stock_seguridad',
    'INSMEVET|10901': 'stock_seguridad',
    'INSMEVET|10902': 'stock_seguridad',
    'INSMEVET|10903': 'stock_seguridad',
    'INSMEVET|10904': 'stock_seguridad',
    'INSMEVET|8354': 'stock_seguridad',
    'INSMEVET|8804': 'stock_seguridad',
    'INSMEVET|2550': 'stock_seguridad',
    'INSMEVET|2366': 'stock_seguridad',
    'INSMEVET|4026': 'stock_seguridad',
    'INSMEVET|9416': 'stock_seguridad',
    'INSMEVET|9417': 'stock_seguridad',
    'INSMEVET|1716': 'stock_seguridad',
    'INSMEVET|6701': 'stock_seguridad',
    'INSMEVET|9018': 'stock_seguridad',
    'INSMEVET|10749': 'stock_seguridad',
    'INSMEVET|4107': 'stock_seguridad',
    'INSMEVET|9638': 'stock_seguridad',
    'INSMEVET|10534': 'stock_seguridad',
    'INSMEVET|9650': 'stock_seguridad',
    'INSMEVET|11040': 'stock_seguridad',
    'INSMEVET|11363': 'stock_seguridad',
    'INSMEVET|10272': 'stock_seguridad',
    'INSMEVET|91': 'stock_seguridad',
    'INSMEVET|11846': 'stock_seguridad',
    'INSMEVET|3297': 'stock_seguridad',
    'INSMEVET|5781': 'stock_seguridad',
    'INSMEVET|9218': 'stock_seguridad',
    'INSMEVET|4939': 'stock_seguridad',
    'INSMEVET|3298': 'stock_seguridad',
    'INSMEVET|6103': 'stock_seguridad',
    'INSMEVET|4530': 'stock_seguridad',
    'INSMEVET|90': 'stock_seguridad',
    'INSMEVET|3300': 'stock_seguridad',
    'INSMEVET|51': 'stock_seguridad',
    'INSMEVET|3328': 'stock_seguridad',
    'INSMEVET|4706': 'stock_seguridad',
    'INSMEVET|4808': 'stock_seguridad',
    'INSMEVET|11853': 'stock_seguridad',
    'INSMEVET|6497': 'stock_seguridad',
    'INSMEVET|4929': 'stock_seguridad',
    'INSMEVET|4989': 'stock_seguridad',
    'INSMEVET|11981': 'stock_seguridad',
    'INSMEVET|11063': 'stock_seguridad',
    'INSMEVET|3329': 'stock_seguridad',
    'INSMEVET|3896': 'stock_seguridad',
    'INSMEVET|4210': 'stock_seguridad',
    'INSMEVET|6676': 'stock_seguridad',
    'INSMEVET|112': 'stock_seguridad',
    'INSMEVET|9664': 'stock_seguridad',
    'INSMEVET|2553': 'stock_seguridad',
    'INSMEVET|5189': 'stock_seguridad',
    'INSMEVET|5846': 'stock_seguridad',
    'INSMEVET|7105': 'stock_seguridad',
    'INSMEVET|2883': 'stock_seguridad',
    'INSMEVET|9007': 'stock_seguridad',
    'INSMEVET|9011': 'stock_seguridad',
    'INSMEVET|9012': 'stock_seguridad',
    'INSMEVET|9013': 'stock_seguridad',
    'INSMEVET|11999': 'stock_seguridad',
    'INSMEVET|9014': 'stock_seguridad',
    'INSMEVET|9015': 'stock_seguridad',
    'INSMEVET|9010': 'stock_seguridad',
    'INSMEVET|6256': 'stock_seguridad',
    'INSMEVET|5405': 'stock_seguridad',
    'INSMEVET|11062': 'stock_seguridad',
    'INSMEVET|6777': 'stock_seguridad',
    'INSMEVET|80': 'stock_seguridad',
    'INSMEVET|83': 'stock_seguridad',
    'INSMEVET|81': 'stock_seguridad',
    'INSMEVET|84': 'stock_seguridad',
    'INSMEVET|5445': 'stock_seguridad',
    'INSMEVET|7835': 'stock_seguridad',
    'INSMEVET|82': 'stock_seguridad',
    'INSMEVET|85': 'stock_seguridad',
    'INSMEVET|5204': 'stock_seguridad',
    'INSMEVET|8359': 'stock_seguridad',
    'INSMEVET|8361': 'stock_seguridad',
    'INSMEVET|8445': 'stock_seguridad',
    'INSMEVET|3303': 'stock_seguridad',
    'INSMEVET|11220': 'stock_seguridad',
    'INSMEVET|5733': 'stock_seguridad',
    'INSMEVET|6208': 'stock_seguridad',
    'INSMEVET|9212': 'stock_seguridad',
    'INSMEVET|12054': 'stock_seguridad',
    'INSMEVET|12204': 'stock_seguridad',
    'INSMEVET|10338': 'stock_seguridad',
    'INSMEVET|12175': 'stock_seguridad',
    'INSMEVET|691': 'stock_seguridad',
    'INSMEVET|12055': 'stock_seguridad',
    'INSMEVET|9023': 'stock_seguridad',
    'INSMEVET|7726': 'stock_seguridad',
    'INSMEVET|7727': 'stock_seguridad',
    'INSMEVET|9418': 'stock_seguridad',
    'INSMEVET|9705': 'stock_seguridad',
    'INSMEVET|11574': 'stock_seguridad',
    'INSMEVET|2811': 'stock_seguridad',
    'INSMEVET|10827': 'stock_seguridad',
    'INSMEVET|6849': 'stock_seguridad',
    'INSMEVET|8369': 'stock_seguridad',
    'INSMEVET|8370': 'stock_seguridad',
    'INSMEVET|8449': 'stock_seguridad',
    'INSMEVET|8395': 'stock_seguridad',
    'INSMEVET|11198': 'stock_seguridad',
    'INSMEVET|9387': 'stock_seguridad',
    'INSMEVET|11097': 'stock_seguridad',
    'INSMEVET|3322': 'stock_seguridad',
    'INSMEVET|6987': 'stock_seguridad',
    'INSMEVET|4791': 'stock_seguridad',
    'INSMEVET|5944': 'stock_seguridad',
    'INSMEVET|4502': 'stock_seguridad',
    'INSMEVET|6331': 'stock_seguridad',
    'INSMEVET|2890': 'stock_seguridad',
    'INSMEVET|10985': 'stock_seguridad',
    'INSMEVET|6491': 'stock_seguridad',
    'INSMEVET|5542': 'stock_seguridad',
    'INSMEVET|4537': 'stock_seguridad',
    'INSMEVET|3314': 'stock_seguridad',
    'INSMEVET|3816': 'stock_seguridad',
    'INSMEVET|11997': 'stock_seguridad',
    'INSMEVET|2891': 'stock_seguridad',
    'INSMEVET|7010': 'stock_seguridad',
    'INSMEVET|11435': 'stock_seguridad',
    'INSMEVET|3316': 'stock_seguridad',
    'INSMEVET|8448': 'stock_seguridad',
    'INSMEVET|6956': 'stock_seguridad',
    'INSMEVET|4109': 'stock_seguridad',
    'INSMEVET|7509': 'stock_seguridad',
    'INSMEVET|11041': 'stock_seguridad',
    'INSMEVET|7160': 'stock_seguridad',
    'INSMEVET|6370': 'stock_seguridad',
    'INSMEVET|6790': 'stock_seguridad',
    'INSMEVET|6298': 'stock_seguridad',
    'INSMEVET|5374': 'stock_seguridad',
    'INSMEVET|8915': 'stock_seguridad',
    'INSMEVET|8914': 'stock_seguridad',
    'INSMEVET|8293': 'stock_seguridad',
    'INSMEVET|3320': 'stock_seguridad',
    'INSMEVET|9019': 'stock_seguridad',
    'INSMEVET|10907': 'stock_seguridad',
    'INSMEVET|2894': 'stock_seguridad',
    'INSMEVET|11768': 'stock_seguridad',
    'INSMEVET|10374': 'stock_seguridad',
    'INSMEVET|8344': 'stock_seguridad',

    // LHAURA
    'LHAURA|712': 'stock_seguridad',
    'LHAURA|756': 'stock_seguridad',
    'LHAURA|757': 'stock_seguridad',
    'LHAURA|658': 'stock_seguridad',
    'LHAURA|8226': 'stock_seguridad',
    'LHAURA|660': 'stock_seguridad',
    'LHAURA|619': 'stock_seguridad',
    'LHAURA|747': 'stock_seguridad',
    'LHAURA|662': 'stock_seguridad',
    'LHAURA|663': 'stock_seguridad',
    'LHAURA|664': 'stock_seguridad',
    'LHAURA|7454': 'stock_seguridad',
    'LHAURA|7610': 'stock_seguridad',
    'LHAURA|753': 'stock_seguridad',
    'LHAURA|4554': 'stock_seguridad',
    'LHAURA|4350': 'stock_seguridad',
    'LHAURA|665': 'stock_seguridad',
    'LHAURA|11986': 'stock_seguridad',
    'LHAURA|12203': 'stock_seguridad',
    'LHAURA|11410': 'stock_seguridad',
    'LHAURA|667': 'stock_seguridad',
    'LHAURA|668': 'stock_seguridad',
    'LHAURA|717': 'stock_seguridad',
    'LHAURA|718': 'stock_seguridad',
    'LHAURA|669': 'stock_seguridad',
    'LHAURA|5022': 'stock_seguridad',
    'LHAURA|758': 'stock_seguridad',
    'LHAURA|7612': 'stock_seguridad',
    'LHAURA|3173': 'stock_seguridad',
    'LHAURA|12178': 'stock_seguridad',
    'LHAURA|12179': 'stock_seguridad',
    'LHAURA|12180': 'stock_seguridad',
    'LHAURA|12181': 'stock_seguridad',
    'LHAURA|12182': 'stock_seguridad',
    'LHAURA|671': 'stock_seguridad',
    'LHAURA|673': 'stock_seguridad',
    'LHAURA|672': 'stock_seguridad',
    'LHAURA|620': 'stock_seguridad',
    'LHAURA|681': 'stock_seguridad',
    'LHAURA|621': 'stock_seguridad',
    'LHAURA|622': 'stock_seguridad',
    'LHAURA|720': 'stock_seguridad',
    'LHAURA|721': 'stock_seguridad',
    'LHAURA|623': 'stock_seguridad',
    'LHAURA|624': 'stock_seguridad',
    'LHAURA|625': 'stock_seguridad',
    'LHAURA|627': 'stock_seguridad',
    'LHAURA|626': 'stock_seguridad',
    'LHAURA|6536': 'stock_seguridad',
    'LHAURA|3321': 'stock_seguridad',
    'LHAURA|12040': 'stock_seguridad',
    'LHAURA|3336': 'stock_seguridad',
    'LHAURA|675': 'stock_seguridad',
    'LHAURA|10242': 'stock_seguridad',
    'LHAURA|722': 'stock_seguridad',
    'LHAURA|677': 'stock_seguridad',
    'LHAURA|678': 'stock_seguridad',
    'LHAURA|723': 'stock_seguridad',
    'LHAURA|724': 'stock_seguridad',
    'LHAURA|725': 'stock_seguridad',
    'LHAURA|726': 'stock_seguridad',
    'LHAURA|6194': 'stock_seguridad',
    'LHAURA|739': 'stock_seguridad',
    'LHAURA|679': 'stock_seguridad',
    'LHAURA|680': 'stock_seguridad',
    'LHAURA|11143': 'stock_seguridad',
    'LHAURA|7332': 'stock_seguridad',
    'LHAURA|629': 'stock_seguridad',
    'LHAURA|9067': 'stock_seguridad',
    'LHAURA|9068': 'stock_seguridad',
    'LHAURA|11806': 'stock_seguridad',
    'LHAURA|741': 'stock_seguridad',
    'LHAURA|6858': 'stock_seguridad',
    'LHAURA|8489': 'stock_seguridad',
    'LHAURA|632': 'stock_seguridad',
    'LHAURA|633': 'stock_seguridad',
    'LHAURA|634': 'stock_seguridad',
    'LHAURA|683': 'stock_seguridad',
    'LHAURA|635': 'stock_seguridad',
    'LHAURA|636': 'stock_seguridad',
    'LHAURA|684': 'stock_seguridad',
    'LHAURA|639': 'stock_seguridad',
    'LHAURA|11713': 'stock_seguridad',
    'LHAURA|640': 'stock_seguridad',
    'LHAURA|9112': 'stock_seguridad',
    'LHAURA|641': 'stock_seguridad',
    'LHAURA|689': 'stock_seguridad',
    'LHAURA|727': 'stock_seguridad',
    'LHAURA|3301': 'stock_seguridad',
    'LHAURA|2884': 'stock_seguridad',
    'LHAURA|9997': 'stock_seguridad',
    'LHAURA|731': 'stock_seguridad',
    'LHAURA|3974': 'stock_seguridad',
    'LHAURA|615': 'stock_seguridad',
    'LHAURA|610': 'stock_seguridad',
    'LHAURA|611': 'stock_seguridad',
    'LHAURA|10993': 'stock_seguridad',
    'LHAURA|612': 'stock_seguridad',
    'LHAURA|7291': 'stock_seguridad',
    'LHAURA|9336': 'stock_seguridad',
    'LHAURA|616': 'stock_seguridad',
    'LHAURA|9900': 'stock_seguridad',
    'LHAURA|3698': 'stock_seguridad',
    'LHAURA|9028': 'stock_seguridad',
    'LHAURA|798': 'stock_seguridad',
    'LHAURA|750': 'stock_seguridad',
    'LHAURA|748': 'stock_seguridad',
    'LHAURA|8606': 'stock_seguridad',
    'LHAURA|8607': 'stock_seguridad',
    'LHAURA|12137': 'stock_seguridad',
    'LHAURA|12138': 'stock_seguridad',
    'LHAURA|12139': 'stock_seguridad',
    'LHAURA|12135': 'stock_seguridad',
    'LHAURA|12136': 'stock_seguridad',
    'LHAURA|6664': 'stock_seguridad',
    'LHAURA|800': 'stock_seguridad',
    'LHAURA|801': 'stock_seguridad',
    'LHAURA|799': 'stock_seguridad',
    'LHAURA|802': 'stock_seguridad',
    'LHAURA|803': 'stock_seguridad',
    'LHAURA|6665': 'stock_seguridad',
    'LHAURA|9315': 'stock_seguridad',
    'LHAURA|7891': 'stock_seguridad',
    'LHAURA|6666': 'stock_seguridad',
    'LHAURA|9223': 'stock_seguridad',
    'LHAURA|6663': 'stock_seguridad',
    'LHAURA|5330': 'stock_seguridad',
    'LHAURA|5701': 'stock_seguridad',
    'LHAURA|643': 'stock_seguridad',
    'LHAURA|644': 'stock_seguridad',
    'LHAURA|645': 'stock_seguridad',
    'LHAURA|646': 'stock_seguridad',
    'LHAURA|4070': 'stock_seguridad',
    'LHAURA|759': 'stock_seguridad',
    'LHAURA|11302': 'stock_seguridad',
    'LHAURA|696': 'stock_seguridad',
    'LHAURA|697': 'stock_seguridad',
    'LHAURA|698': 'stock_seguridad',
    'LHAURA|1653': 'stock_seguridad',
    'LHAURA|617': 'stock_seguridad',
    'LHAURA|618': 'stock_seguridad',
    'LHAURA|647': 'stock_seguridad',
    'LHAURA|648': 'stock_seguridad',
    'LHAURA|9647': 'stock_seguridad',
    'LHAURA|11645': 'stock_seguridad',
    'LHAURA|716': 'stock_seguridad',
    'LHAURA|10826': 'stock_seguridad',
    'LHAURA|744': 'stock_seguridad',
    'LHAURA|4628': 'stock_seguridad',
    'LHAURA|11760': 'stock_seguridad',
    'LHAURA|8132': 'stock_seguridad',
    'LHAURA|701': 'stock_seguridad',
    'LHAURA|651': 'stock_seguridad',
    'LHAURA|4101': 'stock_seguridad',
    'LHAURA|4086': 'stock_seguridad',
    'LHAURA|703': 'stock_seguridad',
    'LHAURA|654': 'stock_seguridad',
    'LHAURA|4380': 'stock_seguridad',
    'LHAURA|9648': 'stock_seguridad',
    'LHAURA|705': 'stock_seguridad',
    'LHAURA|7331': 'stock_seguridad',
    'LHAURA|708': 'stock_seguridad',
    'LHAURA|728': 'stock_seguridad',
    'LHAURA|3812': 'stock_seguridad',
    'LHAURA|709': 'stock_seguridad',
    'LHAURA|754': 'stock_seguridad',
    'LHAURA|10769': 'stock_seguridad',
    'LHAURA|3319': 'stock_seguridad',
    'LHAURA|710': 'stock_seguridad',
    'LHAURA|4078': 'stock_seguridad',
    'LHAURA|729': 'stock_seguridad',
    'LHAURA|11301': 'stock_seguridad',
    'LHAURA|711': 'stock_seguridad',
    'LHAURA|656': 'stock_seguridad',
    'LHAURA|7988': 'stock_seguridad',
    'LHAURA|657': 'stock_seguridad',
    'LHAURA|614': 'stock_seguridad',
    'LHAURA|11280': 'stock_seguridad',
    'LHAURA|730': 'stock_seguridad',
    'LHAURA|749': 'stock_seguridad',
    'LHAURA|7996': 'stock_seguridad',

    // QUIMPAC
    'QUIMPAC|11530': 'stock_seguridad',
    'QUIMPAC|11984': 'stock_seguridad',
    'QUIMPAC|8340': 'stock_seguridad',
    'QUIMPAC|11370': 'stock_seguridad',
    'QUIMPAC|9224': 'stock_seguridad',
    'QUIMPAC|8734': 'stock_seguridad',
    'QUIMPAC|12202': 'stock_seguridad',
    'QUIMPAC|11445': 'stock_seguridad',
    'QUIMPAC|11444': 'stock_seguridad',
    'QUIMPAC|11830': 'stock_seguridad',
    'QUIMPAC|8890': 'stock_seguridad',
    'QUIMPAC|8256': 'stock_seguridad',
    'QUIMPAC|11554': 'stock_seguridad',
    'QUIMPAC|10628': 'stock_seguridad',
    'QUIMPAC|8802': 'stock_seguridad',
    'QUIMPAC|11495': 'stock_seguridad',
    'QUIMPAC|9413': 'stock_seguridad',
    'QUIMPAC|8099': 'stock_seguridad',

    // RENTASAL
    'RENTASAL|10416': 'stock_seguridad',
    'RENTASAL|10041': 'stock_seguridad',
    'RENTASAL|2862': 'stock_seguridad',
    'RENTASAL|2861': 'stock_seguridad',
    'RENTASAL|7826': 'stock_seguridad',
    'RENTASAL|2859': 'stock_seguridad',
    'RENTASAL|2865': 'stock_seguridad',
    'RENTASAL|2866': 'stock_seguridad',
    'RENTASAL|2867': 'stock_seguridad',

    // VITALES - 3 MESES
    'VITALES|4513': 'cantidadx3',
    'VITALES|98': 'cantidadx3',
    'VITALES|100': 'cantidadx3',
    'VITALES|10508': 'cantidadx3',
    'VITALES|99': 'cantidadx3',
    'VITALES|10507': 'cantidadx3',
    'VITALES|103': 'cantidadx3',
    'VITALES|102': 'cantidadx3',

    // VITALES - SS
    'VITALES|8123': 'stock_seguridad',
    'VITALES|8261': 'stock_seguridad',
    'VITALES|9553': 'stock_seguridad',
    'VITALES|8127': 'stock_seguridad',
    'VITALES|11015': 'stock_seguridad',
    'VITALES|10842': 'stock_seguridad',
    'VITALES|11600': 'stock_seguridad',
    'VITALES|11589': 'stock_seguridad',
    'VITALES|10442': 'stock_seguridad',
    'VITALES|10049': 'stock_seguridad',
    'VITALES|8371': 'stock_seguridad',
    'VITALES|11314': 'stock_seguridad',
    'VITALES|10884': 'stock_seguridad',
    };
    // Función de lookup: exacto primero, luego comodín
    function getMultiplo(proveedor, producto) {
        const exactKey    = `${proveedor}|${producto}`;
        const wildcardKey = `${proveedor}|*`;
        if (MULTIPLOS_BASE_COL[exactKey]    !== undefined) return MULTIPLOS_BASE_COL[exactKey];
        if (MULTIPLOS_BASE_COL[wildcardKey] !== undefined) return MULTIPLOS_BASE_COL[wildcardKey];
        return '';
    }
    const exportData = [headers];
    let index = 1;

    updatedData.forEach(row => {
        const rowData = [];
        columnsToExport.forEach((colIndex, i) => {
            if (i === 0) {
                rowData.push(index++);
            } else {
                rowData.push(row[colIndex]);
            }
        });

        // Buscar el valor del múltiplo usando proveedor (índice 7) y producto (índice 2)
        const proveedor = String(row[7]).trim();
        const producto = String(row[2]).trim();
        const key = `${proveedor}|${producto}`;
        const multiplo = getMultiplo(proveedor, producto);

        // Resolver el valor real: stock o cantidadx3
        let valorMultiplo = '';
        if (multiplo === 'stock_seguridad') {
            valorMultiplo = row[10]; // columna stock (ya convertida a int)
        } else if (multiplo === 'cantidadx3') {
            valorMultiplo = row[11]; // columna cantidadx3 (ya convertida a int)
        }

        rowData.push(valorMultiplo);
        exportData.push(rowData);
    });

    const ws = XLSX.utils.aoa_to_sheet(exportData);
    XLSX.utils.book_append_sheet(wb, ws, 'Datos_Productos');

    const fechaActual = new Date();
    const year = fechaActual.getFullYear();
    const mes = String(fechaActual.getMonth() + 1).padStart(2, '0');
    const dia = String(fechaActual.getDate()).padStart(2, '0');
    const fechaFormateada = `${dia}/${mes}/${year}`;
    const nombreArchivo = `Datos_filtrados_${fechaFormateada}.xlsx`;

    XLSX.writeFile(wb, nombreArchivo);
});
*/
async function uploadData() {
    const params = new URLSearchParams();

    getSelectedValues('select-options-items', 'select-all-items')
        .forEach(v => params.append('item', v));
    getSelectedValues('select-options-proveedores', 'select-all-proveedores')
        .forEach(v => params.append('proveedor', v));
    getSelectedValues('select-options-productos', 'select-all-productos')
        .forEach(v => params.append('producto', v));
    getSelectedValues('select-options-sedes', 'select-all-sedes')
        .forEach(v => params.append('sede', v));

    if (!params.toString()) {
        alert('Selecciona al menos un filtro antes de buscar.');
        return null;
    }

    const loader = document.querySelector('.spinner-border');
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
        { targets: [0, 1, 3, 5, 6, 12, 13], visible: false, searchable: false },
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
        // const fechaActual = new Date();
        // const year = fechaActual.getFullYear();
        // const mes = String(fechaActual.getMonth() + 1).padStart(2, '0'); // Los meses empiezan en 0
        // const dia = String(fechaActual.getDate()).padStart(2, '0');

        // const fechaFormateada = `${year}/${mes}/${dia}`;
        
        let content = ``;
        datos.productos.forEach((producto, index) => {
            content += `
                <tr>
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
                    <td>${producto.stock}</td>
                    <td>${producto.cantidadx3}</td>
                    <td>${producto.precio}</td>
                    <td>${producto.fecha}</td>
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
