import pytest  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ..models import Ppx

pytestmark = pytest.mark.django_db


class PpxFactory(DjangoModelFactory):
    class Meta:
        model = Ppx

    # Need to create Gout MedHistory and GoutDetail object when calling the constructor
    # for PpxFactory
