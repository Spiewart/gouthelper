import random
from decimal import Decimal  # pylint: disable=e0401 # type: ignore
from typing import TYPE_CHECKING, Any, Union  # pylint: disable=e0401 # type: ignore

import factory  # pylint: disable=e0401 # type: ignore
import pytest  # pylint: disable=e0401 # type: ignore
from django.db.models import QuerySet
from factory.django import DjangoModelFactory  # pylint: disable=e0401 # type: ignore
from factory.faker import faker  # type: ignore

from ...choices import BOOL_CHOICES
from ...labs.models import Lab, Urate
from ...labs.tests.factories import UrateFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import PPX_MEDHISTORYS
from ...utils.helpers.helpers import get_qs_or_set
from ...utils.helpers.test_helpers import (
    LabCreatorMixin,
    MedHistoryCreatorMixin,
    MedHistoryDataMixin,
    fake_date_drawn,
    fake_urate_decimal,
)
from ..models import Ppx

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # type: ignore

    User = get_user_model()

pytestmark = pytest.mark.django_db

fake = faker.Faker()


class CreatePpxData(MedHistoryDataMixin):
    """Provides data for Ppx and related objects when the class method is called with the appropriate
    arguments. However, the resulting data still needs to be populated with FlareAid-specific data for
    fields on the FlareAid."""

    def create(self):
        mh_data = self.create_mh_data()
        return {**mh_data}


def create_urate_data(index: int, urate: Urate | Decimal = None) -> dict[str, str | Decimal]:
    return {
        f"urate-{index}-value": (
            urate.value
            if urate and isinstance(urate, Urate)
            else urate
            if urate and isinstance(urate, Decimal)
            else fake_urate_decimal()
        ),
        f"urate-{index}-date_drawn": (
            urate.date_drawn if urate and isinstance(urate, Urate) else str(fake_date_drawn())
        ),
        f"urate-{index}-id": (urate.pk if urate and isinstance(urate, Urate) else ""),
    }


def ppx_data_factory(
    user: Union["User", None] = None,
    ppx: Ppx | None = None,
    mh_dets: dict[MedHistoryTypes : dict[str:Any]] = None,
    urates: list[Urate, Decimal] | None = None,
    init_urates: list[Urate, Decimal] | None = None,
    **kwargs,
) -> dict[str, str]:
    """Create data for related MedHistory and Urate objects for the Ppx."""
    data = CreatePpxData(
        aid_mhs=PPX_MEDHISTORYS,
        bool_mhs=[MedHistoryTypes.GOUT],
        req_mhs=[MedHistoryTypes.GOUT],
        aid_mh_dets=[MedHistoryTypes.GOUT],
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
    # Create data for urates
    if user:
        if init_urates:
            raise ValueError("If user is provided, init_urates must be None.")
        init_urates = get_qs_or_set(user, "urate")
    elif ppx:
        if init_urates:
            raise ValueError("If ppx is provided, init_urates must be None.")
        init_urates = get_qs_or_set(ppx, "urate")
    else:
        init_urates = sorted(init_urates, key=lambda urate: urate.date_drawn) if init_urates else []
    if isinstance(init_urates, QuerySet):
        init_urates.order_by("date_drawn")
    init_urate_len = len(init_urates)
    if init_urates:
        exi_i = 0
        for urate in init_urates:
            # If the urate list is not None and the urate is not in the list,
            # it needs to be marked for deletion in the formset
            if urates is not None and urate not in urates:
                data.update(create_urate_data(exi_i, urate))
                data.update({f"urate-{exi_i}-DELETE": "on"})
                exi_i += 1
            # 50/50 chance that each initial urate will be deleted
            elif fake.boolean():
                data.update(create_urate_data(exi_i, urate))
                # 50/50 chance the urate value changed
                if fake.boolean():
                    data.update({f"urate-{exi_i}-value": fake_urate_decimal()})
                exi_i += 1
            # Otherwise, if the urate is a Urate and not a Decimal it needs to be marked for deletion in the formset
            elif isinstance(urate, Urate):
                data.update(create_urate_data(exi_i, urate))
                data.update({f"urate-{exi_i}-DELETE": "on"})
                exi_i += 1
    if urates is not None:
        new_urates = len(urates)
    else:
        new_urates = random.randint(0, 5)
    data.update(
        {
            "urate-INITIAL_FORMS": init_urate_len,
            "urate-TOTAL_FORMS": init_urate_len + new_urates,
        }
    )
    if urates is not None:
        for i, urate in enumerate(urates):
            data.update(create_urate_data(init_urate_len + i, urate))
    else:
        for i in range(new_urates):
            data.update(create_urate_data(init_urate_len + i))
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
        mhs=PPX_MEDHISTORYS,
        mh_dets=[MedHistoryTypes.GOUT],
        user=user,
    ).create(mhs_specified=True, **kwargs)


class PpxFactory(DjangoModelFactory):
    class Meta:
        model = Ppx

    starting_ult = factory.fuzzy.FuzzyChoice(BOOL_CHOICES, getter=lambda c: c[0])
