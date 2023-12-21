import pytest
import rules
from django.test import TestCase

from ..choices import Roles
from .factories import UserFactory

pytestmark = pytest.mark.django_db


class TestCanAddUserWithSpecificProvider(TestCase):
    def setUp(self):
        """Create a User with the Provider role."""
        self.user = UserFactory()
        self.admin = UserFactory(role=Roles.ADMIN)
        self.patient = UserFactory(role=Roles.PATIENT)

    def test__user_provider(self):
        """Test that a User with the Provider role can add a User."""
        assert rules.test_rule("can_add_user_with_specific_provider", self.user, self.user.username)
        assert not rules.test_rule("can_add_user_with_specific_provider", self.user, self.admin.username)

    def test__user_admin(self):
        """Test that a User with the Admin role can add a User."""
        assert rules.test_rule("can_add_user_with_specific_provider", self.admin, self.admin.username)
        assert not rules.test_rule("can_add_user_with_specific_provider", self.admin, self.user.username)


class TestCanAddUserWithProvider:
    def test__user_provider(self):
        """Test that a User with the Provider role can add a User."""
        assert rules.test_rule("can_add_user_with_provider", UserFactory(role=Roles.PROVIDER))

    def test__user_admin(self):
        """Test that a User with the Admin role can add a User."""
        assert rules.test_rule("can_add_user_with_provider", UserFactory(role=Roles.ADMIN))

    def test__user_patient(self):
        """Test that a User with the Patient role cannot add a User."""
        assert not rules.test_rule("can_add_user_with_provider", UserFactory(role=Roles.PATIENT))


class TestCanAddUser:
    def test__user_provider(self):
        """Test that a User with the Provider role can add a User."""
        assert rules.test_rule("can_add_user", UserFactory(role=Roles.PROVIDER))

    def test__user_admin(self):
        """Test that a User with the Admin role can add a User."""
        assert rules.test_rule("can_add_user", UserFactory(role=Roles.ADMIN))

    def test__user_patient(self):
        """Test that a User with the Patient role cannot add a User."""
        assert rules.test_rule("can_add_user", UserFactory(role=Roles.PATIENT))


class TestCanViewProviderList(TestCase):
    def setUp(self):
        """Create a User with the Provider role."""
        self.provider = UserFactory()
        self.admin = UserFactory(role=Roles.ADMIN)
        self.patient = UserFactory(role=Roles.PATIENT)

    def test__provider_can_see_own_list(self):
        """Test that a Provider can see their own list."""
        assert rules.test_rule("can_view_provider_list", self.provider, self.provider.username)

    def test__provider_cannot_see_other_list(self):
        """Test that a Provider cannot see another Provider's list."""
        assert not rules.test_rule("can_view_provider_list", self.provider, self.admin.username)

    def test__admin_can_see_own_list(self):
        """Test that an Admin can see their own list."""
        assert rules.test_rule("can_view_provider_list", self.admin, self.admin.username)

    def test__admin_cannot_see_other_list(self):
        """Test that an Admin cannot see another Admin's list."""
        assert not rules.test_rule("can_view_provider_list", self.admin, self.provider.username)

    def test__patient_cannot_see_either_list(self):
        """Test that a Patient cannot see either Provider's list."""
        assert not rules.test_rule("can_view_provider_list", self.patient, self.provider.username)
        assert not rules.test_rule("can_view_provider_list", self.patient, self.admin.username)
