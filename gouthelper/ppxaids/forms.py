from crispy_forms.helper import FormHelper  # type: ignore
from crispy_forms.layout import Fieldset, Layout  # type: ignore
from django import forms  # type: ignore

from ..medhistorys.choices import MedHistoryTypes
from ..utils.helpers.form_helpers import (
    forms_helper_insert_about_the_patient,
    forms_helper_insert_cvdiseases,
    forms_helper_insert_dateofbirth,
    forms_helper_insert_gender,
    forms_helper_insert_medallergys,
    forms_helper_insert_medhistory,
    forms_helper_insert_other_nsaid_contras,
)
from .models import PpxAid


class PpxAidForm(
    forms.ModelForm,
):
    """
    ModelForm for creating PpxAid objects.
    """

    class Meta:
        model = PpxAid
        exclude = (
            "dateofbirth",
            "decisionaid",
            "gender",
            "medallergys",
            "medhistorys",
        )

    def __init__(self, *args, **kwargs):
        # pop medallergys patients from kwargs in order to populate form from the view
        self.medallergys = kwargs.pop("medallergys")
        self.patient = kwargs.pop("patient", None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                "",
            ),
        )
        forms_helper_insert_about_the_patient(layout=self.helper.layout)
        if not self.patient:
            forms_helper_insert_dateofbirth(layout=self.helper.layout)
            forms_helper_insert_gender(layout=self.helper.layout)
        forms_helper_insert_cvdiseases(layout=self.helper.layout)
        forms_helper_insert_other_nsaid_contras(layout=self.helper.layout)
        forms_helper_insert_medhistory(layout=self.helper.layout, medhistorytype=MedHistoryTypes.CKD)
        forms_helper_insert_medhistory(layout=self.helper.layout, medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION)
        forms_helper_insert_medhistory(layout=self.helper.layout, medhistorytype=MedHistoryTypes.DIABETES)
        forms_helper_insert_medhistory(layout=self.helper.layout, medhistorytype=MedHistoryTypes.ORGANTRANSPLANT)
        forms_helper_insert_medallergys(layout=self.helper.layout, treatments=self.medallergys)
