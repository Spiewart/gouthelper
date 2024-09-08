from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from rules.contrib.rest_framework import AutoPermissionViewSetMixin


class PseudopatientAddPermissionViewSetMixin:

    """
    Custom permission mixin for the PseudopatientViewSet that adds a new permission type
    for the provider_create action. Rather than calling get_object(), which is set on the ViewSet
    to retrieve a Pseudopatient object instance, we are call the view's provider cached_property
    to retrieve the Provider object instance via the username kwarg.
    """

    permission_type_map = {
        **AutoPermissionViewSetMixin.permission_type_map,
        "provider_create": "add_pseudopatient_with_provider",
    }

    def initial(self, *args, **kwargs):
        """Ensures user has permission to perform the requested action."""
        super().initial(*args, **kwargs)
        if not self.request.user:
            # No user, don't check permission
            return

        # Get the handler for the HTTP method in use
        try:
            if self.request.method.lower() not in self.http_method_names:
                raise AttributeError
            handler = getattr(self, self.request.method.lower())
        except AttributeError:
            # method not supported, will be denied anyway
            return

        try:
            perm_type = self.permission_type_map[self.action]
        except KeyError as exc:
            raise ImproperlyConfigured(
                "AutoPermissionViewSetMixin tried to authorize a request with the "
                "{!r} action, but permission_type_map only contains: {!r}".format(
                    self.action, self.permission_type_map
                )
            ) from exc
        if perm_type is None:
            # Skip permission checking for this action
            return

        # Determine whether we've to check object permissions (for detail actions)
        obj = None
        extra_actions = self.get_extra_actions()
        # We have to access the unbound function via __func__
        if handler.__func__ in extra_actions:
            if handler.detail:
                obj = self.get_object()
            elif self.action == "provider_create":
                obj = self.provider
        elif self.action not in ("create", "list"):
            obj = self.get_object()

        # Finally, check permission
        perm = self.get_queryset().model.get_perm(perm_type)
        if not self.request.user.has_perm(perm, obj):
            raise PermissionDenied
