from django.db.models import Manager, QuerySet  # type: ignore

from .selectors import ult_userless_relations


class UltQuerySet(QuerySet):
    def related_objects(self) -> QuerySet:
        return ult_userless_relations(self)


class UltManager(Manager):
    def get_queryset(self) -> QuerySet:
        return UltQuerySet(self.model, using=self._db).related_objects()
