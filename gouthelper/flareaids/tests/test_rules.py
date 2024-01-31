import pytest
import rules
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from ...users.choices import Roles
from ...users.tests.factories import UserFactory, create_psp
from .factories import create_flareaid

pytestmark = pytest.mark.django_db


class TestCanChangeFlareAid(TestCase):
    def setUp(self):
        self.provider = UserFactory(role=Roles.PROVIDER)
        self.provider_psp = create_psp(provider=self.provider)
        self.provider_psp_flareaid = create_flareaid(user=self.provider_psp)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.admin_psp = create_psp(provider=self.admin)
        self.admin_psp_flareaid = create_flareaid(user=self.admin_psp)
        self.anon = AnonymousUser()
        self.anon_flareaid = create_flareaid()

    def test__change_anonymous_object(self):
        """Test that any user can change an anonymous object."""
        assert rules.test_rule("can_change_object", self.anon, self.anon_flareaid)
        assert rules.test_rule("can_change_object", self.provider, self.anon_flareaid)
        assert rules.test_rule("can_change_object", self.admin, self.anon_flareaid)

    def test__change_provider_object(self):
        """Test that only the provider can change an object for his or
        her self."""
        assert rules.test_rule("can_change_object", self.provider, self.provider_psp_flareaid)
        assert not rules.test_rule("can_change_object", self.admin, self.provider_psp_flareaid)
        assert not rules.test_rule("can_change_object", self.anon, self.provider_psp_flareaid)

    def test__change_admin_object(self):
        """Test that only an admin can change an object for another user."""
        assert rules.test_rule("can_change_object", self.admin, self.admin_psp_flareaid)
        assert not rules.test_rule("can_change_object", self.provider, self.admin_psp_flareaid)
        assert not rules.test_rule("can_change_object", self.anon, self.admin_psp_flareaid)


class TestCanDeleteFlareAid(TestCase):
    def setUp(self):
        self.provider = UserFactory(role=Roles.PROVIDER)
        self.provider_psp = create_psp(provider=self.provider)
        self.provider_psp_flareaid = create_flareaid(user=self.provider_psp)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.admin_psp = create_psp(provider=self.admin)
        self.admin_psp_flareaid = create_flareaid(user=self.admin_psp)
        self.anon = AnonymousUser()
        self.anon_flareaid = create_flareaid()

    def test__delete_anonymous_object(self):
        """Test that no one can delete an anonymous object."""
        assert not rules.test_rule("can_delete_object", self.anon, self.anon_flareaid)
        assert not rules.test_rule("can_delete_object", self.provider, self.anon_flareaid)
        assert not rules.test_rule("can_delete_object", self.admin, self.anon_flareaid)

    def test__delete_provider_object(self):
        """Test that only the provider can delete an object for his or
        her self."""
        assert rules.test_rule("can_delete_object", self.provider, self.provider_psp_flareaid)
        assert not rules.test_rule("can_delete_object", self.admin, self.provider_psp_flareaid)
        assert not rules.test_rule("can_delete_object", self.anon, self.provider_psp_flareaid)

    def test__delete_admin_object(self):
        """Test that only an admin can delete an object for another user."""
        assert rules.test_rule("can_delete_object", self.admin, self.admin_psp_flareaid)
        assert not rules.test_rule("can_delete_object", self.provider, self.admin_psp_flareaid)
        assert not rules.test_rule("can_delete_object", self.anon, self.admin_psp_flareaid)


class TestCanViewFlareAid(TestCase):
    def setUp(self):
        self.provider = UserFactory(role=Roles.PROVIDER)
        self.provider_psp = create_psp(provider=self.provider)
        self.provider_psp_flareaid = create_flareaid(user=self.provider_psp)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.admin_psp = create_psp(provider=self.admin)
        self.admin_psp_flareaid = create_flareaid(user=self.admin_psp)
        self.anon = AnonymousUser()
        self.anon_flareaid = create_flareaid()

    def test__view_anonymous_object(self):
        """Test that any user can view an anonymous object."""
        assert rules.test_rule("can_view_object", self.anon, self.anon_flareaid)
        assert rules.test_rule("can_view_object", self.provider, self.anon_flareaid)
        assert rules.test_rule("can_view_object", self.admin, self.anon_flareaid)

    def test__view_provider_object(self):
        """Test that only the provider can view an object for his or
        her self."""
        assert rules.test_rule("can_view_object", self.provider, self.provider_psp_flareaid)
        assert not rules.test_rule("can_view_object", self.admin, self.provider_psp_flareaid)
        assert not rules.test_rule("can_view_object", self.anon, self.provider_psp_flareaid)

    def test__view_admin_object(self):
        """Test that only an admin can view an object for another user."""
        assert rules.test_rule("can_view_object", self.admin, self.admin_psp_flareaid)
        assert not rules.test_rule("can_view_object", self.provider, self.admin_psp_flareaid)
        assert not rules.test_rule("can_view_object", self.anon, self.admin_psp_flareaid)
