from typing import TYPE_CHECKING, Any, Union

from django.http import HttpResponseRedirect  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.views.generic import CreateView, UpdateView, View  # type: ignore

from ..dateofbirths.helpers import age_calc
from ..genders.choices import Genders
from ..labs.forms import BaselineCreatinineForm
from ..labs.models import BaselineCreatinine
from ..labs.selectors import dated_urates
from ..medallergys.forms import MedAllergyTreatmentForm
from ..medallergys.models import MedAllergy
from ..medhistorydetails.models import CkdDetail, GoutDetail
from ..medhistorydetails.services import CkdDetailFormProcessor
from ..medhistorys.choices import MedHistoryTypes
from ..utils.exceptions import EmptyRelatedModel

if TYPE_CHECKING:
    from crispy_forms.helper import FormHelper  # type: ignore
    from django.db.models import Model, QuerySet  # type: ignore
    from django.forms import BaseModelFormSet, ModelForm  # type: ignore
    from django.http import HttpRequest, HttpResponse  # type: ignore

    from ..labs.models import Lab
    from ..medhistorydetails.forms import CkdDetailForm, GoutDetailForm
    from ..medhistorys.models import MedHistory
    from ..models import MedHistoryAidModel  # type: ignore
    from ..treatments.choices import FlarePpxChoices, Treatments, UltChoices
    from .forms import OneToOneForm
    from .types import FormModelDict, MedAllergyAidHistoryModel


def validate_form_list(form_list: list["ModelForm"]) -> bool:
    """Method to validate a list of forms.

    Args:
        form_list: A list of ModelForms to validate.

    Returns:
        True if all forms are valid, False otherwise."""
    forms_valid = True
    for form in form_list:
        if not form.is_valid():
            forms_valid = False
    return forms_valid


class MedHistoryModelBaseView(View):
    class Meta:
        abstract = True

    onetoones: dict[str, "FormModelDict"] = {}
    medallergys: type["FlarePpxChoices"] | type["UltChoices"] | type["Treatments"] | list = []
    medhistorys: dict[MedHistoryTypes, "FormModelDict"] = {}
    medhistory_details: dict[MedHistoryTypes, "ModelForm"] = {}
    labs: tuple[type["BaseModelFormSet"], type["FormHelper"], "QuerySet", str] | None = None

    @cached_property
    def ckddetail(self) -> bool:
        """Method thataid_obj returns True if CKD is in the medhistorys dict."""
        return MedHistoryTypes.CKD in self.medhistory_details.keys()

    @cached_property
    def goutdetail(self) -> bool:
        """Method that returns True if GOUT is in the medhistorys dict."""
        return MedHistoryTypes.GOUT in self.medhistory_details.keys()

    def render_errors(
        self,
        form: "ModelForm",
        onetoone_forms: dict,
        medallergys_forms: dict,
        medhistorys_forms: dict,
        medhistorydetails_forms: dict,
        lab_formset: "BaseModelFormSet",
        labs: tuple["BaseModelFormSet", "FormHelper", "QuerySet", str] | None,
    ) -> "HttpResponse":
        """To shorten code for rendering forms with errors in multiple
        locations in post()."""
        return self.render_to_response(
            self.get_context_data(
                form=form,
                **onetoone_forms,
                **medallergys_forms,
                **medhistorys_forms,
                **medhistorydetails_forms,
                lab_formset=lab_formset,
                lab_formset_helper=labs[1] if labs else None,
            )
        )

    def update_or_create_labs_qs(self, aid_obj: "MedAllergyAidHistoryModel", labs: list["Lab"] | None) -> None:
        """Method that first checks if there is a labs_qs attribute
        to the aid_obj, creates it if not, and adds the labs to the labs_qs attribute.

        Args:
            aid_obj: MedAllergyAidHistoryModel object to add to the labs_qs attribute
            labs: Lab object to add to the labs_qs attribute

        Returns: None"""
        if hasattr(aid_obj, "labs_qs") is False:
            aid_obj.labs_qs = []
        if labs:
            for lab in labs:
                if lab not in aid_obj.labs_qs:
                    aid_obj.labs_qs.append(lab)
                # Check if the lab has a date attr and set it if not
                if hasattr(lab, "date") is False:
                    # Check if the lab has a date drawn and set date to that if so
                    if hasattr(lab, "date_drawn"):
                        lab.date = lab.date_drawn
                    # Otherwise set the date to the date_started of the Flare
                    elif hasattr(lab, "flare"):
                        lab.date = lab.flare.date_started
            # Sort the labs by date
            aid_obj.labs_qs.sort(key=lambda x: x.date, reverse=True)

    def update_or_create_medallergy_qs(
        self, aid_obj: "MedAllergyAidHistoryModel", medallergys: list["MedAllergy"] | None
    ) -> None:
        """Method that first checks if there is a medallegy_qs attribute
        to the aid_obj, creates it if not, and adds the medallergys to the medallegy_qs attribute.

        Args:
            aid_obj: MedAllergyAidHistoryModel object to add to the medhistory_qs attribute
            medallegy: MedAllegy object to add to the medallegy_qs attribute

        Returns: None"""
        if hasattr(aid_obj, "medallergys_qs") is False:
            aid_obj.medallergys_qs = []
        if medallergys:
            for medallergy in medallergys:
                if medallergy not in aid_obj.medallergys_qs:
                    aid_obj.medallergys_qs.append(medallergy)

    def update_or_create_medhistory_qs(
        self, aid_obj: "MedAllergyAidHistoryModel", medhistorys: list["MedHistory"] | None
    ) -> None:
        """Method that first checks if there is a medhistory_qs attribute
        to the aid_obj, creates it if not, and adds the medhistorys to the medhistory_qs attribute.

        Args:
            aid_obj: MedAllergyAidHistoryModel object to add to the medhistory_qs attribute
            medhistorys: MedHistory object to add to the medhistory_qs attribute

        Returns: None"""
        if hasattr(aid_obj, "medhistorys_qs") is False:
            aid_obj.medhistorys_qs = []
        if medhistorys:
            for medhistory in medhistorys:
                if medhistory not in aid_obj.medhistorys_qs:
                    aid_obj.medhistorys_qs.append(medhistory)


