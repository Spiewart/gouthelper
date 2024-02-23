from datetime import timedelta
from decimal import Decimal

import pytest  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from django.contrib.auth.models import AnonymousUser  # type: ignore
from django.core.exceptions import ObjectDoesNotExist  # type: ignore
from django.db.models import Q, QuerySet  # type: ignore
from django.forms import model_to_dict  # type: ignore
from django.http import Http404  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils import timezone  # type: ignore

from ...contents.models import Content
from ...dateofbirths.forms import DateOfBirthForm
from ...dateofbirths.helpers import age_calc
from ...dateofbirths.models import DateOfBirth
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...genders.choices import Genders
from ...genders.forms import GenderForm
from ...genders.models import Gender
from ...genders.tests.factories import GenderFactory
from ...labs.forms import UrateFlareForm
from ...labs.models import Urate
from ...labs.tests.factories import UrateFactory
from ...medhistorydetails.choices import Stages
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.forms import (
    AnginaForm,
    CadForm,
    ChfForm,
    CkdForm,
    GoutForm,
    HeartattackForm,
    MenopauseForm,
    PvdForm,
    StrokeForm,
)
from ...medhistorys.lists import FLARE_MEDHISTORYS
from ...medhistorys.models import Angina, Cad, Chf, Ckd, Gout, Heartattack, MedHistory, Menopause, Pvd, Stroke
from ...users.models import Pseudopatient
from ...users.tests.factories import AdminFactory, UserFactory, create_psp
from ...utils.helpers.test_helpers import medhistory_diff_obj_data, tests_print_response_form_errors
from ..choices import Likelihoods, LimitedJointChoices, Prevalences
from ..forms import FlareForm
from ..models import Flare
from ..selectors import flare_user_qs, user_flares
from ..views import (
    FlareAbout,
    FlareBase,
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


class TestFlareBase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: FlareBase = FlareBase()
        self.flare = create_flare(
            dateofbirth=DateOfBirthFactory(value=timezone.now().date() - timedelta(days=365 * 50)),
            gender=GenderFactory(value=Genders.FEMALE),
            urate=UrateFactory(value=Decimal("5.0")),
        )
        self.flare_data = model_to_dict(self.flare)
        self.flare_data.update({"urate_check": True})
        self.form = FlareForm(data=self.flare_data)
        self.form.is_valid()
        self.form.clean()
        self.menopause_data = {
            f"{MedHistoryTypes.MENOPAUSE}-value": True,
        }
        self.menopause_form = MenopauseForm(data=self.menopause_data)
        self.menopause_form.is_valid()
        self.menopause_form.clean()
        self.medhistorys_forms = {
            f"{MedHistoryTypes.MENOPAUSE}_form": self.menopause_form,
        }
        # NOTE: MUST BE "urate-value" because of the UrateFlareForm prefix
        self.urate_data = {"urate-value": self.flare.urate.value}
        self.urate_form = UrateFlareForm(instance=self.flare.urate, data=self.urate_data)
        self.urate_form.is_valid()
        self.urate_form.clean()
        self.onetoone_forms = {
            "urate_form": self.urate_form,
        }

    def test__post_process_urate_check(self):
        _, _, errors_bool = self.view.post_process_urate_check(
            self.form,
            self.onetoone_forms,
        )
        # Assert there are no errors on the urate form
        self.assertFalse(self.onetoone_forms["urate_form"].errors)
        self.assertFalse(errors_bool)
        # Change the urate data to make it invalid (no value)
        self.urate_data.update({"urate-value": None})
        # Create new urate form and swap into onetoone_forms
        new_urate_form = UrateFlareForm(data=self.urate_data)
        new_urate_form.is_valid()
        new_urate_form.clean()
        self.onetoone_forms.update({"urate_form": new_urate_form})
        _, _, errors_bool = self.view.post_process_urate_check(
            self.form,
            self.onetoone_forms,
        )
        # Assert there are errors on the urate form
        self.assertTrue(self.onetoone_forms["urate_form"].errors)
        self.assertTrue(errors_bool)
        self.assertEqual(
            self.onetoone_forms["urate_form"].errors["value"][0], "If urate was checked, we should know it!"
        )


class TestFlareCreate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: FlareCreate = FlareCreate()
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
            "urate_check": False,
            "urate": "",
            "diagnosed": False,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.GOUT}-value": False,
            f"{MedHistoryTypes.MENOPAUSE}-value": True,
        }
        self.angina_context = {
            "form": AnginaForm,
            "model": Angina,
        }
        self.cad_context = {
            "form": CadForm,
            "model": Cad,
        }
        self.chf_context = {
            "form": ChfForm,
            "model": Chf,
        }
        self.ckd_context = {
            "form": CkdForm,
            "model": Ckd,
        }
        self.gout_context = {
            "form": GoutForm,
            "model": Gout,
        }
        self.heartattack_context = {
            "form": HeartattackForm,
            "model": Heartattack,
        }
        self.stroke_context = {
            "form": StrokeForm,
            "model": Stroke,
        }
        self.pvd_context = {
            "form": PvdForm,
            "model": Pvd,
        }
        self.dateofbirth_context = {
            "form": DateOfBirthForm,
            "model": DateOfBirth,
        }
        self.gender_context = {
            "form": GenderForm,
            "model": Gender,
        }
        self.urate_context = {
            "form": UrateFlareForm,
            "model": Urate,
        }

    def test__attrs(self):
        self.assertIn("dateofbirth", self.view.onetoones)
        self.assertEqual(self.dateofbirth_context, self.view.onetoones["dateofbirth"])
        self.assertIn("gender", self.view.onetoones)
        self.assertEqual(self.gender_context, self.view.onetoones["gender"])
        self.assertIn("urate", self.view.onetoones)
        self.assertEqual(self.urate_context, self.view.onetoones["urate"])
        self.assertIn(MedHistoryTypes.ANGINA, self.view.medhistorys)
        self.assertEqual(self.angina_context, self.view.medhistorys[MedHistoryTypes.ANGINA])
        self.assertIn(MedHistoryTypes.CAD, self.view.medhistorys)
        self.assertEqual(self.cad_context, self.view.medhistorys[MedHistoryTypes.CAD])
        self.assertIn(MedHistoryTypes.CHF, self.view.medhistorys)
        self.assertEqual(self.chf_context, self.view.medhistorys[MedHistoryTypes.CHF])
        self.assertIn(MedHistoryTypes.CKD, self.view.medhistorys)
        self.assertEqual(self.ckd_context, self.view.medhistorys[MedHistoryTypes.CKD])
        self.assertIn(MedHistoryTypes.GOUT, self.view.medhistorys)
        self.assertEqual(self.gout_context, self.view.medhistorys[MedHistoryTypes.GOUT])
        self.assertIn(MedHistoryTypes.HEARTATTACK, self.view.medhistorys)
        self.assertEqual(self.heartattack_context, self.view.medhistorys[MedHistoryTypes.HEARTATTACK])
        self.assertIn(MedHistoryTypes.STROKE, self.view.medhistorys)
        self.assertEqual(self.stroke_context, self.view.medhistorys[MedHistoryTypes.STROKE])
        self.assertIn(MedHistoryTypes.PVD, self.view.medhistorys)
        self.assertEqual(self.pvd_context, self.view.medhistorys[MedHistoryTypes.PVD])

    def test__get_context_data(self):
        request = self.factory.get("/flares/create")
        request.user = AnonymousUser()
        response = FlareCreate.as_view()(request)
        self.assertIsInstance(response.context_data, dict)  # type: ignore
        for medhistory in FLARE_MEDHISTORYS:
            self.assertIn(f"{medhistory}_form", response.context_data)  # type: ignore
            self.assertIsInstance(
                response.context_data[f"{medhistory}_form"], self.view.medhistorys[medhistory]["form"]  # type: ignore
            )
            self.assertIsInstance(
                response.context_data[f"{medhistory}_form"].instance,  # type: ignore
                self.view.medhistorys[medhistory]["model"],
            )
        self.assertIn("dateofbirth_form", response.context_data)  # type: ignore
        self.assertIsInstance(
            response.context_data["dateofbirth_form"], self.view.onetoones["dateofbirth"]["form"]  # type: ignore
        )
        self.assertIsInstance(
            response.context_data["dateofbirth_form"].instance,  # type: ignore
            self.view.onetoones["dateofbirth"]["model"],
        )
        self.assertIsInstance(
            response.context_data["gender_form"], self.view.onetoones["gender"]["form"]  # type: ignore
        )
        self.assertIsInstance(
            response.context_data["gender_form"].instance, self.view.onetoones["gender"]["model"]  # type: ignore
        )
        self.assertIsInstance(
            response.context_data["urate_form"], self.view.onetoones["urate"]["form"]  # type: ignore
        )
        self.assertIsInstance(
            response.context_data["urate_form"].instance, self.view.onetoones["urate"]["model"]  # type: ignore
        )

    def test__post_no_medhistorys(self):
        # Count flares, dateofbirths, and genders
        flare_count, dateofbirth_count, gender_count = (
            Flare.objects.count(),
            DateOfBirth.objects.count(),
            Gender.objects.count(),
        )
        response = self.client.post(reverse("flares:create"), self.flare_data)
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
            "urate_check": True,
            "urate-value": Decimal("5.0"),
            "diagnosed": False,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.GOUT}-value": False,
            f"{MedHistoryTypes.MENOPAUSE}-value": True,
        }
        response = self.client.post(reverse("flares:create"), flare_data)
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
            "urate_check": True,
            "urate-value": Decimal("5.0"),
            "diagnosed": False,
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

    def test__post_process_menopause(self):
        flare = create_flare(
            dateofbirth=DateOfBirthFactory(value=timezone.now().date() - timedelta(days=365 * 50)),
            gender=GenderFactory(value=Genders.FEMALE),
            urate=UrateFactory(value=Decimal("5.0")),
        )
        menopause_data = {
            f"{MedHistoryTypes.MENOPAUSE}-value": True,
        }
        menopause_form = MenopauseForm(data=menopause_data)
        menopause_form.is_valid()
        menopause_form.clean()
        medhistorys_forms = {
            f"{MedHistoryTypes.MENOPAUSE}_form": menopause_form,
        }
        _, errors_bool = self.view.post_process_menopause(
            medhistorys_forms,
            flare,
        )
        # Assert there are no errors on the menopause form
        self.assertFalse(menopause_form.errors)
        self.assertFalse(errors_bool)
        # Change the menopause data to make it invalid (no value)
        menopause_data.update({f"{MedHistoryTypes.MENOPAUSE}-value": None})
        # Need to create new form instance to re-run is_valid and clean
        # NOTE: This is because the form is already bound to the data ???
        new_menopause_form = MenopauseForm(data=menopause_data)
        # Re-run is_valid and clean
        new_menopause_form.data = menopause_data
        new_menopause_form.is_valid()
        new_menopause_form.clean()
        medhistorys_forms.update({f"{MedHistoryTypes.MENOPAUSE}_form": new_menopause_form})
        _, errors_bool = self.view.post_process_menopause(
            medhistorys_forms,
            flare,
        )
        # Assert there are errors on the menopause form
        self.assertTrue(new_menopause_form.errors)
        self.assertTrue(errors_bool)
        # Change the flare.dateofbirth to make it too young for menopause
        flare.dateofbirth.value = timezone.now().date() - timedelta(days=365 * 39)
        flare.dateofbirth.save()
        medhistorys_forms.update({f"{MedHistoryTypes.MENOPAUSE}_form": new_menopause_form})
        _, errors_bool = self.view.post_process_menopause(
            medhistorys_forms,
            flare,
        )
        # Assert the errors_bool is False
        # Form not tested because we didn't create a new one and the errors are the same
        self.assertFalse(errors_bool)
        # Change the flare.dateofbirth to make it too old for menopause
        flare.dateofbirth.value = timezone.now().date() - timedelta(days=365 * 61)
        flare.dateofbirth.save()
        medhistorys_forms.update({f"{MedHistoryTypes.MENOPAUSE}_form": new_menopause_form})
        _, errors_bool = self.view.post_process_menopause(
            medhistorys_forms,
            flare,
        )
        # Assert the errors_bool is False
        # Form not tested because we didn't create a new one and the errors are the same
        self.assertFalse(errors_bool)
        flare.dateofbirth.value = timezone.now().date() - timedelta(days=365 * 45)
        flare.dateofbirth.save()
        medhistorys_forms.update({f"{MedHistoryTypes.MENOPAUSE}_form": new_menopause_form})
        _, errors_bool = self.view.post_process_menopause(
            medhistorys_forms,
            flare,
        )
        self.assertTrue(errors_bool)
        # Test male gender doesn't need menopause
        flare.gender.value = Genders.MALE
        flare.gender.save()
        medhistorys_forms.update({f"{MedHistoryTypes.MENOPAUSE}_form": new_menopause_form})
        _, errors_bool = self.view.post_process_menopause(
            medhistorys_forms,
            flare,
        )
        self.assertFalse(errors_bool)

    def test__urate_check_not_valid(self):
        self.flare_data.update(
            {
                "urate_check": True,
                "urate-value": "",
            }
        )
        response = self.client.post(reverse("flares:create"), self.flare_data)
        self.assertEqual(response.status_code, 200)
        # Assert that the UrateForm has an error
        self.assertTrue(response.context_data["urate_form"].errors)
        self.assertEqual(
            response.context_data["urate_form"].errors["value"][0], "If urate was checked, we should know it!"
        )


