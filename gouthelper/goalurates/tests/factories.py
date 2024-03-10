from typing import TYPE_CHECKING, Union

import pytest  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore
from factory.faker import faker  # type: ignore

from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import GOALURATE_MEDHISTORYS
from ...utils.helpers.tests.helpers import MedHistoryCreatorMixin, MedHistoryDataMixin
from ..models import GoalUrate

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    User = get_user_model()


fake = faker.Faker()
pytestmark = pytest.mark.django_db


class CreateGoalUrateData(MedHistoryDataMixin):
    """Provides data for GoalUrate related objects when the class method is called with the appropriate
    arguments."""

    def create(self):
        mh_data = self.create_mh_data()
        return {**mh_data}


def goalurate_data_factory(
    user: Union["User", None] = None,
    goalurate: GoalUrate | None = None,
    mhs: list[GOALURATE_MEDHISTORYS] | None = None,
) -> dict[str, str]:
    return CreateGoalUrateData(
        aid_mas=None,
        aid_mhs=GOALURATE_MEDHISTORYS,
        mhs=mhs,
        bool_mhs=[
            MedHistoryTypes.EROSIONS,
            MedHistoryTypes.TOPHI,
        ],
        user=user,
        aid_obj=goalurate,
    ).create()


class CreateGoalUrate(MedHistoryCreatorMixin):
    """Inherits from Mixins to create related MedHistory objects."""

    def create(self, **kwargs):
        # Pop the mhs_specified from the kwargs so it don't get passed to the GoalUrate constructor
        mhs_specified = kwargs.pop("mhs_specified", False)
        # Need to add user to the Factory because we aren't setting the user attr with the OneToOneCreatorMixin
        goalurate = GoalUrateFactory(**kwargs, user=self.user)
        self.create_mhs(goalurate, specified=mhs_specified)
        return goalurate


def create_goalurate(
    user: Union["User", bool, None] = None,
    mhs: list[GOALURATE_MEDHISTORYS] | None = None,
    **kwargs,
) -> GoalUrate:
    if mhs is None:
        if user and not isinstance(user, bool):
            mhs = (
                user.medhistorys_qs
                if hasattr(user, "medhistorys_qs")
                else user.medhistory_set.filter(medhistorytype__in=GOALURATE_MEDHISTORYS).all()
            )
        else:
            mhs = GOALURATE_MEDHISTORYS
        mhs_specified = False
    else:
        mhs_specified = True
    # Call the constructor Class Method
    return CreateGoalUrate(
        mhs=mhs,
        user=user,
    ).create(mhs_specified=mhs_specified, **kwargs)


class GoalUrateFactory(DjangoModelFactory):
    class Meta:
        model = GoalUrate
