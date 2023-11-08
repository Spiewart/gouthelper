from typing import TYPE_CHECKING, Union

from ..dateofbirths.helpers import age_calc
from ..medhistorys.helpers import (
    medhistorys_get_ckd,
    medhistorys_get_cvdiseases,
    medhistorys_get_gout,
    medhistorys_get_menopause,
)
from ..utils.helpers.aid_helpers import aids_assign_userless_baselinecreatinine, aids_assign_userless_ckddetail
from .helpers import (
    flares_calculate_likelihood,
    flares_calculate_prevalence,
    flares_calculate_prevalence_points,
    flares_get_less_likelys,
)
from .selectors import flare_userless_qs

if TYPE_CHECKING:
    from uuid import UUID

    from ..flares.models import Flare


class FlareDecisionAid:
    def __init__(
        self,
        pk: "UUID",
        qs: Union["Flare", None] = None,
    ):
        if qs:
            self.flare = qs
        else:
            self.flare = flare_userless_qs(pk=pk).get()
        self.dateofbirth = self.flare.dateofbirth
        self.gender = self.flare.gender
        self.medhistorys = self.flare.medhistorys_qs
        self.urate = self.flare.urate
        self.baselinecreatinine = aids_assign_userless_baselinecreatinine(medhistorys=self.medhistorys)
        self.ckddetail = aids_assign_userless_ckddetail(medhistorys=self.medhistorys)
        # Separate here when adding User to class method
        self.ckd = medhistorys_get_ckd(medhistorys=self.medhistorys)
        self.cvdiseases = medhistorys_get_cvdiseases(medhistorys=self.medhistorys)
        self.age = age_calc(self.dateofbirth.value)
        self.gout = medhistorys_get_gout(medhistorys=self.medhistorys)
        self.menopause = medhistorys_get_menopause(medhistorys=self.medhistorys)

    def _update(self, commit=True) -> "Flare":
        """Updates the Flare likelihood and prevalence fields.

        Args:
            commit (bool): defaults to True, True will clean/save, False will not

        Returns:
            Flare: the updated Flare (self)
        """
        self.flare.prevalence = flares_calculate_prevalence(
            prevalence_points=flares_calculate_prevalence_points(
                gender=self.gender,
                onset=self.flare.onset,
                redness=self.flare.redness,
                joints=self.flare.joints,
                medhistorys=self.medhistorys,
                urate=self.urate,
            )
        )
        self.flare.likelihood = flares_calculate_likelihood(
            less_likelys=flares_get_less_likelys(
                age=self.age,
                date_ended=self.flare.date_ended,
                duration=self.flare.duration,
                gender=self.gender,
                joints=self.flare.joints,
                menopause=self.menopause,
                crystal_analysis=self.flare.crystal_analysis,
                ckd=self.ckd,
            ),
            diagnosed=self.flare.diagnosed,
            crystal_analysis=self.flare.crystal_analysis,
            prevalence=self.flare.prevalence,
        )
        if commit:
            self.flare.full_clean()
            self.flare.save()
        return self.flare
