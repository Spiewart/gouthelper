from typing import TYPE_CHECKING, Any

from django.apps import apps  # pylint: disable=E0401  # type: ignore
from django.contrib import messages  # pylint: disable=E0401  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # pylint: disable=E0401  # type: ignore
from django.http import HttpResponseRedirect  # pylint: disable=E0401  # type: ignore
from django.urls import reverse  # pylint: disable=E0401  # type: ignore
from django.views.generic import (  # pylint: disable=E0401  # type: ignore
    CreateView,
    DetailView,
    TemplateView,
    UpdateView,
)
from rules.contrib.views import (  # pylint: disable=e0401, E0611  # type: ignore
    AutoPermissionRequiredMixin,
    PermissionRequiredMixin,
)

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
    AnginaForm,
    CadForm,
    ChfForm,
    CkdForm,
    HeartattackForm,
    HepatitisForm,
    OrgantransplantForm,
    PvdForm,
    StrokeForm,
    UratestonesForm,
    XoiinteractionForm,
)
from ..medhistorys.models import (
    Angina,
    Cad,
    Chf,
    Ckd,
    Heartattack,
    Hepatitis,
    Organtransplant,
    Pvd,
    Stroke,
    Uratestones,
    Xoiinteraction,
)
from ..treatments.choices import UltChoices
from ..users.models import Pseudopatient
from ..utils.views import GoutHelperAidEditMixin
from .forms import UltAidForm
from .models import UltAid

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # type: ignore
    from django.db.models import QuerySet  # type: ignore

    User = get_user_model()


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

    form_class = UltAidForm
    model = UltAid
    onetoones = {
        "dateofbirth": {"form": DateOfBirthFormOptional, "model": DateOfBirth},
        "ethnicity": {"form": EthnicityForm, "model": Ethnicity},
        "gender": {"form": GenderFormOptional, "model": Gender},
        "hlab5801": {"form": Hlab5801Form, "model": Hlab5801},
    }
    medallergys = UltChoices
    medhistorys = {
        MedHistoryTypes.ANGINA: {"form": AnginaForm, "model": Angina},
        MedHistoryTypes.CAD: {"form": CadForm, "model": Cad},
        MedHistoryTypes.CHF: {"form": ChfForm, "model": Chf},
        MedHistoryTypes.CKD: {"form": CkdForm, "model": Ckd},
        MedHistoryTypes.HEARTATTACK: {"form": HeartattackForm, "model": Heartattack},
        MedHistoryTypes.HEPATITIS: {"form": HepatitisForm, "model": Hepatitis},
        MedHistoryTypes.ORGANTRANSPLANT: {"form": OrgantransplantForm, "model": Organtransplant},
        MedHistoryTypes.PVD: {"form": PvdForm, "model": Pvd},
        MedHistoryTypes.STROKE: {"form": StrokeForm, "model": Stroke},
        MedHistoryTypes.URATESTONES: {"form": UratestonesForm, "model": Uratestones},
        MedHistoryTypes.XOIINTERACTION: {"form": XoiinteractionForm, "model": Xoiinteraction},
    }
    medhistory_details = {MedHistoryTypes.CKD: CkdDetailOptionalForm}


class UltAidCreate(UltAidBase, GoutHelperAidEditMixin, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """Create a new UltAid"""

    permission_required = "ultaids.can_add_ultaid"
    success_message = "UltAid created successfully!"

    def get_permission_object(self):
        return None

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
            )


class UltAidDetailBase(AutoPermissionRequiredMixin, DetailView):
    """DetailView for UltAids."""

    model = UltAid
    object: UltAid

    def get_permission_object(self):
        return self.object


class UltAidDetail(UltAidDetailBase):
    """Overwritten for different url routing/redirecting and assigning the view object."""

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        # If the object has a user, this is the wrong view so redirect to the right one
        if self.object.user:
            return HttpResponseRedirect(self.object.get_absolute_url())
        else:
            # Check if UltAid is up to date and update if not update
            if not request.GET.get("updated", None):
                self.object.update_aid(qs=self.object)
            return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Overwritten to avoid calling get_object again, which is instead
        called on dispatch()."""
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_queryset(self) -> "QuerySet[Any]":
        return UltAid.related_objects.filter(pk=self.kwargs["pk"])

    def get_object(self, *args, **kwargs) -> UltAid:
        """Overwritten to prefetch goalurate medhistory_qs for use in the template and to avoid additional queries.
        Also, if the UltAId has a GoalUrate, update it if it isn't marked as updated in the url params."""
        ultaid: UltAid = super().get_object(*args, **kwargs)  # type: ignore
        if hasattr(ultaid, "goalurate"):
            ultaid.goalurate.medhistorys_qs = ultaid.goalurate.medhistory_set.all()
            if not self.request.GET.get("goalurate_updated", None):
                ultaid.goalurate.update_aid(qs=ultaid.goalurate)
        return ultaid


