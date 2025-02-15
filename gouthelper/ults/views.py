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
from ..utils.views import GoutHelperDetailMixin, MedHistoryFormMixin, OneToOneFormMixin
from .dicts import MEDHISTORY_DETAIL_FORMS, MEDHISTORY_FORMS, OTO_FORMS
from .models import Ult

if TYPE_CHECKING:
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

    # form_class = UltForm
    model = Ult

    MEDHISTORY_DETAIL_FORMS = MEDHISTORY_DETAIL_FORMS
    MEDHISTORY_FORMS = MEDHISTORY_FORMS
    OTO_FORMS = OTO_FORMS


class UltCreate(UltEditBase, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """View to create a new Ult without a user."""

    permission_required = "ults.can_add_ult"
    success_message = "%(patient)s's Ult successfully created."

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Patient the view is trying to create
        a Ult for."""
        return self.patient

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, patient=self.patient)

    def get_HYPERURICEMIA_initial_value(self, mh_object: "MedHistory") -> bool:
        # Called by get_mh_initial method in GoutHelperAidMixin
        return True if mh_object or self.patient.hyperuricemia_urates else None

    def get_queryset(self) -> "QuerySet":
        qs = super().get_queryset()
        return qs.prefetch_related(hyperuricemia_urates_prefetch())

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid()


class UltDetail(GoutHelperDetailMixin, TemplateView):
    """Detail view for a Ult."""

    model = Ult


class UltUpdate(UltEditBase, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin):
    """Updates a Ult"""

    success_message = "%(patient)s's Ult successfully updated."

    def get_permission_object(self):
        return self.object

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, patient=self.patient)

    def get_queryset(self):
        return Ult.related_objects.filter(pk=self.kwargs["pk"])

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid()
