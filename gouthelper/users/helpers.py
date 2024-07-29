from typing import TYPE_CHECKING

from django.urls import reverse  # pylint:disable=E0401  # type: ignore

if TYPE_CHECKING:
    from django.config.auth import get_user_model  # pylint:disable=E0401  # type: ignore

    User = get_user_model()


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
