from crispy_forms.helper import FormHelper  # pylint:disable=E0401 # type: ignore
from crispy_forms.layout import HTML, Div, Fieldset, Layout  # pylint:disable=E0401 # type: ignore
from django import forms  # pylint:disable=E0401 # type: ignore

from ..medhistorys.choices import MedHistoryTypes
from ..utils.forms import (
    forms_helper_insert_about_the_patient,
    forms_helper_insert_dateofbirth,
    forms_helper_insert_gender,
    forms_helper_insert_medhistory,
)
from ..utils.helpers import get_str_attrs
from .models import Ult


class UltForm(
    forms.ModelForm,
):
    """
    ModelForm for creating Ult objects.
    """

    class Meta:
        model = Ult
        fields = (
            "freq_flares",
            "num_flares",
        )

    def __init__(self, *args, **kwargs):
        self.patient = kwargs.pop("patient", None)
        self.request_user = kwargs.pop("request_user", None)
        self.str_attrs = kwargs.pop("str_attrs", None)
        if not self.str_attrs:
            self.str_attrs = get_str_attrs(self, self.patient, self.request_user)
        super().__init__(*args, **kwargs)
        self.fields[
            "freq_flares"
        ].help_text = f"How many gout flares {self.str_attrs['query']} {self.str_attrs['subject_the']} have per year?"
        self.fields[
            "num_flares"
        ].help_text = f"How many gout flares {self.str_attrs['pos']} {self.str_attrs['subject_the']} had in \
{self.str_attrs['gender_pos']} life?"
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                "",
                Div(
                    HTML(
                        f"""
                        <hr size="3" color="dark">
                        <legend>About {self.str_attrs['subject_the_pos']} gout</legend>
                        """
                    ),
                    Div(
                        Div(
                            "num_flares",
                            css_class="col",
                        ),
                        css_class="row",
                        css_id="num_flares",
                    ),
                    Div(
                        Div(
                            "freq_flares",
                            css_class="col",
                        ),
                        css_class="row",
                        css_id="freq_flares",
                    ),
                    css_id="about-the-gout",
                ),
            ),
        )
        forms_helper_insert_about_the_patient(layout=self.helper.layout)
        forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.CKD, layout=self.helper.layout)
        if not self.patient:
            forms_helper_insert_dateofbirth(layout=self.helper.layout)
            forms_helper_insert_gender(layout=self.helper.layout)
        forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.EROSIONS, layout=self.helper.layout)
        forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.HYPERURICEMIA, layout=self.helper.layout)
        forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.TOPHI, layout=self.helper.layout)
        forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.URATESTONES, layout=self.helper.layout)

    def clean(self):
        """Overwritten to raise ValidationError if the form indicates a
        User has only had one (or zero) flares but reported a frequency of flares or
        that they have had two or more flares but did not report a frequency of flares
        , either of which would violate one of the Ult model CheckConstraints and raise
        a nonsensical error."""
        cleaned_data = super().clean()
        num_flares = cleaned_data.get("num_flares")
        freq_flares = cleaned_data.get("freq_flares")
        if (num_flares == Ult.FlareNums.ZERO or num_flares == Ult.FlareNums.ONE) and freq_flares:
            self.add_error(
                "freq_flares",
                f"You indicated that {self.str_attrs['subject_the']} {self.str_attrs['pos']} had one or zero flares, \
but also indicated a frequency of flares. This doesn't make sense to us. Please correct.",
            )
        elif num_flares == Ult.FlareNums.TWOPLUS and not freq_flares:
            self.add_error(
                "freq_flares",
                f"You indicated that {self.str_attrs['subject_the']} {self.str_attrs['pos']} had two or more flares, \
but did not indicate a frequency of flares. This doesn't make sense to us. Please correct.",
            )
        return cleaned_data
