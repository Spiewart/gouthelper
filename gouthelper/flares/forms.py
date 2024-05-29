from crispy_forms.bootstrap import InlineCheckboxes  # type: ignore
from crispy_forms.helper import FormHelper  # type: ignore
from crispy_forms.layout import HTML, Div, Fieldset, Layout  # type: ignore
from django import forms  # type: ignore
from django.utils import timezone  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore

from ..choices import YES_OR_NO_OR_NONE
from ..medhistorys.choices import MedHistoryTypes
from ..utils.forms import (
    ModelFormKwargMixin,
    forms_helper_insert_about_the_patient_legend,
    forms_helper_insert_cvdiseases,
    forms_helper_insert_dateofbirth,
    forms_helper_insert_gender,
    forms_helper_insert_medhistory,
)
from .choices import DIAGNOSED_CHOCIES
from .models import Flare


class FlareForm(
    ModelFormKwargMixin,
    forms.ModelForm,
):
    """
    ModelForm for creating Flare objects.
    """

    class Meta:
        model = Flare
        fields = (
            "crystal_analysis",
            "date_ended",
            "date_started",
            "joints",
            "onset",
            "redness",
            "diagnosed",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields.update(
            {
                "aspiration": forms.TypedChoiceField(
                    widget=forms.Select,
                    choices=YES_OR_NO_OR_NONE,
                    required=False,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields.update(
            {
                "crystal_analysis": forms.TypedChoiceField(
                    widget=forms.Select,
                    choices=YES_OR_NO_OR_NONE,
                    required=False,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[
            "crystal_analysis"
        ].help_text = f"Was monosodium urate found in \
{self.str_attrs.get('subject_the_pos')} synovial fluid?"
        self.fields["date_started"].help_text = f"When did {self.str_attrs.get('subject_the_pos')} symptoms start?"
        self.fields[
            "date_ended"
        ].help_text = f"When did {self.str_attrs.get('subject_the_pos')} symptoms resolve? \
<strong>Leave blank if symptoms are ongoing</strong>."
        self.fields["date_started"].widget.attrs.update({"class": "datepick"})
        self.fields["date_ended"].widget.attrs.update({"class": "datepick"})
        self.fields["joints"].label = "Joint(s)"
        self.fields["joints"].help_text = f"Which of {self.str_attrs.get('subject_the_pos')} joints were affected?"
        self.fields.update(
            {
                "onset": forms.TypedChoiceField(
                    widget=forms.Select,
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=(
                        "True" if self.instance.onset is True else "False" if not self.instance._state.adding else None
                    ),
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields["onset"].initial = (
            None if self.instance._state.adding else "True" if self.instance.onset is True else "False"
        )
        self.fields["onset"].label = "Rapid Onset"
        self.fields[
            "onset"
        ].help_text = f"Did {self.str_attrs.get('subject_the_pos')} symptoms start and peak \
in a day or less?"
        self.fields.update(
            {
                "redness": forms.TypedChoiceField(
                    widget=forms.Select,
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=(
                        "True"
                        if self.instance.redness is True
                        else "False"
                        if not self.instance._state.adding
                        else None
                    ),
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields["redness"].label = "Redness"
        self.fields[
            "redness"
        ].help_text = f"Are {self.str_attrs.get('subject_the_pos')} symptomatic joints \
red (erythematous)?"
        self.fields.update(
            {
                "urate_check": forms.TypedChoiceField(
                    widget=forms.Select,
                    choices=YES_OR_NO_OR_NONE,
                    required=False,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields["urate_check"].label = "Uric Acid Lab Check"
        self.fields[
            "urate_check"
        ].help_text = f"Was {self.str_attrs.get('subject_the_pos')} uric acid level \
checked during the flare?"
        self.fields.update(
            {
                "diagnosed": forms.TypedChoiceField(
                    widget=forms.Select,
                    choices=DIAGNOSED_CHOCIES,
                    required=False,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields["diagnosed"].help_text = _(
            f"Did the medical provider diagnose \
{self.str_attrs.get('subject_the_pos')} symptoms as a gout flare?"
        )
        self.fields["diagnosed"].initial = None
        self.fields.update(
            {
                "aspiration": forms.TypedChoiceField(
                    widget=forms.Select,
                    choices=YES_OR_NO_OR_NONE,
                    required=False,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields["aspiration"].label = "Joint Aspiration"
        self.fields["aspiration"].help_text = "Was a joint aspiration and crystal analysis performed?"
        self.fields.update(
            {
                "medical_evaluation": forms.TypedChoiceField(
                    widget=forms.Select,
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields["medical_evaluation"].label = "Medical Evaluation"
        self.fields[
            "medical_evaluation"
        ].help_text = f"Did {self.str_attrs.get('subject_the')} get an evaluation by a medical provider \
for these symptoms?"
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                "",
                Div(
                    HTML(
                        """
                        <hr size="3" color="dark">
                        <legend>About the Flare</legend>
                        """
                    ),
                    Div(
                        Div(
                            Div(
                                InlineCheckboxes("joints"),
                                css_class="col",
                            ),
                            css_class="row",
                            css_id="joints",
                        ),
                        Div(
                            Div(
                                "onset",
                                css_class="col",
                            ),
                            css_class="row",
                            css_id="onset",
                        ),
                        Div(
                            Div(
                                "redness",
                                css_class="col",
                            ),
                            css_class="row",
                            css_id="redness",
                        ),
                        Div(
                            Div(
                                "date_started",
                                css_class="col",
                            ),
                            css_class="row",
                            css_id="date_started",
                        ),
                        Div(
                            Div(
                                "date_ended",
                                css_class="col",
                            ),
                            css_class="row",
                            css_id="date_ended",
                        ),
                        css_id="about-the-flare",
                    ),
                    HTML(
                        """
                        <hr size="3" color="dark">
                        <legend>Medical Information</legend>
                        """
                    ),
                    Div(
                        Div(
                            Div(
                                "medical_evaluation",
                                css_class="col",
                            ),
                            css_class="row",
                            css_id="medical_evaluation",
                        ),
                        Div(
                            Div(
                                "diagnosed",
                                css_class="col",
                            ),
                            css_class="row",
                            css_id="diagnosed",
                        ),
                        Div(
                            Div(
                                HTML(
                                    """
                                    {% load crispy_forms_tags %}
                                    {% crispy aki_form %}
                                    """
                                ),
                                css_class="col",
                            ),
                            css_class="row",
                            css_id="aki",
                        ),
                        Div(
                            Div(
                                "aspiration",
                                css_class="col",
                            ),
                            css_class="row",
                            css_id="aspiration",
                        ),
                        Div(
                            Div(
                                "crystal_analysis",
                                css_class="col",
                            ),
                            css_class="row",
                            css_id="crystal_analysis",
                        ),
                        Div(
                            Div(
                                "urate_check",
                                css_class="col",
                            ),
                            css_class="row",
                            css_id="urate_check",
                        ),
                        Div(
                            Div(
                                HTML(
                                    """
                                    {% load crispy_forms_tags %}
                                    {% crispy urate_form %}
                                    """
                                ),
                                css_class="col",
                            ),
                            css_class="row",
                            css_id="urate",
                        ),
                        css_id="medical-evaluation",
                    ),
                ),
            ),
        )
        forms_helper_insert_about_the_patient_legend(form=self)
        # Again check if there is a patient and if not, insert DateOfBirthForm, GenderForm, and MenopauseForm
        if not self.patient:
            forms_helper_insert_dateofbirth(layout=self.helper.layout)
            forms_helper_insert_gender(layout=self.helper.layout)
            forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.MENOPAUSE, layout=self.helper.layout)
        # Insert CVDiseasesForm
        forms_helper_insert_cvdiseases(layout=self.helper.layout, subject_the=self.str_attrs["subject_the"])
        # Insert CkdForm
        forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.CKD, layout=self.helper.layout)
        # Again check if there is a patient and if not, insert the GoutForm
        if not self.patient:
            forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.GOUT, layout=self.helper.layout)

    def clean(self):
        cleaned_data = super().clean()
        aspiration = cleaned_data.get("aspiration", None)
        crystal_analysis = cleaned_data.get("crystal_analysis", None)
        date_started = cleaned_data.get("date_started", None)
        date_ended = cleaned_data.get("date_ended", None)
        medical_evaluation = cleaned_data.get("medical_evaluation")
        diagnosed = cleaned_data.get("diagnosed", None)
        urate_check = cleaned_data.get("urate_check", None)
        if date_started and date_started > timezone.now().date():
            self.add_error("date_started", "Date started must be in the past.")
        if date_started and date_ended:
            if date_started > date_ended:
                self.add_error("date_ended", "Date ended must be after date started.")
        if medical_evaluation:
            if aspiration is None:
                self.add_error(
                    "aspiration",
                    f"Joint aspiration must be selected if {self.str_attrs.get('subject_the')} had a \
medical examination.",
                )
            elif aspiration and crystal_analysis is None:
                self.add_error(
                    "crystal_analysis", "Results of crystal analysis must be selected if aspiration is selected."
                )
            if urate_check is None:
                self.add_error(
                    "urate_check", "Uric acid lab check must be selected if a clinician evaluated the flare."
                )
        else:
            if diagnosed is not None:
                cleaned_data["diagnosed"] = ""
            if aspiration is not None:
                cleaned_data["aspiration"] = ""
            if crystal_analysis is not None:
                cleaned_data["crystal_analysis"] = ""
            if urate_check is not None:
                cleaned_data["urate_check"] = ""
        return cleaned_data
