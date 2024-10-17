from datetime import timedelta
from decimal import Decimal

import pytest  # type: ignore
from django.forms import model_to_dict
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ...genders.choices import Genders
from ...labs.tests.factories import BaselineCreatinineFactory, CreatinineFactory
from ...medhistorydetails.choices import Stages
from ...users.tests.factories import create_psp
from ...utils.exceptions import GoutHelperValidationError
from ...utils.test_helpers import date_days_ago, datetime_days_ago, model_instance_to_dict
from ..api.mixins import AkiAPIMixin
from ..api.services import AkiAPICreate, AkiAPIUpdate
from ..choices import Statuses
from ..models import Aki
from .factories import AkiFactory

pytestmark = pytest.mark.django_db


class TestAkiAPIMixin(TestCase):
    def setUp(self):
        self.api = AkiAPIMixin()
        self.api.aki__status = None
        self.api.creatinines_data = None
        self.api.baselinecreatinine__value = None
        self.api.ckddetail__stage = None
        self.creatinine1 = {"value": Decimal("1.0"), "date_drawn": timezone.now() - timedelta(days=1)}
        self.creatinine2 = {"value": Decimal("2.0"), "date_drawn": timezone.now() - timedelta(days=2)}
        self.creatinine3 = {"value": Decimal("3.0"), "date_drawn": timezone.now() - timedelta(days=3)}
        self.creatinines = [self.creatinine1, self.creatinine2, self.creatinine3]
        self.baselinecreatinine = BaselineCreatinineFactory(value=Decimal("1.5"))

    def test__aki_is_resolved_via_creatinines_most_recent_creatinine_normal(self):
        self.api.creatinines_data = self.creatinines
        self.assertTrue(self.api.aki_is_resolved_via_creatinines)

    def test__aki_is_resolved_via_creatinines_most_recent_creatinine_at_baseline(self):
        self.creatinine1 = {"value": Decimal("1.5"), "date_drawn": timezone.now() - timedelta(days=1)}
        self.creatinines = [self.creatinine1, self.creatinine2, self.creatinine3]
        self.api.creatinines_data = self.creatinines
        self.api.baselinecreatinine__value = Decimal("1.5")
        self.assertTrue(self.api.aki_is_resolved_via_creatinines)

    def test__aki_is_not_resolved_via_creatinines(self):
        self.creatinine1 = {"value": Decimal("1.5"), "date_drawn": timezone.now() - timedelta(days=1)}
        self.creatinines = [self.creatinine1, self.creatinine2, self.creatinine3]
        self.api.creatinines_data = self.creatinines
        self.assertFalse(self.api.aki_is_resolved_via_creatinines)

    def test__aki_is_improving_via_creatinines(self):
        self.api.creatinines_data = self.creatinines
        self.assertTrue(self.api.aki_is_improving_via_creatinines)

    def tet__aki_is_improving_via_creatinines_with_stage(self):
        self.api.ckddetail__stage = Stages.THREE
        self.api.gender = Genders.MALE
        self.api.age = 40
        self.creatinine1 = {"value": Decimal("2.0"), "date_drawn": timezone.now() - timedelta(days=1)}
        self.creatinines = [self.creatinine1, self.creatinine2, self.creatinine3]
        self.api.creatinines_data = self.creatinines
        self.assertTrue(self.api.aki_is_improving_via_creatinines)

    def test__aki_is_not_improving_via_creatinines(self):
        self.creatinine1 = {"value": Decimal("3.0"), "date_drawn": timezone.now() - timedelta(days=1)}
        self.creatinines = [self.creatinine1, self.creatinine2, self.creatinine3]
        self.api.creatinines_data = self.creatinines
        self.assertFalse(self.api.aki_is_improving_via_creatinines)

    def test__aki_is_not_improving_via_creatinines_with_stage(self):
        self.api.ckddetail__stage = Stages.THREE
        self.api.gender = Genders.MALE
        self.api.age = 40
        self.creatinine1 = {"value": Decimal("2.8"), "date_drawn": timezone.now() - timedelta(days=1)}
        self.creatinines = [self.creatinine1, self.creatinine2, self.creatinine3]
        self.api.creatinines_data = self.creatinines
        self.assertFalse(self.api.aki_is_improving_via_creatinines)

    def test__order_creatinines_data_by_date_drawn_desc(self):
        self.api.creatinines_data = [self.creatinine2, self.creatinine1, self.creatinine3]
        self.api.order_creatinines_data_by_date_drawn_desc()
        self.assertEqual(self.api.creatinines_data, [self.creatinine1, self.creatinine2, self.creatinine3])

    def test__set__aki_status_resolved(self):
        self.api.creatinines_data = self.creatinines
        self.api.set_aki__status()
        self.assertEqual(self.api.aki__status, Statuses.RESOLVED)

    def test__set__aki_status_improving(self):
        self.creatinine1 = {"value": Decimal("1.7"), "date_drawn": timezone.now() - timedelta(days=1)}
        self.creatinines = [self.creatinine1, self.creatinine2, self.creatinine3]
        self.api.creatinines_data = self.creatinines
        self.api.set_aki__status()
        self.assertEqual(self.api.aki__status, Statuses.IMPROVING)

    def test__set__aki_status_ongoing(self):
        self.creatinine1 = {"value": Decimal("2.5"), "date_drawn": timezone.now() - timedelta(days=1)}
        self.creatinines = [self.creatinine1, self.creatinine2, self.creatinine3]
        self.api.creatinines_data = self.creatinines
        self.api.set_aki__status()
        self.assertEqual(self.api.aki__status, Statuses.ONGOING)

    def test__set_aki_status_ongoing_no_creatinines(self):
        self.api.set_aki__status()
        self.assertEqual(self.api.aki__status, Statuses.ONGOING)


