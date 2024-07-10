from typing import TYPE_CHECKING, Any

from django.apps import apps  # pylint: disable=E0401  # type: ignore
from django.contrib import messages  # pylint: disable=E0401  # type: ignore
from django.contrib.auth import get_user_model  # pylint: disable=E0401  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # pylint: disable=E0401  # type: ignore
from django.http import HttpResponseRedirect  # pylint: disable=E0401  # type: ignore
from django.urls import reverse  # pylint: disable=E0401  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.views.generic import (  # pylint: disable=E0401  # type: ignore
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
from ..flares.models import Flare
from ..genders.models import Gender
from ..users.models import Pseudopatient
from ..utils.views import GoutHelperAidEditMixin
from .dicts import (
    MEDALLERGY_FORMS,
    MEDHISTORY_DETAIL_FORMS,
    MEDHISTORY_FORMS,
    OTO_FORMS,
    PATIENT_OTO_FORMS,
    PATIENT_REQ_OTOS,
)
from .forms import FlareAidForm
from .models import FlareAid

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore

    User = get_user_model()


class FlareAidAbout(TemplateView):
    """About page for FlareAid"""

    template_name = "flareaids/about.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"content": self.content})
        return context

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="about", context=Contexts.FLAREAID, tag=None)


class FlareAidBase:
    class Meta:
        abstract = True

    form_class = FlareAidForm
    model = FlareAid
    MEDALLERGY_FORMS = MEDALLERGY_FORMS
    MEDHISTORY_FORMS = MEDHISTORY_FORMS
    MEDHISTORY_DETAIL_FORMS = MEDHISTORY_DETAIL_FORMS
    OTO_FORMS = OTO_FORMS


class FlareAidCreate(FlareAidBase, GoutHelperAidEditMixin, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """View to create a new FlareAid without a user."""

    permission_required = "flareaids.can_add_flareaid"
    success_message = "FlareAid successfully created."

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        if self.flare:
            kwargs.update({"flare": self.flare})
        return kwargs

    @cached_property
    def flare(self) -> Flare | None:
        flare_kwarg = self.kwargs.get("flare", None)
        return Flare.related_objects.get(pk=flare_kwarg) if flare_kwarg else None  # pylint: disable=W0201

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"flare": self.flare})
        return context

    def get_permission_object(self):
        if self.flare and self.flare.user:
            raise PermissionError("Trying to create a FlareAid for a Flare with a user with an anonymous view.")
        return None

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            kwargs.update({"flare": self.flare})
            return self.form_valid(**kwargs)

    @cached_property
    def related_object(self) -> Flare:
        return self.flare


class FlareAidDetailBase(AutoPermissionRequiredMixin, DetailView):
    """DetailView for FlareAids."""

    class Meta:
        abstract = True

    model = FlareAid
    object: FlareAid

    def get_permission_object(self):
        return self.object


class FlareAidDetail(FlareAidDetailBase):
    """Overwritten for different url routing/redirecting and assigning the view object."""

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        # If the object has a user, this is the wrong view so redirect to the right one
        if self.object.user:
            return HttpResponseRedirect(self.object.get_absolute_url())
        else:
            # Check if FlareAid is up to date and update if not update
            if not request.GET.get("updated", None):
                self.object.update_aid(qs=self.object)
            return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Overwritten to avoid calling get_object again, which is instead
        called on dispatch()."""
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_queryset(self) -> "QuerySet[Any]":
        return FlareAid.related_objects.filter(pk=self.kwargs["pk"])


class FlareAidPatientBase(FlareAidBase):
    class Meta:
        abstract = True

    OTO_FORMS = PATIENT_OTO_FORMS
    REQ_OTOS = PATIENT_REQ_OTOS

    def get_user_queryset(self, username: str) -> "QuerySet[Any]":
        """Used to set the user attribute on the view, with associated related models
        select_related and prefetch_related."""
        return Pseudopatient.objects.flareaid_qs().filter(username=username)


class FlareAidPseudopatientCreate(
    FlareAidPatientBase, GoutHelperAidEditMixin, PermissionRequiredMixin, CreateView, SuccessMessageMixin
):
    """View for creating a FlareAid for a patient."""

    permission_required = "flareaids.can_add_flareaid"
    success_message = "%(user)s's FlareAid successfully created."

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Psuedopatient the view is trying to create
        a FlareAid for."""
        return self.user

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, user=self.user)

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid()


