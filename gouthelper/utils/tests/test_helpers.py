from datetime import timedelta

import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ...users.tests.factories import UserFactory, create_psp
from ..helpers import calculate_duration, get_str_attrs

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


class TestCreateStrAttrs(TestCase):
    def setUp(self):
        self.psp = create_psp()
        self.user = UserFactory()
        self.str_attr_keys = [
            "query",
            "tobe",
            "tobe_past",
            "tobe_neg",
            "pos",
            "pos_past",
            "pos_neg",
            "pos_neg_past",
            "subject",
            "subject_the",
            "subject_pos",
            "subject_the_pos",
            "gender_subject",
            "gender_pos",
            "gender_ref",
        ]
        for str_attr_key in self.str_attr_keys.copy():
            self.str_attr_keys.append(str_attr_key.capitalize())

    def test__get_str_attrs_no_patient(self):
        attrs = get_str_attrs()
        for str_attr_key in self.str_attr_keys:
            self.assertIn(str_attr_key, attrs)

    def test__get_str_attrs_with_patient(self):
        attrs = get_str_attrs(patient=self.psp)
        for str_attr_key in self.str_attr_keys:
            self.assertIn(str_attr_key, attrs)

    def test__get_str_attrs_with_patient_who_is_request_user(self):
        attrs = get_str_attrs(patient=self.psp, request_user=self.psp)
        for str_attr_key in self.str_attr_keys:
            self.assertIn(str_attr_key, attrs)

    def test__get_str_attrs_with_patient_who_is_not_request_user(self):
        attrs = get_str_attrs(patient=self.psp, request_user=self.user)
        for str_attr_key in self.str_attr_keys:
            self.assertIn(str_attr_key, attrs)
