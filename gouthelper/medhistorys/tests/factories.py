from typing import TYPE_CHECKING, Any, Union

from factory import fuzzy  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ...utils.types import _Auto
from ..choices import MedHistoryTypes
from ..models import (
    Angina,
    Anticoagulation,
    Bleed,
    Cad,
    Chf,
    Ckd,
    Colchicineinteraction,
    Diabetes,
    Erosions,
    Gastricbypass,
    Gout,
    Heartattack,
    Hepatitis,
    Hypertension,
    Hyperuricemia,
    Ibd,
    MedHistory,
    Menopause,
    Organtransplant,
    Osteoporosis,
    Pvd,
    Stroke,
    Tophi,
    Uratestones,
    Xoiinteraction,
)

Auto: Any = _Auto()

if TYPE_CHECKING:
    from ...medhistorydetails.models import GoutDetail
    from ...users.models import Pseudopatient
    from ..types import GoutData


class MedHistoryFactory(DjangoModelFactory):
    class Meta:
        model = MedHistory

    medhistorytype = fuzzy.FuzzyChoice(MedHistoryTypes.values)


class AnginaFactory(MedHistoryFactory):
    class Meta:
        model = Angina


class AnticoagulationFactory(MedHistoryFactory):
    class Meta:
        model = Anticoagulation


class BleedFactory(MedHistoryFactory):
    class Meta:
        model = Bleed


class CadFactory(MedHistoryFactory):
    """Factory for creating Cad MedHistory objects."""

    class Meta:
        model = Cad


class ChfFactory(MedHistoryFactory):
    class Meta:
        model = Chf


class CkdFactory(MedHistoryFactory):
    class Meta:
        model = Ckd


class ColchicineinteractionFactory(MedHistoryFactory):
    class Meta:
        model = Colchicineinteraction


class DiabetesFactory(MedHistoryFactory):
    class Meta:
        model = Diabetes


class ErosionsFactory(MedHistoryFactory):
    class Meta:
        model = Erosions


class GastricbypassFactory(MedHistoryFactory):
    class Meta:
        model = Gastricbypass


class GoutFactory(MedHistoryFactory):
    class Meta:
        model = Gout


def get_gout_api_data(
    patient: Union["Pseudopatient", None] = None,
    gout: Gout | None = None,
    value: bool = None,
    at_goal: bool = None,
    at_goal_long_term: bool = None,
    flaring: bool = None,
    on_ppx: bool = None,
    on_ult: bool = None,
    starting_ult: bool = None,
) -> "GoutData":
    if patient and gout:
        raise ValueError("Cannot provide both patient and gout.")
    goutdetail: Union["GoutDetail", None] = getattr(gout, "goutdetail", None)

    return {
        "id": gout.pk if gout else None,
        "value": value if value != Auto else True,
        "goutdetail": {
            "id": goutdetail.pk if goutdetail else None,
            "at_goal": at_goal if at_goal is not None else goutdetail.at_goal if goutdetail else False,
            "at_goal_long_term": (
                at_goal_long_term
                if at_goal_long_term is not None
                else goutdetail.at_goal_long_term
                if goutdetail
                else False
            ),
            "flaring": flaring if flaring is not None else goutdetail.flaring if goutdetail else False,
            "on_ppx": on_ppx if on_ppx is not None else goutdetail.on_ppx if goutdetail else False,
            "on_ult": on_ult if on_ult is not None else goutdetail.on_ult if goutdetail else False,
            "starting_ult": (
                starting_ult if starting_ult is not None else goutdetail.starting_ult if goutdetail else False
            ),
        },
    }


class HeartattackFactory(MedHistoryFactory):
    class Meta:
        model = Heartattack


class HepatitisFactory(MedHistoryFactory):
    class Meta:
        model = Hepatitis


class HypertensionFactory(MedHistoryFactory):
    class Meta:
        model = Hypertension


class HyperuricemiaFactory(MedHistoryFactory):
    class Meta:
        model = Hyperuricemia


class IbdFactory(MedHistoryFactory):
    class Meta:
        model = Ibd


class MenopauseFactory(MedHistoryFactory):
    class Meta:
        model = Menopause


class OrgantransplantFactory(MedHistoryFactory):
    class Meta:
        model = Organtransplant


class OsteoporosisFactory(MedHistoryFactory):
    class Meta:
        model = Osteoporosis


class PvdFactory(MedHistoryFactory):
    class Meta:
        model = Pvd


class StrokeFactory(MedHistoryFactory):
    class Meta:
        model = Stroke


class TophiFactory(MedHistoryFactory):
    class Meta:
        model = Tophi


class UratestonesFactory(MedHistoryFactory):
    class Meta:
        model = Uratestones


class XoiinteractionFactory(MedHistoryFactory):
    class Meta:
        model = Xoiinteraction
