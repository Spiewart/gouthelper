import json
from typing import TYPE_CHECKING, Literal, Union

from django.apps import apps  # pylint: disable=E0401  # type: ignore
from django.contrib.auth import get_user_model  # pylint: disable=E0401  # type: ignore
from django.core.serializers.json import DjangoJSONEncoder  # pylint: disable=E0401  # type: ignore
from django.db.models import OneToOneField, QuerySet  # pylint: disable=E0401  # type: ignore
from django.utils.functional import cached_property  # type: ignore  # pylint: disable=E0401

from ..dateofbirths.helpers import age_calc
from ..defaults.helpers import defaults_treatments_create_dosing_dict
from ..defaults.selectors import (
    defaults_defaultmedhistorys_trttype,
    defaults_defaulttrts_trttype,
    defaults_flareaidsettings,
    defaults_ppxaidsettings,
    defaults_ultaidsettings,
)
from ..ethnicitys.helpers import ethnicitys_hlab5801_risk
from ..medhistorydetails.choices import DialysisChoices, Stages
from ..medhistorys.choices import Contraindications, MedHistoryTypes
from ..medhistorys.dicts import CVD_CONTRAS
from ..medhistorys.helpers import medhistorys_get
from ..treatments.choices import (
    AllopurinolDoses,
    ColchicineDoses,
    Freqs,
    NsaidChoices,
    SteroidChoices,
    Treatments,
    TrtTypes,
)
from .helpers import duration_decimal_parser

if TYPE_CHECKING:
    from ..dateofbirths.models import DateOfBirth
    from ..defaults.models import FlareAidSettings, PpxAidSettings, UltAidSettings
    from ..ethnicitys.models import Ethnicity
    from ..flareaids.models import FlareAid
    from ..flares.models import Flare
    from ..genders.models import Gender
    from ..goalurates.models import GoalUrate
    from ..labs.models import BaselineCreatinine, Hlab5801
    from ..medallergys.models import MedAllergy
    from ..medhistorydetails.models import CkdDetail, GoutDetail
    from ..medhistorys.models import Ckd, MedHistory
    from ..ppxaids.models import PpxAid
    from ..ppxs.models import Ppx
    from ..ultaids.models import UltAid
    from ..ults.models import Ult

    User = get_user_model()


def aids_assign_baselinecreatinine(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"],
) -> Union["BaselineCreatinine", None]:
    """Method that takes a list of userless medhistorys and tries to find one with a BaselineCreatinine.
    Returns BaselineCreatinine if found, otherwise None.

    Args:
        medhistorys (QuerySet[MedHistory]): QuerySet of MedHistory objects.
    Returns:
        Union[BaselineCreatinine, None]: BaselineCreatinine object or None.
    """
    ckd = medhistorys_get(medhistorys, MedHistoryTypes.CKD)
    if ckd and hasattr(ckd, "baselinecreatinine"):
        return ckd.baselinecreatinine
    return None


def aids_assign_ckddetail(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"],
) -> Union["CkdDetail", None]:
    """Method that takes a list of userless medhistorys and tries to find one with a CkdDetail.
    Returns CkdDetail if found, otherwise None.

    Args:
        medhistorys (QuerySet[MedHistory]): QuerySet of MedHistory objects.
    Returns:
        Union[CkdDetail, None]: CkdDetail object or None.
    """
    ckd = medhistorys_get(medhistorys, MedHistoryTypes.CKD)
    if ckd and hasattr(ckd, "ckddetail"):
        return ckd.ckddetail
    return None


def aids_assign_goutdetail(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"],
) -> Union["GoutDetail", None]:
    """Method that takes a list of userless medhistorys and tries to find one with a GoutDetail.
    Returns GoutDetail if found, otherwise None.

    Args:
        medhistorys (QuerySet[MedHistory]): QuerySet of MedHistory objects.
    Returns:
        Union[GoutDetail, None]: GoutDetail object or None.
    """
    gout = medhistorys_get(medhistorys, MedHistoryTypes.GOUT)
    if gout and hasattr(gout, "goutdetail"):
        return gout.goutdetail
    return None


def aids_colchicine_ckd_contra(
    ckd: Union["Ckd", None],
    ckddetail: Union["CkdDetail", None],
    defaulttrtsettings: Union["FlareAidSettings", "PpxAidSettings"],
) -> Contraindications | None:
    """Method that takes an Aid/User/Ultplan's Ckd and CkdDetail and determines
    whether or not colchicine should be contraindicated, dose-adjusted, or neither.

    Args:
        ckd (Ckd): Ckd object.
        ckddetail (CkdDetail): CkdDetail object.
        defaulttrtsettings (Union[FlareAidSettings, PpxAidSettings]): FlareAidSettings or \
PpxAidSettings object.

    Returns:
        Union[Contraindications, None]: Contraindications enum or None.
    """
    if ckd:
        if ckddetail:
            if ckddetail.stage is not None and ckddetail.stage <= 3 and defaulttrtsettings.colch_ckd is True:
                return Contraindications.DOSEADJ
            else:
                return Contraindications.ABSOLUTE
        else:
            return Contraindications.ABSOLUTE
    return None


