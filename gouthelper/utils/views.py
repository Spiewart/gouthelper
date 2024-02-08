from typing import TYPE_CHECKING, Any, Literal, Union

from django.http import HttpResponseRedirect  # type: ignore
from django.urls import reverse
from django.utils.functional import cached_property  # type: ignore
from django.views.generic import CreateView, UpdateView  # type: ignore

from ..dateofbirths.helpers import age_calc
from ..flares.models import Flare
from ..labs.forms import BaselineCreatinineForm
from ..labs.models import BaselineCreatinine
from ..medallergys.forms import MedAllergyTreatmentForm
from ..medallergys.models import MedAllergy
from ..medhistorydetails.models import CkdDetail, GoutDetail
from ..medhistorydetails.services import CkdDetailFormProcessor
from ..medhistorys.choices import MedHistoryTypes
from ..users.choices import Roles
from ..users.selectors import pseudopatient_qs_plus
from ..utils.exceptions import EmptyRelatedModel
from ..utils.helpers.helpers import get_or_create_qs_attr, set_to_delete, set_to_save

if TYPE_CHECKING:
    from crispy_forms.helper import FormHelper  # type: ignore
    from django.db.models import Model, QuerySet  # type: ignore
    from django.forms import BaseModelFormSet, ModelForm  # type: ignore
    from django.http import HttpRequest, HttpResponse  # type: ignore

    from ..labs.models import Lab
    from ..medhistorydetails.forms import CkdDetailForm, GoutDetailForm
    from ..medhistorys.models import MedHistory
    from ..treatments.choices import FlarePpxChoices, Treatments, UltChoices
    from ..users.models import User
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


def validate_formset_list(formset_list: list["BaseModelFormSet"]) -> bool:
    """Method to validate a list of formsets.

    Args:
        formset_list: A list of BaseModelFormSets to validate.

    Returns:
        True if all formsets are valid, False otherwise."""
    formsets_valid = True
    for formset in formset_list:
        if not formset.is_valid():
            formsets_valid = False
    return formsets_valid


class MedHistoryModelBaseMixin:
    onetoones: dict[str, "FormModelDict"] = {}
    medallergys: type["FlarePpxChoices"] | type["UltChoices"] | type["Treatments"] | list = []
    medhistorys: dict[MedHistoryTypes, "FormModelDict"] = {}
    medhistory_details: dict[MedHistoryTypes, "ModelForm"] = {}
    labs: dict[Literal["urate"], tuple[type["BaseModelFormSet"], type["FormHelper"], "QuerySet"]] | None = None

    @cached_property
    def ckddetail(self) -> bool:
        """Method that returns True if CKD is in the medhistory_details dict."""
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
        lab_formsets: dict[str, "BaseModelFormSet"] | None,
        labs: dict[Literal["urate"], tuple["BaseModelFormSet", "FormHelper", "QuerySet"]] | None,
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
                **lab_formsets if lab_formsets else {},
                **{f"{lab}_formset_helper": lab_tup[1] for lab, lab_tup in labs.items()} if labs else {},
            )
        )

    def update_or_create_labs_qs(
        self,
        aid_obj: "MedAllergyAidHistoryModel",
        labs_include: list["Lab"] | None,
        labs_remove: list["Lab"] | None,
    ) -> None:
        """Method that first checks if there is a labs_qs attribute
        to the aid_obj, creates it if not, and adds the labs to the labs_qs attribute.

        Args:
            aid_obj: MedAllergyAidHistoryModel object to add to the labs_qs attribute
            labs_include: Lab objects to include in the qs
            labs_remove: Lab objects to remove from the qs

        Returns: None"""
        if labs_include:
            for lab in labs_include:
                lab_name = lab.__class__.__name__.lower()
                lab_qs_attr = get_or_create_qs_attr(obj=aid_obj, name=lab_name)
                if lab not in lab_qs_attr:
                    lab_qs_attr.append(lab)
                # Check if the lab has a date attr and set it if not
                if hasattr(lab, "date") is False:
                    # Check if the lab has a date drawn and set date to that if so
                    if hasattr(lab, "date_drawn"):
                        lab.date = lab.date_drawn
                    # Otherwise set the date to the date_started of the Flare
                    elif hasattr(lab, "flare"):
                        lab.date = lab.flare.date_started
            # Sort the labs by date
            lab_qs_attr.sort(key=lambda x: x.date, reverse=True)
        if labs_remove:
            for lab in labs_remove:
                lab_name = lab.__class__.__name__.lower()
                lab_qs_attr = get_or_create_qs_attr(obj=aid_obj, name=lab_name)
                if lab in lab_qs_attr:
                    lab_qs_attr.remove(lab)

    def update_or_create_medallergy_qs(
        self,
        aid_obj: "MedAllergyAidHistoryModel",
        ma_include: list["MedAllergy"] | None,
        ma_remove: list["MedAllergy"] | None,
    ) -> None:
        """Method that first checks if there is a medallegy_qs attribute
        to the aid_obj, creates it if not, and adds the medallergys to the medallegy_qs attribute.

        Args:
            aid_obj: MedAllergyAidHistoryModel object to add to the medhistory_qs attribute
            ma_include: MedAllegy objects to include in the qs
            ma_remove: MedAllergy objects to remove from the qs

        Returns: None"""
        if hasattr(aid_obj, "medallergys_qs") is False:
            aid_obj.medallergys_qs = []
        if ma_include:
            for ma in ma_include:
                if ma not in aid_obj.medallergys_qs:
                    aid_obj.medallergys_qs.append(ma)
        if ma_remove:
            for ma in ma_remove:
                if ma in aid_obj.medallergys_qs:
                    aid_obj.medallergys_qs.remove(ma)

    def update_or_create_medhistory_qs(
        self,
        aid_obj: "MedAllergyAidHistoryModel",
        mh_include: list["MedHistory"] | None,
        mh_remove: list["MedHistory"] | None,
    ) -> None:
        """Method that first checks if there is a medhistory_qs attribute
        to the aid_obj, creates it if not, and adds the medhistorys to the medhistory_qs attribute.

        Args:
            aid_obj: MedAllergyAidHistoryModel object to add to the medhistory_qs attribute
            mh_include: MedHistory object to add to the queryset
            mh_remove: MedHistory object to remove from the queryset

        Returns: None"""
        if hasattr(aid_obj, "medhistorys_qs") is False:
            aid_obj.medhistorys_qs = []
        if mh_include:
            for mh in mh_include:
                if mh not in aid_obj.medhistorys_qs:
                    aid_obj.medhistorys_qs.append(mh)
        if mh_remove:
            for mh in mh_remove:
                if mh in aid_obj.medhistorys_qs:
                    aid_obj.medhistorys_qs.remove(mh)


