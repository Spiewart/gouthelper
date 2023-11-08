from datetime import timedelta
from decimal import Decimal

import pytest  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils import timezone  # type: ignore

from ...dateofbirths.models import DateOfBirth
from ...genders.choices import Genders
from ...genders.models import Gender
from ...labs.models import BaselineCreatinine
from ...medhistorydetails.choices import Stages
from ...medhistorydetails.models import CkdDetail
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.models import Ckd, Erosions, Hyperuricemia, Tophi, Uratestones
from ..choices import FlareFreqs, FlareNums
from ..models import Ult
from ..views import UltCreate, UltUpdate
from .factories import UltFactory

pytestmark = pytest.mark.django_db


class TestUltCreate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltCreate = UltCreate()

    def test__get_context_data(self):
        request = self.factory.get("ults/create")
        response = UltCreate.as_view()(request)
        self.assertIn("dateofbirth_form", response.context_data)
        self.assertIn("gender_form", response.context_data)
        self.assertIn(f"{MedHistoryTypes.CKD}_form", response.context_data)
        self.assertIn("ckddetail_form", response.context_data)
        self.assertIn("baselinecreatinine_form", response.context_data)
        self.assertIn(f"{MedHistoryTypes.EROSIONS}_form", response.context_data)
        self.assertIn(f"{MedHistoryTypes.HYPERURICEMIA}_form", response.context_data)
        self.assertIn(f"{MedHistoryTypes.TOPHI}_form", response.context_data)
        self.assertIn(f"{MedHistoryTypes.URATESTONES}_form", response.context_data)

    def test__post_creates_ult_and_related_objects(self):
        ult_data = {
            "num_flares": FlareNums.ONE,
            "dateofbirth-value": (timezone.now() - timedelta(days=365 * 50)).date(),
            "gender-value": Genders.FEMALE,
            f"{MedHistoryTypes.CKD}-value": True,
            "baselinecreatinine-value": Decimal("2.0"),
            "dialysis": False,
            "stage": Stages.THREE,
            f"{MedHistoryTypes.EROSIONS}-value": True,
            f"{MedHistoryTypes.HYPERURICEMIA}-value": True,
            f"{MedHistoryTypes.TOPHI}-value": True,
            f"{MedHistoryTypes.URATESTONES}-value": True,
        }
        response = self.client.post(reverse("ults:create"), ult_data)
        # NOTE: Will print errors for all forms in the context_data.
        # for key, val in response.context_data.items():
        # if key.endswith("_form") or key == "form":
        # print(key, val.errors)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Ult.objects.all().exists())
        ult = Ult.objects.first()
        self.assertEqual(ult.num_flares, FlareNums.ONE)
        self.assertTrue(DateOfBirth.objects.all().exists())
        self.assertEqual(ult.dateofbirth, DateOfBirth.objects.first())
        self.assertTrue(Gender.objects.all().exists())
        self.assertEqual(ult.gender, Gender.objects.last())
        self.assertTrue(Ckd.objects.all().exists())
        ckd = Ckd.objects.first()
        self.assertIn(ckd, ult.medhistorys.all())
        self.assertTrue(CkdDetail.objects.all().exists())
        self.assertTrue(BaselineCreatinine.objects.all().exists())
        baselinecreatinine = BaselineCreatinine.objects.first()
        ckddetail = CkdDetail.objects.first()
        self.assertEqual(ckddetail.medhistory, ckd)
        self.assertEqual(ckddetail.stage, Stages.THREE)
        self.assertEqual(baselinecreatinine.value, Decimal("2.0"))
        self.assertEqual(baselinecreatinine.medhistory, ckd)
        self.assertTrue(Erosions.objects.all().exists())
        self.assertIn(Erosions.objects.first(), ult.medhistorys.all())
        self.assertTrue(Hyperuricemia.objects.all().exists())
        self.assertIn(Hyperuricemia.objects.first(), ult.medhistorys.all())
        self.assertTrue(Tophi.objects.all().exists())
        self.assertIn(Tophi.objects.first(), ult.medhistorys.all())
        self.assertTrue(Uratestones.objects.all().exists())
        self.assertIn(Uratestones.objects.first(), ult.medhistorys.all())

    def test__post_uses_assigned_queryset(self):
        ult_data = {
            "num_flares": FlareNums.ONE,
            "dateofbirth-value": (timezone.now() - timedelta(days=365 * 50)).date(),
            "gender-value": Genders.FEMALE,
            f"{MedHistoryTypes.CKD}-value": True,
            "baselinecreatinine-value": Decimal("2.0"),
            "dialysis": False,
            "stage": Stages.THREE,
            f"{MedHistoryTypes.EROSIONS}-value": True,
            f"{MedHistoryTypes.HYPERURICEMIA}-value": True,
            f"{MedHistoryTypes.TOPHI}-value": True,
            f"{MedHistoryTypes.URATESTONES}-value": True,
        }
        with self.assertNumQueries(46):
            self.client.post(reverse("ults:create"), ult_data)


class TestUltUpdate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: UltUpdate = UltUpdate()

    def test__post_uses_assigned_queryset(self):
        ult = UltFactory(num_flares=FlareNums.TWOPLUS, freq_flares=FlareFreqs.ONEORLESS)
        ult_data = {
            "num_flares": FlareNums.TWOPLUS,
            "freq_flares": FlareFreqs.ONEORLESS,
            "dateofbirth-value": (timezone.now() - timedelta(days=365 * 50)).date(),
            "gender-value": Genders.FEMALE,
            f"{MedHistoryTypes.CKD}-value": True,
            "baselinecreatinine-value": Decimal("2.0"),
            "dialysis": False,
            "stage": Stages.THREE,
            f"{MedHistoryTypes.EROSIONS}-value": True,
            f"{MedHistoryTypes.HYPERURICEMIA}-value": True,
            f"{MedHistoryTypes.TOPHI}-value": True,
            f"{MedHistoryTypes.URATESTONES}-value": True,
        }
        with self.assertNumQueries(48):
            self.client.post(reverse("ults:update", kwargs={"pk": ult.pk}), ult_data)
