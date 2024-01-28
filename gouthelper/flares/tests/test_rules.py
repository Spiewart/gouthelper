import pytest
import rules
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from ...users.choices import Roles
from ...users.tests.factories import PseudopatientFactory, UserFactory
from .factories import FlareFactory, FlareUserFactory

pytestmark = pytest.mark.django_db


class TestCanChangeFlare(TestCase):
    def setUp(self):
        self.provider = UserFactory(role=Roles.PROVIDER)
        self.provider_pseudopatient = PseudopatientFactory()
        self.provider_pseudopatient.profile.provider = self.provider
        self.provider_pseudopatient.profile.save()
        self.provider_flare = FlareUserFactory(user=self.provider_pseudopatient)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.admin_pseudopatient = PseudopatientFactory()
        self.admin_pseudopatient.profile.provider = self.admin
        self.admin_pseudopatient.profile.save()
        self.admin_flare = FlareUserFactory(user=self.admin_pseudopatient)
        self.anon = AnonymousUser()
        self.anon_flare = FlareFactory()

    def test__change_anonymous_object(self):
        """Test that any user can change an anonymous object."""
        assert rules.test_rule("can_change_object", self.anon, self.anon_flare)
        assert rules.test_rule("can_change_object", self.provider, self.anon_flare)
        assert rules.test_rule("can_change_object", self.admin, self.anon_flare)

    def test__change_provider_object(self):
        """Test that only the provider can change an object for his or
        her Pseudopatients."""
        assert rules.test_rule("can_change_object", self.provider, self.provider_flare)
        assert not rules.test_rule("can_change_object", self.admin, self.provider_flare)
        assert not rules.test_rule("can_change_object", self.anon, self.provider_flare)

    def test__change_admin_object(self):
        """Test that only an admin can change an object for another user."""
        assert rules.test_rule("can_change_object", self.admin, self.admin_flare)
        assert not rules.test_rule("can_change_object", self.provider, self.admin_flare)
        assert not rules.test_rule("can_change_object", self.anon, self.admin_flare)


class TestCanCreateFlare(TestCase):
    """Test rules for creating a Flare for a Pseudopatient."""

    def setUp(self):
        self.provider = UserFactory(role=Roles.PROVIDER)
        self.provider_pseudopatient = PseudopatientFactory(provider=self.provider)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.admin_pseudopatient = PseudopatientFactory(provider=self.admin)
        self.anon_psp = PseudopatientFactory()
        self.anon = AnonymousUser()

    def test__create_anonymous_object(self):
        """Test that any user can create an anonymous object."""
        assert rules.test_rule("can_add_pseudopatient_flare", self.anon, self.anon_psp)
        assert rules.test_rule("can_add_pseudopatient_flare", self.provider, self.anon_psp)
        assert rules.test_rule("can_add_pseudopatient_flare", self.admin, self.anon_psp)

    def test__create_provider_object(self):
        """Test that only the provider can create an object for his or
        her pseudopatients."""
        assert rules.test_rule("can_add_pseudopatient_flare", self.provider, self.provider_pseudopatient)
        assert not rules.test_rule("can_add_pseudopatient_flare", self.admin, self.provider_pseudopatient)
        assert not rules.test_rule("can_add_pseudopatient_flare", self.anon, self.provider_pseudopatient)

    def test__create_admin_object(self):
        """Test that only an admin can create an object for another user."""
        assert rules.test_rule("can_add_pseudopatient_flare", self.admin, self.admin_pseudopatient)
        assert not rules.test_rule("can_add_pseudopatient_flare", self.provider, self.admin_pseudopatient)
        assert not rules.test_rule("can_add_pseudopatient_flare", self.anon, self.admin_pseudopatient)


