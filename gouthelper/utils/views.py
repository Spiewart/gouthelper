import uuid
from typing import TYPE_CHECKING, Any, Union

from django.contrib import messages  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from django.core.exceptions import ValidationError  # type: ignore
from django.db import transaction  # type: ignore
from django.db.models import Model  # type: ignore
from django.forms import ModelForm  # type: ignore
from django.http import HttpResponseRedirect  # type: ignore
from django.urls import reverse
from django.utils.functional import cached_property  # type: ignore
from django.views.generic import CreateView, DetailView
from rules.contrib.views import AutoPermissionRequiredMixin

from ..dateofbirths.helpers import age_calc
from ..genders.choices import Genders
from ..labs.models import BaselineCreatinine
from ..medallergys.models import MedAllergy
from ..medhistorydetails.models import CkdDetail, GoutDetail
from ..medhistorydetails.services import CkdDetailFormProcessor
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.dicts import MedHistoryTypesAids
from ..medhistorys.helpers import medhistorys_get, medhistorys_get_default_medhistorytype
from ..medhistorys.models import Gout
from ..profiles.helpers import get_provider_alias
from ..profiles.models import PseudopatientProfile
from ..users.choices import Roles
from ..users.models import Pseudopatient
from ..utils.exceptions import Continue, EmptyRelatedModel
from ..utils.helpers import (
    attr_is_in_model_fields,
    get_or_create_qs_attr,
    get_str_attrs,
    list_of_objects_related_objects,
    list_of_possible_related_object_attrs,
)

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.forms import BaseModelFormSet  # type: ignore
    from django.http import HttpRequest, HttpResponse  # type: ignore

    from ..akis.models import Aki
    from ..dateofbirths.forms import DateOfBirthForm
    from ..dateofbirths.models import DateOfBirth
    from ..genders.forms import GenderForm
    from ..genders.models import Gender
    from ..labs.models import Lab
    from ..medhistorydetails.forms import CkdDetailForm, GoutDetailForm
    from ..medhistorys.models import MedHistory
    from .types import Aids


User = get_user_model()


class PatientSessionMixin:
    """Mixin to add a session to a view."""

    def get_context_data(self, **kwargs):
        """Overwritten to add the patient to the session."""
        context = super().get_context_data(**kwargs)
        self.update_session_patient()
        return context

    def add_patient_to_session(self, patient: Pseudopatient | User) -> None:
        self.request.session.update({"patient": str(patient), "pk": str(patient.pk)})
        if not self.request.session.get("recent_patients", None):
            self.request.session["recent_patients"] = []
        if str(patient.pk) not in [recent_patient[1] for recent_patient in self.request.session["recent_patients"]]:
            self.request.session["recent_patients"].append(tuple([str(patient), str(patient.pk)]))
        elif str(patient.pk) != self.request.session["recent_patients"][0][1]:
            self.request.session["recent_patients"].remove(
                next(
                    iter(
                        [
                            recent_patient
                            for recent_patient in self.request.session["recent_patients"]
                            if recent_patient[1] == str(patient.pk)
                        ]
                    )
                )
            )
            self.request.session["recent_patients"].insert(0, tuple([str(patient), str(patient.pk)]))

    def remove_patient_from_session(
        self,
        patient: Pseudopatient | User,
        delete: bool = False,
    ) -> None:
        self.request.session.pop("patient", None)
        self.request.session.pop("pk", None)
        if (
            delete
            and self.request.session.get("recent_patients", None)
            and str(patient.pk) in [recent_patient[1] for recent_patient in self.request.session["recent_patients"]]
        ):
            self.request.session["recent_patients"].remove(
                next(
                    iter(
                        [
                            recent_patient
                            for recent_patient in self.request.session["recent_patients"]
                            if recent_patient[1] == str(patient.pk)
                        ]
                    )
                )
            )

    def update_session_patient(self) -> None:
        patient = getattr(self, "user", None)
        if patient:
            self.add_patient_to_session(patient)
        else:
            self.remove_patient_from_session(patient)


class GoutHelperDetailMixinBase(AutoPermissionRequiredMixin, DetailView, PatientSessionMixin):
    class Meta:
        abstract = True

    object: "Aids"
    user: User | None

    def get(self, request, *args, **kwargs):
        """Overwritten to avoid calling get_object again, which is instead
        called on dispatch()."""
        if not request.GET.get("updated", None):
            self.object.update_aid(qs=self.user if getattr(self, "user", False) else self.object)
            self.object.update_related_objects(qs=self.user if getattr(self, "user", False) else self.object)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"str_attrs": get_str_attrs(self.object, self.object.user, self.request.user)})
        return context

    def get_permission_object(self):
        return self.object

    def get_queryset(self) -> "QuerySet[Any]":
        return self.model.related_objects.filter(pk=self.kwargs["pk"])

    def update_objects(self):
        self.object.update_aid(qs=self.object)
        if self.object.flareaid:
            self.object.flareaid.update_aid(qs=self.object.flareaid)


class GoutHelperDetailMixin(GoutHelperDetailMixinBase):
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.user:
            return HttpResponseRedirect(self.object.get_absolute_url())
        else:
            return super().dispatch(request, *args, **kwargs)


