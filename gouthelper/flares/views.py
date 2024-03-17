from typing import TYPE_CHECKING, Any  # pylint: disable=E0015, E0013 # type: ignore

from django.apps import apps  # pylint: disable=e0401 # type: ignore
from django.contrib import messages  # pylint: disable=e0401 # type: ignore
from django.contrib.auth import get_user_model  # pylint: disable=e0401 # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # pylint: disable=e0401 # type: ignore
from django.core.exceptions import ValidationError  # pylint: disable=e0401 # type: ignore
from django.http import Http404, HttpResponseRedirect  # pylint: disable=e0401 # type: ignore
from django.urls import reverse  # pylint: disable=e0401 # type: ignore
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

from ..contents.choices import Contexts
from ..dateofbirths.forms import DateOfBirthForm
from ..dateofbirths.models import DateOfBirth
from ..genders.forms import GenderForm
from ..genders.models import Gender
from ..labs.forms import UrateFlareForm
from ..labs.models import Urate
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
from ..medhistorys.models import Angina, Cad, Chf, Ckd, Gout, Heartattack, Hypertension, Menopause, Pvd, Stroke
from ..users.models import Pseudopatient
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

    onetoones = {
        "dateofbirth": {"form": DateOfBirthForm, "model": DateOfBirth},
        "gender": {"form": GenderForm, "model": Gender},
        "urate": {"form": UrateFlareForm, "model": Urate},
    }
    medhistorys = {
        MedHistoryTypes.ANGINA: {"form": AnginaForm, "model": Angina},
        MedHistoryTypes.CAD: {"form": CadForm, "model": Cad},
        MedHistoryTypes.CHF: {"form": ChfForm, "model": Chf},
        MedHistoryTypes.CKD: {"form": CkdForm, "model": Ckd},
        MedHistoryTypes.GOUT: {"form": GoutForm, "model": Gout},
        MedHistoryTypes.HEARTATTACK: {"form": HeartattackForm, "model": Heartattack},
        MedHistoryTypes.HYPERTENSION: {"form": HypertensionForm, "model": Hypertension},
        MedHistoryTypes.MENOPAUSE: {"form": MenopauseForm, "model": Menopause},
        MedHistoryTypes.PVD: {"form": PvdForm, "model": Pvd},
        MedHistoryTypes.STROKE: {"form": StrokeForm, "model": Stroke},
    }
    req_otos = {}

    def post_process_urate_check(
        self,
        form: "ModelForm",
        oto_forms: dict[str, "ModelForm"],
        errors_bool: bool = False,
    ) -> tuple["ModelForm", dict[str, "ModelForm"], bool]:
        urate_val = oto_forms["urate_form"].cleaned_data.get("value", None)
        urate_check = form.cleaned_data.get("urate_check", None)
        if urate_check and not urate_val:
            urate_error = ValidationError(message="If urate was checked, we should know it!")
            form.add_error("urate_check", urate_error)
            oto_forms["urate_form"].add_error("value", urate_error)
            errors_bool = True
        return form, oto_forms, errors_bool


class FlareCreate(FlareBase, GoutHelperAidEditMixin, AutoPermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """Creates a new Flare"""

    success_message = "Flare created successfully!"

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            oto_forms,
            mh_forms,
            mh_det_forms,
            _,  # ma_forms,
            _,  # lab_formsets,
            oto_2_save,
            oto_2_rem,
            mh_2_save,
            mh_2_rem,
            mh_det_2_save,
            mh_det_2_rem,
            _,  # ma_2_save,
            _,  # ma_2_rem,
            _,  # labs_2_save,
            _,  # labs_2_rem,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        mh_forms, errors_bool = self.post_process_menopause(
            mh_forms=mh_forms,
            dateofbirth=oto_forms["dateofbirth_form"].cleaned_data.get("value"),
            gender=oto_forms["gender_form"].cleaned_data.get("value"),
        )
        form, oto_forms, errors_bool = self.post_process_urate_check(
            form=form, oto_forms=oto_forms, errors_bool=errors_bool
        )
        if errors_bool:
            return super().render_errors(
                form=form,
                oto_forms=oto_forms,
                mh_forms=mh_forms,
                mh_det_forms=mh_det_forms,
                ma_forms=None,
                lab_formsets=None,
                labs=None,
            )
        else:
            return self.form_valid(
                form=form,
                oto_2_save=oto_2_save,
                oto_2_rem=oto_2_rem,
                mh_2_save=mh_2_save,
                mh_2_rem=mh_2_rem,
                mh_det_2_save=mh_det_2_save,
                mh_det_2_rem=mh_det_2_rem,
                ma_2_save=None,
                ma_2_rem=None,
                labs_2_save=None,
                labs_2_rem=None,
            )


