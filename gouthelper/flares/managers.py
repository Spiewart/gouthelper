from django.db.models import Manager, QuerySet  # type: ignore

from .selectors import flare_userless_relations


class FlareQuerySet(QuerySet):
    def related_objects(self) -> QuerySet:
        return flare_userless_relations(self)


class FlareManager(Manager):
    def get_queryset(self) -> QuerySet:
        return FlareQuerySet(self.model, using=self._db).related_objects()
