from django import template

from ..permisos import es_admin_conteo, es_contador, puede_depurar

register = template.Library()


@register.filter(name="es_contador")
def filtro_es_contador(user):
    """Uso: {% load conteo_tags %} ... {% if user|es_contador %}"""
    return es_contador(user)


@register.filter(name="es_admin_conteo")
def filtro_es_admin_conteo(user):
    """Uso: {% load conteo_tags %} ... {% if user|es_admin_conteo %}"""
    return es_admin_conteo(user)


@register.filter(name="puede_depurar")
def filtro_puede_depurar(user):
    """Uso: {% load conteo_tags %} ... {% if user|puede_depurar %}"""
    return puede_depurar(user)