class TestCanDeleteFlare(TestCase):
    def setUp(self):
        self.provider = UserFactory(role=Roles.PROVIDER)
        self.provider_pseudopatient = PseudopatientFactory()
        self.provider_pseudopatient.profile.provider = self.provider
        self.provider_pseudopatient.profile.save()
        self.provider_flare = FlareUserFactory(user=self.provider_pseudopatient)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.admin_pseudopatient = PseudopatientFactory()
        self.admin_pseudopatient.profile.provider = self.admin
        self.admin_pseudopatient.profile.save()
        self.admin_flare = FlareUserFactory(user=self.admin_pseudopatient)
        self.anon = AnonymousUser()
        self.anon_flare = FlareFactory()

    def test__delete_anonymous_object(self):
        """Test that no one can delete an anonymous object."""
        assert not rules.test_rule("can_delete_pseudopatient_flare", self.anon, self.anon_flare)
        assert not rules.test_rule("can_delete_pseudopatient_flare", self.provider, self.anon_flare)
        assert not rules.test_rule("can_delete_pseudopatient_flare", self.admin, self.anon_flare)

    def test__delete_provider_object(self):
        """Test that only the provider can delete an object for his or
        her own Pseudopatients."""
        assert rules.test_rule("can_delete_pseudopatient_flare", self.provider, self.provider_flare)
        assert not rules.test_rule("can_delete_pseudopatient_flare", self.admin, self.provider_flare)
        assert not rules.test_rule("can_delete_pseudopatient_flare", self.anon, self.provider_flare)

    def test__delete_admin_object(self):
        """Test that only an admin can delete an object for another user."""
        assert rules.test_rule("can_delete_pseudopatient_flare", self.admin, self.admin_flare)
        assert not rules.test_rule("can_delete_pseudopatient_flare", self.provider, self.admin_flare)
        assert not rules.test_rule("can_delete_pseudopatient_flare", self.anon, self.admin_flare)


class TestCanViewFlare(TestCase):
    def setUp(self):
        self.provider = UserFactory(role=Roles.PROVIDER)
        self.provider_pseudopatient = PseudopatientFactory()
        self.provider_pseudopatient.profile.provider = self.provider
        self.provider_pseudopatient.profile.save()
        self.provider_flare = FlareUserFactory(user=self.provider_pseudopatient)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.admin_pseudopatient = PseudopatientFactory()
        self.admin_pseudopatient.profile.provider = self.admin
        self.admin_pseudopatient.profile.save()
        self.admin_flare = FlareUserFactory(user=self.admin_pseudopatient)
        self.anon = AnonymousUser()
        self.anon_flare = FlareFactory()

    def test__view_anonymous_object(self):
        """Test that any user can view an anonymous object."""
        assert rules.test_rule("can_view_object", self.anon, self.anon_flare)
        assert rules.test_rule("can_view_object", self.provider, self.anon_flare)
        assert rules.test_rule("can_view_object", self.admin, self.anon_flare)

    def test__view_provider_object(self):
        """Test that only the provider can view an object for his or
        her pseudopatients."""
        assert rules.test_rule("can_view_object", self.provider, self.provider_flare)
        assert not rules.test_rule("can_view_object", self.admin, self.provider_flare)
        assert not rules.test_rule("can_view_object", self.anon, self.provider_flare)

    def test__view_admin_object(self):
        """Test that only an admin can view an object for another user."""
        assert rules.test_rule("can_view_object", self.admin, self.admin_flare)
        assert not rules.test_rule("can_view_object", self.provider, self.admin_flare)
        assert not rules.test_rule("can_view_object", self.anon, self.admin_flare)


class TestCanViewFlareList(TestCase):
    """Test rules for viewing a Pseudopatient's list of Flares."""

    def setUp(self):
        self.provider = UserFactory(role=Roles.PROVIDER)
        self.provider_pseudopatient = PseudopatientFactory(provider=self.provider)
        self.admin = UserFactory(role=Roles.ADMIN)
        self.admin_pseudopatient = PseudopatientFactory(provider=self.admin)
        self.anon_psp = PseudopatientFactory()
        self.anon = AnonymousUser()

    def test__view_anonymous_list(self):
        """Test that any user can view an anonymous list."""
        assert rules.test_rule("can_view_pseudopatient_flare_list", self.anon, self.anon_psp)
        assert rules.test_rule("can_view_pseudopatient_flare_list", self.provider, self.anon_psp)
        assert rules.test_rule("can_view_pseudopatient_flare_list", self.admin, self.anon_psp)

    def test__view_provider_list(self):
        """Test that only the provider can view a list for his or her
        pseudopatients."""
        assert rules.test_rule("can_view_pseudopatient_flare_list", self.provider, self.provider_pseudopatient)
        assert not rules.test_rule("can_view_pseudopatient_flare_list", self.admin, self.provider_pseudopatient)
        assert not rules.test_rule("can_view_pseudopatient_flare_list", self.anon, self.provider_pseudopatient)

    def test__view_admin_list(self):
        """Test that only an admin can view a list for another user."""
        assert rules.test_rule("can_view_pseudopatient_flare_list", self.admin, self.admin_pseudopatient)
        assert not rules.test_rule("can_view_pseudopatient_flare_list", self.provider, self.admin_pseudopatient)
        assert not rules.test_rule("can_view_pseudopatient_flare_list", self.anon, self.admin_pseudopatient)
