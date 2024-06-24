from typing import TYPE_CHECKING, Union

from django.conf import settings  # type: ignore
from django.db import models  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..labs.helpers import labs_check_chronological_order_by_date_drawn
from ..rules import add_object, change_object, delete_object, view_object
from ..utils.helpers import get_qs_or_set
from ..utils.models import GoutHelperAidModel, GoutHelperModel
from .choices import Statuses

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    from ..genders.choices import Genders
    from ..labs.models import Creatinine
    from ..medhistorys.models import MedHistory

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
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_status_is_valid",
                check=models.Q(status__in=Statuses.values),
            ),
        ]

    Statuses = Statuses

    status = models.CharField(
        choices=Statuses.choices,
        default=Statuses.ONGOING,
        help_text=_("The status of this AKI."),
        max_length=20,
        verbose_name=_("Status"),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    history = HistoricalRecords()

    objects = models.Manager()

    @cached_property
    def age(self) -> int | None:
        return self.user.age if self.user else self.flare.age if hasattr(self, "flare") else None

    @cached_property
    def ckd(self) -> Union["MedHistory", None]:
        return self.flare.ckd if hasattr(self, "flare") else None

    @cached_property
    def creatinines(self) -> list["Creatinine"] | models.QuerySet["Creatinine"]:
        list_or_qs = get_qs_or_set(self, "creatinine")
        if isinstance(list_or_qs, models.QuerySet):
            list_or_qs = list_or_qs.order_by("-date_drawn")
        else:
            labs_check_chronological_order_by_date_drawn(list_or_qs)
        return list_or_qs

    @cached_property
    def gender(self) -> Union["Genders", None]:
        return self.user.gender.value if self.user else self.flare.gender.value if hasattr(self, "flare") else None

    @cached_property
    def improving_with_creatinines(self) -> bool:
        return self.status == Statuses.IMPROVING and self.creatinines

    @cached_property
    def most_recent_creatinine(self) -> "Creatinine":
        return self.creatinines.first() if isinstance(self.creatinines, models.QuerySet) else self.creatinines[0]

    @cached_property
    def resolved(self) -> bool:
        return self.status == Statuses.RESOLVED
