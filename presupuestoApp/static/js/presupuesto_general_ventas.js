function numberFormat(data, type, row) {
    if (type === 'display' && !isNaN(data)) {
        return new Intl.NumberFormat('es-ES').format(data);
    }
    return data;
}

$(function () {   // ⚡ $(function() {}) == $(document).ready()
    let table = $('#presupuestoTableProyeccionGeneral').DataTable({
        ajax: {
            url: "{% url 'obtener_presupuesto_general_ventas' %}",
            dataSrc: ""
        },
        columns: [
            { data: "year" },
            { data: "mes" },
            { data: "total" },
            { data: "r2" }
        ],
        columnDefs: [
            { targets: 2, render: numberFormat },
            { targets: [0,1,2,3], className: "editable" }
        ],
        dom: 'Bfrtip',
        buttons: [
            {
                extend: 'excelHtml5',
                text: '📥 Exportar a Excel',
                filename: 'presupuesto_general_ventas',
                exportOptions: { columns: ':visible' }
            }
        ]
    });

    // Doble clic para editar
    let editingCell = null;
    $('#presupuestoTableProyeccionGeneral').on('dblclick', 'td.editable', function () {
        if (editingCell) return;
        let cell = table.cell(this);
        let oldValue = cell.data();

        $(this).html('<input type="text" class="cell-input" value="'+ oldValue +'"/>');
        let $input = $(this).find("input").focus();
        editingCell = this;

        $input[0].setSelectionRange(0, $input.val().length);

        $input.on("keydown", function(e) {
            if (e.key === "Enter") {
                cell.data($input.val()).draw(false);
                editingCell = null;
            } else if (e.key === "Escape") {
                cell.data(oldValue).draw(false);
                editingCell = null;
            }
        });
    });

    // Guardar cuando haces clic fuera
    $(document).on("click", function(e) {
        if (editingCell) {
            let $cell = $(editingCell);
            let $input = $cell.find("input");
            if ($input.length && !$(e.target).closest("#presupuestoTableProyeccionGeneral").length) {
                let cell = table.cell(editingCell);
                cell.data($input.val()).draw(false);
                editingCell = null;
            }
        }
    });

    // 🔄 Botón cargar desde histórico
    $(document).on("click", "#cargarBtn", function () {
        $.ajax({
            url: "{% url 'cargar_presupuesto_general_ventas' %}",
            type: "GET",
            success: function() {
                alert("Datos recalculados y cargados desde histórico ✅");
                table.ajax.reload();
            },
            error: function(xhr) {
                alert("Error al cargar desde histórico ❌ " + xhr.responseText);
            }
        });
    });

    // 💾 Botón guardar cambios
    $(document).on("click", "#guardarBtn", function () {
        let data = table.rows().data().toArray();

        $.ajax({
            url: "{% url 'guardar_presupuesto_general_ventas' %}",
            type: "POST",
            data: JSON.stringify(data),
            contentType: "application/json",
            headers: { "X-CSRFToken": "{{ csrf_token }}" },
            success: function() {
                alert("Cambios guardados ✅");
                table.ajax.reload();
            },
            error: function(xhr) {
                alert("Error al guardar ❌: " + xhr.responseText);
            }
        });
    });
});