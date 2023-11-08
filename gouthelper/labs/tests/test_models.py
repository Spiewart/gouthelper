from decimal import Decimal

import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...medhistorys.choices import MedHistoryTypes
from ..choices import Abnormalitys, LabTypes, Units
from ..helpers import eGFR_calculator, stage_calculator
from ..models import Lab
from .factories import BaselineCreatinineFactory, UrateFactory

pytestmark = pytest.mark.django_db


class TestCreatinineBase(TestCase):
    def test__eGFR_property_returns_eGFR_object(self):
        creatinine = BaselineCreatinineFactory()
        assert creatinine.eGFR == eGFR_calculator(creatinine)

    def test__stage_property_returns_stage_calculator(self):
        creatinine = BaselineCreatinineFactory()
        assert creatinine.stage == stage_calculator(creatinine.eGFR)


class TestLabBase(TestCase):
    def setUp(self):
        self.urate = UrateFactory(value=Decimal("5.0"))
        self.lab_list = [
            self.urate,
        ]

    def test__abnormality_returns_abnormality_or_None(self):
        for lab in self.lab_list:
            assert lab.abnormality is None or lab.abnormality in Abnormalitys.values
        assert self.urate.abnormality is None

    def test__high_returns_True_or_False(self):
        assert self.urate.high is False

    def test__low_returns_True_or_False(self):
        assert self.urate.low is False

    def test__units_returns_correct_labtype(self):
        self.assertEqual(self.urate.units, Units.MGDL)


class TestBaselineLab(TestCase):
    def setUp(self):
        self.baselinecreatinine = BaselineCreatinineFactory(value=Decimal("2.20"))

    def test__str__without_user(self):
        assert (
            self.baselinecreatinine.__str__()
            == f"Baseline {getattr(LabTypes, self.baselinecreatinine.labtype).label}: "
            + str(self.baselinecreatinine.value)
            + f" {getattr(Units, self.baselinecreatinine.units).label}"
        )


class TestLab(TestCase):
    def setUp(self):
        self.baselinecreatinine = BaselineCreatinineFactory(value=Decimal("3"))
        self.urate = UrateFactory(value=Decimal("10"))
        self.urate_lab = Lab.objects.filter(labtype=Lab.LabTypes.URATE).get()

    def test__str__returns_correct_method(self):
        self.assertEqual(self.urate_lab.__str__(), self.urate.__str__())
        self.assertEqual(
            self.baselinecreatinine.__str__(),
            f"Baseline {self.baselinecreatinine.labtype.label}: \
{(self.baselinecreatinine.value).quantize(Decimal('1.00'))} {self.baselinecreatinine.units.label}",
        )
        self.assertEqual(
            self.urate.__str__(),
            f"{self.urate.labtype.label}: {(self.urate.value).quantize(Decimal('1.0'))} {self.urate.units.label}",
        )

    def test__medhistorytypes_returns_correct_medhistorys(self):
        self.assertEqual(self.urate_lab.medhistorytypes(), [MedHistoryTypes.GOUT])
        self.assertEqual(self.urate.medhistorytypes(), [MedHistoryTypes.GOUT])

    def test__get_medhistorytypes_returns_correct_medhistorytype(self):
        self.assertEqual(self.urate.get_medhistorytype(), MedHistoryTypes.GOUT)
        self.assertEqual(self.urate_lab.get_medhistorytype(), MedHistoryTypes.GOUT)
