from typing import TYPE_CHECKING, Any

from django.apps import apps  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # type: ignore
from django.views.generic import DetailView, TemplateView, View  # type: ignore

from ..contents.choices import Contexts
from ..dateofbirths.forms import DateOfBirthForm
from ..dateofbirths.models import DateOfBirth
from ..genders.forms import GenderFormOptional
from ..genders.models import Gender
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.forms import (
    AnginaForm,
    AnticoagulationForm,
    BleedForm,
    CadForm,
    ChfForm,
    CkdForm,
    ColchicineinteractionForm,
    DiabetesForm,
    GastricbypassForm,
    HeartattackForm,
    HypertensionForm,
    IbdForm,
    OrgantransplantForm,
    PvdForm,
    StrokeForm,
)
from ..medhistorys.models import (
    Angina,
    Anticoagulation,
    Bleed,
    Cad,
    Chf,
    Ckd,
    Colchicineinteraction,
    Diabetes,
    Gastricbypass,
    Heartattack,
    Hypertension,
    Ibd,
    Organtransplant,
    Pvd,
    Stroke,
)
from ..treatments.choices import FlarePpxChoices
from ..utils.views import MedHistorysModelCreateView, MedHistorysModelUpdateView
from .forms import PpxAidForm
from .models import PpxAid
from .selectors import ppxaid_userless_qs

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore


class PpxAidAbout(TemplateView):
    """About page for gout flare prophylaxis and PpxAids."""

    template_name = "ppxaids/about.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"content": self.content})
        return context

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="about", context=Contexts.PPXAID, tag=None)


class PpxAidBase(View):
    class Meta:
        abstract = True

    model = PpxAid
    form_class = PpxAidForm

    # Assign onetoones dict with key as the name of the model and value as a
    # dict of the model's form and model.
    onetoones = {
        "dateofbirth": {"form": DateOfBirthForm, "model": DateOfBirth},
        "gender": {"form": GenderFormOptional, "model": Gender},
    }
    # Assign medallergys as the Treatment choices for PpxAid
    medallergys = FlarePpxChoices
    # Assign medhistorys dict with key as the name of the model and value as a
    # dict of the model's form and model.
    medhistorys = {
        MedHistoryTypes.ANGINA: {"form": AnginaForm, "model": Angina},
        MedHistoryTypes.ANTICOAGULATION: {"form": AnticoagulationForm, "model": Anticoagulation},
        MedHistoryTypes.BLEED: {"form": BleedForm, "model": Bleed},
        MedHistoryTypes.CAD: {"form": CadForm, "model": Cad},
        MedHistoryTypes.CHF: {"form": ChfForm, "model": Chf},
        MedHistoryTypes.CKD: {"form": CkdForm, "model": Ckd},
        MedHistoryTypes.COLCHICINEINTERACTION: {"form": ColchicineinteractionForm, "model": Colchicineinteraction},
        MedHistoryTypes.DIABETES: {"form": DiabetesForm, "model": Diabetes},
        MedHistoryTypes.GASTRICBYPASS: {"form": GastricbypassForm, "model": Gastricbypass},
        MedHistoryTypes.HEARTATTACK: {"form": HeartattackForm, "model": Heartattack},
        MedHistoryTypes.HYPERTENSION: {"form": HypertensionForm, "model": Hypertension},
        MedHistoryTypes.IBD: {"form": IbdForm, "model": Ibd},
        MedHistoryTypes.ORGANTRANSPLANT: {"form": OrgantransplantForm, "model": Organtransplant},
        MedHistoryTypes.PVD: {"form": PvdForm, "model": Pvd},
        MedHistoryTypes.STROKE: {"form": StrokeForm, "model": Stroke},
    }
    medhistory_details = [MedHistoryTypes.CKD]


class PpxAidCreate(PpxAidBase, MedHistorysModelCreateView, SuccessMessageMixin):
    """
    Create a new PpxAid instance.
    """

    def post(self, request, *args, **kwargs):
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


class PpxAidDetail(DetailView):
    """DetailView for PpxAid model."""

    model = PpxAid
    object: PpxAid

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        for content in self.contents:
            context.update({content.slug: {content.tag: content}})  # type: ignore
        return context

    def get_queryset(self) -> "QuerySet[Any]":
        return ppxaid_userless_qs(self.kwargs["pk"])

    def get_object(self, *args, **kwargs) -> PpxAid:
        ppxaid: PpxAid = super().get_object(*args, **kwargs)  # type: ignore
        # Check if PpxAid is up to date and update if not update
        if not self.request.GET.get("updated", None):
            ppxaid.update(qs=ppxaid)
        return ppxaid

    @property
    def contents(self):
        return apps.get_model("contents.Content").objects.filter(context=Contexts.PPXAID, tag__isnull=False)


class PpxAidUpdate(PpxAidBase, MedHistorysModelUpdateView, SuccessMessageMixin):
    """Updates a PpxAid"""

    def get_queryset(self):
        return ppxaid_userless_qs(self.kwargs["pk"])

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