def aids_create_trts_dosing_dict(default_trts: "QuerySet") -> dict:
    """Method that takes a list of DefaultTrt objects, typically for a type of
    Gout Treatment (Flare, PPx, ULT), and returns a dictionary with dosing info.

    Args:
        default_trts (QuerySet): QuerySet of DefaultTrt objects.

    Returns: dict
    """
    default_dosing_dict = defaults_treatments_create_dosing_dict(default_trts=default_trts)
    for trt in default_dosing_dict.keys():
        default_dosing_dict[trt].update({"contra": False})
    return default_dosing_dict


def aids_dict_to_json(aid_dict: dict) -> str:
    """Converts a dictionary trt_dict to JSON for saving to decisionaid field and
    for comparison."""
    return json.dumps(aid_dict, indent=4, cls=DjangoJSONEncoder)


def aids_dose_adjust_allopurinol_ckd(
    trt_dict: dict,
    defaulttrtsettings: "UltAidSettings",
    dialysis: DialysisChoices | None,
    stage: Stages | None,
) -> dict:
    """Method that dose adjusts allopurinol for the presence of CKD and dialysis.

    FitzGerald JD, et al. 2020 American College of Rheumatology Guideline
    for the Management of Gout. Arthritis Care Res (Hoboken). 2020 Jun;72(6):744-760.
    doi: 10.1002/acr.24180. PMID: 32391934.

    Vargas-Santos AB, Neogi T. Management of Gout and Hyperuricemia in CKD.
    Am J Kidney Dis. 2017 Sep;70(3):422-439. doi: 10.1053/j.ajkd.2017.01.055.
    PMCID: PMC5572666.

    Args:
        trt_dict (dict): Dictionary of Treatments.
        defaulttrtsettings (UltAidSettings): UltAidSettings object.
        dialysis (Union[DialysisChoices, None]): DialysisChoices enum or None.
        stage (Union[Literal[3], Literal[4], Literal[5], None]): CKD stage enum or None.

    Returns:
        dict: Dictionary of Treatments, potentially with dose adjustments.
    """
    treatment_dict = trt_dict
    if dialysis is None:
        if defaulttrtsettings.allo_ckd_fixed_dose is True:
            treatment_dict[Treatments.ALLOPURINOL]["dose"] = AllopurinolDoses.FIFTY
            treatment_dict[Treatments.ALLOPURINOL]["dose_adj"] = AllopurinolDoses.FIFTY
        else:
            if stage == Stages.THREE:
                treatment_dict[Treatments.ALLOPURINOL]["dose"] = AllopurinolDoses.FIFTY
                treatment_dict[Treatments.ALLOPURINOL]["dose_adj"] = AllopurinolDoses.FIFTY
            elif stage == Stages.FOUR:
                treatment_dict[Treatments.ALLOPURINOL]["dose"] = AllopurinolDoses.FIFTY
                treatment_dict[Treatments.ALLOPURINOL]["dose_adj"] = AllopurinolDoses.FIFTY
                treatment_dict[Treatments.ALLOPURINOL]["freq"] = Freqs.QOTHERDAY
            elif stage == Stages.FIVE:
                treatment_dict[Treatments.ALLOPURINOL]["dose"] = AllopurinolDoses.FIFTY
                treatment_dict[Treatments.ALLOPURINOL]["dose_adj"] = AllopurinolDoses.FIFTY
                treatment_dict[Treatments.ALLOPURINOL]["freq"] = Freqs.BIW
    elif dialysis == DialysisChoices.PERITONEAL:
        treatment_dict[Treatments.ALLOPURINOL]["dose"] = AllopurinolDoses.FIFTY
        treatment_dict[Treatments.ALLOPURINOL]["dose_adj"] = AllopurinolDoses.FIFTY
    else:
        treatment_dict[Treatments.ALLOPURINOL]["dose"] = AllopurinolDoses.FIFTY
        treatment_dict[Treatments.ALLOPURINOL]["dose_adj"] = AllopurinolDoses.FIFTY
        treatment_dict[Treatments.ALLOPURINOL]["freq"] = Freqs.TIW
    return treatment_dict


