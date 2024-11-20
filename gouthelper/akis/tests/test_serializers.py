from datetime import timedelta
from decimal import Decimal

import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ...genders.choices import Genders
from ...labs.tests.factories import create_creatinine_api_data
from ...medhistorydetails.choices import Stages
from ...users.tests.factories import create_psp
from ..api.serializers.base_serializers import AkiSerializer
from ..choices import Statuses
from ..tests.factories import create_aki_api_data
from .factories import AkiFactory

pytestmark = pytest.mark.django_db


class TestAkiSerializer(TestCase):
    def setUp(self):
        self.creatinine1 = create_creatinine_api_data(
            value=Decimal("1.0"), date_drawn=timezone.now() - timedelta(days=1)
        )
        self.creatinine2 = create_creatinine_api_data(
            value=Decimal("2.0"), date_drawn=timezone.now() - timedelta(days=2)
        )
        self.creatinine3 = create_creatinine_api_data(
            value=Decimal("3.0"), date_drawn=timezone.now() - timedelta(days=3)
        )
        self.creatinines = [self.creatinine1, self.creatinine2, self.creatinine3]
        self.baselinecreatinine = Decimal("1.5")
        self.stage = Stages.THREE
        self.gender = Genders.MALE
        self.age = 40
        self.patient = create_psp()
        self.aki = AkiFactory(status=Statuses.ONGOING)

    def test__is_valid(self):
        data = create_aki_api_data(
            creatinines=self.creatinines,
        )
        serializer = AkiSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test__is_not_valid_status_creatinines_disagree(self):
        data = create_aki_api_data(
            status=Statuses.ONGOING,
            creatinines=self.creatinines,
        )
        serializer = AkiSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("status", serializer.errors)
        self.assertIn("creatinines", serializer.errors)

    def test__is_not_valid_baselinecreatinine_stage_disagree(self):
        data = create_aki_api_data(
            baselinecreatinine=self.baselinecreatinine,
            stage=Stages.FIVE,
            age=20,
            gender=Genders.MALE,
            status=Statuses.ONGOING,
            creatinines=self.creatinines,
        )

        serializer = AkiSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("stage", serializer.errors)
        self.assertIn("does not match", serializer.errors["stage"][0])

        data.pop("creatinines")

        serializer = AkiSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test__is_not_valid_stage_and_creatinines_without_age_or_gender(self):
        data = create_aki_api_data(
            creatinines=self.creatinines,
            stage=Stages.THREE,
            status=Statuses.ONGOING,
        )

        serializer = AkiSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("age", serializer.errors)
        self.assertIn("gender", serializer.errors)

        data.pop("creatinines")

        serializer = AkiSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test__is_not_valid_stage_and_creatinines_without_age(self):
        data = create_aki_api_data(
            creatinines=self.creatinines,
            stage=Stages.THREE,
            gender=Genders.MALE,
            status=Statuses.ONGOING,
        )

        serializer = AkiSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("age", serializer.errors)

    def test__is_not_valid_stage_and_creatinines_without_gender(self):
        data = create_aki_api_data(
            creatinines=self.creatinines,
            stage=Stages.THREE,
            age=40,
            status=Statuses.ONGOING,
        )

        serializer = AkiSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("gender", serializer.errors)

    def test__create(self):
        data = create_aki_api_data(
            creatinines=self.creatinines,
            stage=self.stage,
            age=self.age,
            gender=self.gender,
            user=self.patient,
        )

        serializer = AkiSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        aki = serializer.save()

        self.assertEqual(aki.status, Statuses.RESOLVED)
        self.assertEqual(aki.user, self.patient)
        self.assertTrue(aki.creatinine_set.exists())
        self.assertEqual(aki.creatinine_set.count(), 3)
        for creatinine_value in [creatinine_data["value"] for creatinine_data in data["creatinines"]]:
            self.assertTrue(aki.creatinine_set.filter(value=creatinine_value).exists())

    def test__update(self):
        data = create_aki_api_data(
            creatinines=self.creatinines,
            stage=self.stage,
            age=self.age,
            gender=self.gender,
            user=self.patient,
        )

        serializer = AkiSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        aki = serializer.save()

        new_data = create_aki_api_data(
            creatinines=None,
            status=Statuses.ONGOING,
        )

        serializer = AkiSerializer(aki, data=new_data)

        self.assertTrue(serializer.is_valid())
        serializer.save()
        aki.refresh_from_db()

        self.assertEqual(aki.status, Statuses.ONGOING)
        self.assertEqual(aki.user, self.patient)
        self.assertFalse(aki.creatinine_set.exists())
