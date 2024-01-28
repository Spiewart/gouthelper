import pytest
import rules
from django.test import TestCase

from ...users.choices import Roles
from ...users.tests.factories import UserFactory, create_psp

pytestmark = pytest.mark.django_db


class TestCanViewProfile(TestCase):
    def setUp(self):
        self.provider = UserFactory(role=Roles.PROVIDER)
        self.patient = UserFactory(role=Roles.PATIENT)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.provider_pseudopatient = create_psp()
        self.provider_pseudopatient.profile.provider = self.provider
        self.provider_pseudopatient.profile.save()
        self.admin_pseudopatient = create_psp()
        self.admin_pseudopatient.profile.provider = self.admin
        self.admin_pseudopatient.profile.save()

    def test__user_provider(self):
        assert rules.test_rule("can_view_profile", self.provider, self.provider.profile)
        assert rules.test_rule("can_view_profile", self.provider, self.provider_pseudopatient.profile)
        assert not rules.test_rule("can_view_profile", self.provider, self.patient.profile)
        assert not rules.test_rule("can_view_profile", self.provider, self.admin.profile)
        assert not rules.test_rule("can_view_profile", self.provider, self.admin_pseudopatient.profile)

    def test__user_admin(self):
        assert not rules.test_rule("can_view_profile", self.admin, self.provider.profile)
        assert not rules.test_rule("can_view_profile", self.admin, self.provider_pseudopatient.profile)
        assert not rules.test_rule("can_view_profile", self.admin, self.patient.profile)
        assert rules.test_rule("can_view_profile", self.admin, self.admin.profile)
        assert rules.test_rule("can_view_profile", self.admin, self.admin_pseudopatient.profile)

    def test__user_patient(self):
        assert not rules.test_rule("can_view_profile", self.patient, self.provider.profile)
        assert not rules.test_rule("can_view_profile", self.patient, self.provider_pseudopatient.profile)
        assert rules.test_rule("can_view_profile", self.patient, self.patient.profile)
        assert not rules.test_rule("can_view_profile", self.patient, self.admin.profile)
        assert not rules.test_rule("can_view_profile", self.patient, self.admin_pseudopatient.profile)
