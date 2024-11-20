import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from django.utils import timezone

from ...akis.tests.factories import AkiFactory
from ...users.tests.factories import create_psp
from ..api.serializers import CreatinineSerializer, UrateSerializer
from .factories import CreatinineFactory, UrateFactory

pytestmark = pytest.mark.django_db


class TestCreatinineSerializer(TestCase):
    def setUp(self):
        self.creatinine = CreatinineFactory()
        self.patient = create_psp()

    def test__create_creatinine(self):
        data = {
            "value": 1.0,
            "date_drawn": timezone.now(),
            "user": self.patient,
            "aki": None,
        }

        creatinine = CreatinineSerializer.create_creatinine(data)

        self.assertEqual(creatinine.value, data["value"])
        self.assertEqual(creatinine.date_drawn, data["date_drawn"])
        self.assertEqual(creatinine.user, data["user"])
        self.assertIsNone(creatinine.aki)

    def test__update_creatinine(self):
        data = {
            "value": 1.0,
            "date_drawn": timezone.now(),
            "user": self.patient,
            "aki": None,
        }

        creatinine = CreatinineSerializer.create_creatinine(data)

        updated_data = {
            "value": 2.0,
            "date_drawn": timezone.now(),
            "user": self.patient,
            "aki": AkiFactory(),
        }

        updated_creatinine = CreatinineSerializer.update_creatinine(updated_data, creatinine)

        self.assertEqual(updated_creatinine.value, updated_data["value"])
        self.assertEqual(updated_creatinine.date_drawn, updated_data["date_drawn"])
        self.assertEqual(updated_creatinine.user, updated_data["user"])
        self.assertIsNotNone(updated_creatinine.aki)


class TestUrateSerializer(TestCase):
    def setUp(self):
        self.urate = UrateFactory()
        self.patient = create_psp()

    def test__create_urate(self):
        data = {
            "value": 1.0,
            "date_drawn": timezone.now(),
            "user": self.patient,
            "ppx": None,
        }

        urate = UrateSerializer.create_urate(data)

        self.assertEqual(urate.value, data["value"])
        self.assertEqual(urate.date_drawn, data["date_drawn"])
        self.assertEqual(urate.user, data["user"])
        self.assertIsNone(urate.ppx)

    def test__update_urate(self):
        data = {
            "value": 1.0,
            "date_drawn": timezone.now(),
            "user": self.patient,
            "ppx": None,
        }

        urate = UrateSerializer.create_urate(data)

        updated_data = {
            "value": 2.0,
            "date_drawn": timezone.now(),
            "user": self.patient,
            "ppx": None,
        }

        updated_urate = UrateSerializer.update_urate(updated_data, urate)

        self.assertEqual(updated_urate.value, updated_data["value"])
        self.assertEqual(updated_urate.date_drawn, updated_data["date_drawn"])
        self.assertEqual(updated_urate.user, updated_data["user"])
        self.assertIsNone(updated_urate.ppx)
