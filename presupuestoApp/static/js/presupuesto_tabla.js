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
 *  - Guardado automático (como los presupuestos generales): cada cambio se
 *    encola con envio_seguro.js, se reintenta solo si el servidor no responde
 *    y queda copia en el navegador hasta que el servidor lo confirma.
 *  - Filtros tipo Excel en la cabecera de cada columna (▾) + búsqueda general.
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

  /** ¿El texto es un número válido? (vacío = 0). Acepta 1234,5 · 1.234.567,89 · -500 · $ 1.000 */
  function esNumeroValido(valor) {
    if (typeof valor === 'number') return isFinite(valor);
    const t = String(valor ?? '').trim().replace(/[$\s]/g, '');
    return t === '' || /^-?\d+([.,]\d+)*$/.test(t);
  }

  /** Identificador de una fila creada en el navegador (el servidor devuelve su id). */
  function nuevoUid() {
    if (global.crypto && global.crypto.randomUUID) return global.crypto.randomUUID();
    return 'u' + Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
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
      throw Object.assign(new Error(mensaje), { status: resp.status });
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

    /**
   * Pide que el usuario escriba una palabra para confirmar una acción delicada.
   * Devuelve true solo si la escribe bien (sin importar mayúsculas).
   */
  function confirmarEscrito(mensaje, palabra = 'CONFIRMAR') {
    palabra = String(palabra).trim().toUpperCase();
    const escrito = prompt(`${mensaje}\n\nEscriba ${palabra} para confirmar:`);
    if (escrito === null) return false;                       // canceló
    if (escrito.trim().toUpperCase() !== palabra) {
      toast('No se realizó la acción: el texto de confirmación no coincide ⚠️', 'warning', 5000);
      return false;
    }
    return true;
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
     *  - codcosto        mostrar la columna "Cód. costo" (solo lectura: sale del área)
     */
    estandar({ cedula = true, cargo = true, base = null, opciones = {}, origen = true, tipo = false,
               codcosto = false } = {}) {
      const cols = [];
      if (origen) cols.push({ campo: 'origen', titulo: 'Origen', tipo: 'origen', editable: false });
      if (tipo) cols.push({ campo: 'tipo_nombre', titulo: 'Concepto de nómina', editable: false });
      if (cedula) cols.push({ campo: 'cedula', titulo: 'Cédula' });
      cols.push({ campo: 'nombre', titulo: 'Nombre' });
      cols.push({ campo: 'centro', titulo: 'Centro', tipo: opciones.centros ? 'select' : 'texto', opciones: opciones.centros });
      cols.push({ campo: 'area', titulo: 'Área', tipo: opciones.areas ? 'select' : 'texto', opciones: opciones.areas });
      if (codcosto) cols.push({ campo: 'codcosto', titulo: 'Cód. costo', editable: false });
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
     *  - filtros        columnas con filtro tipo Excel en la cabecera (null = todas las de texto)
     *  - buscador       caja de búsqueda global (por defecto true)
     *  - camposTotal    columnas que se suman en el pie (por defecto meses + total)
     *  - recalcular     fn(fila, campo) ejecutada tras cada edición (además del total)
     *  - alCambiar      fn(sinGuardar) cuando cambia el estado de "cambios sin guardar"
     *  - urlGuardar     endpoint POST del guardado automático (sin él no se guarda solo)
     *  - claveRespaldo  clave de la copia en el navegador (por usuario y tabla)
     *  - indicador      elemento donde se muestra "Guardando… / Todo guardado"
     */
    constructor(cfg) {
      this.cfg = Object.assign({
        seleccionable: true,
        acciones: ['duplicar', 'eliminar'],
        editable: true,
        filtros: null,
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
      // Filtros tipo Excel: campo -> Set de valores permitidos (solo los activos)
      this.filtros = {};
      this.camposFiltro = this.cfg.filtros ||
        this.columnas.filter(c => c.tipo !== 'numero').map(c => c.campo);
      this.textoBusqueda = '';
      // Filas editadas o agregadas con un filtro activo: siguen a la vista
      // hasta que se cambie el filtro (como en Excel).
      this.fijadas = new WeakSet();
      this.sinGuardar = false;
      // Hasta que los datos no lleguen del servidor no se edita ni se guarda:
      // una tabla vacía por una carga fallida NO puede reemplazar lo guardado.
      this.datosCargados = false;
      this._timerGuardado = null;
      this._respuestaPendiente = null;
      this._avisoReintento = false;
      // Deshacer / rehacer: fotos de la tabla antes de cada cambio
      this._pilaDeshacer = [];
      this._pilaRehacer = [];
      this._fotoTomada = false;
      this._idPorUid = {};          // id que el servidor dio a cada fila nueva
      // Selección de celdas tipo Excel: índices sobre `visibles` y `columnas`
      this.cursor = null;          // {f, c}
      this.ancla = null;           // esquina fija del rango
      this.relleno = null;         // arrastre del cuadrito de relleno
      this._foco = false;

      this.raiz = typeof this.cfg.montaje === 'string'
        ? document.querySelector(this.cfg.montaje) : this.cfg.montaje;

      this.cola = (this.cfg.editable && this.cfg.urlGuardar && global.EnvioSeguro)
        ? global.EnvioSeguro.cola({
            clave: this.cfg.claveRespaldo || ('nomina|' + this.cfg.urlGuardar),
            url: this.cfg.urlGuardar,
            esExito: (j) => j && j.status === 'ok',
            onEstado: (estado, info) => this._alEstadoCola(estado, info),
          })
        : null;

      this._construirEsqueleto();
      this._conectarEventos();
      if (this.cfg.urlDatos) this.cargar();
      else this.datosCargados = true;
    }

    /** Se puede editar: tabla editable y datos ya cargados del servidor. */
    _puedeEditar() { return !!this.cfg.editable && this.datosCargados; }

    // ═════════════════════════════════════════════════════════════════
    //  Deshacer / rehacer (botones ↩️ ↪️, Ctrl+Z y Ctrl+Y)
    //  Antes de cada cambio se guarda una foto de la tabla. Todo lo que se
    //  hace en una misma operación (pegar un bloque, rellenar, Supr sobre un
    //  rango, eliminar una fila…) es UN solo paso de deshacer.
    //  Deshacer también se guarda solo (autoguardado).
    // ═════════════════════════════════════════════════════════════════
    _foto() { return JSON.stringify(this.filas); }

    /** Llamar ANTES de modificar la tabla. */
    antesDeCambiar() {
      if (this._fotoTomada || !this._puedeEditar()) return;
      this._fotoTomada = true;
      this._pilaDeshacer.push(this._foto());
      if (this._pilaDeshacer.length > 50) this._pilaDeshacer.shift();
      this._pilaRehacer.length = 0;
      queueMicrotask(() => { this._fotoTomada = false; this._pintarHistorial(); });
    }

    puedeDeshacer() { return this._puedeEditar() && this._pilaDeshacer.length > 0; }
    puedeRehacer() { return this._puedeEditar() && this._pilaRehacer.length > 0; }
    deshacer() { if (this._restaurar(this._pilaDeshacer, this._pilaRehacer)) toast('Cambio deshecho ↩️'); }
    rehacer() { if (this._restaurar(this._pilaRehacer, this._pilaDeshacer)) toast('Cambio rehecho ↪️'); }

    _limpiarHistorial() {
      this._pilaDeshacer.length = 0;
      this._pilaRehacer.length = 0;
      this._pintarHistorial();
    }

    _pintarHistorial() {
      const b = this.cfg.botonesHistorial || {};
      if (b.deshacer) b.deshacer.disabled = !this.puedeDeshacer();
      if (b.rehacer) b.rehacer.disabled = !this.puedeRehacer();
    }

    _restaurar(desde, hacia) {
      if (!desde.length || !this._puedeEditar()) return false;
      const editor = this.tbody.querySelector('.pt-entrada');
      if (editor) editor.blur();                      // cierra (y guarda) la celda en edición
      const clave = (f) => String(f._uid || f.id || '');
      const antes = new Map(this.filas.map(f => [clave(f), JSON.stringify(f)]));
      const origenAntes = new Map(this.filas.map(f => [clave(f), f.origen]));
      const ids = new Set(this.filas.filter(f => f.id).map(f => String(f.id)));
      hacia.push(this._foto());
      this.filas = JSON.parse(desde.pop());
      this.fijadas = new WeakSet();
      this.filas.forEach(f => {
        if (!f.id && f._uid && this._idPorUid[f._uid]) f.id = this._idPorUid[f._uid];
        if (f.id && !ids.has(String(f.id))) {
          // Fila que se había eliminado: vuelve como fila nueva; el servidor
          // la recrea con su origen, su clave y su histórico (_restaurada).
          f.id = null;
          f._uid = f._uid || nuevoUid();
          f._restaurada = true;
        } else if (f.origen === 'sistema' && origenAntes.get(clave(f)) === 'manual') {
          // La edición la había vuelto manual: al deshacer vuelve a ser calculada.
          f._recalcular = true;
        }
        if (antes.get(clave(f)) !== JSON.stringify(f)) this.fijadas.add(f);   // lo deshecho queda a la vista
      });
      this.seleccion.clear();
      this.filaActiva = null;
      this.pintar();
      this.marcarCambios();
      this._pintarHistorial();
      return true;
    }

    // ------------------------------------------------------ cambios pendientes
    /** Hubo un cambio: se programa el guardado automático. */
    marcarCambios(valor = true) {
      if (this.sinGuardar !== valor) {
        this.sinGuardar = valor;
        if (this.cfg.alCambiar) this.cfg.alCambiar(valor);
      }
      if (valor) this._programarGuardado();
    }

    // ═════════════════════════════════════════════════════════════════
    //  Guardado automático (igual que los presupuestos generales)
    //  · 800 ms después del último cambio se encola la tabla completa.
    //  · La cola reintenta sola si el servidor no responde (despliegue,
    //    corte de red) y guarda copia en el navegador hasta confirmarlo.
    //  · Si el servidor rechaza los datos (4xx) se avisa y no se insiste.
    // ═════════════════════════════════════════════════════════════════
    _estadoGuardado(clase, texto, titulo = '') {
      const el = this.cfg.indicador;
      if (!el) return;
      el.className = 'pt-autoguardado pt-autoguardado--' + clase;
      el.hidden = false;
      const t = el.querySelector('[data-rol="estado-texto"]') || el;
      t.textContent = texto;
      el.title = titulo;
    }

    _programarGuardado() {
      if (!this.cola || !this._puedeEditar()) return;
      this._estadoGuardado('pendiente', 'Cambios sin guardar…');
      clearTimeout(this._timerGuardado);
      this._timerGuardado = setTimeout(() => { this._timerGuardado = null; this._encolar(); }, 800);
    }

    /** La tabla completa tal como se envía (las filas nuevas llevan su _uid). */
    _payload() {
      return {
        filas: this.filas.map(f => {
          if (!f.id && !f._uid) f._uid = nuevoUid();
          return Object.assign({}, f);
        })
      };
    }

    _encolar() {
      if (!this.cola || !this._puedeEditar()) return;
      this.cola.poner(this._payload());
    }

    hayPendientes() { return !!this._timerGuardado || !!(this.cola && this.cola.hayPendientes()); }

    /**
     * Envía ya lo pendiente y espera a que el servidor lo confirme.
     * Devuelve true si todo quedó guardado (o no había nada pendiente).
     */
    async guardarAhora(maxEsperaMs = 60000) {
      if (!this.cola) return true;
      if (this._timerGuardado) {
        clearTimeout(this._timerGuardado);
        this._timerGuardado = null;
        this._encolar();
      }
      try {
        await this.cola.vaciar(maxEsperaMs);
        return true;
      } catch (e) {
        toast(e.message + ' ❌', 'error', 7000);
        return false;
      }
    }

    _alEstadoCola(estado, info) {
      if (estado === 'enviando') {
        this._estadoGuardado('guardando', 'Guardando…');
      } else if (estado === 'enviado') {
        // Las filas nuevas reciben su id aunque ya haya otro envío en camino:
        // así el siguiente envío no las vuelve a crear.
        const resp = info.respuesta || {};
        // p. ej. "Cédula / nombre actualizado en todos los conceptos"
        if (resp.aviso) toast(resp.aviso, resp.resumen && resp.resumen.personas_corregidas ? 'success' : 'warning', 8000);
        const nuevos = resp.nuevos || {};
        Object.assign(this._idPorUid, nuevos);
        this.filas.forEach(f => {
          if (!f.id && f._uid && nuevos[f._uid]) { f.id = nuevos[f._uid]; delete f._restaurada; }
        });
      } else if (estado === 'guardado') {
        const r = info.respuesta || {};
        if (this._avisoReintento) {
          toast('Conexión recuperada: los cambios se guardaron ✅', 'success', 5000);
          this._avisoReintento = false;
        }
        if (this._timerGuardado) return;                // hay cambios más nuevos esperando
        this.sinGuardar = false;
        if (this.cfg.alCambiar) this.cfg.alCambiar(false);
        const recalc = (r.recalculados || []).length ? 'Actualizado también: ' + r.recalculados.join(', ') : '';
        this._estadoGuardado('guardado', 'Todo guardado', [r.msg, recalc].filter(Boolean).join('\n'));
        if (Array.isArray(r.data)) {
          // Los valores que recalculó el servidor (filas que pasaron a manual,
          // histórico ajustado, conceptos dependientes…) se ven sin recargar.
          if (this.tbody.querySelector('.pt-entrada')) this._respuestaPendiente = r.data;
          else this._aplicarDatosServidor(r.data);
        }
      } else if (estado === 'reintentando') {
        const seg = Math.round(info.espera / 1000);
        this._estadoGuardado('guardando', info.conRespaldo
          ? `Servidor no disponible · reintento en ${seg} s · cambios a salvo en este navegador`
          : `Servidor no disponible · reintento en ${seg} s · no cierre esta página`, info.error.message);
        if (!this._avisoReintento) {
          this._avisoReintento = true;
          toast(`${info.error.message}. Los cambios quedan en cola y se guardarán solos cuando el servidor responda ⏳`,
                'warning', 8000);
        }
      } else if (estado === 'error') {
        this._estadoGuardado('error', 'Error al guardar ❌', info.error.message);
        toast('No se pudo guardar: ' + info.error.message + ' ❌', 'error', 8000);
      }
    }

    /** Firma del contenido de una fila (para reconocerla sin id). */
    static firma(f) {
      return [f.cedula, f.nombre, f.centro, f.area, f.cargo, f.concepto].map(v => String(v ?? '').trim())
        .concat(MESES.map(m => Math.round(aNumero(f[m])))).join('|');
    }

    /**
     * Pone en la tabla lo que devolvió el servidor SIN reemplazar los objetos
     * de las filas: se conservan la selección, el cursor, el orden en pantalla
     * y las filas fijadas por el filtro.
     */
    _aplicarDatosServidor(data) {
      this._respuestaPendiente = null;
      const porId = new Map(data.map(d => [String(d.id), d]));
      const usados = new Set();
      const sinId = [];
      const resultado = [];
      this.filas.forEach(f => {
        if (f.id === null || f.id === undefined || f.id === '') { sinId.push(f); resultado.push(f); return; }
        const s = porId.get(String(f.id));
        if (!s) { this.seleccion.delete(f); return; }   // ya no existe en el servidor
        delete f._recalcular;
        Object.assign(f, s);
        usados.add(String(f.id));
        resultado.push(f);
      });
      // Filas nuevas a las que no les llegó el id: se reconocen por su contenido.
      sinId.forEach(f => {
        const s = data.find(d => !usados.has(String(d.id)) &&
                                 TablaPresupuesto.firma(d) === TablaPresupuesto.firma(f));
        if (s) { Object.assign(f, s); usados.add(String(s.id)); }
      });
      data.forEach(d => { if (!usados.has(String(d.id))) resultado.push(Object.assign({}, d)); });
      this.filas = resultado;
      this.pintar();
    }

    /** Copia de una sesión anterior que no alcanzó a llegar al servidor. */
    _revisarRespaldo() {
      if (!this.cola || !this._puedeEditar() || this.cola.hayPendientes()) return;
      const clave = this.cfg.claveRespaldo || ('nomina|' + this.cfg.urlGuardar);
      const respaldo = global.EnvioSeguro.respaldo(clave);
      const filas = respaldo && respaldo.datos && respaldo.datos.filas;
      if (!Array.isArray(filas)) return;
      const firmaTabla = (lista) => JSON.stringify(lista.map(f => [f.id || '', TablaPresupuesto.firma(f)]));
      if (firmaTabla(filas) === firmaTabla(this.filas)) { global.EnvioSeguro.descartar(clave); return; }
      const cuando = new Date(respaldo.ts).toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' });
      const recuperar = confirm(
        `Hay cambios de esta tabla que no alcanzaron a guardarse en el servidor (${cuando}, ${filas.length} filas).\n\n` +
        'Aceptar: recuperarlos y guardarlos ahora.\n' +
        `Cancelar: descartarlos y quedarse con lo que hay en el servidor (${this.filas.length} filas).`);
      if (!recuperar) {
        global.EnvioSeguro.descartar(clave);
        toast('Se descartaron los cambios sin guardar; quedó lo del servidor', 'success', 4000);
        return;
      }
      this.filas = filas.map(f => Object.assign({}, f));
      this.seleccion.clear();
      this._limpiarHistorial();
      this.pintar();
      this.marcarCambios();
      this.guardarAhora();
      toast('Cambios recuperados; guardando en el servidor…', 'success', 4000);
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
        caja.className = 'pt-buscador';
        caja.innerHTML = '<input type="search" placeholder="🔎 Buscar en toda la tabla…" aria-label="Buscar en toda la tabla">';
        const input = caja.querySelector('input');
        let t = null;
        input.addEventListener('input', () => {
          clearTimeout(t);
          t = setTimeout(() => { this.textoBusqueda = normalizar(input.value).trim(); this._cambioDeFiltros(); }, 200);
        });
        input.addEventListener('keydown', (e) => {
          if (e.key === 'Escape') { input.value = ''; clearTimeout(t); this.textoBusqueda = ''; this._cambioDeFiltros(); }
        });
        this.zonaFiltros.appendChild(caja);
      }

      // "Filtrado: N de M filas · Quitar filtros"
      this.estadoFiltro = document.createElement('span');
      this.estadoFiltro.className = 'pt-estado-filtro';
      this.zonaFiltros.appendChild(this.estadoFiltro);

      this.contador = document.createElement('span');
      this.contador.className = 'pt-contador';
      this.zonaFiltros.appendChild(this.contador);

      // El estado del guardado automático va junto a la búsqueda, siempre a la vista.
      if (this.cfg.indicador) this.zonaFiltros.insertBefore(this.cfg.indicador, this.contador);

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
        const filtro = this.camposFiltro.includes(col.campo)
          ? `<button type="button" class="pt-filtro-btn" data-filtro="${col.campo}" title="Filtrar ${escapar(col.titulo)}" aria-label="Filtrar ${escapar(col.titulo)}">▾</button>`
          : '';
        return `<th class="${clase}" data-campo="${col.campo}"><span class="pt-th"><span class="pt-th__texto">${escapar(col.titulo)}</span><span class="pt-orden"></span>${filtro}</span></th>`;
      }).join('');
      this.thead.innerHTML = `<tr>${th}</tr>`;
    }

    // ═════════════════════════════════════════════════════════════════
    //  Filtros tipo Excel (botón ▾ en la cabecera de cada columna)
    //  Los valores de cada lista dependen de los demás filtros activos
    //  (en cascada, como Excel). Las operaciones (editar, pegar, borrar,
    //  rellenar, marcar todo) solo tocan las filas visibles.
    // ═════════════════════════════════════════════════════════════════
    _valorFiltro(fila, campo) {
      if (campo === 'origen') return fila.origen === 'sistema' ? 'Calculado' : 'Manual';
      return String(fila[campo] ?? '').trim();
    }

    hayFiltro() { return !!this.textoBusqueda || Object.keys(this.filtros).length > 0; }

    _pasaFiltros(fila, excepto = null) {
      for (const campo in this.filtros) {
        if (campo !== excepto && !this.filtros[campo].has(this._valorFiltro(fila, campo))) return false;
      }
      if (this.textoBusqueda) {
        const texto = normalizar(this.columnas.map(c =>
          c.tipo === 'origen' ? this._valorFiltro(fila, 'origen') : fila[c.campo]).join(' | '));
        if (!this.textoBusqueda.split(/\s+/).every(p => texto.includes(p))) return false;
      }
      return true;
    }

    /** Al cambiar un filtro se vuelve a evaluar todo (las filas fijadas se sueltan). */
    _cambioDeFiltros() {
      this.fijadas = new WeakSet();
      this.cursor = null;
      this.ancla = null;
      this.pintar();
      if (this.visibles.length) this.irACelda(0, 0, { desplazar: false });
    }

    limpiarFiltros() {
      this.filtros = {};
      const buscador = this.raiz.querySelector('.pt-buscador input');
      if (buscador) buscador.value = '';
      this.textoBusqueda = '';
      this._cerrarPanelFiltro();
      this._cambioDeFiltros();
    }

    _cerrarPanelFiltro() {
      if (this._panelFiltro) { this._panelFiltro.remove(); this._panelFiltro = null; }
    }

    _abrirPanelFiltro(campo, boton) {
      this._cerrarPanelFiltro();
      const col = this.columnas.find(c => c.campo === campo);
      const conteo = new Map();
      this.filas.forEach(f => {
        if (!this._pasaFiltros(f, campo)) return;
        const v = this._valorFiltro(f, campo);
        conteo.set(v, (conteo.get(v) || 0) + 1);
      });
      const valores = [...conteo.keys()].sort((a, b) => a.localeCompare(b, 'es', { numeric: true }));
      const activos = this.filtros[campo];

      const panel = document.createElement('div');
      panel.className = 'pt-fpanel';
      panel.dataset.campo = campo;
      panel.innerHTML = `
        <div class="pt-fpanel__titulo">${escapar(col ? col.titulo : campo)}</div>
        <div class="pt-fpanel__orden">
          <button type="button" data-orden="1">↑ Ordenar A → Z</button>
          <button type="button" data-orden="-1">↓ Ordenar Z → A</button>
        </div>
        <input type="search" class="pt-fpanel__buscar" placeholder="Buscar…" autocomplete="off">
        <label class="pt-fpanel__op pt-fpanel__todos"><input type="checkbox"> <span>(Seleccionar todo)</span></label>
        <div class="pt-fpanel__lista">${valores.map(v => `
          <label class="pt-fpanel__op" data-texto="${escapar(normalizar(v))}">
            <input type="checkbox" value="${escapar(v)}" ${!activos || activos.has(v) ? 'checked' : ''}>
            <span>${escapar(v || '(Vacías)')}</span><small>${conteo.get(v)}</small>
          </label>`).join('') || '<div class="pt-fpanel__vacio">Sin valores</div>'}</div>
        <div class="pt-fpanel__pie">
          <button type="button" data-accion="quitar" ${activos ? '' : 'disabled'}>Quitar filtro</button>
          <span class="pt-espaciador"></span>
          <button type="button" data-accion="cancelar">Cancelar</button>
          <button type="button" data-accion="aceptar" class="pt-fpanel__aceptar">Aceptar</button>
        </div>`;
      document.body.appendChild(panel);
      this._panelFiltro = panel;
      const r = boton.getBoundingClientRect();
      panel.style.left = Math.max(8, Math.min(r.left, global.innerWidth - panel.offsetWidth - 8)) + 'px';
      panel.style.top = Math.max(8, Math.min(r.bottom + 4, global.innerHeight - panel.offsetHeight - 8)) + 'px';

      const buscar = panel.querySelector('.pt-fpanel__buscar');
      const todos = panel.querySelector('.pt-fpanel__todos input');
      const opciones = [...panel.querySelectorAll('.pt-fpanel__lista .pt-fpanel__op')];
      const visibles = () => opciones.filter(o => o.style.display !== 'none');
      const sincronizar = () => {
        const vis = visibles();
        const marcadas = vis.filter(o => o.querySelector('input').checked).length;
        todos.checked = vis.length > 0 && marcadas === vis.length;
        todos.indeterminate = marcadas > 0 && marcadas < vis.length;
      };
      buscar.addEventListener('input', () => {
        const q = normalizar(buscar.value).trim();
        // Como Excel: al buscar quedan marcados solo los resultados.
        opciones.forEach(o => {
          const coincide = !q || o.dataset.texto.includes(q);
          o.style.display = coincide ? '' : 'none';
          if (q) o.querySelector('input').checked = coincide;
        });
        sincronizar();
      });
      todos.addEventListener('change', () => {
        visibles().forEach(o => { o.querySelector('input').checked = todos.checked; });
        sincronizar();
      });
      panel.querySelector('.pt-fpanel__lista').addEventListener('change', sincronizar);

      const aceptar = () => {
        const elegidos = (buscar.value.trim() ? visibles() : opciones)
          .filter(o => o.querySelector('input').checked).map(o => o.querySelector('input').value);
        if (!elegidos.length) { toast('Seleccione al menos un valor ⚠️', 'warning'); return; }
        if (elegidos.length === valores.length && !buscar.value.trim()) delete this.filtros[campo];
        else this.filtros[campo] = new Set(elegidos);
        this._cerrarPanelFiltro();
        this._cambioDeFiltros();
      };
      panel.addEventListener('click', (e) => {
        const b = e.target.closest('button');
        if (!b) return;
        if (b.dataset.orden) {
          this.orden = { campo, dir: Number(b.dataset.orden) };
          this._cerrarPanelFiltro();
          this.pintar();
        } else if (b.dataset.accion === 'aceptar') aceptar();
        else if (b.dataset.accion === 'cancelar') this._cerrarPanelFiltro();
        else if (b.dataset.accion === 'quitar') {
          delete this.filtros[campo];
          this._cerrarPanelFiltro();
          this._cambioDeFiltros();
        }
      });
      panel.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); aceptar(); }
        if (e.key === 'Escape') { e.preventDefault(); this._cerrarPanelFiltro(); }
      });
      sincronizar();
      buscar.focus();
    }

    // -------------------------------------------------------------- datos
    /**
     * Trae las filas del servidor. Si no responde (p. ej. se está publicando
     * una versión nueva) reintenta solo; mientras tanto la tabla no se edita.
     */
    async cargar() {
      const esperas = [1000, 2000, 4000, 8000, 15000, 30000];
      for (let intento = 0; ; intento++) {
        try {
          const respuesta = await pedir(this.cfg.urlDatos, { cache: 'no-store' });
          const primeraVez = !this.datosCargados;
          this.datosCargados = true;
          this.setDatos(Array.isArray(respuesta) ? respuesta : (respuesta.data || []));
          if (this.cola) this._estadoGuardado('guardado', 'Todo guardado');
          if (primeraVez) this._revisarRespaldo();
          return;
        } catch (e) {
          console.error(e);
          const transitorio = !e.status || e.status >= 500;
          if (!transitorio) {
            toast('No se pudieron cargar los datos ❌ ' + e.message, 'error', 8000);
            this._estadoGuardado('error', 'No se pudieron cargar los datos');
            return;
          }
          const espera = esperas[Math.min(intento, esperas.length - 1)];
          if (intento === 0) toast('El servidor no responde; se reintentará solo ⏳', 'warning', 6000);
          this._estadoGuardado('guardando', `Cargando… servidor no disponible, reintento en ${Math.round(espera / 1000)} s`);
          await new Promise(res => setTimeout(res, espera));
        }
      }
    }

    setDatos(filas) {
      this.filas = filas.map(f => Object.assign({}, f));
      this.seleccion.clear();
      this.filaActiva = null;
      this._respuestaPendiente = null;
      this._limpiarHistorial();       // la tabla vino entera del servidor
      this.pintar();
      this.marcarCambios(false);
    }

    /** Filas tal cual se envían al backend. */
    datos() { return this.filas; }

    filasSeleccionadas() { return this.filas.filter(f => this.seleccion.has(f)); }

    // ------------------------------------------------------------- pintado
    _aplicarFiltros() {
      this.visibles = this.hayFiltro()
        ? this.filas.filter(fila => this.fijadas.has(fila) || this._pasaFiltros(fila))
        : this.filas.slice();

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
      if (col.tipo === 'origen') {
        const ceros = (fila.historico && fila.historico._meses_cero) || [];
        if (fila.origen === 'sistema' && ceros.length) {
          // Restablecida desde manual: esos meses se quedan en 0
          const lista = ceros.map(m => m.slice(0, 3)).join(', ');
          return `<span class="pt-origen pt-origen--sistema" title="Calculado, salvo los meses que estaban en 0: ${escapar(lista)}">⚙️ Calculado·0</span>`;
        }
        return ORIGENES[fila.origen] || ORIGENES.manual;
      }
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

        const puedeEditar = this._puedeEditar();
        this.columnas.forEach((col, ic) => {
          const editable = puedeEditar && col.editable !== false;
          const clase = [col.tipo === 'numero' ? 'pt-num' : '', editable ? 'pt-editable' : ''].filter(Boolean).join(' ');
          partes.push(`<td class="${clase}" data-campo="${col.campo}" data-fila="${iv}" data-col="${ic}">${this._celda(fila, col)}</td>`);
        });

        partes.push('</tr>');
      });

      const vacio = !this.datosCargados ? 'Cargando…'
        : (this.filas.length && this.hayFiltro()
          ? 'Ninguna fila coincide con los filtros. <button type="button" class="pt-btn pt-btn--enlace" data-rol="quitar-filtros">Quitar filtros</button>'
          : 'Sin registros para mostrar');
      this.tbody.innerHTML = partes.join('') ||
        `<tr><td class="pt-vacio" colspan="${this._columnasVisibles().length}">${vacio}</td></tr>`;

      this._pintarSeleccionCeldas();
      this._pintarTotales();
      const manuales = this.filas.filter(f => f.origen === 'manual').length;
      this.contador.textContent =
        `${this.visibles.length} de ${this.filas.length} fila(s)` +
        (manuales ? ` · ${manuales} manual(es)` : '') +
        (this.seleccion.size ? ` · ${this.seleccion.size} seleccionada(s)` : '');
      this.estadoFiltro.innerHTML = this.hayFiltro()
        ? `🔎 Filtrado: <b>${this.visibles.length}</b> de ${this.filas.length} filas ` +
          '<button type="button" class="pt-btn pt-btn--enlace" data-rol="quitar-filtros">Quitar filtros</button>'
        : '';
      this.thead.querySelectorAll('.pt-filtro-btn').forEach(b =>
        b.classList.toggle('pt-filtro-btn--activo', !!this.filtros[b.dataset.filtro]));

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
        const btnFiltro = e.target.closest('.pt-filtro-btn');
        if (btnFiltro) {
          e.stopPropagation();
          const abierto = this._panelFiltro && this._panelFiltro.dataset.campo === btnFiltro.dataset.filtro;
          if (abierto) this._cerrarPanelFiltro();
          else this._abrirPanelFiltro(btnFiltro.dataset.filtro, btnFiltro);
          return;
        }
        const th = e.target.closest('th[data-campo]');
        if (!th) return;
        const campo = th.dataset.campo;
        // 1er clic ▲ · 2º clic ▼ · 3er clic: vuelve al orden por nombre y centro
        if (this.orden.campo !== campo) this.orden = { campo, dir: 1 };
        else if (this.orden.dir === 1) this.orden = { campo, dir: -1 };
        else this.orden = { campo: null, dir: 1 };
        this.pintar();
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

      this.raiz.addEventListener('click', (e) => {
        if (e.target.closest('[data-rol="quitar-filtros"]')) this.limpiarFiltros();
      });
      document.addEventListener('mousedown', (e) => {
        if (this._panelFiltro && !e.target.closest('.pt-fpanel') && !e.target.closest('.pt-filtro-btn')) {
          this._cerrarPanelFiltro();
        }
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
      if (this._puedeEditar()) {
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

    /**
     * Valida un valor para una columna (las mismas reglas de los presupuestos
     * generales): números válidos, opciones de la lista y texto en mayúsculas.
     * Devuelve {ok, valor} con el valor ya normalizado.
     */
    _validar(col, texto) {
      if (col.tipo === 'numero') {
        return esNumeroValido(texto) ? { ok: true, valor: aNumero(texto) } : { ok: false };
      }
      const valor = String(texto ?? '').trim();
      if (col.tipo === 'select' && col.opciones && valor) {
        const igual = col.opciones.find(o => normalizar(o).trim() === normalizar(valor).trim());
        return igual ? { ok: true, valor: igual } : { ok: false };
      }
      return { ok: true, valor: valor.toUpperCase() };
    }

    /** Escribe en una celda. true = escrita · false = no editable · 'invalido' = valor rechazado. */
    _escribirCelda(fila, col, texto) {
      if (!this._puedeEditar() || col.editable === false) return false;
      const v = this._validar(col, texto);
      if (!v.ok) return 'invalido';
      const actual = col.tipo === 'numero' ? aNumero(fila[col.campo]) : String(fila[col.campo] ?? '');
      if (actual !== v.valor) this.setValor(fila, col.campo, v.valor);
      return true;
    }

    _avisoInvalidos(n) {
      if (n) toast(`${n} valor(es) no válidos para su columna no se escribieron (números o valores de la lista) ⚠️`,
                   'warning', 6000);
    }

    /** Pega un TSV (de Excel o de la misma tabla) desde la celda activa. */
    pegarTexto(texto) {
      if (!this.cursor || !this._puedeEditar()) return 0;
      const matriz = String(texto).replace(/\r/g, '').replace(/\n$/, '')
        .split('\n').map(l => l.split('\t'));
      if (!matriz.length) return 0;
      const { f, c } = this.cursor;
      let escritas = 0, agregadas = 0, invalidos = 0;
      matriz.forEach((linea, df) => {
        let fila = this.visibles[f + df];
        if (!fila) {                       // más líneas que filas: se agregan al final
          fila = this.agregarFila(this._baseFilaNueva());
          agregadas++;
        }
        linea.forEach((valor, dc) => {
          const col = this.columnas[c + dc];
          const r = col ? this._escribirCelda(fila, col, valor) : false;
          if (r === 'invalido') invalidos++;
          else if (r) escritas++;
        });
      });
      this.pintar();
      this._avisoInvalidos(invalidos);
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
      if (!r || !this._puedeEditar()) return 0;
      let n = 0;
      for (let f = r.f0; f <= r.f1; f++) {
        for (let c = r.c0; c <= r.c1; c++) {
          const col = this.columnas[c];
          if (this._escribirCelda(this.visibles[f], col, col.tipo === 'numero' ? 0 : '') === true) n++;
        }
      }
      this.pintar();
      return n;
    }

    /** Copia los valores del rango sobre el área arrastrada (como Excel). */
    rellenar(destino) {
      const r = this._rango();
      if (!r || !destino || !this._puedeEditar()) return 0;
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
          if (this._escribirCelda(this.visibles[f], col, this._valorCelda(origen, colOrigen)) === true) n++;
        }
      }
      this.cursor = { f: destino.f1, c: destino.c1 };
      this.ancla = { f: Math.min(r.f0, destino.f0), c: Math.min(r.c0, destino.c0) };
      this.pintar();
      return n;
    }

    _conectarCeldas() {
      // Ctrl+Z deshacer · Ctrl+Y (o Ctrl+Shift+Z) rehacer. Dentro de una caja
      // de texto se deja el deshacer propio del navegador.
      document.addEventListener('keydown', (e) => {
        if (!(e.ctrlKey || e.metaKey) || e.altKey || !this.cfg.editable) return;
        const k = e.key.toLowerCase();
        if (k !== 'z' && k !== 'y') return;
        if (e.target.closest && e.target.closest('input, select, textarea, .pt-entrada, dialog')) return;
        e.preventDefault();
        if (k === 'y' || e.shiftKey) this.rehacer(); else this.deshacer();
      });

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
        if (!enFoco() || !this._puedeEditar()) return;
        const texto = this.textoDelRango();
        if (!texto) return;
        e.preventDefault();
        e.clipboardData.setData('text/plain', texto);
        this.borrarRango();
      });
      document.addEventListener('paste', (e) => {
        if (!enFoco() || !this._puedeEditar()) return;
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

      let cerrado = false;
      const cerrar = (guardar) => {
        if (cerrado || !td.contains(entrada)) return;
        cerrado = true;                 // el blur que dispara el repintado ya no vuelve a cerrar
        let cambio = false;
        if (guardar) {
          const v = this._validar(col, entrada.value);
          const anterior = col.tipo === 'numero' ? aNumero(valorOriginal) : String(valorOriginal ?? '');
          if (!v.ok) {
            toast(col.tipo === 'numero'
              ? `"${entrada.value}" no es un número válido para ${col.titulo} ❌`
              : `"${entrada.value}" no está en la lista de ${col.titulo} ❌`, 'error', 5000);
          } else if (v.valor !== anterior) {
            this.setValor(fila, campo, v.valor);
            cambio = true;
          }
        }
        // Lo que devolvió el servidor mientras se editaba se aplica ahora
        // (si hubo cambio, llegará con el próximo guardado).
        if (!cambio && this._respuestaPendiente && !this.hayPendientes()) {
          this._aplicarDatosServidor(this._respuestaPendiente);
        } else {
          this.pintar();
        }
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
      this.antesDeCambiar();
      fila[campo] = valor;
      // Lo que se escribe a mano manda sobre un "restablecer cálculo" pendiente.
      if (MESES.includes(campo) || campo === 'base') delete fila._recalcular;
      if (this.hayFiltro()) this.fijadas.add(fila);     // no desaparece mientras se edita
      if (this.cfg.recalcular) this.cfg.recalcular(fila, campo);
      if (MESES.includes(campo) && 'total' in fila) TablaPresupuesto.recalcularTotal(fila);
      this.marcarCambios();
    }

    _enfocarCelda(posFila, campo, dCol = 0) {
      const editables = this.columnas.filter(c => this._puedeEditar() && c.editable !== false);
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

    /**
     * Fila agregada en pantalla (no salió de cargar Conceptos).
     * Sin clave, o con '#m' si se distribuyó. Sigue siendo propia aunque se le
     * haya restablecido el cálculo: es el mismo criterio que usa el servidor
     * (_viene_de_conceptos) para conservarla al recargar.
     */
    static esPropia(fila) {
      const clave = String(fila.clave ?? '');
      return !clave || clave.includes('#m');
    }

    /** Aplica una función a las filas marcadas. Devuelve cuántas cambiaron. */
    aplicarASeleccionadas(fn, { avisar = true } = {}) {
      const filas = this.filasSeleccionadas();
      if (!filas.length) {
        if (avisar) toast('Selecciona al menos una fila ⚠️', 'warning');
        return 0;
      }
      this.antesDeCambiar();
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
      this.antesDeCambiar();
      const fila = {};
      this.columnas.forEach(c => { fila[c.campo] = c.tipo === 'numero' ? 0 : ''; });
      Object.assign(fila, TablaPresupuesto.filaManual(Object.assign(this._baseFilaNueva(), base)));
      fila._uid = nuevoUid();
      this.filas.push(fila);
      this.fijadas.add(fila);             // se ve aunque un filtro la esconda
      this.filaActiva = fila;
      this.pintar();
      this.marcarCambios();
      this._irAFila(fila);
      return fila;
    }

    /** Lleva el scroll a una fila, la resalta y deja el cursor en su primera celda editable. */
    _irAFila(fila) {
      const f = this.visibles.indexOf(fila);
      if (f < 0) return;
      const primera = this.columnas.findIndex(c => this._puedeEditar() && c.editable !== false);
      this.irACelda(f, primera < 0 ? 0 : primera);
      const tr = this.tbody.querySelector(`td[data-fila="${f}"]`)?.parentElement;
      if (tr) {
        tr.classList.add('pt-destello');
        if (tr.scrollIntoView) tr.scrollIntoView({ block: 'center', behavior: 'smooth' });
        setTimeout(() => tr.classList.remove('pt-destello'), 2000);
      }
    }

    duplicar(fila) {
      this.antesDeCambiar();
      const copia = TablaPresupuesto.filaManual(fila);
      MESES.forEach(m => { if (m in copia) copia[m] = 0; });
      copia.total = 0;
      delete copia._recalcular;
      copia._uid = nuevoUid();
      this.filas.splice(this.filas.indexOf(fila) + 1, 0, copia);
      this.fijadas.add(copia);
      this.filaActiva = copia;
      this.pintar();
      this.marcarCambios();
      this._irAFila(copia);
      toast('Fila duplicada 📑');
    }

    eliminar(fila) {
      const quien = [fila.nombre || fila.cedula, fila.centro, fila.area, fila.concepto]
        .filter(Boolean).join(' · ') || 'fila sin datos';
      const total = formatearNumero(fila.total);
      if (!confirm(`¿Eliminar esta fila?\n\n${quien}\nTotal: ${total}\n\nSe borrará del presupuesto (y no volverá al cargar desde Conceptos) y se recalcularán los conceptos que dependen de ella.`)) {
        return false;
      }
      this.antesDeCambiar();
      this.filas.splice(this.filas.indexOf(fila), 1);
      this.seleccion.delete(fila);
      if (this.filaActiva === fila) this.filaActiva = null;
      this.pintar();
      this.marcarCambios();
      toast('Fila eliminada 🗑️ · Ctrl+Z o ↩️ Deshacer para recuperarla', 'success', 5000);
      return true;
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

      this.antesDeCambiar();
      const nuevas = [];
      seleccionadas.forEach(fila => {
        reparto.filter(r => r.porcentaje > 0).forEach(r => {
          const copia = Object.assign({}, fila, { id: null, clave: '', _uid: nuevoUid() });
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
      nuevas.forEach(f => this.fijadas.add(f));
      this.pintar();
      this.marcarCambios();
      toast(`${seleccionadas.length} fila(s) reemplazadas por ${nuevas.length}. Se guardan solas.`);
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
    /** Compatibilidad: "guardar" ahora es enviar ya lo pendiente del autoguardado. */
    async guardar(url, boton) {
      return conSpinner(boton, () => this.guardarAhora());
    }
  }

  // ------------------------------------------------------ cableado genérico
  /**
   * Conecta los botones de la barra superior a partir de data-rol.
   *
   * data-rol admitidos: inicio | consolidado | guardar | cargar-base | borrar |
   *                     agregar | pegar | exportar | recalcular | distribuir
   * Si el botón tiene data-confirmar="texto", se pide confirmación antes.
   * Ya no hay botón "Guardar": la tabla se guarda sola (urls.guardar es el
   * endpoint del guardado automático).
   */
  function conectarBarra(tabla, urls = {}, extra = {}) {
    const boton = (rol) => document.querySelector(`[data-rol="${rol}"]`);
    const confirmar = (b) => {
      if (b.dataset.confirmarEscrito) return confirmarEscrito(b.dataset.confirmarEscrito, b.dataset.palabra);
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
        // Primero se guarda lo pendiente: un envío atrasado del autoguardado
        // no puede llegar DESPUÉS y deshacer lo que hizo esta acción.
        if (!(await tabla.guardarAhora())) return;
        const r = await pedir(url, { method: 'POST' });
        if (Array.isArray(r.data)) tabla.setDatos(r.data); else await tabla.cargar();
        toast(r.msg || 'Listo ✅', 'success', 6000);
      } catch (e) { console.error(e); toast('Error ❌ ' + e.message, 'error', 6000); }
    });

    if (urls.cargarBase) al('cargar-base', accionServidor(urls.cargarBase));
    if (urls.borrar) al('borrar', accionServidor(urls.borrar));

    al('deshacer', () => tabla.deshacer());
    al('rehacer',  () => tabla.rehacer());
    al('agregar',  extra.agregar || (() => { tabla.agregarFila(); toast('Fila agregada ✅'); }));
    al('pegar',    () => tabla.pegarDelPortapapeles());
    al('exportar', () => tabla.exportar());
    if (urls.guardar) {
      al('recalcular', (b) => {
        if (!tabla.marcarParaRecalcular()) return;
        conSpinner(b, () => tabla.guardarAhora());   // se envía ya, sin esperar
      });
    }
    if (extra.distribuir) al('distribuir', extra.distribuir);

    global.addEventListener('beforeunload', (e) => {
      if (tabla.hayPendientes()) { e.preventDefault(); e.returnValue = ''; }
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
    MESES, Columnas, TablaPresupuesto,
    aNumero, formatearNumero, esNumeroValido, toast, pedir, enviarJSON, conSpinner, confirmarEscrito,
    conectarBarra, listaJSON, leerDistribucion, recordarSecciones
  };
})(window);
