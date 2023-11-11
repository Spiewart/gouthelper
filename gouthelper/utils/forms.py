from django.db.models import DateTimeField  # type: ignore
from django.forms import ModelForm  # type: ignore

from ..utils.exceptions import EmptyRelatedModel  # type: ignore


def make_custom_datetimefield(f, **kwargs):
    """Method to use to override the default DateTimeField widget
    and truncate the datetime to just the date."""
    # Need to call with **kwargs
    # https://stackoverflow.com/questions/14328381/django-error-unexpected-keyword-argument-widget
    if isinstance(f, DateTimeField):
        # return form field with your custom widget here...
        formfield = f.formfield(**kwargs)
        formfield.widget.format = "%m/%d/%Y"
        return formfield
    return f.formfield(**kwargs)


class OneToOneForm(ModelForm):
    class Meta:
        abstract = True

    def check_for_value(self):
        if self.cleaned_data["value"] is not None:
            pass
        else:
            raise EmptyRelatedModel