class TestFlareDetail(TestCase):
    def setUp(self):
        self.flare = create_flare()
        self.factory = RequestFactory()
        self.view: FlareDetail = FlareDetail
        self.content_qs = Content.objects.filter(
            Q(tag=Content.Tags.EXPLANATION) | Q(tag=Content.Tags.WARNING),
            context=Content.Contexts.FLARE,
            slug__isnull=False,
        ).all()

    def test__contents(self):
        self.assertTrue(self.view().contents)
        self.assertTrue(isinstance(self.view().contents, QuerySet))
        for content in self.view().contents:
            self.assertIn(content, self.content_qs)
        for content in self.content_qs:
            self.assertIn(content, self.view().contents)

    def test__dispatch_redirects_if_flare_user(self):
        """Test that the dispatch() method redirects to the Pseudopatient DetailView if the
        Flare has a user."""
        user_f = create_flare(user=True)
        request = self.factory.get("/fake-url/")
        request.user = AnonymousUser()
        response = self.view.as_view()(request, pk=user_f.pk)
        assert response.status_code == 302
        assert response.url == reverse(
            "flares:pseudopatient-detail", kwargs={"username": user_f.user.username, "pk": user_f.pk}
        )

    def test__get_context_data(self):
        response = self.client.get(reverse("flares:detail", kwargs={"pk": self.flare.pk}))
        context = response.context_data
        for content in self.content_qs:
            self.assertIn(content.slug, context)
            self.assertEqual(context[content.slug], {content.tag: content})

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
        with self.assertRaises(AttributeError) as exc:
            self.view().check_user_onetoones(empty_user)
        self.assertEqual(
            exc.exception.args[0], "Baseline information is needed to use GoutHelper Decision and Treatment Aids."
        )
        assert self.view().check_user_onetoones(self.user) is None

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
        kwargs = {"username": self.user.username}
        view = self.view(request=request, kwargs=kwargs)

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
            reverse("flares:pseudopatient-create", kwargs={"username": empty_user.username}), follow=True
        )
        self.assertRedirects(response, reverse("users:pseudopatient-update", kwargs={"username": empty_user.username}))
        message = list(response.context.get("messages"))[0]
        self.assertEqual(message.tags, "error")
        self.assertEqual(
            message.message, "Baseline information is needed to use GoutHelper Decision and Treatment Aids."
        )

    def test__get_user_queryset(self):
        """Test the get_user_queryset() method for the view."""
        request = self.factory.get("/fake-url/")
        kwargs = {"username": self.user.username}
        view = self.view()
        # https://stackoverflow.com/questions/33645780/how-to-unit-test-methods-inside-djangos-class-based-views
        view.setup(request, **kwargs)
        qs = view.get_user_queryset(view.kwargs["username"])
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
            kwargs = {"username": user.username}
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
            kwargs = {"username": user.username}
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
            assert "ckddetail_form" not in response.context_data
            assert "goutdetail_form" not in response.context_data

    def test__get_permission_object(self):
        """Test the get_permission_object() method for the view."""
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        kwargs = {"username": self.user.username}
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
        kwargs = {"username": self.user.username}
        response = self.view.as_view()(request, **kwargs)
        assert response.status_code == 200

    def test__post_sets_object_user(self):
        """Test that the post() method for the view sets the
        user on the object."""
        # Create some fake data for a User's FlareAid
        data = flare_data_factory(self.user)
        response = self.client.post(
            reverse("flares:pseudopatient-create", kwargs={"username": self.user.username}), data=data
        )
        tests_print_response_form_errors(response)
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
            reverse("flares:pseudopatient-create", kwargs={"username": self.psp.username}), data=data
        )
        tests_print_response_form_errors(response)
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
            reverse("flares:pseudopatient-create", kwargs={"username": psp.username}), data=data
        )
        tests_print_response_form_errors(response)
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
            reverse("flares:pseudopatient-create", kwargs={"username": psp.username}), data=data
        )
        tests_print_response_form_errors(response)
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
            reverse("flares:pseudopatient-create", kwargs={"username": self.psp.username}), data=data
        )
        tests_print_response_form_errors(response)
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
                "urate_check": True,
                "urate-value": "",
            }
        )
        # Post the data
        response = self.client.post(
            reverse("flares:pseudopatient-create", kwargs={"username": self.psp.username}), data=data
        )
        assert response.status_code == 200
        tests_print_response_form_errors(response)
        # Assert that the form has an error on the urate_check field
        self.assertTrue(response.context_data["form"].errors)
        self.assertEqual(
            response.context_data["form"].errors["urate_check"][0], "If urate was checked, we should know it!"
        )
        # Assert that the urate_form has an error on the value field
        self.assertTrue(response.context_data["urate_form"].errors)
        self.assertEqual(
            response.context_data["urate_form"].errors["value"][0], "If urate was checked, we should know it!"
        )
        # Change the fake data such that the urate stuff passes but that diagnosed is True but aspiration is
        # not selected, which should result in an error on the aspiration field
        data.update(
            {
                "urate_check": True,
                "urate-value": Decimal("5.0"),
                "diagnosed": True,
                "aspiration": "",
            }
        )
        # Post the data
        response = self.client.post(
            reverse("flares:pseudopatient-create", kwargs={"username": self.psp.username}), data=data
        )
        assert response.status_code == 200
        tests_print_response_form_errors(response)
        # Assert that the form has an error on the aspiration field
        self.assertTrue(response.context_data["form"].errors)
        self.assertEqual(
            response.context_data["form"].errors["aspiration"][0],
            "Joint aspiration must be selected if a clinician diagnosed the flare.",
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
                "diagnosed": True,
                "aspiration": True,
                "crystal_analysis": True,
                "date_started": timezone.now().date() - timedelta(days=35),
                "date_ended": timezone.now().date() - timedelta(days=25),
            }
        )
        # Post the data
        response = self.client.post(
            reverse("flares:pseudopatient-create", kwargs={"username": self.psp.username}), data=data
        )
        tests_print_response_form_errors(response)
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
            dateofbirth=timezone.now().date() - timedelta(days=365 * 64),
            gender=Genders.FEMALE,
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
                "diagnosed": True,
                "aspiration": False,
                "crystal_analysis": "",
            }
        )

        # Post the data
        response = self.client.post(
            reverse("flares:pseudopatient-create", kwargs={"username": psp.username}), data=data
        )
        tests_print_response_form_errors(response)
        assert response.status_code == 302

        flare = Flare.objects.filter(user=psp).order_by("created").last()
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
                "diagnosed": False,
                "aspiration": "",
                "crystal_analysis": "",
                "date_started": timezone.now().date() - timedelta(days=135),
                "date_ended": timezone.now().date() - timedelta(days=5),
            }
        )
        # Post the data
        response = self.client.post(
            reverse("flares:pseudopatient-create", kwargs={"username": self.psp.username}), data=data
        )
        tests_print_response_form_errors(response)
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
        prov_psp_url = reverse("flares:pseudopatient-create", kwargs={"username": prov_psp.username})
        next_url = reverse("flares:pseudopatient-create", kwargs={"username": prov_psp.username})
        prov_psp_redirect_url = f"{reverse('account_login')}?next={next_url}"
        admin = AdminFactory()
        admin_psp = create_psp(provider=admin)
        admin_psp_url = reverse("flares:pseudopatient-create", kwargs={"username": admin_psp.username})
        redirect_url = reverse("flares:pseudopatient-create", kwargs={"username": admin_psp.username})
        admin_psp_redirect_url = f"{reverse('account_login')}?next={redirect_url}"
        # Create an anonymous Pseudopatient
        anon_psp = create_psp()
        anon_psp_url = reverse("flares:pseudopatient-create", kwargs={"username": anon_psp.username})
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
        view.setup(request, username=self.prov_psp.username, pk=self.prov_psp_flare.pk)
        view.dispatch(request)
        assert hasattr(view, "user")
        assert view.user == self.prov_psp
        assert hasattr(view, "object")
        assert view.object == self.prov_psp_flare

    def test__get_object_sets_user_returns_object(self):
        """Test that the get_object() method for the view sets the user attr and returns the object."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, username=self.prov_psp.username, pk=self.prov_psp_flare.pk)
        flare = view.get_object()
        assert hasattr(view, "user")
        assert view.user == self.prov_psp
        assert flare == self.prov_psp_flare

    def test__get_object_raises_404(self):
        """Test that the get_object() method for the view raises a 404 if the User or Flare doesn't exist."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, username=self.prov_psp.username, pk=self.prov_psp_flare.pk)
        view.kwargs["username"] = "fake-username"
        with self.assertRaises(Http404):
            view.get_object()
        view.kwargs["username"] = self.prov_psp.username
        view.kwargs["pk"] = 999
        with self.assertRaises(Http404):
            view.get_object()

    def test__get_permission_object(self):
        """Test that the get_permission_object() method returns the
        view's object, which must have already been set."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, username=self.prov_psp.username, pk=self.prov_psp_flare.pk)
        view.object = self.prov_psp_flare
        assert view.get_permission_object() == self.prov_psp_flare

    def test__get_success_url(self):
        """Test that the get_success_url() method returns the correct url."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, username=self.prov_psp.username, pk=self.prov_psp_flare.pk)
        view.object = self.prov_psp_flare
        assert view.get_success_url() == reverse(
            "flares:pseudopatient-list", kwargs={"username": self.prov_psp.username}
        )

    def test__get_queryset(self):
        """Test that the get_queryset() method returns the correct QuerySet."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, username=self.prov_psp.username, pk=self.prov_psp_flare.pk)
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
            "flares:pseudopatient-delete", kwargs={"username": self.prov_psp.username, "pk": self.prov_psp_flare.pk}
        )
        prov_psp_redirect_url = f"{reverse('account_login')}?next={prov_psp_url}"
        admin_psp_url = reverse(
            "flares:pseudopatient-delete", kwargs={"username": self.admin_psp.username, "pk": self.admin_psp_flare.pk}
        )
        admin_psp_redirect_url = f"{reverse('account_login')}?next={admin_psp_url}"
        anon_psp_url = reverse(
            "flares:pseudopatient-delete", kwargs={"username": self.anon_psp.username, "pk": self.anon_psp_flare.pk}
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
                kwargs={"username": self.prov_psp.username, "pk": self.prov_psp_flare.pk},
            )
        )
        assert response.status_code == 302
        assert not Flare.objects.filter(user=self.prov_psp).exists()
        assert response.url == reverse("flares:pseudopatient-list", kwargs={"username": self.prov_psp.username})


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

    def test__assign_flare_attrs_from_user(self):
        """Test that the assign_flareaid_attrs_from_user() method for the view
        transfers attributes from the QuerySet, which started with a User,
        to the FlareAid object."""
        flare = Flare.objects.filter(user=self.psp).last()
        view = self.view()
        request = self.factory.get("/fake-url/")
        view.setup(request, username=self.psp.username)
        assert not getattr(flare, "dateofbirth")
        assert not getattr(flare, "gender")
        assert not hasattr(flare, "medhistorys_qs")
        view.assign_flare_attrs_from_user(flare=flare, user=flare_user_qs(self.psp.username, flare.pk).get())
        assert getattr(flare, "dateofbirth") == self.psp.dateofbirth
        assert getattr(flare, "gender") == self.psp.gender
        assert hasattr(flare, "medhistorys_qs")

    def test__dispatch(self):
        """Test the dispatch() method for the view. Should redirect to Pseudopatient Update
        view when the user doesn't have the required 1to1 related models."""
        response = self.client.get(
            reverse(
                "flares:pseudopatient-detail",
                kwargs={"username": self.psp.username, "pk": self.psp.flare_set.first().pk},
            )
        )
        self.assertEqual(response.status_code, 200)

        self.psp.dateofbirth.delete()
        # Test that dispatch redirects to the User Update view when the user doesn't have a dateofbirth
        self.assertRedirects(
            self.client.get(
                reverse(
                    "flares:pseudopatient-detail",
                    kwargs={"username": self.psp.username, "pk": self.psp.flare_set.first().pk},
                ),
            ),
            reverse("users:pseudopatient-update", kwargs={"username": self.psp.username}),
        )

    def test__dispatch_sets_object_attr(self):
        """Test that dispatch calls get_object() and sets the object attr on the view."""
        flare = self.psp.flare_set.first()
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        view = self.view()
        view.setup(request, username=self.psp.username, pk=flare.pk)
        view.dispatch(request)
        assert hasattr(view, "object")
        assert view.object == flare

    def test__get_object_sets_user(self):
        """Test that the get_object() method sets the user attribute."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, username=self.psp.username, pk=self.psp.flare_set.first().pk)
        view.get_object()
        assert hasattr(view, "user")
        assert view.user == self.psp

    def test__get_object_assigns_user_qs_attrs_to_flare(self):
        """Test that the get_object method transfers required attributes from the
        User QuerySet to the Flare object."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, username=self.psp.username, pk=self.psp.flare_set.first().pk)
        flare = view.get_object()
        assert hasattr(flare, "dateofbirth")
        assert getattr(flare, "dateofbirth") == view.user.dateofbirth
        assert hasattr(flare, "gender")
        assert getattr(flare, "gender") == view.user.gender
        assert hasattr(flare, "medhistorys_qs")
        assert getattr(flare, "medhistorys_qs") == view.user.medhistorys_qs

    def test__get_object_raises_404s(self):
        """Test that get_object() raises a 404 if the User or the Flare doesn't exist."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, username=self.psp.username, pk=self.psp.flare_set.first().pk)
        view.kwargs["username"] = "fake-username"
        with self.assertRaises(Http404):
            view.get_object()
        view.kwargs["username"] = self.psp.username
        view.kwargs["pk"] = 999
        with self.assertRaises(Http404):
            view.get_object()

    def test__get_object(self):
        """Test that the get_object() method returns the Flare object."""
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, username=self.psp.username, pk=self.psp.flare_set.first().pk)
        flare = view.get_object()
        assert isinstance(flare, Flare)
        assert flare == self.psp.flare_set.first()

    def test__get_permission_object(self):
        """Test that the get_permission_object() method returns the
        view's object, which must have already been set."""
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        view = self.view()
        view.setup(request, username=self.psp.username, pk=self.psp.flare_set.first().pk)
        view.dispatch(request, username=self.psp.username)
        pm_obj = view.get_permission_object()
        assert pm_obj == view.object

    def test__get_queryset(self):
        """Test the get_queryset() method for the view."""
        # Get a flare
        flare = self.psp.flare_set.first()
        request = self.factory.get("/fake-url/")
        view = self.view()
        view.setup(request, username=self.psp.username, pk=flare.pk)
        with self.assertNumQueries(3):
            qs = view.get_queryset().get()
            assert getattr(qs, "flare_qs") == [flare]
        assert qs == self.psp
        assert hasattr(qs, "flare_qs") and qs.flare_qs[0] == flare
        assert hasattr(qs, "dateofbirth") and qs.dateofbirth == self.psp.dateofbirth
        assert hasattr(qs, "gender") and qs.gender == self.psp.gender
        assert hasattr(qs, "medhistorys_qs")
        psp_mhs = self.psp.medhistory_set.filter(medhistorytype__in=FLARE_MEDHISTORYS).all()
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
        flare.update_aid(qs=flare_user_qs(psp.username, flare.pk))
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
            reverse("flares:pseudopatient-detail", kwargs={"username": psp.username, "pk": flare.pk}) + "?updated=True"
        )
        flare.refresh_from_db()
        # Assert that the flare has an unchanged likelihood and prevalence
        self.assertEqual(flare.likelihood, Likelihoods.UNLIKELY)
        self.assertEqual(flare.prevalence, Prevalences.LOW)
        # Call the view with the ?updated=True query parameter to test that it updates the Flare
        self.client.get(reverse("flares:pseudopatient-detail", kwargs={"username": psp.username, "pk": flare.pk}))
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
            "flares:pseudopatient-detail", kwargs={"username": prov_psp.username, "pk": prov_psp_flare.pk}
        )
        redirect_url = reverse(
            "flares:pseudopatient-detail", kwargs={"username": prov_psp.username, "pk": prov_psp_flare.pk}
        )
        prov_psp_redirect_url = f"{reverse('account_login')}?next={redirect_url}"
        admin = AdminFactory()
        admin_psp = create_psp(provider=admin)
        admin_psp_flare = create_flare(user=admin_psp)
        admin_psp_url = reverse(
            "flares:pseudopatient-detail", kwargs={"username": admin_psp.username, "pk": admin_psp_flare.pk}
        )
        redirect_url = reverse(
            "flares:pseudopatient-detail", kwargs={"username": admin_psp.username, "pk": admin_psp_flare.pk}
        )
        admin_psp_redirect_url = f"{reverse('account_login')}?next={redirect_url}"
        # Create an anonymous Pseudopatient + Flare
        anon_psp = create_psp()
        anon_psp_flare = create_flare(user=anon_psp)
        anon_psp_url = reverse(
            "flares:pseudopatient-detail", kwargs={"username": anon_psp.username, "pk": anon_psp_flare.pk}
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
        for _ in range(5):
            create_flare(user=self.psp)
        self.anon_psp = create_psp(plus=True)
        for _ in range(5):
            create_flare(user=self.anon_psp)
        self.empty_psp = create_psp(plus=True)
        self.view = FlarePseudopatientList

    def test__dispatch(self):
        """Test that dispatch sets the userattr on the view."""
        # Create a fake request
        request = RequestFactory().get("/fake-url/")
        request.user = self.provider
        # Create a view
        view = self.view()
        kwargs = {"username": self.psp.username}
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
        view.user = user_flares(self.psp.username).get()
        kwargs = {"username": self.psp.username}
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
        view.user = user_flares(self.psp.username).get()
        kwargs = {"username": self.psp.username}
        # Setup the view
        view.setup(request, **kwargs)
        # Call the get_context_data() method
        qs = user_flares(self.psp.username).get()
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
        view.setup(request, username=self.psp.username)
        view.dispatch(request, username=self.psp.username)
        pm_obj = view.get_permission_object()
        assert pm_obj == view.user

    def test__get_queryset(self):
        """Test the get_queryset() method for the view."""
        request = RequestFactory().get("/fake-url/")
        request.user = self.anon_user
        view = self.view()
        view.setup(request, username=self.psp.username)
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
        prov_psp_url = reverse("flares:pseudopatient-list", kwargs={"username": prov_psp.username})
        redirect_url = reverse("flares:pseudopatient-list", kwargs={"username": prov_psp.username})
        prov_psp_redirect_url = f"{reverse('account_login')}?next={redirect_url}"
        admin = AdminFactory()
        admin_psp = create_psp(provider=admin)
        admin_psp_url = reverse("flares:pseudopatient-list", kwargs={"username": admin_psp.username})
        redirect_url = reverse("flares:pseudopatient-list", kwargs={"username": admin_psp.username})
        admin_psp_redirect_url = f"{reverse('account_login')}?next={redirect_url}"
        # Create an anonymous Pseudopatient
        anon_psp = create_psp()
        anon_psp_url = reverse("flares:pseudopatient-list", kwargs={"username": anon_psp.username})
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
            create_flare(user=psp)

    def test__check_user_onetoones(self):
        """Tests that the view checks for the User's related models."""
        empty_user = create_psp(dateofbirth=False, gender=False)
        with self.assertRaises(AttributeError) as exc:
            self.view().check_user_onetoones(empty_user)
        self.assertEqual(
            exc.exception.args[0], "Baseline information is needed to use GoutHelper Decision and Treatment Aids."
        )
        assert self.view().check_user_onetoones(self.user) is None

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
            reverse(
                "flares:pseudopatient-update", kwargs={"username": empty_user.username, "pk": empty_user_Flare.pk}
            ),
            follow=True,
        )
        self.assertRedirects(response, reverse("users:pseudopatient-update", kwargs={"username": empty_user.username}))
        message = list(response.context.get("messages"))[0]
        self.assertEqual(message.tags, "error")
        self.assertEqual(
            message.message, "Baseline information is needed to use GoutHelper Decision and Treatment Aids."
        )

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
            kwargs = {"username": user.username, "pk": flare.pk}
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
                "urate_check": True if flare.urate else False,
                "diagnosed": flare.diagnosed,
                "aspiration": True if flare.crystal_analysis is not None else False if flare.diagnosed else None,
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
            kwargs = {"username": user.username, "pk": flare.pk}
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
            kwargs = {"username": user.username, "pk": flare.pk}
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
            assert "ckddetail_form" not in response.context_data
            assert "goutdetail_form" not in response.context_data

    def test__get_form_kwargs(self):
        # Create a fake request
        request = self.factory.get("/fake-url/")
        request.user = self.anon_user
        view = self.view(request=request)
        # Create kwargs for view
        kwargs = {"username": self.user.username, "pk": self.user.flare_set.first().pk}
        # Setup the view
        view.setup(request, **kwargs)
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
            kwargs = {"username": flare.user.username, "pk": flare.pk}
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
            elif flare.diagnosed:
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
        kwargs = {"username": flareless_user.username, "pk": 1}
        view = self.view(request=request)
        view.setup(request, **kwargs)
        with self.assertRaises(ObjectDoesNotExist):
            view.get_object()
        # Create a flare for the user
        flare = create_flare(user=flareless_user)
        kwargs = {"username": flareless_user.username, "pk": flare.pk}
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
        kwargs = {"username": self.user.username, "pk": flare.pk}
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
        kwargs = {"username": self.user.username, "pk": self.user.flare_set.first().pk}
        view = self.view()
        # https://stackoverflow.com/questions/33645780/how-to-unit-test-methods-inside-djangos-class-based-views
        view.setup(request, **kwargs)
        qs = view.get_user_queryset(view.kwargs["username"])
        self.assertTrue(isinstance(qs, QuerySet))
        with self.assertNumQueries(3):
            qs = qs.get()
            self.assertTrue(isinstance(qs, User))
            self.assertTrue(hasattr(qs, "flare_qs"))
            self.assertTrue(isinstance(qs.flare_qs, list))
            self.assertEqual(qs.flare_qs[0], flare)
            self.assertTrue(hasattr(qs.flare_qs[0], "urate"))
            self.assertTrue(isinstance(qs.flare_qs[0].urate, Urate))
            self.assertEqual(qs.flare_qs[0].urate, flare.urate)
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
            # Call the view and get the object
            view = self.view()
            view.setup(request, **{"username": user.username, "pk": flare.pk})
            view.object = view.get_object()
            # Create a onetoone_forms dict with the method for testing against
            onetoone_forms = view.post_populate_oto_forms(
                onetoones=view.onetoones,
                request=request,
                query_obj=user,
            )
            for onetoone, modelform_dict in view.onetoones.items():
                # Assert that the onetoone_forms dict has the correct keys
                self.assertIn(f"{onetoone}_form", onetoone_forms)
                # Assert that the onetoone_forms dict has the correct values
                self.assertTrue(isinstance(onetoone_forms[f"{onetoone}_form"], modelform_dict["form"]))
                # Assert that the onetoone_forms dict has the correct initial data
                self.assertEqual(
                    onetoone_forms[f"{onetoone}_form"].initial,
                    {
                        "value": getattr(view.object, onetoone, None).value
                        if getattr(view.object, onetoone, None)
                        else None
                    },
                )

    def test__post_process_oto_forms(self):
        """Test the post_process_oto_forms() method for the view."""
        # Iterate over the Pseudopatients
        for user in Pseudopatient.objects.all():
            # Fetch the Flare, each User will only have 1
            flare = user.flare_set.first()
            # Create a fake POST request
            request = self.factory.post("/fake-url/")
            # Call the view and get the object
            view = self.view()
            view.setup(request, **{"username": user.username, "pk": flare.pk})
            view.object = view.get_object()
            # Create a onetoone_forms dict with the method for testing against
            onetoone_forms = view.post_populate_oto_forms(
                onetoones=view.onetoones,
                request=request,
                query_obj=user,
            )
            # Create some fake flare data
            data = flare_data_factory(user=user, flare=flare)
            # Iterate over the onetoone_forms and update the data with the fake data
            for onetoone, form in onetoone_forms.items():
                # Get the onetoone name str
                onetoone = onetoone.split("_")[0]
                form.data._mutable = True
                form.data[f"{onetoone}-value"] = data.get(f"{onetoone}-value", "")
                form.is_valid()
            # Call the post_process_oto_forms() method and assign to new lists
            # of onetoones to save and delete to test against
            oto_2_save, oto_2_rem = view.post_process_oto_forms(
                oto_forms=onetoone_forms,
                req_onetoones=view.req_onetoones,
                query_obj=user,
            )
            # Iterate over all the onetoones to check if they are marked as to be saved or deleted correctly
            for onetoone in view.onetoones:
                form = onetoone_forms[f"{onetoone}_form"]
                initial = onetoone_forms[f"{onetoone}_form"].initial.get("value", None)
                # If the form is adding a new object, assert that there's no initial data
                if form.instance._state.adding:
                    assert not initial
                data_val = data.get(f"{onetoone}-value", "")
                # Check if there was no pre-existing onetoone and there is no data to create a new one
                if not initial and data_val == (None or ""):
                    # Should not be marked for save or deletion
                    assert not next(iter(onetoone for onetoone in oto_2_save), None) and not next(
                        iter(onetoone for onetoone in oto_2_rem), None
                    )
                # If there was no pre-existing onetoone but there is data to create a new one
                elif not initial and data_val != (None or ""):
                    # Should be marked for save and not deletion
                    assert next(iter(onetoone for onetoone in oto_2_save)) and not next(
                        iter(onetoone for onetoone in oto_2_rem), None
                    )
                # If there was a pre-existing onetoone but the data is not present in the POST data
                elif initial and data_val == (None or ""):
                    # Should be marked for deletion and not save
                    assert not next(iter(onetoone for onetoone in oto_2_save), None) and next(
                        iter(onetoone for onetoone in oto_2_rem)
                    )
                # If there is a pre-existing object and there is data in the POST request
                elif initial and data_val != (None or ""):
                    # If the data changed, the object should be marked for saving
                    if initial != data_val:
                        assert next(iter(onetoone for onetoone in oto_2_save)) and not next(
                            iter(onetoone for onetoone in oto_2_rem), None
                        )
                    # Otherwise it should not be marked for saving or
                    # deletion and the form's changed_data dict should be empty
                    else:
                        assert (
                            not next(iter(onetoone for onetoone in oto_2_save), None)
                            and not next(iter(onetoone for onetoone in oto_2_rem), None)
                            and not onetoone_forms[f"{onetoone}_form"].changed_data
                        )
                        assert onetoone_forms[f"{onetoone}_form"].changed_data == []

    def test__post(self):
        """Test the post() method for the view."""
        request = self.factory.post("/fake-url/")
        if self.user.profile.provider:  # type: ignore
            request.user = self.user.profile.provider  # type: ignore
        else:
            request.user = self.anon_user
        flare = self.user.flare_set.first()
        kwargs = {"username": self.user.username, "pk": flare.pk}
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
                reverse("flares:pseudopatient-update", kwargs={"username": user.username, "pk": flare.pk}), data=data
            )
            tests_print_response_form_errors(response)
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
        # Create a flare with a user and no urate
        flare = create_flare(user=self.user, urate=None)
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
            reverse("flares:pseudopatient-update", kwargs={"username": self.user.username, "pk": flare.pk}), data=data
        )
        tests_print_response_form_errors(response)
        assert response.status_code == 302
        # Assert that the urate was created
        flare.refresh_from_db()
        self.assertTrue(getattr(flare, "urate", None))
        urate = flare.urate
        self.assertEqual(urate.value, Decimal("5.0"))
        self.assertEqual(flare.urate.user, self.user)

    def test__post_updates_urate(self):
        # Create a flare with a user and a urate
        flare = create_flare(user=self.user, urate=UrateFactory(user=self.user, value=Decimal("5.0")))
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
            reverse("flares:pseudopatient-update", kwargs={"username": self.user.username, "pk": flare.pk}), data=data
        )
        tests_print_response_form_errors(response)
        assert response.status_code == 302
        # Assert that the urate was updated
        flare.refresh_from_db()
        self.assertTrue(getattr(flare, "urate", None))
        urate = flare.urate
        self.assertEqual(urate.value, Decimal("6.0"))

    def test__post_deletes_urate(self):
        """Test that the post() method deletes a urate when provided the appropriate data."""
        urate = UrateFactory(user=self.user, value=Decimal("5.0"))
        # Create a flare with a user and a urate
        flare = create_flare(user=self.user, urate=urate)
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
            reverse("flares:pseudopatient-update", kwargs={"username": self.user.username, "pk": flare.pk}), data=data
        )
        tests_print_response_form_errors(response)
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
                "urate_check": True,
                "urate-value": "",
            }
        )
        # Post the data
        response = self.client.post(
            reverse("flares:pseudopatient-update", kwargs={"username": self.psp.username, "pk": flare.pk}), data=data
        )
        assert response.status_code == 200
        tests_print_response_form_errors(response)
        # Assert that the form has an error on the urate_check field
        self.assertTrue(response.context_data["form"].errors)
        self.assertEqual(
            response.context_data["form"].errors["urate_check"][0], "If urate was checked, we should know it!"
        )
        # Assert that the urate_form has an error on the value field
        self.assertTrue(response.context_data["urate_form"].errors)
        self.assertEqual(
            response.context_data["urate_form"].errors["value"][0], "If urate was checked, we should know it!"
        )
        # Change the fake data such that the urate stuff passes but that diagnosed is True but aspiration is
        # not selected, which should result in an error on the aspiration field
        data.update(
            {
                "urate_check": True,
                "urate-value": Decimal("5.0"),
                "diagnosed": True,
                "aspiration": "",
            }
        )
        # Post the data
        response = self.client.post(
            reverse("flares:pseudopatient-update", kwargs={"username": self.psp.username, "pk": flare.pk}), data=data
        )
        assert response.status_code == 200
        tests_print_response_form_errors(response)
        # Assert that the form has an error on the aspiration field
        self.assertTrue(response.context_data["form"].errors)
        self.assertEqual(
            response.context_data["form"].errors["aspiration"][0],
            "Joint aspiration must be selected if a clinician diagnosed the flare.",
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
                "diagnosed": True,
                "aspiration": True,
                "crystal_analysis": True,
                "date_started": timezone.now().date() - timedelta(days=35),
                "date_ended": timezone.now().date() - timedelta(days=25),
            }
        )
        # Post the data
        response = self.client.post(
            reverse("flares:pseudopatient-update", kwargs={"username": self.psp.username, "pk": flare.pk}), data=data
        )
        tests_print_response_form_errors(response)
        assert response.status_code == 302
        flare.refresh_from_db()
        # Assert that the flare has a high likelihood and prevalence
        self.assertEqual(flare.likelihood, Likelihoods.LIKELY)
        self.assertEqual(flare.prevalence, Prevalences.HIGH)

    def test__post_returns_moderate_likelihood_prevalence_flare(self):
        """Test that a flare is created with a moderate likelihood and prevalence when the
        data indicates a moderate likelihood and prevalence flare."""

        # Get a flare for the Pseudopatient
        flare = create_flare(user=True, medhistorys=[], gender=Genders.MALE)
        # Create a fake data dict
        data = flare_data_factory(self.psp)
        # Modify data entries to indicate a moderate likelihood and prevalence flare
        data.update(
            {
                "onset": True,
                "redness": False,
                "joints": [LimitedJointChoices.KNEER],
                "date_started": timezone.now().date() - timedelta(days=7),
                "date_ended": "",
                "urate_check": True,
                "urate-value": Decimal("5.0"),
                "diagnosed": True,
                "aspiration": False,
            }
        )
        # Post the data
        response = self.client.post(
            reverse("flares:pseudopatient-update", kwargs={"username": flare.user.username, "pk": flare.pk}), data=data
        )
        tests_print_response_form_errors(response)
        assert response.status_code == 302
        flare.refresh_from_db()
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
                "urate_check": True,
                "urate-value": Decimal("5.0"),
                "diagnosed": False,
                "aspiration": "",
                "crystal_analysis": "",
                "date_started": timezone.now().date() - timedelta(days=135),
                "date_ended": timezone.now().date() - timedelta(days=5),
            }
        )
        # Post the data
        response = self.client.post(
            reverse("flares:pseudopatient-update", kwargs={"username": self.psp.username, "pk": flare.pk}), data=data
        )
        tests_print_response_form_errors(response)
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
            "flares:pseudopatient-update", kwargs={"username": prov_psp.username, "pk": prov_psp_flare.pk}
        )
        prov_next_url = reverse(
            "flares:pseudopatient-update", kwargs={"username": prov_psp.username, "pk": prov_psp_flare.pk}
        )
        prov_psp_redirect_url = f"{reverse('account_login')}?next={prov_next_url}"
        admin = AdminFactory()
        admin_psp = create_psp(provider=admin)
        admin_psp_flare = create_flare(user=admin_psp)
        admin_psp_url = reverse(
            "flares:pseudopatient-update", kwargs={"username": admin_psp.username, "pk": admin_psp_flare.pk}
        )
        admin_next_url = reverse(
            "flares:pseudopatient-update", kwargs={"username": admin_psp.username, "pk": admin_psp_flare.pk}
        )
        admin_psp_redirect_url = f"{reverse('account_login')}?next={admin_next_url}"
        # Create an anonymous Pseudopatient + Flare
        anon_psp = create_psp()
        anon_psp_flare = create_flare(user=anon_psp)
        anon_psp_url = reverse(
            "flares:pseudopatient-update", kwargs={"username": anon_psp.username, "pk": anon_psp_flare.pk}
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
            "urate_check": True,
            "urate-value": Decimal("14.4"),
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.GOUT}-value": False,
            "diagnosed": True,
            "aspiration": True,
        }
        self.angina_context = {
            "form": AnginaForm,
            "model": Angina,
        }
        self.cad_context = {
            "form": CadForm,
            "model": Cad,
        }
        self.chf_context = {
            "form": ChfForm,
            "model": Chf,
        }
        self.ckd_context = {
            "form": CkdForm,
            "model": Ckd,
        }
        self.gout_context = {
            "form": GoutForm,
            "model": Gout,
        }
        self.heartattack_context = {
            "form": HeartattackForm,
            "model": Heartattack,
        }
        self.stroke_context = {
            "form": StrokeForm,
            "model": Stroke,
        }
        self.pvd_context = {
            "form": PvdForm,
            "model": Pvd,
        }
        self.dateofbirth_context = {
            "form": DateOfBirthForm,
            "model": DateOfBirth,
        }
        self.gender_context = {
            "form": GenderForm,
            "model": Gender,
        }
        self.urate_context = {
            "form": UrateFlareForm,
            "model": Urate,
        }

    def test__attrs(self):
        self.assertIn("dateofbirth", self.view.onetoones)
        self.assertEqual(self.dateofbirth_context, self.view.onetoones["dateofbirth"])
        self.assertIn("gender", self.view.onetoones)
        self.assertEqual(self.gender_context, self.view.onetoones["gender"])
        self.assertIn("urate", self.view.onetoones)
        self.assertEqual(self.urate_context, self.view.onetoones["urate"])
        self.assertIn(MedHistoryTypes.ANGINA, self.view.medhistorys)
        self.assertEqual(self.angina_context, self.view.medhistorys[MedHistoryTypes.ANGINA])
        self.assertIn(MedHistoryTypes.CAD, self.view.medhistorys)
        self.assertEqual(self.cad_context, self.view.medhistorys[MedHistoryTypes.CAD])
        self.assertIn(MedHistoryTypes.CHF, self.view.medhistorys)
        self.assertEqual(self.chf_context, self.view.medhistorys[MedHistoryTypes.CHF])
        self.assertIn(MedHistoryTypes.CKD, self.view.medhistorys)
        self.assertEqual(self.ckd_context, self.view.medhistorys[MedHistoryTypes.CKD])
        self.assertIn(MedHistoryTypes.GOUT, self.view.medhistorys)
        self.assertEqual(self.gout_context, self.view.medhistorys[MedHistoryTypes.GOUT])
        self.assertIn(MedHistoryTypes.HEARTATTACK, self.view.medhistorys)
        self.assertEqual(self.heartattack_context, self.view.medhistorys[MedHistoryTypes.HEARTATTACK])
        self.assertIn(MedHistoryTypes.STROKE, self.view.medhistorys)
        self.assertEqual(self.stroke_context, self.view.medhistorys[MedHistoryTypes.STROKE])
        self.assertIn(MedHistoryTypes.PVD, self.view.medhistorys)
        self.assertEqual(self.pvd_context, self.view.medhistorys[MedHistoryTypes.PVD])

    def test__dispatch_redirects_if_flare_user(self):
        """Test that the dispatch() method redirects to the Pseudopatient DetailView if the
        Flare has a user."""
        user_f = create_flare(user=True)
        request = self.factory.get("/fake-url/")
        request.user = AnonymousUser()
        response = self.view.as_view()(request, pk=user_f.pk)
        assert response.status_code == 302
        assert response.url == reverse(
            "flares:pseudopatient-update", kwargs={"username": user_f.user.username, "pk": user_f.pk}
        )

    def test__get_context_data(self):
        """Test the get_context_data() method for the view."""

        # Test that the context data is correct
        request = self.factory.get(f"/flares/update/{self.flare.pk}")
        request.user = AnonymousUser()
        response = FlareUpdate.as_view()(request, pk=self.flare.pk)
        self.assertIsInstance(response.context_data, dict)  # type: ignore
        for medhistory in FLARE_MEDHISTORYS:
            self.assertIn(f"{medhistory}_form", response.context_data)  # type: ignore
            self.assertIsInstance(
                response.context_data[f"{medhistory}_form"], self.view.medhistorys[medhistory]["form"]  # type: ignore
            )
            if response.context_data[
                f"{medhistory}_form"
            ].instance._state.adding:  # pylint: disable=w0212, line-too-long # noqa: E501
                self.assertIsInstance(
                    response.context_data[f"{medhistory}_form"].instance,  # type: ignore
                    self.view.medhistorys[medhistory]["model"],
                )
            else:
                self.assertIn(
                    response.context_data[f"{medhistory}_form"].instance, self.flare.medhistory_set.all()  # type: ignore, line-too-long # noqa: E501
                )
        self.assertIn("dateofbirth_form", response.context_data)  # type: ignore
        self.assertIsInstance(
            response.context_data["dateofbirth_form"], self.view.onetoones["dateofbirth"]["form"]  # type: ignore
        )
        self.assertIsInstance(
            response.context_data["dateofbirth_form"].instance,  # type: ignore
            self.view.onetoones["dateofbirth"]["model"],
        )
        self.assertEqual(response.context_data["dateofbirth_form"].instance, self.flare.dateofbirth)  # type: ignore
        self.assertIsInstance(
            response.context_data["gender_form"], self.view.onetoones["gender"]["form"]  # type: ignore
        )
        self.assertIsInstance(
            response.context_data["gender_form"].instance, self.view.onetoones["gender"]["model"]  # type: ignore
        )
        self.assertEqual(response.context_data["gender_form"].instance, self.flare.gender)  # type: ignore
        self.assertIsInstance(
            response.context_data["urate_form"], self.view.onetoones["urate"]["form"]  # type: ignore
        )
        self.assertIsInstance(
            response.context_data["urate_form"].instance, self.view.onetoones["urate"]["model"]  # type: ignore
        )
        if getattr(self.flare, "urate", None):
            self.assertEqual(response.context_data["urate_form"].instance, self.flare.urate)
        else:
            self.assertTrue(response.context_data["urate_form"].instance._state.adding)  # type: ignore

    def test__post(self):
        """Test that a POST request to the view redirects to the Flare DetailView."""
        data = flare_data_factory()
        response = self.client.post(reverse("flares:update", kwargs={"pk": self.flare.pk}), data)
        tests_print_response_form_errors(response)
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
            tests_print_response_form_errors(response)
            self.assertEqual(response.status_code, 302)
            # Assert that the number of MedHistory objects in the Flare's medhistory_set changed correctly
            self.assertEqual(flare.medhistory_set.count(), mh_count + mh_diff)

    def test__post_change_one_to_ones(self):
        """Test that the post method changes the Flare's one-to-one related objects correctly."""

        # Iterate over some flares
        for flare in Flare.objects.filter(user__isnull=True).all()[:10]:
            # Create some fake data
            data = flare_data_factory()

            # Post the data
            response = self.client.post(reverse("flares:update", kwargs={"pk": flare.pk}), data)
            tests_print_response_form_errors(response)
            self.assertEqual(response.status_code, 302)

            self.flare.refresh_from_db()
            self.assertEqual(age_calc(self.flare.dateofbirth.value), data["dateofbirth-value"])
            self.assertEqual(self.flare.gender.value, data["gender-value"])
            if data.get("urate-value", None):
                self.assertTrue(getattr(self.flare, "urate", None))
                self.assertEqual(self.flare.urate.value, data["urate-value"])

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
                "urate_check": True,
                "urate-value": "",
            }
        )
        response = self.client.post(reverse("flares:update", kwargs={"pk": self.flare.pk}), data=self.flare_data)
        self.assertEqual(response.status_code, 200)
        # Assert that the UrateForm has an error
        tests_print_response_form_errors(response)
        self.assertTrue(response.context_data["urate_form"].errors)
        self.assertEqual(
            response.context_data["urate_form"].errors["value"][0], "If urate was checked, we should know it!"
        )
