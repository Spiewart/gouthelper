import uuid
from typing import TYPE_CHECKING, Any, Union

from django.contrib import messages  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from django.core.exceptions import ValidationError  # type: ignore
from django.db.models import Model  # type: ignore
from django.forms import ModelForm  # type: ignore
from django.http import HttpResponseRedirect  # type: ignore
from django.urls import reverse
from django.utils.functional import cached_property  # type: ignore
from django.views.generic import CreateView  # type: ignore

from ..dateofbirths.helpers import age_calc
from ..genders.choices import Genders
from ..labs.forms import BaselineCreatinineForm
from ..labs.models import BaselineCreatinine
from ..medallergys.forms import MedAllergyTreatmentForm
from ..medallergys.models import MedAllergy
from ..medhistorydetails.models import CkdDetail, GoutDetail
from ..medhistorydetails.services import CkdDetailFormProcessor
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.dicts import MedHistoryTypesAids
from ..medhistorys.helpers import medhistorys_get
from ..medhistorys.models import Gout
from ..profiles.models import PseudopatientProfile
from ..users.models import Pseudopatient
from ..utils.exceptions import Continue, EmptyRelatedModel
from ..utils.helpers import get_or_create_qs_attr, get_str_attrs

if TYPE_CHECKING:
    from datetime import date

    from django.forms import BaseModelFormSet  # type: ignore
    from django.http import HttpRequest, HttpResponse  # type: ignore

    from ..dateofbirths.forms import DateOfBirthForm
    from ..dateofbirths.models import DateOfBirth
    from ..genders.forms import GenderForm
    from ..genders.models import Gender
    from ..labs.models import Lab
    from ..medhistorydetails.forms import CkdDetailForm, GoutDetailForm
    from ..medhistorys.models import MedHistory
    from ..treatments.choices import FlarePpxChoices, Treatments, UltChoices
    from .types import FormModelDict, MedAllergyAidHistoryModel


User = get_user_model()


def add_patient_to_session(request: "HttpRequest", patient: Pseudopatient | User) -> None:
    request.session.update({"patient": str(patient), "username": patient.username})
    if not request.session.get("recent_patients", None):
        request.session["recent_patients"] = []
    if patient.username not in [recent_patient[1] for recent_patient in request.session["recent_patients"]]:
        request.session["recent_patients"].append(tuple([str(patient), patient.username]))
    elif patient.username != request.session["recent_patients"][0][1]:
        request.session["recent_patients"].remove(
            next(
                iter(
                    [
                        recent_patient
                        for recent_patient in request.session["recent_patients"]
                        if recent_patient[1] == patient.username
                    ]
                )
            )
        )
        request.session["recent_patients"].insert(0, tuple([str(patient), patient.username]))


def remove_patient_from_session(
    request: "HttpRequest",
    patient: Pseudopatient | User,
    delete: bool = False,
) -> None:
    request.session.pop("patient", None)
    request.session.pop("username", None)
    if (
        delete
        and request.session.get("recent_patients", None)
        and patient.username in [recent_patient[1] for recent_patient in request.session["recent_patients"]]
    ):
        request.session["recent_patients"].remove(
            next(
                iter(
                    [
                        recent_patient
                        for recent_patient in request.session["recent_patients"]
                        if recent_patient[1] == patient.username
                    ]
                )
            )
        )


def update_session_patient(request: "HttpRequest", patient: Pseudopatient | User | None) -> None:
    if patient:
        add_patient_to_session(request, patient)
    else:
        remove_patient_from_session(request, patient)


class PatientSessionMixin:
    """Mixin to add a session to a view."""

    def get_context_data(self, **kwargs):
        """Overwritten to add the patient to the session."""
        context = super().get_context_data(**kwargs)
        update_session_patient(self.request, getattr(self, "user", None))
        return context


def validate_form_list(form_list: list[ModelForm]) -> bool:
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


class GoutHelperEditMixin:
    @cached_property
    def model_field_names(self) -> list[str]:
        return [field.name for field in self.model._meta.get_fields()]

    @cached_property
    def object_attr(self) -> str:
        return self.object.__class__.__name__.lower() if not isinstance(self.object, Pseudopatient) else "user"

    def post_get_qs_target(
        self, post_object: Union["MedAllergyAidHistoryModel", User]
    ) -> Union["MedAllergyAidHistoryModel", User]:
        return self.query_object if isinstance(self.query_object, User) else post_object

    @cached_property
    def query_object(self) -> Union["MedAllergyAidHistoryModel", User, None]:
        return self.user if self.user else self.object if not self.create_view else self.related_object

    @cached_property
    def query_obj_attr(self) -> str:
        return (
            self.query_object.__class__.__name__.lower()
            if self.query_object and not isinstance(self.query_object, User)
            else "user"
            if self.query_object
            else None
        )

    @cached_property
    def related_object(self) -> Any:
        """Meant to defualt to None, but can be overwritten in child views."""
        return None

    @cached_property
    def request_user(self):
        return self.request.user

    def set_forms(self) -> None:
        self.set_lab_formsets()
        self.set_medallergy_forms()
        self.set_medhistory_forms()
        self.set_oto_forms()
        self.set_req_otos()

    def set_lab_formsets(self) -> None:
        self.lab_formsets = {}

    def set_medallergy_forms(self) -> None:
        self.medallergy_forms = {}

    def set_medhistory_forms(self) -> None:
        self.medhistory_forms = {}

    def set_oto_forms(self) -> None:
        self.oto_forms = {}

    def set_req_otos(self) -> None:
        self.req_onetoones = []

    @cached_property
    def str_attrs(self) -> dict[str, str]:
        """Returns a dict of string attributes to make forms context-sensitive."""
        return get_str_attrs(self.object if not self.create_view else None, self.user, self.request.user)

    @cached_property
    def user(self) -> User | None:
        """Method that returns the User object from the username kwarg
        and sets the user attr on the view."""
        username = self.kwargs.get("username", None)
        if username:
            try:
                self.user = self.get_user_queryset(username).get()
                return self.user
            except AttributeError:
                return self.get_queryset().get(username=username)
        else:
            return None


