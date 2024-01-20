import pytest
import rules
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from ...users.choices import Roles
from ...users.tests.factories import PseudopatientFactory, UserFactory
from .factories import GoalUrateFactory, GoalUrateUserFactory

pytestmark = pytest.mark.django_db


class TestGoalUrateRules(TestCase):
    def setUp(self):
        self.provider = UserFactory()
        self.admin = UserFactory(role=Roles.ADMIN)
        self.anon = AnonymousUser()
        self.prov_psp = PseudopatientFactory(provider=self.provider)
        self.admin_psp = PseudopatientFactory(provider=self.admin)
        self.anon_psp = PseudopatientFactory()
        self.prov_psp_gu = GoalUrateUserFactory(user=self.prov_psp)
        self.admin_psp_gu = GoalUrateUserFactory(user=self.admin_psp)
        self.anon_psp_gu = GoalUrateUserFactory(user=self.anon_psp)
        self.anon_gu = GoalUrateFactory()

    def test__add_object(self):
        """Test that a Provider or Admin can add GoalUrates for Pseudopatient's for whom they are the provider
        and that anyone can add an anonymous Pseudopatient's GoalUrate or an anonymous GoalUrate."""
        assert rules.test_rule("can_add_pseudopatient_goalurate", self.provider, self.prov_psp)
        assert not rules.test_rule("can_add_pseudopatient_goalurate", self.admin, self.prov_psp)
        assert not rules.test_rule("can_add_pseudopatient_goalurate", self.anon, self.prov_psp)
        assert not rules.test_rule("can_add_pseudopatient_goalurate", self.provider, self.admin_psp)
        assert rules.test_rule("can_add_pseudopatient_goalurate", self.admin, self.admin_psp)
        assert not rules.test_rule("can_add_pseudopatient_goalurate", self.anon, self.admin_psp)
        assert rules.test_rule("can_add_pseudopatient_goalurate", self.provider, self.anon_psp)
        assert rules.test_rule("can_add_pseudopatient_goalurate", self.admin, self.anon_psp)
        assert rules.test_rule("can_add_pseudopatient_goalurate", AnonymousUser(), self.anon_psp)
        assert rules.test_rule("can_add_pseudopatient_goalurate", self.provider, None)
        assert rules.test_rule("can_add_pseudopatient_goalurate", self.admin, None)
        assert rules.test_rule("can_add_pseudopatient_goalurate", AnonymousUser(), None)

    def test__view_object(self):
        """Test that a Provider or Admin can view GoalUrates for Pseudopatient's for whom they are the provider
        and that anyone can view an anonymous Pseudopatient's GoalUrate or an anonymous GoalUrate."""
        assert rules.test_rule("can_view_pseudopatient_goalurate", self.provider, self.prov_psp_gu)
        assert not rules.test_rule("can_view_pseudopatient_goalurate", self.admin, self.prov_psp_gu)
        assert not rules.test_rule("can_view_pseudopatient_goalurate", self.anon, self.prov_psp_gu)
        assert not rules.test_rule("can_view_pseudopatient_goalurate", self.provider, self.admin_psp_gu)
        assert rules.test_rule("can_view_pseudopatient_goalurate", self.admin, self.admin_psp_gu)
        assert not rules.test_rule("can_view_pseudopatient_goalurate", self.anon, self.admin_psp_gu)
        assert rules.test_rule("can_view_pseudopatient_goalurate", self.provider, self.anon_psp_gu)
        assert rules.test_rule("can_view_pseudopatient_goalurate", self.admin, self.anon_psp_gu)
        assert rules.test_rule("can_view_pseudopatient_goalurate", AnonymousUser(), self.anon_psp_gu)
        assert rules.test_rule("can_view_pseudopatient_goalurate", self.provider, self.anon_gu)
        assert rules.test_rule("can_view_pseudopatient_goalurate", self.admin, self.anon_gu)
        assert rules.test_rule("can_view_pseudopatient_goalurate", AnonymousUser(), self.anon_gu)

    def test__change_object(self):
        """Test that a Provider or Admin can change GoalUrates for Pseudopatient's for whom they are the provider
        and that anyone can change an anonymous Pseudopatient's GoalUrate or an anonymous GoalUrate."""
        assert rules.test_rule("can_change_pseudopatient_goalurate", self.provider, self.prov_psp_gu)
        assert not rules.test_rule("can_change_pseudopatient_goalurate", self.admin, self.prov_psp_gu)
        assert not rules.test_rule("can_change_pseudopatient_goalurate", self.anon, self.prov_psp_gu)
        assert not rules.test_rule("can_change_pseudopatient_goalurate", self.provider, self.admin_psp_gu)
        assert rules.test_rule("can_change_pseudopatient_goalurate", self.admin, self.admin_psp_gu)
        assert not rules.test_rule("can_change_pseudopatient_goalurate", self.anon, self.admin_psp_gu)
        assert rules.test_rule("can_change_pseudopatient_goalurate", self.provider, self.anon_psp_gu)
        assert rules.test_rule("can_change_pseudopatient_goalurate", self.admin, self.anon_psp_gu)
        assert rules.test_rule("can_change_pseudopatient_goalurate", AnonymousUser(), self.anon_psp_gu)
        assert rules.test_rule("can_change_pseudopatient_goalurate", self.provider, self.anon_gu)
        assert rules.test_rule("can_change_pseudopatient_goalurate", self.admin, self.anon_gu)
        assert rules.test_rule("can_change_pseudopatient_goalurate", AnonymousUser(), self.anon_gu)
