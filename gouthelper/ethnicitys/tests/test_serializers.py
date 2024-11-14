import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...users.models import Pseudopatient
from ...users.tests.factories import create_psp
from ..api.serializers import EthnicitySerializer
from ..choices import Ethnicitys
from .factories import EthnicityFactory

pytestmark = pytest.mark.django_db


class TestEthnicitySerializer(TestCase):
    def setUp(self):
        self.ethnicity = EthnicityFactory(value=Ethnicitys.AFRICANAMERICAN)
        self.patient = Pseudopatient.objects.create()
        self.ethnicity_data = {
            "id": self.ethnicity.id,
            "value": self.ethnicity.value,
            "user": self.ethnicity.user,
        }
        self.patient_with_ethnicity = create_psp(ethnicity=Ethnicitys.AFRICANAMERICAN)
        self.create_data = {
            "value": Ethnicitys.HANCHINESE,
            "user": None,
        }

    def test__init__optional(self):
        serializer = EthnicitySerializer(data=self.ethnicity_data, optional=True)
        self.assertFalse(serializer.fields["value"].required)

    def test__init__patient_edit(self):
        serializer = EthnicitySerializer(data=self.ethnicity_data, patient_edit=False)
        self.assertTrue(serializer.fields["value"].read_only)
        serializer = EthnicitySerializer(data=self.ethnicity_data, patient_edit=True)
        self.assertFalse(serializer.fields["value"].read_only)

    def test__validate__instance(self):
        serializer = EthnicitySerializer(instance=self.ethnicity, data=self.ethnicity_data, patient_edit=True)
        self.assertTrue(serializer.is_valid())

        serializer = EthnicitySerializer(
            instance=self.patient_with_ethnicity.ethnicity, data=self.ethnicity_data, patient_edit=True
        )
        self.assertTrue(serializer.is_valid())

        serializer = EthnicitySerializer(
            instance=self.patient_with_ethnicity.ethnicity, data=self.ethnicity_data, patient_edit=False
        )
        self.assertTrue(serializer.is_valid())
        self.assertNotIn("value", serializer.validated_data)

    def test__validate_user__instance(self):
        serializer = EthnicitySerializer(instance=self.ethnicity, data=self.ethnicity_data, patient_edit=True)
        self.assertTrue(serializer.is_valid())

        serializer = EthnicitySerializer(
            instance=self.ethnicity, data=self.ethnicity_data.update({"user": create_psp()}), patient_edit=True
        )
        self.assertFalse(serializer.is_valid())

    def test__create(self):
        serializer = EthnicitySerializer(data=self.create_data, patient_edit=True)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertTrue(serializer.instance)
        self.assertEqual(serializer.instance.value, Ethnicitys.HANCHINESE)

    def test__update(self):
        serializer = EthnicitySerializer(instance=self.ethnicity, data=self.ethnicity_data, patient_edit=True)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertTrue(serializer.instance)
        self.assertEqual(serializer.instance.value, self.ethnicity.value)
        self.assertEqual(serializer.instance.user, self.ethnicity.user)
        serializer = EthnicitySerializer(instance=self.ethnicity, data=self.create_data, patient_edit=True)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertTrue(serializer.instance)
        self.assertEqual(serializer.instance.value, Ethnicitys.HANCHINESE)
        self.assertEqual(serializer.instance.user, self.ethnicity.user)
        serializer = EthnicitySerializer(instance=self.ethnicity, data=self.ethnicity_data, patient_edit=False)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertTrue(serializer.instance)
