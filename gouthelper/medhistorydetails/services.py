from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Union

from django.core.exceptions import ValidationError  # type: ignore
from django.utils.functional import cached_property  # type: ignore

from ..dateofbirths.forms import DateOfBirthForm
from ..dateofbirths.helpers import age_calc
from ..dateofbirths.models import DateOfBirth
from ..genders.forms import GenderForm
from ..genders.models import Gender
from ..labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ..labs.models import BaselineCreatinine
from ..utils.exceptions import GoutHelperValidationError
from .choices import Stages
from .models import CkdDetail

if TYPE_CHECKING:
    from uuid import UUID

    from ..genders.choices import Genders
    from ..labs.forms import BaselineCreatinineForm
    from ..medhistorydetails.forms import CkdDetailForm
    from ..medhistorys.models import Ckd
    from ..utils.types import CkdDetailFieldOptions
    from .choices import DialysisChoices, DialysisDurations


class CkdDetailAPIMixin:
    """Mixin class that checks a child class for conflicts in CkdDetail attributes."""

    def __init__(
        self,
        ckddetail: Union["CkdDetail", "UUID", None],
        ckd: Union["Ckd", "UUID", None],
        dialysis: bool | None,
        dialysis_type: Union["DialysisChoices", None],
        dialysis_duration: Union["DialysisDurations", None],
        stage: Stages | None,
        dateofbirth: Union[DateOfBirth, "UUID", "date", None],
        baselinecreatinine: Union[BaselineCreatinine, "UUID", "Decimal", None],
        gender: Union[Gender, "UUID", "Genders", None],
    ):
        self.ckddetail = ckddetail
        self.ckd = ckd
        self.dialysis = dialysis
        self.dialysis_type = dialysis_type
        self.dialysis_duration = dialysis_duration
        self.stage = stage
        self.dateofbirth = dateofbirth
        self.age = self.calculate_age() if dateofbirth else None
        self.baselinecreatinine = baselinecreatinine
        self.gender = gender
        self.errors: list[tuple[str, str]] = []

    def calculate_age(self) -> int:
        return (
            age_calc(self.dateofbirth.value)
            if isinstance(self.dateofbirth, DateOfBirth)
            else age_calc(self.dateofbirth)
        )

    def update_errors(self) -> None:
        if self.stage_calculated_stage_conflict:
            self.errors.append(("stage", "Stage does not match calculated stage."))
        if self.dialysis_stage_conflict:
            self.errors.append(("stage", "Stage must be 5 if dialysis is True."))
        if self.dialysis_type_conflict:
            self.errors.append(("dialysis_type", "Dialysis type is required if dialysis is True."))
        if self.dialysis_duration_conflict:
            self.errors.append(("dialysis_duration", "Dialysis duration is required if dialysis is True."))
        if self.baselinecreatinine_age_gender_conflict:
            self.errors.append(
                (
                    "baselinecreatinine",
                    "Age and gender are required to interpret baseline creatinine (to calculate a stage).",
                )
            )
        if self.ckd_ckddetail_conflict:
            self.errors.append(("non_field_errors", f"{self.ckddetail} is not related to {self.ckd}."))
        elif self.incomplete_info:
            self.errors.append(("non_field_errors", "Incomplete information for CkdDetail."))

    @property
    def no_ckddetail(self) -> bool:
        return self.ckddetail is None and not hasattr(self.ckd, "ckddetail")

    @property
    def ckd_ckddetail_conflict(self) -> bool:
        return (
            self.ckd
            and self.ckddetail
            and (
                (self.ckddetail.medhistory and self.ckddetail.medhistory != self.ckd)
                or (self.ckd.ckddetail and self.ckd.ckddetail != self.ckddetail)
            )
        )

    @property
    def incomplete_info(self) -> bool:
        return self.no_ckddetail and self.dialysis is None and self.stage is None and not self.can_calculate_stage

    @property
    def can_calculate_stage(self) -> bool:
        return self.baselinecreatinine and self.age and self.gender is not None

    @property
    def should_calculate_stage(self) -> bool:
        return not self.dialysis and self.can_calculate_stage

    @property
    def calculated_stage(self) -> "Stages":
        return labs_stage_calculator(
            labs_eGFR_calculator(
                age=self.age,
                creatinine=self.baselinecreatinine,
                gender=self.gender,
            )
        )

    @property
    def stage_calculated_stage_conflict(self) -> bool:
        return self.stage and self.should_calculate_stage and self.calculated_stage != self.stage

    @property
    def dialysis_stage_conflict(self) -> bool:
        return self.dialysis and self.stage and self.stage != Stages.FIVE

    @property
    def dialysis_type_conflict(self) -> bool:
        return self.dialysis and self.dialysis_type is None

    @property
    def dialysis_duration_conflict(self) -> bool:
        return self.dialysis and self.dialysis_duration is None

    @property
    def baselinecreatinine_age_gender_conflict(self) -> bool:
        return self.baselinecreatinine and not self.can_calculate_stage

    @property
    def conflicts(self) -> bool:
        return (
            self.stage_calculated_stage_conflict
            or self.dialysis_stage_conflict
            or self.dialysis_type_conflict
            or self.dialysis_duration_conflict
            or self.baselinecreatinine_age_gender_conflict
        )

    @property
    def has_errors(self) -> bool:
        return self.conflicts or self.incomplete_info or self.ckd_ckddetail_conflict

    def raise_gouthelper_validation_error(self) -> None:
        raise GoutHelperValidationError(
            message=f"Args for {'updating' if self.ckddetail else 'creating'} CkdDetail contain errors:{self.errors}.",
            errors=self.errors,
        )

    def _update_attrs(self) -> None:
        if not self.stage and self.should_calculate_stage:
            self.stage = self.calculated_stage
        elif self.dialysis and self.stage is None:
            self.stage = Stages.FIVE
        if self.dialysis is None:
            self.dialysis = False
        if not self.dialysis:
            self._set_dialysis_duration_type_to_None()

    def _set_dialysis_duration_type_to_None(self) -> None:
        self.dialysis_type = None
        self.dialysis_duration = None


