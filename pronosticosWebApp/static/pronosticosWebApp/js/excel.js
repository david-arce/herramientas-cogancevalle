/* excel.js — generador de archivos .xlsx en JavaScript puro (sin SheetJS ni FileSaver).
 *
 * Uso:
 *   const libro = Excel.crearLibro();
 *   Excel.agregarHoja(libro, 'Datos', [['A', 'B'], [1, 'x']]);
 *   Excel.descargar(libro, 'archivo.xlsx');
 *
 * Cada hoja es un arreglo de filas (arreglo de arreglos). Los números se guardan
 * como números y todo lo demás como texto, igual que hacía XLSX.utils.aoa_to_sheet.
 */
(function (global) {
    'use strict';

    // ---------- utilidades XML ----------
    function escaparXml(texto) {
        return String(texto)
            // Excel no acepta caracteres de control en el XML
            .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function letraColumna(indice) {
        let letras = '';
        let n = indice + 1;
        while (n > 0) {
            const resto = (n - 1) % 26;
            letras = String.fromCharCode(65 + resto) + letras;
            n = Math.floor((n - 1) / 26);
        }
        return letras;
    }

    function celdaXml(valor, ref) {
        if (valor === null || valor === undefined) return '';
        if (typeof valor === 'number') {
            return Number.isFinite(valor) ? `<c r="${ref}"><v>${valor}</v></c>` : '';
        }
        if (typeof valor === 'boolean') {
            return `<c r="${ref}" t="b"><v>${valor ? 1 : 0}</v></c>`;
        }
        return `<c r="${ref}" t="inlineStr"><is><t xml:space="preserve">${escaparXml(valor)}</t></is></c>`;
    }

    function hojaXml(filas) {
        let cuerpo = '';
        filas.forEach((fila, i) => {
            const numFila = i + 1;
            let celdas = '';
            (fila || []).forEach((valor, j) => {
                celdas += celdaXml(valor, letraColumna(j) + numFila);
            });
            cuerpo += `<row r="${numFila}">${celdas}</row>`;
        });
        return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' +
            `<sheetData>${cuerpo}</sheetData></worksheet>`;
    }

    // ---------- ZIP (sin compresión) ----------
    const TABLA_CRC = (() => {
        const tabla = new Uint32Array(256);
        for (let n = 0; n < 256; n++) {
            let c = n;
            for (let k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
            tabla[n] = c >>> 0;
        }
        return tabla;
    })();

    function crc32(bytes) {
        let crc = 0xFFFFFFFF;
        for (let i = 0; i < bytes.length; i++) {
            crc = TABLA_CRC[(crc ^ bytes[i]) & 0xFF] ^ (crc >>> 8);
        }
        return (crc ^ 0xFFFFFFFF) >>> 0;
    }

    function crearZip(archivos) {
        const codificador = new TextEncoder();
        const ahora = new Date();
        const horaDos = (ahora.getHours() << 11) | (ahora.getMinutes() << 5) | Math.floor(ahora.getSeconds() / 2);
        const fechaDos = ((ahora.getFullYear() - 1980) << 9) | ((ahora.getMonth() + 1) << 5) | ahora.getDate();

        const partes = [];
        const central = [];
        let desplazamiento = 0;

        archivos.forEach(({ nombre, contenido }) => {
            const nombreBytes = codificador.encode(nombre);
            const datos = codificador.encode(contenido);
            const crc = crc32(datos);

            const local = new DataView(new ArrayBuffer(30));
            local.setUint32(0, 0x04034b50, true);
            local.setUint16(4, 20, true);
            local.setUint16(6, 0x0800, true);   // nombres en UTF-8
            local.setUint16(8, 0, true);        // sin compresión
            local.setUint16(10, horaDos, true);
            local.setUint16(12, fechaDos, true);
            local.setUint32(14, crc, true);
            local.setUint32(18, datos.length, true);
            local.setUint32(22, datos.length, true);
            local.setUint16(26, nombreBytes.length, true);
            local.setUint16(28, 0, true);
            partes.push(new Uint8Array(local.buffer), nombreBytes, datos);

            const cabecera = new DataView(new ArrayBuffer(46));
            cabecera.setUint32(0, 0x02014b50, true);
            cabecera.setUint16(4, 20, true);
            cabecera.setUint16(6, 20, true);
            cabecera.setUint16(8, 0x0800, true);
            cabecera.setUint16(10, 0, true);
            cabecera.setUint16(12, horaDos, true);
            cabecera.setUint16(14, fechaDos, true);
            cabecera.setUint32(16, crc, true);
            cabecera.setUint32(20, datos.length, true);
            cabecera.setUint32(24, datos.length, true);
            cabecera.setUint16(28, nombreBytes.length, true);
            cabecera.setUint32(42, desplazamiento, true);
            central.push(new Uint8Array(cabecera.buffer), nombreBytes);

            desplazamiento += 30 + nombreBytes.length + datos.length;
        });

        const tamCentral = central.reduce((suma, p) => suma + p.length, 0);
        const fin = new DataView(new ArrayBuffer(22));
        fin.setUint32(0, 0x06054b50, true);
        fin.setUint16(8, archivos.length, true);
        fin.setUint16(10, archivos.length, true);
        fin.setUint32(12, tamCentral, true);
        fin.setUint32(16, desplazamiento, true);

        return new Blob([...partes, ...central, new Uint8Array(fin.buffer)], {
            type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        });
    }

    // ---------- API pública ----------
    function crearLibro() {
        return { hojas: [] };
    }

    function agregarHoja(libro, nombre, filas) {
        // Excel: máximo 31 caracteres, sin : \ / ? * [ ] y nombres únicos
        let base = String(nombre || 'Hoja').replace(/[:\\/?*\[\]]/g, '').substring(0, 31) || 'Hoja';
        let final = base;
        let n = 2;
        const usados = libro.hojas.map(h => h.nombre.toLowerCase());
        while (usados.includes(final.toLowerCase())) {
            const sufijo = ` (${n++})`;
            final = base.substring(0, 31 - sufijo.length) + sufijo;
        }
        libro.hojas.push({ nombre: final, filas: filas || [] });
    }

    function generarBlob(libro) {
        const hojas = libro.hojas.length ? libro.hojas : [{ nombre: 'Hoja1', filas: [] }];
        const decl = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>';

        const archivos = [
            {
                nombre: '[Content_Types].xml',
                contenido: decl +
                    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' +
                    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' +
                    '<Default Extension="xml" ContentType="application/xml"/>' +
                    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>' +
                    '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>' +
                    hojas.map((_, i) => `<Override PartName="/xl/worksheets/sheet${i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`).join('') +
                    '</Types>',
            },
            {
                nombre: '_rels/.rels',
                contenido: decl +
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
                    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>' +
                    '</Relationships>',
            },
            {
                nombre: 'xl/workbook.xml',
                contenido: decl +
                    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">' +
                    '<sheets>' +
                    hojas.map((h, i) => `<sheet name="${escaparXml(h.nombre)}" sheetId="${i + 1}" r:id="rId${i + 1}"/>`).join('') +
                    '</sheets></workbook>',
            },
            {
                nombre: 'xl/_rels/workbook.xml.rels',
                contenido: decl +
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
                    hojas.map((_, i) => `<Relationship Id="rId${i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet${i + 1}.xml"/>`).join('') +
                    `<Relationship Id="rId${hojas.length + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>` +
                    '</Relationships>',
            },
            {
                nombre: 'xl/styles.xml',
                contenido: decl +
                    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' +
                    '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>' +
                    '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>' +
                    '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>' +
                    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>' +
                    '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>' +
                    '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>' +
                    '</styleSheet>',
            },
            ...hojas.map((h, i) => ({ nombre: `xl/worksheets/sheet${i + 1}.xml`, contenido: hojaXml(h.filas) })),
        ];
        return crearZip(archivos);
    }

    function descargar(libro, nombreArchivo) {
        const url = URL.createObjectURL(generarBlob(libro));
        const enlace = document.createElement('a');
        enlace.href = url;
        enlace.download = nombreArchivo;
        document.body.appendChild(enlace);
        enlace.click();
        enlace.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }

    global.Excel = { crearLibro, agregarHoja, generarBlob, descargar };
})(window);
