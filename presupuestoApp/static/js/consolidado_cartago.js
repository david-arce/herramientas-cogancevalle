function numberFormat(data, type, row) {
    if (type === 'display' && !isNaN(data)) {
        return new Intl.NumberFormat('es-ES').format(data);
    }
return data;
}
$(document).ready(function() {
    

    let table = new DataTable('#table', {
        ajax: {
            url: url_obtener_consolidado_cartago,
            dataSrc: 'data'
        },
        columns: [
            {   // 🔥 Columna de selección
                data: null,
                defaultContent: `<input type="checkbox" class="row-check">`,
                orderable: false
            },
            { data: 'mcncuenta' },
            { data: 'mcnccosto' },
            { data: 'zonnombre' },
            { data: 'ctanombre' },
            { data: 'Enero' },
            { data: 'Febrero' },
            { data: 'Marzo' },
            { data: 'Abril' },
            { data: 'Mayo' },
            { data: 'Junio' },
            { data: 'Julio' },
            { data: 'Agosto' },
            { data: 'Septiembre' },
            { data: 'Octubre' },
            { data: 'Noviembre' },
            { data: 'Diciembre' }
        ],
        columnDefs: [
            { width: '35px', targets: 0 },      // Checkbox
            { width: '120px', targets: [1,2,3] },     // CUENTA y CENTRO DE COSTO
            { width: '120px', targets: 4 },     // NOMBRE CUENTA
            { width: '100px', targets: [5,6,7,8,9,10,11,12,13,14,15,16], className: 'dt-body-right', render: numberFormat },
        ],
        autoWidth: false,  // 🔥 IMPORTANTE: Desactiva el ancho automático
        paging: false,
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