class FlareDetailBase(AutoPermissionRequiredMixin, DetailView):
    class Meta:
        abstract = True

    model = Flare
    object: Flare

    @property
    def contents(self):
        return apps.get_model("contents.Content").objects.filter(context=Contexts.FLARE, tag__isnull=False)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        for content in self.contents:
            context.update({content.slug: {content.tag: content}})  # type: ignore
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
    onetoones = {"urate": {"form": UrateFlareForm, "model": Urate}}
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

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            oto_forms,
            mh_forms,
            mh_det_forms,
            _,  # ma_forms,
            _,  # lab_formsets,
            oto_2_save,
            oto_2_rem,
            mh_2_save,
            mh_2_rem,
            mh_det_2_save,
            mh_det_2_rem,
            _,  # ma_2_save,
            _,  # ma_2_rem,
            _,  # labs_2_save,
            _,  # labs_2_rem,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        form, oto_forms, errors_bool = self.post_process_urate_check(
            form=form, oto_forms=oto_forms, errors_bool=errors
        )
        if errors_bool:
            return super().render_errors(
                form=form,
                oto_forms=oto_forms,
                mh_forms=mh_forms,
                mh_det_forms=mh_det_forms,
                ma_forms=None,
                lab_formsets=None,
                labs=None,
            )
        else:
            return self.form_valid(
                form=form,
                oto_2_save=oto_2_save,
                oto_2_rem=oto_2_rem,
                mh_2_save=mh_2_save,
                mh_2_rem=mh_2_rem,
                mh_det_2_save=mh_det_2_save,
                mh_det_2_rem=mh_det_2_rem,
                ma_2_save=None,
                ma_2_rem=None,
                labs_2_save=None,
                labs_2_rem=None,
            )

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
        if getattr(self.object, "crystal_analysis") is not None:
            initial["aspiration"] = True
        elif getattr(self.object, "diagnosed"):
            initial["aspiration"] = False
        else:
            initial["aspiration"] = None
        if getattr(self.object, "urate", None):
            initial["urate_check"] = True
        else:
            initial["urate_check"] = False
        return initial

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, username=self.user.username)

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            oto_forms,
            mh_forms,
            mh_det_forms,
            ma_forms,
            lab_formsets,
            oto_2_save,
            oto_2_rem,
            mh_2_save,
            mh_2_rem,
            mh_det_2_save,
            mh_det_2_rem,
            _,  # ma_2_save,
            _,  # ma_2_rem,
            _,  # labs_2_save,
            _,  # labs_2_rem,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        form, oto_forms, errors_bool = self.post_process_urate_check(form=form, oto_forms=oto_forms)
        if errors_bool:
            return super().render_errors(
                form=form,
                oto_forms=oto_forms,
                mh_forms=mh_forms,
                mh_det_forms=mh_det_forms,
                ma_forms=ma_forms,
                lab_formsets=lab_formsets,
                labs=self.labs if hasattr(self, "labs") else None,
            )
        return self.form_valid(
            form=form,
            oto_2_save=oto_2_save,
            oto_2_rem=oto_2_rem,
            mh_2_save=mh_2_save,
            mh_2_rem=mh_2_rem,
            mh_det_2_save=mh_det_2_save,
            mh_det_2_rem=mh_det_2_rem,
            ma_2_save=None,
            ma_2_rem=None,
            labs_2_save=None,
            labs_2_rem=None,
        )


class FlareUpdate(FlareBase, GoutHelperAidEditMixin, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin):
    """Updates a Flare"""

    success_message = "Flare updated successfully!"

    def get_initial(self) -> dict[str, Any]:
        """Overwrite get_initial() to populate form non-field form inputs"""
        initial = super().get_initial()
        if getattr(self.object, "crystal_analysis") is not None:
            initial["aspiration"] = True
        elif getattr(self.object, "diagnosed"):
            initial["aspiration"] = False
        else:
            initial["aspiration"] = None
        if getattr(self.object, "urate", None):
            initial["urate_check"] = True
        else:
            initial["urate_check"] = False
        return initial

    def get_queryset(self):
        return Flare.related_objects.filter(pk=self.kwargs["pk"])

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            oto_forms,
            mh_forms,
            mh_det_forms,
            _,  # ma_forms,
            _,  # lab_formsets,
            oto_2_save,
            oto_2_rem,
            mh_2_save,
            mh_2_rem,
            mh_det_2_save,
            mh_det_2_rem,
            _,  # ma_2_save,
            _,  # ma_2_rem,
            _,  # labs_2_save,
            _,  # labs_2_rem,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        mh_forms, errors_bool = self.post_process_menopause(mh_forms=mh_forms, post_object=form.instance)
        form, oto_forms, errors_bool = self.post_process_urate_check(
            form=form, oto_forms=oto_forms, errors_bool=errors_bool
        )
        if errors_bool:
            return super().render_errors(
                form=form,
                oto_forms=oto_forms,
                mh_forms=mh_forms,
                mh_det_forms=mh_det_forms,
                ma_forms=None,
                lab_formsets=None,
                labs=None,
            )
        return self.form_valid(
            form=form,
            oto_2_save=oto_2_save,
            oto_2_rem=oto_2_rem,
            mh_2_save=mh_2_save,
            mh_2_rem=mh_2_rem,
            mh_det_2_save=mh_det_2_save,
            mh_det_2_rem=mh_det_2_rem,
            ma_2_save=None,
            ma_2_rem=None,
            labs_2_save=None,
            labs_2_rem=None,
        )
