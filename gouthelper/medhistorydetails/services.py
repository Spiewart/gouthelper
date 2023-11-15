from typing import TYPE_CHECKING, Union

from django.core.exceptions import ValidationError  # type: ignore

from ..dateofbirths.helpers import age_calc
from ..labs.helpers import eGFR_calculator, stage_calculator
from ..medhistorydetails.choices import Stages

if TYPE_CHECKING:
    from ..dateofbirths.forms import DateOfBirthForm
    from ..flareaids.models import FlareAid
    from ..genders.forms import GenderForm
    from ..labs.forms import BaselineCreatinineForm
    from ..labs.models import BaselineCreatinine
    from ..medhistorydetails.forms import CkdDetailForm
    from ..medhistorys.models import Ckd
    from ..ppxaids.models import PpxAid
    from ..ultaids.models import UltAid
    from ..ults.models import Ult


class CkdDetailFormProcessor:
    """Class method to process CkdDetailForm, BaselineCreatinineForm, DateOfBirthForm, and GenderForm.
    Updates forms data and errors. Will CkdDetail and BaselineCreatinine instances if necessary.

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
        updating: Union["FlareAid", "PpxAid", "UltAid", "Ult", None] = None,
    ):
        self.baselinecreatinine_form = baselinecreatinine_form
        self.ckd = ckd
        self.ckddetail_form = ckddetail_form
        self.dateofbirth_form = dateofbirth_form
        self.gender_form = gender_form
        self.updating = updating
        self.dialysis = ckddetail_form.cleaned_data["dialysis"]
        self.dialysis_type = ckddetail_form.cleaned_data["dialysis_type"]
        self.dialysis_duration = ckddetail_form.cleaned_data["dialysis_duration"]
        self.baselinecreatinine = baselinecreatinine_form.cleaned_data["value"]
        # Save initial value of baselinecreatinine to set it back if necessary
        # Avoids errors created by django-simple-history saving a model on delete()
        try:
            self.baselinecreatinine_initial = baselinecreatinine_form.initial["value"]
        except KeyError:
            self.baselinecreatinine_initial = None
        self.stage = ckddetail_form.cleaned_data["stage"]
        self.dateofbirth = dateofbirth_form.cleaned_data["value"]
        # Calculate age from dateofbirth
        if self.dateofbirth:
            self.age = age_calc(self.dateofbirth)
        else:
            self.age = None
        self.gender = gender_form.cleaned_data["value"]
        self.ckddetail = ckddetail_form.save(commit=False)

    @property
    def calculated_stage(self) -> Stages | None:
        """Method that checks if all necessary data is present to calculate a stage.
        If so, returns the calculated stage. Otherwise, returns None.

        Returns:
            Stages enum or None"""
        # Check if all necessary data is present to calculate a stage
        if self.baselinecreatinine and self.age and self.gender is not None:
            # If so, calculate and return stage
            return stage_calculator(
                eGFR=eGFR_calculator(
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

    def ckddetail_check(self) -> bool:
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

    def delete_baselinecreatinine(self, instance: "BaselineCreatinine") -> None:
        """Method that deletes a BaselineCreatinine instance and sets the baselinecreatinine_form to None.
        Adjusts the baselinecreatinine_form.instance to avoid errors created by
        django-simple-history saving a model on delete()."""
        if instance.value != self.baselinecreatinine_initial:
            instance.value = self.baselinecreatinine_initial
        instance.delete()

    def get_stage(self) -> Stages | None:
        """Method that returns the stage to be saved in the CkdDetail instance.

        Returns:
            Stages enum or None"""
        # Check if dialysis is True
        if self.dialysis:
            # If so, return Stage.FIVE
            return Stages.FIVE
        # Else if dialysis is None and there's no stage
        elif self.dialysis is None and not self.stage:
            # Return None, because there's no CkdDetail needing creation/update
            # Will mark ckddetail for deletion if it exists
            return None
        # If there's no dialysis, compare stage and calculated_stage and return the appropriate one
        elif self.stage and not self.calculated_stage:
            return self.stage
        elif self.calculated_stage and not self.stage:
            return self.calculated_stage
        else:
            return self.stage

    def process(self) -> tuple[Union["CkdDetailForm", None], Union["BaselineCreatinineForm", None], bool]:
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
            if self.ckddetail_check():
                # If so, check if there's any changed data in the CkdDetailForm or its related forms
                if self.changed_data:
                    # If so, process CkdDetail and BaselineCreatinine
                    self.set_ckd_fields()
                    self.set_baselinecreatinine()
                # Otherwise just leave the forms as is for the view to manage
            # If there's no CkdDetail instance to be added/updated
            else:
                # Check if there's a CkdDetail instance
                if not self.ckddetail_form.instance._state.adding:
                    # If so, set it's fields to the initial values and delete it
                    for field in self.ckddetail_form.changed_data:
                        setattr(self.ckddetail, field, self.ckddetail_form.initial[field])
                    self.ckddetail_form.instance.delete()
                self.ckddetail = None
                # Call set_baselinecreatinine() to delete the BaselineCreatinine instance
                self.set_baselinecreatinine()
        # Return the forms and errors, forms and their instances will NOT have been
        # processed if there are errors to avoid making saves to the database
        return self.ckddetail, self.baselinecreatinine_form, errors

    def set_baselinecreatinine(self) -> None:
        """Method that modifies the BaselineCreatinineForm and either returns it
        or marks it for deletion by setting the class attribute to None.

        Returns: None"""
        # Check if the baselinecreatinine_form has an instance that is not being added
        # Means this is a potential update vs delete
        if not self.baselinecreatinine_form.instance._state.adding:
            instance = self.baselinecreatinine_form.instance
        else:
            instance = None
        # If this is an update/delete situation
        if instance:
            # If there's no ckddetail, mark for deletion
            if not self.ckddetail_check():
                self.delete_baselinecreatinine(instance)
                self.baselinecreatinine_form = None
            # Else if there's a ckddetail and dialysis is True, mark for deletion
            elif self.dialysis is True:
                self.delete_baselinecreatinine(instance)
                self.baselinecreatinine_form = None
            # Otherwise, check if the baselinecreatinine instance has changed
            elif (
                instance.value != self.baselinecreatinine and "value" not in self.baselinecreatinine_form.changed_data
            ):
                # If so, add "value" to the form's changed_data list
                self.baselinecreatinine_form.changed_data.append("value")
                self.baselinecreatinine_form = self.baselinecreatinine_form.save(commit=False)
            # If there's no value in the baselinecreatinine_form, delete the instance
            elif not self.baselinecreatinine:
                self.delete_baselinecreatinine(instance)
                self.baselinecreatinine_form = None
        # If this is not an update/delete, it's a create situation
        else:
            # If there's no ckddetail, mark for not processing the form further (i.e. saving)
            if not self.ckddetail_check():
                self.baselinecreatinine_form = None
            # Else if there's no baselinecreatinine value, mark for not processing the form further (i.e. saving)
            elif not self.baselinecreatinine:
                self.baselinecreatinine_form = None
            # Else if there's a baselinecreatinine value, mark it for saving by commiting it
            # Add the ckd to the baselinecreatinine instance
            else:
                self.baselinecreatinine_form = self.baselinecreatinine_form.save(commit=False)
                self.baselinecreatinine_form.medhistory = self.ckd

    def set_ckd_fields(self) -> None:
        """Method that modifies the CkdDetailForm to reflect the stage
        determined by get_stage() method and for CkdDetails being created,
        adds the ckd to the CkdDetail medhistory attribute.

        returns: None"""
        # Figure out what the stage should be
        stage = self.get_stage()
        # Set the CkdDetail object stage attribute to the stage
        if self.ckddetail.stage != stage:
            if "stage" not in self.ckddetail_form.changed_data:
                self.ckddetail_form.changed_data.append("stage")
            self.ckddetail.stage = stage
        # If this is a new CkdDetail, add the ckd to the medhistory attribute
        if self.ckddetail_form.instance._state.adding:
            self.ckddetail_form.instance.medhistory = self.ckd
