from crispy_forms.bootstrap import InlineCheckboxes  # type: ignore
from crispy_forms.helper import FormHelper  # type: ignore
from crispy_forms.layout import HTML, Div, Fieldset, Layout  # type: ignore
from django import forms  # type: ignore
from django.utils import timezone  # type: ignore

from ..choices import YES_OR_NO_OR_NONE
from ..medhistorys.choices import MedHistoryTypes
from ..utils.form_helpers import (
    forms_helper_insert_cvdiseases,
    forms_helper_insert_dateofbirth,
    forms_helper_insert_gender,
    forms_helper_insert_medhistory,
)
from .models import Flare


class FlareForm(
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
        self.fields["crystal_analysis"].help_text = "Was monosodium urate found in the synovial fluid?"
        self.fields["joints"].label = "Joint(s)"
        self.fields["joints"].help_text = "Which joints was it in?"
        self.fields.update(
            {
                "onset": forms.TypedChoiceField(
                    widget=forms.Select,
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields["onset"].label = "Rapid Onset"
        self.fields["onset"].help_text = "Symptoms start and peak in a day or less?"
        self.fields.update(
            {
                "redness": forms.TypedChoiceField(
                    widget=forms.Select,
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields["redness"].label = "Redness"
        self.fields["redness"].help_text = "Is(are) the joint(s) red (erythematous)?"
        self.fields.update(
            {
                "urate_check": forms.TypedChoiceField(
                    widget=forms.Select,
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields["urate_check"].label = "Uric Acid Level"
        self.fields["urate_check"].help_text = "Was the uric acid level checked during the flare?"
        self.fields.update(
            {
                "diagnosed": forms.TypedChoiceField(
                    widget=forms.Select,
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
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
                        css_id="about-the-flare",
                    ),
                ),
                Div(
                    HTML(
                        """
                        <hr size="3" color="dark">
                        <legend>About the Patient</legend>
                        """
                    ),
                    css_id="about-patient",
                ),
            ),
        )
        forms_helper_insert_dateofbirth(layout=self.helper.layout)
        forms_helper_insert_gender(layout=self.helper.layout)
        # Insert MenopauseForm
        forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.MENOPAUSE, layout=self.helper.layout)
        # Insert CVDiseasesForm
        forms_helper_insert_cvdiseases(layout=self.helper.layout)
        # Insert CkdForm
        forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.CKD, layout=self.helper.layout)
        # Insert GoutForm
        forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.GOUT, layout=self.helper.layout)

    def clean(self):
        cleaned_data = super().clean()
        aspiration = cleaned_data.get("aspiration", None)
        crystal_analysis = cleaned_data.get("crystal_analysis", None)
        date_started = cleaned_data.get("date_started", None)
        date_ended = cleaned_data.get("date_ended", None)
        diagnosed = cleaned_data.get("diagnosed", None)
        if date_started and date_started > timezone.now().date():
            self.add_error("date_started", "Date started must be in the past.")
        if date_started and date_ended:
            if date_started > date_ended:
                self.add_error("date_ended", "Date ended must be after date started.")
        if diagnosed and aspiration is None:
            self.add_error("aspiration", "Joint aspiration must be selected if a clinician diagnosed the flare.")
        # If diagnosed is False (or None = not selected), crystal_analysis must be None
        if not diagnosed:
            if crystal_analysis is not None:
                cleaned_data["crystal_analysis"] = ""
        # If aspiration is False (or None = not selected), then crystal_analysis must be None
        elif not aspiration:
            if crystal_analysis is not None:
                cleaned_data["crystal_analysis"] = ""
        if aspiration and crystal_analysis is None:
            self.add_error(
                "crystal_analysis", "Results of crystal analysis must be selected if aspiration is selected."
            )
        return cleaned_data
