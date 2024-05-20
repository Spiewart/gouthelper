from crispy_forms.helper import FormHelper  # type: ignore
from crispy_forms.layout import Div, Fieldset, Layout  # type: ignore
from django import forms  # type: ignore
from django.utils.html import mark_safe  # type: ignore
from django.utils.text import format_lazy  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore

from ..choices import YES_OR_NO_OR_NONE
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
        self.fields.update({"value": forms.BooleanField(required=False)})
        self.fields["value"].help_text = _(
            mark_safe(
                format_lazy(
                    """Did {} have an acute kidney injury (<a target='_next' href='{}'>AKI</a>){}? \
<strong>Leave blank if creatinine was not checked</strong>.""",
                    self.str_attrs.get("subject_the"),
                    "https://www.aafp.org/pubs/afp/issues/2012/1001/p631/jcr:content/root/aafp-article-primary-content\
-container/aafp_article_main_par/aafp_tables_content0.enlarge.html",
                    " during this flare",
                )
            )
        )
        self.fields["value"].choices = YES_OR_NO_OR_NONE
        self.fields["value"].initial = None
        self.fields["value"].label = "Acute Kidney Injury"
        self.fields["value"].required = False
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                "",
                Div(
                    "value",
                    css_id="aki-form",
                ),
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
