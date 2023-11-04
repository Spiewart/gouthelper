import re  # type: ignore
from typing import TYPE_CHECKING

from django import template  # type: ignore
from django.template.base import TemplateSyntaxError  # type: ignore

from .ethnicitys.helpers import ethnicitys_hlab5801_risk

if TYPE_CHECKING:
    from .ethnicitys.models import Ethnicity

register = template.Library()

numeric_test = re.compile(r"^\d+$")
register = template.Library()


@register.filter(name="risk_ethnicity")
def risk_ethnicity(ethnicity: "Ethnicity") -> bool:
    """A custom filter that returns whether or not an ethnicity is a
    high-risk ethnicity for HLAB5801."""
    return ethnicitys_hlab5801_risk(ethnicity)


@register.filter
def getattribute(value, arg):
    """Gets an attribute of an object dynamically from a string name"""
    # https://stackoverflow.com/questions/844746/performing-a-getattr-style-lookup-in-a-django-template
    if hasattr(value, str(arg)):
        return getattr(value, arg)
    elif isinstance(value, dict) and arg in value:
        return value[arg]
    elif numeric_test.match(str(arg)) and len(value) > int(arg):
        return value[int(arg)]
    else:
        # instead of: settings.TEMPLATES[0]['OPTIONS']['string_if_invalid']
        raise TemplateSyntaxError("no attr: " + str(arg) + " for: " + str(value))


@register.filter
def index(indexable, i):
    return indexable[i]


@register.filter(name="get_key")
def get_key(dictionary, key):
    return dictionary.get(key)


@register.filter(name="get_keys")
def get_keys(dictionary):
    key_list = []
    if dictionary:
        for key in dictionary:
            key_list.append(key)
    return key_list


@register.filter(name="to_class_name")
def to_class_name(value):
    return value.__class__.__name__.lower()


@register.filter(name="list_to_name")
def list_to_name(value):
    if value:
        return value[0].__class__.__name__.lower()
    else:
        return "No " + str(value) + "'s."


@register.filter(name="ob_2_str")
def ob_2_str(value):
    """Converts object to string"""
    return str(value)


@register.simple_tag(name="get_trt_string")
def get_trt_string(flareaid, trt, trt_info):
    """Template tag to return a string for a FlareAid Treatment
    takes trt and trt_info as args from treatments dict items

    Args:
        flareaid: FlareAid instance
        trt: string from treatments dict
        trt_info: dict of treatment info from treatments dict

    Returns:
        _type_: _description_
    """
    return flareaid.treatment_string(trt, trt_info)
