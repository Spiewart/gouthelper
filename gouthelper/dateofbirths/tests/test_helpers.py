from datetime import datetime, timedelta

import pytest  # type: ignore
from dateutil import parser
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ...defaults.selectors import defaults_flareaidsettings, defaults_ppxaidsettings
from ..helpers import age_calc, dateofbirths_get_nsaid_contra, yearsago
from .factories import DateOfBirthFactory

pytestmark = pytest.mark.django_db


class TestAgeCalc(TestCase):
    def test__age_calc(self):
        self.assertEqual(age_calc(DateOfBirthFactory(value=timezone.now() - timedelta(days=21 * 365.25)).value), 21)


class TestDateOfBirthsGetNsaidContra(TestCase):
    def setUp(self):
        # Declare attrs for *args for dateofbirths_get_nsaid_contra
        self.dateofbirth = DateOfBirthFactory()
        self.flare_trt_settings = defaults_flareaidsettings(user=None)
        self.ppx_trt_settings = defaults_ppxaidsettings(user=None)

    def test__nsaid_age_False_returns_False_over_65_flaretrtsettings(self):
        self.dateofbirth.value = timezone.now() - timedelta(days=66 * 365)
        self.dateofbirth.save()
        self.assertFalse(dateofbirths_get_nsaid_contra(self.dateofbirth, self.flare_trt_settings))

    def test__nsaid_age_True_returns_False_over_65_flaretrtsettings(self):
        self.flare_trt_settings.nsaid_age = False
        self.flare_trt_settings.save()
        self.dateofbirth.value = timezone.now() - timedelta(days=66 * 365)
        self.dateofbirth.save()
        self.assertTrue(dateofbirths_get_nsaid_contra(self.dateofbirth, self.flare_trt_settings))

    def test__nsaid_age_True_returns_False_under_65_flaretrtsettings(self):
        self.flare_trt_settings.nsaid_age = False
        self.flare_trt_settings.save()
        self.dateofbirth.value = timezone.now() - timedelta(days=50 * 365)
        self.dateofbirth.save()
        self.assertFalse(dateofbirths_get_nsaid_contra(self.dateofbirth, self.flare_trt_settings))

    def test__returns_None_no_dateofbirth_flaretrtsettings(self):
        self.assertIsNone(dateofbirths_get_nsaid_contra(None, self.flare_trt_settings))

    def test__nsaid_age_False_returns_False_over_65_ppxtrtsettings(self):
        self.dateofbirth.value = timezone.now() - timedelta(days=66 * 365)
        self.dateofbirth.save()
        self.assertFalse(dateofbirths_get_nsaid_contra(self.dateofbirth, self.ppx_trt_settings))

    def test__nsaid_age_True_returns_False_over_65_ppxtrtsettings(self):
        self.ppx_trt_settings.nsaid_age = False
        self.ppx_trt_settings.save()
        self.dateofbirth.value = timezone.now() - timedelta(days=66 * 365)
        self.dateofbirth.save()
        self.assertTrue(dateofbirths_get_nsaid_contra(self.dateofbirth, self.ppx_trt_settings))

    def test__nsaid_age_True_returns_False_under_65_ppxtrtsettings(self):
        self.ppx_trt_settings.nsaid_age = False
        self.ppx_trt_settings.save()
        self.dateofbirth.value = timezone.now() - timedelta(days=50 * 365)
        self.dateofbirth.save()
        self.assertFalse(dateofbirths_get_nsaid_contra(self.dateofbirth, self.ppx_trt_settings))

    def test__returns_None_no_dateofbirth_ppxtrtsettings(self):
        self.assertIsNone(dateofbirths_get_nsaid_contra(None, self.ppx_trt_settings))


class TestYearsAgo(TestCase):
    def test__yearsago(self):
        now = timezone.now()
        day = now.day
        month = now.month
        self.assertEqual(
            yearsago(21, now).date(),
            parser.parse(f"{now.year - 21}-{month}-{day}").date(),
        )

    def test__leap_year(self):
        now = "2020-02-29"
        self.assertEqual(
            yearsago(1, datetime.strptime(now, "%Y-%m-%d")).date(),
            parser.parse("2019-02-28").date(),
        )
