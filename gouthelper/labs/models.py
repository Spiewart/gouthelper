from decimal import Decimal
from typing import TYPE_CHECKING, Literal, Union

from django.conf import settings  # type: ignore
from django.db import models  # type: ignore
from django.utils import timezone  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..choices import BOOL_CHOICES
from ..dateofbirths.helpers import age_calc
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.helpers import medhistory_attr, medhistorys_get_or_none
from ..utils.models import GoutHelperModel
from .choices import Abnormalitys, LowerLimits, Units, UpperLimits
from .helpers import (
    labs_creatinine_is_at_baseline_creatinine,
    labs_creatinine_within_range_for_stage,
    labs_eGFR_calculator,
    labs_stage_calculator,
)

if TYPE_CHECKING:
    from ..dateofbirths.models import DateOfBirth
    from ..genders.models import Gender
    from ..medhistorydetails.choices import Stages
    from ..medhistorydetails.models import CkdDetail
    from ..medhistorys.models import Ckd


class CreatinineBase(models.Model):
    class Meta:
        abstract = True

    LowerLimits = LowerLimits
    Units = Units
    UpperLimits = UpperLimits

    lower_limit = models.DecimalField(max_digits=4, decimal_places=2, default=LowerLimits.CREATININEMGDL)
    units = models.CharField(_("Units"), choices=Units.choices, max_length=10, default=Units.MGDL)
    upper_limit = models.DecimalField(max_digits=4, decimal_places=2, default=UpperLimits.CREATININEMGDL)
    value = models.DecimalField(
        max_digits=4,
        decimal_places=2,
    )

    @classmethod
    def medhistorytype(cls):
        return MedHistoryTypes.CKD

    @cached_property
    def value_str(self) -> str:
        return f"{self.value.quantize(Decimal('1.00'))} {self.get_units_display()}"

    def __str__(self):
        return f"Creatinine: {self.value.quantize(Decimal('1.00'))} {self.get_units_display()}"

    def calculate_eGFR(
        self: "BaselineCreatinine",
        age: int,
        gender: int,
    ) -> Decimal:  # type: ignore
        """
        Method for calculating eGFR.
        Requires age, gender, race, and a creatinine value.
        Required variables can be called with method or pulled from object's user's profile.
        """
        return labs_eGFR_calculator(creatinine=self.value, age=age, gender=gender)

    def calculate_stage(
        self: "BaselineCreatinine",
        age: int,
        gender: int,
    ) -> "Stages":  # type: ignore
        """Method that takes calculated eGFR and returns Ckd stage

        Returns:
            [Stages / int]: [CKD stage]
        """
        # self.eGFR returns a Decimal for labs_stage_calculator()
        return labs_stage_calculator(self.calculate_eGFR(age=age, gender=gender))


class LabBase(RulesModelMixin, GoutHelperModel, TimeStampedModel, metaclass=RulesModelBase):
    class Meta:
        abstract = True

    @cached_property
    def abnormality(self) -> Literal[Abnormalitys.HIGH] | None:
        if self.high:
            return Abnormalitys.HIGH
        else:
            return None

    @property
    def high(self):
        return self.value > self.upper_limit

    @property
    def low(self):
        return self.value < self.lower_limit


class BaselineLab(LabBase):
    class Meta:
        abstract = True

    medhistory = models.OneToOneField("medhistorys.MedHistory", on_delete=models.CASCADE)
    history = HistoricalRecords(inherit=True)


