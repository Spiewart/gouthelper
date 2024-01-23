import pytest
import rules
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from ..users.choices import Roles
from ..users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestCanAddObject(TestCase):
    """Tests for add_object rule when the object is anonymous, i.e.
    is called without a username kwarg."""

    def setUp(self):
        self.provider = UserFactory(role=Roles.PROVIDER)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.anon = AnonymousUser()

    def test__add_anonymous_object(self):
        """Tests that any user can add an anonymous object."""
        assert rules.test_rule("can_add_object", self.anon, None)
        assert rules.test_rule("can_add_object", self.provider, None)
        assert rules.test_rule("can_add_object", self.admin, None)

    def test__add_provider_object(self):
        """Test that no one can create objects for Providers."""
        assert not rules.test_rule("can_add_object", self.provider, self.provider)
        assert not rules.test_rule("can_add_object", self.admin, self.provider.username)
        assert not rules.test_rule("can_add_object", self.anon, self.provider.username)

    def test__add_admin_object(self):
        """Tests that no one can create objects for Admins."""
        assert not rules.test_rule("can_add_object", self.admin, self.admin)
        assert not rules.test_rule("can_add_object", self.provider, self.admin.username)
        assert not rules.test_rule("can_add_object", self.anon, self.admin.username)


class TestCanViewObjectList(TestCase):
    """Tests for view_object_list rule when the object is anonymous, i.e.
    is called without a username kwarg."""

    def setUp(self):
        self.provider = UserFactory(role=Roles.PROVIDER)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.anon = AnonymousUser()

    def test__view_provider_object_list(self):
        """Tests that only the provider can view an object list for his or
        her self."""
        assert rules.test_rule("can_view_object_list", self.provider, self.provider)
        assert not rules.test_rule("can_view_object_list", self.admin, self.provider.username)
        assert not rules.test_rule("can_view_object_list", self.anon, self.provider.username)

    def test__view_admin_object_list(self):
        """Tests that only an admin can view an object list for another user."""
        assert rules.test_rule("can_view_object_list", self.admin, self.admin)
        assert not rules.test_rule("can_view_object_list", self.provider, self.admin.username)
        assert not rules.test_rule("can_view_object_list", self.anon, self.admin.username)
