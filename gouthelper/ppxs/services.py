from typing import TYPE_CHECKING, Union

from django.apps import apps  # type: ignore
from django.contrib.auth import get_user_model
from django.db.models.query import QuerySet

from ..labs.helpers import labs_urate_within_90_days, labs_urate_within_last_month
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.helpers import medhistorys_get
from ..ults.choices import Indications
from ..utils.services import AidService, aids_assign_goutdetail

if TYPE_CHECKING:
    from ..medhistorydetails.models import GoutDetail
    from ..medhistorys.models import MedHistory
    from ..ppxs.models import Ppx

User = get_user_model()


class PpxDecisionAid(AidService):
    """Class method for creating/updating Ppx indication field."""

    def __init__(
        self,
        qs: Union["Ppx", User, QuerySet] = None,
    ):
        super().__init__(qs=qs, model=apps.get_model(app_label="ppxs", model_name="Ppx"))
        self.gout = medhistorys_get(medhistorys=self.medhistorys, medhistorytype=MedHistoryTypes.GOUT)
        self.goutdetail = aids_assign_goutdetail(medhistorys=[self.gout]) if self.gout else None
        self._check_for_gout_and_detail()
        self.urates = self.qs.urates_qs
        self.urate_within_last_month = labs_urate_within_last_month(urates=self.urates, sorted_by_date=True)
        self.urate_within_90_days: bool = labs_urate_within_90_days(urates=self.urates, sorted_by_date=True)
        self.at_goal = self.model_attr.urates_at_goal
        self.at_goal_long_term = self.model_attr.urates_at_goal_long_term
        self.initial_indication = self.model_attr.indication

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

    def _get_indication(self) -> Indications:
        """Determines the indication for the Ppx object.

        Returns: Indications enum
        """
        # First check if the patient is on or starting ULT
        if self.goutdetail and (self.goutdetail.on_ult or self.goutdetail.starting_ult):
            # If the patient is on ULT but isn't starting ULT
            if self.goutdetail.starting_ult is False:
                # Check if their is a "conditional" indication for prophylaxis
                # This is not guidelines-based, rather GoutHelper-based
                # The rationale is that if they are on ULT and still hyperuricemic or flaring,
                # they are at risk of gout flares and should be on prophylaxis while ULT is titrated
                if (
                    self.goutdetail.flaring
                    or not self.goutdetail.at_goal
                    and not (self.at_goal_long_term and self.urate_within_90_days)
                ):
                    return Indications.CONDITIONAL
                # If the patient is on ULT and it's not a new start and they aren't flaring
                # or hyperuricemic, there isn't a patient-centered rationale for prophylaxis
                else:
                    return Indications.NOTINDICATED
            # If they are starting ULT, the ACR guidelines say they should be on prophylaxis
            else:
                if self.at_goal_long_term and self.urate_within_90_days:
                    return Indications.NOTINDICATED
                else:
                    return Indications.INDICATED
        # If the patient is not on ULT, they should not be on prophylaxis
        else:
            return Indications.NOTINDICATED

    def _update(self, commit=True) -> "Ppx":
        """Updates Ppx indication fields.

        Args:
            commit (bool): defaults to True, True will clean/save, False will not

        Returns:
            ppx: Ppx object
        """

        def _goutdetail_at_goal_needs_update() -> bool:
            return self.model_attr.goutdetail.at_goal != self.at_goal and self.urate_within_last_month

        def _goutdetail_at_goal_long_term_needs_update() -> bool:
            return (
                self.model_attr.goutdetail.at_goal_long_term != self.at_goal_long_term and self.urate_within_last_month
            )

        # Check and update the at_goal and at_goal_long_term fields in the GoutDetail
        if _goutdetail_at_goal_needs_update() or _goutdetail_at_goal_long_term_needs_update():
            self.model_attr.goutdetail.update_at_goal(at_goal=self.at_goal)
            self.model_attr.goutdetail.update_at_goal_long_term(at_goal_long_term=self.at_goal_long_term)
            self.model_attr.goutdetail.full_clean()
            self.model_attr.goutdetail.save()
        self.set_model_attr_indication()
        return super()._update(commit=commit)

    def aid_needs_2_be_saved(self) -> bool:
        return self.indication_has_changed()

    def indication_has_changed(self) -> bool:
        return self.model_attr.indication != self.initial_indication

    def set_model_attr_indication(self) -> None:
        self.model_attr.indication = self._get_indication()