class Lab(LabBase):
    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                check=models.Q(date_drawn__lte=models.functions.Now()),
                name="%(app_label)s_%(class)s_date_drawn_not_in_future",
            ),
        ]

    date_drawn = models.DateTimeField(help_text="What day was this lab drawn?", default=timezone.now, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    history = HistoricalRecords(inherit=True)
    objects = models.Manager()

    def var_x_high(
        self,
        var: Decimal,
        baseline: None | Decimal = None,
    ) -> bool:
        """
        Calculates if a Lab value is higher by a percentage (var).
        If not var *arg, lab.upper_limit used for calculation.

        Args:
            var (Decimal): Percentage for calculating where the current Lab value is relative to baseline
            baseline (Decimal, optional): Baseline value for calculating where the current Lab value is relative to
                baseline. Defaults to None.
        Returns:
            bool: True if Lab.value is > var * baseline, False if not
        """
        return self.value > (Decimal(var) * baseline) if baseline else self.value > (Decimal(var) * self.upper_limit)

    def var_x_low(
        self,
        var: Decimal,
        baseline: None | Decimal = None,
    ) -> bool:
        """
        Calculates if a Lab value is lower by a percentage (var).
        If no var *arg, uses lab.lower_limit for comparison.

        Args:
            var (Decimal): Percentage for calculating where the current Lab value is relative to baseline
            baseline (Decimal, optional): Baseline value for calculating where the current Lab value is relative to
                baseline. Defaults to None.
        Returns:
            bool: True if Lab.value is < var * baseline, False if not
        """
        return self.value < (Decimal(var) * baseline) if baseline else self.value < (Decimal(var) * self.lower_limit)


class BaselineCreatinine(CreatinineBase, BaselineLab):
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(lower_limit=LowerLimits.CREATININEMGDL)
                    & models.Q(units=Units.MGDL)
                    & models.Q(upper_limit=UpperLimits.CREATININEMGDL)
                ),
                name="%(app_label)s_%(class)s_units_upper_lower_limits_valid",
            ),
        ]

    def __str__(self):
        return f"Baseline {super().__str__()}"


