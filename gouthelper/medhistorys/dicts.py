from typing import TYPE_CHECKING, Any

from django.apps import apps

from ..treatments.choices import Treatments, TrtTypes
from .choices import Contraindications, MedHistoryTypes
from .lists import (
    CV_DISEASES,
    FLARE_MEDHISTORYS,
    FLAREAID_MEDHISTORYS,
    GOALURATE_MEDHISTORYS,
    PPX_MEDHISTORYS,
    PPXAID_MEDHISTORYS,
    ULT_MEDHISTORYS,
    ULTAID_MEDHISTORYS,
)

if TYPE_CHECKING:
    from ..utils.types import AidNames, AidTypes

CVD_CONTRAS: dict[MedHistoryTypes, Contraindications] = {cvd: Contraindications.RELATIVE for cvd in CV_DISEASES}

NSAID_CONTRAS: dict[MedHistoryTypes, Contraindications] = {
    MedHistoryTypes.ANGINA: Contraindications.ABSOLUTE,
    MedHistoryTypes.ANTICOAGULATION: Contraindications.RELATIVE,
    MedHistoryTypes.BLEED: Contraindications.ABSOLUTE,
    MedHistoryTypes.CAD: Contraindications.RELATIVE,
    MedHistoryTypes.CHF: Contraindications.ABSOLUTE,
    MedHistoryTypes.CKD: Contraindications.ABSOLUTE,
    MedHistoryTypes.GASTRICBYPASS: Contraindications.RELATIVE,
    MedHistoryTypes.HEARTATTACK: Contraindications.RELATIVE,
    MedHistoryTypes.IBD: Contraindications.RELATIVE,
    MedHistoryTypes.PUD: Contraindications.ABSOLUTE,
    MedHistoryTypes.PVD: Contraindications.RELATIVE,
    MedHistoryTypes.STROKE: Contraindications.RELATIVE,
}

HISTORY_TREATMENT_CONTRAS: dict[Treatments, dict[TrtTypes, dict[MedHistoryTypes, Contraindications]]] = {
    Treatments.ALLOPURINOL: {
        TrtTypes.ULT: {
            MedHistoryTypes.CKD: Contraindications.DOSEADJ,
            MedHistoryTypes.XOIINTERACTION: Contraindications.ABSOLUTE,
        }
    },
    Treatments.CELECOXIB: {
        TrtTypes.FLARE: NSAID_CONTRAS,
        TrtTypes.PPX: NSAID_CONTRAS,
    },
    Treatments.COLCHICINE: {
        TrtTypes.FLARE: {
            MedHistoryTypes.CKD: Contraindications.DOSEADJ,
            MedHistoryTypes.COLCHICINEINTERACTION: Contraindications.RELATIVE,
        },
        TrtTypes.PPX: {
            MedHistoryTypes.CKD: Contraindications.DOSEADJ,
            MedHistoryTypes.COLCHICINEINTERACTION: Contraindications.RELATIVE,
        },
    },
    Treatments.DICLOFENAC: {
        TrtTypes.FLARE: NSAID_CONTRAS,
        TrtTypes.PPX: NSAID_CONTRAS,
    },
    Treatments.FEBUXOSTAT: {
        TrtTypes.ULT: {
            MedHistoryTypes.CKD: Contraindications.DOSEADJ,
            MedHistoryTypes.XOIINTERACTION: Contraindications.ABSOLUTE,
        }
        | CVD_CONTRAS
    },
    Treatments.IBUPROFEN: {
        TrtTypes.FLARE: NSAID_CONTRAS,
        TrtTypes.PPX: NSAID_CONTRAS,
    },
    Treatments.INDOMETHACIN: {
        TrtTypes.FLARE: NSAID_CONTRAS,
        TrtTypes.PPX: NSAID_CONTRAS,
    },
    Treatments.MELOXICAM: {
        TrtTypes.FLARE: NSAID_CONTRAS,
        TrtTypes.PPX: NSAID_CONTRAS,
    },
    Treatments.METHYLPREDNISOLONE: {
        TrtTypes.FLARE: {},
        TrtTypes.PPX: {},
    },
    Treatments.NAPROXEN: {
        TrtTypes.FLARE: NSAID_CONTRAS,
        TrtTypes.PPX: NSAID_CONTRAS,
    },
    Treatments.PREDNISONE: {
        TrtTypes.FLARE: {},
        TrtTypes.PPX: {},
    },
    Treatments.PROBENECID: {
        TrtTypes.ULT: {
            MedHistoryTypes.CKD: Contraindications.RELATIVE,
            MedHistoryTypes.URATESTONES: Contraindications.ABSOLUTE,
        }
    },
}


