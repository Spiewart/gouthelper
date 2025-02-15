from django.urls import resolve, reverse

from gouthelper.users.models import User


def test_detail(user: User):
    assert reverse("users:detail", kwargs={"username": user.username}) == f"/users/{user.username}/"
    assert resolve(f"/users/{user.username}/").view_name == "users:detail"


def test_update():
    assert reverse("users:update") == "/users/~update/"
    assert resolve("/users/~update/").view_name == "users:update"


def test_redirect():
    assert reverse("users:redirect") == "/users/~redirect/"
    assert resolve("/users/~redirect/").view_name == "users:redirect"


def test_create_patient():
    assert reverse("users:patient-create") == "/users/patients/create/"
    assert resolve("/users/patients/create/").view_name == "users:patient-create"


def test_provider_create_patient():
    assert (
        reverse("users:provider-patient-create", kwargs={"username": "fake-user"})
        == "/users/patients/provider-create/fake-user/"
    )
    assert resolve("/users/patients/provider-create/fake-user/").view_name == "users:provider-patient-create"


def test_patients():
    assert reverse("users:patients", kwargs={"username": "fake-user"}) == "/users/fake-user/patients/"
    assert resolve("/users/fake-user/patients/").view_name == "users:patients"
