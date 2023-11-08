from datetime import timedelta  # type: ignore
from decimal import Decimal
from typing import TYPE_CHECKING, Union

from django.utils import timezone  # type: ignore

from ..genders.choices import Genders
from ..goalurates.choices import GoalUrates
from ..medhistorydetails.choices import Stages
from .choices import LabTypes, LowerLimits, Units
from .dicts import LABS_LABTYPES_LOWER_LIMITS, LABS_LABTYPES_UNITS, LABS_LABTYPES_UPPER_LIMITS

if TYPE_CHECKING:
    from django.db.models.query import QuerySet  # type: ignore

    from ..medhistorydetails.models import GoutDetail
    from .models import Creatinine, Urate


def round_decimal(value, places):
    if value is not None:
        # see https://docs.python.org/2/library/decimal.html#decimal.Decimal.quantize for options
        return value.quantize(Decimal(10) ** -places)
    return value


def eGFR_calculator(
    creatinine: Union["Creatinine", Decimal],
    age: int = 45,
    gender: int = Genders.MALE,
) -> Decimal:
    """
    Calculates eGFR from Creatinine value.
    Need to know age and gender.
    https://www.kidney.org/professionals/kdoqi/gfr_calculator/formula
    """
    if (
        hasattr(creatinine, "labtype")
        and not isinstance(creatinine, Decimal)
        and creatinine.labtype == LabTypes.CREATININE
    ):
        value = creatinine.value
    elif isinstance(creatinine, Decimal):
        value = creatinine
    else:
        raise TypeError(f"eGFR_calculator() was called on a non-lab, non-Decimal object: {creatinine}")
    # Set gender-based variables for CKD-EPI Creatinine Equation
    if gender == Genders.MALE:
        sex_modifier = Decimal(1.000)
        alpha = Decimal(-0.302)
        kappa = Decimal(0.9)
    else:
        sex_modifier = Decimal(1.012)
        alpha = Decimal(-0.241)
        kappa = Decimal(0.7)
    # Calculate eGFR
    eGFR = (
        Decimal(142)
        * min(value / kappa, Decimal(1.00)) ** alpha
        * max(value / kappa, Decimal(1.00)) ** Decimal(-1.200)
        * Decimal("0.9938") ** age
        * sex_modifier
    )
    # Return eGFR rounded to 0 decimal points
    return round_decimal(eGFR, 0)


def stage_calculator(eGFR: Decimal) -> "Stages":
    """Method that calculates CKD stage from an eGFR.

    Args: eGFR (decimal): eGFR value, guesstimate (bool): boolean indicating
    whether or not the eGFR value was estimated based on the average age of gout patients.

    Returns:
        ([integer or None], bool): tuple of the CKD stage or None and a boolean
        indicating whether or not the eGFR was an estimate based on the average
        age of gout patients, or not.
    """
    # Use eGFR to determine CKD stage
    if eGFR >= 90:
        return Stages.ONE
    elif 90 > eGFR >= 60:
        return Stages.TWO
    elif 60 > eGFR >= 30:
        return Stages.THREE
    elif 30 > eGFR >= 15:
        return Stages.FOUR
    else:
        return Stages.FIVE


def labs_get_default_labtype(lab_name: LabTypes) -> LabTypes:
    """Method that returns the default LabType for a given Lab proxy model.
    Will raise an error if called on Generic Lab parent model
    because it won't find a LabType for LAB in LabTypes."""
    return LabTypes(lab_name)


def labs_get_default_lower_limit(lab_name: LabTypes) -> LowerLimits:
    """Method that returns the default lower limit for a given Lab proxy model.
    Will raise an error if called on Generic Lab parent model
    because it won't find a LowerLimit for LAB in LowerLimits."""
    return next(iter(LABS_LABTYPES_LOWER_LIMITS[lab_name].values()))


def labs_get_default_units(lab_name: LabTypes) -> Units:
    """Method that returns the default units for a given Lab proxy model.
    Will raise an error if called on Generic Lab parent model
    because it won't find a Units for LAB in Units."""
    return LABS_LABTYPES_UNITS[lab_name][0]


def labs_get_default_upper_limit(lab_name: LabTypes) -> Decimal:
    """Method that returns the default upper limit for a given Lab proxy model.
    Will raise an error if called on Generic Lab parent model
    because it won't find a UpperLimit for LAB in UpperLimits."""
    return next(iter(LABS_LABTYPES_UPPER_LIMITS[lab_name].values()))


def labs_hyperuricemic_calc(urate: "Urate", goal_urate: Decimal = GoalUrates.SIX) -> tuple[bool, bool]:
    """Method that interprets a urate value is above goal for ULT management and
    whether it is above the threshold for extreme hyperuricemia.

    Args:
        urate (Urate): a Urate object
        goal_urate (Decimal): the goal urate for the user, default for Gouthelper
        if urate has no user, defaults to 6.0 mg/dL

    Returns:
        tuple: a tuple of two booleans. The first boolean indicates whether Urate is
        above goal for gout treatment (6.0 or 5.0 mg/dL) and was drawn in the last six months.
        The second boolean indicates whether the urate is above the threshold
        for extreme hyperuricemia (9.0 mg/dL).
    """
    if urate.labtype != LabTypes.URATE:
        raise TypeError(f"hyperuricemic() was called on a lab {urate} that is not a Urate")
    user = getattr(urate, "user", None)
    if user:
        goal_urate = user.defaultsettings.goal_urate
    return (
        (urate.value >= goal_urate) and (urate.date_drawn >= (timezone.now() - timedelta(days=180)))
    ), urate.value >= Decimal("9.0")


