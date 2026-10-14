/* filas_calculadas.js — subtotales del Ejecutado, Presupuestado y Comparativo.
 *
 * Cada fila calculada tiene un código CALC-... que está en Orden de cuentas: la
 * tabla la muestra en la posición que tenga en esa lista (y solo si está
 * visible en la pestaña). Las cuentas que suma cada una salen de Ajustes →
 * Filas calculadas (static/js/subtotales.js).
 *
 *   FilasCalculadas.construir(data, orden, modo, { claveDe, nombres })
 *       -> filas de la tabla: cuentas + filas calculadas intercaladas según `orden`
 *   FilasCalculadas.calcular(tipo, data, modo, claveDe)
 *       -> { Enero, ..., Diciembre, total } de una fila calculada
 *
 *   modo: "sede"  -> Excedentes = Utilidad Operacional
 *         "total" -> Excedentes = Utilidad Op. − Gastos Financieros + Ingresos por Servicios − Gastos por Servicios
 *   claveDe(row): reconoce cuentas clave por el nombre (ventas, costo de ventas); opcional.
 *
 * Necesita subtotales.js.
 */
(function (global) {
  "use strict";

  const MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];

  // código en Orden de cuentas -> tipo de fila (el que usan estilos, tooltips y comentarios)
  const CODIGOS = {
    "CALC-VENTAS-NETAS":             "VentasNetas",
    "CALC-GASTOS-VENTAS":            "54",
    "CALC-GASTOS-ADMINISTRACION":    "51",
    "CALC-PCT-COSTO-VENTAS":         "PctCostoVentas",
    "CALC-MARGEN-BRUTO":             "MargenBruto",
    "CALC-PCT-MARGEN-BRUTO":         "PctMargenBruto",
    "CALC-MARGEN-CONTRIBUCION":      "MargenContribucion",
    "CALC-PCT-MARGEN-CONTRIBUCION":  "PctMargenContribucion",
    "CALC-UTILIDAD-OPERACIONAL":     "UtilidadOperacional",
    "CALC-PCT-UTILIDAD-OPERACIONAL": "PctUtilidadOperacional",
    "CALC-GASTOS-FINANCIEROS":       "GastosFinancieros",
    "CALC-INGRESOS-SERVICIOS":       "IngresosPorServicios",
    "CALC-ASISTENCIA-TECNICA":       "AsistenciaTecnica",
    "CALC-OTROS-INGRESOS":           "OtrosIngresos",
    "CALC-GASTOS-SERVICIOS":         "GastosPorServicios",
    "CALC-EXCEDENTES":               "ExcedentesPerdidaNeta",
    "CALC-PCT-EXCEDENTES":           "PctExcedentes",
  };

  const NOMBRES = {
    VentasNetas: "VENTAS NETAS", "54": "GASTOS DE VENTAS", "51": "GASTOS DE ADMINISTRACIÓN",
    PctCostoVentas: "% Costo de Ventas", MargenBruto: "Margen Bruto", PctMargenBruto: "% Margen Bruto",
    MargenContribucion: "Margen de Contribución", PctMargenContribucion: "% Margen de Contribución",
    UtilidadOperacional: "Utilidad Operacional", PctUtilidadOperacional: "% Utilidad Operacional",
    GastosFinancieros: "Gastos Financieros", IngresosPorServicios: "INGRESOS POR SERVICIOS",
    AsistenciaTecnica: "ASISTENCIA TECNICA", OtrosIngresos: "OTROS INGRESOS",
    GastosPorServicios: "GASTOS POR SERVICIOS", ExcedentesPerdidaNeta: "EXCEDENTES O PERDIDA NETA",
    PctExcedentes: "% Excedente o Pérdida",
  };

  const PORCENTAJES = new Set(["PctCostoVentas", "PctMargenBruto", "PctMargenContribucion",
                               "PctUtilidadOperacional", "PctExcedentes"]);

  /* Calcula (y recuerda) las filas de un conjunto de datos. */
  function calculadora(data, modo, claveDe) {
    const cache = {};
    const sumar = clave => Subtotales.sumar(data || [], clave, MESES, claveDe);
    const op = fn => {
      const t = {};
      MESES.forEach(m => { t[m] = fn(m); });
      t.total = fn("total");
      return t;
    };
    const porcentaje = x => {
      const vn = v("VentasNetas");
      return op(m => { const base = vn[m] || 0; return base !== 0 ? (x[m] / base) * 100 : 0; });
    };

    function calc(tipo) {
      switch (tipo) {
        case "VentasNetas":            return sumar("VentasNetas");
        case "54":                     return sumar("54");
        case "51":                     return sumar("51");
        case "CostoVentas":            return sumar("CostoVentas");
        case "PctCostoVentas":         return porcentaje(v("CostoVentas"));
        case "MargenBruto": {
          const vn = v("VentasNetas"), cv = v("CostoVentas");
          return op(m => (vn[m] || 0) - (cv[m] || 0));
        }
        case "PctMargenBruto":         return porcentaje(v("MargenBruto"));
        case "MargenContribucion": {
          const mb = v("MargenBruto"), aj = sumar("AjustesMargenContribucion");
          return op(m => (mb[m] || 0) + (aj[m] || 0));
        }
        case "PctMargenContribucion":  return porcentaje(v("MargenContribucion"));
        case "UtilidadOperacional": {
          const mc = v("MargenContribucion"), g54 = v("54"), g51 = v("51");
          return op(m => (mc[m] || 0) - (g54[m] || 0) - (g51[m] || 0));
        }
        case "PctUtilidadOperacional": return porcentaje(v("UtilidadOperacional"));
        case "GastosFinancieros":      return sumar("GastosFinancieros");
        case "AsistenciaTecnica":      return sumar("AsistenciaTecnica");
        case "OtrosIngresos":          return sumar("OtrosIngresos");
        case "IngresosPorServicios": {
          const at = v("AsistenciaTecnica"), oi = v("OtrosIngresos");
          return op(m => (at[m] || 0) + (oi[m] || 0));
        }
        case "GastosPorServicios":     return sumar("GastosPorServicios");
        case "ExcedentesPerdidaNeta": {
          const uo = v("UtilidadOperacional");
          if (modo !== "total") return op(m => uo[m] || 0);
          const gf = v("GastosFinancieros"), is = v("IngresosPorServicios"), gs = v("GastosPorServicios");
          return op(m => (uo[m] || 0) - (gf[m] || 0) + (is[m] || 0) - (gs[m] || 0));
        }
        case "PctExcedentes":          return porcentaje(v("ExcedentesPerdidaNeta"));
        default:                       return op(() => 0);
      }
    }
    function v(tipo) {
      if (!cache[tipo]) cache[tipo] = calc(tipo);
      return cache[tipo];
    }

    return {
      valores: v,
      fila(tipo, nombre) {
        // En Total Base los subtotales de gastos muestran su código (54 / 51) en la columna Cuenta
        const cuenta = modo === "total" && (tipo === "54" || tipo === "51") ? tipo : "";
        return { ...v(tipo), mcncuenta: cuenta, ctanombre: nombre || NOMBRES[tipo] || tipo,
                 isTotalRow: true, tipoTotal: tipo, codigoOrden: codigoDe(tipo) };
      },
    };
  }

  const TIPO_A_CODIGO = Object.fromEntries(Object.entries(CODIGOS).map(([c, t]) => [t, c]));
  const codigoDe = tipo => TIPO_A_CODIGO[tipo] || "";

  /* Filas de la tabla: las cuentas de `data` (en el orden en que vienen) con las
     filas calculadas intercaladas en la posición que tienen en `orden`. */
  function construir(data, orden, modo, opciones = {}) {
    const { claveDe = null, nombres = {} } = opciones;
    const calc = calculadora(data, modo, claveDe);
    const lista = (orden || []).map(c => String(c ?? ""));
    const pos = new Map();
    lista.forEach((c, i) => { if (!pos.has(c)) pos.set(c, i); });

    const pendientes = [];
    lista.forEach((c, i) => {
      if (CODIGOS[c] && pos.get(c) === i) pendientes.push({ i, fila: calc.fila(CODIGOS[c], nombres[c]) });
    });

    const resultado = [];
    let k = 0;
    (data || []).forEach(row => {
      const c = String(row.mcncuenta ?? "");
      const p = pos.has(c) ? pos.get(c) : Infinity;
      while (k < pendientes.length && pendientes[k].i < p) resultado.push(pendientes[k++].fila);
      resultado.push(row);
    });
    while (k < pendientes.length) resultado.push(pendientes[k++].fila);
    return resultado;
  }

  function calcular(tipo, data, modo, claveDe) {
    return calculadora(data, modo, claveDe).valores(tipo);
  }

  global.FilasCalculadas = {
    MESES, CODIGOS, NOMBRES, PORCENTAJES,
    construir, calcular, codigoDe,
    esPorcentaje: tipo => PORCENTAJES.has(tipo),
    esCalculada: codigo => Object.prototype.hasOwnProperty.call(CODIGOS, String(codigo ?? "")),
  };
})(window);
