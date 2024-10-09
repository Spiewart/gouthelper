from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ...genders.choices import Genders
from ...labs.models import Creatinine
from ...labs.tests.factories import BaselineCreatinineFactory
from ...medhistorydetails.choices import Stages
from ..api.mixins import AkiAPIMixin
from ..choices import Statuses
from ..services import AkiProcessor
from .factories import CreatinineFactory

if TYPE_CHECKING:
    from ...labs.models import BaselineCreatinine

pytestmark = pytest.mark.django_db


def add_baselinecreatinine_to_creatinines(
    baselinecreatinine: "BaselineCreatinine",
    creatinines: list["Creatinine"],
) -> None:
    for creatinine in creatinines:
        creatinine.baselinecreatinine = baselinecreatinine


class TestAkiProcessor(TestCase):
    def setUp(self):
        self.creatinines = [
            CreatinineFactory(value=Decimal("1.0"), date_drawn=timezone.now() - timedelta(days=1)),
            CreatinineFactory(value=Decimal("2.0"), date_drawn=timezone.now() - timedelta(days=2)),
            CreatinineFactory(value=Decimal("3.0"), date_drawn=timezone.now() - timedelta(days=3)),
        ]
        self.baselinecreatinine = BaselineCreatinineFactory(value=Decimal("1.5"))

    def test__returns_creatinines_error_when_aki_is_false(self):
        processor = AkiProcessor(
            aki_value=False,
            status=Statuses.ONGOING,
            creatinines=self.creatinines,
            baselinecreatinine=self.baselinecreatinine,
        )
        errors = processor.get_errors()
        self.assertIn("creatinine", errors)

    def test__returns_status_and_creatinines_error_when_status_ongoing_creatinines_resolved(self):
        processor = AkiProcessor(
            aki_value=True,
            status=Statuses.ONGOING,
            creatinines=self.creatinines,
            baselinecreatinine=None,
        )
        errors = processor.get_errors()
        self.assertIn("aki", errors)
        self.assertIn("status", errors["aki"])
        self.assertIn("creatinine", errors)
        self.assertIn(None, errors["creatinine"])

    def test__returns_status_and_creatinines_error_when_status_resolved_creatinines_not(self):
        self.creatinines[0] = CreatinineFactory(value=Decimal(5.0))
        processor = AkiProcessor(
            aki_value=True,
            status=Statuses.RESOLVED,
            creatinines=self.creatinines,
            baselinecreatinine=None,
        )
        errors = processor.get_errors()
        self.assertIn("aki", errors)
        self.assertIn("status", errors["aki"])
        self.assertIn("creatinine", errors)
        self.assertIn(None, errors["creatinine"])

    def test__no_errors_when_resolved_and_creatinines_resolved(self):
        processor = AkiProcessor(
            aki_value=True,
            status=Statuses.RESOLVED,
            creatinines=self.creatinines,
            baselinecreatinine=None,
        )
        errors = processor.get_errors()
        self.assertFalse(errors)

    def test__no_errors_when_improving_and_creatinines_improving(self):
        self.creatinines[0] = CreatinineFactory(value=Decimal(2.0))
        add_baselinecreatinine_to_creatinines(
            self.baselinecreatinine,
            self.creatinines,
        )
        processor = AkiProcessor(
            aki_value=True,
            status=Statuses.IMPROVING,
            creatinines=self.creatinines,
            baselinecreatinine=self.baselinecreatinine,
        )
        errors = processor.get_errors()
        self.assertFalse(errors)

    # Write tests for rest of get_errors method

    def test__returns_status_and_creatinines_error_when_status_improving_creatinines_resolved(self):
        add_baselinecreatinine_to_creatinines(
            self.baselinecreatinine,
            self.creatinines,
        )
        processor = AkiProcessor(
            aki_value=True,
            status=Statuses.IMPROVING,
            creatinines=self.creatinines,
            baselinecreatinine=self.baselinecreatinine,
        )
        errors = processor.get_errors()
        self.assertIn("aki", errors)
        self.assertIn("status", errors["aki"])
        self.assertIn("creatinine", errors)
        self.assertIn(None, errors["creatinine"])


