# ══════════════════════════════════════════════════════════════════
#  AJUSTES · CUENTAS CONTABLES  (CRUD sencillo)
#
#  El modelo CuentasContables es managed=False y no declara llave
#  primaria, así que no se depende de la columna "id": todo se hace
#  por el número de cuenta y el INSERT va en SQL directo (Model.create
#  en PostgreSQL pide "RETURNING id" y fallaría si la tabla no la tiene).
# ══════════════════════════════════════════════════════════════════
import json

from django.contrib.auth.decorators import login_required
from django.db import connection, transaction
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .models import CuentasContables

USUARIOS_AJUSTES = ['admin', 'NICOLAS']
MAX_NOMBRE = 255


def _permitido(request):
    return request.user.username in USUARIOS_AJUSTES


def _sin_permiso():
    return JsonResponse({'success': False, 'error': 'Sin permisos'}, status=403)


def _leer_cuenta(valor):
    texto = str(valor if valor is not None else '').strip()
    if not texto.isdigit():
        raise ValueError('La cuenta debe ser un número entero positivo')
    return int(texto)


def _leer_nombre(valor):
    nombre = str(valor or '').strip()
    if not nombre:
        raise ValueError('El nombre de la cuenta es obligatorio')
    if len(nombre) > MAX_NOMBRE:
        raise ValueError(f'El nombre no puede superar {MAX_NOMBRE} caracteres')
    return nombre


def _body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        raise ValueError('JSON inválido')


# ── Página ────────────────────────────────────────────────────────
@login_required
def ajustes_cuentas_contables(request):
    if not _permitido(request):
        return HttpResponseForbidden("⛔ No tienes permisos para acceder a esta página.")
    return render(request, 'ajustes/cuentas_contables.html')


# ── Listar ────────────────────────────────────────────────────────
@login_required
@require_GET
def listar_cuentas_contables(request):
    if not _permitido(request):
        return _sin_permiso()
    data = list(
        CuentasContables.objects
        .order_by('cuenta')
        .values('cuenta', 'nom_cuenta')
    )
    for d in data:
        d['cuenta'] = '' if d['cuenta'] is None else str(d['cuenta'])
        d['nom_cuenta'] = d['nom_cuenta'] or ''
    return JsonResponse({'success': True, 'data': data, 'total': len(data)})


# ── Crear ─────────────────────────────────────────────────────────
@login_required
@require_POST
def crear_cuenta_contable(request):
    if not _permitido(request):
        return _sin_permiso()
    try:
        body = _body(request)
        cuenta = _leer_cuenta(body.get('cuenta'))
        nombre = _leer_nombre(body.get('nom_cuenta'))
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

    with transaction.atomic():
        if CuentasContables.objects.filter(cuenta=cuenta).exists():
            return JsonResponse(
                {'success': False, 'error': f'La cuenta {cuenta} ya existe'}, status=400
            )
        with connection.cursor() as cursor:
            cursor.execute(
                f'INSERT INTO {CuentasContables._meta.db_table} (cuenta, nom_cuenta) VALUES (%s, %s)',
                [cuenta, nombre],
            )
    return JsonResponse({'success': True, 'cuenta': str(cuenta), 'nom_cuenta': nombre})


# ── Editar ────────────────────────────────────────────────────────
@login_required
@require_POST
def actualizar_cuenta_contable(request):
    """Body: { cuenta_original, cuenta, nom_cuenta }  (se puede cambiar el número)."""
    if not _permitido(request):
        return _sin_permiso()
    try:
        body = _body(request)
        original = _leer_cuenta(body.get('cuenta_original'))
        cuenta = _leer_cuenta(body.get('cuenta'))
        nombre = _leer_nombre(body.get('nom_cuenta'))
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

    with transaction.atomic():
        if cuenta != original and CuentasContables.objects.filter(cuenta=cuenta).exists():
            return JsonResponse(
                {'success': False, 'error': f'La cuenta {cuenta} ya existe'}, status=400
            )
        n = CuentasContables.objects.filter(cuenta=original).update(cuenta=cuenta, nom_cuenta=nombre)
    if not n:
        return JsonResponse({'success': False, 'error': 'Cuenta no encontrada'}, status=404)
    return JsonResponse({'success': True, 'cuenta': str(cuenta), 'nom_cuenta': nombre})


# ── Eliminar ──────────────────────────────────────────────────────
@login_required
@require_POST
def eliminar_cuenta_contable(request):
    """Body: { cuenta }"""
    if not _permitido(request):
        return _sin_permiso()
    try:
        cuenta = _leer_cuenta(_body(request).get('cuenta'))
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

    eliminados, _ = CuentasContables.objects.filter(cuenta=cuenta).delete()
    if not eliminados:
        return JsonResponse({'success': False, 'error': 'Cuenta no encontrada'}, status=404)
    return JsonResponse({'success': True, 'eliminados': eliminados})