def aids_dose_adjust_colchicine(
    trt_dict: dict,
    aid_type: TrtTypes,
    defaulttrtsettings: Union["FlareAidSettings", "PpxAidSettings"],
) -> dict:
    """Method that takes a trt_dict and renally adjusts the dosing for Colchicine.
    Checks if the default_settings dictates the dose is adjusted or whether the frequency
    is adjusted.

    Args:
        trt_dict (dict): {TrtTypes: {TrtInfo}}
        aid_type (trttypes): TrtTypes enum to determine how to set the Colchicine dosing.
        defaulttrtsettings (Union[FlareAidSettings, PpxAidSettings]

    Returns:
        dict: {TrtTypes: {TrtInfo}} with colchicine dosing adjusted.
    """
    if defaulttrtsettings.colch_dose_adjust is True:
        if aid_type == TrtTypes.FLARE:
            if trt_dict[Treatments.COLCHICINE]["dose"] == ColchicineDoses.POINTSIX:
                trt_dict[Treatments.COLCHICINE]["dose"] = ColchicineDoses.POINTTHREE
            if trt_dict[Treatments.COLCHICINE]["dose2"] == ColchicineDoses.ONEPOINTTWO:
                trt_dict[Treatments.COLCHICINE]["dose2"] = ColchicineDoses.POINTSIX
            if trt_dict[Treatments.COLCHICINE]["dose3"] == ColchicineDoses.POINTSIX:
                trt_dict[Treatments.COLCHICINE]["dose3"] = ColchicineDoses.POINTTHREE
        else:
            if trt_dict[Treatments.COLCHICINE]["dose"] == ColchicineDoses.POINTSIX:
                trt_dict[Treatments.COLCHICINE]["dose"] = ColchicineDoses.POINTTHREE
    else:
        if aid_type == TrtTypes.FLARE:
            if trt_dict[Treatments.COLCHICINE]["dose2"] == ColchicineDoses.ONEPOINTTWO:
                trt_dict[Treatments.COLCHICINE]["dose2"] = ColchicineDoses.POINTSIX
            if trt_dict[Treatments.COLCHICINE]["freq"] == Freqs.BID:
                trt_dict[Treatments.COLCHICINE]["freq"] = Freqs.QDAY
        else:
            if trt_dict[Treatments.COLCHICINE]["freq"] == Freqs.QDAY:
                trt_dict[Treatments.COLCHICINE]["freq"] = Freqs.QOTHERDAY
    return trt_dict


def aids_dose_adjust_febuxostat_ckd(
    trt_dict: dict,
    defaulttrtsettings: "UltAidSettings",
) -> dict:
    """Method that dose adjusts febuxostat for the presence of CKD.

    FitzGerald JD, et al. 2020 American College of Rheumatology Guideline
    for the Management of Gout. Arthritis Care Res (Hoboken). 2020 Jun;72(6):744-760.
    doi: 10.1002/acr.24180. PMID: 32391934.

    Args:
        trt_dict (dict): Dictionary of Treatments.
        defaulttrtsettings (UltAidSettings): UltAidSettings object.

    Returns:
        dict: Dictionary of Treatments, potentially with dose adjustments.
    """
    trt_dict[Treatments.FEBUXOSTAT]["dose"] = defaulttrtsettings.febu_ckd_initial_dose
    trt_dict[Treatments.FEBUXOSTAT]["dose_adj"] = defaulttrtsettings.febu_ckd_initial_dose
    return trt_dict


def aids_hlab5801_contra(
    hlab5801: Union["Hlab5801", None],
    ethnicity: Union["Ethnicity", None],
    ultaidsettings: "UltAidSettings",
) -> bool:
    """Method that takes optional Hlab5801, Ethnicity, and UltAidSettings
    objects and returns a bool indicating whether or not allopurinol should be
    contraindicated.

    Args:
        hlab5801 [optional]: Hlab5801 object
        ethnicity [optional]: Ethnicity object
        defaultultrtsettings [optional]: UltAidSettings object

    Returns:
        bool: True if allopurinol should be contraindicated, False if not.
    """
    if (
        (hlab5801 and hlab5801.value is True)
        or (
            ethnicity
            and (ethnicitys_hlab5801_risk(ethnicity=ethnicity))
            and not hlab5801
            and not ultaidsettings.allo_risk_ethnicity_no_hlab5801
        )
        or (not ethnicity and not hlab5801 and not ultaidsettings.allo_no_ethnicity_no_hlab5801)
    ):
        return True
    return False


def aids_json_to_trt_dict(decisionaid: str) -> dict:
    """Method that converts a trt_dict json and converts it to a python dict.
    Converts duration and decimal strings into their native Python types.

    Args:
        json "{json}": of the trt_dict

    Returns:
        {dict}: trt_dict for Aid
    """
    return json.loads(decisionaid, object_hook=duration_decimal_parser)


