from typing import TYPE_CHECKING, Union

from ..labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from .choices import Stages

if TYPE_CHECKING:
    from decimal import Decimal

    from ..genders.choices import Genders
    from .choices import DialysisChoices, DialysisDurations


class CkdDetailProcessor:
    def __init__(
        self,
        dialysis: bool,
        stage: Stages | None,
        dialysis_type: Union["DialysisChoices", None],
        dialysis_duration: Union["DialysisDurations", None],
        age: int | None,
        baselinecreatinine: Union["Decimal", None],
        gender: Union["Genders", None],
    ):
        self.dialysis = dialysis
        self.stage = stage
        self.dialysis_type = dialysis_type
        self.dialysis_duration = dialysis_duration
        self.age = age
        self.baselinecreatinine = baselinecreatinine
        self.gender = gender

    def get_errors(self) -> dict[str, str]:
        errors = self.get_arg_errors()
        return errors if errors else self.get_stage_errors()

    def get_arg_errors(self) -> dict[str, str]:
        errors = {}

        if not self.dialysis and not self.stage and not self.baselinecreatinine:
            msg = "Stage or a baseline creatinine is required to calculate a stage if not on dialysis."
            errors["stage"] = msg
            errors["baselinecreatinine"] = msg
        elif not self.dialysis and self.baselinecreatinine and not self.can_calculate_stage:
            if not self.age:
                errors["age"] = "Age is required to interpret a baseline creatinine."
            if not self.gender:
                errors["gender"] = "Gender is required to interpret a baseline creatinine."
        elif self.dialysis:
            if not self.dialysis_type or not self.dialysis_duration:
                if not self.dialysis_type:
                    errors["dialysis_type"] = "Dialysis type is required if on dialysis."
                if not self.dialysis_duration:
                    errors["dialysis_duration"] = "Dialysis duration is required if on dialysis."

        return errors

    @property
    def can_calculate_stage(self) -> bool:
        return self.age and self.baselinecreatinine and self.gender is not None

    def get_stage_errors(self) -> dict[str, str]:
        errors = {}

        if self.dialysis and self.stage and self.stage != Stages.FIVE:
            errors["stage"] = "Stage must be 5 if on dialysis."
        elif self.stage and self.can_calculate_stage and self.stage != self.calculated_stage:
            msg = (
                f"Stage ({self.stage}) does not match stage calculated from baseline creatinine"
                f" ({self.calculated_stage})."
            )
            errors["stage"] = msg

        return errors

    @property
    def calculated_stage(self) -> Stages:
        return labs_stage_calculator(
            labs_eGFR_calculator(
                creatinine=self.baselinecreatinine,
                age=self.age,
                gender=self.gender,
            )
        )
