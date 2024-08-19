from typing import TYPE_CHECKING, Any

from django.apps import apps  # pylint: disable=E0401  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # pylint: disable=E0401  # type: ignore
from django.utils.functional import cached_property  # pylint: disable=E0401  # type: ignore
from django.views.generic import CreateView, TemplateView, UpdateView  # pylint: disable=E0401  # type: ignore
from rules.contrib.views import (  # pylint: disable=e0401, E0611  # type: ignore
    AutoPermissionRequiredMixin,
    PermissionRequiredMixin,
)

from ..contents.choices import Contexts
from ..ults.models import Ult
from ..users.models import Pseudopatient
from ..utils.views import (
    GoutHelperDetailMixin,
    GoutHelperPseudopatientDetailMixin,
    MedAllergyFormMixin,
    MedHistoryFormMixin,
    OneToOneFormMixin,
    PatientSessionMixin,
)
from .dicts import (
    MEDALLERGY_FORMS,
    MEDHISTORY_DETAIL_FORMS,
    MEDHISTORY_FORMS,
    OTO_FORMS,
    PATIENT_OTO_FORMS,
    PATIENT_REQ_OTOS,
)
from .forms import UltAidForm
from .models import UltAid

if TYPE_CHECKING:
    from uuid import UUID  # type: ignore

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


class UltAidEditBase(MedAllergyFormMixin, MedHistoryFormMixin, OneToOneFormMixin, PatientSessionMixin):
    class Meta:
        abstract = True

    form_class = UltAidForm
    model = UltAid

    MEDALLERGY_FORMS = MEDALLERGY_FORMS
    MEDHISTORY_FORMS = MEDHISTORY_FORMS
    MEDHISTORY_DETAIL_FORMS = MEDHISTORY_DETAIL_FORMS
    OTO_FORMS = OTO_FORMS


class UltAidCreate(UltAidEditBase, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """Create a new UltAid"""

    permission_required = "ultaids.can_add_ultaid"
    success_message = "UltAid created successfully!"

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        if self.ult:
            kwargs.update({"ult": self.ult})
        return kwargs

    def get_permission_object(self):
        if self.ult and self.ult.user:
            raise PermissionError("Trying to create a UltAid for a Ult with a user with an anonymous view.")
        return None

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            kwargs.update({"ult": self.ult})
            return self.form_valid(**kwargs)

    @cached_property
    def ult(self) -> Ult | None:
        ult_kwarg = self.kwargs.get("ult", None)
        return Ult.related_objects.get(pk=ult_kwarg) if ult_kwarg else None

    @cached_property
    def related_object(self) -> Ult:
        return self.ult


class UltAidDetail(GoutHelperDetailMixin):
    model = UltAid
    object: UltAid


class UltAidPatientBase(UltAidEditBase):
    """Base class for UltAidCreate/Update views for UltAids that have a user."""

    class Meta:
        abstract = True

    OTO_FORMS = PATIENT_OTO_FORMS
    REQ_OTOS = PATIENT_REQ_OTOS

    def get_user_queryset(self, pseudopatient: "UUID") -> "QuerySet[Any]":
        """Used to set the user attribute on the view, with associated related models
        select_related and prefetch_related."""
        return Pseudopatient.objects.ultaid_qs().filter(pk=pseudopatient)


class UltAidPseudopatientCreate(UltAidPatientBase, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """View for creating a UltAid for a patient."""

    permission_required = "ultaids.can_add_ultaid"
    success_message = "%(user)s's UltAid successfully created."

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Psuedopatient the view is trying to create
        a UltAid for."""
        return self.user

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, user=self.user)

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid()


class UltAidPseudopatientDetail(GoutHelperPseudopatientDetailMixin):
    model = UltAid
    object: UltAid


class UltAidPseudopatientUpdate(UltAidPatientBase, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin):
    """UpdateView for UltAids with a User."""

    success_message = "%(user)s's UltAid successfully updated."

    def get_permission_object(self):
        return self.object

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, user=self.user)

    def post(self, request, *args, **kwargs):
        """Overwritten to finish the post() method and avoid conflicts with the MRO.
        For UltAid, no additional processing is needed."""
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid()


class UltAidUpdate(UltAidEditBase, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin):
    """Updates a UltAid"""

    success_message = "UltAid updated successfully!"

    def get_queryset(self):
        return UltAid.related_objects.filter(pk=self.kwargs["pk"])

    def get_permission_object(self):
        return self.object

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid()
