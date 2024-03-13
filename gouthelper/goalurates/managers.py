from django.db.models import Manager, QuerySet  # type: ignore

from .selectors import goalurate_userless_relations


class GoalUrateQuerySet(QuerySet):
    def related_objects(self) -> QuerySet:
        return goalurate_userless_relations(self)


class GoalUrateManager(Manager):
    def get_queryset(self) -> QuerySet:
        return GoalUrateQuerySet(self.model, using=self._db).related_objects()
