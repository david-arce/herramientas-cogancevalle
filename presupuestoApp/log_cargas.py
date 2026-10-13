"""Logs de inicio y fin de las cargas a Cuenta 5.

Uso:

    with log_carga("cuenta5_base", request, lote="1/12") as info:
        ...                      # la carga
        info["registros"] = 2000 # lo que se quiera ver en la línea de FIN

Escribe en el logger "presupuestoApp.cargas":

    INICIO carga cuenta5_base | usuario=NICOLAS lote=1/12
    FIN    carga cuenta5_base | 4.37 s | usuario=NICOLAS lote=1/12 registros=2000 (458 reg/s)
    ERROR  carga cuenta5_base | 0.82 s | ... (con el traceback)

Si settings.py no tiene LOGGING para este logger, se le pone un handler a
consola (stderr) para que los mensajes salgan igual en los logs del servidor
(gunicorn, runserver, journalctl...). Si settings.py sí lo configura, se
respeta esa configuración
"""
import logging
import time
from contextlib import contextmanager

logger = logging.getLogger("presupuestoApp.cargas")
logger.setLevel(logging.INFO)

if not logger.hasHandlers():
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(_handler)
    logger.propagate = False


def _usuario(request):
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return user.get_username()
    return "anónimo"


def _texto(datos):
    return " ".join(f"{k}={v}" for k, v in datos.items() if v not in (None, ""))


@contextmanager
def log_carga(nombre, request=None, **contexto):
    """Registra INICIO, FIN (con duración) o ERROR de una carga."""
    base = {"usuario": _usuario(request) if request is not None else None, **contexto}
    logger.info("INICIO carga %s | %s", nombre, _texto(base))
    inicio = time.perf_counter()
    info = {}
    try:
        yield info
    except Exception:
        logger.exception("ERROR  carga %s | %.2f s | %s %s",
                         nombre, time.perf_counter() - inicio, _texto(base), _texto(info))
        raise
    duracion = time.perf_counter() - inicio
    velocidad = ""
    registros = info.get("registros")
    if isinstance(registros, int) and registros and duracion > 0:
        velocidad = f" ({registros / duracion:.0f} reg/s)"
    logger.info("FIN    carga %s | %.2f s | %s %s%s",
                nombre, duracion, _texto(base), _texto(info), velocidad)
