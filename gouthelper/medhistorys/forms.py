from crispy_forms.helper import FormHelper  # type: ignore
from crispy_forms.layout import HTML, Div, Field, Fieldset, Layout  # type: ignore
from django import forms  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils.safestring import mark_safe  # type: ignore
from django.utils.text import format_lazy  # type: ignore

from ..choices import YES_OR_NO_OR_NONE
from ..medhistorys.choices import MedHistoryTypes
from ..utils.forms import ModelFormKwargMixin
from .models import (
    Angina,
    Anticoagulation,
    Bleed,
    Cad,
    Chf,
    Ckd,
    Colchicineinteraction,
    Diabetes,
    Erosions,
    Gastricbypass,
    Gout,
    Heartattack,
    Hepatitis,
    Hypertension,
    Hyperuricemia,
    Ibd,
    MedHistory,
    Menopause,
    Organtransplant,
    Pud,
    Pvd,
    Stroke,
    Tophi,
    Uratestones,
    Xoiinteraction,
)


class MedHistoryForm(ModelFormKwargMixin, forms.ModelForm):
    class Meta:
        abstract = True
        model = MedHistory
        exclude = [
            "flareaid",
            "flare",
            "goalurate",
            "last_modified",
            "ppxaid",
            "ppx",
            "setter",
            "set_date",
            "ultaid",
            "ult",
            "user",
            "visit",
        ]

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


class AnginaForm(MHCheckForm):
    class Meta(MedHistoryForm.Meta):
        model = Angina
        prefix = MedHistoryTypes.ANGINA

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.value].label = "Angina"
        self.fields[self.value].help_text = "Exertional chest pain"


class AnticoagulationForm(MHCheckForm):
    class Meta(MedHistoryForm.Meta):
        model = Anticoagulation
        prefix = MedHistoryTypes.ANTICOAGULATION

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.value].label = "Anticoagulation"
        self.fields[
            self.value
        ].help_text = f"{self.str_attrs['Tobe']} {self.str_attrs['subject_the']} on \
anticoagulation?"


class BleedForm(MHCheckForm):
    class Meta(MedHistoryForm.Meta):
        model = Bleed
        prefix = MedHistoryTypes.BLEED

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.value].label = "Bleed"
        self.fields[
            self.value
        ].help_text = f"{self.str_attrs['Pos']} {self.str_attrs['subject_the']} had a major \
bleed (GI, etc.)?"


class CadForm(MHCheckForm):
    class Meta(MedHistoryForm.Meta):
        model = Cad
        prefix = MedHistoryTypes.CAD

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.value].label = "Coronary Artery Disease"
        self.fields[self.value].help_text = "Blocked arteries in the heart"


class ChfForm(MHCheckForm):
    class Meta(MedHistoryForm.Meta):
        model = Chf
        prefix = MedHistoryTypes.CHF

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.value].label = "CHF"
        self.fields[self.value].help_text = "Congestive Heart Failure"