def labs_urates_chronological_dates(
    current_urate: "Urate", previous_urate: Union["Urate", None], first_urate: "Urate"
) -> ValueError | None:
    """Method that takes a Urate, option previous Urate, and an initial
    Urate from a list of QuerySet and raises a ValueError if any of the
    dates don't have a date attr or if the dates aren't in chronological order.
    """
    # Check if the current Urate has a date attr or does but is None
    if hasattr(current_urate, "date") is False or current_urate.date is None:
        # If so, raise a ValueError
        raise ValueError(f"Urate {current_urate} has no date_drawn or Flare")
    # Check to make sure the current Urate isn't newer than the first Urate or the last Urate that was
    # iterated over, raise a ValueError if it is
    if current_urate.date > first_urate.date or previous_urate and current_urate.date > previous_urate.date:
        raise ValueError("The Urates are not in chronological order. QuerySet must be ordered by date.")


def labs_urates_hyperuricemic(
    urates: Union["QuerySet[Urate]", list["Urate"]],
    goutdetail: Union["GoutDetail", None] = None,
    goal_urate: GoalUrates = GoalUrates.SIX,
    commit: bool = True,
) -> bool:
    """Method that takes a list of Urate objects and first checks that index 0
    is the most recent and raises a ValueError if not. Then checks if the most
    recent Urate is above goal_urate and if so, sets goutdetail.hyperuricemic to
    True, saves, and returns True. Will not change goutdetail fields if the GoutDetail
    medhistory has a set_date that is newer than the date attr of the
    most recent Urate. If most recent Urate not hyperuricemic, returns False.

    Args:
        urates (QuerySet[Urate] or list[Urate]): QuerySet or list of Urates,
            require using a QuerySet that annotates each Urate with a date, derived
            either from the Urate.date_drawn or the Urate.flare.date_started.
        goutdetail (GoutDetail): goutdetail object for Gout or None
        goal_urate (GoalUrates enum): goal urate for the user, defaults to 6.0 mg/dL
        commit (bool): defaults to True, True will clean/save, False will not

    Returns:
        bool: True if the most recent Urate is above goal_urate, False if not
    """
    # Check if the urates have date attrs and are in chronological order
    # Raise error if not
    for ui in range(len(urates)):
        labs_urates_chronological_dates(
            current_urate=urates[ui], previous_urate=urates[ui - 1] if ui > 0 else None, first_urate=urates[0]
        )
    # Check if the most recent Urate is above goal_urate
    if urates and urates[0].value >= goal_urate:
        # If so, check if there is a Gout MedHistory and if it is hyperuricemic and if the Gout can be edited
        if (
            goutdetail
            and not goutdetail.hyperuricemic
            and commit
            # Check if the Gout MedHistory has a set_date attr and if it is older than the current Urate
            # or if the GoutDetail hyperuricemic attr has never been set, i.e. is None
            and (
                not goutdetail.medhistory.set_date
                or goutdetail.medhistory.set_date < urates[0].date
                or goutdetail.hyperuricemic is None
            )
        ):
            # If so, set gout.hyperuricemic to True and save
            goutdetail.hyperuricemic = True
            goutdetail.full_clean()
            goutdetail.save()
        # Then return True
        return True
    # If not, return False
    else:
        return False


def labs_urate_last_at_goal(
    urates: Union["QuerySet[Urate]", list["Urate"]],
    goutdetail: Union["GoutDetail", None] = None,
    goal_urate: GoalUrates = GoalUrates.SIX,
    commit: bool = True,
    urates_sorted: bool = True,
) -> bool:
    """Method that iterates over a list of urates annotated with a date attr
    and determines if the most recent Urate in the list was at goal, meaning
    below the goal urate. If there is a goutdetail object, will set the
    goutdetail.hyperuricemic attr to False and save if commit is True."""
    # Check if the urates_sorted arg is False
    if not urates_sorted:
        # Sort the urates by date
        urates = sorted(urates, key=lambda x: x.date, reverse=True)
    # Otherwise check to make sure they are sorted
    else:
        # Raise ValueError if not
        for urate_i in range(len(urates)):
            labs_urates_chronological_dates(
                current_urate=urates[urate_i],
                previous_urate=urates[urate_i - 1] if urate_i > 0 else None,
                first_urate=urates[0],
            )
    # Check if the most recent Urate is below goal_urate
    if urates and urates[0].value <= goal_urate:
        # If so, check if there is a Gout MedHistory and if it is hyperuricemic
        if (
            goutdetail
            and goutdetail.hyperuricemic is not False
            and commit
            # Check if the Gout MedHistory has a set_date attr and if it is older than the current Urate
            # or if the GoutDetail hyperuricemic attr has never been set, i.e. is None
            and (
                not goutdetail.medhistory.set_date
                or goutdetail.medhistory.set_date < urates[0].date
                or goutdetail.hyperuricemic is None
            )
        ):
            # If so, set gout.hyperuricemic to False and save
            goutdetail.hyperuricemic = False
            goutdetail.full_clean()
            goutdetail.save()
        # Then return True
        return True
    # If not, return False
    else:
        return False


