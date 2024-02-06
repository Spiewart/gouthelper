import random
from decimal import Decimal  # pylint: disable=e0401 # type: ignore
from typing import TYPE_CHECKING, Union  # pylint: disable=e0401 # type: ignore

import factory  # pylint: disable=e0401 # type: ignore
import pytest  # pylint: disable=e0401 # type: ignore
from factory.django import DjangoModelFactory  # pylint: disable=e0401 # type: ignore

from ...choices import BOOL_CHOICES
from ...labs.models import Lab
from ...labs.tests.factories import UrateFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import PPX_MEDHISTORYS
from ...utils.helpers.test_helpers import LabCreatorMixin, MedHistoryCreatorMixin, MedHistoryDataMixin
from ..models import Ppx

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # type: ignore

    User = get_user_model()

pytestmark = pytest.mark.django_db


class CreatePpxData(MedHistoryDataMixin):
    """Provides data for Ppx and related objects when the class method is called with the appropriate
    arguments. However, the resulting data still needs to be populated with FlareAid-specific data for
    fields on the FlareAid."""

    def create(self):
        mh_data = self.create_mh_data(required=[MedHistoryTypes.GOUT])
        return {**mh_data}


def ppx_data_factory(
    user: Union["User", None] = None,
    ppx: Ppx | None = None,
) -> dict[str, str]:
    """Create data for related MedHistory and Urate objects for the Ppx."""
    data = CreatePpxData(
        medallergys=None,
        medhistorys=PPX_MEDHISTORYS,
        bool_mhs=[MedHistoryTypes.GOUT],
        mh_details=[MedHistoryTypes.GOUT],
        user=user,
        aid_obj=ppx,
    ).create()
    ppx_stub = PpxFactory.stub()
    # Assign stub attrs to the data as key/val pairs
    for attr in dir(ppx_stub):
        if not attr.startswith("_"):
            data.update({attr: getattr(ppx_stub, attr)})
    # TODO - create Urate data here

    return data


class CreatePpx(LabCreatorMixin, MedHistoryCreatorMixin):
    """Inherits from Mixins to create Lab and MedHistory objects for a Ppx."""

    def create(self, **kwargs):
        # Set the kwargs from the super() method
        kwargs = super().create(**kwargs)

        # Pop the mhs_specified from the kwargs so it don't get passed to the GoalUrate constructor
        mhs_specified = kwargs.pop("mhs_specified", False)

        # Create the Ppx
        ppx = PpxFactory(**kwargs, user=self.user)

        # Create the labs related to the Ppx
        self.create_labs(ppx)

        # Create the MedHistorys related to the Ppx
        self.create_mhs(ppx, specified=mhs_specified)

        # Return the Flare
        return ppx


def create_ppx(
    user: Union["User", None] = None,
    labs: list[Lab, Decimal] | None = None,
    **kwargs,
) -> Ppx:
    """Creates a Ppx with the given user, labs, and medhistorys."""
    # Set the Labs
    if labs is None:
        labs_kwarg = {UrateFactory: [UrateFactory.build() for _ in range(random.randint(0, 5))]}
    else:
        labs_kwarg = {UrateFactory: []}
        for lab in labs:
            if isinstance(lab, Decimal):
                labs_kwarg[UrateFactory].append(UrateFactory.build(value=lab))
            elif isinstance(lab, Lab):
                labs_kwarg[UrateFactory].append(lab)
            else:
                raise TypeError(f"Invalid type for lab: {type(lab)}")
    # Call the constructor Class Method
    return CreatePpx(
        labs=labs_kwarg,
        medhistorys=PPX_MEDHISTORYS,
        mh_details=[MedHistoryTypes.GOUT],
        user=user,
    ).create(mhs_specified=True, **kwargs)


class PpxFactory(DjangoModelFactory):
    class Meta:
        model = Ppx

    starting_ult = factory.fuzzy.FuzzyChoice(BOOL_CHOICES, getter=lambda c: c[0])
