from crispy_forms.helper import FormHelper  # type: ignore
from crispy_forms.layout import Field, Layout  # type: ignore
from django import forms  # type: ignore

from ..treatments.choices import Treatments
from ..utils.helpers import get_str_attrs
from .models import MedAllergy


class MedAllergyTreatmentForm(forms.ModelForm):
    """Form for creating MedAllergy Objects."""

    class Meta:
        model = MedAllergy
        exclude = ["flareaid", "ppxaid", "sideeffects", "treatment", "ultaid", "user"]

    def __init__(self, *args, **kwargs):
        self.patient = kwargs.pop("patient", None)
        self.request_user = kwargs.pop("request_user", None)
        self.str_attrs = kwargs.pop("str_attrs", None)
        if not self.str_attrs:
            self.str_attrs = get_str_attrs(self, self.patient, self.request_user)
        self.treatment = kwargs.pop("treatment")
        super().__init__(*args, **kwargs)
        self.value = f"medallergy_{self.treatment}"
        self.fields.update({self.value: forms.BooleanField(required=False)})
        self.fields[self.value].label = Treatments[self.treatment].label
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field(self.value, wrapper_class="medallergy_select"),
        )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data[self.value]:
            cleaned_data["treatment"] = self.treatment
        return cleaned_data
