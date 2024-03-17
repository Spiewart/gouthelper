from typing import TYPE_CHECKING, Any  # pylint: disable=E0013, E0015 # type: ignore

from django.apps import apps  # pylint: disable=E0401 # type: ignore
from django.contrib import messages  # pylint: disable=E0401  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # pylint: disable=E0401 # type: ignore
from django.db.models import Q  # pylint: disable=E0401 # type: ignore
from django.http import HttpResponseRedirect  # pylint: disable=E0401 # type: ignore
from django.urls import reverse  # pylint: disable=E0401  # type: ignore
from django.views.generic import (  # pylint: disable=E0401 # type: ignore
    CreateView,
    DetailView,
    TemplateView,
    UpdateView,
)
from rules.contrib.views import (  # pylint: disable=W0611, E0401  # type: ignore
    AutoPermissionRequiredMixin,
    PermissionRequiredMixin,
)

from ..contents.choices import Contexts
from ..dateofbirths.forms import DateOfBirthFormOptional
from ..dateofbirths.models import DateOfBirth
from ..genders.forms import GenderFormOptional
from ..genders.models import Gender
from ..medhistorydetails.forms import CkdDetailForm
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.forms import CkdForm, ErosionsForm, HyperuricemiaForm, TophiForm, UratestonesForm
from ..medhistorys.models import Ckd, Erosions, Hyperuricemia, Tophi, Uratestones
from ..users.models import Pseudopatient
from ..utils.views import GoutHelperAidEditMixin, PatientSessionMixin
from .forms import UltForm
from .models import Ult

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # type: ignore
    from django.db.models import QuerySet  # type: ignore

    User = get_user_model()


class UltAbout(TemplateView):
    """About page for ULTs."""

    template_name = "ults/about.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"content": self.content})
        return context

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="about", context=Contexts.ULT, tag=None)


class UltBase:
    class Meta:
        abstract = True

    form_class = UltForm
    model = Ult
    onetoones = {
        "dateofbirth": {"form": DateOfBirthFormOptional, "model": DateOfBirth},
        "gender": {"form": GenderFormOptional, "model": Gender},
    }
    medhistorys = {
        MedHistoryTypes.CKD: {
            "form": CkdForm,
            "model": Ckd,
        },
        MedHistoryTypes.EROSIONS: {
            "form": ErosionsForm,
            "model": Erosions,
        },
        MedHistoryTypes.HYPERURICEMIA: {
            "form": HyperuricemiaForm,
            "model": Hyperuricemia,
        },
        MedHistoryTypes.TOPHI: {
            "form": TophiForm,
            "model": Tophi,
        },
        MedHistoryTypes.URATESTONES: {
            "form": UratestonesForm,
            "model": Uratestones,
        },
    }
    medhistory_details = {MedHistoryTypes.CKD: CkdDetailForm}


