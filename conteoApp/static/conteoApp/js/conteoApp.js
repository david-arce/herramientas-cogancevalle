// seleccionar el formulario especifico
const formTareas = document.getElementById('form-tareas');

// Variable para rastrear si hay cambios en el formulario
let isFormDirty = false;

// Detecta cambios en los inputs y textareas dentro del formulario
if (formTareas !== null) {
    formTareas.querySelectorAll('input, textarea').forEach(element => {
        element.addEventListener('change', (event) => {
            // Marca el formulario como modificado
            isFormDirty = true;
        });
    });
}

// Advertir al usuario antes de salir si hay cambios no guardados
window.addEventListener('beforeunload', function (e) {
    if (isFormDirty) {
        e.preventDefault();
        e.returnValue = '';
    }
});

// obtener el evento de click en el boton de enviar conteo
const btnUpdateTarea = document.getElementById('update-tarea');
if (btnUpdateTarea !== null) {
    btnUpdateTarea.addEventListener('click', function () {
        isFormDirty = false;
    });   
}

// guardar los valores de los inputs y textareas en el formulario por medio del sessionStorage y localStorage en caso de refrescar la pagina
document.addEventListener("DOMContentLoaded", function() {
    const inputs = document.querySelectorAll(".input-conteo, .input-observacion");

    // Cargar valores guardados
    inputs.forEach(input => {
        const savedValue = sessionStorage.getItem(input.name);
        if (savedValue !== null) {
            input.value = savedValue;
        }
    });

    // Guardar valores en tiempo real
    inputs.forEach(input => {
        input.addEventListener("input", () => {
            sessionStorage.setItem(input.name, input.value);
        });
    });
});

// borrar el cero por defecto del input de conteo al hacer clic en el input
// document.addEventListener("DOMContentLoaded", function () {
//     const inputs = document.querySelectorAll(".input-conteo"); // Seleccionar todos los campos de conteo

//     inputs.forEach(input => {
//         // Eliminar el cero inicial al enfocar el input
//         input.addEventListener("focus", () => {
//             if (input.value === "0") {
//                 input.value = ""; // Borra el cero
//             }
//         });

//         // Si el usuario deja el input vacío, volver a poner el cero
//         input.addEventListener("blur", () => {
//             if (input.value === "") {
//                 input.value = "0"; // Restaura el cero si está vacío
//             }
//         });
//     });
// });


// Función para ordenar la tabla
function sortTableById(tableId, columnIndex) {
  const table = document.getElementById(tableId);
  const tbody = table.tBodies[0];
  const rows = Array.from(tbody.rows);
  const asc = table.dataset.sortOrder === "asc";

  rows.sort((a, b) => {
    let aText = a.cells[columnIndex].innerText.trim().toLowerCase();
    let bText = b.cells[columnIndex].innerText.trim().toLowerCase();

    if (!isNaN(aText) && !isNaN(bText)) {
      return asc ? aText - bText : bText - aText;
    }
    return asc ? aText.localeCompare(bText) : bText.localeCompare(aText);
  });

  table.dataset.sortOrder = asc ? "desc" : "asc";
  tbody.replaceChildren(...rows);
}


// Función para ordenar la tabla
function sortTable(columnIndex) {
    const table = document.getElementById("table-asignar");
    let rows = Array.from(table.rows).slice(1); // Ignorar encabezado
    let ascending = table.dataset.sortOrder === "asc";

    rows.sort((rowA, rowB) => {
        let cellA = rowA.cells[columnIndex].innerText.toLowerCase();
        let cellB = rowB.cells[columnIndex].innerText.toLowerCase();

        if (!isNaN(cellA) && !isNaN(cellB)) {
            return ascending ? cellA - cellB : cellB - cellA;
        }

        return ascending ? cellA.localeCompare(cellB) : cellB.localeCompare(cellA);
    });

    table.dataset.sortOrder = ascending ? "desc" : "asc";
    
    rows.forEach(row => table.appendChild(row)); // Reorganizar filas
}

//funcion para buscar usuarios en el formnulario de asignar, eliminar y activar
document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('searchInput');
    const checkboxList = document.getElementById('checkboxList');
    if (!searchInput || !checkboxList) {
        return;
    }
    const labels = Array.from(checkboxList.getElementsByTagName('label'));

    searchInput.addEventListener('input', function () {
        const filter = searchInput.value.trim().toLowerCase();

        labels.forEach(label => {
            const text = label.innerText.trim().toLowerCase();
            if (text.includes(filter)) {
                label.style.display = '';  // Mostrar si coincide
            } else {
                label.style.display = 'none';  // Ocultar si no coincide
            }
        });
    });
});

