// Función para ordenar la tabla
function sortTable(columnIndex) {
    const table = document.getElementById("myTable");
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

//funcion para buscar usuarios en el formnulario de asignar, eliminar 
document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('searchInput');
    const checkboxList = document.getElementById('checkboxList');
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

// Validar que al menos un checkbox esté seleccionado en el formulario de filtrar
document.getElementById('filter_users_form').addEventListener('submit', function (event) {
    const checkboxes = document.querySelectorAll('input[name="usuarios"]:checked');
    
    // Validar que haya al menos un checkbox seleccionado
    if (checkboxes.length === 0) {
        event.preventDefault();  // Evitar el envío del formulario

        // Mostrar el modal de alerta
        const modal = document.getElementById('customAlert');
        modal.style.display = 'block';

        // Cerrar el modal al hacer clic en el botón "Aceptar"
        document.getElementById('closeAlert').addEventListener('click', function () {
            modal.style.display = 'none';
        });
    }
});