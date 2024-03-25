from crispy_forms.helper import FormHelper  # type: ignore
from crispy_forms.layout import HTML, Div, Fieldset, Layout  # type: ignore
from django import forms  # type: ignore
from django.urls import reverse_lazy  # type: ignore
from django.utils.safestring import mark_safe  # type: ignore
from django.utils.text import format_lazy  # type: ignore

from ..choices import YES_OR_NO_OR_NONE, YES_OR_NO_OR_UNKNOWN
from ..medhistorydetails.choices import Stages
from ..utils.helpers import get_str_attrs
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
        self.patient = kwargs.pop("patient", None)
        self.request_user = kwargs.pop("request_user", None)
        self.str_attrs = kwargs.pop("str_attrs", None)
        if not self.str_attrs:
            self.str_attrs = get_str_attrs(self, self.patient, self.request_user)
        super().__init__(*args, **kwargs)
        self.optional = False
        self.fields["dialysis"].required = False
        self.fields["dialysis"].help_text = mark_safe(
            f"{self.str_attrs['Tobe']} {self.str_attrs['subject_the']} on \
<a href='https://en.wikipedia.org/wiki/Hemodialysis' target='_blank'>dialysis</a>?"
        )
        self.fields["dialysis_duration"].help_text = mark_safe(
            f"How long since {self.str_attrs['subject_the']} \
started dialysis?"
        )
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
        self.patient = kwargs.pop("patient", None)
        self.request_user = kwargs.pop("request_user", None)
        self.str_attrs = kwargs.pop("str_attrs", None)
        if not self.str_attrs:
            self.str_attrs = get_str_attrs(self, self.patient, self.request_user)
        super().__init__(*args, **kwargs)
        self.fields["flaring"].initial = None
        self.fields["flaring"].choices = YES_OR_NO_OR_UNKNOWN
        self.fields["flaring"].help_text = format_lazy(
            """{} {} had a gout <a href="{}" target="_blank">flare</a> in the last 6 months?""",
            self.str_attrs["Pos"],
            self.str_attrs["subject_the"],
            reverse_lazy("flares:about"),
        )
        self.fields["hyperuricemic"].initial = None
        self.fields["hyperuricemic"].choices = YES_OR_NO_OR_UNKNOWN
        self.fields["hyperuricemic"].help_text = format_lazy(
            """{} {} had a <a href="{}" target="_blank">uric acid</a> greater \
than 6.0 mg/dL in the past 6 months?""",
            self.str_attrs["Pos"],
            self.str_attrs["subject_the"],
            reverse_lazy("labs:about-urate"),
        )
        self.fields["on_ppx"].initial = None
        self.fields["on_ppx"].choices = YES_OR_NO_OR_NONE
        self.fields["on_ppx"].label = "Already on PPx?"
        self.fields["on_ppx"].help_text = format_lazy(
            """{} {} already on <a href="{}" target="_blank">prophylaxis</a> (PPx) for gout?""",
            self.str_attrs["Tobe"],
            self.str_attrs["subject_the"],
            reverse_lazy("treatments:about-ppx"),
        )
        self.fields["on_ppx"].required = True
        self.fields["on_ult"].label = "Already on ULT?"
        self.fields["on_ult"].help_text = format_lazy(
            """{} {} on <a href="{}" target="_blank">urate lowering therapy</a> (ULT)?""",
            self.str_attrs["Tobe"],
            self.str_attrs["subject_the"],
            reverse_lazy("treatments:about-ult"),
        )
        self.fields["on_ult"].initial = None
        self.fields["on_ult"].choices = YES_OR_NO_OR_NONE
        self.fields["on_ult"].required = True
        self.helper = FormHelper()
        self.helper.form_tag = False
        legend_sub = "the Patient" if not self.patient else self.patient
        self.helper.layout = Layout(
            Fieldset(
                "",
                Div(
                    Div(
                        HTML(
                            f"""
                                <hr size="3" color="dark">
                                <legend>About {legend_sub}'s Gout</legend>
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
            f"{self.str_attrs['Pos']} {self.str_attrs['subject_the']} had a uric acid greater \
than 6.0 mg/dL in the past 6 months? If you want to enter values and dates for uric acids, \
you can do so <a href='#labs_formset_table'>below</a> and we will make this determination for you."
        )
