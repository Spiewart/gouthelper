from crispy_forms.helper import FormHelper  # type: ignore
from crispy_forms.layout import Div, Fieldset, Layout  # type: ignore
from django import forms  # type: ignore

from ..medhistorys.models import MedHistoryTypes
from ..utils.forms import (
    forms_helper_insert_goutdetail,
    forms_helper_insert_medhistory,
    forms_helper_insert_urates_formset,
)
from ..utils.helpers import get_str_attrs
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
            "user",
        )

    def __init__(self, *args, **kwargs):
        self.patient = kwargs.pop("patient", None)
        self.request_user = kwargs.pop("request_user", None)
        self.str_attrs = kwargs.pop("str_attrs", None)
        if not self.str_attrs:
            self.str_attrs = get_str_attrs(self, self.patient, self.request_user)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                "",
                Div(),
            ),
        )
        # Check if there's a patient: if so, only add the GoutDetailForm
        if self.patient:
            forms_helper_insert_goutdetail(layout=self.helper.layout)
        # Otherwise, add the GoutForm and GoutDetailForm
        else:
            forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.GOUT, layout=self.helper.layout)
        forms_helper_insert_urates_formset(layout=self.helper.layout, str_attrs=self.str_attrs)
