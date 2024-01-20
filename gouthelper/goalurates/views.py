from typing import TYPE_CHECKING, Any, Union

from django.apps import apps  # type: ignore
from django.contrib import messages  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # type: ignore
from django.http import HttpResponseRedirect  # type: ignore
from django.urls import reverse  # type: ignore
from django.views.generic import DetailView, TemplateView, View  # type: ignore
from django_htmx.http import HttpResponseClientRefresh  # type: ignore
from rules.contrib.views import AutoPermissionRequiredMixin, PermissionRequiredMixin  # type: ignore

from ..contents.choices import Contexts
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.forms import ErosionsForm, TophiForm
from ..medhistorys.models import Erosions, Tophi
from ..utils.views import (
    MedHistorysModelCreateView,
    MedHistorysModelUpdateView,
    PatientAidCreateView,
    PatientAidUpdateView,
)
from .forms import GoalUrateForm
from .models import GoalUrate
from .selectors import goalurate_user_qs, goalurate_userless_qs

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # type: ignore
    from django.db.models import Model, QuerySet  # type: ignore
    from django.http import HttpResponse  # type: ignore

    from ..labs.models import BaselineCreatinine, Lab
    from ..medallergys.models import MedAllergy
    from ..medhistorydetails.forms import CkdDetailForm, GoutDetailForm
    from ..medhistorys.models import MedHistory

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


class GoalUrateBase(View):
    class Meta:
        abstract = True

    form_class = GoalUrateForm
    model = GoalUrate

    medhistorys = {
        MedHistoryTypes.EROSIONS: {"form": ErosionsForm, "model": Erosions},
        MedHistoryTypes.TOPHI: {"form": TophiForm, "model": Tophi},
    }


