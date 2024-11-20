import pytest  # type: ignore
from django.forms.models import model_to_dict  # type: ignore
from django.test import TestCase  # type: ignore

from ...genders.choices import Genders
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ..choices import MedHistoryTypes
from .data_factories import create_ckd_api_data, create_medhistory_api_data
from .factories import MedHistoryFactory

pytestmark = pytest.mark.django_db


class TestCreateMedHistoryAPIData(TestCase):
    def setUp(self):
        self.medhistory = MedHistoryFactory(medhistorytype=MedHistoryTypes.CAD)

    def test__with_medhistory(self):
        data = create_medhistory_api_data(medhistory=self.medhistory)
        self.assertTrue(isinstance(data, dict))
        self.assertEqual(data["id"], self.medhistory.id)
        self.assertEqual(data["medhistorytype"], self.medhistory.medhistorytype)
        self.assertEqual(data["value"], True)
        self.assertEqual(data["user"], self.medhistory.user.id if self.medhistory.user else None)

    def test__with_medhistory_data(self):
        model_data = model_to_dict(self.medhistory)
        data = create_medhistory_api_data(
            medhistory=None,
            medhistorytype=MedHistoryTypes.CAD,
            value=False,
            user=model_data["user"],
        )
        self.assertTrue(isinstance(data, dict))
        self.assertEqual(data["id"], None)
        self.assertEqual(data["medhistorytype"], self.medhistory.medhistorytype)
        self.assertEqual(data["value"], False)
        self.assertEqual(data["user"], self.medhistory.user.id if self.medhistory.user else None)


class TestCreateCkdAPIData(TestCase):
    def setUp(self):
        self.ckd = MedHistoryFactory(medhistorytype=MedHistoryTypes.CKD)
        self.ckddetail = CkdDetailFactory(medhistory=self.ckd)

    def test__with_ckd(self):
        data = create_ckd_api_data(ckd=self.ckd)
        self.assertTrue(isinstance(data, dict))
        self.assertEqual(data["id"], self.ckd.id)
        self.assertEqual(data["value"], True)
        self.assertEqual(data["user"], self.ckd.user.id if self.ckd.user else None)
        self.assertEqual(data["ckddetail"]["id"], self.ckddetail.id)
        self.assertEqual(data["ckddetail"]["stage"], self.ckddetail.stage)
        self.assertEqual(data["ckddetail"]["dialysis"], self.ckddetail.dialysis)

    def test__without_ckd(self):
        data = create_ckd_api_data(
            ckd=None,
            value=True,
            stage=self.ckddetail.stage,
            dialysis=self.ckddetail.dialysis,
            dialysis_duration=self.ckddetail.dialysis_duration,
            dialysis_type=self.ckddetail.dialysis_type,
            age=50,
            gender=Genders.MALE,
            baselinecreatinine=None,
        )
        self.assertTrue(isinstance(data, dict))
        self.assertEqual(data["id"], None)
        self.assertEqual(data["value"], True)
        self.assertIsNone(data["user"])
        self.assertEqual(data["ckddetail"]["id"], None)
        self.assertEqual(data["ckddetail"]["stage"], self.ckddetail.stage)
        self.assertEqual(data["ckddetail"]["dialysis"], self.ckddetail.dialysis)
        self.assertEqual(data["ckddetail"]["dialysis_duration"], self.ckddetail.dialysis_duration)
        self.assertEqual(data["ckddetail"]["dialysis_type"], self.ckddetail.dialysis_type)

    def test__without_args(self):
        data = create_ckd_api_data()
        self.assertTrue(isinstance(data, dict))
        self.assertEqual(data["id"], None)
        self.assertEqual(data["value"], True)
        self.assertIsNone(data["user"])
