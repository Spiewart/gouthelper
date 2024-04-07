from typing import TYPE_CHECKING, Any

from django.apps import apps  # type: ignore
from django.contrib import messages  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # type: ignore
from django.http import HttpResponseRedirect  # type: ignore
from django.urls import reverse  # type: ignore
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView  # type: ignore
from django_htmx.http import HttpResponseClientRefresh  # type: ignore
from rules.contrib.views import AutoPermissionRequiredMixin, PermissionRequiredMixin  # type: ignore

from ..contents.choices import Contexts
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.forms import ErosionsForm, TophiForm
from ..medhistorys.models import Erosions, Tophi
from ..ultaids.models import UltAid
from ..users.models import Pseudopatient
from ..utils.views import GoutHelperAidEditMixin
from .forms import GoalUrateForm
from .models import GoalUrate

if TYPE_CHECKING:
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


class GoalUrateBase:
    class Meta:
        abstract = True

    form_class = GoalUrateForm
    model = GoalUrate

    medhistorys = {
        MedHistoryTypes.EROSIONS: {"form": ErosionsForm, "model": Erosions},
        MedHistoryTypes.TOPHI: {"form": TophiForm, "model": Tophi},
    }


class GoalUrateEditMixin:
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
        (
            errors,
            form,
            _,  # oto_forms,
            _,  # mh_forms,
            _,  # mh_det_forms,
            _,  # ma_forms,
            _,  # lab_formsets,
            _,  # oto_2_save,
            _,  # oto_2_rem,
            mh_2_save,
            mh_2_rem,
            _,  # mh_det_2_save,
            _,  # mh_det_2_rem,
            _,  # ma_2_save,
            _,  # ma_2_rem,
            _,  # labs_2_save,
            _,  # labs_2_rem,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        else:
            kwargs.update({"ultaid": self.ultaid})
            if request.htmx:
                kwargs.update({"htmx": HttpResponseClientRefresh()})
            return self.form_valid(
                form=form,
                oto_2_save=None,
                oto_2_rem=None,
                mh_2_save=mh_2_save,
                mh_2_rem=mh_2_rem,
                mh_det_2_save=None,
                mh_det_2_rem=None,
                ma_2_save=None,
                ma_2_rem=None,
                labs_2_save=None,
                labs_2_rem=None,
                **kwargs,
            )


class GoalUrateCreate(
    GoalUrateBase, GoalUrateEditMixin, GoutHelperAidEditMixin, PermissionRequiredMixin, CreateView, SuccessMessageMixin
):
    """Creates a new GoalUrate"""

    permission_required = "goalurates.can_add_goalurate"
    success_message = "Goal Urate created successfully!"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add ultaid to context if it exists."""
        context = super().get_context_data(**kwargs)
        context.update({"ultaid": self.ultaid})
        return context

    def get_permission_object(self):
        ultaid_kwarg = self.kwargs.get("ultaid", None)
        self.ultaid = (  # pylint: disable=W0201
            UltAid.objects.select_related("user").get(pk=ultaid_kwarg) if ultaid_kwarg else None
        )
        if self.ultaid and self.ultaid.user:
            raise PermissionError("Trying to create a GoalUrate for a UltAid with a user with an anonymous view.")
        return self.ultaid.user if self.ultaid else None


class GoalUrateDetailBase(AutoPermissionRequiredMixin, DetailView):
    """Abstract base class for attrs and methods that GoalUrateDetail and
    GoalUratePseudopatientDetail inherit from."""

    class Meta:
        abstract = True

    model = GoalUrate
    object: GoalUrate

    @property
    def contents(self):
        return apps.get_model("contents.Content").objects.filter(context=Contexts.GOALURATE, tag__isnull=False)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        for content in self.contents:
            context.update({content.slug: {content.tag: content}})  # type: ignore
        return context

    def get_permission_object(self):
        return self.object


class GoalUrateDetail(GoalUrateDetailBase):
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Check if the object has a User and if there is no username in the kwargs,
        # redirect to the username url
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


class GoalUratePatientBase(GoalUrateBase):
    """Abstract base class for attrs and methods that GoalUratePseudopatientCreate/Update
    inherit from."""

    class Meta:
        abstract = True

    onetoones = {}
    req_otos = []

    def get_user_queryset(self, username: str) -> "QuerySet[Any]":
        return Pseudopatient.objects.goalurate_qs().filter(username=username)


class GoalUratePseudopatientCreate(
    GoalUratePatientBase,
    GoalUrateEditMixin,
    GoutHelperAidEditMixin,
    PermissionRequiredMixin,
    CreateView,
    SuccessMessageMixin,
):
    """View for creating a GoalUrate for a Pseudopatient."""

    permission_required = "goalurates.can_add_goalurate"
    success_message = "%(username)s's GoalUrate successfully created."

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Psuedopatient the view is trying to create
        a FlareAid for."""
        self.ultaid = None  # pylint: disable=W0201
        return self.user

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, username=self.user.username)


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
                reverse("goalurates:pseudopatient-create", kwargs={"username": kwargs["username"]})
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
        return Pseudopatient.objects.goalurate_qs().filter(username=self.kwargs["username"])

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
    GoalUrateEditMixin,
    GoutHelperAidEditMixin,
    AutoPermissionRequiredMixin,
    UpdateView,
    SuccessMessageMixin,
):
    success_message = "%(username)s's GoalUrate successfully created."

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Psuedopatient the view is trying to create
        a FlareAid for."""
        self.ultaid = None  # pylint: disable=W0201
        return self.object

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, username=self.user.username)


class GoalUrateUpdate(
    GoalUrateBase,
    GoalUrateEditMixin,
    GoutHelperAidEditMixin,
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
