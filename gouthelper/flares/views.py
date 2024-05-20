from typing import TYPE_CHECKING, Any  # pylint: disable=E0015, E0013 # type: ignore

from django.apps import apps  # pylint: disable=e0401 # type: ignore
from django.contrib import messages  # pylint: disable=e0401 # type: ignore
from django.contrib.auth import get_user_model  # pylint: disable=e0401 # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # pylint: disable=e0401 # type: ignore
from django.core.exceptions import ValidationError  # pylint: disable=e0401 # type: ignore
from django.http import Http404, HttpResponseRedirect  # pylint: disable=e0401 # type: ignore
from django.urls import reverse  # pylint: disable=e0401 # type: ignore
from django.utils.functional import cached_property  # pylint: disable=e0401 # type: ignore
from django.views.generic import (  # pylint: disable=e0401 # type: ignore
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)
from rules.contrib.views import (  # pylint: disable=e0401 # type: ignore
    AutoPermissionRequiredMixin,
    PermissionRequiredMixin,
)

from ..akis.forms import AkiForm
from ..akis.models import Aki
from ..contents.choices import Contexts
from ..dateofbirths.forms import DateOfBirthForm
from ..dateofbirths.models import DateOfBirth
from ..genders.forms import GenderForm
from ..genders.models import Gender
from ..labs.forms import CreatinineFormHelper, FlareCreatinineFormSet, UrateFlareForm
from ..labs.models import Creatinine, Urate
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.forms import (
    AnginaForm,
    CadForm,
    ChfForm,
    CkdForm,
    GoutForm,
    HeartattackForm,
    HypertensionForm,
    MenopauseForm,
    PvdForm,
    StrokeForm,
)
from ..medhistorys.models import Angina, Cad, Chf, Ckd, Heartattack, Hypertension, Pvd, Stroke
from ..users.models import Pseudopatient
from ..utils.helpers import get_str_attrs
from ..utils.views import GoutHelperAidEditMixin
from .forms import FlareForm
from .models import Flare

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore
    from django.forms import ModelForm  # type: ignore

User = get_user_model()


class FlareAbout(TemplateView):
    """About Flares"""

    template_name = "flares/about.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"content": self.content})
        return context

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="about", context=Contexts.FLARE, tag=None)


class FlareBase:
    class Meta:
        abstract = True

    form_class = FlareForm
    model = Flare
    success_message = "Flare created successfully!"

    @cached_property
    def creatinine_formset_qs(self):
        return (
            Creatinine.objects.filter(aki=self.object.aki)
            if hasattr(self.object, "aki")
            else Creatinine.objects.none()
        )

    def post_process_urate_check(self) -> tuple["ModelForm", dict[str, "ModelForm"], bool]:
        urate_val = self.oto_forms["urate_form"].cleaned_data.get("value", None)
        urate_check = self.form.cleaned_data.get("urate_check", None)
        if urate_check and not urate_val:
            urate_error = ValidationError(
                message="If the serum uric acid was checked, please tell us the value! \
If you don't know the value, please uncheck the Uric Acid Lab Check box."
            )
            self.form.add_error("urate_check", urate_error)
            self.oto_forms["urate_form"].add_error("value", urate_error)
            if not self.errors_bool:
                self.errors_bool = True
        return self.form, self.oto_forms, self.errors_bool

    def set_lab_formsets(self) -> None:
        self.lab_formsets = {"creatinine": (FlareCreatinineFormSet, CreatinineFormHelper)}

    def set_medhistory_forms(self) -> None:
        self.medhistory_forms = {
            MedHistoryTypes.ANGINA: {"form": AnginaForm},
            MedHistoryTypes.CAD: {"form": CadForm},
            MedHistoryTypes.CHF: {"form": ChfForm},
            MedHistoryTypes.CKD: {"form": CkdForm},
            MedHistoryTypes.GOUT: {"form": GoutForm},
            MedHistoryTypes.HEARTATTACK: {"form": HeartattackForm},
            MedHistoryTypes.HYPERTENSION: {"form": HypertensionForm},
            MedHistoryTypes.MENOPAUSE: {"form": MenopauseForm},
            MedHistoryTypes.PVD: {"form": PvdForm},
            MedHistoryTypes.STROKE: {"form": StrokeForm},
        }

    def set_oto_forms(self) -> None:
        self.oto_forms = {
            "aki": {"form": AkiForm},
            "dateofbirth": {"form": DateOfBirthForm},
            "gender": {"form": GenderForm},
            "urate": {"form": UrateFlareForm},
        }

    def set_req_otos(self) -> None:
        self.req_otos = []


