from django import template

register = template.Library()

@register.filter
def times(number):
    """
    Returns a range of numbers from 0 to number-1
    Usage: {% for i in number|times %}...{% endfor %}
    """
    try:
        return range(int(number))
    except (ValueError, TypeError):
        return range(0)

@register.filter
def divided_by(value, arg):
    """
    Divides the value by the argument
    """
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def multiply(value, arg):
    """
    Multiplies the value by the argument
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def add(value, arg):
    """
    Adds the arg to the value
    """
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def get_item(dictionary, key):
    """
    Gets an item from a dictionary using the key
    Usage: {{ dictionary|get_item:key }}
    """
    if dictionary is None:
        return None
    
    try:
        return dictionary.get(key)
    except (AttributeError, KeyError, TypeError):
        return None