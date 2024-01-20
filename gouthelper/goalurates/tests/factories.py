from typing import Any

import factory
import pytest  # type: ignore
from factory import post_generation
from factory.django import DjangoModelFactory  # type: ignore
from factory.faker import faker  # type: ignore

from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import GOALURATE_MEDHISTORYS
from ...medhistorys.tests.factories import ErosionsFactory, TophiFactory
from ...users.tests.factories import PseudopatientFactory
from ..models import GoalUrate

fake = faker.Faker()
pytestmark = pytest.mark.django_db


def create_goalurate_data() -> dict[str, Any]:
    """Method that returns a dictionary of fake data for a GoalUrate object.
    Takes an optional goalurate **kwarg"""

    # Create the data dictionary to be returned
    data = {}

    # Iterate over the goalurate medhistorys and randomly add them to the dict
    for medhistory in GOALURATE_MEDHISTORYS:
        data[f"{medhistory}-value"] = fake.boolean()

    # Return the data
    return data


class GoalUrateFactory(DjangoModelFactory):
    class Meta:
        model = GoalUrate

    @post_generation
    def erosions(self, create, extracted, **kwargs):
        if create:
            if extracted or extracted is None and fake.boolean():
                if self.user and not self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.EROSIONS).exists():
                    ErosionsFactory(user=self.user)
                else:
                    self.medhistorys.add(ErosionsFactory())
            # If extracted is False, delete the User's medhistory if it exists
            else:
                if self.user and self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.EROSIONS).exists():
                    self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.EROSIONS).delete()

    @post_generation
    def tophi(self, create, extracted, **kwargs):
        if create:
            if extracted or extracted is None and fake.boolean():
                if self.user and not self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.TOPHI).exists():
                    TophiFactory(user=self.user)
                else:
                    self.medhistorys.add(TophiFactory())
            # If extracted is False, delete the User's medhistory if it exists
            else:
                if self.user and self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.TOPHI).exists():
                    self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.TOPHI).delete()


class GoalUrateUserFactory(GoalUrateFactory):
    user = factory.SubFactory(PseudopatientFactory)
