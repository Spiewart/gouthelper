import random
from datetime import datetime, timedelta  # type: ignore
from decimal import Decimal
from typing import TYPE_CHECKING, Union

from django.core.exceptions import ValidationError  # type: ignore
from django.forms import BaseModelFormSet  # type: ignore
from django.utils import timezone  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore

from ..genders.choices import Genders
from ..goalurates.choices import GoalUrates
from ..medhistorydetails.choices import Stages

if TYPE_CHECKING:
    from django.db.models.query import QuerySet  # type: ignore
    from django.forms import ModelForm  # type: ignore

    from ..utils.types import LabData
    from .forms import PpxUrateFormSet, UrateForm
    from .models import BaselineCreatinine, Creatinine, Lab, Urate


def labs_calculate_baseline_creatinine_range_from_ckd_stage(
    stage: Stages,
    age: int,
    gender: Genders,
) -> tuple[Decimal | None, Decimal | None]:
    eGFR_min, eGFR_max = labs_eGFR_range_for_stage(stage)
    return (
        labs_calculate_baseline_creatinine_from_eGFR_age_gender(eGFR=eGFR_min, age=age, gender=gender),
        labs_calculate_baseline_creatinine_from_eGFR_age_gender(eGFR=eGFR_max, age=age, gender=gender),
    )


def labs_calculate_baseline_creatinine_from_eGFR_age_gender(
    eGFR: Decimal,
    age: int,
    gender: Genders,
    value: Decimal = Decimal(2.50),
) -> Decimal:
    eGFR_calc = labs_eGFR_calculator(value, age, gender)
    if abs(eGFR_calc - eGFR) >= 1:
        if eGFR_calc < eGFR:
            return labs_calculate_baseline_creatinine_from_eGFR_age_gender(
                eGFR=eGFR,
                age=age,
                gender=gender,
                value=value - value / 2,
            )
        else:
            return labs_calculate_baseline_creatinine_from_eGFR_age_gender(
                eGFR=eGFR, age=age, gender=gender, value=value + value / 2
            )
    return value if value < Decimal(10) else Decimal("9.99")


def labs_creatinine_is_at_baseline_creatinine(
    creatinine: Union["Creatinine", "LabData"],
    baseline_creatinine: Decimal,
) -> bool:
    # https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5198510/#:~:text=).-,Table%202.,-AKI%20definition%20and
    creatinine_value = labs_get_value_from_model_instance_or_json(creatinine)
    return not (
        creatinine_value >= baseline_creatinine + Decimal(0.3)
        or creatinine_value >= baseline_creatinine * Decimal(1.5)
    )


def labs_creatinine_within_range_for_stage(
    creatinine: "Creatinine",
    stage: Stages,
    age: int,
    gender: Genders,
) -> bool:
    min_creatinine, max_creatinine = labs_creatinine_calculate_min_max_creatinine_from_stage_age_gender(
        stage,
        age,
        gender,
    )
    return min_creatinine <= creatinine.value <= max_creatinine


def labs_creatinine_calculate_min_max_creatinine_from_stage_age_gender(
    stage: Stages,
    age: int,
    gender: Genders,
) -> tuple[Decimal, Decimal]:
    min_eGFR, max_eGFR = labs_eGFR_range_for_stage(stage)
    return (
        labs_calculate_baseline_creatinine_from_eGFR_age_gender(max_eGFR, age, gender),
        labs_calculate_baseline_creatinine_from_eGFR_age_gender(min_eGFR, age, gender),
    )


def labs_creatinine_is_at_baseline_eGFR(
    creatinine_eGFR: Decimal,
    baseline_eGFR: Decimal,
) -> bool:
    # https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5198510/#:~:text=51%2C52-,Table%201.,-RIFLE%20criteria%20for
    return not creatinine_eGFR < baseline_eGFR * 0.75


def labs_creatinines_update_baselinecreatinine(
    creatinines: Union["QuerySet[Creatinine]", list["Creatinine"]],
    baselinecreatinine: Union["BaselineCreatinine", None],
) -> None:
    """This is required because there may be instances where creatinines already exist
    but CKD +/- BaselineCreatinine are being added, at which point they may not have a
    user assigned to their CKD related MedHistory and the reverse lookup will fail."""
    if baselinecreatinine:
        for creatinine in creatinines:
            if creatinine.baselinecreatinine != baselinecreatinine:
                creatinine.baselinecreatinine = baselinecreatinine


def labs_creatinines_add_stage_to_new_objects(
    creatinines: Union["QuerySet[Creatinine]", list["Creatinine"]],
    stage: Stages | None,
) -> None:
    for creatinine in creatinines:
        if creatinine._state.adding:
            creatinine.stage = stage


def labs_get_value_from_model_instance_or_json(
    lab: Union["Lab", "LabData"],
) -> Decimal:
    return lab["value"] if isinstance(lab, dict) else lab.value


