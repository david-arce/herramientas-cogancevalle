/* =====================================================================
 * envio_seguro.js — guardado a prueba de despliegues y cortes de red.
 *
 * Mientras se publica una versión nueva de la aplicación el servidor puede
 * no responder unos segundos o minutos (error de red, 502/503/504, una
 * página HTML en vez de JSON, errores 500 mientras corren las migraciones…).
 * Este módulo evita que los cambios que se estaban guardando se pierdan:
 *
 *   1. Antes de enviar, guarda una copia en este navegador (localStorage).
 *   2. Si la falla es TRANSITORIA, reintenta solo: 1 s, 2 s, 4 s, 8 s, 15 s
 *      y luego cada 30 s (o de inmediato cuando vuelve la conexión).
 *   3. Siempre envía la ÚLTIMA versión de los datos: si el usuario sigue
 *      editando mientras se reintenta, no se envían versiones viejas.
 *   4. Solo borra la copia local cuando el servidor confirma el guardado.
 *   5. Si el servidor RECHAZA los datos a propósito (respuesta JSON 4xx: sin
 *      permisos, plazo cerrado, datos inválidos) no insiste: avisa el error y
 *      conserva la copia.
 *
 * Es seguro reintentar porque los guardados de la aplicación reemplazan el
 * estado completo dentro de una transacción (todo o nada): repetir el mismo
 * envío deja exactamente el mismo resultado.
 *
 * Uso — cola persistente (guardado automático):
 *   const cola = EnvioSeguro.cola({ clave, url, esExito: j => j.status === "ok",
 *                                  onEstado: (estado, info) => {...} });
 *     // estados: "enviando" · "enviado" (cada envío confirmado) · "guardado" (todo
 *     // confirmado) · "reintentando" · "error"
 *   cola.poner(datos);           // encola la versión más reciente
 *   await cola.vaciar(60000);    // espera a que todo llegue (o lanza error)
 *   cola.hayPendientes();
 *   EnvioSeguro.respaldo(clave)  // copia que quedó de una sesión anterior
 *   EnvioSeguro.descartar(clave)
 *
 * Uso — un envío con reintentos (sin cola), p. ej. un botón "Guardar":
 *   const json = await EnvioSeguro.enviar(url, datos, { onReintento, maxEsperaMs });
 * ===================================================================== */
(function (global) {
"use strict";

const ESPERAS_MS = [1000, 2000, 4000, 8000, 15000, 30000];
const PREFIJO = "envioSeguro:";

function csrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;
    const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (input) return input.value;
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);
    return m ? decodeURIComponent(m[1]) : "";
}

function errorTransitorio(mensaje, motivo) {
    return Object.assign(new Error(mensaje), { transitorio: true, motivo });
}
function errorPermanente(mensaje, respuesta) {
    return Object.assign(new Error(mensaje), { permanente: true, respuesta });
}
const mensajeDe = (j, por) => (j && (j.message || j.msg || j.mensaje || j.error)) || por;

/** Un intento de POST JSON. Devuelve el JSON o lanza un error transitorio/permanente. */
async function intentar(url, cuerpoTexto, cabecerasExtra = {}) {
    let resp;
    try {
        resp = await fetch(url, {
            method: "POST",
            credentials: "same-origin",
            cache: "no-store",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken(),
                "X-Requested-With": "XMLHttpRequest",
                ...cabecerasExtra,
            },
            body: cuerpoTexto,
        });
    } catch (e) {
        throw errorTransitorio("Sin conexión con el servidor", "red");
    }
    // Sesión vencida: Django redirige al login. Se reintenta: cuando el usuario
    // vuelva a entrar (en otra pestaña) el envío pasa solo.
    if (resp.status === 401 || (resp.redirected && /login/i.test(resp.url))) {
        throw errorTransitorio("La sesión se cerró: vuelve a iniciar sesión en otra pestaña", "sesion");
    }
    const tipo = resp.headers.get("content-type") || "";
    if (!tipo.includes("application/json")) {
        // Página de error del proxy / servidor reiniciando: no es una respuesta de la app.
        throw errorTransitorio(`El servidor no está disponible (HTTP ${resp.status})`, "servidor");
    }
    let json;
    try { json = await resp.json(); }
    catch (e) { throw errorTransitorio("Respuesta incompleta del servidor", "servidor"); }

    if (resp.status >= 500) {
        throw errorTransitorio(mensajeDe(json, `Error del servidor (HTTP ${resp.status})`), "servidor");
    }
    if (!resp.ok) throw errorPermanente(mensajeDe(json, `HTTP ${resp.status}`), json);
    return json;
}

function leer(clave) {
    try {
        const t = global.localStorage.getItem(PREFIJO + clave);
        return t ? JSON.parse(t) : null;
    } catch (e) { return null; }
}
function escribir(clave, valor) {
    try { global.localStorage.setItem(PREFIJO + clave, JSON.stringify(valor)); return true; }
    catch (e) { return false; }   // sin espacio / navegación privada: se sigue reintentando en memoria
}
function borrar(clave) {
    try { global.localStorage.removeItem(PREFIJO + clave); } catch (e) { /* nada */ }
}

