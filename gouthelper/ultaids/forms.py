from crispy_forms.helper import FormHelper  # type: ignore
from crispy_forms.layout import Fieldset, Layout  # type: ignore
from django import forms  # type: ignore

from ..medhistorys.choices import MedHistoryTypes
from ..utils.forms import (
    RelatedObjectModelFormMixin,
    forms_helper_insert_about_the_patient_legend,
    forms_helper_insert_cvdiseases,
    forms_helper_insert_dateofbirth,
    forms_helper_insert_ethnicity,
    forms_helper_insert_gender,
    forms_helper_insert_hlab5801,
    forms_helper_insert_medallergys,
    forms_helper_insert_medhistory,
)
from ..utils.helpers import get_str_attrs
from .models import UltAid


class UltAidForm(
    RelatedObjectModelFormMixin,
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
            "ethnicity",
        )

    def __init__(self, *args, **kwargs):
        self.medallergys = kwargs.pop("medallergys")
        self.patient = kwargs.pop("patient", None)
        self.ethnicity = True
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
            ),
        )
        forms_helper_insert_about_the_patient_legend(form=self)
        if not self.patient:
            forms_helper_insert_ethnicity(layout=self.helper.layout)
        forms_helper_insert_hlab5801(layout=self.helper.layout)
        forms_helper_insert_cvdiseases(layout=self.helper.layout, subject_the=self.str_attrs["subject_the"])
        forms_helper_insert_medhistory(layout=self.helper.layout, medhistorytype=MedHistoryTypes.CKD)
        if not self.patient:
            forms_helper_insert_dateofbirth(layout=self.helper.layout)
            forms_helper_insert_gender(layout=self.helper.layout)
        forms_helper_insert_medhistory(layout=self.helper.layout, medhistorytype=MedHistoryTypes.XOIINTERACTION)
        forms_helper_insert_medhistory(layout=self.helper.layout, medhistorytype=MedHistoryTypes.ORGANTRANSPLANT)
        forms_helper_insert_medallergys(layout=self.helper.layout, treatments=self.medallergys)
        forms_helper_insert_medhistory(layout=self.helper.layout, medhistorytype=MedHistoryTypes.HEPATITIS)
        forms_helper_insert_medhistory(layout=self.helper.layout, medhistorytype=MedHistoryTypes.URATESTONES)