def aids_not_options(
    trt_dict: dict, defaultsettings: Union["FlareAidSettings", "PpxAidSettings", "UltAidSettings"]
) -> dict:
    """Method that iterates over a trt_dict and returns a dictionary of
    treatments that are contraindicated."""
    if defaultsettings and getattr(defaultsettings, "nsaids_equivalent", True):
        not_options = {}
        for trt, sub_dict in trt_dict.items():
            if sub_dict["contra"] is True:
                if trt in NsaidChoices.values:
                    not_options.update({"NSAIDs": sub_dict})
                else:
                    not_options[trt] = sub_dict
        return not_options
    else:
        return {trt: sub_dict for trt, sub_dict in trt_dict.items() if sub_dict["contra"] is True}


def aids_options(trt_dict: dict, recommendation: Treatments = None) -> dict:
    """Method that parses trt_dict (dictionary of potential Aid Treatments)
    and returns a dict of all possible Aid Treatment options by removing
    those which are contraindicated.

    args:
        trt_dict (dict): {TrtTypes: {TrtInfo}}
        recommendation (Treatments, optional): Treatment to remove from options. Defaults to None.

    returns: modified trt_dict with contraindicated treatments removed.
    """

    options_dict = trt_dict.copy()
    for trt, sub_dict in trt_dict.items():
        if sub_dict["contra"] is True:
            options_dict.pop(trt)
        elif recommendation and trt == recommendation:
            options_dict.pop(trt)
    return options_dict


def aids_xois_ckd_contra(
    ckd: Union["Ckd", None],
    ckddetail: Union["CkdDetail", None],
) -> tuple[Contraindications | None, DialysisChoices | None, Stages | None]:
    """Method that checks an Aid/User/Ultplan's Ckd and CkdDetail and determines
    whether or not allopurinol / febuxostat should be dose-adjusted
    and, if so, for what reason.

    Args:
        ckd (Ckd): Ckd object.
        ckddetail (CkdDetail): CkdDetail object.

    Returns:
        tuple of (bool, str, int):
            Contraindications or None = contraindication if True, None if not.
            DialysisChoices or None = dialysis type if there is one, None if not.
            Stages or None = CKD stage if there is one, None if not.
    """
    # Declare return variables in scope
    contraindication: Contraindications | None = None
    # Check if Ckd object exists, if not return None, None, None
    if ckd:
        # Check for CkdDetail object
        # If no CkdDetail, assume stage >= 3 and dose adjust
        # If there is a CkdDetail and the stage is >= 3 or
        # dialysis is True, then dose adjust
        if ckddetail is None:
            contraindication = Contraindications.DOSEADJ
        elif ckddetail.dialysis is True or ckddetail.stage >= Stages.THREE:
            contraindication = Contraindications.DOSEADJ
    dialysis_type = DialysisChoices(ckddetail.dialysis_type) if ckddetail and ckddetail.dialysis_type else None
    stage = Stages(ckddetail.stage) if ckddetail and ckddetail.stage else None
    # return tuple to aids_dose_adjust_allopurinol_ckd
    return contraindication, dialysis_type, stage


def aids_process_hlab5801(
    trt_dict: dict,
    hlab5801: Union["Hlab5801", None],
    ethnicity: Union["Ethnicity", None],
    ultaidsettings: "UltAidSettings",
) -> dict:
    """Method that processes a Hlab5801, ethnicity for User/UltAid/Ultplan and
    determines whether or not allopurinol is contraindicated per the UltAidSettings.
    Modifies trt_dict required *arg and returns the modified dict.

    Args:
        trt_dict (dict): {TrtTypes: {TrtInfo}}
        hlab5801 (Hlab5801): Hlab5801 object.
        ethnicity (Ethnicity): Ethnicity object.
        ultaidsettings (UltAidSettings): UltAidSettings object.

    Returns:
        trt_dict (dict): {TrtTypes: {TrtInfo}} with Allopurinol contraindicated if True.
    """

    if aids_hlab5801_contra(
        hlab5801=hlab5801,
        ethnicity=ethnicity,
        ultaidsettings=ultaidsettings,
    ):
        if trt_dict[Treatments.ALLOPURINOL]["contra"] is False:
            trt_dict[Treatments.ALLOPURINOL]["contra"] = True
    return trt_dict


