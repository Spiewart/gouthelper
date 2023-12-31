from typing import TYPE_CHECKING, Any, Union

from django.apps import apps  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # type: ignore
from django.http import HttpResponseRedirect  # type: ignore
from django.views.generic import DetailView, TemplateView, View  # type: ignore
from django_htmx.http import HttpResponseClientRefresh  # type: ignore

from ..contents.choices import Contexts
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.forms import ErosionsForm, TophiForm
from ..medhistorys.models import Erosions, Tophi
from ..utils.views import MedHistorysModelCreateView, MedHistorysModelUpdateView
from .forms import GoalUrateForm
from .models import GoalUrate
from .selectors import goalurate_userless_qs

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet  # type: ignore
    from django.http import HttpResponse  # type: ignore

    from ..labs.models import BaselineCreatinine, Lab
    from ..medallergys.models import MedAllergy
    from ..medhistorydetails.forms import CkdDetailForm, GoutDetailForm
    from ..medhistorys.models import MedHistory


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


class GoalUrateDetail(DetailView):
    model = GoalUrate
    object: GoalUrate

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        for content in self.contents:
            context.update({content.slug: {content.tag: content}})  # type: ignore
        return context

    def get_queryset(self) -> "QuerySet[Any]":
        return goalurate_userless_qs(self.kwargs["pk"])

    def get_object(self, *args, **kwargs) -> GoalUrate:
        goalurate: GoalUrate = super().get_object(*args, **kwargs)  # type: ignore
        if not self.request.GET.get("updated", None):
            goalurate.update(qs=goalurate)
        return goalurate

    @property
    def contents(self):
        return apps.get_model("contents.Content").objects.filter(context=Contexts.GOALURATE, tag__isnull=False)


class GoalUrateUpdate(GoalUrateBase, MedHistorysModelUpdateView, SuccessMessageMixin):
    """Creates a new GoalUrate"""

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
            _,  # object_data
            _,  # onetoone_forms
            _,  # medhistorys_forms
            _,  # medhistorydetails_forms
            _,  # medallergys_forms
            _,  # lab_formset
            _,  # medallergys_to_save,
            _,  # medallergys_to_remove,
            _,  # onetoones_to_delete,
            _,  # onetoones_to_save,
            _,  # medhistorydetails_to_save,
            _,  # medhistorydetails_to_remove,
            medhistorys_to_save,
            medhistorys_to_remove,
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
