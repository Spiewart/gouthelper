import pytest
import rules
from django.test import TestCase

from ...users.choices import Roles
from ...users.tests.factories import UserFactory, create_psp
from .factories import PatientProfileFactory

pytestmark = pytest.mark.django_db


class TestCanViewProfile(TestCase):
    def setUp(self):
        self.provider = UserFactory(role=Roles.PROVIDER)
        self.patient = UserFactory(role=Roles.PATIENT)
        PatientProfileFactory(user=self.patient)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.provider_patient = create_psp()
        self.provider_patient.profile.provider = self.provider
        self.provider_patient.profile.save()
        self.admin_patient = create_psp()
        self.admin_patient.profile.provider = self.admin
        self.admin_patient.profile.save()

    def test__user_provider(self):
        assert rules.test_rule("can_view_profile", self.provider, self.provider.profile)
        assert rules.test_rule("can_view_profile", self.provider, self.provider_patient.profile)
        assert not rules.test_rule("can_view_profile", self.provider, self.patient.profile)
        assert not rules.test_rule("can_view_profile", self.provider, self.admin.profile)
        assert not rules.test_rule("can_view_profile", self.provider, self.admin_patient.profile)

    def test__user_admin(self):
        assert not rules.test_rule("can_view_profile", self.admin, self.provider.profile)
        assert not rules.test_rule("can_view_profile", self.admin, self.provider_patient.profile)
        assert not rules.test_rule("can_view_profile", self.admin, self.patient.profile)
        assert rules.test_rule("can_view_profile", self.admin, self.admin.profile)
        assert rules.test_rule("can_view_profile", self.admin, self.admin_patient.profile)

    def test__user_patient(self):
        assert not rules.test_rule("can_view_profile", self.patient, self.provider.profile)
        assert not rules.test_rule("can_view_profile", self.patient, self.provider_patient.profile)
        assert rules.test_rule("can_view_profile", self.patient, self.patient.profile)
        assert not rules.test_rule("can_view_profile", self.patient, self.admin.profile)
        assert not rules.test_rule("can_view_profile", self.patient, self.admin_patient.profile)
