/* grafica.js — gráfica de líneas en SVG en JavaScript puro (reemplaza ECharts).
 *
 * Acepta el mismo JSON que devuelve la vista /chart/:
 *   { title: {text, subtext}, xAxis: {data: [...]}, series: [{name, data: [...]}, ...] }
 *
 * Animaciones (al estilo de ECharts):
 *   - Entrada: las líneas se revelan de izquierda a derecha.
 *   - Leyenda: al ocultar/mostrar una serie, el eje Y y las líneas se reajustan
 *     suavemente y la serie se desvanece.
 *   - Tooltip: la línea guía, el recuadro y los puntos resaltados se deslizan.
 *
 * Uso:
 *   const g = new GraficaLineas(document.getElementById('chart'));
 *   g.dibujar(opciones);
 */
(function (global) {
    'use strict';

    const SVG_NS = 'http://www.w3.org/2000/svg';
    const COLORES = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4'];
    const formatoNumero = new Intl.NumberFormat('es-CO');

    const DURACION_ENTRADA = 1000;   // ms
    const DURACION_CAMBIO = 500;     // ms
    const ALTO = 360;
    const MARGEN = { arriba: 16, derecha: 24, abajo: 40, izquierda: 64 };

    const sinMovimiento = () =>
        window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // Curvas de suavizado
    const suavizarSalida = t => 1 - Math.pow(1 - t, 3);                 // cubicOut
    const suavizarEntrada = t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2); // cubicInOut

    const interpolar = (a, b, t) => a + (b - a) * t;

    function el(nombre, atributos = {}, padre = null) {
        const nodo = document.createElementNS(SVG_NS, nombre);
        Object.entries(atributos).forEach(([k, v]) => nodo.setAttribute(k, v));
        if (padre) padre.appendChild(nodo);
        return nodo;
    }

    const esNumero = v => typeof v === 'number' && Number.isFinite(v);

    // Marcas "bonitas" del eje Y (1, 2, 5 × 10^n)
    function marcasEje(min, max, cantidad = 5) {
        if (min === max) {
            max = min + 1;
            if (min > 0) min = 0;
        }
        const bruto = (max - min) / cantidad;
        const magnitud = Math.pow(10, Math.floor(Math.log10(bruto)));
        const paso = [1, 2, 5, 10].map(m => m * magnitud).find(p => p >= bruto);
        const inicio = Math.floor(min / paso) * paso;
        const fin = Math.ceil(max / paso) * paso;
        const marcas = [];
        for (let v = inicio; v <= fin + paso / 2; v += paso) marcas.push(Number(v.toFixed(10)));
        return marcas;
    }

    // Ejecuta una animación con requestAnimationFrame; devuelve una función para cancelarla
    function animar(duracion, alAvanzar, curva = suavizarSalida) {
        if (sinMovimiento() || duracion <= 0) {
            alAvanzar(1);
            return () => {};
        }
        let id = null;
        const inicio = performance.now();
        const paso = (ahora) => {
            const t = Math.min(1, (ahora - inicio) / duracion);
            alAvanzar(curva(t));
            if (t < 1) id = requestAnimationFrame(paso);
        };
        id = requestAnimationFrame(paso);
        return () => cancelAnimationFrame(id);
    }

    class GraficaLineas {
        constructor(contenedor) {
            this.contenedor = contenedor;
            this.opciones = null;
            this.ocultas = new Set();
            this._cancelar = () => {};

            let temporizador = null;
            window.addEventListener('resize', () => {
                clearTimeout(temporizador);
                temporizador = setTimeout(() => {
                    if (this.opciones) this._construir(false);
                }, 150);
            });
        }

        dibujar(opciones) {
            this.opciones = opciones || {};
            this.ocultas.clear();
            this._construir(true);
        }

        // ---------- cálculo de escalas ----------
        _escalaObjetivo() {
            const series = this.opciones.series || [];
            const valores = series
                .filter((_, i) => !this.ocultas.has(i))
                .flatMap(s => (s.data || []).filter(esNumero));
            const marcas = marcasEje(
                valores.length ? Math.min(0, ...valores) : 0,
                valores.length ? Math.max(...valores) : 1,
            );
            return { min: marcas[0], max: marcas[marcas.length - 1], marcas };
        }

        _x(j) {
            const n = this.numPuntos;
            return MARGEN.izquierda + (n === 1 ? this.anchoUtil / 2 : (j * this.anchoUtil) / (n - 1));
        }

        _y(v, escala) {
            return MARGEN.arriba + this.altoUtil - ((v - escala.min) / (escala.max - escala.min)) * this.altoUtil;
        }

        // ---------- construcción del DOM ----------
        _construir(animarEntrada) {
            this._cancelar();
            const op = this.opciones;
            const series = Array.isArray(op.series) ? op.series : [];
            const categorias = (op.xAxis && op.xAxis.data) || [];
            this.contenedor.replaceChildren();
            this.svg = null;

            if (!series.length) {
                const aviso = document.createElement('p');
                aviso.className = 'grafica-aviso';
                aviso.textContent = op.message || 'No hay datos para graficar.';
                this.contenedor.appendChild(aviso);
                return;
            }

            // Encabezado: título, subtítulo y botón de descarga
            const cabecera = document.createElement('div');
            cabecera.className = 'grafica-cabecera';
            const titulos = document.createElement('div');
            const titulo = document.createElement('div');
            titulo.className = 'grafica-titulo';
            titulo.textContent = (op.title && op.title.text) || '';
            const subtitulo = document.createElement('div');
            subtitulo.className = 'grafica-subtitulo';
            subtitulo.textContent = (op.title && op.title.subtext) || '';
            titulos.append(titulo, subtitulo);

            const botonImagen = document.createElement('button');
            botonImagen.type = 'button';
            botonImagen.className = 'grafica-guardar';
            botonImagen.title = 'Guardar como imagen';
            botonImagen.textContent = 'Guardar imagen';
            botonImagen.addEventListener('click', () => this.guardarImagen());
            cabecera.append(titulos, botonImagen);

            // Leyenda (clic = ocultar/mostrar serie)
            const leyenda = document.createElement('div');
            leyenda.className = 'grafica-leyenda';
            series.forEach((s, i) => {
                const item = document.createElement('button');
                item.type = 'button';
                item.className = 'grafica-leyenda-item' + (this.ocultas.has(i) ? ' inactivo' : '');
                item.setAttribute('aria-pressed', String(!this.ocultas.has(i)));
                const muestra = document.createElement('span');
                muestra.className = 'grafica-muestra';
                muestra.style.background = COLORES[i % COLORES.length];
                item.append(muestra, document.createTextNode(s.name || `Serie ${i + 1}`));
                item.addEventListener('click', () => {
                    if (this.ocultas.has(i)) this.ocultas.delete(i); else this.ocultas.add(i);
                    item.classList.toggle('inactivo', this.ocultas.has(i));
                    item.setAttribute('aria-pressed', String(!this.ocultas.has(i)));
                    this._transicionLeyenda();
                });
                leyenda.appendChild(item);
            });
            this.contenedor.append(cabecera, leyenda);

            // Geometría
            this.ancho = Math.max(this.contenedor.clientWidth, 300);
            this.anchoUtil = this.ancho - MARGEN.izquierda - MARGEN.derecha;
            this.altoUtil = ALTO - MARGEN.arriba - MARGEN.abajo;
            this.numPuntos = Math.max(categorias.length, ...series.map(s => (s.data || []).length), 1);
            this.categorias = categorias;

            const svg = el('svg', {
                xmlns: SVG_NS,
                width: this.ancho,
                height: ALTO,
                viewBox: `0 0 ${this.ancho} ${ALTO}`,
                role: 'img',
                'aria-label': titulo.textContent,
                class: 'grafica-svg',
            });
            el('rect', { x: 0, y: 0, width: this.ancho, height: ALTO, fill: '#ffffff' }, svg);

            // Recorte para la animación de entrada (se revela de izquierda a derecha)
            const idRecorte = `recorte-${Math.random().toString(36).slice(2)}`;
            const defs = el('defs', {}, svg);
            const recorte = el('clipPath', { id: idRecorte }, defs);
            this.rectRecorte = el('rect', {
                x: 0, y: 0, height: ALTO,
                width: animarEntrada && !sinMovimiento() ? MARGEN.izquierda : this.ancho,
            }, recorte);

            this.capaRejilla = el('g', {}, svg);

            // Eje X
            el('line', {
                x1: MARGEN.izquierda, x2: this.ancho - MARGEN.derecha,
                y1: MARGEN.arriba + this.altoUtil, y2: MARGEN.arriba + this.altoUtil, stroke: '#6e7079',
            }, svg);
            const saltoEtiqueta = Math.max(1, Math.ceil(this.numPuntos / Math.max(1, Math.floor(this.anchoUtil / 70))));
            for (let j = 0; j < this.numPuntos; j++) {
                if (j % saltoEtiqueta !== 0 && j !== this.numPuntos - 1) continue;
                const t = el('text', {
                    x: this._x(j), y: MARGEN.arriba + this.altoUtil + 20,
                    // la última etiqueta se alinea a la derecha para que no se corte
                    'text-anchor': (j === this.numPuntos - 1 && this.numPuntos > 1) ? 'end' : 'middle',
                    'font-size': 12, fill: '#6e7079',
                }, svg);
                t.textContent = categorias[j] ?? '';
            }

            // Guía vertical del tooltip (se desliza con transform)
            this.guia = el('line', {
                x1: 0, x2: 0, y1: MARGEN.arriba, y2: MARGEN.arriba + this.altoUtil,
                stroke: '#999', 'stroke-dasharray': '4 4', class: 'grafica-guia',
            }, svg);

            // Series: una capa por serie con su línea y sus puntos
            const capaSeries = el('g', { 'clip-path': `url(#${idRecorte})` }, svg);
            this.series = series.map((s, i) => {
                const color = COLORES[i % COLORES.length];
                const grupo = el('g', { class: 'grafica-serie' }, capaSeries);
                const linea = el('path', {
                    fill: 'none', stroke: color, 'stroke-width': 2,
                    'stroke-linejoin': 'round', 'stroke-linecap': 'round',
                }, grupo);
                const puntos = (s.data || []).map((v, j) => esNumero(v)
                    ? el('circle', { cx: this._x(j), r: 3, fill: '#ffffff', stroke: color, 'stroke-width': 2, class: 'grafica-punto' }, grupo)
                    : null);
                const opacidad = this.ocultas.has(i) ? 0 : 1;
                return { datos: s.data || [], grupo, linea, puntos, opacidad };
            });

            // Zona sensible al mouse
            const zona = el('rect', {
                x: MARGEN.izquierda, y: MARGEN.arriba, width: this.anchoUtil, height: this.altoUtil, fill: 'transparent',
            }, svg);

            const lienzo = document.createElement('div');
            lienzo.className = 'grafica-lienzo';
            this.tooltip = document.createElement('div');
            this.tooltip.className = 'grafica-tooltip';
            this.tooltip.setAttribute('aria-hidden', 'true');
            lienzo.append(svg, this.tooltip);
            this.contenedor.appendChild(lienzo);
            this.svg = svg;

            // Pintar el estado final
            this.escala = this._escalaObjetivo();
            this._pintar(this.escala, 1);

            this._indiceActivo = null;
            zona.addEventListener('mousemove', (e) => this._alMoverMouse(e));
            zona.addEventListener('mouseleave', () => this._ocultarTooltip());

            if (animarEntrada) {
                this._cancelar = animar(DURACION_ENTRADA, (t) => {
                    this.rectRecorte.setAttribute('width', interpolar(MARGEN.izquierda, this.ancho, t));
                }, suavizarEntrada);
            }
        }

        // Dibuja rejilla, líneas y puntos para una escala dada.
        // opacidadMarcas: opacidad de las etiquetas/rejilla (para el fundido al cambiar de escala)
        _pintar(escala, opacidadMarcas) {
            // Rejilla y etiquetas del eje Y
            this.capaRejilla.replaceChildren();
            const marcas = escala.marcas || [];
            marcas.forEach(v => {
                const yy = this._y(v, escala);
                if (yy < MARGEN.arriba - 1 || yy > MARGEN.arriba + this.altoUtil + 1) return;
                const g = el('g', { opacity: opacidadMarcas }, this.capaRejilla);
                el('line', { x1: MARGEN.izquierda, x2: this.ancho - MARGEN.derecha, y1: yy, y2: yy, stroke: '#e0e6f1' }, g);
                const t = el('text', { x: MARGEN.izquierda - 8, y: yy + 4, 'text-anchor': 'end', 'font-size': 12, fill: '#6e7079' }, g);
                t.textContent = formatoNumero.format(v);
            });

            // Líneas y puntos
            this.series.forEach(serie => {
                let d = '';
                let enTrazo = false;
                serie.datos.forEach((v, j) => {
                    if (!esNumero(v)) { enTrazo = false; return; }
                    const yy = this._y(v, escala);
                    d += `${enTrazo ? 'L' : 'M'}${this._x(j).toFixed(1)},${yy.toFixed(1)}`;
                    enTrazo = true;
                    serie.puntos[j].setAttribute('cy', yy.toFixed(1));
                });
                serie.linea.setAttribute('d', d);
                serie.grupo.setAttribute('opacity', serie.opacidad);
                serie.grupo.style.pointerEvents = serie.opacidad === 0 ? 'none' : '';
            });
        }

        // Al cambiar la leyenda: el eje Y se reajusta y las series aparecen/desaparecen suavemente
        _transicionLeyenda() {
            this._cancelar();
            // Si la animación de entrada seguía en curso, se completa de inmediato
            this.rectRecorte.setAttribute('width', this.ancho);
            const desde = { min: this.escala.min, max: this.escala.max };
            const hacia = this._escalaObjetivo();
            const opacidadesIniciales = this.series.map(s => s.opacidad);
            const opacidadesFinales = this.series.map((_, i) => (this.ocultas.has(i) ? 0 : 1));
            const cambiaEscala = desde.min !== hacia.min || desde.max !== hacia.max;

            this._cancelar = animar(DURACION_CAMBIO, (t) => {
                const escala = {
                    min: interpolar(desde.min, hacia.min, t),
                    max: interpolar(desde.max, hacia.max, t),
                    marcas: hacia.marcas,
                };
                this.series.forEach((s, i) => {
                    s.opacidad = interpolar(opacidadesIniciales[i], opacidadesFinales[i], t);
                });
                // Las etiquetas nuevas del eje aparecen con un fundido
                this._pintar(escala, cambiaEscala ? Math.max(0.15, t) : 1);
                this.escala = escala;
            });
            this._ocultarTooltip();
        }

        // ---------- tooltip ----------
        _alMoverMouse(evento) {
            const caja = this.svg.getBoundingClientRect();
            const escalaPx = caja.width / this.ancho;   // por si el SVG se reduce con max-width
            const px = (evento.clientX - caja.left) / escalaPx;
            const n = this.numPuntos;
            const j = n === 1 ? 0 : Math.round(((px - MARGEN.izquierda) / this.anchoUtil) * (n - 1));
            if (j < 0 || j >= n || j === this._indiceActivo) return;
            this._indiceActivo = j;

            const xx = this._x(j);
            this.guia.style.transform = `translateX(${xx}px)`;
            this.guia.classList.add('visible');

            // Resaltar los puntos del mes activo
            this.series.forEach(s => s.puntos.forEach((p, k) => {
                if (p) p.classList.toggle('activo', k === j);
            }));

            // Contenido del tooltip
            const series = this.opciones.series || [];
            this.tooltip.replaceChildren();
            const encabezado = document.createElement('strong');
            encabezado.textContent = this.categorias[j] ?? '';
            this.tooltip.appendChild(encabezado);
            series.forEach((s, i) => {
                if (this.ocultas.has(i)) return;
                const v = (s.data || [])[j];
                if (!esNumero(v)) return;
                const linea = document.createElement('div');
                const muestra = document.createElement('span');
                muestra.className = 'grafica-muestra';
                muestra.style.background = COLORES[i % COLORES.length];
                linea.append(muestra, document.createTextNode(`${s.name}: ${formatoNumero.format(v)}`));
                this.tooltip.appendChild(linea);
            });

            // Posición: a la derecha de la guía, o a la izquierda si no cabe
            const anchoTooltip = this.tooltip.offsetWidth;
            const izquierda = xx + 14 + anchoTooltip > this.ancho
                ? Math.max(0, xx - anchoTooltip - 14)
                : xx + 14;
            const primeraVez = !this.tooltip.classList.contains('visible');
            if (primeraVez) this.tooltip.classList.add('sin-transicion');
            this.tooltip.style.transform = `translate(${izquierda * escalaPx}px, ${MARGEN.arriba}px)`;
            if (primeraVez) {
                void this.tooltip.offsetWidth;   // aplica la posición sin animar la primera vez
                this.tooltip.classList.remove('sin-transicion');
            }
            this.tooltip.classList.add('visible');
        }

        _ocultarTooltip() {
            this._indiceActivo = null;
            if (this.guia) this.guia.classList.remove('visible');
            if (this.tooltip) this.tooltip.classList.remove('visible');
            (this.series || []).forEach(s => s.puntos.forEach(p => p && p.classList.remove('activo')));
        }

        // Equivalente a toolbox.saveAsImage: descarga la gráfica como PNG
        guardarImagen() {
            if (!this.svg) return;
            const op = this.opciones || {};
            const ancho = Number(this.svg.getAttribute('width'));
            const alto = Number(this.svg.getAttribute('height'));
            const series = (op.series || []).filter((_, i) => !this.ocultas.has(i));
            const altoCabecera = 70;

            // Copia del SVG sin la guía del tooltip ni el resaltado
            const copia = this.svg.cloneNode(true);
            copia.querySelectorAll('.grafica-guia').forEach(n => n.remove());
            copia.querySelectorAll('.grafica-punto').forEach(n => n.setAttribute('r', 3));
            const datos = new XMLSerializer().serializeToString(copia);
            const url = URL.createObjectURL(new Blob([datos], { type: 'image/svg+xml;charset=utf-8' }));
            const imagen = new Image();
            imagen.onload = () => {
                const escala = window.devicePixelRatio || 1;
                const canvas = document.createElement('canvas');
                canvas.width = ancho * escala;
                canvas.height = (alto + altoCabecera) * escala;
                const ctx = canvas.getContext('2d');
                ctx.scale(escala, escala);
                ctx.fillStyle = '#ffffff';
                ctx.fillRect(0, 0, ancho, alto + altoCabecera);

                ctx.fillStyle = '#333333';
                ctx.font = 'bold 18px Arial, sans-serif';
                ctx.fillText((op.title && op.title.text) || '', 10, 22);
                ctx.fillStyle = '#6e7079';
                ctx.font = '12px Arial, sans-serif';
                ctx.fillText((op.title && op.title.subtext) || '', 10, 40);

                let lx = 10;
                series.forEach((s) => {
                    const i = (op.series || []).indexOf(s);
                    ctx.fillStyle = COLORES[i % COLORES.length];
                    ctx.fillRect(lx, 52, 14, 8);
                    ctx.fillStyle = '#333333';
                    ctx.fillText(s.name, lx + 18, 60);
                    lx += 18 + ctx.measureText(s.name).width + 16;
                });

                ctx.drawImage(imagen, 0, altoCabecera, ancho, alto);
                URL.revokeObjectURL(url);

                const enlace = document.createElement('a');
                enlace.download = `${(op.title && op.title.text) || 'grafica'}.png`;
                enlace.href = canvas.toDataURL('image/png');
                document.body.appendChild(enlace);
                enlace.click();
                enlace.remove();
            };
            imagen.src = url;
        }
    }

    global.GraficaLineas = GraficaLineas;
})(window);
