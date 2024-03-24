from crispy_forms.helper import FormHelper  # type: ignore
from django import forms  # type: ignore
from django.urls import reverse_lazy  # type: ignore
from django.utils.text import format_lazy  # type: ignore

from ..utils.exceptions import EmptyRelatedModel  # type: ignore
from ..utils.helpers import set_object_str_attrs  # type: ignore
from .models import Ethnicity


class EthnicityForm(forms.ModelForm):
    class Meta:
        model = Ethnicity
        fields = ("value",)

    prefix = "ethnicity"

    def __init__(self, *args, **kwargs):
        self.patient = kwargs.pop("patient", None)
        self.request_user = kwargs.pop("request_user", None)
        self.str_attrs = kwargs.pop("str_attrs", None)
        if not self.str_attrs:
            self.str_attrs = set_object_str_attrs(self, self.patient, self.request_user)
        super().__init__(*args, **kwargs)
        self.fields["value"].help_text = (
            format_lazy(
                """What is {} ethnicity or race? <a href="{}" target="_next">Why do we need to know?</a>""",
                self.str_attrs["subject_the_pos"],
                reverse_lazy("ethnicitys:about"),
            ),
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


class EthnicityFormOptional(EthnicityForm):
    """Subclass of EthnicityForm with value field not required.""" ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["value"].required = False
