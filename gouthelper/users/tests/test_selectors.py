from datetime import timedelta

import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.db.models import QuerySet  # type: ignore
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...dateofbirths.selectors import annotate_patient_queryset_with_age
from ...genders.choices import Genders
from ...medhistorys.choices import MedHistoryTypes
from ...users.models import Patient
from ..selectors import patient_qs, patients_filter_age_gender
from .factories import create_psp

pytestmark = pytest.mark.django_db


class TestPatientQuerySet(TestCase):
    def setUp(self):
        self.patient = create_psp(
            medhistorys=[
                MedHistoryTypes.CKD,
                MedHistoryTypes.HEARTATTACK,
            ],
            mh_dets={MedHistoryTypes.CKD: True},
        )
        self.patient = Patient.objects.all_related_objects().get(pk=self.patient.pk)

    def test__qs_returns_correctly(self):
        """Test that the patient_qs returns the correct QuerySet."""
        qs = patient_qs(self.patient.username)
        assert isinstance(qs, QuerySet)
        with self.assertNumQueries(2):
            qs = qs.get()
            assert isinstance(qs, Patient)
            assert qs.pseudopatientprofile == self.patient.pseudopatientprofile
            assert qs.dateofbirth == self.patient.dateofbirth
            assert qs.ethnicity == self.patient.ethnicity
            assert qs.gender == self.patient.gender
            assert hasattr(qs, "medhistorys_qs")
            assert self.patient.ckd in qs.medhistorys_qs
            assert self.patient.gout in qs.medhistorys_qs
            assert self.patient.heartattack in qs.medhistorys_qs

        with CaptureQueriesContext(connection) as queries:
            assert qs.ckd.ckddetail == self.patient.ckddetail
            assert qs.gout.goutdetail == self.patient.goutdetail
        assert len(queries) == 0


class TestPatientFilterAgeGender(TestCase):
    def setUp(self):
        self.patient = create_psp()
        for _ in range(3):
            create_psp(dateofbirth=self.patient.dateofbirth.value - timedelta(days=365 * 2))
        for _ in range(3):
            create_psp(dateofbirth=self.patient.dateofbirth.value, gender=Genders(self.patient.gender.value))

    def test__qs_returns_correctly(self):
        qs = patients_filter_age_gender(
            annotate_patient_queryset_with_age(
                Patient.objects.select_related(
                    "dateofbirth",
                    "gender",
                )
            ),
            age=self.patient.age,
            gender=self.patient.gender.value,
        )
        self.assertEqual(
            qs.count(),
            4,
        )
