import pytest  # type: ignore
from django.db.models import QuerySet  # type: ignore
from django.test import TestCase  # type: ignore

from ...users.models import Patient
from ...users.tests.factories import create_psp
from ..helpers import age_calc
from ..selectors import annotate_patient_queryset_with_age

pytestmark = pytest.mark.django_db


class TestAnnotatePatientQuerySetWithAge(TestCase):
    def setUp(self):
        self.patient = create_psp()

    def test__qs_returns_correctly(self):
        """Test that the patient_qs returns the correct QuerySet."""
        qs = Patient.objects.filter(username=self.patient.username).select_related("dateofbirth")
        assert isinstance(qs, QuerySet)
        with self.assertNumQueries(1):
            qs = annotate_patient_queryset_with_age(qs)
            qs = qs.get()
            assert isinstance(qs, Patient)
            assert qs.age == self.patient.age

    def test__qs_returns_correctly_multiple_patients(self):
        for _ in range(10):
            create_psp()
        qs = Patient.objects.all().select_related("dateofbirth")
        with self.assertNumQueries(1):
            qs = annotate_patient_queryset_with_age(qs)
            for psp in qs:
                assert isinstance(psp, Patient)
                assert hasattr(psp, "age")
                assert psp.age == age_calc(psp.dateofbirth.value)