class TestAkiAPICreate(TestCase):
    def setUp(self):
        self.patient = create_psp()

    def test__create_aki(self):
        aki = AkiAPICreate(
            aki__status=Statuses.ONGOING,
            creatinines_data=[],
            baselinecreatinine__value=None,
            ckddetail__stage=None,
            patient=self.patient,
            age=self.patient.age,
            gender=self.patient.gender.value,
        ).create_aki()
        self.assertTrue(aki)
        self.assertTrue(isinstance(aki, Aki))

        userless_aki = AkiAPICreate(
            aki__status=Statuses.ONGOING,
            creatinines_data=[],
            baselinecreatinine__value=None,
            ckddetail__stage=None,
            patient=None,
            age=self.patient.age,
            gender=self.patient.gender.value,
        ).create_aki()
        self.assertTrue(userless_aki)
        self.assertTrue(isinstance(userless_aki, Aki))
        self.assertIsNone(userless_aki.user)

    def test__create_aki_with_errors(self):
        abnormal_creatinine_data = {"value": Decimal("3.0"), "date_drawn": timezone.now() - timedelta(days=1)}

        with self.assertRaises(GoutHelperValidationError) as exc:
            AkiAPICreate(
                aki__status=Statuses.RESOLVED,
                creatinines_data=[abnormal_creatinine_data],
                baselinecreatinine__value=None,
                ckddetail__stage=None,
                patient=self.patient,
                age=None,
                gender=None,
            ).create_aki()

        self.assertEqual(
            exc.exception.errors,
            [
                (
                    "creatinines_data",
                    "AKI marked as resolved, but the creatinines suggest it is not.",
                )
            ],
        )

    def test__create_aki_with_creatinines_data(self):
        creatinines_data = [
            {"value": Decimal("1.0"), "date_drawn": timezone.now() - timedelta(days=1)},
            {"value": Decimal("2.0"), "date_drawn": timezone.now() - timedelta(days=2)},
            {"value": Decimal("3.0"), "date_drawn": timezone.now() - timedelta(days=3)},
        ]
        aki = AkiAPICreate(
            aki__status=Statuses.RESOLVED,
            creatinines_data=creatinines_data,
            baselinecreatinine__value=None,
            ckddetail__stage=None,
            patient=self.patient,
            age=self.patient.age,
            gender=self.patient.gender,
        ).create_aki()
        self.assertTrue(aki)
        self.assertTrue(isinstance(aki, Aki))
        self.assertEqual(aki.creatinine_set.count(), 3)


