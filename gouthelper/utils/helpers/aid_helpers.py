import json
from typing import TYPE_CHECKING, Union

from django.core.serializers.json import DjangoJSONEncoder  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...defaults.helpers import defaults_treatments_create_dosing_dict
from ...ethnicitys.helpers import ethnicitys_hlab5801_risk
from ...medhistorydetails.choices import DialysisChoices, Stages
from ...medhistorys.choices import Contraindications, MedHistoryTypes
from ...medhistorys.dicts import CVD_CONTRAS
from ...treatments.choices import (
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
    from django.db.models import QuerySet  # type: ignore

    from ...dateofbirths.models import DateOfBirth
    from ...defaults.models import DefaultFlareTrtSettings, DefaultPpxTrtSettings, DefaultUltTrtSettings
    from ...ethnicitys.models import Ethnicity
    from ...labs.models import BaselineCreatinine, Hlab5801
    from ...medallergys.models import MedAllergy
    from ...medhistorydetails.models import CkdDetail, GoutDetail
    from ...medhistorys.models import Ckd, MedHistory


def aids_assign_userless_baselinecreatinine(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"],
) -> Union["BaselineCreatinine", None]:
    """Method that takes a list of userless medhistorys and tries to find one with a BaselineCreatinine.
    Returns BaselineCreatinine if found, otherwise None.

    Args:
        medhistorys (QuerySet[MedHistory]): QuerySet of MedHistory objects.
    Returns:
        Union[BaselineCreatinine, None]: BaselineCreatinine object or None.
    """
    ckd = [medhistory for medhistory in medhistorys if medhistory.medhistorytype == MedHistoryTypes.CKD]
    if ckd and hasattr(ckd[0], "baselinecreatinine"):
        return ckd[0].baselinecreatinine
    return None


def aids_assign_userless_ckddetail(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"],
) -> Union["CkdDetail", None]:
    """Method that takes a list of userless medhistorys and tries to find one with a CkdDetail.
    Returns CkdDetail if found, otherwise None.

    Args:
        medhistorys (QuerySet[MedHistory]): QuerySet of MedHistory objects.
    Returns:
        Union[CkdDetail, None]: CkdDetail object or None.
    """
    ckd = [medhistory for medhistory in medhistorys if medhistory.medhistorytype == MedHistoryTypes.CKD]
    if ckd and hasattr(ckd[0], "ckddetail"):
        return ckd[0].ckddetail
    return None


def aids_assign_userless_goutdetail(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"],
) -> Union["GoutDetail", None]:
    """Method that takes a list of userless medhistorys and tries to find one with a GoutDetail.
    Returns GoutDetail if found, otherwise None.

    Args:
        medhistorys (QuerySet[MedHistory]): QuerySet of MedHistory objects.
    Returns:
        Union[GoutDetail, None]: GoutDetail object or None.
    """
    gout = [medhistory for medhistory in medhistorys if medhistory.medhistorytype == MedHistoryTypes.GOUT]
    if gout and hasattr(gout[0], "goutdetail"):
        return gout[0].goutdetail
    return None


def aids_colchicine_ckd_contra(
    ckd: Union["Ckd", None],
    ckddetail: Union["CkdDetail", None],
    defaulttrtsettings: Union["DefaultFlareTrtSettings", "DefaultPpxTrtSettings"],
) -> Contraindications | None:
    """Method that takes an Aid/User/Ultplan's Ckd and CkdDetail and determines
    whether or not colchicine should be contraindicated, dose-adjusted, or neither.

    Args:
        ckd (Ckd): Ckd object.
        ckddetail (CkdDetail): CkdDetail object.
        defaulttrtsettings (Union[DefaultFlareTrtSettings, DefaultPpxTrtSettings]): DefaultFlareTrtSettings or \
DefaultPpxTrtSettings object.

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
    defaulttrtsettings: "DefaultUltTrtSettings",
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
        defaulttrtsettings (DefaultUltTrtSettings): DefaultUltTrtSettings object.
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
    defaulttrtsettings: Union["DefaultFlareTrtSettings", "DefaultPpxTrtSettings"],
) -> dict:
    """Method that takes a trt_dict and renally adjusts the dosing for Colchicine.
    Checks if the default_settings dictates the dose is adjusted or whether the frequency
    is adjusted.

    Args:
        trt_dict (dict): {TrtTypes: {TrtInfo}}
        aid_type (trttypes): TrtTypes enum to determine how to set the Colchicine dosing.
        defaulttrtsettings (Union[DefaultFlareTrtSettings, DefaultPpxTrtSettings]

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
    defaulttrtsettings: "DefaultUltTrtSettings",
) -> dict:
    """Method that dose adjusts febuxostat for the presence of CKD.

    FitzGerald JD, et al. 2020 American College of Rheumatology Guideline
    for the Management of Gout. Arthritis Care Res (Hoboken). 2020 Jun;72(6):744-760.
    doi: 10.1002/acr.24180. PMID: 32391934.

    Args:
        trt_dict (dict): Dictionary of Treatments.
        defaulttrtsettings (DefaultUltTrtSettings): DefaultUltTrtSettings object.

    Returns:
        dict: Dictionary of Treatments, potentially with dose adjustments.
    """
    trt_dict[Treatments.FEBUXOSTAT]["dose"] = defaulttrtsettings.febu_ckd_initial_dose
    trt_dict[Treatments.FEBUXOSTAT]["dose_adj"] = defaulttrtsettings.febu_ckd_initial_dose
    return trt_dict


def aids_hlab5801_contra(
    hlab5801: Union["Hlab5801", None],
    ethnicity: Union["Ethnicity", None],
    defaultulttrtsettings: "DefaultUltTrtSettings",
) -> bool:
    """Method that takes optional Hlab5801, Ethnicity, and DefaultUltTrtSettings
    objects and returns a bool indicating whether or not allopurinol should be
    contraindicated.

    Args:
        hlab5801 [optional]: Hlab5801 object
        ethnicity [optional]: Ethnicity object
        defaultultrtsettings [optional]: DefaultUltTrtSettings object

    Returns:
        bool: True if allopurinol should be contraindicated, False if not.
    """
    if (
        (hlab5801 and hlab5801.value is True)
        or (
            ethnicity
            and (ethnicitys_hlab5801_risk(ethnicity=ethnicity))
            and not hlab5801
            and not defaultulttrtsettings.allo_risk_ethnicity_no_hlab5801
        )
        or (not ethnicity and not hlab5801 and not defaultulttrtsettings.allo_no_ethnicity_no_hlab5801)
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


def aids_options(trt_dict: dict) -> dict:
    """Method that parses trt_dict (dictionary of potential Aid Treatments)
    and returns a dict of all possible Aid Treatment options by removing
    those which are contraindicated.

    args:
        trt_dict (dict): {TrtTypes: {TrtInfo}}

    returns: modified trt_dict with contraindicated treatments removed.
    """

    options_dict = trt_dict.copy()
    for trt, sub_dict in trt_dict.items():
        if sub_dict["contra"] is True:
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
    defaultulttrtsettings: "DefaultUltTrtSettings",
) -> dict:
    """Method that processes a Hlab5801, ethnicity for User/UltAid/Ultplan and
    determines whether or not allopurinol is contraindicated per the DefaultUltTrtSettings.
    Modifies trt_dict required *arg and returns the modified dict.

    Args:
        trt_dict (dict): {TrtTypes: {TrtInfo}}
        hlab5801 (Hlab5801): Hlab5801 object.
        ethnicity (Ethnicity): Ethnicity object.
        defaultulttrtsettings (DefaultUltTrtSettings): DefaultUltTrtSettings object.

    Returns:
        trt_dict (dict): {TrtTypes: {TrtInfo}} with Allopurinol contraindicated if True.
    """

    if aids_hlab5801_contra(
        hlab5801=hlab5801,
        ethnicity=ethnicity,
        defaultulttrtsettings=defaultulttrtsettings,
    ):
        if trt_dict[Treatments.ALLOPURINOL]["contra"] is False:
            trt_dict[Treatments.ALLOPURINOL]["contra"] = True
    return trt_dict


def aids_process_medhistorys(
    trt_dict: dict,
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"],
    ckddetail: Union["CkdDetail", None],
    default_medhistorys: "QuerySet",
    defaulttrtsettings: Union["DefaultFlareTrtSettings", "DefaultPpxTrtSettings", "DefaultUltTrtSettings"],
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
        defaulttrtsettings (DefaultFlare/Ppx/UltTrtSettings): DefaultFlareTrtSettings or \
DefaultPpxTrtSettings or DefaultUltTrtSettings object.

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
    defaulttrtsettings: Union["DefaultFlareTrtSettings", "DefaultPpxTrtSettings"],
) -> dict:
    """Method that applies NSAID contraindications to all NSAIDs in the trt_dict.
    Checks if that the defaulttrtsettings.nsaids_equivalent is True, first, if not
    then returns the trt_dict unchanged.

    Args:
        trt_dict (dict): {TrtTypes: {TrtInfo}}
        defaulttrtsettings: DefaultFlareTrtSettings or DefaultPpxTrtSettings

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
    defaulttrtsettings: "DefaultUltTrtSettings",
) -> bool:
    """Method that checks CKD status (stage) and returns True if probenecid should be
    contraindicated. False if not.

    Args:
        ckd (Ckd or None): Ckd object or None
        ckddetail (CkdDetail or None): CkdDetail object or None
        defaulttrtsettings (DefaultUltTrtSettings or None): DefaultUltTrtSettings object

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
    defaulttrtsettings: Union["DefaultFlareTrtSettings", "DefaultPpxTrtSettings"],
) -> dict:
    """Method that applies steroid contraindications to all steroids in the trt_dict.
    Checks if that the defaulttrtsettings.steroids_equivalent is True, first, if not
    then returns the trt_dict unchanged.

    Args:
        trt_dict (dict): {TrtTypes: {TrtInfo}}
        defaulttrtsettings: DefaultFlareTrtSettings or DefaultPpxTrtSettings

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
