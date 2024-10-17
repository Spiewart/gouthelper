import uuid
from datetime import timedelta
from decimal import Decimal
from urllib.parse import quote

import pytest  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from django.contrib.auth.models import AnonymousUser  # type: ignore
from django.contrib.sessions.middleware import SessionMiddleware  # type: ignore
from django.core.exceptions import ObjectDoesNotExist  # type: ignore
from django.db import connection  # type: ignore
from django.db.models import Q, QuerySet  # type: ignore
from django.http import Http404  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils import timezone  # type: ignore

from ...akis.choices import Statuses
from ...akis.models import Aki
from ...contents.models import Content
from ...dateofbirths.forms import DateOfBirthForm
from ...dateofbirths.helpers import age_calc
from ...dateofbirths.models import DateOfBirth
from ...genders.choices import Genders
from ...genders.forms import GenderForm
from ...genders.models import Gender
from ...genders.tests.factories import GenderFactory
from ...labs.forms import UrateFlareForm
from ...labs.models import Urate
from ...labs.tests.factories import CreatinineFactory, UrateFactory
from ...medhistorydetails.choices import DialysisChoices, DialysisDurations, Stages
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.forms import AnginaForm, CadForm, ChfForm, CkdForm, GoutForm, HeartattackForm, PvdForm, StrokeForm
from ...medhistorys.lists import FLARE_MEDHISTORYS, FLAREAID_MEDHISTORYS
from ...medhistorys.models import Angina, MedHistory, Menopause
from ...users.models import Pseudopatient
from ...users.tests.factories import AdminFactory, UserFactory, create_psp
from ...utils.factories import medhistory_diff_obj_data, oto_random_age, oto_random_gender, oto_random_urate_or_None
from ...utils.forms import forms_print_response_errors
from ...utils.test_helpers import dummy_get_response
from ..choices import DiagnosedChoices, Likelihoods, LimitedJointChoices, Prevalences
from ..models import Flare
from ..selectors import flares_user_qs
from ..views import (
    FlareAbout,
    FlareCreate,
    FlareDetail,
    FlarePseudopatientCreate,
    FlarePseudopatientDelete,
    FlarePseudopatientDetail,
    FlarePseudopatientList,
    FlarePseudopatientUpdate,
    FlareUpdate,
)
from .factories import create_flare, flare_data_factory

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestFlareAbout(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: FlareAbout = FlareAbout()

    def test__get(self):
        response = self.client.get(reverse("flares:about"))
        self.assertEqual(response.status_code, 200)

    def test__get_context_data(self):
        request = self.factory.get("/flares/about")
        response = FlareAbout.as_view()(request)
        self.assertIsInstance(response.context_data, dict)
        self.assertIn("content", response.context_data)

    def test__content(self):
        self.assertEqual(
            self.view.content,
            Content.objects.get(context=Content.Contexts.FLARE, slug="about", tag=None),
        )


class TestFlareCreate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: FlareCreate = FlareCreate
        self.request = self.factory.get("/fake-url/")
        self.user = AnonymousUser()
        self.request.user = self.user
        self.flare_data = {
            "crystal_analysis": "",
            "date_ended": "",
            "date_started": timezone.now().date(),
            "dateofbirth-value": age_calc(timezone.now() - timedelta(days=365 * 50)),
            "dialysis": False,
            "gender-value": Genders.FEMALE,
            "joints": [LimitedJointChoices.ELBOWL],
            "onset": True,
            "redness": True,
            "stage": Stages.THREE,
            "medical_evaluation": True,
            "aki-value": False,
            "aspiration": False,
            "urate_check": False,
            "urate": "",
            "diagnosed": DiagnosedChoices.NO,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.GOUT}-value": False,
            f"{MedHistoryTypes.MENOPAUSE}-value": True,
            "creatinine-TOTAL_FORMS": 0,
            "creatinine-INITIAL_FORMS": 0,
        }

    def test__attrs(self):
        self.assertIn("dateofbirth", self.view.OTO_FORMS)
        self.assertEqual(DateOfBirthForm, self.view.OTO_FORMS["dateofbirth"])
        self.assertIn("gender", self.view.OTO_FORMS)
        self.assertEqual(GenderForm, self.view.OTO_FORMS["gender"])
        self.assertIn("urate", self.view.OTO_FORMS)
        self.assertEqual(UrateFlareForm, self.view.OTO_FORMS["urate"])
        self.assertIn(MedHistoryTypes.ANGINA, self.view.MEDHISTORY_FORMS)
        self.assertEqual(AnginaForm, self.view.MEDHISTORY_FORMS[MedHistoryTypes.ANGINA])
        self.assertIn(MedHistoryTypes.CAD, self.view.MEDHISTORY_FORMS)
        self.assertEqual(CadForm, self.view.MEDHISTORY_FORMS[MedHistoryTypes.CAD])
        self.assertIn(MedHistoryTypes.CHF, self.view.MEDHISTORY_FORMS)
        self.assertEqual(ChfForm, self.view.MEDHISTORY_FORMS[MedHistoryTypes.CHF])
        self.assertIn(MedHistoryTypes.CKD, self.view.MEDHISTORY_FORMS)
        self.assertEqual(CkdForm, self.view.MEDHISTORY_FORMS[MedHistoryTypes.CKD])
        self.assertIn(MedHistoryTypes.GOUT, self.view.MEDHISTORY_FORMS)
        self.assertEqual(GoutForm, self.view.MEDHISTORY_FORMS[MedHistoryTypes.GOUT])
        self.assertIn(MedHistoryTypes.HEARTATTACK, self.view.MEDHISTORY_FORMS)
        self.assertEqual(HeartattackForm, self.view.MEDHISTORY_FORMS[MedHistoryTypes.HEARTATTACK])
        self.assertIn(MedHistoryTypes.STROKE, self.view.MEDHISTORY_FORMS)
        self.assertEqual(StrokeForm, self.view.MEDHISTORY_FORMS[MedHistoryTypes.STROKE])
        self.assertIn(MedHistoryTypes.PVD, self.view.MEDHISTORY_FORMS)
        self.assertEqual(PvdForm, self.view.MEDHISTORY_FORMS[MedHistoryTypes.PVD])

    def test__get_context_data(self):
        request = self.factory.get("/flares/create")
        request.user = AnonymousUser()
        SessionMiddleware(dummy_get_response).process_request(request)
        response = FlareCreate.as_view()(request)
        self.assertIsInstance(response.context_data, dict)  # type: ignore
        for medhistory in FLARE_MEDHISTORYS:
            self.assertIn(f"{medhistory}_form", response.context_data)  # type: ignore
            self.assertIsInstance(
                response.context_data[f"{medhistory}_form"], self.view.MEDHISTORY_FORMS[medhistory]  # type: ignore
            )
            self.assertIsInstance(
                response.context_data[f"{medhistory}_form"].instance,  # type: ignore
                self.view.MEDHISTORY_FORMS[medhistory]._meta.model,
            )
        self.assertIn("dateofbirth_form", response.context_data)  # type: ignore
        self.assertIsInstance(
            response.context_data["dateofbirth_form"], self.view.OTO_FORMS["dateofbirth"]  # type: ignore
        )
        self.assertIsInstance(
            response.context_data["dateofbirth_form"].instance,  # type: ignore
            self.view.OTO_FORMS["dateofbirth"]._meta.model,
        )
        self.assertIsInstance(response.context_data["gender_form"], self.view.OTO_FORMS["gender"])  # type: ignore
        self.assertIsInstance(
            response.context_data["gender_form"].instance, self.view.OTO_FORMS["gender"]._meta.model  # type: ignore
        )
        self.assertIsInstance(response.context_data["urate_form"], self.view.OTO_FORMS["urate"])  # type: ignore
        self.assertIsInstance(
            response.context_data["urate_form"].instance, self.view.OTO_FORMS["urate"]._meta.model  # type: ignore
        )

    def test__post_no_medhistorys(self):
        # Count flares, dateofbirths, and genders
        flare_count, dateofbirth_count, gender_count = (
            Flare.objects.count(),
            DateOfBirth.objects.count(),
            Gender.objects.count(),
        )
        response = self.client.post(reverse("flares:create"), self.flare_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Flare.objects.count(), flare_count + 1)
        self.assertEqual(DateOfBirth.objects.count(), dateofbirth_count + 1)
        self.assertEqual(Gender.objects.count(), gender_count + 1)
        flare = Flare.objects.order_by("created").last()
        dateofbirth = DateOfBirth.objects.order_by("created").last()
        gender = Gender.objects.order_by("created").last()
        self.assertEqual(dateofbirth, flare.dateofbirth)
        self.assertEqual(gender, flare.gender)

    def test__post_medhistorys(self):
        """Test that medhistorys can be created."""
        # Count flares and medhistorys
        flare_count, medhistorys_count = Flare.objects.count(), MedHistory.objects.count()

        # Create fake data to post()
        self.flare_data.update(
            {
                f"{MedHistoryTypes.ANGINA}-value": True,
            }
        )
        response = self.client.post(reverse("flares:create"), self.flare_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Flare.objects.count(), flare_count + 1)
        self.assertEqual(MedHistory.objects.count(), medhistorys_count + 2)
        flare = Flare.objects.order_by("created").last()
        angina = Angina.objects.order_by("created").last()
        menopause = Menopause.objects.order_by("created").last()
        flare_mhs = flare.medhistory_set.all()
        self.assertIn(angina, flare_mhs)
        self.assertIn(menopause, flare_mhs)
        self.assertEqual(len(flare_mhs), 2)

    def test__post_medhistorys_urate(self):
        self.flare_data.update(
            {
                "urate_check": True,
                "urate-value": Decimal("5.0"),
            }
        )
        response = self.client.post(reverse("flares:create"), self.flare_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Flare.objects.count(), 1)
        self.assertEqual(Urate.objects.count(), 1)
        flare = Flare.objects.get()
        urate = Urate.objects.get()
        self.assertEqual(urate, flare.urate)

    def test__post_multiple_medhistorys_urate(self):
        """Test that multiple medhistorys can be created and that the urate is created."""
        # Count the number of flares, medhistorys and urates
        flare_count, medhistorys_count, urates_count = (
            Flare.objects.count(),
            MedHistory.objects.count(),
            Urate.objects.count(),
        )
        flare_data = {
            "crystal_analysis": "",
            "date_ended": "",
            "date_started": timezone.now().date(),
            "dateofbirth-value": age_calc(timezone.now() - timedelta(days=365 * 50)),
            f"{MedHistoryTypes.ANGINA}-value": True,
            f"{MedHistoryTypes.CAD}-value": True,
            f"{MedHistoryTypes.CHF}-value": True,
            "gender-value": Genders.FEMALE,
            "joints": [LimitedJointChoices.ELBOWL],
            "onset": True,
            "redness": True,
            "medical_evaluation": True,
            "aki-value": False,
            "aspiration": False,
            "urate_check": True,
            "urate-value": Decimal("5.0"),
            "diagnosed": DiagnosedChoices.NO,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.GOUT}-value": False,
            f"{MedHistoryTypes.MENOPAUSE}-value": True,
            "creatinine-TOTAL_FORMS": 0,
            "creatinine-INITIAL_FORMS": 0,
        }
        response = self.client.post(reverse("flares:create"), flare_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Flare.objects.count(), flare_count + 1)
        self.assertEqual(Urate.objects.count(), urates_count + 1)
        self.assertEqual(MedHistory.objects.count(), medhistorys_count + 4)
        flare = Flare.objects.get()
        urate = Urate.objects.get()
        menopause = Menopause.objects.get()
        self.assertEqual(urate, flare.urate)
        self.assertEqual(flare.medhistory_set.count(), 4)
        self.assertIn(menopause, flare.medhistory_set.all())

    def test__post_forms_not_valid(self):
        flare_data = {
            "crystal_analysis": "",
            "date_ended": "",
            "date_started": timezone.now().date(),
            "dateofbirth-value": age_calc(timezone.now() - timedelta(days=365 * 50)),
            f"{MedHistoryTypes.ANGINA}-value": True,
            "gender-value": "DRWHO",
            "joints": [LimitedJointChoices.ELBOWL],
            "onset": True,
            "redness": True,
            "medical_evaluation": True,
            "aspiration": False,
            "urate_check": True,
            "urate-value": Decimal("5.0"),
            "diagnosed": DiagnosedChoices.NO,
        }
        response = self.client.post(reverse("flares:create"), flare_data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context_data["form"].errors)  # type: ignore
        self.assertTrue(response.context_data["gender_form"].errors)  # type: ignore
        self.assertIn("value", response.context_data["gender_form"].errors)  # type: ignore

    def test__post_menopause_not_valid(self):
        """Test that the MenopauseForm is not valid when the patient is a female between 40 and 60."""

        # Modify fake data to post()
        self.flare_data.update(
            {
                f"{MedHistoryTypes.MENOPAUSE}-value": "",
            }
        )
        # Post the data and check that the response is 200 because the MenopauseForm is not valid
        response = self.client.post(reverse("flares:create"), self.flare_data)
        self.assertEqual(response.status_code, 200)

        # Assert that the MenopauseForm has an error
        self.assertTrue(response.context_data[f"{MedHistoryTypes.MENOPAUSE}_form"].errors)  # type: ignore
        self.assertEqual(
            response.context_data[f"{MedHistoryTypes.MENOPAUSE}_form"].errors[f"{MedHistoryTypes.MENOPAUSE}-value"][0],
            "For females between ages 40 and 60, we need to know the patient's \
menopause status to evaluate their flare.",
        )

    def test__post_menopause_valid_too_young(self):
        """Test that the MenopauseForm is valid when the patient
        is too young for menopause."""
        self.flare_data.update(
            {
                "dateofbirth-value": age_calc(timezone.now() - timedelta(days=365 * 39)),
                f"{MedHistoryTypes.MENOPAUSE}-value": "None",
            }
        )
        response = self.client.post(reverse("flares:create"), self.flare_data)
        self.assertEqual(response.status_code, 302)

    def test__post_menopause_valid_too_old(self):
        """Test that the MenopauseForm is valid when the patient
        is too old for menopause."""
        self.flare_data.update(
            {
                "dateofbirth-value": age_calc(timezone.now() - timedelta(days=365 * 61)),
                f"{MedHistoryTypes.MENOPAUSE}-value": "None",
            }
        )
        response = self.client.post(reverse("flares:create"), self.flare_data)
        self.assertEqual(response.status_code, 302)

    def test__urate_check_not_valid(self):
        self.flare_data.update(
            {
                "medical_evaluation": True,
                "urate_check": True,
                "urate-value": "",
            }
        )
        response = self.client.post(reverse("flares:create"), self.flare_data)
        self.assertEqual(response.status_code, 200)
        # Assert that the UrateForm has an error
        self.assertTrue(response.context_data["urate_form"].errors)
        self.assertEqual(
            response.context_data["urate_form"].errors["value"][0],
            "If the serum uric acid was checked, please tell us the value! \
If you don't know the value, please uncheck the Uric Acid Lab Check box.",
        )

    def test__aki_created(self):
        """Test that the AKI MedHistory is created when the patient has CKD."""
        # Create a Flare with CKD
        flare_data = flare_data_factory(otos={"aki": True})
        response = self.client.post(reverse("flares:create"), flare_data)
        self.assertEqual(response.status_code, 302)

        new_flare = Flare.objects.order_by("created").last()
        self.assertTrue(new_flare.aki)

    def test__aki_without_status_created_ongoing(self) -> None:
        flare_data = flare_data_factory(otos={"aki": True})
        flare_data.update({"aki-status": ""})
        response = self.client.post(reverse("flares:create"), flare_data)
        self.assertEqual(response.status_code, 302)

        new_flare = Flare.objects.order_by("created").last()
        self.assertTrue(new_flare.aki)
        self.assertEqual(new_flare.aki.status, Aki.Statuses.ONGOING)

    def test__creatinines_created(self):
        # Create Flare data with creatinines
        flare_data = flare_data_factory(creatinines=[Decimal("3.0"), Decimal("3.0")])
        response = self.client.post(reverse("flares:create"), flare_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        new_flare = Flare.objects.order_by("created").last()
        self.assertTrue(new_flare.aki)
        creatinines = new_flare.aki.creatinine_set.all()
        self.assertEqual(creatinines.count(), 2)

    def test__aki_status_set_with_creatinines(self):
        flare_data = flare_data_factory(otos={"aki": True}, mhs=None, creatinines=[Decimal("3.0"), Decimal("3.0")])
        flare_data.update({"aki-status": ""})
        response = self.client.post(reverse("flares:create"), flare_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        aki = Aki.objects.order_by("created").last()
        self.assertEqual(aki.status, Aki.Statuses.ONGOING)

    def test__aki_ongoing_creatinines_improved_raises_ValidationError(self) -> None:
        flare_data = flare_data_factory(
            otos={"aki": True},
            mhs=None,
            creatinines=[
                CreatinineFactory(value=Decimal("3.0"), date_drawn=timezone.now() - timedelta(days=4)),
                CreatinineFactory(value=Decimal("1.9"), date_drawn=timezone.now() - timedelta(days=2)),
            ],
        )
        flare_data.update({"date_started": str((timezone.now() - timedelta(days=5)).date())})
        flare_data.update({"date_ended": str((timezone.now() - timedelta(days=1)).date())})
        flare_data.update({"creatinine-0-date_drawn": str(timezone.now() - timedelta(days=4))})
        flare_data.update({"creatinine-1-date_drawn": str(timezone.now() - timedelta(days=2))})
        flare_data.update({"aki-status": Statuses.ONGOING})
        response = self.client.post(reverse("flares:create"), flare_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 200)
        self.assertIn("status", response.context_data["aki_form"].errors)
        self.assertIn(
            "The AKI is marked as ongoing, but the creatinines suggest it is improving.",
            response.context_data["aki_form"].errors["status"][0],
        )
        self.assertIn(
            "The AKI is marked as ongoing, but the creatinines suggest it is improving.",
            response.context_data["creatinine_formset"].errors[0]["__all__"],
        )

    def test__post_aki_on_dialysis_raises_ValidationError(self) -> None:
        flare_data = flare_data_factory(otos={"aki": True})
        flare_data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": True,
                "dialysis_type": DialysisChoices.HEMODIALYSIS,
                "dialysis_duration": DialysisDurations.LESSTHANSIX,
            }
        )
        response = self.client.post(reverse("flares:create"), flare_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 200)
        self.assertIn("value", response.context_data["aki_form"].errors)
        self.assertIn(
            "If the patient is on",
            response.context_data["aki_form"].errors["value"][0],
        )
        self.assertIn("dialysis", response.context_data["ckddetail_form"].errors)
        self.assertIn(
            "If the patient is on",
            response.context_data["ckddetail_form"].errors["dialysis"][0],
        )


