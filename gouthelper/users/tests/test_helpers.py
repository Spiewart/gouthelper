from typing import TYPE_CHECKING

from django.test import TestCase
from django.utils import timezone

from ...profiles.tests.factories import PseudopatientProfileFactory
from ..choices import Roles
from ..helpers import create_pseudopatient_username, create_unique_pseudopatient_username_for_provider
from .factories import UserFactory

if TYPE_CHECKING:
    from ..models import Pseudopatient


def create_pseudopatient(provider_username: str, todays_index: int) -> "Pseudopatient":
    pseudpatient = UserFactory(
        role=Roles.PSEUDOPATIENT,
        username=f"{provider_username} [{timezone.now().date().strftime('%-m-%-d-%y')}:{todays_index}]",
    )
    PseudopatientProfileFactory(provider=UserFactory(username=provider_username), user=pseudpatient)
    return pseudpatient


class TestCreatePseudopatientUsername(TestCase):
    def setUp(self) -> None:
        self.provider = UserFactory()
        self.provider_username = self.provider.username

    def test__creates_pseudopatient_username(self) -> None:
        self.assertEqual(
            create_pseudopatient_username(self.provider_username, 1),
            f"{self.provider_username} [{(timezone.now().date().strftime('%-m-%-d-%y'))}:2]",
        )


class TestCreateUniquePseudopatientUsernameForProvider(TestCase):
    def setUp(self):
        self.provider = UserFactory()
        self.provider_username = self.provider.username

    def test__creates_first_new_pseudopatient_username_of_day(self):
        self.assertEqual(
            create_unique_pseudopatient_username_for_provider(self.provider_username),
            f"{self.provider_username} [{(timezone.now().date().strftime('%-m-%-d-%y'))}:1]",
        )

    def test__creates_subsequent_pseudopatient_usernames(self) -> None:
        for i in range(1, 4):
            create_pseudopatient(self.provider_username, i)
            self.assertEqual(
                create_unique_pseudopatient_username_for_provider(self.provider_username),
                f"{self.provider_username} [{(timezone.now().date().strftime('%-m-%-d-%y'))}:{i + 1}]",
            )

    def test__creates_unique_username_with_postfix_for_username_conflict(self) -> None:
        taken_username = create_unique_pseudopatient_username_for_provider(self.provider_username)
        UserFactory(username=taken_username, role=Roles.PSEUDOPATIENT)
        new_username_with_conflict = create_unique_pseudopatient_username_for_provider(self.provider_username)
        prefix = new_username_with_conflict.split(".")[0]
        postfix = new_username_with_conflict.split(".")[1]
        self.assertEqual(
            taken_username,
            prefix + "]",
        )
        self.assertEqual(postfix, "1]")
        UserFactory(username=new_username_with_conflict, role=Roles.PSEUDOPATIENT)
        new_username_with_conflict = create_unique_pseudopatient_username_for_provider(self.provider_username)
        prefix = new_username_with_conflict.split(".")[0]
        postfix = new_username_with_conflict.split(".")[1]
        self.assertEqual(
            taken_username,
            prefix + "]",
        )
        self.assertEqual(postfix, "2]")
