from typing import TYPE_CHECKING, Any, Literal  # pylint: disable=e0401, e0015 # type: ignore

from django.apps import apps  # pylint: disable=e0401 # type: ignore
from django.contrib import messages  # pylint: disable=e0401 # pylint: disable=e0401 # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # pylint: disable=e0401 # type: ignore
from django.http import HttpResponseRedirect  # pylint: disable=e0401 # type: ignore
from django.urls import reverse  # pylint: disable=e0401 # type: ignore
from django.utils.functional import cached_property  # pylint: disable=e0401 # type: ignore
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
from ..labs.forms import LabFormHelper, PpxUrateFormSet
from ..labs.helpers import labs_urates_annotate_order_by_dates
from ..labs.models import Urate
from ..labs.selectors import dated_urates
from ..medhistorydetails.forms import GoutDetailPpxForm
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.forms import GoutForm
from ..medhistorys.models import Gout
from ..utils.views import MedHistoryModelBaseMixin
from .forms import PpxForm
from .models import Ppx
from .selectors import ppx_user_qs, ppx_userless_qs

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # pylint: disable=e0401 # type: ignore
    from django.db.models import QuerySet  # pylint: disable=e0401 # type: ignore

    User = get_user_model()


class PpxAbout(TemplateView):
    """About page for Ppx decision aid."""

    template_name = "ppxs/about.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"content": self.content})
        return context

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="about", context=Contexts.PPX, tag=None)


class PpxBase:
    class Meta:
        abstract = True

    model = Ppx
    form_class = PpxForm

    medhistorys = {
        MedHistoryTypes.GOUT: {"form": GoutForm, "model": Gout},
    }
    medhistory_details = {MedHistoryTypes.GOUT: GoutDetailPpxForm}
    labs: dict[Literal["urate"], tuple[PpxUrateFormSet, LabFormHelper]] = {"urate": (PpxUrateFormSet, LabFormHelper)}


class PpxCreate(PpxBase, MedHistoryModelBaseMixin, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """
    Create a new Ppx instance.
    """

    permission_required = "ppxs.can_add_ppx"
    success_message = "Ppx successfully created."

    def get_permission_object(self):
        return None

    @cached_property
    def urate_formset_qs(self):
        return dated_urates(Urate.objects.none())

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
            _,  # ma_2_save,
            _,  # ma_2_rem,
            labs_2_save,
            labs_2_rem,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        else:
            labs_urates_annotate_order_by_dates(form.instance.urates_qs)
            return self.form_valid(
                form=form,
                oto_2_save=None,
                oto_2_rem=None,
                mh_2_save=mh_2_save,
                mh_2_rem=mh_2_rem,
                mh_det_2_save=mh_det_2_save,
                mh_det_2_rem=mh_det_2_rem,
                ma_2_save=None,
                ma_2_rem=None,
                labs_2_save=labs_2_save,
                labs_2_rem=labs_2_rem,
            )


class PpxDetailBase(AutoPermissionRequiredMixin, DetailView):
    class Meta:
        abstract = True

    model = Ppx
    object: Ppx

    @property
    def contents(self):
        return apps.get_model("contents.Content").objects.filter(context=Contexts.PPX)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        for content in self.contents:
            context.update({content.slug: {content.tag: content}})  # type: ignore
        return context

    def get_permission_object(self):
        return self.object


class PpxDetail(PpxDetailBase):
    """DetailView for Ppx model."""

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Redirect to correct view if the Ppx has a user
        if self.object.user:
            return HttpResponseRedirect(self.object.get_absolute_url())
        else:
            # Check if Ppx is up to date and update if not update
            if not request.GET.get("updated", None):
                self.object.update_aid(qs=self.object)
            return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Overwritten to avoid calling get_object again, which is instead
        called on dispatch()."""
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_queryset(self) -> "QuerySet[Any]":
        return ppx_userless_qs(self.kwargs["pk"])


class PpxPatientBase(PpxBase):
    class Meta:
        abstract = True

    labs = {"urate": (PpxUrateFormSet, LabFormHelper)}

    def get_user_queryset(self, username: str) -> "QuerySet[Any]":
        """Used to set the user attribute on the view, with associated related models
        select_related and prefetch_related."""
        return ppx_user_qs(username=username)

    @cached_property
    def urate_formset_qs(self):
        return dated_urates(Urate.objects.filter(user=self.user))


class PpxPseudopatientCreate(
    PpxPatientBase, MedHistoryModelBaseMixin, PermissionRequiredMixin, CreateView, SuccessMessageMixin
):
    """View for creating a Ppx for a patient."""

    permission_required = "ppxs.can_add_ppx"
    success_message = "%(username)s's Ppx successfully created."

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Pseudopatient the view is trying to create
        a Ppx for."""
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
            _,  # ma_2_save,
            _,  # ma_2_rem,
            labs_2_save,
            labs_2_rem,
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
                ma_2_save=None,
                ma_2_rem=None,
                labs_2_save=labs_2_save,
                labs_2_rem=labs_2_rem,
            )


