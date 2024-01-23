import pytest

from ...users.choices import Roles
from ...users.models import Admin, Provider
from ..models import AdminProfile, ProviderProfile

pytestmark = pytest.mark.django_db


def test__admin_post_save():
    admin = Admin(
        username="test_admin",
        email="harryhog@hogwarts.com",
        password="password",
        role=Roles.ADMIN,
    )
    assert AdminProfile.objects.count() == 0
    admin.save()
    assert AdminProfile.objects.count() == 1


def test__provider_post_save():
    provider = Provider(
        username="test_provider",
        email="harryho@hogwarts.com",
        password="password",
        role=Roles.PROVIDER,
    )
    assert ProviderProfile.objects.count() == 0
    provider.save()
    assert ProviderProfile.objects.count() == 1
