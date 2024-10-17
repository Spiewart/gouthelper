from datetime import date
from itertools import chain
from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from django.http import HttpRequest


def dummy_get_response(request: "HttpRequest"):
    return None


def date_days_ago(days: int) -> date:
    return (timezone.now() - timezone.timedelta(days=days)).date()


def datetime_days_ago(days: int):
    return timezone.now() - timezone.timedelta(days=days)


def date_years_ago(years: int) -> date:
    return (timezone.now() - timezone.timedelta(days=365 * years)).date()


def model_instance_to_dict(instance, fields: list[str] = None, exclude: list[str] = None):
    """Converts a model instance to a dictionary with its field names as keys and their values as values.
    It does NOT omit non-editable fields like model_to_dict from django.forms.
    Values are native Python or Django types, not JSON serialized.
    # https://stackoverflow.com/questions/21925671/convert-django-model-object-to-dict-with-all-of-the-fields-intact"""
    opts = instance._meta
    data = {}

    def get_all_model_field_names(opts):
        return (
            [f.name for f in opts.concrete_fields]
            + [f.name for f in opts.private_fields]
            + [f.name for f in opts.many_to_many]
        )

    all_fields = get_all_model_field_names(opts)

    if fields or exclude:
        invalid_fields = []
        if fields:
            for field in fields:
                if field not in all_fields:
                    invalid_fields.append(field)
        if exclude:
            for field in exclude:
                if field not in all_fields:
                    invalid_fields.append(field)
        if invalid_fields:
            raise ValueError(f"Invalid field(s) for model {instance.__class__.__name__}: {', '.join(invalid_fields)}")

    for f in chain(opts.concrete_fields, opts.private_fields):
        if not fields or f.name in fields and (f.name not in exclude if exclude else True):
            data[f.name] = f.value_from_object(instance)
    for f in opts.many_to_many:
        data[f.name] = [i.id for i in f.value_from_object(instance)]
    return data
