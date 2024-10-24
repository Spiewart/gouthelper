from typing import TYPE_CHECKING, Any  # pylint: disable=e0401, e0015 # type: ignore

from django.apps import apps  # pylint: disable=e0401 # type: ignore
from django.contrib.auth import get_user_model  # pylint: disable=e0401 # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # pylint: disable=e0401 # type: ignore
from django.utils.functional import cached_property  # pylint: disable=e0401 # type: ignore
from django.views.generic import CreateView, TemplateView, UpdateView  # pylint: disable=e0401 # type: ignore
from rules.contrib.views import (  # pylint: disable=e0401 # type: ignore
    AutoPermissionRequiredMixin,
    PermissionRequiredMixin,
)

from ..contents.choices import Contexts
from ..ppxs.models import Ppx
from ..users.models import Pseudopatient
from ..utils.views import (
    GoutHelperDetailMixin,
    GoutHelperPseudopatientDetailMixin,
    MedAllergyFormMixin,
    MedHistoryFormMixin,
    OneToOneFormMixin,
)
from .dicts import (
    MEDALLERGY_FORMS,
    MEDHISTORY_DETAIL_FORMS,
    MEDHISTORY_FORMS,
    OTO_FORMS,
    PATIENT_OTO_FORMS,
    PATIENT_REQ_OTOS,
)
from .forms import PpxAidForm
from .models import PpxAid

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore

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


class PpxAidEditBase(MedAllergyFormMixin, MedHistoryFormMixin, OneToOneFormMixin):
    class Meta:
        abstract = True

    form_class = PpxAidForm
    model = PpxAid
    success_message = "PpxAid successfully created."

    MEDALLERGY_FORMS = MEDALLERGY_FORMS
    MEDHISTORY_FORMS = MEDHISTORY_FORMS
    MEDHISTORY_DETAIL_FORMS = MEDHISTORY_DETAIL_FORMS
    OTO_FORMS = OTO_FORMS


class PpxAidCreate(PpxAidEditBase, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """
    Create a new PpxAid instance.
    """

    permission_required = "ppxaids.can_add_ppxaid"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"ppx": self.ppx})
        return context

    def get_permission_object(self):
        if self.ppx and self.ppx.user:
            raise PermissionError("Trying to create a PpxAid for a Ppx with a user with an anonymous view.")
        return None

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid(**kwargs)

    @cached_property
    def ppx(self) -> Ppx | None:
        ppx_kwarg = self.kwargs.pop("ppx", None)
        return Ppx.related_objects.get(pk=ppx_kwarg) if ppx_kwarg else None

    @cached_property
    def related_object(self) -> Ppx:
        return self.ppx


class PpxAidDetail(GoutHelperDetailMixin):
    model = PpxAid
    object: PpxAid


class PpxAidPatientBase(PpxAidEditBase):
    class Meta:
        abstract = True

    OTO_FORMS = PATIENT_OTO_FORMS
    REQ_OTOS = PATIENT_REQ_OTOS

    def get_user_queryset(self, pseudopatient: "UUID") -> "QuerySet[Any]":
        """Used to set the user attribute on the view, with associated related models
        select_related and prefetch_related."""
        return Pseudopatient.objects.ppxaid_qs().filter(pk=pseudopatient)


class PpxAidPseudopatientCreate(PpxAidPatientBase, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """View for creating a PpxAid for a patient."""

    permission_required = "ppxaids.can_add_ppxaid"
    success_message = "%(user)s's PpxAid successfully created."

    def get_permission_object(self):
        return self.user

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, user=self.user)

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid()


class PpxAidPseudopatientDetail(GoutHelperPseudopatientDetailMixin):
    model = PpxAid
    object: PpxAid


class PpxAidPseudopatientUpdate(PpxAidPatientBase, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin):
    success_message = "%(user)s's PpxAid successfully updated."

    def get_permission_object(self):
        return self.object

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, user=self.user)

    def post(self, request, *args, **kwargs):
        """Overwritten to finish the post() method and avoid conflicts with the MRO.
        For PpxAid, no additional processing is needed."""
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid()


class PpxAidUpdate(PpxAidEditBase, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin):
    """Updates a PpxAid"""

    success_message = "PpxAid successfully updated."

    def get_queryset(self):
        return PpxAid.related_objects.filter(pk=self.kwargs["pk"])

    def get_permission_object(self):
        return self.object

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid()