class GoutHelperPseudopatientDetailMixin(GoutHelperDetailMixinBase):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except self.model.DoesNotExist:
            model_name = self.model._meta.model_name
            messages.error(request, f"{self.user} does not have a {model_name}. Create one instead.")
            return HttpResponseRedirect(
                reverse(f"{model_name.lower()}s:pseudopatient-create", kwargs={"pseudopatient": self.user.pk})
            )
        if not self.user_has_required_otos:
            messages.error(request, "Baseline information is needed to use GoutHelper Decision and Treatment Aids.")
            return HttpResponseRedirect(reverse("users:pseudopatient-update", kwargs={"pseudopatient": self.user.pk}))
        else:
            if not request.GET.get("updated", None):
                self.object.update_aid(qs=self.user)
                self.object.update_related_objects(qs=self.user)
            return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["patient"] = self.user
        return context

    def get_object(self) -> "Aids":
        try:
            self.user: User = self.get_queryset().get()
        except User.DoesNotExist as exc:
            raise User.DoesNotExist("GoutPatient does not exist.") from exc
        try:
            model_name = self.model._meta.model_name
            object: "Aids" = getattr(self.user, model_name.lower())
        except self.model.DoesNotExist as exc:
            raise self.model.DoesNotExist(f"{model_name} for {self.user} does not exist.") from exc
        return object

    def get_queryset(self, **kwargs) -> "QuerySet[Any]":
        return (
            getattr(Pseudopatient.objects, self.model._meta.model_name.lower() + "_qs")(**kwargs)
            .filter(pk=self.kwargs["pseudopatient"])
            .select_related("pseudopatientprofile__provider")
        )

    @property
    def user_has_required_otos(self):
        return all([hasattr(self.user, oto) for oto in self.model.req_otos])


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
    def ckddetail(self) -> bool:
        """Method that returns True if CKD is in the medhistory_details dict."""
        return hasattr(self, "medhistory_detail_forms") and "ckddetail" in self.medhistory_detail_forms.keys()

    @cached_property
    def create_view(self):
        """Method that returns True if the view is a CreateView."""
        return True if isinstance(self, CreateView) else False

    def form_invalid(self, form):
        response = super().form_invalid(form)
        next_url = self.request.GET.get("next") or self.request.POST.get("next")
        if next_url:
            return HttpResponseRedirect(f"{self.request.path}?next={next_url}")
        return response

    def form_valid(self, **kwargs) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Method to be called if all forms are valid."""
        self.form_valid_init()
        self.form_valid_update_fks_and_related_object()
        self.form_valid_end(**kwargs)
        return self.form_valid_return(**kwargs)

    def form_valid_init(self) -> None:
        if self.form_valid_form_should_save():
            self.object = self.form.save(commit=False)
            self.save_object = True
        else:
            self.object = self.form.instance
            self.save_object = False
        if self.user and self.object.user is None:
            self.object.user = self.user

    def form_valid_form_should_save(self) -> bool:
        return (
            self.form.has_changed
            or self.oto_forms
            and (self.oto_2_save or self.oto_2_rem)
            or self.user
            and self.form.instance.user is None
            or self.create_view
        )

    def form_valid_update_fks_and_related_object(self) -> None:
        if self.related_object:
            self.save_related_object = False
            self.form_valid_set_view_model_attr_on_related_object()
        if self.save_object:
            self.object.full_clean()
            self.object.save()
        if self.related_object and self.save_related_object:
            self.related_object.full_clean()
            self.related_object.save()

    def form_valid_end(self, **kwargs) -> Union["HttpResponseRedirect", "HttpResponse"]:
        if self.user:
            setattr(self.user, f"{self.object_attr}_qs", self.object)
            self.object.update_aid(qs=self.user)
        else:
            self.object.update_aid(qs=self.object)
        self.object.update_related_objects(qs=self.user if self.user else self.object)

    def form_valid_return(self, **kwargs) -> Union["HttpResponseRedirect", "HttpResponse"]:
        messages.success(self.request, self.get_success_message(self.form.cleaned_data))
        if self.request.htmx:
            return kwargs.get("htmx")
        return HttpResponseRedirect(self.get_success_url())

    def set_object_attr_on_related_object(self) -> None:
        setattr(self.related_object, self.object_attr, self.object)
        if self.save_related_object is not True:
            self.save_related_object = True

    def form_valid_set_view_model_attr_on_related_object(self) -> None:
        if self.model_attr_empty_on_related_object:
            self.set_object_attr_on_related_object()

    @property
    def model_attr_empty_on_related_object(self) -> bool:
        return (
            self.related_object
            and attr_is_in_model_fields(
                self.object_attr,
                self.related_object,
            )
            and getattr(self.related_object, self.object_attr, None) is None
        )

    def get(self, request, *args, **kwargs):
        """Overwritten to not call get_object()."""
        self.set_forms()
        return self.render_to_response(self.get_context_data())

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        if self.oto_forms or self.req_otos:
            self.context_onetoones(kwargs=kwargs)
        if self.medallergy_forms:
            self.context_medallergys(
                kwargs=kwargs,
            )
        if self.medhistory_forms or self.medhistory_detail_forms:
            self.context_medhistorys(
                kwargs=kwargs,
            )
        if self.lab_formsets:
            self.context_labs(kwargs=kwargs)
        if "patient" not in kwargs and self.user:
            kwargs["patient"] = self.user
        kwargs.update({"str_attrs": self.str_attrs})
        return super().get_context_data(**kwargs)

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        if self.medallergy_forms:
            kwargs["medallergys"] = self.medallergy_forms.keys()
        kwargs.update(
            {
                **self.subform_kwargs,
                "related_object": self.related_object if self.related_object else None,
            }
        )
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
            next_url += f"?updated=True&related_object_id=#{self.object_attr}-card"
            return next_url
        else:
            return super().get_success_url() + "?updated=True"

    def dispatch(self, request, *args, **kwargs):
        """Overwritten to redirect if the user is attempting to create an instance of a model that the intended
        Pseudopatient already has an instance of and their relationship is a 1to1."""
        try:
            self.object = self.get_object()
        except self.model.DoesNotExist as exc:
            if self.user:
                return self.dispatch_redirect_to_user_create_view(request, exc)
            else:
                raise exc

        if self.dispatch_anon_view_needs_redirect_to_user_view():
            return self.dispatch_redirect_to_user_view()
        elif self.user:
            if self.dispatch_user_missing_requirements(request):
                return self.dispatch_redirect_to_user_update_view(request)
            elif self.dispatch_user_create_view_needs_redirect_to_user_model_update_view():
                return self.dispatch_redirect_to_user_model_update_view(request)
        elif self.dispatch_with_related_object_needs_redirect_to_update_view():
            return self.dispatch_redirect_to_update_view_with_related_object_model_attr(request)

        return super().dispatch(request, *args, **kwargs)

    def dispatch_redirect_to_user_update_view(self, request: "HttpRequest") -> HttpResponseRedirect:
        messages.error(request, message=f"{self.user} is missing required information.")
        return HttpResponseRedirect(reverse("users:pseudopatient-update", kwargs={"pseudopatient": self.user.pk}))

    def dispatch_user_missing_requirements(self, request: "HttpRequest") -> bool:
        return False

    def dispatch_user_create_view_needs_redirect_to_user_model_update_view(self) -> bool:
        return (
            self.user
            and self.create_view
            and self.model_name != "Flare"
            and self.model.objects.filter(user=self.user).exists()
        )

    def dispatch_redirect_to_user_create_view(
        self, request: "HttpRequest", exc: ValidationError
    ) -> HttpResponseRedirect:
        messages.error(request, exc.args[0])
        return HttpResponseRedirect(
            reverse(f"{self.model_app}:pseudopatient-create", kwargs={"pseudopatient": self.user.pk})
        )

    def dispatch_redirect_to_user_model_update_view(self, request: "HttpRequest") -> HttpResponseRedirect:
        messages.error(request, f"{self.user} already has a {self.model_name}. Please update it instead.")
        return HttpResponseRedirect(
            reverse(f"{self.model_app}:pseudopatient-update", kwargs={"pseudopatient": self.user.pk})
        )

    def dispatch_with_related_object_needs_redirect_to_update_view(self) -> bool:
        return self.related_object and self.create_view and self.related_object_has_model_attr()

    def related_object_has_model_attr(self) -> bool:
        return self.related_object_model_attr is not None

    @property
    def related_object_model_attr(self) -> Union["Aids", None]:
        return getattr(self.related_object, self.model_name.lower(), None)

    def dispatch_redirect_to_update_view_with_related_object_model_attr(
        self, request: "HttpRequest"
    ) -> HttpResponseRedirect:
        messages.error(request, f"{self.related_object} already has a {self.model_name}. Please update it instead.")
        return HttpResponseRedirect(
            reverse(
                f"{self.model_app}:update",
                kwargs={"pk": self.related_object_model_attr.pk},
            )
        )

    def object_has_user_and_is_not_user(self) -> bool:
        return getattr(self.object, "user", None) and not isinstance(self.object, User)

    def dispatch_anon_view_needs_redirect_to_user_view(self) -> bool:
        return not self.user and self.object_has_user_and_is_not_user()

    def dispatch_redirect_to_user_view(self) -> HttpResponseRedirect:
        kwargs = {"pseudopatient": self.object.user.pk}
        if self.model_name == "Flare":
            kwargs["pk"] = self.object.pk
        return HttpResponseRedirect(
            reverse(
                f"{self.model_app}:pseudopatient-{'create' if self.create_view else 'update'}",
                kwargs=kwargs,
            )
        )

    @classmethod
    def get_modelform_model(cls, modelform: ModelForm) -> Model:
        return modelform._meta.model

    @cached_property
    def goutdetail(self) -> bool:
        """Method that returns True if GOUT is in the medhistorys dict."""
        return hasattr(self, "medhistory_detail_forms") and "goutdetail" in self.medhistory_detail_forms.keys()

    @cached_property
    def model_app(self) -> str:
        return self.model._meta.app_label

    @cached_property
    def model_name(self) -> str:
        return self.model.__name__

    @cached_property
    def model_field_names(self) -> list[str]:
        return [field.name for field in self.model._meta.get_fields()]

    @cached_property
    def object_attr(self) -> str:
        return self.object.__class__.__name__.lower() if not isinstance(self.object, Pseudopatient) else "user"

    def post(self, request, *args, **kwargs):
        self.post_init()
        if self.post_forms_valid():
            self.post_process_forms()
            self.post_errors()
        else:
            self.errors_bool = False
            self.errors = self.render_errors()

    def post_init(self) -> None:
        self.set_forms()
        form_class = self.get_form_class()
        self.form = form_class(
            **self.get_form_kwargs(),
        )

    def post_forms_valid(self) -> bool:
        return self.form.is_valid()

    def post_process_forms(self) -> None:
        self.errors_bool = False
        self.form.save(commit=False)

    def post_errors(self) -> Union["HttpResponse", None]:
        self.errors = self.render_errors() if self.errors_bool else None

    def post_get_qs_target(self, post_object: Union["Aids", User]) -> Union["Aids", User]:
        return self.query_object if isinstance(self.query_object, User) else post_object

    def post_get_ckd(self) -> Union["MedHistory", None]:
        ckd_form = self.medhistory_forms.get(MedHistoryTypes.CKD, None) if self.medhistory_forms else None
        if ckd_form:
            if hasattr(ckd_form, "cleaned_data") and "value" in ckd_form.cleaned_data:
                return ckd_form.cleaned_data["value"]
            else:
                return None
        else:
            return (
                self.query_object.ckd.value if self.query_object and getattr(self.query_object, "ckd", False) else None
            )

    def get_dateofbirth_form(self) -> Union["DateOfBirthForm", None]:
        return self.oto_forms.get("dateofbirth", None) if self.oto_forms and not self.user else None

    def get_gender_form(self) -> Union["GenderForm", None]:
        return self.oto_forms.get("gender", None) if self.oto_forms and not self.user else None

    def post_get_dateofbirth_value(self) -> Union["DateOfBirth", None]:
        dateofbirth_form = self.get_dateofbirth_form()
        if dateofbirth_form and hasattr(dateofbirth_form, "cleaned_data") and "value" in dateofbirth_form.cleaned_data:
            return dateofbirth_form.cleaned_data["value"]
        else:
            return (
                self.query_object.dateofbirth.value
                if self.query_object and getattr(self.query_object, "dateofbirth", False)
                else None
            )

    def post_get_age_value(self) -> int | None:
        dateofbirth_value = self.post_get_dateofbirth_value()
        return age_calc(dateofbirth_value) if dateofbirth_value else None

    def post_get_gender_value(self) -> Union["Gender", None]:
        gender_form = self.get_gender_form()
        if gender_form and hasattr(gender_form, "cleaned_data") and "value" in gender_form.cleaned_data:
            return gender_form.cleaned_data["value"]
        else:
            return (
                self.query_object.gender.value
                if self.query_object and getattr(self.query_object, "gender", False)
                else None
            )

    @cached_property
    def query_object(self) -> Union["Aids", User, None]:
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
    def related_objects(self) -> list[Model]:
        def append_rel_objs_rel_objs(rel_obj: "Aids") -> None:
            for aid_type in rel_obj.related_models:
                if hasattr(rel_obj, aid_type):
                    rel_rel_obj = getattr(rel_obj, aid_type)
                    if rel_rel_obj and rel_rel_obj != self.object and rel_rel_obj not in rel_obj_list:
                        rel_obj_list.append(rel_rel_obj)

        rel_obj_list = []

        if self.create_view and not self.user:
            for aid_type in self.model.related_models:
                if hasattr(self, aid_type):
                    rel_obj = getattr(self, aid_type)
                    if rel_obj:
                        rel_obj_list.append(rel_obj)
                        append_rel_objs_rel_objs(rel_obj)
        elif not self.user:
            for aid_type in self.object.related_models:
                if hasattr(self.object, aid_type):
                    rel_obj = getattr(self.object, aid_type)
                    if rel_obj:
                        rel_obj_list.append(rel_obj)
                        append_rel_objs_rel_objs(rel_obj)
        return rel_obj_list

    @property
    def subform_kwargs(self) -> dict[str, Any]:
        return {
            "patient": self.user,
            "request_user": self.request_user,
            "str_attrs": self.str_attrs,
        }

    @classmethod
    def get_related_objects_attrs(cls) -> list[str]:
        return list_of_possible_related_object_attrs()

    @classmethod
    def get_related_object_attr(cls, related_object: Any) -> str:
        return related_object.__class__.__name__.lower()

    @cached_property
    def related_object_attr(self) -> str:
        return self.get_related_object_attr(self.related_object) if self.related_object else None

    @cached_property
    def request_user(self):
        return self.request.user

    def render_errors(self) -> "HttpResponse":
        """Renders forms with errors in multiple locations in post()."""
        return self.render_to_response(
            self.get_context_data(
                form=self.form,
                **self.oto_forms if self.oto_forms else {},
                **self.medhistory_forms if self.medhistory_forms else {},
                **self.medhistory_detail_forms if self.medhistory_detail_forms else {},
                **self.medallergy_forms if self.medallergy_forms else {},
                **(
                    {f"{lab}_formset": lab_tup[0] for lab, lab_tup in self.lab_formsets.items()}
                    if self.lab_formsets
                    else {}
                ),
                **(
                    {f"{lab}_formset_helper": lab_tup[1] for lab, lab_tup in self.lab_formsets.items()}
                    if self.lab_formsets
                    else {}
                ),
            )
        )

    def set_errors_bool_True(self) -> None:
        if not self.errors_bool:
            self.errors_bool = True

    def set_forms(self) -> None:
        self.set_lab_formsets()
        self.set_medallergy_forms()
        self.set_medhistory_forms()
        self.set_medhistory_detail_forms()
        self.set_oto_forms()
        self.set_req_otos()

    def set_lab_formsets(self) -> None:
        self.lab_formsets = self.LAB_FORMSETS.copy() if hasattr(self, "LAB_FORMSETS") else {}

    def set_medallergy_forms(self) -> None:
        self.medallergy_forms = self.MEDALLERGY_FORMS.copy() if hasattr(self, "MEDALLERGY_FORMS") else {}

    def set_medhistory_forms(self) -> None:
        self.medhistory_forms = self.MEDHISTORY_FORMS.copy() if hasattr(self, "MEDHISTORY_FORMS") else {}

    def set_medhistory_detail_forms(self) -> None:
        self.medhistory_detail_forms = (
            self.MEDHISTORY_DETAIL_FORMS.copy() if hasattr(self, "MEDHISTORY_DETAIL_FORMS") else {}
        )

    def set_oto_forms(self) -> None:
        oto_forms_without_related_objects = (
            {key: val for key, val in self.OTO_FORMS.items() if self.onetoone_not_attr_of_related_object(key)}
            if hasattr(self, "OTO_FORMS")
            else {}
        )
        self.oto_forms = oto_forms_without_related_objects

    def set_req_otos(self) -> None:
        if not hasattr(self, "req_otos"):
            self.req_otos = self.REQ_OTOS.copy() if hasattr(self, "REQ_OTOS") else []
            if self.related_object and hasattr(self, "OTO_FORMS"):
                for key in self.OTO_FORMS.keys():
                    if not self.onetoone_not_attr_of_related_object(key):
                        self.req_otos.append(key)

    @cached_property
    def str_attrs(self) -> dict[str, str]:
        """Returns a dict of string attributes to make forms context-sensitive."""
        return get_str_attrs(self.object if not self.create_view else None, self.user, self.request.user)

    @cached_property
    def user(self) -> User | None:
        """Method that returns the User object from the username kwarg
        and sets the user attr on the view."""
        pseudopatient = self.kwargs.get("pseudopatient", None)
        if pseudopatient:
            if hasattr(self, "get_user_queryset"):
                return self.get_user_queryset(pseudopatient=pseudopatient).get()
            else:
                return self.get_queryset().get(id=pseudopatient)
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
                if self.query_object and self.lab_belongs_to_query_object(lab):
                    queryset_kwargs = {self.query_obj_attr: self.query_object}
                else:
                    lab_related_onetoone_attr = self.lab_belongs_to_onetoone(lab)
                    if lab_related_onetoone_attr:
                        queryset_kwargs = {lab_related_onetoone_attr: getattr(self.object, lab_related_onetoone_attr)}
                    elif self.user:
                        queryset_kwargs = {"user": self.user}
                    elif self.lab_belongs_to_object(lab):
                        queryset_kwargs = {self.object_attr: self.object}
                    else:
                        queryset_kwargs = None
                kwargs[f"{lab}_formset"] = self.populate_a_lab_formset(lab, queryset_kwargs)
            if f"{lab}_formset_helper" not in kwargs:
                kwargs[f"{lab}_formset_helper"] = lab_tup[1]

    def form_valid_update_fks_and_related_object(self) -> None:
        super().form_valid_update_fks_and_related_object()
        self.form_valid_save_and_delete_labs()

    def lab_belongs_to_query_object(self, lab: str) -> bool:
        return not self.user and self.query_obj_attr in self.lab_formsets[lab][0].model.related_models()

    def lab_belongs_to_object(self, lab: str) -> bool:
        return self.object_attr in self.lab_formsets[lab][0].model.related_models()

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

    def lab_oto_belongs_to_query_object(self, oto_attr: str) -> bool:
        return self.query_obj_attr in self.oto_forms[oto_attr].model.related_models()

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

    def post_init(self) -> None:
        super().post_init()
        self.post_populate_lab_formsets()

    def post_forms_valid(self) -> bool:
        other_forms_valid = super().post_forms_valid()
        lab_formsets_valid = (
            validate_formset_list(formset_list=[lab_tup[0] for lab_tup in self.lab_formsets.values()])
            if self.lab_formsets
            else True
        )
        return other_forms_valid and lab_formsets_valid

    def post_process_forms(self) -> None:
        super().post_process_forms()
        self.post_process_lab_formsets()

    def post_populate_lab_formsets(self) -> None:
        """Method to populate a dict of lab forms with POST data in the post() method."""
        for lab, lab_tup in self.lab_formsets.items():
            if self.query_obj_attr and self.lab_belongs_to_query_object(lab):
                queryset_kwargs = {self.query_obj_attr: self.query_object}
            else:
                lab_related_onetoone_attr = self.lab_belongs_to_onetoone(lab)
                if lab_related_onetoone_attr and self.lab_belongs_to_object(lab):
                    queryset_kwargs = (
                        {lab_related_onetoone_attr: getattr(self.object, lab_related_onetoone_attr)}
                        if getattr(self.object, lab_related_onetoone_attr, None)
                        else None
                    )
                elif self.user:
                    queryset_kwargs = {"user": self.user}
                else:
                    queryset_kwargs = None
            self.lab_formsets.update(
                {
                    lab: (
                        self.populate_a_lab_formset(lab, queryset_kwargs),
                        lab_tup[1],
                    )
                }
            )

    def post_process_lab_formsets(self) -> None:
        """Method to process the forms in a Lab formset for the post() method.
        Requires a list of existing labs (can be empty) to iterate over and compare to the forms in the
        formset to identify labs that need to be removed.

        Args:
            lab_formset (BaseModelFormSet): A formset of LabForms
            query_object (Aids | User): The object to which the labs are related

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
                        related_model in list(self.req_otos) + list(self.oto_forms.keys())
                    ):
                        return True
                for oto in self.req_otos + list(self.oto_forms.keys()):
                    if hasattr(lab, oto) and getattr(lab, oto, None) is None:
                        return True
                return False

        # Assign lists to return
        post_qs_target = self.post_get_qs_target(self.form.instance)
        self.labs_2_save: list["Lab"] = []
        self.labs_2_rem: list["Lab"] = []

        if self.lab_formsets:
            for lab_name, lab_tup in self.lab_formsets.items():
                qs_target_method = getattr(self, f"post_get_{lab_name}_qs_target", None)
                qs_attr = get_or_create_qs_attr(
                    qs_target_method(post_qs_target) if qs_target_method else post_qs_target,
                    lab_name,
                    self.query_object,
                )
                # Check for and iterate over the existing queryset of labs to catch objects that
                # are not changed in the formset but NEED to be saved for the view (i.e. to add relations)
                if qs_attr:
                    cleaned_data = lab_tup[0].cleaned_data
                    # NOTE: FOR FUTURE SELF: COPY A LIST WHEN ITERATING OVER IT AND ADDING/REMOVING ELEMENTS
                    for lab in qs_attr.copy():
                        for lab_form in cleaned_data:
                            try:
                                if lab_form["id"] == lab:
                                    if not lab_form["DELETE"]:
                                        if _lab_needs_relation_set(lab):
                                            self.labs_2_save.append(lab)
                                        if lab not in qs_attr:
                                            qs_attr.append(lab)
                                        break
                            except KeyError:
                                pass
                        else:
                            self.labs_2_rem.append(lab)
                            qs_attr.remove(lab)
                for form in lab_tup[0]:
                    if form.instance_should_persist and (
                        (form.instance and form.has_changed())
                        or form.instance is None
                        or _lab_needs_relation_set(form.instance)
                    ):
                        self.labs_2_save.append(form.instance)
                    if form.instance_should_persist and form.instance not in qs_attr:
                        qs_attr.append(form.instance)

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
            "form_kwargs": self.subform_kwargs,
        }
        if self.request.method == "POST":
            formset_kwargs.update({"data": self.request.POST})
        return self.lab_formsets[lab][0](
            **formset_kwargs,
        )

    def post_get_creatinine_qs_target(
        self,
        post_object: Union["Aids", User],
    ) -> Union["Aids", User]:
        qs_target = getattr(post_object, "aki", None) if post_object else None
        if not qs_target:
            qs_target = self.oto_forms["aki"].instance
        return qs_target

    def post_get_urate_qs_target(
        self,
        post_object: Union["Aids", User],
    ) -> Union["Aids", User]:
        return post_object


