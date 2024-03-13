import pytest  # pylint: disable=E0401 # type: ignore
from django.test import TestCase  # pylint: disable=E0401 # type: ignore
from factory.faker import faker  # type: ignore

from ...medhistorys.lists import GOALURATE_MEDHISTORYS
from ...users.tests.factories import create_psp
from ..models import GoalUrate
from .factories import create_goalurate

pytestmark = pytest.mark.django_db

fake = faker.Faker()


class TestGoalUrateManager(TestCase):
    def setUp(self):
        for _ in range(10):
            create_goalurate(user=create_psp() if fake.boolean() else None)

    def test__related_objects(self):
        with self.assertNumQueries(2):
            for goalurate in GoalUrate.related_objects.all():
                self.assertTrue(hasattr(goalurate, "medhistorys_qs"))
                for mh in goalurate.medhistorys_qs:
                    self.assertIn(mh.medhistorytype, GOALURATE_MEDHISTORYS)
