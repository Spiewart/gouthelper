from crispy_forms.helper import FormHelper  # type: ignore
from crispy_forms.layout import HTML, Div, Field, Fieldset, Layout  # type: ignore
from django import forms  # type: ignore
from django.utils.safestring import mark_safe  # type: ignore

from ..choices import YES_OR_NO_OR_NONE
from ..medhistorys.choices import MedHistoryTypes
from .models import (
    Allopurinolhypersensitivity,
    Angina,
    Anticoagulation,
    Bleed,
    Cad,
    Chf,
    Ckd,
    Colchicineinteraction,
    Diabetes,
    Erosions,
    Febuxostathypersensitivity,
    Gastricbypass,
    Gout,
    Heartattack,
    Hypertension,
    Hyperuricemia,
    Ibd,
    MedHistory,
    Menopause,
    Organtransplant,
    Pvd,
    Stroke,
    Tophi,
    Uratestones,
    Xoiinteraction,
)


class MedHistoryForm(forms.ModelForm):
    class Meta:
        abstract = True
        model = MedHistory
        exclude = ["last_modified", "setter", "set_date", "user", "visit"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.value = f"{self._meta.model.__name__.upper()}-value"
        self.fields.update({self.value: forms.BooleanField(required=False)})
        self.fields[self.value].label = f"{self._meta.model.__name__}"
        self.helper = FormHelper()
        self.helper.form_tag = False


class MHCheckForm(MedHistoryForm):
    """Abstract ModelForm model for MedHistory models
    when they are part of a checkbox group. Adds a
    css class wrapper to the value field."""

    class Meta(MedHistoryForm.Meta):
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            Field(self.value, wrapper_class="medhistory_select"),
        )