class FlareCreate(FlareBase, GoutHelperAidEditMixin, AutoPermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """Creates a new Flare"""

    success_message = "Flare created successfully!"

    @cached_property
    def creatinine_formset_qs(self):
        return Creatinine.objects.none()

    def get_initial(self) -> dict[str, Any]:
        initial = super().get_initial()
        initial["onset"] = None
        initial["redness"] = None
        return initial

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        self.mh_forms, self.errors_bool = self.post_process_menopause(
            mh_forms=self.mh_forms,
            dateofbirth=(
                self.oto_forms["dateofbirth_form"].cleaned_data.get("value")
                if hasattr(self.oto_forms["dateofbirth_form"], "cleaned_data")
                else None
            ),
            gender=(
                self.oto_forms["gender_form"].cleaned_data.get("value")
                if hasattr(self.oto_forms["gender_form"], "cleaned_data")
                else None
            ),
        )
        self.form, self.oto_forms, self.errors_bool = self.post_process_urate_check(
            form=self.form, oto_forms=self.oto_forms, errors_bool=self.errors_bool
        )
        if self.errors or self.errors_bool:
            if self.errors_bool and not self.errors:
                return super().render_errors(
                    form=self.form,
                    oto_forms=self.oto_forms,
                    mh_forms=self.mh_forms,
                    mh_det_forms=self.mh_det_forms,
                    ma_forms=self.ma_forms,
                    lab_formsets=self.lab_formsets,
                )
            else:
                return self.errors
        else:
            return self.form_valid()


class FlareDetailBase(AutoPermissionRequiredMixin, DetailView):
    class Meta:
        abstract = True

    model = Flare
    object: Flare

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"str_attrs": get_str_attrs(self.object, self.object.user, self.request.user)})
        return context

    def get_permission_object(self):
        return self.object


class FlareDetail(FlareDetailBase):
    """View for viewing a Flare"""

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Check if the object has a User and if there is no username in the kwargs,
        # redirect to the username url
        if self.object.user:
            return HttpResponseRedirect(self.object.get_absolute_url())
        else:
            # Check if Flare is up to date and update if not update
            if not request.GET.get("updated", None):
                self.object.update_aid(qs=self.object)
            return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not hasattr(self, "object"):
            self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_queryset(self) -> "QuerySet[Any]":
        return Flare.related_objects.filter(pk=self.kwargs["pk"])


class FlarePatientBase(FlareBase):
    medhistorys = {
        MedHistoryTypes.ANGINA: {"form": AnginaForm, "model": Angina},
        MedHistoryTypes.CAD: {"form": CadForm, "model": Cad},
        MedHistoryTypes.CHF: {"form": ChfForm, "model": Chf},
        MedHistoryTypes.CKD: {"form": CkdForm, "model": Ckd},
        MedHistoryTypes.HEARTATTACK: {"form": HeartattackForm, "model": Heartattack},
        MedHistoryTypes.HYPERTENSION: {"form": HypertensionForm, "model": Hypertension},
        MedHistoryTypes.PVD: {"form": PvdForm, "model": Pvd},
        MedHistoryTypes.STROKE: {"form": StrokeForm, "model": Stroke},
    }
    onetoones = {"aki": {"form": AkiForm, "model": Aki}, "urate": {"form": UrateFlareForm, "model": Urate}}
    req_otos = ["dateofbirth", "gender"]

    def get_user_queryset(self, username: str) -> "QuerySet[Any]":
        """Used to set the user attribute on the view, with associated related models
        select_related and prefetch_related."""
        return Pseudopatient.objects.flares_qs(flare_pk=self.kwargs.get("pk")).filter(  # pylint:disable=E1101
            username=username
        )