class TestAkiAPIUpdate(TestCase):
    def setUp(self):
        self.patient = create_psp()
        self.aki = AkiFactory(status=Statuses.ONGOING)
        self.api = AkiAPIUpdate(
            aki=self.aki,
            aki__status=None,
            creatinines=[],
            creatinines_data=[],
            baselinecreatinine__value=None,
            ckddetail__stage=None,
            patient=None,
            age=self.patient.age,
            gender=self.patient.gender.value,
        )

    def test__update_aki(self):
        self.api.aki__status = Statuses.RESOLVED
        aki = self.api.update_aki()

        self.assertEqual(aki.status, Statuses.RESOLVED)

    def test__creates_creatinines(self):
        creatinines_data = [
            {"value": Decimal("1.0"), "date_drawn": timezone.now() - timedelta(days=1)},
            {"value": Decimal("2.0"), "date_drawn": timezone.now() - timedelta(days=2)},
            {"value": Decimal("3.0"), "date_drawn": timezone.now() - timedelta(days=3)},
        ]
        self.api.creatinines_data = creatinines_data
        aki = self.api.update_aki()

        self.assertEqual(aki.creatinine_set.count(), 3)
        self.assertEqual(aki.status, Statuses.RESOLVED)

    def test__creates_more_creatinines(self):
        creatinine_1 = CreatinineFactory(aki=self.aki, value=Decimal("3.0"), date_drawn=datetime_days_ago(10))
        creatinine_2 = CreatinineFactory(aki=self.aki, value=Decimal("2.0"), date_drawn=datetime_days_ago(5))
        creatinine_3 = CreatinineFactory(aki=self.aki, value=Decimal("1.9"), date_drawn=datetime_days_ago(1))

        creatinines = [creatinine_1, creatinine_2, creatinine_3]

        existing_creatinines_data = [
            model_to_dict(creatinine, fields=["aki", "value", "date_drawn"]) for creatinine in creatinines
        ]

        creatinines_data = [
            {"value": Decimal("2.0"), "date_drawn": timezone.now() - timedelta(days=2)},
            {"value": Decimal("3.0"), "date_drawn": timezone.now() - timedelta(days=3)},
            *existing_creatinines_data,
        ]

        self.api.creatinines = creatinines
        self.api.creatinines_data = creatinines_data
        aki = self.api.update_aki()

        self.assertEqual(aki.creatinine_set.count(), 5)
        self.assertEqual(aki.status, Statuses.IMPROVING)

    def test__updates_creatinines(self):
        creatinine_1 = CreatinineFactory(aki=self.aki, value=Decimal("3.0"), date_drawn=datetime_days_ago(10))
        creatinine_2 = CreatinineFactory(aki=self.aki, value=Decimal("2.0"), date_drawn=datetime_days_ago(5))
        creatinine_3 = CreatinineFactory(aki=self.aki, value=Decimal("1.9"), date_drawn=datetime_days_ago(1))

        creatinines = [creatinine_1, creatinine_2, creatinine_3]

        existing_creatinines_data = [
            model_instance_to_dict(creatinine, fields=["aki", "value", "date_drawn", "id"])
            for creatinine in creatinines
        ]

        for creatinine_data in existing_creatinines_data:
            creatinine_data["date_drawn"] = creatinine_data["date_drawn"] + timedelta(days=1)

        self.api.creatinines = creatinines
        self.api.creatinines_data = existing_creatinines_data
        aki = self.api.update_aki()

        self.assertEqual(aki.creatinine_set.count(), 3)
        self.assertEqual(aki.status, Statuses.IMPROVING)
        creatinine_1.refresh_from_db()
        creatinine_2.refresh_from_db()
        creatinine_3.refresh_from_db()
        self.assertEqual(creatinine_1.date_drawn.date(), date_days_ago(9))
        self.assertEqual(creatinine_2.date_drawn.date(), date_days_ago(4))
        self.assertEqual(creatinine_3.date_drawn.date(), date_days_ago(0))

    def test__deletes_creatinines(self):
        creatinine_1 = CreatinineFactory(aki=self.aki, value=Decimal("3.0"), date_drawn=datetime_days_ago(10))
        creatinine_2 = CreatinineFactory(aki=self.aki, value=Decimal("2.0"), date_drawn=datetime_days_ago(5))
        creatinine_3 = CreatinineFactory(aki=self.aki, value=Decimal("1.9"), date_drawn=datetime_days_ago(1))

        creatinines = [creatinine_1, creatinine_2, creatinine_3]

        self.api.creatinines = creatinines
        self.api.creatinines_data = []
        self.api.aki__status = Statuses.RESOLVED
        aki = self.api.update_aki()

        self.assertEqual(aki.creatinine_set.count(), 0)
        self.assertEqual(aki.status, Statuses.RESOLVED)

    def test__raises_error_without_aki(self):
        self.api.aki = None
        with self.assertRaises(GoutHelperValidationError):
            self.api.update_aki()
        self.assertIn(("aki", "Aki instance is required."), self.api.errors)

    def test__raises_error_for_creatinines_aki_status_error(self):
        self.api.aki__status = Statuses.RESOLVED
        self.api.creatinines_data = [
            {"value": Decimal("3.0"), "date_drawn": timezone.now() - timedelta(days=1)},
        ]
        with self.assertRaises(GoutHelperValidationError):
            self.api.update_aki()
        self.assertIn(
            ("creatinines_data", "AKI marked as resolved, but the creatinines suggest it is not."),
            self.api.errors,
        )
