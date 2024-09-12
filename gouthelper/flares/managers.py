from typing import TYPE_CHECKING, Union

from django.db.models import Manager, QuerySet

from ..akis.choices import Statuses  # type: ignore
from ..medhistorydetails.choices import DialysisChoices
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
        # Check for errors in the arguments
        # CkdDetailEditor
        # AkiEditor
        # UrateEditor
        # FlareEditor

        # Modify the arguments to be passed to the create method

        # Create directly related objects
        # aki = AkiEditor.create()
        # urate = UrateEditor.create()

        # Create the flare
        # flare = self.create()

        # Create indirectly related objects and update their querysets on their relations

        # Return the flare
        pass
