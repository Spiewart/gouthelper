from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal

from django.apps import apps  # type: ignore
from django.db import models  # type: ignore
from django.utils import timezone  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..choices import BOOL_CHOICES
from ..medhistorys.choices import MedHistoryTypes
from ..utils.models import GoutHelperModel
from .choices import Abnormalitys, LabTypes, LowerLimits, Units, UpperLimits
from .helpers import (
    labs_eGFR_calculator,
    labs_get_default_labtype,
    labs_get_default_lower_limit,
    labs_get_default_units,
    labs_get_default_upper_limit,
    labs_stage_calculator,
)
from .managers import CreatinineManager, UrateManager

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
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_labtype_valid",
                check=models.Q(labtype__in=LabTypes.values),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_units_upper_lower_limits_valid",
                check=(
                    (
                        models.Q(labtype=LabTypes.CREATININE)
                        & models.Q(lower_limit=LowerLimits.CREATININEMGDL)
                        & models.Q(units=Units.MGDL)
                        & models.Q(upper_limit=UpperLimits.CREATININEMGDL)
                    )
                    | (
                        models.Q(labtype=LabTypes.URATE)
                        & models.Q(lower_limit=LowerLimits.URATEMGDL)
                        & models.Q(units=Units.MGDL)
                        & models.Q(upper_limit=UpperLimits.URATEMGDL)
                        & models.Q(value__lte=Decimal("30.00"))
                    )
                ),
            ),
        ]

    LabTypes = LabTypes
    LowerLimits = LowerLimits
    Units = Units
    UpperLimits = UpperLimits

    labtype = models.CharField(_("Lab Type"), max_length=30, choices=LabTypes.choices, editable=False)
    lower_limit = models.DecimalField(max_digits=6, decimal_places=2)
    units = models.CharField(_("Units"), choices=Units.choices, max_length=10)
    upper_limit = models.DecimalField(max_digits=6, decimal_places=2)
    value = models.DecimalField(
        max_digits=6,
        decimal_places=2,
    )
    history = HistoricalRecords(inherit=True)

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

    def set_fields(self):
        """Method that sets the default values for the labtype, lower_limit, units, and upper_limit."""
        lab_name = self._meta.model.__name__.upper()
        if lab_name.startswith("BASELINE"):
            lab_name = lab_name.replace("BASELINE", "")
        if not self.labtype:
            self.labtype = labs_get_default_labtype(lab_name=lab_name)
        if not self.lower_limit:
            self.lower_limit = labs_get_default_lower_limit(lab_name=lab_name)
        if not self.units:
            self.units = labs_get_default_units(lab_name=lab_name)
        if not self.upper_limit:
            self.upper_limit = labs_get_default_upper_limit(lab_name=lab_name)


class BaselineLab(LabBase):
    class Meta(LabBase.Meta):
        abstract = True
        constraints = LabBase.Meta.constraints

    medhistory = models.OneToOneField("medhistorys.MedHistory", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.labtype}: {self.value} {self.units}"

    def save(
        self,
        *args,
        **kwargs,
    ):
        """Overwritten to set fields on object creation."""
        if self._state.adding is True:
            self.set_fields()
        super().save(*args, **kwargs)


class Lab(LabBase):
    class Meta(LabBase.Meta):
        constraints = LabBase.Meta.constraints + [
            models.CheckConstraint(
                check=models.Q(date_drawn__lte=models.functions.Now()),
                name="%(app_label)s_%(class)s_date_drawn_not_in_future",
            ),
        ]

    date_drawn = models.DateTimeField(help_text="What day was this lab drawn?", default=timezone.now, blank=True)
    objects = models.Manager()

    def delete(
        self,
        *args,
        **kwargs,
    ):
        """Overwritten to change class before and after calling super().delete()
        so Django-Simple-History works."""
        # Change class to Lab, call super().delete(), then change class back
        # to proxy model class in order for Django-Simple-History to work properly
        self.__class__ = Lab
        super().delete(*args, **kwargs)
        self.__class__ = apps.get_model(f"labs.{self.labtype}")

    def save(
        self,
        *args,
        **kwargs,
    ):
        """Overwritten to change class before and after calling super().save()
        so Django-Simple-History works."""
        # Change class to MedHistory, call super().save(), then change class back
        # to proxy model class in order for Django-Simple-History to work properly
        if self._state.adding is True:
            self.set_fields()
        self.__class__ = Lab
        super().save(*args, **kwargs)
        self.__class__ = apps.get_model(f"labs.{self.labtype}")

    def __str__(self):
        return apps.get_model("labs", self.labtype).__str__(self)

    def get_medhistorytype(
        self,
    ) -> MedHistoryTypes:
        """Method that returns the medhistorytype that is specific for this lab and
        its associated abnormality (HIGH or LOW).

        Returns:
            Literal[MedHistoryTypes]
        """
        model: Any = apps.get_model(f"labs.{self.labtype}")
        method = model.get_medhistorytype
        return method(self)

    def medhistorytypes(self) -> list[MedHistoryTypes]:
        model: Any = apps.get_model("labs", self.labtype)
        method = model.medhistorytypes
        return method(self)

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
    class Meta(BaselineLab.Meta):
        constraints = BaselineLab.Meta.constraints

    objects = CreatinineManager()

    @cached_property
    def value_str(self) -> str:
        return f"{self.value.quantize(Decimal('1.00'))} {self.get_units_display()}"

    def __str__(self):
        return f"Baseline {getattr(self.LabTypes, self.labtype).label}: \
{self.value.quantize(Decimal('1.00'))} {getattr(self.Units, self.units).label}"


class Urate(Lab):
    class Meta:
        proxy = True

    objects = UrateManager()

    def __str__(self):
        return f"{getattr(self.LabTypes, self.labtype).label}: \
{self.value.quantize(Decimal('1.0'))} {getattr(self.Units, self.units).label}"

    def get_medhistorytype(self) -> Literal[MedHistoryTypes.GOUT]:
        return MedHistoryTypes.GOUT

    @cached_property
    def value_str(self):
        return f"{self.value.quantize(Decimal('1.0'))} {self.get_units_display()}"

    def medhistorytypes(self) -> list[Literal[MedHistoryTypes.GOUT]]:
        return [MedHistoryTypes.GOUT]


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
    history = HistoricalRecords(inherit=True)
