from typing import TYPE_CHECKING, Any

from django.apps import apps  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.views.generic import CreateView, TemplateView, UpdateView  # type: ignore
from django_htmx.http import HttpResponseClientRefresh  # type: ignore
from rules.contrib.views import AutoPermissionRequiredMixin, PermissionRequiredMixin  # type: ignore

from ..contents.choices import Contexts
from ..ppxs.models import Ppx
from ..ultaids.models import UltAid
from ..users.models import Pseudopatient
from ..utils.views import GoutHelperDetailMixin, GoutHelperPseudopatientDetailMixin, MedHistoryFormMixin
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


class GoalUrateDetail(GoutHelperDetailMixin):
    model = GoalUrate
    object: GoalUrate


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


class GoalUratePseudopatientDetail(GoutHelperPseudopatientDetailMixin):
    model = GoalUrate
    object: GoalUrate


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
