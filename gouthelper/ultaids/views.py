from typing import TYPE_CHECKING, Any

from django.apps import apps  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # type: ignore
from django.db.models import Q  # type: ignore
from django.views.generic import DetailView, TemplateView, View  # type: ignore

from ..contents.choices import Contexts
from ..dateofbirths.forms import DateOfBirthFormOptional
from ..dateofbirths.models import DateOfBirth
from ..ethnicitys.forms import EthnicityForm
from ..ethnicitys.models import Ethnicity
from ..genders.forms import GenderFormOptional
from ..genders.models import Gender
from ..labs.forms import Hlab5801Form
from ..labs.models import Hlab5801
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.forms import (
    AllopurinolhypersensitivityForm,
    AnginaForm,
    CadForm,
    ChfForm,
    CkdForm,
    FebuxostathypersensitivityForm,
    HeartattackForm,
    OrgantransplantForm,
    PvdForm,
    StrokeForm,
    XoiinteractionForm,
)
from ..medhistorys.models import (
    Allopurinolhypersensitivity,
    Angina,
    Cad,
    Chf,
    Ckd,
    Febuxostathypersensitivity,
    Heartattack,
    Organtransplant,
    Pvd,
    Stroke,
    Xoiinteraction,
)
from ..treatments.choices import UltChoices
from ..utils.views import MedHistorysModelCreateView, MedHistorysModelUpdateView
from .forms import UltAidForm
from .models import UltAid
from .selectors import ultaid_userless_qs

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore


class UltAidAbout(TemplateView):
    """About page for gout flare prophylaxis and PpxAids."""

    template_name = "ultaids/about.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"content": self.content})
        return context

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="about", context=Contexts.ULTAID, tag=None)


class UltAidBase(View):
    class Meta:
        abstract = True

    model = UltAid
    form_class = UltAidForm
    # Assign onetoones dict with key as the name of the model and value as a
    # dict of the model's form and model.
    onetoones = {
        "dateofbirth": {"form": DateOfBirthFormOptional, "model": DateOfBirth},
        "ethnicity": {"form": EthnicityForm, "model": Ethnicity},
        "gender": {"form": GenderFormOptional, "model": Gender},
        "hlab5801": {"form": Hlab5801Form, "model": Hlab5801},
    }
    # Assign medallergys as the Treatment choices for UltAid
    medallergys = UltChoices
    # Assign medhistorys dict with key as the name of the model and value as a
    # dict of the model's form and model.
    medhistorys = {
        MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY: {
            "form": AllopurinolhypersensitivityForm,
            "model": Allopurinolhypersensitivity,
        },
        MedHistoryTypes.ANGINA: {"form": AnginaForm, "model": Angina},
        MedHistoryTypes.CAD: {"form": CadForm, "model": Cad},
        MedHistoryTypes.CHF: {"form": ChfForm, "model": Chf},
        MedHistoryTypes.CKD: {"form": CkdForm, "model": Ckd},
        MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY: {
            "form": FebuxostathypersensitivityForm,
            "model": Febuxostathypersensitivity,
        },
        MedHistoryTypes.HEARTATTACK: {"form": HeartattackForm, "model": Heartattack},
        MedHistoryTypes.ORGANTRANSPLANT: {"form": OrgantransplantForm, "model": Organtransplant},
        MedHistoryTypes.PVD: {"form": PvdForm, "model": Pvd},
        MedHistoryTypes.STROKE: {"form": StrokeForm, "model": Stroke},
        MedHistoryTypes.XOIINTERACTION: {"form": XoiinteractionForm, "model": Xoiinteraction},
    }
    # Set ckdetail to True so that parent model will include processing for CkdDetail and BaselineCreatinine
    medhistory_details = [MedHistoryTypes.CKD]


class UltAidCreate(UltAidBase, MedHistorysModelCreateView, SuccessMessageMixin):
    """
    Create a new UltAid instance.
    """

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            _,  # object_data
            _,  # onetoone_forms
            _,  # medallergys_forms
            _,  # medhistorys_forms
            _,  # medhistorydetails_forms
            _,  # labs_formset
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


class UltAidDetail(DetailView):
    """DetailView for UltAid model."""

    model = UltAid
    object: UltAid

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        for content in self.contents:
            context.update({content.slug: {content.tag: content}})  # type: ignore
        return context

    def get_queryset(self) -> "QuerySet[Any]":
        return ultaid_userless_qs(self.kwargs["pk"])

    def get_object(self, *args, **kwargs) -> UltAid:
        ultaid: UltAid = super().get_object(*args, **kwargs)  # type: ignore
        # Prefetch goalurate medhistory_qs for use in the template and to avoid additional queries
        if hasattr(ultaid, "goalurate"):
            ultaid.goalurate.medhistorys_qs = ultaid.goalurate.medhistorys.all()
            if not self.request.GET.get("goalurate_updated", None):
                ultaid.goalurate.update(qs=ultaid.goalurate)
        # Check if UltAid is up to date and update if not update
        if not self.request.GET.get("updated", None):
            ultaid.update(qs=ultaid)
        return ultaid

    @property
    def contents(self):
        return apps.get_model("contents.Content").objects.filter(Q(tag__isnull=False), context=Contexts.ULTAID)


class UltAidUpdate(UltAidBase, MedHistorysModelUpdateView, SuccessMessageMixin):
    """Updates a UltAid"""

    def get_queryset(self):
        return ultaid_userless_qs(self.kwargs["pk"])

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            _,  # object_data
            _,  # onetoone_forms
            _,  # medhistorys_forms
            _,  # medhistorydetails_forms
            _,  # medallergys_forms
            _,  # labs_formset
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
