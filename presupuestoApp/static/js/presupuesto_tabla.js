/* ==========================================================================
 * presupuesto_tabla.js
 * Tabla editable en HTML/CSS/JS puro para el módulo de presupuesto de nómina.
 *
 * Sustituye por completo a: jQuery, DataTables, DataTables Buttons,
 * DataTables FixedHeader, Select2 y JSZip.
 *
 * Todo lo que antes se repetía en cada template (formato de números,
 * footer de totales, edición en línea, duplicar/eliminar fila, filtros,
 * exportación, toasts, CSRF, guardado) vive aquí una sola vez.
 * ========================================================================== */
(function (global) {
  'use strict';

  // ---------------------------------------------------------------- utils
  const MESES = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
  ];

  const formateador = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 2 });

  /** Convierte a número cualquier valor: "1.234.567,89" -> 1234567.89 */
  function aNumero(valor) {
    if (typeof valor === 'number') return isFinite(valor) ? valor : 0;
    if (valor === null || valor === undefined || valor === '') return 0;
    const texto = String(valor).trim().replace(/\s/g, '');
    if (/^-?\d+(\.\d+)?$/.test(texto)) return parseFloat(texto);      // ya viene en formato JS
    const normalizado = texto.replace(/\./g, '').replace(',', '.');   // formato colombiano
    const n = parseFloat(normalizado);
    return isNaN(n) ? 0 : n;
  }

  function formatearNumero(valor) {
    const n = aNumero(valor);
    return n === 0 ? '0' : formateador.format(n);
  }

  function escapar(texto) {
    if (texto === null || texto === undefined) return '';
    return String(texto)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function normalizar(texto) {
    return String(texto ?? '').toLowerCase()
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  }

  // ---------------------------------------------------------------- toasts
  function toast(mensaje, tipo = 'success', duracion = 3000) {
    let contenedor = document.querySelector('.pt-toasts');
    if (!contenedor) {
      contenedor = document.createElement('div');
      contenedor.className = 'pt-toasts';
      document.body.appendChild(contenedor);
    }
    const el = document.createElement('div');
    el.className = 'pt-toast pt-toast--' + tipo;
    el.textContent = mensaje;
    contenedor.appendChild(el);
    const pintarAhora = global.requestAnimationFrame || ((fn) => setTimeout(fn, 16));
    pintarAhora(() => el.classList.add('pt-toast--visible'));
    setTimeout(() => {
      el.classList.remove('pt-toast--visible');
      setTimeout(() => el.remove(), 300);
    }, duracion);
  }

  // ------------------------------------------------------------------ HTTP
  function csrf() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute('content');
    const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (input) return input.value;
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  async function pedir(url, opciones = {}) {
    const cfg = Object.assign({ headers: {} }, opciones);
    cfg.headers['X-Requested-With'] = 'XMLHttpRequest';
    if (cfg.method && cfg.method.toUpperCase() !== 'GET') {
      cfg.headers['X-CSRFToken'] = csrf();
    }
    const resp = await fetch(url, cfg);
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const tipo = resp.headers.get('content-type') || '';
    return tipo.includes('application/json') ? resp.json() : resp.text();
  }

  function enviarJSON(url, datos) {
    return pedir(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(datos)
    });
  }

  /** Ejecuta una acción mostrando el spinner del botón y bloqueándolo. */
  async function conSpinner(boton, accion) {
    if (!boton) return accion();
    const spinner = document.createElement('span');
    spinner.className = 'pt-spinner';
    boton.appendChild(spinner);
    boton.disabled = true;
    try {
      return await accion();
    } finally {
      spinner.remove();
      boton.disabled = false;
    }
  }

  // ------------------------------------------------- multiselect con buscador
  class MultiSelect {
    constructor({ etiqueta, alCambiar }) {
      this.valores = new Set();
      this.opciones = [];
      this.alCambiar = alCambiar || (() => {});

      this.raiz = document.createElement('div');
      this.raiz.className = 'pt-filtro';
      this.raiz.innerHTML = `
        <label>${escapar(etiqueta)}</label>
        <div class="pt-multi">
          <button type="button" class="pt-multi__control">
            <span class="pt-multi__texto pt-multi__texto--vacio">Todos</span>
            <span class="pt-multi__flecha">▼</span>
          </button>
          <div class="pt-multi__menu">
            <input type="search" class="pt-multi__buscar" placeholder="Buscar…" autocomplete="off">
            <div class="pt-multi__opciones"></div>
            <div class="pt-multi__pie">
              <button type="button" data-accion="todos">Seleccionar todo</button>
              <button type="button" data-accion="ninguno">Limpiar</button>
            </div>
          </div>
        </div>`;

      this.caja      = this.raiz.querySelector('.pt-multi');
      this.control   = this.raiz.querySelector('.pt-multi__control');
      this.texto     = this.raiz.querySelector('.pt-multi__texto');
      this.buscador  = this.raiz.querySelector('.pt-multi__buscar');
      this.lista     = this.raiz.querySelector('.pt-multi__opciones');

      this.control.addEventListener('click', () => this.alternar());
      this.buscador.addEventListener('input', () => this.pintarOpciones());
      this.lista.addEventListener('change', (e) => {
        const casilla = e.target.closest('input[type="checkbox"]');
        if (!casilla) return;
        casilla.checked ? this.valores.add(casilla.value) : this.valores.delete(casilla.value);
        this.actualizarTexto();
        this.alCambiar(this.valores);
      });
      this.raiz.querySelector('[data-accion="todos"]').addEventListener('click', () => {
        this.visibles().forEach(v => this.valores.add(v));
        this.pintarOpciones(); this.actualizarTexto(); this.alCambiar(this.valores);
      });
      this.raiz.querySelector('[data-accion="ninguno"]').addEventListener('click', () => {
        this.valores.clear();
        this.pintarOpciones(); this.actualizarTexto(); this.alCambiar(this.valores);
      });
      document.addEventListener('click', (e) => {
        if (!this.raiz.contains(e.target)) this.caja.classList.remove('pt-multi--abierto');
      });
    }

    alternar() {
      const abierto = this.caja.classList.toggle('pt-multi--abierto');
      if (abierto) { this.pintarOpciones(); this.buscador.focus(); }
    }

    visibles() {
      const q = normalizar(this.buscador.value);
      return this.opciones.filter(o => !q || normalizar(o).includes(q));
    }

    setOpciones(opciones) {
      this.opciones = [...new Set(opciones.filter(v => v !== null && v !== undefined && v !== ''))]
        .map(String).sort((a, b) => a.localeCompare(b, 'es'));
      // se descartan los filtros activos que ya no existen en los datos
      [...this.valores].forEach(v => { if (!this.opciones.includes(v)) this.valores.delete(v); });
      this.pintarOpciones();
      this.actualizarTexto();
    }

    pintarOpciones() {
      const visibles = this.visibles();
      this.lista.innerHTML = visibles.length
        ? visibles.map(v => `
            <label class="pt-multi__opcion">
              <input type="checkbox" value="${escapar(v)}" ${this.valores.has(v) ? 'checked' : ''}>
              <span>${escapar(v)}</span>
            </label>`).join('')
        : '<div class="pt-multi__vacio">Sin coincidencias</div>';
    }

    actualizarTexto() {
      const n = this.valores.size;
      this.texto.classList.toggle('pt-multi__texto--vacio', n === 0);
      this.texto.textContent = n === 0 ? 'Todos'
        : n === 1 ? [...this.valores][0]
        : `${n} seleccionados`;
    }
  }

  // ------------------------------------------------------------ definiciones
  /**
   * Atajos para armar las columnas sin repetir las 12 de los meses en cada
   * template. Uso: Columnas.estandar({ base: 'salario_base' })
   */
  const Columnas = {
    meses: () => MESES.map(m => ({
      campo: m, titulo: m.charAt(0).toUpperCase() + m.slice(1), tipo: 'numero'
    })),

    estandar({ cedula = true, cargo = true, base = null, opciones = {} } = {}) {
      const cols = [];
      if (cedula) cols.push({ campo: 'cedula', titulo: 'Cédula' });
      cols.push({ campo: 'nombre', titulo: 'Nombre' });
      cols.push({ campo: 'centro', titulo: 'Centro', tipo: opciones.centros ? 'select' : 'texto', opciones: opciones.centros });
      cols.push({ campo: 'area', titulo: 'Área', tipo: opciones.areas ? 'select' : 'texto', opciones: opciones.areas });
      if (cargo) cols.push({ campo: 'cargo', titulo: 'Cargo', tipo: opciones.cargos ? 'select' : 'texto', opciones: opciones.cargos });
      cols.push({ campo: 'concepto', titulo: 'Concepto' });
      if (base === 'salario_base') cols.push({ campo: 'salario_base', titulo: 'Salario base', tipo: 'numero' });
      if (base === 'base') cols.push({ campo: 'base', titulo: 'Base', tipo: 'numero' });
      cols.push(...Columnas.meses());
      cols.push({ campo: 'total', titulo: 'Total', tipo: 'numero', editable: false });
      return cols;
    }
  };

  // ------------------------------------------------------------- la tabla
  class TablaPresupuesto {
    /**
     * @param {Object} cfg
     *  - montaje        selector del contenedor
     *  - columnas       [{campo, titulo, tipo:'texto'|'numero'|'select', editable, opciones}]
     *  - urlDatos       endpoint GET que devuelve las filas
     *  - claveDatos     'data' si la respuesta viene envuelta (auto-detectado)
     *  - seleccionable  muestra la columna de checkbox (por defecto true)
     *  - acciones       ['duplicar','eliminar','copiar']
     *  - editable       permite edición en línea (por defecto true)
     *  - filtros        campos con multiselect, p. ej. ['nombre','centro','area']
     *  - buscador       caja de búsqueda global (por defecto true)
     *  - camposTotal    columnas que se suman en el pie (por defecto meses + total)
     *  - recalcular     fn(fila) ejecutada tras cada edición (además del total)
     */
    constructor(cfg) {
      this.cfg = Object.assign({
        seleccionable: true,
        acciones: ['duplicar', 'eliminar'],
        editable: true,
        filtros: ['nombre', 'centro', 'area'],
        buscador: true,
        camposTotal: MESES.concat('total'),
        nombreArchivo: 'presupuesto'
      }, cfg);

      this.columnas = this.cfg.columnas;
      this.filas = [];
      this.visibles = [];
      this.seleccion = new Set();   // referencias a los objetos fila
      this.filaActiva = null;
      this.orden = { campo: null, dir: 1 };
      this.filtros = {};            // campo -> MultiSelect
      this.textoBusqueda = '';

      this.raiz = typeof this.cfg.montaje === 'string'
        ? document.querySelector(this.cfg.montaje) : this.cfg.montaje;

      this._construirEsqueleto();
      this._conectarEventos();
      if (this.cfg.urlDatos) this.cargar();
    }

    // ------------------------------------------------------------ esqueleto
    _construirEsqueleto() {
      this.raiz.innerHTML = `
        <div class="pt-filtros"></div>
        <div class="pt-tabla-envoltura">
          <table class="pt-tabla">
            <thead></thead>
            <tbody></tbody>
            <tfoot></tfoot>
          </table>
        </div>`;

      this.zonaFiltros = this.raiz.querySelector('.pt-filtros');
      this.tabla  = this.raiz.querySelector('table');
      this.thead  = this.tabla.tHead;
      this.tbody  = this.tabla.tBodies[0];
      this.tfoot  = this.tabla.tFoot;

      if (this.cfg.buscador) {
        const caja = document.createElement('div');
        caja.className = 'pt-filtro pt-buscador';
        caja.innerHTML = '<label>Buscar</label><input type="search" placeholder="Buscar en toda la tabla…">';
        caja.querySelector('input').addEventListener('input', (e) => {
          this.textoBusqueda = normalizar(e.target.value);
          this.pintar();
        });
        this.zonaFiltros.appendChild(caja);
      }

      (this.cfg.filtros || []).forEach(campo => {
        const col = this.columnas.find(c => c.campo === campo);
        const ms = new MultiSelect({
          etiqueta: col ? col.titulo : campo,
          alCambiar: () => this.pintar()
        });
        this.filtros[campo] = ms;
        this.zonaFiltros.appendChild(ms.raiz);
      });

      this.contador = document.createElement('span');
      this.contador.className = 'pt-contador';
      this.zonaFiltros.appendChild(this.contador);

      this._pintarCabecera();
    }

    _columnasVisibles() {
      const cols = [];
      if (this.cfg.seleccionable) cols.push({ especial: 'check' });
      if (this.cfg.acciones && this.cfg.acciones.length) cols.push({ especial: 'acciones' });
      return cols.concat(this.columnas);
    }

    _pintarCabecera() {
      const th = this._columnasVisibles().map(col => {
        if (col.especial === 'check') {
          return '<th class="pt-col-check"><input type="checkbox" data-rol="check-todos" title="Seleccionar todo"></th>';
        }
        if (col.especial === 'acciones') return '<th class="pt-col-acciones">Acciones</th>';
        const clase = col.tipo === 'numero' ? 'pt-num pt-ordenable' : 'pt-ordenable';
        return `<th class="${clase}" data-campo="${col.campo}">${escapar(col.titulo)}<span class="pt-orden"></span></th>`;
      }).join('');
      this.thead.innerHTML = `<tr>${th}</tr>`;
    }

    // -------------------------------------------------------------- datos
    async cargar() {
      try {
        const respuesta = await pedir(this.cfg.urlDatos);
        this.setDatos(Array.isArray(respuesta) ? respuesta : (respuesta.data || []));
      } catch (e) {
        console.error(e);
        toast('No se pudieron cargar los datos ❌', 'error');
      }
    }

    setDatos(filas) {
      this.filas = filas.map(f => Object.assign({}, f));
      this.seleccion.clear();
      this.filaActiva = null;
      this._refrescarOpcionesFiltro();
      this.pintar();
    }

    /** Filas tal cual se enviarían al backend. */
    datos() { return this.filas; }

    filasSeleccionadas() { return this.filas.filter(f => this.seleccion.has(f)); }

    _refrescarOpcionesFiltro() {
      Object.entries(this.filtros).forEach(([campo, ms]) => {
        ms.setOpciones(this.filas.map(f => f[campo]));
      });
    }

    // ------------------------------------------------------------- pintado
    _aplicarFiltros() {
      const activos = Object.entries(this.filtros).filter(([, ms]) => ms.valores.size);
      this.visibles = this.filas.filter(fila => {
        for (const [campo, ms] of activos) {
          if (!ms.valores.has(String(fila[campo] ?? ''))) return false;
        }
        if (this.textoBusqueda) {
          const texto = this.columnas.map(c => fila[c.campo]).join(' ');
          if (!normalizar(texto).includes(this.textoBusqueda)) return false;
        }
        return true;
      });

      if (this.orden.campo) {
        const col = this.columnas.find(c => c.campo === this.orden.campo);
        const numerica = col && col.tipo === 'numero';
        this.visibles.sort((a, b) => {
          const x = a[this.orden.campo], y = b[this.orden.campo];
          const cmp = numerica
            ? aNumero(x) - aNumero(y)
            : String(x ?? '').localeCompare(String(y ?? ''), 'es', { numeric: true });
          return cmp * this.orden.dir;
        });
      }
    }

    pintar() {
      this._aplicarFiltros();

      const posicion = new Map(this.filas.map((f, i) => [f, i]));
      const partes = [];
      this.visibles.forEach(fila => {
        const idx = posicion.get(fila);
        const clases = [];
        if (this.seleccion.has(fila)) clases.push('pt-fila--marcada');
        if (this.filaActiva === fila) clases.push('pt-fila--activa');
        partes.push(`<tr data-indice="${idx}" class="${clases.join(' ')}">`);

        if (this.cfg.seleccionable) {
          partes.push(`<td class="pt-col-check"><input type="checkbox" data-rol="check-fila" ${this.seleccion.has(fila) ? 'checked' : ''}></td>`);
        }
        if (this.cfg.acciones && this.cfg.acciones.length) {
          partes.push('<td class="pt-col-acciones"><div class="pt-acciones-fila">');
          if (this.cfg.acciones.includes('duplicar')) partes.push('<button type="button" data-rol="duplicar" title="Duplicar fila">📑</button>');
          if (this.cfg.acciones.includes('copiar'))   partes.push('<button type="button" data-rol="copiar"   title="Copiar fila">📋</button>');
          if (this.cfg.acciones.includes('eliminar')) partes.push('<button type="button" data-rol="eliminar" title="Eliminar fila">❌</button>');
          partes.push('</div></td>');
        }

        this.columnas.forEach(col => {
          const editable = this.cfg.editable && col.editable !== false;
          const clase = [col.tipo === 'numero' ? 'pt-num' : '', editable ? 'pt-editable' : ''].filter(Boolean).join(' ');
          const valor = col.tipo === 'numero' ? formatearNumero(fila[col.campo]) : escapar(fila[col.campo] ?? '');
          partes.push(`<td class="${clase}" data-campo="${col.campo}">${valor}</td>`);
        });

        partes.push('</tr>');
      });

      this.tbody.innerHTML = partes.join('') ||
        `<tr><td class="pt-vacio" colspan="${this._columnasVisibles().length}">Sin registros para mostrar</td></tr>`;

      this._pintarTotales();
      this.contador.textContent =
        `${this.visibles.length} de ${this.filas.length} fila(s)` +
        (this.seleccion.size ? ` · ${this.seleccion.size} seleccionada(s)` : '');

      const todos = this.thead.querySelector('[data-rol="check-todos"]');
      if (todos) todos.checked = this.visibles.length > 0 && this.visibles.every(f => this.seleccion.has(f));

      this.thead.querySelectorAll('th[data-campo]').forEach(th => {
        const marca = th.querySelector('.pt-orden');
        marca.textContent = this.orden.campo === th.dataset.campo ? (this.orden.dir === 1 ? '▲' : '▼') : '';
      });
    }

    _pintarTotales() {
      const sumas = {};
      this.cfg.camposTotal.forEach(campo => { sumas[campo] = 0; });
      this.visibles.forEach(fila => {
        this.cfg.camposTotal.forEach(campo => { sumas[campo] += aNumero(fila[campo]); });
      });

      let etiquetaPuesta = false;
      const celdas = this._columnasVisibles().map(col => {
        if (col.especial) {
          if (!etiquetaPuesta && col.especial === 'acciones') { etiquetaPuesta = true; return '<th>Totales</th>'; }
          return '<th></th>';
        }
        if (col.campo in sumas) return `<th class="pt-num">${formatearNumero(sumas[col.campo])}</th>`;
        if (!etiquetaPuesta) { etiquetaPuesta = true; return '<th>Totales visibles</th>'; }
        return '<th></th>';
      });
      this.tfoot.innerHTML = `<tr>${celdas.join('')}</tr>`;
    }

    // ------------------------------------------------------------- eventos
    _conectarEventos() {
      this.thead.addEventListener('click', (e) => {
        const th = e.target.closest('th[data-campo]');
        if (th) {
          this.orden = this.orden.campo === th.dataset.campo
            ? { campo: th.dataset.campo, dir: -this.orden.dir }
            : { campo: th.dataset.campo, dir: 1 };
          this.pintar();
        }
      });

      this.thead.addEventListener('change', (e) => {
        if (e.target.dataset.rol !== 'check-todos') return;
        this.visibles.forEach(f => e.target.checked ? this.seleccion.add(f) : this.seleccion.delete(f));
        this.pintar();
      });

      this.tbody.addEventListener('change', (e) => {
        if (e.target.dataset.rol !== 'check-fila') return;
        const fila = this._filaDe(e.target);
        e.target.checked ? this.seleccion.add(fila) : this.seleccion.delete(fila);
        this.pintar();
      });

      this.tbody.addEventListener('click', (e) => {
        const boton = e.target.closest('button[data-rol]');
        const tr = e.target.closest('tr[data-indice]');
        if (!tr) return;
        const fila = this.filas[Number(tr.dataset.indice)];

        if (boton) {
          if (boton.dataset.rol === 'duplicar') this.duplicar(fila);
          if (boton.dataset.rol === 'eliminar') this.eliminar(fila);
          if (boton.dataset.rol === 'copiar')   this.copiarAlPortapapeles(fila);
          return;
        }
        this.filaActiva = fila;
        this.tbody.querySelectorAll('tr').forEach(x => x.classList.remove('pt-fila--activa'));
        tr.classList.add('pt-fila--activa');
      });

      this.tbody.addEventListener('dblclick', (e) => {
        const td = e.target.closest('td.pt-editable');
        if (td) this.editar(td);
      });
    }

    _filaDe(el) {
      const tr = el.closest('tr[data-indice]');
      return tr ? this.filas[Number(tr.dataset.indice)] : null;
    }

    // ------------------------------------------------------------- edición
    editar(td) {
      if (td.querySelector('.pt-entrada')) return;
      const campo = td.dataset.campo;
      const col = this.columnas.find(c => c.campo === campo);
      const fila = this._filaDe(td);
      const valorOriginal = fila[campo];

      let entrada;
      if (col.tipo === 'select' && col.opciones) {
        entrada = document.createElement('select');
        entrada.innerHTML = '<option value=""></option>' +
          col.opciones.map(o => `<option value="${escapar(o)}">${escapar(o)}</option>`).join('');
        entrada.value = valorOriginal ?? '';
      } else {
        entrada = document.createElement('input');
        entrada.type = col.tipo === 'numero' ? 'number' : 'text';
        entrada.value = col.tipo === 'numero' ? aNumero(valorOriginal) : (valorOriginal ?? '');
      }
      entrada.className = 'pt-entrada';

      td.textContent = '';
      td.appendChild(entrada);
      entrada.focus();
      if (entrada.select) entrada.select();

      // posición de la celda ANTES de repintar, para poder saltar a la vecina
      const posFila = [...this.tbody.rows].indexOf(td.parentElement);

      const cerrar = (guardar) => {
        if (!td.contains(entrada)) return;
        if (guardar) this.setValor(fila, campo, col.tipo === 'numero' ? aNumero(entrada.value) : entrada.value);
        this.pintar();
      };

      entrada.addEventListener('blur', () => cerrar(true));
      entrada.addEventListener('keydown', (e) => {
        const saltar = (dFila, dCol) => {
          e.preventDefault();
          cerrar(true);
          this._enfocarCelda(posFila + dFila, campo, dCol);
        };
        if (e.key === 'Enter') saltar(1, 0);
        else if (e.key === 'Escape') { e.preventDefault(); cerrar(false); }
        else if (e.key === 'Tab') saltar(0, e.shiftKey ? -1 : 1);
        else if (['ArrowUp', 'ArrowDown'].includes(e.key) && entrada.tagName === 'INPUT') {
          saltar(e.key === 'ArrowUp' ? -1 : 1, 0);
        }
      });
    }

    /** Guarda un valor y recalcula el total (y lo que indique cfg.recalcular). */
    setValor(fila, campo, valor) {
      fila[campo] = valor;
      if (this.cfg.recalcular) this.cfg.recalcular(fila, campo);
      if (MESES.includes(campo) && 'total' in fila) TablaPresupuesto.recalcularTotal(fila);
    }

    /** Abre para edición la celda (fila, campo) tras repintar la tabla. */
    _enfocarCelda(posFila, campo, dCol = 0) {
      const editables = this.columnas.filter(c => this.cfg.editable && c.editable !== false);
      let destino = campo;
      if (dCol) {
        const i = editables.findIndex(c => c.campo === campo) + dCol;
        if (i < 0 || i >= editables.length) return;
        destino = editables[i].campo;
      }
      const tr = this.tbody.rows[posFila];
      if (!tr) return;
      const td = tr.querySelector(`td[data-campo="${destino}"]`);
      if (td && td.classList.contains('pt-editable')) {
        if (td.scrollIntoView) td.scrollIntoView({ block: 'nearest', inline: 'nearest' });
        this.editar(td);
      }
    }

    // ----------------------------------------------------------- operaciones
    static recalcularTotal(fila) {
      fila.total = MESES.reduce((suma, m) => suma + aNumero(fila[m]), 0);
      return fila;
    }

    /** Aplica una función a las filas marcadas. Devuelve cuántas cambiaron. */
    aplicarASeleccionadas(fn, { avisar = true } = {}) {
      const filas = this.filasSeleccionadas();
      if (!filas.length) {
        if (avisar) toast('Selecciona al menos una fila ⚠️', 'warning');
        return 0;
      }
      filas.forEach(fila => { fn(fila); TablaPresupuesto.recalcularTotal(fila); });
      this.pintar();
      if (avisar) toast(`Cálculo aplicado a ${filas.length} fila(s) ✅`);
      return filas.length;
    }

    agregarFila(base = {}) {
      const fila = {};
      this.columnas.forEach(c => { fila[c.campo] = c.tipo === 'numero' ? 0 : ''; });
      Object.assign(fila, base);
      this.filas.push(fila);
      this._refrescarOpcionesFiltro();
      this.pintar();
      return fila;
    }

    duplicar(fila) {
      const copia = Object.assign({}, fila);
      delete copia.id;
      MESES.forEach(m => { if (m in copia) copia[m] = 0; });
      if ('total' in copia) copia.total = 0;
      this.filas.splice(this.filas.indexOf(fila) + 1, 0, copia);
      this.filaActiva = copia;
      this.pintar();
      const tr = this.tbody.querySelector(`tr[data-indice="${this.filas.indexOf(copia)}"]`);
      if (tr) {
        tr.classList.add('pt-destello');
        if (tr.scrollIntoView) tr.scrollIntoView({ block: 'nearest' });
      }
      toast('Fila duplicada 📑');
    }

    eliminar(fila) {
      this.filas.splice(this.filas.indexOf(fila), 1);
      this.seleccion.delete(fila);
      this.pintar();
      toast('Fila eliminada ❌', 'error');
    }

    copiarAlPortapapeles(fila, campos = ['cedula', 'nombre', 'centro', 'area', 'cargo', 'concepto']) {
      const reducida = {};
      campos.forEach(c => { if (c in fila) reducida[c] = fila[c] || ''; });
      localStorage.setItem('filaCopiadaNomina', JSON.stringify(reducida));
      toast('Fila copiada 📋');
    }

    pegarDelPortapapeles() {
      const guardada = localStorage.getItem('filaCopiadaNomina');
      if (!guardada) { toast('No hay ninguna fila copiada ⚠️', 'warning'); return null; }
      const fila = this.agregarFila(JSON.parse(guardada));
      toast('Fila pegada desde Sueldos ✅');
      return fila;
    }

    /**
     * Reparte cada fila seleccionada en varias según los porcentajes dados.
     * reparto: [{porcentaje, centro, area}] — los de porcentaje 0 se ignoran.
     */
    distribuir(reparto) {
      const suma = reparto.reduce((a, r) => a + (r.porcentaje || 0), 0);
      if (Math.abs(suma - 100) > 0.001) {
        toast('La suma de los porcentajes debe ser exactamente 100% ❌', 'error');
        return 0;
      }
      const seleccionadas = this.filasSeleccionadas();
      if (!seleccionadas.length) { toast('Selecciona al menos una fila ⚠️', 'warning'); return 0; }

      const nuevas = [];
      seleccionadas.forEach(fila => {
        reparto.filter(r => r.porcentaje > 0).forEach(r => {
          const copia = Object.assign({}, fila);
          delete copia.id;
          const factor = r.porcentaje / 100;
          MESES.forEach(m => { copia[m] = Math.round(aNumero(fila[m]) * factor * 100) / 100; });
          TablaPresupuesto.recalcularTotal(copia);
          if (r.centro) copia.centro = r.centro;
          if (r.area) copia.area = r.area;
          nuevas.push(copia);
        });
      });

      this.filas = this.filas.filter(f => !this.seleccion.has(f)).concat(nuevas);
      this.seleccion.clear();
      this._refrescarOpcionesFiltro();
      this.pintar();
      toast(`${seleccionadas.length} fila(s) reemplazadas por ${nuevas.length} ✅`);
      return nuevas.length;
    }

    // --------------------------------------------------------- exportación
    /** CSV con BOM y separador ';' → Excel lo abre directo, sin JSZip. */
    exportar(nombre = this.cfg.nombreArchivo) {
      const cabecera = this.columnas.map(c => c.titulo);
      const filas = this.visibles.map(f => this.columnas.map(c =>
        c.tipo === 'numero' ? String(aNumero(f[c.campo])).replace('.', ',') : (f[c.campo] ?? '')
      ));
      const csv = [cabecera, ...filas]
        .map(fila => fila.map(v => `"${String(v).replace(/"/g, '""')}"`).join(';'))
        .join('\r\n');

      const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
      const enlace = document.createElement('a');
      enlace.href = URL.createObjectURL(blob);
      enlace.download = `${nombre}.csv`;
      enlace.click();
      URL.revokeObjectURL(enlace.href);
      toast('Archivo exportado 📥');
    }

    // ------------------------------------------------------------ guardado
    async guardar(url, boton, mensaje = 'Datos guardados ✅') {
      return conSpinner(boton, async () => {
        try {
          await enviarJSON(url, this.datos());
          toast(mensaje);
        } catch (e) {
          console.error(e);
          toast('Error al guardar ❌', 'error');
        }
      });
    }
  }

  // ------------------------------------------------------ cableado genérico
  /**
   * Conecta los botones estándar de la barra superior a partir de data-rol,
   * evitando repetir los mismos handlers en cada template.
   *
   * data-rol admitidos: inicio | ir | guardar | guardar-temp | borrar |
   *                     cargar-base | subir | agregar | pegar | exportar |
   *                     calcular | distribuir
   */
  function conectarBarra(tabla, urls = {}, extra = {}) {
    const boton = (rol) => document.querySelector(`[data-rol="${rol}"]`);
    const navegar = (rol, url) => {
      const b = boton(rol);
      if (b && url) b.addEventListener('click', () => { window.location.href = url; });
    };

    navegar('inicio', urls.inicio);
    navegar('ir', urls.ir);

    const conUrl = (rol, url, fn) => {
      const b = boton(rol);
      if (b && url) b.addEventListener('click', () => fn(b));
    };

    conUrl('guardar', urls.guardar, (b) =>
      tabla.guardar(urls.guardar, b, 'Datos guardados ✅'));

    conUrl('guardar-temp', urls.guardarTemp, (b) =>
      tabla.guardar(urls.guardarTemp, b, 'Datos guardados en la tabla temporal ✅'));

    conUrl('cargar-base', urls.cargarBase, (b) => conSpinner(b, async () => {
      try {
        await pedir(urls.cargarBase);
        await tabla.cargar();
        toast('Datos cargados desde Conceptos 📂');
      } catch (e) { console.error(e); toast('Error al cargar los datos ❌', 'error'); }
    }));

    conUrl('subir', urls.subir, (b) => conSpinner(b, async () => {
      try {
        const r = await pedir(urls.subir, { method: 'POST' });
        toast(r.msg || 'Presupuesto subido ✅', r.success === false ? 'error' : 'success');
      } catch (e) { console.error(e); toast('Error en la subida ❌', 'error'); }
    }));

    conUrl('borrar', urls.borrar, (b) => {
      if (!confirm('¿Seguro que quieres borrar todo el presupuesto? Esta acción no se puede deshacer.')) return;
      return conSpinner(b, async () => {
        try {
          await pedir(urls.borrar, { method: 'POST' });
          await tabla.cargar();
          toast('Presupuesto eliminado correctamente ✅');
        } catch (e) { console.error(e); toast('Error al borrar ❌', 'error'); }
      });
    });

    const simple = (rol, fn) => { const b = boton(rol); if (b) b.addEventListener('click', () => fn(b)); };
    simple('agregar',  () => { tabla.agregarFila(); toast('Fila agregada ✅'); });
    simple('pegar',    () => tabla.pegarDelPortapapeles());
    simple('exportar', () => tabla.exportar());
    if (extra.calcular)   simple('calcular',   extra.calcular);
    if (extra.calcular2)  simple('calcular-2', extra.calcular2);
    if (extra.distribuir) simple('distribuir', extra.distribuir);
  }

  /** Lee una lista serializada con {{ variable|json_script:"id" }}. */
  function listaJSON(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  }

  /** Lee los porcentajes del panel de distribución estándar. */
  function leerDistribucion() {
    return [...document.querySelectorAll('.pt-panel__campos input[type="number"]')].map(input => ({
      porcentaje: parseFloat(input.value) || 0,
      centro: input.dataset.centro || '',
      area: input.dataset.area || ''
    }));
  }

  global.PT = {
    MESES, Columnas, TablaPresupuesto, MultiSelect,
    aNumero, formatearNumero, toast, pedir, enviarJSON, conSpinner,
    conectarBarra, listaJSON, leerDistribucion
  };
})(window);
