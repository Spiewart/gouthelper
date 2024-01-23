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


def test_pseudopatients():
    assert reverse("users:pseudopatients", kwargs={"username": "fake-user"}) == "/users/fake-user/pseudopatients/"
    assert resolve("/users/fake-user/pseudopatients/").view_name == "users:pseudopatients"