def aids_process_medhistorys(
    trt_dict: dict,
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"],
    ckddetail: Union["CkdDetail", None],
    default_medhistorys: "QuerySet",
    defaulttrtsettings: Union["FlareAidSettings", "PpxAidSettings", "UltAidSettings"],
) -> dict:
    """Method that takes a trt_dict, cross-references a QuerySet of MedHistorys
    and a queryset of DefaultMedHistorys, and adds MedHistorys and Contraindications to
    trt_dict before returning.

    Takes optional args (CkdDetail, etc.) to process certain combinations of MedHistorys and Treatments.

    Args:
        trt_dict (dict): {TrtTypes: {TrtInfo}}
        medhistorys (QuerySet): QuerySet of MedHistory objects.
        ckddetail (CkdDetail or None): CkdDetail object or None
        default_medhistorys (QuerySet): QuerySet of DefaultMedHistory objects.
        defaulttrtsettings (DefaultFlare/Ppx/UltTrtSettings): FlareAidSettings or \
PpxAidSettings or UltAidSettings object.

    Returns:
        dict: {TrtTypes: {treatment dosing + "contra": True/False}}
    """
    for medhistory in medhistorys:
        contraindications = [
            default_medhistory
            for default_medhistory in default_medhistorys
            if default_medhistory.medhistorytype == medhistory.medhistorytype
        ]
        if contraindications:
            for contraindication in contraindications:
                if medhistory.medhistorytype == MedHistoryTypes.CKD:
                    if contraindication.treatment == Treatments.ALLOPURINOL:
                        allo_ckd_contra = aids_xois_ckd_contra(
                            ckd=medhistory,
                            ckddetail=ckddetail,
                        )
                        if allo_ckd_contra[0] == Contraindications.DOSEADJ:
                            trt_dict = aids_dose_adjust_allopurinol_ckd(
                                trt_dict=trt_dict,
                                defaulttrtsettings=defaulttrtsettings,
                                dialysis=allo_ckd_contra[1],
                                stage=allo_ckd_contra[2],
                            )
                    elif contraindication.treatment == Treatments.COLCHICINE:
                        colch_ckd_contra = aids_colchicine_ckd_contra(
                            ckd=medhistory,
                            ckddetail=ckddetail,
                            defaulttrtsettings=defaulttrtsettings,
                        )
                        # colch_ckd_contra is a Contraindications enum or None
                        # So, only attempt to modify the trt_dict if not None
                        if (
                            colch_ckd_contra is not None
                            and colch_ckd_contra == Contraindications.DOSEADJ
                            and not trt_dict[Treatments.COLCHICINE]["contra"]
                        ):
                            trt_dict = aids_dose_adjust_colchicine(
                                trt_dict=trt_dict,
                                aid_type=contraindication.trttype,
                                defaulttrtsettings=defaulttrtsettings,
                            )
                        elif (
                            colch_ckd_contra is not None
                            and (
                                colch_ckd_contra == Contraindications.ABSOLUTE
                                or colch_ckd_contra == Contraindications.RELATIVE
                            )
                            and trt_dict[Treatments.COLCHICINE]["contra"] is not True
                        ):
                            trt_dict[Treatments.COLCHICINE]["contra"] = True
                    elif contraindication.treatment == Treatments.FEBUXOSTAT:
                        febu_ckd_contra = aids_xois_ckd_contra(
                            ckd=medhistory,
                            ckddetail=ckddetail,
                        )
                        if febu_ckd_contra[0] == Contraindications.DOSEADJ:
                            trt_dict = aids_dose_adjust_febuxostat_ckd(
                                trt_dict=trt_dict,
                                defaulttrtsettings=defaulttrtsettings,
                            )
                    elif contraindication.treatment == Treatments.PROBENECID:
                        prob_ckd_contra = aids_probenecid_ckd_contra(
                            ckd=medhistory,
                            ckddetail=ckddetail,
                            defaulttrtsettings=defaulttrtsettings,
                        )
                        # prob_ckd_contra is a bool, so only switch if True
                        if prob_ckd_contra and not trt_dict[Treatments.PROBENECID]["contra"]:
                            trt_dict[Treatments.PROBENECID]["contra"] = True
                    elif (
                        contraindication.contraindication == Contraindications.ABSOLUTE
                        or contraindication.contraindication == Contraindications.RELATIVE
                    ) and trt_dict[contraindication.treatment]["contra"] is not True:
                        trt_dict[contraindication.treatment]["contra"] = True
                # Check if the contraindication is for febuxostat and cardiovascular disease
                # If so, if the defaulttrtsettings indicate that febuxostat should be contraindicated
                # for CV disease, then set the trt_dict[Treatments.FEBUXOSTAT]["contra"] to True
                elif (
                    contraindication.treatment == Treatments.FEBUXOSTAT
                    and contraindication.contraindication == Contraindications.RELATIVE
                    and medhistory.medhistorytype in CVD_CONTRAS
                ):
                    if not defaulttrtsettings.febu_cv_disease and not trt_dict[Treatments.FEBUXOSTAT]["contra"]:
                        trt_dict[Treatments.FEBUXOSTAT]["contra"] = True
                elif (
                    contraindication.contraindication == Contraindications.ABSOLUTE
                    or contraindication.contraindication == Contraindications.RELATIVE
                ) and trt_dict[contraindication.treatment]["contra"] is not True:
                    trt_dict[contraindication.treatment]["contra"] = True
    return trt_dict


