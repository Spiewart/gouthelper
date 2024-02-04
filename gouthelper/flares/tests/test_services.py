from decimal import Decimal

import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.db.models import Q
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...genders.tests.factories import GenderFactory
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ...labs.tests.factories import BaselineCreatinineFactory, UrateFactory
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.helpers import medhistorys_get
from ...medhistorys.lists import FLARE_MEDHISTORYS
from ...medhistorys.tests.factories import CkdFactory
from ...users.models import Pseudopatient
from ...users.tests.factories import UserFactory, create_psp
from ..choices import Likelihoods, Prevalences
from ..selectors import flare_user_qs, flare_userless_qs
from ..services import FlareDecisionAid
from .factories import create_flare

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
            gender=self.userless_gender,
            urate=self.userless_urate,
            medhistorys=[
                MedHistoryTypes.ANGINA,
                MedHistoryTypes.CHF,
                MedHistoryTypes.HEARTATTACK,
                self.userless_ckd,
                MedHistoryTypes.GOUT,
                MedHistoryTypes.MENOPAUSE,
            ],
        )

    def test__init_without_user(self):
        with CaptureQueriesContext(connection) as context:
            decisionaid = FlareDecisionAid(qs=flare_userless_qs(pk=self.flare_userless.pk))
        self.assertEqual(len(context.captured_queries), 2)
        self.assertEqual(decisionaid.flare, self.flare_userless)
        self.assertEqual(decisionaid.dateofbirth, self.flare_userless.dateofbirth)
        self.assertEqual(age_calc(self.flare_userless.dateofbirth.value), decisionaid.age)
        self.assertEqual(self.userless_gender, decisionaid.gender)
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
        for psp in Pseudopatient.objects.filter(Q(flare__isnull=False)):
            flare = psp.flare_set.last()
            with CaptureQueriesContext(connection) as context:
                decisionaid = FlareDecisionAid(qs=flare_user_qs(username=psp.username))
            self.assertEqual(len(context.captured_queries), 2)
            self.assertEqual(decisionaid.flare, flare)
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
        user = Pseudopatient.objects.first()
        flare = create_flare(user=user)
        self.assertIsNone(flare.dateofbirth)
        self.assertIsNone(flare.gender)
        flare.dateofbirth = flare.user.dateofbirth
        flare.gender = flare.user.gender
        decisionaid = FlareDecisionAid(qs=flare_user_qs(username=flare.user.username, flare_pk=flare.pk))
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
