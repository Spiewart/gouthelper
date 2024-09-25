import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...users.tests.factories import create_psp
from ...utils.exceptions import GoutHelperValidationError
from ..api.services import GenderAPI
from ..choices import Genders
from .factories import GenderFactory

pytestmark = pytest.mark.django_db


class TestGenderAPI(TestCase):
    def setUp(self):
        self.gender = GenderFactory()
        print(self.gender.value)
        self.patient = create_psp()
        self.mixin = GenderAPI(
            gender=self.gender,
            gender__value=self.gender.value,
            patient=self.patient,
        )

    def test__init__(self):
        self.assertEqual(self.mixin.gender, self.gender)
        self.assertEqual(self.mixin.patient, self.patient)

    def test__get_queryset_returns_gender_instance(self):
        self.mixin.gender = self.gender.pk
        self.assertEqual(self.mixin.get_queryset().get(), self.gender)

    def test__check_for_gender_create_errors_with_gender(self):
        self.mixin.patient = None
        self.mixin.gender = self.gender
        self.mixin.check_for_gender_create_errors()
        self.assertEqual(
            self.mixin.errors,
            [("gender", f"{self.gender} already exists.")],
        )

    def test__check_for_gender_create_errors_without_gender_value(self):
        self.mixin.patient = None
        self.mixin.gender = None
        self.mixin.gender__value = None
        self.mixin.check_for_gender_create_errors()
        self.assertEqual(
            self.mixin.errors,
            [("gender__value", "Genders is required to create a Gender instance.")],
        )

    def test__check_for_gender_create_errors_with_patient_with_gender(self):
        self.mixin.gender = None
        self.mixin.check_for_gender_create_errors()
        self.assertEqual(
            self.mixin.errors,
            [("patient", f"{self.mixin.patient} already has a Gender ({self.mixin.patient.gender}).")],
        )

    def test__create_gender_with_patient_with_gender_raises_error(self):
        self.mixin.gender = None
        with self.assertRaises(GoutHelperValidationError) as context:
            self.mixin.create_gender()
        error_keys = [error[0] for error in context.exception.errors]
        self.assertIn("patient", error_keys)
        self.assertEqual(len(error_keys), 1)

    def test__create_gender_without_gender_value_raises_error(self):
        # Set patient and gender to None to avoid triggering the patient_has_gender_error
        self.mixin.gender = None
        self.mixin.patient = None
        self.mixin.gender__value = None
        with self.assertRaises(GoutHelperValidationError) as context:
            self.mixin.create_gender()
        error_keys = [error[0] for error in context.exception.errors]
        self.assertIn("gender__value", error_keys)
        self.assertEqual(len(error_keys), 1)

    def test__create_gender_without_patient(self):
        self.mixin.patient = None
        self.mixin.gender = None
        gender = self.mixin.create_gender()
        self.assertEqual(gender.user, None)
        self.assertEqual(gender.value, self.mixin.gender__value)

    def test__create_gender_with_patient(self):
        # Create a patient without a Gender
        patient = create_psp()
        patient.gender.delete()
        patient.refresh_from_db()
        self.mixin.patient = patient
        self.mixin.gender = None
        gender = self.mixin.create_gender()
        self.assertEqual(gender.user, patient)
        self.assertEqual(gender.value, self.mixin.gender__value)

    def test__patient_has_gender(self):
        self.assertTrue(self.mixin.patient_has_gender)
        self.mixin.patient.gender.delete()
        self.mixin.patient.refresh_from_db()
        self.assertFalse(self.mixin.patient_has_gender)

    def test__has_errors(self):
        self.assertFalse(self.mixin.has_errors)
        self.assertFalse(self.mixin.errors)
        self.mixin.errors.append(("test", "error"))
        self.assertTrue(self.mixin.has_errors)

    def test__check_for_and_raise_errors(self):
        self.mixin.errors.append(("test", "error"))
        with self.assertRaises(GoutHelperValidationError) as context:
            self.mixin.check_for_and_raise_errors()
        self.assertEqual(
            context.exception.errors,
            self.mixin.errors,
        )

    def test__update_gender(self):
        self.mixin.gender = self.mixin.patient.gender
        self.mixin.update_gender()
        self.assertEqual(self.mixin.gender, self.patient.gender)
        self.assertEqual(self.mixin.gender.value, self.mixin.gender__value)

    def test__update_with_uuid(self):
        self.mixin.gender = self.gender.pk
        new_patient = create_psp()
        new_patient.gender.delete()
        self.mixin.patient = new_patient
        self.mixin.update_gender()
        self.assertEqual(self.mixin.gender, self.gender)
        self.assertEqual(self.mixin.gender.value, self.mixin.gender__value)

    def test__check_for_gender_update_errors_without_gender(self):
        self.mixin.gender = None
        self.mixin.check_for_gender_update_errors()
        self.assertEqual(
            self.mixin.errors,
            [("gender", "Genders is required to update a Gender instance.")],
        )

    def test__check_for_gender_update_errors_without_gender_value(self):
        self.mixin.gender__value = None
        self.mixin.check_for_gender_update_errors()
        self.assertEqual(
            self.mixin.errors,
            [("gender__value", "Genders is required to update a Gender instance.")],
        )

    def test__check_for_gender_update_errors_with_gender_user_not_patient(self):
        new_patient = create_psp()
        self.mixin.gender = new_patient.gender
        self.mixin.check_for_gender_update_errors()
        self.assertEqual(
            self.mixin.errors,
            [("gender", f"{new_patient.gender} has a user who is not the {self.patient}.")],
        )

    def test__gender_has_user_who_is_not_patient(self):
        self.assertFalse(self.mixin.gender_has_user_who_is_not_patient)
        new_patient = create_psp()
        self.mixin.gender = new_patient.gender
        self.assertTrue(self.mixin.gender_has_user_who_is_not_patient)

    def test__gender_needs_save(self):
        self.mixin.gender = self.patient.gender
        self.mixin.patient = None
        self.assertTrue(self.mixin.gender_needs_save)
        self.mixin.gender.value = self.mixin.gender__value
        self.mixin.patient = self.patient
        self.assertFalse(self.mixin.gender_needs_save)

    def test__update_gender_instance(self):
        self.mixin.patient.gender.delete()
        self.mixin.gender__value = Genders.FEMALE
        self.mixin.update_gender_instance()
        self.assertEqual(self.gender.value, Genders.FEMALE)
        self.assertEqual(self.gender.user, self.mixin.patient)
