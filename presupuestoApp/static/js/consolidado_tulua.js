function numberFormat(data, type, row) {
    if (type === 'display' && !isNaN(data)) {
        return new Intl.NumberFormat('es-ES').format(data);
    }
return data;
}
$(document).ready(function() {
    

    let table = new DataTable('#table', {
        ajax: {
            url: url_obtener_consolidado_tulua,
            dataSrc: ''
        },
        columns: [
            {   // 🔥 Columna de selección
                data: null,
                defaultContent: `<input type="checkbox" class="row-check">`,
                orderable: false
            },
            { data: 'cuenta' },
            { data: 'enero' },
            { data: 'febrero' },
            { data: 'marzo' },
            { data: 'abril' },
            { data: 'mayo' },
            { data: 'junio' },
            { data: 'julio' },
            { data: 'agosto' },
            { data: 'septiembre'},
            { data: 'octubre'},
            { data: 'noviembre'},
            { data: 'diciembre'},
            { data: 'total' }
        ],
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json'
        },
        columnControl: ['order', ['searchList']],
            ordering: {
                indicators: false,
                handler: false
            }
    });
    
});