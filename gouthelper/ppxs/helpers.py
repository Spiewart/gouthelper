from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..goalurates.choices import GoalUrates
    from ..labs.models import Urate
    from ..medhistorydetails.models import GoutDetail


def ppxs_check_urate_hyperuricemic_discrepant(
    urate: "Urate",
    goutdetail: "GoutDetail",
    goalurate: "GoalUrates",
) -> bool:
    """Check if the urate and goutdetail hyperuricemic fields are discrepant."""
    return goutdetail.hyperuricemic != (urate.value > goalurate) if goutdetail.hyperuricemic is not None else False


def ppxs_urate_hyperuricemic_discrepancy_str(
    urate: "Urate",
    goutdetail: "GoutDetail",
    goalurate: "GoalUrates",
) -> str:
    """Return a string describing the discrepancy between the urate and goutdetail hyperuricemic fields."""
    if goutdetail.hyperuricemic is None:
        return "Clarify hyperuricemic status. At least one uric acid was reported but hyperuricemic was not."
    elif (urate.value > goalurate) and not goutdetail.hyperuricemic:
        return "Clarify hyperuricemic status. Last Urate was above goal, but hyperuricemic reported False."
    elif (urate.value <= goalurate) and goutdetail.hyperuricemic:
        return "Clarify hyperuricemic status. Last Urate was at goal, but hyperuricemic reported True."
