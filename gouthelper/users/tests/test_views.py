from datetime import timedelta
from urllib.parse import unquote

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
from ...dateofbirths.helpers import age_calc, yearsago
from ...ethnicitys.choices import Ethnicitys
from ...ethnicitys.forms import EthnicityForm
from ...genders.choices import Genders
from ...genders.forms import GenderForm
from ...medhistorydetails.forms import GoutDetailForm
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.forms import GoutForm, MenopauseForm
from ...medhistorys.models import Menopause
from ...medhistorys.tests.factories import MenopauseFactory
from ...profiles.models import PatientProfile
from ...utils.forms import forms_print_response_errors
from ...utils.test_helpers import dummy_get_response
from ..choices import Roles
from ..forms import PatientForm, UserAdminChangeForm
from ..models import Patient, User
from ..views import (
    PatientCreateView,
    PatientDeleteView,
    PatientListView,
    PatientUpdateView,
    UserDeleteView,
    UserRedirectView,
    UserUpdateView,
    user_detail_view,
)
from .factories import UserFactory, create_psp
from .factories_data import patient_form_data_factory

pytestmark = pytest.mark.django_db


class TestPatientCreateView(TestCase):
    """Tests for the PatientCreateView, which is actually a View
    with a post method, not a CreateView.
    """

    def setUp(self):
        self.rf = RequestFactory()
        self.provider = UserFactory()
        self.patient = UserFactory(role=Roles.PATIENT)
        self.admin = UserFactory(role=Roles.ADMIN)

    def test__view_attrs(self):
        """Test that the view's attrs are correct."""
        view = PatientCreateView()
        view.set_forms()
        assert view.model == Patient
        assert view.form_class == PatientForm
        assert view.MEDHISTORY_FORMS == {
            MedHistoryTypes.GOUT: GoutForm,
            MedHistoryTypes.MENOPAUSE: MenopauseForm,
        }
        assert view.medhistory_forms == {
            MedHistoryTypes.GOUT: GoutForm,
            MedHistoryTypes.MENOPAUSE: MenopauseForm,
        }
        assert view.OTO_FORMS == {
            "dateofbirth": DateOfBirthForm,
            "ethnicity": EthnicityForm,
            "gender": GenderForm,
        }
        assert view.oto_forms == {
            "dateofbirth": DateOfBirthForm,
            "ethnicity": EthnicityForm,
            "gender": GenderForm,
        }
        assert view.MEDHISTORY_DETAIL_FORMS == {"goutdetail": GoutDetailForm}
        assert view.medhistory_detail_forms == {"goutdetail": GoutDetailForm}

    def test__get_context_data(self):
        """Tests that the required context data is passed to the template."""
        response = self.client.get(reverse("users:patient-create"))
        assert response.status_code == 200
        assert "dateofbirth_form" in response.context
        assert "ethnicity_form" in response.context
        assert "gender_form" in response.context
        assert "goutdetail_form" in response.context

    def test__get_permission_object(self):
        """Test that the view's get_permission_object() method returns
        the username kwarg.
        """
        view = PatientCreateView()
        request = self.rf.get("/fake-url/")
        view.request = request
        # Add the username kwarg
        view.kwargs = {"username": self.provider.username}
        assert view.get_permission_object() == self.provider.username

    def test__post_no_user(self):
        """Tests the post() method of the view."""
        # Count the Patients
        psp_count = Patient.objects.count()

        data = {
            "dateofbirth-value": 50,
            "ethnicity-value": Ethnicitys.CAUCASIANAMERICAN,
            "gender-value": Genders.MALE,
            f"{MedHistoryTypes.GOUT}-value": True,
            "flaring": True,
            "at_goal": True,
            "at_goal_long_term": False,
            "on_ppx": False,
            "on_ult": True,
            "starting_ult": False,
        }
        response = self.client.post(reverse("users:patient-create"), data=data)
        assert response.status_code == 302

        # Assert that a Patient was created
        assert Patient.objects.count() == psp_count + 1
        patient = Patient.objects.last()
        assert getattr(patient, "dateofbirth", None)
        assert patient.dateofbirth.value == yearsago(data["dateofbirth-value"]).date()
        assert getattr(patient, "ethnicity", None)
        assert patient.ethnicity.value == data["ethnicity-value"]
        assert getattr(patient, "gender", None)
        assert patient.gender.value == data["gender-value"]
        assert PatientProfile.objects.exists()
        profile = PatientProfile.objects.filter(user=patient).get()
        assert profile.user == patient
        assert profile.provider is None
        assert patient.medhistory_set.count() == 1
        gout = patient.medhistory_set.get()
        assert getattr(gout, "goutdetail", None)
        assert gout.goutdetail.flaring == data["flaring"]
        assert gout.goutdetail.at_goal == data["at_goal"]
        assert gout.goutdetail.on_ppx == data["on_ppx"]
        assert gout.goutdetail.on_ult == data["on_ult"]
        # Assert that the Patient history was set correctly to track the creating User
        assert User.history.filter(username=patient.username).first().history_user is None
        # Test that the view throws an error if a female between ages 40 and 60 doesn't have menopause data
        data.update({"gender-value": Genders.FEMALE})
        response = self.client.post(reverse("users:patient-create"), data=data)
        forms_print_response_errors(response)
        assert response.status_code == 200
        assert response.context[f"{MedHistoryTypes.MENOPAUSE}_form"].errors[f"{MedHistoryTypes.MENOPAUSE}-value"] == [
            _(
                "For females between ages 40 and 60, we need to know the patient's \
menopause status to evaluate their flare."
            )
        ]
        # Test that menopause is created
        data.update({f"{MedHistoryTypes.MENOPAUSE}-value": True})
        response = self.client.post(reverse("users:patient-create"), data=data)
        assert response.status_code == 302
        assert Patient.objects.order_by("created").last().menopause

    def test__post_with_provider_no_provider_kwarg(self):
        """Test that the view's post() method creates a Patient with
        a unique username when called by a logged in Provider but with no provider
        kwarg in the url.
        """
        # Count the Patients
        psp_count = Patient.objects.count()

        # Log in the provider
        self.client.force_login(self.provider)
        data = {
            "dateofbirth-value": 50,
            "ethnicity-value": Ethnicitys.CAUCASIANAMERICAN,
            "gender-value": Genders.MALE,
            f"{MedHistoryTypes.GOUT}-value": True,
            "flaring": True,
            "at_goal": True,
            "at_goal_long_term": False,
            "on_ppx": False,
            "on_ult": False,
            "starting_ult": False,
        }
        response = self.client.post(reverse("users:patient-create"), data=data)
        assert response.status_code == 302
        # Assert that a Patient was created
        assert Patient.objects.count() == psp_count + 1
        patient = Patient.objects.last()
        assert getattr(patient, "dateofbirth", None)
        assert patient.dateofbirth.value == yearsago(data["dateofbirth-value"]).date()
        assert getattr(patient, "ethnicity", None)
        assert patient.ethnicity.value == data["ethnicity-value"]
        assert getattr(patient, "gender", None)
        assert patient.gender.value == data["gender-value"]
        assert PatientProfile.objects.exists()
        profile = PatientProfile.objects.filter(user=patient).get()
        assert profile.user == patient
        assert profile.provider is None
        assert patient.medhistory_set.count() == 1
        gout = patient.medhistory_set.get()
        assert getattr(gout, "goutdetail", None)
        assert gout.goutdetail.flaring == data["flaring"]
        assert gout.goutdetail.at_goal == data["at_goal"]
        assert gout.goutdetail.on_ppx == data["on_ppx"]
        assert gout.goutdetail.on_ult == data["on_ult"]
        # Assert that the Patient history was set correctly to track the creating User
        assert User.history.filter(username=patient.username).first().history_user == self.provider

    def test__post_with_provider_and_provider_kwarg(self):
        """Test that the view's post() method creates a Patient with
        a unique username when called by a logged in User and with a provider
        kwarg in the url.
        """
        # Count the Patients
        psp_count = Patient.objects.count()

        # Log in the provider
        self.client.force_login(self.provider)
        data = {
            "dateofbirth-value": 50,
            "ethnicity-value": Ethnicitys.CAUCASIANAMERICAN,
            "gender-value": Genders.MALE,
            f"{MedHistoryTypes.GOUT}-value": True,
            "flaring": True,
            "at_goal": True,
            "at_goal_long_term": True,
            "on_ppx": False,
            "on_ult": True,
            "starting_ult": True,
        }
        response = self.client.post(
            reverse("users:provider-patient-create", kwargs={"username": self.provider.username}), data=data
        )
        assert response.status_code == 302
        # Assert that a Patient was created
        assert Patient.objects.count() == psp_count + 1
        patient = (
            Patient.objects.select_related("pseudopatientprofile")
            .filter(patientprofile__provider=self.provider)
            .order_by("created")
            .last()
        )
        assert getattr(patient, "dateofbirth", None)
        assert patient.dateofbirth.value == yearsago(data["dateofbirth-value"]).date()
        assert getattr(patient, "ethnicity", None)
        assert patient.ethnicity.value == data["ethnicity-value"]
        assert getattr(patient, "gender", None)
        assert patient.gender.value == data["gender-value"]
        assert PatientProfile.objects.exists()
        profile = PatientProfile.objects.filter(user=patient).get()
        assert profile.user == patient
        # Need to check or id, not equivalence because of proxy model status (i.e. User vs Provider)
        assert profile.provider.id == self.provider.id
        assert patient.medhistory_set.count() == 1
        gout = patient.medhistory_set.get()
        assert getattr(gout, "goutdetail", None)
        assert gout.goutdetail.flaring == data["flaring"]
        assert gout.goutdetail.at_goal == data["at_goal"]
        assert gout.goutdetail.on_ppx == data["on_ppx"]
        assert gout.goutdetail.on_ult == data["on_ult"]
        # Assert that the Patient history was set correctly to track the creating User
        assert User.history.filter(username=patient.username).first().history_user == self.provider

    def test__rules_provider_no_provider_kwarg(self):
        """Test that the view's post() method creates a Patient
        with a unique username when no provider kwarg is passed in the url
        by a provider.
        """
        view = PatientCreateView
        request = self.rf.get(reverse("users:patient-create"))
        request.user = self.provider
        SessionMiddleware(dummy_get_response).process_request(request)
        assert view.as_view()(request)

    def test__rules_provider_with_provider_kwarg(self):
        """Test that the view's post() method creates a Patient with
        a unique username when called by a logged in Provider and with a provider
        kwarg in the url.
        """
        view = PatientCreateView
        kwargs = {"username": self.provider.username}
        request = self.rf.get(reverse("users:provider-patient-create", kwargs=kwargs))
        request.user = self.provider
        SessionMiddleware(dummy_get_response).process_request(request)
        assert view.as_view()(request, **kwargs)

    def test__rules_provider_provider_kwarg_discrepant_denied(self):
        """Test that the view's post() method raises PermissionDenied
        when called by a logged in User and with a provider
        kwarg in the url that is not the same as the logged in User.
        """
        view = PatientCreateView
        kwargs = {"username": self.patient.username}
        request = self.rf.get(reverse("users:provider-patient-create", kwargs=kwargs))
        request.user = self.provider
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_admin_no_provider_kwarg(self):
        """Test that the view's post() method creates a Patient
        with a unique username when no provider kwarg is passed in the url
        by an Admin.
        """
        view = PatientCreateView
        request = self.rf.get(reverse("users:patient-create"))
        request.user = self.admin
        SessionMiddleware(dummy_get_response).process_request(request)
        assert view.as_view()(request)

    def test__rules_admin_with_provider_kwarg(self):
        """Test that the view's post() method creates a Patient with
        a unique username when called by a logged in Admin and with a provider
        kwarg in the url.
        """
        view = PatientCreateView
        kwargs = {"username": self.admin.username}
        request = self.rf.post(
            reverse("users:provider-patient-create", kwargs=kwargs),
            data=patient_form_data_factory(),
        )
        request.user = self.admin
        SessionMiddleware(dummy_get_response).process_request(request)
        assert view.as_view()(request, **kwargs)

    def test__rules_admin_provider_kwarg_discrepant_denied(self):
        """Test that the view's post() method raises PermissionDenied
        when called by a logged in Admin and with a provider
        kwarg in the url that is not the same as the logged in User.
        """
        view = PatientCreateView
        kwargs = {"username": self.patient.username}
        request = self.rf.get(reverse("users:provider-patient-create", kwargs=kwargs))
        request.user = self.admin
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_user_not_provider_or_admin_provider_kwarg(self):
        """Test that the view's post() method raises PermissionDenied
        when called by a logged in User who is not a Provider or Admin.
        """
        view = PatientCreateView
        kwargs = {"username": "blahaha"}
        request = self.rf.get(reverse("users:provider-patient-create", kwargs=kwargs))
        request.user = self.patient
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_patient(self):
        """Test that the view's post() method raises PermissionDenied
        when called by a logged in Patient.
        """
        view = PatientCreateView
        request = self.rf.post(reverse("users:patient-create"))
        request.user = create_psp()
        with pytest.raises(PermissionDenied):
            view.as_view()(request)

    def test__creates_patient_alias(self):
        patient = create_psp()
        for x in range(3):
            create_psp(
                provider=self.provider,
                dateofbirth=patient.dateofbirth.value,
                gender=Genders(patient.gender.value),
            )
        assert Patient.objects.filter(patientprofile__provider=self.provider).count() == 3
        last_patient_before_create = (
            Patient.objects.filter(patientprofile__provider=self.provider).order_by("created").last()
        )
        self.client.force_login(self.provider)
        patient_form_data_factory()
        data = {
            "dateofbirth-value": age_calc(patient.dateofbirth.value),
            "ethnicity-value": Ethnicitys.CAUCASIANAMERICAN,
            "gender-value": Genders(patient.gender.value),
            f"{MedHistoryTypes.GOUT}-value": True,
            "flaring": True,
            "at_goal": True,
            "at_goal_long_term": True,
            "on_ppx": False,
            "on_ult": True,
            "starting_ult": True,
        }
        if (
            patient.gender.value
            and age_calc(patient.dateofbirth.value) >= 40
            and age_calc(patient.dateofbirth.value) < 60
        ):
            data.update({f"{MedHistoryTypes.MENOPAUSE}-value": True if not patient.menopause else False})
        response = self.client.post(
            reverse("users:provider-patient-create", kwargs={"username": self.provider.username}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302
        assert Patient.objects.filter(patientprofile__provider=self.provider).count() == 4
        newest_patient = Patient.objects.filter(patientprofile__provider=self.provider).order_by("created").last()
        assert newest_patient != last_patient_before_create
        self.assertTrue(newest_patient.profile.provider_alias)
        self.assertEqual(newest_patient.profile.provider_alias, 4)


class TestPatientDetailView(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.provider = UserFactory()
        self.patient = UserFactory(role=Roles.PATIENT)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.provider_patient = create_psp(provider=self.provider)
        self.admin_patient = create_psp(provider=self.admin)
        self.anon_patient = create_psp()

    def test__rules_provider_can_see_own_patient(self):
        """Test that a Provider can see his or her own Patient's detail."""
        self.client.force_login(self.provider)
        assert self.client.get(reverse("users:patient-detail", kwargs={"patient": self.provider_patient.pk}))

    def test__rules_provider_cannot_see_admin_patient(self):
        """Test that a Provider cannot see an Admin's Patient's detail."""
        self.client.force_login(self.provider)
        response = self.client.get(reverse("users:patient-detail", kwargs={"patient": self.admin_patient.pk}))
        assert response.status_code == 403

    def test__rules_provider_can_see_anonymous_patient(self):
        """Test that a Provider can see an Anonymous Patient's detail."""
        self.client.force_login(self.provider)
        assert self.client.get(reverse("users:patient-detail", kwargs={"patient": self.anon_patient.pk}))

    def test__rules_admin_can_see_own_patient(self):
        """Test that an Admin can see his or her own Patient's detail."""
        self.client.force_login(self.admin)
        assert self.client.get(reverse("users:patient-detail", kwargs={"patient": self.admin_patient.pk}))

    def test__rules_admin_cannot_see_provider_patient(self):
        """Test that an Admin cannot see a Provider's Patient's detail."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("users:patient-detail", kwargs={"patient": self.provider_patient.pk}))
        assert response.status_code == 403

    def test__rules_anonymous_cannot_see_provider_patient(self):
        """Test that an Anonymous User cannot see a Provider's Patient's detail."""
        response = self.client.get(reverse("users:patient-detail", kwargs={"patient": self.provider_patient.pk}))
        assert response.status_code == 302
        url = reverse("users:patient-detail", kwargs={"patient": self.provider_patient.pk})
        assert unquote(response.url) == f"/accounts/login/?next={url}"

    def test__rules_admin_can_see_anonymous_patient(self):
        """Test that an Admin can see an Anonymous Patient's detail."""
        self.client.force_login(self.admin)
        assert self.client.get(reverse("users:patient-detail", kwargs={"patient": self.anon_patient.pk}))

    def test__rules_anonymous_can_see_anonymous_patient(self):
        """Test that an Anonymous User can see an Anonymous Patient's detail."""
        assert self.client.get(reverse("users:patient-detail", kwargs={"patient": self.anon_patient.pk}))


class TestPatientListView(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.provider = UserFactory()
        self.provider_patient = create_psp()
        self.provider_patient.profile.provider = self.provider
        self.provider_patient.profile.save()
        self.patient = UserFactory(role=Roles.PATIENT)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.admin_patient = create_psp()
        self.admin_patient.profile.provider = self.admin
        self.admin_patient.profile.save()

    def test__get_permission_object(self):
        """Test that the view's get_permission_object() method returns
        the username kwarg.
        """
        view = PatientListView()
        request = self.rf.get("/fake-url/")
        request.user = self.provider
        view.request = request
        view.kwargs = {"username": self.provider.username}
        assert view.get_permission_object() == self.provider.username

    def test__get_queryset(self):
        """Test that the view's get_queryset() method returns a queryset
        of Patients whose provider is the requesting User.
        """
        view = PatientListView()
        kwargs = {"username": self.provider.username}
        request = self.rf.get(reverse("users:patients", kwargs=kwargs))
        request.user = self.provider
        view.request = request
        view.kwargs = kwargs
        assert list(view.get_queryset()) == [self.provider_patient]

    def test__rules_providers_own_list(self):
        """Test that a Provider can see his or her own list."""
        view = PatientListView
        kwargs = {"username": self.provider.username}
        request = self.rf.get(reverse("users:patients", kwargs=kwargs))
        request.user = self.provider
        SessionMiddleware(dummy_get_response).process_request(request)
        assert view.as_view()(request, **kwargs)

    def test__rules_provider_other_provider_list(self):
        """Test that a Provider cannot see another Provider's list."""
        provider2 = UserFactory()
        provider2_patient = create_psp()
        provider2_patient.profile.provider = provider2
        provider2_patient.profile.save()
        view = PatientListView
        kwargs = {"username": provider2.username}
        request = self.rf.get(reverse("users:patients", kwargs=kwargs))
        request.user = self.provider
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def tes__rules_provider_cannot_see_admin_list(self):
        """Test that a Provider cannot see an Admin's list."""
        view = PatientListView
        kwargs = {"username": self.admin.username}
        request = self.rf.get(reverse("users:patients", kwargs=kwargs))
        request.user = self.provider
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_admin_can_see_own_list(self):
        """Test that an Admin can see his or her own list."""
        view = PatientListView
        kwargs = {"username": self.admin.username}
        request = self.rf.get(reverse("users:patients", kwargs=kwargs))
        request.user = self.admin
        SessionMiddleware(dummy_get_response).process_request(request)
        assert view.as_view()(request, **kwargs)

    def test__rules_admin_cannot_see_providers_list(self):
        """Test that an Admin cannot see a Provider's list."""
        view = PatientListView
        kwargs = {"username": self.provider.username}
        request = self.rf.get(reverse("users:patients", kwargs=kwargs))
        request.user = self.admin
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_patient_cannot_see_provider_list(self):
        """Test that a Patient cannot see either list."""
        view = PatientListView
        kwargs = {"username": self.provider.username}
        request = self.rf.get(reverse("users:patients", kwargs=kwargs))
        request.user = self.patient
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_patient_cannot_see_admin_list(self):
        """Test that a Patient cannot see either list."""
        view = PatientListView
        kwargs = {"username": self.admin.username}
        request = self.rf.get(reverse("users:patients", kwargs=kwargs))
        request.user = self.patient
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)


class TestPatientUpdateView(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.view = PatientUpdateView
        self.anon = AnonymousUser()
        self.provider = UserFactory()
        self.admin = UserFactory(role=Roles.ADMIN)
        # Create a patient
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
        view = PatientUpdateView()
        request = self.rf.get("/fake-url/")
        request.user = self.provider
        view.request = request
        SessionMiddleware(dummy_get_response).process_request(request)
        view.kwargs = {"patient": self.psp.pk}
        view.dispatch(request, **view.kwargs)
        assert view.object == self.psp

    def test__get_permission_object(self):
        """Test that the view's get_permission_object() method returns
        the view's object (intended User)."""
        view = PatientUpdateView()
        request = self.rf.get("/fake-url/")
        request.user = self.provider
        view.request = request
        SessionMiddleware(dummy_get_response).process_request(request)
        view.kwargs = {"patient": self.psp.pk}
        view.dispatch(request, **view.kwargs)
        assert view.get_permission_object() == self.psp

    def test__get_queryset(self):
        """Test that the view's get_queryset() method returns the intended
        Patient and the intended related models."""
        view = PatientUpdateView()
        request = self.rf.get("/fake-url/")
        request.user = self.provider
        view.request = request
        view.kwargs = {"patient": self.female.pk}
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
        view = PatientUpdateView()
        view.set_forms()
        assert view.form_class == PatientForm
        assert view.MEDHISTORY_FORMS == {
            MedHistoryTypes.GOUT: GoutForm,
            MedHistoryTypes.MENOPAUSE: MenopauseForm,
        }
        assert view.medhistory_forms == {
            MedHistoryTypes.GOUT: GoutForm,
            MedHistoryTypes.MENOPAUSE: MenopauseForm,
        }
        assert view.OTO_FORMS == {
            "dateofbirth": DateOfBirthForm,
            "ethnicity": EthnicityForm,
            "gender": GenderForm,
        }
        assert view.oto_forms == {
            "dateofbirth": DateOfBirthForm,
            "ethnicity": EthnicityForm,
            "gender": GenderForm,
        }
        assert view.MEDHISTORY_DETAIL_FORMS == {"goutdetail": GoutDetailForm}
        assert view.medhistory_detail_forms == {"goutdetail": GoutDetailForm}

    def test__get_context_data(self):
        """Tests that the required context data is passed to the template."""
        # Log in the provider
        self.client.force_login(self.provider)
        response = self.client.get(reverse("users:patient-update", kwargs={"patient": self.female.pk}))
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
        """Test rules for the PatientUpdateView."""
        # Anonymous User cannot update a Patient with a provider or a patient
        response = self.client.get(reverse("users:patient-update", kwargs={"patient": self.psp.pk}))
        assert response.status_code == 302
        response = self.client.post(reverse("users:patient-update", kwargs={"patient": self.admin_psp.pk}))
        assert response.status_code == 302
        # Provider can log in and update his or her own Patient
        self.client.force_login(self.provider)
        response = self.client.get(reverse("users:patient-update", kwargs={"patient": self.psp.pk}))
        assert response.status_code == 200
        # Provider cannot update another Provider's Patient
        response = self.client.get(reverse("users:patient-update", kwargs={"patient": self.admin_psp.pk}))
        assert response.status_code == 403
        # Admin can log in and update his or her own Patient
        self.client.force_login(self.admin)
        response = self.client.get(reverse("users:patient-update", kwargs={"patient": self.admin_psp.pk}))
        assert response.status_code == 200
        # Admin cannot update another Provider's Patient
        response = self.client.get(reverse("users:patient-update", kwargs={"patient": self.psp.pk}))
        assert response.status_code == 403

    def test__post(self):
        """Test that the post() method updates onetoones and medhistorys/medhistorydetails."""
        psp = create_psp()
        psp.goutdetail.flaring = False
        psp.goutdetail.at_goal = False
        psp.goutdetail.at_goal_long_term = False
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
            "at_goal": True,
            "at_goal_long_term": False,
            "on_ppx": False,
            "on_ult": False,
            "starting_ult": False,
        }
        # Test that the view returns a ValidationError when the user is a woman aged 40-60
        # and the menopause form is not filled out
        response = self.client.post(reverse("users:patient-update", kwargs={"patient": psp.pk}), data=data)
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
        # Test that view runs post() without errors and redirects to the Patient DetailView
        response = self.client.post(reverse("users:patient-update", kwargs={"patient": psp.pk}), data=data)
        assert response.status_code == 302
        assert response.url == reverse("users:patient-detail", kwargs={"patient": psp.pk}) + "?updated=True"
        # Need to delete both gout and goutdetail cached_properties because they are used
        # to fetch one another and will not be updated otherwise
        delattr(psp, "goutdetail")
        delattr(psp, "gout")
        psp.refresh_from_db()
        assert psp.dateofbirth.value == yearsago(data["dateofbirth-value"]).date()
        assert psp.gender.value == data["gender-value"]
        assert psp.ethnicity.value == data["ethnicity-value"]
        assert psp.goutdetail.flaring == data["flaring"]
        assert psp.goutdetail.at_goal == data["at_goal"]
        assert psp.goutdetail.on_ppx == data["on_ppx"]
        assert psp.goutdetail.on_ult == data["on_ult"]
        # Test that menopause was created
        assert psp.menopause
        # Test that menopause can be deleted
        data.update({f"{MedHistoryTypes.MENOPAUSE}-value": False})
        response = self.client.post(reverse("users:patient-update", kwargs={"patient": psp.pk}), data=data)
        assert response.status_code == 302
        assert not Menopause.objects.filter(user=psp).exists()


class TestPatientDeleteView(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.provider = UserFactory()
        self.patient = UserFactory(role=Roles.PATIENT)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.provider_patient = create_psp(provider=self.provider)
        self.admin_patient = create_psp(provider=self.admin)
        self.anon_patient = create_psp()

    def test__get_success_message(self):
        view = PatientDeleteView()
        request = self.rf.get("/fake-url/")
        view.request = request
        view.object = self.provider_patient
        assert view.get_success_message(cleaned_data={}) == _("GoutPatient successfully deleted")

    def test__get_success_url(self):
        view = PatientDeleteView()
        request = self.rf.get("/fake-url/")
        view.request = request
        request.user = self.provider
        view.object = self.provider_patient
        assert view.get_success_url() == reverse("users:patients", kwargs={"username": self.provider.username})

    def test__get_object(self):
        view = PatientDeleteView()
        request = self.rf.get("/fake-url/")
        request.user = self.provider
        view.request = request
        view.kwargs = {"patient": self.provider_patient.pk}
        assert view.get_object() == self.provider_patient

    def test__rules_provider_can_delete_own_patient(self):
        """Test that a Provider can delete his or her own Patient."""
        self.client.force_login(self.provider)
        user = auth.get_user(self.client)
        assert user.is_authenticated
        initial_response = self.client.get(
            reverse("users:patient-delete", kwargs={"patient": self.provider_patient.pk})
        )
        assert initial_response.status_code == 200

        confirm_response = self.client.post(
            reverse("users:patient-delete", kwargs={"patient": self.provider_patient.pk})
        )

        assert confirm_response.status_code == 302
        assert confirm_response.url == f"/users/{self.provider.username}/patients/"

        assert not Patient.objects.filter(pk=self.provider_patient.pk).exists()

    def test__rules_provider_cannot_delete_admins_patient(self):
        """Test that a Provider cannot delete an Admin's Patient."""
        view = PatientDeleteView
        kwargs = {"patient": self.admin_patient.pk}
        request = self.rf.get(reverse("users:patient-delete", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.provider
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

        request = self.rf.post(reverse("users:patient-delete", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.provider
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_provider_cannot_delete_anonymous_patient(self):
        """Test that a Provider cannot delete an Anonymous Patient."""
        view = PatientDeleteView
        kwargs = {"patient": self.anon_patient.pk}
        request = self.rf.get(reverse("users:patient-delete", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.provider
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

        request = self.rf.post(reverse("users:patient-delete", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.provider
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_admin_can_delete_own_patient(self):
        """Test that an Admin can delete his or her own Patient."""
        view = PatientDeleteView
        kwargs = {"patient": self.admin_patient.pk}
        request = self.rf.get(reverse("users:patient-delete", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.admin
        assert view.as_view()(request, **kwargs)

        request = self.rf.post(reverse("users:patient-delete", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.admin
        assert view.as_view()(request, **kwargs)

    def test__rules_admin_cannot_delete_providers_patient(self):
        """Test that an Admin cannot delete a Provider's Patient."""
        view = PatientDeleteView
        kwargs = {"patient": self.provider_patient.pk}
        request = self.rf.get(reverse("users:patient-delete", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.admin
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

        request = self.rf.post(reverse("users:patient-delete", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.admin
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_admin_cannot_delete_anonymous_patient(self):
        """Test that an Admin cannot delete an Anonymous Patient."""
        view = PatientDeleteView
        kwargs = {"patient": self.anon_patient.pk}
        request = self.rf.get(reverse("users:patient-delete", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.admin
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

        request = self.rf.post(reverse("users:patient-delete", kwargs=kwargs))

        # Add the session/message middleware to the request
        SessionMiddleware(dummy_get_response).process_request(request)
        MessageMiddleware(dummy_get_response).process_request(request)

        request.user = self.admin
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_patient_cannot_delete_provider_patient(self):
        """Test that a Patient cannot delete a Provider's Patient."""
        view = PatientDeleteView
        kwargs = {"patient": self.provider_patient.pk}
        request = self.rf.get(reverse("users:patient-delete", kwargs=kwargs))
        request.user = self.patient
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

        request = self.rf.post(reverse("users:patient-delete", kwargs=kwargs))
        request.user = self.patient
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

    def test__rules_patient_cannot_delete_admin_patient(self):
        """Test that a Patient cannot delete an Admin's Patient."""
        view = PatientDeleteView
        kwargs = {"patient": self.admin_patient.pk}
        request = self.rf.get(reverse("users:patient-delete", kwargs=kwargs))
        request.user = self.patient
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

        request = self.rf.post(reverse("users:patient-delete", kwargs=kwargs))
        request.user = self.patient
        with pytest.raises(PermissionDenied):
            view.as_view()(request, **kwargs)

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


class TestUserDeleteView(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.provider = UserFactory()
        self.patient = UserFactory(role=Roles.PATIENT)
        self.admin = UserFactory(role=Roles.ADMIN)

    def test__get_success_message(self):
        view = UserDeleteView()
        view.object = self.provider
        request = self.rf.get("/fake-url/")
        view.request = request
        assert view.get_success_message(cleaned_data={}) == _("Account successfully deleted")

    def test__get_success_url(self):
        view = UserDeleteView()
        view.object = self.provider
        request = self.rf.get("/fake-url/")
        request.user = self.provider
        view.request = request
        assert view.get_success_url() == reverse("contents:home")

    def test__get_object(self):
        view = UserDeleteView()
        request = self.rf.get("/fake-url/")
        request.user = self.provider
        view.request = request
        view.kwargs = {}
        assert view.get_object() == self.provider

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
        self.provider_patient = create_psp()
        self.provider_patient.profile.provider = self.provider
        self.provider_patient.profile.save()
        self.admin_patient = create_psp()
        self.admin_patient.profile.provider = self.admin
        self.admin_patient.profile.save()
        self.anon_patient = create_psp()

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
        assert view.get_redirect_url() == f"/users/{user.username}/patients/"


class TestUserDetailView(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.provider = UserFactory()
        self.patient = UserFactory(role=Roles.PATIENT)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.provider_patient = create_psp(provider=self.provider)
        self.admin_patient = create_psp(provider=self.admin)
        self.anon_patient = create_psp()

    def test_authenticated(self):
        request = self.rf.get(f"users/{self.provider.username}/")
        request.user = self.provider
        response = user_detail_view(request, username=self.provider.username)

        assert response.status_code == 200

    def test__get(self):
        """Test that the view redirects to patient-detail when the
        User is a Patient.
        """
        view = user_detail_view
        kwargs = {"username": self.provider_patient.username}
        request = self.rf.get(reverse("users:detail", kwargs=kwargs))
        request.user = self.provider_patient
        response = view(request, **kwargs)
        assert response.status_code == 302
        assert response.url == reverse("users:patient-detail", kwargs={"patient": self.provider_patient.pk})

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