class MedAllergyFormMixin(GoutHelperEditMixin):
    def context_medallergys(
        self,
        kwargs: dict,
    ) -> None:
        for treatment, medallergy_form in self.medallergy_forms.items():
            form_str = f"medallergy_{treatment}_form"
            if form_str not in kwargs:
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
                kwargs[form_str] = (
                    medallergy_form
                    if isinstance(medallergy_form, ModelForm)
                    else medallergy_form(
                        treatment=treatment,
                        instance=ma_obj,
                        initial={
                            f"medallergy_{treatment}": True if ma_obj else None,
                            f"{treatment}_matype": ma_obj.matype if ma_obj else None,
                        },
                        patient=self.user,
                        request_user=self.request_user,
                        str_attrs=self.str_attrs,
                    )
                )

    def form_valid_update_fks_and_related_object(self) -> None:
        super().form_valid_update_fks_and_related_object()
        self.form_valid_save_medallergys()
        self.form_valid_delete_medallergys()

    def post_init(self) -> None:
        super().post_init()
        self.post_populate_ma_forms()

    def post_forms_valid(self) -> bool:
        other_forms_valid = super().post_forms_valid()
        ma_forms_valid = (
            validate_form_list(form_list=self.medallergy_forms.values()) if self.medallergy_forms else True
        )
        return other_forms_valid and ma_forms_valid

    def post_process_forms(self) -> None:
        super().post_process_forms()
        self.post_process_ma_forms()

    def post_populate_ma_forms(self) -> None:
        """Method to populate the forms for the MedAllergys for the post() method."""
        if self.medallergy_forms:
            for treatment, medallergy_form in self.medallergy_forms.items():
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
                self.medallergy_forms.update(
                    {
                        treatment: medallergy_form(
                            self.request.POST,
                            treatment=treatment,
                            instance=ma_obj,
                            initial={
                                f"medallergy_{treatment}": True if ma_obj else None,
                                f"{treatment}_matype": ma_obj.matype if ma_obj else None,
                            },
                            patient=self.user,
                            request_user=self.request_user,
                            str_attrs=self.str_attrs,
                        )
                    }
                )

    def post_process_ma_forms(self) -> None:
        post_qs_target = self.post_get_qs_target(self.form.instance)
        self.ma_2_save: list["MedAllergy"] = []
        self.ma_2_rem: list["MedAllergy"] = []
        get_or_create_qs_attr(post_qs_target, "medallergy")
        for treatment, medallergy_form in self.medallergy_forms.items():
            if f"medallergy_{treatment}" in medallergy_form.cleaned_data:
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
                if ma_obj and not medallergy_form.cleaned_data[f"medallergy_{treatment}"]:
                    self.ma_2_rem.append(ma_obj)
                    getattr(post_qs_target, "medallergys_qs", []).remove(ma_obj)
                else:
                    if medallergy_form.cleaned_data[f"medallergy_{treatment}"]:
                        # If there is already an instance, it will not have changed so it doesn't need to be changed
                        if not ma_obj:
                            ma = medallergy_form.save(commit=False)
                            # Assign MedAllergy object treatment attr from the cleaned_data["treatment"]
                            ma.treatment = medallergy_form.cleaned_data["treatment"]
                            ma.matype = medallergy_form.cleaned_data.get(f"{treatment}_matype", None)
                            self.ma_2_save.append(ma)
                            # Add the medallergy to the form instance's medallergys_qs if it's not already there
                            if ma not in getattr(post_qs_target, "medallergys_qs", []):
                                getattr(post_qs_target, "medallergys_qs", []).append(ma)
                        else:
                            if ma_obj.matype != medallergy_form.cleaned_data[f"{treatment}_matype"]:
                                ma_obj.matype = medallergy_form.cleaned_data[f"{treatment}_matype"]
                                self.ma_2_save.append(ma_obj)
                            # Add the medallergy to the form instance's medallergys_qs if it's not already there
                            if ma_obj not in getattr(post_qs_target, "medallergys_qs", []):
                                getattr(post_qs_target, "medallergys_qs", []).append(ma_obj)

    def form_valid_save_medallergys(self) -> None:
        if self.ma_2_save:
            for ma in self.ma_2_save:
                if self.user:
                    if ma.user is None:
                        ma.user = self.user
                else:
                    if getattr(ma, self.object_attr, None) is None:
                        setattr(ma, self.object_attr, self.object)
                ma.save()

    def form_valid_delete_medallergys(self) -> None:
        if self.ma_2_rem:
            for ma in self.ma_2_rem:
                ma.delete()