class MedHistorysModelCreateView(MedHistoryModelBaseMixin, CreateView):
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
                setattr(form.instance, f"{onetoone.__class__.__name__.lower()}", onetoone)
        aid_obj = form.save()
        aid_obj_attr = aid_obj.__class__.__name__.lower()
        if self.medallergys:
            for medallergy in medallergys_to_save:
                setattr(medallergy, aid_obj_attr, aid_obj)
                medallergy.save()
        if self.medhistorys:
            if medhistorys_to_save:
                for medhistory in medhistorys_to_save:
                    setattr(medhistory, aid_obj_attr, aid_obj)
                    medhistory.save()
            for medhistorydetail in medhistorydetails_to_save:
                medhistorydetail.save()
        if self.labs:
            for lab in labs_to_save:
                setattr(lab, aid_obj_attr, aid_obj)
                lab.save()
        # Create and populate the medallergy_qs attribute on the object
        self.update_or_create_medallergy_qs(aid_obj=aid_obj, ma_include=medallergys_to_save, ma_remove=None)
        # Create and populate the medhistory_qs attribute on the object
        self.update_or_create_medhistory_qs(
            aid_obj=aid_obj,
            mh_include=medhistorys_to_save,
            mh_remove=None,
        )
        if self.labs:
            for lab in self.labs.keys():
                get_or_create_qs_attr(obj=aid_obj, name=lab)
            # Create and populate the labs_qs attribute on the object
            self.update_or_create_labs_qs(aid_obj=aid_obj, labs_include=labs_to_save, labs_remove=None)
        # Return object for the child view to use
        return aid_obj

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
            for lab, lab_tup in self.labs.items():
                if f"{lab}_formset" not in kwargs:
                    kwargs[f"{lab}_formset"] = lab_tup[0](  # pylint: disable=unsubscriptable-object
                        queryset=lab_tup[2], prefix=lab  # pylint: disable=unsubscriptable-object
                    )
                    kwargs[f"{lab}_formset_helper"] = lab_tup[1]  # pylint: disable=unsubscriptable-object
        return super().get_context_data(**kwargs)

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        if self.medallergys:
            kwargs["medallergys"] = self.medallergys
        return kwargs

    def post_populate_labformsets(
        self,
        request: "HttpRequest",
    ) -> dict[str, "BaseModelFormSet"] | None:
        """Method to populate a dicts of lab forms with POST data in the post() method."""
        if self.labs:
            lab_formsets = {}
            for lab, lab_tup in self.labs.items():
                lab_formsets.update({f"{lab}_formset": lab_tup[0](request.POST, queryset=lab_tup[2], prefix=lab)})
            return lab_formsets
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
            # If EmptyRelatedModel exception is raised by the related model's form save() method, pass
            except EmptyRelatedModel:
                pass
        return onetoones_to_save

    def post_process_lab_formsets(
        self,
        lab_formsets: dict[str, "BaseModelFormSet"],
    ) -> list["Lab"]:
        """Method that processes LabForms for the post() method."""
        # Create empty list of labs to add
        labs_to_save = []
        # Iterate over the lab_forms dict to create cleaned_data checks for each form
        if self.labs:
            for lab_formset in lab_formsets.values():
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
                        dateofbirth=onetoone_forms["dateofbirth_form"],
                        gender=onetoone_forms["gender_form"],
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
        lab_formsets = self.post_populate_labformsets(request=request)
        # Call is_valid() on all forms, using validate_form_list() for dicts of related model forms
        if (
            form.is_valid()
            and validate_form_list(form_list=list(onetoone_forms.values()))
            and validate_form_list(form_list=list(medallergys_forms.values()))
            and validate_form_list(form_list=list(medhistorys_forms.values()))
            and validate_form_list(form_list=list(medhistorydetails_forms.values()))
            and (validate_formset_list(formset_list=lab_formsets.values()) if lab_formsets else True)
        ):
            errors_bool = False
            form.save(commit=False)
            onetoones_to_save = self.post_process_onetoone_forms(
                onetoone_forms=onetoone_forms, model_obj=form.instance
            )
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
            labs_to_save = self.post_process_lab_formsets(lab_formsets=lab_formsets)
            errors = (
                self.render_errors(
                    form=form,
                    onetoone_forms=onetoone_forms,
                    medallergys_forms=medallergys_forms,
                    medhistorys_forms=medhistorys_forms,
                    medhistorydetails_forms=medhistorydetails_forms,
                    lab_formsets=lab_formsets,
                    labs=self.labs if hasattr(self, "labs") else None,
                )
                if errors_bool
                else None
            )
            return (
                errors,
                form,
                onetoone_forms,
                medallergys_forms,
                medhistorys_forms,
                medhistorydetails_forms,
                lab_formsets,
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
                lab_formsets=lab_formsets,
                labs=self.labs if hasattr(self, "labs") else None,
            )
            return (
                errors,
                form,
                onetoone_forms,
                medallergys_forms,
                medhistorys_forms,
                medhistorydetails_forms,
                lab_formsets if self.labs else None,
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
            self.update_or_create_medallergy_qs(aid_obj=self.object, ma_include=medallergys_to_save, ma_remove=None)
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
            self.update_or_create_medhistory_qs(aid_obj=self.object, mh_include=medhistorys_to_save, mh_remove=None)
        if self.labs:
            if labs_to_save:
                for lab in labs_to_save:
                    lab.user = self.object
                    lab.save()
            # Create and populate the labs_qs attribute on the object
            self.update_or_create_labs_qs(aid_obj=self.object, labs_include=labs_to_save, labs_remove=None)
        # Return object for the child view to use
        return self.object


class PatientAidBaseView(MedHistoryModelBaseMixin):
    """CreateView to create Aid objects with a user field and to populate
    pre-existing User related models into the forms and post data."""

    # List of required onetoone objects that won't be in the form
    # but will be loaded into the view context to interpret other info
    # i.e. age/gender to calculate eGFR for CKD
    req_onetoones: list[str] = []

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
    ) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Method to be called if all forms are valid."""
        # Save the OneToOne related models
        if self.onetoones:
            for onetoone in onetoones_to_save:
                onetoone_str = f"{onetoone.__class__.__name__.lower()}"
                if onetoone.user is None:
                    onetoone.user = self.user
                onetoone.save()
                if getattr(form.instance, onetoone_str, None) is None:
                    setattr(form.instance, onetoone_str, onetoone)
            for onetoone in onetoones_to_delete:
                onetoone.delete()
        if self.medallergys:
            if medallergys_to_save:
                # Modify and remove medallergys from the object
                for medallergy in medallergys_to_save:
                    if medallergy.user is None:
                        medallergy.user = self.user
                    medallergy.save()
            if medallergys_to_remove:
                for medallergy in medallergys_to_remove:
                    medallergy.delete()
        if self.medhistorys:
            # Modify and remove medhistorydetails from the object
            # Add and remove medhistorys from the object
            if medhistorys_to_save:
                for medhistory in medhistorys_to_save:
                    if medhistory.user is None:
                        medhistory.user = self.user
                    medhistory.save()
            if medhistorydetails_to_save:
                for medhistorydetail in medhistorydetails_to_save:
                    medhistorydetail.save()
            if medhistorys_to_remove:
                for medhistory in medhistorys_to_remove:
                    medhistory.delete()
            if medhistorydetails_to_remove:
                for medhistorydetail in medhistorydetails_to_remove:
                    medhistorydetail.instance.delete()
        if self.labs:
            if labs_to_save:
                # Modify and remove labs from the object
                for lab in labs_to_save:
                    if lab.user is None:
                        lab.user = self.user
                    lab.save()
            if labs_to_remove:
                for lab in labs_to_remove:
                    lab.delete()
        if form.instance.user is None:
            form.instance.user = self.user
        return form

    def get_user_queryset(self, username: str) -> "QuerySet":
        """Method to get the User queryset. Needs to be defined with a more
        narrow, specific QuerySet on each child model."""
        return pseudopatient_qs_plus(username=username)

    def check_user_onetoones(self, user: "User") -> None:
        """Method that checks the view's user for the required onetoone models
        and raises and redirects to the user's profile updateview if they are
        missing."""
        # Need to check the user's role to avoid redirecting a Provider or Admin to
        # a view that is meant for a Pseudopatient or Patient
        if user.role != Roles.PSEUDOPATIENT and user.role != Roles.PATIENT:
            pass
        else:
            for onetoone in self.req_onetoones:
                if not hasattr(user, onetoone):
                    raise AttributeError(
                        "Baseline information is needed to use GoutHelper Decision and Treatment Aids."
                    )

    def context_onetoones(
        self,
        onetoones: dict[str, "FormModelDict"],
        req_onetoones: list[str],
        kwargs: dict,
        user: "User",
    ) -> None:
        """Method to populate the onetoones dict with the user's related models."""
        # Primary QuerySet object is the intended Pseudopatient for the view, so
        # 1to1's are populated from that object
        for onetoone, onetoone_dict in onetoones.items():
            form_str = f"{onetoone}_form"
            if form_str not in kwargs:
                kwargs[form_str] = onetoone_dict["form"](instance=getattr(user, onetoone, None))
        for onetoone in req_onetoones:
            if onetoone not in kwargs:
                if onetoone == "dateofbirth":
                    kwargs["age"] = age_calc(getattr(user, onetoone).value)
                else:
                    kwargs[onetoone] = getattr(user, onetoone).value

    def context_medallergys(self, medallergys: list["MedAllergy"], kwargs: dict, user: "User") -> None:
        for treatment in medallergys:
            form_str = f"medallergy_{treatment}_form"
            if form_str not in kwargs:
                try:
                    user_i = [ma for ma in getattr(user, "medallergys_qs") if ma.treatment == treatment][0]
                except IndexError:
                    user_i = None
                kwargs[form_str] = MedAllergyTreatmentForm(
                    treatment=treatment, instance=user_i, initial={f"medallergy_{treatment}": True if user_i else None}
                )

    def context_medhistorys(
        self,
        medhistorys: dict[MedHistoryTypes, "FormModelDict"],
        medhistory_details: dict[MedHistoryTypes, "ModelForm"],
        kwargs: dict,
        user: "User",
        ckddetail: bool,
    ) -> None:
        """Method that iterates over the medhistorys dict and adds the forms to the context."""
        for medhistory, mh_dict in medhistorys.items():
            form_str = f"{medhistory}_form"
            if form_str not in kwargs:
                user_i = next(
                    iter([mh for mh in getattr(user, "medhistorys_qs") if mh.medhistorytype == medhistory]), None
                )
                if medhistory == MedHistoryTypes.CKD:
                    kwargs[form_str] = mh_dict["form"](
                        ckddetail=ckddetail, instance=user_i, initial={f"{medhistory}-value": True if user_i else None}
                    )
                    if ckddetail:
                        if "ckddetail_form" not in kwargs:
                            user_ckddetail_i = getattr(user_i, "ckddetail", None) if user_i else None
                            kwargs["ckddetail_form"] = medhistory_details[medhistory](instance=user_ckddetail_i)
                        if "baselinecreatinine_form" not in kwargs:
                            user_baselinecreatinine_i = getattr(user_i, "baselinecreatinine", None) if user_i else None
                            kwargs["baselinecreatinine_form"] = BaselineCreatinineForm(
                                instance=user_baselinecreatinine_i
                            )
                else:
                    kwargs[form_str] = self.medhistorys[medhistory]["form"](
                        instance=user_i,
                        initial={f"{medhistory}-value": True if user_i else None},
                    )

    def context_labs(
        self,
        labs: dict[str, tuple[type["BaseModelFormSet"], type["FormHelper"], "QuerySet"]],
        user: "User",
        kwargs: dict,
    ) -> None:
        """Method adds a formset of labs to the context. Uses a QuerySet that takes a user
        as an arg to populate existing Lab objects."""
        for lab, lab_tup in labs.items():
            if f"{lab}_formset" not in kwargs:
                kwargs[f"{lab}_formset"] = lab_tup[0](queryset=lab_tup[2](user=user), prefix=lab)
                kwargs[f"{lab}_formset_helper"] = lab_tup[1]
        # TODO: Rewrite BaseModelFormset to take a list of objects rather than a QuerySet

    def post(self, request, *args, **kwargs):
        """Processes forms for primary and related models"""
        # user and object attrs should be set by the dispatch() method on the
        # child view, but if not, set them here by calling get_object()
        if not hasattr(self, "user") or not hasattr(self, "object"):
            self.object = self.get_object()
        form_class = self.get_form_class()
        if self.medallergys:
            form = form_class(
                request.POST,
                medallergys=self.medallergys,
                instance=self.object() if isinstance(self.object, type) else self.object,
                patient=hasattr(self, "user"),
            )
        else:
            form = form_class(
                request.POST,
                instance=self.object() if isinstance(self.object, type) else self.object,
                patient=hasattr(self, "user"),
            )
        # Populate dicts for related models with POST data
        onetoone_forms = self.post_populate_onetoone_forms(onetoones=self.onetoones, request=request, user=self.user)
        medallergys_forms = self.post_populate_medallergys_forms(
            medallergys=self.medallergys, request=request, user=self.user
        )
        medhistorys_forms, medhistorydetails_forms = self.post_populate_medhistorys_details_forms(
            medhistorys=self.medhistorys,
            medhistory_details=self.medhistory_details,
            request=request,
            user=self.user,
            ckddetail=self.ckddetail,
        )
        lab_formsets = self.post_populate_labformsets(request=request, labs=self.labs)
        # Call is_valid() on all forms, using validate_form_list() for dicts of related model forms
        if (
            form.is_valid()
            and validate_form_list(form_list=onetoone_forms.values())
            and validate_form_list(form_list=medallergys_forms.values())
            and validate_form_list(form_list=medhistorys_forms.values())
            and validate_form_list(form_list=medhistorydetails_forms.values())
            and (validate_formset_list(formset_list=lab_formsets.values()) if lab_formsets else True)
        ):
            errors_bool = False
            form.save(commit=False)
            # Set related models for saving and set as attrs of the UpdateView model instance
            onetoones_to_save, onetoones_to_delete = self.post_process_onetoone_forms(
                onetoone_forms=onetoone_forms,
                req_onetoones=self.req_onetoones,
                user=self.user,
            )
            medallergys_to_save, medallergys_to_remove = self.post_process_medallergys_forms(
                medallergys_forms=medallergys_forms,
                user=self.user,
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
                user=self.user,
                ckddetail=self.ckddetail,
                errors_bool=errors_bool,
            )
            (
                labs_to_save,
                labs_to_remove,
            ) = self.post_process_lab_formsets(lab_formsets=lab_formsets, user=self.user)
            # If there are errors picked up after the initial validation step
            # render the errors as errors and include in the return tuple
            errors = (
                self.render_errors(
                    form=form,
                    onetoone_forms=onetoone_forms,
                    medallergys_forms=medallergys_forms,
                    medhistorys_forms=medhistorys_forms,
                    medhistorydetails_forms=medhistorydetails_forms,
                    lab_formsets=lab_formsets,
                    labs=self.labs if hasattr(self, "labs") else None,
                )
                if errors_bool
                else None
            )
            return (
                errors,
                form,
                onetoone_forms,
                medhistorys_forms,
                medhistorydetails_forms,
                medallergys_forms,
                lab_formsets,
                medallergys_to_save,
                medallergys_to_remove,
                onetoones_to_save,
                onetoones_to_delete,
                medhistorydetails_to_save,
                medhistorydetails_to_remove,
                medhistorys_to_save,
                medhistorys_to_remove,
                labs_to_save,
                labs_to_remove,
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
                lab_formsets=lab_formsets,
                labs=self.labs if hasattr(self, "labs") else None,
            )
            return (
                errors,
                form,
                onetoone_forms,
                medhistorys_forms,
                medhistorydetails_forms,
                medallergys_forms,
                lab_formsets if self.labs else None,
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

    def post_populate_labformsets(
        self,
        request: "HttpRequest",
        labs: dict[str, tuple[type["BaseModelFormSet"], type["FormHelper"], "QuerySet", str]] | None,
    ) -> dict[str, "BaseModelFormSet"] | None:
        """Method to populate a dict of lab forms with POST data in the post() method."""
        if labs:
            lab_formsets = {}
            for lab, lab_tup in labs.items():
                lab_formsets.update({lab: lab_tup[0](request.POST, queryset=lab_tup[2], prefix=lab)})
            return lab_formsets
        else:
            return None

    def post_populate_medallergys_forms(
        self,
        medallergys: None | type["FlarePpxChoices"] | type["UltChoices"] | type["Treatments"],
        request: "HttpRequest",
        user: "User",
    ) -> dict[str, "ModelForm"]:
        """Method to populate the forms for the MedAllergys for the post() method."""
        medallergys_forms: dict[str, "ModelForm"] = {}
        if medallergys:
            for treatment in medallergys:
                user_i = next(iter([ma for ma in getattr(user, "medallergys_qs") if ma.treatment == treatment]), None)
                medallergys_forms.update(
                    {
                        f"medallergy_{treatment}_form": MedAllergyTreatmentForm(
                            request.POST,
                            treatment=treatment,
                            instance=user_i,
                            initial={f"medallergy_{treatment}": True if user_i else None},
                        )
                    }
                )
        return medallergys_forms

    def post_populate_medhistorys_details_forms(
        self,
        medhistorys: dict[MedHistoryTypes, "FormModelDict"],
        medhistory_details: dict[MedHistoryTypes, "ModelForm"],
        request: "HttpRequest",
        user: "User",
        ckddetail: bool,
    ) -> tuple[dict[str, "ModelForm"], dict[str, "ModelForm"]]:
        """Method to populate the MedHistory and MedHistoryDetail forms for the post() method."""
        medhistorys_forms: dict[str, "ModelForm"] = {}
        medhistorydetails_forms: dict[str, "ModelForm"] = {}
        if medhistorys:
            for medhistory in medhistorys:
                user_i = next(
                    iter([mh for mh in getattr(user, "medhistorys_qs") if mh.medhistorytype == medhistory]), None
                )
                if medhistory == MedHistoryTypes.CKD:
                    medhistorys_forms.update(
                        {
                            f"{medhistory}_form": medhistorys[medhistory]["form"](
                                request.POST,
                                ckddetail=ckddetail,
                                instance=user_i,
                                initial={f"{medhistory}-value": True if user_i else None},
                            )
                        }
                    )
                    if ckddetail:
                        user_ckddetail_i = getattr(user_i, "ckddetail", None) if user_i else None
                        medhistorydetails_forms.update(
                            {"ckddetail_form": medhistory_details[medhistory](request.POST, instance=user_ckddetail_i)}
                        )
                        user_baselinecreatinine_i = getattr(user_i, "baselinecreatinine", None) if user_i else None
                        medhistorydetails_forms.update(
                            {
                                "baselinecreatinine_form": BaselineCreatinineForm(
                                    request.POST, instance=user_baselinecreatinine_i
                                )
                            }
                        )
                else:
                    medhistorys_forms.update(
                        {
                            f"{medhistory}_form": medhistorys[medhistory]["form"](
                                request.POST,
                                instance=user_i,
                                initial={f"{medhistory}-value": True if user_i else None},
                            )
                        }
                    )
        return medhistorys_forms, medhistorydetails_forms

    def post_populate_onetoone_forms(
        self,
        onetoones: dict[str, "FormModelDict"],
        request: "HttpRequest",
        user: "User",
    ) -> dict[str, "ModelForm"]:
        """Method that populates a dict of OneToOne related model forms with POST data
        in the post() method."""
        onetoone_forms: dict[str, "ModelForm"] = {}
        if onetoones:
            for onetoone in onetoones:
                user_i = getattr(user, onetoone, None)
                onetoone_forms.update(
                    {
                        f"{onetoone}_form": onetoones[onetoone]["form"](
                            request.POST,
                            instance=user_i,
                        )
                    }
                )
        return onetoone_forms

    def post_process_lab_formsets(
        self,
        lab_formsets: dict[str, "BaseModelFormSet"],
        user: "User",
    ) -> tuple[list["Lab"], list["Lab"]]:
        """Method to process the forms in a Lab formset for the post() method.
        Requires a list of existing labs (can be empty) to iterate over and compare to the forms in the
        formset to identify labs that need to be removed.

        Args:
            lab_formset (BaseModelFormSet): A formset of LabForms
            user (User): The user to assign to the labs

        Returns:
            tuple[list[Lab], list[Lab]]: A tuple of lists of labs to save and remove"""
        # Assign lists to return
        labs_to_save: list["Lab"] = []
        labs_to_remove: list["Lab"] = []

        if lab_formsets:
            for lab_name, lab_formset in lab_formsets.items():
                qs_name = f"{lab_name}_qs"
                if not hasattr(user, qs_name):
                    setattr(user, qs_name, [])
                # Iterate over the object's existing labs
                qs_attr = getattr(user, qs_name)
                for lab in qs_attr:
                    cleaned_data = lab_formset.cleaned_data
                    # Check if the lab is not in the formset's cleaned_data list by id key
                    for lab_form in cleaned_data:
                        try:
                            if lab_form["id"] == lab:
                                # Check if the form is not marked for deletion
                                if not lab_form["DELETE"]:
                                    # If the lab is in the formset and not marked for deletion,
                                    # append it to the form instance's labs_qs if it's not already there
                                    if lab not in qs_attr:
                                        qs_attr.append(lab)
                                    # If so, break out of the loop
                                    break
                                # If it is marked for deletion, it will be removed by the formset loop below
                        except KeyError:
                            pass
                    else:
                        # If not, add the lab to the labs_to_remove list
                        labs_to_remove.append(lab)
                        qs_attr.remove(lab)
                # Iterate over the forms in the formset
                for form in lab_formset:
                    # Check if the form has a value in the "value" field
                    if "value" in form.cleaned_data:
                        # Check if the form has an instance and the form has changed
                        if form.instance and form.has_changed() and not form.cleaned_data["DELETE"]:
                            # Add the form's instance to the labs_to_save list
                            labs_to_save.append(form.instance)
                        # If there's a value but no instance, add the form's instance to the labs_to_save list
                        elif form.instance is None:
                            labs_to_save.append(form.instance)
                        # Add the lab to the form instance's labs_qs if it's not already there
                        if form.instance not in qs_attr:
                            qs_attr.append(form.instance)
        return labs_to_save, labs_to_remove

    def post_process_medallergys_forms(
        self,
        medallergys_forms: dict[str, "ModelForm"],
        user: "User",
    ) -> tuple[list["MedAllergy"], list["MedAllergy"]]:
        medallergys_to_save: list["MedAllergy"] = []
        medallergys_to_remove: list["MedAllergy"] = []
        if not hasattr(user, "medallergys_qs"):
            user.medallergys_qs = []
        for medallergy_form_str in medallergys_forms:
            treatment = medallergy_form_str.split("_")[1]
            if f"medallergy_{treatment}" in medallergys_forms[medallergy_form_str].cleaned_data:
                try:
                    user_i = [ma for ma in getattr(user, "medallergys_qs") if ma.treatment == treatment][0]
                except IndexError:
                    user_i = None
                if user_i and not medallergys_forms[medallergy_form_str].cleaned_data[f"medallergy_{treatment}"]:
                    medallergys_to_remove.append(user_i)
                    user.medallergys_qs.remove(user_i)
                else:
                    if medallergys_forms[medallergy_form_str].cleaned_data[f"medallergy_{treatment}"]:
                        # If there is already an instance, it will not have changed so it doesn't need to be changed
                        if not user_i:
                            medallergy = medallergys_forms[medallergy_form_str].save(commit=False)
                            # Assign MedAllergy object treatment attr from the cleaned_data["treatment"]
                            medallergy.treatment = medallergys_forms[medallergy_form_str].cleaned_data["treatment"]
                            medallergys_to_save.append(medallergy)
                            # Add the medallergy to the form instance's medallergys_qs if it's not already there
                            if medallergy not in user.medallergys_qs:
                                user.medallergys_qs.append(medallergy)
                        else:
                            # Add the medallergy to the form instance's medallergys_qs if it's not already there
                            if user_i not in user.medallergys_qs:
                                user.medallergys_qs.append(user_i)
        return medallergys_to_save, medallergys_to_remove

    def post_process_medhistorys_details_forms(
        self,
        medhistorys_forms: dict[str, "ModelForm"],
        medhistorydetails_forms: dict[str, "ModelForm"],
        user: "User",
        ckddetail: bool,
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
        medhistorydetails_to_save: list["CkdDetailForm" | BaselineCreatinine] = []
        medhistorydetails_to_remove: list[CkdDetail | BaselineCreatinine | None] = []
        # Create medhistory_qs attribute on the form instance if it doesn't exist
        if not hasattr(user, "medhistorys_qs"):
            user.medhistorys_qs = []
        for medhistory_form_str in medhistorys_forms:
            medhistorytype = medhistory_form_str.split("_")[0]
            user_i = next(
                iter([mh for mh in getattr(user, "medhistorys_qs") if mh.medhistorytype == medhistorytype]), None
            )
            # If there is a MedHistory instance already, check if it's been deleted, i.e. is not in the
            # form cleaned data, and also check if it has a MedHistoryDetail that may or may not have changed
            if user_i:
                if not medhistorys_forms[medhistory_form_str].cleaned_data[f"{medhistorytype}-value"]:
                    # Mark it for deletion if so
                    medhistorys_to_remove.append(medhistorys_forms[medhistory_form_str].instance)
                    user.medhistorys_qs.remove(user_i)
                else:
                    # If it's not marked for deletion, it should be added to the form instance's medhistory_qs
                    if user_i not in user.medhistorys_qs:
                        user.medhistorys_qs.append(user_i)
                    # Check if the MedHistory is CKD or Gout and process related models/forms
                    if medhistorytype == MedHistoryTypes.CKD and ckddetail:
                        (
                            medhistorydetails_forms["ckddetail_form"],
                            medhistorydetails_forms["baselinecreatinine_form"],
                            ckddetail_errors,
                        ) = CkdDetailFormProcessor(
                            ckd=user_i,
                            ckddetail_form=medhistorydetails_forms["ckddetail_form"],  # type: ignore
                            baselinecreatinine_form=medhistorydetails_forms["baselinecreatinine_form"],  # type: ignore
                            dateofbirth=self.user.dateofbirth,  # type: ignore
                            gender=self.user.gender,  # type: ignore
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
            # Otherwise add medhistorys that are checked in the form data
            else:
                if medhistorys_forms[medhistory_form_str].cleaned_data[f"{medhistorytype}-value"]:
                    medhistory = medhistorys_forms[medhistory_form_str].save(commit=False)
                    medhistorys_to_save.append(medhistory)
                    # Add the medhistory to the form instance's medhistorys_qs if it's not already there
                    if medhistory not in user.medhistorys_qs:
                        user.medhistorys_qs.append(medhistory)
                    if medhistorytype == MedHistoryTypes.CKD and ckddetail:
                        ckddetail_obj, baselinecreatinine, ckddetail_errors = CkdDetailFormProcessor(
                            ckd=medhistory,
                            ckddetail_form=medhistorydetails_forms["ckddetail_form"],  # type: ignore
                            baselinecreatinine_form=medhistorydetails_forms["baselinecreatinine_form"],  # type: ignore
                            dateofbirth=self.user.dateofbirth,
                            gender=self.user.gender,
                        ).process()
                        # Need mark baselinecreatinine and ckddetail for saving because their
                        # related Ckd object will not have been saved yet
                        if baselinecreatinine and baselinecreatinine.instance:
                            # Check if the baselinecreatinine has a to_delete attr, and mark for deletion if so
                            if hasattr(baselinecreatinine.instance, "to_delete"):
                                medhistorydetails_to_remove.append(baselinecreatinine)
                            elif hasattr(baselinecreatinine.instance, "to_save"):
                                medhistorydetails_to_save.append(baselinecreatinine)
                        if ckddetail_obj:
                            if ckddetail_obj.instance and hasattr(ckddetail_obj.instance, "to_delete"):
                                medhistorydetails_to_remove.append(ckddetail_obj)
                            elif ckddetail_obj.instance and hasattr(ckddetail_obj.instance, "to_save"):
                                medhistorydetails_to_save.append(ckddetail_obj)
                        if ckddetail_errors and errors_bool is not True:
                            errors_bool = True
        return (
            medhistorys_to_save,
            medhistorys_to_remove,
            medhistorydetails_to_save,
            medhistorydetails_to_remove,
            errors_bool,
        )

    def post_process_onetoone_forms(
        self,
        onetoone_forms: dict[str, "ModelForm"],
        req_onetoones: list[str],
        user: "User",
    ) -> tuple[list["Model"], list["Model"]]:
        """Method to process the forms for the OneToOne objects for
        the post() method."""

        onetoones_to_save: list["Model"] = []
        onetoones_to_delete: list["Model"] = []
        # Set related models for saving and set as attrs of the UpdateView model instance
        for onetoone_form_str, onetoone_form in onetoone_forms.items():
            object_attr = onetoone_form_str.split("_")[0]
            if object_attr not in req_onetoones:
                try:
                    onetoone_form.check_for_value()
                    # Check if the onetoone changed
                    if onetoone_form.has_changed():
                        onetoone = onetoone_form.save(commit=False)
                        onetoones_to_save.append(onetoone)
                    else:
                        onetoone = onetoone_form.instance
                    setattr(user, object_attr, onetoone)
                # If EmptyRelatedModel exception is raised by the related model's form save() method,
                # Check if the related model exists and delete it if it does
                except EmptyRelatedModel:
                    # Check if the related model has already been saved to the DB and mark for deletion if so
                    if onetoone_form.instance and not onetoone_form.instance._state.adding:
                        to_delete = onetoone_form.instance
                        # Iterate over the forms required_fields property and set the related model's
                        # fields to their initial values to prevent IntegrityError from Django-Simple-History
                        # historical model on delete().
                        if hasattr(onetoone_form, "required_fields"):
                            for field in onetoone_form.required_fields:
                                setattr(to_delete, field, onetoone_form.initial[field])
                        # Set the object attr to None so it is reflected in the QuerySet fed to update in form_valid()
                        if object_attr != "urate":
                            setattr(user, object_attr, None)
                        onetoones_to_delete.append(to_delete)
        return onetoones_to_save, onetoones_to_delete


class PatientAidCreateView(PatientAidBaseView, CreateView):
    """CreateView to create Aid objects with a user field and to populate
    pre-existing User related models into the forms and post data."""

    class Meta:
        abstract = True

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        if self.onetoones or self.req_onetoones:
            self.context_onetoones(
                onetoones=self.onetoones, req_onetoones=self.req_onetoones, kwargs=kwargs, user=self.user
            )
        if self.medallergys:
            self.context_medallergys(medallergys=self.medallergys, kwargs=kwargs, user=self.user)
        if self.medhistorys:
            self.context_medhistorys(
                medhistorys=self.medhistorys,
                medhistory_details=self.medhistory_details,
                kwargs=kwargs,
                user=self.user,
                ckddetail=self.ckddetail,
            )
        if self.labs:
            self.context_labs(
                labs=self.labs,
                user=self.user,
                kwargs=kwargs,
            )
        if "patient" not in kwargs:
            kwargs["patient"] = self.user
        return super().get_context_data(**kwargs)

    def get_form_kwargs(self) -> dict[str, Any]:
        """Method to add the user to the form kwargs."""
        kwargs = super().get_form_kwargs()
        if self.medallergys:
            kwargs["medallergys"] = self.medallergys
        if hasattr(self, "user"):
            kwargs["patient"] = True
        return kwargs

    def get_object(self, *args, **kwargs) -> "MedAllergyAidHistoryModel":
        self.user = self.get_user_queryset(self.kwargs["username"]).get()
        return self.model


class PatientAidUpdateView(PatientAidBaseView, UpdateView):
    class Meta:
        abstract = True

    def context_medhistorys(
        self,
        medhistorys: dict[MedHistoryTypes, "FormModelDict"],
        medhistory_details: dict[MedHistoryTypes, "ModelForm"],
        kwargs: dict,
        user: "User",
        ckddetail: bool,
    ) -> None:
        """Method that iterates over the medhistorys dict and adds the forms to the context."""
        for medhistory, mh_dict in medhistorys.items():
            form_str = f"{medhistory}_form"
            if form_str not in kwargs:
                try:
                    user_i = [mh for mh in getattr(user, "medhistorys_qs") if mh.medhistorytype == medhistory][0]
                except IndexError:
                    user_i = None
                if medhistory == MedHistoryTypes.CKD:
                    kwargs[form_str] = mh_dict["form"](
                        ckddetail=ckddetail,
                        instance=user_i,
                        initial={f"{medhistory}-value": True if user_i else False},
                    )
                    if ckddetail:
                        if "ckddetail_form" not in kwargs:
                            user_ckddetail_i = getattr(user_i, "ckddetail", None) if user_i else None
                            kwargs["ckddetail_form"] = medhistory_details[medhistory](instance=user_ckddetail_i)
                        if "baselinecreatinine_form" not in kwargs:
                            user_baselinecreatinine_i = getattr(user_i, "baselinecreatinine", None) if user_i else None
                            kwargs["baselinecreatinine_form"] = BaselineCreatinineForm(
                                instance=user_baselinecreatinine_i
                            )
                else:
                    kwargs[form_str] = self.medhistorys[medhistory]["form"](
                        instance=user_i,
                        initial={f"{medhistory}-value": True if user_i else False},
                    )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        if self.onetoones or self.req_onetoones:
            self.context_onetoones(
                onetoones=self.onetoones, req_onetoones=self.req_onetoones, kwargs=kwargs, user=self.user
            )
        if self.medallergys:
            self.context_medallergys(medallergys=self.medallergys, kwargs=kwargs, user=self.user)
        if self.medhistorys:
            self.context_medhistorys(
                medhistorys=self.medhistorys,
                medhistory_details=self.medhistory_details,
                kwargs=kwargs,
                user=self.user,
                ckddetail=self.ckddetail,
            )
        if self.labs:
            self.context_labs(
                labs=self.labs,
                user=self.user,
                kwargs=kwargs,
            )
        if "patient" not in kwargs:
            kwargs["patient"] = self.user
        return super().get_context_data(**kwargs)

    def get_form_kwargs(self) -> dict[str, Any]:
        """Method to add the user to the form kwargs."""
        kwargs = super().get_form_kwargs()
        if self.medallergys:
            kwargs["medallergys"] = self.medallergys
        if hasattr(self, "user"):
            kwargs["patient"] = True
        return kwargs

    def get_object(self, *args, **kwargs) -> "MedAllergyAidHistoryModel":
        # QuerySet fetches the user from the username kwarg
        # Returns the User's FlareAid object
        self.user = self.get_user_queryset(self.kwargs["username"]).get()
        try:
            return getattr(self.user, self.model.__name__.lower())
        except self.model.DoesNotExist as exc:
            raise self.model.DoesNotExist(f"No {self.model.__name__} matching the query") from exc


class MedHistorysModelUpdateView(MedHistoryModelBaseMixin, UpdateView):
    class Meta:
        abstract = True

    def dispatch(self, request, *args, **kwargs):
        """Overwritten to check if the object has a User and redirect to the
        correct UpdateView if so."""
        self.object = self.get_object()
        if getattr(self.object, "user", None):
            kwargs = {"username": self.object.user.username}
            if isinstance(self.object, Flare):
                kwargs.update({"pk": self.object.pk})
            return HttpResponseRedirect(
                reverse(
                    f"{self.model.__name__.lower()}s:pseudopatient-update",
                    kwargs=kwargs,
                )
            )
        return super().dispatch(request, *args, **kwargs)

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
    ) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Method to be called if all forms are valid."""
        aid_obj = form.save()
        aid_obj_attr = aid_obj.__class__.__name__.lower()
        # Save the OneToOne related models
        if self.onetoones:
            for onetoone in onetoones_to_save:
                if not getattr(aid_obj, onetoone.__class__.__name__.lower()):
                    setattr(aid_obj, onetoone.__class__.__name__.lower(), onetoone)
                    onetoone.save()
                onetoone.save()
            for onetoone in onetoones_to_delete:
                onetoone.delete()
        if self.medallergys:
            if medallergys_to_save:
                # Modify and remove medallergys from the object
                for medallergy in medallergys_to_save:
                    if not getattr(medallergy, aid_obj_attr):
                        setattr(medallergy, aid_obj_attr, aid_obj)
                    medallergy.save()
            if medallergys_to_remove:
                for medallergy in medallergys_to_remove:
                    medallergy.delete()
        if self.medhistorys:
            # Modify and remove medhistorydetails from the object
            # Add and remove medhistorys from the object
            if medhistorys_to_save:
                for medhistory in medhistorys_to_save:
                    if not getattr(medhistory, aid_obj_attr):
                        setattr(medhistory, aid_obj_attr, aid_obj)
                    medhistory.save()
            if medhistorydetails_to_save:
                for medhistorydetail in medhistorydetails_to_save:
                    medhistorydetail.save()
            if medhistorys_to_remove:
                for medhistory in medhistorys_to_remove:
                    medhistory.delete()
            if medhistorydetails_to_remove:
                for medhistorydetail in medhistorydetails_to_remove:
                    medhistorydetail.instance.delete()
        if self.labs:
            # Modify and remove labs from the object
            for lab in labs_to_save:
                if not getattr(lab, aid_obj_attr):
                    setattr(lab, aid_obj_attr, aid_obj)
                    set_to_save(lab)
                if hasattr(lab, "to_save"):
                    lab.save()
            for lab in labs_to_remove:
                lab.delete()
        # Create and populate the medallergy_qs attribute on the object
        self.update_or_create_medallergy_qs(
            aid_obj=aid_obj, ma_include=medallergys_to_save, ma_remove=medallergys_to_remove
        )
        # Create and populate the medhistory_qs attribute on the object
        self.update_or_create_medhistory_qs(
            aid_obj=aid_obj, mh_include=medhistorys_to_save, mh_remove=medhistorys_to_remove
        )
        # Create and populate the labs_qs attribute on the object
        self.update_or_create_labs_qs(aid_obj=aid_obj, labs_include=labs_to_save, labs_remove=labs_to_remove)
        return aid_obj

    def context_onetoones(
        self, onetoones: dict[str, "FormModelDict"], kwargs: dict, con_obj: "MedAllergyAidHistoryModel"
    ) -> None:
        """Method that iterates over the onetoones dict and adds the forms to the context."""
        for onetoone in onetoones:
            form_str = f"{onetoone}_form"
            if onetoone == "dateofbirth" and form_str not in kwargs:
                kwargs[form_str] = onetoones[onetoone]["form"](
                    instance=getattr(con_obj, onetoone),
                    initial={"value": age_calc(con_obj.dateofbirth.value) if con_obj.dateofbirth else None},
                )
            if form_str not in kwargs:
                kwargs[form_str] = onetoones[onetoone]["form"](instance=getattr(con_obj, onetoone))

    def context_medallergys(
        self, medallergys: list["MedAllergy"], kwargs: dict, con_obj: "MedAllergyAidHistoryModel"
    ) -> None:
        """Method that iterates over the medallergys list and adds the forms to the context."""
        for treatment in medallergys:
            form_str = f"medallergy_{treatment}_form"
            if form_str not in kwargs:
                qs_ma = next(iter([ma for ma in con_obj.medallergys_qs if ma.treatment == treatment]), None)
                kwargs[form_str] = MedAllergyTreatmentForm(
                    treatment=treatment, instance=qs_ma, initial={f"medallergy_{treatment}": True if qs_ma else None}
                )

    def context_medhistorys(
        self, medhistorys: dict[MedHistoryTypes, "FormModelDict"], kwargs: dict, con_obj: "MedAllergyAidHistoryModel"
    ) -> None:
        """Method that iterates over the medhistorys dict and adds the forms to the context."""
        for medhistory in medhistorys:
            form_str = f"{medhistory}_form"
            if form_str not in kwargs:
                qs_mh = next(iter([mh for mh in con_obj.medhistorys_qs if mh.medhistorytype == medhistory]), None)
                if medhistory == MedHistoryTypes.CKD:
                    kwargs[form_str] = medhistorys[medhistory]["form"](
                        instance=qs_mh,
                        initial={f"{medhistory}-value": True if qs_mh else False},
                        ckddetail=self.ckddetail,
                    )
                    if self.ckddetail:
                        if hasattr(qs_mh, "ckddetail") and qs_mh.ckddetail:
                            kwargs["ckddetail_form"] = self.medhistory_details[medhistory](instance=qs_mh.ckddetail)
                            if hasattr(qs_mh, "baselinecreatinine") and qs_mh.baselinecreatinine:
                                kwargs["baselinecreatinine_form"] = BaselineCreatinineForm(
                                    instance=qs_mh.baselinecreatinine
                                )
                        else:
                            kwargs["ckddetail_form"] = self.medhistory_details[medhistory]()
                        if "baselinecreatinine_form" not in kwargs:
                            kwargs["baselinecreatinine_form"] = BaselineCreatinineForm()
                elif medhistory == MedHistoryTypes.GOUT:
                    kwargs[form_str] = medhistorys[medhistory]["form"](
                        instance=qs_mh,
                        initial={f"{medhistory}-value": True if qs_mh else False},
                        goutdetail=self.goutdetail,
                    )
                    if self.goutdetail:
                        if hasattr(qs_mh, "goutdetail") and qs_mh.goutdetail:
                            kwargs["goutdetail_form"] = self.medhistory_details[medhistory](instance=qs_mh.goutdetail)
                        elif "goutdetail_form" not in kwargs:
                            kwargs["goutdetail_form"] = self.medhistory_details[medhistory]()
                else:
                    kwargs[form_str] = self.medhistorys[medhistory]["form"](
                        instance=qs_mh, initial={f"{medhistory}-value": True if qs_mh else False}
                    )

    def context_labs(
        self,
        labs: dict[str, tuple[type["BaseModelFormSet"], type["FormHelper"], "QuerySet", str]] | None,
        con_obj: "MedAllergyAidHistoryModel",
        kwargs: dict,
    ) -> None:
        """Method that iterates over the labs list and adds the forms to the context."""
        if labs:
            for lab, lab_tup in labs.items():
                formset_name = f"{lab}_formset"
                if formset_name not in kwargs:
                    kwargs[formset_name] = lab_tup[0](queryset=lab_tup[2].filter(ppx=con_obj), prefix=lab)
                    kwargs[f"{lab}_formset_helper"] = lab_tup[1]

    def get(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> "HttpResponse":
        """Overwritten to not fetch the object a second time."""
        return self.render_to_response(self.get_context_data(**kwargs))

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        if self.onetoones:
            self.context_onetoones(onetoones=self.onetoones, kwargs=kwargs, con_obj=self.object)
        if self.medallergys:
            self.context_medallergys(medallergys=self.medallergys, kwargs=kwargs, con_obj=self.object)
        if self.medhistorys:
            self.context_medhistorys(medhistorys=self.medhistorys, kwargs=kwargs, con_obj=self.object)
        if self.labs:
            self.context_labs(labs=self.labs, con_obj=self.object, kwargs=kwargs)
        return super().get_context_data(**kwargs)

    def get_form_kwargs(self) -> dict[str, Any]:
        """Method to add the user to the form kwargs."""
        kwargs = super().get_form_kwargs()
        if self.medallergys:
            kwargs["medallergys"] = self.medallergys
        return kwargs

    def post_populate_labformsets(
        self,
        request: "HttpRequest",
    ) -> dict[str, "BaseModelFormSet"] | None:
        """Method to populate a dict of lab forms with POST data
        in the post() method."""
        if self.labs:
            formsets = {}
            for lab, lab_tup in self.labs.items():
                formsets.update(
                    {
                        f"{lab}_formset": lab_tup[0](
                            request.POST, queryset=lab_tup[2].filter(ppx=self.object), prefix=lab
                        )
                    }
                )
            return formsets
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
                qs_ma = next(iter([ma for ma in post_object.medallergys_qs if ma.treatment == treatment]), None)
                if qs_ma:
                    if not medallergys_forms[medallergy_form_str].cleaned_data[f"medallergy_{treatment}"]:
                        medallergys_to_remove.append(qs_ma)
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
                qs_mh = next(
                    iter([mh for mh in post_object.medhistorys_qs if mh.medhistorytype == medhistorytype]), None
                )
                if qs_mh:
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
                            ckd=qs_mh,
                            ckddetail_form=medhistorydetails_forms["ckddetail_form"],  # type: ignore
                            baselinecreatinine_form=medhistorydetails_forms["baselinecreatinine_form"],  # type: ignore
                            dateofbirth=onetoone_forms["dateofbirth_form"],  # type: ignore
                            gender=onetoone_forms["gender_form"],  # type: ignore
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
                                goutdetail_form.instance.medhistory = qs_mh
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
                                dateofbirth=onetoone_forms["dateofbirth_form"],  # type: ignore
                                gender=onetoone_forms["gender_form"],  # type: ignore
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

    def post_process_onetoone_forms(
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
                if onetoone_form.has_changed():
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

    def post_process_lab_formsets(
        self,
        lab_formsets: dict[str, "BaseModelFormSet"],
    ) -> tuple[list["Lab"], list["Lab"]]:
        """Method to process the forms in a Lab formset for the MedHistorysModelUpdateView post() method.
        Requires a list of existing labs (can be empty) to iterate over and compare to the forms in the
        formset to identify labs that need to be removed."""
        # Assign lists to return
        labs_to_save: list["Lab"] = []
        labs_to_remove: list["Lab"] = []
        if lab_formsets:
            for lab_formset in lab_formsets.values():
                for form in lab_formset:
                    if form.cleaned_data.get("DELETE", None):
                        labs_to_remove.append(form.instance)
                        set_to_delete(form.instance)
                    else:
                        if "value" in form.cleaned_data:
                            labs_to_save.append(form.instance)
                            if form.instance and form.has_changed():
                                set_to_save(form.instance)
                            elif form.instance is None:
                                set_to_save(form.instance)

        return labs_to_save, labs_to_remove

    def post(self, request, *args, **kwargs):
        """Processes forms for primary and related models"""

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
        lab_formsets = self.post_populate_labformsets(request=request)
        # Call is_valid() on all forms, using validate_form_list() for dicts of related model forms
        if (
            form.is_valid()
            and validate_form_list(form_list=onetoone_forms.values())
            and validate_form_list(form_list=medallergys_forms.values())
            and validate_form_list(form_list=medhistorys_forms.values())
            and validate_form_list(form_list=medhistorydetails_forms.values())
            and (validate_formset_list(formset_list=lab_formsets.values()) if lab_formsets else True)
        ):
            errors_bool = False
            form.save(commit=False)
            # Set related models for saving and set as attrs of the UpdateView model instance
            onetoones_to_save, onetoones_to_delete = self.post_process_onetoone_forms(
                onetoone_forms=onetoone_forms, model_obj=form.instance
            )
            medallergys_to_save, medallergys_to_remove = self.post_process_medallergys_forms(
                medallergys_forms=medallergys_forms, post_object=form.instance
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
                post_object=form.instance,
                onetoone_forms=onetoone_forms,
                errors_bool=errors_bool,
            )
            (
                labs_to_save,
                labs_to_remove,
            ) = self.post_process_lab_formsets(lab_formsets=lab_formsets)
            # If there are errors picked up after the initial validation step
            # render the errors as errors and include in the return tuple
            errors = (
                self.render_errors(
                    form=form,
                    onetoone_forms=onetoone_forms,
                    medallergys_forms=medallergys_forms,
                    medhistorys_forms=medhistorys_forms,
                    medhistorydetails_forms=medhistorydetails_forms,
                    lab_formsets=lab_formsets,
                    labs=self.labs if hasattr(self, "labs") else None,
                )
                if errors_bool
                else None
            )
            return (
                errors,
                form,
                onetoone_forms,
                medallergys_forms,
                medhistorys_forms,
                medhistorydetails_forms,
                lab_formsets,
                onetoones_to_save,
                onetoones_to_delete,
                medallergys_to_save,
                medallergys_to_remove,
                medhistorys_to_save,
                medhistorys_to_remove,
                medhistorydetails_to_save,
                medhistorydetails_to_remove,
                labs_to_save,
                labs_to_remove,
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
                lab_formsets=lab_formsets,
                labs=self.labs if hasattr(self, "labs") else None,
            )
            return (
                errors,
                form,
                onetoone_forms,
                medallergys_forms,
                medhistorys_forms,
                medhistorydetails_forms,
                lab_formsets if self.labs else None,
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


class PatientModelUpdateView(MedHistorysModelUpdateView):
    """Overwritten to change the view logic to update a Pseudopatient and its
    related models."""

    class Meta:
        abstract = True

    def context_onetoones(
        self, onetoones: dict[str, "FormModelDict"], kwargs: dict, con_obj: "MedAllergyAidHistoryModel"
    ) -> None:
        """Overwritten because User's don't have a field for each of their onetoones, it is
        a reverse relationship, so hasattr() needs to be called before getattr()."""
        for onetoone in onetoones:
            form_str = f"{onetoone}_form"
            if onetoone == "dateofbirth" and form_str not in kwargs:
                kwargs[form_str] = onetoones[onetoone]["form"](
                    instance=getattr(con_obj, onetoone) if hasattr(con_obj, onetoone) else None,
                    initial={
                        "value": age_calc(con_obj.dateofbirth.value) if hasattr(con_obj, "dateofbirth") else None
                    },
                )
            if form_str not in kwargs:
                kwargs[form_str] = onetoones[onetoone]["form"](
                    instance=getattr(con_obj, onetoone, None) if hasattr(con_obj, onetoone) else None
                )

    def form_valid(
        self,
        form,
        onetoones_to_save: list["Model"] | None,
        onetoones_to_delete: list["Model"] | None,
        medhistorydetails_to_save: list["CkdDetailForm", BaselineCreatinine, "GoutDetailForm"] | None,
        medhistorydetails_to_remove: list[CkdDetail, BaselineCreatinine, None] | None,
        medallergys_to_save: list["MedAllergy"] | None,
        medallergys_to_remove: list["MedAllergy"] | None,
        medhistorys_to_save: list["MedHistory"] | None,
        medhistorys_to_remove: list["MedHistory"] | None,
        labs_to_save: list["Lab"] | None,
        labs_to_remove: list["Lab"] | None,
        **kwargs: Any,
    ) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Method to be called if all forms are valid."""
        # DO NOT SAVE THE FORM--USER MODELS ARE NOT MEANT TO BE EDITED IN GOUTHELPER
        if self.onetoones:
            if onetoones_to_save:
                for onetoone in onetoones_to_save:
                    if onetoone.user is None:
                        onetoone.user = self.object
                    onetoone.save()
            if onetoones_to_delete:
                for onetoone in onetoones_to_delete:
                    onetoone.delete()
        if self.medallergys:
            if medallergys_to_save:
                for medallergy in medallergys_to_save:
                    if medallergy.user is None:
                        medallergy.user = self.object
                    medallergy.save()
            if medallergys_to_remove:
                for medallergy in medallergys_to_remove:
                    medallergy.delete()
            self.update_or_create_medallergy_qs(
                aid_obj=self.object, ma_include=medallergys_to_save, ma_remove=medallergys_to_remove
            )
        if self.medhistorys:
            if medhistorys_to_save:
                for medhistory in medhistorys_to_save:
                    if medhistory.user is None:
                        medhistory.user = self.object
                    medhistory.save()
            if medhistorys_to_remove:
                for medhistory in medhistorys_to_remove:
                    medhistory.delete()
            if medhistorydetails_to_save:
                for medhistorydetail in medhistorydetails_to_save:
                    medhistorydetail.save()
            if medhistorydetails_to_remove:
                for medhistorydetail in medhistorydetails_to_remove:
                    medhistorydetail.delete()
            # Create and populate the medhistory_qs attribute on the object
            self.update_or_create_medhistory_qs(
                aid_obj=self.object, mh_include=medhistorys_to_save, mh_remove=medhistorys_to_remove
            )
        if self.labs:
            if labs_to_save:
                for lab in labs_to_save:
                    if lab.user is None:
                        lab.user = self.object
                    lab.save()
            if labs_to_remove:
                for lab in labs_to_remove:
                    lab.delete()
            # Create and populate the labs_qs attribute on the object
            self.update_or_create_labs_qs(aid_obj=self.object, labs_include=labs_to_save, labs_remove=labs_to_remove)
        # Return object for the child view to use
        return self.object

    def get_form_kwargs(self) -> dict[str, Any]:
        """Method to add the user to the form kwargs."""
        kwargs = super().get_form_kwargs()
        if self.medallergys:
            kwargs["medallergys"] = self.medallergys
        if hasattr(self, "user"):
            kwargs["patient"] = True
        return kwargs
