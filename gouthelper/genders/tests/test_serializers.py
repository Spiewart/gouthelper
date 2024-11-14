import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...users.models import Pseudopatient
from ...users.tests.factories import create_psp
from ..api.serializers import GenderSerializer
from ..choices import Genders
from .factories import GenderFactory

pytestmark = pytest.mark.django_db


class TestGenderSerializer(TestCase):
    def setUp(self):
        self.gender = GenderFactory(value=Genders.FEMALE)
        self.patient = Pseudopatient.objects.create()
        self.gender_data = {
            "id": self.gender.id,
            "value": self.gender.value,
            "user": self.gender.user,
        }
        self.patient_with_gender = create_psp(gender=Genders.FEMALE)
        self.create_data = {
            "value": Genders.MALE,
            "user": None,
        }

    def test__init__optional(self):
        serializer = GenderSerializer(data=self.gender_data, optional=True)
        self.assertFalse(serializer.fields["value"].required)

    def test__init__patient_edit(self):
        serializer = GenderSerializer(data=self.gender_data, patient_edit=False)
        self.assertTrue(serializer.fields["value"].read_only)
        serializer = GenderSerializer(data=self.gender_data, patient_edit=True)
        self.assertFalse(serializer.fields["value"].read_only)

    def test__validate__instance(self):
        serializer = GenderSerializer(instance=self.gender, data=self.gender_data, patient_edit=True)
        self.assertTrue(serializer.is_valid())

        serializer = GenderSerializer(
            instance=self.patient_with_gender.gender, data=self.gender_data, patient_edit=True
        )
        self.assertTrue(serializer.is_valid())

        serializer = GenderSerializer(
            instance=self.patient_with_gender.gender, data=self.gender_data, patient_edit=False
        )
        self.assertTrue(serializer.is_valid())
        self.assertNotIn("value", serializer.validated_data)

    def test__validate_user__instance(self):
        serializer = GenderSerializer(instance=self.gender, data=self.gender_data, patient_edit=True)
        self.assertTrue(serializer.is_valid())
        serializer = GenderSerializer(
            instance=self.gender, data=self.gender_data.update({"user": create_psp()}), patient_edit=True
        )
        self.assertFalse(serializer.is_valid())

    def test__create(self):
        serializer = GenderSerializer(data=self.create_data, patient_edit=True)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertTrue(serializer.instance)
        self.assertEqual(serializer.instance.value, Genders.MALE)

    def test__update(self):
        serializer = GenderSerializer(instance=self.gender, data=self.gender_data, patient_edit=True)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertTrue(serializer.instance)
        self.assertEqual(serializer.instance.value, self.gender.value)
        self.assertEqual(serializer.instance.user, self.gender.user)
        serializer = GenderSerializer(instance=self.gender, data=self.create_data, patient_edit=True)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertTrue(serializer.instance)
        self.assertEqual(serializer.instance.value, Genders.MALE)
        self.assertEqual(serializer.instance.user, self.gender.user)
        serializer = GenderSerializer(instance=self.gender, data=self.gender_data, patient_edit=False)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertTrue(serializer.instance)
