from datetime import timedelta
from decimal import Decimal

import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...genders.choices import Genders
from ...genders.tests.factories import GenderFactory
from ...labs.tests.factories import (
    BaselineCreatinineFactory,
    create_baselinecreatinine_api_data,
    create_creatinine_api_data,
)
from ...medhistorydetails.choices import Stages
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ..choices import Statuses
from ..helpers import (
    AkiStatusCreatininesProcessor,
    akis_aki_is_resolved_via_creatinines,
    akis_get_status_from_creatinines,
)
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


class TestAkiStatusCreatininesProcessor(TestCase):
    def setUp(self):
        self.creatinine1 = create_creatinine_api_data(
            value=Decimal("1.0"), date_drawn=timezone.now() - timedelta(days=1)
        )
        self.creatinine2 = create_creatinine_api_data(
            value=Decimal("2.0"), date_drawn=timezone.now() - timedelta(days=2)
        )
        self.creatinine3 = create_creatinine_api_data(
            value=Decimal("3.0"), date_drawn=timezone.now() - timedelta(days=3)
        )
        self.creatinines = [self.creatinine1, self.creatinine2, self.creatinine3]
        self.baselinecreatinine = create_baselinecreatinine_api_data(value=Decimal("1.5"))
        self.stage = Stages.THREE
        self.gender = Genders.MALE
        self.age = 40

    def test__aki_is_resolved_via_creatinines_most_recent_creatinine_normal(self):
        self.assertTrue(
            AkiStatusCreatininesProcessor(
                status=Statuses.RESOLVED,
                creatinines=self.creatinines,
            ).aki_is_resolved_via_creatinines
        )

    def test__aki_is_resolved_via_creatinines_most_recent_creatinine_at_baseline(self):
        self.assertTrue(
            AkiStatusCreatininesProcessor(
                status=Statuses.RESOLVED,
                creatinines=self.creatinines,
                baselinecreatinine=self.baselinecreatinine,
            ).aki_is_resolved_via_creatinines
        )

    def test__aki_is_not_resolved_via_creatinines(self):
        self.creatinine1.update({"value": Decimal("1.5")})
        self.assertFalse(
            AkiStatusCreatininesProcessor(
                status=Statuses.RESOLVED,
                creatinines=self.creatinines,
            ).aki_is_resolved_via_creatinines
        )

    def test__aki_is_improving_via_creatinines(self):
        class_method = AkiStatusCreatininesProcessor(
            status=None,
            creatinines=self.creatinines,
        )
        self.assertTrue(class_method.aki_is_improving_via_creatinines)

    def tet__aki_is_improving_via_creatinines_with_stage(self):
        self.creatinine1.update({"value": Decimal("2.0")})
        class_method = AkiStatusCreatininesProcessor(
            status=None,
            creatinines=self.creatinines,
            stage=self.stage,
        )
        self.assertTrue(class_method.aki_is_improving_via_creatinines)

    def test__aki_is_not_improving_via_creatinines(self):
        self.creatinine1.update({"value": Decimal("3.0")})
        class_method = AkiStatusCreatininesProcessor(
            status=None,
            creatinines=self.creatinines,
        )
        self.assertFalse(class_method.aki_is_improving_via_creatinines)

    def test__aki_is_not_improving_via_creatinines_with_stage(self):
        self.creatinine1.update({"value": Decimal("2.8")})
        class_method = AkiStatusCreatininesProcessor(
            status=None,
            creatinines=self.creatinines,
            stage=self.stage,
        )
        self.assertFalse(class_method.aki_is_improving_via_creatinines)


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
