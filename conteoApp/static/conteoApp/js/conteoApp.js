// ─────────────────────────────────────────────────────────────────────────────
// Utilidades
// ─────────────────────────────────────────────────────────────────────────────
function getCsrfToken() {
    const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (input && input.value) return input.value;
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
}

function mostrar(el) { if (el) el.style.display = 'block'; }
function ocultar(el) { if (el) el.style.display = 'none'; }

// ─────────────────────────────────────────────────────────────────────────────
// Ordenar tablas (clic en el encabezado)
// Lee cada celda una sola vez y usa textContent (innerText fuerza recalcular el
// diseño por cada celda y era muy lento en tablas grandes). Si la celda tiene un
// input/textarea se ordena por su valor.
// ─────────────────────────────────────────────────────────────────────────────
const collator = new Intl.Collator('es', { sensitivity: 'base', numeric: true });

function valorCelda(cell) {
    if (!cell) return '';
    const campo = cell.querySelector('input:not([type="checkbox"]), textarea');
    if (campo) return campo.value.trim();
    const check = cell.querySelector('input[type="checkbox"]');
    if (check) return check.checked ? '1' : '0';
    return cell.textContent.trim();
}

function aNumero(texto) {
    if (texto === '') return null;
    const normal = texto.replace(/\s/g, '').replace(',', '.');
    return /^-?\d+(\.\d+)?$/.test(normal) ? parseFloat(normal) : null;
}

function sortTableById(tableId, columnIndex) {
    const table = document.getElementById(tableId);
    if (!table || !table.tBodies.length) return;
    const tbody = table.tBodies[0];
    const asc = table.dataset.sortOrder === "asc";  // igual que antes: alterna en cada clic

    const filas = Array.from(tbody.rows).map(row => {
        const texto = valorCelda(row.cells[columnIndex]);
        return { row, texto, num: aNumero(texto) };
    });
    const todosNumeros = filas.every(f => f.num !== null || f.texto === '');

    filas.sort((a, b) => {
        let r;
        if (todosNumeros) {
            r = (a.num ?? 0) - (b.num ?? 0);
        } else {
            r = collator.compare(a.texto, b.texto);
        }
        return asc ? r : -r;
    });

    table.dataset.sortOrder = asc ? "desc" : "asc";
    tbody.replaceChildren(...filas.map(f => f.row));
}

// Compatibilidad con llamadas antiguas
function sortTable(columnIndex) {
    sortTableById("table-asignar", columnIndex);
}

// ─────────────────────────────────────────────────────────────────────────────
// Vista del contador: conteo, borradores y aviso de cambios sin guardar
// ─────────────────────────────────────────────────────────────────────────────
const formTareas = document.getElementById('form-tareas');
let isFormDirty = false;

// Advertir al usuario antes de salir si hay cambios no guardados
window.addEventListener('beforeunload', function (e) {
    if (isFormDirty) {
        e.preventDefault();
        e.returnValue = '';
    }
});

function camposConteo() {
    return formTareas ? formTareas.querySelectorAll('.input-conteo, .input-observacion') : [];
}

function guardarBorrador(input) {
    try { sessionStorage.setItem(input.name, input.value); } catch (e) { /* almacenamiento no disponible */ }
}

function limpiarBorradores() {
    camposConteo().forEach(input => {
        try { sessionStorage.removeItem(input.name); } catch (e) { /* ignorar */ }
    });
}

if (formTareas) {
    // Restaurar lo escrito y no guardado si la página se recarga. Si hay borradores
    // distintos a lo que dice el servidor, se marca el formulario como pendiente.
    camposConteo().forEach(input => {
        let guardado = null;
        try { guardado = sessionStorage.getItem(input.name); } catch (e) { /* ignorar */ }
        if (guardado !== null && guardado !== input.value) {
            input.value = guardado;
            isFormDirty = true;
        }
    });

    // Delegación de eventos: funciona también con las filas que llegan después de
    // "Actualizar conteo" (antes esas filas quedaban sin escuchar cambios).
    formTareas.addEventListener('input', function (event) {
        const el = event.target;
        if (el.matches('.input-conteo, .input-observacion')) {
            guardarBorrador(el);
            isFormDirty = true;
        }
    });
    formTareas.addEventListener('change', function () {
        isFormDirty = true;
    });
    // Evitar que Enter en un campo de conteo envíe el formulario de forma tradicional
    formTareas.addEventListener('submit', function (event) {
        event.preventDefault();
        const btn = document.getElementById('update-tarea');
        if (btn && !btn.disabled) btn.click();
    });
}

