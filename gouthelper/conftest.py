import pytest
from django.apps import apps  # type: ignore

from gouthelper.contents.services import create_or_update_contents
from gouthelper.defaults.services import update_defaults
from gouthelper.users.models import User
from gouthelper.users.tests.factories import UserFactory


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Sets up the database for defaults and contents apps."""
    with django_db_blocker.unblock():
        update_defaults(apps=apps, schema_editor=None)
        create_or_update_contents(apps=apps, schema_editor=None)


@pytest.fixture(autouse=True)
def media_storage(settings, tmpdir):
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture
def user(db) -> User:
    return UserFactory()
