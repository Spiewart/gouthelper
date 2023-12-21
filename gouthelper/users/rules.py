import rules

from .choices import Roles


@rules.predicate
def has_no_provider(_, obj):
    """Expects a User object as the second argument."""
    try:
        return getattr(obj.profile, "provider") is None
    except AttributeError:
        return False


@rules.predicate
def is_patient(obj, user):
    """Expects a User object."""
    return obj == user


@rules.predicate
def is_an_admin(user):
    """Expects a User object."""
    return user.role == Roles.ADMIN


@rules.predicate
def is_provider(user, obj):
    """Expects User objects for both arguments."""
    try:
        return getattr(obj.profile, "provider") == user
    except AttributeError:
        return False


@rules.predicate
def is_a_provider(user):
    """Expects a User object."""
    return user.role == Roles.PROVIDER


@rules.predicate
def is_not_pseudopatient(user):
    """Expects a User object."""
    return user.role != Roles.PSEUDOPATIENT if user else True


@rules.predicate
def provider_kwarg_is_provider(user, obj):
    """Expects a string or None as obj."""
    return obj == user.username if obj else True


@rules.predicate
def user_is_provider(user, obj):
    """Expects a User object and string or None as obj."""
    return user.username == obj if obj else True


@rules.predicate
def list_belongs_to_user(user, obj):
    """Expects a User object and string or None as obj."""
    return user.username == obj if obj else False


add_user_with_provider = is_an_admin | is_a_provider
change_user = has_no_provider | is_patient | is_provider
delete_user = is_patient | is_provider
view_user = has_no_provider | is_patient | is_provider
view_provider_list = list_belongs_to_user

rules.add_rule("can_add_user", is_not_pseudopatient)
rules.add_perm("users.can_add_user", is_not_pseudopatient)
rules.add_rule("can_add_user_with_provider", add_user_with_provider)
rules.add_perm("users.can_add_user_with_provider", add_user_with_provider)
rules.add_rule("can_add_user_with_specific_provider", provider_kwarg_is_provider)
rules.add_perm("users.can_add_user_with_specific_provider", provider_kwarg_is_provider)
rules.add_rule("can_delete_user", delete_user)
rules.add_rule("can_edit_user", change_user)
rules.add_rule("can_view_user", view_user)
rules.add_rule("can_view_provider_list", view_provider_list)
rules.add_perm("users.can_view_provider_list", view_provider_list)
