from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Django template tidak bisa lookup dict pakai key dari variabel lain
    (cuma bisa literal). Filter ini dipakai untuk prefill nilai field
    dinamis: {{ field_values|get_item:field.name_attribute }}
    """
    if not dictionary:
        return ''
    return dictionary.get(key, '')