class MedHistorysModelCreateView(MedHistoryModelBaseView, CreateView):
    class Meta:
        abstract = True

    def form_valid(
        self,
        form,
        onetoones_to_save: list["Model"],
        medhistorydetails_to_save: list["CkdDetailForm", BaselineCreatinine, "GoutDetailForm"],
        medallergys_to_save: list["MedAllergy"],
        medhistorys_to_save: list["MedHistory"],
        labs_to_save: list["Lab"],
    ) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Method to be called if all forms are valid."""
        if self.onetoones:
            for onetoone in onetoones_to_save:
                onetoone.save()
        if self.medallergys:
            for medallergy in medallergys_to_save:
                medallergy.save()
            self.update_or_create_medallergy_qs(aid_obj=self.object, medallergys=medallergys_to_save)
        if self.medhistorys:
            if medhistorys_to_save:
                for medhistory in medhistorys_to_save:
                    medhistory.save()
            for medhistorydetail in medhistorydetails_to_save:
                medhistorydetail.save()
            # Create and populate the medhistory_qs attribute on the object
            self.update_or_create_medhistory_qs(aid_obj=self.object, medhistorys=medhistorys_to_save)
        if self.labs:
            for lab in labs_to_save:
                lab.save()
            # Create and populate the labs_qs attribute on the object
            self.update_or_create_labs_qs(aid_obj=self.object, labs=labs_to_save)
        saved_object = form.save()
        if self.medallergys:
            saved_object.add_medallergys(medallergys=medallergys_to_save, commit=False)
        if self.medhistorys:
            saved_object.add_medhistorys(medhistorys=medhistorys_to_save, commit=False)
        if self.labs:
            saved_object.add_labs(labs=labs_to_save, commit=False)
        # Return object for the child view to use
        return self.object

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        for onetoone, onetoone_dict in self.onetoones.items():
            form_str = f"{onetoone}_form"
            if form_str not in kwargs:
                kwargs[form_str] = onetoone_dict["form"]()
        if self.medallergys:
            for treatment in self.medallergys:
                form_str = f"medallergy_{treatment}_form"
                if form_str not in kwargs:
                    kwargs[form_str] = MedAllergyTreatmentForm(treatment=treatment)
        for medhistory, mh_dict in self.medhistorys.items():
            form_str = f"{medhistory}_form"
            if form_str not in kwargs:
                if medhistory == MedHistoryTypes.CKD:
                    kwargs[form_str] = mh_dict["form"](ckddetail=self.ckddetail)
                    if self.ckddetail:
                        if "ckddetail_form" not in kwargs:
                            kwargs["ckddetail_form"] = self.medhistory_details[medhistory]()
                        if "baselinecreatinine_form" not in kwargs:
                            kwargs["baselinecreatinine_form"] = BaselineCreatinineForm()
                elif medhistory == MedHistoryTypes.GOUT:
                    kwargs[form_str] = mh_dict["form"](goutdetail=self.goutdetail)
                    if self.goutdetail:
                        if "goutdetail_form" not in kwargs:
                            kwargs["goutdetail_form"] = self.medhistory_details[medhistory]()
                else:
                    kwargs[form_str] = self.medhistorys[medhistory]["form"]()
        if self.labs:
            if "lab_formset" not in kwargs:
                kwargs["lab_formset"] = self.labs[0](  # pylint: disable=unsubscriptable-object
                    queryset=self.labs[2], prefix=self.labs[3]  # pylint: disable=unsubscriptable-object
                )
                kwargs["lab_formset_helper"] = self.labs[1]  # pylint: disable=unsubscriptable-object
        return super().get_context_data(**kwargs)

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        if self.medallergys:
            kwargs["medallergys"] = self.medallergys
        return kwargs

    def post_populate_labformset(
        self,
        request: "HttpRequest",
    ) -> Union["BaseModelFormSet", None]:
        """Method to populate a dict of lab forms with POST data
        in the post() method."""
        if self.labs:
            return self.labs[0](request.POST, queryset=self.labs[2], prefix=self.labs[3])
        else:
            return None

    def post_populate_medallergys_forms(
        self,
        medallergys: None | type["FlarePpxChoices"] | type["UltChoices"] | type["Treatments"],
        request: "HttpRequest",
    ) -> dict[str, "ModelForm"]:
        medallergys_forms: dict[str, "ModelForm"] = {}
        for treatment in medallergys:
            medallergys_forms.update(
                {
                    f"medallergy_{treatment}_form": MedAllergyTreatmentForm(
                        request.POST, treatment=treatment, instance=MedAllergy()
                    )
                }
            )
        return medallergys_forms

    def post_populate_medhistorys_forms(
        self,
        medhistorys: dict[MedHistoryTypes, "FormModelDict"],
        request: "HttpRequest",
    ) -> tuple[dict[str, "ModelForm"], dict[str, "ModelForm"]]:
        medhistorys_forms = {}
        medhistorydetails_forms = {}
        for medhistory in medhistorys:
            if medhistory == MedHistoryTypes.CKD:
                medhistorys_forms.update(
                    {
                        f"{medhistory}_form": medhistorys[medhistory]["form"](
                            request.POST, instance=medhistorys[medhistory]["model"](), ckddetail=self.ckddetail
                        )
                    }
                )
                if self.ckddetail:
                    medhistorydetails_forms.update(
                        {
                            "ckddetail_form": self.medhistory_details[medhistory](request.POST, instance=CkdDetail()),
                            "baselinecreatinine_form": BaselineCreatinineForm(
                                request.POST, instance=BaselineCreatinine()
                            ),
                        }
                    )
            elif medhistory == MedHistoryTypes.GOUT:
                medhistorys_forms.update(
                    {
                        f"{medhistory}_form": medhistorys[medhistory]["form"](
                            request.POST, instance=medhistorys[medhistory]["model"](), goutdetail=self.goutdetail
                        )
                    }
                )
                if self.goutdetail:
                    medhistorydetails_forms.update(
                        {
                            "goutdetail_form": self.medhistory_details[medhistory](
                                request.POST, instance=GoutDetail()
                            ),
                        }
                    )
            else:
                medhistorys_forms.update(
                    {
                        f"{medhistory}_form": medhistorys[medhistory]["form"](
                            request.POST, instance=medhistorys[medhistory]["model"]()
                        )
                    }
                )
        return medhistorys_forms, medhistorydetails_forms

    def post_populate_onetoone_forms(
        self,
        onetoones: dict[str, "FormModelDict"],
        request: "HttpRequest",
    ) -> dict[str, "ModelForm"]:
        onetoone_forms: dict[str, "ModelForm"] = {}
        for onetoone in onetoones:
            onetoone_forms.update(
                {
                    f"{onetoone}_form": onetoones[onetoone]["form"](
                        request.POST, instance=onetoones[onetoone]["model"]()
                    )
                }
            )
        return onetoone_forms

    def post_process_onetoone_forms(
        self,
        onetoone_forms: dict[str, "ModelForm"],
        model_obj: "MedAllergyAidHistoryModel",
    ):
        """Method to process the OneToOne related models."""
        onetoones_to_save = []
        for onetoone_form_str in onetoone_forms:
            try:
                onetoone_data: "OneToOneForm" = onetoone_forms[onetoone_form_str]
                onetoone_data.check_for_value()
                onetoone = onetoone_data.save(commit=False)
                onetoones_to_save.append(onetoone)
                setattr(model_obj, onetoone_form_str.split("_")[0], onetoone)
            # If EmptyRelatedModel exception is raised by the related model's form save() method, pass
            except EmptyRelatedModel:
                pass
        return onetoones_to_save

    def post_process_lab_formset(
        self,
        lab_formset: dict["BaseModelFormSet"],
    ) -> list["Lab"]:
        """Method that processes LabForms for the post() method."""
        # Create empty list of labs to add
        labs_to_save = []
        # Iterate over the lab_forms dict to create cleaned_data checks for each form
        if self.labs:
            for lab_form in lab_formset:
                # Check if the lab_form has cleaned_data and if the lab_form has a value
                if lab_form.cleaned_data and lab_form.cleaned_data["value"]:
                    # Save the lab_form to the labs_to_save list
                    labs_to_save.append(lab_form.save(commit=False))
        return labs_to_save

    def post_process_medallergys_forms(
        self,
        medallergys_forms: dict[str, "ModelForm"],
    ) -> list["MedAllergy"]:
        medallergys_to_save = []
        for medallergy_form_str in medallergys_forms:
            # split the form string (e.g. "medallergy_colchicine_form") on "_" to get the treatment
            treatment = medallergy_form_str.split("_")[1]
            if (
                medallergys_forms[medallergy_form_str].cleaned_data
                and medallergys_forms[medallergy_form_str].cleaned_data[f"medallergy_{treatment}"]
            ):
                medallergy = medallergys_forms[medallergy_form_str].save(commit=False)
                medallergy.treatment = medallergys_forms[medallergy_form_str].cleaned_data["treatment"]
                medallergys_to_save.append(medallergy)
        return medallergys_to_save

    def post_process_medhistorys_forms(
        self,
        medhistorys_forms: dict[str, "ModelForm"],
        medhistorydetails_forms: dict[str, "ModelForm"],
        onetoone_forms: dict[str, "ModelForm"],
        errors_bool: bool,
    ) -> tuple[list["MedHistory"], list[Union["CkdDetailForm", "BaselineCreatinine", "GoutDetailForm"]], bool]:
        medhistorys_to_save = []
        medhistorydetails_to_save = []
        for medhistory_form_str in medhistorys_forms:
            medhistorytype = medhistory_form_str.split("_")[0]
            # MedHistorysForms have a "value" input field that if checked will
            # trigger the form to save() the model instance. It is prefixed by the
            # MedHistoryType, e.g. "ANGINA-value".
            if (
                medhistorys_forms[medhistory_form_str].cleaned_data
                and medhistorys_forms[medhistory_form_str].cleaned_data[f"{medhistorytype}-value"]
            ):
                medhistory = medhistorys_forms[medhistory_form_str].save(commit=False)
                medhistorys_to_save.append(medhistory)
                if medhistorytype == MedHistoryTypes.CKD and self.ckddetail:
                    (
                        medhistorydetails_forms["ckddetail_form"],
                        medhistorydetails_forms["baselinecreatinine_form"],
                        ckddetail_errors,
                    ) = CkdDetailFormProcessor(
                        ckd=medhistory,
                        ckddetail_form=medhistorydetails_forms["ckddetail_form"],
                        baselinecreatinine_form=medhistorydetails_forms["baselinecreatinine_form"],
                        dateofbirth_form=onetoone_forms["dateofbirth_form"],
                        gender_form=onetoone_forms["gender_form"],
                    ).process()
                    if ckddetail_errors and errors_bool is not True:
                        errors_bool = True
                    # Check if the returned baselinecreatinine_form's instance has the to_save attr
                    if hasattr(medhistorydetails_forms["baselinecreatinine_form"].instance, "to_save"):
                        # If so, add the baselinecreatinine_form's to the medhistorydetails_to_save list
                        medhistorydetails_to_save.append(medhistorydetails_forms["baselinecreatinine_form"])
                    # Check if the returned ckddetail_form's instance has the to_save attr
                    if hasattr(medhistorydetails_forms["ckddetail_form"].instance, "to_save"):
                        # If so, add the ckddetail_form's to the medhistorydetails_to_save list
                        medhistorydetails_to_save.append(medhistorydetails_forms["ckddetail_form"])
                elif medhistorytype == MedHistoryTypes.GOUT and self.goutdetail:
                    goutdetail = medhistorydetails_forms["goutdetail_form"].save(commit=False)
                    goutdetail.medhistory = medhistory
                    medhistorydetails_to_save.append(goutdetail)
        return medhistorys_to_save, medhistorydetails_to_save, errors_bool

    def post(self, request, *args, **kwargs):
        """Processes forms for primary and related models"""

        self.object = self.model
        form_class = self.get_form_class()
        if self.medallergys:
            form = form_class(
                request.POST, medallergys=self.medallergys, instance=self.model(), **kwargs  # type: ignore
            )
        else:
            form = form_class(request.POST, instance=self.model())
        # Populate dicts of related models with POST data
        onetoone_forms = self.post_populate_onetoone_forms(onetoones=self.onetoones, request=request)
        medallergys_forms = self.post_populate_medallergys_forms(medallergys=self.medallergys, request=request)
        medhistorys_forms, medhistorydetails_forms = self.post_populate_medhistorys_forms(
            medhistorys=self.medhistorys, request=request
        )
        # Populate the lab formset
        lab_formset = self.post_populate_labformset(request=request)
        # Call is_valid() on all forms, using validate_form_list() for dicts of related model forms
        if (
            form.is_valid()
            and validate_form_list(form_list=list(onetoone_forms.values()))
            and validate_form_list(form_list=list(medallergys_forms.values()))
            and validate_form_list(form_list=list(medhistorys_forms.values()))
            and validate_form_list(form_list=list(medhistorydetails_forms.values()))
            and (lab_formset.is_valid() if lab_formset else True)
        ):
            errors_bool = False
            object_data: "MedAllergyAidHistoryModel" = form.save(commit=False)
            onetoones_to_save = self.post_process_onetoone_forms(onetoone_forms=onetoone_forms, model_obj=object_data)
            # Iterate through the MedAllergyTreatmentForms and mark those with value for save()
            medallergys_to_save: list[MedAllergy] = self.post_process_medallergys_forms(
                medallergys_forms=medallergys_forms
            )
            medhistorys_to_save, medhistorydetails_to_save, errors_bool = self.post_process_medhistorys_forms(
                medhistorys_forms=medhistorys_forms,
                medhistorydetails_forms=medhistorydetails_forms,
                onetoone_forms=onetoone_forms,
                errors_bool=errors_bool,
            )
            # Process the lab formset forms if it exists
            labs_to_save = self.post_process_lab_formset(lab_formset=lab_formset)
            self.object = object_data
            errors = (
                self.render_errors(
                    form=form,
                    onetoone_forms=onetoone_forms,
                    medallergys_forms=medallergys_forms,
                    medhistorys_forms=medhistorys_forms,
                    medhistorydetails_forms=medhistorydetails_forms,
                    lab_formset=lab_formset,
                    labs=self.labs if hasattr(self, "labs") else None,
                )
                if errors_bool
                else None
            )
            return (
                errors,
                form,
                object_data,
                onetoone_forms,
                medallergys_forms,
                medhistorys_forms,
                medhistorydetails_forms,
                lab_formset,
                onetoones_to_save,
                medallergys_to_save,
                medhistorys_to_save,
                medhistorydetails_to_save,
                labs_to_save,
            )
        else:
            # If all the forms aren't valid unpack the related model form dicts into the context
            # and return the CreateView with the invalid forms
            errors = self.render_errors(
                form=form,
                onetoone_forms=onetoone_forms,
                medallergys_forms=medallergys_forms,
                medhistorys_forms=medhistorys_forms,
                medhistorydetails_forms=medhistorydetails_forms,
                lab_formset=lab_formset,
                labs=self.labs if hasattr(self, "labs") else None,
            )
            return (
                errors,
                form,
                None,
                onetoone_forms,
                medallergys_forms,
                medhistorys_forms,
                medhistorydetails_forms,
                lab_formset if self.labs else None,
                None,
                None,
                None,
                None,
                None,
            )


class PatientModelCreateView(MedHistorysModelCreateView):
    """Overwritten to change the view logic to create a Pseudopatient and its
    related models."""

    class Meta:
        abstract = True

    def form_valid(
        self,
        form,
        onetoones_to_save: list["Model"],
        medhistorydetails_to_save: list["CkdDetailForm", BaselineCreatinine, "GoutDetailForm"],
        medallergys_to_save: list["MedAllergy"],
        medhistorys_to_save: list["MedHistory"],
        labs_to_save: list["Lab"],
    ) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Method to be called if all forms are valid."""
        self.object = form.save()
        if self.onetoones:
            if onetoones_to_save:
                for onetoone in onetoones_to_save:
                    onetoone.user = self.object
                    onetoone.save()
        if self.medallergys:
            if medallergys_to_save:
                for medallergy in medallergys_to_save:
                    medallergy.user = self.object
                    medallergy.save()
            self.update_or_create_medallergy_qs(aid_obj=self.object, medallergys=medallergys_to_save)
        if self.medhistorys:
            if medhistorys_to_save:
                for medhistory in medhistorys_to_save:
                    medhistory.user = self.object
                    medhistory.save()
            if medhistorydetails_to_save:
                for medhistorydetail in medhistorydetails_to_save:
                    medhistorydetail.user = self.object
                    medhistorydetail.save()
            # Create and populate the medhistory_qs attribute on the object
            self.update_or_create_medhistory_qs(aid_obj=self.object, medhistorys=medhistorys_to_save)
        if self.labs:
            if labs_to_save:
                for lab in labs_to_save:
                    lab.user = self.object
                    lab.save()
            # Create and populate the labs_qs attribute on the object
            self.update_or_create_labs_qs(aid_obj=self.object, labs=labs_to_save)
        # Return object for the child view to use
        return self.object


