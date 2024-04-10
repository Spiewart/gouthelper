from typing import TYPE_CHECKING, Any

from django.apps import apps  # pylint: disable=E0401  # type: ignore
from django.contrib import messages  # pylint: disable=E0401  # type: ignore
from django.contrib.auth import get_user_model  # pylint: disable=E0401  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # pylint: disable=E0401  # type: ignore
from django.http import HttpResponseRedirect  # pylint: disable=E0401  # type: ignore
from django.urls import reverse  # pylint: disable=E0401  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.views.generic import (  # pylint: disable=E0401  # type: ignore
    CreateView,
    DetailView,
    TemplateView,
    UpdateView,
)
from rules.contrib.views import (  # pylint: disable=W0611, E0401  # type: ignore
    AutoPermissionRequiredMixin,
    PermissionRequiredMixin,
)

from ..contents.choices import Contexts
from ..dateofbirths.forms import DateOfBirthForm
from ..dateofbirths.models import DateOfBirth
from ..flares.models import Flare
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
    PudForm,
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
    Pud,
    Pvd,
    Stroke,
)
from ..treatments.choices import FlarePpxChoices
from ..users.models import Pseudopatient
from ..utils.views import GoutHelperAidEditMixin
from .forms import FlareAidForm
from .models import FlareAid

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore

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


class FlareAidBase:
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
        MedHistoryTypes.PUD: {"form": PudForm, "model": Pud},
        MedHistoryTypes.PVD: {"form": PvdForm, "model": Pvd},
        MedHistoryTypes.STROKE: {"form": StrokeForm, "model": Stroke},
    }
    medhistory_details = {MedHistoryTypes.CKD: CkdDetailForm}


