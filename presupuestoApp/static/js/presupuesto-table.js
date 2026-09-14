/**
 * presupuesto-table.js
 * ---------------------------------------------------------------------
 * Componente de tabla ligero en JavaScript puro (sin jQuery ni DataTables)
 * pensado para reemplazar el patrón repetido en todas las vistas de
 * "presupuesto_comercial" (pivotar por mes, filtros tipo Excel, orden,
 * edición inline, exportar a Excel).
 *
 * La edición de celdas y los filtros de columna están diseñados para
 * comportarse como en Excel:
 *   - Clic para seleccionar una celda (funciona en cualquier celda,
 *     editable o no, para poder navegar con el teclado).
 *   - Flechas ↑↓←→ mueven la selección entre celdas.
 *   - Tab / Shift+Tab mueven la selección a la derecha/izquierda,
 *     saltando de fila cuando llegan al borde.
 *   - Escribir directamente sobre una celda editable seleccionada
 *     empieza a editarla reemplazando su contenido (igual que Excel).
 *   - F2 o doble clic edita la celda conservando su valor actual.
 *   - Enter confirma y mueve la selección una fila hacia abajo.
 *   - Escape cancela la edición y restaura el valor anterior.
 *   - Suprimir/Retroceso borra el contenido de la celda seleccionada.
 *   - El filtro de columna es un desplegable con "(Seleccionar todo)",
 *     buscador y botones Aceptar/Cancelar: los cambios sólo se aplican al
 *     pulsar "Aceptar" (o Enter en el buscador), igual que el AutoFiltro
 *     de Excel.
 *
 * Un solo archivo reemplaza ~150-250 líneas de JS casi idénticas que
 * existían en cada plantilla .html del módulo.
 * ---------------------------------------------------------------------
 */
