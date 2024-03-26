from crispy_forms.helper import FormHelper  # type: ignore
from crispy_forms.layout import Fieldset, Layout  # type: ignore
from django import forms  # type: ignore

from ..medhistorys.choices import MedHistoryTypes
from ..utils.forms import (
    forms_helper_insert_about_the_patient,
    forms_helper_insert_cvdiseases,
    forms_helper_insert_dateofbirth,
    forms_helper_insert_gender,
    forms_helper_insert_medallergys,
    forms_helper_insert_medhistory,
    forms_helper_insert_other_nsaid_contras,
)
from ..utils.helpers import get_str_attrs
from .models import FlareAid


class FlareAidForm(
    forms.ModelForm,
):
    """
    ModelForm for creating Flare objects.
    """

    class Meta:
        model = FlareAid
        exclude = (
            "dateofbirth",
            "decisionaid",
            "gender",
            "medallergys",
            "medhistorys",
        )

    def __init__(self, *args, **kwargs):
        self.medallergys = kwargs.pop("medallergys")
        self.patient = kwargs.pop("patient", None)
        self.request_user = kwargs.pop("request_user", None)
        self.str_attrs = kwargs.pop("str_attrs", None)
        if not self.str_attrs:
            self.str_attrs = get_str_attrs(None, self.patient, self.request_user)
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
        forms_helper_insert_cvdiseases(layout=self.helper.layout, subject_the=self.str_attrs["subject_the"])
        forms_helper_insert_other_nsaid_contras(layout=self.helper.layout, subject_the=self.str_attrs["subject_the"])
        # Insert CkdForm
        forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.CKD, layout=self.helper.layout)
        # Insert ColchicineInteractionForm
        forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION, layout=self.helper.layout)
        # Insert DiabetesForm
        forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.DIABETES, layout=self.helper.layout)
        # Insert OrganTransplantForm
        forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.ORGANTRANSPLANT, layout=self.helper.layout)
        forms_helper_insert_medallergys(
            layout=self.helper.layout, treatments=self.medallergys, subject_the=self.str_attrs["subject_the"]
        )
