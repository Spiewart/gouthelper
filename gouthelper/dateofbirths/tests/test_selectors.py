import pytest  # type: ignore
from django.db.models import QuerySet  # type: ignore
from django.test import TestCase  # type: ignore

from ...users.models import Pseudopatient
from ...users.tests.factories import create_psp
from ..selectors import annotate_pseudopatient_queryset_with_age

pytestmark = pytest.mark.django_db


class TestAnnotatePseudopatientQuerySetWithAge(TestCase):
    def setUp(self):
        self.pseudopatient = create_psp()

    def test__qs_returns_correctly(self):
        """Test that the pseudopatient_qs returns the correct QuerySet."""
        qs = Pseudopatient.objects.filter(username=self.pseudopatient.username).select_related("dateofbirth")
        assert isinstance(qs, QuerySet)
        with self.assertNumQueries(1):
            qs = annotate_pseudopatient_queryset_with_age(qs)
            qs = qs.get()
            assert isinstance(qs, Pseudopatient)
            assert qs.age == self.pseudopatient.age
