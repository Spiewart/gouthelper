from typing import TYPE_CHECKING, Union

import pytest  # type: ignore
from factory import SubFactory
from factory.django import DjangoModelFactory  # type: ignore
from factory.faker import faker  # type: ignore

from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import GOALURATE_MEDHISTORYS
from ...users.tests.factories import PatientFactory
from ...utils.factories import MedHistoryCreatorMixin, MedHistoryDataMixin
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
    patient: Union["User", None] = None,
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
        patient=patient,
        aid_obj=goalurate,
    ).create()


class CreateGoalUrate(MedHistoryCreatorMixin):
    """Inherits from Mixins to create related MedHistory objects."""

    def create(self, **kwargs):
        # Pop the mhs_specified from the kwargs so it don't get passed to the GoalUrate constructor
        mhs_specified = kwargs.pop("mhs_specified", False)
        # Need to add patient to the Factory because we aren't setting the patient attr with the OneToOneCreatorMixin
        goalurate = GoalUrateFactory(**kwargs, patient=self.patient)
        self.create_mhs(goalurate, specified=mhs_specified)
        return goalurate


def create_goalurate(
    patient: Union["User", None] = None,
    mhs: list[GOALURATE_MEDHISTORYS] | None = None,
    **kwargs,
) -> GoalUrate:
    if mhs is None:
        if patient:
            mhs = (
                patient.medhistorys_qs
                if hasattr(patient, "medhistorys_qs")
                else patient.medhistory_set.filter(medhistorytype__in=GOALURATE_MEDHISTORYS).all()
            )
        else:
            mhs = GOALURATE_MEDHISTORYS
        mhs_specified = False
    else:
        mhs_specified = True
    # Call the constructor Class Method
    return CreateGoalUrate(
        mhs=mhs,
        patient=patient,
    ).create(mhs_specified=mhs_specified, **kwargs)


class GoalUrateFactory(DjangoModelFactory):
    class Meta:
        model = GoalUrate

    goalurate = fake.random_element(elements=GoalUrate.GoalUrates.values)
    patient = SubFactory(PatientFactory)
