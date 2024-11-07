from datetime import date
from decimal import Decimal

import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...akis.tests.factories import AkiFactory
from ...labs.models import BaselineCreatinine, Creatinine
from ...medhistorys.tests.factories import CkdFactory
from ...users.tests.factories import create_psp
from ...utils.test_helpers import date_days_ago
from ..api.mixins import BaselineCreatinineAPIMixin, CreatininesAPIMixin, UrateAPIMixin
from ..schema import UrateSchema
from .factories import BaselineCreatinineFactory, CreatinineFactory, UrateFactory

pytestmark = pytest.mark.django_db


class TestBaselineCreatinineAPIMixin(TestCase):
    def setUp(self):
        self.baselinecreatinine = BaselineCreatinineFactory()
        self.api = BaselineCreatinineAPIMixin()
        self.api_data = {
            "baselinecreatinine": self.baselinecreatinine,
            "baselinecreatinine__value": self.baselinecreatinine.value,
            "baselinecreatinine__medhistory": self.baselinecreatinine.medhistory,
        }

    def set_api_attrs(self):
        for attr, value in self.api_data.items():
            setattr(self.api, attr, value)

    def test__process_baselinecreatinine(self):
        self.assertEqual(BaselineCreatinine.objects.count(), 1)
        self.api_data.update(
            {
                "baselinecreatinine": None,
                "baselinecreatinine__medhistory": CkdFactory(),
            }
        )
        self.set_api_attrs()
        self.api.process_baselinecreatinine()
        self.assertEqual(BaselineCreatinine.objects.count(), 2)

        self.api_data.update(
            {
                "baselinecreatinine": self.api.baselinecreatinine,
                "baselinecreatinine__value": Decimal("2.0"),
                "baselinecreatinine__medhistory": self.api.baselinecreatinine.medhistory,
            }
        )
        self.set_api_attrs()
        self.api.process_baselinecreatinine()
        self.assertEqual(self.api.baselinecreatinine.value, Decimal("2.0"))

        self.api_data.update(
            {
                "baselinecreatinine__value": None,
            }
        )
        self.set_api_attrs()
        self.api.process_baselinecreatinine()
        self.assertIsNone(self.api.baselinecreatinine)

    def test__get_queryset(self):
        self.set_api_attrs()
        with self.assertRaises(TypeError):
            self.api.get_queryset()
        self.api.baselinecreatinine = self.baselinecreatinine.id
        self.assertEqual(self.api.get_queryset().get(), self.baselinecreatinine)

    def test__baselinecreatinine_should_be_deleted(self):
        self.set_api_attrs()
        self.api.baselinecreatinine = None
        self.api.baselinecreatinine_should_be_deleted
        self.assertTrue(self.api.errors)
        self.assertIn(
            ("baselinecreatinine", "BaselineCreatinine instance required for deletion."),
            self.api.errors,
        )

        self.api.baselinecreatinine = self.baselinecreatinine
        self.assertFalse(self.api.baselinecreatinine_should_be_deleted)

        self.api.baselinecreatinine__value = None
        self.assertTrue(self.api.baselinecreatinine_should_be_deleted)

    def test__check_for_baselinecreatinine_delete_errors(self):
        self.set_api_attrs()
        self.api.check_for_baselinecreatinine_delete_errors()
        self.assertFalse(self.api.errors)

        self.api.baselinecreatinine = None
        self.api.check_for_baselinecreatinine_delete_errors()
        self.assertTrue(self.api.errors)
        self.assertIn(
            ("baselinecreatinine", "BaselineCreatinine instance required for deletion."),
            self.api.errors,
        )

    def test__delete_baselinecreatinine(self):
        self.assertEqual(BaselineCreatinine.objects.count(), 1)

        self.set_api_attrs()
        self.api.errors = ["Error"]
        self.api.delete_baselinecreatinine()
        self.assertEqual(BaselineCreatinine.objects.count(), 1)

        self.api.errors = []
        self.api.delete_baselinecreatinine()
        self.assertEqual(BaselineCreatinine.objects.count(), 0)

    def test__baselinecreatinine_needs_update(self):
        self.set_api_attrs()
        self.assertFalse(self.api.baselinecreatinine_needs_update)

        self.api.baselinecreatinine__value = Decimal("2.0")
        self.assertTrue(self.api.baselinecreatinine_needs_update)

        self.api.baselinecreatinine__value = None
        self.assertFalse(self.api.baselinecreatinine_needs_update)

    def test__check_for_baselinecreatinine_update_errors(self):
        self.set_api_attrs()
        self.api.check_for_baselinecreatinine_update_errors()
        self.assertFalse(self.api.errors)

        self.api.baselinecreatinine = None
        self.api.baselinecreatinine__value = None
        self.api.check_for_baselinecreatinine_update_errors()
        self.assertTrue(self.api.errors)
        self.assertIn(
            ("baselinecreatinine__value", "baselinecreatinine__value is required for update."),
            self.api.errors,
        )
        self.assertIn(("baselinecreatinine", "BaselineCreatinine required for update."), self.api.errors)

    def test__update_baselinecreatinine(self):
        self.set_api_attrs()
        self.api.baselinecreatinine__value = Decimal("2.0")
        self.api.update_baselinecreatinine()
        self.assertEqual(self.api.baselinecreatinine.value, Decimal("2.0"))

        self.api.errors = ["Error"]
        self.api.baselinecreatinine__value = Decimal("3.0")
        self.api.update_baselinecreatinine()
        self.assertNotEqual(self.api.baselinecreatinine.value, Decimal("3.0"))

    def test__baselinecreatinine_should_be_created(self):
        self.set_api_attrs()
        self.assertFalse(self.api.baselinecreatinine_should_be_created)
        self.assertTrue(self.api.errors)
        self.assertIn(
            ("baselinecreatinine", "BaselineCreatinine instance already exists."),
            self.api.errors,
        )

        self.api.baselinecreatinine = None
        self.assertTrue(self.api.baselinecreatinine_should_be_created)

    def test__create_baselinecreatinine(self):
        self.assertEqual(BaselineCreatinine.objects.count(), 1)
        self.api.errors = ["Error"]
        self.api.create_baselinecreatinine()
        self.assertEqual(BaselineCreatinine.objects.count(), 1)

        self.set_api_attrs()
        self.api.errors = []
        self.api.baselinecreatinine = None
        self.api.baselinecreatinine__medhistory = CkdFactory()
        self.api.create_baselinecreatinine()
        self.assertEqual(BaselineCreatinine.objects.count(), 2)


