from datetime import timedelta
from typing import TYPE_CHECKING

import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...flares.tests.factories import FlareFactory
from ...genders.choices import Genders
from ...genders.tests.factories import GenderFactory
from ...labs.tests.factories import UrateFactory
from ...medhistorys.helpers import medhistorys_get_ckd, medhistorys_get_menopause
from ...medhistorys.tests.factories import ChfFactory, CkdFactory, GoutFactory, MenopauseFactory
from ...utils.helpers.helpers import calculate_duration
from ..choices import LessLikelys, Likelihoods, LimitedJointChoices, Prevalences
from ..helpers import (
    flares_abnormal_duration,
    flares_calculate_likelihood,
    flares_calculate_prevalence,
    flares_calculate_prevalence_points,
    flares_common_joints,
    flares_get_less_likelys,
    flares_get_likelihood_str,
    flares_uncommon_joints,
)
from ..lists import COMMON_GOUT_JOINTS

if TYPE_CHECKING:
    from ...flares.models import Flare

pytestmark = pytest.mark.django_db


def get_likelihood(flare: "Flare") -> Likelihoods:
    prevalence_points = flares_calculate_prevalence_points(
        gender=flare.gender,
        onset=flare.onset,
        redness=flare.redness,
        joints=flare.joints,
        medhistorys=flare.medhistorys.all(),
        urate=flare.urate,
    )
    prevalence = flares_calculate_prevalence(prevalence_points)
    less_likelys = flares_get_less_likelys(
        age=age_calc(flare.dateofbirth.value),
        date_ended=flare.date_ended,
        duration=calculate_duration(flare.date_started, flare.date_ended),
        gender=flare.gender,
        joints=flare.joints,
        menopause=medhistorys_get_menopause(flare.medhistorys.all()),
        crystal_analysis=flare.crystal_analysis,
        ckd=medhistorys_get_ckd(flare.medhistorys.all()),
    )
    likelihood = flares_calculate_likelihood(
        less_likelys=less_likelys,
        diagnosed=flare.diagnosed,
        crystal_analysis=flare.crystal_analysis,
        prevalence=prevalence,
    )
    return likelihood


