from typing import TYPE_CHECKING

from django.apps import apps
from django.utils import timezone

from ..dateofbirths.selectors import annotate_pseudopatient_queryset_with_age
from ..users.selectors import pseudopatient_filter_age_gender

if TYPE_CHECKING:
    from django.config.auth import get_user_model  # pylint:disable=E0401  # type: ignore

    from ..genders.choices import Genders

    User = get_user_model()


def get_provider_alias(
    provider: "User",
    age: int,
    gender: "Genders",
) -> int | None:
    todays_date = timezone.now().date()

    queryset = annotate_pseudopatient_queryset_with_age(
        apps.get_model("users.Pseudopatient")
        .objects.select_related(
            "dateofbirth",
            "gender",
            "pseudopatientprofile__provider",
        )
        .filter(
            pseudopatientprofile__provider=provider,
            created__date=todays_date,
        )
    )

    # Count of related pseudopatients with the same age, gender, and created date
    alias_conflicts = pseudopatient_filter_age_gender(
        qs=queryset,
        age=age,
        gender=gender,
    ).count()

    return alias_conflicts + 1
