import pytest  # pylint: disable=E0401  # type: ignore
from django.db import connection  # pylint: disable=E0401  # type: ignore
from django.db.models import QuerySet  # pylint: disable=E0401  # type: ignore
from django.test import TestCase  # pylint: disable=E0401  # type: ignore
from django.test.utils import CaptureQueriesContext  # pylint: disable=E0401  # type: ignore

from ...medhistorydetails.choices import Stages
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.tests.factories import CkdFactory, StrokeFactory, UratestonesFactory
from ..choices import FlareFreqs, FlareNums
from ..selectors import ult_userless_qs
from .factories import create_ult

pytestmark = pytest.mark.django_db


class TestUltUserlessQuerySet(TestCase):
    def setUp(self):
        self.ckd = CkdFactory()
        self.ckddetail = CkdDetailFactory(medhistory=self.ckd, stage=Stages.THREE)
        self.stroke = StrokeFactory()
        self.uratestones = UratestonesFactory()
        self.ult = create_ult(
            num_flares=FlareNums.TWOPLUS,
            freq_flares=FlareFreqs.ONEORLESS,
            mhs=[self.ckd, self.uratestones],
            ckddetail={"stage": Stages.THREE},
        )

    def test__queryset_returns_correctly(self):
        queryset = ult_userless_qs(pk=self.ult.pk)
        self.assertIsInstance(queryset, QuerySet)
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), self.ult)
        with CaptureQueriesContext(connection) as queries:
            queryset = queryset.get()
        self.assertEqual(len(queries.captured_queries), 2)
        self.assertIn(self.ckd, queryset.medhistorys_qs)
        self.assertNotIn(self.stroke, queryset.medhistorys_qs)
        self.assertIn(self.uratestones, queryset.medhistorys_qs)
        ckd = [
            medhistory for medhistory in queryset.medhistorys_qs if medhistory.medhistorytype == MedHistoryTypes.CKD
        ][0]
        self.assertEqual(ckd.ckddetail, self.ckddetail)