/** Espera `ms` o hasta que alguien llame a despertar(). */
function dormilon() {
    let despertar = () => {};
    return {
        dormir(ms) {
            return new Promise(res => {
                const t = setTimeout(res, ms);
                despertar = () => { clearTimeout(t); res(); };
            });
        },
        despertar() { despertar(); },
    };
}

class Cola {
    constructor({ clave, url, esExito = () => true, onEstado = () => {}, cabeceras = () => ({}) }) {
        this.clave = clave;
        this.cabeceras = cabeceras;     // cabeceras extra por envío (p. ej. el token del borrador)
        this.url = url;
        this.esExito = esExito;
        this.onEstado = onEstado;
        this.datos = null;          // última versión pendiente de confirmar
        this.seq = 0;
        this.corriendo = false;
        this.ultimoError = null;
        this.esperas = [];          // promesas de vaciar()
        this.sueno = dormilon();
        this.conRespaldo = true;
        global.addEventListener("online", () => this.sueno.despertar());
    }

    hayPendientes() { return this.datos !== null || this.corriendo; }

    poner(datos) {
        this.seq += 1;
        this.datos = datos;
        this.ultimoError = null;
        this.conRespaldo = escribir(this.clave, { url: this.url, datos, ts: Date.now() });
        this.sueno.despertar();             // si estaba esperando para reintentar, envía ya lo nuevo
        this._arrancar();
    }

    /** Espera a que todo lo pendiente quede guardado. Lanza error si no se logra a tiempo. */
    vaciar(maxEsperaMs = 60000) {
        if (!this.hayPendientes()) return Promise.resolve();
        if (!this.corriendo) this._arrancar();   // p. ej. tras un error permanente: un intento más
        this.sueno.despertar();
        return new Promise((resolve, reject) => {
            const t = setTimeout(() => reject(new Error(
                "Todavía no se pudo guardar en el servidor. Tus cambios siguen en cola y se enviarán solos; " +
                "intenta de nuevo cuando diga “Todo guardado”.")), maxEsperaMs);
            this.esperas.push({ resolve: () => { clearTimeout(t); resolve(); },
                                reject: (e) => { clearTimeout(t); reject(e); } });
        });
    }

    _estado(estado, info) {
        try { this.onEstado(estado, info || {}); } catch (e) { console.error(e); }
    }

    _avisarEsperas(error) {
        const esperas = this.esperas;
        this.esperas = [];
        esperas.forEach(w => (error ? w.reject(error) : w.resolve()));
    }

    async _arrancar() {
        if (this.corriendo) return;
        this.corriendo = true;
        let intento = 0;
        while (this.datos !== null) {
            const seq = this.seq, datos = this.datos, url = this.url;
            this._estado("enviando", { conRespaldo: this.conRespaldo });
            try {
                const json = await intentar(url, JSON.stringify(datos), this.cabeceras() || {});
                if (!this.esExito(json)) throw errorPermanente(mensajeDe(json, "El servidor no aceptó los datos"), json);
                intento = 0;
                // Cada envío confirmado (aunque después haya otro con cambios más nuevos).
                this._estado("enviado", { respuesta: json, datos });
                if (this.seq === seq) {             // nadie cambió nada mientras viajaba
                    this.datos = null;
                    borrar(this.clave);
                    this._estado("guardado", { respuesta: json });
                }
            } catch (e) {
                if (!e.transitorio) {
                    this.ultimoError = e;
                    this.corriendo = false;
                    this._estado("error", { error: e, conRespaldo: this.conRespaldo });
                    this._avisarEsperas(e);
                    return;                          // los datos quedan pendientes (y en el navegador)
                }
                const espera = ESPERAS_MS[Math.min(intento, ESPERAS_MS.length - 1)];
                intento += 1;
                this._estado("reintentando", { error: e, espera, intento, conRespaldo: this.conRespaldo });
                await this.sueno.dormir(espera);
            }
        }
        this.corriendo = false;
        this._avisarEsperas(null);
    }
}

/** Un envío con reintentos ante fallas transitorias (sin cola ni copia local). */
async function enviar(url, datos, { onReintento = () => {}, maxEsperaMs = 120000 } = {}) {
    const cuerpo = JSON.stringify(datos);
    const limite = Date.now() + maxEsperaMs;
    const sueno = dormilon();
    const alVolver = () => sueno.despertar();
    global.addEventListener("online", alVolver);
    try {
        for (let intento = 0; ; intento++) {
            try {
                return await intentar(url, cuerpo);
            } catch (e) {
                const espera = ESPERAS_MS[Math.min(intento, ESPERAS_MS.length - 1)];
                if (!e.transitorio || Date.now() + espera > limite) throw e;
                onReintento({ error: e, espera, intento: intento + 1 });
                await sueno.dormir(espera);
            }
        }
    } finally {
        global.removeEventListener("online", alVolver);
    }
}

global.EnvioSeguro = {
    cola: (opciones) => new Cola(opciones),
    enviar,
    intentar,
    respaldo: leer,
    descartar: borrar,
};

})(window);
