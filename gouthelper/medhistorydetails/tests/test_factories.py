import pytest

from ..choices import DialysisChoices, DialysisDurations, Stages
from .factories import CkdDetailFactory

pytestmark = pytest.mark.django_db


def test__dialysis_post_generation():
    ckddetail = CkdDetailFactory(on_dialysis=True)
    assert ckddetail.dialysis is True
    assert ckddetail.dialysis_type in DialysisChoices.values
    assert ckddetail.dialysis_duration in DialysisDurations.values
    assert ckddetail.stage == Stages.FIVE
