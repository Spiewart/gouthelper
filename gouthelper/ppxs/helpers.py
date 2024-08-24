from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    from ..goalurates.choices import GoalUrates
    from ..labs.models import Urate
    from ..medhistorydetails.models import GoutDetail

    User = get_user_model()


def ppxs_check_urate_at_goal_discrepant(
    urate: "Urate",
    goutdetail: "GoutDetail",
    goal_urate: "GoalUrates",
) -> bool:
    """Check if the urate and goutdetail hyperuricemic fields are discrepant."""
    return goutdetail.at_goal != (urate.value <= goal_urate)
