from typing import TYPE_CHECKING, Union

from django.db.models import Manager  # type: ignore

from .selectors import ckddetail_relations
from .services import CkdDetailCreator

if TYPE_CHECKING:
    from decimal import Decimal

    from ..genders.choices import Genders
    from ..medhistorys.models import Ckd
    from .choices import DialysisChoices, DialysisDurations, Stages


class CkdDetailManager(Manager):
    def get_queryset(self):
        return ckddetail_relations(super().get_queryset())

    def api_create(
        self,
        ckd: "Ckd",
        dialysis: bool | None,
        dialysis_type: Union["DialysisChoices", None],
        dialysis_duration: Union["DialysisDurations", None],
        stage: Union["Stages", None],
        age: int | None,
        baselinecreatinine: Union["Decimal", None],
        gender: Union["Genders", None],
        **kwargs,
    ):
        return CkdDetailCreator(
            ckddetail=None,
            ckd=ckd,
            dialysis=dialysis,
            dialysis_type=dialysis_type,
            dialysis_duration=dialysis_duration,
            stage=stage,
            age=age,
            baselinecreatinine=baselinecreatinine,
            gender=gender,
        ).create()
