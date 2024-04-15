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
    from ..flareaids.models import FlareAid
    from ..flares.models import Flare
    from ..goalurates.models import GoalUrate
    from ..ppxaids.models import PpxAid
    from ..ppxs.models import Ppx
    from ..ultaids.models import UltAid
    from ..ults.models import Ult

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


class MedHistoryTypesAids:
    def __init__(
        self,
        mhtypes: list[MedHistoryTypes] | MedHistoryTypes,
        related_object: Any | None = None,
    ):
        self.mhtypes = mhtypes if isinstance(mhtypes, list) else [mhtypes]
        self.related_object = related_object
        self.Flare = apps.get_model("flares", "Flare")
        self.FlareAid = apps.get_model("flareaids", "FlareAid")
        self.GoalUrate = apps.get_model("goalurates", "GoalUrate")
        self.PpxAid = apps.get_model("ppxaids", "PpxAid")
        self.Ppx = apps.get_model("ppxs", "Ppx")
        self.UltAid = apps.get_model("ultaids", "UltAid")
        self.Ult = apps.get_model("ults", "Ult")

    def get_medhistorytype_aid_list(
        self,
        mhtype: MedHistoryTypes,
    ) -> list[
        type["FlareAid"]
        | type["Flare"]
        | type["GoalUrate"]
        | type["PpxAid"]
        | type["Ppx"]
        | type["UltAid"]
        | type["Ult"]
    ]:
        aid_list = []
        if (
            self.related_object
            and (
                getattr(self.related_object, "flare", None)
                and self.related_object.flare
                or getattr(self.related_object, "flare_qs", None)
                and self.related_object.flare_qs
                or getattr(self.related_object, "flares_qs", None)
                and self.related_object.flares_qs
                or isinstance(self.related_object, self.Flare)
            )
            or not self.related_object
        ) and mhtype in FLARE_MEDHISTORYS:
            aid_list.append(self.Flare)
        if (
            (
                self.related_object
                and getattr(self.related_object, "flareaid", None)
                or isinstance(self.related_object, self.FlareAid)
            )
            or not self.related_object
        ) and mhtype in FLAREAID_MEDHISTORYS:
            aid_list.append(self.FlareAid)
        if (
            (
                self.related_object
                and getattr(self.related_object, "goalurate", None)
                or isinstance(self.related_object, self.GoalUrate)
            )
            or not self.related_object
        ) and mhtype in GOALURATE_MEDHISTORYS:
            aid_list.append(self.GoalUrate)
        if (
            (
                self.related_object
                and getattr(self.related_object, "ppxaid", None)
                or isinstance(self.related_object, self.PpxAid)
            )
            or not self.related_object
        ) and mhtype in PPXAID_MEDHISTORYS:
            aid_list.append(self.PpxAid)
        if (
            (
                self.related_object
                and getattr(self.related_object, "ppx", None)
                or isinstance(self.related_object, self.Ppx)
            )
            or not self.related_object
        ) and mhtype in PPX_MEDHISTORYS:
            aid_list.append(self.Ppx)
        if (
            (
                self.related_object
                and getattr(self.related_object, "ultaid", None)
                or isinstance(self.related_object, self.UltAid)
            )
            or not self.related_object
        ) and mhtype in ULTAID_MEDHISTORYS:
            aid_list.append(self.UltAid)
        if (
            (
                self.related_object
                and getattr(self.related_object, "ult", None)
                or isinstance(self.related_object, self.Ult)
            )
            or not self.related_object
        ) and mhtype in ULT_MEDHISTORYS:
            aid_list.append(self.Ult)
        return aid_list

    def get_medhistorytypes_aid_dict(
        self,
    ) -> dict[
        MedHistoryTypes,
        list[
            type["FlareAid"]
            | type["Flare"]
            | type["GoalUrate"]
            | type["PpxAid"]
            | type["Ppx"]
            | type["UltAid"]
            | type["Ult"]
        ],
    ]:
        """Returns a list of all models that use the MedHistoryTypes model.
        Can filter by the types of model that the optional patient has if provided.

        Args:
            mhtypes (MedHistoryTypes): list or single MedHistoryTypes
            patient (Pseudopatient, optional): the optional patient model

        Returns:
            dict: of all models that use the MedHistoryTypes model filtered
                by the types of model that the optional patient has if provided
        """
        aid_dict = {}
        for mhtype in self.mhtypes:
            aid_dict[mhtype] = self.get_medhistorytype_aid_list(mhtype)
        return aid_dict