class UltCreate(UltBase, GoutHelperAidEditMixin, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """View to create a new Ult without a user."""

    permission_required = "ults.can_add_ult"
    success_message = "ULT successfully created."

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            _,  # oto_forms,
            _,  # mh_forms,
            _,  # mh_det_forms,
            _,  # ma_forms,
            _,  # lab_formsets,
            oto_2_save,
            oto_2_rem,
            mh_2_save,
            mh_2_rem,
            mh_det_2_save,
            mh_det_2_rem,
            _,  # ma_2_save,
            _,  # ma_2_rem,
            _,  # labs_2_save,
            _,  # labs_2_rem,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        else:
            return self.form_valid(
                form=form,
                oto_2_save=oto_2_save,
                oto_2_rem=oto_2_rem,
                mh_2_save=mh_2_save,
                mh_2_rem=mh_2_rem,
                mh_det_2_save=mh_det_2_save,
                mh_det_2_rem=mh_det_2_rem,
                ma_2_save=None,
                ma_2_rem=None,
                labs_2_save=None,
                labs_2_rem=None,
            )


class UltDetailBase(AutoPermissionRequiredMixin, DetailView):
    """DetailView for Ult model."""

    class Meta:
        abstract = True

    model = Ult
    object: Ult

    @property
    def contents(self):
        return apps.get_model("contents.Content").objects.filter(Q(tag__isnull=False), context=Contexts.ULT)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        for content in self.contents:
            context.update({content.slug: {content.tag: content}})  # type: ignore
        return context

    def get_permission_object(self):
        return self.object


class UltDetail(UltDetailBase, PatientSessionMixin):
    """Overwritten for different url routing/redirecting and assigning the view object."""

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        # If the object has a user, this is the wrong view so redirect to the right one
        if self.object.user:
            return HttpResponseRedirect(self.object.get_absolute_url())
        else:
            # Check if Ult is up to date and update if not update
            if not request.GET.get("updated", None):
                self.object.update_aid(qs=self.object)
            return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Overwritten to avoid calling get_object again, which is instead
        called on dispatch()."""
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_queryset(self) -> "QuerySet[Any]":
        return Ult.related_objects.filter(pk=self.kwargs["pk"])


class UltPatientBase(UltBase):
    """Base class for UltCreate/Update views for Ults that have a user."""

    class Meta:
        abstract = True

    onetoones = {}
    req_otos = ["dateofbirth", "gender"]

    def get_user_queryset(self, username: str) -> "QuerySet[Any]":
        """Used to set the user attribute on the view, with associated related models
        select_related and prefetch_related."""
        return Pseudopatient.objects.ult_qs().filter(username=username)


class UltPseudopatientCreate(
    UltPatientBase, GoutHelperAidEditMixin, PermissionRequiredMixin, CreateView, SuccessMessageMixin
):
    """View for creating a Ult for a patient."""

    permission_required = "ults.can_add_ult"
    success_message = "%(username)s's Ult successfully created."

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Psuedopatient the view is trying to create
        a Ult for."""
        return self.user

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, username=self.user.username)

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            _,  # oto_forms,
            _,  # mh_forms,
            _,  # mh_det_forms,
            _,  # ma_forms,
            _,  # lab_formsets,
            oto_2_save,
            oto_2_rem,
            mh_2_save,
            mh_2_rem,
            mh_det_2_save,
            mh_det_2_rem,
            _,  # ma_2_save,
            _,  # ma_2_rem,
            _,  # labs_2_save,
            _,  # labs_2_rem,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        else:
            return self.form_valid(
                form=form,
                oto_2_save=oto_2_save,
                oto_2_rem=oto_2_rem,
                mh_2_save=mh_2_save,
                mh_2_rem=mh_2_rem,
                mh_det_2_save=mh_det_2_save,
                mh_det_2_rem=mh_det_2_rem,
                ma_2_save=None,
                ma_2_rem=None,
                labs_2_save=None,
                labs_2_rem=None,
            )