def labs_urate_months_at_goal(
    urates: Union["QuerySet[Urate]", list["Urate"]],
    goutdetail: Union["GoutDetail", None] = None,
    goal_urate: GoalUrates = GoalUrates.SIX,
    months: int = 6,
    r: int = 0,
    commit: bool = True,
) -> bool:
    """
    Recursive function that determines if a set of Urates indicate the Uric acid has been
    "at goal" for a variable number of months or longer. Very important for gout management,
    because six months at goal means the Patient can be taken of flare prophylaxis and they
    are much less likely to be having gout flares.

    Args:
        goutdetail (GoutDetail): goutdetail object for Gout or None
        urates (QuerySet[Urate] or list[Urate]): QuerySet or list of Urates,
            require using a QuerySet that annotates each Urate with a date, derived
            either from the Urate.date_drawn or the Urate.flare.date_started.
        goal_urate (GoalUrates enum): goal urate for the user, defaults to 6.0 mg/dL
        months (int): number of months to check for, defaults to 6
        r (int): recursion counter, defaults to 0
        commit (bool): defaults to True, True will clean/save, False will not

    Returns:
        bool: True if there is a 6 or greater month period where the current
        and all other preceding Urates were < goal_urate. Must contain Urate
        values at least 6 months apart.
    """
    # If index + r is greater than the length of the list
    # The recursion has run beyond the end of the list
    # Has not found a 6 month period where > 1 Urates were < goal_urate, thus returns False
    if r >= len(urates):
        return False
    # Check if urate at LabCheck[r] is under goal_urate
    if urates[r].value <= goal_urate:
        # If so, check if urate at urates[r] is greater than 6 months apart from current urate at urates[0]
        # First, check if the Urate date_drawn attr isn't None
        labs_urates_chronological_dates(
            current_urate=urates[r], previous_urate=urates[r - 1] if r > 0 else None, first_urate=urates[0]
        )
        # Compare the date of the current Urate to the date of the Urate at urates[r]
        # If the difference is greater than the number of months * 30 days
        if (urates[0].date - urates[r].date) >= timedelta(days=30 * months):
            # If so, check if there is a Gout MedHistory and if it is hyperuricemic
            if (
                goutdetail
                and goutdetail.hyperuricemic is not False
                and commit
                # Check if the Gout MedHistory has a set_date attr and if it is older than the current Urate
                # or if the GoutDetail hyperuricemic attr has never been set, i.e. is None
                and (
                    not goutdetail.medhistory.set_date
                    or goutdetail.medhistory.set_date < urates[0].date
                    or goutdetail.hyperuricemic is None
                )
            ):
                # If so, set gout.hyperuricemic to False and save
                goutdetail.hyperuricemic = False
                goutdetail.full_clean()
                goutdetail.save()
            # Then return True
            return True
        # If Urates aren't 6 months apart but both are below goal_urate
        # Recurse to the next urate further back in time urates[r+1]
        else:
            return labs_urate_months_at_goal(
                urates=urates, goutdetail=goutdetail, goal_urate=goal_urate, months=months, r=r + 1
            )
    # If Urate hasn't been under goal_urate for at least 6 months
    # With 2 or more observations, return False
    else:
        return False


def labs_urates_recent_urate(
    urates: Union["QuerySet[Urate]", list["Urate"]],
    sorted_by_date: bool = False,
) -> bool:
    """Method that takes a list or QuerySet of Urates in chronological
    order by a "date" attr with the most recent "date" being index 0
    and returns True if the most recent Urate is less than 90 days old,
    False if not.

    Checks that list is chronologically sorted if sorted is False.

    urates (QuerySet[Urate] or list[Urate]): QuerySet or list of Urates,
        require using a QuerySet that annotates each Urate with a date, derived
        either from the Urate.date_drawn or the Urate.flare.date_started.
    sorted_by_date (bool): defaults to False, if False, will check that the list is
        sorted by date, if True, will not check.

    Returns:
        bool: True if the most recent Urate is less than 90 days old,
        False if not."""
    # Check if the list is sorted
    if not sorted_by_date:
        # Check that the urates are in chronological order
        for urate_i, urate in enumerate(urates):
            labs_urates_chronological_dates(
                current_urate=urate, previous_urate=urates[urate_i - 1] if urate_i > 0 else None, first_urate=urates[0]
            )
    return urates[0].date and urates[0].date > timezone.now() - timedelta(days=90) if urates else False
