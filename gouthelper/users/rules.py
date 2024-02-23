import rules

from .choices import Roles


@rules.predicate
def has_no_provider(_, obj):
    """Expects a User object as the second argument."""
    try:
        return getattr(obj.pseudopatientprofile, "provider") is None
    except AttributeError:
        try:
            return getattr(obj.patientprofile, "provider") is None
        except AttributeError:
            return False


@rules.predicate
def is_user(obj, user):
    """Expects a User object."""
    return obj == user


@rules.predicate
def is_an_admin(user):
    """Expects a User object."""
    return user.role == Roles.ADMIN if hasattr(user, "role") else False


@rules.predicate
def is_provider(user, obj):
    """Expects User objects for both arguments."""
    try:
        return getattr(obj.pseudopatientprofile, "provider", None) == user
    except AttributeError:
        try:
            return getattr(obj.patientprofile, "provider", None) == user
        except AttributeError:
            return False


@rules.predicate
def is_a_provider(user):
    """Expects a User object."""
    return user.role == Roles.PROVIDER if hasattr(user, "role") else False


@rules.predicate
def is_not_pseudopatient(user):
    """Expects a User object."""
    if user.is_authenticated:
        return user.role != Roles.PSEUDOPATIENT if user else True
    else:
        return True


@rules.predicate
def is_pseudopatient(_, obj):
    """Expects a User object."""
    return obj.role == Roles.PSEUDOPATIENT


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


is_providerless_pseudopatient = is_pseudopatient & has_no_provider

add_user_with_provider = (is_an_admin | is_a_provider) & provider_kwarg_is_provider
change_user = is_user | is_provider
change_pseudopatient = is_providerless_pseudopatient | is_user | is_provider
delete_user = is_user | is_provider
view_user = is_providerless_pseudopatient | is_user | is_provider
view_provider_list = list_belongs_to_user

rules.add_rule("can_add_user", is_not_pseudopatient)
rules.add_perm("users.can_add_user", is_not_pseudopatient)
rules.add_rule("can_add_user_with_provider", add_user_with_provider)
rules.add_perm("users.can_add_user_with_provider", add_user_with_provider)
rules.add_rule("can_delete_user", delete_user)
rules.add_perm("users.can_delete_user", delete_user)
rules.add_rule("can_edit_user", change_user)
rules.add_perm("users.can_edit_user", change_user)
rules.add_rule("can_edit_pseudopatient", change_pseudopatient)
rules.add_perm("users.can_edit_pseudopatient", change_pseudopatient)
rules.add_rule("can_view_user", view_user)
rules.add_perm("users.can_view_user", view_user)
rules.add_rule("can_view_provider_list", view_provider_list)
rules.add_perm("users.can_view_provider_list", view_provider_list)
