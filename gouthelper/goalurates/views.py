from typing import TYPE_CHECKING, Any

from django.apps import apps  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # type: ignore
from django.db.models import Q  # type: ignore
from django.views.generic import DetailView, TemplateView, View  # type: ignore

from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.forms import ErosionsForm, TophiForm
from ..medhistorys.models import Erosions, Tophi
from ..pages.choices import Contexts
from ..utils.views import MedHistorysModelCreateView, MedHistorysModelUpdateView
from .forms import GoalUrateForm
from .models import GoalUrate
from .selectors import goalurate_userless_qs

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore


class GoalUrateAbout(TemplateView):
    """About page for GoalUrate"""

    template_name = "goalurates/about.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"page": self.page})
        return context

    @property
    def page(self):
        return apps.get_model("pages.Page").objects.get(slug="about", context=Contexts.GOALURATE, tag=None)


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

    def form_valid(self, form: GoalUrateForm, **kwargs):
        """Override to add ultaid to form instance if it exists.
        Calls GoalUrate-specific update() method."""
        ultaid = self.kwargs.get("ultaid", None)
        if ultaid:
            form.instance.ultaid_id = ultaid
        return super().form_valid(form, **kwargs)

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
            object_data,
            onetoone_forms,
            medallergys_forms,
            medhistorys_forms,
            medhistorydetails_forms,
            lab_formset,
            onetoones_to_save,
            medallergys_to_add,
            medhistorys_to_add,
            medhistorydetails_to_add,
            labs_to_add,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        else:
            return self.form_valid(
                form=form,  # type: ignore
                medallergys_to_add=medallergys_to_add,
                onetoones_to_save=onetoones_to_save,
                medhistorydetails_to_add=medhistorydetails_to_add,
                medhistorys_to_add=medhistorys_to_add,
                labs_to_add=labs_to_add,
            )


class GoalUrateDetail(DetailView):
    model = GoalUrate
    object: GoalUrate

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        for page in self.pages:
            context.update({page.slug: {page.tag: page}})  # type: ignore
        return context

    def get_queryset(self) -> "QuerySet[Any]":
        return goalurate_userless_qs(self.kwargs["pk"])

    def get_object(self, *args, **kwargs) -> GoalUrate:
        goalurate: GoalUrate = super().get_object(*args, **kwargs)  # type: ignore
        if goalurate.uptodate is False:
            goalurate.update()
        return goalurate

    @property
    def pages(self):
        return apps.get_model("pages.Page").objects.filter(Q(tag__isnull=False), context=Contexts.GOALURATE)


class GoalUrateUpdate(GoalUrateBase, MedHistorysModelUpdateView, SuccessMessageMixin):
    """Creates a new GoalUrate"""

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add ultaid to context if it exists."""
        context = super().get_context_data(**kwargs)
        ultaid = self.kwargs.get("ultaid", None)
        if ultaid and "ultaid" not in context:
            context["ultaid"] = ultaid
        return context

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
            object_data,
            onetoone_forms,
            medhistorys_forms,
            medhistorydetails_forms,
            medallergys_forms,
            lab_formset,
            medallergys_to_add,
            medallergys_to_remove,
            onetoones_to_delete,
            onetoones_to_save,
            medhistorydetails_to_add,
            medhistorys_to_add,
            medhistorys_to_remove,
            labs_to_add,
            labs_to_remove,
            labs_to_update,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        else:
            return self.form_valid(
                form=form,  # type: ignore
                medallergys_to_add=medallergys_to_add,
                medallergys_to_remove=medallergys_to_remove,
                onetoones_to_delete=onetoones_to_delete,
                onetoones_to_save=onetoones_to_save,
                medhistorydetails_to_add=medhistorydetails_to_add,
                medhistorys_to_add=medhistorys_to_add,
                medhistorys_to_remove=medhistorys_to_remove,
                labs_to_add=labs_to_add,
                labs_to_remove=labs_to_remove,
                labs_to_update=labs_to_update,
            )
