from typing import TYPE_CHECKING, Any, Union

from django.apps import apps  # type: ignore
from django.contrib import messages  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # type: ignore
from django.http import Http404, HttpResponseRedirect  # type: ignore
from django.urls import reverse
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
from ..utils.views import (
    MedHistorysModelCreateView,
    MedHistorysModelUpdateView,
    PatientAidCreateView,
    PatientAidUpdateView,
)
from .forms import FlareAidForm
from .models import FlareAid
from .selectors import flareaid_user_qs, flareaid_userless_qs

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet  # type: ignore
    from django.http import HttpResponse  # type: ignore

    from ..labs.models import BaselineCreatinine, Lab
    from ..medallergys.models import MedAllergy
    from ..medhistorydetails.forms import GoutDetailForm
    from ..medhistorys.models import MedHistory

User = get_user_model()


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


class FlareAidPatientCreate(FlareAidBase, PatientAidCreateView, SuccessMessageMixin):
    """View for creating a FlareAid for a patient."""

    onetoones = {}
    req_onetoones = ["dateofbirth", "gender"]

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
        aid_obj = super().form_valid(
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
        self.object = aid_obj
        self.user.flareaid = aid_obj
        # Update object / form instance
        aid_obj.update(qs=self.user)
        # Add a querystring to the success_url to trigger the DetailView to NOT re-update the object
        return HttpResponseRedirect(self.get_success_url() + "?updated=True")

    def get_object(self, *args, **kwargs) -> FlareAid:
        return None

    def get_user_queryset(self, username: str) -> "QuerySet[Any]":
        """Used to set the user attribute on the view, with associated related models
        select_related and prefetch_related."""
        return flareaid_user_qs(username=username)

    def post(self, request, *args, **kwargs):
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


class FlareAidPatientUpdate(FlareAidPatientCreate, PatientAidUpdateView):
    success_message = "FlareAid successfully updated."

    def get(self, request, *args, **kwargs):
        self.user = self.get_user_queryset(kwargs["username"]).get()
        try:
            self.check_user_onetoones(user=self.user)
        except AttributeError as exc:
            messages.error(request, exc)
            return HttpResponseRedirect(reverse("users:pseudopatient-update", kwargs={"username": self.user.username}))
        self.object = self.get_object()
        return self.render_to_response(self.get_context_data())

    def get_object(self, *args, **kwargs) -> FlareAid:
        return self.user.flareaid


class FlareAidDetail(DetailView):
    model = FlareAid
    object: FlareAid

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Check if the object has a User and if there is no username in the kwargs,
        # redirect to the username url
        if self.object.user:
            return HttpResponseRedirect(self.object.get_absolute_url())
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

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


class FlareAidPatientDetail(FlareAidDetail):
    """Overwritten for different url routing, object fetching, and
    building the content data."""

    def get(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except FlareAid.DoesNotExist:
            return HttpResponseRedirect(reverse("flareaids:patient-create", kwargs={"username": kwargs["username"]}))
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def assign_flareaid_attrs_from_user(self, flareaid: FlareAid, user: "User") -> FlareAid:
        flareaid.dateofbirth = user.dateofbirth
        flareaid.gender = user.gender
        flareaid.medallergys_qs = user.medallergys_qs
        flareaid.medhistorys_qs = user.medhistorys_qs
        return flareaid

    def get_queryset(self) -> "QuerySet[Any]":
        return flareaid_user_qs(self.kwargs["username"])

    def get_object(self, *args, **kwargs) -> FlareAid:
        try:
            user: User = self.get_queryset().get()
        except User.DoesNotExist as exc:
            raise Http404("No User matching the query") from exc
        flareaid: FlareAid = user.flareaid
        flareaid = self.assign_flareaid_attrs_from_user(flareaid=flareaid, user=user)
        # Check if FlareAid is up to date and update if not update
        if not self.request.GET.get("updated", None):
            flareaid.update()
        return flareaid


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

    def get(self, request, *args, **kwargs):
        """Overwritten to check for a User on the object and redirect to the
        correct FlareAidPatientUpdate url instead."""
        self.object = self.get_object()
        if self.object.user:
            return HttpResponseRedirect(
                reverse("flareaids:patient-update", kwargs={"username": self.object.user.username})
            )
        return self.render_to_response(self.get_context_data())

    def get_queryset(self):
        return flareaid_userless_qs(self.kwargs["pk"])

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
            _,  # labs_to_save
            _,  # labs_to_remove
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
                labs_to_save=None,
                labs_to_remove=None,
            )