class TestFlareDetail(TestCase):
    def setUp(self):
        self.flare = create_flare()
        self.factory = RequestFactory()
        self.view: FlareDetail = FlareDetail

    def test__dispatch_redirects_if_flare_user(self):
        """Test that the dispatch() method redirects to the Pseudopatient DetailView if the
        Flare has a user."""
        user_f = create_flare(user=True)
        request = self.factory.get("/fake-url/")
        request.user = AnonymousUser()
        response = self.view.as_view()(request, pk=user_f.pk)
        assert response.status_code == 302
        assert response.url == reverse(
            "flares:pseudopatient-detail", kwargs={"pseudopatient": user_f.user.pk, "pk": user_f.pk}
        )

    def test__get_queryset(self):
        qs = self.view(kwargs={"pk": self.flare.pk}).get_queryset()
        self.assertTrue(isinstance(qs, QuerySet))
        self.assertEqual(qs.first(), self.flare)
        self.assertTrue(hasattr(qs.first(), "medhistorys_qs"))
        self.assertTrue(hasattr(qs.first(), "ckddetail"))
        self.assertTrue(hasattr(qs.first(), "baselinecreatinine"))
        self.assertTrue(hasattr(qs.first(), "dateofbirth"))
        self.assertTrue(hasattr(qs.first(), "gender"))
        self.assertTrue(hasattr(qs.first(), "urate"))

    def test__get_object_updates(self):
        self.assertIsNone(self.flare.likelihood)
        self.assertIsNone(self.flare.prevalence)
        request = self.factory.get(reverse("flares:detail", kwargs={"pk": self.flare.pk}))
        request.user = AnonymousUser()
        self.view.as_view()(request, pk=self.flare.pk)
        # This needs to be manually refetched from the db
        self.assertIsNotNone(Flare.objects.get().likelihood)
        self.assertIsNotNone(Flare.objects.get().prevalence)

    def test__get_object_does_not_update(self):
        self.assertIsNone(self.flare.likelihood)
        self.assertIsNone(self.flare.prevalence)
        request = self.factory.get(reverse("flares:detail", kwargs={"pk": self.flare.pk}) + "?updated=True")
        request.user = AnonymousUser()
        self.view.as_view()(request, pk=self.flare.pk)
        # This needs to be manually refetched from the db
        self.assertIsNone(Flare.objects.get().likelihood)
        self.assertIsNone(Flare.objects.get().prevalence)


