from datetime import timedelta
from decimal import Decimal

import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...genders.tests.factories import GenderFactory
from ...labs.tests.factories import BaselineCreatinineFactory
from ...medhistorydetails.choices import Stages
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ..choices import Statuses
from ..helpers import akis_aki_is_resolved_via_creatinines, akis_get_status_from_creatinines
from .factories import CreatinineFactory

pytestmark = pytest.mark.django_db


class TestAkiIsResolvedViaCreatinines(TestCase):
    def test__returns_True_via_baselinecreatinine(self):
        baselinecreatinine = BaselineCreatinineFactory(value=Decimal("2.0"))
        creatinine = CreatinineFactory(value=Decimal("2.0"))
        creatinine.baselinecreatinine = baselinecreatinine
        self.assertTrue(akis_aki_is_resolved_via_creatinines(creatinine))

    def test__returns_False_via_baselinecreatinine(self):
        baselinecreatinine = BaselineCreatinineFactory(value=Decimal("2.0"))
        creatinine = CreatinineFactory(value=Decimal("3.0"))
        creatinine.baselinecreatinine = baselinecreatinine
        self.assertFalse(akis_aki_is_resolved_via_creatinines(creatinine))

    def test__returns_True_via_stage(self):
        ckddetail = CkdDetailFactory(stage=Stages.THREE)
        dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 50))
        gender = GenderFactory(value=0)
        creatinine = CreatinineFactory(value=Decimal("2.0"))
        creatinine.dateofbirth = dateofbirth
        creatinine.gender = gender
        creatinine.ckddetail = ckddetail
        self.assertTrue(akis_aki_is_resolved_via_creatinines(creatinine))

    def test__returns_False_via_stage(self):
        ckddetail = CkdDetailFactory(stage=Stages.TWO)
        dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 50))
        gender = GenderFactory(value=0)
        creatinine = CreatinineFactory(value=Decimal("3.0"))
        creatinine.dateofbirth = dateofbirth
        creatinine.gender = gender
        creatinine.ckddetail = ckddetail
        self.assertFalse(akis_aki_is_resolved_via_creatinines(creatinine))

    def test__returns_True_via_normal_limits(self):
        creatinine = CreatinineFactory(value=Decimal("0.6"))
        self.assertTrue(akis_aki_is_resolved_via_creatinines(creatinine))

    def test__returns_False_via_normal_limits(self):
        creatinine = CreatinineFactory(value=Decimal("2.2"))
        self.assertFalse(akis_aki_is_resolved_via_creatinines(creatinine))


class TestGetStatusFromCreatinines(TestCase):
    def test__returns_resolved(self):
        ordered_creatinines = (
            CreatinineFactory(value=Decimal("1.0"), date_drawn=timezone.now() - timedelta(days=2)),
            CreatinineFactory(value=Decimal("1.5"), date_drawn=timezone.now() - timedelta(days=6)),
            CreatinineFactory(value=Decimal("2.0"), date_drawn=timezone.now() - timedelta(days=7)),
        )
        self.assertEqual(akis_get_status_from_creatinines(ordered_creatinines), Statuses.RESOLVED)

    def test__returns_improving(self):
        ordered_creatinines = (
            CreatinineFactory(value=Decimal("1.5"), date_drawn=timezone.now() - timedelta(days=6)),
            CreatinineFactory(value=Decimal("2.0"), date_drawn=timezone.now() - timedelta(days=7)),
        )
        self.assertEqual(akis_get_status_from_creatinines(ordered_creatinines), Statuses.IMPROVING)

    def test__returns_ongoing(self):
        ordered_creatinines = (CreatinineFactory(value=Decimal("1.5"), date_drawn=timezone.now() - timedelta(days=6)),)
        self.assertEqual(akis_get_status_from_creatinines(ordered_creatinines), Statuses.ONGOING)
