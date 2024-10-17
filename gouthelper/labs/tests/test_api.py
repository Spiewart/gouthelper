from decimal import Decimal

import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...akis.tests.factories import AkiFactory
from ...labs.models import Creatinine
from ...users.tests.factories import create_psp
from ...utils.test_helpers import date_days_ago
from ..api.mixins import CreatininesAPICreateMixin, CreatininesAPIUpdateMixin
from .factories import CreatinineFactory

pytestmark = pytest.mark.django_db


class TestCreatininesAPICreateMixin(TestCase):
    def setUp(self):
        self.api = CreatininesAPICreateMixin()
        self.creatinines_data = [
            {"value": Decimal("1.0"), "date_drawn": date_days_ago(1)},
            {"value": Decimal("2.0"), "date_drawn": date_days_ago(2)},
            {"value": Decimal("3.0"), "date_drawn": date_days_ago(3)},
        ]
        self.patient = create_psp()

    def test__create_creatinines(self):
        self.api.creatinines_data = self.creatinines_data
        self.api.patient = self.patient
        creatinines = self.api.create_creatinines()
        self.assertEqual(len(creatinines), 3)
        self.assertEqual(creatinines[0].value, Decimal("1.0"))
        self.assertEqual(creatinines[1].value, Decimal("2.0"))
        self.assertEqual(creatinines[2].value, Decimal("3.0"))
        for creatinine in creatinines:
            self.assertEqual(creatinine.user, self.patient)


class TestCreatininesAPIUpdateMixin(TestCase):
    def setUp(self):
        self.api = CreatininesAPIUpdateMixin()
        self.creatinines = [
            CreatinineFactory(value=Decimal("1.0"), date_drawn=date_days_ago(1)),
            CreatinineFactory(value=Decimal("2.0"), date_drawn=date_days_ago(2)),
            CreatinineFactory(value=Decimal("3.0"), date_drawn=date_days_ago(3)),
        ]
        self.creatinines_data = [
            {"value": Decimal("1.5"), "date_drawn": date_days_ago(3), "id": self.creatinines[0].id},
            {"value": Decimal("2.5"), "date_drawn": date_days_ago(4), "id": self.creatinines[1].id},
            {"value": Decimal("3.5"), "date_drawn": date_days_ago(5), "id": self.creatinines[2].id},
        ]
        self.api.creatinines = self.creatinines
        self.api.creatinines_data = self.creatinines_data
        self.patient = create_psp()
        self.api.patient = self.patient
        self.aki = AkiFactory()

    def test__update_creatinines(self):
        self.api.update_creatinines()
        self.assertEqual(self.api.creatinines[0].value, Decimal("1.5"))
        self.assertEqual(self.api.creatinines[1].value, Decimal("2.5"))
        self.assertEqual(self.api.creatinines[2].value, Decimal("3.5"))
        self.assertEqual(self.api.creatinines[0].date_drawn, date_days_ago(3))
        self.assertEqual(self.api.creatinines[1].date_drawn, date_days_ago(4))
        self.assertEqual(self.api.creatinines[2].date_drawn, date_days_ago(5))

    def test__update_creatinines_deletes_creatinines(self):
        self.api.creatinines_data = []
        self.api.update_creatinines()
        self.assertEqual(Creatinine.objects.count(), 0)

    def test__update_creatinines_creates_creatinines(self):
        self.api.creatinines_data = [
            {"value": Decimal("1.0"), "date_drawn": date_days_ago(1)},
            {"value": Decimal("2.0"), "date_drawn": date_days_ago(2)},
            {"value": Decimal("3.0"), "date_drawn": date_days_ago(3)},
        ]
        self.api.update_creatinines()
        self.assertEqual(Creatinine.objects.count(), 3)
        self.assertEqual(Creatinine.history.count(), 9)