class CkdDetailCreator(CkdDetailAPIMixin):
    def __init__(
        self,
        ckd: Union["Ckd", None],
        dialysis: bool | None,
        dialysis_type: Union["DialysisChoices", None],
        dialysis_duration: Union["DialysisDurations", None],
        stage: Stages | None,
        age: int | None,
        baselinecreatinine: Union["Decimal", None],
        gender: Union["Genders", None],
    ):
        super().__init__(
            ckddetail=None,
            ckd=ckd,
            dialysis=dialysis,
            dialysis_type=dialysis_type,
            dialysis_duration=dialysis_duration,
            stage=stage,
            age=age,
            baselinecreatinine=baselinecreatinine,
            gender=gender,
        )
        self.args_processed = False

    def create(self) -> CkdDetail:
        if self.ckddetail:
            raise ValueError(f"CkdDetail instance already exists for {self.ckd}.")
        elif not self.ckd:
            raise ValueError("Ckd instance required for CkdDetail creation.")
        if not self.args_processed:
            self.process_args()
        return CkdDetail.objects.create(
            dialysis=self.dialysis,
            dialysis_type=self.dialysis_type,
            dialysis_duration=self.dialysis_duration,
            stage=self.stage,
            medhistory=self.ckd,
        )

    def process_args(self) -> None:
        self.update_errors()
        if self.errors:
            self.raise_gouthelper_validation_error()
        self._update_attrs()
        self.args_processed = True

    def update_ckd_attr(self, ckd: Union["Ckd", None]) -> None:
        self.ckd = ckd


