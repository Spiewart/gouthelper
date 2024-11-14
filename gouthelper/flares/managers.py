from typing import TYPE_CHECKING

from django.db.models import Manager, QuerySet

from .selectors import flare_userless_relations

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # pylint:disable=E0401  # type: ignore

    User = get_user_model()


class FlareQuerySet(QuerySet):
    def related_objects(self) -> QuerySet:
        return flare_userless_relations(self)


class FlareManager(Manager):
    def get_queryset(self) -> QuerySet:
        return FlareQuerySet(self.model, using=self._db).related_objects()