//funcion para buscar usuarios en el formnulario de filtrar 
document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('searchInput_homework');
    const checkboxList = document.getElementById('checkboxList_homework');

    // Verificar que los elementos existen antes de continuar
    if (searchInput && checkboxList) {
        const labels = Array.from(checkboxList.getElementsByTagName('label'));

        searchInput.addEventListener('input', function () {
            const filter = searchInput.value.trim().toLowerCase();

            labels.forEach(label => {
                const text = label.innerText.trim().toLowerCase();
                if (text.includes(filter)) {
                    label.style.display = '';  // Mostrar si coincide
                } else {
                    label.style.display = 'none';  // Ocultar si no coincide
                }
            });
        });
    }
});

// Validar que al menos un checkbox esté seleccionado en el formulario de filtrar
document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('filter_users_form');
    const modal = document.getElementById('customAlert');
    const closeAlertButton = document.getElementById('closeAlert');
    const alertMessage = document.getElementById('alertMessage');

    // Verificar si el formulario existe
    if (form) {
        form.addEventListener('submit', function (event) {
            // Detectar qué botón fue presionado
            const submitButton = event.submitter;
            
            // Solo validar checkboxes si se presiona el botón "Filtrar usuarios seleccionados"
            if (submitButton && submitButton.name === 'filter_users') {
                const checkboxes = document.querySelectorAll('#checkboxList_homework .user-checkbox-homework:checked');
                const fechaInput = document.getElementById('fecha_asignacion');

                // Validar que haya al menos un checkbox seleccionado
                if (checkboxes.length === 0) {
                    event.preventDefault(); // Evitar el envío del formulario

                    // Mostrar el modal de alerta si existe
                    if (modal && alertMessage) {
                        alertMessage.textContent = 'Por favor, selecciona al menos un usuario.';
                        modal.style.display = 'block';
                    }
                    return;
                }

                // Validar que se haya seleccionado una fecha
                if (!fechaInput.value) {
                    event.preventDefault();
                    
                    if (modal && alertMessage) {
                        alertMessage.textContent = 'Por favor, selecciona una fecha.';
                        modal.style.display = 'block';
                    }
                    return;
                }
            }
            
            // Si se presiona "Filtrar todos los usuarios", solo validar la fecha
            if (submitButton && submitButton.name === 'filter_all_users') {
                const fechaInput = document.getElementById('fecha_asignacion');

                // Validar que se haya seleccionado una fecha
                if (!fechaInput.value) {
                    event.preventDefault();
                    
                    if (modal && alertMessage) {
                        alertMessage.textContent = 'Por favor, selecciona una fecha.';
                        modal.style.display = 'block';
                    }
                    return;
                }
            }
        });

        // Cerrar el modal al hacer clic en el botón "Aceptar"
        if (closeAlertButton && modal) {
            closeAlertButton.addEventListener('click', function () {
                modal.style.display = 'none';
            });
        }

        // Cerrar el modal al hacer clic fuera de él
        window.addEventListener('click', function(event) {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
    }
});


// funcion para confirmar la eliminacion de las tareas de un usuario
document.addEventListener("DOMContentLoaded", function() {
    const modal = document.getElementById("confirmModal");
    const openModalBtn = document.getElementById("openConfirmModal");
    const closeModalBtn = document.getElementById("cancelDelete");
    const confirmBtn = document.getElementById("confirmDelete");
    const form = document.getElementById("assign_delete_activate_form");

    // Verificar que los elementos existen antes de añadir event listeners
    if (modal && openModalBtn && closeModalBtn && confirmBtn && form) {
        // Abrir el modal cuando el usuario haga clic en el botón
        openModalBtn.addEventListener("click", function() {
            modal.style.display = "block";
        });

        // Cerrar el modal si el usuario cancela
        closeModalBtn.addEventListener("click", function() {
            modal.style.display = "none";
        });

        // Si el usuario confirma, enviar el formulario manualmente
        confirmBtn.addEventListener("click", function() {
            // Crear un input oculto para enviar el nombre del botón (Django lo espera en request.POST)
            let hiddenInput = document.createElement("input");
            hiddenInput.type = "hidden";
            hiddenInput.name = "delete_task";  // Debe coincidir con lo que Django espera
            hiddenInput.value = "1"; // Un valor cualquiera

            form.appendChild(hiddenInput);
            form.submit();
        });

        // Cerrar el modal si el usuario hace clic fuera de él
        window.addEventListener("click", function(event) {
            if (event.target === modal) {
                modal.style.display = "none";
            }
        });
    }
});