class FlareAidPseudopatientDetail(FlareAidDetailBase):
    """Overwritten for different url routing, object fetching, and
    building the content data."""

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        """Overwritten to add the FlareAid's user to the context as 'patient'."""
        context = super().get_context_data(**kwargs)
        context["patient"] = self.user
        return context

    def dispatch(self, request, *args, **kwargs):
        """Redirects to the FlareAid CreateView if the user doesn't have a FlareAid. Also,
        redirects to the Pseudopatient UpdateView if the user doesn't have the required
        OneToOne models. These exceptions are raised by the get_object() method."""
        try:
            self.object = self.get_object()
        except FlareAid.DoesNotExist as exc:
            messages.error(request, exc.args[0])
            return HttpResponseRedirect(
                reverse("flareaids:pseudopatient-create", kwargs={"username": kwargs["username"]})
            )
        except (DateOfBirth.DoesNotExist, Gender.DoesNotExist):
            messages.error(request, "Baseline information is needed to use GoutHelper Decision and Treatment Aids.")
            return HttpResponseRedirect(reverse("users:pseudopatient-update", kwargs={"username": self.user.username}))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Updates the object prior to rendering the view. Does not call get_object()."""
        if not request.GET.get("updated", None):
            self.object.update_aid(qs=self.object)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def assign_flareaid_attrs_from_user(
        self, flareaid: FlareAid, user: "User"
    ) -> FlareAid:  # pylint: disable=W0201 # type: ignore
        """Method that assigns attributes from the User QuerySet to the FlareAid for processing in
        service methods and display in the templates. Raises DoesNotExist errors if the related
        model does not exist on the User, which are then used to redirect to the appropriate view."""
        flareaid.dateofbirth = user.dateofbirth
        flareaid.gender = user.gender
        flareaid.medallergys_qs = user.medallergys_qs
        flareaid.medhistorys_qs = user.medhistorys_qs
        return flareaid

    def get_queryset(self) -> "QuerySet[Any]":
        return Pseudopatient.objects.flareaid_qs().filter(username=self.kwargs["username"])

    def get_object(self, *args, **kwargs) -> FlareAid:
        self.user: "User" = self.get_queryset().get()  # pylint: disable=W0201 # type: ignore
        try:
            flareaid: FlareAid = self.user.flareaid
        except FlareAid.DoesNotExist as exc:
            raise FlareAid.DoesNotExist(f"{self.user} does not have a FlareAid. Create one.") from exc
        flareaid = self.assign_flareaid_attrs_from_user(flareaid=flareaid, user=self.user)
        return flareaid


class FlareAidPseudopatientUpdate(
    FlareAidPatientBase, GoutHelperAidEditMixin, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin
):
    success_message = "%(user)s's FlareAid successfully updated."

    def get_permission_object(self):
        return self.object

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, user=self.user)

    def post(self, request, *args, **kwargs):
        """Overwritten to finish the post() method and avoid conflicts with the MRO.
        For FlareAid, no additional processing is needed."""
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid()


class FlareAidUpdate(
    FlareAidBase, GoutHelperAidEditMixin, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin
):
    """Updates a FlareAid"""

    success_message = "FlareAid successfully updated."

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        if self.flare:
            kwargs.update({"flare": self.flare})
        return kwargs

    @cached_property
    def flare(self) -> Flare | None:
        return getattr(self.object, "flare", None)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add ultaid to context if it exists."""
        context = super().get_context_data(**kwargs)
        context.update({"flare": self.flare})
        return context

    def get_queryset(self):
        return FlareAid.related_objects.filter(pk=self.kwargs["pk"])

    def get_permission_object(self):
        return self.object

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid()

    @cached_property
    def related_object(self) -> Flare:
        return self.flare
