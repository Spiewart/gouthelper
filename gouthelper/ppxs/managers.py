from django.db.models import Manager, QuerySet  # type: ignore

from .selectors import ppx_userless_relations


class PpxQuerySet(QuerySet):
    def related_objects(self) -> QuerySet:
        return ppx_userless_relations(self)


class PpxManager(Manager):
    def get_queryset(self) -> QuerySet:
        return PpxQuerySet(self.model, using=self._db).related_objects()
