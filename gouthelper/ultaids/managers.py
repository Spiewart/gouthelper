from django.db.models import Manager, QuerySet  # type: ignore

from .selectors import ultaid_relations


class UltAidQuerySet(QuerySet):
    def related_objects(self) -> QuerySet:
        return ultaid_relations(self)


class UltAidManager(Manager):
    def get_queryset(self) -> QuerySet:
        return UltAidQuerySet(self.model, using=self._db).related_objects()