class MedHistoryFormMixin(GoutHelperEditMixin):
    @classmethod
    def add_mh_to_qs(cls, mh: "MedHistory", qs: list["MedHistory"], check: bool = True) -> None:
        """Method to add a MedHistory to a list of MedHistories."""
        if not check or mh not in qs:
            qs.append(mh)

    def context_medhistorys(
        self,
        kwargs: dict,
    ) -> None:
        """Method that iterates over the medhistorys dict and adds the forms to the context."""
        for mhtype, mh_form in self.medhistory_forms.items():
            form_str = f"{mhtype}_form"
            if form_str not in kwargs:
                mh_obj = self.get_mh_obj(mhtype)
                if mhtype == MedHistoryTypes.CKD:
                    extra_kwargs = {"ckddetail": self.ckddetail, "sub-form": True}
                    self.ckddetail_mh_context(
                        kwargs=kwargs,
                        mh_obj=mh_obj,
                    )
                elif mhtype == MedHistoryTypes.GOUT:
                    extra_kwargs = {"goutdetail": self.goutdetail, "sub-form": True}
                    if self.goutdetail:
                        try:
                            self.goutdetail_mh_context(kwargs=kwargs, mh_obj=mh_obj)
                        except Continue:
                            continue
                        kwargs[form_str] = (
                            mh_form
                            if isinstance(mh_form, ModelForm)
                            else mh_form(
                                instance=mh_obj,
                                initial={f"{mhtype}-value": True},
                                **self.subform_kwargs,
                                **extra_kwargs,
                            )
                        )
                        continue
                else:
                    extra_kwargs = {}
                kwargs[form_str] = (
                    mh_form
                    if isinstance(mh_form, ModelForm)
                    else mh_form(
                        instance=mh_obj,
                        initial=self.get_mh_initial(mhtype, mh_obj),
                        **self.subform_kwargs,
                        **extra_kwargs,
                    )
                )

    def ckddetail_mh_context(
        self,
        kwargs: dict[str, Any],
        mh_obj: Union["MedHistory", None] = None,
    ) -> None:
        """Method that populates the context dictionary with the CkdDetailForm."""
        if self.ckddetail:
            if "ckddetail_form" not in kwargs:
                ckddetail_i = getattr(mh_obj, "ckddetail", None) if mh_obj else None
                ckddetail_form = self.medhistory_detail_forms["ckddetail"]
                kwargs["ckddetail_form"] = (
                    ckddetail_form
                    if isinstance(ckddetail_form, ModelForm)
                    else ckddetail_form(
                        instance=ckddetail_i,
                        **self.subform_kwargs,
                    )
                )
            if "baselinecreatinine_form" not in kwargs:
                bc_i = getattr(mh_obj, "baselinecreatinine", None) if mh_obj else None
                bc_form = self.medhistory_detail_forms["baselinecreatinine"]
                kwargs["baselinecreatinine_form"] = (
                    bc_form
                    if isinstance(bc_form, ModelForm)
                    else bc_form(
                        instance=bc_i,
                        **self.subform_kwargs,
                    )
                )

    def form_valid_update_fks_and_related_object(self) -> None:
        super().form_valid_update_fks_and_related_object()
        self.form_valid_save_medhistorys()
        self.form_valid_save_medhistory_details()
        self.form_valid_delete_medhistorys()
        self.form_valid_delete_medhistory_details()

    def goutdetail_mh_context(
        self,
        kwargs: dict[str, Any],
        mh_obj: Union["MedHistory", User, None] = None,
    ) -> None:
        """Method that adds the GoutDetailForm to the context."""
        if "goutdetail_form" not in kwargs:
            goutdetail_i = getattr(mh_obj, "goutdetail", None) if mh_obj else None
            goutdetail_form = self.medhistory_detail_forms["goutdetail"]
            kwargs["goutdetail_form"] = (
                goutdetail_form
                if isinstance(goutdetail_form, ModelForm)
                else goutdetail_form(
                    instance=goutdetail_i,
                    **self.subform_kwargs,
                )
            )
            if hasattr(mh_obj, "user") and mh_obj.user:
                raise Continue

    def post_init(self) -> None:
        super().post_init()
        self.post_populate_mh_forms()

    def post_forms_valid(self) -> bool:
        other_forms_valid = super().post_forms_valid()
        mh_forms_valid = self.validate_medhistory_form_list() if self.medhistory_forms else True
        mh_det_forms_valid = (
            validate_form_list(form_list=self.medhistory_detail_forms.values())
            if self.medhistory_detail_forms
            else True
        )
        return other_forms_valid and mh_forms_valid and mh_det_forms_valid

    def post_process_forms(self) -> None:
        super().post_process_forms()
        self.post_process_mh_forms()

    def post_populate_mh_forms(self) -> None:
        """Populates forms for MedHistory and MedHistoryDetail objects in post() method."""
        if self.medhistory_forms:
            for mhtype, mh_form in self.medhistory_forms.items():
                mh_obj = self.get_mh_obj(mhtype)
                form_kwargs = {"patient": self.user, "request_user": self.request_user, "str_attrs": self.str_attrs}
                if mhtype == MedHistoryTypes.CKD:
                    extra_kwargs = {"ckddetail": self.ckddetail, "sub-form": True}
                    if self.ckddetail:
                        self.ckddetail_mh_post_pop(ckd=mh_obj)
                elif mhtype == MedHistoryTypes.GOUT:
                    extra_kwargs = {"goutdetail": self.goutdetail, "sub-form": True}
                    if self.goutdetail:
                        try:
                            self.goutdetail_mh_post_pop(gout=mh_obj)
                        except Continue:
                            continue
                        self.medhistory_forms.update(
                            {
                                mhtype: mh_form(
                                    self.request.POST,
                                    instance=(
                                        mh_obj if mh_obj else self.get_modelform_model(self.medhistory_forms[mhtype])()
                                    ),
                                    initial={f"{mhtype}-value": True},
                                    **form_kwargs,
                                    **extra_kwargs,
                                )
                            }
                        )
                        continue
                else:
                    extra_kwargs = {}
                self.medhistory_forms.update(
                    {
                        mhtype: mh_form(
                            self.request.POST,
                            instance=(mh_obj if mh_obj else self.get_modelform_model(self.medhistory_forms[mhtype])()),
                            initial=({f"{mhtype}-value": self.get_mh_initial(mhtype, mh_obj)}),
                            **form_kwargs,
                            **extra_kwargs,
                        )
                    }
                )

    def ckddetail_mh_post_pop(
        self,
        ckd: Union["MedHistory", None],
    ) -> None:
        """Method that updates the CkdDetail and BaselineCreatinine forms in the post() method."""
        if ckd:
            ckddetail = getattr(ckd, "ckddetail", None)
            bc = getattr(ckd, "baselinecreatinine", None)
        else:
            ckddetail = CkdDetail()
            bc = BaselineCreatinine()
        self.medhistory_detail_forms.update(
            {
                "ckddetail": self.medhistory_detail_forms["ckddetail"](
                    self.request.POST,
                    instance=ckddetail,
                    **self.subform_kwargs,
                )
            }
        )
        self.medhistory_detail_forms.update(
            {
                "baselinecreatinine": self.medhistory_detail_forms["baselinecreatinine"](
                    self.request.POST, instance=bc, **self.subform_kwargs
                )
            }
        )

    def goutdetail_mh_post_pop(
        self,
        gout: Union["MedHistory", None],
    ) -> None:
        """Method that adds the GoutDetailForm to the mh_det_forms dict."""
        if gout:
            gd = getattr(gout, "goutdetail", None)
        else:
            gd = GoutDetail()
        self.medhistory_detail_forms.update(
            {
                "goutdetail": self.medhistory_detail_forms["goutdetail"](
                    self.request.POST,
                    instance=gd,
                    **self.subform_kwargs,
                )
            }
        )
        if gout and hasattr(gout, "user") and gout.user:
            raise Continue

    def get_mh_obj(self, mhtype: MedHistoryTypes) -> Union["MedHistory", None]:
        if self.user:
            return (
                medhistorys_get(self.query_object.medhistorys_qs, mhtype, null_return=None)
                if self.query_object
                else None
            )
        elif self.query_object and mhtype in self.query_object.aid_medhistorys():
            return (
                medhistorys_get(self.query_object.medhistorys_qs, mhtype, null_return=None)
                if self.query_object
                else None
            )
        else:
            return next(
                iter(
                    medhistorys_get(rel_obj.medhistorys_qs, mhtype, null_return=None)
                    for rel_obj in self.related_objects
                    if mhtype in rel_obj.aid_medhistorys()
                ),
                None,
            )

    def default_get_mh_initial_value(self, mhtype: MedHistoryTypes, mh_obj: "MedHistory") -> bool:
        return (
            True
            if mh_obj
            else (
                False
                if (
                    self.medhistory_crossref_with_related_objects_required
                    and self.mhtypes_aids.mhtype_in_related_object_aid(mhtype=mhtype)
                )
                or not self.create_view
                else None
            )
        )

    def get_mh_initial(self, mhtype: MedHistoryTypes, mh_obj: "MedHistory") -> dict[str, Any]:
        if hasattr(self, f"get_{mhtype}_initial_value"):
            return {f"{mhtype}-value": getattr(self, f"get_{mhtype}_initial_value")(mh_obj)}
        else:
            return {f"{mhtype}-value": (self.default_get_mh_initial_value(mhtype, mh_obj))}

    @cached_property
    def mhtypes_aids(self) -> MedHistoryTypesAids:
        return MedHistoryTypesAids(
            mhtypes=list(self.medhistory_forms.keys()),
            related_object=(self.object_to_crossref_medhistorys_with),
        )

    @property
    def medhistory_crossref_with_related_objects_required(self) -> bool:
        return self.create_view and (self.object_to_crossref_medhistorys_with)

    @property
    def object_to_crossref_medhistorys_with(self) -> Union["Aids", User, None]:
        return self.user if self.user else self.related_object if self.related_object else None

    def post_process_mh_forms(
        self,
    ) -> tuple[
        list["MedHistory"],
        list["MedHistory"],
        list["CkdDetailForm", BaselineCreatinine, "GoutDetailForm"],
        list[CkdDetail, BaselineCreatinine, None],
    ]:
        post_qs_target = self.post_get_qs_target(self.form.instance)
        self.mhs_2_save: list["MedHistory"] = []
        self.mhs_2_remove: list["MedHistory"] = []
        self.mhdets_2_save: list["CkdDetailForm" | BaselineCreatinine] = []
        self.mhdets_2_remove: list[CkdDetail | BaselineCreatinine | None] = []
        # Create medhistory_qs attribute on the form instance if it doesn't exist
        get_or_create_qs_attr(post_qs_target, "medhistory")
        for mhtype, mh_form in self.medhistory_forms.items():
            if not isinstance(mh_form, ModelForm):
                self.post_process_medhistory_detail(
                    mhtype=mhtype,
                    medhistory=getattr(self.query_object, mhtype.lower(), None),
                )
                continue
            mh_obj = self.get_mh_obj(mhtype)
            if self.get_mh_cleaned_value(mhtype, mh_form.cleaned_data):
                if mh_obj:
                    if (
                        self.related_objects
                        and self.medhistory_needs_object_attr_update_for_any_related_object(mh_obj)
                        or self.medhistory_needs_object_attr_update(mh_obj, self.object, self.object_attr)
                        or self.user
                        and not mh_obj.user
                    ):
                        self.add_mh_to_qs(mh=mh_obj, qs=self.mhs_2_save)
                else:
                    mh_obj = mh_form.save(commit=False)
                    self.add_mh_to_qs(mh=mh_obj, qs=self.mhs_2_save)
                self.add_mh_to_qs(mh=mh_obj, qs=post_qs_target.medhistorys_qs)
                if self.related_object:
                    self.add_mh_to_qs(mh=mh_obj, qs=self.related_object.medhistorys_qs)
                self.post_process_medhistory_detail(mhtype, mh_obj)
            elif mh_obj:
                self.mhs_2_remove.append(mh_obj)
                self.post_remove_mh_from_medhistorys_qs(post_qs_target, mh_obj)

    def medhistory_needs_object_attr_update_for_any_related_object(self, mh: "MedHistory") -> bool:
        return any(
            [
                self.medhistory_needs_object_attr_update(
                    mh=mh,
                    object=related_object,
                    object_attr=related_object.__class__.__name__.lower(),
                )
                for related_object in self.related_objects
            ]
        )

    def post_process_medhistory_detail(self, mhtype: MedHistoryTypes, medhistory: Union["MedHistory", None]) -> None:
        if mhtype == MedHistoryTypes.GOUT and self.goutdetail:
            self.goutdetail_mh_post_process(
                gout=medhistory,
            )
        elif mhtype == MedHistoryTypes.CKD and self.ckddetail:
            self.ckddetail_mh_post_process(
                ckd=medhistory,
            )

    def post_process_menopause(self) -> None:
        gender = self.post_get_gender_value()
        if gender == Genders.FEMALE:
            ckd = self.post_get_ckd()
            age = self.post_get_age_value()
            if not age and not ckd:
                dateofbirth_error = ValidationError(
                    "GoutHelper needs to know the date of birth for females without CKD."
                )
                self.medhistory_forms[f"{MedHistoryTypes.MENOPAUSE}"].add_error(
                    f"{MedHistoryTypes.MENOPAUSE}-value", dateofbirth_error
                )
                self.oto_forms["dateofbirth"].add_error("value", dateofbirth_error)
                self.errors_bool = True
                return
            age = age
            if age >= 40 and age < 60:
                menopause_value = self.medhistory_forms[f"{MedHistoryTypes.MENOPAUSE}"].cleaned_data.get(
                    f"{MedHistoryTypes.MENOPAUSE}-value", None
                )
                if menopause_value is None or menopause_value == "":
                    menopause_error = ValidationError(
                        message="For females between ages 40 and 60, we need to know the patient's \
menopause status to evaluate their flare."
                    )
                    self.medhistory_forms[f"{MedHistoryTypes.MENOPAUSE}"].add_error(
                        f"{MedHistoryTypes.MENOPAUSE}-value", menopause_error
                    )
                    self.errors_bool = True

    @staticmethod
    def get_mh_cleaned_value(
        mytype: MedHistoryTypes,
        cleaned_data: dict[str, Any],
    ) -> bool:
        """Method that searches a cleaned_data dict for a value key and returns
        True if found, False otherwise."""
        value = cleaned_data.get(f"{mytype}-value", False)
        return False if value == "" else value

    def ckddetail_mh_post_process(
        self,
        ckd: "MedHistory",
    ) -> None:
        """Method to process the CkdDetailForm and BaselineCreatinineForm
        as part of the post() method."""
        dateofbirth_form = self.get_dateofbirth_form()
        gender_form = self.get_gender_form()
        ckddet_form, bc_form, errors = CkdDetailFormProcessor(
            ckd=ckd,
            ckddetail_form=self.medhistory_detail_forms["ckddetail"],
            baselinecreatinine_form=self.medhistory_detail_forms["baselinecreatinine"],
            dateofbirth=dateofbirth_form if dateofbirth_form else self.get_dateofbirth_value(),
            gender=gender_form if gender_form is not None else self.get_gender_value(),
        ).process()
        if bc_form:
            self.baselinecreatinine_form_post_process()
        if ckddet_form:
            self.ckddetail_form_post_process()
        if errors and not self.errors_bool:
            self.errors_bool = errors

    def baselinecreatinine_form_post_process(self) -> None:
        baselinecreatinine_form = self.medhistory_detail_forms["baselinecreatinine"]
        if hasattr(baselinecreatinine_form.instance, "to_save"):
            self.mhdets_2_save.append(baselinecreatinine_form)
        elif hasattr(baselinecreatinine_form.instance, "to_delete"):
            self.mhdets_2_remove.append(baselinecreatinine_form)

    def ckddetail_form_post_process(self) -> None:
        ckddetail_form = self.medhistory_detail_forms["ckddetail"]
        if hasattr(ckddetail_form.instance, "to_save"):
            self.mhdets_2_save.append(ckddetail_form)
        elif hasattr(ckddetail_form.instance, "to_delete"):
            self.mhdets_2_remove.append(ckddetail_form)

    def goutdetail_mh_post_process(
        self,
        gout: Union["MedHistory", None],
    ) -> None:
        """Method that processes the GoutDetailForm as part of the post() method."""

        gd_form = self.medhistory_detail_forms["goutdetail"]
        gd_mh = getattr(gd_form.instance, "medhistory", None)
        if gd_form.has_changed or not gd_mh:
            self.mhdets_2_save.append(gd_form.save(commit=False))
            # Check if the form instance has a medhistory attr
            if not gd_mh and gout:
                # If not, set it to the medhistory instance
                gd_form.instance.medhistory = gout

    def post_remove_mh_from_medhistorys_qs(
        self,
        post_qs_target: Union["Aids", User],
        mh_obj: "MedHistory",
    ) -> None:
        if post_qs_target == self.query_object:
            post_qs_target.medhistorys_qs.remove(mh_obj)
        else:
            self.query_object.medhistorys_qs.remove(mh_obj)

    def form_valid_update_mh_det_mh(self, mh: "MedHistory", commit: bool = True) -> None:
        """Checks if the MedHistory object has a MedHistoryDetail that needs to be saved and adjusts the set_date to
        timezone.now(), also checks if a MedHistoryDetail object that is going to be saved has a MedHistory object
        that needs to be updated and saved."""

        def need_to_save_mh(mh: "MedHistory") -> bool:
            return (self.mhs_2_save and mh not in self.mhs_2_save or not self.mhs_2_save) and (
                self.mhs_2_remove and mh not in self.mhs_2_remove or not self.mhs_2_remove
            )

        if need_to_save_mh(mh):
            mh.update_set_date_and_save(commit=commit)

    def form_valid_save_medhistorys(self) -> None:
        if self.mhs_2_save:
            if self.user:
                for mh in self.mhs_2_save:
                    if mh.user is None:
                        mh.user = self.user
                    mh.update_set_date_and_save()
            else:
                for mh in self.mhs_2_save:
                    if getattr(mh, self.object_attr, None) is None:
                        setattr(mh, self.object_attr, self.object)
                    self.form_valid_update_medhistory_related_objects(mh)
                    mh.update_set_date_and_save()

    def form_valid_update_medhistory_related_objects(self, mh: "MedHistory") -> None:
        for related_object in self.related_objects:
            related_object_attr = related_object.__class__.__name__.lower()
            if self.medhistory_compatible_with_aid_object(mh, related_object):
                if not getattr(mh, related_object_attr, None):
                    setattr(mh, related_object_attr, related_object)
                    self.add_mh_to_medhistorys_qs(mh, related_object)
                    self.add_mh_to_mhs_2_save(mh)
                else:
                    self.add_mh_to_medhistorys_qs(mh, related_object)

    @classmethod
    def add_mh_to_medhistorys_qs(cls, mh: "MedHistory", object: "Aids") -> None:
        cls.add_mh_to_qs(mh, getattr(object, "medhistorys_qs"))

    def add_mh_to_object_medhistorys_qs(self, mh: "MedHistory") -> None:
        self.add_mh_to_qs(mh, getattr(self.object, "medhistorys_qs"))

    def add_mh_to_related_object_medhistorys_qs(self, mh: "MedHistory") -> None:
        self.add_mh_to_qs(mh, getattr(self.related_object, "medhistorys_qs"))

    def add_mh_to_mhs_2_save(self, mh: "MedHistory") -> None:
        self.add_mh_to_qs(mh, self.mhs_2_save)

    @classmethod
    def medhistory_compatible_with_aid_object(cls, mh: "MedHistory", object: "Aids") -> bool:
        return (
            mh.medhistorytype in object.aid_medhistorys()
            or mh._state.adding
            and medhistorys_get_default_medhistorytype(mh) in object.aid_medhistorys()
        )

    @classmethod
    def medhistory_needs_object_attr_update(cls, mh: "MedHistory", object: "Aids", object_attr: str) -> bool:
        if not object_attr:
            object_attr = object.__class__.__name__.lower()
        return cls.medhistory_compatible_with_aid_object(mh, object) and not getattr(mh, object_attr, None)

    def form_valid_save_medhistory_details(self) -> None:
        if self.mhdets_2_save:
            for mh_det in self.mhdets_2_save:
                mh_det.save()
                self.form_valid_update_mh_det_mh(
                    mh_det.instance.medhistory if isinstance(mh_det, ModelForm) else mh_det.medhistory,
                )
                self.form_valid_update_fks_and_related_object_medhistorydetail(
                    mh_det.instance if isinstance(mh_det, ModelForm) else mh_det
                )

    def form_valid_update_fks_and_related_object_medhistorydetail(
        self, mh_detail: Union["CkdDetail", "GoutDetail"]
    ) -> None:
        for related_object in self.related_objects:
            medhistory_attr = f"{mh_detail.medhistory.medhistorytype.lower()}"
            if medhistory_attr in related_object.aid_medhistorys():
                medhistorydetail_attr = f"{mh_detail.__class__.__name__.lower()}"
                related_object_medhistory = getattr(related_object, medhistory_attr, None)
                # These are 100% necessary because of the cached_property decorator-the related medhistory (CKD, Gout)
                # references the now oudated medhistorydetail object (CKDDetail, GoutDetail)
                setattr(related_object_medhistory, medhistorydetail_attr, mh_detail)
                setattr(related_object, medhistorydetail_attr, mh_detail)

    def form_valid_delete_medhistorys(self) -> None:
        if self.mhs_2_remove:
            for mh in self.mhs_2_remove:
                mh.update_set_date_and_save(commit=False)
                mh.delete()
                self.form_valid_remove_medhistory_from_related_objects(mh)

    def form_valid_remove_medhistory_from_related_objects(self, mh: "MedHistory") -> None:
        for related_object in self.related_objects:
            if mh.medhistorytype in related_object.aid_medhistorys():
                related_object_medhistory = next(
                    iter(
                        related_mh
                        for related_mh in related_object.medhistorys_qs
                        if related_mh.medhistorytype == mh.medhistorytype
                    ),
                    None,
                )
                if related_object_medhistory:
                    related_object.medhistorys_qs.remove(related_object_medhistory)

    def form_valid_delete_medhistory_details(self) -> None:
        if self.mhdets_2_remove:
            for mh_det in self.mhdets_2_remove:
                mh_det.instance.delete()
                self.form_valid_update_mh_det_mh(
                    mh_det.instance.medhistory if isinstance(mh_det, ModelForm) else mh_det.medhistory,
                )
                self.form_valid_remove_medhistorydetails_from_related_objects(mh_det.instance)

    def form_valid_remove_medhistorydetails_from_related_objects(
        self, mh_detail: Union["CkdDetail", "GoutDetail"]
    ) -> None:
        for related_object in self.related_objects:
            medhistorydetail_attr = f"{mh_detail.__class__.__name__.lower()}"
            if hasattr(related_object, medhistorydetail_attr):
                medhistory_attr = f"{mh_detail.medhistory.medhistorytype.lower()}"
                related_object_medhistory = getattr(related_object, medhistory_attr, None)
                # These are 100% necessary because of the cached_property decorator-the related medhistory (CKD, Gout)
                # references the now deleted medhistorydetail object (CKDDetail, GoutDetail)
                setattr(related_object_medhistory, medhistorydetail_attr, None)
                setattr(related_object, medhistorydetail_attr, None)

    def validate_medhistory_form_list(self) -> bool:
        forms_valid = True
        for form in self.medhistory_forms.values():
            if not isinstance(form, ModelForm):
                continue
            elif not form.is_valid():
                forms_valid = False
        return forms_valid


