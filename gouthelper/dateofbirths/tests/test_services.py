from datetime import date

import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...users.tests.factories import create_psp
from ...utils.exceptions import GoutHelperValidationError
from ..api.services import DateOfBirthAPI
from .factories import DateOfBirthFactory

pytestmark = pytest.mark.django_db


class TestDateOfBirthAPI(TestCase):
    def setUp(self):
        self.dateofbirth = DateOfBirthFactory()
        self.patient = create_psp()
        self.mixin = DateOfBirthAPI(
            dateofbirth=self.dateofbirth,
            dateofbirth__value=self.dateofbirth.value,
            patient=self.patient,
        )

    def test__init__(self):
        self.assertEqual(self.mixin.dateofbirth, self.dateofbirth)
        self.assertEqual(self.mixin.patient, self.patient)

    def test__get_queryset_returns_dateofbirth_instance(self):
        self.mixin.dateofbirth = self.dateofbirth.pk
        self.assertEqual(self.mixin.get_queryset().get(), self.dateofbirth)

    def test__check_for_dateofbirth_create_errors_with_dateofbirth(self):
        self.mixin.patient = None
        self.mixin.dateofbirth = self.dateofbirth
        self.mixin.check_for_dateofbirth_create_errors()
        self.assertEqual(
            self.mixin.errors,
            [("dateofbirth", f"{self.dateofbirth} already exists.")],
        )

    def test__check_for_dateofbirth_create_errors_without_dateofbirth_value(self):
        self.mixin.patient = None
        self.mixin.dateofbirth = None
        self.mixin.dateofbirth__value = None
        self.mixin.check_for_dateofbirth_create_errors()
        self.assertEqual(
            self.mixin.errors,
            [("dateofbirth__value", "Date is required to create a DateOfBirth instance.")],
        )

    def test__check_for_dateofbirth_create_errors_with_patient_with_dateofbirth(self):
        self.mixin.dateofbirth = None
        self.mixin.check_for_dateofbirth_create_errors()
        self.assertEqual(
            self.mixin.errors,
            [("patient", f"{self.mixin.patient} already has a date of birth ({self.mixin.patient.dateofbirth}).")],
        )

    def test__create_dateofbirth_with_patient_with_dateofbirth_raises_error(self):
        self.mixin.dateofbirth = None
        with self.assertRaises(GoutHelperValidationError) as context:
            self.mixin.create_dateofbirth()
        error_keys = [error[0] for error in context.exception.errors]
        self.assertIn("patient", error_keys)
        self.assertEqual(len(error_keys), 1)

    def test__create_dateofbirth_without_dateofbirth_value_raises_error(self):
        # Set patient and dateofbirth to None to avoid triggering the patient_has_dateofbirth_error
        self.mixin.dateofbirth = None
        self.mixin.patient = None
        self.mixin.dateofbirth__value = None
        with self.assertRaises(GoutHelperValidationError) as context:
            self.mixin.create_dateofbirth()
        error_keys = [error[0] for error in context.exception.errors]
        self.assertIn("dateofbirth__value", error_keys)
        self.assertEqual(len(error_keys), 1)

    def test__create_dateofbirth_without_patient(self):
        self.mixin.patient = None
        self.mixin.dateofbirth = None
        dateofbirth = self.mixin.create_dateofbirth()
        self.assertEqual(dateofbirth.user, None)
        self.assertEqual(dateofbirth.value, self.mixin.dateofbirth__value)

    def test__create_dateofbirth_with_patient(self):
        # Create a patient without a date of birth
        patient = create_psp()
        patient.dateofbirth.delete()
        patient.refresh_from_db()
        self.mixin.patient = patient
        self.mixin.dateofbirth = None
        dateofbirth = self.mixin.create_dateofbirth()
        self.assertEqual(dateofbirth.user, patient)
        self.assertEqual(dateofbirth.value, self.mixin.dateofbirth__value)

    def test__patient_has_dateofbirth(self):
        self.assertTrue(self.mixin.patient_has_dateofbirth)
        self.mixin.patient.dateofbirth.delete()
        self.mixin.patient.refresh_from_db()
        self.assertFalse(self.mixin.patient_has_dateofbirth)

    def test__has_errors(self):
        self.assertFalse(self.mixin.has_errors)
        self.assertFalse(self.mixin.errors)
        self.mixin.errors.append(("test", "error"))
        self.assertTrue(self.mixin.has_errors)

    def test__check_for_and_raise_errors(self):
        self.mixin.errors.append(("test", "error"))
        with self.assertRaises(GoutHelperValidationError) as context:
            self.mixin.check_for_and_raise_errors(model_name="DateOfBirth")
        self.assertEqual(
            context.exception.errors,
            self.mixin.errors,
        )

    def test__update_dateofbirth(self):
        self.mixin.dateofbirth = self.mixin.patient.dateofbirth
        self.mixin.update_dateofbirth()
        self.assertEqual(self.mixin.dateofbirth, self.patient.dateofbirth)
        self.assertEqual(self.mixin.dateofbirth.value, self.mixin.dateofbirth__value)

    def test__update_with_uuid(self):
        self.mixin.dateofbirth = self.dateofbirth.pk
        new_patient = create_psp()
        new_patient.dateofbirth.delete()
        self.mixin.patient = new_patient
        self.mixin.update_dateofbirth()
        self.assertEqual(self.mixin.dateofbirth, self.dateofbirth)
        self.assertEqual(self.mixin.dateofbirth.value, self.mixin.dateofbirth__value)

    def test__check_for_dateofbirth_update_errors_without_dateofbirth(self):
        self.mixin.dateofbirth = None
        self.mixin.check_for_dateofbirth_update_errors()
        self.assertEqual(
            self.mixin.errors,
            [("dateofbirth", "DateOfBirth is required to update a DateOfBirth instance.")],
        )

    def test__check_for_dateofbirth_update_errors_without_dateofbirth_value(self):
        self.mixin.dateofbirth__value = None
        self.mixin.check_for_dateofbirth_update_errors()
        self.assertEqual(
            self.mixin.errors,
            [("dateofbirth__value", "Date is required to update a DateOfBirth instance.")],
        )

    def test__check_for_dateofbirth_update_errors_with_dateofbirth_user_not_patient(self):
        new_patient = create_psp()
        self.mixin.dateofbirth = new_patient.dateofbirth
        self.mixin.check_for_dateofbirth_update_errors()
        self.assertEqual(
            self.mixin.errors,
            [("dateofbirth", f"{new_patient.dateofbirth} has a user who is not the {self.patient}.")],
        )

    def test__dateofbirth_has_user_who_is_not_patient(self):
        self.assertFalse(self.mixin.dateofbirth_has_user_who_is_not_patient)
        new_patient = create_psp()
        self.mixin.dateofbirth = new_patient.dateofbirth
        self.assertTrue(self.mixin.dateofbirth_has_user_who_is_not_patient)

    def test__dateofbirth_needs_save(self):
        self.mixin.dateofbirth = self.patient.dateofbirth
        self.assertTrue(self.mixin.dateofbirth_needs_save)
        self.mixin.dateofbirth.value = self.mixin.dateofbirth__value
        self.assertFalse(self.mixin.dateofbirth_needs_save)

    def test__update_dateofbirth_instance(self):
        self.mixin.patient.dateofbirth.delete()
        self.mixin.dateofbirth__value = "2001-01-01"
        self.mixin.update_dateofbirth_instance()
        self.assertEqual(self.dateofbirth.value, date(2001, 1, 1))
        self.assertEqual(self.dateofbirth.user, self.mixin.patient)

    def test__process_dateofbirth_create(self):
        self.mixin.dateofbirth = None
        self.mixin.patient = None
        self.mixin.process_dateofbirth()
        self.assertIsNotNone(self.mixin.dateofbirth)
        self.assertEqual(self.mixin.dateofbirth.value, self.dateofbirth.value)

    def test__process_dateofbirth_update(self):
        self.mixin.patient = None
        new_dateofbirth__value = "2002-03-03"
        self.mixin.dateofbirth__value = new_dateofbirth__value
        self.mixin.process_dateofbirth()
        self.assertEqual(self.mixin.dateofbirth.value, date(2002, 3, 3))

    def test__check_for_dateofbirth_process_errors_not_optional_with_patient(self):
        self.mixin.dateofbirth__value = None
        self.mixin.dateofbirth = None
        self.mixin.dateofbirth_patient_edit = False
        self.mixin.check_for_dateofbirth_process_errors()
        self.assertIn(("dateofbirth", f"DateOfBirth required for {self.patient}."), self.mixin.errors)

    def test__check_for_dateofbirth_process_errors_not_optional_without_patient(self):
        self.mixin.dateofbirth__value = None
        self.mixin.dateofbirth = None
        self.mixin.patient = None
        self.mixin.dateofbirth_patient_edit = False
        self.mixin.check_for_dateofbirth_process_errors()
        self.assertIn(("dateofbirth__value", "DateOfBirth value is required."), self.mixin.errors)

    def test__check_for_dateofbirth_process_errors_patient_edit_false(self):
        self.mixin.dateofbirth_patient_edit = False
        self.mixin.check_for_dateofbirth_process_errors()
        self.assertIn(
            ("dateofbirth__value", f"Can't edit DateOfBirth value for {self.patient} in {DateOfBirthAPI.__name__}."),
            self.mixin.errors,
        )

    def test__check_for_dateofbirth_process_errors_optional(self):
        self.mixin.dateofbirth__value = None
        self.mixin.dateofbirth = None
        self.mixin.patient = None
        self.mixin.dateofbirth_optional = True
        self.mixin.check_for_dateofbirth_process_errors()
        self.assertFalse(self.mixin.errors)

    def test__check_for_dateofbirth_process_errors_patient_edit(self):
        self.mixin.dateofbirth_patient_edit = True
        self.mixin.check_for_dateofbirth_process_errors()
        self.assertFalse(self.mixin.errors)

    def test__missing_dateofbirth__value_or_patient_dateofbirth(self):
        self.mixin.dateofbirth__value = None
        self.assertTrue(self.mixin.missing_dateofbirth__value_or_patient_dateofbirth)
        self.mixin.dateofbirth__value = self.mixin.dateofbirth.value
        self.mixin.dateofbirth = None
        self.assertFalse(self.mixin.missing_dateofbirth__value_or_patient_dateofbirth)
        self.mixin.dateofbirth_patient_edit = False
        self.assertTrue(self.mixin.missing_dateofbirth__value_or_patient_dateofbirth)
        self.mixin.dateofbirth = self.dateofbirth
        self.assertFalse(self.mixin.missing_dateofbirth__value_or_patient_dateofbirth)
        self.mixin.dateofbirth = None
        self.assertTrue(self.mixin.missing_dateofbirth__value_or_patient_dateofbirth)
        self.mixin.dateofbirth_patient_edit = True
        self.assertFalse(self.mixin.missing_dateofbirth__value_or_patient_dateofbirth)

    def test__missing_patient_dateofbirth(self):
        self.assertFalse(self.mixin.missing_patient_dateofbirth)
        self.mixin.dateofbirth = None
        self.assertFalse(self.mixin.missing_patient_dateofbirth)
        self.mixin.dateofbirth_patient_edit = False
        self.assertTrue(self.mixin.missing_patient_dateofbirth)
