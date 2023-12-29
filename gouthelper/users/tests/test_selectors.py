import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.db.models import QuerySet  # type: ignore
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...ethnicitys.tests.factories import EthnicityFactory
from ...genders.tests.factories import GenderFactory
from ...medhistorydetails.tests.factories import CkdDetailFactory, GoutDetailFactory
from ...medhistorys.tests.factories import CkdFactory, GoutFactory, HeartattackFactory
from ...users.models import Pseudopatient
from ..choices import Roles
from ..selectors import pseudopatient_qs
from .factories import UserFactory

pytestmark = pytest.mark.django_db


class TestPseudopatientQuerySet(TestCase):
    def setUp(self):
        self.pseudopatient = UserFactory(role=Roles.PSEUDOPATIENT)
        self.pseudopatientprofile = self.pseudopatient.profile
        self.dateofbirth = DateOfBirthFactory(user=self.pseudopatient)
        self.ethnicity = EthnicityFactory(user=self.pseudopatient)
        self.gender = GenderFactory(user=self.pseudopatient)
        self.ckd = CkdFactory(user=self.pseudopatient)
        self.gout = GoutFactory(user=self.pseudopatient)
        self.heartattack = HeartattackFactory(user=self.pseudopatient)
        self.ckddetail = CkdDetailFactory(medhistory=self.ckd)
        self.goutdetail = GoutDetailFactory(medhistory=self.gout)

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
            assert self.ckd in qs.medhistorys_qs
            assert self.gout in qs.medhistorys_qs
            assert self.heartattack in qs.medhistorys_qs
        assert len(queries) == 2
        with CaptureQueriesContext(connection) as queries:
            assert qs.ckd.ckddetail == self.ckddetail
            assert qs.gout.goutdetail == self.goutdetail
        assert len(queries) == 0
