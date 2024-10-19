from django.db.models import Manager

from .selectors import urates_related_objects_qs


class UrateManager(Manager):
    def get_queryset(self):
        return urates_related_objects_qs(super().get_queryset())