def labs_get_date_drawn_from_model_instance_or_json(
    lab: Union["Lab", "LabData"],
) -> datetime.date:
    return lab["date_drawn"] if isinstance(lab, dict) else lab.date_drawn


def labs_creatinines_improved(
    newer_creatinine: Union["Creatinine", "LabData"],
    older_creatinine: Union["Creatinine", "LabData"],
    definition_of_improvement: Decimal = Decimal(0.3),
) -> bool:
    labs_compare_two_lab_date_drawns(
        newer_lab=newer_creatinine,
        older_lab=older_creatinine,
    )
    return (labs_get_value_from_model_instance_or_json(older_creatinine)) - (
        labs_get_value_from_model_instance_or_json(newer_creatinine)
    ) >= definition_of_improvement


def labs_creatinines_equivalent(
    newer_creatinine: Union["Creatinine", "LabData"],
    older_creatinine: Union["Creatinine", "LabData"],
    definition_of_equivalence: Decimal = Decimal(0.2),
) -> bool:
    labs_compare_two_lab_date_drawns(
        newer_lab=newer_creatinine,
        older_lab=older_creatinine,
    )
    return (
        abs(
            labs_get_value_from_model_instance_or_json(newer_creatinine)
            - labs_get_value_from_model_instance_or_json(older_creatinine)
        )
        <= definition_of_equivalence
    )


def labs_creatinines_improving(
    creatinines: Union["QuerySet[Creatinine]", list["Creatinine", "LabData"]],
    r=0,
) -> bool:
    if r >= len(creatinines) - 1:
        return False
    return (
        True
        if (
            labs_creatinines_improved(
                newer_creatinine=creatinines[r],
                older_creatinine=creatinines[r + 1],
            )
            and (
                labs_creatinines_equivalent(
                    newer_creatinine=creatinines[0],
                    older_creatinine=creatinines[r],
                )
                if r != 0
                else True
            )
        )
        else labs_creatinines_improving(creatinines, r + 1)
    )


def labs_creatinines_are_drawn_more_than_x_days_apart(
    current_creatinine: "Creatinine",
    prior_creatinine: "Creatinine",
    days: int,
) -> bool:
    labs_compare_chronological_order_by_date_drawn(current_creatinine, prior_creatinine, prior_creatinine)
    return prior_creatinine.date_drawn - current_creatinine.date_drawn >= timedelta(days=days)


def labs_creatinines_are_drawn_more_than_1_day_apart(
    current_creatinine: "Creatinine",
    prior_creatinine: "Creatinine",
) -> bool:
    return labs_creatinines_are_drawn_more_than_x_days_apart(current_creatinine, prior_creatinine, 1)


def labs_creatinines_are_drawn_more_than_2_days_apart(
    current_creatinine: "Creatinine",
    prior_creatinine: "Creatinine",
) -> bool:
    return labs_creatinines_are_drawn_more_than_x_days_apart(current_creatinine, prior_creatinine, 2)


def labs_baselinecreatinine_max_value(value: Decimal):
    """Method that raises a ValidationError if a baselinecreatinine value is greater than 10 mg/dL."""
    if value > 10:
        raise ValidationError(
            _(
                "A baseline creatinine value greater than 10 mg/dL isn't very likely. \
This would typically mean the patient is on dialysis."
            )
        )


def labs_sort_list_by_date_drawn(
    labs: list["Lab", "LabData"],
) -> None:
    """Sorts a list of labs or JSON data by date_drawn field."""
    labs.sort(
        key=lambda x: x.date_drawn,
        reverse=True,
    )


def labs_sort_list_of_data_by_date_drawn(
    labs: list["LabData"],
) -> None:
    """Sorts a list of labs or JSON data by date_drawn field and returns the sorted list."""
    labs.sort(key=lambda x: x["date_drawn"], reverse=True)


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
        return 90, 120
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
    sex_modifier, alpha, kappa = get_sex_modifier_alpha_kappa(gender)
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


def get_sex_modifier_alpha_kappa(gender: Genders) -> tuple[Decimal, Decimal, Decimal]:
    if gender == Genders.MALE:
        return Decimal(1.000), Decimal(-0.302), Decimal(0.9)
    else:
        return Decimal(1.012), Decimal(-0.241), Decimal(0.7)


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


def labs_check_chronological_order_by_date_drawn(
    labs: Union["QuerySet[Lab]", list["Lab"]],
) -> ValueError | None:
    for lab_i, lab in enumerate(labs):
        labs_compare_chronological_order_by_date_drawn(
            newer_lab=lab, older_lab=labs[lab_i - 1] if lab_i > 0 else None, first_lab=labs[0]
        )


