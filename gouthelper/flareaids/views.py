from typing import TYPE_CHECKING, Any

from django.apps import apps  # pylint: disable=E0401  # type: ignore
from django.contrib.auth import get_user_model  # pylint: disable=E0401  # type: ignore
from django.contrib.messages.views import SuccessMessageMixin  # pylint: disable=E0401  # type: ignore
from django.urls import reverse  # pylint: disable=E0401  # type: ignore
from django.utils.functional import cached_property  # pylint: disable=E0401  # type: ignore
from django.views.generic import (  # pylint: disable=E0401  # type: ignore
    CreateView,
    DetailView,
    TemplateView,
    UpdateView,
)
from rules.contrib.views import (  # pylint: disable=W0611, E0401  # type: ignore
    AutoPermissionRequiredMixin,
    PermissionRequiredMixin,
)

from ..contents.choices import Contexts
from ..flares.models import Flare
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
from .forms import FlareAidForm
from .models import FlareAid
from .selectors import flareaid_user_relations

if TYPE_CHECKING:
    from uuid import UUID

    # type: ignore
    from django.db.models import QuerySet  # type: ignore

    User = get_user_model()


class FlareAidAbout(TemplateView):
    """About page for FlareAid"""

    template_name = "flareaids/about.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"content": self.content})
        return context

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="about", context=Contexts.FLAREAID, tag=None)


class FlareAidEditBase(MedAllergyFormMixin, MedHistoryFormMixin, OneToOneFormMixin):
    class Meta:
        abstract = True

    form_class = FlareAidForm
    model = FlareAid
    sucess_message = "FlareAid created successfully."

    MEDALLERGY_FORMS = MEDALLERGY_FORMS
    MEDHISTORY_FORMS = MEDHISTORY_FORMS
    MEDHISTORY_DETAIL_FORMS = MEDHISTORY_DETAIL_FORMS
    OTO_FORMS = OTO_FORMS


class FlareAidCreate(FlareAidEditBase, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """View to create a new FlareAid without a user."""

    permission_required = "flareaids.can_add_flareaid"

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        if self.flare:
            kwargs.update({"flare": self.flare})
        return kwargs

    @cached_property
    def flare(self) -> Flare | None:
        flare_kwarg = self.kwargs.get("flare", None)
        return Flare.related_objects.get(pk=flare_kwarg) if flare_kwarg else None  # pylint: disable=W0201

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"flare": self.flare})
        return context

    def get_permission_object(self):
        if self.flare and self.flare.user:
            raise PermissionError("Trying to create a FlareAid for a Flare with a user with an anonymous view.")
        return None

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            kwargs.update({"flare": self.flare})
            return self.form_valid(**kwargs)

    @cached_property
    def related_object(self) -> Flare:
        return self.flare


class FlareAidDetailBase(AutoPermissionRequiredMixin, DetailView):
    """DetailView for FlareAids."""

    class Meta:
        abstract = True

    model = FlareAid
    object: FlareAid

    def get_permission_object(self):
        return self.object


class FlareAidDetail(GoutHelperDetailMixin):
    model = FlareAid
    object: FlareAid


class FlareAidPatientEditBase(FlareAidEditBase):
    flare: Flare | None
    kwargs: dict[str, Any]

    class Meta:
        abstract = True

    OTO_FORMS = PATIENT_OTO_FORMS
    REQ_OTOS = PATIENT_REQ_OTOS

    def form_valid_end(self, **kwargs) -> None:
        if self.flare:
            setattr(self.user, "flare", self.flare)
        super().form_valid_end(**kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"flare": self.flare})
        return context

    def get_success_url(self):
        if self.flare and not self.request.POST.get("next", None):
            return (
                reverse(
                    "flareaids:pseudopatient-flare-detail",
                    kwargs={
                        "pseudopatient": self.user.id,
                        "flare": self.flare.id,
                    },
                )
                + "?updated=True"
            )
        else:
            return super().get_success_url()

    def get_user_queryset(self, pseudopatient: "UUID") -> "QuerySet[Any]":
        """Used to set the user attribute on the view, with associated related models
        select_related and prefetch_related."""
        return Pseudopatient.objects.flareaid_qs(self.kwargs.get("flare", None)).filter(pk=pseudopatient)


class FlareAidPseudopatientCreate(FlareAidPatientEditBase, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """View for creating a FlareAid for a patient."""

    permission_required = "flareaids.can_add_flareaid"
    success_message = "%(user)s's FlareAid successfully created."

    @cached_property
    def flare(self) -> Flare | None:
        return self.user.flare_qs[0] if hasattr(self.user, "flare_qs") and self.user.flare_qs else None

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


class FlareAidPseudopatientDetail(GoutHelperPseudopatientDetailMixin):
    model = FlareAid
    object: FlareAid

    def get_queryset(self, **kwargs) -> "QuerySet[Any]":
        return flareaid_user_relations(
            qs=Pseudopatient.objects.filter(pk=self.kwargs["pseudopatient"]), flare_id=self.kwargs.get("flare", None)
        )


class FlareAidPseudopatientUpdate(
    FlareAidPatientEditBase, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin
):
    success_message = "%(user)s's FlareAid successfully updated."

    @cached_property
    def flare(self) -> Flare | None:
        return self.object.related_flare

    def get_permission_object(self):
        return self.object

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, user=self.user)

    def post(self, request, *args, **kwargs):
        """Overwritten to finish the post() method and avoid conflicts with the MRO.
        For FlareAid, no additional processing is needed."""
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid()


class FlareAidUpdate(FlareAidEditBase, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin):
    """Updates a FlareAid"""

    success_message = "FlareAid successfully updated."

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        if self.flare:
            kwargs.update({"flare": self.flare})
        return kwargs

    @cached_property
    def flare(self) -> Flare | None:
        return getattr(self.object, "flare", None)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add ultaid to context if it exists."""
        context = super().get_context_data(**kwargs)
        context.update({"flare": self.flare})
        return context

    def get_queryset(self):
        return FlareAid.related_objects.filter(pk=self.kwargs["pk"])

    def get_permission_object(self):
        return self.object

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid()

    @cached_property
    def related_object(self) -> Flare:
        return self.flare
