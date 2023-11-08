from datetime import timedelta

import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ..helpers.helpers import calculate_duration

pytestmark = pytest.mark.django_db


class TestCalcualteDuration(TestCase):
    def setUp(self):
        self.date_started = timezone.now().date() - timedelta(days=15)
        self.date_ended = timezone.now().date() - timedelta(days=7)

    def test__calculate_duration_no_date_ended(self):
        duration = calculate_duration(date_started=self.date_started, date_ended=None)
        self.assertEqual(
            duration,
            (timezone.now().date() - self.date_started),
        )

    def test__calculate_duration_with_date_ended(self):
        duration = calculate_duration(date_started=self.date_started, date_ended=self.date_ended)
        self.assertEqual(
            duration,
            (self.date_ended - self.date_started),
        )
