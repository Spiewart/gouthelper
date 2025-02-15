from datetime import timedelta
from decimal import Decimal

import pytest  # pylint: disable=e0401 # type: ignore
from django.db.models import Q, QuerySet  # pylint: disable=e0401 # type: ignore
from django.test import RequestFactory, TestCase  # pylint: disable=e0401 # type: ignore
from django.urls import reverse  # pylint: disable=e0401 # type: ignore
from django.utils import timezone  # pylint: disable=e0401 # type: ignore

from ...contents.choices import Tags
from ...contents.models import Content
from ...dateofbirths.helpers import age_calc
from ...ethnicitys.choices import Ethnicitys
from ...ethnicitys.tests.factories import EthnicityFactory
from ...genders.choices import Genders
from ...goalurates.tests.factories import GoalUrateFactory
from ...labs.models import Hlab5801
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.models import Xoiinteraction
from ...treatments.choices import Treatments
from ...ults.tests.factories import create_ult
from ...utils.forms import forms_print_response_errors
from ..models import UltAid
from ..views import UltAidAbout, UltAidCreate, UltAidDetail, UltAidUpdate
from .factories import create_ultaid, ultaid_data_factory

pytestmark = pytest.mark.django_db


class TestUltAidAbout(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltAidAbout = UltAidAbout()

    def test__get(self):
        response = self.client.get(reverse("ultaids:about"))
        self.assertEqual(response.status_code, 200)

    def test__get_context_data(self):
        response = self.client.get(reverse("ultaids:about"))
        self.assertIn("content", response.context_data)

    def test__content(self):
        self.assertEqual(
            self.view.content, Content.objects.get(context=Content.Contexts.ULTAID, slug="about", tag=None)
        )


class TestUltAidCreate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltAidCreate = UltAidCreate()

    def test__get_with_ult_resolves(self):
        ult = create_ult()
        response = self.client.get(reverse("ultaids:ult-create", kwargs={"ult": ult.pk}))
        self.assertEqual(response.status_code, 200)

    def test__post_adds_hlab5801_True(self):
        """Tests that a POST request adds a Hlab5801 instance as an attribute
        to the created UltAid."""
        # Create some fake data and add hlab5801-value to it
        ultaid_data = ultaid_data_factory()
        ultaid_data.update({"hlab5801-value": True})

        # Post the data to the view and make sure it responds correctly
        response = self.client.post(reverse("ultaids:create"), ultaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        # Test that the UltAid and Hlab5801 objects were created
        ultaid = UltAid.objects.order_by("created").last()
        hlab5801 = Hlab5801.objects.order_by("created").last()
        self.assertEqual(ultaid.hlab5801, hlab5801)
        self.assertTrue(hlab5801.value)

    def test__post_adds_hlab5801_False(self):
        """Tests that a POST request adds a Hlab5801 instance as an attribute
        to the created UltAid."""
        # Create some fake data and add hlab5801-value to it
        ultaid_data = ultaid_data_factory()
        ultaid_data.update({"hlab5801-value": False})

        # Post the data to the view and make sure it responds correctly
        response = self.client.post(reverse("ultaids:create"), ultaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        # Test that the UltAid and Hlab5801 objects were created
        ultaid = UltAid.objects.order_by("created").last()
        hlab5801 = Hlab5801.objects.order_by("created").last()
        self.assertEqual(ultaid.hlab5801, hlab5801)
        self.assertFalse(hlab5801.value)

    def test__post_doesnt_add_hlab5801(self):
        """Tests that a POST request adds a Hlab5801 instance as an attribute
        to the created UltAid."""
        # Create some fake data without hlab5801-value
        ultaid_data = ultaid_data_factory()
        ultaid_data.update({"hlab5801-value": ""})

        # Post the data to the view and make sure it responds correctly
        response = self.client.post(reverse("ultaids:create"), ultaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        # Test that the UltAid and Hlab5801 objects were created
        ultaid = UltAid.objects.order_by("created").last()
        self.assertIsNone(ultaid.hlab5801)

    def test__post_adds_xoiinteraction_contraindicates_xois(self):
        """Tests that a POST request adds a Hlab5801 instance as an attribute
        to the created UltAid."""
        ultaid_data = {
            "dateofbirth-value": age_calc(timezone.now() - timedelta(days=365 * 50)),
            "gender-value": Genders.FEMALE,
            "ethnicity-value": Ethnicitys.CAUCASIANAMERICAN,
            "hlab5801-value": "",
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.HEPATITIS}-value": True,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"{MedHistoryTypes.URATESTONES}-value": False,
            f"{MedHistoryTypes.XOIINTERACTION}-value": True,
        }
        response = self.client.post(reverse("ultaids:create"), ultaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(UltAid.objects.exists())
        ultaid = UltAid.objects.get()
        self.assertTrue(Xoiinteraction.objects.exists())
        xoiinteraction = Xoiinteraction.objects.order_by("created").last()
        self.assertIn(xoiinteraction, ultaid.medhistory_set.all())
        self.assertNotIn(Treatments.ALLOPURINOL, ultaid.options)
        self.assertNotIn(Treatments.FEBUXOSTAT, ultaid.options)
        self.assertEqual(Treatments.PROBENECID, ultaid.recommendation[0])

    def test__post_with_ult_dateofbirth_gender_ckd(self):
        ult = create_ult(
            mhs=[MedHistoryTypes.CKD],
            gender=Genders.MALE,
            dateofbirth=timezone.now() - timedelta(days=365 * 40),
            baselinecreatinine=Decimal("2.0"),
        )
        self.assertTrue(ult.medhistory_set.filter(medhistorytype=MedHistoryTypes.CKD).exists())
        self.assertTrue(ult.dateofbirth)
        self.assertTrue(ult.gender)
        ultaid_data = {
            "dateofbirth-value": ult.dateofbirth.value,
            "gender-value": ult.gender.value,
            "ethnicity-value": Ethnicitys.CAUCASIANAMERICAN,
            "hlab5801-value": "",
            f"{MedHistoryTypes.CKD}-value": True,
            "dialysis": ult.ckddetail.dialysis,
            "baselinecreatinine": ult.baselinecreatinine.value,
            "stage": ult.ckddetail.stage,
            f"{MedHistoryTypes.HEPATITIS}-value": True,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"{MedHistoryTypes.URATESTONES}-value": False,
            f"{MedHistoryTypes.XOIINTERACTION}-value": True,
        }
        response = self.client.post(reverse("ultaids:ult-create", kwargs={"ult": ult.pk}), ultaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

    def test__get_with_ult_adds_ult_medhistorys_to_context_as_true(self):
        ult = create_ult(mhs=[MedHistoryTypes.CKD, MedHistoryTypes.URATESTONES])
        self.assertTrue(ult.medhistory_set.filter(medhistorytype=MedHistoryTypes.CKD).exists())
        self.assertTrue(ult.medhistory_set.filter(medhistorytype=MedHistoryTypes.URATESTONES).exists())
        response = self.client.get(reverse("ultaids:ult-create", kwargs={"ult": ult.pk}))
        self.assertTrue(response.context_data[f"{MedHistoryTypes.CKD}_form"].fields[f"{MedHistoryTypes.CKD}-value"])
        self.assertTrue(
            response.context_data[f"{MedHistoryTypes.URATESTONES}_form"].fields[f"{MedHistoryTypes.URATESTONES}-value"]
        )

    def test__get_with_ult_adds_age_gender_from_ult_to_context(self):
        ult = create_ult(
            mhs=[MedHistoryTypes.CKD],
            gender=Genders.MALE,
            dateofbirth=timezone.now() - timedelta(days=365 * 40),
            baselinecreatinine=Decimal("2.0"),
        )
        self.assertTrue(ult.medhistory_set.filter(medhistorytype=MedHistoryTypes.CKD).exists())
        self.assertTrue(ult.dateofbirth)
        self.assertTrue(ult.gender)
        response = self.client.get(reverse("ultaids:ult-create", kwargs={"ult": ult.pk}))
        self.assertIn("age", response.context_data)
        self.assertEqual(response.context_data["age"], ult.age)
        self.assertIn("gender", response.context_data)
        self.assertEqual(response.context_data["gender"], ult.gender.value)


class TestUltAidDetail(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltAidDetail = UltAidDetail
        self.content_qs = Content.objects.filter(
            Q(tag=Tags.EXPLANATION) | Q(tag=Tags.WARNING), context=Content.Contexts.ULTAID, slug__isnull=False
        ).all()
        # Need to set ethnicity to Caucasian to avoid HLA-B*5801 contraindication with high risk ethnicity
        self.ultaid = create_ultaid(
            mas=[], mhs=[], ethnicity=EthnicityFactory(value=Ethnicitys.CAUCASIANAMERICAN), hlab5801=False
        )

    def test__get_context_data(self):
        response = self.client.get(reverse("ultaids:detail", kwargs={"pk": self.ultaid.pk}))
        context = response.context_data
        for content in self.content_qs:
            self.assertIn(content.slug, context)
            self.assertEqual(context[content.slug], {content.tag: content})

    def test__get_queryset(self):
        # Create a GoalUrate to and add it to the ultaid object to test the qs
        GoalUrateFactory(ultaid=self.ultaid)
        qs = self.view(kwargs={"pk": self.ultaid.pk}).get_queryset()
        self.assertTrue(isinstance(qs, QuerySet))
        qs_obj = qs.first()
        self.assertEqual(qs_obj, self.ultaid)
        self.assertTrue(hasattr(qs_obj, "medhistorys_qs"))
        self.assertTrue(hasattr(qs_obj, "medallergys_qs"))
        self.assertTrue(hasattr(qs_obj, "ckddetail"))
        self.assertTrue(hasattr(qs_obj, "baselinecreatinine"))
        self.assertTrue(hasattr(qs_obj, "dateofbirth"))
        self.assertTrue(hasattr(qs_obj, "gender"))
        self.assertTrue(hasattr(qs_obj, "ethnicity"))
        self.assertTrue(hasattr(qs_obj, "hlab5801"))
        self.assertTrue(hasattr(qs_obj, "goalurate"))

    def test__get_object_updates(self):
        self.assertTrue(self.ultaid.recommendation[0] == Treatments.ALLOPURINOL)
        MedAllergyFactory(treatment=Treatments.ALLOPURINOL, ultaid=self.ultaid)
        response = self.client.get(reverse("ultaids:detail", kwargs={"pk": self.ultaid.pk}))
        self.assertEqual(response.status_code, 200)
        ultaid = UltAid.objects.get(pk=self.ultaid.pk)
        # This needs to be manually refetched from the db
        self.assertFalse(ultaid.recommendation[0] == Treatments.ALLOPURINOL)


class TestUltAidUpdate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltAidUpdate = UltAidUpdate()

    def test__post_removes_hlab5801(self):
        """Test that a POST request removes a Hlab5801 instance as an attribute
        to the updated UltAid and deletes the Hlab5801 instance."""
        ultaid = create_ultaid(hlab5801=True)
        self.assertTrue(Hlab5801.objects.all())
        self.assertEqual(UltAid.objects.get().hlab5801, Hlab5801.objects.get())
        ultaid_data = ultaid_data_factory(ultaid=ultaid, otos={"hlab5801": ""})
        response = self.client.post(reverse("ultaids:update", kwargs={"pk": ultaid.pk}), ultaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Hlab5801.objects.all())
        ultaid.refresh_from_db()
        self.assertIsNone(ultaid.hlab5801)

    def test__post_adds_False_hlab5801(self):
        """Test that a POST request creates and adds a Hlab5801 instance, with
        a value=False, as an attribute to the updated UltAid."""
        ultaid = create_ultaid(hlab5801=None)
        self.assertFalse(Hlab5801.objects.all())
        self.assertIsNone(UltAid.objects.get().hlab5801)
        ultaid_data = ultaid_data_factory(ultaid=ultaid, otos={"hlab5801": False})
        response = self.client.post(reverse("ultaids:update", kwargs={"pk": ultaid.pk}), ultaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        ultaid.refresh_from_db()
        self.assertTrue(Hlab5801.objects.all())
        hlab5801 = Hlab5801.objects.get()
        self.assertEqual(ultaid.hlab5801, hlab5801)
        self.assertFalse(hlab5801.value)

    def test__post_adds_True_hlab5801(self):
        """Test that a POST request creates and adds a Hlab5801 instance, with
        a value=True, as an attribute to the updated UltAid."""
        ultaid = create_ultaid(hlab5801=None)
        self.assertFalse(Hlab5801.objects.all())
        self.assertIsNone(UltAid.objects.get().hlab5801)
        ultaid_data = ultaid_data_factory(ultaid=ultaid, otos={"hlab5801": True})
        response = self.client.post(reverse("ultaids:update", kwargs={"pk": ultaid.pk}), ultaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        ultaid.refresh_from_db()
        self.assertTrue(Hlab5801.objects.all())
        hlab5801 = Hlab5801.objects.get()
        self.assertEqual(ultaid.hlab5801, hlab5801)
        self.assertTrue(hlab5801.value)

    def test__post_removes_updates_hlab5801_True_to_False(self):
        """Test that a POST request updates a Hlab5801 object / UltAid attribute
        from True to False."""
        ultaid = create_ultaid(hlab5801=True)
        self.assertTrue(Hlab5801.objects.all())
        self.assertEqual(UltAid.objects.get().hlab5801, Hlab5801.objects.get())
        ultaid_data = ultaid_data_factory(ultaid=ultaid, otos={"hlab5801": False})
        response = self.client.post(reverse("ultaids:update", kwargs={"pk": ultaid.pk}), ultaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        self.assertTrue(Hlab5801.objects.all())
        hlab5801 = Hlab5801.objects.get()
        ultaid.refresh_from_db()
        self.assertEqual(ultaid.hlab5801, hlab5801)
        self.assertFalse(hlab5801.value)

    def test__post_removes_updates_hlab5801_False_to_True(self):
        """Test that a POST request updates a Hlab5801 object / UltAid attribute
        from False to True."""
        ultaid = create_ultaid(hlab5801=False)
        self.assertTrue(Hlab5801.objects.all())
        self.assertEqual(UltAid.objects.get().hlab5801, Hlab5801.objects.get())
        ultaid_data = ultaid_data_factory(ultaid=ultaid, otos={"hlab5801": True})

        response = self.client.post(reverse("ultaids:update", kwargs={"pk": ultaid.pk}), ultaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)

        self.assertTrue(Hlab5801.objects.all())
        hlab5801 = Hlab5801.objects.get()
        ultaid.refresh_from_db()
        self.assertEqual(ultaid.hlab5801, hlab5801)
        self.assertTrue(hlab5801.value)

    def test__post_ckd_without_detail_saves(self):
        """Test that a POST request can create or update a CKD instance without
        an associated CkdDetail instance. This is unique to certain models, like
        UltAid, that doesn't require CkdDetail for processing."""
        ultaid = create_ultaid(mhs=[])
        self.assertFalse(ultaid.ckd)
        self.assertFalse(ultaid.ckddetail)
        ultaid_data = ultaid_data_factory(ultaid=ultaid, mhs=[MedHistoryTypes.CKD])
        response = self.client.post(reverse("ultaids:update", kwargs={"pk": ultaid.pk}), ultaid_data)
        forms_print_response_errors(response)
        self.assertEqual(response.status_code, 302)
        ultaid = UltAid.objects.get(pk=ultaid.pk)
        self.assertTrue(ultaid.ckd)
        self.assertFalse(ultaid.ckddetail)