class FlarePseudopatientList(PermissionRequiredMixin, ListView):
    context_object_name = "flares"
    model = Flare
    permission_required = "flares.can_view_flare_list"
    template_name = "flares/flare_list.html"

    def dispatch(self, request, *args, **kwargs):
        self.user = self.get_queryset().get()
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.object_list = self.user.flares_qs
        context = self.get_context_data()
        return self.render_to_response(context)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["patient"] = Pseudopatient.objects.get(username=self.kwargs["username"])
        return context

    def get_permission_object(self):
        return self.user

    def get_queryset(self):
        return Pseudopatient.objects.flares_qs().filter(username=self.kwargs["username"])


class FlarePseudopatientCreate(
    FlarePatientBase, GoutHelperAidEditMixin, PermissionRequiredMixin, CreateView, SuccessMessageMixin
):
    """View for creating a Flare for a patient."""

    permission_required = "flares.can_add_flare"
    success_message = "%(username)s's Flare successfully created."

    def get_initial(self) -> dict[str, Any]:
        initial = super().get_initial()
        initial["onset"] = None
        initial["redness"] = None
        return initial

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        self.form, self.oto_forms, self.errors_bool = self.post_process_urate_check(
            form=self.form, oto_forms=self.oto_forms, errors_bool=self.errors
        )
        if self.errors or self.errors_bool:
            if self.errors_bool and not self.errors:
                return super().render_errors(
                    form=self.form,
                    oto_forms=self.oto_forms,
                    mh_forms=self.mh_forms,
                    mh_det_forms=self.mh_det_forms,
                    ma_forms=self.ma_forms,
                    lab_formsets=self.lab_formsets,
                )
            else:
                return self.errors
        else:
            return self.form_valid()

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, username=self.user.username)


class FlarePseudopatientDelete(AutoPermissionRequiredMixin, DeleteView):
    """View for deleting a Flare for a patient."""

    model = Flare
    success_message = "Flare successfully deleted."

    def dispatch(self, request, *args, **kwargs):
        # Set the user and object with get_object()
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, *args, **kwargs) -> Flare:
        """Overwritten to set the user attr on the view."""
        try:
            self.user: User = self.get_queryset().get()
        except User.DoesNotExist as exc:
            raise Http404(f"User with username {self.kwargs['username']} does not exist.") from exc
        try:
            flare: Flare = self.user.flare_qs[0]
        except IndexError as exc:
            raise Http404(f"Flare for {self.user} does not exist.") from exc
        return flare

    def get_permission_object(self):
        return self.object

    def get_success_url(self) -> str:
        return reverse("flares:pseudopatient-list", kwargs={"username": self.object.user.username})

    def get_queryset(self) -> "QuerySet[Any]":
        return Pseudopatient.objects.flares_qs(flare_pk=self.kwargs["pk"]).filter(username=self.kwargs["username"])


class FlarePseudopatientDetail(FlareDetailBase):
    """Overwritten for different url routing, object fetching, and
    building the content data."""

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["patient"] = self.user
        return context

    def dispatch(self, request, *args, **kwargs):
        """Overwritten to check for a User on the object and redirect to the
        correct FlarePseudopatientCreate url instead. Also checks if the user has
        the correct OneToOne models and redirects to the view to add them if not."""
        try:
            self.object = self.get_object()
        except (DateOfBirth.DoesNotExist, Gender.DoesNotExist):
            messages.error(request, "Baseline information is needed to use GoutHelper Decision and Treatment Aids.")
            return HttpResponseRedirect(reverse("users:pseudopatient-update", kwargs={"username": self.user.username}))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Check if Flare is up to date and update if not update
        if not request.GET.get("updated", None):
            self.object.update_aid(qs=self.object)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def assign_flare_attrs_from_user(self, flare: Flare, user: "User") -> Flare:
        flare.dateofbirth = user.dateofbirth
        flare.gender = user.gender
        flare.medhistorys_qs = user.medhistorys_qs
        return flare

    def get_queryset(self) -> "QuerySet[Any]":
        return Pseudopatient.objects.flares_qs(flare_pk=self.kwargs["pk"]).filter(username=self.kwargs["username"])

    def get_object(self, *args, **kwargs) -> Flare:
        try:
            self.user: User = self.get_queryset().get()
        except User.DoesNotExist as exc:
            raise Http404(f"User with username {self.kwargs['username']} does not exist.") from exc
        try:
            flare: Flare = self.user.flare_qs[0]
        except IndexError as exc:
            raise Http404(f"Flare for {self.user} does not exist.") from exc
        flare = self.assign_flare_attrs_from_user(flare=flare, user=self.user)
        return flare


