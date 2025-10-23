// 🔹 Agregar selects dinámicos en las filas después de cada redibujo
table.on('draw', function() {
    // Agregar selects dinámicos en las columnas deseadas (centro, área, cargo, concepto)
    $('#presupuestoTable tbody tr').each(function() {
        let $row = $(this);
        let data = table.row($row).data();
        if (!data) return;

        // Generar selects si no existen
        if (!$row.find('.select-centro').length) {
            let selectCentro = `<select class="select-centro select2">
                {% for c in centros %}
                    <option value="{{ c|escape }}">{{ c }}</option>
                {% endfor %}
            </select>`;
            $row.find('td:eq(3)').html(selectCentro);
        }

        if (!$row.find('.select-area').length) {
            let selectArea = `<select class="select-area select2">
                {% for a in areas %}
                    <option value="{{ a|escape }}">{{ a }}</option>
                {% endfor %}
            </select>`;
            $row.find('td:eq(4)').html(selectArea);
        }

        if (!$row.find('.select-cargo').length) {
            let selectCargo = `<select class="select-cargo select2">
                {% for c in cargos %}
                    <option value="{{ c|escape }}">{{ c }}</option>
                {% endfor %}
            </select>`;
            $row.find('td:eq(5)').html(selectCargo);
        }

        if (!$row.find('.select-concepto').length) {
            let selectConcepto = `<select class="select-concepto select2">
                {% for c in conceptos %}
                    <option value="{{ c|escape }}">{{ c }}</option>
                {% endfor %}
            </select>`;
            $row.find('td:eq(6)').html(selectConcepto);
        }

        // Asignar el valor actual
        $row.find('.select-centro').val(data.centro);
        $row.find('.select-area').val(data.area);
        $row.find('.select-cargo').val(data.cargo);
        $row.find('.select-concepto').val(data.concepto);

        // Activar select2
        $row.find('.select2').select2({
            width: '100%',
            dropdownAutoWidth: true,
            placeholder: 'Seleccionar...',
            allowClear: true
        });

        // Actualizar los datos del DataTable cuando cambie
        $row.find('select').on('change', function() {
            let updatedData = table.row($row).data();
            updatedData.centro = $row.find('.select-centro').val();
            updatedData.area = $row.find('.select-area').val();
            updatedData.cargo = $row.find('.select-cargo').val();
            updatedData.concepto = $row.find('.select-concepto').val();
            table.row($row).data(updatedData).invalidate().draw(false);
        });
    });
});

// --- Mapeo de Centro y Área por input ---
const configuracionDistribucion = {
    1: { centro: "ALMACEN TULUA", area: "VENTAS GASTOS DE PERSONAL" },
    2: { centro: "ALMACEN BUGA", area: "VENTAS GASTOS DE PERSONAL" },
    3: { centro: "ALMACEN CARTAGO", area: "VENTAS GASTOS DE PERSONAL" },
    4: { centro: "ALMACEN CALI", area: "VENTAS GASTOS DE PERSONAL" },
    5: { centro: "ALMACEN TULUA", area: "ADMINISTRACION DE PERSONAL" },
    6: { centro: "ALMACEN TULUA", area: "ASISTENCIA TECNICA CONVENIO" },
    7: { centro: "ALMACEN TULUA", area: "ASISTENCIA TECNICA PROPIA" },
};

// --- Distribución de porcentajes con actualización de centro y área ---
$(document).on("click", "#btnDistribuir", function () {
    let porcentajes = [];
    $(".input-porcentaje").each(function () {
        let val = parseFloat($(this).val()) || 0;
        porcentajes.push(val);
    });

    // ✅ Validar suma 100
    let suma = porcentajes.reduce((a, b) => a + b, 0);
    if (Math.abs(suma - 100) > 0.001) {
        showToast("❌ La suma de los porcentajes debe ser exactamente 100%.", "error");
        return;
    }

    // ✅ Obtener filas seleccionadas
    let table = $("#presupuestoTable").DataTable();
    let filasSeleccionadas = [];
    $("#presupuestoTable .row-check:checked").each(function () {
        let fila = $(this).closest("tr");
        let data = table.row(fila).data();
        filasSeleccionadas.push({ data, row: fila });
    });

    if (filasSeleccionadas.length === 0) {
        showToast("⚠️ Debes seleccionar al menos una fila.", "error");
        return;
    }

    let nuevasFilas = [];

    // ✅ Procesar duplicación según los porcentajes
    filasSeleccionadas.forEach(({ data }) => {
        porcentajes.forEach((p, idx) => {
            if (p > 0) {
                let nueva = { ...data }; // copia base
                let factor = p / 100.0;

                // calcular meses
                [
                    "enero","febrero","marzo","abril","mayo","junio",
                    "julio","agosto","septiembre","octubre","noviembre","diciembre"
                ].forEach(mes => {
                    nueva[mes] = Math.round(data[mes] * factor);
                });

                // recalcular total
                nueva["total"] = [
                    "enero","febrero","marzo","abril","mayo","junio",
                    "julio","agosto","septiembre","octubre","noviembre","diciembre"
                ].reduce((a, k) => a + (parseFloat(nueva[k]) || 0), 0);

                // --- 🔹 Actualizar Centro y Área según input ---
                let conf = configuracionDistribucion[idx + 1];
                if (conf) {
                    nueva["centro"] = conf.centro;
                    nueva["area"] = conf.area;
                }

                // --- 🔹 Actualizar concepto ---
                //nueva["concepto"] = data["concepto"] + ` (${p}%)`;

                nuevasFilas.push(nueva);
            }
        });
    });

    // ✅ Eliminar las filas originales seleccionadas
    filasSeleccionadas.forEach(({ row }) => {
        table.row(row).remove();
    });

    // ✅ Agregar las nuevas filas generadas
    nuevasFilas.forEach(fila => table.row.add(fila));

    // ✅ Redibujar la tabla
    table.draw(false);

    showToast(`✅ Se distribuyeron y reemplazaron ${filasSeleccionadas.length} fila(s) con ${nuevasFilas.length} nuevas.`, "success");
});


function seleccionarFila($row) {
    // Quitar selección previa
    $('#presupuestoTable tbody tr').removeClass('fila-activa');
    // Marcar la nueva fila
    $row.addClass('fila-activa');
}
// Seleccionar fila cuando se hace clic
$('#presupuestoTable').on('click', 'tbody tr', function() {
    seleccionarFila($(this));
});
// ✅ Checkbox maestro para seleccionar/deseleccionar todos
$('#checkAllIPC').on('change', function() {
    let checked = $(this).is(':checked');
    $('.row-check').prop('checked', checked);
});
// ✅ Si se desmarca una sola fila → se desmarca el "Seleccionar todo"
$('#presupuestoTable').on('change', '.row-check', function() {
    if (!$(this).is(':checked')) {
        $('#checkAllIPC').prop('checked', false);
    } else if ($('.row-check:checked').length === $('.row-check').length) {
        $('#checkAllIPC').prop('checked', true);
    }
}); 

// Función para mostrar toasts
function showToast(message, type = "success", duration = 3000) {
    let container = document.getElementById("toastContainer");

    // Crear toast
    let toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;

    // Insertar en el contenedor
    container.appendChild(toast);

    // Forzar reflow para animación
    setTimeout(() => toast.classList.add("show"), 50);

    // Ocultar y eliminar después de "duration"
    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => toast.remove(), 500); // eliminar después de animación
    }, duration);
}