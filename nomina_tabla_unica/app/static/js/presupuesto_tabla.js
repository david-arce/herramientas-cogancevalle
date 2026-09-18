/* ==========================================================================
 * presupuesto_tabla.js
 * Tabla editable en HTML/CSS/JS puro para el módulo de presupuesto.
 *
 * Cambios para la tabla única de nómina:
 *  - Ya no hay "tabla temporal" ni "subir": se guarda directo y el servidor
 *    recalcula en cascada lo que dependa del concepto.
 *  - Los cálculos (incrementos, retroactivo, promedios…) ya no se hacen en el
 *    navegador: viven en nomina_motor.py (se eliminó presupuesto_calculos.js).
 *  - Columna "Origen": ⚙️ calculada por el sistema / ✋ ajustada a mano.
 *  - Aviso de cambios sin guardar.
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
  function toast(mensaje, tipo = 'success', duracion = 3500) {
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
    const tipo = resp.headers.get('content-type') || '';
    const cuerpo = tipo.includes('application/json') ? await resp.json() : await resp.text();
    if (!resp.ok) {
      const mensaje = (cuerpo && (cuerpo.msg || cuerpo.message || cuerpo.error)) || ('HTTP ' + resp.status);
      throw new Error(mensaje);
    }
    return cuerpo;
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
  const ORIGENES = {
    sistema: '<span class="pt-origen pt-origen--sistema" title="Lo calcula el sistema">⚙️ Calculado</span>',
    manual:  '<span class="pt-origen pt-origen--manual" title="Ajustado a mano: no se recalcula">✋ Manual</span>'
  };

  const Columnas = {
    meses: () => MESES.map(m => ({
      campo: m, titulo: m.charAt(0).toUpperCase() + m.slice(1), tipo: 'numero'
    })),

    /**
     * @param {Object} o
     *  - cedula, cargo   mostrar esas columnas
     *  - base            título de la columna "base" (null = no se muestra)
     *  - opciones        {centros, areas, cargos} para los desplegables
     *  - origen          mostrar la columna Origen
     *  - tipo            mostrar la columna "Concepto de nómina" (vista consolidada)
     */
    estandar({ cedula = true, cargo = true, base = null, opciones = {}, origen = true, tipo = false } = {}) {
      const cols = [];
      if (origen) cols.push({ campo: 'origen', titulo: 'Origen', tipo: 'origen', editable: false });
      if (tipo) cols.push({ campo: 'tipo_nombre', titulo: 'Concepto de nómina', editable: false });
      if (cedula) cols.push({ campo: 'cedula', titulo: 'Cédula' });
      cols.push({ campo: 'nombre', titulo: 'Nombre' });
      cols.push({ campo: 'centro', titulo: 'Centro', tipo: opciones.centros ? 'select' : 'texto', opciones: opciones.centros });
      cols.push({ campo: 'area', titulo: 'Área', tipo: opciones.areas ? 'select' : 'texto', opciones: opciones.areas });
      if (cargo) cols.push({ campo: 'cargo', titulo: 'Cargo', tipo: opciones.cargos ? 'select' : 'texto', opciones: opciones.cargos });
      cols.push({ campo: 'concepto', titulo: 'Concepto' });
      if (base) cols.push({ campo: 'base', titulo: base, tipo: 'numero' });
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
     *  - columnas       [{campo, titulo, tipo:'texto'|'numero'|'select'|'origen', editable, opciones}]
     *  - urlDatos       endpoint GET que devuelve las filas
     *  - seleccionable  muestra la columna de checkbox (por defecto true)
     *  - acciones       ['duplicar','eliminar','copiar']
     *  - editable       permite edición en línea (por defecto true)
     *  - alSeleccionar  fn(filasSeleccionadas) cada vez que se repinta la tabla
     *  - accionesExtra  [{rol, icono, titulo, mostrar(fila), clase(fila)}] botones propios por fila
     *  - alAccion       fn(rol, fila) al pulsar uno de esos botones
     *  - filtros        campos con multiselect, p. ej. ['nombre','centro','area']
     *  - buscador       caja de búsqueda global (por defecto true)
     *  - camposTotal    columnas que se suman en el pie (por defecto meses + total)
     *  - recalcular     fn(fila, campo) ejecutada tras cada edición (además del total)
     *  - alCambiar      fn(sinGuardar) cuando cambia el estado de "cambios sin guardar"
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
      this.seleccion = new Set();
      this.filaActiva = null;
      this.orden = { campo: null, dir: 1 };
      this.filtros = {};
      this.textoBusqueda = '';
      this.sinGuardar = false;
      // Selección de celdas tipo Excel: índices sobre `visibles` y `columnas`
      this.cursor = null;          // {f, c}
      this.ancla = null;           // esquina fija del rango
      this.relleno = null;         // arrastre del cuadrito de relleno
      this._foco = false;

      this.raiz = typeof this.cfg.montaje === 'string'
        ? document.querySelector(this.cfg.montaje) : this.cfg.montaje;

      this._construirEsqueleto();
      this._conectarEventos();
      if (this.cfg.urlDatos) this.cargar();
    }

    // ------------------------------------------------------ cambios pendientes
    marcarCambios(valor = true) {
      if (this.sinGuardar === valor) return;
      this.sinGuardar = valor;
      if (this.cfg.alCambiar) this.cfg.alCambiar(valor);
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
      if (this._hayAcciones()) cols.push({ especial: 'acciones' });
      return cols.concat(this.columnas);
    }

    _hayAcciones() {
      return !!((this.cfg.acciones && this.cfg.acciones.length) ||
                (this.cfg.accionesExtra && this.cfg.accionesExtra.length));
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
        toast('No se pudieron cargar los datos ❌ ' + e.message, 'error');
      }
    }

    setDatos(filas) {
      this.filas = filas.map(f => Object.assign({}, f));
      this.seleccion.clear();
      this.filaActiva = null;
      this._refrescarOpcionesFiltro();
      this.pintar();
      this.marcarCambios(false);
    }

    /** Filas tal cual se envían al backend. */
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

    _celda(fila, col) {
      if (col.tipo === 'numero') return formatearNumero(fila[col.campo]);
      if (col.tipo === 'origen') return ORIGENES[fila.origen] || ORIGENES.manual;
      return escapar(fila[col.campo] ?? '');
    }

    pintar() {
      this._aplicarFiltros();
      if (typeof this.cfg.alSeleccionar === 'function') this.cfg.alSeleccionar(this.filasSeleccionadas());

      const posicion = new Map(this.filas.map((f, i) => [f, i]));
      const partes = [];
      this.visibles.forEach((fila, iv) => {
        const idx = posicion.get(fila);
        const clases = [];
        if (this.seleccion.has(fila)) clases.push('pt-fila--marcada');
        if (this.filaActiva === fila) clases.push('pt-fila--activa');
        if (fila._recalcular) clases.push('pt-fila--recalcular');
        partes.push(`<tr data-indice="${idx}" class="${clases.join(' ')}">`);

        if (this.cfg.seleccionable) {
          partes.push(`<td class="pt-col-check"><input type="checkbox" data-rol="check-fila" ${this.seleccion.has(fila) ? 'checked' : ''}></td>`);
        }
        if (this._hayAcciones()) {
          partes.push('<td class="pt-col-acciones"><div class="pt-acciones-fila">');
          if (this.cfg.acciones.includes('duplicar')) partes.push('<button type="button" data-rol="duplicar" title="Duplicar fila">📑</button>');
          if (this.cfg.acciones.includes('copiar'))   partes.push('<button type="button" data-rol="copiar"   title="Copiar fila">📋</button>');
          (this.cfg.accionesExtra || []).forEach(extra => {
            if (extra.mostrar && !extra.mostrar(fila)) return;
            const clase = extra.clase ? extra.clase(fila) : '';
            const titulo = typeof extra.titulo === 'function' ? extra.titulo(fila) : (extra.titulo || '');
            partes.push(`<button type="button" data-rol="${escapar(extra.rol)}" class="${escapar(clase)}" title="${escapar(titulo)}">${extra.icono}</button>`);
          });
          if (this.cfg.acciones.includes('eliminar')) partes.push('<button type="button" data-rol="eliminar" title="Eliminar fila">❌</button>');
          partes.push('</div></td>');
        }

        this.columnas.forEach((col, ic) => {
          const editable = this.cfg.editable && col.editable !== false;
          const clase = [col.tipo === 'numero' ? 'pt-num' : '', editable ? 'pt-editable' : ''].filter(Boolean).join(' ');
          partes.push(`<td class="${clase}" data-campo="${col.campo}" data-fila="${iv}" data-col="${ic}">${this._celda(fila, col)}</td>`);
        });

        partes.push('</tr>');
      });

      this.tbody.innerHTML = partes.join('') ||
        `<tr><td class="pt-vacio" colspan="${this._columnasVisibles().length}">Sin registros para mostrar</td></tr>`;

      this._pintarSeleccionCeldas();
      this._pintarTotales();
      const manuales = this.filas.filter(f => f.origen === 'manual').length;
      this.contador.textContent =
        `${this.visibles.length} de ${this.filas.length} fila(s)` +
        (manuales ? ` · ${manuales} manual(es)` : '') +
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
          if ((this.cfg.accionesExtra || []).some(x => x.rol === boton.dataset.rol) && this.cfg.alAccion) {
            this.cfg.alAccion(boton.dataset.rol, fila);
          }
          return;
        }
        this.filaActiva = fila;
        this.tbody.querySelectorAll('tr').forEach(x => x.classList.remove('pt-fila--activa'));
        tr.classList.add('pt-fila--activa');
      });

      this.tbody.addEventListener('dblclick', (e) => {
        const td = e.target.closest('td.pt-editable');
        if (td && !e.target.classList.contains('pt-arrastre')) this.editar(td);
      });

      this._conectarCeldas();
    }

    // ══════════════════════════════════════════════════════════════════
    //  Selección de celdas tipo Excel
    //  Flechas para moverse, Shift para extender, Ctrl+C/V/X, Supr para
    //  borrar, escribir para editar y cuadrito de relleno para arrastrar.
    // ══════════════════════════════════════════════════════════════════

    _rango() {
      if (!this.cursor) return null;
      const a = this.ancla || this.cursor;
      return {
        f0: Math.min(a.f, this.cursor.f), f1: Math.max(a.f, this.cursor.f),
        c0: Math.min(a.c, this.cursor.c), c1: Math.max(a.c, this.cursor.c),
      };
    }

    _td(f, c) { return this.tbody.querySelector(`td[data-fila="${f}"][data-col="${c}"]`); }

    _pintarSeleccionCeldas() {
      this.tbody.querySelectorAll('td[data-col]').forEach(td => {
        td.classList.remove('pt-celda--cursor', 'pt-celda--rango', 'pt-celda--relleno');
        const handle = td.querySelector('.pt-arrastre');
        if (handle) handle.remove();
      });
      const r = this._rango();
      if (!r) return;
      if (this.cursor.f >= this.visibles.length) { this.cursor.f = this.visibles.length - 1; }
      for (let f = r.f0; f <= r.f1; f++) {
        for (let c = r.c0; c <= r.c1; c++) {
          const td = this._td(f, c);
          if (td) td.classList.add('pt-celda--rango');
        }
      }
      const activa = this._td(this.cursor.f, this.cursor.c);
      if (activa) activa.classList.add('pt-celda--cursor');
      if (this.relleno) {
        const p = this.relleno.previo;
        if (p) {
          for (let f = p.f0; f <= p.f1; f++) {
            for (let c = p.c0; c <= p.c1; c++) {
              const td = this._td(f, c);
              if (td) td.classList.add('pt-celda--relleno');
            }
          }
        }
      }
      // cuadrito de relleno en la esquina inferior derecha
      if (this.cfg.editable) {
        const esquina = this._td(r.f1, r.c1);
        if (esquina && !esquina.querySelector('.pt-entrada')) {
          const punto = document.createElement('span');
          punto.className = 'pt-arrastre';
          punto.title = 'Arrastre para copiar · doble clic para llenar hacia abajo';
          esquina.appendChild(punto);
        }
      }
    }

    irACelda(f, c, { extender = false, desplazar = true } = {}) {
      if (!this.visibles.length || !this.columnas.length) return;
      f = Math.max(0, Math.min(f, this.visibles.length - 1));
      c = Math.max(0, Math.min(c, this.columnas.length - 1));
      this.cursor = { f, c };
      if (!extender || !this.ancla) this.ancla = extender ? (this.ancla || { f, c }) : { f, c };
      this._pintarSeleccionCeldas();
      const td = this._td(f, c);
      if (td && desplazar && td.scrollIntoView) td.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    }

    _valorCelda(fila, col) {
      const v = fila[col.campo];
      return col.tipo === 'numero' ? String(aNumero(v)) : String(v ?? '');
    }

    /** El rango como texto TSV (lo entiende Excel). */
    textoDelRango() {
      const r = this._rango();
      if (!r) return '';
      const lineas = [];
      for (let f = r.f0; f <= r.f1; f++) {
        const fila = this.visibles[f];
        const celdas = [];
        for (let c = r.c0; c <= r.c1; c++) celdas.push(this._valorCelda(fila, this.columnas[c]));
        lineas.push(celdas.join('\t'));
      }
      return lineas.join('\n');
    }

    _escribirCelda(fila, col, texto) {
      if (!this.cfg.editable || col.editable === false) return false;
      if (col.tipo === 'numero') {
        this.setValor(fila, col.campo, aNumero(texto));
      } else {
        let valor = String(texto ?? '').trim();
        if (col.tipo === 'select' && col.opciones && valor) {
          const igual = col.opciones.find(o => normalizar(o) === normalizar(valor));
          valor = igual || valor;
        }
        this.setValor(fila, col.campo, valor);
      }
      return true;
    }

    /** Pega un TSV (de Excel o de la misma tabla) desde la celda activa. */
    pegarTexto(texto) {
      if (!this.cursor || !this.cfg.editable) return 0;
      const matriz = String(texto).replace(/\r/g, '').replace(/\n$/, '')
        .split('\n').map(l => l.split('\t'));
      if (!matriz.length) return 0;
      const { f, c } = this.cursor;
      let escritas = 0, agregadas = 0;
      matriz.forEach((linea, df) => {
        let fila = this.visibles[f + df];
        if (!fila) {                       // más líneas que filas: se agregan al final
          fila = this.agregarFila(this._baseFilaNueva());
          agregadas++;
        }
        linea.forEach((valor, dc) => {
          const col = this.columnas[c + dc];
          if (col && this._escribirCelda(fila, col, valor)) escritas++;
        });
      });
      this.pintar();
      if (agregadas) {
        this.irACelda(this.visibles.indexOf(this.visibles[this.visibles.length - 1]), c);
        toast(`${escritas} celdas pegadas · ${agregadas} fila(s) nueva(s) ✅`);
      } else {
        this.cursor = { f, c };
        this.ancla = { f: Math.min(f + matriz.length - 1, this.visibles.length - 1),
                       c: Math.min(c + matriz[0].length - 1, this.columnas.length - 1) };
        const fin = this.ancla; this.ancla = { f, c }; this.cursor = fin;
        this._pintarSeleccionCeldas();
        toast(`${escritas} celdas pegadas ✅`);
      }
      return escritas;
    }

    borrarRango() {
      const r = this._rango();
      if (!r || !this.cfg.editable) return 0;
      let n = 0;
      for (let f = r.f0; f <= r.f1; f++) {
        for (let c = r.c0; c <= r.c1; c++) {
          const col = this.columnas[c];
          if (this._escribirCelda(this.visibles[f], col, col.tipo === 'numero' ? 0 : '')) n++;
        }
      }
      this.pintar();
      return n;
    }

    /** Copia los valores del rango sobre el área arrastrada (como Excel). */
    rellenar(destino) {
      const r = this._rango();
      if (!r || !destino || !this.cfg.editable) return 0;
      const altoOrigen = r.f1 - r.f0 + 1;
      const anchoOrigen = r.c1 - r.c0 + 1;
      let n = 0;
      for (let f = destino.f0; f <= destino.f1; f++) {
        for (let c = destino.c0; c <= destino.c1; c++) {
          if (f >= r.f0 && f <= r.f1 && c >= r.c0 && c <= r.c1) continue;
          const origen = this.visibles[r.f0 + ((f - r.f0) % altoOrigen + altoOrigen) % altoOrigen];
          const colOrigen = this.columnas[r.c0 + ((c - r.c0) % anchoOrigen + anchoOrigen) % anchoOrigen];
          const col = this.columnas[c];
          if (col.tipo !== colOrigen.tipo) continue;
          if (this._escribirCelda(this.visibles[f], col, this._valorCelda(origen, colOrigen))) n++;
        }
      }
      this.cursor = { f: destino.f1, c: destino.c1 };
      this.ancla = { f: Math.min(r.f0, destino.f0), c: Math.min(r.c0, destino.c0) };
      this.pintar();
      return n;
    }

    _conectarCeldas() {
      const coords = (el) => {
        const td = el.closest ? el.closest('td[data-col]') : null;
        return td ? { f: Number(td.dataset.fila), c: Number(td.dataset.col) } : null;
      };

      document.addEventListener('mousedown', (e) => {
        this._foco = this.raiz.contains(e.target);
      }, true);

      this.tbody.addEventListener('mousedown', (e) => {
        if (e.target.closest('button, input, select, .pt-entrada')) return;
        if (e.target.classList.contains('pt-arrastre')) {
          e.preventDefault();
          this.relleno = { previo: null };
          return;
        }
        const p = coords(e.target);
        if (!p) return;
        this.irACelda(p.f, p.c, { extender: e.shiftKey });
        this._arrastrando = !e.shiftKey;
      });

      this.tbody.addEventListener('mouseover', (e) => {
        const p = coords(e.target);
        if (!p) return;
        if (this.relleno) {
          const r = this._rango();
          // el relleno se extiende en una sola dirección
          const vertical = p.f < r.f0 || p.f > r.f1 || (p.c >= r.c0 && p.c <= r.c1);
          this.relleno.previo = vertical
            ? { f0: Math.min(r.f0, p.f), f1: Math.max(r.f1, p.f), c0: r.c0, c1: r.c1 }
            : { f0: r.f0, f1: r.f1, c0: Math.min(r.c0, p.c), c1: Math.max(r.c1, p.c) };
          this._pintarSeleccionCeldas();
        } else if (this._arrastrando && (e.buttons & 1)) {
          this.irACelda(p.f, p.c, { extender: true, desplazar: false });
        }
      });

      document.addEventListener('mouseup', () => {
        if (this.relleno) {
          const destino = this.relleno.previo;
          this.relleno = null;
          if (destino) {
            const n = this.rellenar(destino);
            if (n) toast(`${n} celdas rellenadas ✅`);
          } else {
            this._pintarSeleccionCeldas();
          }
        }
        this._arrastrando = false;
      });

      this.tbody.addEventListener('dblclick', (e) => {
        if (!e.target.classList.contains('pt-arrastre')) return;
        const r = this._rango();
        if (r) {
          const n = this.rellenar({ f0: r.f0, f1: this.visibles.length - 1, c0: r.c0, c1: r.c1 });
          if (n) toast(`${n} celdas rellenadas hasta el final ✅`);
        }
      });

      document.addEventListener('keydown', (e) => {
        if (!this._foco || !this.cursor) return;
        if (e.target.closest('.pt-entrada, input, select, textarea')) return;
        const mover = (df, dc) => {
          e.preventDefault();
          this.irACelda(this.cursor.f + df, this.cursor.c + dc, { extender: e.shiftKey });
        };
        switch (e.key) {
          case 'ArrowUp': return mover(-1, 0);
          case 'ArrowDown': return mover(1, 0);
          case 'ArrowLeft': return mover(0, -1);
          case 'ArrowRight': return mover(0, 1);
          case 'Home': return mover(0, -this.columnas.length);
          case 'End': return mover(0, this.columnas.length);
          case 'PageUp': return mover(-15, 0);
          case 'PageDown': return mover(15, 0);
          case 'Tab': return mover(0, e.shiftKey ? -1 : 1);
          case 'Enter': case 'F2': {
            e.preventDefault();
            const td = this._td(this.cursor.f, this.cursor.c);
            if (td && td.classList.contains('pt-editable')) this.editar(td);
            return;
          }
          case 'Escape':
            this.ancla = this.cursor; this._pintarSeleccionCeldas(); return;
          case 'Delete': case 'Backspace': {
            e.preventDefault();
            const n = this.borrarRango();
            if (n) toast(`${n} celdas borradas`);
            return;
          }
          default: break;
        }
        // escribir directamente reemplaza el contenido, como en Excel
        if (!e.ctrlKey && !e.metaKey && !e.altKey && e.key.length === 1) {
          const td = this._td(this.cursor.f, this.cursor.c);
          if (td && td.classList.contains('pt-editable')) {
            this.editar(td, { inicial: e.key });
            e.preventDefault();
          }
        }
      });

      const enFoco = () => this._foco && this.cursor &&
        !document.activeElement?.closest?.('.pt-entrada, input, select, textarea');

      document.addEventListener('copy', (e) => {
        if (!enFoco()) return;
        const texto = this.textoDelRango();
        if (!texto) return;
        e.preventDefault();
        e.clipboardData.setData('text/plain', texto);
      });
      document.addEventListener('cut', (e) => {
        if (!enFoco() || !this.cfg.editable) return;
        const texto = this.textoDelRango();
        if (!texto) return;
        e.preventDefault();
        e.clipboardData.setData('text/plain', texto);
        this.borrarRango();
      });
      document.addEventListener('paste', (e) => {
        if (!enFoco() || !this.cfg.editable) return;
        const texto = (e.clipboardData || global.clipboardData).getData('text');
        if (!texto) return;
        e.preventDefault();
        this.pegarTexto(texto);
      });
    }

    _filaDe(el) {
      const tr = el.closest('tr[data-indice]');
      return tr ? this.filas[Number(tr.dataset.indice)] : null;
    }

    // ------------------------------------------------------------- edición
    editar(td, { inicial = null } = {}) {
      if (td.querySelector('.pt-entrada')) return;
      if (td.dataset.fila !== undefined) {
        this.cursor = { f: Number(td.dataset.fila), c: Number(td.dataset.col) };
        this.ancla = { ...this.cursor };
      }
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
        if (inicial !== null) {   // al escribir una letra se busca la opción
          const op = col.opciones.find(o => normalizar(o).startsWith(normalizar(inicial)));
          if (op) entrada.value = op;
        }
      } else {
        entrada = document.createElement('input');
        entrada.type = 'text';          // sin las flechitas de <input type="number">
        if (col.tipo === 'numero') {
          entrada.inputMode = 'decimal';
          entrada.classList.add('pt-entrada--num');
        }
        entrada.value = col.tipo === 'numero' ? aNumero(valorOriginal) : (valorOriginal ?? '');
        if (inicial !== null) entrada.value = inicial;   // escribir reemplaza, como en Excel
      }
      entrada.className = 'pt-entrada';

      td.textContent = '';
      td.appendChild(entrada);
      this._pintarSeleccionCeldas();
      entrada.focus();
      if (entrada.select && inicial === null) entrada.select();
      if (inicial !== null && entrada.setSelectionRange) {
        try { entrada.setSelectionRange(entrada.value.length, entrada.value.length); } catch (e) { /* number input */ }
      }

      const posFila = [...this.tbody.rows].indexOf(td.parentElement);

      const cerrar = (guardar) => {
        if (!td.contains(entrada)) return;
        if (guardar) {
          const nuevo = col.tipo === 'numero' ? aNumero(entrada.value) : entrada.value;
          const anterior = col.tipo === 'numero' ? aNumero(valorOriginal) : (valorOriginal ?? '');
          if (nuevo !== anterior) this.setValor(fila, campo, nuevo);
        }
        this.pintar();
      };

      entrada.addEventListener('blur', () => cerrar(true));
      entrada.addEventListener('keydown', (e) => {
        /* Guarda y mueve el cursor. `seguirEditando` solo para Tab, que en
           Excel encadena la edición; con Enter se sale del modo edición. */
        const saltar = (dFila, dCol, seguirEditando = false) => {
          e.preventDefault();
          const destino = this.cursor
            ? { f: this.cursor.f + dFila, c: this.cursor.c + dCol }
            : null;
          cerrar(true);
          if (!destino) { this._enfocarCelda(posFila + dFila, campo, dCol); return; }
          this.irACelda(destino.f, destino.c);
          if (!seguirEditando) return;
          const td = this._td(this.cursor.f, this.cursor.c);
          if (td && td.classList.contains('pt-editable')) this.editar(td);
        };
        /* Como en Excel: las flechas cambian de celda salvo que se esté
           moviendo el cursor dentro de un texto que ya existía. */
        const enBorde = (haciaIzquierda) => {
          if (entrada.tagName !== 'INPUT') return true;
          if (inicial !== null) return true;               // valor recién escrito
          const pos = entrada.selectionStart;
          if (pos === null || pos === undefined) return true;
          return haciaIzquierda ? pos === 0 : pos === entrada.value.length;
        };
        if (e.key === 'Enter') saltar(e.shiftKey ? -1 : 1, 0);
        else if (e.key === 'Escape') { e.preventDefault(); cerrar(false); this._pintarSeleccionCeldas(); }
        else if (e.key === 'Tab') saltar(0, e.shiftKey ? -1 : 1, true);
        else if (e.key === 'ArrowLeft' && enBorde(true)) saltar(0, -1);
        else if (e.key === 'ArrowRight' && enBorde(false)) saltar(0, 1);
        else if (['ArrowUp', 'ArrowDown'].includes(e.key) && entrada.tagName === 'INPUT') {
          saltar(e.key === 'ArrowUp' ? -1 : 1, 0);
        }
      });
    }

    /** Guarda un valor y recalcula el total. El servidor decide si la fila pasa a manual. */
    setValor(fila, campo, valor) {
      fila[campo] = valor;
      if (this.cfg.recalcular) this.cfg.recalcular(fila, campo);
      if (MESES.includes(campo) && 'total' in fila) TablaPresupuesto.recalcularTotal(fila);
      this.marcarCambios();
    }

    _enfocarCelda(posFila, campo, dCol = 0) {
      const editables = this.columnas.filter(c => this.cfg.editable && c.editable !== false);
      let destino = campo;
      if (dCol) {
        const i = editables.findIndex(c => c.campo === campo) + dCol;
        if (i < 0 || i >= editables.length) { this._pintarSeleccionCeldas(); return; }
        destino = editables[i].campo;
      }
      const tr = this.tbody.rows[posFila];
      if (!tr) { this._pintarSeleccionCeldas(); return; }
      const td = tr.querySelector(`td[data-campo="${destino}"]`);
      if (td && td.classList.contains('pt-editable')) {
        if (td.dataset.fila !== undefined) {
          this.cursor = { f: Number(td.dataset.fila), c: Number(td.dataset.col) };
          this.ancla = { ...this.cursor };
        }
        if (td.scrollIntoView) td.scrollIntoView({ block: 'nearest', inline: 'nearest' });
        this.editar(td);
      } else {
        this._pintarSeleccionCeldas();
      }
    }

    // ----------------------------------------------------------- operaciones
    static recalcularTotal(fila) {
      fila.total = MESES.reduce((suma, m) => suma + aNumero(fila[m]), 0);
      return fila;
    }

    /** Fila nueva escrita a mano: el sistema no la recalcula. */
    static filaManual(base = {}) {
      return Object.assign({ factor: 1, historico: {}, excluir_de: [], cuenta: '' }, base,
                           { id: null, origen: 'manual', clave: '' });
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
      this.marcarCambios();
      return filas.length;
    }

    /** Marca las filas seleccionadas para que el servidor vuelva a calcularlas. */
    marcarParaRecalcular() {
      return this.aplicarASeleccionadas(fila => { fila._recalcular = true; }, { avisar: true });
    }

    /** Valores que hereda una fila nueva (p. ej. el concepto de la pantalla). */
    _baseFilaNueva() {
      const base = Object.assign({}, this.cfg.valoresNuevos || {});
      if (this.columnas.some(c => c.campo === 'concepto') && !base.concepto) {
        // el concepto más usado en la tabla; si no hay filas, el de la configuración
        const cuenta = new Map();
        this.filas.forEach(f => {
          const v = String(f.concepto || '').trim();
          if (v) cuenta.set(v, (cuenta.get(v) || 0) + 1);
        });
        const comun = [...cuenta.entries()].sort((a, b) => b[1] - a[1])[0];
        base.concepto = comun ? comun[0] : (this.cfg.conceptoNuevo || '');
      }
      return base;
    }

    agregarFila(base = {}) {
      const fila = {};
      this.columnas.forEach(c => { fila[c.campo] = c.tipo === 'numero' ? 0 : ''; });
      Object.assign(fila, TablaPresupuesto.filaManual(Object.assign(this._baseFilaNueva(), base)));
      this.filas.push(fila);
      this._refrescarOpcionesFiltro();
      this.filaActiva = fila;
      this.pintar();

      // si algún filtro la esconde, se limpian para que se vea
      if (!this.visibles.includes(fila)) {
        this.limpiarFiltros();
        toast('Se limpiaron los filtros para mostrar la fila nueva', 'warning');
      }
      this.marcarCambios();
      this._irAFila(fila);
      return fila;
    }

    limpiarFiltros() {
      Object.values(this.filtros).forEach(ms => { ms.valores.clear(); ms.actualizarTexto(); ms.pintarOpciones(); });
      const buscador = this.raiz.querySelector('.pt-buscador input');
      if (buscador) buscador.value = '';
      this.textoBusqueda = '';
      this.pintar();
    }

    /** Lleva el scroll a una fila, la resalta y deja el cursor en su primera celda editable. */
    _irAFila(fila) {
      const f = this.visibles.indexOf(fila);
      if (f < 0) return;
      const primera = this.columnas.findIndex(c => this.cfg.editable && c.editable !== false);
      this.irACelda(f, primera < 0 ? 0 : primera);
      const tr = this.tbody.querySelector(`td[data-fila="${f}"]`)?.parentElement;
      if (tr) {
        tr.classList.add('pt-destello');
        if (tr.scrollIntoView) tr.scrollIntoView({ block: 'center', behavior: 'smooth' });
        setTimeout(() => tr.classList.remove('pt-destello'), 2000);
      }
    }

    duplicar(fila) {
      const copia = TablaPresupuesto.filaManual(fila);
      MESES.forEach(m => { if (m in copia) copia[m] = 0; });
      copia.total = 0;
      delete copia._recalcular;
      this.filas.splice(this.filas.indexOf(fila) + 1, 0, copia);
      this.filaActiva = copia;
      this.pintar();
      this.marcarCambios();
      this._irAFila(copia);
      toast('Fila duplicada 📑');
    }

    eliminar(fila) {
      this.filas.splice(this.filas.indexOf(fila), 1);
      this.seleccion.delete(fila);
      this.pintar();
      this.marcarCambios();
      toast('Fila eliminada (se aplica al guardar) ❌', 'error');
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
      toast('Fila pegada ✅');
      return fila;
    }

    /**
     * Reparte cada fila seleccionada en varias según los porcentajes dados.
     * reparto: [{porcentaje, centro, area}] — los de porcentaje 0 se ignoran.
     * porFactor: true → cada copia guarda su porcentaje en `factor` y sigue
     *            siendo calculada por el sistema (conceptos base).
     */
    distribuir(reparto, { porFactor = false } = {}) {
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
          const copia = Object.assign({}, fila, { id: null, clave: '' });
          delete copia._recalcular;
          const parte = r.porcentaje / 100;
          MESES.forEach(m => { copia[m] = Math.round(aNumero(fila[m]) * parte * 100) / 100; });
          TablaPresupuesto.recalcularTotal(copia);
          if (porFactor && fila.origen === 'sistema') {
            copia.factor = (aNumero(fila.factor) || 1) * parte;
          } else {
            copia.origen = 'manual';
          }
          if (r.centro) copia.centro = r.centro;
          if (r.area) copia.area = r.area;
          nuevas.push(copia);
        });
      });

      this.filas = this.filas.filter(f => !this.seleccion.has(f)).concat(nuevas);
      this.seleccion.clear();
      this._refrescarOpcionesFiltro();
      this.pintar();
      this.marcarCambios();
      toast(`${seleccionadas.length} fila(s) reemplazadas por ${nuevas.length}. Recuerda guardar.`);
      return nuevas.length;
    }

    // --------------------------------------------------------- exportación
    /** CSV con BOM y separador ';' → Excel lo abre directo. */
    exportar(nombre = this.cfg.nombreArchivo) {
      const columnas = this.columnas.filter(c => c.tipo !== 'origen');
      const cabecera = ['Origen'].concat(columnas.map(c => c.titulo));
      const filas = this.visibles.map(f => [f.origen === 'sistema' ? 'Calculado' : 'Manual'].concat(
        columnas.map(c => c.tipo === 'numero' ? String(aNumero(f[c.campo])).replace('.', ',') : (f[c.campo] ?? ''))
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
    /** Envía todas las filas; el servidor responde con la tabla ya recalculada. */
    async guardar(url, boton) {
      return conSpinner(boton, async () => {
        try {
          const r = await enviarJSON(url, { filas: this.datos() });
          if (Array.isArray(r.data)) this.setDatos(r.data);
          toast(r.msg || 'Datos guardados ✅', 'success', r.recalculados && r.recalculados.length ? 6000 : 3500);
          return r;
        } catch (e) {
          console.error(e);
          toast('Error al guardar ❌ ' + e.message, 'error', 6000);
          return null;
        }
      });
    }
  }

  // ------------------------------------------------------ cableado genérico
  /**
   * Conecta los botones de la barra superior a partir de data-rol.
   *
   * data-rol admitidos: inicio | consolidado | guardar | cargar-base | borrar |
   *                     agregar | pegar | exportar | recalcular | distribuir
   * Si el botón tiene data-confirmar="texto", se pide confirmación antes.
   */
  function conectarBarra(tabla, urls = {}, extra = {}) {
    const boton = (rol) => document.querySelector(`[data-rol="${rol}"]`);
    const confirmar = (b) => {
      if (tabla.sinGuardar && b.dataset.descarta !== undefined &&
          !confirm('Hay cambios sin guardar que se perderán. ¿Continuar?')) return false;
      return !b.dataset.confirmar || confirm(b.dataset.confirmar);
    };
    const al = (rol, fn) => {
      const b = boton(rol);
      if (b) b.addEventListener('click', () => { if (confirmar(b)) fn(b); });
    };
    const navegar = (rol, url) => {
      const b = boton(rol);
      if (b && url) b.addEventListener('click', () => { window.location.href = url; });
    };

    navegar('inicio', urls.inicio);
    navegar('consolidado', urls.consolidado);

    /** Acción de servidor que devuelve la tabla ya actualizada. */
    const accionServidor = (url) => (b) => conSpinner(b, async () => {
      try {
        const r = await pedir(url, { method: 'POST' });
        if (Array.isArray(r.data)) tabla.setDatos(r.data); else await tabla.cargar();
        toast(r.msg || 'Listo ✅', 'success', 6000);
      } catch (e) { console.error(e); toast('Error ❌ ' + e.message, 'error', 6000); }
    });

    if (urls.guardar) al('guardar', (b) => tabla.guardar(urls.guardar, b));
    if (urls.cargarBase) al('cargar-base', accionServidor(urls.cargarBase));
    if (urls.borrar) al('borrar', accionServidor(urls.borrar));

    al('agregar',  extra.agregar || (() => { tabla.agregarFila(); toast('Fila agregada ✅'); }));
    al('pegar',    () => tabla.pegarDelPortapapeles());
    al('exportar', () => tabla.exportar());
    if (urls.guardar) {
      al('recalcular', (b) => {
        if (!tabla.marcarParaRecalcular()) return;
        tabla.guardar(urls.guardar, b);
      });
    }
    if (extra.distribuir) al('distribuir', extra.distribuir);

    global.addEventListener('beforeunload', (e) => {
      if (tabla.sinGuardar) { e.preventDefault(); e.returnValue = ''; }
    });
  }

  /** Lee un valor serializado con {{ variable|json_script:"id" }}. */
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

  /**
   * <details data-recordar="clave"> recuerda si quedó abierto u oculto.
   * Se llama sola al cargar la página.
   */
  function recordarSecciones(raiz = document) {
    raiz.querySelectorAll('details[data-recordar]').forEach(det => {
      const clave = 'pt-seccion:' + det.dataset.recordar;
      try {
        const guardado = localStorage.getItem(clave);
        if (guardado !== null) det.open = guardado === '1';
      } catch (e) { /* sin almacenamiento: se usa el estado por defecto */ }
      det.addEventListener('toggle', () => {
        try { localStorage.setItem(clave, det.open ? '1' : '0'); } catch (e) { /* ignorar */ }
      });
    });
  }
  document.addEventListener('DOMContentLoaded', () => recordarSecciones());

  global.PT = {
    MESES, Columnas, TablaPresupuesto, MultiSelect,
    aNumero, formatearNumero, toast, pedir, enviarJSON, conSpinner,
    conectarBarra, listaJSON, leerDistribucion, recordarSecciones
  };
})(window);
