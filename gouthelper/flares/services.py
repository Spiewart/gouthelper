from typing import TYPE_CHECKING, Union

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db.models.query import QuerySet

from ..dateofbirths.helpers import age_calc
from ..medhistorys.helpers import (
    medhistorys_get_ckd,
    medhistorys_get_cvdiseases,
    medhistorys_get_gout,
    medhistorys_get_menopause,
)
from ..utils.helpers.aid_helpers import aids_assign_baselinecreatinine, aids_assign_ckddetail
from .helpers import (
    flares_calculate_likelihood,
    flares_calculate_prevalence,
    flares_calculate_prevalence_points,
    flares_get_less_likelys,
)

User = get_user_model()

if TYPE_CHECKING:
    from ..flares.models import Flare


class FlareDecisionAid:
    def __init__(
        self,
        qs: Union["Flare", User, QuerySet],
    ):
        Flare = apps.get_model("flares", "Flare")
        # Set up the method by calling get() on the QuerySet and
        # checking if the Flare is a Flare or User instance
        if isinstance(qs, QuerySet):
            qs = qs.get()
        if isinstance(qs, Flare):
            self.flare = qs
            self.user = qs.user
            # TODO: custom flare settings fetch will go here
        elif isinstance(qs, User):
            self.flare = qs.flare
            self.user = qs
            # TODO: custom flare settings fetch will go here
        else:
            raise ValueError("FlareDecisionAid requires a Flare or User instance.")
        # Assign other attrs from the QuerySet
        # Assign dateofbirth and age
        self.dateofbirth = qs.dateofbirth
        self.age = age_calc(qs.dateofbirth.value)
        # Check if the QS is a Flare with a User, if so,
        # then set its dateofbirth attr to None to avoid saving a
        # Flare with a User and dateofbirth, which will raise and IntegrityError
        if isinstance(qs, Flare) and qs.user:
            setattr(self.flare, "dateofbirth", None)
        # TODO: custom flare settings fetch will go here in the event it's not done above
        self.gender = qs.gender
        # Check if the QS is a Flare with a User, if so,
        # then sets its gender attr to None to avoid saving a
        # Flare with a User and a gender, which will raise and IntegrityError
        if isinstance(qs, Flare) and qs.user:
            setattr(self.flare, "gender", None)
        self.medhistorys = qs.medhistorys_qs
        # Need to check what sort of qs object is passed in, as the urate
        # attr will not be present on a User, but will be on a Flare
        self.urate = qs.urate if isinstance(qs, Flare) else qs.flare.urate
        self.baselinecreatinine = aids_assign_baselinecreatinine(medhistorys=self.medhistorys)
        self.ckddetail = aids_assign_ckddetail(medhistorys=self.medhistorys)
        self.ckd = medhistorys_get_ckd(medhistorys=self.medhistorys)
        self.cvdiseases = medhistorys_get_cvdiseases(medhistorys=self.medhistorys)
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
