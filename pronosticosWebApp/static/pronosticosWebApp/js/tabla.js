/* tabla.js — tabla HTML nativa con paginación, orden y selección de fila
 * (reemplaza jQuery + DataTables en la página de pronósticos).
 *
 * Uso:
 *   const tabla = new TablaPronosticos('#datatable-productos', {
 *       columnasOcultas: [0, 1],
 *       alSeleccionar: (fila) => { ... },   // fila = arreglo de valores (o null)
 *   });
 *   tabla.cargar(filas);                     // filas = arreglo de arreglos
 *   tabla.filasVisibles();                   // filas en el orden actual
 */
(function (global) {
    'use strict';

    const OPCIONES_PAGINA = [10, 25, 50, -1];

    function compararValores(a, b) {
        const na = Number(a);
        const nb = Number(b);
        const sonNumeros = a !== '' && b !== '' && !Number.isNaN(na) && !Number.isNaN(nb);
        if (sonNumeros) return na - nb;
        return String(a).localeCompare(String(b), 'es', { numeric: true, sensitivity: 'base' });
    }

    class TablaPronosticos {
        constructor(selector, opciones = {}) {
            this.tabla = document.querySelector(selector);
            this.tbody = this.tabla.querySelector('tbody');
            this.encabezados = Array.from(this.tabla.querySelectorAll('thead th'));
            this.ocultas = new Set(opciones.columnasOcultas || []);
            this.alSeleccionar = opciones.alSeleccionar || (() => {});

            this.filas = [];
            this.orden = { columna: 0, asc: true };
            this.pagina = 0;
            this.porPagina = 10;
            this.seleccionada = null;   // índice dentro de this.filas

            this._prepararEncabezados();
            this._crearControles();
        }

        _prepararEncabezados() {
            this.encabezados.forEach((th, i) => {
                th.hidden = this.ocultas.has(i);
                th.classList.add('ordenable');
                th.setAttribute('aria-sort', 'none');
                th.addEventListener('click', () => {
                    if (this.orden.columna === i) {
                        this.orden.asc = !this.orden.asc;
                    } else {
                        this.orden = { columna: i, asc: true };
                    }
                    this._ordenar();
                    this.pagina = 0;
                    this.render();
                });
            });
        }

        _crearControles() {
            const contenedor = this.tabla.closest('.table-responsive') || this.tabla;

            // Barra superior: selector "Mostrar"
            this.barraSuperior = document.createElement('div');
            this.barraSuperior.className = 'tabla-barra';
            const etiqueta = document.createElement('label');
            etiqueta.className = 'tabla-mostrar';
            etiqueta.textContent = 'Mostrar ';
            this.selectPagina = document.createElement('select');
            this.selectPagina.title = 'Paginación';
            OPCIONES_PAGINA.forEach(n => {
                const opt = document.createElement('option');
                opt.value = n;
                opt.textContent = n === -1 ? 'Todos' : `${n} filas`;
                this.selectPagina.appendChild(opt);
            });
            this.selectPagina.addEventListener('change', () => {
                this.porPagina = Number(this.selectPagina.value);
                this.pagina = 0;
                this.render();
            });
            etiqueta.appendChild(this.selectPagina);
            this.barraSuperior.appendChild(etiqueta);
            contenedor.parentNode.insertBefore(this.barraSuperior, contenedor);

            // Barra inferior: información + paginador
            this.barraInferior = document.createElement('div');
            this.barraInferior.className = 'tabla-barra';
            this.info = document.createElement('div');
            this.info.className = 'tabla-info';
            this.paginador = document.createElement('nav');
            this.paginador.className = 'tabla-paginador';
            this.paginador.setAttribute('aria-label', 'Paginación de la tabla');
            this.barraInferior.append(this.info, this.paginador);
            contenedor.parentNode.insertBefore(this.barraInferior, contenedor.nextSibling);
        }

        cargar(filas) {
            this.filas = filas.map(f => f.map(v => (v === null || v === undefined) ? '' : String(v)));
            this.pagina = 0;
            this._deseleccionar(false);
            this._ordenar();
            this.render();
        }

        filasVisibles() {
            return this.filas.map(f => f.slice());
        }

        _ordenar() {
            const { columna, asc } = this.orden;
            const seleccion = this.seleccionada !== null ? this.filas[this.seleccionada] : null;
            this.filas.sort((a, b) => {
                const r = compararValores(a[columna], b[columna]);
                return asc ? r : -r;
            });
            this.seleccionada = seleccion ? this.filas.indexOf(seleccion) : null;

            this.encabezados.forEach((th, i) => {
                th.classList.remove('orden-asc', 'orden-desc');
                th.setAttribute('aria-sort', 'none');
                if (i === columna) {
                    th.classList.add(asc ? 'orden-asc' : 'orden-desc');
                    th.setAttribute('aria-sort', asc ? 'ascending' : 'descending');
                }
            });
        }

        _deseleccionar(notificar = true) {
            this.seleccionada = null;
            if (notificar) this.alSeleccionar(null);
        }

        _totalPaginas() {
            if (this.porPagina === -1) return 1;
            return Math.max(1, Math.ceil(this.filas.length / this.porPagina));
        }

        render() {
            const total = this.filas.length;
            const inicio = this.porPagina === -1 ? 0 : this.pagina * this.porPagina;
            const fin = this.porPagina === -1 ? total : Math.min(inicio + this.porPagina, total);
            const columnas = this.encabezados.length;

            const fragmento = document.createDocumentFragment();
            if (total === 0) {
                const tr = document.createElement('tr');
                const td = document.createElement('td');
                td.colSpan = columnas - this.ocultas.size;
                td.className = 'centered tabla-vacia';
                td.textContent = 'Ningún dato disponible en esta tabla';
                tr.appendChild(td);
                fragmento.appendChild(tr);
            }
            for (let i = inicio; i < fin; i++) {
                const fila = this.filas[i];
                const tr = document.createElement('tr');
                if (i === this.seleccionada) tr.classList.add('seleccionada');
                for (let c = 0; c < columnas; c++) {
                    if (this.ocultas.has(c)) continue;
                    const td = document.createElement('td');
                    td.className = 'centered';
                    td.textContent = fila[c] ?? '';
                    tr.appendChild(td);
                }
                tr.addEventListener('click', () => this._clicFila(i));
                fragmento.appendChild(tr);
            }
            this.tbody.replaceChildren(fragmento);

            this.info.textContent = total === 0
                ? 'Mostrando registros del 0 al 0 de un total de 0 registros'
                : `Mostrando ${inicio + 1} a ${fin} de ${total} registros`
                    + (this.seleccionada !== null ? ' · 1 fila seleccionada' : '');
            this._renderPaginador();
        }

        _clicFila(indice) {
            if (this.seleccionada === indice) {
                this._deseleccionar();
            } else {
                this.seleccionada = indice;
                this.alSeleccionar(this.filas[indice].slice());
            }
            this.render();
        }

        _renderPaginador() {
            const totalPaginas = this._totalPaginas();
            this.paginador.replaceChildren();
            if (totalPaginas <= 1) return;

            const boton = (texto, pagina, { activo = false, deshabilitado = false } = {}) => {
                const b = document.createElement('button');
                b.type = 'button';
                b.textContent = texto;
                b.disabled = deshabilitado;
                if (activo) {
                    b.classList.add('activo');
                    b.setAttribute('aria-current', 'page');
                }
                b.addEventListener('click', () => {
                    this.pagina = pagina;
                    this.render();
                });
                this.paginador.appendChild(b);
            };
            const puntos = () => {
                const s = document.createElement('span');
                s.textContent = '…';
                this.paginador.appendChild(s);
            };

            const actual = this.pagina;
            boton('‹', actual - 1, { deshabilitado: actual === 0 });

            const paginas = new Set([0, totalPaginas - 1, actual - 1, actual, actual + 1]);
            let anterior = -1;
            Array.from(paginas)
                .filter(p => p >= 0 && p < totalPaginas)
                .sort((a, b) => a - b)
                .forEach(p => {
                    if (p - anterior > 1) puntos();
                    boton(String(p + 1), p, { activo: p === actual });
                    anterior = p;
                });

            boton('›', actual + 1, { deshabilitado: actual >= totalPaginas - 1 });
        }
    }

    global.TablaPronosticos = TablaPronosticos;
})(window);
