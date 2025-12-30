function numberFormat(data, type, row) {
    if (type === 'display' && !isNaN(data)) {
        return new Intl.NumberFormat('es-ES').format(data);
    }
return data;
}
$(document).ready(function() {
    

    let table = new DataTable('#table', {
        ajax: {
            url: url_obtener_consolidado_total_base,
            dataSrc: 'data'
        },
        columns: [
            {   // 🔥 Columna de selección
                data: null,
                defaultContent: `
                <div class="action-buttons">
                    <input type="checkbox" class="row-check">
                    <button class="btn-edit" title="Editar">✏️</button>
                    <button class="btn-delete" title="Eliminar">🗑️</button>
                </div>
                `,
                orderable: false
            },
            { data: 'mcncuenta' },
            { data: 'mcnccosto' },
            { data: 'ctanombre' },
            { data: 'enero' },
            { data: 'febrero' },
            { data: 'marzo' },
            { data: 'abril' },
            { data: 'mayo' },
            { data: 'junio' },
            { data: 'julio' },
            { data: 'agosto' },
            { data: 'septiembre' },
            { data: 'octubre' },
            { data: 'noviembre' },
            { data: 'diciembre' },
            { data: 'total' }
        ],
        columnDefs: [
            { width: '120px', targets: 0 },      // Checkbox
            { width: '160px', targets: [1,2] },     // CUENTA y CENTRO DE COSTO
            { width: '200px', targets: 3 },     // NOMBRE CUENTA
            { width: '120px', targets: [4,5,6,7,8,9,10,11,12,13,14,15,16], className: 'dt-body-right', render: numberFormat }, 
        ],
        autoWidth: false,  // 🔥 IMPORTANTE: Desactiva el ancho automático
        paging: false,
        // scrollX: true,
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json'
        },
        columnControl: [['searchList']],
        ordering: {
            indicators: false,
            handler: false
        },
    });
    // ============================================
    // 🔥 AGREGAR NUEVA FILA
    // ============================================
    $('#agregarFilaBtn').on('click', function() {
        const nuevaFila = {
            mcncuenta: '',
            mcnccosto: '',
            ctanombre: '',
            enero: 0, febrero: 0, marzo: 0, abril: 0,
            mayo: 0, junio: 0, julio: 0, agosto: 0,
            septiembre: 0, octubre: 0, noviembre: 0, diciembre: 0,
            total: 0,
            isNew: true
        };
        
        const row = table.row.add(nuevaFila).draw(false);
        // Mover la fila al principio
        const rowNode = row.node();
        $(rowNode).prependTo(table.table().body());
        const $row = $(row.node());
        
        // Hacer editable inmediatamente
        hacerFilaEditable($row, nuevaFila);
        // Scroll hacia arriba para ver la nueva fila
        $('#tableContainer').animate({ scrollTop: 0 }, 300);
    });

    // ============================================
    // 🔥 EDITAR FILA
    // ============================================
    $('#table tbody').on('click', '.btn-edit', function() {
        const $row = $(this).closest('tr');
        const rowData = table.row($row).data();
        
        if ($row.hasClass('editing')) {
            // Guardar cambios
            guardarEdicion($row, rowData);
        } else {
            // Entrar en modo edición
            hacerFilaEditable($row, rowData);
        }
    });

    function hacerFilaEditable($row, rowData) {
        // Cancelar cualquier otra fila en edición
        cancelarEdicionOtrasFila($row);
        $row.addClass('editing');
        
        // Cambiar botón editar por guardar
        $row.find('.btn-edit').html('💾').attr('title', 'Guardar');
        
        // Hacer celdas editables (columnas 1-15, excepto la última que es total)
        $row.find('td').each(function(index) {
            if (index >= 1 && index <= 15) {
                const $td = $(this);
                const valor = $td.text().replace(/\./g, '').trim() || '0';
                
                if (index <= 3) {
                    // Campos de texto: cuenta, centro de costo, nombre
                    $td.html(`<input type="text" class="edit-input" value="${valor}" />`);
                } else {
                    // Campos numéricos: meses
                    $td.html(`<input type="number" class="edit-input numeric" value="${valor}" />`);
                }
            }
        });
        
        // Calcular total al cambiar cualquier mes
        $row.find('.numeric').on('input', function() {
            calcularTotalFila($row);
        });
        // Focus en el primer input
        $row.find('.edit-input').first().focus();
    }
    // Función para cancelar edición de otras filas
    function cancelarEdicionOtrasFila($currentRow) {
        $('#table tbody tr.editing').each(function() {
            const $row = $(this);
            if ($row[0] !== $currentRow[0]) {
                const rowData = table.row($row).data();
                
                // Restaurar la fila sin guardar
                table.row($row).data(rowData).draw(false);
                $row.removeClass('editing');
            }
        });
    }
    // ============================================
    // 🔥 CANCELAR EDICIÓN AL HACER CLIC FUERA
    // ============================================
    $(document).on('click', function(e) {
        const $target = $(e.target);
        
        // Si el clic es fuera del datatable y fuera de los inputs
        if (!$target.closest('#table').length && !$target.closest('.edit-input').length) {
            // Buscar filas en edición
            $('#table tbody tr.editing').each(function() {
                const $row = $(this);
                const rowData = table.row($row).data();
                
                // Confirmar si quiere cancelar
                if (confirm('¿Desea cancelar la edición? Los cambios no guardados se perderán.')) {
                    // Si es una fila nueva (sin datos), eliminarla
                    if (rowData.isNew && !rowData.mcncuenta) {
                        table.row($row).remove().draw(false);
                    } else {
                        // Restaurar datos originales
                        table.row($row).data(rowData).draw(false);
                        $row.removeClass('editing');
                    }
                }
            });
        }
    });
    
    // Prevenir que el clic dentro de la tabla cierre la edición
    $('#table').on('click', function(e) {
        e.stopPropagation();
    });
    function calcularTotalFila($row) {
        let total = 0;
        $row.find('td').slice(4, 16).each(function() {
            const input = $(this).find('input');
            if (input.length) {
                total += parseFloat(input.val()) || 0;
            }
        });
        $row.find('td').eq(16).text(new Intl.NumberFormat('es-ES').format(total));
    }

    function guardarEdicion($row, oldData) {
        const nuevaData = {
            mcncuenta: $row.find('td').eq(1).find('input').val(),
            mcnccosto: $row.find('td').eq(2).find('input').val(),
            ctanombre: $row.find('td').eq(3).find('input').val(),
            enero: parseFloat($row.find('td').eq(4).find('input').val()) || 0,
            febrero: parseFloat($row.find('td').eq(5).find('input').val()) || 0,
            marzo: parseFloat($row.find('td').eq(6).find('input').val()) || 0,
            abril: parseFloat($row.find('td').eq(7).find('input').val()) || 0,
            mayo: parseFloat($row.find('td').eq(8).find('input').val()) || 0,
            junio: parseFloat($row.find('td').eq(9).find('input').val()) || 0,
            julio: parseFloat($row.find('td').eq(10).find('input').val()) || 0,
            agosto: parseFloat($row.find('td').eq(11).find('input').val()) || 0,
            septiembre: parseFloat($row.find('td').eq(12).find('input').val()) || 0,
            octubre: parseFloat($row.find('td').eq(13).find('input').val()) || 0,
            noviembre: parseFloat($row.find('td').eq(14).find('input').val()) || 0,
            diciembre: parseFloat($row.find('td').eq(15).find('input').val()) || 0
        };
        
        // Calcular total
        nuevaData.total = nuevaData.enero + nuevaData.febrero + nuevaData.marzo + nuevaData.abril +
                          nuevaData.mayo + nuevaData.junio + nuevaData.julio + nuevaData.agosto +
                          nuevaData.septiembre + nuevaData.octubre + nuevaData.noviembre + nuevaData.diciembre;
        
        // Validar que cuenta y centro de costo no estén vacíos
        if (!nuevaData.mcncuenta || !nuevaData.mcnccosto) {
            showToast('❌ Cuenta y Centro de Costo son obligatorios', 'error');
            return;
        }
        
        // Deshabilitar botón mientras guarda
        const $btnEdit = $row.find('.btn-edit');
        $btnEdit.prop('disabled', true).html('⏳');
        
        // Guardar en backend
        guardarFilaBackend(nuevaData, oldData).then(success => {
            if (success) {
                // Actualizar la fila en DataTable
                table.row($row).data(nuevaData).draw(false);
                
                // Quitar modo edición
                $row.removeClass('editing');
                $btnEdit.html('✏️').attr('title', 'Editar').prop('disabled', false);
                
                showToast('✅ Cambios guardados correctamente', 'success');
            } else {
                $btnEdit.html('💾').prop('disabled', false);
            }
        });
    }

    // ============================================
    // 🔥 ELIMINAR FILA
    // ============================================
    $('#table tbody').on('click', '.btn-delete', function() {
        const $row = $(this).closest('tr');
        const rowData = table.row($row).data();
        
        if (confirm(`¿Está seguro de eliminar la fila?\nCuenta: ${rowData.mcncuenta}\nCentro Costo: ${rowData.mcnccosto}`)) {
            eliminarFilaBackend(rowData).then(success => {
                if (success) {
                    table.row($row).remove().draw(false);
                    showToast('✅ Fila eliminada correctamente', 'success');
                }
            });
        }
    });

    // ============================================
    // 🔥 GUARDAR EN BACKEND
    // ============================================
    function guardarFilaBackend(nuevaData, oldData) {
        const csrftoken = document.querySelector('[name=csrf-token]').content;
        
        return $.ajax({
            url: url_guardar_fila_consolidado,
            type: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            contentType: 'application/json',
            data: JSON.stringify({
                nueva_data: nuevaData,
                old_data: oldData
            }),
            success: function(response) {
                if (!response.success) {
                    showToast('Error: ' + (response.error || 'Error desconocido'), 'error');
                    return false;
                }
                return true;
            },
            error: function(xhr) {
                let errorMsg = 'Error al guardar';
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    errorMsg = xhr.responseJSON.error;
                }
                showToast(errorMsg, 'error');
                console.error('Error:', xhr);
                return false;
            }
        });
    }

    // ============================================
    // 🔥 ELIMINAR EN BACKEND
    // ============================================
    function eliminarFilaBackend(rowData) {
        const csrftoken = document.querySelector('[name=csrf-token]').content;
        
        return $.ajax({
            url: url_eliminar_fila_consolidado,
            type: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            contentType: 'application/json',
            data: JSON.stringify({
                mcncuenta: rowData.mcncuenta,
                mcnccosto: rowData.mcnccosto
            }),
            success: function(response) {
                if (!response.success) {
                    showToast('Error: ' + (response.error || 'Error desconocido'), 'error');
                    return false;
                }
                return true;
            },
            error: function(xhr) {
                let errorMsg = 'Error al eliminar';
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    errorMsg = xhr.responseJSON.error;
                }
                showToast(errorMsg, 'error');
                console.error('Error:', xhr);
                return false;
            }
        });
    }

    // Botón para calcular y guardar consolidado
    $('#calcularConsolidadoBtn').on('click', function() {
        const btn = $(this);
        const originalText = btn.html();
        
        // Confirmar acción
        if (!confirm('¿Está seguro de recalcular y guardar el consolidado? Esto eliminará los datos actuales y creará nuevos registros.')) {
            return;
        }
        
        // Deshabilitar botón y mostrar loading
        btn.prop('disabled', true).html('⏳ Calculando...');
        
        // Obtener CSRF token
        const csrftoken = document.querySelector('[name=csrf-token]').content;
        
        $.ajax({
            url: url_calcular_consolidado_total_base,  // 👈 Usar la variable definida en el template
            type: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            },
            success: function(response) {
                if (response.success) {
                    showToast(response.mensaje, 'success');
                    
                    // Recargar la tabla después de 1 segundo
                    setTimeout(function() {
                        table.ajax.reload(null, false);  // 👈 Usar la variable table directamente
                    }, 1000);
                } else {
                    showToast('Error: ' + (response.error || 'Error desconocido'), 'error');
                }
            },
            error: function(xhr) {
                let errorMsg = 'Error al calcular consolidado';
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    errorMsg = xhr.responseJSON.error;
                } else if (xhr.statusText) {
                    errorMsg += ': ' + xhr.statusText;
                }
                showToast(errorMsg, 'error');
                console.error('Error completo:', xhr);
            },
            complete: function() {
                // Restaurar botón
                btn.prop('disabled', false).html(originalText);
            }
        });
    });

    // 🔥 Función para mostrar toasts
    function showToast(message, type = 'info') {
        const toastContainer = $('#toastContainer');
        const toast = $(`
            <div class="toast toast-${type}">
                <span>${message}</span>
            </div>
        `);
        
        toastContainer.append(toast);
        
        setTimeout(() => {
            toast.addClass('show');
        }, 100);
        
        setTimeout(() => {
            toast.removeClass('show');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }
    
});