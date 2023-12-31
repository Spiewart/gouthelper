from typing import TYPE_CHECKING, Any

from django.apps import apps  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # type: ignore
from django.db.models import Q  # type: ignore
from django.views.generic import DetailView, TemplateView, View  # type: ignore

from ..contents.choices import Contexts
from ..dateofbirths.forms import DateOfBirthFormOptional
from ..dateofbirths.models import DateOfBirth
from ..genders.forms import GenderFormOptional
from ..genders.models import Gender
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.forms import CkdForm, ErosionsForm, HyperuricemiaForm, TophiForm, UratestonesForm
from ..medhistorys.models import Ckd, Erosions, Hyperuricemia, Tophi, Uratestones
from ..utils.views import MedHistorysModelCreateView, MedHistorysModelUpdateView
from .forms import UltForm
from .models import Ult
from .selectors import ult_userless_qs

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore


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
    medhistory_details = [MedHistoryTypes.CKD]


class UltCreate(UltBaseView, MedHistorysModelCreateView, SuccessMessageMixin):
    """View to create a new Ult instance."""

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
            ult.update(qs=ult)
        return ult

    @property
    def contents(self):
        return apps.get_model("contents.Content").objects.filter(Q(tag__isnull=False), context=Contexts.ULT)


class UltUpdate(UltBaseView, MedHistorysModelUpdateView, SuccessMessageMixin):
    """Updates a Ult"""

    def get_queryset(self):
        return ult_userless_qs(self.kwargs["pk"])

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
            medallergys_to_add,
            medallergys_to_remove,
            onetoones_to_delete,
            onetoones_to_save,
            medhistorydetails_to_add,
            medhistorydetails_to_remove,
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
                medhistorydetails_to_remove=medhistorydetails_to_remove,
                medhistorys_to_add=medhistorys_to_add,
                medhistorys_to_remove=medhistorys_to_remove,
                labs_to_add=labs_to_add,
                labs_to_remove=labs_to_remove,
                labs_to_update=labs_to_update,
            )