class Creatinine(CreatinineBase, Lab):
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(lower_limit=LowerLimits.CREATININEMGDL)
                    & models.Q(units=Units.MGDL)
                    & models.Q(upper_limit=UpperLimits.CREATININEMGDL)
                ),
                name="%(app_label)s_%(class)s_units_upper_lower_limits_valid",
            ),
        ]

    aki = models.ForeignKey(
        "akis.Aki",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    @cached_property
    def age(self):
        return age_calc(date_of_birth=self.dateofbirth.value) if self.dateofbirth else None

    @cached_property
    def ckd(self) -> Union["Ckd", None]:
        if self.user:
            return medhistory_attr(
                MedHistoryTypes.CKD, self.user, ["ckddetail", "baselinecreatinine"], medhistorys_get_or_none
            )
        elif self.aki and hasattr(self.aki, "flare"):
            return medhistory_attr(
                MedHistoryTypes.CKD, self.aki.flare, ["ckddetail", "baselinecreatinine"], medhistorys_get_or_none
            )
        else:
            return None

    @cached_property
    def ckddetail(self) -> Union["CkdDetail", None]:
        if self.ckd:
            return getattr(self.ckd, "ckddetail", None)
        else:
            return None

    @cached_property
    def baselinecreatinine(self) -> Union["BaselineCreatinine", None]:
        if self.ckd:
            return getattr(self.ckd, "baselinecreatinine", None)
        else:
            return None

    def check_for_age_and_gender(self) -> None:
        if not self.age or not self.gender:
            if not self.age and not self.gender:
                raise ValueError(f"{self} has no associated age or gender")
            elif not self.age:
                raise ValueError(f"{self} has no associated age.")
            else:
                raise ValueError(f"{self} has no associated gender.")

    @cached_property
    def dateofbirth(self) -> Union["DateOfBirth", None]:
        if self.user:
            return self.user.dateofbirth
        elif self.aki and hasattr(self.aki, "flare"):
            return self.aki.flare.dateofbirth
        else:
            return None

    @cached_property
    def gender(self) -> Union["Gender", None]:
        if self.user:
            return self.user.gender
        elif self.aki and hasattr(self.aki, "flare"):
            return self.aki.flare.gender
        else:
            return None

    @cached_property
    def is_at_baseline(self) -> bool:
        if not self.baselinecreatinine or not self.baselinecreatinine.value:
            raise ValueError(f"{self} has no BaselineCreatinine to compare for baseline equivalence.")
        elif self.ckddetail and self.ckddetail.dialysis:
            raise ValueError(f"Comparing {self} to {self.ckddetail.explanation}.")
        return labs_creatinine_is_at_baseline_creatinine(self, self.baselinecreatinine.value)

    @cached_property
    def is_within_normal_limits(self) -> bool:
        return self.value <= self.upper_limit

    @cached_property
    def is_within_range_for_stage(self) -> bool:
        if not self.ckddetail:
            raise ValueError(f"{self} has no associated CkdDetail.")
        elif self.ckddetail.dialysis:
            raise ValueError(f"Comparing {self} to {self.ckddetail.explanation}.")
        self.check_for_age_and_gender()
        return labs_creatinine_within_range_for_stage(self, self.ckddetail.stage, self.age, self.gender.value)

    @classmethod
    def related_models(cls) -> list[Literal["aki"]]:
        return ["aki"]


class Urate(Lab):
    class Meta(Lab.Meta):
        constraints = Lab.Meta.constraints + [
            # If there's a User, there can be no associated Ppx objects
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_user_ppx_exclusive",
                check=(
                    models.Q(user__isnull=False, ppx__isnull=True)
                    | models.Q(user__isnull=True, ppx__isnull=False)
                    | models.Q(user__isnull=True, ppx__isnull=True)
                ),
            ),
            models.CheckConstraint(
                check=(
                    models.Q(lower_limit=LowerLimits.URATEMGDL)
                    & models.Q(units=Units.MGDL)
                    & models.Q(upper_limit=UpperLimits.URATEMGDL)
                ),
                name="%(app_label)s_%(class)s_units_upper_lower_limits_valid",
            ),
        ]

    LowerLimits = LowerLimits
    Units = Units
    UpperLimits = UpperLimits

    lower_limit = models.DecimalField(max_digits=3, decimal_places=1, default=LowerLimits.URATEMGDL)
    ppx = models.ForeignKey(
        "ppxs.Ppx",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    units = models.CharField(_("Units"), choices=Units.choices, max_length=10, default=Units.MGDL)
    upper_limit = models.DecimalField(max_digits=3, decimal_places=1, default=UpperLimits.URATEMGDL)
    value = models.DecimalField(
        max_digits=3,
        decimal_places=1,
    )

    def __str__(self):
        if self.value:
            return f"Urate: {self.value.quantize(Decimal('1.0'))} {self.get_units_display()}"
        else:
            return "Urate: No value"

    @cached_property
    def date_drawn_or_flare_date(self):
        if self.date_drawn:
            return self.date_drawn
        elif hasattr(self, "flare"):
            return self.flare.date_started
        else:
            raise ValueError(f"Urate ({self}) has no date_drawn or associated flare.")

    @classmethod
    def related_models(cls) -> list[Literal["ppx"]]:
        return ["ppx"]

    @cached_property
    def value_str(self):
        return f"{self.value.quantize(Decimal('1.0'))} {self.get_units_display()}"


class Hlab5801(RulesModelMixin, GoutHelperModel, TimeStampedModel, metaclass=RulesModelBase):
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(date_drawn__lte=models.functions.Now()),
                name="%(app_label)s_%(class)s_date_drawn_not_in_future",
            ),
        ]

    date_drawn = models.DateTimeField(help_text="What day was the HLA-B*5801 drawn?", default=timezone.now, blank=True)
    value = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name=_("HLA-B*5801"),
        help_text=_("HLA-B*5801 genotype present?"),
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    history = HistoricalRecords()
    objects = models.Manager()

    def __str__(self):
        return f"HLA-B*5801: {'positive' if self.value else 'negative'}"
