from typing import TYPE_CHECKING, Any

from django.apps import apps  # type: ignore
from django.contrib import messages  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # type: ignore
from django.http import HttpResponseRedirect  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView  # type: ignore
from django_htmx.http import HttpResponseClientRefresh  # type: ignore
from rules.contrib.views import AutoPermissionRequiredMixin, PermissionRequiredMixin  # type: ignore

from ..contents.choices import Contexts
from ..ppxs.models import Ppx
from ..ultaids.models import UltAid
from ..users.models import Pseudopatient
from ..utils.helpers import get_str_attrs
from ..utils.views import MedHistoryFormMixin
from .dicts import MEDHISTORY_FORMS
from .forms import GoalUrateForm
from .models import GoalUrate

if TYPE_CHECKING:
    from uuid import UUID

    from django.contrib.auth import get_user_model  # type: ignore
    from django.db.models import QuerySet  # type: ignore

    User = get_user_model()


class GoalUrateAbout(TemplateView):
    """About page for GoalUrate"""

    template_name = "goalurates/about.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"content": self.content})
        return context

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="about", context=Contexts.GOALURATE, tag=None)


class GoalUrateEditBase(MedHistoryFormMixin):
    class Meta:
        abstract = True

    form_class = GoalUrateForm
    model = GoalUrate

    MEDHISTORY_FORMS = MEDHISTORY_FORMS

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        if self.request.htmx:
            kwargs.update({"htmx": True})
        else:
            kwargs.update({"htmx": False})
        return kwargs

    def get_template_names(self) -> list[str]:
        if self.request.htmx:
            return ["goalurates/partials/goalurate_form.html"]
        return super().get_template_names()

    def post(self, request, *args, **kwargs):
        """Overwritten to finish the post() method and avoid conflicts with the MRO.
        For GoalUrate, no additional processing is needed."""
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            if request.htmx:
                kwargs.update({"htmx": HttpResponseClientRefresh()})
            return self.form_valid(**kwargs)

    @cached_property
    def ppx(self) -> Ppx | None:
        ppx_kwarg = self.kwargs.pop("ppx", None)
        return Ppx.related_objects.get(pk=ppx_kwarg) if ppx_kwarg else None

    @cached_property
    def ultaid(self) -> UltAid | None:
        ultaid_kwarg = self.kwargs.pop("ultaid", None)
        return UltAid.related_objects.get(pk=ultaid_kwarg) if ultaid_kwarg else None


class GoalUrateCreate(GoalUrateEditBase, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """Creates a new GoalUrate"""

    permission_required = "goalurates.can_add_goalurate"
    success_message = "Goal Urate created successfully!"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add ultaid to context if it exists."""
        context = super().get_context_data(**kwargs)
        context.update({"ppx": self.ppx})
        context.update({"ultaid": self.ultaid})
        return context

    def get_permission_object(self):
        if self.ultaid and self.ultaid.user:
            raise PermissionError("Trying to create a GoalUrate for a UltAid with a user with an anonymous view.")
        elif self.ppx and self.ppx.user:
            raise PermissionError("Trying to create a GoalUrate for a Ppx with a user with an anonymous view.")
        else:
            return None

    @cached_property
    def related_object(self) -> Ppx:
        return self.ppx if self.ppx else self.ultaid


class GoalUrateDetailBase(AutoPermissionRequiredMixin, DetailView):
    """Abstract base class for attrs and methods that GoalUrateDetail and
    GoalUratePseudopatientDetail inherit from."""

    class Meta:
        abstract = True

    model = GoalUrate
    object: GoalUrate

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"str_attrs": get_str_attrs(self.object, self.object.user, self.request.user)})
        return context

    def get_permission_object(self):
        return self.object


class GoalUrateDetail(GoalUrateDetailBase):
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
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
        return GoalUrate.related_objects.filter(pk=self.kwargs["pk"])


class GoalUratePatientBase(GoalUrateEditBase):
    """Abstract base class for attrs and methods that GoalUratePseudopatientCreate/Update
    inherit from."""

    class Meta:
        abstract = True

    def get_user_queryset(self, pseudopatient: "UUID") -> "QuerySet[Any]":
        return Pseudopatient.objects.goalurate_qs().filter(pk=pseudopatient)


class GoalUratePseudopatientCreate(
    GoalUratePatientBase,
    PermissionRequiredMixin,
    CreateView,
    SuccessMessageMixin,
):
    """View for creating a GoalUrate for a Pseudopatient."""

    permission_required = "goalurates.can_add_goalurate"
    success_message = "%(user)s's GoalUrate successfully created."

    def get_permission_object(self):
        # TODO: figure out if this is needed
        self.ultaid = None  # pylint: disable=W0201
        return self.user

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, user=self.user)


class GoalUratePseudopatientDetail(GoalUrateDetailBase):
    """View for displaying a GoalUrate for a Pseudopatient."""

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        """Overwritten to add the GoalUrate's user to the context as 'patient'."""
        context = super().get_context_data(**kwargs)
        context["patient"] = self.user
        return context

    def dispatch(self, request, *args, **kwargs):
        """Overwritten to check for a User on the object and redirect to the
        correct GoalUratePseudopatientCreate url instead."""
        try:
            self.object = self.get_object()
        except GoalUrate.DoesNotExist as exc:
            messages.error(request, exc.args[0])
            return HttpResponseRedirect(
                reverse("goalurates:pseudopatient-create", kwargs={"pseudopatient": kwargs["pseudopatient"]})
            )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Updates the objet prior to rendering the view."""
        # Check if GoalUrate is up to date and update if not update
        if not request.GET.get("updated", None):
            self.object.update_aid(qs=self.object)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_permission_object(self):
        return self.object

    def assign_goalurate_attrs_from_user(self, goalurate: GoalUrate, user: "User") -> GoalUrate:
        """Transfers the user's medhistorys_qs to the GoalUrate."""
        goalurate.medhistorys_qs = user.medhistorys_qs
        return goalurate

    def get_queryset(self) -> "QuerySet[Any]":
        return Pseudopatient.objects.goalurate_qs().filter(pk=self.kwargs["pseudopatient"])

    def get_object(self, *args, **kwargs) -> GoalUrate:
        """Gets the GoalUrate, sets the user attr, and also transfers the user's
        medhistorys_qs to the GoalUrate."""
        self.user: User = self.get_queryset().get()
        try:
            goalurate: GoalUrate = self.user.goalurate
        except GoalUrate.DoesNotExist as exc:
            raise GoalUrate.DoesNotExist(f"{self.user} does not have a GoalUrate. Create one.") from exc
        goalurate = self.assign_goalurate_attrs_from_user(goalurate=goalurate, user=self.user)
        return goalurate


class GoalUratePseudopatientUpdate(
    GoalUratePatientBase,
    AutoPermissionRequiredMixin,
    UpdateView,
    SuccessMessageMixin,
):
    success_message = "%(user)s's GoalUrate successfully updated."

    def get_permission_object(self):
        self.ultaid = None  # pylint: disable=W0201
        return self.object

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, user=self.user)


class GoalUrateUpdate(
    GoalUrateEditBase,
    AutoPermissionRequiredMixin,
    UpdateView,
    SuccessMessageMixin,
):
    """Creates a new GoalUrate"""

    success_message = "GoalUrate updated successfully!"

    def get_permission_object(self):
        self.ultaid = getattr(self.object, "ultaid", None)  # pylint: disable=W0201
        return self.object

    def get_queryset(self):
        return GoalUrate.related_objects.filter(pk=self.kwargs["pk"])
