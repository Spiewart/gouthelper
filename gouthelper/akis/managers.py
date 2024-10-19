from django.db.models import Manager  # type: ignore

from .selectors import akis_related_objects_qs


class AkiManager(Manager):
    def get_queryset(self):
        return akis_related_objects_qs(super().get_queryset())
