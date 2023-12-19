from datetime import timedelta

import pytest  # type: ignore
from django.db.models import Q, QuerySet  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils import timezone  # type: ignore

from ...contents.choices import Tags
from ...contents.models import Content
from ...ethnicitys.choices import Ethnicitys
from ...ethnicitys.tests.factories import EthnicityFactory
from ...genders.choices import Genders
from ...goalurates.tests.factories import GoalUrateFactory
from ...labs.models import Hlab5801
from ...labs.tests.factories import Hlab5801Factory
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.models import Xoiinteraction
from ...treatments.choices import Treatments
from ..models import UltAid
from ..views import UltAidAbout, UltAidCreate, UltAidDetail, UltAidUpdate
from .factories import UltAidFactory

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

    def test__post_adds_hlab5801_True(self):
        """Tests that a POST request adds a Hlab5801 instance as an attribute
        to the created UltAid."""
        ultaid_data = {
            "dateofbirth-value": (timezone.now() - timedelta(days=365 * 50)).date(),
            "gender-value": Genders.FEMALE,
            "ethnicity-value": Ethnicitys.CAUCASIANAMERICAN,
            "hlab5801-value": True,
            f"{MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY}-value": False,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"{MedHistoryTypes.XOIINTERACTION}-value": False,
        }
        response = self.client.post(reverse("ultaids:create"), ultaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(UltAid.objects.get())
        self.assertTrue(Hlab5801.objects.get())
        self.assertTrue(Hlab5801.objects.get().value)
        self.assertEqual(UltAid.objects.get().hlab5801, Hlab5801.objects.get())

    def test__post_adds_hlab5801_False(self):
        """Tests that a POST request adds a Hlab5801 instance as an attribute
        to the created UltAid."""
        ultaid_data = {
            "dateofbirth-value": (timezone.now() - timedelta(days=365 * 50)).date(),
            "gender-value": Genders.FEMALE,
            "ethnicity-value": Ethnicitys.CAUCASIANAMERICAN,
            "hlab5801-value": False,
            f"{MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY}-value": False,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"{MedHistoryTypes.XOIINTERACTION}-value": False,
        }
        response = self.client.post(reverse("ultaids:create"), ultaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(UltAid.objects.get())
        self.assertTrue(Hlab5801.objects.get())
        self.assertFalse(Hlab5801.objects.get().value)
        self.assertEqual(UltAid.objects.get().hlab5801, Hlab5801.objects.get())

    def test__post_doesnt_add_hlab5801(self):
        """Tests that a POST request adds a Hlab5801 instance as an attribute
        to the created UltAid."""
        ultaid_data = {
            "dateofbirth-value": (timezone.now() - timedelta(days=365 * 50)).date(),
            "gender-value": Genders.FEMALE,
            "ethnicity-value": Ethnicitys.CAUCASIANAMERICAN,
            "hlab5801-value": "",
            f"{MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY}-value": False,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"{MedHistoryTypes.XOIINTERACTION}-value": False,
        }
        response = self.client.post(reverse("ultaids:create"), ultaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(UltAid.objects.get())
        self.assertFalse(Hlab5801.objects.all())
        self.assertIsNone(UltAid.objects.get().hlab5801)

    def test__post_adds_xoiinteraction_contraindicates_xois(self):
        """Tests that a POST request adds a Hlab5801 instance as an attribute
        to the created UltAid."""
        ultaid_data = {
            "dateofbirth-value": (timezone.now() - timedelta(days=365 * 50)).date(),
            "gender-value": Genders.FEMALE,
            "ethnicity-value": Ethnicitys.CAUCASIANAMERICAN,
            "hlab5801-value": "",
            f"{MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY}-value": False,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"{MedHistoryTypes.XOIINTERACTION}-value": True,
        }
        response = self.client.post(reverse("ultaids:create"), ultaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(UltAid.objects.exists())
        ultaid = UltAid.objects.get()
        self.assertTrue(Xoiinteraction.objects.exists())
        xoiinteraction = Xoiinteraction.objects.get()
        self.assertIn(xoiinteraction, ultaid.medhistorys.all())
        self.assertNotIn(Treatments.ALLOPURINOL, ultaid.options)
        self.assertNotIn(Treatments.FEBUXOSTAT, ultaid.options)
        self.assertEqual(Treatments.PROBENECID, ultaid.recommendation[0])


class TestUltAidDetail(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltAidDetail = UltAidDetail
        self.content_qs = Content.objects.filter(
            Q(tag=Tags.EXPLANATION) | Q(tag=Tags.WARNING), context=Content.Contexts.ULTAID, slug__isnull=False
        ).all()
        # Need to set ethnicity to Caucasian to avoid HLA-B*5801 contraindication with high risk ethnicity
        self.ultaid = UltAidFactory(ethnicity=EthnicityFactory(value=Ethnicitys.CAUCASIANAMERICAN))

    def test__contents(self):
        self.assertTrue(self.view().contents)
        self.assertTrue(isinstance(self.view().contents, QuerySet))
        for content in self.view().contents:
            self.assertIn(content, self.content_qs)
        for content in self.content_qs:
            self.assertIn(content, self.view().contents)

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
        medallergy = MedAllergyFactory(treatment=Treatments.ALLOPURINOL)
        self.ultaid.medallergys.add(medallergy)
        request = self.factory.get(reverse("ultaids:detail", kwargs={"pk": self.ultaid.pk}))
        self.view.as_view()(request, pk=self.ultaid.pk)
        # This needs to be manually refetched from the db
        self.assertFalse(UltAid.objects.get().recommendation[0] == Treatments.ALLOPURINOL)


class TestUltAidUpdate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltAidUpdate = UltAidUpdate()

    def test__post_removes_hlab5801(self):
        """Test that a POST request removes a Hlab5801 instance as an attribute
        to the updated UltAid and deletes the Hlab5801 instance."""
        ultaid = UltAidFactory(hlab5801=Hlab5801Factory(value=True))
        self.assertTrue(Hlab5801.objects.all())
        self.assertEqual(UltAid.objects.get().hlab5801, Hlab5801.objects.get())
        ultaid_data = {
            "dateofbirth-value": ultaid.dateofbirth.value,
            "gender-value": ultaid.gender.value,
            "ethnicity-value": ultaid.ethnicity.value,
            "hlab5801-value": "",
            f"{MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY}-value": False,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"{MedHistoryTypes.XOIINTERACTION}-value": False,
        }
        response = self.client.post(reverse("ultaids:update", kwargs={"pk": ultaid.pk}), ultaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Hlab5801.objects.all())
        ultaid.refresh_from_db()
        self.assertIsNone(ultaid.hlab5801)

    def test__post_adds_False_hlab5801(self):
        """Test that a POST request creates and adds a Hlab5801 instance, with
        a value=False, as an attribute to the updated UltAid."""
        ultaid = UltAidFactory(hlab5801=None)
        self.assertFalse(Hlab5801.objects.all())
        self.assertIsNone(UltAid.objects.get().hlab5801)
        ultaid_data = {
            "dateofbirth-value": ultaid.dateofbirth.value,
            "gender-value": ultaid.gender.value,
            "ethnicity-value": ultaid.ethnicity.value,
            "hlab5801-value": False,
            f"{MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY}-value": False,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"{MedHistoryTypes.XOIINTERACTION}-value": False,
        }
        response = self.client.post(reverse("ultaids:update", kwargs={"pk": ultaid.pk}), ultaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        ultaid.refresh_from_db()
        self.assertTrue(Hlab5801.objects.all())
        hlab5801 = Hlab5801.objects.get()
        self.assertEqual(ultaid.hlab5801, hlab5801)
        self.assertFalse(hlab5801.value)

    def test__post_adds_True_hlab5801(self):
        """Test that a POST request creates and adds a Hlab5801 instance, with
        a value=True, as an attribute to the updated UltAid."""
        ultaid = UltAidFactory(hlab5801=None)
        self.assertFalse(Hlab5801.objects.all())
        self.assertIsNone(UltAid.objects.get().hlab5801)
        ultaid_data = {
            "dateofbirth-value": ultaid.dateofbirth.value,
            "gender-value": ultaid.gender.value,
            "ethnicity-value": ultaid.ethnicity.value,
            "hlab5801-value": True,
            f"{MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY}-value": False,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"{MedHistoryTypes.XOIINTERACTION}-value": False,
        }
        response = self.client.post(reverse("ultaids:update", kwargs={"pk": ultaid.pk}), ultaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        ultaid.refresh_from_db()
        self.assertTrue(Hlab5801.objects.all())
        hlab5801 = Hlab5801.objects.get()
        self.assertEqual(ultaid.hlab5801, hlab5801)
        self.assertTrue(hlab5801.value)

    def test__post_removes_updates_hlab5801_True_to_False(self):
        """Test that a POST request updates a Hlab5801 object / UltAid attribute
        from True to False."""
        ultaid = UltAidFactory(hlab5801=Hlab5801Factory(value=True))
        self.assertTrue(Hlab5801.objects.all())
        self.assertEqual(UltAid.objects.get().hlab5801, Hlab5801.objects.get())
        ultaid_data = {
            "dateofbirth-value": ultaid.dateofbirth.value,
            "gender-value": ultaid.gender.value,
            "ethnicity-value": ultaid.ethnicity.value,
            "hlab5801-value": False,
            f"{MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY}-value": False,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"{MedHistoryTypes.XOIINTERACTION}-value": False,
        }
        response = self.client.post(reverse("ultaids:update", kwargs={"pk": ultaid.pk}), ultaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Hlab5801.objects.all())
        hlab5801 = Hlab5801.objects.get()
        ultaid.refresh_from_db()
        self.assertEqual(ultaid.hlab5801, hlab5801)
        self.assertFalse(hlab5801.value)

    def test__post_removes_updates_hlab5801_False_to_True(self):
        """Test that a POST request updates a Hlab5801 object / UltAid attribute
        from False to True."""
        ultaid = UltAidFactory(hlab5801=Hlab5801Factory(value=False))
        self.assertTrue(Hlab5801.objects.all())
        self.assertEqual(UltAid.objects.get().hlab5801, Hlab5801.objects.get())
        ultaid_data = {
            "dateofbirth-value": ultaid.dateofbirth.value,
            "gender-value": ultaid.gender.value,
            "ethnicity-value": ultaid.ethnicity.value,
            "hlab5801-value": True,
            f"{MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY}-value": False,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"{MedHistoryTypes.XOIINTERACTION}-value": False,
        }
        response = self.client.post(reverse("ultaids:update", kwargs={"pk": ultaid.pk}), ultaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
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
        ultaid = UltAidFactory()
        self.assertFalse(ultaid.ckd)
        self.assertFalse(ultaid.ckddetail)
        ultaid_data = {
            "dateofbirth-value": ultaid.dateofbirth.value,
            "gender-value": ultaid.gender.value,
            "ethnicity-value": ultaid.ethnicity.value,
            "hlab5801-value": "",
            f"{MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY}-value": False,
            f"{MedHistoryTypes.CKD}-value": True,
            f"{MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"{MedHistoryTypes.XOIINTERACTION}-value": False,
        }
        response = self.client.post(reverse("ultaids:update", kwargs={"pk": ultaid.pk}), ultaid_data)
        self.assertEqual(response.status_code, 302)
        ultaid.refresh_from_db()
        delattr(ultaid, "ckd")
        delattr(ultaid, "ckddetail")
        self.assertTrue(ultaid.ckd)
        self.assertFalse(ultaid.ckddetail)
