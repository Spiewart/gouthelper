import re  # type: ignore
from typing import TYPE_CHECKING

from django import template  # type: ignore
from django.template.base import TemplateSyntaxError  # type: ignore
from django.utils.html import mark_safe  # type: ignore

from .ethnicitys.helpers import ethnicitys_hlab5801_risk
from .treatments.choices import Treatments, TrtTypes
from .utils.helpers import TrtDictStr

if TYPE_CHECKING:
    from .defaults.models import UltAidSettings
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


@register.filter(name="pop_key")
def pop_key(dictionary, key):
    return dictionary.pop(key)


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


@register.filter(name="is_list")
def is_list(template_object):
    """Template tag to return a boolean if object is a list"""
    return isinstance(template_object, list)


@register.filter(name="comprehend_list_attr")
def comprehend_list_attr(template_list, attr):
    """Takes a list of objects and returns a list of the attribute of each object."""
    return [getattr(obj, attr) for obj in template_list]


@register.filter(name="get_partial_str")
def get_partial_str(template_string, arg):
    """Return a string with the arg appended to the template_string and followed by ".html"."""
    return f"{template_string}{arg}.html"


@register.filter(name="concat_str_with_underscore")
def concat_str_with_underscore(template_string, arg):
    """Return a string with the arg appended to the template_string and followed by "_"."""
    return f"{template_string}_{arg}"


@register.simple_tag(name="trt_dict_to_str")
def trt_dict_to_str(dosing_dict: dict, trttype: TrtTypes, treatment: Treatments) -> str:
    """Return a string explaining a trt_dict's recommendations."""
    return TrtDictStr(dosing_dict, trttype, treatment).trt_dict_to_str()


@register.simple_tag(name="trt_dose_adj_to_str")
def trt_dose_adj_to_str(
    dosing_dict: dict,
    ultaidsettings: "UltAidSettings",
) -> str:
    """Return a string explaining a trt_dict's recommendations."""
    return mark_safe(
        f"increase the dose {dosing_dict['dose_adj']} mg every {int(ultaidsettings.dose_adj_interval.days / 7)} \
weeks until uric acid is at <a class='samepage-link' href='#goalurate'>goal</a>"
    )
