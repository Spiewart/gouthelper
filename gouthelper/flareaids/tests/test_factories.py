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
from ...patients.tests.factories import create_psp
from ...treatments.choices import Treatments
from ..models import FlareAid
from .factories import CustomFlareAidFactory

pytestmark = pytest.mark.django_db

fake = faker.Faker()


class TestFlareAidFactory(TestCase):
    def test__flareaid_created(self):
        factory = CustomFlareAidFactory()
        flareaid = factory.create_object()
        self.assertTrue(isinstance(flareaid, FlareAid))

    def test__patient_created(self) -> None:
        factory = CustomFlareAidFactory()
        flareaid = factory.create_object()
        self.assertTrue(hasattr(flareaid, "patient"))
        self.assertTrue(flareaid.patient)

    def test__patient_created_with_dateofbirth(self) -> None:
        dateofbirth: date = (timezone.now() - timedelta(days=365 * 30)).date()
        factory = CustomFlareAidFactory(dateofbirth=dateofbirth)
        flareaid = factory.create_object()
        self.assertTrue(hasattr(flareaid, "patient"))
        self.assertTrue(flareaid.patient)
        self.assertTrue(hasattr(flareaid.patient, "dateofbirth"))
        self.assertTrue(flareaid.patient.dateofbirth)
        self.assertEqual(flareaid.patient.dateofbirth.value, dateofbirth)

    def test__ValueError_raised_with_patient_and_dateofbirth(self) -> None:
        patient = create_psp()
        with self.assertRaises(ValueError):
            CustomFlareAidFactory(patient=patient, dateofbirth=True)

    def test__patient_created_with_gender(self) -> None:
        factory = CustomFlareAidFactory(patient=True, gender=Genders.FEMALE)
        flareaid = factory.create_object()
        self.assertTrue(hasattr(flareaid, "patient"))
        self.assertTrue(flareaid.patient)
        self.assertTrue(hasattr(flareaid.patient, "gender"))
        self.assertTrue(flareaid.patient.gender)
        self.assertEqual(flareaid.patient.gender.value, Genders.FEMALE)

    def test__ValueError_raised_with_patient_and_gender(self) -> None:
        patient = create_psp()
        with self.assertRaises(ValueError):
            CustomFlareAidFactory(patient=patient, gender=True)

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

    def test__creates_patient_with_ibuprofen_allergy(self) -> None:
        factory = CustomFlareAidFactory(ibuprofen_allergy=True)
        flareaid = factory.create_object()
        self.assertTrue(flareaid.patient.medallergy_set.exists())
        self.assertTrue(flareaid.patient.medallergy_set.filter(treatment=Treatments.IBUPROFEN).exists())