def aids_process_medallergys(trt_dict: dict, medallergys: Union[list["MedAllergy"], "QuerySet[MedAllergy]"]) -> dict:
    """Method that modifies a trt_dict with MedAllergy information.
    Iterates over MedAllergy objects and changes the trt_dict[treatment]["contra"] to
    True for the MedAllergy.treatment key in trt_dict.

    Args:
        trt_dict (dict): {TrtTypes: {TrtInfo}}
        medallergys (QuerySet): QuerySet of MedAllergy objects.

    Returns:
        dict: {TrtTypes: {treatment info + "contra": True/False}}
    """
    treatment_dict = trt_dict
    if medallergys:
        for medallergy in medallergys:
            trt = medallergy.treatment
            if trt in treatment_dict.keys():
                if treatment_dict[trt].get("contra") is not True:
                    treatment_dict[trt]["contra"] = True
    return treatment_dict


def aids_process_nsaids(
    trt_dict: dict,
    dateofbirth: Union["DateOfBirth", None],
    defaulttrtsettings: Union["FlareAidSettings", "PpxAidSettings"],
) -> dict:
    """Method that applies NSAID contraindications to all NSAIDs in the trt_dict.
    Checks if that the defaulttrtsettings.nsaids_equivalent is True, first, if not
    then returns the trt_dict unchanged.

    Args:
        trt_dict (dict): {TrtTypes: {TrtInfo}}
        defaulttrtsettings: FlareAidSettings or PpxAidSettings

    Returns:
        trt_dict (dict): {TrtTypes: {TrtInfo}} with "contras" "sideeffects and "allergys" dicts
        consolidated across all NSAIDs.
    """

    def contraindicate_globally(trt_dict: dict) -> dict:
        """Method that iterates over trt_dict and sets all NSAIDs to contra=True.

        Args:
            trt_dict (dict): {TrtTypes: {TrtInfo}}

        Returns:
            trt_dict (dict): {TrtTypes: {TrtInfo}} with all NSAIDs contra=True.
        """
        for trt, sub_dict in trt_dict.items():
            if trt in NsaidChoices.values:
                if sub_dict["contra"] is False:
                    sub_dict["contra"] = True
        return trt_dict

    if defaulttrtsettings.nsaid_age is False and dateofbirth and age_calc(dateofbirth.value) > 65:
        return contraindicate_globally(trt_dict)
    elif not defaulttrtsettings.nsaids_equivalent:
        return trt_dict
    for trt, sub_dict in trt_dict.items():
        if trt in NsaidChoices.values and sub_dict.get("contra") is True:
            return contraindicate_globally(trt_dict)
    return trt_dict


def aids_probenecid_ckd_contra(
    ckd: Union["Ckd", None],
    ckddetail: Union["CkdDetail", None],
    defaulttrtsettings: "UltAidSettings",
) -> bool:
    """Method that checks CKD status (stage) and returns True if probenecid should be
    contraindicated. False if not.

    Args:
        ckd (Ckd or None): Ckd object or None
        ckddetail (CkdDetail or None): CkdDetail object or None
        defaulttrtsettings (UltAidSettings or None): UltAidSettings object

    Returns:
        bool: True if probenecid should be contraindicated, False if not.
    """
    # Check if there's a Ckd object
    if ckd and (
        # If there's no information on CKD stage or CKD stage is 3 or greater
        # contraindicate probenecid
        not ckddetail
        or ckddetail.stage >= defaulttrtsettings.prob_ckd_stage_contra
    ):
        return True
    return False


def aids_process_sideeffects(trt_dict: dict, sideeffects: Union["QuerySet", None]) -> dict:
    """Method that iterates over side effects looking for treatments in the trt_dict
    that are also associated with the SideEffect. If found, the trt_dict is modified
    to have ["contra"] = True for the treatment.

    Args:
        trt_dict (dict): {TrtTypes: {TrtInfo}}
        sideeffects (QuerySet): QuerySet of SideEffect objects. Each SideEffect object
        is annotated with a "treatments" attribute that is a list of Treatment enum choices.

    Returns:
        dict: {TrtTypes: {treatment + "contra": True/False}}
    """
    if sideeffects:
        for sideeffect in sideeffects:
            for treatment in sideeffect.treatments:
                try:
                    if trt_dict[treatment]["contra"] is not True:
                        trt_dict[treatment]["contra"] = True
                except KeyError:
                    continue
    return trt_dict


