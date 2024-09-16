from typing import TYPE_CHECKING, Union

from django.db import transaction
from django.db.models import Manager, QuerySet

from ..akis.choices import Statuses  # type: ignore
from ..akis.services import AkiCreator
from ..dateofbirths.helpers import age_calc
from ..medhistorydetails.choices import DialysisChoices
from ..medhistorydetails.services import CkdDetailCreator
from ..utils.exceptions import GoutHelperValidationError
from .choices import DiagnosedChoices
from .selectors import flare_userless_relations

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal

    from django.contrib.auth import get_user_model  # pylint:disable=E0401  # type: ignore

    from ..flareaids.models import FlareAid
    from ..genders.choices import Genders
    from ..medhistorydetails.choices import DialysisDurations, Stages
    from .choices import LimitedJointChoices
    from .models import Flare

    User = get_user_model()


class FlareQuerySet(QuerySet):
    def related_objects(self) -> QuerySet:
        return flare_userless_relations(self)


class FlareManager(Manager):
    def get_queryset(self) -> QuerySet:
        return FlareQuerySet(self.model, using=self._db).related_objects()

    def api_create(
        self,
        aki: bool | None,
        aki__status: Statuses | None,
        aki__creatinines: list["Decimal"] | None,
        angina: bool,
        cad: bool,
        chf: bool,
        ckd: bool,
        baselinecreatinine: Union["Decimal", None],
        ckddetail__dialysis: bool,
        ckddetail__dialysis_type: Union["DialysisChoices", None],
        ckddetail__dialysis_duration: Union["DialysisDurations", None],
        ckddetail__stage: Union["Stages", None],
        crystal_analysis: bool | None,
        dateofbirth: Union["date", None],
        date_ended: Union["date", None],
        date_started: "date",
        diagnosed: DiagnosedChoices | None,
        flareaid: Union["FlareAid", None],
        gender: Union["Genders", None],
        gout: bool,
        joints: list["LimitedJointChoices"],
        heartattack: bool,
        hypertension: bool,
        menopause: bool,
        onset: bool,
        pvd: bool,
        redness: bool,
        stroke: bool,
        urate: Union["Decimal", None],
    ) -> "Flare":
        errors = []
        with transaction.atomic():
            if ckd:
                ckddetail_service = CkdDetailCreator(
                    ckd=None,
                    dialysis=ckddetail__dialysis,
                    dialysis_duration=ckddetail__dialysis_duration,
                    dialysis_type=ckddetail__dialysis_type,
                    stage=ckddetail__stage,
                    age=age_calc(dateofbirth),
                    baselinecreatinine=baselinecreatinine,
                    gender=gender,
                )
                try:
                    ckddetail_service.process_args()
                except GoutHelperValidationError:
                    errors.append(ckddetail_service.errors)
            if aki:
                try:
                    aki_service = AkiCreator(
                        status=aki__status,
                        creatinines=aki__creatinines,
                        baselinecreatinine=baselinecreatinine,
                        stage=ckddetail_service.stage if ckd else None,
                    )
                except GoutHelperValidationError:
                    errors.append(aki_service.errors)
            else:
                aki_service = None
                # AkiEditor
                # UrateEditor
                # FlareEditor

                # Modify the arguments to be passed to the create method

                # Create directly related objects
                # if aki:
                # aki = AkiEditor(status=aki__status, creatinines=aki__creatinines)
                # if urate:
                # urate = UrateEditor.create()
                # else:
                # urate = None

                # Create the flare
                # flare = self.create(
                #     aki=aki,
                #     urate=urate,
                # )
        if errors:
            raise GoutHelperValidationError(message="Args for flare has errors.", errors=errors)
        # Create indirectly related objects and update their querysets on their relations

        # Return the flare