class TestCreatininesAPICreateMixin(TestCase):
    def setUp(self):
        self.api = CreatininesAPIMixin()
        self.creatinines_data = [
            {"value": Decimal("1.0"), "date_drawn": date_days_ago(1)},
            {"value": Decimal("2.0"), "date_drawn": date_days_ago(2)},
            {"value": Decimal("3.0"), "date_drawn": date_days_ago(3)},
        ]
        self.patient = create_psp()

    def test__create_creatinines(self):
        self.api.creatinines_data = self.creatinines_data
        self.api.patient = self.patient
        creatinines = self.api.create_creatinines()
        self.assertEqual(len(creatinines), 3)
        self.assertEqual(creatinines[0].value, Decimal("1.0"))
        self.assertEqual(creatinines[1].value, Decimal("2.0"))
        self.assertEqual(creatinines[2].value, Decimal("3.0"))
        for creatinine in creatinines:
            self.assertEqual(creatinine.user, self.patient)


class TestCreatininesAPIUpdateMixin(TestCase):
    def setUp(self):
        self.api = CreatininesAPIMixin()
        self.creatinines = [
            CreatinineFactory(value=Decimal("1.0"), date_drawn=date_days_ago(1)),
            CreatinineFactory(value=Decimal("2.0"), date_drawn=date_days_ago(2)),
            CreatinineFactory(value=Decimal("3.0"), date_drawn=date_days_ago(3)),
        ]
        self.creatinines_data = [
            {"value": Decimal("1.5"), "date_drawn": date_days_ago(3), "id": self.creatinines[0].id},
            {"value": Decimal("2.5"), "date_drawn": date_days_ago(4), "id": self.creatinines[1].id},
            {"value": Decimal("3.5"), "date_drawn": date_days_ago(5), "id": self.creatinines[2].id},
        ]
        self.api.creatinines = self.creatinines
        self.api.creatinines_data = self.creatinines_data
        self.patient = create_psp()
        self.api.patient = self.patient
        self.aki = AkiFactory()

    def test__update_creatinines(self):
        self.api.update_creatinines()
        self.assertEqual(self.api.creatinines[0].value, Decimal("1.5"))
        self.assertEqual(self.api.creatinines[1].value, Decimal("2.5"))
        self.assertEqual(self.api.creatinines[2].value, Decimal("3.5"))
        self.assertEqual(self.api.creatinines[0].date_drawn, date_days_ago(3))
        self.assertEqual(self.api.creatinines[1].date_drawn, date_days_ago(4))
        self.assertEqual(self.api.creatinines[2].date_drawn, date_days_ago(5))

    def test__update_creatinines_deletes_creatinines(self):
        self.api.creatinines_data = []
        self.api.update_creatinines()
        self.assertEqual(Creatinine.objects.count(), 0)

    def test__update_creatinines_creates_creatinines(self):
        self.api.creatinines_data = [
            {"value": Decimal("1.0"), "date_drawn": date_days_ago(1)},
            {"value": Decimal("2.0"), "date_drawn": date_days_ago(2)},
            {"value": Decimal("3.0"), "date_drawn": date_days_ago(3)},
        ]
        self.api.update_creatinines()
        self.assertEqual(Creatinine.objects.count(), 3)
        self.assertEqual(Creatinine.history.count(), 9)