class CkdForm(MedHistoryForm):
    class Meta(MedHistoryForm.Meta):
        model = Ckd
        prefix = MedHistoryTypes.CKD

    def __init__(self, *args, **kwargs):
        ckddetail = kwargs.pop("ckddetail")
        super().__init__(*args, **kwargs)
        self.fields.update(
            {
                self.value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[
            self.value
        ].help_text = f"{self.str_attrs['Query']} {self.str_attrs['subject_the']} have chronic \
kidney disease (CKD)?"
        self.fields[self.value].label = "CKD"
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                "",
                Div(
                    Div(
                        Div(
                            f"{self.value}",
                            css_class="col",
                        ),
                        div_class="row",
                    ),
                    css_id="ckd-form",
                    **self.fieldset_div_kwargs,
                ),
            ),
        )
        if ckddetail:
            self.helper.layout[0][0].append(
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
        self.fields.update(
            {
                self.value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[self.value].label = "Colchicine Interaction"
        self.fields[self.value].help_text = mark_safe(
            f"{self.str_attrs['Tobe']} {self.str_attrs['subject_the']} on any \
<a href='https://www.goodrx.com/colchicine/interactions' \
target='_blank'> medications that interact with colchicine</a> (simvastatin, clarithromycin, diltiazem, etc.)?"
        )


class DiabetesForm(MedHistoryForm):
    class Meta(MedHistoryForm.Meta):
        model = Diabetes
        prefix = MedHistoryTypes.DIABETES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.update(
            {
                self.value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[self.value].label = "Diabetes"
        self.fields[self.value].help_text = f"{self.str_attrs['Tobe']} {self.str_attrs['subject_the']} a diabetic?"


class ErosionsForm(MedHistoryForm):
    """Form to create or delete a Erosions object.
    Widget is a select box with Yes, No, or blank as options."""

    class Meta(MedHistoryForm.Meta):
        model = Erosions
        prefix = MedHistoryTypes.EROSIONS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.update(
            {
                self.value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[self.value].label = "Erosions"
        self.fields[
            self.value
        ].help_text = f"{self.str_attrs['Query']} {self.str_attrs['subject_the']} have gouty \
erosions on x-ray?"


class GastricbypassForm(MHCheckForm):
    """Form to create or delete a Gastricbypass object."""

    class Meta(MedHistoryForm.Meta):
        model = Gastricbypass
        prefix = MedHistoryTypes.GASTRICBYPASS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.value].label = "Gastric Bypass"
        self.fields[
            self.value
        ].help_text = f"{self.str_attrs['Pos']} {self.str_attrs['subject_the']} had a gastric \
bypass?"


class GoutForm(MedHistoryForm):
    class Meta(MedHistoryForm.Meta):
        model = Gout
        prefix = MedHistoryTypes.GOUT

    def __init__(self, *args, **kwargs):
        goutdetail = kwargs.pop("goutdetail")
        super().__init__(*args, **kwargs)
        self.fields.update(
            {
                self.value: forms.TypedChoiceField(
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
            self.fields[self.value].initial = True
            # Hide the field
            self.fields[self.value].widget = forms.HiddenInput()
        else:
            self.fields[self.value].help_text = mark_safe(
                format_lazy(
                    """{} {} had gout or <a target='_next' href={}>symptoms of gout</a> before?""",
                    self.str_attrs["Pos"],
                    self.str_attrs["subject_the"],
                    reverse("flares:about"),
                )
            )
            self.fields[self.value].label = "Gout"
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                "",
                Div(
                    Div(
                        self.value,
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
        self.fields[self.value].label = "Heart Attack"
        self.fields[self.value].help_text = "Myocardial infarction"


class HepatitisForm(MedHistoryForm):
    """Form to create or delete a Hepatitis object.
    Widget is a select box with Yes, No, or blank as options."""

    class Meta(MedHistoryForm.Meta):
        model = Hepatitis
        prefix = MedHistoryTypes.HEPATITIS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.update(
            {
                self.value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[self.value].label = "Hepatitis"
        self.fields[self.value].help_text = mark_safe(
            format_lazy(
                """{} {} have <a href={} target='_next'>hepatitis</a> or <a href={} target='_next'>cirrhosis</a> of \
the liver?""",
                self.str_attrs["Query"],
                self.str_attrs["subject_the"],
                "https://en.wikipedia.org/wiki/Hepatitis",
                "https://en.wikipedia.org/wiki/Cirrhosis",
            )
        )


class HypertensionForm(MedHistoryForm):
    class Meta(MedHistoryForm.Meta):
        model = Hypertension
        prefix = MedHistoryTypes.HYPERTENSION

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.value].label = "Hypertension"
        self.fields[self.value].help_text = "High blood pressure"


class HyperuricemiaForm(MedHistoryForm):
    """Form to create or delete a Hyperuricemia object.
    Widget is a select box with Yes, No, or blank as options."""

    class Meta(MedHistoryForm.Meta):
        model = Hyperuricemia
        prefix = MedHistoryTypes.HYPERTENSION

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.update(
            {
                self.value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[self.value].label = "Hyperuricemia"
        self.fields[
            self.value
        ].help_text = f"{self.str_attrs['Query']} {self.str_attrs['subject_the']} have an elevated serum uric acid \
(greater than 9.0 mg/dL)?"


class IbdForm(MHCheckForm):
    class Meta(MedHistoryForm.Meta):
        model = Ibd
        prefix = MedHistoryTypes.IBD

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.value].label = "Inflammatory Bowel Disease"
        self.fields[
            self.value
        ].help_text = f"{self.str_attrs['Query']} {self.str_attrs['subject_the']} have a \
history of inflammatory bowel disease?"


class MenopauseForm(MedHistoryForm):
    class Meta(MedHistoryForm.Meta):
        model = Menopause
        prefix = MedHistoryTypes.MENOPAUSE

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.update(
            {
                self.value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=False,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[
            self.value
        ].help_text = f"{self.str_attrs['Tobe']} {self.str_attrs['subject_the']} menopausal or post-menopausal?"
        self.fields[self.value].label = "Menopause"


class OrgantransplantForm(MedHistoryForm):
    class Meta(MedHistoryForm.Meta):
        model = Organtransplant
        prefix = MedHistoryTypes.ORGANTRANSPLANT

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.update(
            {
                self.value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[self.value].label = "Organ Transplant"
        self.fields[
            self.value
        ].help_text = f"{self.str_attrs['Pos']} {self.str_attrs['subject_the']} had \
an organ transplant?"


class PudForm(MHCheckForm):
    class Meta(MedHistoryForm.Meta):
        model = Pud
        prefix = MedHistoryTypes.PUD

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.value].label = "Peptic Ulcer Disease"
        self.fields[
            self.value
        ].help_text = f"{self.str_attrs['Pos']} {self.str_attrs['subject_the']} had gastric or \
other gastrointestinal ulcers?"


class PvdForm(MHCheckForm):
    class Meta(MedHistoryForm.Meta):
        model = Pvd
        prefix = MedHistoryTypes.PVD

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.value].label = "Peripheral Arterial Disease"
        self.fields[self.value].help_text = "Blocked arteries in the legs or arms"


class StrokeForm(MHCheckForm):
    class Meta(MedHistoryForm.Meta):
        model = Stroke
        prefix = MedHistoryTypes.STROKE

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.value].label = "Stroke"
        self.fields[self.value].help_text = "Cerebrovascular accident"


class TophiForm(MedHistoryForm):
    """Form to create or delete a Tophi object.
    Widget is a select box with Yes, No, or blank as options."""

    class Meta(MedHistoryForm.Meta):
        model = Tophi
        prefix = MedHistoryTypes.TOPHI

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.update(
            {
                self.value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[self.value].label = "Tophi"
        self.fields[
            self.value
        ].help_text = f"{self.str_attrs['Query']} {self.str_attrs['subject_the']} have gouty \
tophi?"


class UratestonesForm(MedHistoryForm):
    """Form to create or delete a Uratestones object.
    Widget is a select box with Yes, No, or blank as options."""

    class Meta(MedHistoryForm.Meta):
        model = Uratestones
        prefix = MedHistoryTypes.URATESTONES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.update(
            {
                self.value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[self.value].label = "Urate Kidney Stones"
        self.fields[self.value].help_text = mark_safe(
            format_lazy(
                """{} {} have a history of <a href={} target='_next'>urate kidney stones</a>?""",
                self.str_attrs["Query"],
                self.str_attrs["subject_the"],
                "https://en.wikipedia.org/wiki/Kidney_stone_disease#:~:text=microscopy.%5B74%5D-,Uric%20acid%20stones,\
-%5Bedit%5D",
            )
        )


class XoiinteractionForm(MedHistoryForm):
    class Meta(MedHistoryForm.Meta):
        model = Xoiinteraction
        prefix = MedHistoryTypes.XOIINTERACTION

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.update(
            {
                self.value: forms.TypedChoiceField(
                    choices=YES_OR_NO_OR_NONE,
                    required=True,
                    initial=None,
                    empty_value=None,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields[self.value].label = "Xanthine Oxidase Inhibitor Interaction"
        self.fields[self.value].help_text = mark_safe(
            format_lazy(
                """{} {} on <a href={} target='_next'>6-mercaptopurine</a> or <a href={} \
target='_next'>azathioprine</a>?""",
                self.str_attrs["Tobe"],
                self.str_attrs["subject_the"],
                "https://en.wikipedia.org/wiki/Mercaptopurine",
                "https://en.wikipedia.org/wiki/Azathioprine",
            )
        )
