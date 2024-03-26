from typing import TYPE_CHECKING, Union

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
    from ..users.models import Pseudopatient

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
            MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY: Contraindications.ABSOLUTE,
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
            MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY: Contraindications.ABSOLUTE,
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
        patient: Union["Pseudopatient", None] = None,
    ):
        self.mhtypes = mhtypes if isinstance(mhtypes, list) else [mhtypes]
        self.patient = patient
        self._set_model_attrs()

    def _set_model_attrs(self):
        if (
            self.patient
            and (hasattr(self.patient, "flare_qs") or hasattr(self.patient, "flares_qs"))
            or not self.patient
        ) and next(iter(self.mhtypes)) in FLARE_MEDHISTORYS:
            self.Flare = apps.get_model("flares", "Flare")
        if (
            self.patient
            and hasattr(self.patient, "flareaid")
            or not self.patient
            and next(iter(self.mhtypes)) in FLAREAID_MEDHISTORYS
        ):
            self.FlareAid = apps.get_model("flareaids", "FlareAid")
        if (
            self.patient
            and hasattr(self.patient, "goalurate")
            or not self.patient
            and next(iter(self.mhtypes)) in GOALURATE_MEDHISTORYS
        ):
            self.GoalUrate = apps.get_model("goalurates", "GoalUrate")
        if (
            self.patient
            and hasattr(self.patient, "ppxaid")
            or not self.patient
            and next(iter(self.mhtypes)) in PPXAID_MEDHISTORYS
        ):
            self.PpxAid = apps.get_model("ppxaids", "PpxAid")
        if (
            self.patient
            and hasattr(self.patient, "ppx")
            or not self.patient
            and next(iter(self.mhtypes)) in PPX_MEDHISTORYS
        ):
            self.Ppx = apps.get_model("ppxs", "Ppx")
        if (
            self.patient
            and hasattr(self.patient, "ultaid")
            or not self.patient
            and next(iter(self.mhtypes)) in ULTAID_MEDHISTORYS
        ):
            self.UltAid = apps.get_model("ultaids", "UltAid")
        if (
            self.patient
            and hasattr(self.patient, "ult")
            or not self.patient
            and next(iter(self.mhtypes)) in ULT_MEDHISTORYS
        ):
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
            self.patient
            and (
                hasattr(self.patient, "flare_qs")
                and self.patient.flare_qs
                or hasattr(self.patient, "flares_qs")
                and self.patient.flares_qs
            )
            or not self.patient
        ) and mhtype in FLARE_MEDHISTORYS:
            aid_list.append(self.Flare)
        if (self.patient and hasattr(self.patient, "flareaid") or not self.patient) and mhtype in FLAREAID_MEDHISTORYS:
            aid_list.append(self.FlareAid)
        if (
            self.patient and hasattr(self.patient, "goalurate") or not self.patient
        ) and mhtype in GOALURATE_MEDHISTORYS:
            aid_list.append(self.GoalUrate)
        if (self.patient and hasattr(self.patient, "ppxaid") or not self.patient) and mhtype in PPXAID_MEDHISTORYS:
            aid_list.append(self.PpxAid)
        if (self.patient and hasattr(self.patient, "ppx") or not self.patient) and mhtype in PPX_MEDHISTORYS:
            aid_list.append(self.Ppx)
        if (self.patient and hasattr(self.patient, "ultaid") or not self.patient) and mhtype in ULTAID_MEDHISTORYS:
            aid_list.append(self.UltAid)
        if (self.patient and hasattr(self.patient, "ult") or not self.patient) and mhtype in ULT_MEDHISTORYS:
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
