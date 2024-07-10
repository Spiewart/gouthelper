from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore
from factory.faker import faker  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...genders.choices import Genders
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ...medhistorydetails.choices import Stages
from ...medhistorys.choices import MedHistoryTypes
from ...treatments.choices import Treatments
from ...users.tests.factories import create_psp
from ..models import FlareAid
from .factories import CustomFlareAidFactory

pytestmark = pytest.mark.django_db

fake = faker.Faker()


class TestFlareAidFactory(TestCase):
    def test__flareaid_created(self):
        factory = CustomFlareAidFactory()
        flareaid = factory.create_object()
        self.assertTrue(isinstance(flareaid, FlareAid))

    def test__user_created(self) -> None:
        factory = CustomFlareAidFactory(user=True)
        flareaid = factory.create_object()
        self.assertTrue(hasattr(flareaid, "user"))
        self.assertTrue(flareaid.user)

    def test__user_created_with_dateofbirth(self) -> None:
        dateofbirth: date = (timezone.now() - timedelta(days=365 * 30)).date()
        factory = CustomFlareAidFactory(user=True, dateofbirth=dateofbirth)
        flareaid = factory.create_object()
        self.assertTrue(hasattr(flareaid, "user"))
        self.assertTrue(flareaid.user)
        self.assertTrue(hasattr(flareaid.user, "dateofbirth"))
        self.assertTrue(flareaid.user.dateofbirth)
        self.assertEqual(flareaid.user.dateofbirth.value, dateofbirth)

    def test__ValueError_raised_with_user_and_dateofbirth(self) -> None:
        user = create_psp()
        with self.assertRaises(ValueError):
            CustomFlareAidFactory(user=user, dateofbirth=True)

    def test__user_created_with_gender(self) -> None:
        factory = CustomFlareAidFactory(user=True, gender=Genders.FEMALE)
        flareaid = factory.create_object()
        self.assertTrue(hasattr(flareaid, "user"))
        self.assertTrue(flareaid.user)
        self.assertTrue(hasattr(flareaid.user, "gender"))
        self.assertTrue(flareaid.user.gender)
        self.assertEqual(flareaid.user.gender.value, Genders.FEMALE)

    def test__ValueError_raised_with_user_and_gender(self) -> None:
        user = create_psp()
        with self.assertRaises(ValueError):
            CustomFlareAidFactory(user=user, gender=True)

    def test__stage_creates_ckddetail(self):
        factory = CustomFlareAidFactory(stage=Stages.THREE)
        flareaid = factory.create_object()
        self.assertTrue(flareaid.medhistory_set.filter(medhistorytype=MedHistoryTypes.CKD).exists())
        self.assertTrue(flareaid.ckd)
        self.assertTrue(flareaid.ckddetail)
        self.assertEqual(flareaid.ckddetail.stage, Stages.THREE)

    def test__creates_baselinecreatinine(self) -> None:
        factory = CustomFlareAidFactory(baselinecreatinine=Decimal("2.0"))
        flareaid = factory.create_object()
        self.assertTrue(flareaid.ckd)
        self.assertTrue(flareaid.ckddetail)
        self.assertTrue(flareaid.baselinecreatinine)
        self.assertEqual(flareaid.baselinecreatinine.value, Decimal("2.0"))
        self.assertEqual(
            flareaid.ckddetail.stage,
            labs_stage_calculator(
                labs_eGFR_calculator(
                    flareaid.baselinecreatinine, age_calc(flareaid.dateofbirth.value), flareaid.gender.value
                )
            ),
        )

    def test__deletes_ckd_and_relations_when_ckd_is_False(self) -> None:
        factory = CustomFlareAidFactory(baselinecreatinine=Decimal("2.0"))
        flareaid = factory.create_object()
        next_factory = CustomFlareAidFactory(flareaid=flareaid, ckd=False)
        modified_flareaid = next_factory.create_object()
        self.assertFalse(modified_flareaid.ckd)
        self.assertFalse(modified_flareaid.ckddetail)
        self.assertFalse(modified_flareaid.baselinecreatinine)

    def test__creates_ibuprofen_allergy(self) -> None:
        factory = CustomFlareAidFactory(ibuprofen_allergy=True)
        flareaid = factory.create_object()
        self.assertTrue(flareaid.medallergy_set.exists())
        self.assertTrue(flareaid.medallergy_set.filter(treatment=Treatments.IBUPROFEN).exists())

    def test__creates_user_with_ibuprofen_allergy(self) -> None:
        factory = CustomFlareAidFactory(user=True, ibuprofen_allergy=True)
        flareaid = factory.create_object()
        self.assertTrue(flareaid.user.medallergy_set.exists())
        self.assertTrue(flareaid.user.medallergy_set.filter(treatment=Treatments.IBUPROFEN).exists())