class PpxPseudopatientDetail(PpxDetailBase):
    """Overwritten for different url routing, object fetching, and
    building the content data."""

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        """Overwritten to add the Ppx's user to the context as 'patient'."""
        context = super().get_context_data(**kwargs)
        context["patient"] = self.user
        return context

    def dispatch(self, request, *args, **kwargs):
        """Overwritten to check for a User on the object and redirect to the
        correct PpxPseudopatientCreate url instead."""
        try:
            self.object = self.get_object()
        except Ppx.DoesNotExist as exc:
            messages.error(request, exc.args[0])
            return HttpResponseRedirect(reverse("ppxs:pseudopatient-create", kwargs={"username": kwargs["username"]}))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Updates the object prior to rendering the view."""
        # Check if Ppx is up to date and update if not update
        if not request.GET.get("updated", None):
            self.object.update_aid(qs=self.object)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_permission_object(self):
        return self.object

    def assign_ppx_attrs_from_user(self, ppx: Ppx, user: "User") -> Ppx:
        ppx.medhistorys_qs = user.medhistorys_qs
        ppx.urates_qs = user.urates_qs
        return ppx

    def get_queryset(self) -> "QuerySet[Any]":
        return ppx_user_qs(self.kwargs["username"])

    def get_object(self, *args, **kwargs) -> Ppx:
        self.user: User = self.get_queryset().get()  # pylint: disable=W0201
        try:
            ppx: Ppx = self.user.ppx
        except Ppx.DoesNotExist as exc:
            raise Ppx.DoesNotExist(f"{self.user} does not have a Ppx. Create one.") from exc
        ppx = self.assign_ppx_attrs_from_user(ppx=ppx, user=self.user)
        return ppx


class PpxPseudopatientUpdate(
    PpxPatientBase, MedHistoryModelBaseMixin, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin
):
    success_message = "%(username)s's Ppx successfully created."

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Psuedopatient the view is trying to create
        a Ppx for."""
        return self.object

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, username=self.user.username)

    def post(self, request, *args, **kwargs):
        """Overwritten to finish the post() method and avoid conflicts with the MRO.
        For Ppx, no additional processing is needed."""
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
            _,  # ma_2_save,
            _,  # ma_2_rem,
            labs_2_save,
            labs_2_rem,
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
                ma_2_save=None,
                ma_2_rem=None,
                labs_2_save=labs_2_save,
                labs_2_rem=labs_2_rem,
            )


class PpxUpdate(PpxBase, MedHistoryModelBaseMixin, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin):
    """Updates a Ppx"""

    labs = {"urate": (PpxUrateFormSet, LabFormHelper, dated_urates(Urate.objects.all()))}

    @cached_property
    def urate_formset_qs(self):
        return dated_urates(Urate.objects.filter(ppx=self.object))

    def get_permission_object(self):
        return self.object

    def get_queryset(self):
        return ppx_userless_qs(self.kwargs["pk"])

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
            _,  # ma_2_save,
            _,  # ma_2_rem,
            labs_2_save,
            labs_2_rem,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        labs_urates_annotate_order_by_dates(form.instance.urates_qs)
        return self.form_valid(
            form=form,
            oto_2_rem=None,
            oto_2_save=None,
            mh_2_save=mh_2_save,
            mh_2_rem=mh_2_rem,
            mh_det_2_save=mh_det_2_save,
            mh_det_2_rem=mh_det_2_rem,
            ma_2_save=None,
            ma_2_rem=None,
            labs_2_save=labs_2_save,
            labs_2_rem=labs_2_rem,
        )