def labs_compare_chronological_order_by_date_drawn(
    newer_lab: "Lab", older_lab: Union["Lab", None], first_lab: "Lab"
) -> ValueError | None:
    if newer_lab.date_drawn > first_lab.date_drawn or older_lab and newer_lab.date_drawn > older_lab.date_drawn:
        raise ValueError("The Labs are not in chronological order. QuerySet must be ordered by date.")


def labs_compare_two_lab_date_drawns(newer_lab: "Lab", older_lab: "Lab") -> ValueError | None:
    if labs_get_date_drawn_from_model_instance_or_json(newer_lab) < labs_get_date_drawn_from_model_instance_or_json(
        older_lab
    ):
        raise ValueError("The Labs are not in chronological order. QuerySet must be ordered by date.")


def labs_urates_check_chronological_order_by_date(
    urates: Union["QuerySet[Urate]", list["Urate"]],
) -> ValueError | None:
    for urate_i, urate in enumerate(urates):
        labs_urates_compare_chronological_order_by_date(
            current_urate=urate, previous_urate=urates[urate_i - 1] if urate_i > 0 else None, first_urate=urates[0]
        )


def labs_urates_compare_chronological_order_by_date(
    current_urate: "Urate", previous_urate: Union["Urate", None], first_urate: "Urate"
) -> ValueError | None:
    if (
        current_urate.flare_date_or_date_drawn > first_urate.flare_date_or_date_drawn
        or previous_urate
        and current_urate.flare_date_or_date_drawn > previous_urate.flare_date_or_date_drawn
    ):
        raise ValueError("The Urates are not in chronological order. QuerySet must be ordered by date.")


def labs_urates_annotate_order_by_flare_date_or_date_drawn(
    urates: list["Urate"],
) -> None:
    urates.sort(key=lambda x: x.flare_date_or_date_drawn, reverse=True)


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


def labs_formset_order_by_date_drawn_remove_deleted_and_blank_forms(
    formset: "BaseModelFormSet",
) -> list["ModelForm"]:
    """Method that orders a labs formset by date_drawn, removes blank forms and forms that have been deleted,
    and returns a list of Lab objects."""

    # Eliminate blank forms and forms that have been deleted
    ordered_formset = [
        form
        for form in formset
        if form.cleaned_data.get("date_drawn")
        and form.cleaned_data.get("value")
        and not form.cleaned_data.get("DELETE")
    ]

    # Order the formset by date_drawn
    ordered_formset = sorted(ordered_formset, key=lambda x: x.cleaned_data.get("date_drawn"), reverse=True)

    return ordered_formset


def labs_get_list_of_instances_from_list_of_forms_cleaned_data(
    list_of_forms: list["ModelForm"],
) -> list["Lab"]:
    """Method that returns a list of urate values from a labs formset."""
    return [form.instance for form in list_of_forms]


def labs_formset_get_most_recent_form(
    ordered_formset: "BaseModelFormSet",
) -> Union["ModelForm", None]:
    """Method that returns the most recent LabForm object in an ordered labs formset.
    Ordered: sorted by date_drawn in descending order, forms marked for deletion removed."""
    return ordered_formset[0] if ordered_formset else None


def labs_formset_has_one_or_more_valid_labs(
    formset: "BaseModelFormSet",
) -> bool:
    """Method that checks if a urates formset has at least one valid Urate object."""
    for form in formset:
        date_drawn, value, delete = labs_forms_get_date_drawn_value_DELETE(form)
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
    return labs_urates_at_goal(urates, goal_urate) and labs_check_date_drawn_within_a_month(
        urates[0].flare_date_or_date_drawn
    )


def labs_urates_not_at_goal_within_last_x_days(
    urates: Union["QuerySet[Urate]", list["Urate"]],
    x: int,
    goal_urate: GoalUrates = GoalUrates.SIX,
) -> bool:
    """Checks if the most recent urate in a list or QuerySet of Urates is not at goal within the last x days."""
    return labs_urates_not_at_goal(urates, goal_urate) and labs_check_date_drawn_is_within_x_days(
        urates[0].flare_date_or_date_drawn, x
    )


def labs_urates_not_at_goal_within_last_month(
    urates: Union["QuerySet[Urate]", list["Urate"]],
    goal_urate: GoalUrates = GoalUrates.SIX,
) -> bool:
    """Checks if the most recent urate in a list or QuerySet of Urates is not at goal within the last month."""
    return labs_urates_not_at_goal(urates, goal_urate) and labs_check_date_drawn_within_a_month(
        urates[0].flare_date_or_date_drawn
    )


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
        if (urates[0].flare_date_or_date_drawn - urates[r].flare_date_or_date_drawn) >= timedelta(days=30 * x):
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
    if not sorted_by_date:
        labs_urates_check_chronological_order_by_date(urates)
    return (
        urates[0].flare_date_or_date_drawn
        and urates[0].flare_date_or_date_drawn > (timezone.now() - timedelta(days=x)).date()
        if urates
        else False
    )


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
