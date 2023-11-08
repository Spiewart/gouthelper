from datetime import timedelta

import pytest  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils import timezone  # type: ignore

from ...ethnicitys.choices import Ethnicitys
from ...genders.choices import Genders
from ...labs.models import Hlab5801
from ...labs.tests.factories import Hlab5801Factory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.models import Xoiinteraction
from ...treatments.choices import Treatments
from ..models import UltAid
from ..views import UltAidCreate, UltAidUpdate
from .factories import UltAidFactory

pytestmark = pytest.mark.django_db


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
