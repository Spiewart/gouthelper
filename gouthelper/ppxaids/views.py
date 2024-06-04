from typing import TYPE_CHECKING, Any  # pylint: disable=e0401, e0015 # type: ignore

from django.apps import apps  # pylint: disable=e0401 # type: ignore
from django.contrib import messages  # pylint: disable=e0401 # type: ignore
from django.contrib.auth import get_user_model  # pylint: disable=e0401 # type: ignore
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
from ..dateofbirths.models import DateOfBirth
from ..genders.models import Gender
from ..ppxs.models import Ppx
from ..users.models import Pseudopatient
from ..utils.helpers import get_str_attrs
from ..utils.views import GoutHelperAidEditMixin
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


class PpxAidBase:
    class Meta:
        abstract = True

    model = PpxAid
    form_class = PpxAidForm
    MEDALLERGY_FORMS = MEDALLERGY_FORMS
    MEDHISTORY_FORMS = MEDHISTORY_FORMS
    MEDHISTORY_DETAIL_FORMS = MEDHISTORY_DETAIL_FORMS
    OTO_FORMS = OTO_FORMS


class PpxAidCreate(PpxAidBase, GoutHelperAidEditMixin, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """
    Create a new PpxAid instance.
    """

    permission_required = "ppxaids.can_add_ppxaid"
    success_message = "PpxAid successfully created."

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
            kwargs.update({"ppx": self.ppx})
            return self.form_valid(**kwargs)

    @cached_property
    def ppx(self) -> Ppx | None:
        ppx_kwarg = self.kwargs.get("ppx", None)
        return Ppx.related_objects.get(pk=ppx_kwarg) if ppx_kwarg else None

    @cached_property
    def related_object(self) -> Ppx:
        return self.ppx


class PpxAidDetailBase(AutoPermissionRequiredMixin, DetailView):
    """DetailView for PpxAids."""

    class Meta:
        abstract = True

    model = PpxAid
    object: PpxAid

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"str_attrs": get_str_attrs(self.object, self.object.user, self.request.user)})
        return context

    def get_permission_object(self):
        return self.object


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
        return PpxAid.related_objects.filter(pk=self.kwargs["pk"])


class PpxAidPatientBase(PpxAidBase):
    class Meta:
        abstract = True

    OTO_FORMS = PATIENT_OTO_FORMS
    REQ_OTOS = PATIENT_REQ_OTOS

    def get_user_queryset(self, username: str) -> "QuerySet[Any]":
        """Used to set the user attribute on the view, with associated related models
        select_related and prefetch_related."""
        return Pseudopatient.objects.ppxaid_qs().filter(username=username)


class PpxAidPseudopatientCreate(
    PpxAidPatientBase, GoutHelperAidEditMixin, PermissionRequiredMixin, CreateView, SuccessMessageMixin
):
    """View for creating a PpxAid for a patient."""

    permission_required = "ppxaids.can_add_ppxaid"
    success_message = "%(username)s's PpxAid successfully created."

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Pseudopatient the view is trying to create
        a PpxAid for."""
        return self.user

    def get_success_message(self, cleaned_data) -> str:
        return self.success_message % dict(cleaned_data, username=self.user.username)

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid()


class PpxAidPseudopatientDetail(PpxAidDetailBase):
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
        return Pseudopatient.objects.ppxaid_qs().filter(username=self.kwargs["username"])

    def get_object(self, *args, **kwargs) -> PpxAid:
        self.user: User = self.get_queryset().get()  # pylint: disable=W0201
        try:
            ppxaid: PpxAid = self.user.ppxaid
        except PpxAid.DoesNotExist as exc:
            raise PpxAid.DoesNotExist(f"{self.user} does not have a PpxAid. Create one.") from exc
        ppxaid = self.assign_ppxaid_attrs_from_user(ppxaid=ppxaid, user=self.user)
        return ppxaid


class PpxAidPseudopatientUpdate(
    PpxAidPatientBase, GoutHelperAidEditMixin, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin
):
    success_message = "%(username)s's PpxAid successfully created."

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
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
            return self.form_valid()


class PpxAidUpdate(PpxAidBase, GoutHelperAidEditMixin, AutoPermissionRequiredMixin, UpdateView, SuccessMessageMixin):
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
