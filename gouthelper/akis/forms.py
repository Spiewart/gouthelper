from crispy_forms.helper import FormHelper  # type: ignore
from crispy_forms.layout import Div, Fieldset, Layout  # type: ignore
from django import forms  # type: ignore
from django.utils.html import mark_safe  # type: ignore
from django.utils.text import format_lazy  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore

from ..choices import BOOL_CHOICES, YES_OR_NO_OR_NONE
from ..utils.exceptions import EmptyRelatedModel
from ..utils.forms import ModelFormKwargMixin, forms_helper_insert_creatinines_formset
from .models import Aki


class AkiForm(ModelFormKwargMixin, forms.ModelForm):
    class Meta:
        model = Aki
        exclude = [
            "dateofbirth",
            "gender",
            "flare",
            "user",
            "ckd",
        ]

    prefix = "aki"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        self.fields["resolved"].widget = forms.Select(choices=YES_OR_NO_OR_NONE)
        self.fields["resolved"].label = "AKI Resolved"
        self.fields["resolved"].help_text = _(
            "Has this AKI resolved? (i.e., has the creatinine level returned to normal?)"
        )
        self.fields["resolved"].required = False
        self.fields["resolved"].initial = None
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                "",
                Div("value", "resolved", css_id="aki-form", **self.fieldset_div_kwargs),
            ),
        )
        forms_helper_insert_creatinines_formset(self)

    def check_for_value(self):
        value = self.cleaned_data["value"]
        if not value:
            raise EmptyRelatedModel

    @property
    def required_fields(self) -> list[str]:
        """Return a list of required fields"""
        return ["value"]
