import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...users.tests.factories import create_psp
from ...utils.exceptions import GoutHelperValidationError
from ..services import DateOfBirthAPIMixin
from .factories import DateOfBirthFactory

pytestmark = pytest.mark.django_db


class TestDateOfBirthAPIMixin(TestCase):
    def setUp(self):
        self.dateofbirth = DateOfBirthFactory()
        self.patient = create_psp()
        self.mixin = DateOfBirthAPIMixin(
            dateofbirth=self.dateofbirth,
            dateofbirth__value=self.dateofbirth.value,
            patient=self.patient,
        )

    def test__init__(self):
        self.assertEqual(self.mixin.dateofbirth, self.dateofbirth)
        self.assertEqual(self.mixin.patient, self.patient)

    # def test__get_queryset_returns_error_with_dateofbirth_instance(self):
    #     with self.assertRaises(GoutHelperValidationError) as context:
    #         self.mixin.get_queryset()
    #         self.assertIn("dateofbirth", context.errors)

    def test__get_queryset_returns_dateofbirth_instance(self):
        self.mixin.dateofbirth = self.dateofbirth.pk
        self.assertEqual(self.mixin.get_queryset().get(), self.dateofbirth)

    def test__create_dateofbirth_with_patient_with_dateofbirth_raises_error(self):
        self.mixin.dateofbirth = None
        with self.assertRaises(GoutHelperValidationError) as context:
            self.mixin.create_dateofbirth()
        error_keys = [error[0] for error in context.exception.errors]
        self.assertIn("patient", error_keys)
        self.assertEqual(len(error_keys), 1)

    def test__create_dateofbirth_with_dateofbirth_value_missing_raises_error(self):
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
