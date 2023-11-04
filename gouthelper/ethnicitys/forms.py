from crispy_forms.helper import FormHelper  # type: ignore
from django import forms  # type: ignore

from ..utils.exceptions import EmptyRelatedModel  # type: ignore
from .models import Ethnicity


class EthnicityForm(forms.ModelForm):
    class Meta:
        model = Ethnicity
        fields = ("value",)

    prefix = "ethnicity"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["value"].label = "Ethnicity"
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


class EthnicityFormOptional(EthnicityForm):
    """Subclass of EthnicityForm with value field not required.""" ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["value"].required = False
