from typing import TYPE_CHECKING, Union

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db.models.query import QuerySet

from ..medhistorys.choices import CVDiseases, MedHistoryTypes
from ..medhistorys.helpers import medhistorys_get
from ..utils.services import AidService, aids_assign_baselinecreatinine, aids_assign_ckddetail
from .helpers import (
    flares_calculate_likelihood,
    flares_calculate_prevalence,
    flares_calculate_prevalence_points,
    flares_get_less_likelys,
)

User = get_user_model()

if TYPE_CHECKING:
    from ..flares.models import Flare


class FlareDecisionAid(AidService):
    """Class method for creating/updating Flare likelihood and prevalence fields."""

    def __init__(
        self,
        qs: Union["Flare", User, QuerySet],
    ):
        super().__init__(qs=qs, model=apps.get_model(app_label="flares", model_name="Flare"))
        self.urate = qs.urate if isinstance(qs, self.model) else self.model_attr.urate
        self.ckd = medhistorys_get(self.medhistorys, MedHistoryTypes.CKD)
        self.baselinecreatinine = aids_assign_baselinecreatinine(medhistorys=self.medhistorys)
        self.ckddetail = aids_assign_ckddetail(medhistorys=self.medhistorys)
        self.cvdiseases = medhistorys_get(self.medhistorys, CVDiseases.values)
        self.gout = medhistorys_get(self.medhistorys, MedHistoryTypes.GOUT)
        self.menopause = medhistorys_get(self.medhistorys, MedHistoryTypes.MENOPAUSE)
        self.initial_likelihood = self.model_attr.likelihood
        self.initial_prevalence = self.model_attr.prevalence

    def _update(self, commit=True) -> "Flare":
        """Updates the Flare likelihood and prevalence fields.

        Args:
            commit (bool): defaults to True, True will clean/save, False will not

        Returns:
            Flare: the updated Flare (self)
        """
        self.update_prevalence()
        self.update_likelihood()
        return super()._update(commit=commit)

    def get_aid_object_from_user_qs(
        self,
        model_attr_str: str = "flare",
    ) -> "Flare":
        if hasattr(self.qs, f"{model_attr_str}_qs"):
            model_obj = getattr(self.qs, f"{model_attr_str}_qs")
        elif hasattr(self.qs, f"most_recent_{model_attr_str}"):
            model_obj = getattr(self.qs, f"most_recent_{model_attr_str}")
        else:
            raise AttributeError(
                f"{self.qs} does not have a '{model_attr_str}_qs' or 'most_recent_{model_attr_str}' attribute."
            )
        if isinstance(model_obj, QuerySet):
            return model_obj[0]
        elif isinstance(model_obj, list):
            return model_obj[0]
        else:
            return model_obj

    def update_prevalence(self) -> None:
        self.model_attr.prevalence = flares_calculate_prevalence(prevalence_points=self.prevalence_points)

    @property
    def prevalence_points(self) -> float:
        return flares_calculate_prevalence_points(
            gender=self.gender,
            onset=self.model_attr.onset,
            redness=self.model_attr.redness,
            joints=self.model_attr.joints,
            medhistorys=self.medhistorys,
            urate=self.urate,
        )

    def update_likelihood(self) -> None:
        self.model_attr.likelihood = flares_calculate_likelihood(
            less_likelys=flares_get_less_likelys(
                age=self.age,
                date_ended=self.model_attr.date_ended,
                duration=self.model_attr.duration,
                gender=self.gender,
                joints=self.model_attr.joints,
                menopause=self.menopause,
                crystal_analysis=self.model_attr.crystal_analysis,
                ckd=self.ckd,
            ),
            diagnosed=self.model_attr.diagnosed,
            crystal_analysis=self.model_attr.crystal_analysis,
            prevalence=self.model_attr.prevalence,
        )

    def likelihood_has_changed(self) -> bool:
        """Returns True if the Flare likelihood or prevalence has changed, False if not."""
        return self.model_attr.likelihood != self.initial_likelihood

    def prevalence_has_changed(self) -> bool:
        """Returns True if the Flare prevalence has changed, False if not."""
        return self.model_attr.prevalence != self.initial_prevalence

    def aid_needs_2_be_saved(self) -> bool:
        """Returns True if the Flare likelihood or prevalence has changed, False if not."""
        return self.likelihood_has_changed() or self.prevalence_has_changed()
