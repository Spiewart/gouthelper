from typing import TYPE_CHECKING, Union

from django.apps import apps  # pylint: disable=E0401 # type: ignore
from django.contrib.auth import get_user_model  # pylint: disable=E0401 # type: ignore

from ..medhistorys.lists import ULT_MEDHISTORYS
from ..utils.services import AidService
from .choices import FlareFreqs, FlareNums, Indications

if TYPE_CHECKING:
    from ..medhistorydetails.models import CkdDetail
    from ..medhistorys.models import MedHistory
    from ..ults.models import Ult

User = get_user_model()


class UltDecisionAid(AidService):
    """Class method for creating/updating Ult indication fields."""

    def __init__(
        self,
        qs: Union["Ult", User, None] = None,
    ):
        super().__init__(qs=qs, model=apps.get_model(app_label="ults", model_name="Ult"))
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
            setattr(
                self,
                medhistorytype.lower(),
                next(
                    iter(
                        [medhistory for medhistory in self.medhistorys if medhistory.medhistorytype == medhistorytype],
                    ),
                    None,
                )
                if self.medhistorys
                else None,
            )

    def _get_indication(self) -> Indications:
        """Calculates the indication for the Ult object.

        Returns: Indications enum
        """
        return (
            Indications.INDICATED
            if (
                # ULT is indicated if either erosions or tophi are present, or if there are two
                # or more flares per year.
                self.erosions
                or self.tophi
                or self.model_attr.freq_flares == FlareFreqs.TWOORMORE
            )
            else (
                Indications.CONDITIONAL
                if (
                    # ULT is conditionally indicated if there is one flare per year
                    # but with a history of more than 1 gout flare, or if there is
                    # a first and only gout flare with either CKD >= III,
                    # hyperuricemia, or history of urate kidney stones.
                    self.model_attr.freq_flares == FlareFreqs.ONEORLESS
                    and self.model_attr.num_flares == FlareNums.TWOPLUS
                    or self.model_attr.num_flares == FlareNums.ONE
                    and (
                        (self.ckddetail is not None and self.ckddetail.stage >= 3)
                        or self.hyperuricemia
                        or self.uratestones
                    )
                    # Otherwise, ULT is not indicated.
                )
                else Indications.NOTINDICATED
            )
        )

    def _update(self, commit=True) -> "Ult":
        """Overwritten to update the indication field."""
        self.model_attr.indication = self._get_indication()
        return super()._update(commit=commit)
