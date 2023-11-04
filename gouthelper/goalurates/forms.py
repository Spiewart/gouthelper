from crispy_forms.helper import FormHelper  # type: ignore
from crispy_forms.layout import Fieldset, Layout  # type: ignore
from django import forms  # type: ignore

from ..medhistorys.choices import MedHistoryTypes
from ..utils.form_helpers import forms_helper_insert_about_the_patient, forms_helper_insert_medhistory
from .models import GoalUrate


class GoalUrateForm(
    forms.ModelForm,
):
    """
    ModelForm for creating GoalUrate objects.
    """

    class Meta:
        model = GoalUrate
        exclude = (
            "goal_urate",
            "medhistorys",
            "ultaid",
        )

    def __init__(self, *args, **kwargs):
        htmx = kwargs.pop("htmx", False)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                "",
            ),
        )
        forms_helper_insert_about_the_patient(layout=self.helper.layout, htmx=htmx)
        # Insert ErosionsForm
        forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.EROSIONS, layout=self.helper.layout)
        # Insert TophiForm
        forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.TOPHI, layout=self.helper.layout)
