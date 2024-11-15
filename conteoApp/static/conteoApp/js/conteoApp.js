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
