import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from rest_framework.exceptions import ValidationError

from ...medhistorydetails.models import GoutDetail
from ...medhistorydetails.tests.factories import GoutDetailFactory
from ...users.tests.factories import create_psp
from ..api.serializers.nested_serializers import AnginaSerializer, GoutSerializer
from ..models import Angina, Gout
from .factories import AnginaFactory, GoutFactory

pytestmark = pytest.mark.django_db


class TestMedHistorySerializer(TestCase):
    # Uses AnginaSerializer for testing because inheritance is the same for all
    # MedHistory serializers child classes without a related MedHistoryDetail

    def setUp(self):
        self.angina = AnginaFactory()
        self.patient = create_psp()
        self.angina_data = {
            "value": True,
            "user": None,
        }

    def test__save(self):
        self.assertEqual(Angina.objects.count(), 1)

        serializer = AnginaSerializer(data=self.angina_data)
        self.assertTrue(serializer.is_valid())
        angina = serializer.save()
        self.assertTrue(isinstance(angina, Angina))

        self.angina_data.update({"user": self.patient.id})
        serializer = AnginaSerializer(instance=angina, data=self.angina_data)
        self.assertTrue(serializer.is_valid())
        angina = serializer.save()
        self.assertIsNotNone(angina.user)
        self.assertEqual(angina.user, self.patient)

        self.assertEqual(Angina.objects.count(), 2)
        self.angina_data.update({"value": False})
        serializer = AnginaSerializer(instance=angina, data=self.angina_data)
        self.assertTrue(serializer.is_valid())
        angina = serializer.save()
        self.assertEqual(Angina.objects.count(), 1)

    def test__save_raises_exception_without_validated_data(self):
        serializer = AnginaSerializer(data={})
        with self.assertRaises(ValidationError):
            serializer.save()

    def test__is_valid(self):
        serializer = AnginaSerializer(data=self.angina_data)
        self.assertTrue(serializer.is_valid())

        self.angina_data.update({"user": self.patient.id})
        serializer = AnginaSerializer(data=self.angina_data)
        self.assertTrue(serializer.is_valid())

        self.angina_data.pop("value")
        serializer = AnginaSerializer(data=self.angina_data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["value"], False)

    def test__should_create_or_update(self):
        # Should return True because data is valid and instance should be created
        serializer = AnginaSerializer(data=self.angina_data)
        serializer.is_valid()
        self.assertTrue(serializer.should_create_or_update(serializer.validated_data))

        # Should return False because data is valid but instance does not need to be updated
        serializer = AnginaSerializer(instance=self.angina, data=self.angina_data)
        serializer.is_valid()
        self.assertFalse(serializer.should_create_or_update(serializer.validated_data))

        # Should return True because data is valid and instance should be updated
        self.angina_data.update({"user": self.patient.id})
        serializer = AnginaSerializer(instance=self.angina, data=self.angina_data)
        serializer.is_valid()
        self.assertTrue(serializer.should_create_or_update(serializer.validated_data))

        serializer.update(instance=self.angina, validated_data=self.angina_data)
        self.assertFalse(serializer.should_create_or_update(serializer.validated_data))

    def test__should_delete(self):
        # Should return False because instance should not be deleted
        serializer = AnginaSerializer(instance=self.angina, data=self.angina_data)
        serializer.is_valid()
        self.assertFalse(serializer.should_delete(serializer.validated_data))

        # Should return True because instance should be deleted
        self.angina_data.update({"value": False})
        serializer = AnginaSerializer(instance=self.angina, data=self.angina_data)
        serializer.is_valid()
        self.assertTrue(serializer.should_delete(serializer.validated_data))

        # Should return False because there is no instance
        self.angina_data.update({"value": True})
        serializer = AnginaSerializer(data=self.angina_data)
        serializer.is_valid()
        self.assertFalse(serializer.should_delete(serializer.validated_data))

    def test__create_medhistory(self):
        serializer = AnginaSerializer(data=self.angina_data)
        serializer.is_valid()
        angina = serializer.save()
        self.assertTrue(isinstance(angina, Angina))

    def test__update_medhistory(self):
        self.assertIsNone(self.angina.user)
        self.angina_data.update({"user": self.patient.id})
        serializer = AnginaSerializer(instance=self.angina, data=self.angina_data)
        serializer.is_valid()
        angina = serializer.save()
        self.assertEqual(angina.user, self.patient)


