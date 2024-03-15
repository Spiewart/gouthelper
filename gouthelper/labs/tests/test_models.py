from decimal import Decimal

import pytest  # type: ignore
from django.db.utils import IntegrityError  # type: ignore
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ..choices import Abnormalitys, Units
from ..helpers import labs_eGFR_calculator, labs_stage_calculator
from ..models import Urate
from .factories import BaselineCreatinineFactory, Hlab5801Factory, UrateFactory

pytestmark = pytest.mark.django_db


class TestCreatinineBase(TestCase):
    def test__eGFR_property_returns_eGFR_object(self):
        creatinine = BaselineCreatinineFactory()
        assert creatinine.eGFR == labs_eGFR_calculator(creatinine)

    def test__stage_property_returns_labs_stage_calculator(self):
        creatinine = BaselineCreatinineFactory()
        assert creatinine.stage == labs_stage_calculator(creatinine.eGFR)


class TestLabBase(TestCase):
    def setUp(self):
        self.baselinecreatinine = BaselineCreatinineFactory(value=Decimal("2.20"))
        self.urate = UrateFactory(value=Decimal("5.0"))
        self.lab_list = [
            self.baselinecreatinine,
            self.urate,
        ]

    def test__baselinecreatinine_constraint_units_upper_lower_limits_valid(self):
        baselinecreatinine = BaselineCreatinineFactory()
        baselinecreatinine.lower_limit = Decimal("16.0")
        with self.assertRaises(IntegrityError) as context:
            baselinecreatinine.save()
        self.assertTrue("units_upper_lower_limits_valid" in str(context.exception))

    def test__urate_constraint_units_upper_lower_limits_valid(self):
        urate = UrateFactory()
        urate.lower_limit = Decimal("16.0")
        with self.assertRaises(IntegrityError) as context:
            urate.save()
        self.assertTrue("units_upper_lower_limits_valid" in str(context.exception))

    def test__abnormality_returns_abnormality_or_None(self):
        for lab in self.lab_list:
            assert lab.abnormality is None or lab.abnormality in Abnormalitys.values
        assert self.baselinecreatinine.abnormality is Abnormalitys.HIGH
        assert self.urate.abnormality is None

    def test__high_returns_True_or_False(self):
        assert self.baselinecreatinine.high is True
        assert self.urate.high is False

    def test__low_returns_True_or_False(self):
        assert self.baselinecreatinine.low is False
        assert self.urate.low is False

    def test__units_returns_correct_labtype(self):
        self.assertEqual(self.urate.units, Units.MGDL)


class TestBaselineLab(TestCase):
    def setUp(self):
        self.baselinecreatinine = BaselineCreatinineFactory(value=Decimal("2.20"))

    def test__str__without_user(self):
        assert (
            self.baselinecreatinine.__str__()
            == "Baseline Creatinine: "
            + str(self.baselinecreatinine.value)
            + f" {getattr(Units, self.baselinecreatinine.units).label}"
        )


class TestLab(TestCase):
    def setUp(self):
        self.baselinecreatinine = BaselineCreatinineFactory(value=Decimal("3"))
        self.urate = UrateFactory(value=Decimal("10"))
        self.urate_lab = Urate.objects.get()

    def test__date_drawn_not_in_future_constraint(self):
        urate = UrateFactory()
        urate.date_drawn = timezone.now() + timezone.timedelta(days=100)
        with self.assertRaises(IntegrityError) as context:
            urate.save()
        self.assertTrue("date_drawn_not_in_future" in str(context.exception))

    def test__delete_creates_lab_history(self):
        self.assertTrue(Urate.history.exists())
        self.assertEqual(Urate.history.count(), 1)
        self.urate.delete()
        self.assertEqual(Urate.history.count(), 2)

    def test__save_creates_lab_history(self):
        self.assertEqual(Urate.history.count(), 1)
        self.urate.save()
        self.assertEqual(Urate.history.count(), 2)

    def test__str__(self):
        self.assertEqual(
            self.urate.__str__(),
            f"Urate: {(self.urate.value).quantize(Decimal('1.0'))} {self.urate.units.label}",
        )

    def test__str__parent_returns_correct_method(self):
        self.assertEqual(self.urate_lab.__str__(), self.urate.__str__())
        self.assertEqual(
            self.baselinecreatinine.__str__(),
            f"Baseline Creatinine: \
{(self.baselinecreatinine.value).quantize(Decimal('1.00'))} {self.baselinecreatinine.units.label}",
        )
        self.assertEqual(
            self.urate.__str__(),
            f"Urate: {(self.urate.value).quantize(Decimal('1.0'))} {self.urate.units.label}",
        )

    def test__var_x_high(self):
        self.assertFalse(self.urate.var_x_high(Decimal("10.0")))
        self.assertTrue(self.urate.var_x_high(Decimal("3.0"), Decimal("1.0")))

    def test__var_x_low(self):
        self.assertFalse(self.urate.var_x_low(Decimal("0.75")))
        self.assertTrue(self.urate.var_x_low(Decimal("0.3"), Decimal("50")))


class TestBaselineCreatinine(TestCase):
    def setUp(self):
        self.baselinecreatinine = BaselineCreatinineFactory(value=Decimal("2.20"))

    def test__value_str(self):
        self.assertEqual(
            self.baselinecreatinine.value_str,
            f"{(self.baselinecreatinine.value).quantize(Decimal('1.00'))} {self.baselinecreatinine.units.label}",
        )

    def test___str__(self):
        self.assertEqual(
            self.baselinecreatinine.__str__(),
            f"Baseline Creatinine: \
{(self.baselinecreatinine.value).quantize(Decimal('1.00'))} {self.baselinecreatinine.units.label}",
        )


class TestUrate(TestCase):
    def setUp(self):
        self.urate = UrateFactory(value=Decimal("5.0"))

    def test__value_str(self):
        self.assertEqual(
            self.urate.value_str,
            f"{(self.urate.value).quantize(Decimal('1.0'))} {self.urate.units.label}",
        )

    def test__str__(self):
        self.assertEqual(
            self.urate.__str__(),
            f"Urate: {(self.urate.value).quantize(Decimal('1.0'))} {self.urate.units.label}",
        )


class TestHlab5801(TestCase):
    def setUp(self):
        self.hlab5801 = Hlab5801Factory()

    def test__date_drawn_not_in_future_constraint(self):
        self.hlab5801.date_drawn = timezone.now() + timezone.timedelta(days=100)
        with self.assertRaises(IntegrityError) as context:
            self.hlab5801.save()
        self.assertTrue("date_drawn_not_in_future" in str(context.exception))
