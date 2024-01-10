"""Project-level rules for object-level permissions for objects that have
an optional user field. This is the majority of models in GoutHelper."""

import rules
from django.contrib.auth import get_user_model

from .users.choices import Roles

User = get_user_model()


@rules.predicate
def anon_obj_creation(_, obj):
    """Checks if the object intended to be created has a provider. This is
    accomplished by setting the get_permission_object function on the view
    to check for if the user defined by the username kwarg has a provider and
    return the provider as the permission object if so.

    Expects a str or None as obj."""
    if isinstance(obj, User):
        return (
            True
            if getattr(obj, "profile") and hasattr(obj.profile, "provider") and obj.profile.provider is None
            else False
        )
    else:
        return True if obj is None else False


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
    return obj.user.profile.provider is None if obj.user else True


@rules.predicate
def is_obj_provider(user, obj):
    """Checks if the request.user is the provider for the object's user.

    Expects an object with an optional user field."""
    return obj.user.pseudopatientprofile.provider == user if obj.user else False


add_object = (
    anon_obj_creation | (is_a_provider & request_user_kwarg_provider) | (is_an_admin & request_user_kwarg_provider)
)
change_object = is_anon_obj | is_obj_provider
delete_object = is_obj_provider
view_object = is_anon_obj | is_obj_provider
view_object_list = (is_a_provider & request_user_kwarg_provider_or_user) | (
    is_an_admin & request_user_kwarg_provider_or_user
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
