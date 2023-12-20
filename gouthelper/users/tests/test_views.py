import pytest
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponseRedirect
from django.test import RequestFactory
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from ...profiles.models import PseudopatientProfile
from ..choices import Roles
from ..forms import UserAdminChangeForm
from ..models import Pseudopatient, User
from ..tests.factories import UserFactory
from ..views import PseudopatientCreateView, UserRedirectView, UserUpdateView, user_detail_view

pytestmark = pytest.mark.django_db


class TestPseudoPatientCreateView:
    """Tests for the PseudopatientCreateView, which is actually a View
    with a post method, not a CreateView.
    """

    def test__post_no_user(self, rf: RequestFactory):
        """Test that the view's post() method creates a Pseudopatient
        with a unique username when no provider kwarg is passed in the url.
        """
        view = PseudopatientCreateView()
        request = rf.get("/fake-url/")
        request.user = AnonymousUser()
        view.post(request=request)
        assert Pseudopatient.objects.count() == 1
        user = Pseudopatient.objects.get()
        assert user.role == Roles.PSEUDOPATIENT
        assert PseudopatientProfile.objects.count() == 1
        profile = PseudopatientProfile.objects.get()
        assert profile.user == user
        assert profile.provider is None

    def test__post_with_user_no_provider_kwarg(self, rf: RequestFactory):
        """Test that the view's post() method creates a Pseudopatient with
        a unique username when called by a logged in User but with no provider
        kwarg in the url.
        """
        view = PseudopatientCreateView()
        request = rf.get("/fake-url/")
        request.user = UserFactory()
        view.post(request=request)
        assert Pseudopatient.objects.count() == 1
        user = Pseudopatient.objects.last()
        assert user.role == Roles.PSEUDOPATIENT
        assert PseudopatientProfile.objects.count() == 1
        profile = PseudopatientProfile.objects.get()
        assert profile.user == user
        assert profile.provider is None

    def test__post_with_user_and_provider_kwarg(self, rf: RequestFactory):
        """Test that the view's post() method creates a Pseudopatient with
        a unique username when called by a logged in User and with a provider
        kwarg in the url.
        """
        view = PseudopatientCreateView()
        request = rf.get("/fake-url/")
        request.user = UserFactory()
        view.post(request=request, username=request.user.username)
        assert Pseudopatient.objects.count() == 1
        user = Pseudopatient.objects.last()
        assert user.role == Roles.PSEUDOPATIENT
        assert PseudopatientProfile.objects.count() == 1
        profile = PseudopatientProfile.objects.get()
        assert profile.user == user
        assert profile.provider == request.user

    def test__post_user_provider_kwarg_discrepant(self, rf: RequestFactory):
        """Test that the view's post() method raises PermissionDenied
        when called by a logged in User and with a provider
        kwarg in the url that is not the same as the logged in User.
        """
        view = PseudopatientCreateView()
        request = rf.get("/fake-url/")
        request.user = UserFactory()
        with pytest.raises(PermissionDenied) as exc:
            view.post(request=request, username=UserFactory().username)
        assert exc.value.args[0] == "You can't create a pseudopatient for a User other than yourself."


class TestUserUpdateView:
    """
    TODO:
        extracting view initialization code as class-scoped fixture
        would be great if only pytest-django supported non-function-scoped
        fixture db access -- this is a work-in-progress for now:
        https://github.com/pytest-dev/pytest-django/pull/258
    """

    def dummy_get_response(self, request: HttpRequest):
        return None

    def test_get_success_url(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.post("/fake-url/")
        request.user = user

        view.request = request
        assert view.get_success_url() == f"/users/{user.username}/"

    def test_get_object(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")
        request.user = user

        view.request = request

        assert view.get_object() == user

    def test_form_valid(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)
        request.user = user

        view.request = request

        # Initialize the form
        form = UserAdminChangeForm()
        form.cleaned_data = {}
        form.instance = user
        view.form_valid(form)

        messages_sent = [m.message for m in messages.get_messages(request)]
        assert messages_sent == [_("Information successfully updated")]


class TestUserRedirectView:
    def test_get_redirect_url(self, user: User, rf: RequestFactory):
        view = UserRedirectView()
        request = rf.get("/fake-url")
        request.user = user

        view.request = request
        assert view.get_redirect_url() == f"/users/{user.username}/"


class TestUserDetailView:
    def test_authenticated(self, user: User, rf: RequestFactory):
        request = rf.get("/fake-url/")
        request.user = UserFactory()
        response = user_detail_view(request, username=user.username)

        assert response.status_code == 200

    def test_not_authenticated(self, user: User, rf: RequestFactory):
        request = rf.get("/fake-url/")
        request.user = AnonymousUser()
        response = user_detail_view(request, username=user.username)
        login_url = reverse(settings.LOGIN_URL)

        assert isinstance(response, HttpResponseRedirect)
        assert response.status_code == 302
        assert response.url == f"{login_url}?next=/fake-url/"
