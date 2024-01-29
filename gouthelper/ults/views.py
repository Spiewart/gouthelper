from typing import TYPE_CHECKING, Any, Union

from django.apps import apps  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # type: ignore
from django.db.models import Q  # type: ignore
from django.http import HttpResponseRedirect  # type: ignore
from django.views.generic import DetailView, TemplateView, View  # type: ignore

from ..contents.choices import Contexts
from ..dateofbirths.forms import DateOfBirthFormOptional
from ..dateofbirths.models import DateOfBirth
from ..genders.forms import GenderFormOptional
from ..genders.models import Gender
from ..medhistorydetails.forms import CkdDetailForm
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.forms import CkdForm, ErosionsForm, HyperuricemiaForm, TophiForm, UratestonesForm
from ..medhistorys.models import Ckd, Erosions, Hyperuricemia, Tophi, Uratestones
from ..utils.views import MedHistorysModelCreateView, MedHistorysModelUpdateView
from .forms import UltForm
from .models import Ult
from .selectors import ult_userless_qs

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet  # type: ignore
    from django.http import HttpResponse  # type: ignore

    from ..labs.models import BaselineCreatinine, Lab
    from ..medallergys.models import MedAllergy
    from ..medhistorydetails.forms import GoutDetailForm
    from ..medhistorys.models import MedHistory


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


class UltBaseView(View):
    class Meta:
        abstract = True

    model = Ult
    form_class = UltForm

    # Assign onetoones dict with key as the name of the model and value as a
    # dict of the model's form and model.
    onetoones = {
        "dateofbirth": {"form": DateOfBirthFormOptional, "model": DateOfBirth},
        "gender": {"form": GenderFormOptional, "model": Gender},
    }
    # Assign medhistory manytomanys to a dict of ULT_MEDHISTORYS
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


class UltCreate(UltBaseView, MedHistorysModelCreateView, SuccessMessageMixin):
    """View to create a new Ult instance."""

    def form_valid(
        self,
        form,
        onetoones_to_save: list["Model"],
        medhistorydetails_to_save: list[CkdDetailForm, "BaselineCreatinine", "GoutDetailForm"],
        medallergys_to_save: list["MedAllergy"],
        medhistorys_to_save: list["MedHistory"],
        labs_to_save: list["Lab"],
        **kwargs,
    ) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Overwritten to redirect appropriately."""
        # Object will be returned by the super().form_valid() call
        self.object = super().form_valid(
            form,
            onetoones_to_save=onetoones_to_save,
            medhistorydetails_to_save=medhistorydetails_to_save,
            medallergys_to_save=medallergys_to_save,
            medhistorys_to_save=medhistorys_to_save,
            labs_to_save=labs_to_save,
            **kwargs,
        )
        # Update object / form instance
        self.object.update_aid(qs=self.object)
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


class UltDetail(DetailView):
    """DetailView for Ult model."""

    model = Ult
    object: Ult

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        for content in self.contents:
            context.update({content.slug: {content.tag: content}})  # type: ignore
        return context

    def get_queryset(self) -> "QuerySet[Any]":
        return ult_userless_qs(self.kwargs["pk"])

    def get_object(self, *args, **kwargs) -> Ult:
        ult: Ult = super().get_object(*args, **kwargs)  # type: ignore
        # Check if Ult is up to date and update if not update
        if not self.request.GET.get("updated", None):
            ult.update_aid(qs=ult)
        return ult

    @property
    def contents(self):
        return apps.get_model("contents.Content").objects.filter(Q(tag__isnull=False), context=Contexts.ULT)


class UltUpdate(UltBaseView, MedHistorysModelUpdateView, SuccessMessageMixin):
    """Updates a Ult"""

    def form_valid(
        self,
        form,
        onetoones_to_save: list["Model"] | None,
        onetoones_to_delete: list["Model"] | None,
        medhistorydetails_to_save: list[CkdDetailForm, "BaselineCreatinine", "GoutDetailForm"] | None,
        medhistorydetails_to_remove: list[CkdDetailForm, "BaselineCreatinine", "GoutDetailForm"] | None,
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
        # Update the object / form instance
        self.object.update_aid(qs=self.object)
        # Add a querystring to the success_url to trigger the DetailView to NOT re-update the object
        return HttpResponseRedirect(self.get_success_url() + "?updated=True")

    def get_queryset(self):
        return ult_userless_qs(self.kwargs["pk"])

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            _,  # onetoone_forms
            _,  # medallergys_forms
            _,  # medhistorys_forms
            _,  # medhistorydetails_forms
            _,  # lab_formset
            onetoones_to_save,
            onetoones_to_delete,
            medallergys_to_save,
            medallergys_to_remove,
            medhistorys_to_save,
            medhistorys_to_remove,
            medhistorydetails_to_save,
            medhistorydetails_to_remove,
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
