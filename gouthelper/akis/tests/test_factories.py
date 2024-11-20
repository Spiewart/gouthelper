from datetime import timedelta
from decimal import Decimal

import pytest  # type: ignore
from django.forms.models import model_to_dict  # type: ignore
from django.test import TestCase  # type: ignore
from django.utils import timezone

from ...labs.tests.factories import CreatinineFactory, create_creatinine_api_data
from .factories import AkiFactory, create_aki_api_data

pytestmark = pytest.mark.django_db


class TestCreateAkiAPIData(TestCase):
    def setUp(self):
        self.creatinine1 = CreatinineFactory(value=Decimal("1.0"), date_drawn=timezone.now().date())
        self.creatinine2 = CreatinineFactory(
            value=Decimal("2.0"), date_drawn=timezone.now().date() - timedelta(days=2)
        )
        self.creatinine3 = CreatinineFactory(
            value=Decimal("3.0"), date_drawn=timezone.now().date() - timedelta(days=5)
        )
        self.creatinines = [self.creatinine1, self.creatinine2, self.creatinine3]
        self.aki = AkiFactory()

    def test__with_aki(self):
        data = create_aki_api_data(aki=self.aki)
        self.assertTrue(isinstance(data, dict))
        self.assertEqual(data["id"], self.aki.id)
        self.assertEqual(data["status"], self.aki.status)
        self.assertEqual(data["user"], self.aki.user.id if self.aki.user else None)
        self.assertEqual(
            data["creatinines"],
            [create_creatinine_api_data(creatinine=creatinine) for creatinine in self.aki.creatinines.all()],
        )

    def test__with_aki_data(self):
        model_data = model_to_dict(self.aki)
        data = create_aki_api_data(
            aki=None,
            status=model_data["status"],
            user=model_data["user"],
            creatinines=self.aki.creatinine_set.all(),
        )
        self.assertTrue(isinstance(data, dict))
        self.assertEqual(data["id"], None)
        self.assertEqual(data["status"], self.aki.status)
        self.assertEqual(data["user"], self.aki.user.id if self.aki.user else None)
        self.assertEqual(
            data["creatinines"],
            [create_creatinine_api_data(creatinine=creatinine) for creatinine in self.aki.creatinines.all()],
        )
