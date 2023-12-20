import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView, RedirectView, UpdateView, View
from rules.contrib.views import AutoPermissionRequiredMixin, PermissionRequiredMixin

from ..profiles.models import PseudopatientProfile
from .choices import Roles
from .models import Pseudopatient

User = get_user_model()


class PseudopatientCreateView(LoginRequiredMixin, AutoPermissionRequiredMixin, SuccessMessageMixin, View):
    """View to create Pseudopatient Users. If called with a provider kwarg in the url,
    assigns provider field to the creating User.

    Returns:
        [redirect]: [Redirects to the newly created Pseudopatient's Detail page.]
    """

    def post(self, request, *args, **kwargs):
        provider = kwargs.get("username", None)
        # If the user is logged in, is a Provider or Admin, and there is a username kwarg in the url,
        # check if the logged in User's username isn't the same as the username kwarg in the url
        if (
            request.user.is_authenticated
            and provider
            and (request.user.role == Roles.PROVIDER or request.user.role == Roles.ADMIN)
        ) and request.user.username != provider:
            # Raise PermissionDenied if so
            raise PermissionDenied("You can't create a pseudopatient for a User other than yourself.")
        # Create a Pseudopatient with a unique username
        pseudopatient = Pseudopatient.objects.create(username=uuid.uuid4().hex[:30])
        # Create a PseudopatientProfile for the Pseudopatient
        PseudopatientProfile.objects.create(
            user=pseudopatient,
            provider=request.user if provider else None,
        )
        return HttpResponseRedirect(reverse("users:detail", kwargs={"username": pseudopatient.username}))


pseudopatient_create_view = PseudopatientCreateView.as_view()


class PseudopatientListView(LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin, ListView):
    """ListView for displaying all of a Provider or Admin's Pseudopatients."""

    model = Pseudopatient
    # THIS PERMISSION COULD BE TIGHTENED UP A LITTLE TO RESTRICT THE URL BUT DOESN'T CHANGE CONTENT ###
    permission_required = "users.add_user"
    template_name = "users/pseudopatients.html"
    paginate_by = 5

    # Test whether User is Provider, if not raise 404
    def test_func(self):
        return self.request.user.username == self.kwargs.get("username")

    # Overwrite get_queryset() to return Patient objects filtered by their PseudopatientProfile provider field
    # Fetch only Pseudopatients where the provider is equal to the requesting User (Provider)
    def get_queryset(self):
        return Pseudopatient.objects.filter(pseudopatientprofile__provider=self.request.user)


pseudopatient_list_view = PseudopatientListView.as_view()


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
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
