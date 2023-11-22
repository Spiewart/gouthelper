from decimal import Decimal
from typing import TYPE_CHECKING, Union

from django.core.exceptions import ValidationError  # type: ignore
from django.utils.functional import cached_property  # type: ignore

from ..dateofbirths.helpers import age_calc
from ..labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ..medhistorydetails.choices import Stages

if TYPE_CHECKING:
    from ..dateofbirths.forms import DateOfBirthForm
    from ..genders.forms import GenderForm
    from ..labs.forms import BaselineCreatinineForm
    from ..labs.models import BaselineCreatinine
    from ..medhistorydetails.forms import CkdDetailForm
    from ..medhistorys.models import Ckd


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
        dateofbirth_form: "DateOfBirthForm",
        gender_form: "GenderForm",
    ):
        self.baselinecreatinine_form = baselinecreatinine_form
        self.ckd: "Ckd" = ckd
        self.ckddetail_form = ckddetail_form
        self.dateofbirth_form = dateofbirth_form
        self.gender_form = gender_form
        # Don't get these form values. They are not required by the form and so
        # should be in cleaned data as empty values. If they are not, there's
        # a problem and an error should be raised.
        self.baselinecreatinine: Decimal | None = baselinecreatinine_form.cleaned_data["value"]
        self.dialysis = ckddetail_form.cleaned_data["dialysis"]
        self.dialysis_type = ckddetail_form.cleaned_data["dialysis_type"]
        self.dialysis_duration = ckddetail_form.cleaned_data["dialysis_duration"]
        self.stage = ckddetail_form.cleaned_data["stage"]
        self.dateofbirth = dateofbirth_form.cleaned_data["value"]
        self.gender = gender_form.cleaned_data["value"]

    @cached_property
    def age(self) -> int | None:
        return age_calc(self.dateofbirth) if self.dateofbirth else None

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
            else False
            or "value" in self.dateofbirth_form.changed_data
            or "value" in self.gender_form.changed_data
            or not getattr(self.ckddetail_form.instance, "medhistory", None)
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
        # Check if dialysis is not True
        # NOTE: dialysis is NOT None, an empty value from the form comes as an empty string
        if self.dialysis != "" and self.dialysis is False:
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
        # See NOTE above re: why dialysis is an empty string
        elif self.dialysis == "" and self.baselinecreatinine:
            dialysis_error = ValidationError(
                message="If dialysis is not checked, there should be no baseline creatinine."
            )
            self.baselinecreatinine_form.add_error("value", dialysis_error)
            self.ckddetail_form.add_error("dialysis", dialysis_error)
            errors = True
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
            if self.ckddetail_bool and self.changed_data:
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
            # Check if there's a CkdDetail instance to be deleted
            elif (
                not self.ckddetail_bool
                and self.ckddetail_form.instance
                and not self.ckddetail_form.instance._state.adding
            ):
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