class TestUrateAPIMixinCreate(TestCase):
    def setUp(self):
        self.api = UrateAPIMixin()
        self.urate__date_drawn = date_days_ago(1)
        self.urate__value = Decimal("1.0")
        self.patient = create_psp()

    def test__create_urate(self):
        self.api.urate__date_drawn = self.urate__date_drawn
        self.api.urate__value = self.urate__value
        self.api.patient = self.patient
        urate = self.api.create_urate()
        self.assertEqual(urate.value, Decimal("1.0"))
        self.assertEqual(urate.user, self.patient)

    def test__urate_should_be_created(self):
        self.api.urate__date_drawn = self.urate__date_drawn
        self.api.urate__value = self.urate__value
        self.api.patient = self.patient
        self.assertTrue(self.api.urate_should_be_created)

    def test__check_for_urate_create_errors(self):
        self.api.urate__value = None
        self.api.urate__date_drawn = None
        self.api.errors = []
        self.api.check_for_urate_create_errors()
        self.assertTrue(self.api.errors)
        self.assertIn(
            (
                "urate__value",
                "urate__value is required.",
            ),
            self.api.errors,
        )
        self.assertIn(
            (
                "urate__date_drawn",
                "urate__date_drawn is required.",
            ),
            self.api.errors,
        )


class TestUrateAPIMixinUpdate(TestCase):
    def setUp(self):
        self.urate = UrateFactory()
        self.api = UrateAPIMixin()
        self.urate__date_drawn = date_days_ago(1)
        self.urate__value = Decimal("7.0")
        self.patient = create_psp()
        self.urate_data = {"value": "8.0", "date_drawn": "2021-01-01"}

    def test__update_with_data(self):
        self.urate_data.update({"id": self.urate.id, "user": self.patient.id, "ppx": None})
        serializer = UrateSchema.drf_serializer(data=self.urate_data)
        serializer.is_valid(raise_exception=True)
        self.api.urate = self.urate
        self.api.urate__value = serializer.validated_data["value"]
        self.api.urate__date_drawn = serializer.validated_data["date_drawn"]
        self.api.patient = serializer.validated_data["user"]
        self.api.update_urate()
        self.assertEqual(self.api.urate.value, Decimal("8.0"))
        self.assertEqual(self.api.urate.date_drawn.date(), date(2021, 1, 1))
        self.assertEqual(self.api.urate.user, self.patient)

    def test__check_for_update_errors(self):
        self.api.urate = None
        self.api.check_for_urate_update_errors()
        self.assertTrue(self.api.errors)
        self.assertIn(
            (
                "urate",
                "Urate instance is required.",
            ),
            self.api.errors,
        )

    def test__urate_should_be_deleted(self):
        self.api.urate = self.urate
        self.api.urate__value = None
        self.assertTrue(self.api.urate_should_be_deleted)

    def test__urate_user_is_patient(self):
        new_patient = create_psp()
        new_patient_urate = UrateFactory(user=new_patient)
        self.assertTrue(self.api.urate_user_is_patient(new_patient_urate, new_patient))
        self.assertTrue(self.api.urate_user_is_patient(new_patient_urate, new_patient.id))
        self.assertFalse(self.api.urate_user_is_patient(new_patient_urate, self.patient))
        self.assertFalse(self.api.urate_user_is_patient(new_patient_urate, self.patient.id))

    def test__get_queryset(self):
        self.api.urate = self.urate.id
        qs = self.api.get_queryset()
        self.assertEqual(qs, self.urate)

    def test__get_queryset_raises_error_urate_not_uuid(self):
        self.api.urate = self.urate
        with self.assertRaises(TypeError):
            self.api.get_queryset()

    def test__get_queryset_raises_error_user_not_patient(self):
        self.api.patient = self.patient
        self.urate.user = create_psp()
        self.urate.save()
        self.api.urate = self.urate.id
        with self.assertRaises(ValueError):
            self.api.get_queryset()

    def test__set_attrs_from_qs(self):
        self.api.patient = None
        self.api.urate = self.urate.id
        self.api.set_attrs_from_qs()
        self.assertEqual(self.api.urate, self.urate)
        self.assertEqual(self.api.patient, self.urate.user)
