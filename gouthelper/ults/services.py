from typing import TYPE_CHECKING, Union

from ..medhistorys.lists import ULT_MEDHISTORYS
from ..utils.helpers.aid_helpers import aids_assign_userless_ckddetail
from .choices import FlareFreqs, FlareNums, Indications
from .selectors import ult_userless_qs

if TYPE_CHECKING:
    from uuid import UUID

    from ..medhistorydetails.models import CkdDetail
    from ..medhistorys.models import MedHistory
    from ..ults.models import Ult


class UltDecisionAid:
    """Class method for creating/updating Ult indication fields."""

    def __init__(
        self,
        pk: "UUID",
        qs: Union["Ult", None] = None,
    ):
        if qs is not None:
            self.ult = qs
        else:
            self.ult = ult_userless_qs(pk=pk).get()
        self.medhistorys = self.ult.medhistorys_qs
        self.ckddetail = aids_assign_userless_ckddetail(medhistorys=self.medhistorys)
        self._assign_medhistorys()

    ckd: Union["MedHistory", None]
    ckddetail: Union["CkdDetail", None]
    erosions: Union["MedHistory", None]
    hyperuricemia: Union["MedHistory", None]
    tophi: Union["MedHistory", None]
    uratestones: Union["MedHistory", None]

    FlareNums = FlareNums
    FlareFreqs = FlareFreqs
    Indications = Indications

    def _assign_medhistorys(self) -> None:
        """Iterates over ULT_MEDHISTORYS and assign attributes to the class method
        for each medhistory in ULT_MEDHISTORYS. Assign the attribute to the matching
        medhistory in self.medhistorys if it exists, None if not."""
        for medhistorytype in ULT_MEDHISTORYS:
            medhistory = [medhistory for medhistory in self.medhistorys if medhistory.medhistorytype == medhistorytype]
            if medhistory:
                setattr(self, medhistorytype.lower(), medhistory[0])
            else:
                setattr(self, medhistorytype.lower(), None)

    def _get_indication(self) -> Indications:
        """Calculates the indication for the Ult object.

        Returns: Indications enum
        """
        # If either erosions or tophi are present, then ULT is indicated.
        if self.erosions or self.tophi:
            return Indications.INDICATED
        # Two or more flares per year is an indication for ULT.
        elif self.ult.freq_flares == FlareFreqs.TWOORMORE:
            return Indications.INDICATED
        # One flare per year but with a history of more than 1 gout flare is a conditional indication for ULT.
        elif self.ult.freq_flares == FlareFreqs.ONEORLESS and self.ult.num_flares == FlareNums.TWOPLUS:
            return Indications.CONDITIONAL
        # First and only gout flare with either CKD >= III,
        # hyperuricemia, or history of urate kidney stones is a conditional indication for ULT
        elif self.ult.num_flares == FlareNums.ONE and (
            (self.ckddetail is not None and self.ckddetail.stage >= 3) or self.hyperuricemia or self.uratestones
        ):
            return Indications.CONDITIONAL
        # Otherwise ULT is not indicated.
        else:
            return Indications.NOTINDICATED

    def _update(self, commit=True) -> "Ult":
        """Updates Ult indication field.

        Args:
            commit (bool): defaults to True, True will clean/save, False will not

        Returns:
            ult: Ult object
        """
        self.ult.indication = self._get_indication()
        if commit:
            self.ult.full_clean()
            self.ult.save()
        return self.ult
