from datetime import timedelta
from typing import TYPE_CHECKING, Union

from django.conf import settings  # type: ignore
from django.core.validators import MaxValueValidator, MinValueValidator  # type: ignore
from django.db import models  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils import timezone  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..choices import BOOL_CHOICES
from ..defaults.helpers import defaults_get_goalurate
from ..labs.choices import LabTypes
from ..labs.helpers import labs_urates_last_at_goal, labs_urates_months_at_goal, labs_urates_recent_urate
from ..labs.selectors import dated_urates
from ..medhistorys.lists import PPX_MEDHISTORYS
from ..rules import add_object, change_object, delete_object, view_object
from ..ults.choices import Indications
from ..utils.models import DecisionAidModel, GoutHelperModel, LabAidModel, MedHistoryAidModel
from .helpers import ppxs_check_urate_hyperuricemic_discrepant, ppxs_urate_hyperuricemic_discrepancy_str
from .services import PpxDecisionAid

if TYPE_CHECKING:
    from ..goalurates.choices import GoalUrates
    from ..medhistorys.choices import MedHistoryTypes


class Ppx(
    RulesModelMixin,
    DecisionAidModel,
    GoutHelperModel,
    LabAidModel,
    MedHistoryAidModel,
    TimeStampedModel,
    metaclass=RulesModelBase,
):
    """Model to collate information for a patient and determine if he or she has
    an indication for gout flare prophylaxis."""

    Indications = Indications

    class Meta:
        rules_permissions = {
            "add": add_object,
            "change": change_object,
            "delete": delete_object,
            "view": view_object,
        }

    indication = models.IntegerField(
        _("Indication"),
        validators=[MinValueValidator(0), MaxValueValidator(2)],
        choices=Indications.choices,
        help_text="Does the patient have an indication for prophylaxis?",
        default=Indications.NOTINDICATED,
    )
    starting_ult = models.BooleanField(
        _("Starting ULT?"),
        choices=BOOL_CHOICES,
        default=False,
        help_text="Is the patient starting ULT?",
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    history = HistoricalRecords()

    @classmethod
    def aid_medhistorys(cls) -> list["MedHistoryTypes"]:
        return PPX_MEDHISTORYS

    @classmethod
    def aid_labs(cls) -> list[str]:
        return [LabTypes.URATE]

    @cached_property
    def at_goal(self) -> bool:
        """Method that interprets the Ppx's labs (Urates) and returns a bool
        indicating whether the patient is at goal."""
        if hasattr(self, "labs_qs"):
            return labs_urates_months_at_goal(
                urates=self.labs_qs,
                goutdetail=self.gout.goutdetail if self.gout and self.gout.goutdetail else None,
                goal_urate=self.goalurate,
                commit=False,
            )
        else:
            return labs_urates_months_at_goal(
                urates=dated_urates(self.labs).all(),
                goutdetail=self.gout.goutdetail if self.gout and self.gout.goutdetail else None,  # type: ignore
                goal_urate=self.goalurate,
                commit=False,
            )

    @cached_property
    def conditional_indication(self) -> bool:
        """Method that returns whether or not the Ult
        has a conditional recommendation for ULT."""
        return self.indication == Indications.CONDITIONAL

    @cached_property
    def flaring(self) -> bool | None:
        """Method that returns Gout MedHistory object's GoutDetail object's flaring
        attribute."""
        return self.gout.goutdetail.flaring if self.gout and self.gout.goutdetail else None

    @cached_property
    def goalurate(self) -> "GoalUrates":
        """Fetches the Ppx objects associated GoalUrate.goal_urate if it exists, otherwise
        returns the GoutHelper default GoalUrates.SIX enum object"""
        return defaults_get_goalurate(self)

    def get_absolute_url(self):
        return reverse("ppxs:detail", kwargs={"pk": self.pk})

    @cached_property
    def hyperuricemic(self) -> bool | None:
        """Method that returns Gout MedHistory object's GoutDetail object's hyperuricemic
        attribute."""
        return self.gout.goutdetail.hyperuricemic if self.gout and self.gout.goutdetail else None

    @cached_property
    def indicated(self) -> bool:
        """Method that returns a bool indicating whether Ult is indicated."""
        return self.indication == Indications.INDICATED or self.indication == Indications.CONDITIONAL

    @cached_property
    def last_urate_at_goal(self) -> bool:
        """Method that determines if the last urate in the Ppx's labs was at goal."""
        if hasattr(self, "labs_qs"):
            return labs_urates_last_at_goal(
                urates=self.labs_qs,
                goutdetail=self.gout.goutdetail if self.gout and self.gout.goutdetail else None,
                goal_urate=self.goalurate,
                commit=False,
            )
        else:
            return labs_urates_last_at_goal(
                urates=dated_urates(self.labs).all(),
                goutdetail=self.gout.goutdetail if self.gout and self.gout.goutdetail else None,
                goal_urate=self.goalurate,
                commit=False,
            )

    @cached_property
    def on_ppx(self) -> bool:
        """Method that returns Gout MedHistory object's GoutDetail object's on_ppx
        attribute."""
        return self.gout.goutdetail.on_ppx if self.gout and self.gout.goutdetail else False

    @cached_property
    def on_ult(self) -> bool:
        """Method that returns Gout MedHistory object's GoutDetail object's on_ult
        attribute."""
        return self.gout.goutdetail.on_ult if self.gout and self.gout.goutdetail else False

    @cached_property
    def recent_urate(self) -> bool:
        """Method that returns True if the patient has had his or her uric acid checked
        in the last 3 months, False if not."""
        if hasattr(self, "labs_qs"):
            return labs_urates_recent_urate(
                urates=self.labs_qs,
                sorted_by_date=True,
            )
        else:
            return labs_urates_recent_urate(
                urates=dated_urates(self.labs).all(),
                sorted_by_date=True,
            )

    @cached_property
    def semi_recent_urate(self) -> bool:
        """Method that returns True if the patient has had his or her uric acid checked
        in the last 6 months, False if not."""
        if hasattr(self, "labs_qs"):
            return [
                lab for lab in self.labs_qs if lab.date_drawn and lab.date_drawn > timezone.now() - timedelta(days=180)
            ]
        else:
            return [
                lab
                for lab in dated_urates(self.labs).all()
                if lab.date and lab.date > timezone.now() - timedelta(days=180)
            ]

    def update(self, decisionaid: PpxDecisionAid | None = None, qs: Union["Ppx", None] = None) -> "Ppx":
        """Updates the Ppx indication field.

        Args:
            decisionaid: PpxDecisionAid object
            qs: Ppx object

        Returns:
            Ppx: Ppx object."""
        if decisionaid is None:
            decisionaid = PpxDecisionAid(pk=self.pk, qs=qs)
        return decisionaid._update()

    @cached_property
    def urates_discrepant(self) -> bool:
        """Method that implements the ppxs_check_urate_hyperuricemic_discrepant helper
        method to determine if the labs (Urates) and the goutdetail hyperuricemic field
        are discrepant.

        returns:
            bool: True if the labs (Urates) and the goutdetail hyperuricemic field are
            discrepant (i.e. hyperuricemic is True but the last urate was at goal),
            False if not.
        """
        return (
            ppxs_check_urate_hyperuricemic_discrepant(
                urate=(
                    self.labs_qs[0]
                    if hasattr(self, "labs_qs") and self.labs_qs
                    else self.labs.order_by("-date_drawn").first()
                ),
                goutdetail=self.goutdetail,  # type: ignore
                goalurate=self.goalurate,
            )
            if (hasattr(self, "labs_qs") and self.labs_qs or self.labs.exists()) and self.goutdetail
            else False
        )

    @property
    def urates_discrepant_str(self) -> str | None:
        """Property that implements the ppxs_urate_hyperuricemic_discrepancy_str helper
        method. Calling this property implies that: There is at least 1 Urate, and a
        GoutDetail object associated with the Ppx.

        returns:
            str: A string indicating the discrepant status of the labs (Urates) and the
            goutdetail hyperuricemic field."""
        return (
            ppxs_urate_hyperuricemic_discrepancy_str(
                urate=(
                    self.labs_qs[0]
                    if hasattr(self, "labs_qs") and self.labs_qs
                    else self.labs.order_by("-date_drawn").first()
                ),
                goutdetail=self.goutdetail,  # type: ignore
                goalurate=self.goalurate,
            )
            if (hasattr(self, "labs_qs") and self.labs_qs or self.labs.exists()) and self.goutdetail
            else None
        )
