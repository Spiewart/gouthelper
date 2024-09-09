import pytest
from django.urls import resolve, reverse

from .factories import create_psp

pytestmark = pytest.mark.django_db


def test_pseudopatient_detail():
    pseudopatient = create_psp()
    assert (
        reverse("api:pseudopatient-detail", kwargs={"pk": pseudopatient.pk})
        == f"/api/pseudopatients/{pseudopatient.pk}/"
    )
    assert resolve(f"/api/pseudopatients/{pseudopatient.pk}/").view_name == "api:pseudopatient-detail"


def test_pseudopatient_list():
    assert reverse("api:pseudopatient-list") == "/api/pseudopatients/"
    assert resolve("/api/pseudopatients/").view_name == "api:pseudopatient-list"


def test__provider_create():
    assert reverse("api:pseudopatient-provider-create") == "/api/pseudopatients/provider_create/"
    assert resolve("/api/pseudopatients/provider_create/").view_name == "api:pseudopatient-provider-create"
