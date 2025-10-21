function numberFormat(data, type, row) {
    if (type === 'display' && !isNaN(data)) {
        return new Intl.NumberFormat('es-ES').format(data);
    }
return data;
}

let opcionesCuentaMayor = [];
let mapaCuentaMayor = {};
function cargarOpciones() {
    $.get(url_seleccionCuentasContables, function(response) {
        opcionesCuentaMayor = Object.values(response.cuentas_dict || []);
        mapaCuentaMayor = response.cuentas_dict || {};
    });
}

$(document).ready(function() {
    let persistentToast = null; // 🔥 guardamos referencia al toast de advertencia
    let editando = false; // 🔥 Bandera global
    
    function abrirModal(id) {
        document.getElementById(id).style.display = "block";
    }
    function cerrarModal(id) {
        document.getElementById(id).style.display = "none";
    }

    cargarOpciones();
    let table = $('#tempTable').DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            url: url_obtener_cuenta5_base,
            type: "GET"
        },
        columns: [
            {   // 🔥 Columna de selección
                data: null,
                defaultContent: `<input type="checkbox" class="row-check">`,
                orderable: false
            },
            { 
                data: null,
                defaultContent: `
                    <button class="duplicarFila" title="Duplicar fila">📑</button>
                    <button class="eliminarFila" title="Eliminar fila">❌</button>
                `,
                orderable: false,
                width: "60px"
            },
            
            { data: 'mcncuenta', render: numberFormat },
            { data: 'mcnfecha', render: numberFormat },
            { data: 'mcntipodoc' },
            { data: 'mcnnumedoc', render: numberFormat },
            { data: 'mcnvincula', render: numberFormat },
            { data: 'vinnombre' },
            { data: 'mcnsucvin' },
            { data: 'saldoant', render: numberFormat },
            { data: 'mcnvaldebi', render: numberFormat },
            { data: 'mcnvalcred', render: numberFormat },
            { data: 'saldonew', render: numberFormat },
            { data: 'mcnsucurs' },
            { data: 'mcnccosto' },
            { data: 'mcndestino' },
            { data: 'mcndetalle' },
            { data: 'mcnzona' },
            { data: 'cconombre' },
            { data: 'dnonombre' },
            { data: 'zonnombre' },
            { data: 'mcnempresa', render: numberFormat },
            { data: 'mcnclase' },
            { data: 'mcnvinkey' },
            { data: 'tpreg', render: numberFormat },
            { data: 'ctanombre' },
            { data: 'docdetalle' },
            { data: 'infdetalle' }
        ],
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json'
        },
        createdRow: function(row, data, dataIndex) {
            // marcar todas menos Acciones como editables
            $('td', row).each(function(index) {
                let colName = table.column(index).dataSrc();

                // ❌ columnas bloqueadas
                if (["codcosto", "centro_tra", "cuenta", "total"].includes(colName)) {
                    $(this).removeClass("editable"); 
                } else if (index > 0 && index <= 23) {
                    // ✅ solo las demás editables
                    $(this).addClass("editable");
                }
            });
        },
        dom: 'Bfltip', // 🔥 agrega botones arriba de la tabla
        buttons: [
            {
                extend: 'excelHtml5',
                text: '📥 Exportar a Excel',
                filename: 'presupuesto_almacen_buga_auxiliar',
                exportOptions: {
                columns: ':visible:not(:lt(2))',
                    format: {
                        body: function (data, row, column, node) {
                        // Helper: quitar etiquetas HTML y trim
                        function stripHtml(input) {
                            if (input === null || input === undefined) return '';
                            if (typeof input !== 'string') return input;
                            return input.replace(/<\/?[^>]+(>|$)/g, "").trim();
                        }

                        var txt = stripHtml(data);

                        // Índices de tus columnas numéricas según tu DataTable (0-based)
                        var moneyCols = [4,5,6,7,8,9,10,11,12,13,14,15,16];
                        

                        // Si es columna de dinero: quitar separadores de miles, símbolo y ajustar decimal
                        if (moneyCols.indexOf(column) !== -1) {
                            txt = String(txt)
                                    .replace(/\s/g,'')    // quita espacios
                                    .replace(/\$/g,'')    // quita signo peso (si lo hubiera)
                                    .replace(/\./g,'')    // quita separador de miles
                                    .replace(/,/g,'.')    // cambia coma decimal por punto
                                    .replace(/[^0-9.-]/g,''); // deja sólo números, punto y signo
                            return txt === '' ? 0 : txt;
                        }

                        // Columnas de texto: devolver el texto limpio (sin HTML)
                        return txt;
                        }
                    }
                }
            }
        ],
        scrollX: true,   // 🔥 Activa scroll horizontal
        scrollY: "65vh",   // altura de la tabla
        scrollCollapse: true, // si hay pocas filas, la tabla se ajusta
        fixedHeader: true,   // 🔥 Aquí activamos el header fijo
        pageLength: 50
    });

    // función para recalcular total de una fila
    function recalcularTotal(rowData) {
        let meses = ["enero","febrero","marzo","abril","mayo","junio",
                    "julio","agosto","septiembre","octubre","noviembre","diciembre"];
        let total = 0;
        meses.forEach(m => {
            total += parseFloat(rowData[m]) || 0;
        });
        rowData.total = total;
        return rowData;
    }

    // cerrar edición y guardar valor
    function cerrarEdicion(cell, newValue) {
        try {
            if (!table) {
                // console.error("Error: la tabla no está inicializada."); 
                return;
            }

            // Asegurarse de que la celda aún existe en el DOM
            if (!cell || !$.contains(document, cell)) {
                // console.warn("La celda ya no existe en el DOM. Cancelando edición.");
                editingCell = null;
                return;
            }

            const dtCell = table.cell(cell);
            if (!dtCell || dtCell.index() === undefined) {
                // console.warn("La celda de DataTables ya no es válida.");
                editingCell = null;
                return;
            }

            const colIdx = dtCell.index().column;
            const row = table.row($(cell).closest("tr"));
            const rowData = row.data();

            if (!rowData) {
                // console.warn("No se pudo obtener la fila asociada a la celda."); 
                editingCell = null;
                return;
            }

            const colName = table.column(colIdx).dataSrc();
            if (!colName) {
                // console.warn("No se encontró la columna para índice:", colIdx);
                editingCell = null;
                return;
            }

            // Actualizar el valor en los datos de la fila
            rowData[colName] = newValue;

            // Recalcular total dinámicamente (según tu lógica)
            const newRowData = recalcularTotal(rowData);

            // Actualizar la fila sin redibujar completamente
            row.data(newRowData).draw(false);

        } catch (err) {
            console.error("Error en cerrarEdicion:", err);
        } finally {
            editingCell = null;
        }
    }


    // ======== 🔹 GESTIÓN DE FILA ACTIVA (solo color) ========
    function seleccionarFila($row) {
        // Quitar selección previa
        $('#tempTable tbody tr').removeClass('fila-activa');
        // Marcar la nueva fila
        $row.addClass('fila-activa');
    }

    // Seleccionar fila cuando se hace clic
    $('#tempTable').on('click', 'tbody tr', function() {
        seleccionarFila($(this));
    });

    // Seleccionar fila automáticamente al editar
    $('#tempTable').on('dblclick', 'td.editable', function() {
        seleccionarFila($(this).closest('tr'));
    });

    // 🔹 Permitir redimensionar verticalmente el contenedor del DataTable
    const container = document.getElementById('tableContainer');
    const handle = document.getElementById('resizeHandle');

    if (handle && container) {
        let isResizing = false;
        let startY;
        let startHeight;

        handle.addEventListener('mousedown', function(e) {
            isResizing = true;
            startY = e.clientY;
            startHeight = container.offsetHeight;
            document.body.style.cursor = 'ns-resize';
        });

        document.addEventListener('mousemove', function(e) {
            if (!isResizing) return;
            const dy = e.clientY - startY;
            container.style.height = `${startHeight + dy}px`;
        });

        document.addEventListener('mouseup', function() {
            if (isResizing) {
                isResizing = false;
                document.body.style.cursor = 'default';
            }
        });
    }

    // ✅ Checkbox maestro para seleccionar/deseleccionar todos
    $('#checkAllIPC').on('change', function() {
        let checked = $(this).is(':checked');
        $('.row-check').prop('checked', checked);
    });

    // ✅ Si se desmarca una sola fila, se desmarca el "Seleccionar todo"
    $('#tempTable').on('change', '.row-check', function() {
        if (!$(this).is(':checked')) {
            $('#checkAllIPC').prop('checked', false);
        } else if ($('.row-check:checked').length === $('.row-check').length) {
            $('#checkAllIPC').prop('checked', true);
        }
    });
    // ✅ Si se desmarca una sola fila → se desmarca el "Seleccionar todo"
    $('#tempTable').on('change', '.row-check', function() {
        if (!$(this).is(':checked')) {
            $('#checkAllIPC').prop('checked', false);
        } else if ($('.row-check:checked').length === $('.row-check').length) {
            $('#checkAllIPC').prop('checked', true);
        }
    });

    // ✅ Sincronizar checkbox maestro al recargar la tabla (por Ajax o redraw)
    table.on('draw', function() {
        let total = $('.row-check').length;
        let marcados = $('.row-check:checked').length;

        if (marcados === 0) {
            $('#checkAllIPC').prop('checked', false).prop('indeterminate', false);
        } else if (marcados === total) {
            $('#checkAllIPC').prop('checked', true).prop('indeterminate', false);
        } else {
            $('#checkAllIPC').prop('checked', false).prop('indeterminate', true);
        }
    });
    let filaAEliminar = null; // 🔥 Guardar la fila temporal
    let editingCell = null;
    
    // duplicar fila
    $('#tempTable').on('click', '.duplicarFila', function() {
        let row = table.row($(this).parents('tr'));
        let rowData = row.data();
        let currentIndex = row.index();

        // clonar datos
        let newRow = { ...rowData };

        // reiniciar meses
        let meses = ["enero","febrero","marzo","abril","mayo","junio",
                    "julio","agosto","septiembre","octubre","noviembre","diciembre"];
        meses.forEach(m => newRow[m] = 0);

        // total en 0
        newRow.total = 0;

        // 🔹 obtener todos los datos actuales de la tabla
        let allData = table.rows().data().toArray();

        // 🔹 insertar justo después del índice actual
        allData.splice(currentIndex + 1, 0, newRow);

        // 🔹 limpiar y volver a cargar los datos sin alterar scroll
        let scrollBody = $('.dataTables_scrollBody');
        let scrollPos = scrollBody.scrollTop();

        table.clear().rows.add(allData).draw(false);

        // 🔹 restaurar scroll y mantener selección
        setTimeout(() => {
            scrollBody.scrollTop(scrollPos);

            // buscar la nueva fila duplicada
            let $newRowNode = $('#tempTable tbody tr').eq(currentIndex + 1);

            // seleccionar y animar
            seleccionarFila($newRowNode);
            $newRowNode.addClass("blink");
            setTimeout(() => $newRowNode.removeClass("blink"), 2000);
        }, 50);

        showToast("Fila duplicada 📑", "success");
    });

    // lista desplegable para columna nombre centro
    const opcionesNombreCentro = {
        "ALMACEN TULUA": {codigoCosto: "020202", centro: "001"},
        "ALMACEN BUGA": {codigoCosto: "020200", centro: "002"},
        "ALMACEN CARTAGO": {codigoCosto: "020202", centro: "003"},
        "ALMACEN CALI" : {codigoCosto: "020202", centro: "004"},
        "ADMINISTRACIÓN" : {codigoCosto: "0102", centro: "001"},
        "SEVICIOS TÉCNICOS" : {codigoCosto: "020302", centro: "001"},
    };

    // ==========================
    //  LÓGICA DE EDICIÓN TIPO EXCEL
    // ==========================

    // doble clic para editar
    $('#tempTable').on('dblclick', 'td.editable', function() {
        if (!editando) {
            showToast("⚠️ Estás editando la tabla. Recuerda guardar los cambios.", "error", 0, true);
            editando = true;
        }
        let cell = table.cell(this);
        let oldValue = cell.data();
        let colIdx = table.cell(this).index().column;
        let colName = table.column(colIdx).dataSrc();

        // 🔥 Si ya hay otra celda editándose, cerrarla primero
        if (editingCell && editingCell !== this) {
            let $prevInput = $(editingCell).find("input");
            if ($prevInput.length) {
                cerrarEdicion(editingCell, $prevInput.val());
            }
        }

        // Si la misma celda está en edición, no volver a abrir
        if (editingCell === this) return;

        // si es columna con desplegable
        if (colName === "cuenta_mayor") {
            let opciones = Object.keys(mapaCuentaMayor); // 🔥 ahora son las claves (códigos)
            let row = table.row($(this).closest("tr"));
            let rowData = row.data();
            
            // 🔥 Si el nombre_cen es ADMINISTRACIÓN → solo mostrar claves que empiezan con 51
            if (rowData["nombre_cen"] && rowData["nombre_cen"].toUpperCase() === "ADMINISTRACIÓN") {
                opciones = opciones.filter(o => o.startsWith("51"));
            }else{
                // 🔥 Si no es administración → excluir todas las que empiezan con 51
                opciones = opciones.filter(o => !o.startsWith("51"));
            }

            // 🔥 Lista de códigos a excluir exactamente
            const excluir = [
                "51", "52", "5105", "5110", "54",
                "541001", "541003", "541006", "5410",
                "541019", "541027", "541033", "541095"
            ];
            // 🔥 Filtrar excluyendo solo coincidencias exactas
            opciones = opciones.filter(o => !excluir.includes(o));

            // 🔹 Ordenamos por la clave (código) ascendente
            opciones.sort((a, b) => a.localeCompare(b, 'es', { numeric: true }));
            let htmlSelect = `<select class="cell-select">` +
            opciones.map(o => {
                let leyenda = mapaCuentaMayor[o] || "";
                return `<option value="${o}" ${o==oldValue ? "selected":""}>${o} - ${leyenda}</option>`;
            }).join("") +
            `</select>`;

            $(this).html(htmlSelect);
            let $select = $(this).find("select").focus();
            editingCell = this;

            $select.on("change blur", function() {
                let nuevoValor = $(this).val();
                
                rowData["cuenta_mayor"] = mapaCuentaMayor[nuevoValor] || "";
                rowData["cuenta"] = nuevoValor;
                // 🔥 Condición especial: si es capacitación o salud ocupacional → codcosto = 0101
                if (nuevoValor === "510531" || nuevoValor === "51059503") {
                    rowData["codcosto"] = "0101";
                }
                if (nuevoValor === "540531" || nuevoValor === "54059503") {
                    rowData["codcosto"] = "020201";
                }

                // 🔥 Esperar al siguiente ciclo de ejecución para evitar error del blur
                setTimeout(() => {
                    row.data(rowData).draw(false);
                    editingCell = null;
                }, 0);
            });


            $select.on("keydown", function(e) {
                if (e.key === "Enter") {
                    cerrarEdicion(editingCell, $(this).val());
                } else if (e.key === "Escape") {
                    table.cell(editingCell).data(oldValue).draw(false);
                    editingCell = null;
                }
            });
        } else if (colName === "nombre_cen") {
            let opciones = Object.keys(opcionesNombreCentro);
            let htmlSelect = `<select class="cell-select">` +
                opciones.map(o => `<option value="${o}" ${o==oldValue ? "selected":""}>${o}</option>`).join("") +
                `</select>`;
            $(this).html(htmlSelect);
            let $select = $(this).find("select").focus();
            editingCell = this;

            $select.on("change blur", function() {
                let nuevoValor = $(this).val();
                // 🔥 Actualizar columnas código costo y centro en la misma fila
                let row = table.row($(editingCell).closest("tr"));
                let rowData = row.data();
                rowData["nombre_cen"] = nuevoValor;
                rowData["codcosto"] = opcionesNombreCentro[nuevoValor]?.codigoCosto || "";
                rowData["centro_tra"] = opcionesNombreCentro[nuevoValor]?.centro || "";
                
                // 🔥 Esperar al siguiente ciclo de ejecución para evitar error del blur
                setTimeout(() => {
                    row.data(rowData).draw(false);
                    editingCell = null;
                }, 0);
            });

            $select.on("keydown", function(e) {
                if (e.key === "Enter") {
                    cerrarEdicion(editingCell, $(this).val());
                } else if (e.key === "Escape") {
                    table.cell(editingCell).data(oldValue).draw(false);
                    editingCell = null;
                }
            });
        } 
        else {
            // para otras columnas, input de texto
            $(this).html('<input type="text" class="cell-input" value="'+ oldValue +'" style="min-width:40px; "/>');
            let $input = $(this).find("input").focus();
            editingCell = this;
            // seleccionar todo el contenido
            $input[0].setSelectionRange(0, $input.val().length);
            
            // 🔹 Crear un span oculto para medir el ancho del texto
            let $mirror = $('<span>')
                .css({
                    position: 'absolute',
                    top: '-9999px',
                    left: '-9999px',
                    whiteSpace: 'pre',
                    font: $input.css('font'),
                    padding: $input.css('padding'),
                    border: $input.css('border')
                })
                .appendTo('body');

            // 🔹 Función para ajustar el ancho dinámicamente
            function ajustarAncho() {
                $mirror.text($input.val() || ' ');
                const newWidth = $mirror.width() + 15; // margen extra
                
                $input.css('width', newWidth + 'px');
            }

            // 🔹 Ajustar al inicio y en cada cambio
            ajustarAncho();
            $input.on('input', ajustarAncho);

            // 🔹 Al cerrar edición, eliminar el span espejo
            $input.on('blur', function() {
                $mirror.remove();
            });

            // 🔹 Validación: si la columna es un mes, solo permitir números enteros
            const mesesCols = ["enero","febrero","marzo","abril","mayo","junio",
                    "julio","agosto","septiembre","octubre","noviembre","diciembre"];

            if (mesesCols.includes(colName)) {
                // Solo permitir dígitos
                $input.on("input", function() {
                    this.value = this.value.replace(/[^0-9]/g, ""); 
            });
            } else{
                // 🔥 convertir a mayúsculas mientras escribe (para comentarios u otros textos)
                $input.on("input", function() {
                    this.value = this.value.toUpperCase();
                });
            }

            // manejar Enter, Escape y flechas
            $input.on("keydown", function(e) {
                const key = e.key;
                const cursorPos = this.selectionStart;
                const cursorEnd = this.selectionEnd;
                const valueLength = this.value.length;

                if (key === "Enter") {
                    e.preventDefault();
                    moverCelda("ArrowDown", editingCell, $input.val());
                    return;
                }
                if (key === "Escape") {
                    table.cell(editingCell).data(oldValue).draw(false);
                    editingCell = null;
                    return;
                }
                // 🔸 Tab → moverse hacia la DERECHA
                if (key === "Tab") {
                    e.preventDefault();
                    moverCelda("ArrowRight", editingCell, $input.val());
                    return;
                }

                // 🧭 Flechas: comportamiento como Excel fuera de edición,
                // pero dentro de edición se mueven dentro del input.
                if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(key)) {

                    // 🔸 Si hay texto seleccionado, no mover a otra celda.
                    if (cursorPos !== cursorEnd) return;

                    // 🔸 Si la flecha es izquierda y no estamos al inicio → mover el cursor
                    if (key === "ArrowLeft" && cursorPos > 0) return;
                    // 🔸 Si la flecha es derecha y no estamos al final → mover el cursor
                    if (key === "ArrowRight" && cursorPos < valueLength) return;

                    // 🔸 En caso contrario, movernos a la celda adyacente
                    e.preventDefault();
                    moverCelda(key, editingCell, $input.val());
                }
            });

            // 🔸 Función auxiliar para moverse entre celdas
            function moverCelda(key, editingCell, value) {
                let $td = $(editingCell);
                let $tr = $td.closest("tr");
                let rowIdx = $tr.index();
                let colIdx = $td.index();

                if (key === "ArrowUp") rowIdx--;
                if (key === "ArrowDown") rowIdx++;
                if (key === "ArrowLeft") colIdx--;
                if (key === "ArrowRight") colIdx++;

                let $target = $('#tempTable tbody tr').eq(rowIdx).find("td").eq(colIdx);
                if ($target.length && $target.hasClass("editable")) {
                    cerrarEdicion(editingCell, value);
                    $target.dblclick();
                }else {
                    // Si la celda siguiente no es editable, buscar la próxima editable
                    let $nextEditable;
                    if (key === "ArrowRight" || key === "Tab") {
                        $nextEditable = $tr.find("td.editable").filter(function() {
                            return $(this).index() > colIdx;
                        }).first();
                    } else if (key === "ArrowDown" || key === "Enter") {
                        $nextEditable = $('#tempTable tbody tr').eq(rowIdx)
                            .find("td.editable").eq($td.index());
                    }
                    if ($nextEditable && $nextEditable.length) {
                        cerrarEdicion(editingCell, value);
                        $nextEditable.dblclick();
                    } else {
                        cerrarEdicion(editingCell, value);
                    }
                }
            }

        }
    });
    // 🔥 Guardar automáticamente cuando se hace clic FUERA de la celda en edición
    $(document).on("click", function(e) {
        if (editingCell) {
            const $cell = $(editingCell);
            const $inputOrSelect = $cell.find("input, select");

            // ✅ Si el clic fue dentro de la celda que se está editando, NO cerrar la edición
            if ($cell.is(e.target) || $.contains($cell[0], e.target)) {
                return; // como Excel: permite seguir interactuando con el campo
            }

            // ✅ Si se hace clic fuera, cerrar edición y guardar
            if ($inputOrSelect.length) {
                cerrarEdicion(editingCell, $inputOrSelect.val());
            }
        }
    });

    // Botones cancelar de cualquier modal
    $('.btn-cancel').on('click', function() {
        let modalId = $(this).data('modal'); // viene del atributo data-modal="..."
        cerrarModal(modalId);
    });

    // agregar fila vacía
    $('#agregarFila').on('click', function() {
        table.row.add({
            centro_tra: "",
            nombre_cen: "",
            codcosto: "",
            responsable: "",
            cuenta: 0,
            cuenta_mayor: "",
            detalle_cuenta: "",
            sede_distribucion: 0,
            proveedor: "",
            enero: 0,
            febrero: 0,
            marzo: 0,
            abril: 0,
            mayo: 0,
            junio: 0,
            julio: 0,
            agosto: 0,
            septiembre: 0,
            octubre: 0,
            noviembre: 0,
            diciembre: 0,
            total: 0,
            comentario: ""
        }).draw();
        showToast("Fila agregada ✅", "success");
    });

    // 🗑 Confirmación de eliminar fila
    $('#tempTable').on('click', '.eliminarFila', function() {
        filaAEliminar = table.row($(this).parents('tr'));
        abrirModal('modalEliminar');
    });

    $('#confirmEliminar').on('click', function() {
        if (filaAEliminar) {
            let currentNode = filaAEliminar.node();
            let $currentRow = $(currentNode);
            let $nextRow = $currentRow.next('tr');
            // 🔹 Guardar posición actual del scroll
            let scrollPos = $('.dataTables_scrollBody').scrollTop();

            // 🔹 Eliminar fila sin reiniciar la posición
            filaAEliminar.remove().draw(false);
            // 🔹 Restaurar scroll después del redibujado
            $('.dataTables_scrollBody').scrollTop(scrollPos);

            // Seleccionar siguiente fila si existe, sino la anterior
            if ($nextRow.length) {
                seleccionarFila($nextRow);
            } else {
                let $prevRow = $currentRow.prev('tr');
                if ($prevRow.length) seleccionarFila($prevRow);
            }
            showToast("Fila eliminada ❌", "error");
            filaAEliminar = null;
        }
        cerrarModal('modalEliminar');
    });


    // Configurar CSRF para AJAX
    function getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]').getAttribute("content");
    }

    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!(/^GET|HEAD|OPTIONS|TRACE$/i.test(settings.type))) {
                xhr.setRequestHeader("X-CSRFToken", getCSRFToken());
            }
        }
    });

    // Guardar en BD temporal
    // $('#guardarTempBtn').on('click', function() {
    //     let $btn = $(this);
    //     let $spinner = $btn.find('.spinner');
    //     let data = table.rows().data().toArray();

    //     // Mostrar spinner
    //     $spinner.show();
    //     $btn.prop("disabled", true);

    //     $.ajax({
    //         url: "{% url 'guardar_almacen_buga_temp' %}",
    //         type: "POST",
    //         data: JSON.stringify(data),
    //         contentType: "application/json",
    //         success: function() {
    //             showToast("Datos guardados en tabla temporal ✅", "success");
    //             // ✅ Ocultar advertencia al guardar
    //             if (persistentToast) {
    //                 persistentToast.classList.remove("show");
    //                 setTimeout(() => {
    //                     if (persistentToast && document.body.contains(persistentToast)) {
    //                         persistentToast.remove();
    //                     }
    //                     persistentToast = null;
    //                 }, 500);
    //             }
    //             editando = false;
    //         },
    //         error: function() {
    //             showToast("Error al guardar ❌", "error");
    //         },
    //         complete: function() {
    //             // Ocultar spinner y reactivar botón
    //             $spinner.hide();
    //             $btn.prop("disabled", false);
    //         }
    //     });
    // });

    // =====================================================
    // 🔹 BOTÓN: EXPORTAR PLANTILLA EXCEL VACÍA
    // =====================================================
    $('#exportarPlantillaBtn').on('click', function() {
        // 🔸 Encabezados que quieres en la plantilla
        const headers = [
            "MCNCUENTA", "MCNFECHA", "MCNTIPODOC", "MCNNUMEDOC", "MCNVINCULA", 
            "VINNOMBRE", "MCNSUCVIN", "SALDOANT", "MCNVALDEBI", "MCNVALCRED", 
            "SALDONEW", "MCNSUCURS", "MCNCCOSTO", "MCNDESTINO", "MCNDETALLE", 
            "MCNZONA", "CCONOMBRE", "DNONOMBRE", "ZONNOMBRE", "MCNEMPRESA", 
            "MCNCLASE", "MCNVINKEY", "TPREG", "CTANOMBRE", "DOCDETALLE", "INFDETALLE"
        ];

        // 🔸 Crear un libro y una hoja usando SheetJS (si no está, se puede agregar CDN)
        const wb = XLSX.utils.book_new();
        const ws = XLSX.utils.aoa_to_sheet([headers]); // Solo fila de headers

        // 🔸 Añadir la hoja al libro
        XLSX.utils.book_append_sheet(wb, ws, "Plantilla");

        // 🔸 Generar archivo y descargarlo
        XLSX.writeFile(wb, "plantilla_base_presupuesto.xlsx");
    });

    // ===========================================================
    // 🔹 SUBIR Y VALIDAR ARCHIVO EXCEL
    // ===========================================================

    document.getElementById("btnCargarExcel").addEventListener("click", () => {
        document.getElementById("inputExcel").click();
    });

    document.getElementById("inputExcel").addEventListener("change", function (e) {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = function (event) {
            const data = new Uint8Array(event.target.result);
            const workbook = XLSX.read(data, { type: "array" });
            const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
            const jsonData = XLSX.utils.sheet_to_json(firstSheet, { defval: null });

            if (jsonData.length === 0) {
                alert("⚠️ El archivo está vacío o no tiene datos.");
                return;
            }

            // Validar columnas requeridas
            const requiredColumns = [
                "MCNCUENTA", "MCNFECHA", "MCNTIPODOC", "MCNNUMEDOC",
                "MCNVINCULA", "VINNOMBRE", "MCNSUCVIN", "SALDOANT",
                "MCNVALDEBI", "MCNVALCRED", "SALDONEW", "MCNSUCURS",
                "MCNCCOSTO", "MCNDESTINO", "MCNDETALLE", "MCNZONA",
                "CCONOMBRE", "DNONOMBRE", "ZONNOMBRE", "MCNEMPRESA",
                "MCNCLASE", "MCNVINKEY", "TPREG", "CTANOMBRE",
                "DOCDETALLE", "INFDETALLE"
            ];

            const fileColumns = Object.keys(jsonData[0]);
            const missingCols = requiredColumns.filter(c => !fileColumns.includes(c));
            if (missingCols.length > 0) {
                alert("❌ Faltan columnas obligatorias:\n" + missingCols.join(", "));
                return;
            }

            // Validación de tipos de datos
            const errores = [];
            const registrosValidos = [];

            jsonData.forEach((row, index) => {
                const numRow = index + 2; // fila Excel (1 es encabezado)
                try {
                    const validRow = {
                        mcncuenta: parseString(row.MCNCUENTA),
                        mcnfecha: parseFloatOrNull(row.MCNFECHA),
                        mcntipodoc: parseString(row.MCNTIPODOC),
                        mcnnumedoc: parseBigInt(row.MCNNUMEDOC),
                        mcnvincula: parseFloatOrNull(row.MCNVINCULA),
                        vinnombre: parseString(row.VINNOMBRE),
                        mcnsucvin: parseString(row.MCNSUCVIN),
                        saldoant: parseBigInt(row.SALDOANT),
                        mcnvaldebi: parseFloatOrNull(row.MCNVALDEBI),
                        mcnvalcred: parseFloatOrNull(row.MCNVALCRED),
                        saldonew: parseFloatOrNull(row.SALDONEW),
                        mcnsucurs: parseString(row.MCNSUCURS),
                        mcnccosto: parseString(row.MCNCCOSTO),
                        mcndestino: parseString(row.MCNDESTINO),
                        mcndetalle: parseString(row.MCNDETALLE),
                        mcnzona: parseString(row.MCNZONA),
                        cconombre: parseString(row.CCONOMBRE),
                        dnonombre: parseString(row.DNONOMBRE),
                        zonnombre: parseString(row.ZONNOMBRE),
                        mcnempresa: parseString(row.MCNEMPRESA),
                        mcnclase: parseString(row.MCNCLASE),
                        mcnvinkey: parseString(row.MCNVINKEY),
                        tpreg: parseBigInt(row.TPREG),
                        ctanombre: parseString(row.CTANOMBRE),
                        docdetalle: parseString(row.DOCDETALLE),
                        infdetalle: parseString(row.INFDETALLE),
                    };

                    registrosValidos.push(validRow);
                } catch (error) {
                    errores.push(`Fila ${numRow}: ${error.message}`);
                }
            });

            if (errores.length > 0) {
                alert("❌ Errores encontrados:\n" + errores.slice(0, 10).join("\n") + 
                    (errores.length > 10 ? `\n...y ${errores.length - 10} más` : ""));
                return;
            }

            // Enviar datos válidos al backend
            fetch("/presupuesto/subir_excel_cuenta5/", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": getCookie("csrftoken") },
                body: JSON.stringify({ registros: registrosValidos }),
            })
            .then(resp => resp.json())
            .then(data => {
                alert(`✅ ${data.insertados} registros cargados correctamente`);
            })
            .catch(err => {
                console.error(err);
                alert("❌ Error al subir los datos.");
            });
        };

        reader.readAsArrayBuffer(file);
    });

    // ===========================================================
    // Funciones auxiliares para validación
    // ===========================================================
    function parseBigInt(value) {
        if (value === null || value === "") return null;
        const parsed = Number(value);
        if (!Number.isInteger(parsed)) throw new Error(`Se esperaba un número entero, recibido: ${value}`);
        return parsed;
    }
    function parseFloatOrNull(value) {
        if (value === null || value === "") return null;
        const parsed = parseFloat(value);
        if (isNaN(parsed)) throw new Error(`Se esperaba un número decimal, recibido: ${value}`);
        return parsed;
    }
    function parseString(value) {
        if (value === null) return null;
        return String(value);
    }
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== "") {
            const cookies = document.cookie.split(";");
            for (let cookie of cookies) {
                cookie = cookie.trim();
                if (cookie.startsWith(name + "=")) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    $("#btnBorrar").on("click", function () {
        if (!confirm("⚠️ ¿Estás seguro de borrar todo el presupuesto? Esta acción no se puede deshacer.")) {
            return;
        }

        $.ajax({
            url: url_borrar_cuenta5_base, // 🔥 Nueva vista Django
            type: "POST",
            headers: { "X-CSRFToken": $("meta[name='csrf-token']").attr("content") },
            success: function (response) {
                showToast("Presupuesto eliminado correctamente ✅", "success");
                table.ajax.reload(null, false); // recarga sin perder paginación
            },
            error: function (xhr) {
                showToast("Error al borrar ❌: " + xhr.responseText, "error");
            }
        });
    });

    function showToast(message, type = "success", duration = 3000, persistent = false) {
        let container = document.getElementById("toastContainer");
        let toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.textContent = message;

        container.appendChild(toast);

        setTimeout(() => toast.classList.add("show"), 50);

        if (persistent) {
            persistentToast = toast; // lo guardamos
        } else {
            setTimeout(() => {
                toast.classList.remove("show");
                setTimeout(() => toast.remove(), 500);
            }, duration);
        }
    }
    
});

