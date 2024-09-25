import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...users.choices import Roles
from ...users.tests.factories import UserFactory, create_psp
from ...utils.exceptions import GoutHelperValidationError
from ..api.services import PseudopatientProfileAPI

pytestmark = pytest.mark.django_db


class TestPseudopatientProfileAPI(TestCase):
    def setUp(self):
        self.patient = create_psp()
        self.pseudopatientprofile = self.patient.pseudopatientprofile
        self.provider = UserFactory()
        self.patient_without_profile = UserFactory(role=Roles.PSEUDOPATIENT)

        self.create_mixin = PseudopatientProfileAPI(
            patient=self.patient_without_profile,
            provider=self.provider,
        )
        self.update_mixin = PseudopatientProfileAPI(
            pseudopatientprofile=self.pseudopatientprofile,
            provider=None,
        )

    def test__init__(self):
        self.assertEqual(self.create_mixin.patient, self.patient_without_profile)
        self.assertEqual(self.create_mixin.provider, self.provider)
        self.assertEqual(self.update_mixin.pseudopatientprofile, self.pseudopatientprofile)
        self.assertIsNone(self.update_mixin.provider)

    def test__get_queryset(self):
        self.update_mixin.pseudopatientprofile = self.pseudopatientprofile.pk
        self.assertEqual(self.update_mixin.get_queryset().get(), self.pseudopatientprofile)

    def test__get_queryset_raises_error(self):
        with self.assertRaises(TypeError) as context:
            self.update_mixin.pseudopatientprofile = self.pseudopatientprofile
            self.update_mixin.get_queryset()
        self.assertEqual(context.exception.args, ("pseudopatientprofile arg must be a UUID to call get_queryset().",))

    def test__set_attrs_from_qs(self):
        self.update_mixin.pseudopatientprofile = self.pseudopatientprofile.pk
        self.update_mixin.set_attrs_from_qs()
        self.assertEqual(self.update_mixin.pseudopatientprofile, self.pseudopatientprofile)
        self.assertEqual(self.update_mixin.patient, self.patient)
        self.assertEqual(self.update_mixin.provider, self.pseudopatientprofile.provider)

    def test__create_pseudopatientprofile(self):
        # Delete patient's profile and set to the create_mixin attr, as this patient has a dateofbirth and gender,
        # which are required to create a PseudopatientProfile instance.
        self.pseudopatientprofile.delete()
        self.patient.refresh_from_db()
        self.create_mixin.patient = self.patient
        new_profile = self.create_mixin.create_pseudopatientprofile()
        self.assertIsNotNone(self.create_mixin.pseudopatientprofile)
        self.assertEqual(new_profile.user, self.patient)
        self.assertEqual(new_profile.provider, self.provider)
        self.assertTrue(new_profile.provider_alias)

    def test__create_pseudopatientprofile_raises_error(self):
        with self.assertRaises(GoutHelperValidationError) as context:
            self.update_mixin.create_pseudopatientprofile()
        errors_keys = [error[0] for error in context.exception.errors]
        self.assertIn("patient", errors_keys)
        self.assertIn(
            ("patient", "Patient is required to create a PseudopatientProfile instance."),
            context.exception.errors,
        )

    def test__check_for_pseudopatientprofile_create_errors_with_profile(self):
        self.create_mixin.patient = None
        self.create_mixin.pseudopatientprofile = self.pseudopatientprofile
        self.create_mixin.check_for_pseudopatientprofile_create_errors()
        self.assertIn(
            ("pseudopatientprofile", f"{self.pseudopatientprofile} already exists."),
            self.create_mixin.errors,
        )

    def test__check_for_pseudopatientprofile_create_errors_with_patient_with_profile(self):
        self.create_mixin.pseudopatientprofile = None
        self.create_mixin.patient = self.update_mixin.pseudopatientprofile.user
        self.create_mixin.check_for_pseudopatientprofile_create_errors()
        self.assertIn(
            ("patient", f"{self.update_mixin.pseudopatientprofile.user} already has a pseudopatient profile."),
            self.create_mixin.errors,
        )

    def test__check_for_and_raise_errors(self):
        self.create_mixin.patient = self.update_mixin.pseudopatientprofile.user
        with self.assertRaises(GoutHelperValidationError) as context:
            self.create_mixin.create_pseudopatientprofile()
            self.create_mixin.check_for_and_raise_errors()
        self.assertIn(
            ("patient", f"{self.create_mixin.patient} already has a pseudopatient profile."),
            context.exception.errors,
        )

    def test__update_pseudopatientprofile(self):
        self.update_mixin.provider = self.provider
        self.update_mixin.update_pseudopatientprofile()
        self.assertEqual(self.update_mixin.pseudopatientprofile.provider, self.provider)

    def test__update_pseudopatientprofile_raises_error(self):
        with self.assertRaises(GoutHelperValidationError) as context:
            self.create_mixin.update_pseudopatientprofile()
        self.assertIn(
            ("pseudopatientprofile", "No PseudopatientProfile to update."),
            context.exception.errors,
        )

    def test__check_for_pseudopatientprofile_update_errors(self):
        self.update_mixin.pseudopatientprofile = None
        self.update_mixin.check_for_pseudopatientprofile_update_errors()
        self.assertIn(
            ("pseudopatientprofile", "No PseudopatientProfile to update."),
            self.update_mixin.errors,
        )

    def test__patient_has_pseudopatientprofile(self):
        self.assertFalse(self.create_mixin.patient_has_pseudopatientprofile)

    def test__pseudopatientprofile_needs_save(self):
        self.update_mixin.provider = self.provider
        self.assertTrue(self.update_mixin.pseudopatientprofile_needs_save)

    def test__update_pseudopatientprofile_instance(self):
        self.update_mixin.provider = self.provider
        self.update_mixin.update_pseudopatientprofile_instance()
        self.assertEqual(self.update_mixin.pseudopatientprofile.provider, self.provider)
