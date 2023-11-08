import pytest
from django.apps import apps  # type: ignore

from gouthelper.defaults.services import update_defaults
from gouthelper.users.models import User
from gouthelper.users.tests.factories import UserFactory


@pytest.fixture(autouse=True)
def media_storage(settings, tmpdir):
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture
def user(db) -> User:
    return UserFactory()


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        update_defaults(apps=apps, schema_editor=None)