class LabFormSetsMixin(GoutHelperEditMixin):
    def context_labs(
        self,
        kwargs: dict,
    ) -> None:
        """Method adds a formset of labs to the context. Uses a QuerySet that takes a query_object
        as an arg to populate existing Lab objects."""

        for lab, lab_tup in self.lab_formsets.items():
            if f"{lab}_formset" not in kwargs:
                if self.query_object and self.lab_belong_to_query_object(lab):
                    kwargs[f"{lab}_formset"] = self.populate_a_lab_formset(
                        lab, {self.query_obj_attr: self.query_object}
                    )
                else:
                    lab_related_onetoone_attr = self.lab_belongs_to_onetoone(lab)
                    if lab_related_onetoone_attr and self.query_object:
                        kwargs[f"{lab}_formset"] = self.populate_a_lab_formset(
                            lab, {lab_related_onetoone_attr: getattr(self.query_object, lab_related_onetoone_attr)}
                        )
                    else:
                        kwargs[f"{lab}_formset"] = self.populate_a_lab_formset(lab, None)
            if f"{lab}_formset_helper" not in kwargs:
                kwargs[f"{lab}_formset_helper"] = lab_tup[1]

    def lab_belong_to_query_object(self, lab: str) -> bool:
        return self.query_obj_attr in self.lab_formsets[lab][0].model.related_models() or self.user

    def lab_belongs_to_onetoone(self, lab: str) -> str | None:
        return next(
            iter(
                [
                    attr
                    for attr in self.lab_formsets[lab][0].model.related_models()
                    if attr in self.oto_forms.keys() and attr in self.model_field_names
                ]
            ),
            None,
        )

    def form_valid_save_and_delete_labs(self) -> None:
        if self.labs_2_save:
            # Modify and remove labs from the object
            for lab in self.labs_2_save:
                if self.user:
                    if lab.user is None:
                        lab.user = self.user
                # check if the lab has the object_attr in its list of fields
                elif self.object_attr in lab.related_models():
                    if getattr(lab, self.object_attr, None) is None:
                        setattr(lab, self.object_attr, self.object)
                lab_related_onetoone_attr = self.lab_belongs_to_onetoone(lab.__class__.__name__.lower())
                if lab_related_onetoone_attr and getattr(lab, lab_related_onetoone_attr, None) is None:
                    setattr(lab, lab_related_onetoone_attr, getattr(self.object, lab_related_onetoone_attr))
                lab.save()
        if self.labs_2_rem:
            for lab in self.labs_2_rem:
                lab.delete()

    def post_populate_lab_formsets(self) -> None:
        """Method to populate a dict of lab forms with POST data in the post() method."""

        for lab, lab_tup in self.lab_formsets.items():
            if self.query_obj_attr:
                if self.query_obj_attr in lab_tup[0].model.related_models():
                    self.lab_formsets.update(
                        {lab: self.populate_a_lab_formset(lab, {self.query_obj_attr: self.query_object})}
                    )
                else:
                    related_onetoone_attr = self.lab_belongs_to_onetoone(lab)
                    if related_onetoone_attr:
                        queryset_kwargs = (
                            {related_onetoone_attr: getattr(self.query_object, related_onetoone_attr)}
                            if getattr(self.query_object, related_onetoone_attr, None)
                            else None
                        )
                        self.lab_formsets.update(
                            {lab: self.populate_a_lab_formset(lab, queryset_kwargs if queryset_kwargs else None)}
                        )
                    else:
                        self.lab_formsets.update({lab: self.populate_a_lab_formset(lab, None)})
            else:
                self.lab_formsets.update({lab: self.populate_a_lab_formset(lab, None)})

    def post_process_lab_formsets(
        self,
        lab_formsets: dict[str, "BaseModelFormSet"],
        post_object: Union["MedAllergyAidHistoryModel", User, None],
    ) -> tuple[list["Lab"], list["Lab"]]:
        """Method to process the forms in a Lab formset for the post() method.
        Requires a list of existing labs (can be empty) to iterate over and compare to the forms in the
        formset to identify labs that need to be removed.

        Args:
            lab_formset (BaseModelFormSet): A formset of LabForms
            query_object (MedAllergyAidHistoryModel | User): The object to which the labs are related

        Returns:
            tuple[list[Lab], list[Lab]]: A tuple of lists of labs to save and remove"""

        def _lab_needs_relation_set(lab: "Lab") -> bool:
            if self.user:
                return lab.user is None
            elif self.object_attr in [lab.related_models()]:
                return getattr(lab, self.object_attr, None) is None
            else:
                for related_model in lab.related_models():
                    if getattr(lab, related_model, None) is None and (
                        related_model in list(self.req_otos) + list(self.onetoones.keys())
                    ):
                        return True
                for oto in self.req_otos + list(self.onetoones.keys()):
                    if hasattr(lab, oto) and getattr(lab, oto, None) is None:
                        return True
                return False

        # Assign lists to return
        post_qs_target = self.post_get_qs_target(post_object)
        labs_2_save: list["Lab"] = []
        labs_2_rem: list["Lab"] = []

        if lab_formsets:
            for lab_name, lab_formset in lab_formsets.items():
                qs_target_method = getattr(self, f"post_get_{lab_name}_qs_target", None)
                qs_attr = get_or_create_qs_attr(
                    qs_target_method(post_object) if qs_target_method else post_qs_target, lab_name, self.query_object
                )
                # Check for and iterate over the existing queryset of labs to catch objects that
                # are not changed in the formset but NEED to be saved for the view (i.e. to add relations)
                if qs_attr:
                    cleaned_data = lab_formset.cleaned_data
                    # NOTE: FOR FUTURE SELF: COPY A LIST WHEN ITERATING OVER IT AND ADDING/REMOVING ELEMENTS
                    for lab in qs_attr.copy():
                        for lab_form in cleaned_data:
                            try:
                                if lab_form["id"] == lab:
                                    if not lab_form["DELETE"]:
                                        if _lab_needs_relation_set(lab):
                                            labs_2_save.append(lab)
                                        if lab not in qs_attr:
                                            qs_attr.append(lab)
                                        break
                            except KeyError:
                                pass
                        else:
                            labs_2_rem.append(lab)
                            qs_attr.remove(lab)
                for form in lab_formset:
                    if (
                        "value" in form.cleaned_data
                        and not form.cleaned_data["DELETE"]
                        and (
                            _lab_needs_relation_set(form.instance)
                            or (form.instance and form.has_changed())
                            or form.instance is None
                        )
                    ):
                        labs_2_save.append(form.instance)
                    if form.instance not in qs_attr:
                        qs_attr.append(form.instance)
        return labs_2_save, labs_2_rem

    def populate_a_lab_formset(
        self,
        lab: str,
        queryset_kwargs: dict[str, Any] | None,
    ) -> "BaseModelFormSet":
        formset_kwargs = {
            "queryset": (
                getattr(self, f"{lab}_formset_qs").filter(**queryset_kwargs)
                if queryset_kwargs
                else getattr(self, f"{lab}_formset_qs").none()
            ),
            "prefix": lab,
            "form_kwargs": {
                "patient": self.user,
                "request_user": self.request_user,
                "str_attrs": self.str_attrs,
            },
        }
        if self.request.method == "POST":
            formset_kwargs.update({"data": self.request.POST})
        return self.labs[lab][0](
            **formset_kwargs,
        )

    def post_get_creatinine_qs_target(
        self,
        post_object: Union["MedAllergyAidHistoryModel", User],
    ) -> Union["MedAllergyAidHistoryModel", User]:
        qs_target = getattr(post_object, "aki", None) if post_object else None
        if not qs_target:
            qs_target = self.oto_forms["aki_form"].instance
        return qs_target

    def post_get_urate_qs_target(
        self,
        post_object: Union["MedAllergyAidHistoryModel", User],
    ) -> Union["MedAllergyAidHistoryModel", User]:
        return post_object


class OneToOneFormMixin(GoutHelperEditMixin):
    def context_onetoones(
        self,
        kwargs: dict,
    ) -> None:
        for onetoone, oto_form in self.oto_forms.items():
            if self.related_object and getattr(self.related_object, onetoone, None) and onetoone not in kwargs:
                self.context_update_onetoone(onetoone, kwargs)
            else:
                form_str = f"{onetoone}_form"
                oto_obj = self.get_oto_obj(onetoone) if self.query_object else None
                if form_str not in kwargs:
                    onetoone_form_kwargs = {
                        "instance": oto_obj if oto_obj else oto_form._meta.model(),
                        "patient": self.user,
                        "request_user": self.request_user,
                        "str_attrs": self.str_attrs,
                    }
                    onetoone_form_kwargs.update({"initial": {"value": self.get_onetoone_value(onetoone)}})
                    kwargs[form_str] = oto_form(**onetoone_form_kwargs)
        for onetoone in self.req_otos:
            if onetoone not in kwargs:
                self.context_update_onetoone(onetoone, kwargs)

    def context_update_onetoone(self, onetoone: str, kwargs: dict) -> None:
        kwargs.update({"age" if onetoone == "dateofbirth" else onetoone: self.get_onetoone_value(onetoone)})

    def get_onetoone_value(
        self,
        onetoone: str,
    ) -> Any | None:
        if hasattr(self, f"get_{onetoone}_value"):
            return getattr(self, f"get_{onetoone}_value")()
        else:
            onetoone_object = getattr(self.query_object, onetoone, None) if self.query_object else None
            return onetoone_object.value if onetoone_object else None

    def get_dateofbirth(self) -> Union["DateOfBirth", None]:
        return getattr(self.query_object, "dateofbirth", None)

    def get_dateofbirth_value(self) -> int:
        dateofbirth = self.get_dateofbirth()
        return age_calc(dateofbirth.value) if dateofbirth else None

    def get_aki(self) -> bool | None:
        aki = getattr(self.query_object, "aki", None)
        return aki if aki else (getattr(self.object, "aki", None) if self.object else None)

    def get_aki_value(self) -> True | None:
        aki = self.get_aki()
        return True if aki else None

    def get_urate(self) -> Union["Lab", None]:
        urate = getattr(self.query_object, "urate", None)
        return urate if urate else (getattr(self.object, "urate", None) if self.object else None)

    def get_urate_value(self) -> str | None:
        urate = self.get_urate()
        return urate.value if urate else None

    def post_populate_oto_forms(self) -> None:
        if self.oto_forms:
            for onetoone, oto_form in self.oto_forms.items():
                if not self.related_object or (
                    self.related_object and not getattr(self.related_object, onetoone, None)
                ):
                    oto_obj = self.get_oto_obj(onetoone) if self.query_object else None
                    oto_form_kwargs = {
                        "instance": oto_obj if oto_obj else oto_form._meta.model(),
                        "patient": self.user,
                        "request_user": self.request_user,
                        "str_attrs": self.str_attrs,
                    }
                    oto_form_kwargs.update({"initial": {"value": self.get_onetoone_value(onetoone)}})
                    self.oto_forms.update({onetoone: oto_form(self.request.POST, **oto_form_kwargs)})

    def get_oto_obj(
        self,
        onetoone: str,
    ) -> Model:
        """Method that looks looks for a 1to1 related object on the query_object and returns it if found.
        If it's not, if the oto str is "urate", it looks for the 1to1 on the alt_obj and returns it if found."""
        oto_obj = getattr(self.query_object, onetoone, None) if self.query_object else None
        if not oto_obj and (onetoone == "urate" or onetoone == "aki"):
            oto_obj = getattr(self.object, onetoone, None) if self.object else None
        return oto_obj

    def post_process_oto_forms(
        self,
    ) -> tuple[list[Model], list[Model]]:
        oto_2_save: list[Model] = []
        oto_2_rem: list[Model] = []
        for onetoone, oto_form in self.oto_forms.items():
            object_attr = onetoone.lower()
            if object_attr not in self.req_otos and (
                not self.related_object
                or (self.related_object and not getattr(self.related_object, object_attr, None))
            ):
                try:
                    oto_form.check_for_value()
                    # Check if the onetoone changed
                    if oto_form.has_changed():
                        onetoone = oto_form.save(commit=False)
                        oto_2_save.append(onetoone)
                    else:
                        onetoone = oto_form.instance
                # If EmptyRelatedModel exception is raised by the related model's form save() method,
                # Check if the related model exists and delete it if it does
                except EmptyRelatedModel:
                    # Check if the related model has already been saved to the DB and mark for deletion if so
                    if oto_form.instance and not oto_form.instance._state.adding:
                        # Set the related model's fields to their initial values to prevent
                        # IntegrityError from Django-Simple-History historical model on delete().
                        if hasattr(oto_form, "required_fields"):
                            for field in oto_form.required_fields:
                                setattr(oto_form.instance, field, oto_form.initial[field])
                        oto_2_rem.append(oto_form.instance)
        return oto_2_save, oto_2_rem