class TestFlarePseudopatientCreate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = FlarePseudopatientCreate
        self.anon_user = AnonymousUser()
        self.user = create_psp(plus=True)
        for _ in range(10):
            create_psp(plus=True)
        self.psp = create_psp()

    def test__check_user_onetoones(self):
        """Tests that the view checks for the User's related models."""
        empty_user = create_psp(dateofbirth=False, gender=False)
        view = self.view()
        view.user = empty_user
        self.assertFalse(view.user_has_required_otos)

    def test__ckddetail(self):
        """Tests the ckddetail cached_property."""
        self.assertFalse(self.view().ckddetail)

    def test__goutdetail(self):
        """Tests the goutdetail cached_property."""
        self.assertFalse(self.view().goutdetail)

    def test__get_form_kwargs(self):
        # Create a fake request
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        kwargs = {"pseudopatient": self.user.pk}
        view = self.view(request=request, kwargs=kwargs)
        view.set_forms()

        # Set the object on the view, which is required for the get_form_kwargs method
        view.object = view.get_object()
        form_kwargs = view.get_form_kwargs()

        # Assert that the form_kwargs detected the view has a user attr and sets
        # the patient kwarg to True
        self.assertIn("patient", form_kwargs)
        self.assertEqual(form_kwargs["patient"], self.user)

    def test__dispatch(self):
        """Test the dispatch() method for the view. Should redirect to Pseudopatient Update
        view when the user doesn't have the required 1to1 related models."""
        # Create empty user and test that the view redirects to the user update view
        empty_user = create_psp(dateofbirth=False)
        self.client.force_login(empty_user)
        response = self.client.get(
            reverse("flares:pseudopatient-create", kwargs={"pseudopatient": empty_user.pk}), follow=True
        )
        self.assertRedirects(response, reverse("users:pseudopatient-update", kwargs={"pseudopatient": empty_user.pk}))
        message = list(response.context.get("messages"))[0]
        self.assertEqual(message.tags, "error")
        self.assertEqual(message.message, f"{empty_user} is missing required information.")

    def test__get_user_queryset(self):
        """Test the get_user_queryset() method for the view."""
        request = self.factory.get("/fake-url/")
        kwargs = {"pseudopatient": self.user.pk}
        view = self.view()
        # https://stackoverflow.com/questions/33645780/how-to-unit-test-methods-inside-djangos-class-based-views
        view.setup(request, **kwargs)
        qs = view.get_user_queryset(view.kwargs["pseudopatient"])
        self.assertTrue(isinstance(qs, QuerySet))
        qs = qs.get()
        self.assertTrue(isinstance(qs, User))
        self.assertTrue(hasattr(qs, "medhistorys_qs"))
        self.assertTrue(hasattr(qs, "dateofbirth"))
        self.assertTrue(hasattr(qs, "gender"))

    def test__get_context_data_onetoones(self):
        """Test that the context data includes the user's
        related models."""
        for user in Pseudopatient.objects.all():
            request = self.factory.get("/fake-url/")
            if user.profile.provider:
                request.user = user.profile.provider
            else:
                request.user = self.anon_user
            SessionMiddleware(dummy_get_response).process_request(request)
            kwargs = {"pseudopatient": user.pk}
            response = self.view.as_view()(request, **kwargs)
            assert response.status_code == 200
            assert "age" in response.context_data
            assert response.context_data["age"] == age_calc(user.dateofbirth.value)
            assert "gender" in response.context_data
            assert response.context_data["gender"] == user.gender.value

    def test__get_context_data_medhistorys(self):
        """Test that the context data includes the user's
        related models."""
        for user in Pseudopatient.objects.all():
            request = self.factory.get("/fake-url/")
            if user.profile.provider:
                request.user = user.profile.provider
            else:
                request.user = self.anon_user
            SessionMiddleware(dummy_get_response).process_request(request)
            kwargs = {"pseudopatient": user.pk}
            response = self.view.as_view()(request, **kwargs)
            assert response.status_code == 200
            for mh in user.medhistory_set.all():
                if mh.medhistorytype in FLARE_MEDHISTORYS:
                    if (
                        not mh.medhistorytype == MedHistoryTypes.MENOPAUSE
                        and not mh.medhistorytype == MedHistoryTypes.GOUT
                    ):
                        assert f"{mh.medhistorytype}_form" in response.context_data
                        assert response.context_data[f"{mh.medhistorytype}_form"].instance == mh
                        assert response.context_data[f"{mh.medhistorytype}_form"].instance._state.adding is False
                        assert response.context_data[f"{mh.medhistorytype}_form"].initial == {
                            f"{mh.medhistorytype}-value": True
                        }
                else:
                    assert f"{mh.medhistorytype}_form" not in response.context_data
            for mhtype in FLARE_MEDHISTORYS:
                if mhtype == MedHistoryTypes.MENOPAUSE or mhtype == MedHistoryTypes.GOUT:
                    assert f"{mhtype}_form" not in response.context_data
                else:
                    assert f"{mhtype}_form" in response.context_data
                    if mhtype not in user.medhistory_set.values_list("medhistorytype", flat=True):
                        assert response.context_data[f"{mhtype}_form"].instance._state.adding is True
                        if mhtype == MedHistoryTypes.MENOPAUSE:
                            if user.gender.value == Genders.FEMALE:
                                age = age_calc(user.dateofbirth.value)
                                if age >= 60:
                                    assert response.context_data[f"{mhtype}_form"].initial == {f"{mhtype}-value": True}
                                elif age >= 40 and age < 60:
                                    assert response.context_data[f"{mhtype}_form"].initial == {
                                        f"{mhtype}-value": False
                                    }
                                else:
                                    assert response.context_data[f"{mhtype}_form"].initial == {f"{mhtype}-value": None}
            assert "ckddetail_form" in response.context_data
            assert "baselinecreatinine_form" in response.context_data
            assert "goutdetail_form" not in response.context_data

    def test__get_permission_object(self):
        """Test the get_permission_object() method for the view."""
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        kwargs = {"pseudopatient": self.user.pk}
        view = self.view()
        # https://stackoverflow.com/questions/33645780/how-to-unit-test-methods-inside-djangos-class-based-views
        view.setup(request, **kwargs)
        view.user = self.user
        permission_object = view.get_permission_object()
        self.assertEqual(permission_object, self.user)

    def test__post(self):
        """Test the post() method for the view."""
        request = self.factory.post("/fake-url/")
        if self.user.profile.provider:  # type: ignore
            request.user = self.user.profile.provider  # type: ignore
        else:
            request.user = self.anon_user
        SessionMiddleware(dummy_get_response).process_request(request)
        kwargs = {"pseudopatient": self.user.pk}
        response = self.view.as_view()(request, **kwargs)
        assert response.status_code == 200

    def test__post_sets_object_user(self):
        """Test that the post() method for the view sets the
        user on the object."""
        # Create some fake data for a User's FlareAid
        data = flare_data_factory(self.user)
        response = self.client.post(
            reverse("flares:pseudopatient-create", kwargs={"pseudopatient": self.user.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302
        assert Flare.objects.filter(user=self.user).exists()
        flare = Flare.objects.last()
        assert flare.user
        assert flare.user == self.user

    def test__post_creates_medhistorys(self):
        """Test that the post() method for the view creates medhistorys."""

        # Assert that the Pseudopatient doesn't have CAD or CHF
        self.assertFalse(MedHistory.objects.filter(user=self.psp, medhistorytype=MedHistoryTypes.CAD).exists())
        self.assertFalse(MedHistory.objects.filter(user=self.psp, medhistorytype=MedHistoryTypes.CHF).exists())

        # Create some fake data for a User's FlareAid
        data = flare_data_factory(self.psp)
        data.update(
            {
                f"{MedHistoryTypes.CAD}-value": True,
                f"{MedHistoryTypes.CHF}-value": True,
            }
        )

        # Post the data
        response = self.client.post(
            reverse("flares:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302

        # Assert that the medhistorys were created
        self.assertTrue(MedHistory.objects.filter(user=self.psp, medhistorytype=MedHistoryTypes.CAD).exists())
        self.assertTrue(MedHistory.objects.filter(user=self.psp, medhistorytype=MedHistoryTypes.CHF).exists())

    def test__post_deletes_medhistorys(self):
        """Test that the post() method for the view deletes
        medhistorys that are not selected."""

        # Create an empty pseudopatient without any medhistorys
        psp = create_psp()

        # Assert that the Pseudopatient doesn't have CAD or CHF
        self.assertFalse(MedHistory.objects.filter(user=psp, medhistorytype=MedHistoryTypes.CAD).exists())
        self.assertFalse(MedHistory.objects.filter(user=psp, medhistorytype=MedHistoryTypes.CHF).exists())

        # Create some fake data for a User's FlareAid
        data = flare_data_factory(psp)
        # Add some medhistorys to the data
        data.update(
            {
                f"{MedHistoryTypes.CAD}-value": True,
                f"{MedHistoryTypes.CHF}-value": True,
            }
        )

        # Post the data
        response = self.client.post(
            reverse("flares:pseudopatient-create", kwargs={"pseudopatient": psp.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302

        # Assert that the medhistorys were created
        self.assertTrue(MedHistory.objects.filter(user=psp, medhistorytype=MedHistoryTypes.CAD).exists())
        self.assertTrue(MedHistory.objects.filter(user=psp, medhistorytype=MedHistoryTypes.CHF).exists())

    def test__post_unchanged_medhistorys(self):
        """Test that post does not change medhistorys that are not changed
        from their pre-post() values by the form."""
        # Create an empty pseudopatient and then create some known medhistorys
        psp = create_psp(medhistorys=[MedHistoryTypes.ANGINA, MedHistoryTypes.CHF])
        self.assertTrue(MedHistory.objects.filter(user=psp, medhistorytype=MedHistoryTypes.ANGINA).exists())
        self.assertTrue(MedHistory.objects.filter(user=psp, medhistorytype=MedHistoryTypes.CHF).exists())
        # Create some fake data for a User's FlareAid
        data = flare_data_factory(psp)
        # Add the medhistorys to the data
        data.update(
            {
                f"{MedHistoryTypes.ANGINA}-value": True,
                f"{MedHistoryTypes.CHF}-value": True,
            }
        )
        # Post the data
        response = self.client.post(
            reverse("flares:pseudopatient-create", kwargs={"pseudopatient": psp.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302
        # Assert that the medhistorys were not changed
        self.assertTrue(MedHistory.objects.filter(user=psp).exists())
        self.assertTrue(MedHistory.objects.filter(user=psp, medhistorytype=MedHistoryTypes.ANGINA).exists())
        self.assertTrue(MedHistory.objects.filter(user=psp, medhistorytype=MedHistoryTypes.CHF).exists())

    def test__post_adds_urate(self):
        """Test that the post() method creates a urate when provided the appropriate data
        and that the urate is assigned to the flare onetoone urate field."""
        data = flare_data_factory(self.psp)
        data.update(
            {
                "urate_check": True,
                "urate-value": Decimal("5.0"),
            }
        )
        response = self.client.post(
            reverse("flares:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302
        self.assertTrue(Urate.objects.filter(user=self.psp).exists())
        flare = Flare.objects.get()
        urate = Urate.objects.get()
        self.assertEqual(urate, flare.urate)

    def test__post_returns_errors(self):
        """Test that the post() method returns the correct errors when the data is invalid."""
        # Create some fake data and update it to have a urate_check but no urate-value
        data = flare_data_factory(self.psp)
        data.update(
            {
                "medical_evaluation": True,
                "urate_check": True,
                "urate-value": "",
            }
        )
        # Post the data
        response = self.client.post(
            reverse("flares:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 200
        # Assert that the form has an error on the urate_check field
        self.assertTrue(response.context_data["form"].errors)
        self.assertEqual(
            response.context_data["form"].errors["urate_check"][0],
            "If the serum uric acid was checked, please tell us the value! \
If you don't know the value, please uncheck the Uric Acid Lab Check box.",
        )
        # Assert that the urate_form has an error on the value field
        self.assertTrue(response.context_data["urate_form"].errors)
        self.assertEqual(
            response.context_data["urate_form"].errors["value"][0],
            "If the serum uric acid was checked, please tell us the value! \
If you don't know the value, please uncheck the Uric Acid Lab Check box.",
        )
        # Change the fake data such that the urate stuff passes but that diagnosed is True but aspiration is
        # not selected, which should result in an error on the aspiration field
        data.update(
            {
                "urate_check": True,
                "urate-value": Decimal("5.0"),
                "diagnosed": DiagnosedChoices.YES,
                "aspiration": "",
            }
        )
        # Post the data
        response = self.client.post(
            reverse("flares:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        assert response.status_code == 200
        forms_print_response_errors(response)
        # Assert that the form has an error on the aspiration field
        self.assertTrue(response.context_data["form"].errors)
        self.assertIn(
            "Joint aspiration must be selected if",
            response.context_data["form"].errors["aspiration"][0],
        )

    def test__post_returns_high_likelihood_prevalence_flare(self):
        """Test that a flare is created with a high likelihood and prevalence when the
        data indicates a high likelihood and prevalence flare."""
        # Modify Pseudopatient related demographic objects to facilitate high likelihood/prevalence
        self.psp.dateofbirth.value = timezone.now().date() - timedelta(days=365 * 64)
        self.psp.dateofbirth.save()
        self.psp.gender.value = Genders.MALE
        self.psp.gender.save()
        # Create a fake data dict
        data = flare_data_factory(self.psp)
        # Modify data entries to indicate a high likelihood and prevalence flare
        data.update(
            {
                "onset": True,
                "redness": True,
                "joints": [LimitedJointChoices.MTP1L, LimitedJointChoices.MTP1R],
                "urate_check": True,
                "urate-value": Decimal("9.0"),
                "diagnosed": DiagnosedChoices.YES,
                "aspiration": True,
                "crystal_analysis": True,
                "date_started": timezone.now().date() - timedelta(days=35),
                "date_ended": timezone.now().date() - timedelta(days=25),
            }
        )
        # Post the data
        response = self.client.post(
            reverse("flares:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302
        # Assert that the flare was created
        self.assertTrue(Flare.objects.filter(user=self.psp).exists())
        flare = Flare.objects.get()
        # Assert that the flare has a high likelihood and prevalence
        self.assertEqual(flare.likelihood, Likelihoods.LIKELY)
        self.assertEqual(flare.prevalence, Prevalences.HIGH)

    def test__post_returns_moderate_likelihood_prevalence_flare(self):
        """Test that a flare is created with a moderate likelihood and prevalence when the
        data indicates a moderate likelihood and prevalence flare."""
        # Create a Pseudopatient without medhistorys to avoid that influencing the likelihood and prevalence
        psp = create_psp(
            dateofbirth=timezone.now().date() - timedelta(days=365 * 64), gender=Genders.FEMALE, medhistorys=[]
        )
        # Create a fake data dict
        data = flare_data_factory(psp)
        # Modify data entries to indicate a moderate likelihood and prevalence flare
        data.update(
            {
                "onset": True,
                "redness": False,
                "joints": [LimitedJointChoices.KNEER],
                "date_started": timezone.now().date() - timedelta(days=7),
                "date_ended": "",
                "urate_check": True,
                "urate-value": Decimal("7.0"),
                "diagnosed": DiagnosedChoices.YES,
                "aspiration": False,
                "crystal_analysis": "",
            }
        )

        # Post the data
        response = self.client.post(
            reverse("flares:pseudopatient-create", kwargs={"pseudopatient": psp.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302

        # Assert that the flare was created
        self.assertTrue(Flare.objects.filter(user=psp).exists())
        flare = Flare.objects.filter(user=psp).last()
        # Assert that the flare has a moderate likelihood and prevalence
        self.assertEqual(flare.likelihood, Likelihoods.EQUIVOCAL)
        self.assertEqual(flare.prevalence, Prevalences.MEDIUM)

    def test__post_returns_low_likelihood_prevalence_flare(self):
        """Test that a flare is created with a low likelihood and prevalence when the
        data indicates a low likelihood and prevalence flare."""
        # Modify Pseudopatient related demographic objects to facilitate low likelihood/prevalence
        self.psp.dateofbirth.value = timezone.now().date() - timedelta(days=365 * 24)
        self.psp.dateofbirth.save()
        self.psp.gender.value = Genders.FEMALE
        self.psp.gender.save()
        # Create a fake data dict
        data = flare_data_factory(self.psp)
        # Modify data entries to indicate a low likelihood and prevalence flare
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": False,
                "onset": False,
                "redness": False,
                "joints": [LimitedJointChoices.HIPL],
                "urate_check": True,
                "urate-value": Decimal("5.0"),
                "medical_evaluation": True,
                "diagnosed": DiagnosedChoices.NO,
                "aspiration": False,
                "crystal_analysis": "",
                "date_started": timezone.now().date() - timedelta(days=135),
                "date_ended": timezone.now().date() - timedelta(days=5),
            }
        )
        # Post the data
        response = self.client.post(
            reverse("flares:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302
        # Assert that the flare was created
        self.assertTrue(Flare.objects.filter(user=self.psp).exists())
        flare = Flare.objects.get()
        # Assert that the flare has a low likelihood and prevalence
        self.assertEqual(flare.likelihood, Likelihoods.UNLIKELY)
        self.assertEqual(flare.prevalence, Prevalences.LOW)

    def test__rules(self):
        """Test that django-rules permissions are set correctly and working for the view."""
        # Create a Provider and Admin, each with their own Pseudopatient
        provider = UserFactory()
        prov_psp = create_psp(provider=provider)
        prov_psp_url = reverse("flares:pseudopatient-create", kwargs={"pseudopatient": prov_psp.pk})
        next_url = reverse("flares:pseudopatient-create", kwargs={"pseudopatient": prov_psp.pk})
        prov_psp_redirect_url = f"{reverse('account_login')}?next={next_url}"
        admin = AdminFactory()
        admin_psp = create_psp(provider=admin)
        admin_psp_url = reverse("flares:pseudopatient-create", kwargs={"pseudopatient": admin_psp.pk})
        redirect_url = reverse("flares:pseudopatient-create", kwargs={"pseudopatient": admin_psp.pk})
        admin_psp_redirect_url = f"{reverse('account_login')}?next={redirect_url}"
        # Create an anonymous Pseudopatient
        anon_psp = create_psp()
        anon_psp_url = reverse("flares:pseudopatient-create", kwargs={"pseudopatient": anon_psp.pk})
        # Test that an anonymous user who is not logged in can't see any Pseudopatient
        # with a provider but can see the anonymous Pseudopatient
        self.assertRedirects(self.client.get(prov_psp_url), prov_psp_redirect_url)
        self.assertRedirects(self.client.get(admin_psp_url), admin_psp_redirect_url)
        response = self.client.get(anon_psp_url)
        assert response.status_code == 200
        # Test that the Provider can access the view for his or her own Pseudopatient
        self.client.force_login(provider)
        response = self.client.get(prov_psp_url)
        assert response.status_code == 200
        # Test that the Provider can't access the view for the Admin's Pseudopatient
        response = self.client.get(admin_psp_url)
        assert response.status_code == 403
        # Test that the logged in Provider can see an anonymous Pseudopatient
        response = self.client.get(anon_psp_url)
        assert response.status_code == 200
        # Test that the Admin can access the view for his or her own Pseudopatient
        self.client.force_login(admin)
        response = self.client.get(admin_psp_url)
        assert response.status_code == 200
        # Test that the Admin can't access the view for the Provider's Pseudopatient
        response = self.client.get(prov_psp_url)
        assert response.status_code == 403
        # Test that the logged in Admin can see an anonymous Pseudopatient
        response = self.client.get(anon_psp_url)
        assert response.status_code == 200

    def test__aki_created(self):
        """Test that the AKI MedHistory is created when the patient has CKD."""
        # Create a Flare with CKD
        flare_data = flare_data_factory(user=self.psp, otos={"aki": True})
        response = self.client.post(
            reverse("flares:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}), flare_data
        )
        self.assertEqual(response.status_code, 302)

        new_flare = Flare.objects.filter(user=self.psp).order_by("created").last()
        self.assertTrue(new_flare.aki)
        self.assertEqual(new_flare.aki.user, self.psp)

    def test__creatinines_created(self):
        # Create Flare data with creatinines
        flare_data = flare_data_factory(user=self.psp, creatinines=[Decimal("2.0"), Decimal("2.0")])
        response = self.client.post(
            reverse("flares:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}), flare_data
        )
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        new_flare = Flare.objects.filter(user=self.psp).order_by("created").last()
        self.assertTrue(new_flare.aki)
        self.assertEqual(new_flare.aki.user, self.psp)
        creatinines = new_flare.aki.creatinine_set.all()
        self.assertEqual(creatinines.count(), 2)
        for creatinine in creatinines:
            self.assertEqual(creatinine.aki, new_flare.aki)
            self.assertEqual(creatinine.user, self.psp)

    def test__post_aki_on_dialysis_raises_ValidationError(self) -> None:
        flare_data = flare_data_factory(user=self.psp, otos={"aki": True})
        flare_data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": True,
                "dialysis_type": DialysisChoices.HEMODIALYSIS,
                "dialysis_duration": DialysisDurations.LESSTHANSIX,
            }
        )
        response = self.client.post(
            reverse("flares:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}), flare_data
        )
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 200)
        self.assertIn("value", response.context_data["aki_form"].errors)
        self.assertIn(
            "If the patient is on",
            response.context_data["aki_form"].errors["value"][0],
        )
        self.assertIn("dialysis", response.context_data["ckddetail_form"].errors)
        self.assertIn(
            "If the patient is on",
            response.context_data["ckddetail_form"].errors["dialysis"][0],
        )

    def test__get_redirects_when_another_flare_does_not_have_date_ended(self):
        conflicting_flare = create_flare(user=self.psp, date_ended=None)
        response = self.client.get(
            reverse("flares:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}),
        )
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse(
                "flares:pseudopatient-detail",
                kwargs={"pseudopatient": conflicting_flare.user.pk, "pk": conflicting_flare.pk},
            ),
        )

    def test__post_raises_ValidationError_when_date_started_or_ended_conflicts_with_another_flare(self):
        conflicting_flare = create_flare(user=self.psp, date_ended=(timezone.now() - timedelta(days=1)).date())
        self.assertEqual(conflicting_flare.date_ended, (timezone.now() - timedelta(days=1)).date())
        flare_data = flare_data_factory(user=self.psp)
        flare_data.update(
            {
                "date_started": conflicting_flare.date_started,
                "date_ended": conflicting_flare.date_ended,
            }
        )
        response = self.client.post(
            reverse("flares:pseudopatient-create", kwargs={"pseudopatient": self.psp.pk}),
            data=flare_data,
        )
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data["form"].errors)
        self.assertIn("date_started", response.context_data["form"].errors)


class TestFlarePseudopatientDelete(TestCase):
    """Tests for the FlarePseudopatientDelete view."""

    def setUp(self):
        # Create a Provider and Admin, each with their own Pseudopatient and an
        # anonymous Pseudopatient, each with a Flare
        self.provider = UserFactory()
        self.prov_psp = create_psp(provider=self.provider)
        self.prov_psp_flare = create_flare(user=self.prov_psp)
        self.admin = AdminFactory()
        self.admin_psp = create_psp(provider=self.admin)
        self.admin_psp_flare = create_flare(user=self.admin_psp)
        self.anon_psp = create_psp()
        self.anon_psp_flare = create_flare(user=self.anon_psp)
        self.factory = RequestFactory()
        self.view = FlarePseudopatientDelete
        self.anon_user = AnonymousUser()

    def test__dispatch_sets_user_and_object_attrs(self):
        """Test that the dispatch() method for the view sets the user and object attrs."""
        request = self.factory.get("/fake-url/")
        request.user = self.provider
        view = self.view()
        view.setup(request, pseudopatient=self.prov_psp.pk, pk=self.prov_psp_flare.pk)
        view.dispatch(request)
        assert hasattr(view, "user")
        assert view.user == self.prov_psp
        assert hasattr(view, "object")
        assert view.object == self.prov_psp_flare

    def test__get_object_sets_user_returns_object(self):
        """Test that the get_object() method for the view sets the user attr and returns the object."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, pseudopatient=self.prov_psp.pk, pk=self.prov_psp_flare.pk)
        flare = view.get_object()
        assert hasattr(view, "user")
        assert view.user == self.prov_psp
        assert flare == self.prov_psp_flare

    def test__get_object_raises_404(self):
        """Test that the get_object() method for the view raises a 404 if the User or Flare doesn't exist."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, pseudopatient=self.prov_psp.pk, pk=self.prov_psp_flare.pk)
        view.kwargs["pseudopatient"] = uuid.uuid4()
        with self.assertRaises(Http404):
            view.get_object()
        view.kwargs["pseudopatient"] = self.prov_psp.pk
        view.kwargs["pk"] = 999
        with self.assertRaises(Http404):
            view.get_object()

    def test__get_permission_object(self):
        """Test that the get_permission_object() method returns the
        view's object, which must have already been set."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, pseudopatient=self.prov_psp.pk, pk=self.prov_psp_flare.pk)
        view.object = self.prov_psp_flare
        assert view.get_permission_object() == self.prov_psp_flare

    def test__get_success_url(self):
        """Test that the get_success_url() method returns the correct url."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, pseudopatient=self.prov_psp.pk, pk=self.prov_psp_flare.pk)
        view.object = self.prov_psp_flare
        assert view.get_success_url() == reverse(
            "flares:pseudopatient-list", kwargs={"pseudopatient": self.prov_psp.pk}
        )

    def test__get_queryset(self):
        """Test that the get_queryset() method returns the correct QuerySet."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, pseudopatient=self.prov_psp.pk, pk=self.prov_psp_flare.pk)
        qs = view.get_queryset()
        assert isinstance(qs, QuerySet)
        user = qs.get()
        assert user == self.prov_psp
        assert hasattr(user, "flare_qs")
        assert user.flare_qs[0] == self.prov_psp_flare
        assert hasattr(user, "medhistorys_qs")

    def test__rules(self):
        """Test that django-rules permissions are set correctly and working for the view."""
        # Create a Provider and Admin, each with their own Pseudopatient + Flare
        prov_psp_url = reverse(
            "flares:pseudopatient-delete", kwargs={"pseudopatient": self.prov_psp.pk, "pk": self.prov_psp_flare.pk}
        )
        prov_psp_redirect_url = f"{reverse('account_login')}?next={prov_psp_url}"
        admin_psp_url = reverse(
            "flares:pseudopatient-delete", kwargs={"pseudopatient": self.admin_psp.pk, "pk": self.admin_psp_flare.pk}
        )
        admin_psp_redirect_url = f"{reverse('account_login')}?next={admin_psp_url}"
        anon_psp_url = reverse(
            "flares:pseudopatient-delete", kwargs={"pseudopatient": self.anon_psp.pk, "pk": self.anon_psp_flare.pk}
        )
        anon_psp_redirect_url = f"{reverse('account_login')}?next={anon_psp_url}"
        # Test that an anonymous user who is not logged in can't delete anything
        self.assertRedirects(self.client.get(prov_psp_url), prov_psp_redirect_url)
        self.assertRedirects(self.client.get(admin_psp_url), admin_psp_redirect_url)
        self.assertRedirects(self.client.get(anon_psp_url), anon_psp_redirect_url)
        # Test that the Provider can delete his or her own Pseudopatient
        self.client.force_login(self.provider)
        response = self.client.get(prov_psp_url)
        assert response.status_code == 200
        # Test that the Provider can't access the view for the Admin's Pseudopatient
        response = self.client.get(admin_psp_url)
        assert response.status_code == 403
        # Test that the logged in Provider can't delete an anonymous Pseudopatient's flare
        response = self.client.get(anon_psp_url)
        assert response.status_code == 403
        # Test that the Admin can delete his or her own Pseudopatient
        self.client.force_login(self.admin)
        response = self.client.get(admin_psp_url)
        assert response.status_code == 200
        # Test that the Admin can't access the view for the Provider's Pseudopatient
        response = self.client.get(prov_psp_url)
        assert response.status_code == 403
        # Test that the logged in Admin can't delete an anonymous Pseudopatient's flare
        response = self.client.get(anon_psp_url)
        assert response.status_code == 403

    def test__delete(self):
        """Test that the delete() method for the view deletes the Flare and returns the
        correct redirect."""
        self.client.force_login(self.provider)
        response = self.client.post(
            reverse(
                "flares:pseudopatient-delete",
                kwargs={"pseudopatient": self.prov_psp.pk, "pk": self.prov_psp_flare.pk},
            )
        )
        assert response.status_code == 302
        assert not Flare.objects.filter(user=self.prov_psp).exists()
        assert response.url == reverse("flares:pseudopatient-list", kwargs={"pseudopatient": self.prov_psp.pk})


class TestFlarePseudopatientDetail(TestCase):
    """Test suite for the FlarePseudopatientDetail view."""

    def setUp(self):
        self.factory = RequestFactory()
        self.view = FlarePseudopatientDetail
        self.anon_user = AnonymousUser()
        self.psp = create_psp(plus=True)
        for psp in Pseudopatient.objects.all():
            create_flare(user=psp)
        self.empty_psp = create_psp(plus=True)

    def test__dispatch(self):
        """Test the dispatch() method for the view. Should redirect to Pseudopatient Update
        view when the user doesn't have the required 1to1 related models."""
        response = self.client.get(
            reverse(
                "flares:pseudopatient-detail",
                kwargs={"pseudopatient": self.psp.pk, "pk": self.psp.flare_set.first().pk},
            )
        )
        self.assertEqual(response.status_code, 200)

        self.psp.dateofbirth.delete()
        # Test that dispatch redirects to the User Update view when the user doesn't have a dateofbirth
        self.assertRedirects(
            self.client.get(
                reverse(
                    "flares:pseudopatient-detail",
                    kwargs={"pseudopatient": self.psp.pk, "pk": self.psp.flare_set.first().pk},
                ),
            ),
            reverse("users:pseudopatient-update", kwargs={"pseudopatient": self.psp.pk}),
        )

    def test__dispatch_sets_object_attr(self):
        """Test that dispatch calls get_object() and sets the object attr on the view."""
        flare = self.psp.flare_set.first()
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        view = self.view()
        view.setup(request, pseudopatient=self.psp.pk, pk=flare.pk)
        view.dispatch(request)
        assert hasattr(view, "object")
        assert view.object == flare

    def test__get_object_sets_user(self):
        """Test that the get_object() method sets the user attribute."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, pseudopatient=self.psp.pk, pk=self.psp.flare_set.first().pk)
        view.get_object()
        assert hasattr(view, "user")
        assert view.user == self.psp

    def test__get_object_raises_DoesNotExist(self):
        """Test that get_object() raises a 404 if the User or the Flare doesn't exist."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, pseudopatient=self.psp.pk, pk=self.psp.flare_set.first().pk)
        view.kwargs["pseudopatient"] = uuid.uuid4()
        with self.assertRaises(ObjectDoesNotExist):
            view.get_object()
        view.kwargs["pseudopatient"] = self.psp.pk
        view.kwargs["pk"] = 999
        with self.assertRaises(ObjectDoesNotExist):
            view.get_object()

    def test__get_object(self):
        """Test that the get_object() method returns the Flare object."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, pseudopatient=self.psp.pk, pk=self.psp.flare_set.first().pk)
        flare = view.get_object()
        assert isinstance(flare, Flare)
        assert flare == self.psp.flare_set.first()

    def test__get_permission_object(self):
        """Test that the get_permission_object() method returns the
        view's object, which must have already been set."""
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        view = self.view()
        view.setup(request, pseudopatient=self.psp.pk, pk=self.psp.flare_set.first().pk)
        view.dispatch(request, pseudopatient=self.psp.pk)
        pm_obj = view.get_permission_object()
        assert pm_obj == view.object

    def test__get_queryset(self):
        """Test the get_queryset() method for the view."""
        # Get a flare
        flare = self.psp.flare_set.first()
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, pseudopatient=self.psp.pk, pk=flare.pk)
        with CaptureQueriesContext(connection) as queries:
            qs = view.get_queryset().get()
        assert qs == self.psp
        assert hasattr(qs, "flare_qs")
        qs_flare = qs.flare_qs[0]
        assert qs_flare == flare
        if getattr(qs_flare, "aki", False):
            assert len(queries.captured_queries) == 5
        else:
            assert len(queries.captured_queries) == 4
        assert hasattr(qs, "dateofbirth") and qs.dateofbirth == self.psp.dateofbirth
        assert hasattr(qs, "gender") and qs.gender == self.psp.gender
        assert hasattr(qs, "medhistorys_qs")
        psp_mhs = self.psp.medhistory_set.filter(
            Q(medhistorytype__in=FLARE_MEDHISTORYS) | Q(medhistorytype__in=FLAREAID_MEDHISTORYS)
        ).all()
        for mh in qs.medhistorys_qs:
            assert mh in psp_mhs

    def test__get_updates_Flare(self):
        """Test that the get method updates the object when called with the
        correct url parameters."""
        psp = create_psp(gender=Genders.FEMALE, dateofbirth=timezone.now().date() - timedelta(days=365 * 24))
        # Create a Flare for the Pseudopatient
        flare = create_flare(
            user=psp,
            onset=False,
            redness=False,
            joints=[LimitedJointChoices.HIPL],
            date_started=timezone.now().date() - timedelta(days=135),
            date_ended=timezone.now().date() - timedelta(days=5),
            diagnosed=False,
            urate=None,
        )
        flare.update_aid(qs=flares_user_qs(psp.pk, flare.pk))
        flare.refresh_from_db()
        self.assertEqual(flare.likelihood, Likelihoods.UNLIKELY)
        self.assertEqual(flare.prevalence, Prevalences.LOW)
        # Modify the flare to have a high likelihood and prevalence
        flare.onset = True
        flare.redness = True
        flare.joints = [LimitedJointChoices.MTP1L, LimitedJointChoices.MTP1R]
        flare.urate = UrateFactory(user=psp, value=Decimal("9.0"))
        flare.diagnosed = True
        flare.crystal_analysis = True
        flare.date_started = timezone.now().date() - timedelta(days=35)
        flare.date_ended = timezone.now().date() - timedelta(days=25)
        flare.save()
        psp.gender.value = Genders.MALE
        psp.gender.save()
        self.assertEqual(flare.likelihood, Likelihoods.UNLIKELY)
        self.assertEqual(flare.prevalence, Prevalences.LOW)
        # Call the view with the ?updated=True query parameter to test that it doesn't update the Flare
        self.client.get(
            reverse("flares:pseudopatient-detail", kwargs={"pseudopatient": psp.pk, "pk": flare.pk}) + "?updated=True"
        )
        flare.refresh_from_db()
        # Assert that the flare has an unchanged likelihood and prevalence
        self.assertEqual(flare.likelihood, Likelihoods.UNLIKELY)
        self.assertEqual(flare.prevalence, Prevalences.LOW)
        # Call the view with the ?updated=True query parameter to test that it updates the Flare
        self.client.get(reverse("flares:pseudopatient-detail", kwargs={"pseudopatient": psp.pk, "pk": flare.pk}))
        flare.refresh_from_db()
        # Assert that the flare has an updated likelihood and prevalence
        self.assertEqual(flare.likelihood, Likelihoods.LIKELY)
        self.assertEqual(flare.prevalence, Prevalences.HIGH)

    def test__rules(self):
        """Test that django-rules permissions are set correctly and working for the view."""
        # Create a Provider and Admin, each with their own Pseudopatient + Flare
        provider = UserFactory()
        prov_psp = create_psp(provider=provider)
        prov_psp_flare = create_flare(user=prov_psp)
        prov_psp_url = reverse(
            "flares:pseudopatient-detail", kwargs={"pseudopatient": prov_psp.pk, "pk": prov_psp_flare.pk}
        )
        prov_psp_redirect_url = f"{reverse('account_login')}?next={prov_psp_url}"
        admin = AdminFactory()
        admin_psp = create_psp(provider=admin)
        admin_psp_flare = create_flare(user=admin_psp)
        admin_psp_url = reverse(
            "flares:pseudopatient-detail", kwargs={"pseudopatient": admin_psp.pk, "pk": admin_psp_flare.pk}
        )
        redirect_url = reverse(
            "flares:pseudopatient-detail", kwargs={"pseudopatient": admin_psp.pk, "pk": admin_psp_flare.pk}
        )
        admin_psp_redirect_url = f"{reverse('account_login')}?next={redirect_url}"
        # Create an anonymous Pseudopatient + Flare
        anon_psp = create_psp()
        anon_psp_flare = create_flare(user=anon_psp)
        anon_psp_url = reverse(
            "flares:pseudopatient-detail", kwargs={"pseudopatient": anon_psp.pk, "pk": anon_psp_flare.pk}
        )
        # Test that an anonymous user who is not logged in can't see any Pseudopatient
        # with a provider but can see the anonymous Pseudopatient
        self.assertRedirects(self.client.get(prov_psp_url), prov_psp_redirect_url)
        self.assertRedirects(self.client.get(admin_psp_url), admin_psp_redirect_url)
        response = self.client.get(anon_psp_url)
        assert response.status_code == 200
        # Test that the Provider can access the view for his or her own Pseudopatient
        self.client.force_login(provider)
        response = self.client.get(prov_psp_url)
        assert response.status_code == 200
        # Test that the Provider can't access the view for the Admin's Pseudopatient
        response = self.client.get(admin_psp_url)
        assert response.status_code == 403
        # Test that the logged in Provider can see an anonymous Pseudopatient
        response = self.client.get(anon_psp_url)
        assert response.status_code == 200
        # Test that the Admin can access the view for his or her own Pseudopatient
        self.client.force_login(admin)
        response = self.client.get(admin_psp_url)
        assert response.status_code == 200
        # Test that the Admin can't access the view for the Provider's Pseudopatient
        response = self.client.get(prov_psp_url)
        assert response.status_code == 403
        # Test that the logged in Admin can see an anonymous Pseudopatient
        response = self.client.get(anon_psp_url)
        assert response.status_code == 200


class TestFlarePseudopatientList(TestCase):
    """Tests for the FlarePseudopatientList view."""

    def setUp(self):
        self.provider = UserFactory()
        self.admin = AdminFactory()
        self.anon_user = AnonymousUser()
        self.psp = create_psp(provider=self.provider, plus=True)
        for i in range(5):
            create_flare(
                user=self.psp,
                date_started=timezone.now().date() - timedelta(days=5 * i),
                date_ended=timezone.now().date() - timedelta(days=4 * i),
            )
        self.anon_psp = create_psp(plus=True)
        for i in range(5):
            create_flare(
                user=self.anon_psp,
                date_started=timezone.now().date() - timedelta(days=5 * i),
                date_ended=timezone.now().date() - timedelta(days=4 * i),
            )
        self.empty_psp = create_psp(plus=True)
        self.view = FlarePseudopatientList

    def test__dispatch(self):
        """Test that dispatch sets the userattr on the view."""
        # Create a fake request
        request = RequestFactory().get("/fake-url/")
        request.user = self.provider
        # Create a view
        view = self.view()
        kwargs = {"pseudopatient": self.psp.pk}
        # Setup the view
        view.setup(request, **kwargs)
        # Call dispatch
        view.dispatch(request, **kwargs)
        # Assert that the view has a user and object_list attr
        assert hasattr(view, "user")
        assert hasattr(view, "object_list")
        # Assert that the user is the Pseudopatient
        assert view.user == self.psp

    def test__get(self):
        """Test the get() method for the view."""
        # Create a fake request
        request = RequestFactory().get("/fake-url/")
        request.user = self.provider
        # Create a view
        view = self.view()
        # Set the user with the qs so that the related queries are populated on the user
        view.user = flares_user_qs(self.psp.pk).get()
        kwargs = {"pseudopatient": self.psp.pk}
        # Setup the view
        view.setup(request, **kwargs)
        # Call the get() method
        view.get(request, **kwargs)
        # Assert that the object_list is the Pseudopatient's FlareAids
        psp_flares = Flare.objects.filter(user=self.psp).select_related("urate").all()
        for obj in view.object_list:
            assert obj in psp_flares
        for flare in psp_flares:
            assert flare in view.object_list

    def test__get_context_data(self):
        """Test the get_context_data() method for the view."""
        # Create a fake request
        request = RequestFactory().get("/fake-url/")
        request.user = self.provider
        # Create a view
        view = self.view()
        # Set the user with the qs so that the related queries are populated on the user
        view.user = flares_user_qs(self.psp.pk).get()
        kwargs = {"pseudopatient": self.psp.pk}
        # Setup the view
        view.setup(request, **kwargs)
        # Call the get_context_data() method
        qs = flares_user_qs(self.psp.pk).get()
        view.object_list = qs.flares_qs
        context = view.get_context_data(**kwargs)
        # Assert that the context has the correct keys
        assert "patient" in context
        assert "flares" in context
        # Assert that the patient is the Pseudopatient
        assert context["patient"] == self.psp
        # Assert that the flares are the Pseudopatient's FlareAids
        psp_flares = Flare.objects.filter(user=self.psp).select_related("urate").all()
        for obj in context["flares"]:
            assert obj in psp_flares
        for flare in psp_flares:
            assert flare in context["flares"]

    def test__get_permission_object(self):
        """Test that the get_permission_object() method returns the
        view's object, which must have already been set."""
        request = RequestFactory().get("/fake-url/")
        request.user = self.anon_user
        view = self.view()
        view.setup(request, pseudopatient=self.psp.pk)
        view.dispatch(request, pseudopatient=self.psp.pk)
        pm_obj = view.get_permission_object()
        assert pm_obj == view.user

    def test__get_queryset(self):
        """Test the get_queryset() method for the view."""
        request = RequestFactory().get("/fake-url/")
        request.user = self.anon_user
        view = self.view()
        view.setup(request, pseudopatient=self.psp.pk)
        qs = view.get_queryset()
        self.assertTrue(isinstance(qs, QuerySet))
        qs = qs.get()
        self.assertTrue(isinstance(qs, Pseudopatient))
        self.assertEqual(qs, self.psp)
        self.assertTrue(hasattr(qs, "flares_qs"))
        self.assertTrue(hasattr(qs, "pseudopatientprofile"))

    def test__rules(self):
        """Test that django-rules permissions are set correctly and working for the view."""
        # Create a Provider and Admin, each with their own Pseudopatient
        provider = UserFactory()
        prov_psp = create_psp(provider=provider)
        prov_psp_url = reverse("flares:pseudopatient-list", kwargs={"pseudopatient": prov_psp.pk})
        redirect_url = reverse("flares:pseudopatient-list", kwargs={"pseudopatient": prov_psp.pk})
        prov_psp_redirect_url = f"{reverse('account_login')}?next={redirect_url}"
        admin = AdminFactory()
        admin_psp = create_psp(provider=admin)
        admin_psp_url = reverse("flares:pseudopatient-list", kwargs={"pseudopatient": admin_psp.pk})
        redirect_url = reverse("flares:pseudopatient-list", kwargs={"pseudopatient": admin_psp.pk})
        admin_psp_redirect_url = f"{reverse('account_login')}?next={redirect_url}"
        # Create an anonymous Pseudopatient
        anon_psp = create_psp()
        anon_psp_url = reverse("flares:pseudopatient-list", kwargs={"pseudopatient": anon_psp.pk})
        # Test that an anonymous user who is not logged in can't see any Pseudopatient
        # with a provider but can see the anonymous Pseudopatient
        self.assertRedirects(self.client.get(prov_psp_url), prov_psp_redirect_url)
        self.assertRedirects(self.client.get(admin_psp_url), admin_psp_redirect_url)
        response = self.client.get(anon_psp_url)
        assert response.status_code == 200
        # Test that the Provider can access the view for his or her own Pseudopatient
        self.client.force_login(provider)
        response = self.client.get(prov_psp_url)
        assert response.status_code == 200
        # Test that the Provider can't access the view for the Admin's Pseudopatient
        response = self.client.get(admin_psp_url)
        assert response.status_code == 403
        # Test that the logged in Provider can see an anonymous Pseudopatient's list
        response = self.client.get(anon_psp_url)
        assert response.status_code == 200
        # Test that the Admin can access the view for his or her own Pseudopatient
        self.client.force_login(admin)
        response = self.client.get(admin_psp_url)
        assert response.status_code == 200
        # Test that the Admin can't access the view for the Provider's Pseudopatient
        response = self.client.get(prov_psp_url)
        assert response.status_code == 403
        # Test that the logged in Admin can see an anonymous Pseudopatient's list
        response = self.client.get(anon_psp_url)
        assert response.status_code == 200


class TestFlarePseudopatientUpdate(TestCase):
    """Test suite for the FlarePatientUpdate view."""

    def setUp(self):
        self.factory = RequestFactory()
        self.view = FlarePseudopatientUpdate
        self.anon_user = AnonymousUser()
        self.user = create_psp(plus=True)
        for _ in range(10):
            create_psp(plus=True)
        self.psp = create_psp()
        for psp in Pseudopatient.objects.all():
            create_flare(
                user=psp,
                date_started=(timezone.now() - timedelta(days=50)).date(),
                date_ended=(timezone.now() - timedelta(days=45)).date(),
            )

    def test__check_user_onetoones(self):
        """Tests that the view checks for the User's related models."""
        empty_user = create_psp(dateofbirth=False, gender=False)
        view = self.view()
        view.user = empty_user
        self.assertFalse(view.user_has_required_otos)

    def test__ckddetail(self):
        """Tests the ckddetail cached_property."""
        self.assertFalse(self.view().ckddetail)

    def test__dispatch(self):
        """Test the dispatch() method for the view. Should redirect to Pseudopatient Update
        view when the user doesn't have the required 1to1 related models."""
        # Create a Pseudopatient and delete his or her DateOfBirth
        empty_user = create_psp()
        empty_user_Flare = create_flare(user=empty_user)
        empty_user.dateofbirth.delete()

        # Test that the view redirects to the user update view
        self.client.force_login(empty_user)
        response = self.client.get(
            reverse("flares:pseudopatient-update", kwargs={"pseudopatient": empty_user.pk, "pk": empty_user_Flare.pk}),
            follow=True,
        )
        self.assertRedirects(response, reverse("users:pseudopatient-update", kwargs={"pseudopatient": empty_user.pk}))
        message = list(response.context.get("messages"))[0]
        self.assertEqual(message.tags, "error")
        self.assertIn("is missing required information.", message.message)

    def test__goutdetail(self):
        """Tests the goutdetail cached_property."""
        self.assertFalse(self.view().goutdetail)

    def test__get_context_data(self):
        """Test that the non-onetoone and non-medhistory context data is correct."""
        for user in Pseudopatient.objects.all():
            flare = user.flare_set.first()
            request = self.factory.get("/fake-url/")
            if user.profile.provider:
                request.user = user.profile.provider
            else:
                request.user = self.anon_user
            SessionMiddleware(dummy_get_response).process_request(request)
            kwargs = {"pseudopatient": user.pk, "pk": flare.pk}
            response = self.view.as_view()(request, **kwargs)
            assert response.status_code == 200
            assert "flare" in response.context_data
            assert response.context_data["flare"] == flare
            assert "form" in response.context_data
            assert response.context_data["form"].instance == flare
            assert response.context_data["form"].instance._state.adding is False
            assert response.context_data["form"].initial == {
                "onset": flare.onset,
                "redness": flare.redness,
                "joints": flare.joints,
                "medical_evaluation": (
                    True if flare.diagnosed is not None or flare.crystal_analysis or flare.urate else False
                ),
                "urate_check": True if flare.urate else False,
                "diagnosed": flare.diagnosed,
                "aspiration": (
                    True if flare.crystal_analysis is not None else False if flare.diagnosed is not None else None
                ),
                "crystal_analysis": flare.crystal_analysis,
                "date_started": flare.date_started,
                "date_ended": flare.date_ended,
            }
            assert (
                response.context_data["urate_form"].initial == {"value": flare.urate.value}
                if flare.urate
                else {"value": None}
            )
            assert "patient" in response.context_data
            assert response.context_data["patient"] == user

    def test__get_context_data_onetoones(self):
        """Test that the context data includes the user's
        related models."""
        for user in Pseudopatient.objects.prefetch_related("flare_set").all():
            flare = user.flare_set.first()
            request = self.factory.get("/fake-url/")
            if user.profile.provider:
                request.user = user.profile.provider
            else:
                request.user = self.anon_user
            SessionMiddleware(dummy_get_response).process_request(request)
            kwargs = {"pseudopatient": user.pk, "pk": flare.pk}
            response = self.view.as_view()(request, **kwargs)
            assert response.status_code == 200
            assert "age" in response.context_data
            assert response.context_data["age"] == age_calc(user.dateofbirth.value)
            assert "gender" in response.context_data
            assert response.context_data["gender"] == user.gender.value
            assert "urate_form" in response.context_data
            if flare.urate:
                assert response.context_data["urate_form"].instance == flare.urate
                assert response.context_data["urate_form"].instance._state.adding is False
                assert response.context_data["urate_form"].initial == {"value": flare.urate.value}
            else:
                assert response.context_data["urate_form"].instance._state.adding is True
                assert response.context_data["urate_form"].initial == {"value": None}
            if flare.aki:
                assert "aki_form" in response.context_data
                assert response.context_data["aki_form"].instance == flare.aki
                assert response.context_data["aki_form"].instance._state.adding is False
                assert response.context_data["aki_form"].initial == {"value": "True", "status": flare.aki.status}
            else:
                assert response.context_data["aki_form"].instance._state.adding is True
                assert response.context_data["aki_form"].initial == {"value": None, "status": Aki.Statuses.ONGOING}

    def test__get_context_data_medhistorys(self):
        """Test that the context data includes the user's
        related models."""
        for user in Pseudopatient.objects.all():
            flare = user.flare_set.first()
            request = self.factory.get("/fake-url/")
            if user.profile.provider:
                request.user = user.profile.provider
            else:
                request.user = self.anon_user
            SessionMiddleware(dummy_get_response).process_request(request)
            kwargs = {"pseudopatient": user.pk, "pk": flare.pk}
            response = self.view.as_view()(request, **kwargs)
            assert response.status_code == 200
            for mh in user.medhistory_set.all():
                if mh.medhistorytype in FLARE_MEDHISTORYS:
                    if (
                        not mh.medhistorytype == MedHistoryTypes.MENOPAUSE
                        and not mh.medhistorytype == MedHistoryTypes.GOUT
                    ):
                        assert f"{mh.medhistorytype}_form" in response.context_data
                        assert response.context_data[f"{mh.medhistorytype}_form"].instance == mh
                        assert response.context_data[f"{mh.medhistorytype}_form"].instance._state.adding is False
                        assert response.context_data[f"{mh.medhistorytype}_form"].initial == {
                            f"{mh.medhistorytype}-value": True
                        }
                else:
                    assert f"{mh.medhistorytype}_form" not in response.context_data
            for mhtype in FLARE_MEDHISTORYS:
                if mhtype == MedHistoryTypes.MENOPAUSE or mhtype == MedHistoryTypes.GOUT:
                    assert f"{mhtype}_form" not in response.context_data
                else:
                    assert f"{mhtype}_form" in response.context_data
                    if mhtype not in user.medhistory_set.values_list("medhistorytype", flat=True):
                        assert response.context_data[f"{mhtype}_form"].instance._state.adding is True
                        if mhtype == MedHistoryTypes.MENOPAUSE:
                            if user.gender.value == Genders.FEMALE:
                                age = age_calc(user.dateofbirth.value)
                                if age >= 60:
                                    assert response.context_data[f"{mhtype}_form"].initial == {f"{mhtype}-value": True}
                                elif age >= 40 and age < 60:
                                    assert response.context_data[f"{mhtype}_form"].initial == {
                                        f"{mhtype}-value": False
                                    }
                                else:
                                    assert response.context_data[f"{mhtype}_form"].initial == {f"{mhtype}-value": None}
            assert "ckddetail_form" in response.context_data
            assert "baselinecreatinine_form" in response.context_data
            assert "goutdetail_form" not in response.context_data

    def test__get_form_kwargs(self):
        # Create a fake request
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        view = self.view(request=request)
        # Create kwargs for view
        kwargs = {"pseudopatient": self.user.pk, "pk": self.user.flare_set.first().pk}
        # Setup the view
        view.setup(request, **kwargs)
        view.set_forms()
        # Set the object on the view
        view.object = view.get_object()
        # Delete the user attr on the view because it will be set by the get_object() method
        # and is checked for with hasattr(), which will return True even if it is None
        delattr(view, "user")
        # Get the form kwargs
        form_kwargs = view.get_form_kwargs()
        # Test form kwargs are correct
        form_kwargs = view.get_form_kwargs()
        self.assertIn("patient", form_kwargs)
        self.assertEqual(form_kwargs["patient"], self.user)

    def test__get_initial(self):
        """Test the get_initial() method for the view."""
        # Iterate over all the flares with a user attr
        for flare in Flare.objects.filter(Q(user__isnull=False)).all():
            # Create a fake request
            request = self.factory.get("/fake-url/")
            request.user = self.anon_user
            # Create a fake kwargs dict
            kwargs = {"pseudopatient": flare.user.pk, "pk": flare.pk}
            # Create the view
            view = self.view(request=request)
            # https://stackoverflow.com/questions/33645780/how-to-unit-test-methods-inside-djangos-class-based-views
            view.setup(request, **kwargs)
            view.object = view.get_object()
            # Get the initial data
            initial = view.get_initial()
            # Assert that the initial data is a dict
            self.assertTrue(isinstance(initial, dict))
            # Assert that the initial data has the correct key/val pairs
            if flare.crystal_analysis:
                self.assertEqual(initial["aspiration"], True)
            elif flare.diagnosed is not None:
                self.assertIsNotNone(initial["aspiration"])
            else:
                self.assertEqual(initial["aspiration"], None)
            if flare.urate:
                self.assertEqual(initial["urate_check"], True)
            else:
                self.assertEqual(initial["urate_check"], False)

    def test__get_object(self):
        flareless_user = create_psp()
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        kwargs = {"pseudopatient": flareless_user.pk, "pk": 1}
        view = self.view(request=request)
        view.setup(request, **kwargs)
        with self.assertRaises(ObjectDoesNotExist):
            view.get_object()
        # Create a flare for the user
        flare = create_flare(user=flareless_user)
        kwargs = {"pseudopatient": flareless_user.pk, "pk": flare.pk}
        view = self.view(request=request)
        view.setup(request, **kwargs)
        view.object = view.get_object()
        self.assertTrue(isinstance(view.object, Flare))
        self.assertEqual(view.object.user, flareless_user)

    def test__get_permission_object(self):
        """Test the get_permission_object() method for the view."""
        request = self.factory.get("/fake-url/")
        request.user = self.user
        flare = self.user.flare_set.first()
        kwargs = {"pseudopatient": self.user.pk, "pk": flare.pk}
        view = self.view()
        # https://stackoverflow.com/questions/33645780/how-to-unit-test-methods-inside-djangos-class-based-views
        view.setup(request, **kwargs)
        view.object = view.get_object()
        permission_object = view.get_permission_object()
        self.assertEqual(permission_object, flare)

    def test__get_user_queryset(self):
        """Test the get_user_queryset() method for the view."""
        # Set a flare var and add a Urate to it for consistency
        flare = self.user.flare_set.first()
        flare.urate = UrateFactory(user=self.user)
        flare.save()
        request = self.factory.get("/fake-url/")
        kwargs = {"pseudopatient": self.user.pk, "pk": self.user.flare_set.first().pk}
        view = self.view()
        # https://stackoverflow.com/questions/33645780/how-to-unit-test-methods-inside-djangos-class-based-views
        view.setup(request, **kwargs)
        qs = view.get_user_queryset(view.kwargs["pseudopatient"])
        self.assertTrue(isinstance(qs, QuerySet))
        with CaptureQueriesContext(connection) as queries:
            qs = qs.get()
        self.assertTrue(isinstance(qs, User))
        self.assertTrue(hasattr(qs, "flares_qs"))
        self.assertTrue(isinstance(qs.flares_qs, list))
        self.assertIn(flare, qs.flares_qs)
        flare = next(iter(flare for flare in qs.flares_qs if flare is flare))
        if flare.aki:
            self.assertTrue(isinstance(flare.aki, Aki))
            self.assertTrue(hasattr(flare.aki, "creatinines_qs"))
            self.assertEqual(len(queries.captured_queries), 5)
        else:
            self.assertFalse(hasattr(flare, "aki"))
            self.assertEqual(len(queries.captured_queries), 3)
        self.assertTrue(hasattr(flare, "urate"))
        self.assertTrue(isinstance(flare.urate, Urate))
        self.assertEqual(flare.urate, flare.urate)
        self.assertTrue(hasattr(qs, "medhistorys_qs"))
        self.assertTrue(hasattr(qs, "dateofbirth"))
        self.assertTrue(hasattr(qs, "gender"))

    def test__post_populate_oto_forms(self):
        """Test the post_populate_oto_forms() method for the view."""
        # Iterate over the Pseudopatients
        for user in Pseudopatient.objects.all():
            # Fetch the Flare, each User will only have 1
            flare = user.flare_set.first()
            # Create a fake POST request
            request = self.factory.post("/fake-url/")
            request.user = user.profile.provider if user.profile.provider else self.anon_user
            # Call the view and get the object
            view = self.view()
            view.setup(request, **{"pseudopatient": user.pk, "pk": flare.pk})
            view.set_forms()
            view.object = view.get_object()
            # Create a onetoone_forms dict with the method for testing against
            view.post_populate_oto_forms()
            for onetoone, oto_form in view.oto_forms.items():
                # Assert that the onetoone_forms dict has the correct keys
                self.assertIn(f"{onetoone}", view.OTO_FORMS.keys())
                # Assert that the onetoone_forms dict has the correct values
                self.assertTrue(isinstance(oto_form, view.OTO_FORMS[onetoone]))
                # Assert that the onetoone_forms dict has the correct initial data
                self.assertEqual(
                    oto_form.initial["value"],
                    ("True" if onetoone == "aki" else getattr(view.object, onetoone, None).value)
                    if getattr(view.object, onetoone, False)
                    else None,
                )
                if onetoone == "aki":
                    self.assertIn("status", oto_form.initial)

    def test__post_process_oto_forms(self):
        """Test the post_process_oto_forms() method for the view."""

        def convert_str_bool_to_bool(val: str) -> bool:
            return True if val == "True" else False if val == "False" else val

        # Iterate over the Pseudopatients
        for user in Pseudopatient.objects.all():
            # Fetch the Flare, each User will only have 1
            flare = user.flare_set.first()
            data = flare_data_factory(user=user, flare=flare)
            # Create a fake POST request
            request = self.factory.post("/fake-url/", data)
            request.user = user.profile.provider if user.profile.provider else self.anon_user
            # Call the view and get the object
            view = self.view()
            view.setup(request, **{"pseudopatient": user.pk, "pk": flare.pk})
            view.set_forms()
            view.object = view.get_object()
            # Create a onetoone_forms dict with the method for testing against
            view.post_populate_oto_forms()
            for form in view.oto_forms.values():
                assert form.is_valid()

            # Call the post_process_oto_forms() method and assign to new lists
            # of onetoones to save and delete to test against
            view.post_process_oto_forms()
            # Iterate over all the onetoones to check if they are marked as to be saved or deleted correctly
            for onetoone, oto_form in view.oto_forms.items():
                initial = oto_form.initial.get("value", None)
                # If the form is adding a new object, assert that there's no initial data
                if oto_form.instance._state.adding:
                    assert not initial
                data_val = data.get(f"{onetoone}-value", "")
                # Check if there was no pre-existing onetoone and there is no data to create a new one
                filtered_otos_to_save = [oto for oto in view.oto_2_save if oto.__class__.__name__.lower() == onetoone]
                filtered_otos_to_rem = [oto for oto in view.oto_2_rem if oto.__class__.__name__.lower() == onetoone]
                if not initial and (not convert_str_bool_to_bool(data_val) or data_val == ""):
                    # Should not be marked for save or deletion
                    assert not next(iter(onetoone for onetoone in filtered_otos_to_save), None) and not next(
                        iter(onetoone for onetoone in filtered_otos_to_rem), None
                    )
                # If there was no pre-existing onetoone but there is data to create a new one
                elif not initial and (convert_str_bool_to_bool(data_val) and data_val != ""):
                    # Should be marked for save and not deletion
                    assert next(iter(onetoone for onetoone in filtered_otos_to_save)) and not next(
                        iter(onetoone for onetoone in filtered_otos_to_rem), None
                    )
                # If there was a pre-existing onetoone but the data is not present in the POST data
                elif initial and (not convert_str_bool_to_bool(data_val) or data_val == ""):
                    # Should be marked for deletion and not save
                    assert not next(iter(onetoone for onetoone in filtered_otos_to_save), None) and next(
                        iter(onetoone for onetoone in filtered_otos_to_rem)
                    )
                # If there is a pre-existing object and there is data in the POST request
                elif initial and (convert_str_bool_to_bool(data_val) and data_val != ""):
                    initial_status = oto_form.initial.get("status", None)
                    data_status = data.get(f"{onetoone}-status", None)
                    # If the data changed, the object should be marked for saving
                    if initial != data_val or initial_status != data_status:
                        assert next(iter(onetoone for onetoone in filtered_otos_to_save), None) and not next(
                            iter(onetoone for onetoone in filtered_otos_to_rem), None
                        )
                    # Otherwise it should not be marked for saving or
                    # deletion and the form's changed_data dict should be empty
                    else:
                        assert (
                            not next(iter(onetoone for onetoone in filtered_otos_to_save), None)
                            and not next(iter(onetoone for onetoone in filtered_otos_to_rem), None)
                            and not view.oto_forms[f"{onetoone}"].changed_data
                        )
                        assert view.oto_forms[f"{onetoone}"].changed_data == []

    def test__post(self):
        """Test the post() method for the view."""
        request = self.factory.post("/fake-url/")
        if self.user.profile.provider:  # type: ignore
            request.user = self.user.profile.provider  # type: ignore
        else:
            request.user = self.anon_user
        SessionMiddleware(dummy_get_response).process_request(request)
        flare = self.user.flare_set.first()
        kwargs = {"pseudopatient": self.user.pk, "pk": flare.pk}
        response = self.view.as_view()(request, **kwargs)
        assert response.status_code == 200

    def test__post_updates_medhistorys(self):
        """Test that the post() method updates the user's medhistorys
        correctly."""
        # Iterate over the Pseudopatients
        for user in Pseudopatient.objects.all():
            # Copy the user's medhistorys to a list
            medhistorys = list(user.medhistory_set.all())
            # Fetch the Flare, each User will only have 1
            flare = user.flare_set.first()
            # Create some fake flare data
            data = flare_data_factory(user=user, flare=flare)
            # Call the view
            response = self.client.post(
                reverse("flares:pseudopatient-update", kwargs={"pseudopatient": user.pk, "pk": flare.pk}), data=data
            )
            forms_print_response_errors(response)
            assert response.status_code == 302
            # Assert that the medhistorys were updated correctly
            for mh in medhistorys:
                val = data.get(f"{mh.medhistorytype}-value", None)
                if (
                    mh.medhistorytype in FLARE_MEDHISTORYS
                    and (val is False or val is None or val == "")
                    # Need to exclude GOUT and MENOPAUSE because they aren't in the form for modification
                    and mh.medhistorytype != MedHistoryTypes.MENOPAUSE
                    and mh.medhistorytype != MedHistoryTypes.GOUT
                ):
                    self.assertFalse(user.medhistory_set.filter(medhistorytype=mh.medhistorytype).exists())
                else:
                    self.assertTrue(user.medhistory_set.filter(medhistorytype=mh.medhistorytype).exists())
            # Iterate over the data for medhistory values and make sure they were created
            for key, val in data.items():
                mh = key.split("-")[0]
                if mh in FLARE_MEDHISTORYS and (val is not False and val is not None and val != ""):
                    self.assertTrue(MedHistory.objects.filter(medhistorytype=mh, user=user).exists())

    def test__post_creates_urate(self):
        """Test that the post() method creates a urate when provided the appropriate data."""
        users_first_flare = self.user.flare_set.first()
        # Create a flare with a user and no urate
        flare = create_flare(
            user=self.user,
            urate=None,
            date_started=(users_first_flare.date_started - timedelta(days=10)),
            date_ended=(users_first_flare.date_started - timedelta(days=5)),
        )
        # Create some fake flare data
        data = flare_data_factory(user=self.user, flare=flare)
        # Add the urate data
        data.update(
            {
                "urate_check": True,
                "urate-value": Decimal("5.0"),
            }
        )
        # Call the view
        response = self.client.post(
            reverse("flares:pseudopatient-update", kwargs={"pseudopatient": self.user.pk, "pk": flare.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302
        # Assert that the urate was created
        flare.refresh_from_db()
        self.assertTrue(getattr(flare, "urate", None))
        urate = flare.urate
        self.assertEqual(urate.value, Decimal("5.0"))
        self.assertEqual(flare.urate.user, self.user)

    def test__post_updates_urate(self):
        users_first_flare = self.user.flare_set.first()
        # Create a flare with a user and a urate
        flare = create_flare(
            user=self.user,
            urate=UrateFactory(user=self.user, value=Decimal("5.0")),
            date_started=(users_first_flare.date_started - timedelta(days=10)),
            date_ended=(users_first_flare.date_started - timedelta(days=1)),
        )
        # Create some fake flare data
        data = flare_data_factory(user=self.user, flare=flare)
        # Add the urate data
        data.update(
            {
                "urate_check": True,
                "urate-value": Decimal("6.0"),
            }
        )
        # Call the view
        response = self.client.post(
            reverse("flares:pseudopatient-update", kwargs={"pseudopatient": self.user.pk, "pk": flare.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302
        # Assert that the urate was updated
        flare.refresh_from_db()
        self.assertTrue(getattr(flare, "urate", None))
        urate = flare.urate
        self.assertEqual(urate.value, Decimal("6.0"))

    def test__post_deletes_urate(self):
        """Test that the post() method deletes a urate when provided the appropriate data."""
        users_first_flare = self.user.flare_set.first()
        urate = UrateFactory(user=self.user, value=Decimal("5.0"))
        # Create a flare with a user and a urate
        flare = create_flare(
            user=self.user,
            urate=urate,
            date_started=(users_first_flare.date_started - timedelta(days=10)),
            date_ended=(users_first_flare.date_started - timedelta(days=1)),
        )
        # Create some fake flare data
        data = flare_data_factory(user=self.user, flare=flare)
        # Add the urate data
        data.update(
            {
                "urate_check": False,
                "urate-value": "",
            }
        )
        # Call the view
        response = self.client.post(
            reverse("flares:pseudopatient-update", kwargs={"pseudopatient": self.user.pk, "pk": flare.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302
        # Assert that the urate was updated
        flare.refresh_from_db()
        self.assertIsNone(getattr(flare, "urate", None))
        self.assertFalse(Urate.objects.filter(pk=urate.pk).exists())

    def test__post_returns_errors(self):
        """Test that the post() method returns the correct errors when the data is invalid."""
        # Get a flare for the Pseudopatient
        flare = self.psp.flare_set.first()
        # Create some fake data and update it to have a urate_check but no urate-value
        data = flare_data_factory(self.psp)
        data.update(
            {
                "medical_evaluation": True,
                "aspiration": False,
                "urate_check": True,
                "urate-value": "",
            }
        )
        # Post the data
        response = self.client.post(
            reverse("flares:pseudopatient-update", kwargs={"pseudopatient": self.psp.pk, "pk": flare.pk}), data=data
        )
        assert response.status_code == 200
        forms_print_response_errors(response)
        # Assert that the form has an error on the urate_check field
        self.assertTrue(response.context_data["form"].errors)
        self.assertEqual(
            response.context_data["form"].errors["urate_check"][0],
            "If the serum uric acid was checked, please tell us the value! \
If you don't know the value, please uncheck the Uric Acid Lab Check box.",
        )
        # Assert that the urate_form has an error on the value field
        self.assertTrue(response.context_data["urate_form"].errors)
        self.assertEqual(
            response.context_data["urate_form"].errors["value"][0],
            "If the serum uric acid was checked, please tell us the value! \
If you don't know the value, please uncheck the Uric Acid Lab Check box.",
        )
        # Change the fake data such that the urate stuff passes but that diagnosed is True but aspiration is
        # not selected, which should result in an error on the aspiration field
        data.update(
            {
                "urate_check": True,
                "urate-value": Decimal("5.0"),
                "diagnosed": DiagnosedChoices.YES,
                "aspiration": "",
            }
        )
        # Post the data
        response = self.client.post(
            reverse("flares:pseudopatient-update", kwargs={"pseudopatient": self.psp.pk, "pk": flare.pk}), data=data
        )
        assert response.status_code == 200
        forms_print_response_errors(response)
        # Assert that the form has an error on the aspiration field
        self.assertTrue(response.context_data["form"].errors)
        self.assertIn(
            "Joint aspiration must be selected",
            response.context_data["form"].errors["aspiration"][0],
        )

    def test__post_returns_high_likelihood_prevalence_flare(self):
        """Test that a flare is updated with a high likelihood and prevalence when the
        data indicates a high likelihood and prevalence flare."""
        # Modify Pseudopatient related demographic objects to facilitate high likelihood/prevalence
        self.psp.dateofbirth.value = timezone.now().date() - timedelta(days=365 * 64)
        self.psp.dateofbirth.save()
        self.psp.gender.value = Genders.MALE
        self.psp.gender.save()
        flare = Flare.objects.filter(user=self.psp).first()
        # Create a fake data dict
        data = flare_data_factory(self.psp)
        # Modify data entries to indicate a high likelihood and prevalence flare
        data.update(
            {
                "onset": True,
                "redness": True,
                "joints": [LimitedJointChoices.MTP1L, LimitedJointChoices.MTP1R],
                "urate_check": True,
                "urate-value": Decimal("9.0"),
                "diagnosed": DiagnosedChoices.YES,
                "aspiration": True,
                "crystal_analysis": True,
                "date_started": timezone.now().date() - timedelta(days=35),
                "date_ended": timezone.now().date() - timedelta(days=25),
            }
        )
        # Post the data
        response = self.client.post(
            reverse("flares:pseudopatient-update", kwargs={"pseudopatient": self.psp.pk, "pk": flare.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302
        flare.refresh_from_db()
        # Assert that the flare has a high likelihood and prevalence
        self.assertEqual(flare.likelihood, Likelihoods.LIKELY)
        self.assertEqual(flare.prevalence, Prevalences.HIGH)

    def test__post_returns_moderate_likelihood_prevalence_flare(self):
        """Test that a flare is created with a moderate likelihood and prevalence when the
        data indicates a moderate likelihood and prevalence flare."""

        # Get a flare for the Pseudopatient
        flare = create_flare(user=True, mhs=[], gender=Genders.MALE)
        # Create a fake data dict
        data = flare_data_factory(flare.user)
        # Modify data entries to indicate a moderate likelihood and prevalence flare
        data.update(
            {
                "onset": True,
                "redness": False,
                "joints": [LimitedJointChoices.KNEER],
                "date_started": timezone.now().date() - timedelta(days=7),
                "date_ended": "",
                "medical_evaluation": True,
                "urate_check": True,
                "urate-value": Decimal("5.0"),
                "diagnosed": DiagnosedChoices.YES,
                "aspiration": False,
                "crystal_analysis": "",
            }
        )
        # Post the data
        response = self.client.post(
            reverse("flares:pseudopatient-update", kwargs={"pseudopatient": flare.user.pk, "pk": flare.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302
        flare.refresh_from_db()
        # Assert that the flare has a moderate likelihood and prevalence
        self.assertEqual(flare.prevalence, Prevalences.MEDIUM)
        self.assertEqual(flare.likelihood, Likelihoods.EQUIVOCAL)

    def test__post_returns_low_likelihood_prevalence_flare(self):
        """Test that a flare is created with a low likelihood and prevalence when the
        data indicates a low likelihood and prevalence flare."""
        # Modify Pseudopatient related demographic objects to facilitate low likelihood/prevalence
        self.psp.dateofbirth.value = timezone.now().date() - timedelta(days=365 * 24)
        self.psp.dateofbirth.save()
        self.psp.gender.value = Genders.FEMALE
        self.psp.gender.save()
        # Get a flare for the Pseudopatient
        flare = self.psp.flare_set.first()
        # Create a fake data dict
        data = flare_data_factory(self.psp)
        # Modify data entries to indicate a low likelihood and prevalence flare
        data.update(
            {
                f"{MedHistoryTypes.CKD}-value": False,
                "onset": False,
                "redness": False,
                "joints": [LimitedJointChoices.HIPL],
                "medical_evaluation": True,
                "urate_check": True,
                "urate-value": Decimal("5.0"),
                "diagnosed": DiagnosedChoices.NO,
                "aspiration": False,
                "crystal_analysis": "",
                "date_started": timezone.now().date() - timedelta(days=135),
                "date_ended": timezone.now().date() - timedelta(days=5),
            }
        )
        # Post the data
        response = self.client.post(
            reverse("flares:pseudopatient-update", kwargs={"pseudopatient": self.psp.pk, "pk": flare.pk}), data=data
        )
        forms_print_response_errors(response)
        assert response.status_code == 302
        flare.refresh_from_db()
        # Assert that the flare has a low likelihood and prevalence
        self.assertEqual(flare.likelihood, Likelihoods.UNLIKELY)
        self.assertEqual(flare.prevalence, Prevalences.LOW)

    def test__rules(self):
        """Test that django-rules permissions are set correctly and working for the view."""
        # Create a Provider and Admin, each with their own Pseudopatient + Flare
        provider = UserFactory()
        prov_psp = create_psp(provider=provider)
        prov_psp_flare = create_flare(user=prov_psp)
        prov_psp_url = reverse(
            "flares:pseudopatient-update", kwargs={"pseudopatient": prov_psp.pk, "pk": prov_psp_flare.pk}
        )
        prov_next_url = quote(
            reverse("flares:pseudopatient-update", kwargs={"pseudopatient": prov_psp.pk, "pk": prov_psp_flare.pk})
        )
        prov_psp_redirect_url = f"{reverse('account_login')}?next={prov_next_url}"
        admin = AdminFactory()
        admin_psp = create_psp(provider=admin)
        admin_psp_flare = create_flare(user=admin_psp)
        admin_psp_url = reverse(
            "flares:pseudopatient-update", kwargs={"pseudopatient": admin_psp.pk, "pk": admin_psp_flare.pk}
        )
        admin_next_url = quote(
            reverse("flares:pseudopatient-update", kwargs={"pseudopatient": admin_psp.pk, "pk": admin_psp_flare.pk})
        )
        admin_psp_redirect_url = f"{reverse('account_login')}?next={admin_next_url}"
        # Create an anonymous Pseudopatient + Flare
        anon_psp = create_psp()
        anon_psp_flare = create_flare(user=anon_psp)
        anon_psp_url = reverse(
            "flares:pseudopatient-update", kwargs={"pseudopatient": anon_psp.pk, "pk": anon_psp_flare.pk}
        )
        # Test that an anonymous user who is not logged in can't see any Pseudopatient
        # with a provider but can see the anonymous Pseudopatient
        self.assertRedirects(self.client.get(prov_psp_url), prov_psp_redirect_url)
        self.assertRedirects(self.client.get(admin_psp_url), admin_psp_redirect_url)
        response = self.client.get(anon_psp_url)
        assert response.status_code == 200
        # Test that the Provider can access the view for his or her own Pseudopatient
        self.client.force_login(provider)
        response = self.client.get(prov_psp_url)
        assert response.status_code == 200
        # Test that the Provider can't access the view for the Admin's Pseudopatient
        response = self.client.get(admin_psp_url)
        assert response.status_code == 403
        # Test that the logged in Provider can see an anonymous Pseudopatient
        response = self.client.get(anon_psp_url)
        assert response.status_code == 200
        # Test that the Admin can access the view for his or her own Pseudopatient
        self.client.force_login(admin)
        response = self.client.get(admin_psp_url)
        assert response.status_code == 200
        # Test that the Admin can't access the view for the Provider's Pseudopatient
        response = self.client.get(prov_psp_url)
        assert response.status_code == 403
        # Test that the logged in Admin can see an anonymous Pseudopatient
        response = self.client.get(anon_psp_url)
        assert response.status_code == 200

    def test__post_aki_on_dialysis_raises_ValidationError(self) -> None:
        flare = self.psp.flare_set.first()
        flare_data = flare_data_factory(user=self.psp, otos={"aki": True})
        flare_data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": True,
                "dialysis_type": DialysisChoices.HEMODIALYSIS,
                "dialysis_duration": DialysisDurations.LESSTHANSIX,
            }
        )
        response = self.client.post(
            reverse("flares:pseudopatient-update", kwargs={"pseudopatient": self.psp.pk, "pk": flare.pk}), flare_data
        )
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 200)
        self.assertIn("value", response.context_data["aki_form"].errors)
        self.assertIn(
            "If the patient is on",
            response.context_data["aki_form"].errors["value"][0],
        )
        self.assertIn("dialysis", response.context_data["ckddetail_form"].errors)
        self.assertIn(
            "If the patient is on",
            response.context_data["ckddetail_form"].errors["dialysis"][0],
        )

    def test__post_raises_ValidationError_when_date_started_or_ended_conflicts_with_another_flare(self):
        flare = self.psp.flare_set.last()
        conflicting_flare = create_flare(
            user=self.psp,
            date_started=flare.date_started - timedelta(days=10),
            date_ended=flare.date_started - timedelta(days=5),
        )
        flare_data = flare_data_factory(flare=flare)
        flare_data.update(
            {
                "date_started": conflicting_flare.date_started,
                "date_ended": conflicting_flare.date_ended,
            }
        )
        response = self.client.post(
            reverse("flares:pseudopatient-update", kwargs={"pseudopatient": self.psp.pk, "pk": flare.pk}),
            data=flare_data,
        )
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data["form"].errors)
        self.assertIn("date_started", response.context_data["form"].errors)
        self.assertIn("date_ended", response.context_data["form"].errors)


class TestFlareUpdate(TestCase):
    def setUp(self):
        self.flare = create_flare(gender=GenderFactory(value=Genders.MALE))
        self.factory = RequestFactory()
        self.view: FlareUpdate = FlareUpdate
        self.flare_data = {
            "crystal_analysis": True,
            "date_ended": "",
            "date_started": self.flare.date_started,
            "dateofbirth-value": age_calc(timezone.now().date() - timedelta(days=365 * 64)),
            "gender-value": self.flare.gender.value,
            "joints": self.flare.joints,
            "onset": True,
            "redness": True,
            "medical_evaluation": True,
            "urate_check": True,
            "urate-value": Decimal("14.4"),
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.GOUT}-value": False,
            "diagnosed": DiagnosedChoices.YES,
            "aspiration": True,
        }

    def test__attrs(self):
        self.assertIn("dateofbirth", self.view.OTO_FORMS)
        self.assertEqual(self.view.OTO_FORMS["dateofbirth"], DateOfBirthForm)
        self.assertIn("gender", self.view.OTO_FORMS)
        self.assertEqual(self.view.OTO_FORMS["gender"], GenderForm)
        self.assertIn("urate", self.view.OTO_FORMS)
        self.assertEqual(self.view.OTO_FORMS["urate"], UrateFlareForm)
        self.assertIn(MedHistoryTypes.ANGINA, self.view.MEDHISTORY_FORMS)
        self.assertEqual(self.view.MEDHISTORY_FORMS[MedHistoryTypes.ANGINA], AnginaForm)
        self.assertIn(MedHistoryTypes.CAD, self.view.MEDHISTORY_FORMS)
        self.assertEqual(self.view.MEDHISTORY_FORMS[MedHistoryTypes.CAD], CadForm)
        self.assertIn(MedHistoryTypes.CHF, self.view.MEDHISTORY_FORMS)
        self.assertEqual(self.view.MEDHISTORY_FORMS[MedHistoryTypes.CHF], ChfForm)
        self.assertIn(MedHistoryTypes.CKD, self.view.MEDHISTORY_FORMS)
        self.assertEqual(self.view.MEDHISTORY_FORMS[MedHistoryTypes.CKD], CkdForm)
        self.assertIn(MedHistoryTypes.GOUT, self.view.MEDHISTORY_FORMS)
        self.assertEqual(self.view.MEDHISTORY_FORMS[MedHistoryTypes.GOUT], GoutForm)
        self.assertIn(MedHistoryTypes.HEARTATTACK, self.view.MEDHISTORY_FORMS)
        self.assertEqual(self.view.MEDHISTORY_FORMS[MedHistoryTypes.HEARTATTACK], HeartattackForm)
        self.assertIn(MedHistoryTypes.STROKE, self.view.MEDHISTORY_FORMS)
        self.assertEqual(self.view.MEDHISTORY_FORMS[MedHistoryTypes.STROKE], StrokeForm)
        self.assertIn(MedHistoryTypes.PVD, self.view.MEDHISTORY_FORMS)
        self.assertEqual(self.view.MEDHISTORY_FORMS[MedHistoryTypes.PVD], PvdForm)

    def test__dispatch_redirects_if_flare_user(self):
        """Test that the dispatch() method redirects to the Pseudopatient DetailView if the
        Flare has a user."""
        user_f = create_flare(user=True)
        request = self.factory.get("/fake-url/")
        request.user = AnonymousUser()
        response = self.view.as_view()(request, pk=user_f.pk)
        assert response.status_code == 302
        assert response.url == reverse(
            "flares:pseudopatient-update", kwargs={"pseudopatient": user_f.user.pk, "pk": user_f.pk}
        )

    def test__get_context_data(self):
        """Test the get_context_data() method for the view."""

        # Test that the context data is correct
        request = self.factory.get(f"/flares/update/{self.flare.pk}")
        request.user = AnonymousUser()
        SessionMiddleware(dummy_get_response).process_request(request)
        response = FlareUpdate.as_view()(request, pk=self.flare.pk)
        self.assertIsInstance(response.context_data, dict)  # type: ignore
        for medhistory in FLARE_MEDHISTORYS:
            self.assertIn(f"{medhistory}_form", response.context_data)  # type: ignore
            self.assertIsInstance(
                response.context_data[f"{medhistory}_form"], self.view.MEDHISTORY_FORMS[medhistory]  # type: ignore
            )
            if response.context_data[
                f"{medhistory}_form"
            ].instance._state.adding:  # pylint: disable=w0212, line-too-long # noqa: E501
                self.assertIsInstance(
                    response.context_data[f"{medhistory}_form"].instance,  # type: ignore
                    self.view.MEDHISTORY_FORMS[medhistory]._meta.model,
                )
            else:
                self.assertIn(
                    response.context_data[f"{medhistory}_form"].instance, self.flare.medhistory_set.all()  # type: ignore, line-too-long # noqa: E501
                )
        self.assertIn("dateofbirth_form", response.context_data)  # type: ignore
        self.assertIsInstance(
            response.context_data["dateofbirth_form"], self.view.OTO_FORMS["dateofbirth"]  # type: ignore
        )

        self.assertEqual(response.context_data["dateofbirth_form"].instance, self.flare.dateofbirth)  # type: ignore
        self.assertIsInstance(response.context_data["gender_form"], self.view.OTO_FORMS["gender"])  # type: ignore
        self.assertIsInstance(
            response.context_data["gender_form"].instance, self.view.OTO_FORMS["gender"]._meta.model  # type: ignore
        )
        self.assertEqual(response.context_data["gender_form"].instance, self.flare.gender)  # type: ignore
        self.assertIsInstance(response.context_data["urate_form"], self.view.OTO_FORMS["urate"])  # type: ignore
        self.assertIsInstance(
            response.context_data["urate_form"].instance, self.view.OTO_FORMS["urate"]._meta.model  # type: ignore
        )
        if getattr(self.flare, "urate", None):
            self.assertEqual(response.context_data["urate_form"].instance, self.flare.urate)
        else:
            self.assertTrue(response.context_data["urate_form"].instance._state.adding)  # type: ignore

    def test__post(self):
        """Test that a POST request to the view redirects to the Flare DetailView."""
        data = flare_data_factory()
        response = self.client.post(reverse("flares:update", kwargs={"pk": self.flare.pk}), data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        updated_url_str = reverse("flares:detail", kwargs={"pk": self.flare.pk})
        updated_url_str += "?updated=True"
        self.assertEqual(response.url, updated_url_str)

    def test__post_updates_medhistorys(self):
        """Test that the post method adds medhistorys to the Flare."""

        # Iterate over some flares
        for flare in Flare.objects.filter(user__isnull=True).all()[:10]:
            # Create some fake data and calculate the difference between the current and intended MedHistorys
            # on the Flare
            data = flare_data_factory()
            mh_count = flare.medhistory_set.count()
            mh_diff = medhistory_diff_obj_data(flare, data, FLARE_MEDHISTORYS)
            # Post the data
            response = self.client.post(reverse("flares:update", kwargs={"pk": flare.pk}), data)
            forms_print_response_errors(response)
            self.assertEqual(response.status_code, 302)
            # Assert that the number of MedHistory objects in the Flare's medhistory_set changed correctly
            self.assertEqual(flare.medhistory_set.count(), mh_count + mh_diff)

    def test__post_change_one_to_ones(self):
        """Test that the post method changes the Flare's one-to-one related objects correctly."""

        # Iterate over some flares
        for flare in Flare.objects.filter(user__isnull=True).all()[:10]:
            # Create some fake data
            data = flare_data_factory(flare=flare)

            # Change the data to be different from the Flare's current one-to-one related objects
            data["dateofbirth-value"] = oto_random_age()
            data["gender-value"] = oto_random_gender()
            data["urate-value"] = oto_random_urate_or_None()
            if data.get("urate-value", None):
                data["urate_check"] = True
            else:
                data["urate-value"] = ""
                data["urate_check"] = False
            # Post the data
            response = self.client.post(reverse("flares:update", kwargs={"pk": flare.pk}), data)
            forms_print_response_errors(response)
            self.assertEqual(response.status_code, 302)

            self.flare.refresh_from_db()
            self.assertEqual(age_calc(self.flare.dateofbirth.value), data["dateofbirth-value"])
            self.assertEqual(self.flare.gender.value, data["gender-value"])
            if data.get("urate-value", None):
                self.assertTrue(getattr(self.flare, "urate", None))
                self.assertEqual(self.flare.urate.value, data["urate-value"])
            else:
                self.assertFalse(getattr(self.flare, "urate", None))

    def test__post_forms_not_valid(self):
        """Test that the post method returns the correct errors when the data is invalid."""

        self.flare_data.update(
            {
                "gender-value": "DRWHO",
            }
        )
        response = self.client.post(reverse("flares:update", kwargs={"pk": self.flare.pk}), data=self.flare_data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context_data["form"].errors)  # type: ignore
        self.assertTrue(response.context_data["gender_form"].errors)  # type: ignore
        self.assertIn("value", response.context_data["gender_form"].errors)  # type: ignore

    def test__post_menopause_not_valid(self):
        """Test that the post method returns the correct errors when the data is invalid."""

        self.flare_data.update(
            {
                "gender-value": Genders.FEMALE,
                "dateofbirth-value": age_calc(timezone.now().date() - timedelta(days=365 * 50)),
                f"{MedHistoryTypes.MENOPAUSE}-value": "",
            }
        )
        response = self.client.post(reverse("flares:update", kwargs={"pk": self.flare.pk}), data=self.flare_data)
        self.assertEqual(response.status_code, 200)
        # Assert that the MenopauseForm has an error
        self.assertTrue(response.context_data[f"{MedHistoryTypes.MENOPAUSE}_form"].errors)  # type: ignore
        self.assertEqual(
            response.context_data[f"{MedHistoryTypes.MENOPAUSE}_form"].errors[f"{MedHistoryTypes.MENOPAUSE}-value"][0],
            "For females between ages 40 and 60, we need to know the patient's \
menopause status to evaluate their flare.",
        )

    def test__urate_check_not_valid(self):
        """Test that the post method returns the correct errors when the data is invalid."""

        self.flare_data.update(
            {
                "medical_evaluation": True,
                "urate_check": True,
                "urate-value": "",
            }
        )
        response = self.client.post(reverse("flares:update", kwargs={"pk": self.flare.pk}), data=self.flare_data)
        self.assertEqual(response.status_code, 200)
        # Assert that the UrateForm has an error
        forms_print_response_errors(response)
        self.assertTrue(response.context_data["urate_form"].errors)
        self.assertEqual(
            response.context_data["urate_form"].errors["value"][0],
            "If the serum uric acid was checked, please tell us the value! \
If you don't know the value, please uncheck the Uric Acid Lab Check box.",
        )

    def test__aki_created(self):
        flare = create_flare(aki=None)
        self.assertIsNone(flare.aki)
        data = flare_data_factory(flare=flare, otos={"aki": True})
        response = self.client.post(reverse("flares:update", kwargs={"pk": flare.pk}), data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        flare.refresh_from_db()
        self.assertTrue(getattr(flare, "aki", False))

    def test__aki_deleted(self):
        flare = create_flare(aki=True)
        self.assertTrue(flare.aki)
        data = flare_data_factory(flare=flare, otos={"aki": False})
        response = self.client.post(reverse("flares:update", kwargs={"pk": flare.pk}), data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        flare.refresh_from_db()
        self.assertFalse(getattr(flare, "aki", False))

    def test__creatinines_created(self):
        flare = create_flare(labs=[])
        data = flare_data_factory(flare=flare, creatinines=[Decimal("2.0")])
        response = self.client.post(reverse("flares:update", kwargs={"pk": flare.pk}), data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        flare.refresh_from_db()
        self.assertTrue(flare.aki)
        self.assertTrue(flare.aki.creatinine_set.exists())
        self.assertEqual(flare.aki.creatinine_set.first().value, Decimal("2.0"))

    def test__creatinines_deleted(self):
        flare = create_flare(labs=[Decimal("2.0"), Decimal("3.0")])
        self.assertTrue(flare.aki)
        self.assertTrue(flare.aki.creatinine_set.exists())
        self.assertEqual(flare.aki.creatinine_set.count(), 2)
        data = flare_data_factory(flare=flare, creatinines=None)
        response = self.client.post(reverse("flares:update", kwargs={"pk": flare.pk}), data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        flare.refresh_from_db()
        self.assertTrue(flare.aki)
        self.assertFalse(flare.aki.creatinine_set.exists())

    def test__post_aki_on_dialysis_raises_ValidationError(self) -> None:
        flare = create_flare()
        flare_data = flare_data_factory(otos={"aki": True})
        flare_data.update(
            {
                f"{MedHistoryTypes.CKD}-value": True,
                "dialysis": True,
                "dialysis_type": DialysisChoices.HEMODIALYSIS,
                "dialysis_duration": DialysisDurations.LESSTHANSIX,
            }
        )
        response = self.client.post(reverse("flares:update", kwargs={"pk": flare.pk}), flare_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 200)
        self.assertIn("value", response.context_data["aki_form"].errors)
        self.assertIn(
            "If the patient is on",
            response.context_data["aki_form"].errors["value"][0],
        )
        self.assertIn("dialysis", response.context_data["ckddetail_form"].errors)
        self.assertIn(
            "If the patient is on",
            response.context_data["ckddetail_form"].errors["dialysis"][0],
        )
