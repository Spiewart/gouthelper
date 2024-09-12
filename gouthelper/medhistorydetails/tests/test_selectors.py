import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...labs.tests.factories import BaselineCreatinineFactory
from ...medhistorys.tests.factories import CkdFactory
from ...users.tests.factories import create_psp
from ..models import CkdDetail
from ..selectors import ckddetail_relations
from .factories import create_ckddetail

pytestmark = pytest.mark.django_db


class TestCkdDetailRelations(TestCase):
    def setUp(self):
        self.ckddetail = create_ckddetail(medhistory=CkdFactory())
        self.baselinecreatinine = BaselineCreatinineFactory(medhistory=self.ckddetail.medhistory)
        self.ckddetail_qs = CkdDetail.objects.filter(pk=self.ckddetail.pk)
        self.ckddetail_with_user = create_ckddetail(medhistory=CkdFactory(user=create_psp()))
        self.baselinecreatinine_with_user = BaselineCreatinineFactory(medhistory=self.ckddetail_with_user.medhistory)
        self.ckddetail_with_user_qs = CkdDetail.objects.filter(pk=self.ckddetail_with_user.pk)

    def test__queryset_executes_one_query(self):
        with CaptureQueriesContext(connection=connection) as queries:
            ckddetail = ckddetail_relations(self.ckddetail_qs).get()
            self.assertEqual(ckddetail.medhistory.baselinecreatinine, self.baselinecreatinine)
            self.assertIsNone(ckddetail.medhistory.user)
            self.assertEqual(len(queries), 1)

    def test__queryset_executes_one_query_with_user(self):
        with CaptureQueriesContext(connection=connection) as queries:
            ckddetail = ckddetail_relations(self.ckddetail_with_user_qs).get()
            self.assertEqual(ckddetail.medhistory.baselinecreatinine, self.baselinecreatinine_with_user)
            self.assertEqual(ckddetail.medhistory.user, self.ckddetail_with_user.medhistory.user)
            self.assertEqual(len(queries), 1)