class CkdDetailUpdater(CkdDetailAPIMixin):
    def __init__(
        self,
        ckddetail: Union["CkdDetail", None],
        dialysis: bool | None,
        dialysis_type: Union["DialysisChoices", None],
        dialysis_duration: Union["DialysisDurations", None],
        stage: Stages | None,
        age: int | None,
        baselinecreatinine: Union["Decimal", None],
        gender: Union["Genders", None],
        initial: Union["CkdDetailFieldOptions", None] = None,
    ):
        super().__init__(
            ckddetail=ckddetail,
            ckd=ckddetail.medhistory,
            dialysis=dialysis,
            dialysis_type=dialysis_type,
            dialysis_duration=dialysis_duration,
            stage=stage,
            age=age,
            baselinecreatinine=baselinecreatinine,
            gender=gender,
        )
        self.initial = initial

    def check_ckddetail_initial_error(self) -> None:
        if self.ckddetail_initial_conflict:
            raise ValueError("Initial values do not match CkdDetail instance values.")

    @property
    def ckddetail_initial_conflict(self) -> bool:
        return (
            self.ckddetail
            and self.initial
            and next(iter([getattr(self.ckddetail, key) != val for key, val in self.initial.items()]))
        )

    @property
    def ckddetail_has_changed(self) -> bool:
        return any([getattr(self, key) != val for key, val in self.initial.items()])

    def update_ckddetail_fields(self) -> None:
        for field_val in self.get_ckddetail_changed_fields():
            setattr(self.ckddetail, field_val[0], field_val[1])

    def get_ckddetail_changed_fields(self) -> list[tuple[str, Any]]:
        changed_fields = []
        for key, val in self.initial.items():
            editor_attr = getattr(self, key)
            if editor_attr != val:
                changed_fields.append((key, editor_attr))
        return changed_fields

    def update(self) -> CkdDetail:
        if not self.ckddetail:
            raise ValueError("CkdDetail instance required for update.")
        if self.initial:
            self.check_ckddetail_initial_error()
        else:
            self._update_initial()
        self.update_errors()
        if self.errors:
            self.raise_gouthelper_validation_error()
        self._update_attrs()
        if self.ckddetail_has_changed:
            self.update_ckddetail_fields()
            self.ckddetail.full_clean()
            self.ckddetail.save()
        return self.ckddetail

    def _update_initial(self):
        self.initial.update(
            {
                "dialysis": self.ckddetail.dialysis,
                "dialysis_type": self.ckddetail.dialysis_type,
                "dialysis_duration": self.ckddetail.dialysis_duration,
                "stage": self.ckddetail.stage,
            }
        )