def historys_get_treatments_contras() -> dict[Treatments, dict[TrtTypes, dict[MedHistoryTypes, Contraindications]]]:
    """Returns a dictionary of contraindications for all treatments.

    Returns:
        dict: of all Treatments and their contraindications
    """
    return HISTORY_TREATMENT_CONTRAS


def get_dict_of_aid_tuple_of_model_and_medhistorytypes() -> dict["AidTypes", list[MedHistoryTypes]]:
    return {
        "Flare": (apps.get_model("flares", "Flare"), FLARE_MEDHISTORYS),
        "FlareAid": (apps.get_model("flareaids", "FlareAid"), FLAREAID_MEDHISTORYS),
        "GoalUrate": (apps.get_model("goalurates", "GoalUrate"), GOALURATE_MEDHISTORYS),
        "PpxAid": (apps.get_model("ppxaids", "PpxAid"), PPXAID_MEDHISTORYS),
        "Ppx": (apps.get_model("ppxs", "Ppx"), PPX_MEDHISTORYS),
        "UltAid": (apps.get_model("ultaids", "UltAid"), ULTAID_MEDHISTORYS),
        "Ult": (apps.get_model("ults", "Ult"), ULT_MEDHISTORYS),
    }


class MedHistoryTypesAids:
    def __init__(
        self,
        mhtypes: list[MedHistoryTypes] | MedHistoryTypes,
        related_object: Any | None = None,
        dict_of_aid_tuple_of_model_and_medhistorytypes: dict["AidTypes", list[MedHistoryTypes]] | None = None,
    ):
        self.mhtypes = mhtypes if isinstance(mhtypes, list) else [mhtypes]
        self.related_object = related_object
        self.dict_of_aid_tuple_of_model_and_medhistorytypes = (
            dict_of_aid_tuple_of_model_and_medhistorytypes or get_dict_of_aid_tuple_of_model_and_medhistorytypes()
        )
        for aid_attr, model_medhistorytypes_tuple in self.dict_of_aid_tuple_of_model_and_medhistorytypes.items():
            setattr(self, aid_attr, model_medhistorytypes_tuple[0])
            setattr(self, f"{aid_attr.upper()}_MEDHISTORYS", model_medhistorytypes_tuple[1])

    def mhtype_in_related_objects_medhistorys(self, mhtype: MedHistoryTypes, aid_type: "AidTypes") -> bool:
        self.related_object_error_check()
        aid_name = aid_type.__name__.lower()
        if not hasattr(self, f"related_object_is_or_has_{aid_name}"):
            return self.related_object_is_or_has_aid_type(aid_name, aid_type) and self.mhtype_in_aid_medhistorys(
                mhtype, aid_name
            )
        else:
            return getattr(self, f"related_object_is_or_has_{aid_name}") and self.mhtype_in_aid_medhistorys(
                mhtype, aid_name
            )

    def related_object_is_or_has_aid_type(self, aid_name: "AidNames", aid_type: "AidTypes") -> bool:
        self.related_object_error_check()
        return getattr(self.related_object, aid_name, None) or isinstance(self.related_object, aid_type)

    def related_object_error_check(self) -> None:
        if not self.related_object or (
            getattr(self.related_object, "user", False) and self.related_object.user != self.related_object
        ):
            raise ValueError(
                "Method must be called with a related object that either does not have a user or IS a user"
            )

    def mhtype_in_aid_medhistorys(self, mhtype: MedHistoryTypes, aid_name: "AidNames") -> bool:
        return mhtype in getattr(self, f"{aid_name.upper()}_MEDHISTORYS")

    @property
    def related_object_is_or_has_flare(self) -> bool:
        return (
            getattr(self.related_object, "flare", None)
            and self.related_object.flare
            or getattr(self.related_object, "flare_qs", None)
            and self.related_object.flare_qs
            or getattr(self.related_object, "flares_qs", None)
            and self.related_object.flares_qs
            or isinstance(self.related_object, getattr(self, "Flare"))
        )

    def mhtype_in_related_object_aid(self, mhtype: MedHistoryTypes) -> bool:
        return next(
            iter(
                True
                for aid_type, _ in self.dict_of_aid_tuple_of_model_and_medhistorytypes.values()
                if self.mhtype_in_related_objects_medhistorys(mhtype, aid_type) is True
            ),
            False,
        )