def aids_process_steroids(
    trt_dict: dict,
    defaulttrtsettings: Union["FlareAidSettings", "PpxAidSettings"],
) -> dict:
    """Method that applies steroid contraindications to all steroids in the trt_dict.
    Checks if that the defaulttrtsettings.steroids_equivalent is True, first, if not
    then returns the trt_dict unchanged.

    Args:
        trt_dict (dict): {TrtTypes: {TrtInfo}}
        defaulttrtsettings: FlareAidSettings or PpxAidSettings

    Returns:
        trt_dict (dict): {TrtTypes: {TrtInfo}} with "contras" "sideeffects and "allergys" dicts
        consolidated across all steroids.
    """
    if not defaulttrtsettings.steroids_equivalent:
        return trt_dict
    global_contra = False
    for trt, sub_dict in trt_dict.items():
        if trt in SteroidChoices.values and sub_dict.get("contra") is True:
            global_contra = True
    if global_contra is True:
        for trt, sub_dict in trt_dict.items():
            if trt in SteroidChoices.values:
                if sub_dict["contra"] is False:
                    sub_dict["contra"] = True
    return trt_dict


def aids_get_defaultsettings_qs(
    model: type[Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "UltAid", "Ult"]],
    user: Union["User", None] = None,
) -> QuerySet | None:
    if model == apps.get_model("flareaids", "FlareAid"):
        return defaults_flareaidsettings(user)
    elif model == apps.get_model("ppxaids", "PpxAid"):
        return defaults_ppxaidsettings(user)
    elif model == apps.get_model("ultaids", "UltAid"):
        return defaults_ultaidsettings(user)
    else:
        return None


def aid_service_get_oto(
    qs: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "UltAid", "Ult", "User"],
    model_fields: list[Literal["dateofbirth"], Literal["ethnicity"], Literal["gender"]],
    oto: Literal["dateofbirth"] | Literal["ethnicity"] | Literal["gender"],
) -> Union["DateOfBirth", "Ethnicity", "Gender", None]:
    return getattr(qs, oto, None) if oto in model_fields else None


def aid_service_check_oto_swap(
    oto: Literal["dateofbirth"] | Literal["ethnicity"] | Literal["gender"],
    qs_has_user: bool,
    model_attr: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "UltAid", "Ult"],
) -> None:
    if qs_has_user and getattr(model_attr, oto, None):
        setattr(model_attr, oto, None)


def get_service_object(
    model_attr: Literal["flareaid", "flare", "goalurate", "ppxaid", "ppx", "ultaid", "ult"],
    qs: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "UltAid", "Ult", "User"],
) -> str:
    if model_attr != "flare":
        return getattr(qs, model_attr)
    else:
        model_obj = getattr(qs, f"{model_attr}_qs")
        if isinstance(model_obj, QuerySet):
            return model_obj[0]
        elif isinstance(model_obj, list):
            return model_obj[0]
        else:
            return model_obj


