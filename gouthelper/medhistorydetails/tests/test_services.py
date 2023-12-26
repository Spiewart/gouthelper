from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ...dateofbirths.forms import DateOfBirthForm, DateOfBirthFormOptional
from ...dateofbirths.helpers import age_calc
from ...dateofbirths.models import DateOfBirth
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...genders.choices import Genders
from ...genders.forms import GenderForm, GenderFormOptional
from ...genders.models import Gender
from ...genders.tests.factories import GenderFactory
from ...labs.forms import BaselineCreatinineForm
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ...labs.models import BaselineCreatinine
from ...labs.tests.factories import BaselineCreatinineFactory
from ...medhistorydetails.choices import DialysisChoices, DialysisDurations, Stages
from ...medhistorys.tests.factories import CkdFactory
from ..forms import CkdDetailForm
from ..models import CkdDetail
from ..services import CkdDetailFormProcessor
from .factories import CkdDetailFactory

if TYPE_CHECKING:
    from ...medhistorys.models import Ckd


def setup_service(
    ckd: "Ckd",
    ckddetail_form: CkdDetailForm,
    baselinecreatinine_form: BaselineCreatinineForm,
    dateofbirth_form: DateOfBirthForm,
    gender_form: GenderForm,
) -> tuple[CkdDetailFormProcessor, bool]:
    """Helper method to setup a CkdDetailFormProcessor object and return it along with
    a boolean indicating whether any of the forms are invalid."""
    errors = False
    # Validate all the forms and set the errors boolean to True if any are invalid
    if (
        not ckddetail_form.is_valid()
        or not baselinecreatinine_form.is_valid()
        or not dateofbirth_form.is_valid()
        or not gender_form.is_valid()
    ):
        errors = True if errors is False else errors
    # Create a CkdDetailFormProcessor object
    service = CkdDetailFormProcessor(
        ckd=ckd,
        ckddetail_form=ckddetail_form,
        baselinecreatinine_form=baselinecreatinine_form,
        dateofbirth_form=dateofbirth_form,
        gender_form=gender_form,
    )
    return service, errors