// Enviar el conteo por AJAX y reemplazar las filas con las pendientes
document.addEventListener("DOMContentLoaded", function () {
    const btn = document.getElementById("update-tarea");
    if (!formTareas || !btn) return;
    const modal = document.getElementById("processingModal");

    btn.addEventListener("click", function (e) {
        e.preventDefault();
        if (btn.disabled) return;  // evita doble envío

        const formData = new FormData(formTareas);
        formData.append("update_tarea", "1");

        mostrar(modal);
        btn.disabled = true;

        fetch(window.location.href, {
            method: "POST",
            headers: {
                "X-CSRFToken": getCsrfToken(),
                "X-Requested-With": "XMLHttpRequest"
            },
            body: formData,
            credentials: "same-origin"
        })
        .then(res => {
            const tipo = res.headers.get("content-type") || "";
            if (!tipo.includes("application/json")) {
                // Normalmente: la sesión expiró y el servidor devolvió la página de login
                throw new Error("La sesión expiró o el servidor no respondió correctamente. Recarga la página (lo escrito se conserva).");
            }
            return res.json();
        })
        .then(data => {
            if (data.status !== "ok") {
                throw new Error(data.msg || "Error al actualizar");
            }
            limpiarBorradores();          // lo guardado ya está en el servidor
            document.getElementById("tareas-body").innerHTML = data.html;
            isFormDirty = false;
        })
        .catch(err => {
            console.error(err);
            alert(err.message || "Hubo un problema, revisa la consola.");
        })
        .finally(() => {
            ocultar(modal);
            btn.disabled = false;
        });
    });
});

// ─────────────────────────────────────────────────────────────────────────────
// Panel de asignación
// ─────────────────────────────────────────────────────────────────────────────