class TestAkiAPIMixin(TestCase):
    def setUp(self):
        self.api = AkiAPIMixin()
        self.creatinine1 = CreatinineFactory(value=Decimal("1.0"), date_drawn=timezone.now() - timedelta(days=1))
        self.creatinine2 = CreatinineFactory(value=Decimal("2.0"), date_drawn=timezone.now() - timedelta(days=2))
        self.creatinine3 = CreatinineFactory(value=Decimal("3.0"), date_drawn=timezone.now() - timedelta(days=3))
        self.creatinines = [self.creatinine1, self.creatinine2, self.creatinine3]
        self.baselinecreatinine = BaselineCreatinineFactory(value=Decimal("1.5"))

    def test__queryset_list(self):
        creat_qs = Creatinine.objects.all().order_by("-date_drawn")
        self.assertEqual(list(self.creatinines), list(creat_qs))

    def test__aki_is_resolved_via_creatinines_most_recent_creatinine_normal(self):
        self.api.aki__creatinines = self.creatinines
        self.assertTrue(self.api.aki_is_resolved_via_creatinines)

    def test__aki_is_resolved_via_creatinines_most_recent_creatinine_at_baseline(self):
        self.creatinine1 = CreatinineFactory(value=Decimal("1.5"), date_drawn=timezone.now() - timedelta(days=1))
        self.creatinines = [self.creatinine1, self.creatinine2, self.creatinine3]
        self.api.aki__creatinines = self.creatinines
        self.api.baselinecreatinine__value = Decimal("1.5")
        self.assertTrue(self.api.aki_is_resolved_via_creatinines)

    def test__aki_is_not_resolved_via_creatinines(self):
        self.creatinine1 = CreatinineFactory(value=Decimal("1.5"), date_drawn=timezone.now() - timedelta(days=1))
        self.creatinines = [self.creatinine1, self.creatinine2, self.creatinine3]
        self.api.aki__creatinines = self.creatinines
        self.api.baselinecreatinine__value = None
        self.api.ckddetail__stage = None
        self.assertFalse(self.api.aki_is_resolved_via_creatinines)

    def test__aki_is_improving_via_creatinines(self):
        self.api.aki__creatinines = self.creatinines
        self.assertTrue(self.api.aki_is_improving_via_creatinines)

    def tet__aki_is_improving_via_creatinines_with_stage(self):
        self.api.ckddetail__stage = Stages.THREE
        self.api.gender = Genders.MALE
        self.api.age = 40
        self.api.baselinecreatinine__value = None
        self.creatinine1 = CreatinineFactory(value=Decimal("2.0"), date_drawn=timezone.now() - timedelta(days=1))
        self.creatinines = [self.creatinine1, self.creatinine2, self.creatinine3]
        self.api.aki__creatinines = self.creatinines
        self.assertTrue(self.api.aki_is_improving_via_creatinines)

    def test__aki_is_not_improving_via_creatinines(self):
        self.creatinine1 = CreatinineFactory(value=Decimal("3.0"), date_drawn=timezone.now() - timedelta(days=1))
        self.creatinines = [self.creatinine1, self.creatinine2, self.creatinine3]
        self.api.aki__creatinines = self.creatinines
        self.assertFalse(self.api.aki_is_improving_via_creatinines)

    def test__aki_is_not_improving_via_creatinines_with_stage(self):
        self.api.ckddetail__stage = Stages.THREE
        self.api.gender = Genders.MALE
        self.api.age = 40
        self.api.baselinecreatinine__value = None
        self.creatinine1 = CreatinineFactory(value=Decimal("2.8"), date_drawn=timezone.now() - timedelta(days=1))
        self.creatinines = [self.creatinine1, self.creatinine2, self.creatinine3]
        self.api.aki__creatinines = self.creatinines
        self.assertFalse(self.api.aki_is_improving_via_creatinines)

    def test__order_aki__creatinines_by_date_drawn_desc(self):
        self.api.aki__creatinines = [self.creatinine2, self.creatinine1, self.creatinine3]
        self.api.order_aki__creatinines_by_date_drawn_desc()
        self.assertEqual(self.api.aki__creatinines, [self.creatinine1, self.creatinine2, self.creatinine3])

    def test__order_aki__creatinines_by_date_drawn_desc_with_dicts(self):
        self.creatinines = [self.creatinine2, self.creatinine1, self.creatinine3]
        creatinines_dicts = [
            {"id": creatinine.id, "value": creatinine.value, "date_drawn": creatinine.date_drawn}
            for creatinine in self.creatinines
        ]
        self.api.aki__creatinines = creatinines_dicts
        self.api.order_aki__creatinines_by_date_drawn_desc()
        self.assertEqual(self.api.aki__creatinines[0]["id"], self.creatinine1.id)
        self.assertEqual(self.api.aki__creatinines[1]["id"], self.creatinine2.id)
        self.assertEqual(self.api.aki__creatinines[2]["id"], self.creatinine3.id)
