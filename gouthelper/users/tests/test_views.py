from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib import auth, messages
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
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
from ...medhistorydetails.forms import GoutDetailForm
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.forms import GoutForm, MenopauseForm
from ...medhistorys.models import Gout, Menopause
from ...medhistorys.tests.factories import MenopauseFactory
from ...profiles.models import PseudopatientProfile
from ...utils.test_helpers import dummy_get_response
from ..choices import Roles
from ..forms import PseudopatientForm, UserAdminChangeForm
from ..models import Pseudopatient, User
from ..views import (
    PseudopatientCreateView,
    PseudopatientListView,
    PseudopatientUpdateView,
    UserDeleteView,
    UserRedirectView,
    UserUpdateView,
    user_detail_view,
)
from .factories import UserFactory, create_psp

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
        assert view.medhistorys == {
            MedHistoryTypes.GOUT: {"form": GoutForm, "model": Gout},
            MedHistoryTypes.MENOPAUSE: {"form": MenopauseForm, "model": Menopause},
        }
        assert view.onetoones == {
            "dateofbirth": {"form": DateOfBirthForm, "model": DateOfBirth},
            "ethnicity": {"form": EthnicityForm, "model": Ethnicity},
            "gender": {"form": GenderForm, "model": Gender},
        }
        assert view.medhistory_details == {MedHistoryTypes.GOUT: GoutDetailForm}

    def test__get_context_data(self):
        """Tests that the required context data is passed to the template."""
        response = self.client.get(reverse("users:pseudopatient-create"))
        assert response.status_code == 200
        assert "dateofbirth_form" in response.context
        assert "ethnicity_form" in response.context
        assert "gender_form" in response.context
        assert "goutdetail_form" in response.context

    def test__get_permission_object(self):
        """Test that the view's get_permission_object() method returns
        the username kwarg.
        """
        view = PseudopatientCreateView()
        request = self.rf.get("/fake-url/")
        view.request = request
        # Add the username kwarg
        view.kwargs = {"username": self.provider.username}
        assert view.get_permission_object() == self.provider.username

    def test__post_no_user(self):
        """Tests the post() method of the view."""
        # Count the Pseudopatients
        psp_count = Pseudopatient.objects.count()

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
        response = self.client.post(reverse("users:pseudopatient-create"), data=data)
        assert response.status_code == 302

        # Assert that a Pseudopatient was created
        assert Pseudopatient.objects.count() == psp_count + 1
        pseudopatient = Pseudopatient.objects.last()
        assert getattr(pseudopatient, "dateofbirth", None)
        assert pseudopatient.dateofbirth.value == yearsago(data["dateofbirth-value"]).date()
        assert getattr(pseudopatient, "ethnicity", None)
        assert pseudopatient.ethnicity.value == data["ethnicity-value"]
        assert getattr(pseudopatient, "gender", None)
        assert pseudopatient.gender.value == data["gender-value"]
        assert PseudopatientProfile.objects.exists()
        profile = PseudopatientProfile.objects.filter(user=pseudopatient).get()
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
        # Test that the view throws an error if a female between ages 40 and 60 doesn't have menopause data
        data.update({"gender-value": Genders.FEMALE})
        response = self.client.post(reverse("users:pseudopatient-create"), data=data)
        assert response.status_code == 200
        assert response.context[f"{MedHistoryTypes.MENOPAUSE}_form"].errors[f"{MedHistoryTypes.MENOPAUSE}-value"] == [
            _(
                "For females between ages 40 and 60, we need to know the patient's \
menopause status to evaluate their flare."
            )
        ]
        # Test that menopause is created
        data.update({f"{MedHistoryTypes.MENOPAUSE}-value": True})
        response = self.client.post(reverse("users:pseudopatient-create"), data=data)
        assert response.status_code == 302
        assert Pseudopatient.objects.last().menopause

    def test__post_with_provider_no_provider_kwarg(self):
        """Test that the view's post() method creates a Pseudopatient with
        a unique username when called by a logged in Provider but with no provider
        kwarg in the url.
        """
        # Count the Pseudopatients
        psp_count = Pseudopatient.objects.count()

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
        response = self.client.post(reverse("users:pseudopatient-create"), data=data)
        assert response.status_code == 302
        # Assert that a Pseudopatient was created
        assert Pseudopatient.objects.count() == psp_count + 1
        pseudopatient = Pseudopatient.objects.last()
        assert getattr(pseudopatient, "dateofbirth", None)
        assert pseudopatient.dateofbirth.value == yearsago(data["dateofbirth-value"]).date()
        assert getattr(pseudopatient, "ethnicity", None)
        assert pseudopatient.ethnicity.value == data["ethnicity-value"]
        assert getattr(pseudopatient, "gender", None)
        assert pseudopatient.gender.value == data["gender-value"]
        assert PseudopatientProfile.objects.exists()
        profile = PseudopatientProfile.objects.filter(user=pseudopatient).get()
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
        # Count the Pseudopatients
        psp_count = Pseudopatient.objects.count()

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
            reverse("users:provider-pseudopatient-create", kwargs={"username": self.provider.username}), data=data
        )
        assert response.status_code == 302
        # Assert that a Pseudopatient was created
        assert Pseudopatient.objects.count() == psp_count + 1
        pseudopatient = (
            Pseudopatient.objects.select_related("pseudopatientprofile")
            .filter(pseudopatientprofile__provider=self.provider)
            .order_by("created")
            .last()
        )
        assert getattr(pseudopatient, "dateofbirth", None)
        assert pseudopatient.dateofbirth.value == yearsago(data["dateofbirth-value"]).date()
        assert getattr(pseudopatient, "ethnicity", None)
        assert pseudopatient.ethnicity.value == data["ethnicity-value"]
        assert getattr(pseudopatient, "gender", None)
        assert pseudopatient.gender.value == data["gender-value"]
        assert PseudopatientProfile.objects.exists()
        profile = PseudopatientProfile.objects.filter(user=pseudopatient).get()
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
        request = self.rf.get(reverse("users:pseudopatient-create"))
        request.user = self.provider
        SessionMiddleware(dummy_get_response).process_request(request)
        assert view.as_view()(request)

    def test__rules_provider_with_provider_kwarg(self):
        """Test that the view's post() method creates a Pseudopatient with
        a unique username when called by a logged in Provider and with a provider
        kwarg in the url.
        """
        view = PseudopatientCreateView
        kwargs = {"username": self.provider.username}
        request = self.rf.get(reverse("users:provider-pseudopatient-create", kwargs=kwargs))
        request.user = self.provider
        SessionMiddleware(dummy_get_response).process_request(request)
        assert view.as_view()(request, **kwargs)

    def test__rules_provider_provider_kwarg_discrepant_denied(self):
        """Test that the view's post() method raises PermissionDenied
        when called by a logged in User and with a provider
        kwarg in the url that is not the same as the logged in User.
        """
        view = PseudopatientCreateView
        kwargs = {"username": self.patient.username}
        request = self.rf.get(reverse("users:provider-pseudopatient-create", kwargs=kwargs))
        request.user = self.provider
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_admin_no_provider_kwarg(self):
        """Test that the view's post() method creates a Pseudopatient
        with a unique username when no provider kwarg is passed in the url
        by an Admin.
        """
        view = PseudopatientCreateView
        request = self.rf.get(reverse("users:pseudopatient-create"))
        request.user = self.admin
        SessionMiddleware(dummy_get_response).process_request(request)
        assert view.as_view()(request)

    def test__rules_admin_with_provider_kwarg(self):
        """Test that the view's post() method creates a Pseudopatient with
        a unique username when called by a logged in Admin and with a provider
        kwarg in the url.
        """
        view = PseudopatientCreateView
        kwargs = {"username": self.admin.username}
        request = self.rf.post(reverse("users:provider-pseudopatient-create", kwargs=kwargs))
        request.user = self.admin
        SessionMiddleware(dummy_get_response).process_request(request)
        assert view.as_view()(request, **kwargs)

    def test__rules_admin_provider_kwarg_discrepant_denied(self):
        """Test that the view's post() method raises PermissionDenied
        when called by a logged in Admin and with a provider
        kwarg in the url that is not the same as the logged in User.
        """
        view = PseudopatientCreateView
        kwargs = {"username": self.patient.username}
        request = self.rf.get(reverse("users:provider-pseudopatient-create", kwargs=kwargs))
        request.user = self.admin
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_user_not_provider_or_admin_provider_kwarg(self):
        """Test that the view's post() method raises PermissionDenied
        when called by a logged in User who is not a Provider or Admin.
        """
        view = PseudopatientCreateView
        kwargs = {"username": "blahaha"}
        request = self.rf.get(reverse("users:provider-pseudopatient-create", kwargs=kwargs))
        request.user = self.patient
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_pseudopatient(self):
        """Test that the view's post() method raises PermissionDenied
        when called by a logged in Pseudopatient.
        """
        view = PseudopatientCreateView
        request = self.rf.post(reverse("users:pseudopatient-create"))
        request.user = create_psp()
        with pytest.raises(PermissionDenied):
            view.as_view()(request)


