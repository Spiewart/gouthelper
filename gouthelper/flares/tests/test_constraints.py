from datetime import date, timedelta

import pytest
from django.db.utils import IntegrityError  # type: ignore
from django.test import TestCase  # type: ignore

from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...genders.tests.factories import GenderFactory
from ...users.tests.factories import create_psp
from ..choices import LimitedJointChoices
from ..models import Flare


class TestFlaresFlareOneActiveFlarePerUser(TestCase):
    def setUp(self):
        self.psp = create_psp()

    def test__constraint_raises_IntegrityError(self):
        Flare.objects.create(
            user=self.psp,
            joints=[LimitedJointChoices.ANKLEL],
            date_started=date.today() - timedelta(days=10),
            date_ended=None,
        )
        with pytest.raises(IntegrityError):
            Flare.objects.create(
                user=self.psp,
                joints=[LimitedJointChoices.ANKLEL],
                date_started=date.today(),
                date_ended=None,
            )

    def test__constraint_without_user_does_not_raise_IntegrityError(self):
        Flare.objects.create(
            dateofbirth=DateOfBirthFactory(),
            gender=GenderFactory(),
            joints=[LimitedJointChoices.ANKLEL],
            date_started=date.today() - timedelta(days=10),
            date_ended=None,
        )
        Flare.objects.create(
            dateofbirth=DateOfBirthFactory(),
            gender=GenderFactory(),
            joints=[LimitedJointChoices.ANKLEL],
            date_started=date.today(),
            date_ended=None,
        )


class TestFlaresFlareExcludeUserOverlapping(TestCase):
    def setUp(self):
        self.psp = create_psp()

    def test__constraint_raises_IntegrityError_new_flare_no_date_ended(self):
        Flare.objects.create(
            user=self.psp,
            joints=[LimitedJointChoices.ANKLEL],
            date_started=date.today() - timedelta(days=10),
            date_ended=date.today() - timedelta(days=5),
        )
        with pytest.raises(IntegrityError):
            Flare.objects.create(
                user=self.psp,
                joints=[LimitedJointChoices.ANKLEL],
                date_started=date.today() - timedelta(days=6),
                date_ended=None,
            )

    def test__constraint_raises_IntegrityError_new_flare_with_date_ended(self):
        Flare.objects.create(
            user=self.psp,
            joints=[LimitedJointChoices.ANKLEL],
            date_started=date.today() - timedelta(days=10),
            date_ended=date.today() - timedelta(days=5),
        )
        with pytest.raises(IntegrityError):
            Flare.objects.create(
                user=self.psp,
                joints=[LimitedJointChoices.ANKLEL],
                date_started=date.today() - timedelta(days=6),
                date_ended=date.today(),
            )

    def test__constraint_does_not_raise_IntegrityError_with_user(self):
        Flare.objects.create(
            user=self.psp,
            joints=[LimitedJointChoices.ANKLEL],
            date_started=date.today() - timedelta(days=10),
            date_ended=date.today() - timedelta(days=5),
        )
        Flare.objects.create(
            user=self.psp,
            joints=[LimitedJointChoices.ANKLEL],
            date_started=date.today() - timedelta(days=4),
            date_ended=date.today(),
        )

    def test__constraint_does_not_raise_IntegrityError_without_user(self):
        Flare.objects.create(
            user=None,
            dateofbirth=DateOfBirthFactory(),
            gender=GenderFactory(),
            joints=[LimitedJointChoices.ANKLEL],
            date_started=date.today() - timedelta(days=10),
            date_ended=date.today() - timedelta(days=5),
        )
        Flare.objects.create(
            user=None,
            dateofbirth=DateOfBirthFactory(),
            gender=GenderFactory(),
            joints=[LimitedJointChoices.ANKLEL],
            date_started=date.today() - timedelta(days=6),
            date_ended=date.today(),
        )
