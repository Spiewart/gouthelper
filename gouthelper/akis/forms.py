from crispy_forms.helper import FormHelper  # type: ignore
from crispy_forms.layout import Div, Fieldset, Layout  # type: ignore
from django import forms  # type: ignore
from django.utils.html import mark_safe  # type: ignore
from django.utils.text import format_lazy  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore

from ..choices import BOOL_CHOICES
from ..utils.exceptions import EmptyRelatedModel
from ..utils.forms import ModelFormKwargMixin, forms_helper_insert_creatinines_formset
from .choices import Statuses
from .models import Aki


class AkiForm(ModelFormKwargMixin, forms.ModelForm):
    class Meta:
        model = Aki
        fields = ["status"]

    prefix = "aki"
    AkiFormStatuses = Statuses.choices + [(None, "I don't know")]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fieldset_div_kwargs.update({"css_class": "sub-form"})
        self.fields.update(
            {
                "value": forms.TypedChoiceField(
                    widget=forms.Select,
                    choices=BOOL_CHOICES,
                    required=True,
                    initial=False,
                    coerce=lambda x: x == "True",
                )
            }
        )
        self.fields["value"].help_text = _(
            mark_safe(
                format_lazy(
                    """Did {} have an acute kidney injury (<a target='_next' href='{}'>AKI</a>){}? \
<strong>Leave as "No" if creatinine was not checked</strong>.""",
                    self.str_attrs.get("subject_the"),
                    "https://www.aafp.org/pubs/afp/issues/2012/1001/p631/jcr:content/root/aafp-article-primary-content\
-container/aafp_article_main_par/aafp_tables_content0.enlarge.html",
                    " during this flare",
                )
            )
        )
        self.fields["value"].label = "Acute Kidney Injury"
        self.fields["status"].choices = self.AkiFormStatuses
        self.fields["status"].initial = None
        self.fields["status"].label = "AKI Status"
        self.fields["status"].help_text = _(
            "What is the status of this AKI? If unknown, you can enter creatinine \
values below and GoutHelper will figure it out. Otherwise, GoutHelper will \
assume the AKI is ongoing."
        )
        self.fields["status"].required = False
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                "",
                Div("value", "status", css_id="aki-form", **self.fieldset_div_kwargs),
            ),
        )
        forms_helper_insert_creatinines_formset(self)

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("value", False) and "status" not in cleaned_data:
            cleaned_data["status"] = Aki.Statuses.ONGOING
        return cleaned_data

    def check_for_value(self):
        value = self.cleaned_data["value"]
        if not value:
            raise EmptyRelatedModel

    @property
    def required_fields(self) -> list[str]:
        """Return a list of required fields"""
        return ["value"]
