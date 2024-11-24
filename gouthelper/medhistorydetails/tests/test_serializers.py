import pytest  # pylint: disable=E0401  # type: ignore
from django.test import TestCase  # pylint: disable=E0401  # type: ignore

from ...medhistorys.tests.factories import CkdFactory, GoutFactory
from ..api.serializers import CkdDetailSerializer, GoutDetailSerializer
from ..choices import Stages
from ..models import CkdDetail, GoutDetail
from .factories import GoutDetailFactory, create_ckddetail, create_ckddetail_api_data

pytestmark = pytest.mark.django_db


class TestCkdDetailSerializer(TestCase):
    def setUp(self):
        self.ckddetail = create_ckddetail()
        self.ckddetail_data = create_ckddetail_api_data(ckd=self.ckddetail.medhistory)

    def test__is_valid(self):
        serializer = CkdDetailSerializer(data=self.ckddetail_data)
        self.assertTrue(serializer.is_valid())

        self.ckddetail_data.update(
            {
                "dialysis": False,
                "stage": Stages.TWO,
            }
        )
        serializer = CkdDetailSerializer(data=self.ckddetail_data)
        self.assertTrue(serializer.is_valid())

        self.ckddetail_data.update(
            {
                "dialysis": True,
            }
        )
        serializer = CkdDetailSerializer(data=self.ckddetail_data)
        self.assertFalse(serializer.is_valid())

    def test__create(self):
        serializer = CkdDetailSerializer(data=self.ckddetail_data)
        self.assertTrue(serializer.is_valid())
        serializer.validated_data["medhistory"] = CkdFactory()
        serializer.save()
        self.assertTrue(serializer.instance.pk)
        self.assertTrue(isinstance(serializer.instance, CkdDetail))

        # Test with dialysis
        self.ckddetail_data.update(
            {
                "dialysis": True,
                "dialysis_type": CkdDetail.DialysisChoices.PERITONEAL,
                "dialysis_duration": CkdDetail.DialysisDurations.LESSTHANYEAR,
                "stage": None,
            }
        )
        serializer = CkdDetailSerializer(data=self.ckddetail_data)
        self.assertTrue(serializer.is_valid())
        serializer.validated_data["medhistory"] = CkdFactory()
        serializer.save()
        self.assertTrue(serializer.instance.pk)
        self.assertTrue(isinstance(serializer.instance, CkdDetail))
        self.assertEqual(serializer.instance.stage, Stages.FIVE)

    def test__update(self):
        serializer = CkdDetailSerializer(self.ckddetail, data=self.ckddetail_data)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertTrue(serializer.instance.pk)
        self.assertTrue(isinstance(serializer.instance, CkdDetail))

        # Test with dialysis
        self.ckddetail_data.update(
            {
                "dialysis": True,
                "dialysis_type": CkdDetail.DialysisChoices.PERITONEAL,
                "dialysis_duration": CkdDetail.DialysisDurations.LESSTHANYEAR,
                "stage": None,
            }
        )
        serializer = CkdDetailSerializer(self.ckddetail, data=self.ckddetail_data)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertTrue(serializer.instance.pk)
        self.assertTrue(isinstance(serializer.instance, CkdDetail))
        self.assertEqual(serializer.instance.stage, Stages.FIVE)


class TestGoutDetailSerializer(TestCase):
    def setUp(self):
        self.goutdetail = GoutDetailFactory()
        self.goutdetail_data = {
            "at_goal": True,
            "at_goal_long_term": False,
            "flaring": True,
            "on_ppx": True,
            "on_ult": False,
            "starting_ult": True,
        }

    def test__is_valid(self):
        serializer = GoutDetailSerializer(data=self.goutdetail_data)
        self.assertTrue(serializer.is_valid())

        self.goutdetail_data.update(
            {
                "at_goal": False,
                "at_goal_long_term": True,
            }
        )
        serializer = GoutDetailSerializer(data=self.goutdetail_data)
        self.assertFalse(serializer.is_valid())

    def test__create(self):
        serializer = GoutDetailSerializer(data=self.goutdetail_data)
        self.assertTrue(serializer.is_valid())
        serializer.validated_data["medhistory"] = GoutFactory()
        serializer.save()
        self.assertTrue(serializer.instance.pk)
        self.assertTrue(isinstance(serializer.instance, GoutDetail))

    def test__update(self):
        serializer = GoutDetailSerializer(self.goutdetail, data=self.goutdetail_data)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertTrue(serializer.instance.pk)
        self.assertTrue(isinstance(serializer.instance, GoutDetail))
