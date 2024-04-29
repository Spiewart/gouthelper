import random
from datetime import datetime, timedelta  # type: ignore
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

    from ..labs.forms import PpxUrateFormSet
    from .forms import UrateForm
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


def labs_round_decimal(value: Decimal, places: int) -> Decimal:
    """Method that rounds a Decimal to a given number of places."""
    if value is not None:
        # see https://docs.python.org/2/library/decimal.html#decimal.Decimal.quantize for options
        return value.quantize(Decimal(10) ** -places)
    return value


def labs_eGFR_range_for_stage(
    stage: Stages,
) -> tuple[int, int]:
    """Method that takes a CKD stage and returns the eGFR range for that stage."""
    if stage == Stages.ONE:
        return 90, 100
    elif stage == Stages.TWO:
        return 60, 89
    elif stage == Stages.THREE:
        return 30, 59
    elif stage == Stages.FOUR:
        return 15, 29
    elif stage == Stages.FIVE:
        return 0, 14


def labs_eGFR_calculator(
    creatinine: Union["Creatinine", Decimal],
    age: int,
    gender: int,
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


def labs_baselinecreatinine_calculator(
    stage: Stages,
    age: int,
    gender: Genders,
    creat: Decimal = Decimal(random.uniform(0, 10)),
) -> Decimal:
    """Method that calculates a baseline creatinine range based on the a CKD stage,
    an age, and a Gender.

    Args:
        stage (Stages enum): CKD stage
        age (int): age of patient in years
        gender (Genders enum): gender of the patient

    Returns:
        Decimal: a baseline creatinine value that falls within the eGFR range for the CKD stage"""
    min_eGFR, max_eGFR = labs_eGFR_range_for_stage(stage)
    creat = Decimal(random.uniform(0, 10))
    eGFR = labs_eGFR_calculator(creat, age, gender)
    while eGFR < min_eGFR or eGFR > max_eGFR:
        if eGFR < min_eGFR:
            return labs_baselinecreatinine_calculator(stage, age, gender, Decimal(random.uniform(0, float(creat))))
        else:
            return labs_baselinecreatinine_calculator(stage, age, gender, Decimal(random.uniform(float(creat), 10)))
    return labs_round_decimal(creat, 2)


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


def labs_urate_is_newer_than_goutdetail_set_date(urate, goutdetail):
    return labs_urate_date_drawn_newer_than_set_date(urate.date, goutdetail.medhistory.set_date)


def labs_urates_check_chronological_order_by_date(
    urates: Union["QuerySet[Urate]", list["Urate"]],
) -> ValueError | None:
    """Raises a ValueError if a list or QuerySet of urates is not in chronological order
    from the newest urate by a date attr annotated by a QuerySet."""
    for urate_i, urate in enumerate(urates):
        labs_urates_compare_chronological_order_by_date(
            current_urate=urate, previous_urate=urates[urate_i - 1] if urate_i > 0 else None, first_urate=urates[0]
        )


def labs_urates_compare_chronological_order_by_date(
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


def labs_urates_last_at_goal(
    urates: Union["QuerySet[Urate]", list["Urate"]],
    goal_urate: GoalUrates = GoalUrates.SIX,
) -> bool:
    """Methot that takes a list or QuerySet of urates and returns True if the last Urate
    is less than the goal_urate, False if not. Raises a ValueError if the urates are not
    in chronological order."""
    labs_urates_check_chronological_order_by_date(urates)
    return urates[0].value <= goal_urate if urates else False


def labs_check_date_drawn_is_date(
    date_drawn: datetime.date,
    date: datetime.date,
) -> bool:
    """Method that checks if a date_drawn is the same as a date provided as an arg."""
    return date_drawn == date


def labs_check_date_drawn_is_within_x_days(
    date_drawn: datetime.date,
    x: int,
) -> bool:
    """Method that checks if a date_drawn is within x days of the current date."""
    return date_drawn.date() >= timezone.now().date() - timedelta(days=x)


def labs_check_date_drawn_within_a_week(
    date_drawn: datetime.date,
) -> bool:
    """Method that checks if a date_drawn is within a week of the current date."""
    return labs_check_date_drawn_is_within_x_days(date_drawn, 7)


def labs_check_date_drawn_within_a_month(
    date_drawn: datetime.date,
) -> bool:
    """Method that checks if a date_drawn is within a month of the current date."""
    return labs_check_date_drawn_is_within_x_days(date_drawn, 30)


def labs_check_date_drawn_within_a_day(
    date_drawn: datetime.date,
) -> bool:
    """Method that checks if a date_drawn is the same as the date the form was filled out."""
    return labs_check_date_drawn_is_date(date_drawn.date(), timezone.now().date())


def labs_forms_get_date_drawn_value(form) -> tuple[str, Decimal]:
    """Method that returns the value of the date_drawn and value fields on a form."""
    return form.cleaned_data.get("date_drawn"), form.cleaned_data.get("value")


def labs_forms_get_date_drawn_value_DELETE(form) -> tuple[str, Decimal, bool]:
    """Method that returns the value of the DELETE field on a form."""
    return labs_forms_get_date_drawn_value(form) + (form.cleaned_data.get("DELETE", False),)


def labs_urate_form_at_goal_within_last_month(
    urate_form: "UrateForm",
    goal_urate: GoalUrates = GoalUrates.SIX,
) -> bool:
    """Returns True if a UrateForm's uric acid was drawn within the last month and is
    less than or equal to the goal urate."""
    date_drawn, value, delete = labs_forms_get_date_drawn_value_DELETE(urate_form)
    if (
        date_drawn
        and labs_check_date_drawn_within_a_month(date_drawn)
        and value
        and not delete
        and value <= goal_urate
    ):
        return True
    return False


def labs_urate_form_not_at_goal_within_last_month(
    urate_form: "UrateForm",
    goal_urate: GoalUrates = GoalUrates.SIX,
) -> bool:
    """Returns True if a UrateForm's uric acid was drawn within the last month and is greater than the goal urate."""
    date_drawn, value, delete = labs_forms_get_date_drawn_value_DELETE(urate_form)
    if date_drawn and labs_check_date_drawn_within_a_month(date_drawn) and value and not delete and value > goal_urate:
        return True
    return False


def labs_urate_formset_order_by_dates_remove_deleted_and_blank_forms(
    urate_formset: "PpxUrateFormSet",
) -> list["Urate"]:
    """Method that orders a urates formset by date_drawn, removes blank forms and forms that have been deleted,
    and returns a list of Urate objects."""

    # Eliminate blank forms and forms that have been deleted
    ordered_formset = [
        form
        for form in urate_formset
        if form.cleaned_data.get("date_drawn")
        and form.cleaned_data.get("value")
        and not form.cleaned_data.get("DELETE")
    ]

    # Order the formset by date_drawn
    ordered_formset = sorted(ordered_formset, key=lambda x: x.cleaned_data.get("date_drawn"), reverse=True)

    return ordered_formset


def labs_urate_formset_get_most_recent_ordered_urate_form(
    ordered_urate_formset: "PpxUrateFormSet",
) -> Union["UrateForm", None]:
    """Method that returns the most recent UrateForm object in an ordered urates formset.
    Ordered: sorted by date_drawn in descending order, forms marked for deletion removed."""
    return ordered_urate_formset[0] if ordered_urate_formset else None


def labs_urate_formset_has_one_or_more_valid_urates(
    urate_formset: "PpxUrateFormSet",
) -> bool:
    """Method that checks if a urates formset has at least one valid Urate object."""
    for urate_form in urate_formset:
        date_drawn, value, delete = labs_forms_get_date_drawn_value_DELETE(urate_form)
        if date_drawn and value and not delete:
            return True
    return False


def labs_urate_formset_at_goal_for_x_months(
    ordered_urate_formset: "PpxUrateFormSet",
    months: int,
    goal_urate: GoalUrates = GoalUrates.SIX,
    r: int = 0,
) -> bool:
    """Recursive that iterates over urates formset cleaned data and checks if the urates suggest that
    the Patient has been at goal for x months. If so, returns True, otherwise False."""
    # If the recursion has run beyond the end of the list, a x month period where > 1 Urates were < goal_urate
    # has not been found, thus returns False
    if r >= len(ordered_urate_formset):
        return False

    # Check if urate at LabCheck[r] is under goal_urate
    if ordered_urate_formset[r].cleaned_data.get("value") <= goal_urate:
        if (
            ordered_urate_formset[0].cleaned_data.get("date_drawn")
            - ordered_urate_formset[r].cleaned_data.get("date_drawn")
        ) >= timedelta(days=30 * months):
            return True
        else:
            return labs_urate_formset_at_goal_for_x_months(
                ordered_urate_formset=ordered_urate_formset,
                goal_urate=goal_urate,
                months=months,
                r=r + 1,
            )
    else:
        return False


def labs_urate_formset_at_goal_for_six_months(
    ordered_urate_formset: "PpxUrateFormSet",
    goal_urate: GoalUrates = GoalUrates.SIX,
) -> bool:
    """Calls the labs_urate_formset_at_goal_for_x_months function on an ordered urate_formset
    with a default of 6 months. Ordered: sorted by date_drawn in descending order, forms marked for deletion
    removed."""
    return labs_urate_formset_at_goal_for_x_months(
        ordered_urate_formset=ordered_urate_formset,
        goal_urate=goal_urate,
        months=6,
    )


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


def labs_urates_at_goal(
    urates: Union["QuerySet[Urate]", list["Urate"]],
    goal_urate: GoalUrates = GoalUrates.SIX,
) -> bool:
    """Checks if the most recent urate in a list or QuerySet of Urates is at goal."""
    labs_urates_check_chronological_order_by_date(urates)
    return urates[0].value <= goal_urate if urates else False


def labs_urates_not_at_goal(
    urates: Union["QuerySet[Urate]", list["Urate"]],
    goal_urate: GoalUrates = GoalUrates.SIX,
) -> bool:
    """Checks if the most recent urate in a list or QuerySet of Urates is not at goal."""
    labs_urates_check_chronological_order_by_date(urates)
    return urates[0].value > goal_urate if urates else False


def labs_urates_at_goal_within_last_month(
    urates: Union["QuerySet[Urate]", list["Urate"]],
    goal_urate: GoalUrates = GoalUrates.SIX,
) -> bool:
    """Checks if the most recent urate in a list or QuerySet of Urates is at goal within the last month."""
    return labs_urates_at_goal(urates, goal_urate) and labs_check_date_drawn_within_a_month(urates[0].date)


def labs_urates_not_at_goal_within_last_x_days(
    urates: Union["QuerySet[Urate]", list["Urate"]],
    x: int,
    goal_urate: GoalUrates = GoalUrates.SIX,
) -> bool:
    """Checks if the most recent urate in a list or QuerySet of Urates is not at goal within the last x days."""
    return labs_urates_not_at_goal(urates, goal_urate) and labs_check_date_drawn_is_within_x_days(urates[0].date, x)


def labs_urates_not_at_goal_within_last_month(
    urates: Union["QuerySet[Urate]", list["Urate"]],
    goal_urate: GoalUrates = GoalUrates.SIX,
) -> bool:
    """Checks if the most recent urate in a list or QuerySet of Urates is not at goal within the last month."""
    return labs_urates_not_at_goal(urates, goal_urate) and labs_check_date_drawn_within_a_month(urates[0].date)


def labs_urates_at_goal_x_months(
    urates: Union["QuerySet[Urate]", list["Urate"]],
    x: int,
    goal_urate: GoalUrates = GoalUrates.SIX,
    r: int = 0,
) -> bool:
    """Recursive function that determines if a set of Urates indicate the Uric acid has been
    "at goal" for a variable number of months or longer. Raises a ValueError if the Urates are not
    in chronological order.

    Args:
        urates (QuerySet[Urate] or list[Urate]): QuerySet or list of Urates,
            require using a QuerySet that annotates each Urate with a date, derived
            either from the Urate.date_drawn or the Urate.flare.date_started.
        goal_urate (GoalUrates enum): goal urate for the user, defaults to 6.0 mg/dL
        x (int): number of months to check for, defaults to 6
        r (int): recursion counter, defaults to 0

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
        # Return True if urates[r] is greater than x months apart from current urate at urates[0]
        labs_urates_compare_chronological_order_by_date(
            current_urate=urates[r], previous_urate=urates[r - 1] if r > 0 else None, first_urate=urates[0]
        )
        if (urates[0].date - urates[r].date) >= timedelta(days=30 * x):
            return True
        # If Urates aren't x months apart but both are below goal_urate
        # Recurse to the next urate further back in time urates[r+1]
        else:
            return labs_urates_at_goal_x_months(
                urates=urates,
                goal_urate=goal_urate,
                x=x,
                r=r + 1,
            )
    # If urate isn't at goal, return False
    else:
        return False


def labs_urate_date_drawn_newer_than_set_date(
    date_drawn: datetime.date,
    set_date: datetime.date,
) -> bool:
    """Method that checks if a date_drawn is newer than a set_date."""
    return date_drawn > set_date


def labs_urates_six_months_at_goal(
    urates: Union["QuerySet[Urate]", list["Urate"]],
    goal_urate: GoalUrates = GoalUrates.SIX,
    r: int = 0,
) -> bool:
    """Calls the labs_urates_at_goal_x_months function with a default of 6 months."""
    return labs_urates_at_goal_x_months(
        urates=urates,
        goal_urate=goal_urate,
        x=6,
        r=r,
    )


def labs_urate_within_x_days(
    urates: Union["QuerySet[Urate]", list["Urate"]],
    x: int,
    sorted_by_date: bool = False,
) -> bool:
    """Method that takes a list or QuerySet of Urates in chronological
    order by a "date" attr with the most recent "date" being index 0
    and returns True if the most recent Urate is less than x days old,
    False if not.

    Checks that list is chronologically sorted if sorted is False.

    urates (QuerySet[Urate] or list[Urate]): QuerySet or list of Urates,
        require using a QuerySet that annotates each Urate with a date, derived
        either from the Urate.date_drawn or the Urate.flare.date_started.
    x (int): number of days to check for
    sorted_by_date (bool): defaults to False, if False, will check that the list is
        sorted by date, if True, will not check.

    Returns:
        bool: True if the most recent Urate is less than x days old,
        False if not."""
    # Check if the list is sorted
    if not sorted_by_date:
        # Check that the urates are in chronological order
        labs_urates_check_chronological_order_by_date(urates)
    return urates[0].date and urates[0].date > timezone.now() - timedelta(days=x) if urates else False


def labs_urate_within_last_month(
    urates: Union["QuerySet[Urate]", list["Urate"]],
    sorted_by_date: bool = False,
) -> bool:
    """Calls the labs_urate_within_x_days function with a default of 30 days."""
    return labs_urate_within_x_days(urates=urates, x=30, sorted_by_date=sorted_by_date)


def labs_urate_within_90_days(
    urates: Union["QuerySet[Urate]", list["Urate"]],
    sorted_by_date: bool = False,
) -> bool:
    """Calls the labs_urate_within_x_days function with a default of 90 days."""
    return labs_urate_within_x_days(urates=urates, x=90, sorted_by_date=sorted_by_date)
