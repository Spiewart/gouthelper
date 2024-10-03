import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...users.choices import Roles
from ...users.models import Pseudopatient
from ...users.tests.factories import create_psp
from ...utils.exceptions import GoutHelperValidationError
from ..api.services import PseudopatientAPI
from ..services import PseudopatientBaseAPI
from .factories import UserFactory

pytestmark = pytest.mark.django_db


class TestPseudopatientBaseAPI(TestCase):
    def setUp(self):
        self.patient = create_psp()
        self.mixin = PseudopatientBaseAPI(patient=self.patient)
        self.empty_mixin = PseudopatientBaseAPI(patient=None)

    def test__create_pseudopatient(self):
        new_patient = self.empty_mixin.create_pseudopatient()
        self.assertIsNotNone(self.empty_mixin.patient)
        self.assertTrue(isinstance(new_patient, Pseudopatient))
        self.assertEqual(new_patient.role, Roles.PSEUDOPATIENT)

    def test__create_pseudopatient_raises_error(self):
        with self.assertRaises(GoutHelperValidationError) as context:
            self.mixin.create_pseudopatient()
        errors_keys = [error[0] for error in context.exception.errors]
        self.assertIn("patient", errors_keys)
        self.assertEqual(
            context.exception.errors,
            [("patient", f"{self.patient} already exists.")],
        )

    def test__get_queryset(self):
        self.mixin.patient = self.patient.pk
        patient = self.mixin.get_queryset()
        self.assertEqual(patient.first(), self.patient)

    def test__get_queryset_raises_error(self):
        with self.assertRaises(TypeError) as context:
            self.mixin.patient = self.patient
            self.mixin.get_queryset()
        self.assertEqual(context.exception.args, ("patient arg must be a UUID to call get_queryset().",))

    def test__add_errors(self):
        self.empty_mixin.add_errors(api_args=[("patient", "error")])
        self.assertEqual(self.empty_mixin.errors, [("patient", "error")])

    def test__check_for_pseudopatient_create_errors(self):
        self.mixin.check_for_pseudopatient_create_errors()
        self.assertEqual(
            self.mixin.errors,
            [("patient", f"{self.patient} already exists.")],
        )

    def test__check_for_and_raise_errors(self):
        with self.assertRaises(GoutHelperValidationError) as context:
            self.mixin.create_pseudopatient()
            self.mixin.check_for_and_raise_errors(model_name="Pseudopatient")
        self.assertEqual(
            context.exception.errors,
            [("patient", f"{self.mixin.patient} already exists.")],
        )