class TestCkdProcessor(TestCase):
    def setUp(self):
        self.ckd = CkdFactory()
        self.baselinecreatinine = BaselineCreatinineFactory(medhistory=self.ckd, value=Decimal("1.0"))
        self.dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 20))
        self.gender = GenderFactory(value=Genders.FEMALE)
        self.ckddetail = CkdDetailFactory(
            medhistory=self.ckd,
            stage=labs_stage_calculator(
                labs_eGFR_calculator(
                    creatinine=self.baselinecreatinine.value,
                    age=age_calc(self.dateofbirth.value),
                    gender=self.gender,
                )
            ),
        )
        # Create some forms that can be modified in the tests
        self.ckddetail_form = CkdDetailForm(
            instance=self.ckddetail,
            data={
                "stage": self.ckddetail.stage,
                "dialysis": self.ckddetail.dialysis,
                "dialysis_type": self.ckddetail.dialysis_type,
                "dialysis_duration": self.ckddetail.dialysis_duration,
            },
        )
        self.baselinecreatinine_form = BaselineCreatinineForm(
            instance=self.baselinecreatinine, data={"baselinecreatinine-value": self.baselinecreatinine.value}
        )
        self.dateofbirth_form = DateOfBirthForm(
            instance=self.dateofbirth, data={"dateofbirth-value": age_calc(self.dateofbirth.value)}
        )
        self.gender_form = GenderForm(instance=self.gender, data={"gender-value": self.gender.value})
        self.service, errors = setup_service(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        self.assertFalse(errors)

    def test___init__(self):
        self.assertTrue(hasattr(self.service, "ckd"))
        self.assertTrue(hasattr(self.service, "ckddetail_form"))
        self.assertTrue(hasattr(self.service, "baselinecreatinine_form"))
        self.assertTrue(hasattr(self.service, "dateofbirth_form"))
        self.assertTrue(hasattr(self.service, "gender_form"))
        self.assertTrue(hasattr(self.service, "baselinecreatinine"))
        self.assertTrue(hasattr(self.service, "stage"))
        self.assertTrue(hasattr(self.service, "dialysis"))
        self.assertTrue(hasattr(self.service, "dialysis_type"))
        self.assertTrue(hasattr(self.service, "dialysis_duration"))
        self.assertTrue(hasattr(self.service, "dateofbirth"))
        self.assertTrue(hasattr(self.service, "gender"))
        self.assertEqual(getattr(self.service, "ckd"), self.ckd)
        self.assertEqual(getattr(self.service, "ckddetail_form"), self.ckddetail_form)
        self.assertEqual(getattr(self.service, "dialysis"), self.ckddetail_form.cleaned_data["dialysis"])
        self.assertEqual(getattr(self.service, "dialysis_type"), self.ckddetail_form.cleaned_data["dialysis_type"])
        self.assertEqual(
            getattr(self.service, "dialysis_duration"), self.ckddetail_form.cleaned_data["dialysis_duration"]
        )
        self.assertEqual(getattr(self.service, "stage"), self.ckddetail_form.cleaned_data["stage"])
        self.assertEqual(getattr(self.service, "baselinecreatinine_form"), self.baselinecreatinine_form)
        self.assertEqual(
            getattr(self.service, "baselinecreatinine"), self.baselinecreatinine_form.cleaned_data["value"]
        )
        self.assertEqual(getattr(self.service, "dateofbirth"), self.dateofbirth_form.cleaned_data["value"])
        self.assertEqual(getattr(self.service, "gender"), self.gender_form.cleaned_data["value"])

    def test__age(self):
        """Tests the age cached_property."""
        self.assertEqual(
            self.service.age,
            age_calc(self.service.dateofbirth),
        )

    def test__baselinecreatinine_initial(self):
        """Tests the baselinecreatinine_initial property."""
        self.assertTrue(isinstance(self.service.baselinecreatinine_initial, Decimal))
        self.assertEqual(
            self.service.baselinecreatinine_initial,
            self.baselinecreatinine_form.initial["value"],
        )

    def test__calculated_stage(self):
        """Tests the calculated_stage property."""
        self.assertEqual(
            self.service.calculated_stage,
            labs_stage_calculator(
                labs_eGFR_calculator(
                    creatinine=self.baselinecreatinine.value,
                    age=self.service.age,
                    gender=self.gender.value,
                )
            ),
        )
        # Change the value of an attr required for stage calculation
        # to None and check that the calculated_stage is None
        setattr(self.service, "baselinecreatinine", None)
        self.assertIsNone(self.service.calculated_stage)

    def test__changed_data(self):
        """Tests the changed_data property."""
        # Test base without any changed data returns False
        self.assertFalse(self.service.changed_data)
        # Test that changing the dialysis value returns True
        self.ckddetail_form = CkdDetailForm(
            instance=self.ckddetail,
            data={
                "stage": self.ckddetail.stage,
                "dialysis": True,
                "dialysis_type": DialysisChoices.PERITONEAL,
                "dialysis_duration": DialysisDurations.LESSTHANSIX,
            },
        )
        self.service, _ = setup_service(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        self.assertTrue(self.service.changed_data)
        # Test that changing the baselinecreatinine value returns True
        self.baselinecreatinine_form = BaselineCreatinineForm(
            instance=self.baselinecreatinine, data={"baselinecreatinine-value": Decimal("1.0")}
        )
        self.service, _ = setup_service(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        self.assertTrue(self.service.changed_data)
        # Test that removing the baselinecreatinine value returns True
        self.baselinecreatinine_form = BaselineCreatinineForm(
            instance=self.baselinecreatinine, data={"baselinecreatinine-value": ""}
        )
        self.service, _ = setup_service(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        self.assertTrue(self.service.changed_data)
        # Test that changing the stage value returns True
        self.ckddetail_form = CkdDetailForm(
            instance=self.ckddetail,
            data={
                "stage": [stage for stage in Stages.values if stage != self.ckddetail.stage][0],
                "dialysis": self.ckddetail.dialysis,
                "dialysis_type": self.ckddetail.dialysis_type,
                "dialysis_duration": self.ckddetail.dialysis_duration,
            },
        )
        self.service, _ = setup_service(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        self.assertTrue(self.service.changed_data)
        # Test that changing the dateofbirth value returns True
        self.dateofbirth_form = DateOfBirthForm(
            instance=self.dateofbirth,
            data={"dateofbirth-value": age_calc(timezone.now().date() - timedelta(days=365 * 20))},
        )
        self.service, _ = setup_service(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        self.assertTrue(self.service.changed_data)
        # Test that changing the gender value returns True
        self.gender_form = GenderForm(
            instance=self.gender,
            data={"gender-value": [gender for gender in Genders.values if gender != self.gender.value][0]},
        )
        self.service, _ = setup_service(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        self.assertTrue(self.service.changed_data)

    def test___check_process_returns(self):
        self.service._check_process_returns(
            ckddetailform=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
        )
        self.ckddetail_form.instance.to_delete = True
        with self.assertRaises(ValueError) as error:
            self.service._check_process_returns(
                ckddetailform=self.ckddetail_form,
                baselinecreatinine_form=self.baselinecreatinine_form,
            )
        self.assertEqual(
            error.exception.args[0],
            "If the CkdDetail is marked for deletion, the BaselineCreatinine should be as well.",
        )

    def test__ckddetail_bool(self):
        """Tests the ckddetail_bool property."""
        self.assertTrue(self.service.ckddetail_bool)
        self.ckddetail_form = CkdDetailForm(
            instance=self.ckddetail,
            data={
                "stage": "",
                "dialysis": "",
                "dialysis_type": "",
                "dialysis_duration": "",
            },
        )
        self.baselinecreatinine_form = BaselineCreatinineForm(
            instance=self.baselinecreatinine, data={"baselinecreatinine-value": ""}
        )
        self.service, _ = setup_service(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        self.assertFalse(self.service.ckddetail_bool)

    def test__check_for_errors(self):
        """Test teh check_for_errors method."""
        # TODO: Come back and write this test later.

    def test__delete_baselinecreatinine(self):
        """Test teh delete_baselinecreatinine method, whose job it is to
        mark a baselinecreatinine instance for deletion. In the process, it needs
        to check if the instance's non-nullable fields have been set to None and
        sets them back to their initial value."""
        self.baselinecreatinine_form.initial["value"] = Decimal("55.0")
        self.service.delete_baselinecreatinine(
            instance=self.baselinecreatinine,
            initial=self.baselinecreatinine_form.initial["value"],
        )
        self.assertTrue(hasattr(self.baselinecreatinine, "to_delete"))
        self.assertTrue(self.baselinecreatinine.to_delete)
        self.assertEqual(self.baselinecreatinine.value, Decimal("55.0"))
        self.assertTrue(hasattr(self.baselinecreatinine_form.instance, "to_delete"))
        self.assertTrue(self.baselinecreatinine_form.instance.to_delete)
        self.assertEqual(self.baselinecreatinine_form.instance.value, Decimal("55.0"))

    def test__get_stage(self):
        """Method to test the class method get_stage."""
        initial_stage = self.service.calculated_stage
        # Test that baseline method works, which should return the CkdDetail stage
        # because the stage and calculated_stage are the same
        gotten_stage = self.service.get_stage(
            dialysis=self.ckddetail.dialysis,
            stage=self.ckddetail.stage,
            calculated_stage=self.service.calculated_stage,
        )
        self.assertEqual(
            gotten_stage,
            self.ckddetail.stage,
        )
        self.assertEqual(
            gotten_stage,
            self.service.calculated_stage,
        )
        # Change the stage to None, modify baselinecreatinine value and test that
        # the calculated stage is returned
        self.ckddetail_form = CkdDetailForm(
            instance=self.ckddetail,
            data={
                "stage": "",
                "dialysis": False,
                "dialysis_type": "",
                "dialysis_duration": "",
            },
        )
        self.baselinecreatinine_form = BaselineCreatinineForm(
            instance=self.baselinecreatinine, data={"baselinecreatinine-value": Decimal("3.0")}
        )
        self.service, errors = setup_service(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        self.assertFalse(errors)
        gotten_stage = self.service.get_stage(
            dialysis=self.ckddetail.dialysis,
            stage=self.ckddetail.stage,
            calculated_stage=self.service.calculated_stage,
        )
        self.assertNotEqual(gotten_stage, initial_stage)
        self.assertEqual(
            gotten_stage,
            self.service.calculated_stage,
        )
        # Change the stage and dialysis to None, should return None
        self.ckddetail_form = CkdDetailForm(
            instance=self.ckddetail,
            data={
                "stage": "",
                "dialysis": "",
                "dialysis_type": "",
                "dialysis_duration": "",
            },
        )
        self.baselinecreatinine_form = BaselineCreatinineForm(
            instance=self.baselinecreatinine, data={"baselinecreatinine-value": ""}
        )
        self.service, errors = setup_service(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        self.assertFalse(errors)
        gotten_stage = self.service.get_stage(
            dialysis=self.ckddetail.dialysis,
            stage=self.ckddetail.stage,
            calculated_stage=self.service.calculated_stage,
        )
        self.assertIsNone(gotten_stage)
        # Test that dialysis True returns Stages.FIVE
        self.ckddetail_form = CkdDetailForm(
            instance=self.ckddetail,
            data={
                "stage": "",
                "dialysis": True,
                "dialysis_type": DialysisChoices.PERITONEAL,
                "dialysis_duration": DialysisDurations.LESSTHANSIX,
            },
        )
        self.service, errors = setup_service(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        self.assertFalse(errors)
        gotten_stage = self.service.get_stage(
            dialysis=self.ckddetail.dialysis,
            stage=self.ckddetail.stage,
            calculated_stage=self.service.calculated_stage,
        )
        self.assertEqual(gotten_stage, Stages.FIVE)
        # Test that ValueError is raised when there is a stage and calculated stage and
        # they are not the same
        self.ckddetail_form = CkdDetailForm(
            instance=self.ckddetail,
            data={
                "stage": Stages.ONE,
                "dialysis": False,
                "dialysis_type": "",
                "dialysis_duration": "",
            },
        )
        self.baselinecreatinine_form = BaselineCreatinineForm(
            instance=self.baselinecreatinine, data={"baselinecreatinine-value": Decimal("3.0")}
        )
        self.service, errors = setup_service(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        self.assertFalse(errors)
        with self.assertRaises(ValueError) as error:
            self.service.get_stage(
                dialysis=self.ckddetail.dialysis,
                stage=self.ckddetail.stage,
                calculated_stage=self.service.calculated_stage,
            )
        self.assertIn(
            "If there's a stage and a calculated_stage, they should be equal. \
Please double check and try again.",
            error.exception.args[0],
        )

    def test__process(self):
        """Method to test the process method."""
        # Test that process returns the forms unmodified because none of the data changed
        ckddetail_form, baselinecreatinine_form, errors = self.service.process()
        self.assertFalse(hasattr(ckddetail_form.instance, "to_delete"))
        self.assertFalse(hasattr(ckddetail_form.instance, "to_save"))
        self.assertFalse(hasattr(baselinecreatinine_form.instance, "to_delete"))
        self.assertFalse(hasattr(baselinecreatinine_form.instance, "to_save"))
        self.assertFalse(errors)
        # Test that process marks the BaselineCreatinine for deletion when the value is absent
        self.baselinecreatinine_form = BaselineCreatinineForm(
            instance=self.baselinecreatinine, data={"baselinecreatinine-value": ""}
        )
        self.service, errors = setup_service(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        ckddetail_form, baselinecreatinine_form, errors = self.service.process()
        self.assertFalse(hasattr(ckddetail_form.instance, "to_delete"))
        self.assertFalse(hasattr(ckddetail_form.instance, "to_save"))
        self.assertTrue(hasattr(baselinecreatinine_form.instance, "to_delete"))
        self.assertFalse(hasattr(baselinecreatinine_form.instance, "to_save"))
        # Test that process marks the CkdDetail for deletion when the stage and dialysis are absent
        # First delete the to_delete attr on the BaselineCreatinine instance
        delattr(baselinecreatinine_form.instance, "to_delete")
        self.assertFalse(hasattr(baselinecreatinine_form.instance, "to_delete"))
        self.ckddetail_form = CkdDetailForm(
            instance=self.ckddetail,
            data={
                "stage": "",
                "dialysis": "",
                "dialysis_type": "",
                "dialysis_duration": "",
            },
        )
        # Don't modify the baselinecreatinine_form, it already has an empty value
        self.service, errors = setup_service(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        ckddetail_form, baselinecreatinine_form, errors = self.service.process()
        self.assertTrue(hasattr(ckddetail_form.instance, "to_delete"))
        self.assertFalse(hasattr(ckddetail_form.instance, "to_save"))
        self.assertTrue(hasattr(baselinecreatinine_form.instance, "to_delete"))
        self.assertFalse(hasattr(baselinecreatinine_form.instance, "to_save"))
        # Test that process marks the CkdDetail to_save when the data (stage) is modified
        # First delete the to_delete attr on the CkdDetail instance
        delattr(ckddetail_form.instance, "to_delete")
        delattr(baselinecreatinine_form.instance, "to_delete")
        self.assertFalse(hasattr(ckddetail_form.instance, "to_delete"))
        self.assertFalse(hasattr(baselinecreatinine_form.instance, "to_delete"))
        self.ckddetail_form = CkdDetailForm(
            instance=self.ckddetail,
            data={
                # Elaborate way of picking a stage that isn't the current stage
                "stage": [stage for stage in Stages.values if stage != self.ckddetail.stage and stage is not None][0],
                "dialysis": False,
                "dialysis_type": "",
                "dialysis_duration": "",
            },
        )
        # Validate the CkdDetailForm
        self.assertTrue(self.ckddetail_form.is_valid())
        # Don't modify the baselinecreatinine_form, it already has an empty value
        self.service, errors = setup_service(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        ckddetail_form, baselinecreatinine_form, errors = self.service.process()
        self.assertFalse(hasattr(ckddetail_form.instance, "to_delete"))
        self.assertTrue(hasattr(ckddetail_form.instance, "to_save"))
        self.assertTrue(hasattr(baselinecreatinine_form.instance, "to_delete"))
        self.assertFalse(hasattr(baselinecreatinine_form.instance, "to_save"))
        # Test that the service marks the baselinecreatinine to_save when the value is modified
        # First delete the to_save attr on the ckddetail_form instance and the to_delete attr on the
        # baselinecreatinine_form instance
        delattr(ckddetail_form.instance, "to_save")
        delattr(baselinecreatinine_form.instance, "to_delete")
        self.assertFalse(hasattr(ckddetail_form.instance, "to_save"))
        self.assertFalse(hasattr(baselinecreatinine_form.instance, "to_delete"))
        # Set the new baselinecreatinine-value to a new value
        self.baselinecreatinine_form = BaselineCreatinineForm(
            instance=self.baselinecreatinine, data={"baselinecreatinine-value": Decimal("5.0")}
        )
        # Validate the BaselineCreatinineForm
        self.assertTrue(self.baselinecreatinine_form.is_valid())
        # Need to modify the CkdDetailForm's data empty value
        # Otherwise it will raise a ValidationError
        self.ckddetail_form = CkdDetailForm(
            instance=self.ckddetail,
            data={
                "stage": "",
                "dialysis": False,
                "dialysis_type": "",
                "dialysis_duration": "",
            },
        )
        # Validate the CkdDetailForm
        self.assertTrue(self.ckddetail_form.is_valid())
        self.service, errors = setup_service(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        ckddetail_form, baselinecreatinine_form, errors = self.service.process()
        self.assertFalse(errors)
        self.assertFalse(hasattr(ckddetail_form.instance, "to_delete"))
        self.assertTrue(hasattr(ckddetail_form.instance, "to_save"))
        self.assertFalse(hasattr(baselinecreatinine_form.instance, "to_delete"))
        self.assertTrue(hasattr(baselinecreatinine_form.instance, "to_save"))
        # Test that new CkdDetail is created when the ckddetail_form has a new instance
        # First, remove the to_delete attrs from the CkdDetail and BaselineCreatinine instances
        delattr(ckddetail_form.instance, "to_save")
        delattr(baselinecreatinine_form.instance, "to_save")
        # Create a new CkdDetailForm with a new instance
        self.ckddetail_form = CkdDetailForm(
            instance=CkdDetail(),
            data={
                "stage": Stages.FOUR,
                "dialysis": False,
                "dialysis_type": "",
                "dialysis_duration": "",
            },
        )
        # Run is_is_valid() method on the CkdDetailForm
        self.assertTrue(self.ckddetail_form.is_valid())
        self.baselinecreatinine_form = BaselineCreatinineForm(
            instance=BaselineCreatinine(), data={"baselinecreatinine-value": ""}
        )
        # Run is_is_valid() method on the BaselineCreatinineForm
        self.assertTrue(self.baselinecreatinine_form.is_valid())
        # Set up the service with a new Ckd object to avoid IntegrityError when saving new CkdDetail
        self.service, errors = setup_service(
            ckd=CkdFactory(),
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        ckddetail_form, baselinecreatinine_form, errors = self.service.process()
        # Assert that the CkdDetailForm instance is marked for saving
        self.assertTrue(hasattr(ckddetail_form.instance, "to_save"))
        self.assertFalse(hasattr(ckddetail_form.instance, "to_delete"))
        # Assert that the BaselineCreatinineForm instance is unmarked
        self.assertFalse(hasattr(baselinecreatinine_form.instance, "to_save"))
        self.assertFalse(hasattr(baselinecreatinine_form.instance, "to_delete"))
        # Test that new BaselineCreatinine is created when the baselinecreatinine_form has a new instance
        # First, remove the to_save attrs from the CkdDetail
        delattr(ckddetail_form.instance, "to_save")
        # Create a new BaselineCreatinineForm with a new instance
        self.baselinecreatinine_form = BaselineCreatinineForm(
            instance=BaselineCreatinine(), data={"baselinecreatinine-value": Decimal("3.0")}
        )
        # Run is_is_valid() method on the BaselineCreatinineForm
        self.assertTrue(self.baselinecreatinine_form.is_valid())
        # Set up the service with a new Ckd object to avoid IntegrityError when saving new BaselineCreatinine
        self.service, errors = setup_service(
            ckd=CkdFactory(),
            ckddetail_form=ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        ckddetail_form, baselinecreatinine_form, errors = self.service.process()
        # Assert that the CkdDetailForm instance is marked to_save
        self.assertTrue(hasattr(ckddetail_form.instance, "to_save"))
        self.assertFalse(hasattr(ckddetail_form.instance, "to_delete"))
        # Assert that the BaselineCreatinineForm instance is marked to_save
        self.assertTrue(hasattr(baselinecreatinine_form.instance, "to_save"))
        self.assertFalse(hasattr(baselinecreatinine_form.instance, "to_delete"))

    def test__set_ckd_fields(self):
        """Method to test the set_ckd_fields method."""
        # Set the attrs to be changed to None
        self.ckddetail_form.instance.stage = None
        self.ckddetail_form.instance.medhistory = None
        self.ckddetail_form.instance._state.adding = True
        self.assertIsNone(self.ckddetail_form.instance.stage)
        self.assertFalse(hasattr(self.ckddetail_form.instance, "to_save"))
        # NOTE: Can't check that medhistory doesn't exist because it's non-nullable
        # and this will raise a RelatedObjectDoesNotExist exception
        self.assertIsNone(
            self.service.set_ckd_fields(
                ckddetail_form=self.ckddetail_form,
                stage=self.ckddetail_form.cleaned_data["stage"],
                ckd=self.ckd,
            )
        )
        # Assert that the attrs changed back
        self.assertEqual(self.ckddetail_form.instance.stage, self.ckddetail_form.cleaned_data["stage"])
        self.assertEqual(self.ckddetail_form.instance.medhistory, self.ckd)
        self.assertTrue(self.ckddetail_form.instance.to_save)

    def test__set_baselinecreatinine(self):
        """Method to test the set_baselinecreatinine method."""
        # Test the method with nothing changed
        form = self.service.set_baselinecreatinine(
            ckddetail_bool=self.service.ckddetail_bool,
            baselinecreatinine_form=self.baselinecreatinine_form,
            initial=self.service.baselinecreatinine_initial,
            dialysis=self.ckddetail_form.cleaned_data["dialysis"],
        )
        self.assertTrue(isinstance(form, BaselineCreatinineForm))
        self.assertTrue(form.instance)
        # Assert that the original value and the cleaned data are the same
        self.assertEqual(form.instance.value, self.baselinecreatinine_form.cleaned_data["value"])
        self.assertFalse(hasattr(form.instance, "to_delete"))
        self.assertFalse(hasattr(form.instance, "to_save"))
        # Test the method with a new baselinecreatinine value
        self.baselinecreatinine_form = BaselineCreatinineForm(
            instance=self.baselinecreatinine, data={"baselinecreatinine-value": Decimal("3.0")}
        )
        # Run is_is_valid() method on the BaselineCreatinineForm
        self.assertTrue(self.baselinecreatinine_form.is_valid())
        form = self.service.set_baselinecreatinine(
            ckddetail_bool=self.service.ckddetail_bool,
            baselinecreatinine_form=self.baselinecreatinine_form,
            initial=self.service.baselinecreatinine_initial,
            dialysis=self.ckddetail_form.cleaned_data["dialysis"],
        )
        # Assert that the original value and the cleaned data are not the same
        self.assertNotEqual(form.instance.value, self.service.baselinecreatinine_initial)
        self.assertFalse(hasattr(form.instance, "to_delete"))
        self.assertTrue(hasattr(form.instance, "to_save"))
        # Test the method setting the baselinecreatinine to_delete to True
        # Delete the last to_save attr on the instance
        delattr(form.instance, "to_save")
        self.baselinecreatinine_form = BaselineCreatinineForm(
            instance=self.baselinecreatinine, data={"baselinecreatinine-value": ""}
        )
        # Run is_is_valid() method on the BaselineCreatinineForm
        self.assertTrue(self.baselinecreatinine_form.is_valid())
        form = self.service.set_baselinecreatinine(
            ckddetail_bool=self.service.ckddetail_bool,
            baselinecreatinine_form=self.baselinecreatinine_form,
            initial=self.service.baselinecreatinine_initial,
            dialysis=self.ckddetail_form.cleaned_data["dialysis"],
        )
        # Assert that the original value and the cleaned data ARE the same
        # This will have been reset by the delete_baselinecreatinine method
        # to avoid nulling a non-nullable field
        self.assertEqual(form.instance.value, self.service.baselinecreatinine_initial)
        self.assertTrue(hasattr(form.instance, "to_delete"))
        self.assertFalse(hasattr(form.instance, "to_save"))
        # Test that the method turns to_delete to True when the dialysis value is True
        # First delete the to_delete attr on the instance
        delattr(form.instance, "to_delete")
        self.assertFalse(hasattr(form.instance, "to_delete"))
        # Change the dialysis value to True in CkdForm
        self.ckddetail_form = CkdDetailForm(
            instance=self.ckddetail,
            data={
                "stage": "",
                "dialysis": True,
                "dialysis_type": DialysisChoices.PERITONEAL,
                "dialysis_duration": DialysisDurations.LESSTHANSIX,
            },
        )
        # re-validate the CkdDetailForm
        self.assertTrue(self.ckddetail_form.is_valid())
        form = self.service.set_baselinecreatinine(
            ckddetail_bool=self.service.ckddetail_bool,
            baselinecreatinine_form=self.baselinecreatinine_form,
            initial=self.service.baselinecreatinine_initial,
            dialysis=self.ckddetail_form.cleaned_data["dialysis"],
        )
        # Assert that the to_delete attr is True
        self.assertTrue(hasattr(form.instance, "to_delete"))
        # Test that the baselinecreatinine is marked for deletion when ckddetail_bool is False
        # First delete the to_delete attr on the instance
        delattr(form.instance, "to_delete")
        self.assertFalse(hasattr(form.instance, "to_delete"))
        form = self.service.set_baselinecreatinine(
            ckddetail_bool=False,
            baselinecreatinine_form=self.baselinecreatinine_form,
            initial=self.service.baselinecreatinine_initial,
            dialysis=self.ckddetail_form.cleaned_data["dialysis"],
        )
        self.assertTrue(hasattr(form.instance, "to_delete"))
        # Test that the method creates a new BaselineCreatinine instance when
        # there is no initial BaselineCreatinine instance but there is a value
        # in the BaselineCreatinineForm
        # First, delete the BaselineCreatinine instance
        self.baselinecreatinine.delete()
        self.assertFalse(BaselineCreatinine.objects.filter(pk=self.baselinecreatinine.pk).exists())
        # Create a new BaselineCreatinineForm with a value
        self.baselinecreatinine_form = BaselineCreatinineForm(
            instance=BaselineCreatinine(), data={"baselinecreatinine-value": Decimal("3.0")}
        )
        # Run is_is_valid() method on the BaselineCreatinineForm
        self.assertTrue(self.baselinecreatinine_form.is_valid())
        form = self.service.set_baselinecreatinine(
            ckddetail_bool=self.service.ckddetail_bool,
            baselinecreatinine_form=self.baselinecreatinine_form,
            initial=self.service.baselinecreatinine_initial,
            dialysis=self.ckddetail_form.cleaned_data["dialysis"],
        )
        self.assertFalse(hasattr(form.instance, "to_delete"))
        self.assertTrue(hasattr(form.instance, "to_save"))
        # Test that the method doesn't add any attrs when ckddetail_bool is False
        # Delete the to_save attr on the instance
        delattr(form.instance, "to_save")
        form = self.service.set_baselinecreatinine(
            ckddetail_bool=False,
            baselinecreatinine_form=self.baselinecreatinine_form,
            initial=self.service.baselinecreatinine_initial,
            dialysis=self.ckddetail_form.cleaned_data["dialysis"],
        )
        self.assertFalse(hasattr(form.instance, "to_delete"))
        self.assertFalse(hasattr(form.instance, "to_save"))


class TestCkdProcessorCheckForErrors(TestCase):
    """Test suite for the CkdProcessor.check_for_errors method."""

    def setUp(self):
        self.ckd = CkdFactory()
        # Create empty CkdDetailForm and BaselineCreatinineForm
        self.ckddetail_form = CkdDetailForm(instance=CkdDetail(), data={})
        self.baselinecreatinine_form = BaselineCreatinineForm(instance=BaselineCreatinine(), data={})
        # Create a DateOfBirthForm and GenderForm
        self.dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=365 * 20))
        self.dateofbirth_form = DateOfBirthForm(
            instance=self.dateofbirth, data={"dateofbirth-value": age_calc(self.dateofbirth.value)}
        )
        self.gender = GenderFactory()
        self.gender_form = GenderForm(instance=self.gender, data={"gender-value": self.gender.value})

    def test__empty_forms_return_no_errors(self):
        service, errors = setup_service(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        self.assertFalse(errors)
        self.assertFalse(service.check_for_errors())

    def test__dialysis_empty_baselinecreatinine_errors(self):
        self.baselinecreatinine_form = BaselineCreatinineForm(
            instance=BaselineCreatinine(), data={"baselinecreatinine-value": Decimal("3.0")}
        )
        service, errors = setup_service(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        self.assertFalse(errors)
        self.assertTrue(service.check_for_errors())
        self.assertTrue(self.baselinecreatinine_form.errors)
        self.assertTrue(self.ckddetail_form.errors)
        self.assertIn("value", self.baselinecreatinine_form.errors)
        self.assertIn("dialysis", self.ckddetail_form.errors)
        self.assertEqual(
            self.baselinecreatinine_form.errors["value"],
            ["If dialysis is not checked, there should be no baseline creatinine."],
        )
        self.assertEqual(
            self.ckddetail_form.errors["dialysis"],
            ["If dialysis is not checked, there should be no baseline creatinine."],
        )

    def test__dialysis_False_age_missing(self):
        self.dateofbirth_form = DateOfBirthFormOptional(instance=DateOfBirth(), data={})
        self.baselinecreatinine_form = BaselineCreatinineForm(
            instance=BaselineCreatinine(), data={"baselinecreatinine-value": Decimal("3.0")}
        )
        self.ckddetail_form = CkdDetailForm(
            instance=CkdDetail(),
            data={
                "stage": "",
                "dialysis": False,
                "dialysis_type": "",
                "dialysis_duration": "",
            },
        )
        # Validate the forms
        self.assertTrue(self.dateofbirth_form.is_valid())
        self.assertTrue(self.baselinecreatinine_form.is_valid())
        self.assertTrue(self.ckddetail_form.is_valid())
        # Set up the service
        service, errors = setup_service(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        self.assertFalse(errors)
        self.assertTrue(service.check_for_errors())
        self.assertTrue(self.dateofbirth_form.errors)
        self.assertTrue(self.baselinecreatinine_form.errors)
        self.assertIn("value", self.dateofbirth_form.errors)
        self.assertIn("value", self.baselinecreatinine_form.errors)
        self.assertEqual(
            self.dateofbirth_form.errors["value"],
            [
                "Age is required to interpret a baseline creatinine (calculate a stage). \
Please double check and try again."
            ],
        )
        self.assertEqual(
            self.baselinecreatinine_form.errors["value"],
            [
                "Age is required to interpret a baseline creatinine (calculate a stage). \
Please double check and try again."
            ],
        )

    def test__dialysis_False_gender_missing(self):
        self.gender_form = GenderFormOptional(instance=Gender(), data={})
        self.baselinecreatinine_form = BaselineCreatinineForm(
            instance=BaselineCreatinine(), data={"baselinecreatinine-value": Decimal("3.0")}
        )
        self.ckddetail_form = CkdDetailForm(
            instance=CkdDetail(),
            data={
                "stage": "",
                "dialysis": False,
                "dialysis_type": "",
                "dialysis_duration": "",
            },
        )
        # Validate the forms
        self.assertTrue(self.gender_form.is_valid())
        self.assertTrue(self.baselinecreatinine_form.is_valid())
        self.assertTrue(self.ckddetail_form.is_valid())
        # Set up the service
        service, errors = setup_service(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        self.assertFalse(errors)
        self.assertTrue(service.check_for_errors())
        self.assertTrue(self.gender_form.errors)
        self.assertTrue(self.baselinecreatinine_form.errors)
        self.assertIn("value", self.gender_form.errors)
        self.assertIn("value", self.baselinecreatinine_form.errors)
        self.assertEqual(
            self.gender_form.errors["value"],
            [
                "Gender is required to interpret a baseline creatinine (calculate a stage). \
Please double check and try again."
            ],
        )
        self.assertEqual(
            self.baselinecreatinine_form.errors["value"],
            [
                "Gender is required to interpret a baseline creatinine (calculate a stage). \
Please double check and try again."
            ],
        )

    def test__dialysis_False_gender_and_dateofbirth_missing(self):
        self.dateofbirth_form = DateOfBirthFormOptional(instance=DateOfBirth(), data={})
        self.gender_form = GenderFormOptional(instance=Gender(), data={})
        self.baselinecreatinine_form = BaselineCreatinineForm(
            instance=BaselineCreatinine(), data={"baselinecreatinine-value": Decimal("3.0")}
        )
        self.ckddetail_form = CkdDetailForm(
            instance=CkdDetail(),
            data={
                "stage": "",
                "dialysis": False,
                "dialysis_type": "",
                "dialysis_duration": "",
            },
        )
        # Validate the forms
        self.assertTrue(self.dateofbirth_form.is_valid())
        self.assertTrue(self.gender_form.is_valid())
        self.assertTrue(self.baselinecreatinine_form.is_valid())
        self.assertTrue(self.ckddetail_form.is_valid())
        # Set up the service
        service, errors = setup_service(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        self.assertFalse(errors)
        self.assertTrue(service.check_for_errors())
        self.assertTrue(self.dateofbirth_form.errors)
        self.assertTrue(self.gender_form.errors)
        self.assertTrue(self.baselinecreatinine_form.errors)
        self.assertIn("value", self.dateofbirth_form.errors)
        self.assertIn("value", self.gender_form.errors)
        self.assertIn("value", self.baselinecreatinine_form.errors)
        self.assertEqual(
            self.dateofbirth_form.errors["value"],
            [
                "Age and gender are required to interpret a baseline creatinine (calculate a stage). \
Please double check and try again."
            ],
        )
        self.assertEqual(
            self.gender_form.errors["value"],
            [
                "Age and gender are required to interpret a baseline creatinine (calculate a stage). \
Please double check and try again."
            ],
        )
        self.assertEqual(
            self.baselinecreatinine_form.errors["value"],
            [
                "Age and gender are required to interpret a baseline creatinine (calculate a stage). \
Please double check and try again."
            ],
        )

    def test__dialysis_False_stage_and_calculated_stage_not_equal(self):
        # Adjust the ckddetail_form and baselinecreatinine_form to result in different stages
        self.ckddetail_form = CkdDetailForm(
            instance=CkdDetail(),
            data={
                "stage": Stages.ONE,
                "dialysis": False,
                "dialysis_type": "",
                "dialysis_duration": "",
            },
        )
        self.baselinecreatinine_form = BaselineCreatinineForm(
            instance=BaselineCreatinine(), data={"baselinecreatinine-value": Decimal("4.0")}
        )
        # Validate the forms
        self.assertTrue(self.ckddetail_form.is_valid())
        self.assertTrue(self.baselinecreatinine_form.is_valid())
        # Set up the service
        service, errors = setup_service(
            ckd=self.ckd,
            ckddetail_form=self.ckddetail_form,
            baselinecreatinine_form=self.baselinecreatinine_form,
            dateofbirth_form=self.dateofbirth_form,
            gender_form=self.gender_form,
        )
        self.assertFalse(errors)
        self.assertTrue(service.check_for_errors())
        self.assertTrue(self.ckddetail_form.errors)
        self.assertTrue(self.baselinecreatinine_form.errors)
        self.assertIn("stage", self.ckddetail_form.errors)
        self.assertIn("value", self.baselinecreatinine_form.errors)
        self.assertIn(
            "baseline creatinine, age, and gender does not match the selected stage",
            self.baselinecreatinine_form.errors["value"][0],
        )
        self.assertIn(
            "calculated from the baseline creatinine, age, and gender.",
            self.ckddetail_form.errors["stage"][0],
        )
