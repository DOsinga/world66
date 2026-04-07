from django import template

register = template.Library()


@register.filter
def replace_underscores(value):
    return str(value).replace("_", " ")
