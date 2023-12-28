import pytest
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponseRedirect
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from ...dateofbirths.forms import DateOfBirthForm
from ...dateofbirths.helpers import yearsago
from ...dateofbirths.models import DateOfBirth
from ...ethnicitys.choices import Ethnicitys
from ...ethnicitys.forms import EthnicityForm
from ...ethnicitys.models import Ethnicity
from ...genders.choices import Genders
from ...genders.forms import GenderForm
from ...genders.models import Gender
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.forms import GoutForm
from ...medhistorys.models import Gout
from ...profiles.models import PseudopatientProfile
from ..choices import Roles
from ..forms import PseudopatientForm, UserAdminChangeForm
from ..models import Pseudopatient, User
from ..tests.factories import UserFactory
from ..views import (
    PseudopatientCreateView,
    PseudopatientListView,
    UserDeleteView,
    UserRedirectView,
    UserUpdateView,
    user_detail_view,
)

pytestmark = pytest.mark.django_db


class TestPseudoPatientCreateView(TestCase):
    """Tests for the PseudopatientCreateView, which is actually a View
    with a post method, not a CreateView.
    """

    def setUp(self):
        self.rf = RequestFactory()
        self.provider = UserFactory()
        self.patient = UserFactory(role=Roles.PATIENT)
        self.admin = UserFactory(role=Roles.ADMIN)

    def test__view_attrs(self):
        """Test that the view's attrs are correct."""
        view = PseudopatientCreateView()
        assert view.model == Pseudopatient
        assert view.form_class == PseudopatientForm
        assert view.medhistorys == {MedHistoryTypes.GOUT: {"form": GoutForm, "model": Gout}}
        assert view.onetoones == {
            "dateofbirth": {"form": DateOfBirthForm, "model": DateOfBirth},
            "ethnicity": {"form": EthnicityForm, "model": Ethnicity},
            "gender": {"form": GenderForm, "model": Gender},
        }
        assert view.medhistory_details == [MedHistoryTypes.GOUT]

    def test__get_context_data(self):
        """Tests that the required context data is passed to the template."""
        response = self.client.get(reverse("users:create-pseudopatient"))
        assert response.status_code == 200
        assert f"{MedHistoryTypes.GOUT}_form" in response.context
        assert "dateofbirth_form" in response.context
        assert "ethnicity_form" in response.context
        assert "gender_form" in response.context
        assert "goutdetail_form" in response.context

    def test__post_no_user(self):
        """Tests the post() method of the view."""
        data = {
            "dateofbirth-value": 50,
            "ethnicity-value": Ethnicitys.CAUCASIANAMERICAN,
            "gender-value": Genders.MALE,
            f"{MedHistoryTypes.GOUT}-value": True,
            "flaring": True,
            "hyperuricemic": True,
            "on_ppx": False,
            "on_ult": False,
        }
        response = self.client.post(reverse("users:create-pseudopatient"), data=data)
        assert response.status_code == 302
        assert Pseudopatient.objects.count() == 1
        pseudopatient = Pseudopatient.objects.get()
        assert getattr(pseudopatient, "dateofbirth", None)
        assert pseudopatient.dateofbirth.value == yearsago(data["dateofbirth-value"]).date()
        assert getattr(pseudopatient, "ethnicity", None)
        assert pseudopatient.ethnicity.value == data["ethnicity-value"]
        assert getattr(pseudopatient, "gender", None)
        assert pseudopatient.gender.value == data["gender-value"]
        assert PseudopatientProfile.objects.exists()
        profile = PseudopatientProfile.objects.get()
        assert profile.user == pseudopatient
        assert profile.provider is None
        assert pseudopatient.medhistory_set.count() == 1
        gout = pseudopatient.medhistory_set.get()
        assert getattr(gout, "goutdetail", None)
        assert gout.goutdetail.flaring == data["flaring"]
        assert gout.goutdetail.hyperuricemic == data["hyperuricemic"]
        assert gout.goutdetail.on_ppx == data["on_ppx"]
        assert gout.goutdetail.on_ult == data["on_ult"]
        # Assert that the Pseudopatient history was set correctly to track the creating User
        assert User.history.filter(username=pseudopatient.username).first().history_user is None

    def test__post_with_provider_no_provider_kwarg(self):
        """Test that the view's post() method creates a Pseudopatient with
        a unique username when called by a logged in Provider but with no provider
        kwarg in the url.
        """
        # Log in the provider
        self.client.force_login(self.provider)
        data = {
            "dateofbirth-value": 50,
            "ethnicity-value": Ethnicitys.CAUCASIANAMERICAN,
            "gender-value": Genders.MALE,
            f"{MedHistoryTypes.GOUT}-value": True,
            "flaring": True,
            "hyperuricemic": True,
            "on_ppx": False,
            "on_ult": False,
        }
        response = self.client.post(reverse("users:create-pseudopatient"), data=data)
        assert response.status_code == 302
        assert Pseudopatient.objects.count() == 1
        pseudopatient = Pseudopatient.objects.get()
        assert getattr(pseudopatient, "dateofbirth", None)
        assert pseudopatient.dateofbirth.value == yearsago(data["dateofbirth-value"]).date()
        assert getattr(pseudopatient, "ethnicity", None)
        assert pseudopatient.ethnicity.value == data["ethnicity-value"]
        assert getattr(pseudopatient, "gender", None)
        assert pseudopatient.gender.value == data["gender-value"]
        assert PseudopatientProfile.objects.exists()
        profile = PseudopatientProfile.objects.get()
        assert profile.user == pseudopatient
        assert profile.provider is None
        assert pseudopatient.medhistory_set.count() == 1
        gout = pseudopatient.medhistory_set.get()
        assert getattr(gout, "goutdetail", None)
        assert gout.goutdetail.flaring == data["flaring"]
        assert gout.goutdetail.hyperuricemic == data["hyperuricemic"]
        assert gout.goutdetail.on_ppx == data["on_ppx"]
        assert gout.goutdetail.on_ult == data["on_ult"]
        # Assert that the Pseudopatient history was set correctly to track the creating User
        assert User.history.filter(username=pseudopatient.username).first().history_user == self.provider

    def test__post_with_provider_and_provider_kwarg(self):
        """Test that the view's post() method creates a Pseudopatient with
        a unique username when called by a logged in User and with a provider
        kwarg in the url.
        """
        # Log in the provider
        self.client.force_login(self.provider)
        data = {
            "dateofbirth-value": 50,
            "ethnicity-value": Ethnicitys.CAUCASIANAMERICAN,
            "gender-value": Genders.MALE,
            f"{MedHistoryTypes.GOUT}-value": True,
            "flaring": True,
            "hyperuricemic": True,
            "on_ppx": False,
            "on_ult": False,
        }
        response = self.client.post(
            reverse("users:provider-create-pseudopatient", kwargs={"username": self.provider.username}), data=data
        )
        assert response.status_code == 302
        assert Pseudopatient.objects.count() == 1
        pseudopatient = Pseudopatient.objects.get()
        assert getattr(pseudopatient, "dateofbirth", None)
        assert pseudopatient.dateofbirth.value == yearsago(data["dateofbirth-value"]).date()
        assert getattr(pseudopatient, "ethnicity", None)
        assert pseudopatient.ethnicity.value == data["ethnicity-value"]
        assert getattr(pseudopatient, "gender", None)
        assert pseudopatient.gender.value == data["gender-value"]
        assert PseudopatientProfile.objects.exists()
        profile = PseudopatientProfile.objects.get()
        assert profile.user == pseudopatient
        # Need to check or id, not equivalence because of proxy model status (i.e. User vs Provider)
        assert profile.provider.id == self.provider.id
        assert pseudopatient.medhistory_set.count() == 1
        gout = pseudopatient.medhistory_set.get()
        assert getattr(gout, "goutdetail", None)
        assert gout.goutdetail.flaring == data["flaring"]
        assert gout.goutdetail.hyperuricemic == data["hyperuricemic"]
        assert gout.goutdetail.on_ppx == data["on_ppx"]
        assert gout.goutdetail.on_ult == data["on_ult"]
        # Assert that the Pseudopatient history was set correctly to track the creating User
        assert User.history.filter(username=pseudopatient.username).first().history_user == self.provider

    def test__rules_provider_no_provider_kwarg(self):
        """Test that the view's post() method creates a Pseudopatient
        with a unique username when no provider kwarg is passed in the url
        by a provider.
        """
        view = PseudopatientCreateView
        request = self.rf.get(reverse("users:create-pseudopatient"))
        request.user = self.provider
        assert view.as_view()(request)

    def test__rules_provider_with_provider_kwarg(self):
        """Test that the view's post() method creates a Pseudopatient with
        a unique username when called by a logged in Provider and with a provider
        kwarg in the url.
        """
        view = PseudopatientCreateView
        kwargs = {"username": self.provider.username}
        request = self.rf.get(reverse("users:provider-create-pseudopatient", kwargs=kwargs))
        request.user = self.provider
        assert view.as_view()(request, **kwargs)

    def test__rules_provider_provider_kwarg_discrepant_denied(self):
        """Test that the view's post() method raises PermissionDenied
        when called by a logged in User and with a provider
        kwarg in the url that is not the same as the logged in User.
        """
        view = PseudopatientCreateView
        kwargs = {"username": self.patient.username}
        request = self.rf.get(reverse("users:provider-create-pseudopatient", kwargs=kwargs))
        request.user = self.provider
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_admin_no_provider_kwarg(self):
        """Test that the view's post() method creates a Pseudopatient
        with a unique username when no provider kwarg is passed in the url
        by an Admin.
        """
        view = PseudopatientCreateView
        request = self.rf.get(reverse("users:create-pseudopatient"))
        request.user = self.admin
        assert view.as_view()(request)

    def test__rules_admin_with_provider_kwarg(self):
        """Test that the view's post() method creates a Pseudopatient with
        a unique username when called by a logged in Admin and with a provider
        kwarg in the url.
        """
        view = PseudopatientCreateView
        kwargs = {"username": self.admin.username}
        request = self.rf.post(reverse("users:provider-create-pseudopatient", kwargs=kwargs))
        request.user = self.admin
        assert view.as_view()(request, **kwargs)

    def test__rules_admin_provider_kwarg_discrepant_denied(self):
        """Test that the view's post() method raises PermissionDenied
        when called by a logged in Admin and with a provider
        kwarg in the url that is not the same as the logged in User.
        """
        view = PseudopatientCreateView
        kwargs = {"username": self.patient.username}
        request = self.rf.get(reverse("users:provider-create-pseudopatient", kwargs=kwargs))
        request.user = self.admin
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_user_not_provider_or_admin_provider_kwarg(self):
        """Test that the view's post() method raises PermissionDenied
        when called by a logged in User who is not a Provider or Admin.
        """
        view = PseudopatientCreateView
        kwargs = {"username": "blahaha"}
        request = self.rf.get(reverse("users:provider-create-pseudopatient", kwargs=kwargs))
        request.user = self.patient
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_pseudopatient(self):
        """Test that the view's post() method raises PermissionDenied
        when called by a logged in Pseudopatient.
        """
        view = PseudopatientCreateView
        request = self.rf.post(reverse("users:create-pseudopatient"))
        request.user = UserFactory(role=Roles.PSEUDOPATIENT)
        with pytest.raises(PermissionDenied):
            view.as_view()(request)


