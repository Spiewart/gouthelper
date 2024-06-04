from typing import TYPE_CHECKING

from ..labs.helpers import labs_check_chronological_order_by_date_drawn

if TYPE_CHECKING:
    from ..labs.models import Creatinine


def akis_aki_is_resolved_via_creatinines(creatinines: list["Creatinine"]) -> bool:
    if not creatinines:
        return False
    labs_check_chronological_order_by_date_drawn(labs=creatinines)
