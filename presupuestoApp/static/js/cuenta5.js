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
            type: "POST",
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            dataSrc: 'data'
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
                    <button class="eliminarFila" title="Eliminar fila">❌</button>
                `,
                orderable: false,
                width: "60px"
            },
            
            { data: 'mcncuenta'},
            { data: 'mcnfecha'},
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

    // Botones cancelar de cualquier modal
    $('.btn-cancel').on('click', function() {
        let modalId = $(this).data('modal'); // viene del atributo data-modal="..."
        cerrarModal(modalId);
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
        const $btn = $('#btnCargarExcel');
        const $spinner = $btn.find('.spinner');
        $spinner.show();
        $btn.prop("disabled", true);
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
                $spinner.hide();
                $btn.prop("disabled", false);
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
                    $spinner.hide();
                    $btn.prop("disabled", false);
                }
            });

            if (errores.length > 0) {
                alert("❌ Errores encontrados:\n" + errores.slice(0, 10).join("\n") + 
                    (errores.length > 10 ? `\n...y ${errores.length - 10} más` : ""));
                $spinner.hide();
                $btn.prop("disabled", false);
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
                table.ajax.reload(null, false); // recargar tabla sin perder paginación
                $spinner.hide();
                $btn.prop("disabled", false);
            })
            .catch(err => {
                console.error(err);
                alert("❌ Error al subir los datos.");
                $spinner.hide();
                $btn.prop("disabled", false);
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
        if (!Number.isInteger(parsed)) {
            $spinner.hide();
            $btn.prop("disabled", false);
            throw new Error(`Se esperaba un número entero, recibido: ${value}`);
        }
        return parsed;
    }
    function parseFloatOrNull(value) {
        if (value === null || value === "") return null;
        const parsed = parseFloat(value);
        if (isNaN(parsed)) {
            $spinner.hide();
            $btn.prop("disabled", false);
            throw new Error(`Se esperaba un número decimal, recibido: ${value}`);
        }
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

    $("#btnBorrar").on("click", function (e) {
        e.preventDefault();
        abrirModal('modalEliminarCuenta');
    });

    $("#confirmEliminarCuenta").on("click", function () {
        cerrarModal('modalEliminarCuenta');
        $.ajax({
            url: url_borrar_cuenta5_base, // 🔥 Nueva vista Django
            type: "POST",
            headers: { "X-CSRFToken": $("meta[name='csrf-token']").attr("content") },
            success: function (response) {
                showToast("Presupuesto eliminado correctamente ✅", "success");
                table.ajax.reload(null, false); 
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

