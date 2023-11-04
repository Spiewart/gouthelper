from crispy_forms.helper import FormHelper  # type: ignore
from crispy_forms.layout import HTML, Div, Fieldset, Layout  # type: ignore
from django import forms  # type: ignore

from ..medhistorys.choices import MedHistoryTypes
from ..utils.form_helpers import (
    forms_helper_insert_cvdiseases,
    forms_helper_insert_dateofbirth,
    forms_helper_insert_gender,
    forms_helper_insert_medallergys,
    forms_helper_insert_medhistory,
    forms_helper_insert_other_nsaid_contras,
)
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
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                "",
                Div(
                    HTML(
                        """
                            <hr size="3" color="dark">
                            <legend>About the Patient</legend>
                            """
                    ),
                ),
            ),
        )
        forms_helper_insert_dateofbirth(layout=self.helper.layout)
        forms_helper_insert_gender(layout=self.helper.layout)
        forms_helper_insert_cvdiseases(layout=self.helper.layout)
        forms_helper_insert_other_nsaid_contras(layout=self.helper.layout)
        # Insert CkdForm
        forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.CKD, layout=self.helper.layout)
        # Insert ColchicineInteractionForm
        forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION, layout=self.helper.layout)
        # Insert DiabetesForm
        forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.DIABETES, layout=self.helper.layout)
        # Insert OrganTransplantForm
        forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.ORGANTRANSPLANT, layout=self.helper.layout)
        forms_helper_insert_medallergys(layout=self.helper.layout, treatments=self.medallergys)
