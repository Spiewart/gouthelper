"""Project-level rules for object-level permissions for objects that have
an optional user field. This is the majority of models in GoutHelper."""

import rules
from django.contrib.auth import get_user_model

from .users.choices import Roles

User = get_user_model()


@rules.predicate
def anon_obj_creation(_, obj):
    """Checks if the object intended to be created has a user. This is
    accomplished by setting the get_permission_object function on the view
    to check for a username kwarg.

    Expects a str or None as obj."""
    return True if obj is None else False


@rules.predicate
def request_user_is_username_kwarg_provider(user, obj):
    """Checks if the request.user.username is the same as the provider
    for the user object associated with a username kwarg via his or her
    profile.

    Expects a str or None as obj."""
    return User.objects.get(username=obj).profile.provider == user


@rules.predicate
def is_an_admin(user):
    return user.role == Roles.ADMIN


@rules.predicate
def is_a_provider(user):
    return user.role == Roles.PROVIDER


@rules.predicate
def is_anon_obj(_, obj):
    """Checks if the object is an anonymous object, in that it has a user
    field that is None.

    Expects an object with an optional user field."""
    return obj.user is None


@rules.predicate
def is_obj_provider(user, obj):
    """Checks if the request.user is the provider for the object's user.

    Expects an object with an optional user field."""

    return obj.user.profile.provider == user if obj.user else False


add_object = (
    anon_obj_creation
    | (is_a_provider & request_user_is_username_kwarg_provider)
    | (is_an_admin & request_user_is_username_kwarg_provider)
)
change_object = is_anon_obj | is_obj_provider
delete_object = is_obj_provider
view_object = is_anon_obj | is_obj_provider
view_object_list = (is_a_provider & request_user_is_username_kwarg_provider) | (
    is_an_admin & request_user_is_username_kwarg_provider
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
