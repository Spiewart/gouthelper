from typing import Any

from django.apps import apps  # pylint: disable=E0401  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # pylint: disable=E0401  # type: ignore
from django.views.generic import CreateView, TemplateView, UpdateView  # pylint: disable=E0401  # type: ignore
from rules.contrib.views import (  # pylint: disable=e0401, E0611  # type: ignore
    AutoPermissionRequiredMixin,
    PermissionRequiredMixin,
)

from ..contents.choices import Contexts
from ..utils.views import (
    GoutHelperDetailMixin,
    MedAllergyFormMixin,
    MedHistoryFormMixin,
    OneToOneFormMixin,
    PatientSessionMixin,
)
from .dicts import MEDALLERGY_FORMS, MEDHISTORY_DETAIL_FORMS, MEDHISTORY_FORMS, OTO_FORMS
from .forms import UltAidForm
from .models import UltAid


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
    success_message = "%(patient)s's UltAid successfully created."

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Psuedopatient the view is trying to create
        a UltAid for."""
        return self.patient

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, patient=self.patient)

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            kwargs.update({"ult": self.ult})
            return self.form_valid(**kwargs)


class UltAidDetail(GoutHelperDetailMixin):
    model = UltAid
    object: UltAid


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
