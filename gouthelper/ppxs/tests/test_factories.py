from decimal import Decimal

import pytest

from ...choices import BOOL_CHOICES
from ...labs.models import Urate
from ...medhistorys.choices import MedHistoryTypes
from ..models import Ppx
from .factories import create_ppx, ppx_data_factory

pytestmark = pytest.mark.django_db


def test__ppx_data_factory():
    """Tests that the data factory returns a dict with the correct
    keys and values."""
    bool_bools = [tup[0] for tup in BOOL_CHOICES]
    data = ppx_data_factory()
    assert isinstance(data, dict)
    assert "starting_ult" in data
    assert data["starting_ult"] in bool_bools
    assert "flaring" in data
    assert data["flaring"] in bool_bools
    assert "hyperuricemic" in data
    assert data["hyperuricemic"] in bool_bools
    assert "on_ppx" in data
    assert data["on_ppx"] in bool_bools
    assert "on_ult" in data
    assert data["on_ult"] in bool_bools


def test__create_ppx_without_user():
    """Tests that the create_ppx function returns a Ppx object with the requisite
    MedHistory related objects."""
    ppx = create_ppx()
    assert isinstance(ppx, Ppx)
    assert ppx.medhistory_set.exists()
    assert MedHistoryTypes.GOUT in [mh.medhistorytype for mh in ppx.medhistory_set.all()]
    assert hasattr(ppx.gout, "goutdetail")
    assert hasattr(ppx, "urates_qs")
    if ppx.urates_qs:
        for urate in ppx.urates_qs:
            assert isinstance(urate, Urate)
            assert urate.value


def test__create_ppx_with_user():
    """Tests that the create_ppx function returns a Ppx object with the requisite
    MedHistory related objects and a user."""
    ppx = create_ppx(user=True)
    assert isinstance(ppx, Ppx)
    assert not ppx.medhistory_set.exists()
    assert ppx.user
    assert ppx.user.medhistory_set.exists()
    assert MedHistoryTypes.GOUT in [mh.medhistorytype for mh in ppx.user.medhistory_set.all()]
    assert hasattr(ppx.user.gout, "goutdetail")
    assert hasattr(ppx, "urates_qs")
    if ppx.urates_qs:
        for urate in ppx.urates_qs:
            assert isinstance(urate, Urate)
            assert urate.value
            assert urate.user == ppx.user


def test__create_ppx_with_urates():
    """Tests that the create_ppx function returns a Ppx object with the requisite
    MedHistory related objects and Urates with the supplied values."""
    ppx = create_ppx(user=True, labs=[Decimal("15.0"), Decimal("12.0")])
    assert isinstance(ppx, Ppx)
    assert not ppx.medhistory_set.exists()
    assert ppx.user
    assert ppx.user.medhistory_set.exists()
    assert MedHistoryTypes.GOUT in [mh.medhistorytype for mh in ppx.user.medhistory_set.all()]
    assert hasattr(ppx.user.gout, "goutdetail")
    assert hasattr(ppx, "urates_qs")
    assert next(iter([urate for urate in ppx.urates_qs if urate.value == Decimal("15.0")]))
    assert next(iter([urate for urate in ppx.urates_qs if urate.value == Decimal("12.0")]))
    for urate in ppx.urates_qs:
        assert isinstance(urate, Urate)
        assert urate.user == ppx.user
