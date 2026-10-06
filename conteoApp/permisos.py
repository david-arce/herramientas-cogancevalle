"""Reglas de acceso del módulo de conteo, en un solo lugar."""

# Usuarios que administran el conteo (asignar productos, ver diferencias, exportar).
USUARIOS_ADMIN = ("DBENITEZ", "CHINCAPI", "PROJAS", "LAMAYA", "AGRAJALE", "admin")


def es_admin_conteo(user):
    return getattr(user, "is_authenticated", False) and user.username in USUARIOS_ADMIN


def es_contador(user):
    """
    Contador = usuario con permiso para ver sus tareas (conteoApp.view_tarea)
    que no es administrador del conteo ni superusuario.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser or es_admin_conteo(user):
        return False
    return user.has_perm("conteoApp.view_tarea")


# Único usuario que puede depurar (eliminar) conteos antiguos.
USUARIO_DEPURACION = "admin"


def puede_depurar(user):
    return getattr(user, "is_authenticated", False) and user.username == USUARIO_DEPURACION