class FlarePseudopatientUpdate(
    FlarePatientBase, GoutHelperAidEditMixin, PermissionRequiredMixin, UpdateView, SuccessMessageMixin
):
    permission_required = "flares.can_change_flare"
    success_message = "%(username)s's FlareAid successfully updated."

    def get_initial(self) -> dict[str, Any]:
        """Overwrite get_initial() to populate form non-field field inputs"""
        initial = super().get_initial()
        crystal_analysis = getattr(self.object, "crystal_analysis")
        diagnosed = getattr(self.object, "diagnosed")
        urate = getattr(self.object, "urate")
        if crystal_analysis is not None or diagnosed is not None or urate is not None:
            initial["medical_evaluation"] = True
            if crystal_analysis is not None:
                initial["aspiration"] = True
            else:
                initial["aspiration"] = False
            if urate is not None:
                initial["urate_check"] = True
            else:
                initial["urate_check"] = False
        else:
            initial["medical_evaluation"] = False
            initial["aspiration"] = None
            initial["diagnosed"] = None
            initial["urate_check"] = None
        return initial

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, username=self.user.username)

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        self.form, self.oto_forms, self.errors_bool = self.post_process_urate_check(
            form=self.form, oto_forms=self.oto_forms
        )
        if self.errors or self.errors_bool:
            if self.errors_bool and not self.errors:
                return super().render_errors(
                    form=self.form,
                    oto_forms=self.oto_forms,
                    mh_forms=self.mh_forms,
                    mh_det_forms=self.mh_det_forms,
                    ma_forms=self.ma_forms,
                    lab_formsets=self.lab_formsets,
                )
            else:
                return self.errors
        return self.form_valid()


class FlareUpdate(FlareBase, GoutHelperAidEditMixin, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin):
    """Updates a Flare"""

    success_message = "Flare updated successfully!"

    def get_initial(self) -> dict[str, Any]:
        """Overwrite get_initial() to populate form non-field field inputs"""
        initial = super().get_initial()
        crystal_analysis = getattr(self.object, "crystal_analysis")
        diagnosed = getattr(self.object, "diagnosed")
        urate = getattr(self.object, "urate")
        if crystal_analysis is not None or diagnosed is not None or urate is not None:
            initial["medical_evaluation"] = True
            if crystal_analysis is not None:
                initial["aspiration"] = True
            else:
                initial["aspiration"] = False
            if urate is not None:
                initial["urate_check"] = True
            else:
                initial["urate_check"] = False
        else:
            initial["medical_evaluation"] = False
            initial["aspiration"] = None
            initial["diagnosed"] = None
            initial["urate_check"] = None
        return initial

    def get_queryset(self):
        return Flare.related_objects.filter(pk=self.kwargs["pk"])

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        self.mh_forms, self.errors_bool = self.post_process_menopause(
            mh_forms=self.mh_forms, post_object=self.form.instance
        )
        self.form, self.oto_forms, self.errors_bool = self.post_process_urate_check(
            form=self.form, oto_forms=self.oto_forms, errors_bool=self.errors_bool
        )
        if self.errors or self.errors_bool:
            if self.errors_bool and not self.errors:
                return super().render_errors(
                    form=self.form,
                    oto_forms=self.oto_forms,
                    mh_forms=self.mh_forms,
                    mh_det_forms=self.mh_det_forms,
                    ma_forms=None,
                    lab_formsets=self.lab_formsets,
                )
            else:
                return self.errors
        return self.form_valid()
