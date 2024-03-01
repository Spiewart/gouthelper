import random
from decimal import Decimal
from typing import Any

from factory.faker import faker  # pylint: disable=e0401 # type: ignore

from ...medhistorydetails.choices import DialysisChoices, DialysisDurations, Stages
from ...medhistorys.choices import MedHistoryTypes

fake = faker.Faker()

ModDialysisDurations = DialysisDurations.values
ModDialysisDurations.remove("")
ModStages = Stages.values
ModStages.remove(None)


def create_baselinecreatinine_value() -> Decimal:
    return fake.pydecimal(
        left_digits=2,
        right_digits=2,
        positive=True,
        min_value=2,
        max_value=10,
    )


def make_ckddetail_kwargs(
    mh_dets: dict[MedHistoryTypes : dict[str:Any]] | None = None,
):
    ckddetail_kwargs = mh_dets.get(MedHistoryTypes.CKD, {}) if mh_dets else {}
    d_kwarg = ckddetail_kwargs.get("dialysis", None) if ckddetail_kwargs else None
    d_val = d_kwarg if d_kwarg is not None else fake.boolean()
    ckddetail_kwargs.update({"dialysis": d_val})
    if d_val:
        d_d_kwarg = ckddetail_kwargs.get("dialysis_duration", None) if ckddetail_kwargs else None
        if not d_d_kwarg:
            d_d_val = random.choice(ModDialysisDurations)
            ckddetail_kwargs.update({"dialysis_duration": d_d_val})
        d_t_kwarg = ckddetail_kwargs.get("dialysis_type", None) if ckddetail_kwargs else None
        if not d_t_kwarg:
            d_t_val = random.choice(DialysisChoices.values)
            ckddetail_kwargs.update({"dialysis_type": d_t_val})
        ckddetail_kwargs.update({"stage": Stages.FIVE})
    else:
        stage_kwarg = ckddetail_kwargs.get("stage", None) if ckddetail_kwargs else None
        bc_kwarg = (
            ckddetail_kwargs.get("baselinecreatinine", None)
            if ckddetail_kwargs and "baselinecreatinine" in ckddetail_kwargs
            else mh_dets.get("baselinecreatinine", None)
            if mh_dets
            else None
        )
        if stage_kwarg or bc_kwarg:
            if stage_kwarg:
                ckddetail_kwargs.update({"stage": stage_kwarg})
            elif fake.boolean():
                ckddetail_kwargs.update({"stage": random.choice(ModStages)})
            if bc_kwarg:
                ckddetail_kwargs.update({"baselinecreatinine": bc_kwarg})
            elif fake.boolean():
                ckddetail_kwargs.update({"baselinecreatinine": create_baselinecreatinine_value()})
        else:
            if fake.boolean():
                ckddetail_kwargs.update({"baselinecreatinine": create_baselinecreatinine_value()})
            if fake.boolean():
                ckddetail_kwargs.update({"stage": random.choice(ModStages)})
    return ckddetail_kwargs
