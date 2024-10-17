from typing import TYPE_CHECKING, Literal, Union

from django.conf import settings  # type: ignore
from django.db import models  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..dateofbirths.helpers import age_calc
from ..labs.helpers import labs_check_chronological_order_by_date_drawn
from ..rules import add_object, change_object, delete_object, view_object
from ..utils.helpers import get_qs_or_set
from ..utils.models import GoutHelperAidModel, GoutHelperModel
from .choices import Statuses
from .managers import AkiManager, AkiUserManager

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
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_status_is_valid",
                check=models.Q(status__in=Statuses.values),
            ),
        ]

    Statuses = Statuses
    user_foreign_key_fields: list[Literal["creatinine"]] = ["creatinine"]

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
    related_objects = AkiManager()
    related_user_objects = AkiUserManager()

    @cached_property
    def age(self) -> int | None:
        return (
            age_calc(self.user.dateofbirth.value) if self.user else self.flare.age if hasattr(self, "flare") else None
        )

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
    def improving_with_creatinines_but_not_at_baselinecreatinine(self) -> bool:
        return self.improving_with_creatinines and (
            self.baselinecreatinine and not self.most_recent_creatinine.is_at_baseline and self.has_age_and_gender
        )

    @cached_property
    def improving_with_creatinines_stage_age_gender_no_baselinecreatinine(self) -> bool:
        return self.improving_with_creatinines and (
            not self.baselinecreatinine and self.stage and self.has_age_and_gender
        )

    @cached_property
    def improving_with_creatinines_age_gender_no_stage_or_baselinecreatinine(self) -> bool:
        return self.improving_with_creatinines and (
            not self.stage and not self.baselinecreatinine and self.has_age_and_gender
        )

    @cached_property
    def has_age_and_gender(self) -> bool:
        return self.age and self.gender is not None

    @cached_property
    def most_recent_creatinine(self) -> "Creatinine":
        return self.creatinines.first() if isinstance(self.creatinines, models.QuerySet) else self.creatinines[0]

    @cached_property
    def resolved(self) -> bool:
        return self.status == Statuses.RESOLVED

    def __str__(self) -> str:
        return f"AKI, {self.get_status_display()}"

    def update(self, status: Statuses) -> None:
        if self.status != status:
            self.status = status
            self.save()
