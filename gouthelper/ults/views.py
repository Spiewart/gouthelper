from typing import TYPE_CHECKING, Any  # pylint: disable=E0013, E0015 # type: ignore

from django.apps import apps  # pylint: disable=E0401 # type: ignore
from django.contrib import messages  # pylint: disable=E0401  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # pylint: disable=E0401 # type: ignore
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
from ..dateofbirths.models import DateOfBirth
from ..genders.models import Gender
from ..labs.selectors import hyperuricemia_urates_prefetch
from ..users.models import Pseudopatient
from ..utils.helpers import get_str_attrs
from ..utils.views import MedHistoryFormMixin, OneToOneFormMixin, PatientSessionMixin
from .dicts import MEDHISTORY_DETAIL_FORMS, MEDHISTORY_FORMS, OTO_FORMS, PATIENT_OTO_FORMS, PATIENT_REQ_OTOS
from .forms import UltForm
from .models import Ult

if TYPE_CHECKING:
    from uuid import UUID

    from django.contrib.auth import get_user_model  # type: ignore
    from django.db.models import QuerySet  # type: ignore

    from ..medhistorys.models import MedHistory

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


class UltEditBase(MedHistoryFormMixin, OneToOneFormMixin):
    class Meta:
        abstract = True

    form_class = UltForm
    model = Ult

    MEDHISTORY_DETAIL_FORMS = MEDHISTORY_DETAIL_FORMS
    MEDHISTORY_FORMS = MEDHISTORY_FORMS
    OTO_FORMS = OTO_FORMS


class UltCreate(UltEditBase, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """View to create a new Ult without a user."""

    permission_required = "ults.can_add_ult"
    success_message = "ULT successfully created."

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid()


class UltDetailBase(AutoPermissionRequiredMixin, DetailView):
    """DetailView for Ult model."""

    class Meta:
        abstract = True

    model = Ult
    object: Ult

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"str_attrs": get_str_attrs(self.object, self.object.user, self.request.user)})
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


class UltPatientBase(UltEditBase):
    """Base class for UltCreate/Update views for Ults that have a user."""

    class Meta:
        abstract = True

    OTO_FORMS = PATIENT_OTO_FORMS
    REQ_OTOS = PATIENT_REQ_OTOS

    def get_user_queryset(self, pseudopatient: "UUID") -> "QuerySet[Any]":
        """Used to set the user attribute on the view, with associated related models
        select_related and prefetch_related."""
        return Pseudopatient.objects.ult_qs().filter(pk=pseudopatient)


class UltPseudopatientCreate(UltPatientBase, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """View for creating a Ult for a patient."""

    permission_required = "ults.can_add_ult"
    success_message = "%(user)s's Ult successfully created."

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Psuedopatient the view is trying to create
        a Ult for."""
        return self.user

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, user=self.user)

    def get_HYPERURICEMIA_initial_value(self, mh_object: "MedHistory") -> bool:
        # Called by get_mh_initial method in GoutHelperAidMixin
        return True if mh_object or self.user.hyperuricemia_urates else None

    def get_user_queryset(self, pseudopatient: "UUID") -> "QuerySet[Any]":
        qs = super().get_user_queryset(pseudopatient=pseudopatient)
        return qs.prefetch_related(hyperuricemia_urates_prefetch())

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid()


class UltPseudopatientDetail(UltDetailBase, PatientSessionMixin):
    """DetailView for Ults that have a user."""

    pk_url_kwarg = "pseudopatient"

    def dispatch(self, request, *args, **kwargs):
        """Redirects to the Ult CreateView if the user doesn't have a Ult. Also,
        redirects to the Pseudopatient UpdateView if the user doesn't have the required
        OneToOne models. These exceptions are raised by the get_object() method."""
        try:
            self.object = self.get_object()
        except Ult.DoesNotExist as exc:
            messages.error(request, exc.args[0])
            return HttpResponseRedirect(
                reverse("ults:pseudopatient-create", kwargs={"pseudopatient": kwargs["pseudopatient"]})
            )
        except (DateOfBirth.DoesNotExist, Gender.DoesNotExist):
            messages.error(request, "Baseline information is needed to use GoutHelper Decision and Treatment Aids.")
            return HttpResponseRedirect(reverse("users:pseudopatient-update", kwargs={"pseudopatient": self.user.pk}))
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
        return Pseudopatient.objects.ult_qs().filter(pk=self.kwargs["pseudopatient"])

    def get_object(self, *args, **kwargs) -> Ult:
        self.user: User = self.get_queryset().get()  # pylint: disable=W0201 # type: ignore
        try:
            ult: Ult = self.user.ult
        except Ult.DoesNotExist as exc:
            raise Ult.DoesNotExist(f"{self.user} does not have a Ult. Create one.") from exc
        ult = self.assign_ult_attrs_from_user(ult=ult, user=self.user)
        return ult


class UltPseudopatientUpdate(UltPatientBase, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin):
    """UpdateView for Ults with a User."""

    success_message = "%(user)s's Ult successfully updated."

    def get_permission_object(self):
        return self.object

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, user=self.user)

    def post(self, request, *args, **kwargs):
        """Overwritten to finish the post() method and avoid conflicts with the MRO.
        For Ult, no additional processing is needed."""
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid()


class UltUpdate(UltEditBase, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin):
    """Updates a Ult"""

    success_message = "ULT updated successfully."

    def get_queryset(self):
        return Ult.related_objects.filter(pk=self.kwargs["pk"])

    def get_permission_object(self):
        return self.object

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid()
