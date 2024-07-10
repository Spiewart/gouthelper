from datetime import timedelta
from typing import TYPE_CHECKING, Any, Union  # pylint: disable=E0015, E0013 # type: ignore

from django.apps import apps  # pylint: disable=e0401 # type: ignore
from django.contrib import messages  # pylint: disable=e0401 # type: ignore
from django.contrib.auth import get_user_model  # pylint: disable=e0401 # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # pylint: disable=e0401 # type: ignore
from django.core.exceptions import ValidationError  # pylint: disable=e0401 # type: ignore
from django.http import Http404, HttpResponseRedirect  # pylint: disable=e0401 # type: ignore
from django.urls import reverse  # pylint: disable=e0401 # type: ignore
from django.utils.functional import cached_property  # pylint: disable=e0401 # type: ignore
from django.views.generic import (  # pylint: disable=e0401 # type: ignore
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)
from rules.contrib.views import (  # pylint: disable=e0401 # type: ignore
    AutoPermissionRequiredMixin,
    PermissionRequiredMixin,
)

from ..akis.choices import Statuses
from ..akis.services import AkiProcessor
from ..contents.choices import Contexts
from ..dateofbirths.models import DateOfBirth
from ..genders.models import Gender
from ..labs.helpers import (
    labs_formset_has_one_or_more_valid_labs,
    labs_formset_order_by_date_drawn_remove_deleted_and_blank_forms,
    labs_get_list_of_instances_from_list_of_forms_cleaned_data,
)
from ..labs.models import Creatinine
from ..medhistorys.choices import MedHistoryTypes
from ..users.models import Pseudopatient
from ..utils.helpers import get_str_attrs
from ..utils.views import LabFormSetsMixin, MedHistoryFormMixin, OneToOneFormMixin
from .dicts import (
    LAB_FORMSETS,
    MEDHISTORY_DETAIL_FORMS,
    MEDHISTORY_FORMS,
    OTO_FORMS,
    PATIENT_MEDHISTORY_FORMS,
    PATIENT_OTO_FORMS,
    PATIENT_REQ_OTOS,
    REQ_OTOS,
)
from .forms import FlareForm
from .models import Flare

if TYPE_CHECKING:
    from decimal import Decimal

    from django.db.models import QuerySet  # type: ignore
    from django.forms import ModelForm  # type: ignore

    from ..labs.models import BaselineCreatinine

User = get_user_model()


class FlareAbout(TemplateView):
    """About Flares"""

    template_name = "flares/about.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"content": self.content})
        return context

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="about", context=Contexts.FLARE, tag=None)


