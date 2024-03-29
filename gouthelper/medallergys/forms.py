from crispy_forms.helper import FormHelper  # type: ignore
from crispy_forms.layout import Div, Field, Layout  # type: ignore
from django import forms  # type: ignore
from django.utils.html import mark_safe

from ..treatments.choices import Treatments
from ..utils.helpers import get_str_attrs
from .models import MedAllergy


class MedAllergyTreatmentForm(forms.ModelForm):
    """Form for creating MedAllergy Objects."""

    class Meta:
        model = MedAllergy
        exclude = ["flareaid", "matype", "ppxaid", "other", "sideeffects", "treatment", "ultaid", "user"]

    def __init__(self, *args, **kwargs):
        self.patient = kwargs.pop("patient", None)
        self.request_user = kwargs.pop("request_user", None)
        self.str_attrs = kwargs.pop("str_attrs", None)
        if not self.str_attrs:
            self.str_attrs = get_str_attrs(self, self.patient, self.request_user)
        self.treatment = kwargs.pop("treatment")
        super().__init__(*args, **kwargs)
        self.value = f"medallergy_{self.treatment}"
        self.fields.update(
            {
                self.value: forms.BooleanField(
                    required=False,
                    widget=forms.CheckboxInput(attrs={"class": "slider form-control"}),
                )
            }
        )
        self.fields[self.value].label = Treatments[self.treatment].label

        # If treatment is not allopurinol or febuxostat, remove the matype field
        if self.treatment in [Treatments.ALLOPURINOL, Treatments.FEBUXOSTAT]:
            trt_matype = f"{self.treatment}_matype"
            # Add matype field with a choice of hypersensitivity syndrome
            self.fields.update(
                {
                    trt_matype: forms.BooleanField(
                        required=False, widget=forms.CheckboxInput(attrs={"class": "slider form-control"})
                    )
                }
            )
            self.fields[trt_matype].label = "Hypersensitivity Syndrome"
            self.fields[trt_matype].help_text = mark_safe(
                "Was this a <a target='_next' \
href='https://en.wikipedia.org/wiki/Allopurinol_hypersensitivity_syndrome'>hypersensitivity reaction</a>?"
            )
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Div(
                    Field(
                        self.value,
                        css_class="form-check-input",
                        wrapper_class="medallergy_select form-check form-switch",
                    ),
                    css_class="col",
                ),
                css_class="row",
            )
        )

        if self.treatment in [Treatments.ALLOPURINOL, Treatments.FEBUXOSTAT]:
            self.helper.layout[0][0].append(
                Field(
                    f"{self.treatment}_matype",
                    css_class="form-check-input",
                    wrapper_class=f"{self.treatment}_matype_select form-check form-switch",
                ),
            )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data[self.value]:
            cleaned_data["treatment"] = self.treatment
        if cleaned_data.get(f"{self.treatment}_matype", None) is True:
            cleaned_data.update({f"{self.treatment}_matype": MedAllergy.MaTypes.HYPERSENSITIVITY})
        else:
            cleaned_data.update({f"{self.treatment}_matype": None})
        return cleaned_data