class TestGoutSerializer(TestCase):
    def setUp(self):
        self.gout = GoutFactory()
        self.goutdetail = GoutDetailFactory(medhistory=self.gout)
        self.patient = create_psp()
        self.goutdetail_data = {
            "id": None,
            "at_goal": False,
            "at_goal_long_term": False,
            "flaring": True,
            "on_ppx": False,
            "on_ult": False,
            "starting_ult": False,
        }
        self.gout_data = {
            "id": None,
            "value": True,
            "user": None,
        }

    def test__init__implicit(self):
        serializer = GoutSerializer(data=self.gout_data, implicit=True)
        self.assertTrue(serializer.fields["value"].read_only)
        self.assertTrue(serializer.fields["value"].default)

        serializer = GoutSerializer(data=self.gout_data, implicit=False)
        self.assertFalse(serializer.fields["value"].read_only)
        self.assertFalse(serializer.fields["value"].default)
        self.assertTrue(serializer.fields["value"].required)

    def test__is_valid(self):
        serializer = GoutSerializer(data=self.gout_data, implicit=False, goutdetail_optional=True)
        self.assertTrue(serializer.is_valid())

        self.gout_data["goutdetail"] = self.goutdetail_data
        serializer = GoutSerializer(data=self.gout_data, implicit=False)
        self.assertTrue(serializer.is_valid())

        self.goutdetail_data.pop("at_goal")
        serializer = GoutSerializer(data=self.gout_data, implicit=False)
        self.assertFalse(serializer.is_valid())

    def test__create(self):
        self.gout_data.pop("value")
        serializer = GoutSerializer(data=self.gout_data, implicit=True, goutdetail_optional=True)
        self.assertTrue(serializer.is_valid())
        gout = serializer.save()
        self.assertTrue(isinstance(gout, Gout))

        serializer = GoutSerializer(data=self.gout_data, implicit=False, goutdetail_optional=True)
        self.assertFalse(serializer.is_valid())

        self.gout_data.update({"value": False})
        serializer = GoutSerializer(data=self.gout_data, implicit=False, goutdetail_optional=True)
        self.assertTrue(serializer.is_valid())
        gout = serializer.save()
        self.assertIsNone(gout)

        self.gout_data.update({"value": True})
        serializer = GoutSerializer(data=self.gout_data, implicit=False, goutdetail_optional=True)
        self.assertTrue(serializer.is_valid())
        gout = serializer.save()
        self.assertTrue(isinstance(gout, Gout))

        self.gout_data.update({"goutdetail": self.goutdetail_data})
        serializer = GoutSerializer(data=self.gout_data, implicit=False)
        self.assertTrue(serializer.is_valid())
        gout = serializer.save()
        self.assertTrue(isinstance(gout, Gout))
        self.assertTrue(gout.goutdetail)
        self.assertTrue(isinstance(gout.goutdetail, GoutDetail))

        self.gout_data.pop("value")
        serializer = GoutSerializer(data=self.gout_data, implicit=True)
        self.assertTrue(serializer.is_valid())
        gout = serializer.save()
        self.assertTrue(isinstance(gout, Gout))
        self.assertTrue(gout.goutdetail)
        self.assertTrue(isinstance(gout.goutdetail, GoutDetail))

    def test__update(self):
        self.gout_data.pop("value")
        serializer = GoutSerializer(instance=self.gout, data=self.gout_data, implicit=True, goutdetail_optional=True)
        self.assertTrue(serializer.is_valid())
        gout = serializer.save()
        self.assertTrue(isinstance(gout, Gout))

        # "value" is still absent but required because implicit is False
        serializer = GoutSerializer(instance=self.gout, data=self.gout_data, implicit=False, goutdetail_optional=True)
        self.assertFalse(serializer.is_valid())

        self.gout_data.update({"value": True})
        serializer = GoutSerializer(instance=self.gout, data=self.gout_data, implicit=True, goutdetail_optional=True)
        self.assertTrue(serializer.is_valid())
        gout = serializer.save()
        self.assertTrue(isinstance(gout, Gout))

        serializer = GoutSerializer(instance=self.gout, data=self.gout_data, implicit=False, goutdetail_optional=True)
        self.assertTrue(serializer.is_valid())
        gout = serializer.save()
        self.assertTrue(isinstance(gout, Gout))

        self.gout_data.update({"goutdetail": self.goutdetail_data})
        serializer = GoutSerializer(instance=self.gout, data=self.gout_data, implicit=False)
        self.assertTrue(serializer.is_valid())
        gout = serializer.save()
        self.assertTrue(isinstance(gout, Gout))
        self.assertTrue(gout.goutdetail)
        self.assertTrue(isinstance(gout.goutdetail, GoutDetail))

        self.gout_data.pop("value")
        self.gout_data.update({"goutdetail": self.goutdetail_data})
        serializer = GoutSerializer(instance=self.gout, data=self.gout_data, implicit=True)
        self.assertTrue(serializer.is_valid())
        gout = serializer.save()
        self.assertTrue(isinstance(gout, Gout))
        self.assertTrue(gout.goutdetail)
        self.assertTrue(isinstance(gout.goutdetail, GoutDetail))

        self.goutdetail_data.update({"at_goal": True, "at_goal_long_term": True})
        serializer = GoutSerializer(instance=self.gout, data=self.gout_data, implicit=True)
        self.assertTrue(serializer.is_valid())
        gout = serializer.save()
        self.assertTrue(gout.goutdetail.at_goal)
        self.assertTrue(gout.goutdetail.at_goal_long_term)

    def test__delete(self):
        self.gout_data.update({"value": False})
        serializer = GoutSerializer(instance=self.gout, data=self.gout_data, implicit=False, goutdetail_optional=True)
        self.assertTrue(serializer.is_valid())
        gout = serializer.save()
        self.assertIsNone(gout)
        self.assertFalse(Gout.objects.filter(id=self.gout.id).exists())
