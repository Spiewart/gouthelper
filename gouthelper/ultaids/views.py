from typing import TYPE_CHECKING, Any, Union

from django.apps import apps  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # type: ignore
from django.db.models import Q  # type: ignore
from django.http import HttpResponseRedirect  # type: ignore
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView  # type: ignore

from ..contents.choices import Contexts
from ..dateofbirths.forms import DateOfBirthFormOptional
from ..dateofbirths.models import DateOfBirth
from ..ethnicitys.forms import EthnicityForm
from ..ethnicitys.models import Ethnicity
from ..genders.forms import GenderFormOptional
from ..genders.models import Gender
from ..labs.forms import Hlab5801Form
from ..labs.models import Hlab5801
from ..medhistorydetails.forms import CkdDetailOptionalForm
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
from ..utils.views import MedHistoryModelBaseMixin
from .forms import UltAidForm
from .models import UltAid
from .selectors import ultaid_userless_qs

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet  # type: ignore
    from django.http import HttpResponse  # type: ignore

    from ..labs.models import BaselineCreatinine, Lab
    from ..medallergys.models import MedAllergy
    from ..medhistorydetails.forms import GoutDetailForm
    from ..medhistorys.models import MedHistory


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


class UltAidBase:
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
    medhistory_details = {MedHistoryTypes.CKD: CkdDetailOptionalForm}


class UltAidCreate(UltAidBase, MedHistoryModelBaseMixin, CreateView, SuccessMessageMixin):
    """
    Create a new UltAid instance.
    """

    success_message = "UltAid created successfully!"

    def form_valid(
        self,
        form: UltAidForm,
        oto_2_save: list["Model"] | None,
        mh_det_2_save: list[CkdDetailOptionalForm, "BaselineCreatinine", "GoutDetailForm"] | None,
        ma_2_save: list["MedAllergy"] | None,
        mh_2_save: list["MedHistory"] | None,
        labs_2_save: list["Lab"] | None,
        **kwargs,
    ) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Overwritten to redirect appropriately, as parent method doesn't redirect at all."""
        # Object will be returned by the super().form_valid() call
        self.object = super().form_valid(
            form=form,
            oto_2_save=oto_2_save,
            mh_det_2_save=mh_det_2_save,
            ma_2_save=ma_2_save,
            mh_2_save=mh_2_save,
            labs_2_save=labs_2_save,
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
            _,  # labs_formset
            oto_2_save,
            ma_2_save,
            mh_2_save,
            mh_det_2_save,
            labs_2_save,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        else:
            return self.form_valid(
                form=form,  # type: ignore
                ma_2_save=ma_2_save,
                oto_2_save=oto_2_save,
                mh_det_2_save=mh_det_2_save,
                mh_2_save=mh_2_save,
                labs_2_save=labs_2_save,
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
                ultaid.goalurate.update_aid(qs=ultaid.goalurate)
        # Check if UltAid is up to date and update if not update
        if not self.request.GET.get("updated", None):
            ultaid.update_aid(qs=ultaid)
        return ultaid

    @property
    def contents(self):
        return apps.get_model("contents.Content").objects.filter(Q(tag__isnull=False), context=Contexts.ULTAID)


class UltAidUpdate(UltAidBase, MedHistoryModelBaseMixin, UpdateView, SuccessMessageMixin):
    """Updates a UltAid"""

    def form_valid(
        self,
        form,
        oto_2_save: list["Model"] | None,
        oto_2_rem: list["Model"] | None,
        mh_det_2_save: list[CkdDetailOptionalForm, "BaselineCreatinine", "GoutDetailForm"] | None,
        mh_det_2_rem: list[CkdDetailOptionalForm, "BaselineCreatinine", "GoutDetailForm"] | None,
        ma_2_save: list["MedAllergy"] | None,
        ma_2_rem: list["MedAllergy"] | None,
        mh_2_save: list["MedHistory"] | None,
        mh_2_rem: list["MedHistory"] | None,
        labs_2_save: list["Lab"] | None,
        labs_2_rem: list["Lab"] | None,
    ) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Overwritten to redirect appropriately and update the form instance."""

        self.object = super().form_valid(
            form=form,
            oto_2_save=oto_2_save,
            oto_2_rem=oto_2_rem,
            mh_2_save=mh_2_save,
            mh_2_rem=mh_2_rem,
            mh_det_2_save=mh_det_2_save,
            mh_det_2_rem=mh_det_2_rem,
            ma_2_save=ma_2_save,
            ma_2_rem=ma_2_rem,
            labs_2_save=labs_2_save,
            labs_2_rem=labs_2_rem,
        )
        # Update object / form instance
        self.object.update_aid(qs=self.object)
        # Add a querystring to the success_url to trigger the DetailView to NOT re-update the object
        return HttpResponseRedirect(self.get_success_url() + "?updated=True")

    def get_queryset(self):
        return ultaid_userless_qs(self.kwargs["pk"])

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            _,  # onetoone_forms
            _,  # medallergys_forms
            _,  # medhistorys_forms
            _,  # medhistorydetails_forms
            _,  # lab_formset
            oto_2_save,
            oto_2_rem,
            ma_2_save,
            ma_2_rem,
            mh_2_save,
            mh_2_rem,
            mh_det_2_save,
            mh_det_2_rem,
            labs_2_save,
            labs_2_rem,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        else:
            return self.form_valid(
                form=form,  # type: ignore
                ma_2_save=ma_2_save,
                ma_2_rem=ma_2_rem,
                oto_2_rem=oto_2_rem,
                oto_2_save=oto_2_save,
                mh_det_2_save=mh_det_2_save,
                mh_det_2_rem=mh_det_2_rem,
                mh_2_save=mh_2_save,
                mh_2_rem=mh_2_rem,
                labs_2_save=labs_2_save,
                labs_2_rem=labs_2_rem,
            )
