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


def test_create_pseudopatient():
    assert reverse("users:create-pseudopatient") == "/users/pseudopatients/create/"
    assert resolve("/users/pseudopatients/create/").view_name == "users:create-pseudopatient"


def test_provider_create_pseudopatient():
    assert (
        reverse("users:provider-create-pseudopatient", kwargs={"username": "fake-user"})
        == "/users/pseudopatients/provider-create/fake-user/"
    )
    assert (
        resolve("/users/pseudopatients/provider-create/fake-user/").view_name == "users:provider-create-pseudopatient"
    )


def test_pseudopatients():
    assert reverse("users:pseudopatients", kwargs={"username": "fake-user"}) == "/users/fake-user/pseudopatients/"
    assert resolve("/users/fake-user/pseudopatients/").view_name == "users:pseudopatients"
