from datetime import timedelta  # type: ignore
from decimal import Decimal
from typing import TYPE_CHECKING, Union

from django.core.exceptions import ValidationError  # type: ignore
from django.utils import timezone  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore

from ..genders.choices import Genders
from ..goalurates.choices import GoalUrates
from ..medhistorydetails.choices import Stages

if TYPE_CHECKING:
    from django.db.models.query import QuerySet  # type: ignore

    from ..medhistorydetails.models import GoutDetail
    from .models import Creatinine, Urate


def labs_baselinecreatinine_max_value(value: Decimal):
    """Method that raises a ValidationError if a baselinecreatinine value is greater than 10 mg/dL."""
    if value > 10:
        raise ValidationError(
            _(
                "A baseline creatinine value greater than 10 mg/dL isn't very likely. \
This would typically mean the patient is on dialysis."
            )
        )


def labs_eGFR_calculator(
    creatinine: Union["Creatinine", Decimal],
    age: int = 45,
    gender: int = Genders.MALE,
) -> Decimal:
    """
    Calculates eGFR from Creatinine value.
    Need to know age and gender.
    https://www.kidney.org/professionals/kdoqi/gfr_calculator/formula

    args:
        creatinine (Creatinine or Decimal): Creatinine object or Decimal value
        age (int): age of patient in years
        gender (Genders enum = int): gender object representing the patient's gender

    returns: eGFR (decimal) rounded to 0 decimal points
    """
    # Check if creatinine is a Creatinine object or a Decimal
    if isinstance(creatinine, Decimal):
        # If so, set value to the creatinine
        value = creatinine
    # If neither, raise a TypeError
    else:
        try:
            value = creatinine.value
        except AttributeError as exc:
            raise TypeError(
                f"labs_eGFR_calculator() was called on a non-lab, non-Decimal object: {creatinine}"
            ) from exc
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
    return labs_round_decimal(eGFR, 0)


def labs_round_decimal(value: Decimal, places: int) -> Decimal:
    """Method that rounds a Decimal to a given number of places."""
    if value is not None:
        # see https://docs.python.org/2/library/decimal.html#decimal.Decimal.quantize for options
        return value.quantize(Decimal(10) ** -places)
    return value


def labs_stage_calculator(eGFR: Decimal) -> "Stages":
    """Method that calculates CKD stage from an eGFR.

    Args:
        eGFR (decimal): eGFR value

    Returns:
        Stages enum object: CKD stage
    """
    # Use eGFR to determine CKD stage and return
    return (
        Stages.ONE
        if eGFR >= 90
        else Stages.TWO
        if 90 > eGFR >= 60
        else Stages.THREE
        if 60 > eGFR >= 30
        else Stages.FOUR
        if 30 > eGFR >= 15
        else Stages.FIVE
    )


def labs_urates_chronological_dates(
    current_urate: "Urate", previous_urate: Union["Urate", None], first_urate: "Urate"
) -> ValueError | None:
    """Helper function to determine if a list or QuerySet of urates is in chronological order
    from the newest urate by a date attr annotated by a QuerySet.

    args:
        current_urate (Urate): current Urate object
        previous_urate (Urate, None): optional previous Urate object
        first_urate (Urate): first Urate object in the list or QuerySet

    returns:
        None

    raises:
        ValueError: if the current Urate has a date attr or does but is None
        ValueError: if the current Urate is newer than the first Urate or the last Urate that was
            iterated over
    """
    # Check if the current Urate has a date attr or does but is None
    if hasattr(current_urate, "date") is False or current_urate.date is None:
        # If so, raise a ValueError
        raise ValueError(f"Urate {current_urate} has no date_drawn, Flare, or annotated date.")
    # Check to make sure the current Urate isn't newer than the first Urate or the last Urate that was
    # iterated over, raise a ValueError if it is
    if current_urate.date > first_urate.date or previous_urate and current_urate.date > previous_urate.date:
        raise ValueError("The Urates are not in chronological order. QuerySet must be ordered by date.")


def labs_urates_annotate_order_by_dates(
    urates: list["Urate"],
) -> None:
    """Method that takes a list of Urate objects and annotates each Urate with a date attr
    that is derived from the date_drawn field on the Urate if it exists and, if not,
    the date_started field on the Urate's Flare object. Raises a ValueError if neither
    field exists. Orders the list by date in descending order."""
    for urate in urates:
        if urate.date_drawn:
            urate.date = urate.date_drawn
        elif hasattr(urate, "flare") and urate.flare.date_started:
            urate.date = urate.flare.date_started
        else:
            raise ValueError(f"Urate {urate} has no date_drawn, Flare, or annotated date.")
    urates.sort(key=lambda x: x.date, reverse=True)


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


def labs_urates_last_at_goal(
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
        for ui, urate in enumerate(urates):
            labs_urates_chronological_dates(
                current_urate=urate,
                previous_urate=urates[ui - 1] if ui > 0 else None,
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


def labs_urates_max_value(value: Decimal):
    """Method that raises a ValidationError if a Urate value is greater than 30 mg/dL.

    Args:
        value (Decimal): Urate value

    Raises:
        ValidationError: if value is greater than 30 mg/dL
    """
    if value > 30:
        raise ValidationError(
            _(
                "Uric acid values above 30 mg/dL are very unlikely. \
If this value is correct, an emergency medical evaluation is warranted."
            )
        )


def labs_urates_months_at_goal(
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
            return labs_urates_months_at_goal(
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
