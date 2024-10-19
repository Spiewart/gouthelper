from datetime import timedelta
from decimal import Decimal

import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ...flares.tests.factories import create_flare
from ...ppxs.tests.factories import create_ppx
from ...users.tests.factories import create_psp
from ..models import Urate
from ..selectors import dated_urates, urates_dated_qs, urates_related_objects_qs
from .factories import UrateFactory

pytestmark = pytest.mark.django_db


class TestUrateUserlessQuerySet(TestCase):
    def setUp(self):
        self.urate1 = UrateFactory(value=Decimal(5.0), date_drawn=timezone.now())
        self.urate2 = UrateFactory(value=Decimal(6.0), date_drawn=timezone.now() - timedelta(days=23))
        self.urate3 = UrateFactory(value=Decimal(7.0), date_drawn=timezone.now() - timedelta(days=190))
        self.urate4 = UrateFactory(value=Decimal(8.0), date_drawn=timezone.now() - timedelta(days=365))
        self.flare = create_flare(
            date_started=(timezone.now() - timedelta(days=150)).date(), urate=UrateFactory(value=15.0)
        )
        self.urate5 = self.flare.urate

    def test__all_urates_fetched(self):
        qs = urates_dated_qs().all()
        self.assertEqual(qs.count(), 5)

    def test__urates_in_order_by_reverse_date(self):
        qs = urates_dated_qs().all()
        self.assertEqual(qs[0], self.urate1)
        self.assertEqual(qs[1], self.urate2)
        self.assertEqual(qs[2], self.urate5)
        self.assertEqual(qs[3], self.urate3)
        self.assertEqual(qs[4], self.urate4)

    def test__urates_annotated_with_date(self):
        qs = urates_dated_qs().all()
        for urate in qs:
            self.assertTrue(hasattr(urate, "date"))
            self.assertTrue(urate.date)
        # assert that the date is the date_drawn if it exists, otherwise is the Flare.date_started
        self.assertEqual(qs[0].date, self.urate1.date_drawn)
        self.assertEqual(qs[1].date, self.urate2.date_drawn)
        self.assertEqual(qs[2].date.date(), self.urate5.flare.date_started)
        self.assertEqual(qs[3].date, self.urate3.date_drawn)
        self.assertEqual(qs[4].date, self.urate4.date_drawn)


class TestDatedUrates(TestCase):
    def test__no_flares(self):
        # Create a few urates
        UrateFactory(value=Decimal(5.0), date_drawn=timezone.now())
        UrateFactory(value=Decimal(6.0), date_drawn=timezone.now() - timedelta(days=23))
        UrateFactory(value=Decimal(7.0), date_drawn=timezone.now() - timedelta(days=190))
        # Test that the queryset is annotated with date_drawns
        qs = Urate.objects.all()
        qs = dated_urates(qs)
        for urate in qs:
            self.assertTrue(hasattr(urate, "date"))
            self.assertEqual(urate.date, urate.date_drawn)

    def test__no_date_drawns(self):
        # Create a few urates without date_drawns
        urate1 = UrateFactory(value=Decimal(5.0))
        urate2 = UrateFactory(value=Decimal(6.0))
        urate3 = UrateFactory(value=Decimal(7.0))
        # Create a few flares and assign urates to the flares urate attr
        create_flare(date_started=(timezone.now() - timedelta(days=150)).date(), urate=urate1)
        create_flare(date_started=(timezone.now() - timedelta(days=23)).date(), urate=urate2)
        create_flare(date_started=(timezone.now() - timedelta(days=190)).date(), urate=urate3)
        # Test that the queryset is annotated with flare.date_started
        qs = Urate.objects.all()
        qs = dated_urates(qs)
        for urate in qs:
            self.assertTrue(hasattr(urate, "date"))
            self.assertEqual(urate.date.date(), urate.flare.date_started)

    def test__date_drawns_and_flares(self):
        # Create a few urates without date_drawns
        urate1 = UrateFactory(value=Decimal(5.0), date_drawn=timezone.now() - timedelta(days=151))
        urate2 = UrateFactory(value=Decimal(6.0), date_drawn=timezone.now() - timedelta(days=22))
        urate3 = UrateFactory(value=Decimal(7.0))
        # Create a few flares and assign urates to the flares urate attr
        create_flare(date_started=timezone.now() - timedelta(days=150), urate=urate1)
        create_flare(date_started=timezone.now() - timedelta(days=23), urate=urate2)
        create_flare(date_started=timezone.now() - timedelta(days=190), urate=urate3)
        # Test that the queryset is annotated with flare.date_started
        # and that flare.date_started takes precedence over urate.date_drawn
        qs = Urate.objects.all()
        qs = dated_urates(qs)
        for urate in qs:
            self.assertTrue(hasattr(urate, "date"))
            if urate.flare:
                self.assertEqual(urate.date.date(), urate.flare.date_started)
            else:
                self.assertEqual(urate.date.date(), urate.date_drawn)

    def test__urates_limited_to_last_2_years(self):
        # Create some urates, including some older than 2 years
        UrateFactory(value=Decimal(5.0), date_drawn=timezone.now())
        UrateFactory(value=Decimal(6.0), date_drawn=timezone.now() - timedelta(days=23))
        UrateFactory(value=Decimal(7.0), date_drawn=timezone.now() - timedelta(days=190))
        old_urate = UrateFactory(value=8.0, date_drawn=timezone.now() - timedelta(days=765))
        # Test that the queryset excludes urates older than 2 years
        qs = Urate.objects.all()
        qs = dated_urates(qs)
        self.assertEqual(qs.count(), 3)
        self.assertNotIn(old_urate, qs)


# write tests for urates_related_objects_qs
class TestUratesRelatedObjectsQS(TestCase):
    def setUp(self):
        self.urate = UrateFactory()
        self.urate_with_flare = UrateFactory()
        create_flare(date_started=timezone.now() - timedelta(days=150), urate=self.urate_with_flare)
        self.urate_with_ppx = UrateFactory()
        create_ppx(labs=[self.urate_with_ppx])
        self.patient = create_psp()

    def test__urates_related_objects_qs(self):
        with self.assertNumQueries(1):
            accurate_qs = urates_related_objects_qs(Urate.objects.filter(id=self.urate.id)).get()
            self.assertEqual(accurate_qs, self.urate)

        with self.assertNumQueries(1):
            accurate_qs = urates_related_objects_qs(Urate.objects.filter(id=self.urate_with_flare.id)).get()
            self.assertEqual(accurate_qs, self.urate_with_flare)
            self.assertEqual(accurate_qs.flare, self.urate_with_flare.flare)

        with self.assertNumQueries(1):
            accurate_qs = urates_related_objects_qs(Urate.objects.filter(id=self.urate_with_ppx.id)).get()
            self.assertEqual(accurate_qs, self.urate_with_ppx)
            self.assertEqual(accurate_qs.ppx, self.urate_with_ppx.ppx)
