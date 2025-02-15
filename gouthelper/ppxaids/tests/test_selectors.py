import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.db.models import QuerySet  # type: ignore
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...defaults.tests.factories import PpxAidSettingsFactory
from ...medhistorys.lists import PPXAID_MEDHISTORYS
from ...treatments.choices import FlarePpxChoices
from ..selectors import ppxaid_relations
from .factories import create_ppxaid

pytestmark = pytest.mark.django_db


class TestPpxAidUserQuerySet(TestCase):
    """Tests for the ppxaid_relations() queryset."""

    def setUp(self):
        self.user_ppx = create_ppxaid(user=True)
        self.ppxaidsettings = PpxAidSettingsFactory(user=self.user_ppx.user)

    def test__queryset_returns_correctly(self):
        with CaptureQueriesContext(connection) as queries:
            queryset = ppxaid_relations(self.user_ppx.user.pk)
            self.assertIsInstance(queryset, QuerySet)
            queryset = queryset.get()
            self.assertEqual(queryset, self.user_ppx.user)
            self.assertEqual(len(queries.captured_queries), 5)
            self.assertTrue(hasattr(queryset, "ppxaid"))
            self.assertEqual(queryset.ppxaid, self.user_ppx)
            self.assertTrue(hasattr(queryset, "ppxaidsettings"))
            self.assertEqual(queryset.ppxaidsettings, self.ppxaidsettings)
            self.assertTrue(hasattr(queryset, "dateofbirth"))
            self.assertEqual(queryset.dateofbirth, self.user_ppx.user.dateofbirth)
            if hasattr(queryset, "gender"):
                self.assertEqual(queryset.gender, self.user_ppx.user.gender)
            self.assertTrue(hasattr(queryset, "medhistorys_qs"))
            for mh in self.user_ppx.user.medhistory_set.filter(medhistorytype__in=PPXAID_MEDHISTORYS):
                self.assertIn(mh, queryset.medhistorys_qs)
            self.assertTrue(hasattr(queryset, "medallergys_qs"))
            for ma in self.user_ppx.user.medallergy_set.filter(treatment__in=FlarePpxChoices.values):
                self.assertIn(ma, queryset.medallergys_qs)
