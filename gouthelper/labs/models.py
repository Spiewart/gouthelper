from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from django.conf import settings  # type: ignore
from django.db import models  # type: ignore
from django.utils import timezone  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..choices import BOOL_CHOICES
from ..utils.models import GoutHelperModel
from .choices import Abnormalitys, LowerLimits, Units, UpperLimits
from .helpers import labs_eGFR_calculator, labs_stage_calculator

if TYPE_CHECKING:
    from ..medhistorydetails.choices import Stages


class CreatinineBase:
    class Meta:
        abstract = True

    @property
    def eGFR(self: "BaselineCreatinine") -> Decimal:  # type: ignore
        """
        Method for calculating eGFR.
        Requires age, gender, race, and a creatinine value.
        Required variables can be called with method or pulled from object's user's profile.
        """
        return labs_eGFR_calculator(creatinine=self)

    @property
    def stage(self: "BaselineCreatinine") -> "Stages":  # type: ignore
        """Method that takes calculated eGFR and returns Ckd stage

        Returns:
            [Stages / int]: [CKD stage]
        """
        # self.eGFR returns a Decimal for labs_stage_calculator()
        return labs_stage_calculator(self.eGFR)


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

    history = HistoricalRecords()

    @cached_property
    def value_str(self) -> str:
        return f"{self.value.quantize(Decimal('1.00'))} {self.get_units_display()}"

    def __str__(self):
        return f"Baseline Creatinine: {self.value.quantize(Decimal('1.00'))} {self.get_units_display()}"


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
        return f"Urate: {self.value.quantize(Decimal('1.0'))} {self.get_units_display()}"

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
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    history = HistoricalRecords()
