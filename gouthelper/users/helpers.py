from django.urls import reverse  # pylint:disable=E0401  # type: ignore
from django.utils import timezone  # pylint:disable=E0401  # type: ignore

from .selectors import pseudopatient_count_for_provider_with_todays_date_in_username


def get_user_change(instance, request, **kwargs):  # pylint:disable=W0613
    # https://django-simple-history.readthedocs.io/en/latest/user_tracking.html
    """Method for django-simple-history to assign the user who made the change
    to the HistoricalUser history_user field. Written to deal with the case where
    the User is deleting his or her own profile and setting the history_user
    to the User's id will result in an IntegrityError."""
    # Check if the user is authenticated and the user is the User instance
    # and if the url for the request is for the User's deletion
    if request and request.user and request.user.is_authenticated:
        if request.user == instance and request.path.endswith(reverse("users:delete")):
            # Set the history_user to None
            return None
        else:
            # Otherwise, return the request.user
            return request.user
    else:
        # Otherwise, return None
        return None


def create_pseudopatient_username_for_new_user_for_provider(provider_username: str) -> str:
    current_date_pseudopatients = pseudopatient_count_for_provider_with_todays_date_in_username(provider_username)
    return provider_username + f" [{(timezone.now().date().strftime('%-m-%-d-%y'))}:{current_date_pseudopatients + 1}]"
