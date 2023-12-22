import rules
from django.contrib.auth import get_user_model

User = get_user_model()


@rules.predicate
def is_user(user, profile):
    return getattr(profile, "user") == user


@rules.predicate
def is_provider(user, profile):
    if getattr(profile, "provider", None):
        return getattr(profile, "provider") == user
    return False


view_profile = is_user | is_provider

rules.add_rule("can_view_profile", view_profile)
rules.add_perm("profiles.view_profile", view_profile)
