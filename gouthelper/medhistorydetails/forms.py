from crispy_forms.helper import FormHelper  # type: ignore
from crispy_forms.layout import HTML, Div, Fieldset, Layout  # type: ignore
from django import forms  # type: ignore
from django.urls import reverse_lazy  # type: ignore
from django.utils.safestring import mark_safe  # type: ignore
from django.utils.text import format_lazy  # type: ignore

from ..choices import YES_OR_NO_OR_NONE, YES_OR_NO_OR_UNKNOWN
from ..medhistorydetails.choices import Stages
from .models import CkdDetail, GoutDetail


class CkdDetailForm(forms.ModelForm):
    """Form for CkdDetail model. Embeds BaselineCreatinine form
    within, so will need to be processed as well by the view."""

    class Meta:
        model = CkdDetail
        fields = (
            "dialysis",
            "dialysis_duration",
            "dialysis_type",
            "stage",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.optional = False
        self.fields["dialysis"].required = False
        self.fields["stage"].required = False
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                "",
                Div(
                    Div(
                        Div(
                            Div(
                                "dialysis",
                                css_class="col",
                            ),
                            css_class="row",
                            css_id="dialysis",
                        ),
                        Div(
                            Div(
                                "dialysis_type",
                                css_class="col",
                            ),
                            css_class="row",
                            css_id="dialysis_type",
                        ),
                        Div(
                            Div(
                                "dialysis_duration",
                                css_class="col",
                            ),
                            css_class="row",
                            css_id="dialysis_duration",
                        ),
                        Div(
                            Div(
                                "stage",
                                css_class="col",
                            ),
                            css_class="row",
                            css_id="stage",
                        ),
                        Div(
                            Div(
                                HTML(
                                    """
                                    {% load crispy_forms_tags %}
                                    {% crispy baselinecreatinine_form %}
                                    """
                                ),
                                css_class="col",
                            ),
                            css_class="row",
                            css_id="baselinecreatinine",
                        ),
                        css_id="ckddetail",
                    ),
                    css_id="ckddetail-form",
                ),
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        dialysis = cleaned_data["dialysis"]
        stage = cleaned_data["stage"]
        if dialysis is True:
            if cleaned_data["dialysis_type"] is None:
                self.add_error(
                    "dialysis_type",
                    forms.ValidationError(
                        "If dialysis is checked, dialysis type must be selected.", code="dialysis_type"
                    ),
                )
            if cleaned_data["dialysis_duration"] is None:
                self.add_error(
                    "dialysis_duration",
                    forms.ValidationError(
                        "If dialysis is checked, dialysis duration must be selected.", code="dialysis_duration"
                    ),
                )
            if stage is not Stages.FIVE:
                cleaned_data.update({"stage": Stages.FIVE})
        else:
            if cleaned_data["dialysis_type"] is not None:
                cleaned_data.update({"dialysis_type": None})
            if cleaned_data["dialysis_duration"] is not None:
                cleaned_data.update({"dialysis_duration": None})
        return cleaned_data


class CkdDetailOptionalForm(CkdDetailForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.optional = True


class GoutDetailForm(forms.ModelForm):
    """Form for GoutDetail model. Embeds Urate forms within,
    so will need to be processed as well by the view."""

    class Meta:
        model = GoutDetail
        fields = (
            "flaring",
            "hyperuricemic",
            "on_ppx",
            "on_ult",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["flaring"].initial = None
        self.fields["flaring"].choices = YES_OR_NO_OR_UNKNOWN
        self.fields["flaring"].help_text = format_lazy(
            """Has the patient had a gout <a href="{}" target="_blank">flare</a> in the last 6 months?""",
            reverse_lazy("flares:about"),
        )
        self.fields["hyperuricemic"].initial = None
        self.fields["hyperuricemic"].choices = YES_OR_NO_OR_UNKNOWN
        self.fields["hyperuricemic"].help_text = format_lazy(
            """Has the patient had a <a href="{}" target="_blank">uric acid</a> greater \
than 6.0 mg/dL in the past 6 months?""",
            reverse_lazy("labs:about-urate"),
        )
        self.fields["on_ppx"].initial = None
        self.fields["on_ppx"].choices = YES_OR_NO_OR_NONE
        self.fields["on_ppx"].label = "Already on PPx?"
        self.fields["on_ppx"].help_text = format_lazy(
            """Is the patient already on <a href="{}" target="_blank">prophylaxis</a> (PPx) for gout?""",
            reverse_lazy("treatments:about-ppx"),
        )
        self.fields["on_ppx"].required = True
        self.fields["on_ult"].label = "Already on ULT?"
        self.fields["on_ult"].help_text = format_lazy(
            """Is the patient on <a href="{}" target="_blank">urate lowering therapy</a> (ULT)?""",
            reverse_lazy("treatments:about-ult"),
        )
        self.fields["on_ult"].initial = None
        self.fields["on_ult"].choices = YES_OR_NO_OR_NONE
        self.fields["on_ult"].required = True
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                "",
                Div(
                    Div(
                        HTML(
                            """
                                <hr size="3" color="dark">
                                <legend>About the Gout</legend>
                                """
                        ),
                        css_id="about-the-gout",
                    ),
                    Div(
                        Div(
                            "flaring",
                            css_class="col",
                        ),
                        css_class="row",
                        css_id="flaring",
                    ),
                    Div(
                        Div(
                            "hyperuricemic",
                            css_class="col",
                        ),
                        css_class="row",
                        css_id="hyperuricemic",
                    ),
                    Div(
                        Div(
                            "on_ppx",
                            css_class="col",
                        ),
                        css_class="row",
                        css_id="on_ppx",
                    ),
                    Div(
                        Div(
                            "on_ult",
                            css_class="col",
                        ),
                        css_class="row",
                        css_id="on_ult",
                    ),
                    css_id="goutdetail-form",
                ),
            ),
        )


class GoutDetailPpxForm(GoutDetailForm):
    """Form for GoutDetail model. Embeds Urate forms within,
    so will need to be processed as well by the view."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["hyperuricemic"].help_text = mark_safe(
            "Has the patient had a uric acid greater \
than 6.0 mg/dL in the past 6 months? If you want to enter values and dates for uric acids, \
you can do so <a href='#labs_formset_table'>below</a> and we will make this determination for you."
        )
