from typing import TYPE_CHECKING, Union

from ..labs.helpers import labs_check_chronological_order_by_date_drawn
from .choices import Statuses

if TYPE_CHECKING:
    from ..labs.models import BaselineCreatinine, Creatinine


class CreatinineProcessor:
    def __init__(
        self,
        aki_value: bool,
        status: Statuses,
        creatinines: list["Creatinine"],
        baselinecreatinine: Union["BaselineCreatinine", None],
        # stage: Stages | None,
    ):
        self.aki_value = aki_value
        self.status = status
        self.creatinines = creatinines
        labs_check_chronological_order_by_date_drawn(self.creatinines)
        self.baselinecreatinine = baselinecreatinine
        # self.labs_creatinines_update_baselinecreatinine()
        self.aki_errors = {}
        self.creatinines_errors = {}
        self.baselinecreatinine_errors = {}
        self.errors: dict = {}
