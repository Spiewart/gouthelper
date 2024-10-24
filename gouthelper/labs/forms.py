from crispy_forms.helper import FormHelper  # type: ignore
from crispy_forms.layout import Div, Field, Fieldset, Layout  # type: ignore
from django import forms  # type: ignore
from django.core.exceptions import ValidationError  # type: ignore
from django.urls import reverse_lazy  # type: ignore
from django.utils import timezone  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.utils.safestring import mark_safe  # type: ignore
from django.utils.text import format_lazy  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore

from ..choices import YES_OR_NO_OR_UNKNOWN
from ..utils.exceptions import EmptyRelatedModel
from ..utils.forms import ModelFormKwargMixin, forms_make_custom_datetimefield
from .helpers import labs_baselinecreatinine_max_value, labs_urates_max_value
from .models import BaselineCreatinine, Creatinine, Hlab5801, Urate


class BaseLabForm(
    ModelFormKwargMixin,
    forms.ModelForm,
):
    prefix: str = "lab"

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.fields["value"].label = mark_safe(f"{self.prefix.capitalize()}")
        self.helper.layout = Layout(
            Fieldset(
                "",
                "value",
            ),
        )


class LabForm(BaseLabForm):
    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        updated_css_class = (
            self.fieldset_div_kwargs.get("css_class", "") + f" {self._meta.__class__.__name__.lower()}-form"
        )
        self.fieldset_div_kwargs.update({"css_class": updated_css_class})
        self.helper = FormHelper(self)
        self.fields["date_drawn"].initial = None
        self.fields["date_drawn"].label = mark_safe("Date Drawn")
        self.fields["date_drawn"].help_text = mark_safe(f"What day was this {self.prefix} drawn?")
        self.fields["date_drawn"].widget.attrs["class"] = "datepick"
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                "",
                Div(
                    Div(
                        Div(
                            "value",
                            css_class="col",
                        ),
                        Div(
                            Field("date_drawn", css_class="date_drawn"),
                            css_class="col",
                        ),
                        css_class="row",
                    ),
                    **self.fieldset_div_kwargs,
                ),
            ),
        )

    def clean(self):
        """
        Requires date_drawn if value is present
        """
        # Fetch cleaned data for fields that need cleaning
        cleaned_data = super().clean()
        value = cleaned_data.get("value", None)
        date_drawn = cleaned_data.get("date_drawn", None)

        # Check for value
        if value:
            # If present, raise error if there's no date_drawn
            if not date_drawn:
                error_message = ValidationError(_("We need to know when this was drawn."))
                self.add_error("date_drawn", error_message)
            else:
                if date_drawn > timezone.now():
                    error_message = ValidationError(_("Labs can't be drawn in the future... Or can they?"))
                    self.add_error("date_drawn", error_message)

    @cached_property
    def instance_should_persist(self) -> bool:
        return (
            hasattr(self, "cleaned_data")
            and self.cleaned_data.get("value", None) not in [None, ""]
            and not self.cleaned_data.get("DELETE")
        )


