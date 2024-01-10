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
from ...medhistorys.lists import FLARE_MEDHISTORYS
from ...medhistorys.tests.factories import AllopurinolhypersensitivityFactory, CkdFactory, MenopauseFactory
from ..choices import Likelihoods, LimitedJointChoices
from ..models import Flare
from ..selectors import flare_userless_qs
from .factories import FlareFactory

pytestmark = pytest.mark.django_db


class TestFlareMethods(TestCase):
    def setUp(self):
        self.flare = FlareFactory()

    def test__add_medhistorys_adds_flare_medhistory(self):
        ckd = CkdFactory()
        self.flare.add_medhistorys([ckd])
        self.assertIn(ckd, self.flare.medhistorys.all())

    def test__add_medhistorys_raises_TypeError_with_non_flare_medhistory(self):
        allopurinolhypersensitivity = AllopurinolhypersensitivityFactory()
        with self.assertRaises(TypeError) as error:
            self.flare.add_medhistorys([allopurinolhypersensitivity])
        self.assertEqual(
            f"{allopurinolhypersensitivity} is not a valid MedHistory for {self.flare}",
            str(error.exception),
        )

    def test__constraint_diagnosed_valid(self):
        with self.assertRaises(IntegrityError):
            FlareFactory(diagnosed=False, crystal_analysis=True)

    def test__constraint_date_started_not_in_future(self):
        with self.assertRaises(IntegrityError):
            FlareFactory(date_started=timezone.now() + timedelta(days=1))

    def test__constraint_start_end_date_valid(self):
        with self.assertRaises(IntegrityError):
            FlareFactory(date_started=timezone.now(), date_ended=timezone.now() - timedelta(days=1))

    def test__constraint_likelihood_valid(self):
        with self.assertRaises(IntegrityError):
            FlareFactory(likelihood=99)

    def test__constraint_prevalence_valid(self):
        with self.assertRaises(IntegrityError):
            FlareFactory(prevalence=99)

    def test__constraint_joints_valid(self):
        with self.assertRaises(IntegrityError):
            FlareFactory(joints=["SI", "Intervertebral disc"])

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

    def test__aid_medhistorys(self):
        self.assertEqual(self.flare.aid_medhistorys(), FLARE_MEDHISTORYS)

    def test__at_risk_for_gout_True(self):
        flare = FlareFactory(
            gender=GenderFactory(value=Genders.MALE),
            dateofbirth=DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 40)),
        )
        self.assertTrue(flare.at_risk_for_gout)

    def test__at_risk_for_gout_female_True(self):
        flare = FlareFactory(
            gender=GenderFactory(value=Genders.FEMALE),
            dateofbirth=DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 40)),
        )
        menopause = MenopauseFactory()
        ckd = CkdFactory()
        flare.medhistorys.add(menopause, ckd)
        self.assertTrue(flare.at_risk_for_gout)

    def test__at_risk_for_gout_False(self):
        flare = FlareFactory(
            gender=GenderFactory(value=Genders.FEMALE),
            dateofbirth=DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 40)),
        )
        self.assertFalse(flare.at_risk_for_gout)

    def test__remove_medhistorys_removes_medhistory(self):
        ckd = CkdFactory()
        self.flare.medhistorys.add(ckd)
        self.flare.update()
        self.flare.refresh_from_db()
        self.flare.remove_medhistorys([ckd])
        self.assertNotIn(ckd, self.flare.medhistorys.all())

    def test__duration_returns_timedelta(self):
        duration = self.flare.duration
        self.assertTrue(isinstance(duration, timedelta))
        self.assertEqual(duration, timezone.now().date() - self.flare.date_started)

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
        self.assertEqual(self.flare.duration, timezone.now().date() - self.flare.date_started)
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
        flare = FlareFactory(urate=None)
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
        # Need to refetch the flare from the DB every time
        # M2M's are changed
        dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 50))
        menopause = MenopauseFactory()
        flare = FlareFactory(dateofbirth=dateofbirth)
        self.assertFalse(flare.post_menopausal)
        flare.add_medhistorys([menopause])
        flare = Flare.objects.get(pk=flare.pk)
        self.assertTrue(flare.post_menopausal)
        flare.remove_medhistorys([menopause])
        flare = Flare.objects.get(pk=flare.pk)
        self.assertFalse(flare.post_menopausal)
        dateofbirth.value = timezone.now() - timedelta(days=365 * 69)
        dateofbirth.save()
        flare = Flare.objects.get(pk=flare.pk)
        self.assertTrue(flare.post_menopausal)

    def test___str__(self):
        self.flare.joints = [LimitedJointChoices.KNEER]
        self.flare.date_started = (timezone.now() - timedelta(days=7)).date()
        self.flare.save()
        self.assertEqual(self.flare.__str__(), f"Monoarticular, {self.flare.date_started} - present")
        self.flare.date_ended = (timezone.now() - timedelta(days=1)).date()
        self.flare.save()
        self.assertEqual(self.flare.__str__(), f"Monoarticular, {self.flare.date_started} - {self.flare.date_ended}")
        self.flare.joints = [LimitedJointChoices.KNEER, LimitedJointChoices.ANKLEL]
        self.flare.save()
        self.assertEqual(self.flare.__str__(), f"Polyarticular, {self.flare.date_started} - {self.flare.date_ended}")

    def test__uncommon_joints(self):
        self.flare.joints = [LimitedJointChoices.HIPL, LimitedJointChoices.SHOULDERR, LimitedJointChoices.MTP1L]
        self.assertEqual(self.flare.uncommon_joints, [LimitedJointChoices.HIPL, LimitedJointChoices.SHOULDERR])

    def test__uncommon_joints_str(self):
        self.flare.joints = [LimitedJointChoices.HIPL, LimitedJointChoices.SHOULDERR, LimitedJointChoices.MTP1L]
        self.assertEqual(self.flare.uncommon_joints_str, "left hip, right shoulder")

    def test__update(self):
        self.assertIsNone(self.flare.prevalence)
        self.assertIsNone(self.flare.likelihood)
        self.flare.update()
        self.flare.refresh_from_db()
        self.assertIsNotNone(self.flare.prevalence)
        self.assertIsNotNone(self.flare.likelihood)

    def test__update_with_kwarg(self):
        self.assertIsNone(self.flare.prevalence)
        self.assertIsNone(self.flare.likelihood)
        self.assertEqual(self.flare, self.flare.update(qs=flare_userless_qs(pk=self.flare.pk)))
        self.flare.refresh_from_db()
        self.assertIsNotNone(self.flare.prevalence)
        self.assertIsNotNone(self.flare.likelihood)