class OneToOneFormMixin(GoutHelperEditMixin):
    request: "HttpRequest"

    @property
    def user_has_required_otos(self) -> bool:
        if not hasattr(self, "req_otos"):
            self.set_req_otos()
        return all(hasattr(self.user, onetoone) for onetoone in self.req_otos)

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
                    if isinstance(oto_form, ModelForm):
                        kwargs[form_str] = oto_form
                    else:
                        onetoone_form_kwargs = {
                            "instance": oto_obj if oto_obj else oto_form._meta.model(),
                            "patient": self.user,
                            "request_user": self.request_user,
                            "str_attrs": self.str_attrs,
                        }
                        onetoone_form_kwargs.update({"initial": self.get_onetoone_initial(onetoone)})
                        kwargs[form_str] = oto_form(**onetoone_form_kwargs)
        for onetoone in self.req_otos:
            if onetoone not in kwargs:
                self.context_update_onetoone(onetoone, kwargs)

    def context_update_onetoone(self, onetoone: str, kwargs: dict) -> None:
        kwargs.update({"age" if onetoone == "dateofbirth" else onetoone: self.get_onetoone_value(onetoone)})

    def dispatch_user_missing_requirements(self, request: "HttpRequest") -> bool:
        return not self.user_has_required_otos or super().dispatch_user_missing_requirements(request)

    def form_valid_init(self) -> None:
        super().form_valid_init()
        self.form_valid_save_otos()
        self.form_valid_delete_otos()
        if self.req_otos and self.related_object:
            self.form_valid_related_object_otos()

    def form_valid_save_otos(self) -> None:
        if self.oto_2_save:
            for oto in self.oto_2_save:
                oto_attr = f"{oto.__class__.__name__.lower()}"
                if self.user and oto.user is None:
                    oto.user = self.user
                oto.save()
                if getattr(self.form.instance, oto_attr, None) is None:
                    if not self.user or oto_attr == "urate" or oto_attr == "aki":
                        setattr(self.form.instance, oto_attr, oto)

    def form_valid_delete_otos(self) -> None:
        if self.oto_2_rem:
            for oto in self.oto_2_rem:
                oto_class = oto.__class__.__name__.lower()
                if not self.user or oto_class == "urate" or oto_class == "aki":
                    setattr(self.form.instance, f"{oto.__class__.__name__.lower()}", None)
                oto.delete()

    def form_valid_related_object_otos(self):
        def check_if_oto_attr_in_related_object_fields(oto_attr: str) -> bool:
            return attr_is_in_model_fields(oto_attr, self.related_object)

        for oto_attr in self.req_otos:
            related_object_oto = getattr(self.related_object, oto_attr, None)
            if (
                related_object_oto
                and check_if_oto_attr_in_related_object_fields(oto_attr)
                and getattr(self.form.instance, oto_attr, None) is None
            ):
                setattr(self.form.instance, oto_attr, related_object_oto)

    def get_onetoone_initial(self, onetoone: str) -> dict[str, Any]:
        if hasattr(self, f"get_{onetoone}_initial"):
            return getattr(self, f"get_{onetoone}_initial")()
        else:
            return {"value": self.get_onetoone_value(onetoone)}

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

    def get_gender(self) -> Union["Gender", None]:
        return getattr(self.query_object, "gender", None)

    def get_gender_value(self) -> Genders | None:
        gender = self.get_gender()
        return gender.value if gender else None

    @cached_property
    def str_attrs(self) -> dict[str, str]:
        """Returns a dict of string attributes to make forms context-sensitive."""
        return get_str_attrs(
            self.object if not self.create_view else self.get_gender_value(), self.user, self.request.user
        )

    @cached_property
    def aki(self) -> Union["Aki", None]:
        return self.get_aki()

    def get_aki(self):
        aki = getattr(self.query_object, "aki", None)
        return aki if aki else (getattr(self.object, "aki", None) if self.object else None)

    def get_aki_value(self):
        return "True" if self.aki else "False"

    def get_aki_status(self):
        return self.aki.Statuses(self.aki.status) if self.aki else None

    def get_aki_initial(self) -> dict[str, Any]:
        return {"value": self.get_aki_value(), "status": self.get_aki_status()}

    def get_urate(self) -> Union["Lab", None]:
        urate = getattr(self.query_object, "urate", None)
        return urate if urate else (getattr(self.object, "urate", None) if self.object else None)

    def get_urate_value(self):
        urate = self.get_urate()
        return urate.value if urate else None

    def post_populate_oto_forms(self) -> None:
        for onetoone, oto_form in self.oto_forms.items():
            if self.onetoone_not_attr_of_related_object(onetoone):
                oto_obj = self.get_oto_obj(onetoone) if self.query_object else None
                oto_form_kwargs = {
                    "instance": oto_obj if oto_obj else oto_form._meta.model(),
                    "patient": self.user,
                    "request_user": self.request_user,
                    "str_attrs": self.str_attrs,
                }
                oto_form_kwargs.update({"initial": self.get_onetoone_initial(onetoone=onetoone)})
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

    def onetoone_not_attr_of_related_object(self, onetoone: str) -> bool:
        return not self.related_object or (self.related_object and not getattr(self.related_object, onetoone, None))

    def post_init(self) -> None:
        super().post_init()
        self.post_populate_oto_forms()

    def post_forms_valid(self) -> bool:
        other_forms_valid = super().post_forms_valid()
        oto_forms_valid = validate_form_list(form_list=self.oto_forms.values()) if self.oto_forms else True
        return other_forms_valid and oto_forms_valid

    def post_process_forms(self) -> None:
        super().post_process_forms()
        self.post_process_oto_forms()

    def post_process_oto_forms(
        self,
    ) -> tuple[list[Model], list[Model]]:
        self.oto_2_save: list[Model] = []
        self.oto_2_rem: list[Model] = []
        for onetoone, oto_form in self.oto_forms.items():
            try:
                oto_form.check_for_value()
                # Check if the onetoone changed
                if oto_form.has_changed():
                    onetoone = oto_form.save(commit=False)
                    self.oto_2_save.append(onetoone)
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
                    self.oto_2_rem.append(oto_form.instance)