(function (global) {
    'use strict';

    const MESES_NUM_A_NOMBRE = { 1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic' };
    const MESES_NOMBRE_A_NUM = { Ene: 1, Feb: 2, Mar: 3, Abr: 4, May: 5, Jun: 6, Jul: 7, Ago: 8, Sep: 9, Oct: 10, Nov: 11, Dic: 12 };
    const NOMBRES_MESES = Object.keys(MESES_NOMBRE_A_NUM);

    const fmtNumero = new Intl.NumberFormat('es-ES');
    const fmtPorcentaje = new Intl.NumberFormat('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const fmtMoneda = new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0 });

    function esNumerico(v) {
        return v !== null && v !== undefined && v !== '' && !isNaN(v);
    }

    function aNumero(v) {
        if (v === null || v === undefined || v === '') return null;
        if (typeof v === 'number') return isNaN(v) ? null : v;
        const limpio = String(v).replace(/[^0-9.\-]/g, '');
        if (limpio === '' || limpio === '-') return null;
        const n = parseFloat(limpio);
        return isNaN(n) ? null : n;
    }

    function formatearValor(valor, tipo) {
        if (valor === null || valor === undefined || valor === '') return '';
        switch (tipo) {
            case 'number': return esNumerico(valor) ? fmtNumero.format(valor) : String(valor);
            case 'money': return esNumerico(valor) ? fmtMoneda.format(valor) : String(valor);
            case 'percent': return esNumerico(valor) ? fmtPorcentaje.format(valor) + ' %' : String(valor);
            default: return String(valor);
        }
    }

    // ---------------------------------------------------------------
    // Un único listener global (evita el bug de "fugas" de handlers
    // que se acumulaban cada vez que se recargaba una tabla DataTables).
    // Los menús de filtro se crean de nuevo cada vez que se abren (para
    // reflejar siempre los datos/filtros vigentes) y se eliminan del DOM
    // al cerrarse; los de visibilidad de columnas se reutilizan.
    // ---------------------------------------------------------------
    document.addEventListener('click', function (e) {
        document.querySelectorAll('.pt-filter-menu.open').forEach(function (menu) {
            if (menu.contains(e.target)) return;
            if (menu.__triggerBtn && menu.__triggerBtn.contains(e.target)) return;
            menu.classList.remove('open');
            if (menu.__triggerBtn) menu.__triggerBtn.__open = false;
            if (menu.parentNode) menu.parentNode.removeChild(menu);
        });
        document.querySelectorAll('.pt-colvis-menu.open').forEach(function (menu) {
            if (menu.contains(e.target)) return;
            if (menu.__triggerBtn && menu.__triggerBtn.contains(e.target)) return;
            menu.classList.remove('open');
        });
    });

    class PresupuestoTable {
        /**
         * @param {Object} cfg
         * @param {string|HTMLElement} cfg.container - id o elemento contenedor
         * @param {Array}  cfg.columns - [{key,label,type,filterable,sortable,editable,visible}]
         * @param {Function} [cfg.pivot] - (rawData) => rows
         * @param {Function} [cfg.onEdit] - (row, key, nuevoValor) => void  (muta la fila; recalcula columnas dependientes)
         * @param {Function} [cfg.onChange] - (row, key, nuevoValor) => void  (se dispara sólo cuando el valor realmente cambió; pensado para autoguardado)
         * @param {string} [cfg.emptyMessage]
         * @param {string} [cfg.exportFileName]
         */
        constructor(cfg) {
            this.cfg = Object.assign({
                columns: [],
                pivot: null,
                onEdit: null,
                onChange: null,
                emptyMessage: 'Sin datos para mostrar',
                exportFileName: 'presupuesto',
            }, cfg);

            this.container = typeof cfg.container === 'string' ? document.getElementById(cfg.container) : cfg.container;
            this.rawData = [];
            this.rows = [];
            this.filters = {};                 // key -> Set(valoresPermitidos)
            this.sortState = { key: null, dir: 1 };
            this.selectedCell = null;          // { row, col } - celda seleccionada actualmente
            this._filasActuales = [];
            this._colsActuales = [];
            this.visibleCols = new Set(
                this.cfg.columns.filter(c => c.visible !== false).map(c => c.key)
            );

            this._buildSkeleton();
        }

        // ------------------------------------------------------------------
        // Construcción del DOM base
        // ------------------------------------------------------------------
        _buildSkeleton() {
            this.container.classList.add('pt-wrapper');
            this.container.innerHTML = '';
            this.table = document.createElement('table');
            this.table.className = 'pt-table';
            this.thead = document.createElement('thead');
            this.tbody = document.createElement('tbody');
            this.table.appendChild(this.thead);
            this.table.appendChild(this.tbody);
            this.container.appendChild(this.table);
            this._renderHead();
            this._renderBody();
        }

        // ------------------------------------------------------------------
        // Datos
        // ------------------------------------------------------------------
        setData(raw) {
            if (!this.container.contains(this.table)) {
                this._buildSkeleton();
            }
            this.rawData = raw || [];
            this.rows = this.cfg.pivot ? this.cfg.pivot(this.rawData) : this.rawData.slice();
            this.filters = {};
            this.selectedCell = null;
            this._renderHead();
            this._renderBody();
        }

        getRows() {
            return this.rows;
        }

        // Columnas visibles, en orden de definición
        _cols() {
            return this.cfg.columns.filter(c => this.visibleCols.has(c.key));
        }

        // ------------------------------------------------------------------
        // Cabecera (orden + filtros + visibilidad de columnas)
        // ------------------------------------------------------------------
        _renderHead() {
            this.thead.innerHTML = '';
            const tr = document.createElement('tr');
            this._cols().forEach(col => {
                const th = document.createElement('th');
                const inner = document.createElement('span');
                inner.className = 'pt-th-inner';

                const label = document.createElement('span');
                label.textContent = col.label;
                inner.appendChild(label);

                if (col.sortable !== false) {
                    const icon = document.createElement('span');
                    icon.className = 'pt-sort-icon';
                    icon.textContent = this.sortState.key === col.key ? (this.sortState.dir === 1 ? '▲' : '▼') : '⇅';
                    inner.appendChild(icon);
                    th.style.cursor = 'pointer';
                    th.addEventListener('click', (e) => {
                        if (e.target.closest('.pt-filter-btn')) return;
                        this._toggleSort(col.key);
                    });
                }

                if (col.filterable) {
                    const btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = 'pt-filter-btn' + (this.filters[col.key] ? ' active' : '');
                    btn.textContent = '▾';
                    btn.title = 'Filtrar ' + col.label;
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        this._toggleFilterMenu(col, btn);
                    });
                    inner.appendChild(btn);
                }

                th.appendChild(inner);
                tr.appendChild(th);
            });
            this.thead.appendChild(tr);
        }

        _toggleSort(key) {
            if (this.sortState.key === key) {
                this.sortState.dir *= -1;
            } else {
                this.sortState = { key, dir: 1 };
            }
            this._renderHead();
            this._renderBody();
        }

        // ------------------------------------------------------------------
        // Filtro tipo "Excel" por columna: Quitar filtro, buscador,
        // (Seleccionar todo) + lista de valores, y Aceptar/Cancelar.
        // El menú se reconstruye cada vez que se abre (para reflejar datos y
        // filtros vigentes) y se destruye al cerrarse.
        // ------------------------------------------------------------------
        _toggleFilterMenu(col, btn) {
            // Cerrar cualquier otro menú de filtro abierto.
            document.querySelectorAll('.pt-filter-menu.open').forEach(m => {
                m.classList.remove('open');
                if (m.__triggerBtn) m.__triggerBtn.__open = false;
                if (m.parentNode) m.parentNode.removeChild(m);
            });

            if (btn.__open) {
                btn.__open = false;
                return;
            }

            const menu = this._buildFilterMenu(col, btn);
            menu.__triggerBtn = btn;
            document.body.appendChild(menu);
            btn.__open = true;

            const rect = btn.getBoundingClientRect();
            menu.style.top = (rect.bottom + window.scrollY) + 'px';
            menu.style.left = (rect.left + window.scrollX - 150) + 'px';
            menu.classList.add('open');
        }

        _buildFilterMenu(col, btn) {
            const menu = document.createElement('div');
            menu.className = 'pt-filter-menu';

            const cerrar = () => {
                menu.classList.remove('open');
                btn.__open = false;
                if (menu.parentNode) menu.parentNode.removeChild(menu);
            };

            // --- Quitar filtro (sólo si esta columna tiene uno activo) ---
            if (this.filters[col.key]) {
                const btnClear = document.createElement('button');
                btnClear.type = 'button';
                btnClear.className = 'pt-filter-clear';
                btnClear.textContent = '✕ Quitar filtro de "' + col.label + '"';
                btnClear.addEventListener('click', () => {
                    delete this.filters[col.key];
                    this._renderHead();
                    this._renderBody();
                    cerrar();
                });
                menu.appendChild(btnClear);
                menu.appendChild(document.createElement('hr')).className = 'pt-filter-sep';
            }

            // --- Buscador ---
            const search = document.createElement('input');
            search.type = 'text';
            search.placeholder = 'Buscar...';
            menu.appendChild(search);

            // --- (Seleccionar todo) + lista de valores ---
            const selectAllLabel = document.createElement('label');
            selectAllLabel.className = 'pt-filter-selectall';
            const chkAll = document.createElement('input');
            chkAll.type = 'checkbox';
            selectAllLabel.appendChild(chkAll);
            selectAllLabel.appendChild(document.createTextNode(' (Seleccionar todo)'));
            menu.appendChild(selectAllLabel);

            const list = document.createElement('div');
            list.className = 'pt-filter-list';
            menu.appendChild(list);

            const valores = Array.from(new Set(this.rows.map(r => (r[col.key] === null || r[col.key] === undefined) ? '' : String(r[col.key]))))
                .filter(v => v !== '')
                .sort((a, b) => a.localeCompare(b, 'es', { numeric: true }));

            const seleccionPrevia = this.filters[col.key];
            // Estado "pendiente": las casillas no se aplican hasta pulsar Aceptar.
            const pendiente = new Set(seleccionPrevia ? Array.from(seleccionPrevia) : valores);
            const checks = [];

            // El "Seleccionar todo" sólo tiene en cuenta lo que está visible
            // en ese momento (si hay una búsqueda activa, sólo lo que coincide).
            const actualizarSelectAll = () => {
                const visibles = checks.filter(c => c.parentElement.style.display !== 'none');
                const marcados = visibles.filter(c => c.checked).length;
                chkAll.checked = visibles.length > 0 && marcados === visibles.length;
                chkAll.indeterminate = marcados > 0 && marcados < visibles.length;
            };

            valores.forEach(val => {
                const label = document.createElement('label');
                const chk = document.createElement('input');
                chk.type = 'checkbox';
                chk.value = val;
                chk.checked = pendiente.has(val);
                chk.addEventListener('change', () => {
                    if (chk.checked) pendiente.add(val); else pendiente.delete(val);
                    actualizarSelectAll();
                });
                checks.push(chk);
                label.appendChild(chk);
                label.appendChild(document.createTextNode(' ' + val));
                list.appendChild(label);
            });
            actualizarSelectAll();

            chkAll.addEventListener('change', () => {
                checks.forEach(c => {
                    if (c.parentElement.style.display === 'none') return; // respeta lo filtrado por el buscador
                    c.checked = chkAll.checked;
                    if (c.checked) pendiente.add(c.value); else pendiente.delete(c.value);
                });
                chkAll.indeterminate = false;
            });

            // Al escribir en el buscador se filtra la lista y, además, se
            // selecciona automáticamente sólo lo que coincide (igual que el
            // buscador del AutoFiltro de Excel). Antes sólo ocultaba filas de
            // la lista pero no tocaba las casillas, así que al pulsar
            // Aceptar seguían marcados TODOS los valores originales y no se
            // aplicaba ningún filtro.
            const aplicarBusqueda = () => {
                const term = search.value.trim().toLowerCase();
                checks.forEach(chk => {
                    const label = chk.parentElement;
                    const coincide = term === '' || chk.value.toLowerCase().includes(term);
                    label.style.display = coincide ? '' : 'none';
                    chk.checked = coincide;
                    if (coincide) pendiente.add(chk.value); else pendiente.delete(chk.value);
                });
                actualizarSelectAll();
            };
            search.addEventListener('input', aplicarBusqueda);

            // --- Aceptar / Cancelar ---
            const actions = document.createElement('div');
            actions.className = 'pt-filter-actions';
            const btnOk = document.createElement('button');
            btnOk.type = 'button';
            btnOk.className = 'pt-filter-ok';
            btnOk.textContent = 'Aceptar';
            const aplicarYcerrar = () => {
                if (pendiente.size === valores.length) delete this.filters[col.key];
                else this.filters[col.key] = new Set(pendiente);
                this._renderHead();
                this._renderBody();
                cerrar();
            };
            btnOk.addEventListener('click', aplicarYcerrar);
            const btnCancel = document.createElement('button');
            btnCancel.type = 'button';
            btnCancel.textContent = 'Cancelar';
            btnCancel.addEventListener('click', cerrar);
            actions.appendChild(btnOk);
            actions.appendChild(btnCancel);
            menu.appendChild(actions);

            // Enter en el buscador aplica y cierra directamente, igual que
            // en el AutoFiltro de Excel.
            search.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') { e.preventDefault(); aplicarYcerrar(); }
            });

            return menu;
        }

        // ------------------------------------------------------------------
        // Filtrado + orden aplicados sobre this.rows
        // ------------------------------------------------------------------
        _procesarFilas() {
            let filas = this.rows.filter(row => {
                return Object.keys(this.filters).every(key => {
                    const set = this.filters[key];
                    const val = (row[key] === null || row[key] === undefined) ? '' : String(row[key]);
                    return set.has(val);
                });
            });

            if (this.sortState.key) {
                const key = this.sortState.key, dir = this.sortState.dir;
                filas = filas.slice().sort((a, b) => {
                    const na = aNumero(a[key]), nb = aNumero(b[key]);
                    let cmp;
                    if (na !== null && nb !== null) cmp = na - nb;
                    else cmp = String(a[key] ?? '').localeCompare(String(b[key] ?? ''), 'es', { numeric: true });
                    return cmp * dir;
                });
            }
            return filas;
        }

        // ------------------------------------------------------------------
        // Cuerpo de la tabla
        // ------------------------------------------------------------------
        _renderBody() {
            this.tbody.innerHTML = '';
            const filas = this._procesarFilas();
            const cols = this._cols();
            this._filasActuales = filas;
            this._colsActuales = cols;

            if (!filas.length) {
                const tr = document.createElement('tr');
                const td = document.createElement('td');
                td.colSpan = cols.length || 1;
                td.className = 'pt-empty';
                td.textContent = this.cfg.emptyMessage;
                tr.appendChild(td);
                this.tbody.appendChild(tr);
                return;
            }

            let celdaAEnfocar = null;

            filas.forEach(row => {
                const tr = document.createElement('tr');
                cols.forEach(col => {
                    const td = document.createElement('td');
                    const tipo = col.type || 'text';
                    if (tipo === 'number' || tipo === 'money' || tipo === 'percent') td.classList.add('num');
                    td.textContent = formatearValor(row[col.key], tipo);
                    td.tabIndex = -1;

                    const esEditable = typeof col.editable === 'function' ? col.editable(row) : !!col.editable;
                    if (esEditable) {
                        td.classList.add('editable');
                        td.title = 'Doble clic, F2 o escribir para editar · flechas para navegar';
                    } else {
                        td.title = 'Flechas para navegar';
                    }

                    if (this.selectedCell && this.selectedCell.row === row && this.selectedCell.col === col) {
                        td.classList.add('pt-cell-selected');
                        celdaAEnfocar = td;
                    }

                    td.addEventListener('click', (e) => {
                        if (e.target.tagName === 'INPUT') return;
                        this._seleccionarCelda(row, col);
                    });
                    if (esEditable) {
                        td.addEventListener('dblclick', () => this._editarCelda(td, row, col));
                    }
                    td.addEventListener('keydown', (e) => this._onCeldaKeydown(e, row, col, esEditable));

                    tr.appendChild(td);
                });
                this.tbody.appendChild(tr);
            });

            if (celdaAEnfocar) {
                celdaAEnfocar.focus({ preventScroll: false });
                // Refuerzo: si por cualquier motivo el navegador no deja el foco
                // en la celda de inmediato, se reintenta en el siguiente frame.
                // OJO: se comprueba "contains", no igualdad estricta, porque para
                // entonces la celda puede ya tener dentro un <input> de edición
                // (p. ej. abierto por un doble clic justo después de este clic);
                // si comparáramos con "!==" le robaríamos el foco al input recién
                // abierto y la edición se cerraría solo al instante.
                requestAnimationFrame(() => {
                    if (document.body.contains(celdaAEnfocar) && !celdaAEnfocar.contains(document.activeElement)) {
                        celdaAEnfocar.focus({ preventScroll: true });
                    }
                });
            }
        }

        // ------------------------------------------------------------------
        // Selección y navegación de celdas (estilo Excel)
        // ------------------------------------------------------------------
        // Importante: seleccionar/navegar NO reconstruye toda la tabla (sólo
        // mueve la clase visual "pt-cell-selected" y el foco). Si el clic de
        // selección reconstruyera el <td> en cada clic, un doble clic
        // terminaría apuntando a una celda "fantasma" ya desconectada del
        // documento (el 2º clic la destruía antes de que llegara el evento
        // "dblclick"), y la edición no se abría. La reconstrucción completa
        // sólo ocurre cuando algo realmente cambia de valor (confirmar una
        // edición, borrar con Suprimir, filtrar, ordenar, etc.).
        _seleccionarCelda(row, col) {
            this.selectedCell = { row, col };
            this._actualizarSeleccionVisual();
        }

        // Aplica la clase "seleccionada" + el foco sobre el <td> vigente que
        // corresponde a this.selectedCell, sin tocar el resto del DOM.
        _actualizarSeleccionVisual() {
            this.tbody.querySelectorAll('td.pt-cell-selected').forEach(td => td.classList.remove('pt-cell-selected'));
            if (!this.selectedCell) return;
            const filas = this._filasActuales, cols = this._colsActuales;
            const ri = filas.indexOf(this.selectedCell.row);
            const ci = cols.indexOf(this.selectedCell.col);
            if (ri === -1 || ci === -1) return;
            const tr = this.tbody.children[ri];
            if (!tr) return;
            const td = tr.children[ci];
            if (!td) return;
            td.classList.add('pt-cell-selected');
            td.focus({ preventScroll: false });
            // Mismo cuidado que en _renderBody: usar "contains" y no "!==",
            // para no robarle el foco a un <input> de edición que se haya
            // abierto dentro de esta celda entre este clic y el siguiente
            // frame (el caso típico: el 2º clic de un doble clic).
            requestAnimationFrame(() => {
                if (document.body.contains(td) && !td.contains(document.activeElement)) {
                    td.focus({ preventScroll: true });
                }
            });
        }

        // Calcula (sin mutar nada) la celda destino al mover dRow filas /
        // dCol columnas, sin salir de los límites de la tabla (igual que
        // Excel, que no da la vuelta al llegar al borde).
        _calcularMovimiento(dRow, dCol) {
            if (!this.selectedCell) return null;
            const filas = this._filasActuales, cols = this._colsActuales;
            const ri = filas.indexOf(this.selectedCell.row);
            const ci = cols.indexOf(this.selectedCell.col);
            if (ri === -1 || ci === -1) return null;
            const nRi = Math.min(Math.max(ri + dRow, 0), filas.length - 1);
            const nCi = Math.min(Math.max(ci + dCol, 0), cols.length - 1);
            return { row: filas[nRi], col: cols[nCi] };
        }

        // Igual que arriba, pero para Tab/Shift+Tab: avanza/retrocede
        // saltando de fila al llegar al borde.
        _calcularTab(dir) {
            if (!this.selectedCell) return null;
            const filas = this._filasActuales, cols = this._colsActuales;
            let ri = filas.indexOf(this.selectedCell.row);
            let ci = cols.indexOf(this.selectedCell.col);
            if (ri === -1 || ci === -1) return null;
            ci += dir;
            if (ci >= cols.length) {
                ci = 0;
                ri = Math.min(ri + 1, filas.length - 1);
            } else if (ci < 0) {
                ci = cols.length - 1;
                ri = Math.max(ri - 1, 0);
            }
            return { row: filas[ri], col: cols[ci] };
        }

        // Navegación "pura" con flechas/Tab (sin edición de por medio): sólo
        // mueve la selección visualmente, sin reconstruir la tabla.
        _moverSeleccion(dRow, dCol) {
            const destino = this._calcularMovimiento(dRow, dCol);
            if (!destino) return;
            this.selectedCell = destino;
            this._actualizarSeleccionVisual();
        }

        _tab(dir) {
            const destino = this._calcularTab(dir);
            if (!destino) return;
            this.selectedCell = destino;
            this._actualizarSeleccionVisual();
        }

        // Usado tras confirmar una edición: al haber cambiado un valor (y
        // posiblemente columnas dependientes vía onEdit), aquí SÍ hace falta
        // reconstruir la tabla para reflejarlo, moviendo la selección al
        // mismo tiempo.
        _moverYRenderizar(destino) {
            if (destino) this.selectedCell = destino;
            this._renderBody();
        }

        _onCeldaKeydown(e, row, col, esEditable) {
            if (e.target.tagName === 'INPUT') return; // el <input> de edición maneja sus propias teclas
            const key = e.key;

            if (key === 'ArrowDown') { e.preventDefault(); this._moverSeleccion(1, 0); return; }
            if (key === 'ArrowUp') { e.preventDefault(); this._moverSeleccion(-1, 0); return; }
            if (key === 'ArrowLeft') { e.preventDefault(); this._moverSeleccion(0, -1); return; }
            if (key === 'ArrowRight') { e.preventDefault(); this._moverSeleccion(0, 1); return; }
            if (key === 'Tab') { e.preventDefault(); this._tab(e.shiftKey ? -1 : 1); return; }
            if (key === 'Enter') { e.preventDefault(); this._moverSeleccion(1, 0); return; }
            if (key === 'F2') {
                if (esEditable) { e.preventDefault(); this._editarCelda(e.currentTarget, row, col); }
                return;
            }
            if ((key === 'Delete' || key === 'Backspace') && esEditable) {
                e.preventDefault();
                const vacio = col.type === 'text' ? '' : 0;
                if (row[col.key] !== vacio) {
                    row[col.key] = vacio;
                    if (typeof this.cfg.onEdit === 'function') this.cfg.onEdit(row, col.key, vacio);
                    row.__editado = true;
                    if (typeof this.cfg.onChange === 'function') this.cfg.onChange(row, col.key, vacio);
                }
                this._renderBody();
                return;
            }
            // Escribir directamente sobre una celda editable seleccionada empieza a
            // editarla reemplazando su contenido (igual que Excel).
            if (esEditable && key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
                e.preventDefault();
                this._editarCelda(e.currentTarget, row, col, key);
            }
        }

        // ------------------------------------------------------------------
        // Edición inline de una celda
        // ------------------------------------------------------------------
        // initialChar: si viene definido, la edición empieza reemplazando el
        // valor anterior con ese carácter (el usuario empezó a escribir sobre
        // la celda). Si no viene, se conserva el valor anterior con el cursor
        // al final (doble clic o F2), igual que en Excel.
        _editarCelda(td, row, col, initialChar) {
            if (!td || td.querySelector('input')) return;
            this.selectedCell = { row, col };

            const valorAnterior = row[col.key];
            td.innerHTML = '';
            td.classList.add('pt-cell-selected');
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'pt-cell-input';
            input.value = initialChar !== undefined
                ? initialChar
                : (valorAnterior === null || valorAnterior === undefined ? '' : valorAnterior);
            td.appendChild(input);
            input.focus();
            const len = input.value.length;
            input.setSelectionRange(len, len);

            let confirmado = false;

            const commit = () => {
                if (confirmado) return;
                confirmado = true;
                const nuevoValor = col.type === 'text' ? input.value : (parseFloat(input.value.replace(',', '.')) || 0);
                const cambio = nuevoValor !== valorAnterior;
                row[col.key] = nuevoValor;
                if (typeof this.cfg.onEdit === 'function') this.cfg.onEdit(row, col.key, nuevoValor);
                if (cambio) {
                    row.__editado = true;
                    if (typeof this.cfg.onChange === 'function') this.cfg.onChange(row, col.key, nuevoValor);
                }
            };

            const cancelar = () => { confirmado = true; };

            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') { e.preventDefault(); commit(); this._moverYRenderizar(this._calcularMovimiento(1, 0)); }
                else if (e.key === 'Escape') { e.preventDefault(); cancelar(); this._renderBody(); }
                else if (e.key === 'Tab') { e.preventDefault(); commit(); this._moverYRenderizar(this._calcularTab(e.shiftKey ? -1 : 1)); }
                else if (e.key === 'ArrowDown') { e.preventDefault(); commit(); this._moverYRenderizar(this._calcularMovimiento(1, 0)); }
                else if (e.key === 'ArrowUp') { e.preventDefault(); commit(); this._moverYRenderizar(this._calcularMovimiento(-1, 0)); }
                // ArrowLeft / ArrowRight: comportamiento nativo del input (mover el cursor de texto).
            });
            input.addEventListener('blur', () => { commit(); this._renderBody(); });
        }

        // ------------------------------------------------------------------
        // Visibilidad de columnas (reemplaza el botón "colvis" de DataTables)
        // ------------------------------------------------------------------
        toggleColumnVisibilityMenu(btn) {
            if (btn.__menu && btn.__menu.classList.contains('open')) {
                btn.__menu.classList.remove('open');
                return;
            }
            if (!btn.__menu) {
                const menu = document.createElement('div');
                menu.className = 'pt-filter-menu pt-colvis-menu';
                this.cfg.columns.forEach(col => {
                    const label = document.createElement('label');
                    const chk = document.createElement('input');
                    chk.type = 'checkbox';
                    chk.checked = this.visibleCols.has(col.key);
                    chk.addEventListener('change', () => {
                        if (chk.checked) this.visibleCols.add(col.key);
                        else this.visibleCols.delete(col.key);
                        this._renderHead();
                        this._renderBody();
                    });
                    label.appendChild(chk);
                    label.appendChild(document.createTextNode(' ' + col.label));
                    menu.appendChild(label);
                });
                menu.__triggerBtn = btn;
                document.body.appendChild(menu);
                btn.__menu = menu;
            }
            const rect = btn.getBoundingClientRect();
            btn.__menu.style.top = (rect.bottom + window.scrollY) + 'px';
            btn.__menu.style.left = (rect.left + window.scrollX) + 'px';
            btn.__menu.classList.add('open');
        }

        // ------------------------------------------------------------------
        // Exportar a Excel (tabla HTML -> .xls, sin dependencias externas)
        // ------------------------------------------------------------------
        exportToExcel(filename) {
            const cols = this._cols();
            const filas = this._procesarFilas();
            let html = '<table><thead><tr>';
            cols.forEach(c => { html += '<th>' + c.label + '</th>'; });
            html += '</tr></thead><tbody>';
            filas.forEach(row => {
                html += '<tr>';
                cols.forEach(c => {
                    let val = row[c.key];
                    if (val === null || val === undefined) val = '';
                    html += '<td>' + String(val).replace(/</g, '&lt;') + '</td>';
                });
                html += '</tr>';
            });
            html += '</tbody></table>';

            const plantilla = '<html xmlns:o="urn:schemas-microsoft-com:office:office" ' +
                'xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">' +
                '<head><meta charset="UTF-8"></head><body>' + html + '</body></html>';

            const blob = new Blob(['\ufeff' + plantilla], { type: 'application/vnd.ms-excel' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = (filename || this.cfg.exportFileName) + '.xls';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(link.href);
        }
    }

    // =====================================================================
    // Utilidades compartidas: pivotar/despivotar por mes, ajax y spinners.
    // Sustituyen las funciones "pivotData/unpivotData/numberFormat" que
    // estaban duplicadas (casi idénticas) en cada plantilla.
    // =====================================================================
    const PresupuestoUtils = {

        columnasMeses(opts) {
            opts = opts || {};
            return NOMBRES_MESES.map(m => ({
                key: m, label: m, type: 'number', editable: opts.editable || false,
                editableIf: opts.editableIf, sortable: false, filterable: false,
            }));
        },

        /**
         * Convierte filas planas {year, mes, total, ...} en filas pivotadas
         * por mes: {year, Ene, Feb, ..., Dic, ...extras}
         */
        pivotByMonth(data, groupFields, extraFields) {
            extraFields = extraFields || [];
            const pivot = {};
            (data || []).forEach(row => {
                const key = groupFields.map(f => row[f]).join('|');
                if (!pivot[key]) {
                    const base = {};
                    groupFields.forEach(f => { base[f] = row[f]; });
                    extraFields.forEach(f => { base[f] = row[f] !== undefined && row[f] !== null ? row[f] : 0; });
                    NOMBRES_MESES.forEach(m => { base[m] = 0; });
                    pivot[key] = base;
                }
                const nombreMes = MESES_NUM_A_NOMBRE[parseInt(row.mes, 10)];
                if (nombreMes) pivot[key][nombreMes] = row.total;
            });
            return Object.values(pivot);
        },

        /**
         * Operación inversa: de filas pivotadas por mes a filas planas
         * listas para enviar al backend en el "guardar cambios".
         */
        unpivotByMonth(rows, groupFields) {
            const resultado = [];
            (rows || []).forEach(row => {
                NOMBRES_MESES.forEach(m => {
                    if (row[m] === undefined) return;
                    const rec = { mes: MESES_NOMBRE_A_NUM[m], total: parseInt(row[m], 10) || 0 };
                    groupFields.forEach(f => { rec[f] = row[f]; });
                    resultado.push(rec);
                });
            });
            return resultado;
        },

        formatearValor,
        aNumero,

        /**
         * Convierte una <table> estática (renderizada por Django con
         * {% for %}) en una tabla ordenable por clic de cabecera, sin
         * reescribir su HTML ni depender de DataTables. Pensado para
         * reemplazar los ~6 bloques casi idénticos de inicialización de
         * DataTables que había en presupuesto_comercial.html.
         */
        makeSortableStaticTable(table, opciones) {
            if (!table) return;
            opciones = opciones || {};
            const numericCols = new Set(opciones.numericCols || []);
            table.classList.add('pt-table');
            const wrapper = document.createElement('div');
            wrapper.className = 'pt-wrapper';
            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);

            const thead = table.tHead;
            if (!thead) return;
            const ths = Array.from(thead.rows[0].cells);
            const tbody = table.tBodies[0];
            let sortState = { index: null, dir: 1 };

            ths.forEach((th, index) => {
                th.style.cursor = 'pointer';
                th.title = 'Clic para ordenar';
                th.addEventListener('click', () => {
                    sortState = sortState.index === index ? { index, dir: sortState.dir * -1 } : { index, dir: 1 };
                    const filas = Array.from(tbody.rows);
                    const esNumerica = numericCols.has(index);
                    filas.sort((a, b) => {
                        const ta = a.cells[index] ? a.cells[index].textContent.trim() : '';
                        const tb = b.cells[index] ? b.cells[index].textContent.trim() : '';
                        if (esNumerica) {
                            const na = aNumero(ta) || 0, nb = aNumero(tb) || 0;
                            return (na - nb) * sortState.dir;
                        }
                        return ta.localeCompare(tb, 'es', { numeric: true }) * sortState.dir;
                    });
                    filas.forEach(f => tbody.appendChild(f));
                });
            });
        },

        async getJSON(url) {
            const res = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
            if (!res.ok) throw new Error('Error HTTP ' + res.status);
            const data = await res.json();
            return Array.isArray(data) ? data : (data.data || data);
        },

        async postJSON(url, payload, csrfToken) {
            const res = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify(payload),
            });
            const texto = await res.text();
            let data;
            try { data = JSON.parse(texto); } catch (e) { data = { status: res.ok ? 'ok' : 'error', mensaje: texto }; }
            if (!res.ok && !data.mensaje) data.mensaje = 'Error HTTP ' + res.status;
            return data;
        },

        /**
         * Ejecuta una acción async mostrando un spinner y deshabilitando
         * el botón mientras dura, evitando doble-click y dejando el botón
         * "colgado" si la petición falla (bug presente en el código original).
         */
        async withSpinner(btn, accionAsync) {
            if (!btn) return accionAsync();
            const spinner = document.createElement('span');
            spinner.className = 'pt-spinner';
            btn.disabled = true;
            btn.appendChild(spinner);
            try {
                return await accionAsync();
            } finally {
                btn.disabled = false;
                spinner.remove();
            }
        },
        /**
         * Muestra un loader dentro del contenedor mientras corre `tarea`.
         * Pensado para la carga inicial de cada vista: el contenedor queda
         * ocupado por el spinner hasta que la tabla se pinta, y si la
         * promesa falla el error se ve en pantalla y no sólo en consola.
         */
        async conLoader(container, mensaje, tarea) {
            const cont = typeof container === 'string' ? document.getElementById(container) : container;
            if (!cont) return tarea();

            cont.innerHTML =
                '<div class="pt-loader">' +
                '<div class="pt-loader__spinner" role="status" aria-live="polite"></div>' +
                '<span>' + (mensaje || 'Cargando datos…') + '</span>' +
                '</div>';

            try {
                return await tarea();
            } catch (err) {
                console.error(err);
                cont.innerHTML =
                    '<div class="pt-loader__error">❌ No se pudieron cargar los datos: ' +
                    (err.message || err) + '</div>';
                throw err;
            }
        },
        /**
         * Debounce genérico: agrupa llamadas repetidas (p. ej. cada tecla
         * pulsada al editar una celda) en una sola ejecución transcurridos
         * `delay` ms sin nuevas llamadas. Pensado para el autoguardado.
         */
        debounce(fn, delay) {
            let timer = null;
            return function (...args) {
                clearTimeout(timer);
                timer = setTimeout(() => fn.apply(this, args), delay);
            };
        },

        
    };
    global.PresupuestoTable = PresupuestoTable;
    global.PresupuestoUtils = PresupuestoUtils;
})(window);
