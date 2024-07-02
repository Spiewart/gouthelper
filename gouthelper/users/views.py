from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView, ListView, RedirectView, UpdateView
from rules.contrib.views import AutoPermissionRequiredMixin, PermissionRequiredMixin

from ..flares.models import Flare
from ..medhistorydetails.forms import GoutDetailForm
from ..medhistorys.choices import MedHistoryTypes
from ..utils.views import GoutHelperUserDetailMixin, GoutHelperUserEditMixin, remove_patient_from_session
from .choices import Roles
from .dicts import (
    FLARE_MEDHISTORY_FORMS,
    FLARE_OTO_FORMS,
    FLARE_REQ_OTOS,
    MEDHISTORY_DETAIL_FORMS,
    MEDHISTORY_FORMS,
    OTO_FORMS,
)
from .forms import PseudopatientForm
from .models import Pseudopatient
from .selectors import pseudopatient_profile_qs, pseudopatient_qs

User = get_user_model()


class PseudopatientCreateView(GoutHelperUserEditMixin, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """View to create Pseudopatient Users. If called with a provider kwarg in the url,
    assigns provider field to the creating User.

    Returns:
        [redirect]: [Redirects to the newly created Pseudopatient's Detail page.]
    """

    model = Pseudopatient
    form_class = PseudopatientForm

    MEDHISTORY_FORMS = MEDHISTORY_FORMS
    OTO_FORMS = OTO_FORMS
    MEDHISTORY_DETAIL_FORMS = MEDHISTORY_DETAIL_FORMS

    medhistory_details = {MedHistoryTypes.GOUT: GoutDetailForm}

    def get_permission_required(self):
        """Returns the list of permissions that the user must have in order to access the view."""
        perms = ["users.can_add_user"]
        if self.kwargs.get("username", None):
            perms += ["users.can_add_user_with_provider"]
        return perms

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        self.post_process_menopause()
        if self.errors_bool:
            return super().render_errors()
        else:
            return self.form_valid()


pseudopatient_create_view = PseudopatientCreateView.as_view()


class PseudopatientFlareCreateView(GoutHelperUserEditMixin, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    model = Pseudopatient
    form_class = PseudopatientForm

    MEDHISTORY_FORMS = FLARE_MEDHISTORY_FORMS
    OTO_FORMS = FLARE_OTO_FORMS
    REQ_OTOS = FLARE_REQ_OTOS
    MEDHISTORY_DETAIL_FORMS = MEDHISTORY_DETAIL_FORMS

    # TODO: refactor dispatch to prevent calling on a flare with a FlareAid

    @cached_property
    def flare(self) -> Flare | None:
        flare_kwarg = self.kwargs.get("flare", None)
        return Flare.related_objects.get(pk=flare_kwarg) if flare_kwarg else None  # pylint: disable=W0201

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"flare": self.flare})
        return context

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        if self.flare:
            kwargs.update({"flare": self.flare})
        return kwargs

    def get_permission_object(self):
        if self.flare and self.flare.user:
            raise PermissionError("Trying to create a Pseudopatient for a Flare that already has a user.")
        return None

    def get_permission_required(self):
        """Returns the list of permissions that the user must have in order to access the view."""
        perms = ["users.can_add_user"]
        if self.kwargs.get("username", None):
            perms += ["users.can_add_user_with_provider"]
        return perms

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


pseudopatient_flare_create_view = PseudopatientFlareCreateView.as_view()


class PseudopatientUpdateView(GoutHelperUserEditMixin, PermissionRequiredMixin, UpdateView, SuccessMessageMixin):
    """View to update Pseudopatient Users.

    Returns:
        [redirect]: [Redirects to the updated Pseudopatient's Detail page.]
    """

    model = Pseudopatient
    slug_field = "username"
    slug_url_kwarg = "username"
    form_class = PseudopatientForm
    permission_required = "users.can_edit_pseudopatient"

    MEDHISTORY_FORMS = MEDHISTORY_FORMS
    OTO_FORMS = OTO_FORMS
    MEDHISTORY_DETAIL_FORMS = MEDHISTORY_DETAIL_FORMS

    def get_queryset(self):
        return pseudopatient_profile_qs(self.kwargs.get("username"))

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        self.post_process_menopause()
        if self.errors_bool:
            return super().render_errors()
        else:
            return self.form_valid()

    def get_object(self, queryset=None):
        qs = super().get_object(queryset)
        self.user = qs
        return qs


