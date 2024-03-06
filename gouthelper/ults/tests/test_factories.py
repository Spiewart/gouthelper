import itertools

import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from factory.faker import faker  # type: ignore

from ...medhistorys.lists import ULT_MEDHISTORYS
from ...users.models import Pseudopatient
from ...users.tests.factories import create_psp
from ..choices import FlareFreqs, FlareNums
from ..models import Ult
from .factories import create_ult

pytestmark = pytest.mark.django_db


fake = faker.Faker()


class TestCreateUlt(TestCase):
    def setUp(self):
        for _ in range(100):
            create_ult(user=create_psp(plus=True) if fake.boolean() else None)
        self.ults_without_user = Ult.related_objects.filter(user__isnull=True).all()
        self.users_with_ults = Pseudopatient.objects.ult_qs().filter(ult__isnull=False).all()

    def test__FlareFreqs_are_random(self):
        for freq in FlareFreqs.values:
            print(freq)
            self.assertTrue(Ult.related_objects.filter(freq_flares=freq).exists())
            self.assertTrue(Pseudopatient.objects.ult_qs().filter(ult__freq_flares=freq).exists())

    def test__FlareNums_are_random(self):
        for num in FlareNums.values:
            self.assertTrue(Ult.related_objects.filter(num_flares=num).exists())
            self.assertTrue(Pseudopatient.objects.ult_qs().filter(ult__num_flares=num).exists())

    def test__MedHistoryTypes_are_random(self):
        for mhtype in ULT_MEDHISTORYS:
            print(mhtype)
            self.assertTrue(
                next(
                    iter(
                        [
                            mh
                            for mh in itertools.chain.from_iterable(
                                [ult.medhistorys_qs for ult in self.ults_without_user]
                            )
                            if mh.medhistorytype == mhtype
                        ]
                    ),
                    False,
                )
            )
            self.assertTrue(
                next(
                    iter(
                        mh
                        for mh in itertools.chain.from_iterable([psp.medhistorys_qs for psp in self.users_with_ults])
                        if mh.medhistorytype == mhtype
                    ),
                    False,
                )
            )
