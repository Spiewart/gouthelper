from datetime import timedelta

import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.db.models import QuerySet  # type: ignore
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...dateofbirths.selectors import annotate_pseudopatient_queryset_with_age
from ...genders.choices import Genders
from ...medhistorys.choices import MedHistoryTypes
from ...users.models import Pseudopatient
from ..selectors import pseudopatient_filter_age_gender, pseudopatient_qs
from .factories import create_psp

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


class TestPseudopatientFilterAgeGender(TestCase):
    def setUp(self):
        self.pseudopatient = create_psp()
        for _ in range(3):
            create_psp(dateofbirth=self.pseudopatient.dateofbirth.value - timedelta(days=365 * 2))
        for _ in range(3):
            create_psp(
                dateofbirth=self.pseudopatient.dateofbirth.value, gender=Genders(self.pseudopatient.gender.value)
            )

    def test__qs_returns_correctly(self):
        qs = pseudopatient_filter_age_gender(
            annotate_pseudopatient_queryset_with_age(
                Pseudopatient.objects.select_related(
                    "dateofbirth",
                    "gender",
                )
            ),
            age=self.pseudopatient.age,
            gender=self.pseudopatient.gender.value,
        )
        self.assertEqual(
            qs.count(),
            4,
        )
