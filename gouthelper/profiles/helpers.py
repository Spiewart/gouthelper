from typing import TYPE_CHECKING

from django.utils import timezone

from ..dateofbirths.selectors import annotate_pseudopatient_queryset_with_age
from ..users.models import Pseudopatient

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
        Pseudopatient.objects.select_related(
            "dateofbirth__value",
            "gender__value",
            "pseudopatientprofile__provider",
        ).filter(
            pseudopatientprofile__provider=provider,
            created__date=todays_date,
        )
    )

    # Count of related pseudopatients with the same age, gender, and created date
    alias_conflicts = queryset.filter(
        age=age,
        gender__value=gender,
    ).count()
    print("printing alias_conflicts")
    print(alias_conflicts)
    print(provider)
    print(age)
    print(gender)
    return alias_conflicts if alias_conflicts else None
