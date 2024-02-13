from typing import TYPE_CHECKING, Any, Union  # pylint: disable=e0015

from django.apps import apps  # pylint: disable=e0401 # type: ignore
from django.contrib import messages  # pylint: disable=e0401 # type: ignore
from django.contrib.auth import get_user_model  # pylint: disable=e0401 # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # pylint: disable=e0401 # type: ignore
from django.http import HttpResponseRedirect  # pylint: disable=e0401 # type: ignore
from django.urls import reverse  # pylint: disable=e0401 # type: ignore
from django.views.generic import (  # pylint: disable=e0401 # type: ignore
    CreateView,
    DetailView,
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
from ..utils.views import MedHistoryModelBaseMixin
from .forms import PpxAidForm
from .models import PpxAid
from .selectors import ppxaid_user_qs, ppxaid_userless_qs

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet  # type: ignore
    from django.http import HttpResponse  # type: ignore

    from ..labs.models import BaselineCreatinine, Lab
    from ..medallergys.models import MedAllergy
    from ..medhistorydetails.forms import GoutDetailForm
    from ..medhistorys.models import MedHistory

User = get_user_model()


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


class PpxAidBase:
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
    medhistory_details = {MedHistoryTypes.CKD: CkdDetailForm}


class PpxAidCreate(PpxAidBase, MedHistoryModelBaseMixin, CreateView, SuccessMessageMixin):
    """
    Create a new PpxAid instance.
    """

    def form_valid(
        self,
        form: PpxAid,
        oto_2_save: list["Model"] | None,
        mh_det_2_save: list[CkdDetailForm, "BaselineCreatinine", "GoutDetailForm"] | None,
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
            _,  # onetoone_forms
            _,  # medallergys_forms
            _,  # medhistorys_forms
            _,  # medhistorydetails_forms
            _,  # lab_formset
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


class PpxAidDetailBase(DetailView):
    class Meta:
        abstract = True

    model = PpxAid
    object: PpxAid  # TODO: why is this necessary?

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        for content in self.contents:
            context.update({content.slug: {content.tag: content}})  # type: ignore
        return context

    @property
    def contents(self):
        return apps.get_model("contents.Content").objects.filter(context=Contexts.PPXAID, tag__isnull=False)


class PpxAidDetail(PpxAidDetailBase):
    """DetailView for PpxAid model."""

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Check if the object has a User and if there is no username in the kwargs,
        # redirect to the username url
        if self.object.user:
            return HttpResponseRedirect(self.object.get_absolute_url())
        else:
            # Check if PpxAid is up to date and update if not update
            if not request.GET.get("updated", None):
                self.object.update_aid(qs=self.object)
            return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Overwritten to avoid calling get_object again, which is instead
        called on dispatch()."""
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_queryset(self) -> "QuerySet[Any]":
        return ppxaid_userless_qs(self.kwargs["pk"])


class PpxAidPatientBase(PpxAidBase):
    class Meta:
        abstract = True

    onetoones = {}
    req_onetoones = ["dateofbirth", "gender"]

    def get_user_queryset(self, username: str) -> "QuerySet[Any]":
        """Used to set the user attribute on the view, with associated related models
        select_related and prefetch_related."""
        return ppxaid_user_qs(username=username)


class PpxAidPseudopatientCreate(
    PermissionRequiredMixin, PpxAidPatientBase, MedHistoryModelBaseMixin, CreateView, SuccessMessageMixin
):
    """View for creating a PpxAid for a patient."""

    permission_required = "ppxaids.can_add_pseudopatient_ppxaid"
    success_message = "%(username)s's PpxAid successfully created."

    def dispatch(self, request, *args, **kwargs):
        """Overwritten to check for a User on the object and redirect to the
        correct PpxAidPseudopatientUpdate url instead."""
        # Will also set self.user
        model = self.get_object()
        if model.objects.filter(user=self.user).exists():
            messages.error(request, f"{self.user} already has a {model.__name__}. Please update it instead.")
            view_str = "ppxaids:pseudopatient-detail"
            return HttpResponseRedirect(reverse(view_str, kwargs={"username": self.user.username}))
        try:
            self.check_user_onetoones(user=self.user)
        except AttributeError as exc:
            messages.error(request, exc)
            return HttpResponseRedirect(reverse("users:pseudopatient-update", kwargs={"username": self.user.username}))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(
        self,
        form,
        oto_2_save: list["Model"] | None,
        oto_2_rem: list["Model"] | None,
        mh_det_2_save: list[CkdDetailForm, "BaselineCreatinine", "GoutDetailForm"] | None,
        mh_det_2_rem: list[CkdDetailForm, "BaselineCreatinine", "GoutDetailForm"] | None,
        ma_2_save: list["MedAllergy"] | None,
        ma_2_rem: list["MedAllergy"] | None,
        mh_2_save: list["MedHistory"] | None,
        mh_2_rem: list["MedHistory"] | None,
        labs_2_save: list["Lab"] | None,
        labs_2_rem: list["Lab"] | None,
    ) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Overwritten to redirect appropriately and update the form instance."""
        form = super().form_valid(
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
        ppxaid = form.save()
        # Add the relationship to the existing user object so that user
        # can be used as the QuerySet for the update method
        self.user.ppxaid = ppxaid
        # Update object / form instance
        ppxaid.update_aid(qs=self.user)
        # Add a querystring to the success_url to trigger the DetailView to NOT re-update the object
        return HttpResponseRedirect(ppxaid.get_absolute_url() + "?updated=True")

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Pseudopatient the view is trying to create
        a PpxAid for."""
        return self.user

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, username=self.user.username)

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            _,  # onetoone_forms
            _,  # medhistorys_forms
            _,  # medhistorydetails_forms
            _,  # medallergys_forms
            _,  # lab_formsets
            ma_2_save,
            ma_2_rem,
            oto_2_rem,
            oto_2_save,
            mh_det_2_save,
            mh_det_2_rem,
            mh_2_save,
            mh_2_rem,
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


class PpxAidPseudopatientDetail(AutoPermissionRequiredMixin, PpxAidDetailBase):
    """Overwritten for different url routing, object fetching, and
    building the content data."""

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        """Overwritten to add the PpxAid's user to the context as 'patient'."""
        context = super().get_context_data(**kwargs)
        context["patient"] = self.user
        return context

    def dispatch(self, request, *args, **kwargs):
        """Overwritten to check for a User on the object and redirect to the
        correct PpxAidPseudopatientCreate url instead. Also checks if the user has
        the correct OneToOne models and redirects to the view to add them if not."""
        try:
            self.object = self.get_object()
        except PpxAid.DoesNotExist as exc:
            messages.error(request, exc.args[0])
            return HttpResponseRedirect(
                reverse("ppxaids:pseudopatient-create", kwargs={"username": kwargs["username"]})
            )
        except (DateOfBirth.DoesNotExist, Gender.DoesNotExist):
            messages.error(request, "Baseline information is needed to use GoutHelper Decision and Treatment Aids.")
            return HttpResponseRedirect(reverse("users:pseudopatient-update", kwargs={"username": self.user.username}))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Updates the objet prior to rendering the view."""
        # Check if PpxAid is up to date and update if not update
        if not request.GET.get("updated", None):
            self.object.update_aid(qs=self.object)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_permission_object(self):
        return self.object

    def assign_ppxaid_attrs_from_user(self, ppxaid: PpxAid, user: "User") -> PpxAid:
        ppxaid.dateofbirth = user.dateofbirth
        if hasattr(user, "gender"):
            ppxaid.gender = user.gender
        ppxaid.medallergys_qs = user.medallergys_qs
        ppxaid.medhistorys_qs = user.medhistorys_qs
        return ppxaid

    def get_queryset(self) -> "QuerySet[Any]":
        return ppxaid_user_qs(self.kwargs["username"])

    def get_object(self, *args, **kwargs) -> PpxAid:
        self.user: User = self.get_queryset().get()  # pylint: disable=W0201
        try:
            ppxaid: PpxAid = self.user.ppxaid
        except PpxAid.DoesNotExist as exc:
            raise PpxAid.DoesNotExist(f"{self.user} does not have a PpxAid. Create one.") from exc
        ppxaid = self.assign_ppxaid_attrs_from_user(ppxaid=ppxaid, user=self.user)
        return ppxaid


class PpxAidPseudopatientUpdate(
    AutoPermissionRequiredMixin, PpxAidPatientBase, MedHistoryModelBaseMixin, UpdateView, SuccessMessageMixin
):
    success_message = "%(username)s's PpxAid successfully created."

    def dispatch(self, request, *args, **kwargs):
        """Overwritten to check if the User has a PpxAid and redirect to the CreateView if not."""
        try:
            self.object = self.get_object()
        except PpxAid.DoesNotExist as exc:
            messages.error(request, exc.args[0])
            return HttpResponseRedirect(
                reverse("ppxaids:pseudopatient-create", kwargs={"username": kwargs["username"]})
            )
        # self.user set by get_object()
        try:
            self.check_user_onetoones(user=self.user)
        except AttributeError as exc:
            messages.error(request, exc)
            return HttpResponseRedirect(reverse("users:pseudopatient-update", kwargs={"username": self.user.username}))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(
        self,
        form,
        oto_2_save: list["Model"] | None,
        oto_2_rem: list["Model"] | None,
        mh_det_2_save: list[CkdDetailForm, "BaselineCreatinine", "GoutDetailForm"] | None,
        mh_det_2_rem: list[CkdDetailForm, "BaselineCreatinine", "GoutDetailForm"] | None,
        ma_2_save: list["MedAllergy"] | None,
        ma_2_rem: list["MedAllergy"] | None,
        mh_2_save: list["MedHistory"] | None,
        mh_2_rem: list["MedHistory"] | None,
        labs_2_save: list["Lab"] | None,
        labs_2_rem: list["Lab"] | None,
    ) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Overwritten to redirect appropriately and update the form instance."""
        form = super().form_valid(
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
        ppxaid = form.save()
        # Add the relationship to the existing user object so that user
        # can be used as the QuerySet for the update method
        self.user.ppxaid = ppxaid
        # Update object / form instance
        ppxaid.update_aid(qs=self.user)
        # Add a querystring to the success_url to trigger the DetailView to NOT re-update the object
        return HttpResponseRedirect(ppxaid.get_absolute_url() + "?updated=True")

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Psuedopatient the view is trying to create
        a PpxAid for."""
        return self.object

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, username=self.user.username)

    def post(self, request, *args, **kwargs):
        """Overwritten to finish the post() method and avoid conflicts with the MRO.
        For PpxAid, no additional processing is needed."""
        (
            errors,
            form,
            _,  # onetoone_forms
            _,  # medhistorys_forms
            _,  # medhistorydetails_forms
            _,  # medallergys_forms
            _,  # lab_formset
            ma_2_save,
            ma_2_rem,
            oto_2_rem,
            oto_2_save,
            mh_det_2_save,
            mh_det_2_rem,
            mh_2_save,
            mh_2_rem,
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


class PpxAidUpdate(PpxAidBase, MedHistoryModelBaseMixin, UpdateView, SuccessMessageMixin):
    """Updates a PpxAid"""

    def form_valid(
        self,
        form,
        oto_2_save: list["Model"] | None,
        oto_2_rem: list["Model"] | None,
        mh_det_2_save: list[CkdDetailForm, "BaselineCreatinine", "GoutDetailForm"] | None,
        mh_det_2_rem: list[CkdDetailForm, "BaselineCreatinine", "GoutDetailForm"] | None,
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

    def get(self, request, *args, **kwargs):
        """Overwritten to check for a User on the object and redirect to the
        correct PpxAidPseudopatientUpdate url instead."""
        self.object = self.get_object()
        if self.object.user:
            return HttpResponseRedirect(
                reverse("ppxaids:pseudopatient-update", kwargs={"username": self.object.user.username})
            )
        return self.render_to_response(self.get_context_data())

    def get_queryset(self):
        return ppxaid_userless_qs(self.kwargs["pk"])

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
