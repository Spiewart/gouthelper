from crispy_forms.helper import FormHelper  # type: ignore
from crispy_forms.layout import Div, Fieldset, Layout  # type: ignore
from django import forms  # type: ignore

from ..medhistorys.models import MedHistoryTypes
from ..utils.helpers.form_helpers import forms_helper_insert_medhistory, forms_helper_insert_urates_formset
from .models import Ppx


class PpxForm(
    forms.ModelForm,
):
    """
    ModelForm for creating PpxAid objects.
    """

    class Meta:
        model = Ppx
        exclude = (
            "indication",
            "labs",
            "medhistorys",
            "user",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[
            "starting_ult"
        ].help_text = "Is the patient either just starting ULT (urate-lowering therapy) or \
has started ULT in the last 3 months?"
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                "",
                Div(),
            ),
        )
        # Insert GoutForm
        forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.GOUT, layout=self.helper.layout)
        layout_len = len(self.helper.layout)
        sub_len = len(self.helper.layout[layout_len - 1])
        self.helper.layout[layout_len - 1][sub_len - 1].append(
            Div(
                Div(
                    Div(
                        "starting_ult",
                        css_class="col",
                    ),
                ),
                css_class="row",
                css_id="starting_ult",
            ),
        )
        forms_helper_insert_urates_formset(layout=self.helper.layout)
