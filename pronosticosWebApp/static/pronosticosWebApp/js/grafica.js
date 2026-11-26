/* grafica.js — gráfica de líneas en SVG en JavaScript puro (reemplaza ECharts).
 *
 * Acepta el mismo JSON que devuelve la vista /chart/:
 *   { title: {text, subtext}, xAxis: {data: [...]}, series: [{name, data: [...]}, ...] }
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

    function el(nombre, atributos = {}, padre = null) {
        const nodo = document.createElementNS(SVG_NS, nombre);
        Object.entries(atributos).forEach(([k, v]) => nodo.setAttribute(k, v));
        if (padre) padre.appendChild(nodo);
        return nodo;
    }

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

    class GraficaLineas {
        constructor(contenedor) {
            this.contenedor = contenedor;
            this.opciones = null;
            this.ocultas = new Set();
            this._alRedimensionar = () => this.opciones && this._render();
            window.addEventListener('resize', this._alRedimensionar);
        }

        dibujar(opciones) {
            this.opciones = opciones || {};
            this.ocultas.clear();
            this._render();
        }

        _render() {
            const op = this.opciones;
            const series = Array.isArray(op.series) ? op.series : [];
            const categorias = (op.xAxis && op.xAxis.data) || [];
            this.contenedor.replaceChildren();

            if (!series.length) {
                const aviso = document.createElement('p');
                aviso.className = 'grafica-aviso';
                aviso.textContent = op.message || 'No hay datos para graficar.';
                this.contenedor.appendChild(aviso);
                return;
            }

            // ---------- encabezado: título, leyenda y botón de descarga ----------
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
                    this._render();
                });
                leyenda.appendChild(item);
            });

            this.contenedor.append(cabecera, leyenda);

            // ---------- área de dibujo ----------
            const ancho = Math.max(this.contenedor.clientWidth, 300);
            const alto = 360;
            const margen = { arriba: 16, derecha: 24, abajo: 40, izquierda: 64 };
            const anchoUtil = ancho - margen.izquierda - margen.derecha;
            const altoUtil = alto - margen.arriba - margen.abajo;

            const visibles = series.map((s, i) => ({ s, i })).filter(({ i }) => !this.ocultas.has(i));
            const valores = visibles.flatMap(({ s }) => (s.data || []).filter(v => typeof v === 'number' && Number.isFinite(v)));
            const numPuntos = Math.max(categorias.length, ...series.map(s => (s.data || []).length), 1);

            const marcas = marcasEje(valores.length ? Math.min(0, ...valores) : 0, valores.length ? Math.max(...valores) : 1);
            const yMin = marcas[0];
            const yMax = marcas[marcas.length - 1];
            const x = (j) => margen.izquierda + (numPuntos === 1 ? anchoUtil / 2 : (j * anchoUtil) / (numPuntos - 1));
            const y = (v) => margen.arriba + altoUtil - ((v - yMin) / (yMax - yMin)) * altoUtil;

            const svg = el('svg', {
                xmlns: SVG_NS,
                width: ancho,
                height: alto,
                viewBox: `0 0 ${ancho} ${alto}`,
                role: 'img',
                'aria-label': titulo.textContent,
                class: 'grafica-svg',
            });
            el('rect', { x: 0, y: 0, width: ancho, height: alto, fill: '#ffffff' }, svg);

            // Rejilla y eje Y
            marcas.forEach(v => {
                const yy = y(v);
                el('line', { x1: margen.izquierda, x2: ancho - margen.derecha, y1: yy, y2: yy, stroke: '#e0e6f1' }, svg);
                const t = el('text', { x: margen.izquierda - 8, y: yy + 4, 'text-anchor': 'end', 'font-size': 12, fill: '#6e7079' }, svg);
                t.textContent = formatoNumero.format(v);
            });

            // Eje X
            el('line', {
                x1: margen.izquierda, x2: ancho - margen.derecha,
                y1: margen.arriba + altoUtil, y2: margen.arriba + altoUtil, stroke: '#6e7079',
            }, svg);
            const saltoEtiqueta = Math.max(1, Math.ceil(numPuntos / Math.max(1, Math.floor(anchoUtil / 70))));
            for (let j = 0; j < numPuntos; j++) {
                if (j % saltoEtiqueta !== 0 && j !== numPuntos - 1) continue;
                const t = el('text', {
                    x: x(j), y: margen.arriba + altoUtil + 20,
                    // la última etiqueta se alinea a la derecha para que no se corte
                    'text-anchor': (j === numPuntos - 1 && numPuntos > 1) ? 'end' : 'middle',
                    'font-size': 12, fill: '#6e7079',
                }, svg);
                t.textContent = categorias[j] ?? '';
            }

            // Líneas
            visibles.forEach(({ s, i }) => {
                const color = COLORES[i % COLORES.length];
                let d = '';
                let enTrazo = false;
                (s.data || []).forEach((v, j) => {
                    if (typeof v !== 'number' || !Number.isFinite(v)) { enTrazo = false; return; }
                    d += `${enTrazo ? 'L' : 'M'}${x(j).toFixed(1)},${y(v).toFixed(1)}`;
                    enTrazo = true;
                });
                el('path', { d, fill: 'none', stroke: color, 'stroke-width': 2, 'stroke-linejoin': 'round' }, svg);
                (s.data || []).forEach((v, j) => {
                    if (typeof v !== 'number' || !Number.isFinite(v)) return;
                    el('circle', { cx: x(j), cy: y(v), r: 3, fill: '#ffffff', stroke: color, 'stroke-width': 2 }, svg);
                });
            });

            // Tooltip por eje (como trigger: 'axis')
            const guia = el('line', {
                y1: margen.arriba, y2: margen.arriba + altoUtil, stroke: '#999', 'stroke-dasharray': '4 4', visibility: 'hidden',
            }, svg);
            const zona = el('rect', {
                x: margen.izquierda, y: margen.arriba, width: anchoUtil, height: altoUtil, fill: 'transparent',
            }, svg);

            const lienzo = document.createElement('div');
            lienzo.className = 'grafica-lienzo';
            const tooltip = document.createElement('div');
            tooltip.className = 'grafica-tooltip';
            tooltip.hidden = true;
            lienzo.append(svg, tooltip);
            this.contenedor.appendChild(lienzo);
            this.svg = svg;

            const mostrar = (evento) => {
                const caja = svg.getBoundingClientRect();
                const px = evento.clientX - caja.left;
                const j = numPuntos === 1 ? 0
                    : Math.round(((px - margen.izquierda) / anchoUtil) * (numPuntos - 1));
                if (j < 0 || j >= numPuntos) return;
                guia.setAttribute('x1', x(j));
                guia.setAttribute('x2', x(j));
                guia.setAttribute('visibility', 'visible');

                tooltip.replaceChildren();
                const encabezado = document.createElement('strong');
                encabezado.textContent = categorias[j] ?? '';
                tooltip.appendChild(encabezado);
                visibles.forEach(({ s, i }) => {
                    const v = (s.data || [])[j];
                    if (typeof v !== 'number') return;
                    const linea = document.createElement('div');
                    const muestra = document.createElement('span');
                    muestra.className = 'grafica-muestra';
                    muestra.style.background = COLORES[i % COLORES.length];
                    linea.append(muestra, document.createTextNode(`${s.name}: ${formatoNumero.format(v)}`));
                    tooltip.appendChild(linea);
                });
                tooltip.hidden = false;
                const izquierda = x(j) + 12;
                tooltip.style.top = `${margen.arriba}px`;
                tooltip.style.left = izquierda + tooltip.offsetWidth > ancho
                    ? `${Math.max(0, x(j) - tooltip.offsetWidth - 12)}px`
                    : `${izquierda}px`;
            };
            zona.addEventListener('mousemove', mostrar);
            zona.addEventListener('mouseleave', () => {
                guia.setAttribute('visibility', 'hidden');
                tooltip.hidden = true;
            });
        }

        // Equivalente a toolbox.saveAsImage: descarga la gráfica como PNG
        guardarImagen() {
            if (!this.svg) return;
            const op = this.opciones || {};
            const ancho = Number(this.svg.getAttribute('width'));
            const alto = Number(this.svg.getAttribute('height'));
            const series = (op.series || []).filter((_, i) => !this.ocultas.has(i));
            const altoCabecera = 70;

            const datos = new XMLSerializer().serializeToString(this.svg);
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
