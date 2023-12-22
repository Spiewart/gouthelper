import pytest

from ..models import User

pytestmark = pytest.mark.django_db


def test_user_get_absolute_url(user: User):
    assert user.get_absolute_url() == f"/users/{user.username}/"


def test_default_user_role_provider(user: User):
    assert user.role == User.Roles.PROVIDER


def test_default_superuser_role_admin():
    """Test that creating a superuser sets the superuser's role to
    Roles.ADMIN."""
    superuser = User.objects.create_superuser(username="superuser", email="blahbloo", password="blahblah")
    assert superuser.role == User.Roles.ADMIN