class FlareEditBase(LabFormSetsMixin, MedHistoryFormMixin, OneToOneFormMixin):
    class Meta:
        abstract = True

    form_class = FlareForm
    model = Flare
    success_message = "Flare created successfully!"

    LAB_FORMSETS = LAB_FORMSETS
    MEDHISTORY_FORMS = MEDHISTORY_FORMS
    MEDHISTORY_DETAIL_FORMS = MEDHISTORY_DETAIL_FORMS
    OTO_FORMS = OTO_FORMS
    REQ_OTOS = REQ_OTOS

    @cached_property
    def creatinine_formset_qs(self):
        return (
            Creatinine.objects.filter(aki=self.object.aki)
            if hasattr(self.object, "aki")
            else Creatinine.objects.none()
        )

    def post_process_aki(self) -> None:
        creatinine_formsets = self.lab_formsets["creatinine"][0]
        aki_form, aki, status = self.get_aki_form_value_and_status()
        if labs_formset_has_one_or_more_valid_labs(creatinine_formsets):
            ckd = self.get_ckd()
            baselinecreatinine = self.get_baselinecreatinine() if ckd else None
            stage = self.get_stage(ckd)
            ordered_creatinine_formset = labs_formset_order_by_date_drawn_remove_deleted_and_blank_forms(
                creatinine_formsets
            )
            if not self.creatinines_date_drawns_are_out_of_bounds(ordered_creatinine_formset):
                ordered_list_of_creatinines = labs_get_list_of_instances_from_list_of_forms_cleaned_data(
                    ordered_creatinine_formset
                )
                processor = AkiProcessor(
                    aki_value=aki,
                    status=status,
                    creatinines=ordered_list_of_creatinines,
                    baselinecreatinine=(baselinecreatinine if baselinecreatinine else None),
                    stage=stage,
                )
                if status is not None and status != "":
                    aki_creatinine_errors = processor.get_errors()
                    if aki_creatinine_errors:
                        self.set_aki_creatinines_errors(aki_creatinine_errors)
                else:
                    status = processor.get_status()
                    aki_form.instance.status = status
        elif aki and (status is None or status == ""):
            aki_form.cleaned_data["status"] = Statuses.ONGOING
            aki_form.instance.status = Statuses.ONGOING

    def get_aki_form_value_and_status(self) -> tuple["ModelForm", bool, Union["Statuses", None]]:
        form = self.oto_forms["aki"]
        return form, form.cleaned_data.get("value", None), form.cleaned_data.get("status", None)

    def get_baselinecreatinine(self) -> Union["BaselineCreatinine", None]:
        form = self.medhistory_detail_forms["baselinecreatinine"]
        return form.instance if (hasattr(form, "cleaned_data") and form.cleaned_data.get("value", False)) else None

    def get_ckd(self):
        ckd_form = self.medhistory_forms[MedHistoryTypes.CKD]
        return (
            ckd_form.cleaned_data.get(f"{MedHistoryTypes.CKD}-value", None)
            if hasattr(ckd_form, "cleaned_data")
            else None
        )
        # TODO - WRITE TEST FOR THESE METHODS

    def get_stage(self, ckd):
        if ckd:
            form = self.medhistory_detail_forms["ckddetail"]
            return form.cleaned_data.get("stage", None) if hasattr(form, "cleaned_data") else None
        return None

    def set_aki_creatinines_errors(self, errors: dict) -> None:
        for form_key, error_dict in errors.items():
            if form_key in self.oto_forms:
                for error_key, error in error_dict.items():
                    self.oto_forms[form_key].add_error(error_key, error)
            elif form_key in self.lab_formsets:
                for error_key, error in error_dict.items():
                    self.lab_formsets[form_key][0][0].add_error(error_key, error)
            self.set_errors_bool_True()

    def creatinine_date_drawn_out_of_bounds(self, creatinine: "Creatinine") -> bool:
        return (
            creatinine.date_drawn.date() < self.object.date_started - timedelta(days=15)
            or self.object.date_ended
            and creatinine.date_drawn.date() > self.object.date_ended
        )

    def creatinines_date_drawns_are_out_of_bounds(self, creatinine_forms: list["ModelForm"]) -> bool:
        """Compares Creatinines date_drawn field to Flare date_started and date_ended fields."""
        out_of_bounds_error = False
        for form in creatinine_forms:
            if self.creatinine_date_drawn_out_of_bounds(form.instance):
                message = (
                    f"Creatinine wasn't close enough ({form.instance.date_drawn.date()}) to "
                    f"the Flare's symptoms {self.object.dates} to be relevent."
                )
                form.add_error("date_drawn", ValidationError(message=message))
                out_of_bounds_error = True
        if out_of_bounds_error and not self.errors_bool:
            self.errors_bool = True
        return out_of_bounds_error

    def post_process_urate_check(self) -> None:
        urate_form, urate_val = self.get_urate_form_and_value()
        urate_check = self.form.cleaned_data.get("urate_check", None)
        if urate_check and not urate_val:
            urate_error = ValidationError(
                message="If the serum uric acid was checked, please tell us the value! \
If you don't know the value, please uncheck the Uric Acid Lab Check box."
            )
            self.form.add_error("urate_check", urate_error)
            urate_form.add_error("value", urate_error)
            self.set_errors_bool_True()

    def get_urate_form_and_value(self) -> Union["ModelForm", Union["Decimal", None]]:
        form = self.oto_forms["urate"]
        return form, form.cleaned_data.get("value", None)


class FlareAnonEditBase(FlareEditBase):
    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        self.post_process_aki()
        # Compare creatinine date_drawns to Flare date_started and date_ended
        self.post_process_menopause()
        self.post_process_urate_check()
        # Compare urate date_drawn to flare_date_started and date_ended
        if self.errors or self.errors_bool:
            if self.errors_bool and not self.errors:
                return super().render_errors()
            else:
                return self.errors
        else:
            return self.form_valid()


