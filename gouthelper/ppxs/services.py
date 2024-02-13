from typing import TYPE_CHECKING, Union

from django.apps import apps  # type: ignore
from django.contrib.auth import get_user_model
from django.db.models.query import QuerySet
from django.utils.functional import cached_property  # type: ignore

from ..defaults.helpers import defaults_get_goalurate
from ..goalurates.choices import GoalUrates
from ..labs.helpers import labs_urates_hyperuricemic, labs_urates_months_at_goal, labs_urates_recent_urate
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.helpers import medhistorys_get
from ..ults.choices import Indications
from ..utils.helpers.aid_helpers import aids_assign_goutdetail

if TYPE_CHECKING:
    from ..medhistorydetails.models import GoutDetail
    from ..medhistorys.models import MedHistory
    from ..ppxs.models import Ppx

User = get_user_model()


class PpxDecisionAid:
    """Class method for creating/updating Ppx indication field."""

    def __init__(
        self,
        qs: Union["Ppx", User, QuerySet] = None,
    ):
        Ppx = apps.get_model("ppxs.Ppx")
        if isinstance(qs, QuerySet):
            qs = qs.get()
        if isinstance(qs, Ppx):
            self.ppx = qs
            self.user = qs.user
        elif isinstance(qs, User):
            self.ppx = qs.ppx
            self.user = qs
        else:
            raise ValueError("PpxDecisionAid requires a Ppx or User instance.")
        self.medhistorys = qs.medhistorys_qs
        self.gout = medhistorys_get(medhistorys=self.medhistorys, medhistorytype=MedHistoryTypes.GOUT)
        self.goutdetail = aids_assign_goutdetail(medhistorys=[self.gout]) if self.gout else None
        self._check_for_gout_and_detail()
        self.urates = qs.urates_qs
        # Process the urates to figure out if the Urates indicate that the patient
        # has been at goal uric acid for the past 6 months or longer
        self.at_goal: bool = False
        if not labs_urates_hyperuricemic(urates=self.urates, goutdetail=self.goutdetail):
            self.at_goal = labs_urates_months_at_goal(urates=self.urates, goutdetail=self.goutdetail)
        # Check if there is a recent_urate
        self.recent_urate: bool = labs_urates_recent_urate(urates=self.urates, sorted_by_date=True)

    gout: Union["MedHistory", None]
    goutdetail: Union["GoutDetail", None]

    Indications = Indications

    def _check_for_gout_and_detail(self) -> None:
        """This class method requires a Gout MedHistory and GoutDetail MedHistoryDetail.
        This is because no patient who doesn't have gout should be on prophylaxis for
        gout flares. Checks for these attrs after they have been assigned and raises a
        TypeError if they are None."""
        if not self.gout:
            raise TypeError("No Gout MedHistory in Ppx.medhistorys.")
        if not self.goutdetail:
            raise TypeError("No GoutDetail associated with Ppx.gout.")

    @cached_property
    def goalurate(self) -> "GoalUrates":
        """Fetches the Ppx objects associated GoalUrate.goal_urate if it exists, otherwise
        returns the GoutHelper default GoalUrates.SIX enum object"""
        return defaults_get_goalurate(self.user if self.user else self)

    @property
    def flaring(self) -> bool:
        """Returns True the Gout MedHistory flaring attr is True,
        False if not or there is no Gout."""
        return self.goutdetail.flaring

    def _get_indication(self) -> Indications:
        """Determines the indication for the Ppx object.

        Returns: Indications enum
        """
        # First check if the patient is on or starting ULT
        if self.goutdetail and (self.goutdetail.on_ult or self.ppx.starting_ult):
            # If the patient is on ULT but isn't starting ULT
            if self.ppx.starting_ult is False:
                # Check if their is a "conditional" indication for prophylaxis
                # This is not guidelines-based, rather GoutHelper-based
                # The rationale is that if they are on ULT and still hyperuricemic or flaring,
                # they are at risk of gout flares and should be on prophylaxis while ULT is titrated
                if (
                    self.goutdetail.flaring
                    or self.goutdetail.hyperuricemic
                    and not (self.at_goal and self.recent_urate)
                ):
                    return Indications.CONDITIONAL
                # If the patient is on ULT and it's not a new start and they aren't flaring
                # or hyperuricemic, there isn't a patient-centered rationale for prophylaxis
                else:
                    return Indications.NOTINDICATED
            # If they are starting ULT, the ACR guidelines say they should be on prophylaxis
            else:
                if self.at_goal and self.recent_urate:
                    return Indications.NOTINDICATED
                else:
                    return Indications.INDICATED
        # If the patient is not on ULT, they should not be on prophylaxis
        else:
            return Indications.NOTINDICATED

    @property
    def hyperuricemic(self) -> bool | None:
        """Returns True if the Gout MedHistory hyperuricemic attr is True,
        False if not or there is no Gout."""
        return self.goutdetail.hyperuricemic

    def _update(self, commit=True) -> "Ppx":
        """Updates Ppx indication fields.

        Args:
            commit (bool): defaults to True, True will clean/save, False will not

        Returns:
            ppx: Ppx object
        """
        self.ppx.indication = self._get_indication()
        if commit:
            self.ppx.full_clean()
            self.ppx.save()
        return self.ppx
