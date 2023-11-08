from datetime import timedelta

from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils import timezone  # type: ignore

from ...genders.choices import Genders
from ...medallergys.models import MedAllergy
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.models import MedHistory
from ...medhistorys.tests.factories import MedHistoryFactory
from ...treatments.choices import Treatments
from ..models import FlareAid
from ..views import FlareAidCreate, FlareAidUpdate
from .factories import FlareAidFactory


class TestFlareAidCreate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: FlareAidCreate = FlareAidCreate()

    def test__successful_post(self):
        flareaid_data = {
            "dateofbirth-value": (timezone.now() - timedelta(days=365 * 50)).date(),
            "dialysis": False,
            "gender-value": Genders.FEMALE,
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
        }
        response = self.client.post(reverse("flareaids:create"), flareaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertTrue(FlareAid.objects.get())
        self.assertEqual(response.status_code, 302)


class TestFlareAidUpdate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: FlareAidUpdate = FlareAidUpdate()

    def test__post_unchanged_medallergys(self):
        flareaid = FlareAidFactory()
        medallergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        flareaid.medallergys.add(medallergy)
        flareaid_data = {
            "dateofbirth-value": flareaid.dateofbirth.value,
            "gender-value": "",
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"medallergy_{Treatments.COLCHICINE}": True,
        }
        response = self.client.post(reverse("flareaids:update", kwargs={"pk": flareaid.pk}), flareaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MedAllergy.objects.filter(treatment=Treatments.COLCHICINE).exists())

    def test__post_add_medallergys(self):
        flareaid = FlareAidFactory()
        medallergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        flareaid.medallergys.add(medallergy)
        flareaid_data = {
            "dateofbirth-value": flareaid.dateofbirth.value,
            "gender-value": "",
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"medallergy_{Treatments.COLCHICINE}": True,
            f"medallergy_{Treatments.PREDNISONE}": True,
            f"medallergy_{Treatments.NAPROXEN}": True,
        }
        response = self.client.post(reverse("flareaids:update", kwargs={"pk": flareaid.pk}), flareaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MedAllergy.objects.filter(treatment=Treatments.PREDNISONE).exists())
        self.assertTrue(MedAllergy.objects.filter(treatment=Treatments.NAPROXEN).exists())
        self.assertEqual(MedAllergy.objects.count(), 3)

    def test__post_delete_medallergys(self):
        flareaid = FlareAidFactory()
        medallergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        flareaid.medallergys.add(medallergy)
        flareaid_data = {
            "dateofbirth-value": flareaid.dateofbirth.value,
            "gender-value": "",
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"medallergy_{Treatments.COLCHICINE}": "",
        }
        response = self.client.post(reverse("flareaids:update", kwargs={"pk": flareaid.pk}), flareaid_data)
        self.assertEqual(response.status_code, 302)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertFalse(MedAllergy.objects.filter(treatment=Treatments.COLCHICINE).exists())
        self.assertEqual(MedAllergy.objects.count(), 0)

    def test__post_unchanged_medhistorys(self):
        flareaid = FlareAidFactory()
        medhistory = MedHistoryFactory(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION)
        flareaid.medhistorys.add(medhistory)
        flareaid_data = {
            "dateofbirth-value": flareaid.dateofbirth.value,
            "gender-value": "",
            f"{MedHistoryTypes.CKD}-value": False,
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": True,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
        }
        response = self.client.post(reverse("flareaids:update", kwargs={"pk": flareaid.pk}), flareaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MedHistory.objects.filter(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION).exists())
        self.assertEqual(MedHistory.objects.count(), 1)

    def test__post_delete_medhistorys(self):
        flareaid = FlareAidFactory()
        medhistory = MedHistoryFactory(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION)
        flareaid.medhistorys.add(medhistory)
        flareaid_data = {
            "dateofbirth-value": flareaid.dateofbirth.value,
            "gender-value": "",
            f"{MedHistoryTypes.CKD}-value": False,
            # Need to mark Colchicineinteraction as False to delete it, required by form.
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": False,
            f"{MedHistoryTypes.DIABETES}-value": False,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
        }
        response = self.client.post(reverse("flareaids:update", kwargs={"pk": flareaid.pk}), flareaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(MedHistory.objects.filter(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION).exists())
        self.assertEqual(MedHistory.objects.count(), 0)

    def test__post_add_medhistorys(self):
        flareaid = FlareAidFactory()
        medhistory = MedHistoryFactory(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION)
        flareaid.medhistorys.add(medhistory)
        flareaid_data = {
            "dateofbirth-value": flareaid.dateofbirth.value,
            "gender-value": "",
            f"{MedHistoryTypes.CKD}-value": False,
            # Need to mark Colchicineinteraction as False to delete it, required by form.
            f"{MedHistoryTypes.COLCHICINEINTERACTION}-value": True,
            f"{MedHistoryTypes.DIABETES}-value": True,
            f"{MedHistoryTypes.ORGANTRANSPLANT}-value": False,
            f"{MedHistoryTypes.STROKE}-value": True,
        }
        response = self.client.post(reverse("flareaids:update", kwargs={"pk": flareaid.pk}), flareaid_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MedHistory.objects.filter(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION).exists())
        self.assertTrue(MedHistory.objects.filter(medhistorytype=MedHistoryTypes.DIABETES).exists())
        self.assertTrue(MedHistory.objects.filter(medhistorytype=MedHistoryTypes.STROKE).exists())
        self.assertEqual(MedHistory.objects.count(), 3)
