from typing import TYPE_CHECKING

from django.conf import settings  # type: ignore
from django.db import models  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..rules import add_object, change_object, delete_object, view_object
from ..utils.helpers import get_qs_or_set
from ..utils.models import GoutHelperAidModel, GoutHelperModel

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    User = get_user_model()


class Aki(
    RulesModelMixin,
    GoutHelperAidModel,
    GoutHelperModel,
    TimeStampedModel,
    metaclass=RulesModelBase,
):
    class Meta:
        rules_permissions = {
            "add": add_object,
            "change": change_object,
            "delete": delete_object,
            "view": view_object,
        }
        constraints = [
            # If there's a User, there can be no associated Ppx objects
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_user_ppx_exclusive",
                check=(models.Q(user__isnull=False) | models.Q(user__isnull=True)),
            ),
        ]

    resolved = models.BooleanField(
        default=False,
        help_text=_("Has this AKI resolved? (i.e., has the creatinine level returned to normal?)"),
        verbose_name=_("Resolved"),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    history = HistoricalRecords()

    objects = models.Manager()

    @cached_property
    def creatinines(self):
        return get_qs_or_set(self, "creatinine")