// Buscador de usuarios y "Seleccionar todos" (mismo comportamiento para ambas listas)
function configurarListaUsuarios(searchId, listId, selectAllId, checkboxClass) {
    const searchInput = document.getElementById(searchId);
    const checkboxList = document.getElementById(listId);
    const selectAll = document.getElementById(selectAllId);
    if (!checkboxList) return;

    const labels = Array.from(checkboxList.getElementsByTagName('label'));
    const textos = labels.map(label => label.textContent.trim().toLowerCase());
    const checkboxes = () => checkboxList.querySelectorAll('.' + checkboxClass);

    if (searchInput) {
        searchInput.addEventListener('input', function () {
            const filter = searchInput.value.trim().toLowerCase();
            labels.forEach((label, i) => {
                label.style.display = textos[i].includes(filter) ? '' : 'none';
            });
        });
    }

    if (selectAll) {
        selectAll.addEventListener('change', function () {
            checkboxes().forEach(cb => { cb.checked = selectAll.checked; });
        });
        checkboxList.addEventListener('change', function (event) {
            if (event.target.classList.contains(checkboxClass)) {
                selectAll.checked = Array.from(checkboxes()).every(cb => cb.checked);
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', function () {
    configurarListaUsuarios('searchInput', 'checkboxList', 'selectAll', 'user-checkbox');
    configurarListaUsuarios('searchInput_homework', 'checkboxList_homework', 'selectAllHomework', 'user-checkbox-homework');
});

// Validar el formulario de historial (al menos un usuario y una fecha)
document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('filter_users_form');
    const modal = document.getElementById('customAlert');
    const closeAlertButton = document.getElementById('closeAlert');
    const alertMessage = document.getElementById('alertMessage');
    if (!form) return;

    function alerta(texto) {
        if (modal && alertMessage) {
            alertMessage.textContent = texto;
            mostrar(modal);
        }
    }

    form.addEventListener('submit', function (event) {
        const submitButton = event.submitter;
        const fechaInput = document.getElementById('fecha_asignacion');
        if (!submitButton) return;

        // Solo validar checkboxes si se presiona el botón "Filtrar usuarios seleccionados"
        if (submitButton.name === 'filter_users') {
            const marcados = document.querySelectorAll('#checkboxList_homework .user-checkbox-homework:checked');
            if (marcados.length === 0) {
                event.preventDefault();
                alerta('Por favor, selecciona al menos un usuario.');
                return;
            }
        }
        // Para ambos botones se valida la fecha
        if ((submitButton.name === 'filter_users' || submitButton.name === 'filter_all_users') && !fechaInput.value) {
            event.preventDefault();
            alerta('Por favor, selecciona una fecha.');
        }
    });

    if (closeAlertButton) {
        closeAlertButton.addEventListener('click', () => ocultar(modal));
    }
    window.addEventListener('click', function (event) {
        if (event.target === modal) ocultar(modal);
    });
});

// Confirmar la eliminación de las tareas asignadas
document.addEventListener("DOMContentLoaded", function () {
    const modal = document.getElementById("confirmModal");
    const openModalBtn = document.getElementById("openConfirmModal");
    const closeModalBtn = document.getElementById("cancelDelete");
    const confirmBtn = document.getElementById("confirmDelete");
    const form = document.getElementById("assign_delete_activate_form");
    if (!(modal && openModalBtn && closeModalBtn && confirmBtn && form)) return;

    openModalBtn.addEventListener("click", () => mostrar(modal));
    closeModalBtn.addEventListener("click", () => ocultar(modal));

    confirmBtn.addEventListener("click", function () {
        confirmBtn.disabled = true;  // evita doble envío
        const hiddenInput = document.createElement("input");
        hiddenInput.type = "hidden";
        hiddenInput.name = "delete_task";  // Debe coincidir con lo que Django espera
        hiddenInput.value = "1";
        form.appendChild(hiddenInput);
        form.submit();
    });

    window.addEventListener("click", function (event) {
        if (event.target === modal) ocultar(modal);
    });
});

// Deshabilitar el botón de asignar tareas y mostrar "Procesando..."
document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("assign_delete_activate_form");
    const assignButton = document.getElementById("assignButton");
    const modal = document.getElementById("processingModal");
    if (!(form && assignButton && modal)) return;

    form.addEventListener("submit", function (event) {
        if (event.submitter === assignButton) {
            assignButton.style.display = "none";
            mostrar(modal);
        }
    });
});

// Al volver con el botón "atrás" el navegador puede restaurar la página desde caché
// con el modal "Procesando..." abierto: se cierra y se restaura el botón.
window.addEventListener('pageshow', function (event) {
    if (event.persisted) {
        document.querySelectorAll('#processingModal').forEach(ocultar);
        const assignButton = document.getElementById("assignButton");
        if (assignButton) assignButton.style.display = "";
        const confirmBtn = document.getElementById("confirmDelete");
        if (confirmBtn) confirmBtn.disabled = false;
    }
});

// Marcar/desmarcar "verificado" (delegado: un solo listener para toda la tabla)
document.addEventListener("change", function (event) {
    const checkbox = event.target;
    if (!checkbox.classList || !checkbox.classList.contains("verificado-check")) return;
    if (typeof toggleVerificadoURL === "undefined") return;

    checkbox.disabled = true;
    fetch(toggleVerificadoURL, {
        method: "POST",
        headers: {
            "X-CSRFToken": getCsrfToken(),
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "XMLHttpRequest"
        },
        body: new URLSearchParams({ "tarea_id": checkbox.dataset.id }),
        credentials: "same-origin"
    })
    .then(response => response.json())
    .then(data => {
        if (data.status !== "ok") {
            alert("Error al actualizar el estado");
            checkbox.checked = !checkbox.checked;
        } else {
            checkbox.checked = data.verificado;  // estado real según el servidor
        }
    })
    .catch(() => {
        alert("Error en la petición");
        checkbox.checked = !checkbox.checked;
    })
    .finally(() => { checkbox.disabled = false; });
});
