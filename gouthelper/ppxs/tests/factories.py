import random
from decimal import Decimal  # pylint: disable=e0401 # type: ignore
from typing import TYPE_CHECKING, Any, Union  # pylint: disable=e0401 # type: ignore

import factory  # pylint: disable=e0401 # type: ignore
import pytest  # pylint: disable=e0401 # type: ignore
from factory.django import DjangoModelFactory  # pylint: disable=e0401 # type: ignore
from factory.faker import faker  # pylint: disable=e0401 # type: ignore

from ...choices import BOOL_CHOICES
from ...labs.models import Lab, Urate
from ...labs.tests.factories import UrateFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import PPX_MEDHISTORYS
from ...utils.helpers.tests.helpers import LabCreatorMixin, LabDataMixin, MedHistoryCreatorMixin, MedHistoryDataMixin
from ..models import Ppx

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # type: ignore

    User = get_user_model()

pytestmark = pytest.mark.django_db

fake = faker.Faker()


class CreatePpxData(MedHistoryDataMixin, LabDataMixin):
    """Provides data for Ppx and related objects when the class method is called with the appropriate
    arguments. However, the resulting data still needs to be populated with FlareAid-specific data for
    fields on the FlareAid."""

    def create(self):
        mh_data = self.create_mh_data()
        lab_data = self.create_lab_data()
        return {**mh_data, **lab_data}


def ppx_data_factory(
    user: Union["User", None] = None,
    ppx: Ppx | None = None,
    mh_dets: dict[MedHistoryTypes : dict[str:Any]] = None,
    urates: list[Urate, Decimal, tuple[Urate, Any]] | None = None,
    **kwargs,
) -> dict[str, str]:
    """Create data for related MedHistory and Urate objects for the Ppx.

    Args:
        user: The user to associate with the Ppx data.
        ppx: The Ppx to associate with the data.
        mh_dets: Dictionary of MedHistoryTypes and to add kwargs to the creation / modification of their
                    related MedHistoryDetails.
        urates: List of Urate objects or Decimal values OR tuples of Urate objects or Decimal values
                and a dictionary containing field / value mappings to modify the data for
                existing Urate objects already related to the Ppx object. Passing a dict with "DELETE":True
                will flag the urate for deletion in the data. Passing an empty list will result in standard
                behavior where data for anywhere between 0 and 5 urates will be added. PASS NONE if you
                want to mark all urates for deletion and not create any new ones.
    """

    data = CreatePpxData(
        aid_mhs=PPX_MEDHISTORYS,
        aid_labs=["urate"],
        bool_mhs=[MedHistoryTypes.GOUT],
        req_mhs=[MedHistoryTypes.GOUT],
        aid_mh_dets=[MedHistoryTypes.GOUT],
        labs={"urate": urates if urates or urates is None else []},
        mh_dets=mh_dets,
        req_mh_dets=[MedHistoryTypes.GOUT],
        user=user,
        aid_obj=ppx,
    ).create()
    if kwargs and "starting_ult" in kwargs:
        data.update({"starting_ult": kwargs["starting_ult"]})
    elif ppx:
        data.update({"starting_ult": ppx.starting_ult})
    elif user and hasattr(user, "ppx"):
        data.update({"starting_ult": user.ppx.starting_ult})
    ppx_stub = PpxFactory.stub()
    # Assign stub attrs to the data as key/val pairs
    for attr in dir(ppx_stub):
        if not attr.startswith("_") and attr not in data:
            data.update({attr: getattr(ppx_stub, attr)})
    return data


class CreatePpx(LabCreatorMixin, MedHistoryCreatorMixin):
    """Inherits from Mixins to create Lab and MedHistory objects for a Ppx."""

    def create(self, **kwargs):
        # Set the kwargs from the super() method
        kwargs = super().create(**kwargs)

        # Pop the mhs_specified from the kwargs so it don't get passed to the Ppx constructor
        mhs_specified = kwargs.pop("mhs_specified", False)

        # Create the Ppx
        ppx = PpxFactory(user=self.user, **kwargs)

        # Create the labs related to the Ppx
        self.create_labs(ppx)

        # Create the MedHistorys related to the Ppx
        self.create_mhs(ppx, specified=mhs_specified)

        # Return the Flare
        return ppx


def create_ppx(
    user: Union["User", bool, None] = None,
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
        mhs=PPX_MEDHISTORYS,
        mh_dets={MedHistoryTypes.GOUT: {}},
        user=user,
    ).create(mhs_specified=True, **kwargs)


class PpxFactory(DjangoModelFactory):
    class Meta:
        model = Ppx

    starting_ult = factory.fuzzy.FuzzyChoice(BOOL_CHOICES, getter=lambda c: c[0])
