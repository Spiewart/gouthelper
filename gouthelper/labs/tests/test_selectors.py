from datetime import timedelta

import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ...flares.tests.factories import FlareFactory
from ..selectors import urate_userless_qs
from .factories import UrateFactory

pytestmark = pytest.mark.django_db


class TestUrateUserlessQuerySet(TestCase):
    def setUp(self):
        self.urate1 = UrateFactory(value=5.0, date_drawn=timezone.now())
        self.urate2 = UrateFactory(value=6.0, date_drawn=timezone.now() - timedelta(days=23))
        self.urate3 = UrateFactory(value=7.0, date_drawn=timezone.now() - timedelta(days=190))
        self.urate4 = UrateFactory(value=8.0, date_drawn=timezone.now() - timedelta(days=365))
        self.flare = FlareFactory(date_started=timezone.now() - timedelta(days=150), urate=UrateFactory(value=15.0))
        self.urate5 = self.flare.urate

    def test__all_urates_fetched(self):
        qs = urate_userless_qs().all()
        self.assertEqual(qs.count(), 5)

    def test__urates_in_order_by_reverse_date(self):
        qs = urate_userless_qs().all()
        self.assertEqual(qs[0], self.urate1)
        self.assertEqual(qs[1], self.urate2)
        self.assertEqual(qs[2], self.urate5)
        self.assertEqual(qs[3], self.urate3)
        self.assertEqual(qs[4], self.urate4)

    def test__urates_annotated_with_date(self):
        qs = urate_userless_qs().all()
        for urate in qs:
            self.assertTrue(hasattr(urate, "date"))
            self.assertTrue(urate.date)
        # assert that the date is the date_drawn if it exists, otherwise is the Flare.date_started
        self.assertEqual(qs[0].date, self.urate1.date_drawn)
        self.assertEqual(qs[1].date, self.urate2.date_drawn)
        self.assertEqual(qs[2].date.date(), self.urate5.flare.date_started.date())
        self.assertEqual(qs[3].date, self.urate3.date_drawn)
        self.assertEqual(qs[4].date, self.urate4.date_drawn)