class GoutHelperAidEditMixin(PatientSessionMixin, OneToOneFormMixin, LabFormSetsMixin, GoutHelperEditMixin):
    def add_mh_to_qs(self, mh: "MedHistory", qs: list["MedHistory"], check: bool = True) -> None:
        """Method to add a MedHistory to a list of MedHistories."""
        if not check or mh not in qs:
            qs.append(mh)

    def baselinecreatinine_form_post_process(
        self,
        baselinecreatinine_form: ModelForm,
        mhd_to_save: list["CkdDetail", "GoutDetail", BaselineCreatinine],
        mhd_to_remove: list["CkdDetail", "GoutDetail", BaselineCreatinine],
    ) -> None:
        if hasattr(baselinecreatinine_form.instance, "to_save"):
            mhd_to_save.append(baselinecreatinine_form)
        elif hasattr(baselinecreatinine_form.instance, "to_delete"):
            mhd_to_remove.append(baselinecreatinine_form)

    def check_user_onetoones(self, user: User) -> None:
        """Method that checks the view's user for the required onetoone models
        and raises and redirects to the user's profile updateview if they are
        missing."""
        # Need to check the user's role to avoid redirecting a Provider or Admin to
        # a view that is meant for a Pseudopatient or Patient
        for onetoone in self.req_otos:
            if not hasattr(user, onetoone):
                raise AttributeError("Baseline information is needed to use GoutHelper Decision and Treatment Aids.")

    @cached_property
    def ckddetail(self) -> bool:
        """Method that returns True if CKD is in the medhistory_details dict."""
        return MedHistoryTypes.CKD in self.medhistory_details.keys()

    def ckddetail_form_post_process(
        self,
        ckddetail_form: ModelForm,
        mhd_to_save: list["CkdDetail", "GoutDetail", BaselineCreatinine],
        mhd_to_remove: list["CkdDetail", "GoutDetail", BaselineCreatinine],
    ) -> None:
        if hasattr(ckddetail_form.instance, "to_save"):
            mhd_to_save.append(ckddetail_form)
        elif hasattr(ckddetail_form.instance, "to_delete"):
            mhd_to_remove.append(ckddetail_form)

    def ckddetail_mh_context(
        self,
        kwargs: dict[str, Any],
        mh_dets: dict[MedHistoryTypes, ModelForm],
        ckddetail: bool,
        mh_obj: Union["MedHistory", None] = None,
        patient: Pseudopatient | None = None,
        request_user: User | None = None,
        str_attrs: dict[str, str] = None,
    ) -> None:
        """Method that populates the context dictionary with the CkdDetailForm."""
        if ckddetail:
            if "ckddetail_form" not in kwargs:
                ckddetail_i = getattr(mh_obj, "ckddetail", None) if mh_obj else None
                kwargs["ckddetail_form"] = mh_dets[MedHistoryTypes.CKD](
                    instance=ckddetail_i,
                    patient=patient,
                    request_user=request_user,
                    str_attrs=str_attrs,
                )
            if "baselinecreatinine_form" not in kwargs:
                bc_i = getattr(mh_obj, "baselinecreatinine", None) if mh_obj else None
                kwargs["baselinecreatinine_form"] = BaselineCreatinineForm(
                    instance=bc_i,
                    patient=patient,
                    request_user=request_user,
                    str_attrs=str_attrs,
                )

    def ckddetail_mh_post_pop(
        self,
        ckd: Union["MedHistory", None],
        mh_det_forms: dict[str, ModelForm],
        mh_dets: dict[MedHistoryTypes, ModelForm],
        request: "HttpRequest",
        patient: Pseudopatient | None,
        request_user: User | None,
        str_attrs: dict[str, str],
    ) -> None:
        """Method that updates the CkdDetail and BaselineCreatinine forms to populate the MedHistoryDetails Forms
        in the post() method."""
        if ckd:
            ckddetail = getattr(ckd, "ckddetail", None)
            bc = getattr(ckd, "baselinecreatinine", None)
        else:
            ckddetail = CkdDetail()
            bc = BaselineCreatinine()
        mh_det_forms.update(
            {
                "ckddetail_form": mh_dets[MedHistoryTypes.CKD](
                    request.POST, instance=ckddetail, patient=patient, request_user=request_user, str_attrs=str_attrs
                )
            }
        )
        mh_det_forms.update(
            {
                "baselinecreatinine_form": BaselineCreatinineForm(
                    request.POST, instance=bc, patient=patient, request_user=request_user, str_attrs=str_attrs
                )
            }
        )

    def ckddetail_mh_post_process(
        self,
        ckd: "MedHistory",
        mh_det_forms: dict[str, ModelForm],
        dateofbirth: "DateOfBirth",
        gender: "Gender",
        mhd_to_save: list["CkdDetail", "GoutDetail", BaselineCreatinine],
        mhd_to_remove: list["CkdDetail", "GoutDetail", BaselineCreatinine],
    ) -> tuple["CkdDetailForm", BaselineCreatinine, bool]:
        """Method to process the CkdDetailForm and BaselineCreatinineForm
        as part of the post() method."""
        ckddet_form, bc_form, errors = CkdDetailFormProcessor(
            ckd=ckd,
            ckddetail_form=mh_det_forms["ckddetail_form"],
            baselinecreatinine_form=mh_det_forms["baselinecreatinine_form"],
            dateofbirth=dateofbirth,
            gender=gender,
        ).process()
        if bc_form:
            self.baselinecreatinine_form_post_process(
                baselinecreatinine_form=bc_form,
                mhd_to_save=mhd_to_save,
                mhd_to_remove=mhd_to_remove,
            )
        if ckddet_form:
            self.ckddetail_form_post_process(
                ckddetail_form=ckddet_form,
                mhd_to_save=mhd_to_save,
                mhd_to_remove=mhd_to_remove,
            )
        return errors

    def context_medallergys(
        self,
        medallergys: list["MedAllergy"],
        kwargs: dict,
        query_object: Union["MedAllergyAidHistoryModel", User, None],
        patient: Pseudopatient | None = None,
        request_user: User | None = None,
        str_attrs: dict[str, str] = None,
    ) -> None:
        for treatment in medallergys:
            form_str = f"medallergy_{treatment}_form"
            if form_str not in kwargs:
                ma_obj = (
                    next(
                        iter([ma for ma in getattr(query_object, "medallergys_qs", []) if ma.treatment == treatment]),
                        None,
                    )
                    if query_object
                    else None
                )
                kwargs[form_str] = MedAllergyTreatmentForm(
                    treatment=treatment,
                    instance=ma_obj,
                    initial={
                        f"medallergy_{treatment}": True if ma_obj else None,
                        f"{treatment}_matype": ma_obj.matype if ma_obj else None,
                    },
                    patient=patient,
                    request_user=request_user,
                    str_attrs=str_attrs,
                )

    def context_medhistorys(
        self,
        medhistorys: dict[MedHistoryTypes, "FormModelDict"],
        mh_dets: dict[MedHistoryTypes, ModelForm],
        kwargs: dict,
        query_object: Union["MedAllergyAidHistoryModel", User, None],
        ckddetail: bool,
        goutdetail: bool,
        patient: Pseudopatient | None = None,
        request_user: User | None = None,
        str_attrs: dict[str, str] = None,
    ) -> None:
        """Method that iterates over the medhistorys dict and adds the forms to the context."""
        mhtype_aids = (
            MedHistoryTypesAids(
                mhtypes=list(self.medhistorys.keys()),
                related_object=patient if patient else self.related_object if self.related_object else None,
            ).get_medhistorytypes_aid_dict()
            if self.create_view and (patient or self.related_object)
            else None
        )
        for mhtype, mh_dict in medhistorys.items():
            form_str = f"{mhtype}_form"
            if form_str not in kwargs:
                mh_obj = (
                    medhistorys_get(query_object.medhistorys_qs, mhtype, null_return=None) if query_object else None
                )
                form_kwargs = {"str_attrs": str_attrs, "patient": patient, "request_user": request_user}
                if mhtype == MedHistoryTypes.CKD:
                    form_kwargs.update({"ckddetail": ckddetail})
                    self.ckddetail_mh_context(
                        kwargs=kwargs,
                        mh_dets=mh_dets,
                        ckddetail=ckddetail,
                        mh_obj=mh_obj,
                        patient=patient,
                        request_user=request_user,
                        str_attrs=str_attrs,
                    )
                elif mhtype == MedHistoryTypes.GOUT:
                    form_kwargs.update({"goutdetail": goutdetail})
                    if goutdetail:
                        try:
                            self.goutdetail_mh_context(
                                kwargs=kwargs,
                                mh_dets=mh_dets,
                                mh_obj=mh_obj,
                                patient=patient,
                                request_user=request_user,
                                str_attrs=str_attrs,
                            )
                        except Continue:
                            continue
                        kwargs[form_str] = mh_dict["form"](
                            instance=mh_obj,
                            initial={f"{mhtype}-value": True},
                            **form_kwargs,
                        )
                        continue
                kwargs[form_str] = mh_dict["form"](
                    instance=mh_obj,
                    initial={
                        f"{mhtype}-value": (
                            True
                            if mh_obj
                            else (
                                False
                                if (mhtype_aids and mhtype_aids.get(mhtype))
                                else None
                                if self.create_view
                                else False
                            )
                        )
                    },
                    **form_kwargs,
                )

    @cached_property
    def create_view(self):
        """Method that returns True if the view is a CreateView."""
        return True if isinstance(self, CreateView) else False

    def dispatch(self, request, *args, **kwargs):
        """Overwritten to redirect if the user is attempting to create an instance of a model that the intended
        Pseudopatient already has an instance of and their relationship is a 1to1."""
        # Will also set self.user
        try:
            self.object = self.get_object()
        except self.model.DoesNotExist as exc:
            if self.user:
                messages.error(request, exc.args[0])
                return HttpResponseRedirect(
                    reverse(
                        f"{self.model.__name__.lower()}s:pseudopatient-create", kwargs={"username": kwargs["username"]}
                    )
                )
            else:
                raise exc
        if self.user:
            try:
                self.check_user_onetoones(user=self.user)
            except AttributeError as exc:
                messages.error(request, exc)
                return HttpResponseRedirect(
                    reverse("users:pseudopatient-update", kwargs={"username": self.user.username})
                )
            if self.create_view:
                model_name = self.model.__name__
                if model_name != "Flare" and self.model.objects.filter(user=self.user).exists():
                    messages.error(request, f"{self.user} already has a {model_name}. Please update it instead.")
                    return HttpResponseRedirect(
                        reverse(f"{model_name.lower()}s:pseudopatient-update", kwargs={"username": self.user.username})
                    )
        elif getattr(self.object, "user", None) and not isinstance(self.object, User):
            kwargs = {"username": self.object.user.username}
            if self.model.__name__.lower() == "flare":
                kwargs["pk"] = self.object.pk
            return HttpResponseRedirect(
                reverse(
                    f"{self.model._meta.app_label}:pseudopatient-{'create' if self.create_view else 'update'}",
                    kwargs=kwargs,
                )
            )
        # Raise a redirect if trying to create a related Aid for an Aid that already has that Aid set (i.e. FlareAid
        # for a Flare with a flareaid attr already set)
        elif self.related_object:
            if self.create_view:
                related_object_attr = getattr(self.related_object, self.model_name.lower(), None)
                if related_object_attr:
                    messages.error(
                        request, f"{self.related_object} already has a {self.model_name}. Please update it instead."
                    )
                    return HttpResponseRedirect(
                        reverse(
                            f"{self.model_name.lower()}s:update",
                            kwargs={"pk": related_object_attr.pk},
                        )
                    )
        return super().dispatch(request, *args, **kwargs)

    def form_valid_set_aid_obj_relations(
        self,
        aid_obj: "MedAllergyAidHistoryModel",
        kwargs: dict[str, Any],
        save_aid_obj: bool,
    ) -> bool:
        """Sets related objects for the aid_obj that are passed to form_valid
        from the post() method.

        returns: bool, save_aid_obj arg, potentially modified in the method."""
        for key, val in kwargs.items():
            if (
                isinstance(val, Model)
                and key in [field.name for field in aid_obj._meta.fields]
                and getattr(aid_obj, key, None) is None
            ):
                setattr(aid_obj, key, val)
                if save_aid_obj is not True:
                    save_aid_obj = True
        return save_aid_obj

    def form_valid_set_related_object_aid_obj_attr(
        self,
        aid_obj: "MedAllergyAidHistoryModel",
        aid_obj_attr: str,
        kwargs: dict[str, Any],
    ) -> None:
        """Sets the related object's aid_obj_attr attr to the aid_obj and saves the model
        if the related object was updated."""

        for val in kwargs.values():
            if (
                isinstance(val, Model)
                and aid_obj_attr in [field.name for field in val._meta.fields]
                and getattr(val, aid_obj_attr, None) is None
            ):
                setattr(val, aid_obj_attr, aid_obj)
                val.full_clean()
                val.save()

    def form_valid_update_mh_det_mh(
        self, mh: "MedHistory", mhs_to_save: list["MedHistory"], mhs_to_rem: list["MedHistory"], commit: bool = True
    ) -> None:
        """Checks if the MedHistory object has a MedHistoryDetail that needs to be saved and adjusts the set_date to
        timezone.now(), also checks if a MedHistoryDetail object that is going to be saved has a MedHistory object
        that needs to be updated and saved."""

        def need_to_save_mh(mh: "MedHistory", mhs_to_save: list["MedHistory"], mhs_to_rem: list["MedHistory"]) -> bool:
            return (mhs_to_save and mh not in mhs_to_save or not mhs_to_save) and (
                mhs_to_rem and mh not in mhs_to_rem or not mhs_to_rem
            )

        if need_to_save_mh(mh, mhs_to_save, mhs_to_rem):
            mh.update_set_date(commit=commit)

    def form_valid_save_otos(
        self,
        oto_2_save: list[Model] | None,
        form: ModelForm,
    ) -> None:
        """Method that saves the OneToOne related models. Related fields for the OneToOne are
        set based on the User-status of the view, as are attributes of the view's object."""
        if oto_2_save:
            for oto in oto_2_save:
                oto_attr = f"{oto.__class__.__name__.lower()}"
                if self.user and oto.user is None:
                    oto.user = self.user
                oto.save()
                if getattr(form.instance, oto_attr, None) is None:
                    if not self.user or oto_attr == "urate" or oto_attr == "aki":
                        setattr(form.instance, oto_attr, oto)

    def form_valid_related_object_otos(
        self,
        form: ModelForm,
        onetoones: dict[str, "FormModelDict"],
        related_object: "MedAllergyAidHistoryModel",
    ):
        def check_if_oto_attr_in_related_object_fields(
            oto_attr: str, related_object: "MedAllergyAidHistoryModel"
        ) -> bool:
            return oto_attr in [field.name for field in related_object._meta.fields]

        for oto_attr in onetoones.keys():
            related_object_oto = getattr(related_object, oto_attr, None)
            if (
                related_object_oto
                and check_if_oto_attr_in_related_object_fields(oto_attr, related_object)
                and getattr(form.instance, oto_attr, None) is None
            ):
                setattr(form.instance, oto_attr, related_object_oto)

    def form_valid_delete_otos(self, oto_2_rem: list[Model] | None, form: ModelForm) -> None:
        """Method to delete the OneToOne related models. Related fields for the OneToOne are
        set based on the User-status of the view, as are attributes of the view's object."""
        if oto_2_rem:
            for oto in oto_2_rem:
                oto_class = oto.__class__.__name__.lower()
                if not self.user or oto_class == "urate" or oto_class == "aki":
                    setattr(form.instance, f"{oto.__class__.__name__.lower()}", None)
                oto.delete()

    def form_valid(self, **kwargs) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Method to be called if all forms are valid."""
        if isinstance(self.form.instance, User):
            self.user = self.form.save()
            save_aid_obj = False
        elif (
            self.form.has_changed
            or self.onetoones
            and (self.oto_2_save or self.oto_2_rem)
            or self.user
            and self.form.instance.user is None
            or self.create_view
        ):
            self.object = self.form.save(commit=False)
            save_aid_obj = True
        else:
            self.object = self.form.instance
            save_aid_obj = False
        if self.user and self.object.user is None:
            self.object.user = self.user
        # Save the OneToOne related models
        if self.onetoones:
            print(self.oto_2_save)
            self.form_valid_save_otos(self.oto_2_save, self.form)
            self.form_valid_delete_otos(self.oto_2_rem, self.form)
            if self.related_object:
                self.form_valid_related_object_otos(
                    form=self.form,
                    onetoones=self.onetoones,
                    related_object=self.related_object,
                )
        if kwargs:
            self.form_valid_set_aid_obj_relations(self.object, kwargs, save_aid_obj)
        if save_aid_obj:
            self.object.save()
        if kwargs:
            self.form_valid_set_related_object_aid_obj_attr(self.object, self.object_attr, kwargs)
        if self.medallergys:
            if self.ma_2_save:
                for ma in self.ma_2_save:
                    if self.user:
                        if ma.user is None:
                            ma.user = self.user
                    else:
                        if getattr(ma, self.object_attr, None) is None:
                            setattr(ma, self.object_attr, self.object)
                    ma.save()
            if self.ma_2_rem:
                for ma in self.ma_2_rem:
                    ma.delete()
        if self.medhistorys:
            if self.mh_2_save:
                for mh in self.mh_2_save:
                    if self.user:
                        if mh.user is None:
                            mh.user = self.user
                    else:
                        if getattr(mh, self.object_attr, None) is None:
                            setattr(mh, self.object_attr, self.object)
                    mh.update_set_date()
            if self.mh_det_2_save:
                for mh_det in self.mh_det_2_save:
                    mh_det.save()
                    self.form_valid_update_mh_det_mh(
                        mh_det.instance.medhistory if isinstance(mh_det, ModelForm) else mh_det.medhistory,
                        self.mh_2_save,
                        self.mh_2_rem,
                    )
            if self.mh_2_rem:
                for mh in self.mh_2_rem:
                    mh.update_set_date(commit=False)
                    mh.delete()
            if self.mh_det_2_rem:
                for mh_det in self.mh_det_2_rem:
                    mh_det.instance.delete()
                    self.form_valid_update_mh_det_mh(
                        mh_det.instance.medhistory if isinstance(mh_det, ModelForm) else mh_det.medhistory,
                        self.mh_2_save,
                        self.mh_2_rem,
                    )
        if self.labs:
            self.form_valid_save_and_delete_labs(self.labs_2_save, self.labs_2_rem)
        if self.user:
            setattr(self.user, f"{self.object_attr}_qs", self.object)
            self.object.update_aid(qs=self.user)
        else:
            self.object.update_aid(qs=self.object)
        messages.success(self.request, self.get_success_message(self.form.cleaned_data))
        if self.request.htmx:
            return kwargs.get("htmx")
        return HttpResponseRedirect(self.get_success_url())

    def get(self, request, *args, **kwargs):
        """Overwritten to not call get_object()."""
        self.set_forms()
        return self.render_to_response(self.get_context_data())

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        if self.onetoones or self.req_otos:
            self.context_onetoones(kwargs=kwargs)
        if self.medallergys:
            self.context_medallergys(
                medallergys=self.medallergys,
                kwargs=kwargs,
                query_object=self.query_object,
                patient=self.user,
                request_user=self.request.user,
                str_attrs=self.str_attrs,
            )
        if self.medhistorys or self.medhistory_details:
            self.context_medhistorys(
                medhistorys=self.medhistorys,
                mh_dets=self.medhistory_details,
                kwargs=kwargs,
                query_object=self.query_object,
                ckddetail=self.ckddetail,
                goutdetail=self.goutdetail,
                patient=self.user,
                request_user=self.request.user,
                str_attrs=self.str_attrs,
            )
        if self.labs:
            self.context_labs(
                labs=self.labs,
                kwargs=kwargs,
            )
        if "patient" not in kwargs and self.user:
            kwargs["patient"] = self.user
        kwargs.update({"str_attrs": self.str_attrs})
        return super().get_context_data(**kwargs)

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        if self.medallergys:
            kwargs["medallergys"] = self.medallergys
        kwargs.update(
            {
                "patient": self.user,
                "request_user": self.request.user,
                "str_attrs": self.str_attrs,
                "related_object": self.related_object if self.related_object else None,
            }
        )
        if self.create_view:
            kwargs.update({"instance": self.object})
        return kwargs

    def get_http_response_redirect(self) -> HttpResponseRedirect:
        """Method that returns an HttpResponseRedirect object."""
        return HttpResponseRedirect(self.object.get_absolute_url())

    def get_object(self, queryset=None) -> Model:
        if not hasattr(self, "object"):
            if self.create_view:
                return self.model()
            elif self.user:
                if self.model not in (User, Pseudopatient):
                    model_name = self.model.__name__.lower()
                    try:
                        return getattr(self.user, model_name)
                    except self.model.DoesNotExist as exc:
                        raise self.model.DoesNotExist(f"No {self.model.__name__} matching the query") from exc
                    except AttributeError as exc:
                        model_qs = getattr(self.user, f"{model_name}_qs")
                        try:
                            return model_qs[0]
                        except IndexError:
                            raise self.model.DoesNotExist(f"No {self.model.__name__} matching the query") from exc
                else:
                    return self.user
            return super().get_object(queryset)

    def get_permission_object(self):
        """Returns the view's object, which will have already been set by dispatch()."""
        return self.object if not self.create_view else self.user if self.user else None

    def get_success_url(self):
        """Overwritten to take optional next parameter from url"""
        next_url = self.request.POST.get("next", None)
        if next_url:
            return next_url
        else:
            return super().get_success_url() + "?updated=True"

    @cached_property
    def goutdetail(self) -> bool:
        """Method that returns True if GOUT is in the medhistorys dict."""
        return MedHistoryTypes.GOUT in self.medhistory_details.keys()

    def goutdetail_mh_context(
        self,
        kwargs: dict[str, Any],
        mh_dets: dict[MedHistoryTypes, ModelForm],
        mh_obj: Union["MedHistory", User, None] = None,
        patient: Pseudopatient | None = None,
        request_user: User | None = None,
        str_attrs: dict[str, str] = None,
    ) -> None:
        """Method that adds the GoutDetailForm to the context."""
        if "goutdetail_form" not in kwargs:
            goutdetail_i = getattr(mh_obj, "goutdetail", None) if mh_obj else None
            kwargs["goutdetail_form"] = mh_dets[MedHistoryTypes.GOUT](
                instance=goutdetail_i,
                patient=patient,
                request_user=request_user,
                str_attrs=str_attrs,
            )
            if hasattr(mh_obj, "user") and mh_obj.user:
                raise Continue

    def goutdetail_mh_post_pop(
        self,
        gout: Union["MedHistory", None],
        mh_det_forms: dict[str, ModelForm],
        mh_dets: dict[MedHistoryTypes, ModelForm],
        request: "HttpRequest",
        patient: Pseudopatient | None,
        request_user: User | None,
        str_attrs: dict[str, str],
    ) -> None:
        """Method that adds the GoutDetailForm to the mh_det_forms dict."""
        if gout:
            gd = getattr(gout, "goutdetail", None)
        else:
            gd = GoutDetail()
        mh_det_forms.update(
            {
                "goutdetail_form": mh_dets[MedHistoryTypes.GOUT](
                    request.POST, instance=gd, patient=patient, request_user=request_user, str_attrs=str_attrs
                )
            }
        )
        if hasattr(gout, "user") and gout.user:
            raise Continue

    def goutdetail_mh_post_process(
        self,
        gout: Union["MedHistory", None],
        mh_det_forms: dict[str, ModelForm],
        mhd_to_save: list["CkdDetail", "GoutDetail", BaselineCreatinine],
    ) -> None:
        """Method that processes the GoutDetailForm as part of the post() method."""

        gd_form = mh_det_forms["goutdetail_form"]
        gd_mh = getattr(gd_form.instance, "medhistory", None)
        if gd_form.has_changed or not gd_mh:
            mhd_to_save.append(gd_form.save(commit=False))
            # Check if the form instance has a medhistory attr
            if not gd_mh and gout:
                # If not, set it to the medhistory instance
                gd_form.instance.medhistory = gout

    def mh_clean_data(
        self,
        mh: MedHistoryTypes,
        cd: dict[str, Any],
    ) -> bool:
        """Method that searches a cleaned_data dict for a value key and returns
        True if found, False otherwise."""

        return cd.get(f"{mh}-value", False)

    @cached_property
    def model_name(self) -> str:
        return self.model.__name__

    def post(self, request, *args, **kwargs):
        """Processes forms for primary and related models"""
        self.set_forms()
        # user and object attrs are set by the dispatch() method on the child class
        form_class = self.get_form_class()
        self.form = form_class(
            **self.get_form_kwargs(),
        )
        # Populate dicts for related models with POST data
        self.oto_forms = self.post_populate_oto_forms() if self.onetoones else None
        self.ma_forms = self.post_populate_ma_forms(
            medallergys=self.medallergys,
            request=request,
            patient=self.user,
            request_user=self.request.user,
            str_attrs=self.str_attrs,
        )
        self.mh_forms, self.mh_det_forms = self.post_populate_mh_forms(
            medhistorys=self.medhistorys,
            mh_dets=self.medhistory_details,
            request=request,
            ckddetail=self.ckddetail,
            goutdetail=self.goutdetail,
            create=True if self.create_view else False,
            patient=self.user,
            request_user=self.request.user,
            str_attrs=self.str_attrs,
        )
        self.lab_formsets = self.post_populate_lab_formsets(labs=self.labs) if self.labs else None
        form_is_valid = self.form.is_valid()
        oto_forms_is_valid = validate_form_list(form_list=self.oto_forms.values()) if self.oto_forms else True
        ma_forms_is_valid = validate_form_list(form_list=self.ma_forms.values()) if self.ma_forms else True
        mh_forms_is_valid = validate_form_list(form_list=self.mh_forms.values()) if self.mh_forms else True
        mh_det_forms_is_valid = validate_form_list(form_list=self.mh_det_forms.values()) if self.mh_det_forms else True
        lab_formsets_is_valid = (
            validate_formset_list(formset_list=self.lab_formsets.values()) if self.lab_formsets else True
        )
        if (
            form_is_valid
            and oto_forms_is_valid
            and ma_forms_is_valid
            and mh_forms_is_valid
            and mh_det_forms_is_valid
            and lab_formsets_is_valid
        ):
            self.errors_bool = False
            self.form.save(commit=False)
            # Set related models for saving and set as attrs of the UpdateView model instance
            self.oto_2_save, self.oto_2_rem = self.post_process_oto_forms() if self.onetoones else (None, None)
            self.ma_2_save, self.ma_2_rem = self.post_process_ma_forms(
                ma_forms=self.ma_forms,
                post_object=self.form.instance,
            )
            (
                self.mh_2_save,
                self.mh_2_rem,
                self.mh_det_2_save,
                self.mh_det_2_rem,
                self.errors_bool,
            ) = self.post_process_mh_forms(
                mh_forms=self.mh_forms,
                mh_det_forms=self.mh_det_forms,
                post_object=self.form.instance,
                ckddetail=self.ckddetail,
                goutdetail=self.goutdetail,
                dateofbirth=self.oto_forms.get("dateofbirth_form", None) if self.oto_forms else None,
                gender=self.oto_forms.get("gender_form") if self.oto_forms else None,
            )
            (
                self.labs_2_save,
                self.labs_2_rem,
            ) = (
                self.post_process_lab_formsets(
                    lab_formsets=self.lab_formsets,
                    post_object=self.form.instance,
                )
                if self.labs
                else (None, None)
            )
            # If there are errors picked up after the initial validation step
            # render the errors as errors and include in the return tuple
            self.errors = (
                self.render_errors(
                    form=self.form,
                    oto_forms=self.oto_forms if self.oto_forms else None,
                    ma_forms=self.ma_forms if self.ma_forms else None,
                    mh_forms=self.mh_forms if self.mh_forms else None,
                    mh_det_forms=self.mh_det_forms if self.mh_det_forms else None,
                    lab_formsets=self.lab_formsets if self.lab_formsets else None,
                )
                if self.errors_bool
                else None
            )
        else:
            # If all the forms aren't valid unpack the related model form dicts into the context
            # and return the UpdateView with the invalid forms
            self.errors = self.render_errors(
                form=self.form,
                oto_forms=self.oto_forms if self.oto_forms else None,
                ma_forms=self.ma_forms if self.ma_forms else None,
                mh_forms=self.mh_forms if self.mh_forms else None,
                mh_det_forms=self.mh_det_forms if self.mh_det_forms else None,
                lab_formsets=self.lab_formsets if self.lab_formsets else None,
            )

    def post_populate_ma_forms(
        self,
        medallergys: None | type["FlarePpxChoices"] | type["UltChoices"] | type["Treatments"],
        request: "HttpRequest",
        patient: Pseudopatient | None = None,
        request_user: User | None = None,
        str_attrs: dict[str, str] = None,
    ) -> dict[str, ModelForm]:
        """Method to populate the forms for the MedAllergys for the post() method."""
        ma_forms: dict[str, ModelForm] = {}
        if medallergys:
            for treatment in medallergys:
                ma_obj = (
                    next(
                        iter(
                            [
                                ma
                                for ma in getattr(self.query_object, "medallergys_qs", [])
                                if ma.treatment == treatment
                            ]
                        ),
                        None,
                    )
                    if self.query_object
                    else None
                )
                ma_forms.update(
                    {
                        f"medallergy_{treatment}_form": MedAllergyTreatmentForm(
                            request.POST,
                            treatment=treatment,
                            instance=ma_obj,
                            initial={
                                f"medallergy_{treatment}": True if ma_obj else None,
                                f"{treatment}_matype": ma_obj.matype if ma_obj else None,
                            },
                            patient=patient,
                            request_user=request_user,
                            str_attrs=str_attrs,
                        )
                    }
                )
        return ma_forms

    def post_populate_mh_forms(
        self,
        medhistorys: dict[MedHistoryTypes, "FormModelDict"],
        mh_dets: dict[MedHistoryTypes, ModelForm],
        request: "HttpRequest",
        ckddetail: bool,
        goutdetail: bool,
        create: bool = False,
        patient: Pseudopatient | None = None,
        request_user: User | None = None,
        str_attrs: dict[str, str] = None,
    ) -> tuple[dict[str, ModelForm], dict[str, ModelForm]]:
        """Populates forms for MedHistory and MedHistoryDetail objects in post() method."""
        mh_forms: dict[str, ModelForm] = {}
        mh_det_forms: dict[str, ModelForm] = {}
        if medhistorys:
            mhtype_aids = (
                MedHistoryTypesAids(
                    mhtypes=list(self.medhistorys.keys()),
                    related_object=patient if patient else self.related_object if self.related_object else None,
                ).get_medhistorytypes_aid_dict()
                if self.create_view and (patient or self.related_object)
                else None
            )
            for medhistory in medhistorys:
                mh_obj = (
                    medhistorys_get(self.query_object.medhistorys_qs, medhistory, null_return=None)
                    if self.query_object
                    else None
                )
                form_kwargs = {"patient": patient, "request_user": request_user, "str_attrs": str_attrs}
                if medhistory == MedHistoryTypes.CKD:
                    form_kwargs.update({"ckddetail": ckddetail})
                    if ckddetail:
                        self.ckddetail_mh_post_pop(
                            ckd=mh_obj,
                            mh_det_forms=mh_det_forms,
                            mh_dets=mh_dets,
                            request=request,
                            patient=patient,
                            request_user=request_user,
                            str_attrs=str_attrs,
                        )
                elif medhistory == MedHistoryTypes.GOUT:
                    form_kwargs.update({"goutdetail": goutdetail})
                    if goutdetail:
                        try:
                            self.goutdetail_mh_post_pop(
                                gout=mh_obj,
                                mh_det_forms=mh_det_forms,
                                mh_dets=mh_dets,
                                request=request,
                                patient=patient,
                                request_user=request_user,
                                str_attrs=str_attrs,
                            )
                        except Continue:
                            continue
                        mh_forms.update(
                            {
                                f"{medhistory}_form": medhistorys[medhistory]["form"](
                                    request.POST,
                                    instance=mh_obj if mh_obj else medhistorys[medhistory]["model"](),
                                    initial={f"{medhistory}-value": True},
                                    **form_kwargs,
                                )
                            }
                        )
                        continue
                mh_forms.update(
                    {
                        f"{medhistory}_form": medhistorys[medhistory]["form"](
                            request.POST,
                            instance=mh_obj if mh_obj else medhistorys[medhistory]["model"](),
                            initial=(
                                {
                                    f"{medhistory}-value": True
                                    if mh_obj
                                    else False
                                    if (mhtype_aids and mhtype_aids.get(medhistory))
                                    else None
                                    if create
                                    else False
                                }
                            ),
                            **form_kwargs,
                        )
                    }
                )
        return mh_forms, mh_det_forms

    def post_process_ma_forms(
        self,
        ma_forms: dict[str, ModelForm],
        post_object: Union["MedAllergyAidHistoryModel", User, None],
    ) -> tuple[list["MedAllergy"], list["MedAllergy"]]:
        post_qs_target = self.post_get_qs_target(post_object)
        ma_2_save: list["MedAllergy"] = []
        ma_2_rem: list["MedAllergy"] = []
        get_or_create_qs_attr(post_qs_target, "medallergy")
        for ma_form_str in ma_forms:
            treatment = ma_form_str.split("_")[1]
            if f"medallergy_{treatment}" in ma_forms[ma_form_str].cleaned_data:
                ma_obj = (
                    next(
                        iter(
                            [
                                ma
                                for ma in getattr(self.query_object, "medallergys_qs", [])
                                if ma.treatment == treatment
                            ]
                        ),
                        None,
                    )
                    if self.query_object
                    else None
                )
                if ma_obj and not ma_forms[ma_form_str].cleaned_data[f"medallergy_{treatment}"]:
                    ma_2_rem.append(ma_obj)
                    getattr(post_qs_target, "medallergys_qs", []).remove(ma_obj)
                else:
                    if ma_forms[ma_form_str].cleaned_data[f"medallergy_{treatment}"]:
                        # If there is already an instance, it will not have changed so it doesn't need to be changed
                        if not ma_obj:
                            ma = ma_forms[ma_form_str].save(commit=False)
                            # Assign MedAllergy object treatment attr from the cleaned_data["treatment"]
                            ma.treatment = ma_forms[ma_form_str].cleaned_data["treatment"]
                            ma.matype = ma_forms[ma_form_str].cleaned_data.get(f"{treatment}_matype", None)
                            ma_2_save.append(ma)
                            # Add the medallergy to the form instance's medallergys_qs if it's not already there
                            if ma not in getattr(post_qs_target, "medallergys_qs", []):
                                getattr(post_qs_target, "medallergys_qs", []).append(ma)
                        else:
                            if ma_obj.matype != ma_forms[ma_form_str].cleaned_data[f"{treatment}_matype"]:
                                ma_obj.matype = ma_forms[ma_form_str].cleaned_data[f"{treatment}_matype"]
                                ma_2_save.append(ma_obj)
                            # Add the medallergy to the form instance's medallergys_qs if it's not already there
                            if ma_obj not in getattr(post_qs_target, "medallergys_qs", []):
                                getattr(post_qs_target, "medallergys_qs", []).append(ma_obj)
        return ma_2_save, ma_2_rem

    def post_process_menopause(
        self,
        mh_forms: dict[str, ModelForm],
        post_object: Union["MedAllergyAidHistoryModel", None] = None,
        gender: Genders | None = None,
        dateofbirth: Union["date", None] = None,
        errors_bool: bool = False,
    ) -> tuple[dict[str, ModelForm], bool]:
        if post_object and gender or post_object and dateofbirth:
            raise ValueError("You must provide either a MedAllergyAidHistoryModel object or a dateofbirth and gender.")
        gender = post_object.gender.value if post_object else gender
        dateofbirth = post_object.dateofbirth.value if post_object else dateofbirth
        if gender and gender == Genders.FEMALE and dateofbirth:
            age = age_calc(dateofbirth)
            if age >= 40 and age < 60:
                menopause = mh_forms[f"{MedHistoryTypes.MENOPAUSE}_form"].cleaned_data.get(
                    f"{MedHistoryTypes.MENOPAUSE}-value", None
                )
                if menopause is None or menopause == "":
                    menopause_error = ValidationError(
                        message="For females between ages 40 and 60, we need to know the patient's \
menopause status to evaluate their flare."
                    )
                    mh_forms[f"{MedHistoryTypes.MENOPAUSE}_form"].add_error(
                        f"{MedHistoryTypes.MENOPAUSE}-value", menopause_error
                    )
                    errors_bool = True
        return mh_forms, errors_bool

    def post_process_mh_forms(
        self,
        mh_forms: dict[str, ModelForm],
        mh_det_forms: dict[str, ModelForm],
        post_object: Union["MedAllergyAidHistoryModel", User],
        ckddetail: bool,
        goutdetail: bool,
        dateofbirth: Union["DateOfBirthForm", "DateOfBirth", None],
        gender: Union["GenderForm", "Gender", None],
    ) -> tuple[
        list["MedHistory"],
        list["MedHistory"],
        list["CkdDetailForm", BaselineCreatinine, "GoutDetailForm"],
        list[CkdDetail, BaselineCreatinine, None],
        bool,
    ]:
        post_qs_target = self.post_get_qs_target(post_object)
        mhs_2_save: list["MedHistory"] = []
        mhs_2_remove: list["MedHistory"] = []
        mhdets_2_save: list["CkdDetailForm" | BaselineCreatinine] = []
        mhdets_2_remove: list[CkdDetail | BaselineCreatinine | None] = []
        errors = False
        # Create medhistory_qs attribute on the form instance if it doesn't exist
        get_or_create_qs_attr(post_qs_target, "medhistory")
        for mh_form_str, mh_form in mh_forms.items():
            mhtype = MedHistoryTypes(mh_form_str.split("_")[0])
            mh_obj = (
                medhistorys_get(self.query_object.medhistorys_qs, mhtype, null_return=None)
                if self.query_object
                else None
            )
            if self.mh_clean_data(mhtype, mh_form.cleaned_data):
                if mh_obj:
                    mh_to_include = mh_obj
                else:
                    mh_to_include = mh_form.save(commit=False)
                    self.add_mh_to_qs(mh=mh_to_include, qs=mhs_2_save)
                self.add_mh_to_qs(mh=mh_to_include, qs=post_qs_target.medhistorys_qs)
                if mhtype == MedHistoryTypes.CKD and ckddetail:
                    ckddetail_errors = self.ckddetail_mh_post_process(
                        ckd=mh_to_include,
                        mh_det_forms=mh_det_forms,
                        dateofbirth=dateofbirth if dateofbirth else self.query_object.dateofbirth,
                        gender=gender if gender else self.query_object.gender,
                        mhd_to_save=mhdets_2_save,
                        mhd_to_remove=mhdets_2_remove,
                    )
                    if ckddetail_errors:
                        errors = True
                elif mhtype == MedHistoryTypes.GOUT and goutdetail:
                    self.goutdetail_mh_post_process(
                        gout=mh_to_include,
                        mh_det_forms=mh_det_forms,
                        mhd_to_save=mhdets_2_save,
                    )
            elif mh_obj:
                mhs_2_remove.append(mh_obj)
                self.post_remove_mh_from_medhistorys_qs(post_qs_target, mh_obj)
        # Iterate over the forms in the MedHistoryDetail form dict and,
        # if their associated MedHistory is not present in the MedHistory form dict
        # then it still needs to be processed
        for form in mh_det_forms.values():
            mhtype = form._meta.model.medhistorytype()  # pylint: disable=W0212
            if f"{mhtype}_form" not in mh_forms:
                if mhtype == MedHistoryTypes.GOUT and goutdetail:
                    self.goutdetail_mh_post_process(
                        gout=getattr(self.query_object, "gout", None),
                        mh_det_forms=mh_det_forms,
                        mhd_to_save=mhdets_2_save,
                    )
                elif mhtype == MedHistoryTypes.CKD and ckddetail:
                    ckddetail_errors = self.ckddetail_mh_post_process(
                        ckd=mh_to_include,
                        mh_det_forms=mh_det_forms,
                        dateofbirth=dateofbirth if dateofbirth else self.query_object.dateofbirth,
                        gender=gender if gender else self.query_object.gender,
                        mhd_to_save=mhdets_2_save,
                        mhd_to_remove=mhdets_2_remove,
                    )
                    if ckddetail_errors:
                        errors = True
        return (
            mhs_2_save,
            mhs_2_remove,
            mhdets_2_save,
            mhdets_2_remove,
            errors,
        )

    def post_remove_mh_from_medhistorys_qs(
        self,
        post_qs_target: Union["MedAllergyAidHistoryModel", User],
        mh_obj: "MedHistory",
    ) -> None:
        if post_qs_target == self.query_object:
            post_qs_target.medhistorys_qs.remove(mh_obj)
        else:
            self.query_object.medhistorys_qs.remove(mh_obj)

    def render_errors(
        self,
        form: ModelForm,
        oto_forms: dict | None,
        mh_forms: dict | None,
        mh_det_forms: dict | None,
        ma_forms: dict | None,
        lab_formsets: dict[str, "BaseModelFormSet"] | None,
    ) -> "HttpResponse":
        """To shorten code for rendering forms with errors in multiple
        locations in post()."""
        return self.render_to_response(
            self.get_context_data(
                form=form,
                **oto_forms if oto_forms else {},
                **mh_forms if mh_forms else {},
                **mh_det_forms if mh_det_forms else {},
                **ma_forms if ma_forms else {},
                **{f"{lab}_formset": formset for lab, formset in lab_formsets.items()} if lab_formsets else {},
                **{f"{lab}_formset_helper": lab_tup[1] for lab, lab_tup in self.labs.items()} if self.labs else {},
            )
        )


