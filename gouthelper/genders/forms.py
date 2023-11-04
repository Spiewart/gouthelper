from crispy_forms.helper import FormHelper  # type: ignore
from django import forms  # type: ignore

from ..utils.exceptions import EmptyRelatedModel  # type: ignore
from .models import Gender


class GenderForm(forms.ModelForm):
    class Meta:
        model = Gender
        fields = ("value",)

    prefix = "gender"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["value"].label = "Gender"
        self.helper = FormHelper()
        self.helper.form_tag = False

    def check_for_value(self):
        value = self.cleaned_data["value"]
        if value != 0 and not value:
            raise EmptyRelatedModel

    @property
    def required_fields(self) -> list[str]:
        """Return a list of required fields"""
        return ["value"]


class GenderFormOptional(GenderForm):
    """Subclass of GenderForm with value field not required."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["value"].required = False