class CkdDetailFormProcessor:
    """Class method to process CkdDetailForm, BaselineCreatinineForm, DateOfBirthForm, and GenderForm.
    Updates forms data and errors.

    process() method returns a tuple of:
        -CkdDetailForm or None, potentially modified
        -BaselineCreatinineForm or None, potentially modified
        -bool indicating whether or not there are errors

    Args:
        ckd (Ckd): Ckd instance
        ckddetail_form (CkdDetailForm): CkdDetailForm instance
        baselinecreatinine_form (BaselineCreatinineForm): BaselineCreatinineForm instance
        dateofbirth_form (DateOfBirthForm): DateOfBirthForm instance
        gender_form (GenderForm): GenderForm instance
    """

    def __init__(
        self,
        ckd: "Ckd",
        ckddetail_form: "CkdDetailForm",
        baselinecreatinine_form: "BaselineCreatinineForm",
        dateofbirth: Union[DateOfBirthForm, "DateOfBirth"],
        gender: Union[GenderForm, "Gender"],
    ):
        self.baselinecreatinine_form = baselinecreatinine_form
        self.ckd: "Ckd" = ckd
        self.ckddetail_form = ckddetail_form
        self.dateofbirth_form = dateofbirth if isinstance(dateofbirth, DateOfBirthForm) else None
        self.gender_form = gender if isinstance(gender, GenderForm) else None
        # Don't get these form values. They are not required by the form and so
        # should be in cleaned data as empty values. If they are not, there's
        # a problem and an error should be raised.
        self.baselinecreatinine: Decimal | None = baselinecreatinine_form.cleaned_data["value"]
        self.dialysis = ckddetail_form.cleaned_data["dialysis"]
        self.dialysis_type = ckddetail_form.cleaned_data["dialysis_type"]
        self.dialysis_duration = ckddetail_form.cleaned_data["dialysis_duration"]
        self.stage = ckddetail_form.cleaned_data["stage"]
        if self.dateofbirth_form:
            self.dateofbirth = self.dateofbirth_form.cleaned_data["value"]
        else:
            self.dateofbirth = dateofbirth.value if isinstance(dateofbirth, DateOfBirth) else dateofbirth
        if self.gender_form:
            self.gender = self.gender_form.cleaned_data["value"]
        else:
            self.gender = gender.value if isinstance(gender, Gender) else gender

    @cached_property
    def age(self) -> int | None:
        return (
            age_calc(self.dateofbirth)
            if self.dateofbirth and isinstance(self.dateofbirth, (date, datetime))
            else self.dateofbirth
            if self.dateofbirth
            else None
        )

    @property
    def baselinecreatinine_initial(self) -> Decimal | None:
        """Method that returns the initial value of the baselinecreatinine_form.

        Returns:
            float or None"""
        # Save initial value of baselinecreatinine to set it back if necessary
        # Avoids errors created by django-simple-history saving a model on delete()
        try:
            return self.baselinecreatinine_form.initial["value"]
        except KeyError:
            return None

    @property
    def calculated_stage(self) -> Stages | None:
        """Method that checks if all necessary data is present to calculate a stage.
        If so, returns the calculated stage. Otherwise, returns None.

        Returns:
            Stages enum or None"""
        # Check if all necessary data is present to calculate a stage
        if self.baselinecreatinine and self.age and self.gender is not None:
            # If so, calculate and return stage
            return labs_stage_calculator(
                eGFR=labs_eGFR_calculator(
                    creatinine=self.baselinecreatinine,
                    age=self.age,
                    gender=self.gender,
                ),
            )
        # If not all necessary data is present, return None
        return None

    @property
    def changed_data(self) -> bool:
        """Method that returns a bool indicating whether or not any of the forms have changed data."""
        return (
            "dialysis" in self.ckddetail_form.changed_data
            or "dialysis_type" in self.ckddetail_form.changed_data
            or "dialysis_duration" in self.ckddetail_form.changed_data
            or "stage" in self.ckddetail_form.changed_data
            or "value" in self.baselinecreatinine_form.changed_data
            if self.baselinecreatinine_form
            else False or "value" in self.dateofbirth_form.changed_data
            if self.dateofbirth_form
            else False or "value" in self.gender_form.changed_data
            if self.gender_form
            else False or not getattr(self.ckddetail_form.instance, "medhistory", None)
        )

    def _check_process_returns(
        self,
        ckddetailform: Union["CkdDetailForm", None],
        baselinecreatinine_form: Union["BaselineCreatinineForm", None],
    ) -> None:
        # Check if there are forms and instances on the forms
        ckddetail = ckddetailform.instance if ckddetailform else None
        baselinecreatinine = baselinecreatinine_form.instance if baselinecreatinine_form else None
        # If there's a CkdDetail instance
        if ckddetail:
            # Check if the ckddetail is marked for deletion
            if hasattr(ckddetail, "to_delete") and ckddetail.to_delete:
                # If so, check if there's a baselinecreatinine instance
                if baselinecreatinine and not baselinecreatinine._state.adding:
                    # If so, check if it's marked for deletion and raise an error if its not
                    if (
                        not hasattr(baselinecreatinine, "to_delete")
                        or hasattr(baselinecreatinine, "to_delete")
                        and not baselinecreatinine.to_delete
                    ):
                        # If so, raise an error
                        raise ValueError(
                            "If the CkdDetail is marked for deletion, the BaselineCreatinine should be as well."
                        )

    @cached_property
    def ckddetail_bool(self) -> bool:
        """Method that returns a bool indicating whether or not a
        CkdDetail instance should be created or updated."""
        if not self.stage and not self.dialysis and not self.calculated_stage:
            return False
        return True

    def check_for_errors(self) -> bool:
        """Method that checks for errors and adds them to the forms if necessary.
        Checks and updates the following:
            -baselinecreatinine_form
            -gender_form
            -dateofbirth_form
            -ckddetail_form

        returns: bool indicating whether or not there are errors
        """
        # Check for errors and add them to the forms if necessary
        errors = False
        # NOTE: dialysis is NOT None, an empty value from the form comes as an empty string
        # If a CkdDetail is being processed, dialysis is required
        # This has to be checked by the view because the forms are different
        if self.dialysis == "" and not self.ckddetail_form.optional:
            dialysis_error = ValidationError(message="Dialysis is a required field.")
            self.ckddetail_form.add_error("dialysis", dialysis_error)
            errors = True
        # Check if dialysis is False
        elif self.dialysis is False:
            # If there's a baselinecreatinine
            if self.baselinecreatinine is not None:
                # If so, check if gender and age, required for interpreting baseline creatinine, are present
                # NOTE: Gender also is not None, but an empty string if null from the form
                if self.gender == "" or self.age is None:
                    # Create default error message and add to it based on presence / absence of age/gender
                    age_gender_str = "required to interpret a baseline creatinine (calculate a stage). \
Please double check and try again."
                    if not self.age and self.gender == "":
                        age_gender_str = "Age and gender are " + age_gender_str
                    elif not self.age:
                        age_gender_str = "Age is " + age_gender_str
                    else:
                        age_gender_str = "Gender is " + age_gender_str
                    age_gender_baselinecreat_error = ValidationError(message=age_gender_str)
                    self.baselinecreatinine_form.add_error("value", age_gender_baselinecreat_error)
                    if self.gender == "":
                        self.gender_form.add_error("value", age_gender_baselinecreat_error)
                    if self.age is None:
                        self.dateofbirth_form.add_error("value", age_gender_baselinecreat_error)
                    errors = True
                # Else if there's a baselinecreatinine and a stage can be calculated
                # Compare with stage in CkdDetailForm
                elif self.calculated_stage and self.stage and self.calculated_stage != self.stage:
                    # If the two aren't equal, update errors and add them to the forms
                    baselinecreatinine_error = ValidationError(
                        message=f"The stage ({self.calculated_stage}) calculated from the baseline creatinine, \
age, and gender does not match the selected stage ({self.stage}). Please double check and try again."
                    )
                    self.baselinecreatinine_form.add_error("value", baselinecreatinine_error)
                    stage_error = ValidationError(
                        message=f"The selected stage ({self.stage}) does not match the stage \
{self.calculated_stage} calculated from the baseline creatinine, age, and gender. \
Please double check and try again."
                    )
                    self.ckddetail_form.add_error("stage", stage_error)
                    errors = True
        # If dialysis is True, dialysis_type and dialysis_duration are handled by the form
        return errors

    def delete_baselinecreatinine(
        self,
        instance: "BaselineCreatinine",
        initial: Decimal | None = None,
    ) -> None:
        """Method that marks a BaselineCreatinine instance for deletion.
        Adjusts the baselinecreatinine_form.instance to avoid errors created by
        django-simple-history saving a model on delete()."""
        if instance.value != initial:
            instance.value = initial
        if not hasattr(instance, "to_delete") or not instance.to_delete:
            instance.to_delete = True

    def get_stage(
        self,
        dialysis: bool | None,
        stage: Stages | None,
        calculated_stage: Stages | None,
    ) -> Stages | None:
        """Method that returns the stage to be saved in the CkdDetail instance.

        returns:
            Stages enum or None"""
        # Check if dialysis is True
        if dialysis:
            # If so, return Stage.FIVE
            return Stages.FIVE
        # Else if dialysis is None and there's no stage
        elif dialysis is None and not stage:
            # Return None, because there's no CkdDetail needing creation/update
            # Will mark ckddetail for deletion if it exists
            return None
        # If there's both a stage and a calculated_stage and they're not equal
        # raise a ValueError. This should already have been caught by check_for_errors().
        elif stage and calculated_stage and stage != calculated_stage:
            raise ValueError(
                "If there's a stage and a calculated_stage, they should be equal. \
Please double check and try again."
            )
        # If there's no dialysis, compare stage and calculated_stage and return the appropriate one
        elif stage and not calculated_stage:
            return stage
        elif calculated_stage and not stage:
            return calculated_stage
        elif stage and calculated_stage and stage == calculated_stage:
            return stage
        return None

    def ckd_stage_is_empty_with_baselinecreatinine(self) -> bool:
        return not self.stage and self.baselinecreatinine

    def process(
        self,
    ) -> tuple[Union["CkdDetailForm", None], Union["BaselineCreatinineForm", None], bool]:
        """Modifies form data, checks them for and adds errors, and deletes
        CkdDetail and BaselineCreatinine instances if necessary.

        Returns:
            -CkdDetailForm or None, potentially modified
            -BaselineCreatinineForm or None, potentially modified
            -bool indicating whether or not there are errors
        """
        # Check for errors, which will populate errors on the forms, mark errors bool as True if so
        errors = self.check_for_errors()
        # If there are no errors, process the forms
        if not errors:
            # Check if there is supposed to be a CkdDetail instance added/updated
            if (self.ckddetail_bool or self.baselinecreatinine) and (
                self.changed_data or self.ckd_stage_is_empty_with_baselinecreatinine
            ):
                # If so, process CkdDetail and BaselineCreatinine
                self.set_ckd_fields(
                    ckddetail_form=self.ckddetail_form,
                    stage=self.get_stage(
                        dialysis=self.dialysis,
                        stage=self.stage,
                        calculated_stage=self.calculated_stage,
                    ),
                    ckd=self.ckd,
                )
                self.baselinecreatinine_form = self.set_baselinecreatinine(
                    ckddetail_bool=self.ckddetail_bool,
                    baselinecreatinine_form=self.baselinecreatinine_form,
                    initial=self.baselinecreatinine_initial,
                    dialysis=self.dialysis,
                    ckd=self.ckd,
                )
            # Check if there's a CkdDetail or BaselineCreatinine instance to be deleted
            elif not self.ckddetail_bool:
                if self.ckddetail_form.instance and not self.ckddetail_form.instance._state.adding:
                    # If so, set it's fields to the initial values and mark it for deletion
                    for field in self.ckddetail_form.changed_data:
                        setattr(self.ckddetail_form.instance, field, self.ckddetail_form.initial[field])
                    # If so, mark it for deletion
                    self.ckddetail_form.instance.to_delete = True
                # Check if there's a BaselineCreatinine instance to be deleted
                if self.baselinecreatinine_form.instance and not self.baselinecreatinine_form.instance._state.adding:
                    # If so, mark it for deletion
                    self.baselinecreatinine_form = self.set_baselinecreatinine(
                        ckddetail_bool=self.ckddetail_bool,
                        baselinecreatinine_form=self.baselinecreatinine_form,
                        initial=self.baselinecreatinine_initial,
                        dialysis=self.dialysis,
                        ckd=self.ckd,
                    )
            # If there's no CkdDetail instance to be added or updated
            else:
                # Call set_baselinecreatinine() to mark the BaselineCreatinine instance for deletion
                self.baselinecreatinine_form = self.set_baselinecreatinine(
                    ckddetail_bool=self.ckddetail_bool,
                    baselinecreatinine_form=self.baselinecreatinine_form,
                    initial=self.baselinecreatinine_initial,
                    dialysis=self.dialysis,
                    ckd=self.ckd,
                )
        # Call the _check_process_returns method to double-check that the CkdDetail
        # and BaselineCreatinine instances are consistent
        self._check_process_returns(self.ckddetail_form, self.baselinecreatinine_form)
        # Return the forms and errors, forms and their instances will NOT have been
        # processed if there are errors to avoid making saves to the database
        return self.ckddetail_form, self.baselinecreatinine_form, errors

    def set_baselinecreatinine(
        self,
        ckddetail_bool: bool,
        baselinecreatinine_form: Union["BaselineCreatinineForm", None] = None,
        initial: Decimal | None = None,
        dialysis: bool | None = None,
        ckd: Union["Ckd", None] = None,
    ) -> "BaselineCreatinineForm":
        """Method that modifies the BaselineCreatinineForm and either returns it
        or marks it for deletion by setting its instance's to_delete attr to True.

        Returns: None"""
        cleaned_value = baselinecreatinine_form.cleaned_data["value"] if baselinecreatinine_form else None
        # If this is an update/delete situation
        if not baselinecreatinine_form.instance._state.adding:
            # If there's no ckddetail, mark for deletion
            if not ckddetail_bool:
                self.delete_baselinecreatinine(
                    baselinecreatinine_form.instance, initial=self.baselinecreatinine_initial
                )
            # Else if there's a ckddetail and dialysis is True, mark for deletion
            elif dialysis is True:
                self.delete_baselinecreatinine(instance=baselinecreatinine_form.instance, initial=initial)
            # Otherwise, check if the baselinecreatinine instance has changed
            elif cleaned_value and cleaned_value != initial:
                # If so, check if "value" is in the form's changed_data list
                if "value" not in baselinecreatinine_form.changed_data:
                    # If so, add "value" to the form's changed_data list
                    baselinecreatinine_form.changed_data.append("value")
                # Set the baselinecreatinine instance to_save attr to True
                baselinecreatinine_form.instance.to_save = True
            # If there's no value in the baselinecreatinine_form, delete the instance
            elif not cleaned_value:
                self.delete_baselinecreatinine(instance=baselinecreatinine_form.instance, initial=initial)
        # If this is not an update/delete, it's a create situation
        # Check if there is a CkdDetail and a baselinecreatinine
        elif ckddetail_bool and cleaned_value:
            baselinecreatinine_form.save(commit=False)
            baselinecreatinine_form.instance.to_save = True
            baselinecreatinine_form.instance.medhistory = ckd
        return baselinecreatinine_form

    def set_ckd_fields(
        self,
        ckddetail_form: "CkdDetailForm",
        stage: Stages | None = None,
        ckd: Union["Ckd", None] = None,
    ) -> None:
        """Method that modifies the CkdDetailForm to reflect the stage
        determined by get_stage() method and for CkdDetails being created,
        adds the ckd to the CkdDetail medhistory attribute.

        returns: None"""
        # Set the CkdDetail object stage attribute to the stage
        if ckddetail_form.instance.stage != stage:
            if "stage" not in ckddetail_form.changed_data:
                ckddetail_form.changed_data.append("stage")
            ckddetail_form.instance.stage = stage
        # If this is a new CkdDetail, add the ckd to the medhistory attribute
        if ckddetail_form.instance._state.adding:
            # Set the ckddetail_form's instance to_save attr to True
            ckddetail_form.instance.to_save = True
            ckddetail_form.instance.medhistory = ckd
        # Otherwise, this is a potential update. Check if the CkdDetail instance has changed
        elif self.changed_data and self.ckddetail_bool and ckddetail_form.changed_data:
            # If so, set the CkdDetail instance to_save attr to True
            ckddetail_form.instance.to_save = True
