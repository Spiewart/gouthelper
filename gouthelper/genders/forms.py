from crispy_forms.helper import FormHelper  # type: ignore
from django import forms  # type: ignore
from django.urls import reverse_lazy  # type: ignore
from django.utils.text import format_lazy  # type: ignore

from ..utils.exceptions import EmptyRelatedModel  # type: ignore]
from ..utils.forms import ModelFormKwargMixin  # type: ignore
from .models import Gender


class GenderForm(ModelFormKwargMixin, forms.ModelForm):
    class Meta:
        model = Gender
        fields = ("value",)

    prefix = "gender"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["value"].help_text = format_lazy(
            """What is {} biological sex? <a href="{}" target="_next">Why do we need to know?</a>""",
            self.str_attrs["subject_the_pos"],
            reverse_lazy("genders:about"),
        )
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
