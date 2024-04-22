import pytest

from ..choices import DialysisChoices, DialysisDurations, Stages
from .factories import CkdDetailFactory, GoutDetailFactory

pytestmark = pytest.mark.django_db


def test__dialysis_post_generation():
    ckddetail = CkdDetailFactory(on_dialysis=True)
    assert ckddetail.dialysis is True
    assert ckddetail.dialysis_type in DialysisChoices.values
    assert ckddetail.dialysis_duration in DialysisDurations.values
    assert ckddetail.stage == Stages.FIVE


def test__goutdetail_factory_ppx_conditional():
    gd = GoutDetailFactory(ppx_conditional=True)
    assert gd.flaring
    assert gd.at_goal
    assert (gd.on_ppx) is False
    assert gd.on_ult


def test__goutdetail_factory_ppx_indicated():
    gd = GoutDetailFactory(ppx_indicated=True)
    assert gd.flaring
    assert gd.at_goal
    assert (gd.on_ppx) is False
    assert (gd.on_ult) is False


def test__goutdetail_factory_ppx_not_indicated():
    gd = GoutDetailFactory(ppx_not_indicated=True)
    assert (gd.flaring) is False
    assert (gd.at_goal) is False
    assert (gd.on_ppx) is False
    assert (gd.on_ult) is False


def test__goutdetail_factory_consistently_passes():
    for _ in range(10):
        assert GoutDetailFactory()