class UltAidPatientBase(UltAidBase):
    """Base class for UltAidCreate/Update views for UltAids that have a user."""

    class Meta:
        abstract = True

    onetoones = {"hlab5801": {"form": Hlab5801Form, "model": Hlab5801}}
    req_otos = ["dateofbirth", "gender", "ethnicity"]

    def get_user_queryset(self, username: str) -> "QuerySet[Any]":
        """Used to set the user attribute on the view, with associated related models
        select_related and prefetch_related."""
        return Pseudopatient.objects.ultaid_qs().filter(username=username)


class UltAidPseudopatientCreate(
    UltAidPatientBase, GoutHelperAidEditMixin, PermissionRequiredMixin, CreateView, SuccessMessageMixin
):
    """View for creating a UltAid for a patient."""

    permission_required = "ultaids.can_add_ultaid"
    success_message = "%(username)s's UltAid successfully created."

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Psuedopatient the view is trying to create
        a UltAid for."""
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
            )


class UltAidPseudopatientDetail(UltAidDetailBase):
    """DetailView for UltAids that have a user."""

    def dispatch(self, request, *args, **kwargs):
        """Redirects to the UltAid CreateView if the user doesn't have a UltAid. Also,
        redirects to the Pseudopatient UpdateView if the user doesn't have the required
        OneToOne models. These exceptions are raised by the get_object() method."""
        try:
            self.object = self.get_object()
        except UltAid.DoesNotExist as exc:
            messages.error(request, exc.args[0])
            return HttpResponseRedirect(
                reverse("ultaids:pseudopatient-create", kwargs={"username": kwargs["username"]})
            )
        except (DateOfBirth.DoesNotExist, Ethnicity.DoesNotExist, Gender.DoesNotExist):
            messages.error(request, "Baseline information is needed to use GoutHelper Decision and Treatment Aids.")
            return HttpResponseRedirect(reverse("users:pseudopatient-update", kwargs={"username": self.user.username}))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        """Overwritten to add the UltAid's user to the context as 'patient'."""
        context = super().get_context_data(**kwargs)
        context["patient"] = self.user
        return context

    def get(self, request, *args, **kwargs):
        """Updates the object prior to rendering the view. Does not call get_object()."""
        if not request.GET.get("updated", None):
            self.object.update_aid(qs=self.object)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    @classmethod
    def assign_ultaid_attrs_from_user(
        cls, ultaid: UltAid, user: "User"
    ) -> UltAid:  # pylint: disable=W0613  # type: ignore
        """Method that assigns attributes from the User QuerySet to the UltAid, and related GoalUrate
        if it exists, for processing in service methods and display in the templates. Raises
        DoesNotExist errors if the related model does not exist on the User, which are then
        used to redirect to the appropriate view."""
        ultaid.dateofbirth = user.dateofbirth
        ultaid.ethnicity = user.ethnicity
        ultaid.gender = user.gender
        if hasattr(user, "hlab5801"):
            ultaid.hlab5801 = user.hlab5801
        if hasattr(user, "goalurate"):
            ultaid.goalurate = user.goalurate
            ultaid.goalurate.medhistorys_qs = user.medhistorys_qs
        ultaid.medallergys_qs = user.medallergys_qs
        ultaid.medhistorys_qs = user.medhistorys_qs
        return ultaid

    def get_queryset(self) -> "QuerySet[Any]":
        return Pseudopatient.objects.ultaid_qs().filter(username=self.kwargs["username"])

    def get_object(self, *args, **kwargs) -> UltAid:
        self.user: User = self.get_queryset().get()  # pylint: disable=W0201 # type: ignore
        try:
            ultaid: UltAid = self.user.ultaid
        except UltAid.DoesNotExist as exc:
            raise UltAid.DoesNotExist(f"{self.user} does not have a UltAid. Create one.") from exc
        ultaid = self.assign_ultaid_attrs_from_user(ultaid=ultaid, user=self.user)
        return ultaid


class UltAidPseudopatientUpdate(
    UltAidPatientBase, GoutHelperAidEditMixin, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin
):
    """UpdateView for UltAids with a User."""

    success_message = "%(username)s's UltAid successfully updated."

    def get_permission_object(self):
        return self.object

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, username=self.user.username)

    def post(self, request, *args, **kwargs):
        """Overwritten to finish the post() method and avoid conflicts with the MRO.
        For UltAid, no additional processing is needed."""
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
            )


class UltAidUpdate(UltAidBase, GoutHelperAidEditMixin, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin):
    """Updates a UltAid"""

    success_message = "UltAid updated successfully!"

    def get_queryset(self):
        return UltAid.related_objects.filter(pk=self.kwargs["pk"])

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
