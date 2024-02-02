from datetime import timedelta
from decimal import Decimal

import pytest  # type: ignore
from django.db.utils import IntegrityError  # type: ignore
from django.test import TestCase  # type: ignore
from django.urls import reverse_lazy  # type: ignore
from django.utils import timezone  # type: ignore

from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...genders.choices import Genders
from ...genders.tests.factories import GenderFactory
from ...labs.tests.factories import UrateFactory
from ...medhistorys.tests.factories import CkdFactory, MenopauseFactory
from ...users.tests.factories import PseudopatientFactory
from ..choices import Likelihoods, LimitedJointChoices
from ..models import Flare
from ..selectors import flare_userless_qs
from .factories import create_flare

pytestmark = pytest.mark.django_db


class TestFlareMethods(TestCase):
    def setUp(self):
        self.flare = create_flare()

    def test__constraint_diagnosed_valid(self):
        with self.assertRaises(IntegrityError):
            create_flare(diagnosed=False, crystal_analysis=True)

    def test__constraint_date_started_not_in_future(self):
        with self.assertRaises(IntegrityError):
            create_flare(date_started=(timezone.now() + timedelta(days=1)).date())

    def test__constraint_start_end_date_valid(self):
        with self.assertRaises(IntegrityError):
            create_flare(date_started=timezone.now().date(), date_ended=(timezone.now() - timedelta(days=1)).date())

    def test__constraint_likelihood_valid(self):
        with self.assertRaises(IntegrityError):
            create_flare(likelihood=99)

    def test__constraint_prevalence_valid(self):
        with self.assertRaises(IntegrityError):
            create_flare(prevalence=99)

    def test__constraint_joints_valid(self):
        with self.assertRaises(IntegrityError):
            create_flare(joints=["SI", "Intervertebral disc"])

    def test__abnormal_duration_True(self):
        self.flare.date_started = timezone.now() - timedelta(days=45)
        self.flare.date_ended = timezone.now() - timedelta(days=1)
        self.flare.save()
        self.assertTrue(self.flare.abnormal_duration)

    def test__abnormal_duration_False(self):
        self.flare.date_started = timezone.now() - timedelta(days=8)
        self.flare.date_ended = timezone.now()
        self.flare.save()
        self.assertFalse(self.flare.abnormal_duration)

    def test__at_risk_for_gout_True(self):
        flare = create_flare(
            gender=GenderFactory(value=Genders.MALE),
            dateofbirth=DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 40)),
        )
        self.assertTrue(flare.at_risk_for_gout)

    def test__at_risk_for_gout_female_True(self):
        flare = create_flare(
            gender=GenderFactory(value=Genders.FEMALE),
            dateofbirth=DateOfBirthFactory(value=(timezone.now() - timedelta(days=365 * 40)).date()),
            medhistorys=[CkdFactory()],
            menopause=True,
        )
        self.assertTrue(flare.at_risk_for_gout)

    def test__at_risk_for_gout_False(self):
        flare = create_flare(
            gender=GenderFactory(value=Genders.FEMALE),
            dateofbirth=DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 40)),
            medhistorys=[],  # No medhistorys
            menopause=False,
        )
        self.assertFalse(flare.at_risk_for_gout)

    def test__duration_returns_timedelta(self):
        """Check that the duration property returns a timedelta object and that the
        duration is correct."""
        duration = self.flare.duration
        self.assertTrue(isinstance(duration, timedelta))
        self.assertEqual(
            duration,
            (self.flare.date_ended if self.flare.date_ended else timezone.now().date()) - self.flare.date_started,
        )

    def test__common_joints(self):
        self.flare.joints = [LimitedJointChoices.KNEER, LimitedJointChoices.ANKLEL, LimitedJointChoices.HIPL]
        self.flare.save()
        self.assertEqual(self.flare.common_joints, [LimitedJointChoices.KNEER, LimitedJointChoices.ANKLEL])

    def test__common_joints_str_singular(self):
        self.flare.joints = [LimitedJointChoices.KNEER]
        self.flare.save()
        self.assertEqual(self.flare.common_joints_str, "right knee")

    def test__common_joints_str_plural(self):
        self.flare.joints = [LimitedJointChoices.KNEER, LimitedJointChoices.ANKLEL]
        self.flare.save()
        self.assertEqual(self.flare.common_joints_str, "right knee, left ankle")

    def test__duration(self):
        self.assertEqual(
            self.flare.duration,
            (self.flare.date_ended if self.flare.date_ended else timezone.now().date()) - self.flare.date_started,
        )
        self.assertTrue(isinstance(self.flare.duration, timedelta))

    def test__firstmtp(self):
        self.flare.joints = [LimitedJointChoices.MTP1L]
        self.flare.save()
        self.assertTrue(self.flare.firstmtp)
        self.flare.joints = [LimitedJointChoices.SHOULDERL]
        self.flare.save()
        self.assertFalse(Flare.objects.get().firstmtp)

    def test__firstmtp_str(self):
        self.flare.joints = [LimitedJointChoices.MTP1L]
        self.flare.save()
        self.assertEqual(self.flare.firstmtp_str, "left first metatarsophalangeal joint")
        self.flare.joints = [LimitedJointChoices.MTP1L, LimitedJointChoices.MTP1R]
        self.flare.save()
        self.assertEqual(self.flare.firstmtp_str, "left and right first metatarsophalangeal joint")
        self.flare.joints = [LimitedJointChoices.MTP1R]
        self.flare.save()
        self.assertEqual(self.flare.firstmtp_str, "right first metatarsophalangeal joint")

    def test__get_absolute_url(self):
        self.assertEqual(
            self.flare.get_absolute_url(),
            reverse_lazy("flares:detail", kwargs={"pk": self.flare.pk}),
        )

    def test__hyperuricemia(self):
        flare = create_flare(urate=None)
        self.assertFalse(flare.hyperuricemia)
        urate = UrateFactory(value=Decimal("9.9"))
        flare.urate = urate
        flare.save()
        del flare.hyperuricemia
        self.assertTrue(flare.hyperuricemia)
        flare.urate.value = Decimal("5.0")
        flare.urate.save()
        del flare.hyperuricemia
        self.assertFalse(flare.hyperuricemia)

    def test__joints_str(self):
        self.flare.joints = [LimitedJointChoices.KNEER]
        self.flare.save()
        self.assertEqual(self.flare.joints_str(), "right knee")
        self.flare.joints = [LimitedJointChoices.KNEER, LimitedJointChoices.ANKLEL]
        self.flare.save()
        self.assertEqual(self.flare.joints_str(), "right knee, left ankle")

    def test__likelihood_str(self):
        self.assertEqual(self.flare.likelihood_str, "Flare hasn't been processed yet...")
        self.flare.likelihood = Likelihoods.UNLIKELY
        self.flare.save()
        self.assertEqual(
            self.flare.likelihood_str,
            "Gout isn't likely and alternative causes of the symptoms should be investigated.",
        )
        self.flare.likelihood = Likelihoods.EQUIVOCAL
        self.flare.save()
        self.assertEqual(
            self.flare.likelihood_str,
            "Indeterminate likelihood of gout and it can't be ruled in or out. \
Physician evaluation is recommended.",
        )
        self.flare.likelihood = Likelihoods.LIKELY
        self.flare.save()
        self.assertEqual(
            self.flare.likelihood_str,
            "Gout is very likely. Not a whole lot else needs to be done, other \
than treat the gout!",
        )

    def test__polyarticular(self):
        self.flare.joints = [LimitedJointChoices.KNEER]
        self.flare.save()
        self.assertFalse(self.flare.polyarticular)
        self.flare.joints = [LimitedJointChoices.KNEER, LimitedJointChoices.ANKLEL]
        self.flare.save()
        self.assertTrue(self.flare.polyarticular)

    def test__post_menopausal(self):
        """Test the post_menopausal cached property."""
        # Need to refetch the flare from the DB every time
        # M2M's are changed

        # Check that a young person is no post-menopausal
        dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 30))
        flare = create_flare(dateofbirth=dateofbirth)
        self.assertFalse(flare.post_menopausal)

        # Add a Menopause MedHistory and check that the person is post-menopausal
        menopause = MenopauseFactory(flare=flare)
        flare = Flare.objects.prefetch_related("medhistory_set").get(pk=flare.pk)
        self.assertTrue(flare.post_menopausal)

        # Remove the Menopause MedHistory and check that the person again
        menopause.delete()
        flare = Flare.objects.prefetch_related("medhistory_set").get(pk=flare.pk)
        self.assertFalse(flare.post_menopausal)

        # Check that a woman over age 60 is post-menopausal
        dateofbirth.value = timezone.now() - timedelta(days=365 * 69)
        dateofbirth.save()
        flare.gender.value = Genders.FEMALE
        flare.save()
        flare = Flare.objects.prefetch_related("medhistory_set").get(pk=flare.pk)
        self.assertTrue(flare.post_menopausal)

    def test___str__(self):
        self.flare.date_started = (timezone.now() - timedelta(days=7)).date()
        self.flare.date_ended = None
        self.flare.save()
        self.assertEqual(self.flare.__str__(), f"Flare ({self.flare.date_started.strftime('%m/%d/%Y')} - present)")
        self.flare.date_ended = (timezone.now() - timedelta(days=1)).date()
        self.assertEqual(
            self.flare.__str__(),
            f"Flare ({self.flare.date_started.strftime('%m/%d/%Y')} - {self.flare.date_ended.strftime('%m/%d/%Y')})",
        )
        self.assertEqual(
            self.flare.__str__(),
            f"Flare ({self.flare.date_started.strftime('%m/%d/%Y')} - {self.flare.date_ended.strftime('%m/%d/%Y')})",
        )
        self.flare.user = PseudopatientFactory()
        self.assertEqual(
            self.flare.__str__(),
            f"{self.flare.user}'s Flare ({self.flare.date_started.strftime('%m/%d/%Y')} \
- {self.flare.date_ended.strftime('%m/%d/%Y')})",
        )

    def test__uncommon_joints(self):
        self.flare.joints = [LimitedJointChoices.HIPL, LimitedJointChoices.SHOULDERR, LimitedJointChoices.MTP1L]
        self.assertEqual(self.flare.uncommon_joints, [LimitedJointChoices.HIPL, LimitedJointChoices.SHOULDERR])

    def test__uncommon_joints_str(self):
        self.flare.joints = [LimitedJointChoices.HIPL, LimitedJointChoices.SHOULDERR, LimitedJointChoices.MTP1L]
        self.assertEqual(self.flare.uncommon_joints_str, "left hip, right shoulder")

    def test__update(self):
        self.assertIsNone(self.flare.prevalence)
        self.assertIsNone(self.flare.likelihood)
        self.flare.update_aid()
        self.flare.refresh_from_db()
        self.assertIsNotNone(self.flare.prevalence)
        self.assertIsNotNone(self.flare.likelihood)

    def test__update_with_kwarg(self):
        self.assertIsNone(self.flare.prevalence)
        self.assertIsNone(self.flare.likelihood)
        self.assertEqual(self.flare, self.flare.update_aid(qs=flare_userless_qs(pk=self.flare.pk)))
        self.flare.refresh_from_db()
        self.assertIsNotNone(self.flare.prevalence)
        self.assertIsNotNone(self.flare.likelihood)