class GoutHelperUserDetailMixin(PatientSessionMixin):
    @cached_property
    def user(self) -> User | None:
        return self.object if isinstance(self.object, User) else getattr(self.object, "user", None)


class GoutHelperUserEditMixin(
    PatientSessionMixin,
    OneToOneFormMixin,
    MedHistoryFormMixin,
    MedAllergyFormMixin,
):
    """Overwritten to modify related models around a User, rather than
    a GoutHelper DecisionAid or TreatmentAid object. Also to create a user."""

    def get_dateofbirth_form(self) -> "DateOfBirthForm":
        """Overwritten to avoid returning None if there is a User as is the case for the non-User edit view."""
        return self.oto_forms["dateofbirth"]

    def get_gender_form(self) -> "GenderForm":
        """Overwritten to avoid returning None if there is a User as is the case for the non-User edit view."""
        return self.oto_forms["gender"]

    def gout_form_is_in_mhs_2_save(self) -> bool:
        return any([isinstance(mh, Gout) for mh in self.mhs_2_save])

    def form_valid(self, **kwargs) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Overwritten to facilitate creating Users."""

        def create_pseudopatient() -> Pseudopatient:
            self.form.instance.username = uuid.uuid4().hex[:30]
            self.form.instance.role = Roles.PSEUDOPATIENT
            new_goutpatient = self.form.save()
            return new_goutpatient

        def create_pseudopatientprofile() -> None:
            with transaction.atomic():
                PseudopatientProfile.objects.create(
                    user=self.object,
                    provider=self.request.user if self.provider else None,
                    provider_alias=(
                        get_provider_alias(
                            provider=self.provider,
                            age=self.post_get_age_value(),
                            gender=self.post_get_gender_value(),
                        )
                        if self.provider
                        else None
                    ),
                )

        if self.create_view:  # pylint: disable=W0125
            self.object = create_pseudopatient()
        self.user = self.object
        self.form_valid_process_related_objects()
        # Save the OneToOne related models
        if self.oto_forms:
            self.form_valid_save_otos()
            self.form_valid_delete_otos()
        if self.req_otos and self.related_object:
            self.form_valid_related_object_otos()
        if self.medhistory_forms:
            self.form_valid_save_medhistorys()
            self.form_valid_save_medhistory_details()
            self.form_valid_delete_medhistorys()
            self.form_valid_delete_medhistory_details()
        if self.medallergy_forms:
            self.form_valid_save_medallergys()
            self.form_valid_delete_medallergys()
        if self.create_view:  # pylint: disable=W0125
            create_pseudopatientprofile()
        return HttpResponseRedirect(self.get_success_url())

    def form_valid_process_related_objects(self) -> None:
        if self.related_object:
            related_objects_related_objects = list_of_objects_related_objects(self.related_object)
            for related_object in related_objects_related_objects:
                related_object_attr = self.get_related_object_attr(related_object)
                setattr(self.related_object, related_object_attr, None)
                self.update_related_object_and_otos(related_object)
                self.update_related_object_medhistorys_qs(related_object, related_object_attr)
                if hasattr(related_object, "medallergys_qs"):
                    self.update_related_object_medallergys_qs(related_object, related_object_attr)
            self.update_related_object_and_otos(self.related_object)
            self.update_related_object_medhistorys_qs(self.related_object, self.related_object_attr)

    def form_valid_update_related_object_oto_user_foreign_keys(
        self,
        related_object_oto: Any,
    ) -> None:
        if hasattr(related_object_oto, "user_foreign_key_fields"):
            for fk_field in related_object_oto.user_foreign_key_fields:
                for fk in getattr(related_object_oto, f"{fk_field}s_qs"):
                    if fk.user is None:
                        fk.user = self.user
                        fk.full_clean()
                        fk.save()

    def update_related_obj_medhistory(
        self, mh: "MedHistory", mh_related_obj: Any | None, related_object_attr: str
    ) -> None:
        if mh_related_obj is not None:
            setattr(mh, related_object_attr, None)
        if mh.user is None:
            mh.user = self.user
        if mh not in self.mhs_2_save:
            self.mhs_2_save.append(mh)

    def update_related_object_medhistorys_qs(self, related_object: Any, related_object_attr: str) -> None:
        if not hasattr(related_object, "medhistorys_qs"):
            raise AttributeError("Related object must have a medhistorys_qs attribute.")
        for mh in related_object.medhistorys_qs:
            mh_related_obj = getattr(mh, related_object_attr, None)
            if mh_related_obj is not None or mh.user is None:
                # For some reason this is needed to prevent IntegrityError when saving the MedHistory
                # TODO: learn more about editing object references between separate lists
                mh_in_mhs_2_save = next((m for m in self.mhs_2_save if m == mh), None)
                self.update_related_obj_medhistory(
                    mh_in_mhs_2_save if mh_in_mhs_2_save else mh, mh_related_obj, related_object_attr
                )

    def update_related_object_medallergys_qs(self, related_object: Any, related_object_attr: str) -> None:
        if not hasattr(related_object, "medallergys_qs"):
            raise AttributeError("Related object must have a medallergys_qs attribute.")
        if self.form_valid_need_to_set_ma_save_rem_forms():
            self.medallergy_forms = True
            self.ma_2_save = []
            self.ma_2_rem = []
        for ma in related_object.medallergys_qs:
            ma_related_obj = getattr(ma, related_object_attr, None)
            if ma_related_obj is not None or ma.user is None:
                ma_in_ma_2_save = next((m for m in self.ma_2_save if m == ma), None)
                self.update_related_obj_medallergy(
                    ma_in_ma_2_save if ma_in_ma_2_save else ma, ma_related_obj, related_object_attr
                )

    def form_valid_need_to_set_ma_save_rem_forms(self) -> bool:
        return (
            not hasattr(self, "ma_2_save")
            or not hasattr(self, "ma_2_rem")
            or not hasattr(self, "medallergy_forms")
            or hasattr(self, "medallergy_forms")
            and not self.medallergy_forms
        )

    def update_related_obj_medallergy(
        self, ma: "MedAllergy", ma_related_obj: Any | None, related_object_attr: str
    ) -> None:
        if ma_related_obj is not None:
            setattr(ma, related_object_attr, None)
        if ma.user is None:
            ma.user = self.user
        if ma not in self.ma_2_save:
            self.ma_2_save.append(ma)

    def update_related_object_and_otos(self, related_object: Any) -> None:
        if self.update_related_object_oto_fields(related_object):
            related_object.full_clean()
            related_object.save()

    def update_related_object_oto(self, related_object: Any, oto: str, related_obj_oto: Any) -> None:
        setattr(related_object, oto, None)
        self.update_related_object_oto_user(related_obj_oto)

    def update_related_object_oto_user(self, related_obj_oto: Any) -> bool:
        if related_obj_oto.user is None:
            related_obj_oto.user = self.user
            self.oto_2_save.append(related_obj_oto)
            return True
        return False

    def update_related_object_oto_fields(self, related_object: Any) -> bool:
        save_related_obj = False
        for oto in related_object.get_list_of_onetoone_fields():
            related_obj_oto = getattr(related_object, oto, None)
            if related_obj_oto:
                if oto in self.req_otos:
                    if related_obj_oto:
                        self.update_related_object_oto(related_object, oto, related_obj_oto)
                        if not save_related_obj:
                            save_related_obj = True
                    if related_object.user is None:
                        related_object.user = self.user
                        if not save_related_obj:
                            save_related_obj = True
                elif self.update_related_object_oto_user(related_obj_oto):
                    if not save_related_obj:
                        save_related_obj = True
            self.form_valid_update_related_object_oto_user_foreign_keys(related_obj_oto)
        return save_related_obj

    def form_valid_save_medhistory_details(self) -> None:
        if self.mhdets_2_save:
            for mh_det in self.mhdets_2_save:
                # Call self.gout_form_is_in_mhs_2_save() at the end of the conditional to prevent
                # IntegrityError when creating a Pseudopatient from a Flare that already has a Gout MedHistory
                if self.create_view and isinstance(mh_det, GoutDetail) and not self.gout_form_is_in_mhs_2_save():
                    mh_det.medhistory = Gout.objects.create(user=self.object)
                mh_det.save()
                self.form_valid_update_mh_det_mh(
                    mh_det.instance.medhistory if isinstance(mh_det, ModelForm) else mh_det.medhistory,
                )

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Provider the view is trying to create
        a Pseudopatient for."""
        if self.create_view:  # pylint: disable=W0125
            return self.provider_username
        else:
            return self.object

    def goutdetail_mh_context(
        self,
        kwargs: dict[str, Any],
        mh_obj: Union["MedHistory", User, None] = None,
    ) -> None:
        """Overwritten to always raise Continue, which will skip adding the GoutForm to the context."""
        if "goutdetail_form" not in kwargs:
            goutdetail_i = getattr(mh_obj, "goutdetail", None) if mh_obj else None
            goutdetail_form = self.medhistory_detail_forms["goutdetail"]
            kwargs["goutdetail_form"] = (
                goutdetail_form
                if isinstance(goutdetail_form, ModelForm)
                else goutdetail_form(
                    instance=goutdetail_i,
                    patient=self.user,
                    request_user=self.request_user,
                    str_attrs=self.str_attrs,
                )
            )
            raise Continue

    def goutdetail_mh_post_pop(
        self,
        gout: Union["MedHistory", None],
    ) -> None:
        """Overwritten to always raise Continue, which will skip adding the GoutForm to the context."""
        if gout:
            gd = getattr(gout, "goutdetail", None)
        else:
            gd = GoutDetail()
        self.medhistory_detail_forms.update(
            {
                "goutdetail": self.medhistory_detail_forms["goutdetail"](
                    self.request.POST,
                    instance=gd,
                    str_attrs=self.str_attrs,
                    patient=self.user,
                    request_user=self.request_user,
                )
            }
        )
        raise Continue

    @cached_property
    def provider_username(self) -> str | None:
        """Method that returns the username kwarg from the url."""
        return self.kwargs.get("username", None)

    @cached_property
    def provider(self) -> User | None:
        return (
            self.request.user
            if self.provider_username and self.request.user.username == self.provider_username
            else None
        )

    @cached_property
    def user(self) -> User | None:
        return None

    @cached_property
    def related_objects(self) -> list[Model]:
        return []
