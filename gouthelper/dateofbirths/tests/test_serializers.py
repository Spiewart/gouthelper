from datetime import date

import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...users.models import Pseudopatient
from ...users.tests.factories import create_psp
from ..api.serializers import DateOfBirthSerializer
from .factories import DateOfBirthFactory

pytestmark = pytest.mark.django_db


class TestDateOfBirthSerializer(TestCase):
    def setUp(self):
        self.dateofbirth = DateOfBirthFactory()
        self.patient = Pseudopatient.objects.create()
        self.dateofbirth_data = {
            "id": self.dateofbirth.id,
            "value": self.dateofbirth.value,
            "user": self.dateofbirth.user,
        }
        self.patient_with_dateofbirth = create_psp()
        self.create_data = {
            "value": "2000-01-01",
            "user": None,
        }

    def test__init__optional(self):
        serializer = DateOfBirthSerializer(data=self.dateofbirth_data, optional=True)
        self.assertFalse(serializer.fields["value"].required)

    def test__init__patient_edit(self):
        serializer = DateOfBirthSerializer(data=self.dateofbirth_data, patient_edit=False)
        self.assertTrue(serializer.fields["value"].read_only)
        serializer = DateOfBirthSerializer(data=self.dateofbirth_data, patient_edit=True)
        self.assertFalse(serializer.fields["value"].read_only)

    def test__validate__instance(self):
        serializer = DateOfBirthSerializer(instance=self.dateofbirth, data=self.dateofbirth_data, patient_edit=True)
        self.assertTrue(serializer.is_valid())

        serializer = DateOfBirthSerializer(
            instance=self.patient_with_dateofbirth.dateofbirth, data=self.dateofbirth_data, patient_edit=True
        )
        self.assertTrue(serializer.is_valid())

        serializer = DateOfBirthSerializer(
            instance=self.patient_with_dateofbirth.dateofbirth, data=self.dateofbirth_data, patient_edit=False
        )
        self.assertTrue(serializer.is_valid())
        self.assertNotIn("value", serializer.validated_data)

    def test__validate_user__instance(self):
        serializer = DateOfBirthSerializer(instance=self.dateofbirth, data=self.dateofbirth_data, patient_edit=True)
        self.assertTrue(serializer.is_valid())

        serializer = DateOfBirthSerializer(
            instance=self.dateofbirth, data=self.dateofbirth_data.update({"user": create_psp()}), patient_edit=True
        )
        self.assertFalse(serializer.is_valid())

    def test__create(self):
        serializer = DateOfBirthSerializer(data=self.create_data, patient_edit=True)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertTrue(serializer.instance)
        self.assertEqual(serializer.instance.value, date(2000, 1, 1))

    def test__update(self):
        serializer = DateOfBirthSerializer(instance=self.dateofbirth, data=self.dateofbirth_data, patient_edit=True)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertTrue(serializer.instance)
        self.assertEqual(serializer.instance.value, self.dateofbirth.value)
        self.assertEqual(serializer.instance.user, self.dateofbirth.user)
        serializer = DateOfBirthSerializer(instance=self.dateofbirth, data=self.create_data, patient_edit=True)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertTrue(serializer.instance)
        self.assertEqual(serializer.instance.value, date(2000, 1, 1))
        self.assertEqual(serializer.instance.user, self.dateofbirth.user)
        serializer = DateOfBirthSerializer(instance=self.dateofbirth, data=self.dateofbirth_data, patient_edit=False)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertTrue(serializer.instance)
