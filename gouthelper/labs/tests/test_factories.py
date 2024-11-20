from datetime import date

import pytest  # type: ignore
from django.forms.models import model_to_dict  # type: ignore
from django.test import TestCase  # type: ignore

from .factories import CreatinineFactory, UrateFactory, create_creatinine_api_data, create_urate_api_data

pytestmark = pytest.mark.django_db


class TestCreateCreateinineAPIData(TestCase):
    def setUp(self):
        self.creatinine = CreatinineFactory()

    def test__with_creatinine(self):
        data = create_creatinine_api_data(creatinine=self.creatinine)
        self.assertTrue(isinstance(data, dict))
        self.assertEqual(data["id"], self.creatinine.id)
        self.assertEqual(data["value"], self.creatinine.value)
        self.assertEqual(data["date_drawn"], self.creatinine.date_drawn)
        self.assertEqual(data["user"], self.creatinine.user.id if self.creatinine.user else None)
        self.assertEqual(data["aki"], self.creatinine.aki.id if self.creatinine.aki else None)

    def test__with_creatinine_data(self):
        model_data = model_to_dict(self.creatinine)
        data = create_creatinine_api_data(
            creatinine=None,
            value=model_data["value"],
            date_drawn=model_data["date_drawn"],
            user=model_data["user"],
            aki=model_data["aki"],
        )
        self.assertTrue(isinstance(data, dict))
        self.assertEqual(data["id"], None)
        self.assertEqual(data["value"], self.creatinine.value)
        self.assertEqual(data["date_drawn"], self.creatinine.date_drawn)
        self.assertEqual(data["user"], self.creatinine.user.id if self.creatinine.user else None)
        self.assertEqual(data["aki"], self.creatinine.aki.id if self.creatinine.aki else None)

    def test__data_overwrites_instance(self):
        model_data = model_to_dict(self.creatinine)
        data = create_creatinine_api_data(
            creatinine=self.creatinine,
            value=model_data["value"] + 1,
            date_drawn=date.today(),
            user=None,
            aki=None,
        )
        self.assertTrue(isinstance(data, dict))
        self.assertEqual(data["id"], self.creatinine.id)
        self.assertEqual(data["value"], model_data["value"] + 1)
        self.assertEqual(data["date_drawn"], date.today())
        self.assertEqual(data["user"], None)
        self.assertEqual(data["aki"], None)


class TestCreateUrateAPIData(TestCase):
    def setUp(self):
        self.urate = UrateFactory()

    def test__with_urate(self):
        data = create_urate_api_data(urate=self.urate)
        self.assertTrue(isinstance(data, dict))
        self.assertEqual(data["id"], self.urate.id)
        self.assertEqual(data["value"], self.urate.value)
        self.assertEqual(data["date_drawn"], self.urate.date_drawn)
        self.assertEqual(data["user"], self.urate.user.id if self.urate.user else None)

    def test__with_urate_data(self):
        model_data = model_to_dict(self.urate)
        data = create_urate_api_data(
            urate=None,
            value=model_data["value"],
            date_drawn=model_data["date_drawn"],
            user=model_data["user"],
        )
        self.assertTrue(isinstance(data, dict))
        self.assertEqual(data["id"], None)
        self.assertEqual(data["value"], self.urate.value)
        self.assertEqual(data["date_drawn"], self.urate.date_drawn)
        self.assertEqual(data["user"], self.urate.user.id if self.urate.user else None)
