from django.db.models import Manager, QuerySet  # type: ignore

from .selectors import flareaid_userless_relations


class FlareAidQuerySet(QuerySet):
    def related_objects(self) -> QuerySet:
        return flareaid_userless_relations(self)


class FlareAidManager(Manager):
    def get_queryset(self) -> QuerySet:
        return FlareAidQuerySet(self.model, using=self._db).related_objects()
