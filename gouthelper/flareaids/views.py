from typing import TYPE_CHECKING, Any, Union

from django.apps import apps  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # type: ignore
from django.http import HttpResponseRedirect  # type: ignore
from django.views.generic import DetailView, TemplateView, View  # type: ignore

from ..contents.choices import Contexts
from ..dateofbirths.forms import DateOfBirthForm
from ..dateofbirths.models import DateOfBirth
from ..genders.forms import GenderFormOptional
from ..genders.models import Gender
from ..medhistorydetails.forms import CkdDetailForm
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
from .forms import FlareAidForm
from .models import FlareAid
from .selectors import flareaid_userless_qs

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet  # type: ignore
    from django.http import HttpResponse  # type: ignore

    from ..labs.models import BaselineCreatinine, Lab
    from ..medallergys.models import MedAllergy
    from ..medhistorydetails.forms import GoutDetailForm
    from ..medhistorys.models import MedHistory


class FlareAidAbout(TemplateView):
    """About page for FlareAid"""

    template_name = "flareaids/about.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"content": self.content})
        return context

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="about", context=Contexts.FLAREAID, tag=None)


class FlareAidBase(View):
    class Meta:
        abstract = True

    form_class = FlareAidForm
    model = FlareAid
    onetoones = {
        "dateofbirth": {"form": DateOfBirthForm, "model": DateOfBirth},
        "gender": {"form": GenderFormOptional, "model": Gender},
    }
    medallergys = FlarePpxChoices
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
    medhistory_details = {MedHistoryTypes.CKD: CkdDetailForm}


class FlareAidCreate(FlareAidBase, MedHistorysModelCreateView, SuccessMessageMixin):
    """Creates a new FlareAid"""

    def form_valid(
        self,
        form: FlareAidForm,
        onetoones_to_save: list["Model"] | None,
        medhistorydetails_to_save: list[CkdDetailForm, "BaselineCreatinine", "GoutDetailForm"] | None,
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


class FlareAidDetail(DetailView):
    model = FlareAid
    object: FlareAid

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        for content in self.contents:
            context.update({content.slug: {content.tag: content}})  # type: ignore
        return context

    def get_queryset(self) -> "QuerySet[Any]":
        return flareaid_userless_qs(self.kwargs["pk"])

    def get_object(self, *args, **kwargs) -> FlareAid:
        flareaid: FlareAid = super().get_object(*args, **kwargs)  # type: ignore
        # Check if FlareAid is up to date and update if not update
        if not self.request.GET.get("updated", None):
            flareaid.update()
        return flareaid

    @property
    def contents(self):
        return apps.get_model("contents.Content").objects.filter(context=Contexts.FLAREAID, tag__isnull=False)


class FlareAidUpdate(FlareAidBase, MedHistorysModelUpdateView, SuccessMessageMixin):
    """Updates a FlareAid"""

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
        labs_to_update: list["Lab"] | None,
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
            labs_to_update=labs_to_update,
        )
        # Update object / form instance
        self.object.update(qs=self.object)
        # Add a querystring to the success_url to trigger the DetailView to NOT re-update the object
        return HttpResponseRedirect(self.get_success_url() + "?updated=True")

    def get_queryset(self):
        return flareaid_userless_qs(self.kwargs["pk"])

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
            labs_to_update,
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
                labs_to_update=labs_to_update,
            )