class UltPseudopatientDetail(UltDetailBase, PatientSessionMixin):
    """DetailView for Ults that have a user."""

    def dispatch(self, request, *args, **kwargs):
        """Redirects to the Ult CreateView if the user doesn't have a Ult. Also,
        redirects to the Pseudopatient UpdateView if the user doesn't have the required
        OneToOne models. These exceptions are raised by the get_object() method."""
        try:
            self.object = self.get_object()
        except Ult.DoesNotExist as exc:
            messages.error(request, exc.args[0])
            return HttpResponseRedirect(reverse("ults:pseudopatient-create", kwargs={"username": kwargs["username"]}))
        except (DateOfBirth.DoesNotExist, Gender.DoesNotExist):
            messages.error(request, "Baseline information is needed to use GoutHelper Decision and Treatment Aids.")
            return HttpResponseRedirect(reverse("users:pseudopatient-update", kwargs={"username": self.user.username}))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        """Overwritten to add the Ult's user to the context as 'patient'."""
        context = super().get_context_data(**kwargs)
        context["patient"] = self.user
        return context

    def get(self, request, *args, **kwargs):
        """Updates the object prior to rendering the view. Does not call get_object()."""
        if not request.GET.get("updated", None):
            self.object.update_aid(qs=self.object)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    @classmethod
    def assign_ult_attrs_from_user(cls, ult: Ult, user: "User") -> Ult:  # pylint: disable=W0613  # type: ignore
        """Method that assigns attributes from the User QuerySet to the Ult for processing
        in service methods and display in the templates. Raises DoesNotExist errors if the
        related model does not exist on the User, which are then used to redirect to the
        appropriate view."""
        ult.dateofbirth = user.dateofbirth
        ult.gender = user.gender
        ult.medhistorys_qs = user.medhistorys_qs
        return ult

    def get_queryset(self) -> "QuerySet[Any]":
        return Pseudopatient.objects.ult_qs().filter(username=self.kwargs["username"])

    def get_object(self, *args, **kwargs) -> Ult:
        self.user: User = self.get_queryset().get()  # pylint: disable=W0201 # type: ignore
        try:
            ult: Ult = self.user.ult
        except Ult.DoesNotExist as exc:
            raise Ult.DoesNotExist(f"{self.user} does not have a Ult. Create one.") from exc
        ult = self.assign_ult_attrs_from_user(ult=ult, user=self.user)
        return ult


class UltPseudopatientUpdate(
    UltPatientBase, GoutHelperAidEditMixin, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin
):
    """UpdateView for Ults with a User."""

    success_message = "%(username)s's Ult successfully updated."

    def get_permission_object(self):
        return self.object

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, username=self.user.username)

    def post(self, request, *args, **kwargs):
        """Overwritten to finish the post() method and avoid conflicts with the MRO.
        For Ult, no additional processing is needed."""
        (
            errors,
            form,
            _,  # oto_forms,
            _,  # mh_forms,
            _,  # mh_det_forms,
            _,  # ma_forms,
            _,  # lab_formsets,
            oto_2_save,
            oto_2_rem,
            mh_2_save,
            mh_2_rem,
            mh_det_2_save,
            mh_det_2_rem,
            _,  # ma_2_save,
            _,  # ma_2_rem,
            _,  # labs_2_save,
            _,  # labs_2_rem,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        else:
            return self.form_valid(
                form=form,
                oto_2_save=oto_2_save,
                oto_2_rem=oto_2_rem,
                mh_2_save=mh_2_save,
                mh_2_rem=mh_2_rem,
                mh_det_2_save=mh_det_2_save,
                mh_det_2_rem=mh_det_2_rem,
                ma_2_save=None,
                ma_2_rem=None,
                labs_2_save=None,
                labs_2_rem=None,
            )


class UltUpdate(UltBase, GoutHelperAidEditMixin, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin):
    """Updates a Ult"""

    success_message = "ULT updated successfully."

    def get_queryset(self):
        return Ult.related_objects.filter(pk=self.kwargs["pk"])

    def get_permission_object(self):
        return self.object

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            _,  # oto_forms,
            _,  # mh_forms,
            _,  # mh_det_forms,
            _,  # ma_forms,
            _,  # lab_formsets,
            oto_2_save,
            oto_2_rem,
            mh_2_save,
            mh_2_rem,
            mh_det_2_save,
            mh_det_2_rem,
            _,  # ma_2_save,
            _,  # ma_2_rem,
            _,  # labs_2_save,
            _,  # labs_2_rem,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        else:
            return self.form_valid(
                form=form,
                oto_2_rem=oto_2_rem,
                oto_2_save=oto_2_save,
                mh_2_save=mh_2_save,
                mh_2_rem=mh_2_rem,
                mh_det_2_save=mh_det_2_save,
                mh_det_2_rem=mh_det_2_rem,
                ma_2_save=None,
                ma_2_rem=None,
                labs_2_save=None,
                labs_2_rem=None,
            )