pseudopatient_update_view = PseudopatientUpdateView.as_view()


class PseudopatientDetailView(AutoPermissionRequiredMixin, GoutHelperUserDetailMixin, DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"
    template_name = "users/pseudopatient_detail.html"

    def get_queryset(self):
        return pseudopatient_qs(self.kwargs.get("username", None))


pseudopatient_detail_view = PseudopatientDetailView.as_view()


class PseudopatientListView(LoginRequiredMixin, PermissionRequiredMixin, GoutHelperUserDetailMixin, ListView):
    """ListView for displaying all of a Provider or Admin's Pseudopatients."""

    model = Pseudopatient
    template_name = "users/pseudopatients.html"
    paginate_by = 5
    permission_required = "users.can_view_provider_list"

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Provider the view is trying to create
        a list of Pseudopatients for."""
        return self.kwargs.get("username", None)

    # Overwrite get_queryset() to return Patient objects filtered by their PseudopatientProfile provider field
    # Fetch only Pseudopatients where the provider is equal to the requesting User (Provider)
    def get_queryset(self):
        return Pseudopatient.objects.filter(pseudopatientprofile__provider=self.request.user)


pseudopatient_list_view = PseudopatientListView.as_view()


class UserDeleteView(
    LoginRequiredMixin, AutoPermissionRequiredMixin, GoutHelperUserDetailMixin, SuccessMessageMixin, DeleteView
):
    model = User
    success_message = _("User successfully deleted")

    def form_valid(self, form):
        remove_patient_from_session(self.request, self.object, delete=True)
        return super().form_valid(form)

    def get_success_message(self, cleaned_data):
        if self.object.role == Roles.PSEUDOPATIENT:
            return _("Pseudopatient successfully deleted")
        else:
            return _("User successfully deleted")

    def get_success_url(self):
        if self.object != self.request.user:
            return reverse("users:pseudopatients", kwargs={"username": self.request.user.username})
        else:
            return reverse("contents:home")

    def get_object(self):
        username = self.kwargs.get("username", None)
        if username:
            return User.objects.filter(role=Roles.PSEUDOPATIENT).get(username=username)
        else:
            return self.request.user


user_delete_view = UserDeleteView.as_view()


class UserDetailView(LoginRequiredMixin, AutoPermissionRequiredMixin, DetailView):
    """Default DetailView for GoutHelper Users, which are Providers by default. If the requested
    User is a Pseudopatient, redirect to the PseudopatientDetailView."""

    model = User
    slug_field = "username"
    slug_url_kwarg = "username"

    def get(self, request, *args, **kwargs):
        """Overwritten to check if the requested User is a Pseudopatient. If so, redirect to the
        PseudopatientDetailView."""
        self.object = self.get_object()
        if self.object.role == Roles.PSEUDOPATIENT:
            return HttpResponseRedirect(
                reverse("users:pseudopatient-detail", kwargs={"username": self.get_object().username})
            )
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, AutoPermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def dispatch(self, request, *args, **kwargs):
        if request.user.role == Roles.PSEUDOPATIENT:
            return HttpResponseRedirect(
                reverse("users:pseudopatient-update", kwargs={"username": request.user.username})
            )
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        assert self.request.user.is_authenticated  # for mypy to know that the user is authenticated
        return self.request.user.get_absolute_url()

    def get_object(self):
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse("users:detail", kwargs={"username": self.request.user.username})


user_redirect_view = UserRedirectView.as_view()
