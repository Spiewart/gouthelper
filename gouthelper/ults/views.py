from typing import TYPE_CHECKING, Any  # pylint: disable=E0013, E0015 # type: ignore

from django.apps import apps  # pylint: disable=E0401 # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # pylint: disable=E0401 # type: ignore
from django.views.generic import CreateView, TemplateView, UpdateView  # pylint: disable=E0401 # type: ignore
from rules.contrib.views import (  # pylint: disable=W0611, E0401  # type: ignore
    AutoPermissionRequiredMixin,
    PermissionRequiredMixin,
)

from ..contents.choices import Contexts
from ..labs.selectors import hyperuricemia_urates_prefetch
from ..users.models import Pseudopatient
from ..utils.views import (
    GoutHelperDetailMixin,
    GoutHelperPseudopatientDetailMixin,
    MedHistoryFormMixin,
    OneToOneFormMixin,
)
from .dicts import MEDHISTORY_DETAIL_FORMS, MEDHISTORY_FORMS, OTO_FORMS, PATIENT_OTO_FORMS, PATIENT_REQ_OTOS
from .forms import UltForm
from .models import Ult

if TYPE_CHECKING:
    from uuid import UUID

    from django.contrib.auth import get_user_model  # type: ignore
    from django.db.models import QuerySet  # type: ignore

    from ..medhistorys.models import MedHistory

    User = get_user_model()


class UltAbout(TemplateView):
    """About page for ULTs."""

    template_name = "ults/about.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"content": self.content})
        return context

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="about", context=Contexts.ULT, tag=None)


class UltEditBase(MedHistoryFormMixin, OneToOneFormMixin):
    class Meta:
        abstract = True

    form_class = UltForm
    model = Ult

    MEDHISTORY_DETAIL_FORMS = MEDHISTORY_DETAIL_FORMS
    MEDHISTORY_FORMS = MEDHISTORY_FORMS
    OTO_FORMS = OTO_FORMS


class UltCreate(UltEditBase, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """View to create a new Ult without a user."""

    permission_required = "ults.can_add_ult"
    success_message = "ULT successfully created."

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid()


class UltDetail(GoutHelperDetailMixin):
    model = Ult
    object: Ult


class UltPatientBase(UltEditBase):
    """Base class for UltCreate/Update views for Ults that have a user."""

    class Meta:
        abstract = True

    OTO_FORMS = PATIENT_OTO_FORMS
    REQ_OTOS = PATIENT_REQ_OTOS

    def get_user_queryset(self, pseudopatient: "UUID") -> "QuerySet[Any]":
        """Used to set the user attribute on the view, with associated related models
        select_related and prefetch_related."""
        return Pseudopatient.objects.ult_qs().filter(pk=pseudopatient)


class UltPseudopatientCreate(UltPatientBase, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """View for creating a Ult for a patient."""

    permission_required = "ults.can_add_ult"
    success_message = "%(user)s's Ult successfully created."

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Psuedopatient the view is trying to create
        a Ult for."""
        return self.user

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, user=self.user)

    def get_HYPERURICEMIA_initial_value(self, mh_object: "MedHistory") -> bool:
        # Called by get_mh_initial method in GoutHelperAidMixin
        return True if mh_object or self.user.hyperuricemia_urates else None

    def get_user_queryset(self, pseudopatient: "UUID") -> "QuerySet[Any]":
        qs = super().get_user_queryset(pseudopatient=pseudopatient)
        return qs.prefetch_related(hyperuricemia_urates_prefetch())

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid()


class UltPseudopatientDetail(GoutHelperPseudopatientDetailMixin):
    model = Ult
    object: Ult


class UltPseudopatientUpdate(UltPatientBase, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin):
    """UpdateView for Ults with a User."""

    success_message = "%(user)s's Ult successfully updated."

    def get_permission_object(self):
        return self.object

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, user=self.user)

    def post(self, request, *args, **kwargs):
        """Overwritten to finish the post() method and avoid conflicts with the MRO.
        For Ult, no additional processing is needed."""
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid()


class UltUpdate(UltEditBase, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin):
    """Updates a Ult"""

    success_message = "ULT updated successfully."

    def get_queryset(self):
        return Ult.related_objects.filter(pk=self.kwargs["pk"])

    def get_permission_object(self):
        return self.object

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid()
