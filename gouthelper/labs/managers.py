from django.db.models import Manager

from .selectors import baselinelab_relations, urates_related_objects_qs


class BaselineCreatinineManager(Manager):
    def get_queryset(self):
        return baselinelab_relations(super().get_queryset())


class UrateManager(Manager):
    def get_queryset(self):
        return urates_related_objects_qs(super().get_queryset())