class FlareCreate(FlareAnonEditBase, AutoPermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """Creates a new Flare"""

    success_message = "Flare created successfully!"

    @cached_property
    def creatinine_formset_qs(self):
        return Creatinine.objects.none()

    def get_initial(self) -> dict[str, Any]:
        initial = super().get_initial()
        initial["onset"] = None
        initial["redness"] = None
        return initial


class FlareDetailBase(AutoPermissionRequiredMixin, DetailView):
    class Meta:
        abstract = True

    model = Flare
    object: Flare

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"str_attrs": get_str_attrs(self.object, self.object.user, self.request.user)})
        return context

    def get_permission_object(self):
        return self.object


class FlareDetail(FlareDetailBase):
    """View for viewing a Flare"""

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Check if the object has a User and if there is no username in the kwargs,
        # redirect to the username url
        if self.object.user:
            return HttpResponseRedirect(self.object.get_absolute_url())
        else:
            # Check if Flare is up to date and update if not update
            if not request.GET.get("updated", None):
                self.object.update_aid(qs=self.object)
            return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not hasattr(self, "object"):
            self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_queryset(self) -> "QuerySet[Any]":
        return Flare.related_objects.filter(pk=self.kwargs["pk"])


class FlarePatientEditBase(FlareEditBase):
    MEDHISTORY_FORMS = PATIENT_MEDHISTORY_FORMS
    OTO_FORMS = PATIENT_OTO_FORMS
    REQ_OTOS = PATIENT_REQ_OTOS

    def get_user_queryset(self, username: str) -> "QuerySet[Any]":
        """Used to set the user attribute on the view, with associated related models
        select_related and prefetch_related."""
        return Pseudopatient.objects.flares_qs(flare_pk=self.kwargs.get("pk")).filter(  # pylint:disable=E1101
            username=username
        )

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, user=self.user)

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        self.post_process_aki()
        # Compare creatinine date_drawns to Flare date_started and date_ended
        self.post_process_urate_check()
        # Compare urate date_drawn to flare_date_started and date_ended
        # Compare Flare date_started and date_ended to other Flares for the same user
        if self.errors or self.errors_bool:
            if self.errors_bool and not self.errors:
                return super().render_errors()
            else:
                return self.errors
        else:
            return self.form_valid()

    def compare_flare_dates_to_other_flares_for_user(self) -> None:
        pass


class FlarePseudopatientList(PermissionRequiredMixin, ListView):
    context_object_name = "flares"
    model = Flare
    permission_required = "flares.can_view_flare_list"
    template_name = "flares/flare_list.html"

    def dispatch(self, request, *args, **kwargs):
        self.user = self.get_queryset().get()
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.object_list = self.user.flares_qs
        context = self.get_context_data()
        return self.render_to_response(context)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["patient"] = Pseudopatient.objects.get(username=self.kwargs["username"])
        return context

    def get_permission_object(self):
        return self.user

    def get_queryset(self):
        return Pseudopatient.objects.flares_qs().filter(username=self.kwargs["username"])


class FlarePseudopatientCreate(FlarePatientEditBase, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """View for creating a Flare for a patient."""

    permission_required = "flares.can_add_flare"
    success_message = "%(user)s's Flare successfully created."

    def get_initial(self) -> dict[str, Any]:
        initial = super().get_initial()
        initial["onset"] = None
        initial["redness"] = None
        return initial


class FlarePseudopatientDelete(AutoPermissionRequiredMixin, DeleteView, SuccessMessageMixin):
    """View for deleting a Flare for a patient."""

    model = Flare
    success_message = "%(user)s's Flare successfully deleted."

    def dispatch(self, request, *args, **kwargs):
        # Set the user and object with get_object()
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, *args, **kwargs) -> Flare:
        """Overwritten to set the user attr on the view."""
        try:
            self.user: User = self.get_queryset().get()
        except User.DoesNotExist as exc:
            raise Http404(f"User with username {self.kwargs['username']} does not exist.") from exc
        try:
            flare: Flare = self.user.flare_qs[0]
        except IndexError as exc:
            raise Http404(f"Flare for {self.user} does not exist.") from exc
        return flare

    def get_permission_object(self):
        return self.object

    def get_success_url(self) -> str:
        return reverse("flares:pseudopatient-list", kwargs={"username": self.object.user.username})

    def get_queryset(self) -> "QuerySet[Any]":
        return Pseudopatient.objects.flares_qs(flare_pk=self.kwargs["pk"]).filter(username=self.kwargs["username"])