/*
// funcion para que cambiar el type al botón de 'submit' a 'button' al enviar el conteo
document.addEventListener("DOMContentLoaded", function () {
    const updateButton = document.getElementById("update-tarea");
    const form = document.getElementById("form-tareas");
    const modal = document.getElementById("processingModal");

    // Verificar que los elementos existen antes de agregar eventos
    if (updateButton && form && modal) {
        updateButton.addEventListener("click", function () {
            // Crear un input oculto para enviar el nombre del botón (Django lo espera en request.POST)
            let hiddenInput = document.createElement("input");
            hiddenInput.type = "hidden";
            hiddenInput.name = "update_tarea";  // Debe coincidir con lo que Django espera
            hiddenInput.value = "1"; // Un valor cualquiera

            form.appendChild(hiddenInput);
            
            // Ocultar el botón de actualizar y mostrar el modal
            updateButton.style.display = "none"; // Ocultar el botón
            modal.style.display = "block"; // Mostrar el modal de procesamiento

            form.submit();  // Enviar el formulario manualmente
        });
    }
});
*/

// funcion para deshabilitar el botón de asignar tareas y mostrar un mensaje de procesamiento
document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("assign_delete_activate_form");
    const assignButton = document.getElementById("assignButton");
    const modal = document.getElementById("processingModal");

    // Verificar que los elementos existen antes de agregar eventos
    if (form && assignButton && modal) {
        form.addEventListener("submit", function (event) {
            if (event.submitter === assignButton) { // Solo si se presiona "Asignar Tareas"
                assignButton.style.display = "none"; // Oculta el botón
                modal.style.display = "block"; // Muestra el modal
            }
        });
    }
});

// Función para manejar el cambio de estado de verificado
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".verificado-check").forEach(function (checkbox) {
        checkbox.addEventListener("change", function () {
            const tareaId = this.dataset.id;
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute("content");

            fetch(toggleVerificadoURL, {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrfToken,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                body: new URLSearchParams({
                    "tarea_id": tareaId,
                }),
            })
            .then(response => response.json())
            .then(data => {
                if (data.status !== "ok") {
                    alert("Error al actualizar el estado");
                    checkbox.checked = !checkbox.checked;
                }
            })
            .catch(error => {
                alert("Error en la petición");
                checkbox.checked = !checkbox.checked;
            });
        });
    });
});

// Función para actualizar las tareas
document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("form-tareas");
  const btn  = document.getElementById("update-tarea");

  if (!form || !btn) return;

  btn.addEventListener("click", function (e) {
    e.preventDefault();

    const formData = new FormData(form);
    formData.append("update_tarea", "1");

    const csrfToken = form.querySelector('input[name="csrfmiddlewaretoken"]').value;

    document.getElementById("processingModal").style.display = "block";
    btn.disabled = true;

    fetch(window.location.href, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrfToken,
        "X-Requested-With": "XMLHttpRequest"
      },
      body: formData
    })
    .then(res => res.json())
    .then(data => { 
      if (data.status === "ok") {
        // Reemplazamos el contenido del <tbody>
        const body = document.getElementById("tareas-body")
        // inyecto nuevo HTML
        body.innerHTML = data.html;
        // Ocultamos modal y reactivamos botón
        document.getElementById("processingModal").style.display = "none";
        btn.disabled = false;
      } else {
        throw new Error("Error al actualizar");
      }
    })
    .catch(err => {
      console.error(err);
      alert("Hubo un problema, revisa la consola.");
      console.log(err);
      document.getElementById("processingModal").style.display = "none";
      btn.disabled = false;
    });
  });
});

// Seleccionar/Deseleccionar todos - Primera lista (Asignar tareas)
document.getElementById('selectAll').addEventListener('change', function() {
    const checkboxes = document.querySelectorAll('#checkboxList .user-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = this.checked;
    });
});

// Actualizar el estado del checkbox "Seleccionar todos" si se deselecciona alguno manualmente
document.querySelectorAll('#checkboxList .user-checkbox').forEach(checkbox => {
    checkbox.addEventListener('change', function() {
        const allCheckboxes = document.querySelectorAll('#checkboxList .user-checkbox');
        const allChecked = Array.from(allCheckboxes).every(cb => cb.checked);
        document.getElementById('selectAll').checked = allChecked;
    });
});

// Seleccionar/Deseleccionar todos - Segunda lista (Historial)
document.getElementById('selectAllHomework').addEventListener('change', function() {
    const checkboxes = document.querySelectorAll('#checkboxList_homework .user-checkbox-homework');
    checkboxes.forEach(checkbox => {
        checkbox.checked = this.checked;
    });
});

// Actualizar el estado del checkbox "Seleccionar todos" en historial
document.querySelectorAll('#checkboxList_homework .user-checkbox-homework').forEach(checkbox => {
    checkbox.addEventListener('change', function() {
        const allCheckboxes = document.querySelectorAll('#checkboxList_homework .user-checkbox-homework');
        const allChecked = Array.from(allCheckboxes).every(cb => cb.checked);
        document.getElementById('selectAllHomework').checked = allChecked;
    });
});