class TestPseudopatientDetailView(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.provider = UserFactory()
        self.patient = UserFactory(role=Roles.PATIENT)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.provider_pseudopatient = create_psp()
        self.provider_pseudopatient.profile.provider = self.provider
        self.provider_pseudopatient.profile.save()
        self.admin_pseudopatient = create_psp()
        self.admin_pseudopatient.profile.provider = self.admin
        self.admin_pseudopatient.profile.save()
        self.anon_pseudopatient = create_psp()

    def test__rules_provider_can_see_own_pseudopatient(self):
        """Test that a Provider can see his or her own Pseudopatient's detail."""
        self.client.force_login(self.provider)
        assert self.client.get(
            reverse("users:pseudopatient-detail", kwargs={"username": self.provider_pseudopatient.username})
        )

    def test__rules_provider_cannot_see_admin_pseudopatient(self):
        """Test that a Provider cannot see an Admin's Pseudopatient's detail."""
        self.client.force_login(self.provider)
        response = self.client.get(
            reverse("users:pseudopatient-detail", kwargs={"username": self.admin_pseudopatient.username})
        )
        assert response.status_code == 403

    def test__rules_provider_can_see_anonymous_pseudopatient(self):
        """Test that a Provider can see an Anonymous Pseudopatient's detail."""
        self.client.force_login(self.provider)
        assert self.client.get(
            reverse("users:pseudopatient-detail", kwargs={"username": self.anon_pseudopatient.username})
        )

    def test__rules_admin_can_see_own_pseudopatient(self):
        """Test that an Admin can see his or her own Pseudopatient's detail."""
        self.client.force_login(self.admin)
        assert self.client.get(
            reverse("users:pseudopatient-detail", kwargs={"username": self.admin_pseudopatient.username})
        )

    def test__rules_admin_cannot_see_provider_pseudopatient(self):
        """Test that an Admin cannot see a Provider's Pseudopatient's detail."""
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("users:pseudopatient-detail", kwargs={"username": self.provider_pseudopatient.username})
        )
        assert response.status_code == 403

    def test__rules_anonymous_cannot_see_provider_pseudopatient(self):
        """Test that an Anonymous User cannot see a Provider's Pseudopatient's detail."""
        response = self.client.get(
            reverse("users:pseudopatient-detail", kwargs={"username": self.provider_pseudopatient.username})
        )
        assert response.status_code == 302
        url = reverse("users:pseudopatient-detail", kwargs={"username": self.provider_pseudopatient.username})
        assert response.url == f"/accounts/login/?next={url}"

    def test__rules_admin_can_see_anonymous_pseudopatient(self):
        """Test that an Admin can see an Anonymous Pseudopatient's detail."""
        self.client.force_login(self.admin)
        assert self.client.get(
            reverse("users:pseudopatient-detail", kwargs={"username": self.anon_pseudopatient.username})
        )

    def test__rules_anonymous_can_see_anonymous_pseudopatient(self):
        """Test that an Anonymous User can see an Anonymous Pseudopatient's detail."""
        assert self.client.get(
            reverse("users:pseudopatient-detail", kwargs={"username": self.anon_pseudopatient.username})
        )


