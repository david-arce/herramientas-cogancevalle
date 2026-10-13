/* fecha_excel.js — normaliza la columna MCNFECHA al cargar un Excel.
 *
 * La base de datos guarda la fecha como serial de Excel (46023 = 2026-01-01).
 * En el archivo la fecha puede venir:
 *   - como número (serial de Excel)              46023 · "46023"
 *   - como celda de fecha (objeto Date)          (si se lee con cellDates)
 *   - como texto con formato de fecha            "2026-01-31" · "2026/01/31"
 *                                                "31/01/2026" · "31-01-2026" · "31.01.2026"
 *                                                "31/01/26"   · "31-ene-2026" · "31 jan 2026"
 *     (con o sin hora: "31/01/2026 00:00:00", "2026-01-31T00:00:00")
 *
 * Con día/mes ambiguo ("05/03/2026") se asume DD/MM/AAAA (formato Colombia).
 * Si el primer número es > 12 es el día; si el segundo es > 12 se lee MM/DD.
 *
 * parseFechaExcel(v) devuelve el serial de Excel (número) o null si viene
 * vacía, y lanza un Error si la fecha no se reconoce o no existe (31/02).
 */
(function (global) {
  "use strict";

  const DIAS_EPOCH_A_SERIAL = 25569;   // 1970-01-01 en serial de Excel
  const MS_DIA = 86400000;

  const MESES = {
    ene: 1, jan: 1, feb: 2, mar: 3, abr: 4, apr: 4, may: 5, jun: 6, jul: 7,
    ago: 8, aug: 8, sep: 9, set: 9, oct: 10, nov: 11, dic: 12, dec: 12,
  };

  function serialDesde(anio, mes, dia, original) {
    if (anio < 100) anio += 2000;
    const utc = Date.UTC(anio, mes - 1, dia);
    const d = new Date(utc);
    // Rechaza fechas que no existen (31/02, mes 13...) en vez de "corregirlas"
    if (mes < 1 || mes > 12 || d.getUTCFullYear() !== anio ||
        d.getUTCMonth() !== mes - 1 || d.getUTCDate() !== dia) {
      throw new Error(`Fecha inválida en MCNFECHA: ${original}`);
    }
    return Math.round(utc / MS_DIA) + DIAS_EPOCH_A_SERIAL;
  }

  function parseFechaExcel(v) {
    if (v === null || v === undefined) return null;

    // Número: ya es serial de Excel
    if (typeof v === "number") {
      if (!Number.isFinite(v)) throw new Error(`Fecha inválida en MCNFECHA: ${v}`);
      return v;
    }

    // Celda de fecha leída como Date
    if (v instanceof Date) {
      if (isNaN(v.getTime())) throw new Error(`Fecha inválida en MCNFECHA: ${v}`);
      return serialDesde(v.getFullYear(), v.getMonth() + 1, v.getDate(), v);
    }

    const s = String(v).trim();
    if (s === "") return null;

    // Serial escrito como texto: "46023" o "46023.0"
    if (/^\d+(\.\d+)?$/.test(s)) return parseFloat(s);

    // Se ignora la hora si viene: "2026-01-31 00:00:00", "2026-01-31T00:00"
    const fecha = s.split(/[T\s](?=\d{1,2}:)/)[0].trim();
    let m;

    // AAAA-MM-DD · AAAA/MM/DD · AAAA.MM.DD
    if ((m = fecha.match(/^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$/))) {
      return serialDesde(+m[1], +m[2], +m[3], v);
    }

    // DD/MM/AAAA · DD-MM-AAAA · DD.MM.AAAA (también con año de 2 dígitos)
    if ((m = fecha.match(/^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4}|\d{2})$/))) {
      let dia = +m[1], mes = +m[2];
      if (dia <= 12 && mes > 12) [dia, mes] = [mes, dia];   // venía MM/DD
      return serialDesde(+m[3], mes, dia, v);
    }

    // DD-mmm-AAAA · DD mmm AAAA · DD/mmm/AAAA  (ene, feb... o jan, feb...)
    if ((m = fecha.match(/^(\d{1,2})[-/.\s]+([a-záéíóú]{3,})\.?[-/.\s]+(\d{4}|\d{2})$/i))) {
      const mes = MESES[m[2].slice(0, 3).toLowerCase()];
      if (mes) return serialDesde(+m[3], mes, +m[1], v);
    }

    throw new Error(`Fecha no reconocida en MCNFECHA: "${s}" (use AAAA-MM-DD, DD/MM/AAAA o número de Excel)`);
  }

  global.parseFechaExcel = parseFechaExcel;
})(window);