class TestPseudopatientAPI(TestCase):
    def setUp(self):
        self.patient = create_psp(provider=UserFactory())
        self.mixin = PseudopatientAPI(
            patient=self.patient,
            dateofbirth__value=self.patient.dateofbirth.value,
            ethnicity__value=self.patient.ethnicity.value,
            gender__value=self.patient.gender.value,
            provider=self.patient.provider,
            goutdetail__at_goal=True,
            goutdetail__at_goal_long_term=True,
            goutdetail__flaring=True,
            goutdetail__on_ppx=True,
            goutdetail__on_ult=True,
            goutdetail__starting_ult=True,
        )
        self.empty_mixin = PseudopatientAPI(
            patient=None,
            dateofbirth__value=self.patient.dateofbirth.value,
            ethnicity__value=self.patient.ethnicity.value,
            gender__value=self.patient.gender.value,
            provider=None,
            goutdetail__at_goal=True,
            goutdetail__at_goal_long_term=True,
            goutdetail__flaring=True,
            goutdetail__on_ppx=True,
            goutdetail__on_ult=True,
            goutdetail__starting_ult=True,
        )

    def test__create_pseudopatient_and_profile(self):
        new_patient = self.empty_mixin.create_pseudopatient_and_profile()
        self.assertIsNotNone(self.empty_mixin.patient)
        self.assertTrue(isinstance(new_patient, Pseudopatient))
        self.assertEqual(new_patient.role, Roles.PSEUDOPATIENT)
        self.assertTrue(new_patient.dateofbirth)
        self.assertEqual(new_patient.dateofbirth.value, self.patient.dateofbirth.value)
        self.assertTrue(new_patient.ethnicity)
        self.assertEqual(new_patient.ethnicity.value, self.patient.ethnicity.value)
        self.assertTrue(new_patient.gender)
        self.assertEqual(new_patient.gender.value, self.patient.gender.value)
        self.assertFalse(new_patient.provider)
        del new_patient.gout
        del new_patient.goutdetail
        self.assertTrue(new_patient.goutdetail)
        self.assertTrue(new_patient.goutdetail.at_goal)
        self.assertTrue(new_patient.goutdetail.at_goal_long_term)
        self.assertTrue(new_patient.goutdetail.flaring)
        self.assertTrue(new_patient.goutdetail.on_ppx)
        self.assertTrue(new_patient.goutdetail.on_ult)
        self.assertTrue(new_patient.goutdetail.starting_ult)

    def test__create_pseudopatient_and_profile_raises_patient_error(self):
        with self.assertRaises(GoutHelperValidationError) as context:
            self.mixin.create_pseudopatient_and_profile()
        errors_keys = [error[0] for error in context.exception.errors]
        self.assertIn("patient", errors_keys)
        self.assertEqual(
            context.exception.errors,
            [("patient", f"{self.patient} already exists.")],
        )

    def test__create_pseudopatient_and_profile_raises_dateofbirth_error(self):
        self.empty_mixin.dateofbirth__value = None
        with self.assertRaises(GoutHelperValidationError) as context:
            self.empty_mixin.create_pseudopatient_and_profile()
        errors_keys = [error[0] for error in context.exception.errors]
        self.assertIn("dateofbirth__value", errors_keys)
        self.assertEqual(
            context.exception.errors,
            [("dateofbirth__value", "Date is required to create a DateOfBirth instance.")],
        )

    def test__has_errors(self):
        self.assertFalse(self.empty_mixin.has_errors)
        self.assertFalse(self.mixin.has_errors)
        self.empty_mixin.errors.append(("test", "error"))
        self.assertTrue(self.empty_mixin.has_errors)
        self.mixin.errors.append(("test", "error"))
        self.assertTrue(self.mixin.has_errors)

    def test__check_for_and_raise_errors(self):
        self.empty_mixin.dateofbirth__value = None
        with self.assertRaises(GoutHelperValidationError) as context:
            self.empty_mixin.create_pseudopatient_and_profile()
            self.empty_mixin.check_for_and_raise_errors(model_name="Pseudopatient")
        self.assertEqual(
            context.exception.errors,
            [("dateofbirth__value", "Date is required to create a DateOfBirth instance.")],
        )

    def test__update_pseudopatient_and_profile(self):
        self.mixin.update_pseudopatient_and_profile()
        self.assertTrue(self.mixin.patient.dateofbirth)
        self.assertEqual(self.mixin.patient.dateofbirth.value, self.mixin.dateofbirth__value)
        self.assertTrue(self.mixin.patient.ethnicity)
        self.assertEqual(self.mixin.patient.ethnicity.value, self.mixin.ethnicity__value)
        self.assertTrue(self.mixin.patient.gender)
        self.assertEqual(self.mixin.patient.gender.value, self.mixin.gender__value)
        self.assertTrue(self.mixin.patient.provider)
        self.assertTrue(self.mixin.patient.goutdetail)
        self.assertTrue(self.mixin.patient.goutdetail.at_goal)
        self.assertTrue(self.mixin.patient.goutdetail.at_goal_long_term)
        self.assertTrue(self.mixin.patient.goutdetail.flaring)
        self.assertTrue(self.mixin.patient.goutdetail.on_ppx)
        self.assertTrue(self.mixin.patient.goutdetail.on_ult)
        self.assertTrue(self.mixin.patient.goutdetail.starting_ult)

    def test__update_pseudopatient_and_profile_raises_error(self):
        with self.assertRaises(GoutHelperValidationError) as context:
            self.empty_mixin.update_pseudopatient_and_profile()
        errors_keys = [error[0] for error in context.exception.errors]
        self.assertIn("patient", errors_keys)
        self.assertEqual(context.exception.errors, [("patient", "No Pseudopatient to update.")])
