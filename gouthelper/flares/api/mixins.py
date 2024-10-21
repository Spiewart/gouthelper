from typing import TYPE_CHECKING, Union

from ...akis.api.mixins import AkiAPICreateMixin
from ...dateofbirths.api.mixins import DateOfBirthAPIMixin
from ...genders.api.mixins import GenderAPIMixin
from ...labs.api.mixins import UrateAPICreateMixin, UrateAPIUpdateMixin
from ...medhistorys.api.mixins import (
    AnginaAPIMixin,
    CadAPIMixin,
    ChfAPIMixin,
    CkdAPIMixin,
    GoutAPIMixin,
    HeartattackAPIMixin,
    HypertensionAPIMixin,
    MenopauseAPIMixin,
    PvdAPIMixin,
    StrokeAPIMixin,
)
from ..models import Flare

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

    from ...akis.choices import Statuses
    from ...akis.models import Aki
    from ...dateofbirths.models import DateOfBirth
    from ...flareaids.models import FlareAid
    from ...genders.choices import Genders
    from ...genders.models import Gender
    from ...labs.models import BaselineCreatinine, Creatinine, Urate
    from ...medhistorydetails.choices import DialysisChoices, DialysisDurations, Stages
    from ...medhistorydetails.models import CkdDetail
    from ...medhistorys.models import (
        Cad,
        Chf,
        Ckd,
        Gout,
        Heartattack,
        Hypertension,
        MedHistory,
        Menopause,
        Pvd,
        Stroke,
    )
    from ...users.models import Pseudopatient
    from ..choices import DiagnosedChoices, LimitedJointChoices


class FlareAPIMixin(
    AkiAPICreateMixin,
    DateOfBirthAPIMixin,
    GenderAPIMixin,
    AnginaAPIMixin,
    CadAPIMixin,
    ChfAPIMixin,
    CkdAPIMixin,
    GoutAPIMixin,
    HeartattackAPIMixin,
    HypertensionAPIMixin,
    MenopauseAPIMixin,
    PvdAPIMixin,
    StrokeAPIMixin,
    UrateAPICreateMixin,
):
    patient: Union["Pseudopatient", None]
    aki: Union["Aki", "UUID", bool, None]
    aki__status: Union["Statuses", None]
    creatinines_data: list["Creatinine", "UUID"] | None
    angina: Union["MedHistory", "UUID", None]
    angina__value: bool | None
    cad: Union["Cad", "MedHistory", "UUID", None]
    cad__value: bool | None
    chf: Union["Chf", "MedHistory", "UUID", None]
    chf__value: bool | None
    ckd: Union["Ckd", "MedHistory", "UUID", None]
    ckd__value: bool | None
    baselinecreatinine: Union["BaselineCreatinine", "UUID", None]
    baselinecreatinine__value: Union["Decimal", None]
    ckddetail: Union["CkdDetail", "UUID", None]
    ckddetail__dialysis: bool
    ckddetail__dialysis_type: Union["DialysisChoices", None]
    ckddetail__dialysis_duration: Union["DialysisDurations", None]
    ckddetail__stage: Union["Stages", None]
    crystal_analysis: bool
    dateofbirth: Union["DateOfBirth", "UUID", None]
    dateofbirth__value: Union["date", None]
    dateofbirth_optional: bool = True
    date_ended: Union["date", None]
    date_started: "date"
    diagnosed: Union["DiagnosedChoices", None]
    flareaid: Union["FlareAid", "UUID", None]
    gender: Union["Gender", None]
    gender__value: Union["Genders", None]
    gender_optional: bool = True
    gout: Union["Gout", "MedHistory", "UUID", None]
    gout__value: bool | None
    joints: list["LimitedJointChoices"]
    heartattack: Union["Heartattack", "MedHistory", "UUID", None]
    heartattack__value: bool | None
    hypertension: Union["Hypertension", "MedHistory", "UUID", None]
    hypertension__value: bool | None
    menopause: Union["Menopause", "MedHistory", "UUID", None]
    menopause__value: bool | None
    onset: bool
    pvd: Union["Pvd", "MedHistory", "UUID", None]
    pvd__value: bool | None
    redness: bool
    stroke: Union["Stroke", "MedHistory", "UUID", None]
    stroke__value: bool | None
    urate: Union["Urate", "UUID", None]
    urate__value: Union["Decimal", None]

    def set_attrs(self) -> None:
        """Updates the instance attributes for correct processing between related models."""
        if self.baselinecreatinine__value:
            self.dateofbirth_optional = False
            self.gender_optional = False


class FlareAPICreateMixin(FlareAPIMixin):
    def create_flare(self) -> Flare:
        self.set_attrs()
        self.check_for_flare_create_errors()
        self.check_for_and_raise_errors(model_name="Flare")
        self.process_dateofbirth()
        self.process_gender()
        if self.aki_should_be_created:
            self.create_aki()
        if self.urate_should_be_created:
            self.create_urate()
        self.flare = Flare.objects.create(
            patient=self.patient,
            dateofbirth=self.dateofbirth if not self.patient else None,
            gender=self.gender if not self.patient else None,
            date_started=self.date_started,
            date_ended=self.date_ended,
            onset=self.onset,
            redness=self.redness,
            crystal_analysis=self.crystal_analysis,
            diagnosed=self.diagnosed,
            flareaid=self.flareaid,
            joints=self.joints,
            aki=self.aki,
            urate=self.urate,
        )
        self.process_angina()
        self.process_cad()
        self.process_chf()
        self.process_ckd()
        self.process_gout()
        self.process_heartattack()
        self.process_hypertension()
        self.process_menopause()
        self.process_pvd()
        self.process_stroke()
        return self.flare

    def check_for_flare_create_errors(self):
        if self.flare:
            self.add_errors(
                api_args=[("flare", f"{self.flare} already exists.")],
            )


class FlareAPIUpdateMixin(FlareAPIMixin, UrateAPIUpdateMixin):
    flare: Union["Flare", "UUID", None]
