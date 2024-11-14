from datetime import date

import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...ethnicitys.choices import Ethnicitys
from ...genders.choices import Genders
from ..api.serializers.nested_serializers import PseudopatientSerializer
from ..models import Pseudopatient
from .factories import UserFactory, create_psp, pseudopatient_api_data_create, pseudopatient_api_data_populate

pytestmark = pytest.mark.django_db


class TestPseudopatientSerializer(TestCase):
    def setUp(self):
        self.patient = create_psp()
        self.patient_data = pseudopatient_api_data_populate(self.patient)
        self.provider = UserFactory()

    def test__init__(self):
        self.assertIsNone(PseudopatientSerializer(provider=None).provider)
        self.assertEqual(self.provider, PseudopatientSerializer(provider=self.provider).provider)

    def test__is_valid(self):
        serializer = PseudopatientSerializer(data=self.patient_data)
        self.assertTrue(serializer.is_valid())
        self.assertIn("dateofbirth", serializer.validated_data)
        self.assertIn("ethnicity", serializer.validated_data)
        self.assertIn("gender", serializer.validated_data)

    def test_create(self):
        data = pseudopatient_api_data_create(gender=Genders.MALE)
        serializer = PseudopatientSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        patient = serializer.create(serializer.validated_data)
        self.assertIsInstance(patient, Pseudopatient)
        self.assertEqual(patient.dateofbirth.value, serializer.validated_data["dateofbirth"]["value"])
        self.assertEqual(patient.ethnicity.value, serializer.validated_data["ethnicity"]["value"])
        self.assertEqual(patient.gender.value, serializer.validated_data["gender"]["value"])
        self.assertTrue(patient.gout)
        self.assertTrue(patient.gout.goutdetail)
        self.assertEqual(patient.gout.goutdetail.medhistory, patient.gout)
        self.assertEqual(patient.gout.goutdetail.at_goal, serializer.validated_data["gout"]["goutdetail"]["at_goal"])
        self.assertEqual(
            patient.gout.goutdetail.at_goal_long_term,
            serializer.validated_data["gout"]["goutdetail"]["at_goal_long_term"],
        )
        self.assertEqual(patient.gout.goutdetail.flaring, serializer.validated_data["gout"]["goutdetail"]["flaring"])
        self.assertEqual(
            patient.gout.goutdetail.on_ppx,
            serializer.validated_data["gout"]["goutdetail"]["on_ppx"],
        )
        self.assertEqual(
            patient.gout.goutdetail.on_ult,
            serializer.validated_data["gout"]["goutdetail"]["on_ult"],
        )
        self.assertEqual(
            patient.gout.goutdetail.starting_ult,
            serializer.validated_data["gout"]["goutdetail"]["starting_ult"],
        )

    def test__update(self):
        new_data = self.patient_data.copy()
        new_data["dateofbirth"]["value"] = date(1990, 1, 1)
        new_data["gender"]["value"] = [gender for gender in Genders.values if gender is not self.patient.gender.value][
            0
        ]
        new_data["ethnicity"]["value"] = Ethnicitys.THAI
        new_data["gout"]["goutdetail"]["at_goal"] = not self.patient.gout.goutdetail.at_goal
        new_data["gout"]["goutdetail"]["at_goal_long_term"] = (
            True if not self.patient.gout.goutdetail.at_goal else False
        )
        serializer = PseudopatientSerializer(instance=self.patient, data=new_data)
        serializer.is_valid()
        print(serializer.errors)
        self.assertTrue(serializer.is_valid())
        patient = serializer.update(self.patient, serializer.validated_data)
        self.assertIsInstance(patient, Pseudopatient)
        self.assertEqual(patient.dateofbirth.value, new_data["dateofbirth"]["value"])
        self.assertEqual(patient.ethnicity.value, new_data["ethnicity"]["value"])
        self.assertEqual(patient.gender.value, new_data["gender"]["value"])
        self.assertEqual(patient.gout.goutdetail.at_goal, new_data["gout"]["goutdetail"]["at_goal"])
        self.assertEqual(
            patient.gout.goutdetail.at_goal_long_term, new_data["gout"]["goutdetail"]["at_goal_long_term"]
        )
