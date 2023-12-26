from crispy_forms.helper import FormHelper  # type: ignore
from django.forms import IntegerField, NumberInput  # type: ignore
from django.utils.translation import gettext_lazy as _

from ..utils.exceptions import EmptyRelatedModel
from ..utils.forms import OneToOneForm
from .helpers import yearsago
from .models import DateOfBirth


class DateOfBirthForm(OneToOneForm):
    class Meta:
        model = DateOfBirth
        fields = ("value",)

    prefix = "dateofbirth"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["value"] = IntegerField(
            widget=NumberInput(attrs={"min": 18, "max": 120, "step": 1}),
        )
        self.fields["value"].label = _("Age")
        self.fields["value"].help_text = _("Enter age in years (range 18 to 120).")
        self.helper = FormHelper()
        self.helper.form_tag = False

    def check_for_value(self):
        value = self.cleaned_data["value"]
        if not value:
            raise EmptyRelatedModel

    @property
    def required_fields(self) -> list[str]:
        """Return a list of required fields"""
        return ["value"]

    def clean_value(self):
        # Overwritten to check if there is an int age and
        # convert it to a date of birth string
        value = self.cleaned_data["value"]
        if value:
            try:
                value = int(value)
            except ValueError:
                pass
            else:
                return yearsago(value)


class DateOfBirthFormOptional(DateOfBirthForm):
    """Subclass of DateOfBirthForm with value field not required."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["value"].required = False