class TestFlareHelpers(TestCase):
    def setUp(self):
        self.flare = FlareFactory()

    def test__flares_abnormal_duration_too_long(self):
        self.flare.date_started = timezone.now().date() - timedelta(days=16)
        self.flare.date_ended = timezone.now().date()
        self.flare.save()
        self.assertEqual(
            flares_abnormal_duration(duration=self.flare.duration, date_ended=self.flare.date_ended),
            LessLikelys.TOOLONG,
        )

    def test__flares_abnormal_duration_too_short(self):
        self.flare.date_started = timezone.now().date() - timedelta(days=1)
        self.flare.date_ended = timezone.now().date()
        self.flare.save()
        self.assertEqual(
            flares_abnormal_duration(duration=self.flare.duration, date_ended=self.flare.date_ended),
            LessLikelys.TOOSHORT,
        )

    def test__flares_abnormal_duration_just_right(self):
        self.flare.date_started = timezone.now().date() - timedelta(days=5)
        self.flare.date_ended = timezone.now().date()
        self.flare.save()
        self.assertFalse(flares_abnormal_duration(duration=self.flare.duration, date_ended=self.flare.date_ended))

    def test__flares_calculate_prevalence_zero_points(self):
        dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 30))
        gender = GenderFactory(value=Genders.FEMALE)
        flare = FlareFactory(
            crystal_analysis=None,
            dateofbirth=dateofbirth,
            gender=gender,
            joints=[LimitedJointChoices.SHOULDERR],
            onset=False,
            redness=False,
            diagnosed=False,
            urate=None,
        )
        prevalence_points = flares_calculate_prevalence_points(
            gender=gender,
            onset=flare.onset,
            redness=flare.redness,
            joints=flare.joints,
            medhistorys=flare.medhistorys.all(),
            urate=flare.urate,
        )
        self.assertTrue(isinstance(prevalence_points, float))
        self.assertEqual(prevalence_points, 0)

    def test__flares_calculate_prevalence_points_gender_male(self):
        dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 30))
        gender = GenderFactory(value=Genders.MALE)
        flare = FlareFactory(
            crystal_analysis=None,
            dateofbirth=dateofbirth,
            gender=gender,
            joints=[LimitedJointChoices.SHOULDERR],
            onset=False,
            redness=False,
            diagnosed=False,
            urate=None,
        )
        prevalence_points = flares_calculate_prevalence_points(
            gender=gender,
            onset=flare.onset,
            redness=flare.redness,
            joints=flare.joints,
            medhistorys=flare.medhistorys.all(),
            urate=flare.urate,
        )
        self.assertTrue(isinstance(prevalence_points, float))
        self.assertEqual(prevalence_points, 2.0)

    def test__flares_calculate_prevalence_points_gout_history(self):
        dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 30))
        gender = GenderFactory(value=Genders.FEMALE)
        gout = GoutFactory()
        flare = FlareFactory(
            crystal_analysis=None,
            dateofbirth=dateofbirth,
            gender=gender,
            joints=[LimitedJointChoices.SHOULDERR],
            onset=False,
            redness=False,
            diagnosed=False,
            urate=None,
        )
        flare.medhistorys.add(gout)
        prevalence_points = flares_calculate_prevalence_points(
            gender=gender,
            onset=flare.onset,
            redness=flare.redness,
            joints=flare.joints,
            medhistorys=flare.medhistorys.all(),
            urate=flare.urate,
        )
        self.assertTrue(isinstance(prevalence_points, float))
        self.assertEqual(prevalence_points, 2.0)

    def test__flares_calculate_prevalence_points_onset_True(self):
        dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 30))
        gender = GenderFactory(value=Genders.FEMALE)
        flare = FlareFactory(
            crystal_analysis=None,
            dateofbirth=dateofbirth,
            gender=gender,
            joints=[LimitedJointChoices.SHOULDERR],
            onset=True,
            redness=False,
            diagnosed=False,
            urate=None,
        )
        prevalence_points = flares_calculate_prevalence_points(
            gender=gender,
            onset=flare.onset,
            redness=flare.redness,
            joints=flare.joints,
            medhistorys=flare.medhistorys.all(),
            urate=flare.urate,
        )
        self.assertTrue(isinstance(prevalence_points, float))
        self.assertEqual(prevalence_points, 0.5)

    def test__flares_calculate_prevalence_points_redness_True(self):
        dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 30))
        gender = GenderFactory(value=Genders.FEMALE)
        flare = FlareFactory(
            crystal_analysis=None,
            dateofbirth=dateofbirth,
            gender=gender,
            joints=[LimitedJointChoices.SHOULDERR],
            onset=False,
            redness=True,
            diagnosed=False,
            urate=None,
        )
        prevalence_points = flares_calculate_prevalence_points(
            gender=gender,
            onset=flare.onset,
            redness=flare.redness,
            joints=flare.joints,
            medhistorys=flare.medhistorys.all(),
            urate=flare.urate,
        )
        self.assertTrue(isinstance(prevalence_points, float))
        self.assertEqual(prevalence_points, 1.0)

    def test__flares_calculate_prevalence_points_MTP_involved(self):
        dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 30))
        gender = GenderFactory(value=Genders.FEMALE)
        flare = FlareFactory(
            crystal_analysis=None,
            dateofbirth=dateofbirth,
            gender=gender,
            joints=[LimitedJointChoices.SHOULDERR, LimitedJointChoices.MTP1L],
            onset=True,
            redness=False,
            diagnosed=False,
            urate=None,
        )
        prevalence_points = flares_calculate_prevalence_points(
            gender=gender,
            onset=flare.onset,
            redness=flare.redness,
            joints=flare.joints,
            medhistorys=flare.medhistorys.all(),
            urate=flare.urate,
        )
        self.assertTrue(isinstance(prevalence_points, float))
        self.assertEqual(prevalence_points, 3.0)

    def test__flares_calculate_prevalence_points_CV_risk_present(self):
        dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 30))
        gender = GenderFactory(value=Genders.FEMALE)
        chf = ChfFactory()
        flare = FlareFactory(
            crystal_analysis=None,
            dateofbirth=dateofbirth,
            gender=gender,
            joints=[LimitedJointChoices.SHOULDERR, LimitedJointChoices.MTP1L],
            onset=True,
            redness=False,
            diagnosed=False,
            urate=None,
        )
        flare.medhistorys.add(chf)
        prevalence_points = flares_calculate_prevalence_points(
            gender=gender,
            onset=flare.onset,
            redness=flare.redness,
            joints=flare.joints,
            medhistorys=flare.medhistorys.all(),
            urate=flare.urate,
        )
        self.assertTrue(isinstance(prevalence_points, float))
        self.assertEqual(prevalence_points, 4.5)

    def test__flares_calculate_prevalence_points_high_urate(self):
        dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 30))
        gender = GenderFactory(value=Genders.FEMALE)
        chf = ChfFactory()
        urate = UrateFactory(value=10.0)
        flare = FlareFactory(
            crystal_analysis=None,
            dateofbirth=dateofbirth,
            gender=gender,
            joints=[LimitedJointChoices.SHOULDERR, LimitedJointChoices.MTP1L],
            onset=True,
            redness=False,
            diagnosed=False,
            urate=urate,
        )
        flare.medhistorys.add(chf)
        prevalence_points = flares_calculate_prevalence_points(
            gender=gender,
            onset=flare.onset,
            redness=flare.redness,
            joints=flare.joints,
            medhistorys=flare.medhistorys.all(),
            urate=flare.urate,
        )
        self.assertTrue(isinstance(prevalence_points, float))
        self.assertEqual(prevalence_points, 8.0)

    def test__flares_common_joints(self):
        common_joints = flares_common_joints(
            joints=LimitedJointChoices.values,
        )
        for joint in COMMON_GOUT_JOINTS:
            self.assertIn(joint.value, common_joints)

    def test__flares_get_less_likelys_female(self):
        self.flare.dateofbirth.value = timezone.now() - timedelta(days=365 * 30)
        self.flare.dateofbirth.save()
        self.flare.gender.value = Genders.FEMALE
        self.flare.gender.save()
        less_likelys = flares_get_less_likelys(
            age=age_calc(self.flare.dateofbirth.value),
            date_ended=None,
            duration=self.flare.duration,
            gender=self.flare.gender,
            joints=self.flare.joints,
            menopause=self.flare.menopause,
            crystal_analysis=self.flare.crystal_analysis,
            ckd=self.flare.ckd,
        )
        self.assertIn(LessLikelys.FEMALE, less_likelys)

    def test__flares_get_less_likelys_female_with_menopause(self):
        self.flare.dateofbirth.value = timezone.now() - timedelta(days=365 * 30)
        self.flare.dateofbirth.save()
        self.flare.gender.value = Genders.FEMALE
        self.flare.gender.save()
        self.flare.add_medhistorys([MenopauseFactory()])
        less_likelys = flares_get_less_likelys(
            age=age_calc(self.flare.dateofbirth.value),
            date_ended=None,
            duration=self.flare.duration,
            gender=self.flare.gender,
            joints=self.flare.joints,
            menopause=self.flare.menopause,
            crystal_analysis=self.flare.crystal_analysis,
            ckd=self.flare.ckd,
        )
        self.assertNotIn(LessLikelys.FEMALE, less_likelys)

    def test__flares_get_less_likelys_female_with_ckd(self):
        self.flare.dateofbirth.value = timezone.now() - timedelta(days=365 * 30)
        self.flare.dateofbirth.save()
        self.flare.gender.value = Genders.FEMALE
        self.flare.gender.save()
        self.flare.add_medhistorys([CkdFactory()])
        less_likelys = flares_get_less_likelys(
            age=age_calc(self.flare.dateofbirth.value),
            date_ended=None,
            duration=self.flare.duration,
            gender=self.flare.gender,
            joints=self.flare.joints,
            menopause=self.flare.menopause,
            crystal_analysis=self.flare.crystal_analysis,
            ckd=self.flare.ckd,
        )
        self.assertNotIn(LessLikelys.FEMALE, less_likelys)

    def test__flares_get_less_likelys_female_over_45(self):
        self.flare.dateofbirth.value = timezone.now() - timedelta(days=365 * 46)
        self.flare.dateofbirth.save()
        self.flare.gender.value = Genders.FEMALE
        self.flare.gender.save()
        less_likelys = flares_get_less_likelys(
            age=age_calc(self.flare.dateofbirth.value),
            date_ended=None,
            duration=self.flare.duration,
            gender=self.flare.gender,
            joints=self.flare.joints,
            menopause=self.flare.menopause,
            crystal_analysis=self.flare.crystal_analysis,
            ckd=self.flare.ckd,
        )
        self.assertNotIn(LessLikelys.FEMALE, less_likelys)

    def test__flares_get_less_likelys_too_young(self):
        less_likelys = flares_get_less_likelys(
            age=15,
            date_ended=None,
            duration=self.flare.duration,
            gender=self.flare.gender,
            joints=self.flare.joints,
            menopause=self.flare.menopause,
            crystal_analysis=self.flare.crystal_analysis,
            ckd=self.flare.ckd,
        )
        self.assertIn(LessLikelys.TOOYOUNG, less_likelys)

    def test__flares_get_less_likelys_duration_too_long(self):
        self.flare.date_started = timezone.now().date() - timedelta(days=16)
        self.flare.date_ended = timezone.now().date()
        self.flare.save()
        less_likelys = flares_get_less_likelys(
            age=age_calc(self.flare.dateofbirth.value),
            date_ended=self.flare.date_ended,
            duration=self.flare.duration,
            gender=self.flare.gender,
            joints=self.flare.joints,
            menopause=self.flare.menopause,
            crystal_analysis=self.flare.crystal_analysis,
            ckd=self.flare.ckd,
        )
        self.assertIn(LessLikelys.TOOLONG, less_likelys)

    def test__flares_get_less_likelys_duration_too_short(self):
        self.flare.date_started = timezone.now().date() - timedelta(days=1)
        self.flare.date_ended = timezone.now().date()
        self.flare.save()
        less_likelys = flares_get_less_likelys(
            age=age_calc(self.flare.dateofbirth.value),
            date_ended=self.flare.date_ended,
            duration=self.flare.duration,
            gender=self.flare.gender,
            joints=self.flare.joints,
            menopause=self.flare.menopause,
            crystal_analysis=self.flare.crystal_analysis,
            ckd=self.flare.ckd,
        )
        self.assertIn(LessLikelys.TOOSHORT, less_likelys)

    def test__flares_get_less_likelys_uncommon_joints_only(self):
        less_likelys = flares_get_less_likelys(
            age=age_calc(self.flare.dateofbirth.value),
            date_ended=None,
            duration=self.flare.duration,
            gender=self.flare.gender,
            joints=[LimitedJointChoices.SHOULDERR, LimitedJointChoices.HIPL],
            menopause=self.flare.menopause,
            crystal_analysis=self.flare.crystal_analysis,
            ckd=self.flare.ckd,
        )
        self.assertIn(LessLikelys.JOINTS, less_likelys)

    def test__flares_get_less_likelys_crystal_analysis_False(self):
        self.flare.crystal_analysis = False
        self.flare.diagnosed = True
        self.flare.save()
        less_likelys = flares_get_less_likelys(
            age=age_calc(self.flare.dateofbirth.value),
            date_ended=None,
            duration=self.flare.duration,
            gender=self.flare.gender,
            joints=self.flare.joints,
            menopause=self.flare.menopause,
            crystal_analysis=self.flare.crystal_analysis,
            ckd=self.flare.ckd,
        )
        self.assertIn(LessLikelys.NEGCRYSTALS, less_likelys)

    def test__flares_get_less_likelys_crystal_analysis_None(self):
        self.flare.crystal_analysis = None
        self.flare.save()
        less_likelys = flares_get_less_likelys(
            age=age_calc(self.flare.dateofbirth.value),
            date_ended=None,
            duration=self.flare.duration,
            gender=self.flare.gender,
            joints=self.flare.joints,
            menopause=self.flare.menopause,
            crystal_analysis=self.flare.crystal_analysis,
            ckd=self.flare.ckd,
        )
        self.assertNotIn(LessLikelys.NEGCRYSTALS, less_likelys)

    def test__flares_get_likelihood_str(self):
        self.flare.likelihood = Likelihoods.UNLIKELY
        self.flare.save()
        self.assertEqual(
            flares_get_likelihood_str(self.flare),
            "Gout isn't likely and alternative causes of the symptoms should be investigated.",
        )
        self.flare.likelihood = Likelihoods.EQUIVOCAL
        self.flare.save()
        self.assertEqual(
            flares_get_likelihood_str(self.flare),
            "Indeterminate likelihood of gout and it can't be ruled in or out. \
Physician evaluation is recommended.",
        )
        self.flare.likelihood = Likelihoods.LIKELY
        self.flare.save()
        self.assertEqual(
            flares_get_likelihood_str(self.flare),
            "Gout is very likely. Not a whole lot else needs to be done, other than treat the gout!",
        )
        self.flare.likelihood = None
        self.flare.save()
        self.assertEqual(flares_get_likelihood_str(self.flare), "Flare hasn't been processed yet...")

    def test__flares_calculate_likelihood(self):
        self.assertEqual(
            flares_calculate_likelihood(
                less_likelys=[], diagnosed=True, crystal_analysis=True, prevalence=Prevalences.LOW
            ),
            Likelihoods.LIKELY,
        )
        self.assertEqual(
            flares_calculate_likelihood(
                less_likelys=[], diagnosed=True, crystal_analysis=False, prevalence=Prevalences.LOW
            ),
            Likelihoods.UNLIKELY,
        )
        self.assertEqual(
            flares_calculate_likelihood(
                less_likelys=[LessLikelys.TOOLONG],
                diagnosed=False,
                crystal_analysis=None,
                prevalence=Prevalences.MEDIUM,
            ),
            Likelihoods.UNLIKELY,
        )
        self.assertEqual(
            flares_calculate_likelihood(
                less_likelys=[LessLikelys.TOOLONG],
                diagnosed=False,
                crystal_analysis=None,
                prevalence=Prevalences.HIGH,
            ),
            Likelihoods.EQUIVOCAL,
        )
        self.assertEqual(
            flares_calculate_likelihood(
                less_likelys=[LessLikelys.TOOLONG],
                diagnosed=False,
                crystal_analysis=None,
                prevalence=Prevalences.LOW,
            ),
            Likelihoods.UNLIKELY,
        )
        self.assertEqual(
            flares_calculate_likelihood(
                less_likelys=[],
                diagnosed=False,
                crystal_analysis=None,
                prevalence=Prevalences.LOW,
            ),
            Likelihoods.UNLIKELY,
        )
        self.assertEqual(
            flares_calculate_likelihood(
                less_likelys=[],
                diagnosed=False,
                crystal_analysis=None,
                prevalence=Prevalences.MEDIUM,
            ),
            Likelihoods.EQUIVOCAL,
        )
        self.assertEqual(
            flares_calculate_likelihood(
                less_likelys=[],
                diagnosed=False,
                crystal_analysis=None,
                prevalence=Prevalences.HIGH,
            ),
            Likelihoods.LIKELY,
        )

    def test__flares_flares_likelihood_calculator_no_common_gout_joints_lowers_likelihood(
        self,
    ):
        dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 30))
        gender = GenderFactory(value=Genders.MALE)
        chf = ChfFactory()
        urate = UrateFactory(value=10.0)
        flare = FlareFactory(
            crystal_analysis=None,
            dateofbirth=dateofbirth,
            gender=gender,
            joints=[LimitedJointChoices.MTP1L],
            onset=True,
            redness=True,
            diagnosed=False,
            urate=urate,
        )
        flare.medhistorys.add(chf)
        likelihood = get_likelihood(flare=flare)
        self.assertEqual(likelihood, Likelihoods.LIKELY)
        flare.joints = [LimitedJointChoices.SHOULDERL, LimitedJointChoices.HIPL]
        flare.save()
        likelihood = get_likelihood(flare=flare)
        self.assertEqual(likelihood, Likelihoods.EQUIVOCAL)

    def test__flares_flares_likelihood_calculator_female_under_45_without_menopause_lowers_likelihood(
        self,
    ):
        dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 30))
        gender = GenderFactory(value=Genders.FEMALE)
        chf = ChfFactory()
        urate = UrateFactory(value=10.0)
        flare = FlareFactory(
            crystal_analysis=None,
            dateofbirth=dateofbirth,
            gender=gender,
            joints=[LimitedJointChoices.SHOULDERR, LimitedJointChoices.MTP1L],
            onset=True,
            redness=True,
            diagnosed=False,
            urate=urate,
        )
        flare.medhistorys.add(chf)
        likelihood = get_likelihood(flare=flare)
        self.assertEqual(likelihood, Likelihoods.EQUIVOCAL)

    def test__flares_flares_likelihood_calculator_female_under_45_with_menopause_retains_likelihood(
        self,
    ):
        dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 30))
        gender = GenderFactory(value=Genders.FEMALE)
        chf = ChfFactory()
        menopause = MenopauseFactory()
        urate = UrateFactory(value=10.0)
        flare = FlareFactory(
            crystal_analysis=None,
            dateofbirth=dateofbirth,
            gender=gender,
            joints=[LimitedJointChoices.SHOULDERR, LimitedJointChoices.MTP1L],
            onset=True,
            redness=True,
            diagnosed=False,
            urate=urate,
        )
        flare.medhistorys.add(chf, menopause)
        likelihood = get_likelihood(flare=flare)
        self.assertEqual(likelihood, Likelihoods.LIKELY)

    def test__flares_flares_likelihood_calculator_female_under_45_with_ckd_retains_likelihood(
        self,
    ):
        dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 30))
        gender = GenderFactory(value=Genders.FEMALE)
        chf = ChfFactory()
        ckd = CkdFactory()
        urate = UrateFactory(value=10.0)
        flare = FlareFactory(
            crystal_analysis=None,
            dateofbirth=dateofbirth,
            gender=gender,
            joints=[LimitedJointChoices.SHOULDERR, LimitedJointChoices.MTP1L],
            onset=True,
            redness=True,
            diagnosed=False,
            urate=urate,
        )
        flare.medhistorys.add(chf, ckd)
        likelihood = get_likelihood(flare=flare)
        self.assertEqual(likelihood, Likelihoods.LIKELY)

    def test__flares_flares_likelihood_calculator_long_flare_lowers_likelihood(self):
        dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 30))
        gender = GenderFactory(value=Genders.MALE)
        chf = ChfFactory()
        urate = UrateFactory(value=10.0)
        flare = FlareFactory(
            crystal_analysis=None,
            date_ended=None,
            date_started=(timezone.now() - timedelta(days=6)).date(),
            dateofbirth=dateofbirth,
            gender=gender,
            joints=[LimitedJointChoices.SHOULDERR, LimitedJointChoices.MTP1L],
            onset=True,
            redness=True,
            diagnosed=False,
            urate=urate,
        )
        flare.medhistorys.add(chf)
        likelihood = get_likelihood(flare=flare)
        self.assertEqual(likelihood, Likelihoods.LIKELY)
        flare.date_started = (timezone.now() - timedelta(days=35)).date()
        flare.save()
        likelihood = get_likelihood(flare=flare)
        self.assertEqual(likelihood, Likelihoods.EQUIVOCAL)

    def test__flares_flares_likelihood_calculator_short_flare_lowers_likelihood(self):
        dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 30))
        gender = GenderFactory(value=Genders.MALE)
        chf = ChfFactory()
        urate = UrateFactory(value=10.0)
        flare = FlareFactory(
            crystal_analysis=None,
            date_ended=timezone.now().date(),
            date_started=(timezone.now() - timedelta(days=6)).date(),
            dateofbirth=dateofbirth,
            gender=gender,
            joints=[LimitedJointChoices.SHOULDERR, LimitedJointChoices.MTP1L],
            onset=True,
            redness=True,
            diagnosed=False,
            urate=urate,
        )
        flare.medhistorys.add(chf)
        likelihood = get_likelihood(flare=flare)
        self.assertEqual(likelihood, Likelihoods.LIKELY)
        flare.date_started = (timezone.now() - timedelta(days=2)).date()
        flare.save()
        likelihood = get_likelihood(flare=flare)
        self.assertEqual(likelihood, Likelihoods.EQUIVOCAL)

    def test__flares_flares_likelihood_calculator_less_likely_lowers_medium_prevalence(
        self,
    ):
        dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 30))
        gender = GenderFactory(value=Genders.MALE)
        flare = FlareFactory(
            crystal_analysis=None,
            date_ended=timezone.now().date(),
            date_started=(timezone.now() - timedelta(days=6)).date(),
            dateofbirth=dateofbirth,
            gender=gender,
            joints=[LimitedJointChoices.SHOULDERR, LimitedJointChoices.MTP1L],
            onset=False,
            redness=True,
            diagnosed=False,
            urate=None,
        )
        likelihood = get_likelihood(flare=flare)
        self.assertEqual(likelihood, Likelihoods.EQUIVOCAL)
        flare.date_started = (timezone.now() - timedelta(days=2)).date()
        flare.save()
        likelihood = get_likelihood(flare=flare)
        self.assertEqual(likelihood, Likelihoods.UNLIKELY)

    def test__flares_flares_likelihood_calculator_returns_low_prevalence_unlikely(self):
        dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 30))
        gender = GenderFactory(value=Genders.MALE)
        flare = FlareFactory(
            crystal_analysis=None,
            date_ended=timezone.now().date(),
            date_started=(timezone.now() - timedelta(days=6)).date(),
            dateofbirth=dateofbirth,
            gender=gender,
            joints=[LimitedJointChoices.SHOULDERR, LimitedJointChoices.RHAND],
            onset=False,
            redness=False,
            diagnosed=False,
            urate=None,
        )
        likelihood = get_likelihood(flare=flare)
        self.assertEqual(likelihood, Likelihoods.UNLIKELY)

    def test__flares_flares_likelihood_calculator_crystal_analysis_returns_likely(self):
        dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 30))
        gender = GenderFactory(value=Genders.FEMALE)
        flare = FlareFactory(
            crystal_analysis=True,
            date_ended=timezone.now().date(),
            date_started=(timezone.now() - timedelta(days=6)).date(),
            dateofbirth=dateofbirth,
            gender=gender,
            joints=[LimitedJointChoices.SHOULDERR],
            onset=False,
            redness=False,
            diagnosed=True,
            urate=None,
        )
        likelihood = get_likelihood(flare=flare)
        self.assertEqual(likelihood, Likelihoods.LIKELY)

    def test__flares_calculate_prevalence(self):
        self.assertEqual(flares_calculate_prevalence(prevalence_points=2.0), Prevalences.LOW)
        self.assertEqual(flares_calculate_prevalence(prevalence_points=5.0), Prevalences.MEDIUM)
        self.assertEqual(flares_calculate_prevalence(prevalence_points=8.0), Prevalences.HIGH)

    def test__flares_uncommon_joints(self):
        uncommon_joints = flares_uncommon_joints(joints=LimitedJointChoices.values)
        for joint in COMMON_GOUT_JOINTS:
            self.assertNotIn(joint, uncommon_joints)
        for joint in [joint for joint in LimitedJointChoices.values if joint not in COMMON_GOUT_JOINTS]:
            self.assertIn(joint, uncommon_joints)
