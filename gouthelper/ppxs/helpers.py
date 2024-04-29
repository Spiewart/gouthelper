from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    from ..goalurates.choices import GoalUrates
    from ..labs.models import Urate
    from ..medhistorydetails.models import GoutDetail
    from .models import Ppx

    User = get_user_model()


def assign_ppx_attrs_from_user(ppx: "Ppx", user: "User") -> "Ppx":
    """Transfers medhistorys_qs and urates_qs from a User object to a Ppx object."""
    ppx.medhistorys_qs = user.medhistorys_qs
    ppx.urates_qs = user.urates_qs
    return ppx


def ppxs_check_urate_at_goal_discrepant(
    urate: "Urate",
    goutdetail: "GoutDetail",
    goalurate: "GoalUrates",
) -> bool:
    """Check if the urate and goutdetail hyperuricemic fields are discrepant."""
    return goutdetail.at_goal != (urate.value <= goalurate)