class FlareAidCreate(FlareAidBase, GoutHelperAidEditMixin, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """View to create a new FlareAid without a user."""

    permission_required = "flareaids.can_add_flareaid"
    success_message = "FlareAid successfully created."

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        if self.flare:
            kwargs.update({"flare": self.flare})
        return kwargs

    @cached_property
    def flare(self) -> Flare | None:
        flare_kwarg = self.kwargs.get("flare", None)
        return Flare.related_objects.get(pk=flare_kwarg) if flare_kwarg else None  # pylint: disable=W0201

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add ultaid to context if it exists."""
        context = super().get_context_data(**kwargs)
        context.update({"flare": self.flare})
        return context

    def get_permission_object(self):
        if self.flare and self.flare.user:
            raise PermissionError("Trying to create a FlareAid for a Flare with a user with an anonymous view.")
        return self.flare.user if self.flare else None

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            _,  # oto_forms,
            _,  # mh_forms,
            _,  # mh_det_forms,
            _,  # ma_forms,
            _,  # lab_formsets,
            oto_2_save,
            oto_2_rem,
            mh_2_save,
            mh_2_rem,
            mh_det_2_save,
            mh_det_2_rem,
            ma_2_save,
            ma_2_rem,
            _,  # labs_2_save,
            _,  # labs_2_rem,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        else:
            kwargs.update({"flare": self.flare})
            return self.form_valid(
                form=form,
                oto_2_save=oto_2_save,
                oto_2_rem=oto_2_rem,
                mh_2_save=mh_2_save,
                mh_2_rem=mh_2_rem,
                mh_det_2_save=mh_det_2_save,
                mh_det_2_rem=mh_det_2_rem,
                ma_2_save=ma_2_save,
                ma_2_rem=ma_2_rem,
                labs_2_save=None,
                labs_2_rem=None,
                **kwargs,
            )

    @cached_property
    def related_object(self) -> Flare:
        return self.flare


class FlareAidDetailBase(AutoPermissionRequiredMixin, DetailView):
    """DetailView for FlareAids."""

    class Meta:
        abstract = True

    model = FlareAid
    object: FlareAid

    def get_permission_object(self):
        return self.object


class FlareAidDetail(FlareAidDetailBase):
    """Overwritten for different url routing/redirecting and assigning the view object."""

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        # If the object has a user, this is the wrong view so redirect to the right one
        if self.object.user:
            return HttpResponseRedirect(self.object.get_absolute_url())
        else:
            # Check if FlareAid is up to date and update if not update
            if not request.GET.get("updated", None):
                self.object.update_aid(qs=self.object)
            return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Overwritten to avoid calling get_object again, which is instead
        called on dispatch()."""
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_queryset(self) -> "QuerySet[Any]":
        return FlareAid.related_objects.filter(pk=self.kwargs["pk"])


class FlareAidPatientBase(FlareAidBase):
    class Meta:
        abstract = True

    onetoones = {}
    req_otos = ["dateofbirth", "gender"]

    def get_user_queryset(self, username: str) -> "QuerySet[Any]":
        """Used to set the user attribute on the view, with associated related models
        select_related and prefetch_related."""
        return Pseudopatient.objects.flareaid_qs().filter(username=username)


class FlareAidPseudopatientCreate(
    FlareAidPatientBase, GoutHelperAidEditMixin, PermissionRequiredMixin, CreateView, SuccessMessageMixin
):
    """View for creating a FlareAid for a patient."""

    permission_required = "flareaids.can_add_flareaid"
    success_message = "%(username)s's FlareAid successfully created."

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Psuedopatient the view is trying to create
        a FlareAid for."""
        return self.user

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, username=self.user.username)

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            _,  # oto_forms,
            _,  # mh_forms,
            _,  # mh_det_forms,
            _,  # ma_forms,
            _,  # lab_formsets,
            _,  # oto_2_save,
            _,  # oto_2_rem,
            mh_2_save,
            mh_2_rem,
            mh_det_2_save,
            mh_det_2_rem,
            ma_2_save,
            ma_2_rem,
            _,  # labs_2_save,
            _,  # labs_2_rem,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        else:
            return self.form_valid(
                form=form,
                oto_2_save=None,
                oto_2_rem=None,
                mh_2_save=mh_2_save,
                mh_2_rem=mh_2_rem,
                mh_det_2_save=mh_det_2_save,
                mh_det_2_rem=mh_det_2_rem,
                ma_2_save=ma_2_save,
                ma_2_rem=ma_2_rem,
                labs_2_save=None,
                labs_2_rem=None,
            )


class FlareAidPseudopatientDetail(FlareAidDetailBase):
    """Overwritten for different url routing, object fetching, and
    building the content data."""

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        """Overwritten to add the FlareAid's user to the context as 'patient'."""
        context = super().get_context_data(**kwargs)
        context["patient"] = self.user
        return context

    def dispatch(self, request, *args, **kwargs):
        """Redirects to the FlareAid CreateView if the user doesn't have a FlareAid. Also,
        redirects to the Pseudopatient UpdateView if the user doesn't have the required
        OneToOne models. These exceptions are raised by the get_object() method."""
        try:
            self.object = self.get_object()
        except FlareAid.DoesNotExist as exc:
            messages.error(request, exc.args[0])
            return HttpResponseRedirect(
                reverse("flareaids:pseudopatient-create", kwargs={"username": kwargs["username"]})
            )
        except (DateOfBirth.DoesNotExist, Gender.DoesNotExist):
            messages.error(request, "Baseline information is needed to use GoutHelper Decision and Treatment Aids.")
            return HttpResponseRedirect(reverse("users:pseudopatient-update", kwargs={"username": self.user.username}))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Updates the object prior to rendering the view. Does not call get_object()."""
        if not request.GET.get("updated", None):
            self.object.update_aid(qs=self.object)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def assign_flareaid_attrs_from_user(
        self, flareaid: FlareAid, user: "User"
    ) -> FlareAid:  # pylint: disable=W0201 # type: ignore
        """Method that assigns attributes from the User QuerySet to the FlareAid for processing in
        service methods and display in the templates. Raises DoesNotExist errors if the related
        model does not exist on the User, which are then used to redirect to the appropriate view."""
        flareaid.dateofbirth = user.dateofbirth
        flareaid.gender = user.gender
        flareaid.medallergys_qs = user.medallergys_qs
        flareaid.medhistorys_qs = user.medhistorys_qs
        return flareaid

    def get_queryset(self) -> "QuerySet[Any]":
        return Pseudopatient.objects.flareaid_qs().filter(username=self.kwargs["username"])

    def get_object(self, *args, **kwargs) -> FlareAid:
        self.user: "User" = self.get_queryset().get()  # pylint: disable=W0201 # type: ignore
        try:
            flareaid: FlareAid = self.user.flareaid
        except FlareAid.DoesNotExist as exc:
            raise FlareAid.DoesNotExist(f"{self.user} does not have a FlareAid. Create one.") from exc
        flareaid = self.assign_flareaid_attrs_from_user(flareaid=flareaid, user=self.user)
        return flareaid


class FlareAidPseudopatientUpdate(
    FlareAidPatientBase, GoutHelperAidEditMixin, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin
):
    success_message = "%(username)s's FlareAid successfully updated."

    def get_permission_object(self):
        return self.object

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, username=self.user.username)

    def post(self, request, *args, **kwargs):
        """Overwritten to finish the post() method and avoid conflicts with the MRO.
        For FlareAid, no additional processing is needed."""
        (
            errors,
            form,
            _,  # oto_forms,
            _,  # mh_forms,
            _,  # mh_det_forms,
            _,  # ma_forms,
            _,  # lab_formsets,
            _,  # oto_2_save,
            _,  # oto_2_rem,
            mh_2_save,
            mh_2_rem,
            mh_det_2_save,
            mh_det_2_rem,
            ma_2_save,
            ma_2_rem,
            _,  # labs_2_save,
            _,  # labs_2_rem,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        else:
            return self.form_valid(
                form=form,
                oto_2_save=None,
                oto_2_rem=None,
                mh_2_save=mh_2_save,
                mh_2_rem=mh_2_rem,
                mh_det_2_save=mh_det_2_save,
                mh_det_2_rem=mh_det_2_rem,
                ma_2_save=ma_2_save,
                ma_2_rem=ma_2_rem,
                labs_2_save=None,
                labs_2_rem=None,
            )


class FlareAidUpdate(
    FlareAidBase, GoutHelperAidEditMixin, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin
):
    """Updates a FlareAid"""

    success_message = "FlareAid successfully updated."

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        if self.flare:
            kwargs.update({"flare": self.flare})
        return kwargs

    @cached_property
    def flare(self) -> Flare | None:
        return getattr(self.object, "flare", None)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add ultaid to context if it exists."""
        context = super().get_context_data(**kwargs)
        context.update({"flare": self.flare})
        return context

    def get_queryset(self):
        return FlareAid.related_objects.filter(pk=self.kwargs["pk"])

    def get_permission_object(self):
        return self.object

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            _,  # oto_forms,
            _,  # mh_forms,
            _,  # mh_det_forms,
            _,  # ma_forms,
            _,  # lab_formsets,
            oto_2_save,
            oto_2_rem,
            mh_2_save,
            mh_2_rem,
            mh_det_2_save,
            mh_det_2_rem,
            ma_2_save,
            ma_2_rem,
            _,  # labs_2_save,
            _,  # labs_2_rem,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        else:
            return self.form_valid(
                form=form,
                oto_2_rem=oto_2_rem,
                oto_2_save=oto_2_save,
                mh_2_save=mh_2_save,
                mh_2_rem=mh_2_rem,
                mh_det_2_save=mh_det_2_save,
                mh_det_2_rem=mh_det_2_rem,
                ma_2_save=ma_2_save,
                ma_2_rem=ma_2_rem,
                labs_2_save=None,
                labs_2_rem=None,
            )

    @cached_property
    def related_object(self) -> Flare:
        return self.flare