class TestPseudopatientListView(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.provider = UserFactory()
        self.provider_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)
        self.provider_pseudopatient.profile.provider = self.provider
        self.provider_pseudopatient.profile.save()
        self.patient = UserFactory(role=Roles.PATIENT)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.admin_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)
        self.admin_pseudopatient.profile.provider = self.admin
        self.admin_pseudopatient.profile.save()

    def test__get_permission_object(self):
        """Test that the view's get_permission_object() method returns
        the username kwarg.
        """
        view = PseudopatientListView()
        request = self.rf.get("/fake-url/")
        request.user = self.provider
        view.request = request
        view.kwargs = {"username": self.provider.username}
        assert view.get_permission_object() == self.provider.username

    def test__get_queryset(self):
        """Test that the view's get_queryset() method returns a queryset
        of Pseudopatients whose provider is the requesting User.
        """
        view = PseudopatientListView()
        kwargs = {"username": self.provider.username}
        request = self.rf.get(reverse("users:pseudopatients", kwargs=kwargs))
        request.user = self.provider
        view.request = request
        view.kwargs = kwargs
        assert list(view.get_queryset()) == [self.provider_pseudopatient]

    def test__rules_providers_own_list(self):
        """Test that a Provider can see his or her own list."""
        view = PseudopatientListView
        kwargs = {"username": self.provider.username}
        request = self.rf.get(reverse("users:pseudopatients", kwargs=kwargs))
        request.user = self.provider
        assert view.as_view()(request, **kwargs)

    def test__rules_provider_other_provider_list(self):
        """Test that a Provider cannot see another Provider's list."""
        provider2 = UserFactory()
        provider2_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)
        provider2_pseudopatient.profile.provider = provider2
        provider2_pseudopatient.profile.save()
        view = PseudopatientListView
        kwargs = {"username": provider2.username}
        request = self.rf.get(reverse("users:pseudopatients", kwargs=kwargs))
        request.user = self.provider
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def tes__rules_provider_cannot_see_admin_list(self):
        """Test that a Provider cannot see an Admin's list."""
        view = PseudopatientListView
        kwargs = {"username": self.admin.username}
        request = self.rf.get(reverse("users:pseudopatients", kwargs=kwargs))
        request.user = self.provider
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_admin_can_see_own_list(self):
        """Test that an Admin can see his or her own list."""
        view = PseudopatientListView
        kwargs = {"username": self.admin.username}
        request = self.rf.get(reverse("users:pseudopatients", kwargs=kwargs))
        request.user = self.admin
        assert view.as_view()(request, **kwargs)

    def test__rules_admin_cannot_see_providers_list(self):
        """Test that an Admin cannot see a Provider's list."""
        view = PseudopatientListView
        kwargs = {"username": self.provider.username}
        request = self.rf.get(reverse("users:pseudopatients", kwargs=kwargs))
        request.user = self.admin
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_patient_cannot_see_provider_list(self):
        """Test that a Patient cannot see either list."""
        view = PseudopatientListView
        kwargs = {"username": self.provider.username}
        request = self.rf.get(reverse("users:pseudopatients", kwargs=kwargs))
        request.user = self.patient
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_patient_cannot_see_admin_list(self):
        """Test that a Patient cannot see either list."""
        view = PseudopatientListView
        kwargs = {"username": self.admin.username}
        request = self.rf.get(reverse("users:pseudopatients", kwargs=kwargs))
        request.user = self.patient
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)


