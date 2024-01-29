import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.db.models import QuerySet  # type: ignore
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.tests.factories import CkdFactory, HeartattackFactory
from ...users.models import Pseudopatient
from ..selectors import pseudopatient_qs
from .factories import create_psp

pytestmark = pytest.mark.django_db


class TestPseudopatientQuerySet(TestCase):
    def setUp(self):
        self.pseudopatient = create_psp()
        self.pseudopatient.ckd = CkdFactory(user=self.pseudopatient)
        self.pseudopatient.heartattack = HeartattackFactory(user=self.pseudopatient)
        self.pseudopatientprofile = self.pseudopatient.profile
        self.dateofbirth = self.pseudopatient.dateofbirth
        self.ethnicity = self.pseudopatient.ethnicity
        self.gender = self.pseudopatient.gender
        self.ckddetail = CkdDetailFactory(medhistory=self.pseudopatient.ckd)

    def test__qs_returns_correctly(self):
        """Test that the pseudopatient_qs returns the correct QuerySet."""
        qs = pseudopatient_qs(self.pseudopatient.username)
        assert isinstance(qs, QuerySet)
        with CaptureQueriesContext(connection) as queries:
            qs = qs.get()
            assert isinstance(qs, Pseudopatient)
            assert qs.pseudopatientprofile == self.pseudopatientprofile
            assert qs.dateofbirth == self.dateofbirth
            assert qs.ethnicity == self.ethnicity
            assert qs.gender == self.gender
            assert hasattr(qs, "medhistorys_qs")
            assert self.pseudopatient.ckd in qs.medhistorys_qs
            assert self.pseudopatient.gout in qs.medhistorys_qs
            assert self.pseudopatient.heartattack in qs.medhistorys_qs
        assert len(queries) == 2
        with CaptureQueriesContext(connection) as queries:
            assert qs.ckd.ckddetail == self.ckddetail
            assert qs.gout.goutdetail == self.goutdetail
        assert len(queries) == 0
