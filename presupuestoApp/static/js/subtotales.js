/* subtotales.js — sumas de las filas calculadas con las cuentas configuradas
 * en Ajustes → Filas calculadas (Otros Ingresos, Gastos por Servicios,
 * Gastos de Administración, Ventas Netas...).
 *
 * La página trae la configuración en <script id="configSubtotales"> (json_script):
 *   { "OtrosIngresos": { "nombre": "Otros Ingresos", "cuentas": [...], "prefijos": [...] }, ... }
 *
 * Una fila de la tabla entra en la suma si su código está en `cuentas` o
 * empieza por alguno de los `prefijos`. Con `claveDe(row)` (opcional) también
 * entran las filas que se reconocen como cuenta clave por el nombre
 * (ventas a crédito, costo de ventas...).
 *
 *   Subtotales.sumar(data, 'OtrosIngresos', MESES, cuentaClave) -> { Enero, ..., total }
 *   Subtotales.formula('OtrosIngresos', nombres)                -> texto para el tooltip
 *   Subtotales.resumen('CostoVentas')                           -> "613522"
 */
(function (global) {
  "use strict";

  let CONFIG = {};
  try {
    const nodo = document.getElementById("configSubtotales");
    CONFIG = (nodo && JSON.parse(nodo.textContent)) || {};
  } catch (e) {
    console.error("[Subtotales] configuración inválida", e);
    CONFIG = {};
  }

  function cfg(clave) {
    const c = CONFIG[clave] || {};
    return { nombre: c.nombre || clave, cuentas: c.cuentas || [], prefijos: c.prefijos || [] };
  }

  function coincide(clave, codigo, codigoClave) {
    const c = cfg(clave);
    const cod = String(codigo || "");
    if (cod && (c.cuentas.includes(cod) || c.prefijos.some(p => cod.startsWith(p)))) return true;
    return !!codigoClave && (c.cuentas.includes(codigoClave) || c.prefijos.includes(codigoClave));
  }

  function sumar(data, clave, meses, claveDe) {
    const t = { total: 0 };
    meses.forEach(m => { t[m] = 0; });
    (data || []).forEach(row => {
      if (coincide(clave, row.mcncuenta, claveDe ? claveDe(row) : null)) {
        meses.forEach(m => { t[m] += parseFloat(row[m]) || 0; });
        t.total += parseFloat(row.total) || 0;
      }
    });
    return t;
  }

  /* Texto corto en una línea: "613522" · "inicia con 54" · "41659505, 41659501, 422004… (13 cuentas)" */
  function resumen(clave) {
    const c = cfg(clave);
    const partes = [];
    if (c.cuentas.length) {
      partes.push(c.cuentas.length <= 4
        ? c.cuentas.join(", ")
        : `${c.cuentas.slice(0, 3).join(", ")}… (${c.cuentas.length} cuentas)`);
    }
    if (c.prefijos.length) partes.push("inicia con " + c.prefijos.join(", "));
    return partes.join(" · ") || "sin cuentas";
  }

  /* Fórmula completa para el tooltip. `nombres` = { código: nombre } (opcional). */
  function formula(clave, nombres) {
    const c = cfg(clave);
    nombres = nombres || {};
    const lineas = [];
    if (c.cuentas.length && c.cuentas.length <= 8) {
      c.cuentas.forEach(cod => lineas.push(nombres[cod] ? `${cod} (${nombres[cod]})` : cod));
    } else if (c.cuentas.length) {
      for (let i = 0; i < c.cuentas.length; i += 5) lineas.push(c.cuentas.slice(i, i + 5).join(" + "));
    }
    if (c.prefijos.length) {
      lineas.push((c.prefijos.length === 1 ? "Cuentas que inician con " : "Cuentas que inician con ")
        + c.prefijos.join(", "));
    }
    if (!lineas.length) return "No suma ninguna cuenta (Ajustes → Filas calculadas)";
    return lineas.map((l, i) => (i === 0 ? l : "+ " + l)).join("\n");
  }

  global.Subtotales = { config: CONFIG, cfg, coincide, sumar, resumen, formula };
})(window);
