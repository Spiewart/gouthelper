import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.db.models import QuerySet  # type: ignore
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...medhistorys.choices import MedHistoryTypes
from ...users.models import Pseudopatient
from ..selectors import pseudopatient_count_for_provider_with_todays_date_in_username, pseudopatient_qs
from .factories import create_psp
from .test_helpers import create_pseudopatient

pytestmark = pytest.mark.django_db


class TestPseudopatientQuerySet(TestCase):
    def setUp(self):
        self.pseudopatient = create_psp(
            medhistorys=[
                MedHistoryTypes.CKD,
                MedHistoryTypes.HEARTATTACK,
            ],
            mh_dets={MedHistoryTypes.CKD: True},
        )
        self.pseudopatient = Pseudopatient.objects.all_related_objects().get(pk=self.pseudopatient.pk)

    def test__qs_returns_correctly(self):
        """Test that the pseudopatient_qs returns the correct QuerySet."""
        qs = pseudopatient_qs(self.pseudopatient.username)
        assert isinstance(qs, QuerySet)
        with self.assertNumQueries(2):
            qs = qs.get()
            assert isinstance(qs, Pseudopatient)
            assert qs.pseudopatientprofile == self.pseudopatient.pseudopatientprofile
            assert qs.dateofbirth == self.pseudopatient.dateofbirth
            assert qs.ethnicity == self.pseudopatient.ethnicity
            assert qs.gender == self.pseudopatient.gender
            assert hasattr(qs, "medhistorys_qs")
            assert self.pseudopatient.ckd in qs.medhistorys_qs
            assert self.pseudopatient.gout in qs.medhistorys_qs
            assert self.pseudopatient.heartattack in qs.medhistorys_qs

        with CaptureQueriesContext(connection) as queries:
            assert qs.ckd.ckddetail == self.pseudopatient.ckddetail
            assert qs.gout.goutdetail == self.pseudopatient.goutdetail
        assert len(queries) == 0


class TestPseudopatientCountForProviderWithTodaysDateInUsername(TestCase):
    def setUp(self):
        self.provider = create_psp()
        self.provider_username = self.provider.username

    def test__returns_zero(self):
        """Test that the count is zero when no pseudopatients exist."""
        self.assertEqual(
            pseudopatient_count_for_provider_with_todays_date_in_username(self.provider_username),
            0,
        )

    def test__returns_correct_count(self):
        """Test that the count is correct when pseudopatients exist."""
        for i in range(1, 4):
            create_pseudopatient(self.provider_username, i)
            self.assertEqual(
                pseudopatient_count_for_provider_with_todays_date_in_username(self.provider_username),
                i,
            )
