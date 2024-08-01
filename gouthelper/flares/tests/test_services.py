from datetime import timedelta
from decimal import Decimal

import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore
from django.utils import timezone

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...genders.choices import Genders
from ...genders.tests.factories import GenderFactory
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ...labs.tests.factories import BaselineCreatinineFactory, UrateFactory
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.helpers import medhistorys_get
from ...medhistorys.lists import FLARE_MEDHISTORYS
from ...medhistorys.models import MedHistory
from ...medhistorys.tests.factories import CkdFactory
from ...users.models import Pseudopatient
from ...users.tests.factories import UserFactory, create_psp
from ..choices import Likelihoods, LimitedJointChoices, Prevalences
from ..selectors import flare_userless_qs, flares_user_qs
from ..services import FlareDecisionAid
from .factories import CustomFlareFactory, create_flare

pytestmark = pytest.mark.django_db


class TestFlareMethods(TestCase):
    def setUp(self):
        self.provider = UserFactory()
        for _ in range(10):
            create_psp(provider=self.provider, plus=True)
        self.anon_psp = create_psp(plus=True)
        self.userless_dateofbirth = DateOfBirthFactory()
        self.userless_gender = GenderFactory()

        self.userless_urate = UrateFactory()
        self.userless_ckd = CkdFactory()
        self.userless_baselinecreatinine = BaselineCreatinineFactory(
            medhistory=self.userless_ckd, value=Decimal("2.2")
        )
        self.userless_ckddetail = CkdDetailFactory(
            medhistory=self.userless_ckd,
            stage=labs_stage_calculator(
                labs_eGFR_calculator(
                    self.userless_baselinecreatinine.value,
                    age_calc(self.userless_dateofbirth.value),
                    self.userless_gender,
                )
            ),
        )
        self.flare_userless = create_flare(
            dateofbirth=self.userless_dateofbirth,
            gender=Genders.FEMALE,
            urate=self.userless_urate,
            mhs=[
                MedHistoryTypes.ANGINA,
                MedHistoryTypes.CHF,
                MedHistoryTypes.HEARTATTACK,
                self.userless_ckd,
                MedHistoryTypes.GOUT,
                MedHistoryTypes.MENOPAUSE,
            ],
        )
        self.flare = CustomFlareFactory().create_object()

    def test__init_without_user(self):
        with CaptureQueriesContext(connection) as context:
            decisionaid = FlareDecisionAid(qs=flare_userless_qs(pk=self.flare_userless.pk))
        self.assertEqual(len(context.captured_queries), 3)
        self.assertEqual(decisionaid.flare, self.flare_userless)
        self.assertEqual(decisionaid.dateofbirth, self.flare_userless.dateofbirth)
        self.assertEqual(age_calc(self.flare_userless.dateofbirth.value), decisionaid.age)
        self.assertEqual(Genders.FEMALE, decisionaid.gender.value)
        flare_mhs = self.flare_userless.medhistory_set.all()
        for medhistory in flare_mhs:
            self.assertIn(medhistory, decisionaid.medhistorys)
        self.assertEqual(self.userless_urate, decisionaid.urate)
        self.assertEqual(self.userless_baselinecreatinine, decisionaid.baselinecreatinine)
        self.assertEqual(self.userless_ckd.ckddetail, decisionaid.ckddetail)
        self.assertEqual(decisionaid.ckd, self.userless_ckd)
        self.assertEqual(decisionaid.gout, medhistorys_get(flare_mhs, MedHistoryTypes.GOUT))
        self.assertEqual(decisionaid.menopause, medhistorys_get(flare_mhs, MedHistoryTypes.MENOPAUSE))

    def test__init__with_user(self):
        for psp in Pseudopatient.objects.flares_qs().all():
            if psp.flares_qs:
                psp.flare_qs = psp.flares[0]
                with CaptureQueriesContext(connection) as context:
                    decisionaid = FlareDecisionAid(qs=psp)
                self.assertEqual(len(context.captured_queries), 2)
                self.assertEqual(decisionaid.flare, psp.flare)
                self.assertEqual(decisionaid.dateofbirth, psp.dateofbirth)
                self.assertIsNone(decisionaid.flare.dateofbirth)
                self.assertEqual(age_calc(psp.dateofbirth.value), decisionaid.age)
                self.assertEqual(decisionaid.gender, psp.gender)
                for mh in psp.medhistory_set.all():
                    if mh in FLARE_MEDHISTORYS:
                        self.assertIn(mh, decisionaid.medhistorys)
                urate = psp.urate_set.last()
                self.assertEqual(decisionaid.urate, urate)
                self.assertEqual(decisionaid.baselinecreatinine, psp.baselinecreatinine)
                self.assertEqual(decisionaid.ckddetail, psp.ckddetail)
                self.assertEqual(decisionaid.ckd, psp.ckd)
                self.assertEqual(decisionaid.gout, psp.gout)
                self.assertEqual(decisionaid.menopause, psp.menopause)
                self.assertEqual(decisionaid.cvdiseases, psp.cvdiseases)

    def test__init__with_flare_with_user(self):
        """Test that the __init__method removes dateofbirth and gender from the Flare
        object when it has a user to avoid saving a Flare to the database with either of
        these fields an a user, which will raise an IntegrityError."""
        user = Pseudopatient.objects.flares_qs().first()
        flare = create_flare(user=user)
        self.assertIsNone(flare.dateofbirth)
        self.assertIsNone(flare.gender)
        flare.dateofbirth = flare.user.dateofbirth
        flare.gender = flare.user.gender
        decisionaid = FlareDecisionAid(qs=flares_user_qs(pseudopatient=flare.user.pk, flare_pk=flare.pk))
        self.assertIsNone(decisionaid.flare.dateofbirth)
        self.assertIsNone(decisionaid.flare.gender)
        self.assertEqual(decisionaid.dateofbirth, flare.user.dateofbirth)
        self.assertEqual(decisionaid.gender, flare.user.gender)

    def test__update(self):
        self.assertIsNone(self.flare_userless.likelihood)
        self.assertIsNone(self.flare_userless.prevalence)
        decisionaid = FlareDecisionAid(qs=flare_userless_qs(pk=self.flare_userless.pk))
        decisionaid._update()  # pylint: disable=w0212
        self.flare_userless.refresh_from_db()
        self.assertIsNotNone(self.flare_userless.likelihood)
        self.assertIn(self.flare_userless.prevalence, Prevalences.values)
        self.assertIsNotNone(self.flare_userless.prevalence)
        self.assertIn(self.flare_userless.likelihood, Likelihoods.values)

    def test__aid_needs_2_be_saved_False(self) -> None:
        decisionaid = FlareDecisionAid(qs=self.flare)
        decisionaid._update()
        decisionaid = FlareDecisionAid(qs=self.flare)
        decisionaid.update_prevalence()
        decisionaid.update_likelihood()
        self.assertFalse(decisionaid.aid_needs_2_be_saved())

    def test__aid_needs_2_be_saved_True(self) -> None:
        decisionaid = FlareDecisionAid(qs=self.flare)
        decisionaid.update_prevalence()
        decisionaid.update_likelihood()
        self.assertTrue(decisionaid.aid_needs_2_be_saved())

    def test__aid_needs_to_be_saved_True_with_changed_related_object(self) -> None:
        flare = CustomFlareFactory(
            crystal_analysis=False,
            joints=[LimitedJointChoices.ANKLEL],
            date_ended=None,
            medical_evaluation=False,
            redness=False,
            onset=False,
            angina=False,
            cad=False,
            chf=False,
            ckd=False,
            heartattack=False,
            hypertension=False,
            stroke=False,
            gender=Genders.FEMALE,
            dateofbirth=(timezone.now() - timedelta(days=365 * 34)).date(),
            urate=None,
        ).create_object()
        decisionaid = FlareDecisionAid(qs=flare)
        decisionaid.update_prevalence()
        decisionaid.update_likelihood()
        self.assertTrue(decisionaid.aid_needs_2_be_saved())
        decisionaid = FlareDecisionAid(qs=flare)
        decisionaid.update_prevalence()
        decisionaid.update_likelihood()
        self.assertFalse(decisionaid.aid_needs_2_be_saved())
        flare.redness = True
        flare.onset = True
        MedHistory.objects.create(flare=flare, medhistorytype=MedHistoryTypes.CAD)
        flare.gender.value = Genders.MALE
        flare.gender.save()
        flare = flare_userless_qs(pk=flare.pk).first()
        decisionaid = FlareDecisionAid(qs=flare)
        decisionaid.update_prevalence()
        decisionaid.update_likelihood()
        self.assertTrue(decisionaid.aid_needs_2_be_saved())
