import pytest
import rules
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from ...users.choices import Roles
from ...users.tests.factories import UserFactory, create_psp
from .factories import create_goalurate

pytestmark = pytest.mark.django_db


class TestGoalUrateRules(TestCase):
    def setUp(self):
        self.provider = UserFactory()
        self.admin = UserFactory(role=Roles.ADMIN)
        self.anon = AnonymousUser()
        self.prov_psp = create_psp(provider=self.provider)
        self.admin_psp = create_psp(provider=self.admin)
        self.anon_psp = create_psp()
        self.prov_psp_gu = create_goalurate(user=self.prov_psp)
        self.admin_psp_gu = create_goalurate(user=self.admin_psp)
        self.anon_psp_gu = create_goalurate(user=self.anon_psp)
        self.anon_gu = create_goalurate()

    def test__add_object(self):
        """Test that a Provider or Admin can add GoalUrates for Pseudopatient's for whom they are the provider
        and that anyone can add an anonymous Pseudopatient's GoalUrate or an anonymous GoalUrate."""
        assert rules.test_rule("can_add_goalurate", self.provider, self.prov_psp)
        assert not rules.test_rule("can_add_goalurate", self.admin, self.prov_psp)
        assert not rules.test_rule("can_add_goalurate", self.anon, self.prov_psp)
        assert not rules.test_rule("can_add_goalurate", self.provider, self.admin_psp)
        assert rules.test_rule("can_add_goalurate", self.admin, self.admin_psp)
        assert not rules.test_rule("can_add_goalurate", self.anon, self.admin_psp)
        assert rules.test_rule("can_add_goalurate", self.provider, self.anon_psp)
        assert rules.test_rule("can_add_goalurate", self.admin, self.anon_psp)
        assert rules.test_rule("can_add_goalurate", AnonymousUser(), self.anon_psp)
        assert rules.test_rule("can_add_goalurate", self.provider, None)
        assert rules.test_rule("can_add_goalurate", self.admin, None)
        assert rules.test_rule("can_add_goalurate", AnonymousUser(), None)

    def test__view_object(self):
        """Test that a Provider or Admin can view GoalUrates for Pseudopatient's for whom they are the provider
        and that anyone can view an anonymous Pseudopatient's GoalUrate or an anonymous GoalUrate."""
        assert rules.test_rule("can_view_goalurate", self.provider, self.prov_psp_gu)
        assert not rules.test_rule("can_view_goalurate", self.admin, self.prov_psp_gu)
        assert not rules.test_rule("can_view_goalurate", self.anon, self.prov_psp_gu)
        assert not rules.test_rule("can_view_goalurate", self.provider, self.admin_psp_gu)
        assert rules.test_rule("can_view_goalurate", self.admin, self.admin_psp_gu)
        assert not rules.test_rule("can_view_goalurate", self.anon, self.admin_psp_gu)
        assert rules.test_rule("can_view_goalurate", self.provider, self.anon_psp_gu)
        assert rules.test_rule("can_view_goalurate", self.admin, self.anon_psp_gu)
        assert rules.test_rule("can_view_goalurate", AnonymousUser(), self.anon_psp_gu)
        assert rules.test_rule("can_view_goalurate", self.provider, self.anon_gu)
        assert rules.test_rule("can_view_goalurate", self.admin, self.anon_gu)
        assert rules.test_rule("can_view_goalurate", AnonymousUser(), self.anon_gu)

    def test__change_object(self):
        """Test that a Provider or Admin can change GoalUrates for Pseudopatient's for whom they are the provider
        and that anyone can change an anonymous Pseudopatient's GoalUrate or an anonymous GoalUrate."""
        assert rules.test_rule("can_change_goalurate", self.provider, self.prov_psp_gu)
        assert not rules.test_rule("can_change_goalurate", self.admin, self.prov_psp_gu)
        assert not rules.test_rule("can_change_goalurate", self.anon, self.prov_psp_gu)
        assert not rules.test_rule("can_change_goalurate", self.provider, self.admin_psp_gu)
        assert rules.test_rule("can_change_goalurate", self.admin, self.admin_psp_gu)
        assert not rules.test_rule("can_change_goalurate", self.anon, self.admin_psp_gu)
        assert rules.test_rule("can_change_goalurate", self.provider, self.anon_psp_gu)
        assert rules.test_rule("can_change_goalurate", self.admin, self.anon_psp_gu)
        assert rules.test_rule("can_change_goalurate", AnonymousUser(), self.anon_psp_gu)
        assert rules.test_rule("can_change_goalurate", self.provider, self.anon_gu)
        assert rules.test_rule("can_change_goalurate", self.admin, self.anon_gu)
        assert rules.test_rule("can_change_goalurate", AnonymousUser(), self.anon_gu)