class GoalUrateCreate(GoalUrateBase, MedHistorysModelCreateView, SuccessMessageMixin):
    """Creates a new GoalUrate"""

    success_message = "Goal Urate created successfully!"

    def form_valid(
        self,
        form: GoalUrateForm,
        onetoones_to_save: list["Model"],
        medhistorydetails_to_save: list["CkdDetailForm", "BaselineCreatinine", "GoutDetailForm"],
        medallergys_to_save: list["MedAllergy"],
        medhistorys_to_save: list["MedHistory"],
        labs_to_save: list["Lab"],
        **kwargs,
    ) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Overwritten to redirect appropriately and to add ultaid to form instance if it exists."""
        ultaid = self.kwargs.get("ultaid", None)
        if ultaid:
            form.instance.ultaid_id = ultaid
        # Object will be returned by the super().form_valid() call
        self.object = super().form_valid(
            form=form,
            onetoones_to_save=onetoones_to_save,
            medhistorydetails_to_save=medhistorydetails_to_save,
            medallergys_to_save=medallergys_to_save,
            medhistorys_to_save=medhistorys_to_save,
            labs_to_save=labs_to_save,
            **kwargs,
        )
        # Update object / form instance
        self.object.update(qs=self.object)
        # If request is an htmx request, return HttpResponseClientRefresh
        # Will reload related model DetailPage
        if self.request.htmx:
            return HttpResponseClientRefresh()
        return HttpResponseRedirect(self.get_success_url())

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        if self.request.htmx:
            kwargs.update({"htmx": True})
        else:
            kwargs.update({"htmx": False})
        return kwargs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add ultaid to context if it exists."""
        context = super().get_context_data(**kwargs)
        ultaid = self.kwargs.get("ultaid", None)
        if ultaid and "ultaid" not in context:
            context["ultaid"] = ultaid
        return context

    def get_template_names(self) -> list[str]:
        if self.request.htmx:
            return ["goalurates/partials/goalurate_form.html"]
        return super().get_template_names()

    def post(self, request, *args, **kwargs):
        try:
            kwargs.pop("ultaid")
        except KeyError:
            pass
        (
            errors,
            form,
            _,  # object_data
            _,  # onetoone_forms
            _,  # medallergys_forms
            _,  # medhistorys_forms
            _,  # medhistorydetails_forms
            _,  # lab_formset
            onetoones_to_save,
            medallergys_to_save,
            medhistorys_to_save,
            medhistorydetails_to_save,
            labs_to_save,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        else:
            return self.form_valid(
                form=form,  # type: ignore
                medallergys_to_save=medallergys_to_save,
                onetoones_to_save=onetoones_to_save,
                medhistorydetails_to_save=medhistorydetails_to_save,
                medhistorys_to_save=medhistorys_to_save,
                labs_to_save=labs_to_save,
            )


class GoalUrateDetailBase(DetailView):
    """Abstract base class for attrs and methods that GoalUrateDetail and
    GoalUratePseudopatientDetail inherit from."""

    class Meta:
        abstract = True

    model = GoalUrate
    object: GoalUrate

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        for content in self.contents:
            context.update({content.slug: {content.tag: content}})  # type: ignore
        return context

    @property
    def contents(self):
        return apps.get_model("contents.Content").objects.filter(context=Contexts.GOALURATE, tag__isnull=False)


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
                self.object.update(qs=self.object)
                return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Overwritten to avoid calling get_object again, which is instead
        called on dispatch()."""
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_queryset(self) -> "QuerySet[Any]":
        return goalurate_userless_qs(self.kwargs["pk"])


class GoalUrateUpdate(GoalUrateBase, MedHistorysModelUpdateView, SuccessMessageMixin):
    """Creates a new GoalUrate"""

    success_message = "GoalUrate updated successfully!"

    def form_valid(
        self,
        form,
        onetoones_to_save: list["Model"] | None,
        onetoones_to_delete: list["Model"] | None,
        medhistorydetails_to_save: list["CkdDetailForm", "BaselineCreatinine", "GoutDetailForm"] | None,
        medhistorydetails_to_remove: list["CkdDetailForm", "BaselineCreatinine", "GoutDetailForm"] | None,
        medallergys_to_save: list["MedAllergy"] | None,
        medallergys_to_remove: list["MedAllergy"] | None,
        medhistorys_to_save: list["MedHistory"] | None,
        medhistorys_to_remove: list["MedHistory"] | None,
        labs_to_save: list["Lab"] | None,
        labs_to_remove: list["Lab"] | None,
    ) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Overwritten to redirect appropriately and update the form instance."""

        self.object = super().form_valid(
            form=form,
            onetoones_to_save=onetoones_to_save,
            onetoones_to_delete=onetoones_to_delete,
            medhistorys_to_save=medhistorys_to_save,
            medhistorys_to_remove=medhistorys_to_remove,
            medhistorydetails_to_save=medhistorydetails_to_save,
            medhistorydetails_to_remove=medhistorydetails_to_remove,
            medallergys_to_save=medallergys_to_save,
            medallergys_to_remove=medallergys_to_remove,
            labs_to_save=labs_to_save,
            labs_to_remove=labs_to_remove,
        )
        # Update the DecisionAidModel by calling the update method with the QuerySet
        # of the object, which will hopefully have been annotated by the view to
        # include the related models
        self.object.update(qs=self.object)
        if self.request.htmx:
            return HttpResponseClientRefresh()
        # Add a querystring to the success_url to trigger the DetailView to NOT re-update the object
        return HttpResponseRedirect(self.get_success_url() + "?updated=True")

    def get(self, request, *args, **kwargs):
        """Overwritten to check for a User on the object and redirect to the
        correct FlareAidPseudopatientUpdate url instead."""
        self.object = self.get_object()
        if self.object.user:
            return HttpResponseRedirect(
                reverse("goalurates:pseudopatient-update", kwargs={"username": self.object.user.username})
            )
        return self.render_to_response(self.get_context_data())

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        if self.request.htmx:
            kwargs.update({"htmx": True})
        else:
            kwargs.update({"htmx": False})
        return kwargs

    def get_queryset(self):
        return goalurate_userless_qs(self.kwargs["pk"])

    def get_template_names(self) -> list[str]:
        if self.request.htmx:
            return ["goalurates/partials/goalurate_form.html"]
        return super().get_template_names()

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            _,  # onetoone_forms
            _,  # medallergys_forms
            _,  # medhistorys_forms
            _,  # medhistorydetails_forms
            _,  # lab_formset
            _,  # onetoones_to_delete,
            _,  # onetoones_to_save,
            _,  # medallergys_to_save,
            _,  # medallergys_to_remove,
            medhistorys_to_save,
            medhistorys_to_remove,
            _,  # medhistorydetails_to_save,
            _,  # medhistorydetails_to_remove,
            _,  # labs_to_save,
            _,  # labs_to_remove,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        else:
            return self.form_valid(
                form=form,  # type: ignore
                onetoones_to_delete=None,
                onetoones_to_save=None,
                medhistorys_to_save=medhistorys_to_save,
                medhistorys_to_remove=medhistorys_to_remove,
                medhistorydetails_to_save=None,
                medhistorydetails_to_remove=None,
                medallergys_to_save=None,
                medallergys_to_remove=None,
                labs_to_save=None,
                labs_to_remove=None,
            )


class GoalUratePatientBase(GoalUrateBase):
    """Abstract base class for attrs and methods that GoalUratePseudopatientCreate/Update
    inherit from."""

    class Meta:
        abstract = True

    onetoones = {}
    req_onetoones = []

    def get_user_queryset(self, username: str) -> "QuerySet[Any]":
        return goalurate_user_qs(username=username)


class GoalUratePseudopatientCreate(
    PermissionRequiredMixin, GoalUratePatientBase, PatientAidCreateView, SuccessMessageMixin
):
    """View for creating a GoalUrate for a Pseudopatient."""

    permission_required = "goalurates.can_add_pseudopatient_goalurate"
    success_message = "%(username)s's GoalUrate successfully created."

    def dispatch(self, request, *args, **kwargs):
        """Overwritten to check for a User on the object and redirect to the
        correct GoalUratePseudopatientUpdate url instead."""
        # For CreateView, self.object is set to the Model class being created
        # Also sets the user attribute on the view
        self.object = self.get_object()
        if hasattr(self.user, "goalurate"):
            messages.error(request, f"{self.user} already has a {self.object.__name__}. Please update it instead.")
            view_str = "goalurates:pseudopatient-detail"
            return HttpResponseRedirect(reverse(view_str, kwargs={"username": self.user.username}))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(
        self,
        form,
        onetoones_to_save: list["Model"] | None,
        onetoones_to_delete: list["Model"] | None,
        medhistorydetails_to_save: list["CkdDetailForm", "BaselineCreatinine", "GoutDetailForm"] | None,
        medhistorydetails_to_remove: list["CkdDetailForm", "BaselineCreatinine", "GoutDetailForm"] | None,
        medallergys_to_save: list["MedAllergy"] | None,
        medallergys_to_remove: list["MedAllergy"] | None,
        medhistorys_to_save: list["MedHistory"] | None,
        medhistorys_to_remove: list["MedHistory"] | None,
        labs_to_save: list["Lab"] | None,
        labs_to_remove: list["Lab"] | None,
    ) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Overwritten to redirect appropriately and update the form instance."""
        form = super().form_valid(
            form=form,
            onetoones_to_save=onetoones_to_save,
            onetoones_to_delete=onetoones_to_delete,
            medhistorys_to_save=medhistorys_to_save,
            medhistorys_to_remove=medhistorys_to_remove,
            medhistorydetails_to_save=medhistorydetails_to_save,
            medhistorydetails_to_remove=medhistorydetails_to_remove,
            medallergys_to_save=medallergys_to_save,
            medallergys_to_remove=medallergys_to_remove,
            labs_to_save=labs_to_save,
            labs_to_remove=labs_to_remove,
        )
        goalurate = form.save()
        # Add the relationship to the existing user object so that user
        # can be used as the QuerySet for the update method
        self.user.goalurate = goalurate
        # Update object / form instance
        goalurate.update(qs=self.user)
        # Add a querystring to the success_url to trigger the DetailView to NOT re-update the object
        return HttpResponseRedirect(goalurate.get_absolute_url() + "?updated=True")

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Psuedopatient the view is trying to create
        a FlareAid for."""
        return self.user

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, username=self.user.username)

    def post(self, request, *args, **kwargs):
        """Overwritten to finish the post() method and avoid conflicts with the MRO.
        For GoalUrate, no additional processing is needed."""
        (
            errors,
            form,
            _,  # onetoone_forms
            _,  # medhistorys_forms
            _,  # medhistorydetails_forms
            _,  # medallergys_forms
            _,  # lab_formset
            medallergys_to_save,
            medallergys_to_remove,
            onetoones_to_delete,
            onetoones_to_save,
            medhistorydetails_to_save,
            medhistorydetails_to_remove,
            medhistorys_to_save,
            medhistorys_to_remove,
            labs_to_save,
            labs_to_remove,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        else:
            return self.form_valid(
                form=form,  # type: ignore
                medallergys_to_save=medallergys_to_save,
                medallergys_to_remove=medallergys_to_remove,
                onetoones_to_delete=onetoones_to_delete,
                onetoones_to_save=onetoones_to_save,
                medhistorydetails_to_save=medhistorydetails_to_save,
                medhistorydetails_to_remove=medhistorydetails_to_remove,
                medhistorys_to_save=medhistorys_to_save,
                medhistorys_to_remove=medhistorys_to_remove,
                labs_to_save=labs_to_save,
                labs_to_remove=labs_to_remove,
            )


class GoalUratePseudopatientDetail(AutoPermissionRequiredMixin, GoalUrateDetailBase):
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
            self.object.update(qs=self.object)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_permission_object(self):
        return self.object

    def assign_goalurate_attrs_from_user(self, goalurate: GoalUrate, user: "User") -> GoalUrate:
        """Transfers the user's medhistorys_qs to the GoalUrate."""
        goalurate.medhistorys_qs = user.medhistorys_qs
        return goalurate

    def get_queryset(self) -> "QuerySet[Any]":
        return goalurate_user_qs(self.kwargs["username"])

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
    AutoPermissionRequiredMixin, GoalUratePatientBase, PatientAidUpdateView, SuccessMessageMixin
):
    success_message = "%(username)s's GoalUrate successfully created."

    def dispatch(self, request, *args, **kwargs):
        """Overwritten to check if the User has a GoalUrate and redirect to the CreateView if not."""
        try:
            self.object = self.get_object()
        except GoalUrate.DoesNotExist as exc:
            messages.error(request, exc.args[0])
            return HttpResponseRedirect(
                reverse("goalurates:pseudopatient-create", kwargs={"username": kwargs["username"]})
            )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(
        self,
        form,
        onetoones_to_save: list["Model"] | None,
        onetoones_to_delete: list["Model"] | None,
        medhistorydetails_to_save: list["CkdDetailForm", "BaselineCreatinine", "GoutDetailForm"] | None,
        medhistorydetails_to_remove: list["CkdDetailForm", "BaselineCreatinine", "GoutDetailForm"] | None,
        medallergys_to_save: list["MedAllergy"] | None,
        medallergys_to_remove: list["MedAllergy"] | None,
        medhistorys_to_save: list["MedHistory"] | None,
        medhistorys_to_remove: list["MedHistory"] | None,
        labs_to_save: list["Lab"] | None,
        labs_to_remove: list["Lab"] | None,
    ) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Overwritten to redirect appropriately and update the form instance."""
        form = super().form_valid(
            form=form,
            onetoones_to_save=onetoones_to_save,
            onetoones_to_delete=onetoones_to_delete,
            medhistorys_to_save=medhistorys_to_save,
            medhistorys_to_remove=medhistorys_to_remove,
            medhistorydetails_to_save=medhistorydetails_to_save,
            medhistorydetails_to_remove=medhistorydetails_to_remove,
            medallergys_to_save=medallergys_to_save,
            medallergys_to_remove=medallergys_to_remove,
            labs_to_save=labs_to_save,
            labs_to_remove=labs_to_remove,
        )
        goalurate = form.save()
        # Add the relationship to the existing user object so that user
        # can be used as the QuerySet for the update method
        self.user.goalurate = goalurate
        # Update object / form instance
        goalurate.update(qs=self.user)
        # Add a querystring to the success_url to trigger the DetailView to NOT re-update the object
        return HttpResponseRedirect(goalurate.get_absolute_url() + "?updated=True")

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Psuedopatient the view is trying to create
        a FlareAid for."""
        return self.object

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, username=self.user.username)

    def post(self, request, *args, **kwargs):
        """Overwritten to finish the post() method and avoid conflicts with the MRO.
        For GoalUrate, no additional processing is needed."""
        (
            errors,
            form,
            _,  # onetoone_forms
            _,  # medhistorys_forms
            _,  # medhistorydetails_forms
            _,  # medallergys_forms
            _,  # lab_formset
            medallergys_to_save,
            medallergys_to_remove,
            onetoones_to_delete,
            onetoones_to_save,
            medhistorydetails_to_save,
            medhistorydetails_to_remove,
            medhistorys_to_save,
            medhistorys_to_remove,
            labs_to_save,
            labs_to_remove,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        else:
            return self.form_valid(
                form=form,  # type: ignore
                medallergys_to_save=medallergys_to_save,
                medallergys_to_remove=medallergys_to_remove,
                onetoones_to_delete=onetoones_to_delete,
                onetoones_to_save=onetoones_to_save,
                medhistorydetails_to_save=medhistorydetails_to_save,
                medhistorydetails_to_remove=medhistorydetails_to_remove,
                medhistorys_to_save=medhistorys_to_save,
                medhistorys_to_remove=medhistorys_to_remove,
                labs_to_save=labs_to_save,
                labs_to_remove=labs_to_remove,
            )