class FlarePseudopatientDetail(FlareDetailBase):
    """Overwritten for different url routing, object fetching, and
    building the content data."""

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["patient"] = self.user
        return context

    def dispatch(self, request, *args, **kwargs):
        """Overwritten to check for a User on the object and redirect to the
        correct FlarePseudopatientCreate url instead. Also checks if the user has
        the correct OneToOne models and redirects to the view to add them if not."""
        try:
            self.object = self.get_object()
        except (DateOfBirth.DoesNotExist, Gender.DoesNotExist):
            messages.error(request, "Baseline information is needed to use GoutHelper Decision and Treatment Aids.")
            return HttpResponseRedirect(reverse("users:pseudopatient-update", kwargs={"username": self.user.username}))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Check if Flare is up to date and update if not update
        if not request.GET.get("updated", None):
            self.object.update_aid(qs=self.object)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def assign_flare_attrs_from_user(self, flare: Flare, user: "User") -> Flare:
        flare.dateofbirth = user.dateofbirth
        flare.gender = user.gender
        flare.medhistorys_qs = user.medhistorys_qs
        return flare

    def get_queryset(self) -> "QuerySet[Any]":
        return Pseudopatient.objects.flares_qs(flare_pk=self.kwargs["pk"]).filter(username=self.kwargs["username"])

    def get_object(self, *args, **kwargs) -> Flare:
        try:
            self.user: User = self.get_queryset().get()
        except User.DoesNotExist as exc:
            raise Http404(f"User with username {self.kwargs['username']} does not exist.") from exc
        try:
            flare: Flare = self.user.flare_qs[0]
        except IndexError as exc:
            raise Http404(f"Flare for {self.user} does not exist.") from exc
        flare = self.assign_flare_attrs_from_user(flare=flare, user=self.user)
        return flare


class FlareUpdateMixin:
    def get_initial(self) -> dict[str, Any]:
        """Overwrite get_initial() to populate form non-field field inputs"""
        initial = super().get_initial()
        aki = getattr(self.object, "aki")
        crystal_analysis = getattr(self.object, "crystal_analysis")
        diagnosed = getattr(self.object, "diagnosed")
        urate = getattr(self.object, "urate")
        if aki or crystal_analysis is not None or diagnosed is not None or urate is not None:
            initial["medical_evaluation"] = True
            if crystal_analysis is not None:
                initial["aspiration"] = True
            else:
                initial["aspiration"] = False
            if urate is not None:
                initial["urate_check"] = True
            else:
                initial["urate_check"] = False
        else:
            initial["medical_evaluation"] = False
            initial["aspiration"] = None
            initial["diagnosed"] = None
            initial["urate_check"] = None
        return initial


class FlarePseudopatientUpdate(
    FlareUpdateMixin,
    FlarePatientEditBase,
    PermissionRequiredMixin,
    UpdateView,
    SuccessMessageMixin,
):
    permission_required = "flares.can_change_flare"
    success_message = "%(user)s's FlareAid successfully updated."

    @cached_property
    def creatinine_formset_qs(self):
        return (
            Creatinine.objects.filter(aki=self.object.aki).order_by("-date_drawn")
            if hasattr(self.object, "aki")
            else Creatinine.objects
        )


class FlareUpdate(
    FlareUpdateMixin,
    FlareAnonEditBase,
    AutoPermissionRequiredMixin,
    UpdateView,
    SuccessMessageMixin,
):
    """Updates a Flare"""

    success_message = "Flare updated successfully!"

    @cached_property
    def creatinine_formset_qs(self):
        return (
            Creatinine.objects.filter(aki=self.object.aki).order_by("-date_drawn")
            if hasattr(self.object, "aki")
            else Creatinine.objects
        )

    def get_queryset(self):
        return Flare.related_objects.filter(pk=self.kwargs["pk"])
