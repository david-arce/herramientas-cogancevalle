/* ==========================================================================
 * presupuesto_calculos.js
 * Las reglas de cálculo que antes estaban copiadas (con 12 variables
 * "nuevaComisionEnero…" cada vez) dentro de cada template auxiliar.
 * Aquí quedan como recetas con parámetros; cada template solo elige una.
 * ========================================================================== */
(function (global) {
  'use strict';

  const { MESES, aNumero, TablaPresupuesto } = global.PT;
  const redondear = (v) => Math.round(v);

  const Calculos = {
    MESES,

    /** Suma de los 12 meses en `total`. */
    total: TablaPresupuesto.recalcularTotal,

    /**
     * Incrementa cada mes un porcentaje: mes = mes * (1 + pct/100).
     * Usado por: auxilio TBC/KIT, auxilio educación, bolsa consumibles,
     * auxilio de transporte.
     */
    incrementarMeses(fila, pct, meses = MESES) {
      meses.forEach(m => { fila[m] = redondear(aNumero(fila[m]) * (1 + pct / 100)); });
      return Calculos.total(fila);
    },

    /**
     * Aplica un porcentaje sobre el valor del mes: mes = mes * pct/100.
     * Usado por: cesantías, prima, vacaciones.
     */
    porcentajeMeses(fila, pct, meses = MESES) {
      meses.forEach(m => { fila[m] = redondear(aNumero(fila[m]) * pct / 100); });
      return Calculos.total(fila);
    },

    /**
     * Reparte un valor base fijo en todos los meses, incrementado.
     * Usado por: aprendiz.
     */
    baseFija(fila, { campoBase = 'salario_base', pct = 0 } = {}) {
      const base = aNumero(fila[campoBase]);
      if (base <= 0) return fila;
      const valor = redondear(base * (1 + pct / 100));
      MESES.forEach(m => { fila[m] = valor; });
      return Calculos.total(fila);
    },

    /**
     * Enero y febrero con el valor anterior, marzo con el retroactivo de esos
     * dos meses y de marzo en adelante el valor nuevo.
     * Usado por: sueldos, medios de transporte, ayuda de transporte.
     *
     * @param {Object} opc
     *   campoBase   campo con el valor de partida ('salario_base' | 'base')
     *   pct         porcentaje de incremento
     *   minimo      (opcional) piso legal; si la base es menor, enero y
     *               febrero se pagan al mínimo incrementado
     *   mesRetro    mes que recibe el retroactivo (por defecto 'marzo')
     */
    conRetroactivo(fila, { campoBase = 'base', pct = 0, minimo = null, mesRetro = 'marzo' } = {}) {
      const base = aNumero(fila[campoBase]);
      if (base <= 0) return fila;

      const nuevo = base * (1 + pct / 100);
      let valorInicial = base;
      let retroactivo = nuevo + (nuevo - base) * 2;

      if (minimo !== null) {
        const minimoIncrementado = minimo * (1 + pct / 100);
        if (base < minimoIncrementado) {
          valorInicial = minimoIncrementado;
          retroactivo = nuevo + (nuevo - minimoIncrementado) * 2;
        }
      }

      const iRetro = MESES.indexOf(mesRetro);
      MESES.forEach((m, i) => {
        if (i < iRetro)       fila[m] = redondear(valorInicial);
        else if (i === iRetro) fila[m] = redondear(retroactivo);
        else                   fila[m] = redondear(nuevo);
      });
      return Calculos.total(fila);
    },

    /**
     * Incrementa los meses con dato real y rellena los meses restantes con el
     * promedio de esos meses, también incrementado.
     * Usado por: comisiones (ene–sep → oct–dic) y horas extra (ene–ago → sep–dic).
     */
    incrementoYPromedio(fila, { pct = 0, mesesBase = [], mesesPromedio = [] } = {}) {
      const originales = mesesBase.map(m => aNumero(fila[m]));
      mesesBase.forEach((m, i) => { fila[m] = redondear(originales[i] * (1 + pct / 100)); });

      const promedio = originales.reduce((a, b) => a + b, 0) / (mesesBase.length || 1);
      const ajustado = redondear(Math.round(promedio) * (1 + pct / 100));
      mesesPromedio.forEach(m => { fila[m] = ajustado; });

      return Calculos.total(fila);
    },

    /**
     * Rellena unos meses con el promedio (incrementado) de otros.
     * Se usa al editar un mes en comisiones, para recalcular oct–dic.
     */
    promedioEn(fila, { mesesBase = [], mesesDestino = [], pct = 0 } = {}) {
      const suma = mesesBase.reduce((a, m) => a + aNumero(fila[m]), 0);
      const promedio = Math.round(suma / (mesesBase.length || 1));
      const valor = redondear(promedio * (1 + pct / 100));
      mesesDestino.forEach(m => { fila[m] = valor; });
      return Calculos.total(fila);
    },

    /**
     * Intereses de cesantías por bloques consecutivos con valor:
     * interés = (acumulado * días * 12%) / 360, descontando lo ya causado.
     * Un mes en cero corta el bloque.
     */
    interesesCesantias(fila, tasa = 0.12) {
      let acumulado = 0, consecutivos = 0, enBloque = false, causados = 0;

      MESES.forEach(mes => {
        const valor = aNumero(fila[mes]);
        if (valor === 0) { fila[mes] = 0; enBloque = false; return; }
        if (!enBloque) { acumulado = 0; consecutivos = 0; causados = 0; enBloque = true; }

        acumulado += valor;
        consecutivos += 1;
        const dias = 30 * consecutivos;
        const interes = (acumulado * dias * tasa) / 360 - causados;
        causados += interes;
        fila[mes] = redondear(interes);
      });

      return Calculos.total(fila);
    },

    /**
     * Variante "simple": no corta por meses en cero y acumula por cédula
     * entre todas las filas seleccionadas.
     *
     * Comportamiento idéntico al original: cada fila de una misma cédula
     * recibe el interés calculado sobre la suma del grupo. Si se quiere que
     * el valor quede una sola vez (para no duplicarlo al sumar), pasar
     * `{ soloPrimera: true }`.
     */
    interesesCesantiasAgrupado(filas, { tasa = 0.12, soloPrimera = false } = {}) {
      const porCedula = {};
      filas.forEach(f => {
        const cedula = f.cedula;
        (porCedula[cedula] = porCedula[cedula] || []).push(f);
      });

      Object.values(porCedula).forEach(grupo => {
        let acumulado = 0, causados = 0;
        const interesPorMes = {};

        MESES.forEach((mes, i) => {
          acumulado += grupo.reduce((suma, f) => suma + aNumero(f[mes]), 0);
          const dias = 30 * (i + 1);
          const interes = (acumulado * dias * tasa) / 360 - causados;
          causados += interes;
          interesPorMes[mes] = interes;
        });

        grupo.forEach((fila, idx) => {
          const aplica = !soloPrimera || idx === 0;
          MESES.forEach(mes => { fila[mes] = aplica ? redondear(interesPorMes[mes]) : 0; });
          Calculos.total(fila);
        });
      });

      return filas;
    }
  };

  global.PTCalculos = Calculos;
})(window);