class TestPseudopatientListView(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.provider = UserFactory()
        self.provider_pseudopatient = create_psp()
        self.provider_pseudopatient.profile.provider = self.provider
        self.provider_pseudopatient.profile.save()
        self.patient = UserFactory(role=Roles.PATIENT)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.admin_pseudopatient = create_psp()
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
        SessionMiddleware(dummy_get_response).process_request(request)
        assert view.as_view()(request, **kwargs)

    def test__rules_provider_other_provider_list(self):
        """Test that a Provider cannot see another Provider's list."""
        provider2 = UserFactory()
        provider2_pseudopatient = create_psp()
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
        SessionMiddleware(dummy_get_response).process_request(request)
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


class TestPseudopatientUpdateView(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.view = PseudopatientUpdateView
        self.anon = AnonymousUser()
        self.provider = UserFactory()
        self.admin = UserFactory(role=Roles.ADMIN)
        # Create a pseudopatient
        self.psp = create_psp(provider=self.provider)
        self.admin_psp = create_psp(provider=self.admin)
        self.female = create_psp()
        self.female.dateofbirth.value = timezone.now() - timedelta(days=365 * 50)
        self.female.dateofbirth.save()
        self.female.gender.value = Genders.FEMALE
        self.female.gender.save()
        if not self.female.menopause:
            MenopauseFactory(user=self.female)
        delattr(self.female, "menopause")

    def test__dispatch(self):
        """Test that dispatch sets the object attr."""
        view = PseudopatientUpdateView()
        request = self.rf.get("/fake-url/")
        request.user = self.provider
        view.request = request
        SessionMiddleware(dummy_get_response).process_request(request)
        view.kwargs = {"username": self.psp.username}
        view.dispatch(request, **view.kwargs)
        assert view.object == self.psp

    def test__get_permission_object(self):
        """Test that the view's get_permission_object() method returns
        the view's object (intended User)."""
        view = PseudopatientUpdateView()
        request = self.rf.get("/fake-url/")
        request.user = self.provider
        view.request = request
        SessionMiddleware(dummy_get_response).process_request(request)
        view.kwargs = {"username": self.psp.username}
        view.dispatch(request, **view.kwargs)
        assert view.get_permission_object() == self.psp

    def test__get_queryset(self):
        """Test that the view's get_queryset() method returns the intended
        Pseudopatient and the intended related models."""
        view = PseudopatientUpdateView()
        request = self.rf.get("/fake-url/")
        request.user = self.provider
        view.request = request
        view.kwargs = {"username": self.female.username}
        with self.assertNumQueries(2):
            qs = view.get_queryset().get()
            assert qs == self.female
            assert qs.dateofbirth == self.female.dateofbirth
            assert qs.gender == self.female.gender
            assert qs.ethnicity == self.female.ethnicity
            assert qs.pseudopatientprofile == self.female.pseudopatientprofile
            assert hasattr(qs, "medhistorys_qs")
        assert self.female.menopause in qs.medhistorys_qs
        assert self.female.gout in qs.medhistorys_qs
        assert [mh for mh in qs.medhistorys_qs if mh.medhistorytype == MedHistoryTypes.GOUT][
            0
        ].goutdetail == self.female.goutdetail

    def test__view_attrs(self):
        """Test that the view's attrs are correct."""
        view = PseudopatientUpdateView()
        assert view.form_class == PseudopatientForm
        assert view.medhistorys == {
            MedHistoryTypes.GOUT: {"form": GoutForm, "model": Gout},
            MedHistoryTypes.MENOPAUSE: {"form": MenopauseForm, "model": Menopause},
        }
        assert view.onetoones == {
            "dateofbirth": {"form": DateOfBirthForm, "model": DateOfBirth},
            "ethnicity": {"form": EthnicityForm, "model": Ethnicity},
            "gender": {"form": GenderForm, "model": Gender},
        }
        assert view.medhistory_details == {MedHistoryTypes.GOUT: GoutDetailForm}

    def test__get_context_data(self):
        """Tests that the required context data is passed to the template."""
        # Log in the provider
        self.client.force_login(self.provider)
        response = self.client.get(reverse("users:pseudopatient-update", kwargs={"username": self.female.username}))
        assert response.status_code == 200
        assert f"{MedHistoryTypes.GOUT}_form" not in response.context
        assert "dateofbirth_form" in response.context
        assert response.context["dateofbirth_form"].instance == self.female.dateofbirth
        assert "ethnicity_form" in response.context
        assert response.context["ethnicity_form"].instance == self.female.ethnicity
        assert "gender_form" in response.context
        assert response.context["gender_form"].instance == self.female.gender
        assert "goutdetail_form" in response.context
        assert f"{MedHistoryTypes.MENOPAUSE}_form" in response.context
        assert response.context[f"{MedHistoryTypes.MENOPAUSE}_form"].instance == self.female.menopause

    def test__rules(self):
        """Test rules for the PseudopatientUpdateView."""
        # Anonymous User cannot update a Pseudopatient with a provider or a patient
        response = self.client.get(reverse("users:pseudopatient-update", kwargs={"username": self.psp.username}))
        assert response.status_code == 302
        response = self.client.post(
            reverse("users:pseudopatient-update", kwargs={"username": self.admin_psp.username})
        )
        assert response.status_code == 302
        # Provider can log in and update his or her own Pseudopatient
        self.client.force_login(self.provider)
        response = self.client.get(reverse("users:pseudopatient-update", kwargs={"username": self.psp.username}))
        assert response.status_code == 200
        # Provider cannot update another Provider's Pseudopatient
        response = self.client.get(reverse("users:pseudopatient-update", kwargs={"username": self.admin_psp.username}))
        assert response.status_code == 403
        # Admin can log in and update his or her own Pseudopatient
        self.client.force_login(self.admin)
        response = self.client.get(reverse("users:pseudopatient-update", kwargs={"username": self.admin_psp.username}))
        assert response.status_code == 200
        # Admin cannot update another Provider's Pseudopatient
        response = self.client.get(reverse("users:pseudopatient-update", kwargs={"username": self.psp.username}))
        assert response.status_code == 403

    def test__post(self):
        """Test that the post() method updates onetoones and medhistorys/medhistorydetails."""
        psp = create_psp()
        psp.goutdetail.flaring = False
        psp.goutdetail.hyperuricemic = False
        psp.goutdetail.on_ppx = True
        psp.goutdetail.on_ult = True
        psp.goutdetail.save()
        try:
            Menopause.objects.get(user=psp).delete()
        except Menopause.DoesNotExist:
            pass
        data = {
            "dateofbirth-value": 50,
            "gender-value": Genders.FEMALE,
            "ethnicity-value": Ethnicitys.CAUCASIANAMERICAN,
            f"{MedHistoryTypes.GOUT}-value": True,
            "flaring": True,
            "hyperuricemic": True,
            "on_ppx": False,
            "on_ult": False,
        }
        # Test that the view returns a ValidationError when the user is a woman aged 40-60
        # and the menopause form is not filled out
        response = self.client.post(
            reverse("users:pseudopatient-update", kwargs={"username": psp.username}), data=data
        )
        assert response.status_code == 200
        assert response.context[f"{MedHistoryTypes.MENOPAUSE}_form"].errors[f"{MedHistoryTypes.MENOPAUSE}-value"]
        assert response.context[f"{MedHistoryTypes.MENOPAUSE}_form"].errors[f"{MedHistoryTypes.MENOPAUSE}-value"][
            0
        ] == _(
            "For females between ages 40 and 60, we need to know the patient's \
menopause status to evaluate their flare."
        )
        # Update menopause value
        data.update({f"{MedHistoryTypes.MENOPAUSE}-value": True})
        # Test that view runs post() without errors and redirects to the Pseudopatient DetailView
        response = self.client.post(
            reverse("users:pseudopatient-update", kwargs={"username": psp.username}), data=data
        )
        assert response.status_code == 302
        assert response.url == reverse("users:pseudopatient-detail", kwargs={"username": psp.username})
        # Need to delete both gout and goutdetail cached_properties because they are used
        # to fetch one another and will not be updated otherwise
        delattr(psp, "goutdetail")
        delattr(psp, "gout")
        psp.refresh_from_db()
        assert psp.dateofbirth.value == yearsago(data["dateofbirth-value"]).date()
        assert psp.gender.value == data["gender-value"]
        assert psp.ethnicity.value == data["ethnicity-value"]
        assert psp.goutdetail.flaring == data["flaring"]
        assert psp.goutdetail.hyperuricemic == data["hyperuricemic"]
        assert psp.goutdetail.on_ppx == data["on_ppx"]
        assert psp.goutdetail.on_ult == data["on_ult"]
        # Test that menopause was created
        assert psp.menopause
        # Test that menopause can be deleted
        data.update({f"{MedHistoryTypes.MENOPAUSE}-value": False})
        response = self.client.post(
            reverse("users:pseudopatient-update", kwargs={"username": psp.username}), data=data
        )
        assert response.status_code == 302
        assert not Menopause.objects.filter(user=psp).exists()


class TestUserDeleteView(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.provider = UserFactory()
        self.patient = UserFactory(role=Roles.PATIENT)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.provider_pseudopatient = create_psp(provider=self.provider)
        self.admin_pseudopatient = create_psp(provider=self.admin)
        self.anon_pseudopatient = create_psp()

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
        request.user = self.provider
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
        self.client.force_login(self.provider)
        user = auth.get_user(self.client)
        assert user.is_authenticated
        initial_response = self.client.get(
            reverse("users:pseudopatient-delete", kwargs={"username": self.provider_pseudopatient.username})
        )
        assert initial_response.status_code == 200

        confirm_response = self.client.post(
            reverse("users:pseudopatient-delete", kwargs={"username": self.provider_pseudopatient.username})
        )

        assert confirm_response.status_code == 302
        assert confirm_response.url == f"/users/{self.provider.username}/pseudopatients/"

        assert not Pseudopatient.objects.filter(username=self.provider_pseudopatient.username).exists()

    def test__rules_provider_cannot_delete_admins_pseudopatient(self):
        """Test that a Provider cannot delete an Admin's Pseudopatient."""
        view = UserDeleteView
        kwargs = {"username": self.admin_pseudopatient.username}
        request = self.rf.get(reverse("users:pseudopatient-delete", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.provider
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

        request = self.rf.post(reverse("users:pseudopatient-delete", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.provider
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_provider_cannot_delete_anonymous_pseudopatient(self):
        """Test that a Provider cannot delete an Anonymous Pseudopatient."""
        view = UserDeleteView
        kwargs = {"username": self.anon_pseudopatient.username}
        request = self.rf.get(reverse("users:pseudopatient-delete", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.provider
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

        request = self.rf.post(reverse("users:pseudopatient-delete", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.provider
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_admin_can_delete_own_pseudopatient(self):
        """Test that an Admin can delete his or her own Pseudopatient."""
        view = UserDeleteView
        kwargs = {"username": self.admin_pseudopatient.username}
        request = self.rf.get(reverse("users:pseudopatient-delete", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.admin
        assert view.as_view()(request, **kwargs)

        request = self.rf.post(reverse("users:pseudopatient-delete", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.admin
        assert view.as_view()(request, **kwargs)

    def test__rules_admin_cannot_delete_providers_pseudopatient(self):
        """Test that an Admin cannot delete a Provider's Pseudopatient."""
        view = UserDeleteView
        kwargs = {"username": self.provider_pseudopatient.username}
        request = self.rf.get(reverse("users:pseudopatient-delete", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.admin
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

        request = self.rf.post(reverse("users:pseudopatient-delete", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.admin
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_admin_cannot_delete_anonymous_pseudopatient(self):
        """Test that an Admin cannot delete an Anonymous Pseudopatient."""
        view = UserDeleteView
        kwargs = {"username": self.anon_pseudopatient.username}
        request = self.rf.get(reverse("users:pseudopatient-delete", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.admin
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

        request = self.rf.post(reverse("users:pseudopatient-delete", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.admin
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_patient_cannot_delete_provider_pseudopatient(self):
        """Test that a Patient cannot delete a Provider's Pseudopatient."""
        view = UserDeleteView
        kwargs = {"username": self.provider_pseudopatient.username}
        request = self.rf.get(reverse("users:pseudopatient-delete", kwargs=kwargs))
        request.user = self.patient
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

        request = self.rf.post(reverse("users:pseudopatient-delete", kwargs=kwargs))
        request.user = self.patient
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_patient_cannot_delete_admin_pseudopatient(self):
        """Test that a Patient cannot delete an Admin's Pseudopatient."""
        view = UserDeleteView
        kwargs = {"username": self.admin_pseudopatient.username}
        request = self.rf.get(reverse("users:pseudopatient-delete", kwargs=kwargs))
        request.user = self.patient
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

        request = self.rf.post(reverse("users:pseudopatient-delete", kwargs=kwargs))
        request.user = self.patient
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_provider_can_delete_self(self):
        """Test that a Provider can delete his or her own User."""
        view = UserDeleteView

        request = self.rf.get(f"users/{self.provider.username}/")

        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.provider
        assert view.as_view()(request)

        request = self.rf.post(f"users/{self.provider.username}/")

        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.provider
        assert view.as_view()(request)

    def test__rules_admin_can_delete_self(self):
        """Test that an Admin can delete his or her own User."""
        view = UserDeleteView

        request = self.rf.get(f"users/{self.admin.username}/")

        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.admin
        assert view.as_view()(request)

        request = self.rf.post(f"users/{self.admin.username}/")

        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.admin
        assert view.as_view()(request)

    def test__rules_patient_can_delete_self(self):
        """Test that a Patient can delete his or her own User."""
        view = UserDeleteView

        request = self.rf.get(f"users/{self.patient.username}/")

        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.patient
        assert view.as_view()(request)

        request = self.rf.post(f"users/{self.patient.username}/")

        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

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
        self.provider_pseudopatient = create_psp()
        self.provider_pseudopatient.profile.provider = self.provider
        self.provider_pseudopatient.profile.save()
        self.admin_pseudopatient = create_psp()
        self.admin_pseudopatient.profile.provider = self.admin
        self.admin_pseudopatient.profile.save()
        self.anon_pseudopatient = create_psp()

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
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)
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
        self.provider_pseudopatient = create_psp(provider=self.provider)
        self.admin_pseudopatient = create_psp(provider=self.admin)
        self.anon_pseudopatient = create_psp()

    def test_authenticated(self):
        request = self.rf.get(f"users/{self.provider.username}/")
        request.user = self.provider
        response = user_detail_view(request, username=self.provider.username)

        assert response.status_code == 200

    def test__get(self):
        """Test that the view redirects to pseudopatient-detail when the
        User is a Pseudopatient.
        """
        view = user_detail_view
        kwargs = {"username": self.provider_pseudopatient.username}
        request = self.rf.get(reverse("users:detail", kwargs=kwargs))
        request.user = self.provider_pseudopatient
        response = view(request, **kwargs)
        assert response.status_code == 302
        assert response.url == reverse("users:pseudopatient-detail", kwargs=kwargs)

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

    def test__rules_provider_cannot_see_admin(self):
        """Test that a Provider cannot see an Admin's detail."""
        view = user_detail_view
        kwargs = {"username": self.admin.username}
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
