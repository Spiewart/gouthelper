from crispy_forms.helper import FormHelper  # type: ignore
from crispy_forms.layout import Fieldset, Layout  # type: ignore
from django import forms  # type: ignore

from ..medhistorys.choices import MedHistoryTypes
from ..utils.helpers.form_helpers import (
    forms_helper_insert_about_the_patient,
    forms_helper_insert_cvdiseases,
    forms_helper_insert_dateofbirth,
    forms_helper_insert_ethnicity,
    forms_helper_insert_gender,
    forms_helper_insert_hlab5801,
    forms_helper_insert_medallergys,
    forms_helper_insert_medhistory,
)
from .models import UltAid


class UltAidForm(
    forms.ModelForm,
):
    """
    ModelForm for creating UltAid objects.
    """

    class Meta:
        model = UltAid
        exclude = (
            "dateofbirth",
            "decisionaid",
            "gender",
            "hlab5801",
            "medallergys",
            "medhistorys",
            "ethnicity",
        )

    def __init__(self, *args, **kwargs):
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
        forms_helper_insert_ethnicity(layout=self.helper.layout)
        forms_helper_insert_hlab5801(layout=self.helper.layout)
        forms_helper_insert_cvdiseases(layout=self.helper.layout)
        # Insert CkdForm
        forms_helper_insert_medhistory(layout=self.helper.layout, medhistorytype=MedHistoryTypes.CKD)
        forms_helper_insert_dateofbirth(layout=self.helper.layout)
        forms_helper_insert_gender(layout=self.helper.layout)
        # Insert XoiInteractionForm
        forms_helper_insert_medhistory(layout=self.helper.layout, medhistorytype=MedHistoryTypes.XOIINTERACTION)
        # Insert OrganTransplantForm
        forms_helper_insert_medhistory(layout=self.helper.layout, medhistorytype=MedHistoryTypes.ORGANTRANSPLANT)
        forms_helper_insert_medallergys(layout=self.helper.layout, treatments=self.medallergys)
        # Insert AllopurinolHypersensitivityForm
        forms_helper_insert_medhistory(
            layout=self.helper.layout, medhistorytype=MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY
        )
        # Insert FebuxostatHypersensitivityForm
        forms_helper_insert_medhistory(
            layout=self.helper.layout, medhistorytype=MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY
        )
