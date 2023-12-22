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


class TestCanDeleteUser(TestCase):
    def setUp(self):
        """Create a User with the Provider role."""
        self.provider = UserFactory()
        self.provider_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)
        self.provider_pseudopatient.profile.provider = self.provider
        self.provider_pseudopatient.profile.save()
        self.admin = UserFactory(role=Roles.ADMIN)
        self.admin_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)
        self.admin_pseudopatient.profile.provider = self.admin
        self.admin_pseudopatient.profile.save()
        self.patient = UserFactory(role=Roles.PATIENT)
        self.anon_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)

    def test__provider_can_delete_self(self):
        """Test that a User with the Provider role can delete a User."""
        assert rules.test_rule("can_delete_user", self.provider, self.provider)

    def test__provider_can_delete_own_pseudopatient(self):
        """Test that a Provider can delete their own Pseudopatient."""
        assert rules.test_rule("can_delete_user", self.provider, self.provider_pseudopatient)

    def test__provider_cannot_delete_admin(self):
        """Test that a Provider cannot delete an Admin."""
        assert not rules.test_rule("can_delete_user", self.provider, self.admin)

    def test__provider_cannot_delete_admin_pseudopatient(self):
        """Test that a Provider cannot delete an Admin's Pseudopatient."""
        assert not rules.test_rule("can_delete_user", self.provider, self.admin_pseudopatient)

    def test__provider_cannot_delete_patient(self):
        """Test that a Provider cannot delete a Patient."""
        assert not rules.test_rule("can_delete_user", self.provider, self.patient)

    def test__provider_cannot_delete_anonymous_pseudopatient(self):
        """Test that a Provider cannot delete an Anonymous Pseudopatient."""
        assert not rules.test_rule("can_delete_user", self.provider, self.anon_pseudopatient)

    def test__admin_can_delete_self(self):
        """Test that a User with the Admin role can delete a User."""
        assert rules.test_rule("can_delete_user", self.admin, self.admin)

    def test__admin_can_delete_own_pseudopatient(self):
        """Test that an Admin can delete their own Pseudopatient."""
        assert rules.test_rule("can_delete_user", self.admin, self.admin_pseudopatient)

    def test__admin_cannot_delete_provider(self):
        """Test that an Admin cannot delete a Provider."""
        assert not rules.test_rule("can_delete_user", self.admin, self.provider)

    def test__admin_cannot_delete_provider_pseudopatient(self):
        """Test that an Admin cannot delete a Provider's Pseudopatient."""
        assert not rules.test_rule("can_delete_user", self.admin, self.provider_pseudopatient)

    def test__admin_cannot_delete_patient(self):
        """Test that an Admin cannot delete a Patient."""
        assert not rules.test_rule("can_delete_user", self.admin, self.patient)

    def test__admin_cannot_delete_anonymous_pseudopatient(self):
        """Test that an Admin cannot delete an Anonymous Pseudopatient."""
        assert not rules.test_rule("can_delete_user", self.admin, self.anon_pseudopatient)

    def test__patient_can_delete_self(self):
        """Test that a User with the Patient role cannot delete a User."""
        assert rules.test_rule("can_delete_user", self.patient, self.patient)

    def test__patient_cannot_delete_provider(self):
        """Test that a Patient cannot delete a Provider."""
        assert not rules.test_rule("can_delete_user", self.patient, self.provider)

    def test__patient_cannot_delete_provider_pseudopatient(self):
        """Test that a Patient cannot delete a Provider's Pseudopatient."""
        assert not rules.test_rule("can_delete_user", self.patient, self.provider_pseudopatient)

    def test__patient_cannot_delete_admin(self):
        """Test that a Patient cannot delete an Admin."""
        assert not rules.test_rule("can_delete_user", self.patient, self.admin)

    def test__patient_cannot_delete_admin_pseudopatient(self):
        """Test that a Patient cannot delete an Admin's Pseudopatient."""
        assert not rules.test_rule("can_delete_user", self.patient, self.admin_pseudopatient)

    def test__patient_cannot_delete_anonymous_pseudopatient(self):
        """Test that a Patient cannot delete an Anonymous Pseudopatient."""
        assert not rules.test_rule("can_delete_user", self.patient, self.anon_pseudopatient)


