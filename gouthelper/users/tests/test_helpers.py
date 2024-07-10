from typing import TYPE_CHECKING

from django.test import TestCase
from django.utils import timezone

from ...profiles.tests.factories import PseudopatientProfileFactory
from ..choices import Roles
from ..helpers import create_pseudopatient_username_for_new_user_for_provider
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


class TestCreatePseudopatientUsernameForNewUserForProvider(TestCase):
    def setUp(self):
        self.provider = UserFactory()
        self.provider_username = self.provider.username

    def test__creates_first_new_pseudopatient_username_of_day(self):
        self.assertEqual(
            create_pseudopatient_username_for_new_user_for_provider(self.provider_username),
            f"{self.provider_username} [{(timezone.now().date().strftime('%-m-%-d-%y'))}:1]",
        )

    def test__creates_subsequent_pseudopatient_usernames(self) -> None:
        for i in range(1, 4):
            create_pseudopatient(self.provider_username, i)
            self.assertEqual(
                create_pseudopatient_username_for_new_user_for_provider(self.provider_username),
                f"{self.provider_username} [{(timezone.now().date().strftime('%-m-%-d-%y'))}:{i + 1}]",
            )
