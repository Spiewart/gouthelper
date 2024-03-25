from crispy_forms.helper import FormHelper  # type: ignore
from django.forms import IntegerField, NumberInput  # type: ignore
from django.urls import reverse_lazy
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from ..utils.exceptions import EmptyRelatedModel
from ..utils.forms import OneToOneForm
from ..utils.helpers import get_str_attrs
from .helpers import yearsago
from .models import DateOfBirth


class DateOfBirthForm(OneToOneForm):
    class Meta:
        model = DateOfBirth
        fields = ("value",)
        widgets = {
            "value": NumberInput(attrs={"min": 18, "max": 120, "step": 1}),
        }

    prefix = "dateofbirth"

    def __init__(self, *args, **kwargs):
        self.patient = kwargs.pop("patient", None)
        self.request_user = kwargs.pop("request_user", None)
        self.str_attrs = kwargs.pop("str_attrs", None)
        if not self.str_attrs:
            self.str_attrs = get_str_attrs(self, self.patient, self.request_user)
        super().__init__(*args, **kwargs)
        self.fields["value"] = IntegerField(
            label=_("Age"),
            help_text=format_lazy(
                """How old {} {} (range: 18-120)? <a href="{}" target="_next">Why do we need to know?</a>""",
                self.str_attrs["tobe"],
                self.str_attrs["subject_the"],
                reverse_lazy("dateofbirths:about"),
            ),
            min_value=18,
            max_value=120,
            required=True,
        )
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
