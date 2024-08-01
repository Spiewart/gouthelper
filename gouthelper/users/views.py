from typing import TYPE_CHECKING, Any, Union

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.forms import ModelForm
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView, ListView, RedirectView, UpdateView
from rules.contrib.views import AutoPermissionRequiredMixin, PermissionRequiredMixin

from ..flares.models import Flare
from ..flares.selectors import flareaid_medallergy_prefetch, flareaid_medhistory_prefetch
from ..medhistorydetails.forms import GoutDetailForm
from ..medhistorydetails.models import GoutDetail
from ..medhistorys.choices import MedHistoryTypes
from ..utils.exceptions import Continue
from ..utils.views import GoutHelperUserDetailMixin, GoutHelperUserEditMixin
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
from .selectors import pseudopatient_profile_qs, pseudopatient_profile_update_qs

if TYPE_CHECKING:
    from ..medhistorys.models import MedHistory

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

    @cached_property
    def flare(self) -> Flare | None:
        flare_kwarg = self.kwargs.get("flare", None)
        return (
            Flare.related_objects.prefetch_related(flareaid_medhistory_prefetch(), flareaid_medallergy_prefetch()).get(
                pk=flare_kwarg
            )
            if flare_kwarg
            else None  # pylint: disable=W0201
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"flare": self.flare})
        return context

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        if self.flare:
            kwargs.update({"flare": self.flare})
        return kwargs

    def get_goutdetail_initial(self) -> dict[str, Any]:
        initial = {
            "on_ppx": None,
            "on_ult": None,
            "starting_ult": None,
        }
        initial["flaring"] = True
        initial["at_goal"] = False if self.flare.urate and not self.flare.urate.at_goal else None
        return initial

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

    def goutdetail_mh_context(
        self,
        kwargs: dict[str, Any],
        mh_obj: Union["MedHistory", User, None] = None,
    ) -> None:
        """Overwritten to add initial to the GoutDetail form."""
        if "goutdetail_form" not in kwargs:
            goutdetail_i = getattr(mh_obj, "goutdetail", None) if mh_obj else None
            goutdetail_form = self.medhistory_detail_forms["goutdetail"]
            kwargs["goutdetail_form"] = (
                goutdetail_form
                if isinstance(goutdetail_form, ModelForm)
                else goutdetail_form(
                    instance=goutdetail_i,
                    initial=self.get_goutdetail_initial(),
                    patient=self.user,
                    request_user=self.request_user,
                    str_attrs=self.str_attrs,
                )
            )
            raise Continue

    def goutdetail_mh_post_pop(
        self,
        gout: Union["MedHistory", None],
    ) -> None:
        """Overwritten to add initial to GoutDetailForm."""
        if gout:
            gd = getattr(gout, "goutdetail", None)
        else:
            gd = GoutDetail()
        self.medhistory_detail_forms.update(
            {
                "goutdetail": self.medhistory_detail_forms["goutdetail"](
                    self.request.POST,
                    instance=gd,
                    initial=self.get_goutdetail_initial(),
                    str_attrs=self.str_attrs,
                    patient=self.user,
                    request_user=self.request_user,
                )
            }
        )
        raise Continue

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        if self.errors:
            return self.errors
        else:
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
    pk_url_kwarg = "pseudopatient"
    form_class = PseudopatientForm
    permission_required = "users.can_edit_pseudopatient"

    MEDHISTORY_FORMS = MEDHISTORY_FORMS
    OTO_FORMS = OTO_FORMS
    MEDHISTORY_DETAIL_FORMS = MEDHISTORY_DETAIL_FORMS

    def get_queryset(self):
        return pseudopatient_profile_update_qs(self.kwargs.get("pseudopatient"))

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
    pk_url_kwarg = "pseudopatient"
    template_name = "users/pseudopatient_detail.html"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return pseudopatient_profile_qs(self.kwargs.get("pseudopatient", None))

    def get(self, request, *args, **kwargs):
        self.update_onetoones()
        self.update_most_recent_flare()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def update_onetoones(self):
        for onetoone in Pseudopatient.list_of_related_aid_models():
            related_onetoone = getattr(self.object, onetoone, None)
            if related_onetoone:
                related_onetoone.update_aid(qs=self.object)

    def update_most_recent_flare(self):
        most_recent_flare_qs = getattr(self.object, "most_recent_flare", None)
        most_recent_flare = most_recent_flare_qs[0] if most_recent_flare_qs else None
        if most_recent_flare and not most_recent_flare.date_ended:
            most_recent_flare.update_aid(qs=self.object)

    def get_permission_object(self) -> Pseudopatient:
        return self.object

    def update_session_patient(self) -> None:
        self.add_patient_to_session(self.object)


pseudopatient_detail_view = PseudopatientDetailView.as_view()


class PseudopatientListView(LoginRequiredMixin, PermissionRequiredMixin, GoutHelperUserDetailMixin, ListView):
    """ListView for displaying all of a Provider or Admin's Pseudopatients."""

    model = Pseudopatient
    template_name = "users/pseudopatients.html"
    paginate_by = 5
    permission_required = "users.can_view_provider_list"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context

    def get_permission_object(self):
        """Returns the object the permission is being checked against. For this view,
        that is the username kwarg indicating which Provider the view is trying to create
        a list of Pseudopatients for."""
        return self.kwargs.get("username", None)

    # Overwrite get_queryset() to return Patient objects filtered by their PseudopatientProfile provider field
    # Fetch only Pseudopatients where the provider is equal to the requesting User (Provider)
    def get_queryset(self):
        return (
            Pseudopatient.objects.select_related("pseudopatientprofile__provider")
            .filter(pseudopatientprofile__provider=self.request.user)
            .order_by("modified")
        )


pseudopatient_list_view = PseudopatientListView.as_view()


class UserDeleteView(
    LoginRequiredMixin, AutoPermissionRequiredMixin, GoutHelperUserDetailMixin, SuccessMessageMixin, DeleteView
):
    model = User

    def get_success_message(self, cleaned_data):
        return _("User successfully deleted")

    def get_success_url(self):
        return reverse("contents:home")

    def get_object(self):
        return self.request.user


user_delete_view = UserDeleteView.as_view()


class PseudopatientDeleteView(UserDeleteView):
    model = Pseudopatient

    def form_valid(self, form):
        self.remove_patient_from_session(self.object, delete=True)
        return super().form_valid(form)

    def get_object(self):
        return Pseudopatient.objects.get(pk=self.kwargs.get("pseudopatient", None))

    def get_success_message(self, cleaned_data):
        return _("Pseudopatient successfully deleted")

    def get_success_url(self):
        return reverse("users:pseudopatients", kwargs={"username": self.request.user.username})


pseudopatient_delete_view = PseudopatientDeleteView.as_view()


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
                reverse("users:pseudopatient-detail", kwargs={"pseudopatient": self.get_object().pk})
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
        if self.request.user.role == Roles.PROVIDER:
            return reverse("users:pseudopatients", kwargs={"username": self.request.user.username})
        else:
            return reverse("users:detail", kwargs={"username": self.request.user.username})


user_redirect_view = UserRedirectView.as_view()