class TestCanEditUser(TestCase):
    def setUp(self):
        """Create a User with the Provider role."""
        self.provider = UserFactory()
        self.provider_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)
        self.provider_pseudopatient.profile.provider = self.provider
        self.provider_pseudopatient.profile.save()
        self.admin = UserFactory(role=Roles.ADMIN)
        self.admin_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)
        self.admin_pseudopatient.profile.provider = self.admin
        self.admin_pseudopatient.profile.save()
        self.patient = UserFactory(role=Roles.PATIENT)
        self.anon_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)

    def test__provider_can_edit_self(self):
        """Test that a Provider can edit their own User."""
        assert rules.test_rule("can_edit_user", self.provider, self.provider)

    def test__provider_cannot_edit_pseudopatient(self):
        """Test that a Provider can edit their own Pseudopatient."""
        assert not rules.test_rule("can_edit_user", self.provider, self.provider_pseudopatient)

    def test__provider_cannot_edit_admin(self):
        """Test that a Provider cannot edit an Admin."""
        assert not rules.test_rule("can_edit_user", self.provider, self.admin)

    def test__provider_cannot_edit_admin_pseudopatient(self):
        """Test that a Provider cannot edit an Admin's Pseudopatient."""
        assert not rules.test_rule("can_edit_user", self.provider, self.admin_pseudopatient)

    def test__provider_cannot_edit_patient(self):
        """Test that a Provider cannot edit a Patient."""
        assert not rules.test_rule("can_edit_user", self.provider, self.patient)

    def test__admin_can_edit_self(self):
        """Test that an Admin can edit their own User."""
        assert rules.test_rule("can_edit_user", self.admin, self.admin)

    def test__admin_cannot_edit_pseudopatient(self):
        """Test that an Admin can edit their own Pseudopatient."""
        assert not rules.test_rule("can_edit_user", self.admin, self.admin_pseudopatient)

    def test__admin_cannot_edit_provider(self):
        """Test that an Admin cannot edit a Provider."""
        assert not rules.test_rule("can_edit_user", self.admin, self.provider)

    def test__admin_cannot_edit_provider_pseudopatient(self):
        """Test that an Admin cannot edit a Provider's Pseudopatient."""
        assert not rules.test_rule("can_edit_user", self.admin, self.provider_pseudopatient)

    def test__admin_cannot_edit_patient(self):
        """Test that an Admin cannot edit a Patient."""
        assert not rules.test_rule("can_edit_user", self.admin, self.patient)

    def test__patient_can_edit_self(self):
        """Test that a Patient can edit their own User."""
        assert rules.test_rule("can_edit_user", self.patient, self.patient)

    def test__patient_cannot_edit_provider(self):
        """Test that a Patient cannot edit a Provider."""
        assert not rules.test_rule("can_edit_user", self.patient, self.provider)

    def test__patient_cannot_edit_provider_pseudopatient(self):
        """Test that a Patient cannot edit a Provider's Pseudopatient."""
        assert not rules.test_rule("can_edit_user", self.patient, self.provider_pseudopatient)

    def test__patient_cannot_edit_admin(self):
        """Test that a Patient cannot edit an Admin."""
        assert not rules.test_rule("can_edit_user", self.patient, self.admin)

    def test__patient_cannot_edit_admin_pseudopatient(self):
        """Test that a Patient cannot edit an Admin's Pseudopatient."""
        assert not rules.test_rule("can_edit_user", self.patient, self.admin_pseudopatient)

    def test__no_one_can_edit_anonymous_pseudopatient(self):
        """Test that anyone can edit an Anonymous Pseudopatient."""
        assert not rules.test_rule("can_edit_user", self.patient, self.anon_pseudopatient)
        assert not rules.test_rule("can_edit_user", self.admin, self.anon_pseudopatient)
        assert not rules.test_rule("can_edit_user", self.provider, self.anon_pseudopatient)


