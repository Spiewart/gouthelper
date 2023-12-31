from typing import TYPE_CHECKING, Any, Union

from django.apps import apps  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # type: ignore
from django.http import HttpResponseRedirect  # type: ignore
from django.views.generic import DetailView, TemplateView, View  # type: ignore

from ..contents.choices import Contexts
from ..labs.forms import LabFormHelper, PpxUrateFormSet
from ..labs.models import Urate
from ..medhistorydetails.forms import GoutDetailPpxForm
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.forms import GoutForm
from ..medhistorys.models import Gout
from ..utils.views import MedHistorysModelCreateView, MedHistorysModelUpdateView
from .forms import PpxForm
from .models import Ppx
from .selectors import ppx_userless_qs

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet  # type: ignore
    from django.http import HttpResponse  # type: ignore

    from ..labs.models import BaselineCreatinine, Lab
    from ..medallergys.models import MedAllergy
    from ..medhistorydetails.forms import CkdDetailForm
    from ..medhistorys.models import MedHistory


class PpxAbout(TemplateView):
    """About page for Ppx decision aid."""

    template_name = "ppxs/about.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"content": self.content})
        return context

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="about", context=Contexts.PPX, tag=None)


class PpxBase(View):
    class Meta:
        abstract = True

    model = Ppx
    form_class = PpxForm

    # Assign onetoones dict with key as the name of the model and value as a
    # dict of the model's form and model.
    medhistorys = {
        MedHistoryTypes.GOUT: {"form": GoutForm, "model": Gout},
    }
    medhistory_details = {MedHistoryTypes.GOUT: GoutDetailPpxForm}
    labs = (PpxUrateFormSet, LabFormHelper, Urate.objects.none(), "labs")


class PpxCreate(PpxBase, MedHistorysModelCreateView, SuccessMessageMixin):
    """
    Create a new Ppx instance.
    """

    def form_valid(
        self,
        form: PpxForm,
        onetoones_to_save: list["Model"] | None,
        medhistorydetails_to_save: list["CkdDetailForm", "BaselineCreatinine", GoutDetailPpxForm] | None,
        medallergys_to_save: list["MedAllergy"] | None,
        medhistorys_to_save: list["MedHistory"] | None,
        labs_to_save: list["Lab"] | None,
        **kwargs,
    ) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Overwritten to redirect appropriately, as parent method doesn't redirect at all."""
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
        return HttpResponseRedirect(self.get_success_url())

    def post(self, request, *args, **kwargs):
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


class PpxDetail(DetailView):
    """DetailView for Ppx model."""

    model = Ppx
    object: Ppx

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        for content in self.contents:
            context.update({content.slug: {content.tag: content}})  # type: ignore
        return context

    def get_queryset(self) -> "QuerySet[Any]":
        return ppx_userless_qs(self.kwargs["pk"])

    def get_object(self, *args, **kwargs) -> Ppx:
        ppx: Ppx = super().get_object(*args, **kwargs)  # type: ignore
        # Check if Ppx is up to date and update if not update
        if not self.request.GET.get("updated", None):
            ppx.update(qs=ppx)
        return ppx

    @property
    def contents(self):
        return apps.get_model("contents.Content").objects.filter(context=Contexts.PPX)


class PpxUpdate(PpxBase, MedHistorysModelUpdateView, SuccessMessageMixin):
    """Updates a Ppx"""

    def form_valid(
        self,
        form,
        onetoones_to_save: list["Model"] | None,
        onetoones_to_delete: list["Model"] | None,
        medhistorydetails_to_save: list["CkdDetailForm", "BaselineCreatinine", GoutDetailPpxForm] | None,
        medhistorydetails_to_remove: list["CkdDetailForm", "BaselineCreatinine", GoutDetailPpxForm] | None,
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
        # Update object / form instance
        self.object.update(qs=self.object)
        # Add a querystring to the success_url to trigger the DetailView to NOT re-update the object
        return HttpResponseRedirect(self.get_success_url() + "?updated=True")

    def get_queryset(self):
        return ppx_userless_qs(self.kwargs["pk"])

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
