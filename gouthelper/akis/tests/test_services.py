from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ...labs.tests.factories import BaselineCreatinineFactory
from ..choices import Statuses
from ..services import AkiProcessor
from .factories import CreatinineFactory

if TYPE_CHECKING:
    from ...labs.models import BaselineCreatinine, Creatinine

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
        print([c.date_drawn for c in self.creatinines])
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
