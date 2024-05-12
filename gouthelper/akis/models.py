from typing import TYPE_CHECKING

from django.conf import settings  # type: ignore
from django.db import models  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..rules import add_object, change_object, delete_object, view_object
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
                check=(
                    models.Q(user__isnull=False, ckd__isnull=True, dateofbirth__isnull=True, gender__isnull=True)
                    | models.Q(user__isnull=True)
                ),
            ),
        ]

    ckd = models.ForeignKey(
        "medhistorys.Ckd",
        on_delete=models.CASCADE,
        related_name="akis",
        verbose_name=_("CKD"),
    )
    dateofbirth = models.OneToOneField(
        "dateofbirths.DateOfBirth",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    gender = models.OneToOneField(
        "genders.Gender",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    history = HistoricalRecords()

    objects = models.Manager()