class TestUserDeleteView(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.provider = UserFactory()
        self.patient = UserFactory(role=Roles.PATIENT)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.provider_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)
        self.provider_pseudopatient.profile.provider = self.provider
        self.provider_pseudopatient.profile.save()
        self.admin_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)
        self.admin_pseudopatient.profile.provider = self.admin
        self.admin_pseudopatient.profile.save()
        self.anon_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)

    def dummy_get_response(self, request: HttpRequest):
        return None

    def test__get_success_message(self):
        view = UserDeleteView()
        view.object = self.provider
        request = self.rf.get("/fake-url/")
        view.request = request
        assert view.get_success_message(cleaned_data={}) == _("User successfully deleted")
        view.object = self.provider_pseudopatient
        assert view.get_success_message(cleaned_data={}) == _("Pseudopatient successfully deleted")

    def test__get_success_url(self):
        view = UserDeleteView()
        view.object = self.provider
        request = self.rf.get("/fake-url/")
        request.user = AnonymousUser()
        view.request = request
        assert view.get_success_url() == reverse("contents:home")
        request.user = self.provider
        view.object = self.provider_pseudopatient
        assert view.get_success_url() == reverse("users:pseudopatients", kwargs={"username": self.provider.username})

    def test__get_object(self):
        view = UserDeleteView()
        request = self.rf.get("/fake-url/")
        request.user = self.provider
        view.request = request
        view.kwargs = {}
        assert view.get_object() == self.provider
        view.kwargs = {"username": self.provider_pseudopatient.username}
        assert view.get_object() == self.provider_pseudopatient

    def test__rules_provider_can_delete_own_pseudopatient(self):
        """Test that a Provider can delete his or her own Pseudopatient."""
        view = UserDeleteView
        kwargs = {"username": self.provider_pseudopatient.username}
        request = self.rf.get(reverse("users:delete-pseudopatient", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        request.user = self.provider
        assert view.as_view()(request, **kwargs)

        request = self.rf.post(reverse("users:delete-pseudopatient", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        request.user = self.provider
        assert view.as_view()(request, **kwargs)

    def test__rules_provider_cannot_delete_admins_pseudopatient(self):
        """Test that a Provider cannot delete an Admin's Pseudopatient."""
        view = UserDeleteView
        kwargs = {"username": self.admin_pseudopatient.username}
        request = self.rf.get(reverse("users:delete-pseudopatient", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        request.user = self.provider
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

        request = self.rf.post(reverse("users:delete-pseudopatient", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        request.user = self.provider
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_provider_cannot_delete_anonymous_pseudopatient(self):
        """Test that a Provider cannot delete an Anonymous Pseudopatient."""
        view = UserDeleteView
        kwargs = {"username": self.anon_pseudopatient.username}
        request = self.rf.get(reverse("users:delete-pseudopatient", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        request.user = self.provider
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

        request = self.rf.post(reverse("users:delete-pseudopatient", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        request.user = self.provider
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_admin_can_delete_own_pseudopatient(self):
        """Test that an Admin can delete his or her own Pseudopatient."""
        view = UserDeleteView
        kwargs = {"username": self.admin_pseudopatient.username}
        request = self.rf.get(reverse("users:delete-pseudopatient", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        request.user = self.admin
        assert view.as_view()(request, **kwargs)

        request = self.rf.post(reverse("users:delete-pseudopatient", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        request.user = self.admin
        assert view.as_view()(request, **kwargs)

    def test__rules_admin_cannot_delete_providers_pseudopatient(self):
        """Test that an Admin cannot delete a Provider's Pseudopatient."""
        view = UserDeleteView
        kwargs = {"username": self.provider_pseudopatient.username}
        request = self.rf.get(reverse("users:delete-pseudopatient", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        request.user = self.admin
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

        request = self.rf.post(reverse("users:delete-pseudopatient", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        request.user = self.admin
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_admin_cannot_delete_anonymous_pseudopatient(self):
        """Test that an Admin cannot delete an Anonymous Pseudopatient."""
        view = UserDeleteView
        kwargs = {"username": self.anon_pseudopatient.username}
        request = self.rf.get(reverse("users:delete-pseudopatient", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        request.user = self.admin
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

        request = self.rf.post(reverse("users:delete-pseudopatient", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        request.user = self.admin
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_patient_cannot_delete_provider_pseudopatient(self):
        """Test that a Patient cannot delete a Provider's Pseudopatient."""
        view = UserDeleteView
        kwargs = {"username": self.provider_pseudopatient.username}
        request = self.rf.get(reverse("users:delete-pseudopatient", kwargs=kwargs))
        request.user = self.patient
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

        request = self.rf.post(reverse("users:delete-pseudopatient", kwargs=kwargs))
        request.user = self.patient
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_patient_cannot_delete_admin_pseudopatient(self):
        """Test that a Patient cannot delete an Admin's Pseudopatient."""
        view = UserDeleteView
        kwargs = {"username": self.admin_pseudopatient.username}
        request = self.rf.get(reverse("users:delete-pseudopatient", kwargs=kwargs))
        request.user = self.patient
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

        request = self.rf.post(reverse("users:delete-pseudopatient", kwargs=kwargs))
        request.user = self.patient
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_provider_can_delete_self(self):
        """Test that a Provider can delete his or her own User."""
        view = UserDeleteView

        request = self.rf.get(f"users/{self.provider.username}/")

        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        request.user = self.provider
        assert view.as_view()(request)

        request = self.rf.post(f"users/{self.provider.username}/")

        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        request.user = self.provider
        assert view.as_view()(request)

    def test__rules_admin_can_delete_self(self):
        """Test that an Admin can delete his or her own User."""
        view = UserDeleteView

        request = self.rf.get(f"users/{self.admin.username}/")

        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        request.user = self.admin
        assert view.as_view()(request)

        request = self.rf.post(f"users/{self.admin.username}/")

        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        request.user = self.admin
        assert view.as_view()(request)

    def test__rules_patient_can_delete_self(self):
        """Test that a Patient can delete his or her own User."""
        view = UserDeleteView

        request = self.rf.get(f"users/{self.patient.username}/")

        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        request.user = self.patient
        assert view.as_view()(request)

        request = self.rf.post(f"users/{self.patient.username}/")

        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        request.user = self.patient
        assert view.as_view()(request)


class TestUserUpdateView(TestCase):
    """
    TODO:
        extracting view initialization code as class-scoped fixture
        would be great if only pytest-django supported non-function-scoped
        fixture db access -- this is a work-in-progress for now:
        https://github.com/pytest-dev/pytest-django/pull/258
    """

    def setUp(self):
        self.rf = RequestFactory()
        self.provider = UserFactory()
        self.patient = UserFactory(role=Roles.PATIENT)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.provider_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)
        self.provider_pseudopatient.profile.provider = self.provider
        self.provider_pseudopatient.profile.save()
        self.admin_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)
        self.admin_pseudopatient.profile.provider = self.admin
        self.admin_pseudopatient.profile.save()
        self.anon_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)

    def dummy_get_response(self, request: HttpRequest):
        return None

    def test_get_success_url(self):
        view = UserUpdateView()
        request = self.rf.post("/fake-url/")
        request.user = self.provider

        view.request = request
        assert view.get_success_url() == f"/users/{self.provider.username}/"

    def test_get_object(self):
        view = UserUpdateView()
        request = self.rf.get("/fake-url/")
        request.user = self.provider

        view.request = request

        assert view.get_object() == self.provider

    def test_form_valid(self):
        view = UserUpdateView()
        request = self.rf.get("/fake-url/")

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)
        request.user = self.provider

        view.request = request

        # Initialize the form
        form = UserAdminChangeForm()
        form.cleaned_data = {}
        form.instance = self.provider
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


class TestUserDetailView(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.provider = UserFactory()
        self.patient = UserFactory(role=Roles.PATIENT)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.provider_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)
        self.provider_pseudopatient.profile.provider = self.provider
        self.provider_pseudopatient.profile.save()
        self.admin_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)
        self.admin_pseudopatient.profile.provider = self.admin
        self.admin_pseudopatient.profile.save()
        self.anon_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)

    def test_authenticated(self):
        request = self.rf.get(f"users/{self.provider.username}/")
        request.user = self.provider
        response = user_detail_view(request, username=self.provider.username)

        assert response.status_code == 200

    def test_not_authenticated(self):
        request = self.rf.get("/fake-url/")
        request.user = AnonymousUser()
        response = user_detail_view(request, username=self.provider.username)
        login_url = reverse(settings.LOGIN_URL)

        assert isinstance(response, HttpResponseRedirect)
        assert response.status_code == 302
        assert response.url == f"{login_url}?next=/fake-url/"

    def test__rules_provider_own_detail(self):
        """Test that a Provider can see his or her own detail."""
        view = user_detail_view
        kwargs = {"username": self.provider.username}
        request = self.rf.get(reverse("users:detail", kwargs=kwargs))
        request.user = self.provider
        assert view(request, **kwargs)

    def test__rules_provider_own_patient(self):
        """Test that a Provider can see his or her own Pseudopatient's detail."""
        view = user_detail_view
        kwargs = {"username": self.provider_pseudopatient.username}
        request = self.rf.get(reverse("users:detail", kwargs=kwargs))
        request.user = self.provider
        assert view(request, **kwargs)

    def test__rules_provider_cannot_see_admin(self):
        """Test that a Provider cannot see an Admin's detail."""
        view = user_detail_view
        kwargs = {"username": self.admin.username}
        request = self.rf.get(reverse("users:detail", kwargs=kwargs))
        request.user = self.provider
        with pytest.raises(PermissionDenied):
            view(request, **kwargs)

    def test__rules_provider_cannot_see_admin_pseudopatient(self):
        """Test that a Provider cannot see an Admin's Pseudopatient's detail."""
        view = user_detail_view
        kwargs = {"username": self.admin_pseudopatient.username}
        request = self.rf.get(reverse("users:detail", kwargs=kwargs))
        request.user = self.provider
        with pytest.raises(PermissionDenied):
            view(request, **kwargs)

    def test__rules_provider_cannot_see_patient(self):
        """Test that a Provider cannot see a Patient's detail."""
        view = user_detail_view
        kwargs = {"username": self.patient.username}
        request = self.rf.get(reverse("users:detail", kwargs=kwargs))
        request.user = self.provider
        with pytest.raises(PermissionDenied):
            view(request, **kwargs)

    def test__rules_provider_can_see_anonymous_pseudopatient(self):
        """Test that a Provider can see an Anonymous Pseudopatient's detail."""
        view = user_detail_view
        kwargs = {"username": self.anon_pseudopatient.username}
        request = self.rf.get(reverse("users:detail", kwargs=kwargs))
        request.user = self.provider
        assert view(request, **kwargs)