class AllopurinolhypersensitivityForm(MedHistoryForm):
    class Meta(MedHistoryForm.Meta):
        model = Allopurinolhypersensitivity
        prefix = MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        value = f"{MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY}-value"
        self.fields.update(
            {
                value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[f"{MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY}-value"].label = "Allopurinol Hypersensitivity"
        self.fields[
            f"{MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY}-value"
        ].help_text = "Does the patient have any history of allopurinol hypersensitivity syndrome?"


class AnginaForm(MHCheckForm):
    class Meta(MedHistoryForm.Meta):
        model = Angina
        prefix = MedHistoryTypes.ANGINA

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[f"{MedHistoryTypes.ANGINA}-value"].label = "Angina"
        self.fields[f"{MedHistoryTypes.ANGINA}-value"].help_text = "Exertional chest pain"


class AnticoagulationForm(MHCheckForm):
    class Meta(MedHistoryForm.Meta):
        model = Anticoagulation
        prefix = MedHistoryTypes.ANTICOAGULATION

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[f"{MedHistoryTypes.ANTICOAGULATION}-value"].label = "Anticoagulation"
        self.fields[f"{MedHistoryTypes.ANTICOAGULATION}-value"].help_text = "Is the patient on anticoagulation?"


class BleedForm(MHCheckForm):
    class Meta(MedHistoryForm.Meta):
        model = Bleed
        prefix = MedHistoryTypes.BLEED

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[f"{MedHistoryTypes.BLEED}-value"].label = "Bleed"
        self.fields[f"{MedHistoryTypes.BLEED}-value"].help_text = "Has the patient had a major bleed (GI, etc.)?"


class CadForm(MHCheckForm):
    class Meta(MedHistoryForm.Meta):
        model = Cad
        prefix = MedHistoryTypes.CAD

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[f"{MedHistoryTypes.CAD}-value"].label = "Coronary Artery Disease"
        self.fields[f"{MedHistoryTypes.CAD}-value"].help_text = "Blocked arteries in the heart"


class ChfForm(MHCheckForm):
    class Meta(MedHistoryForm.Meta):
        model = Chf
        prefix = MedHistoryTypes.CHF

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[f"{MedHistoryTypes.CHF}-value"].label = "CHF"
        self.fields[f"{MedHistoryTypes.CHF}-value"].help_text = "Congestive Heart Failure"


class CkdForm(MedHistoryForm):
    class Meta(MedHistoryForm.Meta):
        model = Ckd
        prefix = MedHistoryTypes.CKD

    def __init__(self, *args, **kwargs):
        ckddetail = kwargs.pop("ckddetail")
        super().__init__(*args, **kwargs)
        value = f"{MedHistoryTypes.CKD}-value"
        self.fields.update(
            {
                value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[value].help_text = "Does the patient have chronic kidney disease (CKD)?"
        self.fields[value].label = "CKD"
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                "",
                Div(
                    Div(
                        Div(
                            f"{value}",
                            css_class="col",
                        ),
                        div_class="row",
                    ),
                ),
            ),
        )
        if ckddetail:
            self.helper.layout[0].append(
                Div(
                    Div(
                        Div(
                            HTML(
                                """
                                {% load crispy_forms_tags %}
                                {% crispy ckddetail_form %}
                                """
                            ),
                            css_class="col",
                        ),
                        css_class="row",
                    ),
                    css_id="ckddetail",
                ),
            )


class ColchicineinteractionForm(MedHistoryForm):
    class Meta(MedHistoryForm.Meta):
        model = Colchicineinteraction
        prefix = MedHistoryTypes.COLCHICINEINTERACTION

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        value = f"{MedHistoryTypes.COLCHICINEINTERACTION}-value"
        self.fields.update(
            {
                value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[f"{MedHistoryTypes.COLCHICINEINTERACTION}-value"].label = "Colchicine Interaction"
        self.fields[f"{MedHistoryTypes.COLCHICINEINTERACTION}-value"].help_text = mark_safe(
            "Is the patient on any <a href='https://www.goodrx.com/colchicine/interactions' target='_blank'>\
medications that interact with colchicine</a> (simvastatin, clarithromycin, diltiazem, etc.)?"
        )


class DiabetesForm(MedHistoryForm):
    class Meta(MedHistoryForm.Meta):
        model = Diabetes
        prefix = MedHistoryTypes.DIABETES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        value = f"{MedHistoryTypes.DIABETES}-value"
        self.fields.update(
            {
                value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[f"{MedHistoryTypes.DIABETES}-value"].label = "Diabetes"
        self.fields[f"{MedHistoryTypes.DIABETES}-value"].help_text = "Is the patient a diabetic?"


class ErosionsForm(MedHistoryForm):
    """Form to create or delete a Erosions object.
    Widget is a select box with Yes, No, or blank as options."""

    class Meta(MedHistoryForm.Meta):
        model = Erosions
        prefix = MedHistoryTypes.EROSIONS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        value = f"{MedHistoryTypes.EROSIONS}-value"
        self.fields.update(
            {
                value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[f"{MedHistoryTypes.EROSIONS}-value"].label = "Erosions"
        self.fields[f"{MedHistoryTypes.EROSIONS}-value"].help_text = "Does the patient have gouty erosions on x-ray?"


class FebuxostathypersensitivityForm(MedHistoryForm):
    class Meta(MedHistoryForm.Meta):
        model = Febuxostathypersensitivity
        prefix = MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        value = f"{MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY}-value"
        self.fields.update(
            {
                value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[f"{MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY}-value"].label = "Febuxostat Hypersensitivity"
        self.fields[
            f"{MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY}-value"
        ].help_text = "Does the patient have any history of febuxostat hypersensitivity syndrome?"


class GastricbypassForm(MHCheckForm):
    """Form to create or delete a Gastricbypass object."""

    class Meta(MedHistoryForm.Meta):
        model = Gastricbypass
        prefix = MedHistoryTypes.GASTRICBYPASS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[f"{MedHistoryTypes.GASTRICBYPASS}-value"].label = "Gastric Bypass"
        self.fields[f"{MedHistoryTypes.GASTRICBYPASS}-value"].help_text = "Has the patient had a gastric bypass?"


class GoutForm(MedHistoryForm):
    class Meta(MedHistoryForm.Meta):
        model = Gout
        prefix = MedHistoryTypes.GOUT

    def __init__(self, *args, **kwargs):
        goutdetail = kwargs.pop("goutdetail")
        super().__init__(*args, **kwargs)
        value = f"{MedHistoryTypes.GOUT}-value"
        self.fields.update(
            {
                value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        # Check if the goutdetail kwarg is True
        # If it is, then the patient has had gout before
        if goutdetail:
            # Set the initial value to True
            self.fields[value].initial = True
            # Hide the field
            self.fields[value].widget = forms.HiddenInput()
        else:
            self.fields[value].help_text = "Has the patient had gout or symptoms compatible with gout before?"
            self.fields[value].label = "Gout"
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                "",
                Div(
                    Div(
                        value,
                        css_class="col inline-cb",
                    ),
                    css_class="row",
                ),
            ),
        )
        if goutdetail:
            self.helper.layout[0].append(
                Div(
                    Div(
                        Div(
                            HTML(
                                """
                                {% load crispy_forms_tags %}
                                {% crispy goutdetail_form %}
                                """
                            ),
                            css_class="col",
                        ),
                        css_class="row",
                    ),
                    css_id="goutdetail",
                ),
            )


class HeartattackForm(MHCheckForm):
    class Meta(MedHistoryForm.Meta):
        model = Heartattack
        prefix = MedHistoryTypes.HEARTATTACK

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[f"{MedHistoryTypes.HEARTATTACK}-value"].label = "Heart Attack"
        self.fields[f"{MedHistoryTypes.HEARTATTACK}-value"].help_text = "Myocardial infarction"


class HypertensionForm(MedHistoryForm):
    class Meta(MedHistoryForm.Meta):
        model = Hypertension
        prefix = MedHistoryTypes.HYPERTENSION

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[f"{MedHistoryTypes.HYPERTENSION}-value"].label = "Hypertension"
        self.fields[f"{MedHistoryTypes.HYPERTENSION}-value"].help_text = "High blood pressure"


class HyperuricemiaForm(MedHistoryForm):
    """Form to create or delete a Hyperuricemia object.
    Widget is a select box with Yes, No, or blank as options."""

    class Meta(MedHistoryForm.Meta):
        model = Hyperuricemia
        prefix = MedHistoryTypes.HYPERTENSION

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        value = f"{MedHistoryTypes.HYPERURICEMIA}-value"
        self.fields.update(
            {
                value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[f"{MedHistoryTypes.HYPERURICEMIA}-value"].label = "Hyperuricemia"
        self.fields[
            f"{MedHistoryTypes.HYPERURICEMIA}-value"
        ].help_text = "Does the patient have an elevated serum uric acid (greater than 9.0 mg/dL)?"


class IbdForm(MHCheckForm):
    class Meta(MedHistoryForm.Meta):
        model = Ibd
        prefix = MedHistoryTypes.IBD

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[f"{MedHistoryTypes.IBD}-value"].label = "Inflammatory Bowel Disease"
        self.fields[
            f"{MedHistoryTypes.IBD}-value"
        ].help_text = "Does the patient have a history of inflammatory bowel disease?"


class MenopauseForm(MedHistoryForm):
    class Meta(MedHistoryForm.Meta):
        model = Menopause
        prefix = MedHistoryTypes.MENOPAUSE

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        value = f"{self._meta.model.__name__.upper()}-value"
        self.fields.update(
            {
                value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=False,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[
            f"{MedHistoryTypes.MENOPAUSE}-value"
        ].help_text = "Has the patient gone through menopause? (Either biologically or medically)"
        self.fields[f"{MedHistoryTypes.MENOPAUSE}-value"].label = "Menopause"


class OrgantransplantForm(MedHistoryForm):
    class Meta(MedHistoryForm.Meta):
        model = Organtransplant
        prefix = MedHistoryTypes.ORGANTRANSPLANT

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        value = f"{MedHistoryTypes.ORGANTRANSPLANT}-value"
        self.fields.update(
            {
                value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[f"{MedHistoryTypes.ORGANTRANSPLANT}-value"].label = "Organ Transplant"
        self.fields[f"{MedHistoryTypes.ORGANTRANSPLANT}-value"].help_text = "Has the patient had an organ transplant?"


class PvdForm(MHCheckForm):
    class Meta(MedHistoryForm.Meta):
        model = Pvd
        prefix = MedHistoryTypes.PVD

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[f"{MedHistoryTypes.PVD}-value"].label = "Peripheral Arterial Disease"
        self.fields[f"{MedHistoryTypes.PVD}-value"].help_text = "Blocked arteries in the legs or arms"


class StrokeForm(MHCheckForm):
    class Meta(MedHistoryForm.Meta):
        model = Stroke
        prefix = MedHistoryTypes.STROKE

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[f"{MedHistoryTypes.STROKE}-value"].label = "Stroke"
        self.fields[f"{MedHistoryTypes.STROKE}-value"].help_text = "Cerebrovascular accident"


class TophiForm(MedHistoryForm):
    """Form to create or delete a Tophi object.
    Widget is a select box with Yes, No, or blank as options."""

    class Meta(MedHistoryForm.Meta):
        model = Tophi
        prefix = MedHistoryTypes.TOPHI

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        value = f"{MedHistoryTypes.TOPHI}-value"
        self.fields.update(
            {
                value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[f"{MedHistoryTypes.TOPHI}-value"].label = "Tophi"
        self.fields[f"{MedHistoryTypes.TOPHI}-value"].help_text = "Does the patient have gouty tophi?"


class UratestonesForm(MedHistoryForm):
    """Form to create or delete a Uratestones object.
    Widget is a select box with Yes, No, or blank as options."""

    class Meta(MedHistoryForm.Meta):
        model = Uratestones
        prefix = MedHistoryTypes.URATESTONES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        value = f"{MedHistoryTypes.URATESTONES}-value"
        self.fields.update(
            {
                value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[f"{MedHistoryTypes.URATESTONES}-value"].label = "Urate Kidney Stones"
        self.fields[
            f"{MedHistoryTypes.URATESTONES}-value"
        ].help_text = "Does the patient have a history of urate kidney stones?"


class XoiinteractionForm(MedHistoryForm):
    class Meta(MedHistoryForm.Meta):
        model = Xoiinteraction
        prefix = MedHistoryTypes.XOIINTERACTION

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        value = f"{MedHistoryTypes.XOIINTERACTION}-value"
        self.fields.update(
            {
                value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[f"{MedHistoryTypes.XOIINTERACTION}-value"].label = "Xanthine Oxidase Inhibitor Interaction"
        self.fields[
            f"{MedHistoryTypes.XOIINTERACTION}-value"
        ].help_text = "Is the patient on 6-mercaptopurine or azathioprine?"