class MedHistorysModelUpdateView(MedHistoryModelBaseView, UpdateView):
    class Meta:
        abstract = True

    def form_valid(
        self,
        form,
        onetoones_to_save: list["Model"] | None,
        onetoones_to_delete: list["Model"] | None,
        medhistorydetails_to_save: list["CkdDetailForm", BaselineCreatinine, "GoutDetailForm"] | None,
        medhistorydetails_to_remove: list["CkdDetailForm", BaselineCreatinine, "GoutDetailForm"] | None,
        medallergys_to_save: list["MedAllergy"] | None,
        medallergys_to_remove: list["MedAllergy"] | None,
        medhistorys_to_save: list["MedHistory"] | None,
        medhistorys_to_remove: list["MedHistory"] | None,
        labs_to_save: list["Lab"] | None,
        labs_to_remove: list["Lab"] | None,
        labs_to_update: list["Lab"] | None,
    ) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Method to be called if all forms are valid."""
        # Save the OneToOne related models
        if self.onetoones:
            for onetoone in onetoones_to_save:
                onetoone.save()
            for onetoone in onetoones_to_delete:
                onetoone.delete()
        if self.medallergys:
            if medallergys_to_save:
                # Modify and remove medallergys from the object
                for medallergy in medallergys_to_save:
                    medallergy.save()
            if medallergys_to_remove:
                for medallergy in medallergys_to_remove:
                    self.object.medallergys_qs.remove(medallergy)
            # Create and populate the medallergy_qs attribute on the object
            self.update_or_create_medallergy_qs(aid_obj=self.object, medallergys=medallergys_to_save)
        if self.medhistorys:
            # Modify and remove medhistorydetails from the object
            # Add and remove medhistorys from the object
            if medhistorys_to_save:
                for medhistory in medhistorys_to_save:
                    medhistory.save()
            if medhistorydetails_to_save:
                for medhistorydetail in medhistorydetails_to_save:
                    medhistorydetail.save()
            # Create and populate the medhistory_qs attribute on the object
            self.update_or_create_medhistory_qs(aid_obj=self.object, medhistorys=medhistorys_to_save)
            if medhistorys_to_remove:
                for medhistory in medhistorys_to_remove:
                    self.object.medhistorys_qs.remove(medhistory)
            if medhistorydetails_to_remove:
                for medhistorydetail in medhistorydetails_to_remove:
                    medhistorydetail.instance.delete()
        if self.labs:
            # Modify and remove labs from the object
            for lab in labs_to_save:
                lab.save()
            # Save the labs to be updated
            for lab in labs_to_update:
                lab.save()
            # Combine the labs_to_save and labs_to_update lists
            labs_to_save.extend(labs_to_update)
            # Create and populate the labs_qs attribute on the object
            self.update_or_create_labs_qs(aid_obj=self.object, labs=labs_to_save)
        self.saved_object = form.save()
        if self.medallergys:
            self.saved_object.add_medallergys(medallergys=medallergys_to_save, commit=False)
            self.saved_object.remove_medallergys(
                medallergys=medallergys_to_remove,
                commit=False,
            )
        if self.medhistorys:
            self.saved_object.add_medhistorys(medhistorys=medhistorys_to_save, commit=False)
            self.saved_object.remove_medhistorys(
                medhistorys=medhistorys_to_remove,
                commit=False,
            )
        if self.labs:
            self.saved_object.add_labs(labs=labs_to_save, commit=False)
            self.saved_object.remove_labs(labs=labs_to_remove, commit=False)
        return self.object

    def context_onetoones(
        self, onetoones: dict[str, "FormModelDict"], kwargs: dict, object: "MedAllergyAidHistoryModel"
    ) -> None:
        """Method that iterates over the onetoones dict and adds the forms to the context."""
        for onetoone in onetoones:
            form_str = f"{onetoone}_form"
            if onetoone == "dateofbirth" and form_str not in kwargs:
                kwargs[form_str] = onetoones[onetoone]["form"](
                    instance=getattr(object, onetoone),
                    initial={"value": age_calc(object.dateofbirth.value) if object.dateofbirth else None},
                )
            if form_str not in kwargs:
                kwargs[form_str] = onetoones[onetoone]["form"](instance=getattr(object, onetoone))

    def context_medallergys(
        self, medallergys: list["MedAllergy"], kwargs: dict, object: "MedAllergyAidHistoryModel"
    ) -> None:
        """Method that iterates over the medallergys list and adds the forms to the context."""
        for treatment in medallergys:
            form_str = f"medallergy_{treatment}_form"
            if form_str not in kwargs:
                qs_medallergy = [
                    qs_medallergy for qs_medallergy in object.medallergys_qs if qs_medallergy.treatment == treatment
                ]
                if qs_medallergy:
                    kwargs[form_str] = MedAllergyTreatmentForm(
                        treatment=treatment, instance=qs_medallergy[0], initial={f"medallergy_{treatment}": True}
                    )
                else:
                    kwargs[form_str] = MedAllergyTreatmentForm(treatment=treatment)

    def context_medhistorys(
        self, medhistorys: dict[MedHistoryTypes, "FormModelDict"], kwargs: dict, object: "MedAllergyAidHistoryModel"
    ) -> None:
        """Method that iterates over the medhistorys dict and adds the forms to the context."""
        for medhistory in medhistorys:
            form_str = f"{medhistory}_form"
            if form_str not in kwargs:
                qs_medhistory = [
                    qs_medhistory
                    for qs_medhistory in object.medhistorys_qs
                    if qs_medhistory.medhistorytype == medhistory
                ]
                if qs_medhistory:
                    if medhistory == MedHistoryTypes.CKD:
                        ckd = qs_medhistory[0]
                        kwargs[form_str] = medhistorys[medhistory]["form"](
                            instance=ckd,
                            initial={f"{medhistory}-value": True},
                            ckddetail=self.ckddetail,
                        )
                        if self.ckddetail:
                            if hasattr(ckd, "ckddetail") and ckd.ckddetail:
                                kwargs["ckddetail_form"] = self.medhistory_details[medhistory](instance=ckd.ckddetail)
                                if hasattr(ckd, "baselinecreatinine") and ckd.baselinecreatinine:
                                    kwargs["baselinecreatinine_form"] = BaselineCreatinineForm(
                                        instance=ckd.baselinecreatinine
                                    )
                            else:
                                kwargs["ckddetail_form"] = self.medhistory_details[medhistory]()
                            if "baselinecreatinine_form" not in kwargs:
                                kwargs["baselinecreatinine_form"] = BaselineCreatinineForm()
                    elif medhistory == MedHistoryTypes.GOUT:
                        gout = qs_medhistory[0]
                        kwargs[form_str] = medhistorys[medhistory]["form"](
                            instance=gout,
                            initial={f"{medhistory}-value": True},
                            goutdetail=self.goutdetail,
                        )
                        if self.goutdetail:
                            if hasattr(gout, "goutdetail") and gout.goutdetail:
                                kwargs["goutdetail_form"] = self.medhistory_details[medhistory](
                                    instance=gout.goutdetail
                                )
                            elif "goutdetail_form" not in kwargs:
                                kwargs["goutdetail_form"] = self.medhistory_details[medhistory]()
                    else:
                        kwargs[form_str] = self.medhistorys[medhistory]["form"](
                            instance=qs_medhistory[0], initial={f"{medhistory}-value": True}
                        )
                else:
                    if medhistory == MedHistoryTypes.CKD:
                        if self.ckddetail:
                            kwargs[form_str] = medhistorys[medhistory]["form"](
                                ckddetail=self.ckddetail, initial={f"{medhistory}-value": False}
                            )
                            if "ckddetail_form" not in kwargs:
                                kwargs["ckddetail_form"] = self.medhistory_details[medhistory]()
                            if "baselinecreatinine_form" not in kwargs:
                                kwargs["baselinecreatinine_form"] = BaselineCreatinineForm()
                        else:
                            kwargs[form_str] = medhistorys[medhistory]["form"](
                                ckddetail=None, initial={f"{medhistory}-value": False}
                            )
                    elif medhistory == MedHistoryTypes.GOUT:
                        kwargs[form_str] = medhistorys[medhistory]["form"](
                            goutdetail=self.goutdetail, initial={f"{medhistory}-value": False}
                        )
                        if self.goutdetail and "goutdetail_form" not in kwargs:
                            kwargs["goutdetail_form"] = self.medhistory_details[medhistory]()
                    # Check if the medhistory is Menopause
                    elif medhistory == MedHistoryTypes.MENOPAUSE:
                        if object.gender.value == Genders.FEMALE:
                            # Check if the Flare to be updated's gender is Female
                            age = age_calc(object.dateofbirth.value)
                            if age >= 40 and age < 60:
                                initial = False
                            elif age > 60:
                                initial = True
                            else:
                                initial = None
                            kwargs[form_str] = medhistorys[medhistory]["form"](
                                initial={f"{medhistory}-value": initial}
                            )
                        else:
                            kwargs[form_str] = medhistorys[medhistory]["form"](initial={f"{medhistory}-value": None})
                    else:
                        kwargs[form_str] = medhistorys[medhistory]["form"](initial={f"{medhistory}-value": False})

    def context_labs(
        self,
        labs_tuple: tuple[type["BaseModelFormSet"], type["FormHelper"], "QuerySet", str],
        model_obj: "MedAllergyAidHistoryModel",
        kwargs: dict,
    ) -> None:
        """Method that iterates over the labs list and adds the forms to the context."""
        if "lab_formset" not in kwargs:
            # TODO: Rewrite BaseModelFormset to take a list of objects rather than a QuerySet
            kwargs["lab_formset"] = labs_tuple[0](
                queryset=dated_urates(model_obj.labs).all().reverse(), prefix=labs_tuple[3]
            )
            kwargs["lab_formset_helper"] = labs_tuple[1]

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        if self.onetoones:
            self.context_onetoones(onetoones=self.onetoones, kwargs=kwargs, object=self.object)
        if self.medallergys:
            self.context_medallergys(medallergys=self.medallergys, kwargs=kwargs, object=self.object)
        if self.medhistorys:
            self.context_medhistorys(medhistorys=self.medhistorys, kwargs=kwargs, object=self.object)
        if self.labs:
            self.context_labs(labs_tuple=self.labs, model_obj=self.object, kwargs=kwargs)
        return super().get_context_data(**kwargs)

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        if self.medallergys:
            kwargs["medallergys"] = self.medallergys
        return kwargs

    def post_populate_labformset(
        self,
        request: "HttpRequest",
    ) -> Union["BaseModelFormSet", None]:
        """Method to populate a dict of lab forms with POST data
        in the post() method."""
        if self.labs:
            # TODO: Rewrite BaseModelFormset to take a list of objects rather than a QuerySet
            return self.labs[0](request.POST, queryset=dated_urates(self.object.labs).all(), prefix=self.labs[3])
        else:
            return None

    def post_populate_medallergys_forms(
        self,
        medallergys: None | type["FlarePpxChoices"] | type["UltChoices"] | type["Treatments"],
        post_object: "MedAllergyAidHistoryModel",
        request: "HttpRequest",
    ) -> dict[str, "ModelForm"]:
        medallergys_forms: dict[str, "ModelForm"] = {}
        if medallergys:
            for treatment in medallergys:
                medallergy_list = [
                    qs_medallergy
                    for qs_medallergy in post_object.medallergys_qs
                    if qs_medallergy.treatment == treatment
                ]
                if medallergy_list:
                    medallergy = medallergy_list[0]
                    medallergys_forms.update(
                        {
                            f"medallergy_{treatment}_form": MedAllergyTreatmentForm(
                                request.POST, treatment=treatment, instance=medallergy
                            )
                        }
                    )
                else:
                    medallergys_forms.update(
                        {f"medallergy_{treatment}_form": MedAllergyTreatmentForm(request.POST, treatment=treatment)}
                    )
        return medallergys_forms

    def post_populate_medhistorys_details_forms(
        self,
        medhistorys: dict[MedHistoryTypes, "FormModelDict"],
        post_object: "MedAllergyAidHistoryModel",
        request: "HttpRequest",
    ) -> tuple[dict[str, "ModelForm"], dict[str, "ModelForm"]]:
        """Method to populate the forms for the MedHistory and MedHistoryDetail
        objects for the MedHistorysModelUpdateView post() method."""
        medhistorys_forms: dict[str, "ModelForm"] = {}
        medhistorydetails_forms: dict[str, "ModelForm"] = {}
        if medhistorys:
            for medhistory in medhistorys:
                medhistory_list = [
                    qs_medhistory
                    for qs_medhistory in post_object.medhistorys_qs
                    if qs_medhistory.medhistorytype == medhistory
                ]
                if medhistory_list:
                    medhistory_obj = medhistory_list[0]
                    if medhistory == MedHistoryTypes.CKD:
                        medhistorys_forms.update(
                            {
                                f"{medhistory}_form": medhistorys[medhistory]["form"](
                                    request.POST,
                                    instance=medhistory_obj,
                                    initial={f"{medhistory}-value": True},
                                    ckddetail=self.ckddetail,
                                )
                            }
                        )
                        if self.ckddetail:
                            if hasattr(medhistory_obj, "ckddetail") and medhistory_obj.ckddetail:
                                medhistorydetails_forms.update(
                                    {
                                        "ckddetail_form": self.medhistory_details[medhistory](
                                            request.POST, instance=medhistory_obj.ckddetail
                                        )
                                    }
                                )
                            else:
                                medhistorydetails_forms.update(
                                    {"ckddetail_form": self.medhistory_details[medhistory](request.POST)}
                                )
                            if hasattr(medhistory_obj, "baselinecreatinine") and medhistory_obj.baselinecreatinine:
                                medhistorydetails_forms.update(
                                    {
                                        "baselinecreatinine_form": BaselineCreatinineForm(
                                            request.POST, instance=medhistory_obj.baselinecreatinine
                                        )
                                    }
                                )
                            else:
                                medhistorydetails_forms.update(
                                    {"baselinecreatinine_form": BaselineCreatinineForm(request.POST)}
                                )
                    elif medhistory == MedHistoryTypes.GOUT:
                        medhistorys_forms.update(
                            {
                                f"{medhistory}_form": medhistorys[medhistory]["form"](
                                    request.POST,
                                    instance=medhistory_obj,
                                    initial={f"{medhistory}-value": True},
                                    goutdetail=self.goutdetail,
                                )
                            }
                        )
                        if self.goutdetail:
                            if hasattr(medhistory_obj, "goutdetail") and medhistory_obj.goutdetail:
                                medhistorydetails_forms.update(
                                    {
                                        "goutdetail_form": self.medhistory_details[medhistory](
                                            request.POST, instance=medhistory_obj.goutdetail
                                        ),
                                    }
                                )
                            else:
                                medhistorydetails_forms.update(
                                    {"goutdetail_form": self.medhistory_details[medhistory](request.POST)}
                                )
                    else:
                        medhistorys_forms.update(
                            {
                                f"{medhistory}_form": medhistorys[medhistory]["form"](
                                    request.POST, instance=medhistory_obj, initial={f"{medhistory}-value": True}
                                )
                            }
                        )
                else:
                    if medhistory == MedHistoryTypes.CKD:
                        medhistorys_forms.update(
                            {
                                f"{medhistory}_form": medhistorys[medhistory]["form"](
                                    request.POST,
                                    instance=medhistorys[medhistory]["model"](),
                                    initial={f"{medhistory}-value": False},
                                    ckddetail=self.ckddetail,
                                ),
                            }
                        )
                        if self.ckddetail:
                            medhistorydetails_forms.update(
                                {
                                    "ckddetail_form": self.medhistory_details[medhistory](
                                        request.POST, instance=CkdDetail()
                                    ),
                                    "baselinecreatinine_form": BaselineCreatinineForm(
                                        request.POST, instance=BaselineCreatinine()
                                    ),
                                }
                            )
                    elif medhistory == MedHistoryTypes.GOUT:
                        medhistorys_forms.update(
                            {
                                f"{medhistory}_form": medhistorys[medhistory]["form"](
                                    request.POST,
                                    instance=medhistorys[medhistory]["model"](),
                                    initial={f"{medhistory}-value": False},
                                    goutdetail=self.goutdetail,
                                ),
                            }
                        )
                        if self.goutdetail:
                            medhistorydetails_forms.update(
                                {
                                    "goutdetail_form": self.medhistory_details[medhistory](
                                        request.POST, instance=GoutDetail()
                                    ),
                                }
                            )
                    else:
                        medhistorys_forms.update(
                            {
                                f"{medhistory}_form": medhistorys[medhistory]["form"](
                                    request.POST,
                                    instance=medhistorys[medhistory]["model"](),
                                    initial={f"{medhistory}-value": False},
                                )
                            }
                        )
        return medhistorys_forms, medhistorydetails_forms

    def post_populate_onetoone_forms(
        self, onetoones: dict[str, "FormModelDict"], post_object: "MedAllergyAidHistoryModel", request: "HttpRequest"
    ) -> dict[str, "ModelForm"]:
        onetoone_forms: dict[str, "ModelForm"] = {}
        if onetoones:
            for onetoone in onetoones:
                onetoone_forms.update(
                    {
                        f"{onetoone}_form": onetoones[onetoone]["form"](
                            request.POST, instance=getattr(post_object, onetoone)
                        )
                    }
                )
        return onetoone_forms

    def post_process_medallergys_forms(
        self,
        medallergys_forms: dict[str, "ModelForm"],
        post_object: "MedAllergyAidHistoryModel",
    ) -> tuple[list["MedAllergy"], list["MedAllergy"]]:
        medallergys_to_save: list["MedAllergy"] = []
        medallergys_to_remove: list["MedAllergy"] = []
        for medallergy_form_str in medallergys_forms:
            treatment = medallergy_form_str.split("_")[1]
            if f"medallergy_{treatment}" in medallergys_forms[medallergy_form_str].cleaned_data:
                medallergy_list = [
                    qs_medallergy
                    for qs_medallergy in post_object.medallergys_qs
                    if qs_medallergy.treatment == treatment
                ]
                if medallergy_list:
                    medallergy = medallergy_list[0]
                    if not medallergys_forms[medallergy_form_str].cleaned_data[f"medallergy_{treatment}"]:
                        medallergys_to_remove.append(medallergy)
                else:
                    if medallergys_forms[medallergy_form_str].cleaned_data[f"medallergy_{treatment}"]:
                        medallergy = medallergys_forms[medallergy_form_str].save(commit=False)
                        # Assign MedAllergy object treatment attr from the cleaned_data["treatment"]
                        medallergy.treatment = medallergys_forms[medallergy_form_str].cleaned_data["treatment"]
                        medallergys_to_save.append(medallergy)
        return medallergys_to_save, medallergys_to_remove

    def post_process_medhistorys_details_forms(
        self,
        medhistorys_forms: dict[str, "ModelForm"],
        medhistorydetails_forms: dict[str, "ModelForm"],
        post_object: "MedAllergyAidHistoryModel",
        onetoone_forms: dict[str, "ModelForm"],
        errors_bool: bool,
    ) -> tuple[
        list["MedHistory"],
        list["MedHistory"],
        list["CkdDetailForm", BaselineCreatinine, "GoutDetailForm"],
        list[CkdDetail, BaselineCreatinine, None],
        bool,
    ]:
        medhistorys_to_save: list["MedHistory"] = []
        medhistorys_to_remove: list["MedHistory"] = []
        medhistorydetails_to_save: list["CkdDetailForm" | BaselineCreatinine | "GoutDetailForm"] = []
        medhistorydetails_to_remove: list[CkdDetail | BaselineCreatinine | None] = []
        for medhistory_form_str in medhistorys_forms:
            medhistorytype = medhistory_form_str.split("_")[0]
            # MedHistorysForms have a "value" input field that if checked means the
            # Object has that medhistory in its medhistorys field.
            # It is prefixed by the MedHistoryType, e.g. "ANGINA-value".
            if f"{medhistorytype}-value" in medhistorys_forms[medhistory_form_str].cleaned_data:
                # Check if the Object has a medhistory that no longer has a value in the form data
                medhistory_list = [
                    qs_medhistory
                    for qs_medhistory in post_object.medhistorys_qs
                    if qs_medhistory.medhistorytype == medhistorytype
                ]
                if medhistory_list:
                    medhistory = medhistory_list[0]
                    if not medhistorys_forms[medhistory_form_str].cleaned_data[f"{medhistorytype}-value"]:
                        # Mark it for deletion if so
                        medhistorys_to_remove.append(medhistorys_forms[medhistory_form_str].instance)
                    # Check if the MedHistory is CKD or Gout and process related models/forms
                    elif medhistorytype == MedHistoryTypes.CKD and self.ckddetail:
                        (
                            medhistorydetails_forms["ckddetail_form"],
                            medhistorydetails_forms["baselinecreatinine_form"],
                            ckddetail_errors,
                        ) = CkdDetailFormProcessor(
                            ckd=medhistory,
                            ckddetail_form=medhistorydetails_forms["ckddetail_form"],  # type: ignore
                            baselinecreatinine_form=medhistorydetails_forms["baselinecreatinine_form"],  # type: ignore
                            dateofbirth_form=onetoone_forms["dateofbirth_form"],  # type: ignore
                            gender_form=onetoone_forms["gender_form"],  # type: ignore
                        ).process()
                        # Check if the returned baselinecreatinine_form's instance has the to_save attr
                        if hasattr(medhistorydetails_forms["baselinecreatinine_form"].instance, "to_save"):
                            # If so, add the baselinecreatinine_form's to the medhistorydetails_to_save list
                            medhistorydetails_to_save.append(medhistorydetails_forms["baselinecreatinine_form"])
                        elif hasattr(medhistorydetails_forms["baselinecreatinine_form"].instance, "to_delete"):
                            medhistorydetails_to_remove.append(medhistorydetails_forms["baselinecreatinine_form"])
                        # Check if the returned ckddetail_form's instance has the to_save attr
                        if hasattr(medhistorydetails_forms["ckddetail_form"].instance, "to_save"):
                            # If so, add the ckddetail_form's to the medhistorydetails_to_save list
                            medhistorydetails_to_save.append(medhistorydetails_forms["ckddetail_form"])
                        elif hasattr(medhistorydetails_forms["ckddetail_form"].instance, "to_delete"):
                            medhistorydetails_to_remove.append(medhistorydetails_forms["ckddetail_form"])
                        if ckddetail_errors and errors_bool is not True:
                            errors_bool = True
                    elif medhistorytype == MedHistoryTypes.GOUT and self.goutdetail:
                        goutdetail_form = medhistorydetails_forms["goutdetail_form"]
                        if (
                            "flaring" in goutdetail_form.changed_data
                            or "hyperuricemic" in goutdetail_form.changed_data
                            or "on_ppx" in goutdetail_form.changed_data
                            or "on_ult" in goutdetail_form.changed_data
                            or not getattr(goutdetail_form.instance, "medhistory", None)
                        ):
                            medhistorydetails_to_save.append(goutdetail_form.save(commit=False))
                            # Check if the form instance has a medhistory attr
                            if getattr(goutdetail_form.instance, "medhistory", None):
                                # If not, set it to the medhistory instance
                                goutdetail_form.instance.medhistory = medhistory
                # Otherwise add medhistorys that are checked in the form data
                else:
                    if medhistorys_forms[medhistory_form_str].cleaned_data[f"{medhistorytype}-value"]:
                        medhistory = medhistorys_forms[medhistory_form_str].save(commit=False)
                        medhistorys_to_save.append(medhistory)
                        if medhistorytype == MedHistoryTypes.CKD and self.ckddetail:
                            ckddetail, baselinecreatinine, ckddetail_errors = CkdDetailFormProcessor(
                                ckd=medhistory,
                                ckddetail_form=medhistorydetails_forms["ckddetail_form"],  # type: ignore
                                baselinecreatinine_form=medhistorydetails_forms[
                                    "baselinecreatinine_form"
                                ],  # type: ignore
                                dateofbirth_form=onetoone_forms["dateofbirth_form"],  # type: ignore
                                gender_form=onetoone_forms["gender_form"],  # type: ignore
                            ).process()
                            # Need mark baselinecreatinine and ckddetail for saving because their
                            # related Ckd object will not have been saved yet
                            if baselinecreatinine and baselinecreatinine.instance:
                                # Check if the baselinecreatinine has a to_delete attr, and mark for deletion if so
                                if hasattr(baselinecreatinine.instance, "to_delete"):
                                    medhistorydetails_to_remove.append(baselinecreatinine)
                                elif hasattr(baselinecreatinine.instance, "to_save"):
                                    medhistorydetails_to_save.append(baselinecreatinine)
                            if ckddetail:
                                if ckddetail.instance and hasattr(ckddetail.instance, "to_delete"):
                                    medhistorydetails_to_remove.append(ckddetail)
                                elif ckddetail.instance and hasattr(ckddetail.instance, "to_save"):
                                    medhistorydetails_to_save.append(ckddetail)
                            if ckddetail_errors and errors_bool is not True:
                                errors_bool = True
        return (
            medhistorys_to_save,
            medhistorys_to_remove,
            medhistorydetails_to_save,
            medhistorydetails_to_remove,
            errors_bool,
        )

    def post_process_one_to_one_forms(
        self, onetoone_forms: dict[str, "ModelForm"], model_obj: "MedAllergyAidHistoryModel"
    ) -> tuple[list["Model"], list["Model"]]:
        """Method to process the forms for the OneToOne objects for
        the MedHistorysModelUpdateView post() method."""

        onetoones_to_save: list["Model"] = []
        onetoones_to_delete: list["Model"] = []
        # Set related models for saving and set as attrs of the UpdateView model instance
        for onetoone_form_str, onetoone_form in onetoone_forms.items():
            object_attr = onetoone_form_str.split("_")[0]
            try:
                onetoone_form.check_for_value()
                onetoone = onetoone_form.save(commit=False)
                onetoones_to_save.append(onetoone)
                setattr(model_obj, object_attr, onetoone)
            # If EmptyRelatedModel exception is raised by the related model's form save() method,
            # Check if the related model exists and delete it if it does
            except EmptyRelatedModel:
                if getattr(self.object, object_attr):
                    to_delete = getattr(self.object, object_attr)
                    # Iterate over the forms required_fields property and set the related model's
                    # fields to their initial values to prevent IntegrityError from Django-Simple-History
                    # historical model on delete().
                    if hasattr(onetoone_form, "required_fields"):
                        for field in onetoone_form.required_fields:
                            setattr(to_delete, field, onetoone_form.initial[field])
                    # Set the object attr to None so it is reflected in the QuerySet fed to update in form_valid()
                    setattr(self.object, object_attr, None)
                    onetoones_to_delete.append(to_delete)
        return onetoones_to_save, onetoones_to_delete

    def post_process_lab_formset(
        self,
        lab_formset: "BaseModelFormSet",
    ) -> tuple[list["Lab"], list["Lab"], list["Lab"]]:
        """Method to process the forms in a Lab formset for the MedHistorysModelUpdateView post() method.
        Requires a list of existing labs (can be empty) to iterate over and compare to the forms in the
        formset to identify labs that need to be removed."""
        # Assign lists to return
        labs_to_save: list["Lab"] = []
        labs_to_remove: list["Lab"] = []
        labs_to_update: list["Lab"] = []
        if lab_formset:
            # Iterate over the object's existing labs
            for lab in self.object.labs_qs:
                cleaned_data = lab_formset.cleaned_data
                # Check if the lab is not in the formset's cleaned_data list by id key
                for lab_form in cleaned_data:
                    try:
                        if lab_form["id"] == lab:
                            # Check if the form is not marked for deletion
                            if not lab_form["DELETE"]:
                                # If so, break out of the loop
                                break
                            # If it is marked for deletion, it will be removed by the formset loop below
                    except KeyError:
                        pass
                else:
                    # If not, add the lab to the labs_to_remove list
                    labs_to_remove.append(lab)
            # Iterate over the forms in the formset
            for form in lab_formset:
                # Check if the form has a value in the "value" field
                if "value" in form.cleaned_data:
                    # Check if the form has an instance and the form has changed
                    if form.instance and form.has_changed() and not form.cleaned_data["DELETE"]:
                        # Add the form's instance to the labs_to_update list
                        labs_to_update.append(form.instance)
                    # If there's a value but no instance, add the form's instance to the labs_to_save list
                    elif form.instance is None:
                        labs_to_save.append(form.instance)
        return labs_to_save, labs_to_remove, labs_to_update

    def post(self, request, *args, **kwargs):
        """Processes forms for primary and related models"""

        self.object: "MedAllergyAidHistoryModel" = self.get_object()  # type: ignore
        form_class = self.get_form_class()
        if self.medallergys:
            form = form_class(request.POST, medallergys=self.medallergys, instance=self.object)
        else:
            form = form_class(request.POST, instance=self.object)
        # Populate dicts for related models with POST data
        onetoone_forms = self.post_populate_onetoone_forms(
            onetoones=self.onetoones, post_object=self.object, request=request
        )
        medallergys_forms = self.post_populate_medallergys_forms(
            medallergys=self.medallergys, post_object=self.object, request=request
        )
        medhistorys_forms, medhistorydetails_forms = self.post_populate_medhistorys_details_forms(
            medhistorys=self.medhistorys, post_object=self.object, request=request
        )
        lab_formset = self.post_populate_labformset(request=request)
        # Call is_valid() on all forms, using validate_form_list() for dicts of related model forms
        if (
            form.is_valid()
            and validate_form_list(form_list=onetoone_forms.values())
            and validate_form_list(form_list=medallergys_forms.values())
            and validate_form_list(form_list=medhistorys_forms.values())
            and validate_form_list(form_list=medhistorydetails_forms.values())
            and (not lab_formset or lab_formset.is_valid())
        ):
            errors_bool = False
            object_data: "MedHistoryAidModel" = form.save(commit=False)
            # Set related models for saving and set as attrs of the UpdateView model instance
            onetoones_to_save, onetoones_to_delete = self.post_process_one_to_one_forms(
                onetoone_forms=onetoone_forms, model_obj=object_data
            )
            medallergys_to_save, medallergys_to_remove = self.post_process_medallergys_forms(
                medallergys_forms=medallergys_forms, post_object=object_data
            )
            (
                medhistorys_to_save,
                medhistorys_to_remove,
                medhistorydetails_to_save,
                medhistorydetails_to_remove,
                errors_bool,
            ) = self.post_process_medhistorys_details_forms(
                medhistorys_forms=medhistorys_forms,
                medhistorydetails_forms=medhistorydetails_forms,
                post_object=object_data,
                onetoone_forms=onetoone_forms,
                errors_bool=errors_bool,
            )
            (
                labs_to_save,
                labs_to_remove,
                labs_to_update,
            ) = self.post_process_lab_formset(lab_formset=lab_formset)
            # If there are errors picked up after the initial validation step
            # render the errors as errors and include in the return tuple
            errors = (
                self.render_errors(
                    form=form,
                    onetoone_forms=onetoone_forms,
                    medallergys_forms=medallergys_forms,
                    medhistorys_forms=medhistorys_forms,
                    medhistorydetails_forms=medhistorydetails_forms,
                    lab_formset=lab_formset,
                    labs=self.labs if hasattr(self, "labs") else None,
                )
                if errors_bool
                else None
            )
            return (
                errors,
                form,
                object_data,
                onetoone_forms,
                medhistorys_forms,
                medhistorydetails_forms,
                medallergys_forms,
                lab_formset,
                medallergys_to_save,
                medallergys_to_remove,
                onetoones_to_delete,
                onetoones_to_save,
                medhistorydetails_to_save,
                medhistorydetails_to_remove,
                medhistorys_to_save,
                medhistorys_to_remove,
                labs_to_save,
                labs_to_remove,
                labs_to_update,
            )
        else:
            # If all the forms aren't valid unpack the related model form dicts into the context
            # and return the UpdateView with the invalid forms
            errors = self.render_errors(
                form=form,
                onetoone_forms=onetoone_forms,
                medallergys_forms=medallergys_forms,
                medhistorys_forms=medhistorys_forms,
                medhistorydetails_forms=medhistorydetails_forms,
                lab_formset=lab_formset,
                labs=self.labs if hasattr(self, "labs") else None,
            )
            return (
                errors,
                form,
                None,
                onetoone_forms,
                medhistorys_forms,
                medhistorydetails_forms,
                medallergys_forms,
                lab_formset if self.labs else None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            )