class GoutHelperUserDetailMixin(PatientSessionMixin):
    @cached_property
    def user(self) -> User | None:
        return self.object if isinstance(self.object, User) else getattr(self.object, "user", None)


class GoutHelperUserEditMixin(GoutHelperAidEditMixin):
    """Overwritten to modify related models around a User, rather than
    a GoutHelper DecisionAid or TreatmentAid object. Also to create a user."""

    def form_valid(
        self,
        form,
        oto_2_save: list["Model"] | None,
        oto_2_rem: list["Model"] | None,
        mh_2_save: list["MedHistory"] | None,
        mh_2_rem: list["MedHistory"] | None,
        mh_det_2_save: list["CkdDetailForm", "BaselineCreatinine", "GoutDetailForm"] | None,
        mh_det_2_rem: list["CkdDetailForm", "BaselineCreatinine", "GoutDetailForm"] | None,
        ma_2_save: list["MedAllergy"] | None,
        ma_2_rem: list["MedAllergy"] | None,
        labs_2_save: list["Lab"] | None,
        labs_2_rem: list["Lab"] | None,
        **kwargs,
    ) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Overwritten to facilitate creating Users."""
        if self.create_view:  # pylint: disable=W0125
            form.instance.username = uuid.uuid4().hex[:30]
            self.object = form.save()
        # Save the OneToOne related models
        if self.onetoones:
            if oto_2_save:
                for oto in oto_2_save:
                    if oto.user is None:
                        oto.user = self.object
                    oto.save()
            if oto_2_rem:
                for oto in oto_2_rem:
                    oto.delete()
        if self.medhistorys:
            if mh_2_save:
                for mh in mh_2_save:
                    if mh.user is None:
                        mh.user = self.object
                    mh.save()
            if mh_det_2_save:
                for mh_det in mh_det_2_save:
                    if self.create_view and isinstance(mh_det, GoutDetail):
                        mh_det.medhistory = Gout.objects.create(user=self.object)
                    mh_det.save()
            if mh_2_rem:
                for mh in mh_2_rem:
                    mh.delete()
            if mh_det_2_rem:
                for mh_det in mh_det_2_rem:
                    mh_det.instance.delete()
        if self.medallergys:
            if ma_2_save:
                for ma in ma_2_save:
                    if ma.user is None:
                        ma.user = self.object
                    ma.save()
            if ma_2_rem:
                for ma in ma_2_rem:
                    ma.delete()
        if self.labs:
            if labs_2_save:
                # Modify and remove labs from the object
                for lab in labs_2_save:
                    if lab.user is None:
                        lab.user = self.object
                    lab.save()
            if labs_2_rem:
                for lab in labs_2_rem:
                    lab.delete()
        if self.create_view:  # pylint: disable=W0125
            # Create a PseudopatientProfile for the Pseudopatient
            PseudopatientProfile.objects.create(
                user=self.object,
                provider=self.request.user if self.provider else None,  # pylint: disable=W0125
            )
        return HttpResponseRedirect(self.get_success_url())

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Provider the view is trying to create
        a Pseudopatient for."""
        if self.create_view:  # pylint: disable=W0125
            return self.provider
        else:
            return self.object

    def goutdetail_mh_context(
        self,
        kwargs: dict[str, Any],
        mh_dets: dict[MedHistoryTypes, ModelForm],
        mh_obj: Union["MedHistory", User, None] = None,
        patient: Pseudopatient | None = None,
        request_user: User | None = None,
        str_attrs: dict[str, str] = None,
    ) -> None:
        """Overwritten to always raise Continue, which will skip adding the GoutForm to the context."""
        if "goutdetail_form" not in kwargs:
            goutdetail_i = getattr(mh_obj, "goutdetail", None) if mh_obj else None
            kwargs["goutdetail_form"] = mh_dets[MedHistoryTypes.GOUT](
                instance=goutdetail_i,
                patient=patient,
                request_user=request_user,
                str_attrs=str_attrs,
            )
            raise Continue

    def goutdetail_mh_post_pop(
        self,
        gout: Union["MedHistory", None],
        mh_det_forms: dict[str, ModelForm],
        mh_dets: dict[MedHistoryTypes, ModelForm],
        request: "HttpRequest",
        patient: Pseudopatient | None = None,
        request_user: User | None = None,
        str_attrs: dict[str, str] = None,
    ) -> None:
        """Overwritten to always raise Continue, which will skip adding the GoutForm to the context."""
        if gout:
            gd = getattr(gout, "goutdetail", None)
        else:
            gd = GoutDetail()
        mh_det_forms.update(
            {
                "goutdetail_form": mh_dets[MedHistoryTypes.GOUT](
                    request.POST, instance=gd, str_attrs=str_attrs, patient=patient, request_user=request_user
                )
            }
        )
        raise Continue

    @cached_property
    def provider(self) -> str | None:
        """Method that returns the username kwarg from the url."""
        return self.kwargs.get("username", None)

    @cached_property
    def user(self) -> None:
        return None
