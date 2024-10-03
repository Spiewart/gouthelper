import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...users.tests.factories import create_psp
from ...utils.exceptions import GoutHelperValidationError
from ..api.services import EthnicityAPI
from ..choices import Ethnicitys
from .factories import EthnicityFactory

pytestmark = pytest.mark.django_db


class TestEthnicityAPI(TestCase):
    def setUp(self):
        self.ethnicity = EthnicityFactory()
        self.patient = create_psp()
        self.mixin = EthnicityAPI(
            ethnicity=self.ethnicity,
            ethnicity__value=self.ethnicity.value,
            patient=self.patient,
        )

    def test__init__(self):
        self.assertEqual(self.mixin.ethnicity, self.ethnicity)
        self.assertEqual(self.mixin.patient, self.patient)

    def test__get_queryset_returns_ethnicity_instance(self):
        self.mixin.ethnicity = self.ethnicity.pk
        self.assertEqual(self.mixin.get_queryset().get(), self.ethnicity)

    def test__check_for_ethnicity_create_errors_with_ethnicity(self):
        self.mixin.patient = None
        self.mixin.ethnicity = self.ethnicity
        self.mixin.check_for_ethnicity_create_errors()
        self.assertEqual(
            self.mixin.errors,
            [("ethnicity", f"{self.ethnicity} already exists.")],
        )

    def test__check_for_ethnicity_create_errors_without_ethnicity_value(self):
        self.mixin.patient = None
        self.mixin.ethnicity = None
        self.mixin.ethnicity__value = None
        self.mixin.check_for_ethnicity_create_errors()
        self.assertEqual(
            self.mixin.errors,
            [("ethnicity__value", "Ethnicitys is required to create a Ethnicity instance.")],
        )

    def test__check_for_ethnicity_create_errors_with_patient_with_ethnicity(self):
        self.mixin.ethnicity = None
        self.mixin.check_for_ethnicity_create_errors()
        self.assertEqual(
            self.mixin.errors,
            [("patient", f"{self.mixin.patient} already has an ethnicity ({self.mixin.patient.ethnicity}).")],
        )

    def test__create_ethnicity_with_patient_with_ethnicity_raises_error(self):
        self.mixin.ethnicity = None
        with self.assertRaises(GoutHelperValidationError) as context:
            self.mixin.create_ethnicity()
        error_keys = [error[0] for error in context.exception.errors]
        self.assertIn("patient", error_keys)
        self.assertEqual(len(error_keys), 1)

    def test__create_ethnicity_without_ethnicity_value_raises_error(self):
        # Set patient and ethnicity to None to avoid triggering the patient_has_ethnicity_error
        self.mixin.ethnicity = None
        self.mixin.patient = None
        self.mixin.ethnicity__value = None
        with self.assertRaises(GoutHelperValidationError) as context:
            self.mixin.create_ethnicity()
        error_keys = [error[0] for error in context.exception.errors]
        self.assertIn("ethnicity__value", error_keys)
        self.assertEqual(len(error_keys), 1)

    def test__create_ethnicity_without_patient(self):
        self.mixin.patient = None
        self.mixin.ethnicity = None
        ethnicity = self.mixin.create_ethnicity()
        self.assertEqual(ethnicity.user, None)
        self.assertEqual(ethnicity.value, self.mixin.ethnicity__value)

    def test__create_ethnicity_with_patient(self):
        # Create a patient without a ethnicity
        patient = create_psp()
        patient.ethnicity.delete()
        patient.refresh_from_db()
        self.mixin.patient = patient
        self.mixin.ethnicity = None
        ethnicity = self.mixin.create_ethnicity()
        self.assertEqual(ethnicity.user, patient)
        self.assertEqual(ethnicity.value, self.mixin.ethnicity__value)

    def test__patient_has_ethnicity(self):
        self.assertTrue(self.mixin.patient_has_ethnicity)
        self.mixin.patient.ethnicity.delete()
        self.mixin.patient.refresh_from_db()
        self.assertFalse(self.mixin.patient_has_ethnicity)

    def test__has_errors(self):
        self.assertFalse(self.mixin.has_errors)
        self.assertFalse(self.mixin.errors)
        self.mixin.errors.append(("test", "error"))
        self.assertTrue(self.mixin.has_errors)

    def test__check_for_and_raise_errors(self):
        self.mixin.errors.append(("test", "error"))
        with self.assertRaises(GoutHelperValidationError) as context:
            self.mixin.check_for_and_raise_errors(model_name="Ethnicity")
        self.assertEqual(
            context.exception.errors,
            self.mixin.errors,
        )

    def test__update_ethnicity(self):
        self.mixin.ethnicity = self.mixin.patient.ethnicity
        self.mixin.update_ethnicity()
        self.assertEqual(self.mixin.ethnicity, self.patient.ethnicity)
        self.assertEqual(self.mixin.ethnicity.value, self.mixin.ethnicity__value)

    def test__update_with_uuid(self):
        self.mixin.ethnicity = self.ethnicity.pk
        new_patient = create_psp()
        new_patient.ethnicity.delete()
        self.mixin.patient = new_patient
        self.mixin.update_ethnicity()
        self.assertEqual(self.mixin.ethnicity, self.ethnicity)
        self.assertEqual(self.mixin.ethnicity.value, self.mixin.ethnicity__value)

    def test__check_for_ethnicity_update_errors_without_ethnicity(self):
        self.mixin.ethnicity = None
        self.mixin.check_for_ethnicity_update_errors()
        self.assertEqual(
            self.mixin.errors,
            [("ethnicity", "Ethnicity is required to update an Ethnicity instance.")],
        )

    def test__check_for_ethnicity_update_errors_without_ethnicity_value(self):
        self.mixin.ethnicity__value = None
        self.mixin.check_for_ethnicity_update_errors()
        self.assertEqual(
            self.mixin.errors,
            [("ethnicity__value", "Ethnicitys is required to update an Ethnicity instance.")],
        )

    def test__check_for_ethnicity_update_errors_with_ethnicity_user_not_patient(self):
        new_patient = create_psp()
        self.mixin.ethnicity = new_patient.ethnicity
        self.mixin.check_for_ethnicity_update_errors()
        self.assertEqual(
            self.mixin.errors,
            [("ethnicity", f"{new_patient.ethnicity} has a user who is not the {self.patient}.")],
        )

    def test__ethnicity_has_user_who_is_not_patient(self):
        self.assertFalse(self.mixin.ethnicity_has_user_who_is_not_patient)
        new_patient = create_psp()
        self.mixin.ethnicity = new_patient.ethnicity
        self.assertTrue(self.mixin.ethnicity_has_user_who_is_not_patient)

    def test__ethnicity_needs_save(self):
        self.mixin.ethnicity = self.patient.ethnicity
        self.assertTrue(self.mixin.ethnicity_needs_save)
        self.mixin.ethnicity.value = self.mixin.ethnicity__value
        self.assertFalse(self.mixin.ethnicity_needs_save)

    def test__update_ethnicity_instance(self):
        self.mixin.patient.ethnicity.delete()
        self.mixin.ethnicity__value = Ethnicitys.PACIFICISLANDER
        self.mixin.update_ethnicity_instance()
        self.assertEqual(self.ethnicity.value, Ethnicitys.PACIFICISLANDER)
        self.assertEqual(self.ethnicity.user, self.mixin.patient)
