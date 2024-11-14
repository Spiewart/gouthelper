import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...medhistorydetails.models import GoutDetail
from ...medhistorydetails.tests.factories import GoutDetailFactory
from ...users.tests.factories import create_psp
from ..api.serializers.nested_serializers import GoutSerializer
from ..models import Gout
from .factories import GoutFactory

pytestmark = pytest.mark.django_db


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

        self.gout_data.update({"value": True})
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
