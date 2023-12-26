from datetime import timedelta
from decimal import Decimal

import pytest
from django.db.models import Q, QuerySet  # type: ignore
from django.forms import model_to_dict  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils import timezone  # type: ignore

from ...contents.models import Content
from ...dateofbirths.forms import DateOfBirthForm
from ...dateofbirths.helpers import age_calc, yearsago
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
from ...medhistorys.models import Angina, Cad, Chf, Ckd, Gout, Heartattack, Menopause, Pvd, Stroke
from ...medhistorys.tests.factories import AnginaFactory, ChfFactory, GoutFactory, MenopauseFactory
from ...utils.helpers.test_helpers import tests_print_response_form_errors
from ..choices import Likelihoods, LimitedJointChoices, Prevalences
from ..forms import FlareForm
from ..models import Flare
from ..views import FlareAbout, FlareBase, FlareCreate, FlareDetail, FlareUpdate
from .factories import FlareFactory

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
        self.flare = FlareFactory(
            dateofbirth=DateOfBirthFactory(value=timezone.now().date() - timedelta(days=365 * 50)),
            gender=GenderFactory(value=Genders.FEMALE),
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

    def test__post_process_menopause(self):
        _, errors_bool = self.view.post_process_menopause(
            self.medhistorys_forms,
            self.flare,
        )
        # Assert there are no errors on the menopause form
        self.assertFalse(self.menopause_form.errors)
        self.assertFalse(errors_bool)
        # Change the menopause data to make it invalid (no value)
        self.menopause_data.update({f"{MedHistoryTypes.MENOPAUSE}-value": None})
        # Need to create new form instance to re-run is_valid and clean
        # NOTE: This is because the form is already bound to the data ???
        new_menopause_form = MenopauseForm(data=self.menopause_data)
        # Re-run is_valid and clean
        new_menopause_form.data = self.menopause_data
        new_menopause_form.is_valid()
        new_menopause_form.clean()
        self.medhistorys_forms.update({f"{MedHistoryTypes.MENOPAUSE}_form": new_menopause_form})
        _, errors_bool = self.view.post_process_menopause(
            self.medhistorys_forms,
            self.flare,
        )
        # Assert there are errors on the menopause form
        self.assertTrue(new_menopause_form.errors)
        self.assertTrue(errors_bool)
        # Change the flare.dateofbirth to make it too young for menopause
        self.flare.dateofbirth.value = timezone.now().date() - timedelta(days=365 * 39)
        self.flare.dateofbirth.save()
        self.medhistorys_forms.update({f"{MedHistoryTypes.MENOPAUSE}_form": new_menopause_form})
        _, errors_bool = self.view.post_process_menopause(
            self.medhistorys_forms,
            self.flare,
        )
        # Assert the errors_bool is False
        # Form not tested because we didn't create a new one and the errors are the same
        self.assertFalse(errors_bool)
        # Change the flare.dateofbirth to make it too old for menopause
        self.flare.dateofbirth.value = timezone.now().date() - timedelta(days=365 * 61)
        self.flare.dateofbirth.save()
        self.medhistorys_forms.update({f"{MedHistoryTypes.MENOPAUSE}_form": new_menopause_form})
        _, errors_bool = self.view.post_process_menopause(
            self.medhistorys_forms,
            self.flare,
        )
        # Assert the errors_bool is False
        # Form not tested because we didn't create a new one and the errors are the same
        self.assertFalse(errors_bool)
        self.flare.dateofbirth.value = timezone.now().date() - timedelta(days=365 * 45)
        self.flare.dateofbirth.save()
        self.medhistorys_forms.update({f"{MedHistoryTypes.MENOPAUSE}_form": new_menopause_form})
        _, errors_bool = self.view.post_process_menopause(
            self.medhistorys_forms,
            self.flare,
        )
        self.assertTrue(errors_bool)
        # Test male gender doesn't need menopause
        self.flare.gender.value = Genders.MALE
        self.flare.gender.save()
        self.medhistorys_forms.update({f"{MedHistoryTypes.MENOPAUSE}_form": new_menopause_form})
        _, errors_bool = self.view.post_process_menopause(
            self.medhistorys_forms,
            self.flare,
        )
        self.assertFalse(errors_bool)

    def test__post_process_urate_check(self):
        _, _, errors_bool = self.view.post_process_urate_check(
            self.form,
            self.flare,
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
            self.flare,
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
        response = self.client.post(reverse("flares:create"), self.flare_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Flare.objects.count(), 1)
        self.assertEqual(DateOfBirth.objects.count(), 1)
        self.assertEqual(Gender.objects.count(), 1)
        flare = Flare.objects.get()
        dateofbirth = DateOfBirth.objects.get()
        gender = Gender.objects.get()
        self.assertEqual(dateofbirth, flare.dateofbirth)
        self.assertEqual(gender, flare.gender)

    def test__post_medhistorys(self):
        self.flare_data.update(
            {
                f"{MedHistoryTypes.ANGINA}-value": True,
            }
        )
        response = self.client.post(reverse("flares:create"), self.flare_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Flare.objects.count(), 1)
        self.assertEqual(Angina.objects.count(), 1)
        flare = Flare.objects.get()
        angina = Angina.objects.get()
        menopause = Menopause.objects.get()
        self.assertIn(angina, flare.medhistorys.all())
        self.assertIn(menopause, flare.medhistorys.all())
        self.assertEqual(flare.medhistorys.count(), 2)

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
        self.assertEqual(Flare.objects.count(), 1)
        self.assertEqual(Urate.objects.count(), 1)
        self.assertEqual(Menopause.objects.count(), 1)
        flare = Flare.objects.get()
        urate = Urate.objects.get()
        menopause = Menopause.objects.get()
        self.assertEqual(urate, flare.urate)
        self.assertEqual(flare.medhistorys.count(), 4)
        self.assertIn(menopause, flare.medhistorys.all())

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
        self.assertEqual(Flare.objects.count(), 0)
        self.assertEqual(Angina.objects.count(), 0)
        self.assertFalse(response.context_data["form"].errors)  # type: ignore
        self.assertTrue(response.context_data["gender_form"].errors)  # type: ignore
        self.assertIn("value", response.context_data["gender_form"].errors)  # type: ignore

    def test__post_menopause_not_valid(self):
        self.flare_data.update(
            {
                f"{MedHistoryTypes.MENOPAUSE}-value": "",
            }
        )
        response = self.client.post(reverse("flares:create"), self.flare_data)
        self.assertEqual(response.status_code, 200)
        # Assert that the MenopauseForm has an error
        self.assertTrue(response.context_data[f"{MedHistoryTypes.MENOPAUSE}_form"].errors)  # type: ignore
        self.assertEqual(
            response.context_data[f"{MedHistoryTypes.MENOPAUSE}_form"].errors[f"{MedHistoryTypes.MENOPAUSE}-value"][0],
            "For females between ages 40 and 60, we need to know the patient's \
menopause status to evaluate their flare.",
        )

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
        self.flare = FlareFactory()
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
        self.view.as_view()(request, pk=self.flare.pk)
        # This needs to be manually refetched from the db
        self.assertIsNotNone(Flare.objects.get().likelihood)
        self.assertIsNotNone(Flare.objects.get().prevalence)

    def test__get_object_does_not_update(self):
        self.assertIsNone(self.flare.likelihood)
        self.assertIsNone(self.flare.prevalence)
        request = self.factory.get(reverse("flares:detail", kwargs={"pk": self.flare.pk}) + "?updated=True")
        self.view.as_view()(request, pk=self.flare.pk)
        # This needs to be manually refetched from the db
        self.assertIsNone(Flare.objects.get().likelihood)
        self.assertIsNone(Flare.objects.get().prevalence)


class TestFlareUpdate(TestCase):
    def setUp(self):
        self.flare = FlareFactory(gender=GenderFactory(value=Genders.MALE))
        self.factory = RequestFactory()
        self.view: FlareUpdate = FlareUpdate()
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

    def test__form_valid_updates_new_medhistorys(self):
        flare = FlareFactory(
            crystal_analysis=None,
            date_started=timezone.now().date() - timedelta(days=35),
            date_ended=timezone.now().date() - timedelta(days=5),
            dateofbirth=DateOfBirthFactory(value=timezone.now().date() - timedelta(days=365 * 24)),
            gender=GenderFactory(value=Genders.FEMALE),
            joints=[LimitedJointChoices.ELBOWL],
            onset=False,
            redness=False,
            urate=UrateFactory(value=Decimal("5.0")),
            diagnosed=False,
        )
        flare.update()
        flare.refresh_from_db()
        self.assertEqual(flare.prevalence, Prevalences.LOW)
        self.assertEqual(flare.likelihood, Likelihoods.UNLIKELY)
        angina = AnginaFactory()
        chf = ChfFactory()
        menopause = MenopauseFactory()
        gout = GoutFactory()
        flare.add_medhistorys([angina, chf, gout, menopause])
        flare.refresh_from_db()
        for medhistory in flare.medhistorys.all():
            self.flare_data[f"{medhistory.medhistorytype}-value"] = True
        response = self.client.post(reverse("flares:update", kwargs={"pk": flare.pk}), self.flare_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        flare.refresh_from_db()
        self.assertEqual(flare.prevalence, Prevalences.HIGH)
        self.assertEqual(flare.likelihood, Likelihoods.LIKELY)

    def test__form_valid_updates_urate(self):
        flare = FlareFactory(
            crystal_analysis=None,
            date_started=timezone.now().date() - timedelta(days=35),
            date_ended=timezone.now().date() - timedelta(days=5),
            dateofbirth=DateOfBirthFactory(value=timezone.now().date() - timedelta(days=365 * 24)),
            gender=GenderFactory(value=Genders.FEMALE),
            joints=[LimitedJointChoices.ELBOWL],
            onset=True,
            redness=False,
            urate=None,
            diagnosed=False,
        )
        flare.medhistorys.add(MenopauseFactory())
        flare.update()
        flare.refresh_from_db()
        self.assertEqual(flare.prevalence, Prevalences.LOW)
        self.assertEqual(flare.likelihood, Likelihoods.UNLIKELY)
        # Test create Urate
        flare_data = {
            "crystal_analysis": "",
            "date_ended": flare.date_ended,
            "date_started": flare.date_started,
            "dateofbirth-value": age_calc(flare.dateofbirth.value),
            "gender-value": flare.gender.value,
            "joints": flare.joints,
            "onset": flare.onset,
            "redness": flare.redness,
            "urate_check": True,
            "urate-value": Decimal("14.4"),
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.GOUT}-value": False,
            "diagnosed": flare.diagnosed,
        }
        self.client.post(reverse("flares:update", kwargs={"pk": flare.pk}), flare_data)
        flare.refresh_from_db()
        self.assertEqual(flare.prevalence, Prevalences.MEDIUM)
        self.assertEqual(flare.likelihood, Likelihoods.UNLIKELY)
        # Test delete urate
        flare_data = {
            "crystal_analysis": "",
            "date_ended": flare.date_ended,
            "date_started": flare.date_started,
            "dateofbirth-value": age_calc(flare.dateofbirth.value),
            "gender-value": flare.gender.value,
            "joints": flare.joints,
            "onset": flare.onset,
            "redness": flare.redness,
            "urate_check": False,
            "urate-value": "",
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.GOUT}-value": False,
            "diagnosed": flare.diagnosed,
        }
        self.client.post(reverse("flares:update", kwargs={"pk": flare.pk}), flare_data)
        flare.refresh_from_db()
        # Need to delete the aid_dict cached_propert to refresh it so test passes.
        self.assertEqual(flare.prevalence, Prevalences.LOW)
        self.assertEqual(flare.likelihood, Likelihoods.UNLIKELY)
        self.assertIsNone(flare.urate)

    def test__get_context_data(self):
        angina = AnginaFactory()
        chf = ChfFactory()
        self.flare.medhistorys.add(angina)
        self.flare.medhistorys.add(chf)
        request = self.factory.get(f"/flares/update/{self.flare.pk}")
        response = FlareUpdate.as_view()(request, pk=self.flare.pk)
        self.assertIsInstance(response.context_data, dict)  # type: ignore
        for medhistory in FLARE_MEDHISTORYS:
            self.assertIn(f"{medhistory}_form", response.context_data)  # type: ignore
            self.assertIsInstance(
                response.context_data[f"{medhistory}_form"], self.view.medhistorys[medhistory]["form"]  # type: ignore
            )
            if response.context_data[f"{medhistory}_form"].instance._state.adding:  # type: ignore
                self.assertIsInstance(
                    response.context_data[f"{medhistory}_form"].instance,  # type: ignore
                    self.view.medhistorys[medhistory]["model"],
                )
            else:
                self.assertIn(
                    response.context_data[f"{medhistory}_form"].instance, self.flare.medhistorys.all()  # type: ignore
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
        self.assertEqual(response.context_data["urate_form"].instance, self.flare.urate)  # type: ignore

    def test__post_no_changes(self):
        angina = AnginaFactory()
        chf = ChfFactory()
        self.flare.medhistorys.add(angina)
        self.flare.medhistorys.add(chf)
        flare_data = {
            "crystal_analysis": "",
            "date_ended": "",
            "date_started": self.flare.date_started,
            "dateofbirth-value": age_calc(self.flare.dateofbirth.value),
            "gender-value": self.flare.gender.value,
            "joints": self.flare.joints,
            "onset": self.flare.onset,
            "redness": self.flare.redness,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.GOUT}-value": False,
            "urate_check": True,
            "urate-value": self.flare.urate.value,
            "diagnosed": self.flare.diagnosed,
        }
        for medhistory in self.flare.medhistorys.all():
            flare_data[f"{medhistory.medhistorytype}-value"] = True
        response = self.client.post(reverse("flares:update", kwargs={"pk": self.flare.pk}), flare_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form"):
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.flare.refresh_from_db()

    def test__post_add_medhistorys(self):
        angina = AnginaFactory()
        chf = ChfFactory()
        self.flare.medhistorys.add(angina)
        self.flare.medhistorys.add(chf)
        flare_data = {
            "crystal_analysis": "",
            "date_ended": "",
            "date_started": self.flare.date_started,
            "dateofbirth-value": age_calc(self.flare.dateofbirth.value),
            "gender-value": self.flare.gender.value,
            "joints": self.flare.joints,
            "onset": self.flare.onset,
            "redness": self.flare.redness,
            "urate_check": True,
            "urate-value": self.flare.urate.value,
            "diagnosed": self.flare.diagnosed,
            f"{MedHistoryTypes.CKD}-value": False,
        }
        for medhistory in self.flare.medhistorys.all():
            flare_data[f"{medhistory.medhistorytype}-value"] = True
        flare_data[f"{MedHistoryTypes.CAD}-value"] = True
        flare_data[f"{MedHistoryTypes.GOUT}-value"] = True
        flare_data[f"{MedHistoryTypes.STROKE}-value"] = True
        response = self.client.post(reverse("flares:update", kwargs={"pk": self.flare.pk}), flare_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.flare.refresh_from_db()
        medhistorys = self.flare.medhistorys.all()
        self.assertIn(angina, medhistorys)
        self.assertIn(Cad.objects.last(), medhistorys)
        self.assertIn(chf, medhistorys)
        self.assertIn(Stroke.objects.last(), medhistorys)

    def test__post_remove_medhistorys(self):
        angina = AnginaFactory()
        chf = ChfFactory()
        self.flare.medhistorys.add(angina)
        self.flare.medhistorys.add(chf)
        flare_data = {
            "crystal_analysis": "",
            "date_ended": "",
            "date_started": self.flare.date_started,
            "dateofbirth-value": age_calc(self.flare.dateofbirth.value),
            "gender-value": self.flare.gender.value,
            "joints": self.flare.joints,
            "onset": self.flare.onset,
            "redness": self.flare.redness,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.GOUT}-value": False,
            "urate_check": True,
            "urate-value": self.flare.urate.value,
            "diagnosed": self.flare.diagnosed,
        }
        response = self.client.post(reverse("flares:update", kwargs={"pk": self.flare.pk}), flare_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        #    if key.endswith("_form") or key == "form":
        #        print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.flare.refresh_from_db()
        medhistorys = self.flare.medhistorys.all()
        self.assertNotIn(angina, medhistorys)
        self.assertNotIn(chf, medhistorys)

    def test__post_change_one_to_ones(self):
        self.flare.dateofbirth.value = timezone.datetime(1973, 3, 3).date()
        self.flare.dateofbirth.save()
        self.flare.gender.value = Genders.MALE
        self.flare.gender.save()
        angina = AnginaFactory()
        chf = ChfFactory()
        self.flare.medhistorys.add(angina)
        self.flare.medhistorys.add(chf)
        new_age = 42
        new_date_of_birth = yearsago(new_age).date()
        flare_data = {
            "crystal_analysis": "",
            "date_ended": "",
            "date_started": self.flare.date_started,
            "dateofbirth-value": new_age,
            "gender-value": Genders.FEMALE,
            "joints": self.flare.joints,
            "onset": self.flare.onset,
            "redness": self.flare.redness,
            "urate_check": False,
            "urate-value": "",
            "diagnosed": self.flare.diagnosed,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.GOUT}-value": False,
            f"{MedHistoryTypes.MENOPAUSE}-value": True,
        }
        for medhistory in self.flare.medhistorys.all():
            flare_data[f"{medhistory.medhistorytype}-value"] = True
        response = self.client.post(reverse("flares:update", kwargs={"pk": self.flare.pk}), flare_data)
        self.assertEqual(response.status_code, 302)
        self.flare.refresh_from_db()
        self.assertEqual(self.flare.dateofbirth.value, new_date_of_birth)
        self.assertEqual(self.flare.gender.value, Genders.FEMALE)
        self.assertIsNone(self.flare.urate)
        self.assertFalse(Urate.objects.all())

    def test__post_forms_not_valid(self):
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