class BaselineCreatinineForm(BaseLabForm):
    prefix = "baselinecreatinine"

    class Meta:
        model = BaselineCreatinine
        fields = ("value",)
        widgets = {
            "value": forms.NumberInput(attrs={"step": 0.10}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["value"].required = False
        self.fields["value"].label = "Baseline Creatinine"
        self.fields["value"].decimal_places = 2
        self.fields["value"].help_text = mark_safe(
            f"What is {self.str_attrs['subject_the_pos']} baseline creatinine? \
Creatinine is typically reported in micrograms per deciliter (mg/dL)."
        )
        self.fields["value"].validators.append(labs_baselinecreatinine_max_value)
        self.helper = FormHelper(self)
        self.helper.form_tag = False

    @property
    def required_fields(self) -> list[str]:
        """Return a list of required fields"""
        return ["value"]

    def check_for_value(self):
        if self.cleaned_data.get("value", None) is not None:
            pass
        else:
            raise EmptyRelatedModel


class CreatinineForm(LabForm):
    prefix = "creatinine"

    class Meta:
        model = Creatinine
        fields = (
            "value",
            "date_drawn",
        )
        widgets = {
            "value": forms.NumberInput(attrs={"step": 0.10}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["value"].label = "Creatinine (mg/dL)"
        self.fields["value"].decimal_places = 2
        self.fields["value"].required = False
        self.fields["value"].validators.append(labs_baselinecreatinine_max_value)
        self.fields["value"].help_text = mark_safe("Serum creatinine in micrograms per deciliter (mg/dL).")
        self.fields["date_drawn"].help_text = mark_safe("When was this creatinine drawn?")


class Hlab5801Form(BaseLabForm):
    prefix = "hlab5801"

    class Meta:
        model = Hlab5801
        fields = ("value",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["value"].choices = YES_OR_NO_OR_UNKNOWN
        self.fields["value"].initial = None
        self.fields["value"].required = False
        self.fields["value"].label = "HLA-B*5801 Genotype"
        self.fields["value"].help_text = mark_safe(
            format_lazy(
                """Is {} <a target='_next' href={}>HLA-B*5801</a> genotype known?""",
                self.str_attrs["subject_the_pos"],
                reverse_lazy("labs:about-hlab5801"),
            )
        )
        self.helper = FormHelper(self)
        self.helper.form_tag = False

    def check_for_value(self):
        # Unlike CheckBox fields, Choice fields return "" instead of None
        # This won't evaluate to None, but will evaluate to False which
        # indicates that the field is empty and either shouldn't be created
        # or should be deleted.
        value = self.cleaned_data.get("value", None)
        if value is True or (value is False and not value == ""):
            pass
        else:
            raise EmptyRelatedModel

    @property
    def required_fields(self) -> list[str]:
        """Return a list of required fields"""
        return ["value"]


class UrateForm(LabForm):
    prefix = "urate"
    formfield_callback = forms_make_custom_datetimefield

    class Meta:
        model = Urate
        fields = (
            "value",
            "date_drawn",
        )
        widgets = {
            "value": forms.NumberInput(attrs={"step": 0.10}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["value"].label = "Uric Acid (mg/dL)"
        self.fields["value"].decimal_places = 1
        self.fields["value"].required = False
        self.fields["value"].validators.append(labs_urates_max_value)
        self.fields["value"].help_text = mark_safe("Serum uric acid in micrograms per deciliter (mg/dL).")
        self.fields["date_drawn"].help_text = mark_safe("When was this uric acid drawn?")
        self.fields["date_drawn"].widget.attrs["class"] = "datepick"


class UrateFlareForm(BaseLabForm):
    prefix = "urate"

    class Meta:
        model = Urate
        fields = ("value",)
        widgets = {
            "value": forms.NumberInput(attrs={"step": 0.10}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["value"].required = False
        self.fields["value"].label = "Uric Acid Level"
        self.fields["value"].decimal_places = 1
        self.fields["value"].help_text = mark_safe(
            f"What was {self.str_attrs.get('subject_pos')} uric acid level? \
Uric acid is typically reported in micrograms per deciliter (mg/dL)."
        )
        self.fields["value"].validators.append(labs_urates_max_value)
        self.helper = FormHelper(self)
        self.helper.form_tag = False

    @property
    def required_fields(self) -> list[str]:
        """Return a list of required fields"""
        return ["value"]

    def check_for_value(self):
        if self.cleaned_data["value"] is not None:
            pass
        else:
            raise EmptyRelatedModel


class CreatinineFormHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_tag = False
        self.template = "bootstrap4/table_inline_formset.html"
        self.form_id = "creatinine_formset"


# https://stackoverflow.com/questions/42615357/cannot-pass-helper-to-django-crispy-formset-in-template
class UrateFormHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_tag = False
        self.template = "bootstrap4/table_inline_formset.html"
        self.form_id = "urate_formset"


FlareCreatinineFormSet = forms.modelformset_factory(
    Creatinine,
    CreatinineForm,
    # Converts all the datetime fields to just date fields
    formfield_callback=forms_make_custom_datetimefield,
    can_delete=True,
    extra=1,
)

# https://stackoverflow.com/questions/14328381/django-error-unexpected-keyword-argument-widget
PpxUrateFormSet = forms.modelformset_factory(
    Urate,
    UrateForm,
    # Converts all the datetime fields to just date fields
    formfield_callback=forms_make_custom_datetimefield,
    can_delete=True,
    extra=1,
)
