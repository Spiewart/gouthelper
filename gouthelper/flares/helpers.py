from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Union

from ..genders.choices import Genders
from ..medhistorys.helpers import medhistorys_get_cvdiseases, medhistorys_get_gout
from .choices import LessLikelys, Likelihoods, LimitedJointChoices, Prevalences
from .lists import COMMON_GOUT_JOINTS

if TYPE_CHECKING:
    from datetime import date

    from ..flares.models import Flare
    from ..genders.models import Gender
    from ..labs.models import Urate
    from ..medhistorys.models import MedHistory


def flares_abnormal_duration(duration: timedelta, date_ended: Union["date", None]) -> LessLikelys | bool:
    """Method that returns a LessLikelys enum if the duration is abnormal
    for gout. Otherwise returns False."""
    if duration >= timedelta(days=14):
        return LessLikelys.TOOLONG
    elif date_ended and duration <= timedelta(days=2):
        return LessLikelys.TOOSHORT
    return False


def flares_calculate_prevalence_points(
    gender: "Gender",
    onset: bool,
    redness: bool,
    joints: list[LimitedJointChoices],
    medhistorys: list["MedHistory"],
    urate: Union["Urate", None],
) -> float:
    """Method that takes a bunch of Flare fields and calculates
    the number of points present for estimating the prevalence
    of gout in similar patients.

        Citations:
        1. Janssens HJEM, Fransen J, van de Lisdonk EH, van Riel PLCM, van Weel C, Janssen M. \
            A Diagnostic Rule for Acute Gouty Arthritis in Primary Care Without Joint Fluid Analysis. \
                Arch Intern Med. 2010;170(13):1120–1126. doi:10.1001/archinternmed.2010.196
        2. Laura B. E. Kienhorst, Hein J. E. M. Janssens, Jaap Fransen, Matthijs Janssen.\
            The validation of a diagnostic rule for gout without joint fluid analysis: \
                a prospective study, Rheumatology, Volume 54, Issue 4, April 2015, Pages 609–614, \
                    https://doi.org/10.1093/rheumatology/keu378

    Args:
        gender = Gender
        onset = bool
        redness = bool
        joints = list[LimitedJointChoices]
        medhistorys = list[MedHistory]
        urate = Urate

    Returns:
        float: points for prevalence
    """
    points = 0.0
    if gender.value == Genders.MALE:
        points += 2.0
    gout = medhistorys_get_gout(medhistorys)
    if gout:
        points += 2.0
    if onset is True:
        points += 0.5
    if redness is True:
        points += 1.0
    if LimitedJointChoices.MTP1L in joints or LimitedJointChoices.MTP1R in joints:
        points += 2.5
    cvdiseases = medhistorys_get_cvdiseases(medhistorys, hypertension=True)
    if cvdiseases:
        points += 1.5
    if urate and urate.value > Decimal("5.88"):
        points += 3.5
    return points


def flares_common_joints(joints: list[LimitedJointChoices]) -> list[LimitedJointChoices]:
    """Method that takes a list of joints and returns a list of those joints that are
    in COMMON_GOUT_JOINTS."""
    return [joint for joint in joints if joint in COMMON_GOUT_JOINTS]


def flares_get_less_likelys(
    age: int,
    date_ended: Union["date", None],
    duration: timedelta,
    gender: "Gender",
    joints: list[LimitedJointChoices],
    menopause: bool | None,
    crystal_analysis: bool | None,
    ckd: Union["MedHistory", None],
) -> list[LessLikelys]:
    """Return list of strings of less likelys for a Flare."""

    less_likelys = []
    if gender.value == Genders.FEMALE and age < 45 and not menopause and not ckd:
        less_likelys.append(LessLikelys.FEMALE)
    if age < 18:
        less_likelys.append(LessLikelys.TOOYOUNG)
    abnormal_duration = flares_abnormal_duration(duration, date_ended)
    if abnormal_duration:
        less_likelys.append(abnormal_duration)
    if not flares_common_joints(joints):
        less_likelys.append(LessLikelys.JOINTS)
    if crystal_analysis is False:
        less_likelys.append(LessLikelys.NEGCRYSTALS)
    return less_likelys


def flares_get_likelihood_str(flare: "Flare") -> str:
    if flare.likelihood == Likelihoods.UNLIKELY:
        flare_str = "Gout isn't likely and alternative causes of the symptoms should be investigated."
    elif flare.likelihood == Likelihoods.EQUIVOCAL:
        flare_str = "Indeterminate likelihood of gout and it can't be ruled in or out. \
Physician evaluation is recommended."
    elif flare.likelihood == Likelihoods.LIKELY:
        flare_str = "Gout is very likely. Not a whole lot else needs to be done, other than treat the gout!"
    else:
        flare_str = "Flare hasn't been processed yet..."
    return flare_str


def flares_calculate_likelihood(
    less_likelys: list[LessLikelys],
    diagnosed: bool,
    crystal_analysis: bool | None,
    prevalence: Prevalences,
) -> Likelihoods:
    """Method that takes a likelihood_dict and calculates the likelihood
    of a flare being gout.

    Args:
        likelihood_dict: dictionary to process

    Raises:
        ValueError: if prevalence is not set
    Returns:
        Likelihoods: enum representing the likelihood of a flare being gout
    """
    # Check if the flare was diagnosed by a clinician
    if diagnosed:
        # If the clinician performed and aspiration and found gout, then
        # gout is likely
        if crystal_analysis is True:
            likelihood = Likelihoods.LIKELY
        # If the clinician performed an aspiration and didn't find gout,
        # then gout is unlikely
        elif crystal_analysis is False:
            likelihood = Likelihoods.UNLIKELY
        # If no aspiration was performed, then gout is probably is not any
        # more or less likely than if the flare was not diagnosed by a clinician
    # Set baseline likelihood based on the presence or absence of less likelys
    elif less_likelys:
        # If there are less likely gout factors
        # reduce the likelihood dependent on the prevalence
        if prevalence == Prevalences.HIGH:
            likelihood = Likelihoods.EQUIVOCAL
        elif prevalence == Prevalences.MEDIUM:
            likelihood = Likelihoods.UNLIKELY
        else:
            likelihood = Likelihoods.UNLIKELY
    else:
        # Otherwise set the likelihood based on the prevalence
        if prevalence == Prevalences.HIGH:
            likelihood = Likelihoods.LIKELY
        elif prevalence == Prevalences.MEDIUM:
            likelihood = Likelihoods.EQUIVOCAL
        else:
            likelihood = Likelihoods.UNLIKELY
    return likelihood


def flares_calculate_prevalence(
    prevalence_points: float,
) -> Prevalences:
    """Method that uses prevalence_points to determine the prevalence
    of gout in a population of similar patients.

    Args:
        prevalence_points: float representing the prevalence points,
        generated from flares_prevalence_points_calculator

    Returns:
        Prevalences: enum representing the prevalence of gout in a population
    """
    if prevalence_points >= 8:
        return Prevalences.HIGH
    elif prevalence_points >= 4 and prevalence_points < 8:
        return Prevalences.MEDIUM
    else:
        return Prevalences.LOW


def flares_uncommon_joints(joints: list[LimitedJointChoices]) -> list[LimitedJointChoices]:
    """Method that takes a list of joints and returns a list of those joints that are
    NOT in COMMON_GOUT_JOINTS."""
    return [joint for joint in joints if joint not in COMMON_GOUT_JOINTS]
