from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView, ListView, RedirectView, UpdateView
from rules.contrib.views import AutoPermissionRequiredMixin, PermissionRequiredMixin

from ..dateofbirths.forms import DateOfBirthForm
from ..dateofbirths.models import DateOfBirth
from ..ethnicitys.forms import EthnicityForm
from ..ethnicitys.models import Ethnicity
from ..genders.forms import GenderForm
from ..genders.models import Gender
from ..medhistorydetails.forms import GoutDetailForm
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.forms import GoutForm, MenopauseForm
from ..medhistorys.models import Gout, Menopause
from ..utils.views import GoutHelperUserMixin
from .choices import Roles
from .forms import PseudopatientForm
from .models import Pseudopatient
from .selectors import pseudopatient_profile_qs, pseudopatient_qs

User = get_user_model()


class PseudopatientCreateView(GoutHelperUserMixin, PermissionRequiredMixin, CreateView, SuccessMessageMixin):
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
        MedHistoryTypes.MENOPAUSE: {
            "form": MenopauseForm,
            "model": Menopause,
        },
    }
    medhistory_details = {MedHistoryTypes.GOUT: GoutDetailForm}

    def get_permission_required(self):
        """Returns the list of permissions that the user must have in order to access the view."""
        perms = ["users.can_add_user"]
        if self.kwargs.get("username", None):
            perms += ["users.can_add_user_with_provider"]
        return perms

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            oto_forms,
            mh_forms,
            mh_det_forms,
            _,  # ma_forms,
            _,  # lab_formsets,
            oto_2_save,
            oto_2_rem,
            mh_2_save,
            mh_2_rem,
            mh_det_2_save,
            mh_det_2_rem,
            _,  # ma_2_save,
            _,  # ma_2_rem,
            _,  # labs_2_save,
            _,  # labs_2_rem,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        mh_forms, errors_bool = self.post_process_menopause(
            mh_forms=mh_forms,
            dateofbirth=oto_forms["dateofbirth_form"].cleaned_data.get("value"),
            gender=oto_forms["gender_form"].cleaned_data.get("value"),
        )
        if errors_bool:
            return super().render_errors(
                form=form,
                oto_forms=oto_forms,
                mh_forms=mh_forms,
                mh_det_forms=mh_det_forms,
                ma_forms=None,
                lab_formsets=None,
                labs=None,
            )
        else:
            return self.form_valid(
                form=form,
                oto_2_save=oto_2_save,
                oto_2_rem=oto_2_rem,
                mh_2_save=mh_2_save,
                mh_2_rem=mh_2_rem,
                mh_det_2_save=mh_det_2_save,
                mh_det_2_rem=mh_det_2_rem,
                ma_2_save=None,
                ma_2_rem=None,
                labs_2_save=None,
                labs_2_rem=None,
            )


pseudopatient_create_view = PseudopatientCreateView.as_view()


class PseudopatientUpdateView(GoutHelperUserMixin, PermissionRequiredMixin, UpdateView, SuccessMessageMixin):
    """View to update Pseudopatient Users.

    Returns:
        [redirect]: [Redirects to the updated Pseudopatient's Detail page.]
    """

    model = Pseudopatient
    slug_field = "username"
    slug_url_kwarg = "username"
    form_class = PseudopatientForm
    permission_required = "users.can_edit_pseudopatient"

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
        MedHistoryTypes.MENOPAUSE: {
            "form": MenopauseForm,
            "model": Menopause,
        },
    }
    medhistory_details = {MedHistoryTypes.GOUT: GoutDetailForm}

    def get_queryset(self):
        return pseudopatient_profile_qs(self.kwargs.get("username"))

    def post(self, request, *args, **kwargs):
        (
            errors,
            form,
            oto_forms,
            mh_forms,
            mh_det_forms,
            _,  # ma_forms,
            _,  # lab_formsets,
            oto_2_save,
            oto_2_rem,
            mh_2_save,
            mh_2_rem,
            mh_det_2_save,
            mh_det_2_rem,
            _,  # ma_2_save,
            _,  # ma_2_rem,
            _,  # labs_2_save,
            _,  # labs_2_rem,
        ) = super().post(request, *args, **kwargs)
        if errors:
            return errors
        mh_forms, errors_bool = self.post_process_menopause(
            mh_forms=mh_forms,
            dateofbirth=oto_forms["dateofbirth_form"].cleaned_data.get("value"),
            gender=oto_forms["gender_form"].cleaned_data.get("value"),
        )
        if errors_bool:
            return super().render_errors(
                form=form,
                oto_forms=oto_forms,
                mh_forms=mh_forms,
                mh_det_forms=mh_det_forms,
                ma_forms=None,
                lab_formsets=None,
                labs=None,
            )
        else:
            return self.form_valid(
                form=form,
                oto_2_save=oto_2_save,
                oto_2_rem=oto_2_rem,
                mh_2_save=mh_2_save,
                mh_2_rem=mh_2_rem,
                mh_det_2_save=mh_det_2_save,
                mh_det_2_rem=mh_det_2_rem,
                ma_2_save=None,
                ma_2_rem=None,
                labs_2_save=None,
                labs_2_rem=None,
            )


pseudopatient_update_view = PseudopatientUpdateView.as_view()


class PseudopatientDetailView(AutoPermissionRequiredMixin, DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"
    template_name = "users/pseudopatient_detail.html"

    def get_queryset(self):
        return pseudopatient_qs(self.kwargs.get("username", None))


pseudopatient_detail_view = PseudopatientDetailView.as_view()


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
