from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView, ListView, RedirectView, UpdateView
from rules.contrib.views import AutoPermissionRequiredMixin, PermissionRequiredMixin

from ..medhistorydetails.forms import GoutDetailForm
from ..medhistorys.choices import MedHistoryTypes
from ..utils.views import GoutHelperUserDetailMixin, GoutHelperUserEditMixin
from .choices import Roles
from .dicts import MEDHISTORY_DETAIL_FORMS, MEDHISTORY_FORMS, OTO_FORMS
from .forms import PatientForm
from .models import Patient
from .selectors import patient_profile_qs, patient_profile_update_qs

User = get_user_model()


class PatientCreateView(GoutHelperUserEditMixin, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
    """View to create Patient Users. If called with a provider kwarg in the url,
    assigns provider field to the creating User.

    Returns:
        [redirect]: [Redirects to the newly created Patient's Detail page.]
    """

    model = Patient
    form_class = PatientForm

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


patient_create_view = PatientCreateView.as_view()


class PatientUpdateView(GoutHelperUserEditMixin, PermissionRequiredMixin, UpdateView, SuccessMessageMixin):
    """View to update Patient Users.

    Returns:
        [redirect]: [Redirects to the updated Patient's Detail page.]
    """

    model = Patient
    pk_url_kwarg = "patient"
    form_class = PatientForm
    permission_required = "users.can_edit_patient"

    MEDHISTORY_FORMS = MEDHISTORY_FORMS
    OTO_FORMS = OTO_FORMS
    MEDHISTORY_DETAIL_FORMS = MEDHISTORY_DETAIL_FORMS

    def get_queryset(self):
        return patient_profile_update_qs(self.kwargs.get("patient"))

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


patient_update_view = PatientUpdateView.as_view()


class PatientDetailView(AutoPermissionRequiredMixin, GoutHelperUserDetailMixin, DetailView):
    model = User
    pk_url_kwarg = "patient"
    template_name = "users/patient_detail.html"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return patient_profile_qs(self.kwargs.get("patient", None))

    def get(self, request, *args, **kwargs):
        self.update_onetoones()
        self.update_most_recent_flare()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def update_onetoones(self):
        for onetoone in Patient.list_of_related_aid_models():
            related_onetoone = getattr(self.object, onetoone, None)
            if related_onetoone:
                related_onetoone.update_aid(qs=self.object)

    def update_most_recent_flare(self):
        most_recent_flare_qs = getattr(self.object, "most_recent_flare", None)
        most_recent_flare = most_recent_flare_qs[0] if most_recent_flare_qs else None
        if most_recent_flare and not most_recent_flare.date_ended:
            most_recent_flare.update_aid(qs=self.object)

    def get_permission_object(self) -> Patient:
        return self.object

    def update_session_patient(self) -> None:
        self.add_patient_to_session(self.object)


patient_detail_view = PatientDetailView.as_view()


class PatientListView(LoginRequiredMixin, PermissionRequiredMixin, GoutHelperUserDetailMixin, ListView):
    """ListView for displaying all of a Provider or Admin's Patients."""

    model = Patient
    template_name = "users/patients.html"
    paginate_by = 5
    permission_required = "users.can_view_provider_list"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Provider the view is trying to create
        a list of Patients for."""
        return self.kwargs.get("username", None)

    # Overwrite get_queryset() to return Patient objects filtered by their PatientProfile provider field
    # Fetch only Patients where the provider is equal to the requesting User (Provider)
    def get_queryset(self):
        return (
            Patient.objects.select_related("patientprofile__provider")
            .filter(patientprofile__provider=self.request.user)
            .order_by("-modified")
        )


patient_list_view = PatientListView.as_view()


class UserDeleteView(LoginRequiredMixin, AutoPermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    model = User

    def get_success_message(self, cleaned_data):
        return _("Account successfully deleted")

    def get_success_url(self):
        return reverse("contents:home")

    def get_object(self):
        return self.request.user


user_delete_view = UserDeleteView.as_view()


class PatientDeleteView(UserDeleteView, GoutHelperUserDetailMixin):
    model = Patient

    def form_valid(self, form):
        self.remove_patient_from_session(self.object, delete=True)
        return super().form_valid(form)

    def get_object(self):
        return Patient.objects.get(pk=self.kwargs.get("patient", None))

    def get_success_message(self, cleaned_data):
        return _("GoutPatient successfully deleted")

    def get_success_url(self):
        return reverse("users:patients", kwargs={"username": self.request.user.username})


patient_delete_view = PatientDeleteView.as_view()


class UserDetailView(LoginRequiredMixin, AutoPermissionRequiredMixin, DetailView):
    """Default DetailView for GoutHelper Users, which are Providers by default. If the requested
    User is a Patient, redirect to the PatientDetailView."""

    model = User
    slug_field = "username"
    slug_url_kwarg = "username"

    def get(self, request, *args, **kwargs):
        """Overwritten to check if the requested User is a Patient. If so, redirect to the
        PatientDetailView."""
        self.object = self.get_object()
        if self.object.role == Roles.PSEUDOPATIENT:
            return HttpResponseRedirect(reverse("users:patient-detail", kwargs={"patient": self.get_object().pk}))
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, AutoPermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def dispatch(self, request, *args, **kwargs):
        if request.user.role == Roles.PSEUDOPATIENT:
            return HttpResponseRedirect(reverse("users:patient-update", kwargs={"username": request.user.username}))
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
        if self.request.user.role == Roles.PROVIDER:
            return reverse("users:patients", kwargs={"username": self.request.user.username})
        else:
            return reverse("users:detail", kwargs={"username": self.request.user.username})


user_redirect_view = UserRedirectView.as_view()
