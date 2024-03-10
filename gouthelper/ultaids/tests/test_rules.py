import pytest  # pylint: disable=E0401, E0013, E0015  # type: ignore
import rules
from django.contrib.auth.models import AnonymousUser  # pylint: disable=E0401  # type: ignore
from django.test import TestCase  # pylint: disable=E0401  # type: ignore

from ...users.choices import Roles
from ...users.tests.factories import UserFactory, create_psp
from .factories import create_ultaid

pytestmark = pytest.mark.django_db


class TestCanChangeUltAid(TestCase):
    def setUp(self):
        self.provider = UserFactory(role=Roles.PROVIDER)
        self.provider_pseudopatient = create_psp(provider=self.provider)
        self.provider_ultaid = create_ultaid(user=self.provider_pseudopatient)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.admin_pseudopatient = create_psp(provider=self.admin)
        self.admin_ultaid = create_ultaid(user=self.admin_pseudopatient)
        self.anon = AnonymousUser()
        self.anon_ultaid = create_ultaid()

    def test__change_anonymous_object(self):
        """Test that any user can change an anonymous object."""
        assert rules.test_rule("can_change_object", self.anon, self.anon_ultaid)
        assert rules.test_rule("can_change_object", self.provider, self.anon_ultaid)
        assert rules.test_rule("can_change_object", self.admin, self.anon_ultaid)

    def test__change_provider_object(self):
        """Test that only the provider can change an object for his or
        her self."""
        assert rules.test_rule("can_change_object", self.provider, self.provider_ultaid)
        assert not rules.test_rule("can_change_object", self.admin, self.provider_ultaid)
        assert not rules.test_rule("can_change_object", self.anon, self.provider_ultaid)

    def test__change_admin_object(self):
        """Test that only an admin can change an object for another user."""
        assert rules.test_rule("can_change_object", self.admin, self.admin_ultaid)
        assert not rules.test_rule("can_change_object", self.provider, self.admin_ultaid)
        assert not rules.test_rule("can_change_object", self.anon, self.admin_ultaid)


class TestCanDeleteUltAid(TestCase):
    def setUp(self):
        self.provider = UserFactory(role=Roles.PROVIDER)
        self.provider_pseudopatient = create_psp()
        self.provider_pseudopatient.profile.provider = self.provider
        self.provider_pseudopatient.profile.save()
        self.provider_ultaid = create_ultaid(user=self.provider_pseudopatient)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.admin_pseudopatient = create_psp()
        self.admin_pseudopatient.profile.provider = self.admin
        self.admin_pseudopatient.profile.save()
        self.admin_ultaid = create_ultaid(user=self.admin_pseudopatient)
        self.anon = AnonymousUser()
        self.anon_ultaid = create_ultaid()

    def test__delete_anonymous_object(self):
        """Test that no one can delete an anonymous object."""
        assert not rules.test_rule("can_delete_object", self.anon, self.anon_ultaid)
        assert not rules.test_rule("can_delete_object", self.provider, self.anon_ultaid)
        assert not rules.test_rule("can_delete_object", self.admin, self.anon_ultaid)

    def test__delete_provider_object(self):
        """Test that only the provider can delete an object for his or
        her self."""
        assert rules.test_rule("can_delete_object", self.provider, self.provider_ultaid)
        assert not rules.test_rule("can_delete_object", self.admin, self.provider_ultaid)
        assert not rules.test_rule("can_delete_object", self.anon, self.provider_ultaid)

    def test__delete_admin_object(self):
        """Test that only an admin can delete an object for another user."""
        assert rules.test_rule("can_delete_object", self.admin, self.admin_ultaid)
        assert not rules.test_rule("can_delete_object", self.provider, self.admin_ultaid)
        assert not rules.test_rule("can_delete_object", self.anon, self.admin_ultaid)


class TestCanViewUltAid(TestCase):
    def setUp(self):
        self.provider = UserFactory(role=Roles.PROVIDER)
        self.provider_pseudopatient = create_psp()
        self.provider_pseudopatient.profile.provider = self.provider
        self.provider_pseudopatient.profile.save()
        self.provider_ultaid = create_ultaid(user=self.provider_pseudopatient)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.admin_pseudopatient = create_psp()
        self.admin_pseudopatient.profile.provider = self.admin
        self.admin_pseudopatient.profile.save()
        self.admin_ultaid = create_ultaid(user=self.admin_pseudopatient)
        self.anon = AnonymousUser()
        self.anon_ultaid = create_ultaid()

    def test__view_anonymous_object(self):
        """Test that any user can view an anonymous object."""
        assert rules.test_rule("can_view_object", self.anon, self.anon_ultaid)
        assert rules.test_rule("can_view_object", self.provider, self.anon_ultaid)
        assert rules.test_rule("can_view_object", self.admin, self.anon_ultaid)

    def test__view_provider_object(self):
        """Test that only the provider can view an object for his or
        her self."""
        assert rules.test_rule("can_view_object", self.provider, self.provider_ultaid)
        assert not rules.test_rule("can_view_object", self.admin, self.provider_ultaid)
        assert not rules.test_rule("can_view_object", self.anon, self.provider_ultaid)

    def test__view_admin_object(self):
        """Test that only an admin can view an object for another user."""
        assert rules.test_rule("can_view_object", self.admin, self.admin_ultaid)
        assert not rules.test_rule("can_view_object", self.provider, self.admin_ultaid)
        assert not rules.test_rule("can_view_object", self.anon, self.admin_ultaid)
