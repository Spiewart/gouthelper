from django.test import TestCase

from ...genders.choices import Genders
from ...users.tests.factories import UserFactory, create_psp
from ..helpers import get_provider_alias


class TestCreateProviderAlias(TestCase):
    def setUp(self):
        self.provider = UserFactory()

    def test__creates_provider_alias__no_conflicts(self):
        alias = get_provider_alias(provider=self.provider, age=20, gender=Genders.FEMALE)
        self.assertIsNone(alias)

    def test__creates_provider_alias__conflict(self):
        psp = create_psp(
            provider=self.provider,
        )
        alias = get_provider_alias(provider=self.provider, age=psp.age, gender=psp.gender.value)
        self.assertEqual(alias, 1)

    def test__creates_provider_alias__multiple_conflicts(self):
        psp = create_psp(
            provider=self.provider,
        )
        for _ in range(3):
            print(
                create_psp(
                    provider=self.provider,
                    dateofbirth=psp.dateofbirth.value,
                    gender=Genders(psp.gender.value),
                )
            )
        print(psp)
        alias = get_provider_alias(provider=self.provider, age=psp.age, gender=psp.gender.value)
        self.assertEqual(alias, 4)
