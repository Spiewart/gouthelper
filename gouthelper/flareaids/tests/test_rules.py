import pytest
import rules
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from ...users.choices import Roles
from ...users.tests.factories import UserFactory
from .factories import FlareAidFactory, FlareAidUserFactory

pytestmark = pytest.mark.django_db


class TestCanChangeFlareAid(TestCase):
    def setUp(self):
        self.provider = UserFactory(role=Roles.PROVIDER)
        self.provider_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)
        self.provider_pseudopatient.profile.provider = self.provider
        self.provider_pseudopatient.profile.save()
        self.provider_flareaid = FlareAidUserFactory(user=self.provider_pseudopatient)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.admin_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)
        self.admin_pseudopatient.profile.provider = self.admin
        self.admin_pseudopatient.profile.save()
        self.admin_flareaid = FlareAidUserFactory(user=self.admin_pseudopatient)
        self.anon = AnonymousUser()
        self.anon_flareaid = FlareAidFactory()

    def test__change_anonymous_object(self):
        """Test that any user can change an anonymous object."""
        assert rules.test_rule("can_change_object", self.anon, self.anon_flareaid)
        assert rules.test_rule("can_change_object", self.provider, self.anon_flareaid)
        assert rules.test_rule("can_change_object", self.admin, self.anon_flareaid)

    def test__change_provider_object(self):
        """Test that only the provider can change an object for his or
        her self."""
        assert rules.test_rule("can_change_object", self.provider, self.provider_flareaid)
        assert not rules.test_rule("can_change_object", self.admin, self.provider_flareaid)
        assert not rules.test_rule("can_change_object", self.anon, self.provider_flareaid)

    def test__change_admin_object(self):
        """Test that only an admin can change an object for another user."""
        assert rules.test_rule("can_change_object", self.admin, self.admin_flareaid)
        assert not rules.test_rule("can_change_object", self.provider, self.admin_flareaid)
        assert not rules.test_rule("can_change_object", self.anon, self.admin_flareaid)


class TestCanDeleteFlareAid(TestCase):
    def setUp(self):
        self.provider = UserFactory(role=Roles.PROVIDER)
        self.provider_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)
        self.provider_pseudopatient.profile.provider = self.provider
        self.provider_pseudopatient.profile.save()
        self.provider_flareaid = FlareAidUserFactory(user=self.provider_pseudopatient)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.admin_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)
        self.admin_pseudopatient.profile.provider = self.admin
        self.admin_pseudopatient.profile.save()
        self.admin_flareaid = FlareAidUserFactory(user=self.admin_pseudopatient)
        self.anon = AnonymousUser()
        self.anon_flareaid = FlareAidFactory()

    def test__delete_anonymous_object(self):
        """Test that no one can delete an anonymous object."""
        assert not rules.test_rule("can_delete_object", self.anon, self.anon_flareaid)
        assert not rules.test_rule("can_delete_object", self.provider, self.anon_flareaid)
        assert not rules.test_rule("can_delete_object", self.admin, self.anon_flareaid)

    def test__delete_provider_object(self):
        """Test that only the provider can delete an object for his or
        her self."""
        assert rules.test_rule("can_delete_object", self.provider, self.provider_flareaid)
        assert not rules.test_rule("can_delete_object", self.admin, self.provider_flareaid)
        assert not rules.test_rule("can_delete_object", self.anon, self.provider_flareaid)

    def test__delete_admin_object(self):
        """Test that only an admin can delete an object for another user."""
        assert rules.test_rule("can_delete_object", self.admin, self.admin_flareaid)
        assert not rules.test_rule("can_delete_object", self.provider, self.admin_flareaid)
        assert not rules.test_rule("can_delete_object", self.anon, self.admin_flareaid)


class TestCanViewFlareAid(TestCase):
    def setUp(self):
        self.provider = UserFactory(role=Roles.PROVIDER)
        self.provider_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)
        self.provider_pseudopatient.profile.provider = self.provider
        self.provider_pseudopatient.profile.save()
        self.provider_flareaid = FlareAidUserFactory(user=self.provider_pseudopatient)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.admin_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)
        self.admin_pseudopatient.profile.provider = self.admin
        self.admin_pseudopatient.profile.save()
        self.admin_flareaid = FlareAidUserFactory(user=self.admin_pseudopatient)
        self.anon = AnonymousUser()
        self.anon_flareaid = FlareAidFactory()

    def test__view_anonymous_object(self):
        """Test that any user can view an anonymous object."""
        assert rules.test_rule("can_view_object", self.anon, self.anon_flareaid)
        assert rules.test_rule("can_view_object", self.provider, self.anon_flareaid)
        assert rules.test_rule("can_view_object", self.admin, self.anon_flareaid)

    def test__view_provider_object(self):
        """Test that only the provider can view an object for his or
        her self."""
        assert rules.test_rule("can_view_object", self.provider, self.provider_flareaid)
        assert not rules.test_rule("can_view_object", self.admin, self.provider_flareaid)
        assert not rules.test_rule("can_view_object", self.anon, self.provider_flareaid)

    def test__view_admin_object(self):
        """Test that only an admin can view an object for another user."""
        assert rules.test_rule("can_view_object", self.admin, self.admin_flareaid)
        assert not rules.test_rule("can_view_object", self.provider, self.admin_flareaid)
        assert not rules.test_rule("can_view_object", self.anon, self.admin_flareaid)