class AidService:
    """Base class for Aid service class methods."""

    def __init__(
        self,
        qs: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "UltAid", "Ult", "User"],
        model: type[Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "UltAid", "Ult"]],
    ):
        self.model = model
        if isinstance(qs, QuerySet):
            self.qs = qs.get()
        else:
            self.qs = qs
        model_attr = self.model.__name__.lower()
        model_fields = [field.name for field in model._meta.get_fields() if isinstance(field, OneToOneField)]
        self.default_settings_class = getattr(model, "defaultsettings", None)
        self.default_settings_attr = (
            self.default_settings_class().__name__.lower() if self.default_settings_class else None
        )
        if isinstance(self.qs, model):
            setattr(self, model_attr, self.qs)
            self.user = self.qs.user
            self.qs_has_user = True if self.user else False
        elif isinstance(self.qs, get_user_model()):
            setattr(self, model_attr, get_service_object(model_attr=model_attr, qs=self.qs))
            self.user = self.qs
            self.qs_has_user = False
        else:
            model_name = model.__class__.__name__
            raise TypeError(f"f{model_name}DecisionAid requires a {model_name} or User instance.")
        self.model_attr = getattr(self, model_attr)
        # If the queryset is a TreatmentAid object with a user or a User,
        # try to fetch user's default settings for that type of aid
        self.defaultsettings = (
            getattr(self.user, self.default_settings_attr, None)
            if self.default_settings_attr and self.user and hasattr(self.user, self.default_settings_attr)
            else aids_get_defaultsettings_qs(model, self.user)
        )
        self.dateofbirth = aid_service_get_oto(
            qs=self.qs,
            model_fields=model_fields,
            oto="dateofbirth",
        )
        if self.dateofbirth is not None:
            self.age = age_calc(self.dateofbirth.value)
        else:
            self.age = None
        aid_service_check_oto_swap(oto="dateofbirth", qs_has_user=self.qs_has_user, model_attr=self.model_attr)
        self.ethnicity = aid_service_get_oto(
            qs=self.qs,
            model_fields=model_fields,
            oto="ethnicity",
        )
        aid_service_check_oto_swap(oto="ethnicity", qs_has_user=self.qs_has_user, model_attr=self.model_attr)
        self.gender = aid_service_get_oto(
            qs=self.qs,
            model_fields=model_fields,
            oto="gender",
        )
        aid_service_check_oto_swap(oto="gender", qs_has_user=self.qs_has_user, model_attr=self.model_attr)
        self.medallergys = self.qs.medallergys_qs if hasattr(self.qs, "medallergys_qs") else None
        if hasattr(self.qs, "medhistorys_qs"):
            self.medhistorys = self.qs.medhistorys_qs
        else:
            self.medhistorys = None
        # TODO: Add side effects back in at later stage, kept here to avoid breaking other code
        self.sideeffects = None

    def _update(self, commit=True) -> Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "UltAid", "Ult"]:
        """Updates the model object's decisionaid field.

        Args:
            commit (bool): defaults to True, True will clean/save, False will not

        Returns:
            str: decisionaid field JSON representation of trt_dict
        """
        if commit:
            self.model_attr.full_clean()
            self.model_attr.save()
        return self.model_attr


class TreatmentAidService(AidService):
    """Base class for TreatmentAid service class methods. Adds
    methods for creating trt_dict, decisionaid_dict, filtering DefaultTrts,
    and updating the model's decisionaid field."""

    ckddetail: Union["CkdDetail", None]
    trttype: TrtTypes.FLARE | TrtTypes.PPX | TrtTypes.ULT

    def _create_trts_dict(self):
        """Returns a dict {Treatments: {dose/freq/duration + contra=False}}."""
        return aids_create_trts_dosing_dict(default_trts=self.default_trts)

    def _create_decisionaid_dict(self) -> dict:
        """Returns a trt_dict (dict {Treatments: {dose/freq/duration + contra=False}} with
        dosing and contraindications for each treatment adjusted for the patient's
        relevant medical history."""
        trt_dict = self._create_trts_dict()
        trt_dict = aids_process_medhistorys(
            trt_dict=trt_dict,
            medhistorys=self.medhistorys,
            ckddetail=self.ckddetail,
            default_medhistorys=self.default_medhistorys,
            defaulttrtsettings=self.defaultsettings,
        )
        trt_dict = aids_process_medallergys(trt_dict=trt_dict, medallergys=self.medallergys)
        trt_dict = aids_process_sideeffects(trt_dict=trt_dict, sideeffects=self.sideeffects)
        return trt_dict

    @cached_property
    def default_medhistorys(self) -> QuerySet:
        """Returns a QuerySet of DefaultMedHistorys filtered for the class User and treatment type."""
        return defaults_defaultmedhistorys_trttype(medhistorys=self.medhistorys, trttype=self.trttype, user=self.user)

    @cached_property
    def default_trts(self) -> QuerySet:
        """Returns a QuerySet of DefaultTrts filtered for the class User and treatment type."""
        return defaults_defaulttrts_trttype(trttype=self.trttype, user=self.user)

    def _save_trt_dict_to_decisionaid(self, decisionaid_dict: dict, commit=True) -> str:
        """Saves the trt_dict to the model object's decisionaid field as a JSON string.

        Args:
            decisionaid_dict {dict}: keys = Treatments, vals = dosing + contraindications.
            commit (bool): defaults to True, True will clean/save, False will not

        Returns:
            str: decisionaid field JSON representation fo the trt_dict
        """
        self.model_attr.decisionaid = aids_dict_to_json(aid_dict=decisionaid_dict)
        if commit:
            self.model_attr.full_clean()
            self.model_attr.save()
        return self.model_attr.decisionaid

    def _update(self, commit=True) -> Union["FlareAid", "PpxAid", "UltAid"]:
        """Updates the model object's decisionaid field.

        Args:
            commit (bool): defaults to True, True will clean/save, False will not

        Returns:
            Union[FlareAid, PpxAid, UltAid]: model object
        """
        decisionaid_dict = self._create_decisionaid_dict()
        self.model_attr.decisionaid = self._save_trt_dict_to_decisionaid(
            decisionaid_dict=decisionaid_dict, commit=False
        )
        return super()._update(commit=commit)
