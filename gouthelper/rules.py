"""Project-level rules for object-level permissions for objects that have
an optional user field. This is the majority of models in GoutHelper."""

import rules
from django.contrib.auth import get_user_model

from .users.choices import Roles

User = get_user_model()


@rules.predicate
def anon_user(_, obj):
    """Checks if the object is an anonymous user, in that they do not have
    a provider. This is for views that set the get_permission_object function
    to return the user defined by the username kwarg. If the permission object
    is None, then the object does not have an intended User and is therefore
    anonymous.

    Expects a str or None as obj."""
    # Check if the permission object is a User
    if isinstance(obj, User):
        # If so, check if the User has a profile and if the profile has a provider
        return getattr(obj, "profile", False) and not getattr(obj.profile, "provider", None)
    # If not, check if the permission object is None
    else:
        return True if obj is None else False


@rules.predicate
def is_an_admin(user):
    return hasattr(user, "role") and user.role == Roles.ADMIN


@rules.predicate
def is_a_provider(user):
    return hasattr(user, "role") and user.role == Roles.PROVIDER


@rules.predicate
def is_anon_obj(_, obj):
    """Checks if the object is an anonymous object, in that it has a user
    field that is None.

    Expects an object with an optional user field."""
    return hasattr(obj.user, "profile") and obj.user.profile.provider is None if obj.user else True


@rules.predicate
def no_user(_, obj):
    """Checks if the request.user is None and that the object's user is None."""
    return not isinstance(obj, User) and (obj.user is None if hasattr(obj, "user") else True)


@rules.predicate
def is_obj_provider(user, obj):
    """Checks if the request.user is the provider for the object's user.

    Expects an object with an optional user field."""
    return obj.user.pseudopatientprofile.provider == user if obj.user else False


@rules.predicate
def request_user_kwarg_provider(user, obj):
    """Checks if the request.user.username is the same as the provider
    for the user object associated with a username kwarg via his or her
    profile.

    Expects a str or None as obj."""
    return (
        obj.profile.provider == user if obj and isinstance(obj, User) and hasattr(obj.profile, "provider") else False
    )


@rules.predicate
def request_user_kwarg_provider_or_user(user, obj):
    """Checks if the request.user.username is the same as the provider
    for the user object associated with a username kwarg via his or her
    profile.

    Expects a str or None as obj."""
    return (
        obj.profile.provider == user
        if obj and isinstance(obj, User) and hasattr(obj.profile, "provider")
        else obj == user
    )


add_object = (
    no_user | anon_user | (is_a_provider & request_user_kwarg_provider) | (is_an_admin & request_user_kwarg_provider)
)
change_object = no_user | is_anon_obj | is_obj_provider
delete_object = is_obj_provider
view_object = no_user | is_anon_obj | is_obj_provider
view_object_list = (
    anon_user
    | (is_a_provider & request_user_kwarg_provider_or_user)
    | (is_an_admin & request_user_kwarg_provider_or_user)
)

rules.add_rule("can_add_object", add_object)
rules.add_rule("can_change_object", change_object)
rules.add_rule("can_delete_object", delete_object)
rules.add_rule("can_view_object", view_object)
rules.add_rule("can_view_object_list", view_object_list)
rules.add_perm("can_add_object", add_object)
rules.add_perm("can_change_object", change_object)
rules.add_perm("can_delete_object", delete_object)
rules.add_perm("can_view_object", view_object)
rules.add_perm("can_view_object_list", view_object_list)
