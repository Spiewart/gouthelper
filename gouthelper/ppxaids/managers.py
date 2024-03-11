from django.db.models import Manager, QuerySet  # type: ignore

from .selectors import ppxaid_userless_relations


class PpxAidQuerySet(QuerySet):
    def related_objects(self) -> QuerySet:
        return ppxaid_userless_relations(self)


class PpxAidManager(Manager):
    def get_queryset(self) -> QuerySet:
        return PpxAidQuerySet(self.model, using=self._db).related_objects()
