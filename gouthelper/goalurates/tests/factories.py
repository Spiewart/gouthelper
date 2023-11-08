import pytest  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ..models import GoalUrate

pytestmark = pytest.mark.django_db


class GoalUrateFactory(DjangoModelFactory):
    class Meta:
        model = GoalUrate
