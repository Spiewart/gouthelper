import uuid
from typing import TYPE_CHECKING, Any, Literal, Union

from django.contrib import messages  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from django.core.exceptions import ValidationError  # type: ignore
from django.db.models import Model  # type: ignore
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

    from crispy_forms.helper import FormHelper  # type: ignore
    from django.db.models import QuerySet  # type: ignore
    from django.forms import BaseModelFormSet, ModelForm  # type: ignore
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


class GoutHelperAidEditMixin(PatientSessionMixin):
    onetoones: dict[str, "FormModelDict"] = {}
    req_otos: list[str] = []
    medallergys: type["FlarePpxChoices"] | type["UltChoices"] | type["Treatments"] | list = []
    medhistorys: dict[MedHistoryTypes, "FormModelDict"] = {}
    medhistory_details: dict[MedHistoryTypes, "ModelForm"] = {}
    labs: dict[Literal["urate"], tuple[type["BaseModelFormSet"], type["FormHelper"], "QuerySet"]] | None = None

    def add_mh_to_qs(self, mh: "MedHistory", qs: list["MedHistory"], check: bool = True) -> None:
        """Method to add a MedHistory to a list of MedHistories."""
        if not check or mh not in qs:
            qs.append(mh)

    def baselinecreatinine_form_post_process(
        self,
        baselinecreatinine_form: "ModelForm",
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
        ckddetail_form: "ModelForm",
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
        mh_dets: dict[MedHistoryTypes, "ModelForm"],
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
        mh_det_forms: dict[str, "ModelForm"],
        mh_dets: dict[MedHistoryTypes, "ModelForm"],
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
        mh_det_forms: dict[str, "ModelForm"],
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

    def context_labs(
        self,
        labs: dict[str, tuple[type["BaseModelFormSet"], type["FormHelper"], "QuerySet"]],
        query_object: Union["MedAllergyAidHistoryModel", User, None],
        kwargs: dict,
        patient: Pseudopatient | None = None,
        request_user: User | None = None,
        str_attrs: dict[str, str] = None,
    ) -> None:
        """Method adds a formset of labs to the context. Uses a QuerySet that takes a query_object
        as an arg to populate existing Lab objects."""
        query_obj_attr = (
            query_object.__class__.__name__.lower()
            if query_object and not isinstance(query_object, User)
            else "user"
            if query_object
            else None
        )
        for lab, lab_tup in labs.items():
            if f"{lab}_formset" not in kwargs:
                if query_obj_attr:
                    kwargs[f"{lab}_formset"] = lab_tup[0](
                        queryset=getattr(self, f"{lab}_formset_qs").filter(**{query_obj_attr: query_object}),
                        prefix=lab,
                        form_kwargs={"patient": patient, "request_user": request_user, "str_attrs": str_attrs},
                    )
                else:
                    kwargs[f"{lab}_formset"] = lab_tup[0](
                        queryset=getattr(self, f"{lab}_formset_qs").none(),
                        prefix=lab,
                        form_kwargs={"patient": patient, "request_user": request_user, "str_attrs": str_attrs},
                    )
            if f"{lab}_formset_helper" not in kwargs:
                kwargs[f"{lab}_formset_helper"] = lab_tup[1]
        # TODO: Rewrite BaseModelFormset to take a list of objects rather than a QuerySet

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
        mh_dets: dict[MedHistoryTypes, "ModelForm"],
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

    def context_onetoones(
        self,
        onetoones: dict[str, "FormModelDict"],
        req_otos: list[str],
        kwargs: dict,
        query_object: Union["MedAllergyAidHistoryModel", User, None],
        patient: Pseudopatient | None = None,
        request_user: User | None = None,
        str_attrs: dict[str, str] = None,
    ) -> None:
        """Method to populate the kwargs dict with forms for the objects's related 1to1 models. For
        required one to one objects, the value is set as a kwarg for the context."""
        for onetoone, onetoone_dict in onetoones.items():
            if self.related_object and getattr(self.related_object, onetoone) and onetoone not in kwargs:
                if onetoone == "dateofbirth":
                    kwargs["age"] = age_calc(getattr(query_object, onetoone).value)
                else:
                    kwargs[onetoone] = getattr(query_object, onetoone).value
            else:
                form_str = f"{onetoone}_form"
                oto_obj = self.get_oto_obj(query_object, onetoone, self.object) if query_object else None
                if form_str not in kwargs:
                    if onetoone == "dateofbirth":
                        kwargs[form_str] = onetoone_dict["form"](
                            instance=oto_obj if oto_obj else onetoone_dict["model"](),
                            initial={"value": age_calc(oto_obj.value) if oto_obj else None},
                            patient=patient,
                            request_user=request_user,
                            str_attrs=str_attrs,
                        )
                    else:
                        # Add the form to the context with a new instance of the related model
                        kwargs[form_str] = onetoone_dict["form"](
                            instance=oto_obj if oto_obj else onetoone_dict["model"](),
                            initial={"value": oto_obj.value if oto_obj else None},
                            patient=patient,
                            request_user=request_user,
                            str_attrs=str_attrs,
                        )
        # Add the required one to one objects to the context
        for onetoone in req_otos:
            if onetoone not in kwargs:
                # If the one to one is a dateofbirth, calculate the age and add it to the context
                if onetoone == "dateofbirth":
                    kwargs["age"] = age_calc(getattr(query_object, onetoone).value)
                else:
                    kwargs[onetoone] = getattr(query_object, onetoone).value

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
            related_model_name = self.related_object._meta.model_name
            if self.create_view and getattr(self.related_object, self.model_name.lower(), None):
                messages.error(
                    request, f"{self.related_object} already has a {self.model_name}. Please update it instead."
                )
                return HttpResponseRedirect(
                    reverse(
                        f"{self.model_name.lower()}s:{related_model_name}-update",
                        kwargs={"pk": getattr(self.related_object, self.model_name.lower()).pk},
                    )
                )
        return super().dispatch(request, *args, **kwargs)

    def form_valid_save_otos(
        self,
        oto_2_save: list[Model] | None,
        form: "ModelForm",
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
                    if not self.user or oto_attr == "urate":
                        setattr(form.instance, oto_attr, oto)

    def form_valid_related_object_otos(
        self,
        form: "ModelForm",
        onetoones: dict[str, "FormModelDict"],
        related_object: "MedAllergyAidHistoryModel",
    ):
        for oto_attr in onetoones.keys():
            related_object_oto = getattr(related_object, oto_attr, None)
            if related_object_oto and getattr(form.instance, oto_attr, None) is None:
                setattr(form.instance, oto_attr, related_object_oto)

    def form_valid_delete_otos(self, oto_2_rem: list[Model] | None, form: "ModelForm") -> None:
        """Method to delete the OneToOne related models. Related fields for the OneToOne are
        set based on the User-status of the view, as are attributes of the view's object."""
        if oto_2_rem:
            for oto in oto_2_rem:
                if not self.user or oto.__class__.__name__.lower() == "urate":
                    setattr(form.instance, f"{oto.__class__.__name__.lower()}", None)
                oto.delete()

    def form_valid(
        self,
        form,
        oto_2_save: list[Model] | None,
        oto_2_rem: list[Model] | None,
        mh_2_save: list["MedHistory"] | None,
        mh_2_rem: list["MedHistory"] | None,
        mh_det_2_save: list["CkdDetailForm", BaselineCreatinine, "GoutDetailForm"] | None,
        mh_det_2_rem: list["CkdDetailForm", BaselineCreatinine, "GoutDetailForm"] | None,
        ma_2_save: list["MedAllergy"] | None,
        ma_2_rem: list["MedAllergy"] | None,
        labs_2_save: list["Lab"] | None,
        labs_2_rem: list["Lab"] | None,
        **kwargs,
    ) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Method to be called if all forms are valid."""
        if isinstance(form.instance, User):
            self.user = form.save()
            save_aid_obj = False
        elif (
            form.has_changed
            or self.onetoones
            and (oto_2_save or oto_2_rem)
            or self.user
            and form.instance.user is None
            or self.create_view
        ):
            aid_obj = form.save(commit=False)
            save_aid_obj = True
        else:
            aid_obj = form.instance
            save_aid_obj = False
        if self.user and aid_obj.user is None:
            aid_obj.user = self.user
        # Save the OneToOne related models
        if self.onetoones:
            self.form_valid_save_otos(oto_2_save, form)
            self.form_valid_delete_otos(oto_2_rem, form)
            if self.related_object:
                self.form_valid_related_object_otos(
                    form=form,
                    onetoones=self.onetoones,
                    related_object=self.related_object,
                )
        if kwargs:
            for key, val in kwargs.items():
                if (
                    isinstance(val, Model)
                    and key in [field.name for field in aid_obj._meta.fields]
                    and getattr(aid_obj, key, None) is None
                ):
                    setattr(aid_obj, key, val)
                    if save_aid_obj is not True:
                        save_aid_obj = True
        if save_aid_obj:
            aid_obj.save()
        aid_obj_attr = aid_obj._meta.model_name
        if kwargs:
            for key, val in kwargs.items():
                if (
                    isinstance(val, Model)
                    and aid_obj_attr in [field.name for field in val._meta.fields]
                    and getattr(val, aid_obj_attr, None) is None
                ):
                    setattr(val, aid_obj_attr, aid_obj)
                    val.full_clean()
                    val.save()
        if self.medallergys:
            if ma_2_save:
                for ma in ma_2_save:
                    if self.user:
                        if ma.user is None:
                            ma.user = self.user
                    else:
                        if getattr(ma, aid_obj_attr, None) is None:
                            setattr(ma, aid_obj_attr, aid_obj)
                    ma.save()
            if ma_2_rem:
                for ma in ma_2_rem:
                    ma.delete()
        if self.medhistorys:
            if mh_2_save:
                for mh in mh_2_save:
                    if self.user:
                        if mh.user is None:
                            mh.user = self.user
                    else:
                        if getattr(mh, aid_obj_attr, None) is None:
                            setattr(mh, aid_obj_attr, aid_obj)
                    mh.save()
            if mh_det_2_save:
                for mh_det in mh_det_2_save:
                    mh_det.save()
            if mh_2_rem:
                for mh in mh_2_rem:
                    mh.delete()
            if mh_det_2_rem:
                for mh_det in mh_det_2_rem:
                    mh_det.instance.delete()
        if self.labs:
            if labs_2_save:
                # Modify and remove labs from the object
                for lab in labs_2_save:
                    if self.user:
                        if lab.user is None:
                            lab.user = self.user
                    elif not self.user and getattr(lab, aid_obj_attr, None) is None:
                        setattr(lab, aid_obj_attr, aid_obj)
                    lab.save()
            if labs_2_rem:
                for lab in labs_2_rem:
                    lab.delete()
        if self.user:
            setattr(self.user, f"{aid_obj_attr}_qs", aid_obj)
            aid_obj.update_aid(qs=self.user)
        else:
            aid_obj.update_aid(qs=aid_obj)
        messages.success(self.request, self.get_success_message(form.cleaned_data))
        if self.request.htmx:
            return kwargs.get("htmx")
        return HttpResponseRedirect(self.get_success_url())

    def get(self, request, *args, **kwargs):
        """Overwritten to not call get_object()."""
        return self.render_to_response(self.get_context_data())

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        if self.onetoones or self.req_otos:
            self.context_onetoones(
                onetoones=self.onetoones,
                req_otos=self.req_otos,
                kwargs=kwargs,
                query_object=self.query_object,
                patient=self.user,
                request_user=self.request.user,
                str_attrs=self.str_attrs,
            )
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
                query_object=self.query_object,
                kwargs=kwargs,
                patient=self.user,
                request_user=self.request.user,
                str_attrs=self.str_attrs,
            )
        if "patient" not in kwargs and self.user:
            kwargs["patient"] = self.user
        kwargs.update({"str_attrs": self.str_attrs})
        return super().get_context_data(**kwargs)

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        if self.medallergys:
            kwargs["medallergys"] = self.medallergys
        kwargs.update({"patient": self.user, "request_user": self.request.user, "str_attrs": self.str_attrs})
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

    def get_oto_obj(
        self,
        query_object: Union["MedAllergyAidHistoryModel", User, None],
        oto: str,
        alt_obj: Model = None,
    ) -> Model:
        """Method that looks looks for a 1to1 related object on the query_object and returns it if found.
        If it's not, if the oto str is "urate", it looks for the 1to1 on the alt_obj and returns it if found."""
        oto_obj = getattr(query_object, oto, None) if query_object else None
        if not oto_obj and oto == "urate":
            oto_obj = getattr(alt_obj, "urate", None) if alt_obj else None
        return oto_obj

    def get_permission_object(self):
        """Returns the view's object, which will have already been set by dispatch()."""
        return self.object if not self.create_view else self.user if self.user else None

    def get_success_url(self):
        """Overwritten to take optional next parameter from url"""
        next_url = self.request.POST.get("next", None)
        print(next_url)
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
        mh_dets: dict[MedHistoryTypes, "ModelForm"],
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
        mh_det_forms: dict[str, "ModelForm"],
        mh_dets: dict[MedHistoryTypes, "ModelForm"],
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
        mh_det_forms: dict[str, "ModelForm"],
        mhd_to_save: list["CkdDetail", "GoutDetail", BaselineCreatinine],
    ) -> None:
        """Method that processes the GoutDetailForm as part of the post() method."""

        gd_form = mh_det_forms["goutdetail_form"]
        gd_mh = getattr(gd_form.instance, "medhistory", None)
        if (
            "flaring" in gd_form.changed_data
            or "hyperuricemic" in gd_form.changed_data
            or "on_ppx" in gd_form.changed_data
            or "on_ult" in gd_form.changed_data
            or not gd_mh
        ):
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
        # user and object attrs are set by the dispatch() method on the child class
        form_class = self.get_form_class()
        form = form_class(
            **self.get_form_kwargs(),
        )
        # Populate dicts for related models with POST data
        oto_forms = self.post_populate_oto_forms(
            onetoones=self.onetoones,
            request=request,
            patient=self.user,
            request_user=self.request.user,
            str_attrs=self.str_attrs,
        )
        ma_forms = self.post_populate_ma_forms(
            medallergys=self.medallergys,
            request=request,
            patient=self.user,
            request_user=self.request.user,
            str_attrs=self.str_attrs,
        )
        mh_forms, mh_det_forms = self.post_populate_mh_forms(
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
        lab_formsets = self.post_populate_labformsets(
            request=request,
            labs=self.labs,
            patient=self.user,
            request_user=self.request.user,
            str_attrs=self.str_attrs,
        )
        form_is_valid = form.is_valid()
        oto_forms_is_valid = validate_form_list(form_list=oto_forms.values()) if oto_forms else True
        ma_forms_is_valid = validate_form_list(form_list=ma_forms.values()) if ma_forms else True
        mh_forms_is_valid = validate_form_list(form_list=mh_forms.values()) if mh_forms else True
        mh_det_forms_is_valid = validate_form_list(form_list=mh_det_forms.values()) if mh_det_forms else True
        lab_formsets_is_valid = validate_formset_list(formset_list=lab_formsets.values()) if lab_formsets else True
        if (
            form_is_valid
            and oto_forms_is_valid
            and ma_forms_is_valid
            and mh_forms_is_valid
            and mh_det_forms_is_valid
            and lab_formsets_is_valid
        ):
            errors_bool = False
            form.save(commit=False)
            # Set related models for saving and set as attrs of the UpdateView model instance
            oto_2_save, oto_2_rem = self.post_process_oto_forms(
                oto_forms=oto_forms,
                req_otos=self.req_otos,
            )
            ma_2_save, ma_2_rem = self.post_process_ma_forms(
                ma_forms=ma_forms,
                post_object=form.instance,
            )
            (
                mh_2_save,
                mh_2_rem,
                mh_det_2_save,
                mh_det_2_rem,
                errors_bool,
            ) = self.post_process_mh_forms(
                mh_forms=mh_forms,
                mh_det_forms=mh_det_forms,
                post_object=form.instance,
                ckddetail=self.ckddetail,
                goutdetail=self.goutdetail,
                dateofbirth=oto_forms.get("dateofbirth_form", None) if oto_forms else None,
                gender=oto_forms.get("gender_form") if oto_forms else None,
            )
            (
                labs_2_save,
                labs_2_rem,
            ) = self.post_process_lab_formsets(
                lab_formsets=lab_formsets,
                post_object=form.instance,
            )
            # If there are errors picked up after the initial validation step
            # render the errors as errors and include in the return tuple
            errors = (
                self.render_errors(
                    form=form,
                    oto_forms=oto_forms if oto_forms else None,
                    ma_forms=ma_forms if ma_forms else None,
                    mh_forms=mh_forms if mh_forms else None,
                    mh_det_forms=mh_det_forms if mh_det_forms else None,
                    lab_formsets=lab_formsets if lab_formsets else None,
                    labs=self.labs if hasattr(self, "labs") else None,
                )
                if errors_bool
                else None
            )
            return (
                errors,
                form,
                oto_forms if oto_forms else None,
                mh_forms if mh_forms else None,
                mh_det_forms if mh_det_forms else None,
                ma_forms if ma_forms else None,
                lab_formsets if self.labs else None,
                oto_2_save if oto_2_save else None,
                oto_2_rem if oto_2_rem else None,
                mh_2_save if mh_2_save else None,
                mh_2_rem if mh_2_rem else None,
                mh_det_2_save if mh_det_2_save else None,
                mh_det_2_rem if mh_det_2_rem else None,
                ma_2_save if ma_2_save else None,
                ma_2_rem if ma_2_rem else None,
                labs_2_save if labs_2_save else None,
                labs_2_rem if labs_2_rem else None,
            )
        else:
            # If all the forms aren't valid unpack the related model form dicts into the context
            # and return the UpdateView with the invalid forms
            errors = self.render_errors(
                form=form,
                oto_forms=oto_forms if oto_forms else None,
                ma_forms=ma_forms if ma_forms else None,
                mh_forms=mh_forms if mh_forms else None,
                mh_det_forms=mh_det_forms if mh_det_forms else None,
                lab_formsets=lab_formsets if lab_formsets else None,
                labs=self.labs if hasattr(self, "labs") else None,
            )
            return (
                errors,
                form,
                oto_forms if oto_forms else None,
                mh_forms if mh_forms else None,
                mh_det_forms if mh_det_forms else None,
                ma_forms if ma_forms else None,
                lab_formsets if lab_formsets else None,
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
        patient: Pseudopatient | None = None,
        request_user: User | None = None,
        str_attrs: dict[str, str] = None,
    ) -> dict[str, "BaseModelFormSet"] | None:
        """Method to populate a dict of lab forms with POST data in the post() method."""
        if labs:
            query_obj_attr = (
                self.query_object.__class__.__name__.lower()
                if self.query_object and not isinstance(self.query_object, User)
                else "user"
                if self.query_object
                else None
            )
            lab_formsets = {}
            for lab, lab_tup in labs.items():
                if query_obj_attr:
                    lab_formsets.update(
                        {
                            lab: lab_tup[0](
                                request.POST,
                                queryset=getattr(self, f"{lab}_formset_qs").filter(
                                    **{query_obj_attr: self.query_object}
                                ),
                                prefix=lab,
                                form_kwargs={
                                    "patient": patient,
                                    "request_user": request_user,
                                    "str_attrs": str_attrs,
                                },
                            )
                        }
                    )
                else:
                    lab_formsets.update(
                        {
                            lab: lab_tup[0](
                                request.POST,
                                queryset=getattr(self, f"{lab}_formset_qs").none(),
                                prefix=lab,
                                form_kwargs={
                                    "patient": patient,
                                    "request_user": request_user,
                                    "str_attrs": str_attrs,
                                },
                            )
                        }
                    )
            return lab_formsets
        else:
            return None

    def post_populate_ma_forms(
        self,
        medallergys: None | type["FlarePpxChoices"] | type["UltChoices"] | type["Treatments"],
        request: "HttpRequest",
        patient: Pseudopatient | None = None,
        request_user: User | None = None,
        str_attrs: dict[str, str] = None,
    ) -> dict[str, "ModelForm"]:
        """Method to populate the forms for the MedAllergys for the post() method."""
        ma_forms: dict[str, "ModelForm"] = {}
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
        mh_dets: dict[MedHistoryTypes, "ModelForm"],
        request: "HttpRequest",
        ckddetail: bool,
        goutdetail: bool,
        create: bool = False,
        patient: Pseudopatient | None = None,
        request_user: User | None = None,
        str_attrs: dict[str, str] = None,
    ) -> tuple[dict[str, "ModelForm"], dict[str, "ModelForm"]]:
        """Populates forms for MedHistory and MedHistoryDetail objects in post() method."""
        mh_forms: dict[str, "ModelForm"] = {}
        mh_det_forms: dict[str, "ModelForm"] = {}
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

    def post_populate_oto_forms(
        self,
        onetoones: dict[str, "FormModelDict"],
        request: "HttpRequest",
        patient: Pseudopatient | None = None,
        request_user: User | None = None,
        str_attrs: dict[str, str] = None,
    ) -> dict[str, "ModelForm"]:
        """Method that populates a dict of OneToOne related model forms with POST data
        in the post() method."""
        oto_forms: dict[str, "ModelForm"] = {}
        if onetoones:
            for onetoone in onetoones:
                if not self.related_object or (self.related_object and not getattr(self.related_object, onetoone)):
                    oto_obj = self.get_oto_obj(self.query_object, onetoone, self.object) if self.query_object else None
                    oto_forms.update(
                        {
                            f"{onetoone}_form": onetoones[onetoone]["form"](
                                request.POST,
                                instance=oto_obj if oto_obj else onetoones[onetoone]["model"](),
                                patient=patient,
                                request_user=request_user,
                                str_attrs=str_attrs,
                            )
                        }
                    )
        return oto_forms

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
        # Assign lists to return
        labs_2_save: list["Lab"] = []
        labs_2_rem: list["Lab"] = []

        if lab_formsets:
            post_obj_attr = (
                f"{post_object.__class__.__name__.lower()}" if not isinstance(post_object, User) else "user"
            )
            for lab_name, lab_formset in lab_formsets.items():
                qs_attr = get_or_create_qs_attr(post_object, lab_name)
                if qs_attr:
                    cleaned_data = lab_formset.cleaned_data
                    # NOTE: FOR FUTURE SELF: COPY A LIST WHEN ITERATING OVER IT AND ADDING/REMOVING ELEMENTS
                    for lab in qs_attr.copy():
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
                                        if getattr(lab, post_obj_attr, None) is None:
                                            if not self.user:
                                                setattr(lab, post_obj_attr, post_object)
                                            labs_2_save.append(lab)
                                        # If so, break out of the loop
                                        break
                                    # If it is marked for deletion, it will be removed by the formset loop below
                            except KeyError:
                                pass
                        else:
                            # If not, add the lab to the labs_2_rem list
                            labs_2_rem.append(lab)
                            qs_attr.remove(lab)
                # Iterate over the forms in the formset
                for form in lab_formset:
                    # Check if the form has a value in the "value" field
                    if "value" in form.cleaned_data and not form.cleaned_data["DELETE"]:
                        # Check if the form has an instance and the form has changed
                        if getattr(form.instance, post_obj_attr, None) is None and not self.user:
                            setattr(form.instance, post_obj_attr, post_object)
                            labs_2_save.append(form.instance)
                        elif (form.instance and form.has_changed()) or form.instance is None:
                            labs_2_save.append(form.instance)
                        # Add the lab to the form instance's labs_qs if it's not already there
                        if form.instance not in qs_attr:
                            qs_attr.append(form.instance)
        return labs_2_save, labs_2_rem

    def post_process_ma_forms(
        self,
        ma_forms: dict[str, "ModelForm"],
        post_object: Union["MedAllergyAidHistoryModel", User, None],
    ) -> tuple[list["MedAllergy"], list["MedAllergy"]]:
        ma_2_save: list["MedAllergy"] = []
        ma_2_rem: list["MedAllergy"] = []
        get_or_create_qs_attr(post_object, "medallergy")
        for ma_form_str in ma_forms:
            treatment = ma_form_str.split("_")[1]
            if f"medallergy_{treatment}" in ma_forms[ma_form_str].cleaned_data:
                ma_obj = next(
                    iter([ma for ma in getattr(post_object, "medallergys_qs", []) if ma.treatment == treatment]), None
                )
                if ma_obj and not ma_forms[ma_form_str].cleaned_data[f"medallergy_{treatment}"]:
                    ma_2_rem.append(ma_obj)
                    getattr(post_object, "medallergys_qs", []).remove(ma_obj)
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
                            if ma not in getattr(post_object, "medallergys_qs", []):
                                getattr(post_object, "medallergys_qs", []).append(ma)
                        else:
                            if ma_obj.matype != ma_forms[ma_form_str].cleaned_data[f"{treatment}_matype"]:
                                ma_obj.matype = ma_forms[ma_form_str].cleaned_data[f"{treatment}_matype"]
                                ma_2_save.append(ma_obj)
                            # Add the medallergy to the form instance's medallergys_qs if it's not already there
                            if ma_obj not in getattr(post_object, "medallergys_qs", []):
                                getattr(post_object, "medallergys_qs", []).append(ma_obj)
        return ma_2_save, ma_2_rem

    def post_process_menopause(
        self,
        mh_forms: dict[str, "ModelForm"],
        post_object: Union["MedAllergyAidHistoryModel", None] = None,
        gender: Genders | None = None,
        dateofbirth: Union["date", None] = None,
        errors_bool: bool = False,
    ) -> tuple[dict[str, "ModelForm"], bool]:
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
        mh_forms: dict[str, "ModelForm"],
        mh_det_forms: dict[str, "ModelForm"],
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
        mhs_2_save: list["MedHistory"] = []
        mhs_2_remove: list["MedHistory"] = []
        mhdets_2_save: list["CkdDetailForm" | BaselineCreatinine] = []
        mhdets_2_remove: list[CkdDetail | BaselineCreatinine | None] = []
        errors = False
        # Create medhistory_qs attribute on the form instance if it doesn't exist
        get_or_create_qs_attr(post_object, "medhistory")
        for mh_form_str, mh_form in mh_forms.items():
            mhtype = MedHistoryTypes(mh_form_str.split("_")[0])
            mh_obj = medhistorys_get(post_object.medhistorys_qs, mhtype, null_return=None)
            if self.mh_clean_data(mhtype, mh_form.cleaned_data):
                if mh_obj:
                    mh_to_include = mh_obj
                else:
                    mh_to_include = mh_form.save(commit=False)
                    self.add_mh_to_qs(mh=mh_to_include, qs=mhs_2_save)
                self.add_mh_to_qs(mh=mh_to_include, qs=post_object.medhistorys_qs)
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
                post_object.medhistorys_qs.remove(mh_obj)
        # Iterate over the forms in the MedHistoryDetail form dict and,
        # if their associated MedHistory is not present in the MedHistory form dict
        # then it still needs to be processed
        for form in mh_det_forms.values():
            mhtype = form._meta.model.medhistorytype()  # pylint: disable=W0212
            if f"{mhtype}_form" not in mh_forms:
                if mhtype == MedHistoryTypes.GOUT and goutdetail:
                    self.goutdetail_mh_post_process(
                        gout=post_object.gout if not (self.create_view and isinstance(post_object, User)) else None,
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

    def post_process_oto_forms(
        self,
        oto_forms: dict[str, "ModelForm"],
        req_otos: list[str],
    ) -> tuple[list[Model], list[Model]]:
        """Method to process the forms for the OneToOne objects for the post() method."""
        oto_2_save: list[Model] = []
        oto_2_rem: list[Model] = []
        for oto_form_str, oto_form in oto_forms.items():
            object_attr = oto_form_str.split("_")[0]
            if object_attr not in req_otos and (
                not self.related_object or (self.related_object and not getattr(self.related_object, "object_attr"))
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

    @cached_property
    def query_object(self) -> Union["MedAllergyAidHistoryModel", User, None]:
        return (
            self.user if self.user else self.object if not self.create_view else getattr(self, "related_object", None)
        )

    @cached_property
    def related_object(self) -> Any:
        """Meant to defualt to None, but can be overwritten in child views."""
        return None

    def render_errors(
        self,
        form: "ModelForm",
        oto_forms: dict | None,
        mh_forms: dict | None,
        mh_det_forms: dict | None,
        ma_forms: dict | None,
        lab_formsets: dict[str, "BaseModelFormSet"] | None,
        labs: dict[Literal["urate"], tuple["BaseModelFormSet", "FormHelper", "QuerySet"]] | None,
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
                **{f"{lab}_formset_helper": lab_tup[1] for lab, lab_tup in labs.items()} if labs else {},
            )
        )

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
        mh_dets: dict[MedHistoryTypes, "ModelForm"],
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
        mh_det_forms: dict[str, "ModelForm"],
        mh_dets: dict[MedHistoryTypes, "ModelForm"],
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
