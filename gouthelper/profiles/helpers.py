from typing import TYPE_CHECKING

from django.urls import reverse
from django.utils import timezone

from ..dateofbirths.selectors import annotate_patient_queryset_with_age
from ..users.models import Patient
from ..users.selectors import patients_filter_age_gender

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

    queryset = annotate_patient_queryset_with_age(
        Patient.objects.select_related(
            "dateofbirth",
            "gender",
            "patientprofile__provider",
        ).filter(
            pseudopatientprofile__provider=provider,
            created__date=todays_date,
        )
    )

    # Count of related patients with the same age, gender, and created date
    alias_conflicts = patients_filter_age_gender(
        qs=queryset,
        age=age,
        gender=gender,
    ).count()

    return alias_conflicts + 1


def get_user_change(instance, request, **kwargs):
    # https://django-simple-history.readthedocs.io/en/latest/user_tracking.html
    """Method for django-simple-history to assign the user who made the change
    to the HistoricalProfile history_user field. Written to deal with the case where
    the User is deleting his or her own account and its associated profile and
    setting the history_user to the User's id will result in an IntegrityError."""
    # Check if the user is authenticated and the user is the User instance
    # and if the url for the request is for the User's deletion
    if request and request.user and request.user.is_authenticated:
        if request.user == instance.user and request.path.endswith(reverse("users:delete")):
            # Set the history_user to None
            return None
        else:
            # Otherwise, return the request.user
            return request.user
    else:
        # Otherwise, return None
        return None