class TestCanViewUser(TestCase):
    def setUp(self):
        """Create a User with the Provider role."""
        self.provider = UserFactory()
        self.provider_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)
        self.provider_pseudopatient.profile.provider = self.provider
        self.provider_pseudopatient.profile.save()
        self.admin = UserFactory(role=Roles.ADMIN)
        self.admin_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)
        self.admin_pseudopatient.profile.provider = self.admin
        self.admin_pseudopatient.profile.save()
        self.patient = UserFactory(role=Roles.PATIENT)
        self.anon_pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)

    def test__provider_can_see_self(self):
        """Test that a Provider can see their own User."""
        assert rules.test_rule("can_view_user", self.provider, self.provider)

    def test__provider_can_see_pseudopatient(self):
        """Test that a Provider can see their own Pseudopatient."""
        assert rules.test_rule("can_view_user", self.provider, self.provider_pseudopatient)

    def test__provider_cannot_see_admin(self):
        """Test that a Provider cannot see an Admin."""
        assert not rules.test_rule("can_view_user", self.provider, self.admin)

    def test__provider_cannot_see_admin_pseudopatient(self):
        """Test that a Provider cannot see an Admin's Pseudopatient."""
        assert not rules.test_rule("can_view_user", self.provider, self.admin_pseudopatient)

    def test__provider_cannot_see_patient(self):
        """Test that a Provider cannot see a Patient."""
        assert not rules.test_rule("can_view_user", self.provider, self.patient)

    def test__admin_can_see_self(self):
        """Test that an Admin can see their own User."""
        assert rules.test_rule("can_view_user", self.admin, self.admin)

    def test__admin_can_see_pseudopatient(self):
        """Test that an Admin can see their own Pseudopatient."""
        assert rules.test_rule("can_view_user", self.admin, self.admin_pseudopatient)

    def test__admin_cannot_see_provider(self):
        """Test that an Admin cannot see a Provider."""
        assert not rules.test_rule("can_view_user", self.admin, self.provider)

    def test__admin_cannot_see_provider_pseudopatient(self):
        """Test that an Admin cannot see a Provider's Pseudopatient."""
        assert not rules.test_rule("can_view_user", self.admin, self.provider_pseudopatient)

    def test__admin_cannot_see_patient(self):
        """Test that an Admin cannot see a Patient."""
        assert not rules.test_rule("can_view_user", self.admin, self.patient)

    def test__patient_can_see_self(self):
        """Test that a Patient can see their own User."""
        assert rules.test_rule("can_view_user", self.patient, self.patient)

    def test__patient_cannot_see_provider(self):
        """Test that a Patient cannot see a Provider."""
        assert not rules.test_rule("can_view_user", self.patient, self.provider)

    def test__patient_cannot_see_provider_pseudopatient(self):
        """Test that a Patient cannot see a Provider's Pseudopatient."""
        assert not rules.test_rule("can_view_user", self.patient, self.provider_pseudopatient)

    def test__patient_cannot_see_admin(self):
        """Test that a Patient cannot see an Admin."""
        assert not rules.test_rule("can_view_user", self.patient, self.admin)

    def test__patient_cannot_see_admin_pseudopatient(self):
        """Test that a Patient cannot see an Admin's Pseudopatient."""
        assert not rules.test_rule("can_view_user", self.patient, self.admin_pseudopatient)

    def test__anyone_can_see_anonymous_pseudopatient(self):
        """Test that anyone can see an Anonymous Pseudopatient."""
        assert rules.test_rule("can_view_user", self.patient, self.anon_pseudopatient)
        assert rules.test_rule("can_view_user", self.admin, self.anon_pseudopatient)
        assert rules.test_rule("can_view_user", self.provider, self.anon_pseudopatient)


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
