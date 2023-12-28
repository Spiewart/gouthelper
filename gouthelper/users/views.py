import uuid
from typing import TYPE_CHECKING, Union

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DeleteView, DetailView, ListView, RedirectView, UpdateView
from rules.contrib.views import AutoPermissionRequiredMixin, PermissionRequiredMixin

from ..dateofbirths.forms import DateOfBirthForm
from ..dateofbirths.models import DateOfBirth
from ..ethnicitys.forms import EthnicityForm
from ..ethnicitys.models import Ethnicity
from ..genders.forms import GenderForm
from ..genders.models import Gender
from ..medhistorydetails.forms import GoutDetailForm
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.forms import GoutForm
from ..medhistorys.models import Gout
from ..profiles.models import PseudopatientProfile
from ..utils.views import PatientModelCreateView
from .choices import Roles
from .forms import PseudopatientForm
from .models import Pseudopatient

User = get_user_model()

if TYPE_CHECKING:
    from django.db.models import Model  # type: ignore
    from django.http import HttpResponse  # type: ignore

    from ..labs.models import BaselineCreatinine, Lab
    from ..medallergys.models import MedAllergy
    from ..medhistorydetails.forms import CkdDetailForm
    from ..medhistorys.models import MedHistory


class PseudopatientCreateView(PermissionRequiredMixin, PatientModelCreateView, SuccessMessageMixin):
    """View to create Pseudopatient Users. If called with a provider kwarg in the url,
    assigns provider field to the creating User.

    Returns:
        [redirect]: [Redirects to the newly created Pseudopatient's Detail page.]
    """

    model = Pseudopatient
    form_class = PseudopatientForm

    onetoones = {
        "dateofbirth": {"form": DateOfBirthForm, "model": DateOfBirth},
        "ethnicity": {"form": EthnicityForm, "model": Ethnicity},
        "gender": {"form": GenderForm, "model": Gender},
    }
    medhistorys = {
        MedHistoryTypes.GOUT: {
            "form": GoutForm,
            "model": Gout,
        },
    }
    medhistory_details = {MedHistoryTypes.GOUT: GoutDetailForm}

    def form_valid(
        self,
        form,
        onetoones_to_save: list["Model"],
        medhistorydetails_to_save: list["CkdDetailForm", "BaselineCreatinine", GoutDetailForm],
        medallergys_to_save: list["MedAllergy"],
        medhistorys_to_save: list["MedHistory"],
        labs_to_save: list["Lab"],
        **kwargs,
    ) -> Union["HttpResponseRedirect", "HttpResponse"]:
        """Overwritten to redirect appropriately."""
        # Set the username attr on the form instance
        form.instance.username = uuid.uuid4().hex[:30]
        # Pop the username kwarg from the url
        provider = kwargs.pop("username", None)
        # Object will be returned by the super().form_valid() call
        self.object = super().form_valid(
            form,
            onetoones_to_save=onetoones_to_save,
            medhistorydetails_to_save=medhistorydetails_to_save,
            medallergys_to_save=medallergys_to_save,
            medhistorys_to_save=medhistorys_to_save,
            labs_to_save=labs_to_save,
            **kwargs,
        )
        # Create a PseudopatientProfile for the Pseudopatient
        PseudopatientProfile.objects.create(
            user=self.object,
            provider=self.request.user if provider else None,
        )
        return HttpResponseRedirect(self.get_success_url())

    def get_permission_required(self):
        """Returns the list of permissions that the user must have in order to access the view."""
        perms = ["users.can_add_user"]
        if self.kwargs.get("username", None):
            perms += ["users.can_add_user_with_provider", "users.can_add_user_with_specific_provider"]
        return perms

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Provider the view is trying to create
        a Pseudopatient for."""
        return self.kwargs.get("username", None)

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            _,  # object_data
            _,  # onetoone_forms
            _,  # medallergys_forms
            _,  # medhistorys_forms
            _,  # medhistorydetails_forms
            _,  # lab_formset
            onetoones_to_save,
            medallergys_to_save,
            medhistorys_to_save,
            medhistorydetails_to_save,
            labs_to_save,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        else:
            return self.form_valid(
                form=form,  # type: ignore
                medallergys_to_save=medallergys_to_save,
                onetoones_to_save=onetoones_to_save,
                medhistorydetails_to_save=medhistorydetails_to_save,
                medhistorys_to_save=medhistorys_to_save,
                labs_to_save=labs_to_save,
                **kwargs,
            )


pseudopatient_create_view = PseudopatientCreateView.as_view()


class PseudopatientListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
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


class UserDeleteView(LoginRequiredMixin, AutoPermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    model = User
    success_message = _("User successfully deleted")

    def get_success_message(self, cleaned_data):
        if self.object.role == Roles.PSEUDOPATIENT:
            return _("Pseudopatient successfully deleted")
        else:
            return _("User successfully deleted")

    def get_success_url(self):
        if self.request.user.is_authenticated and self.object != self.request.user:
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


class UserDetailView(AutoPermissionRequiredMixin, DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, AutoPermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

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
