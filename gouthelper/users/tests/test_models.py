import pytest
from django.test import TestCase

from ...genders.choices import Genders
from ...genders.helpers import get_gender_abbreviation
from ...utils.helpers import shorten_date_for_str
from ..models import User
from .factories import UserFactory, create_psp

pytestmark = pytest.mark.django_db


def test_user_get_absolute_url(user: User):
    assert user.get_absolute_url() == f"/users/{user.username}/"


def test_default_user_role_provider(user: User):
    assert user.role == User.Roles.PROVIDER


def test_default_superuser_role_admin():
    """Test that creating a superuser sets the superuser's role to
    Roles.ADMIN."""
    superuser = User.objects.create_superuser(username="superuser", email="blahbloo", password="blahblah")
    assert superuser.role == User.Roles.ADMIN


class TestPseudopatient(TestCase):
    def setUp(self):
        self.psp = create_psp()
        self.provider_psp = create_psp(provider=UserFactory())
        self.provider = self.provider_psp.provider
        self.provider_psp_with_alias = create_psp(
            provider=self.provider,
            dateofbirth=self.provider_psp.dateofbirth.value,
            gender=Genders(self.provider_psp.gender.value),
        )

    def test_pseudopatient_get_absolute_url(self):
        self.assertEqual(
            self.psp.get_absolute_url(),
            f"/users/pseudopatients/{self.psp.username}/",
        )

    def test__str__without_provider(self):
        self.assertEqual(
            str(self.psp),
            (
                f"{self.psp.age}{get_gender_abbreviation(self.psp.gender.value)} "
                f"[{shorten_date_for_str(date=self.psp.created.date(), month_abbrev=True)}]"
            ),
        )

    def test__str__with_provider(self):
        self.assertEqual(
            str(self.provider_psp),
            (
                f"{self.provider_psp.age}{get_gender_abbreviation(self.provider_psp.gender.value)} "
                f"[{shorten_date_for_str(date=self.psp.created.date(), month_abbrev=True)}]"
            ),
        )

    def test__str_with_provider_and_alias(self):
        self.assertEqual(
            str(self.provider_psp_with_alias),
            (
                f"{self.provider_psp_with_alias.age}"
                f"{get_gender_abbreviation(self.provider_psp_with_alias.gender.value)} "
                f"[{shorten_date_for_str(date=self.psp.created.date(), month_abbrev=True)}]"
                f" #{self.provider_psp_with_alias.provider_alias}"
            ),
        )
