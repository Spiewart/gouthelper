from datetime import timedelta
from decimal import Decimal

from django.db import connection
from django.db.models import QuerySet  # type: ignore
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore
from django.utils import timezone  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...genders.choices import Genders
from ...genders.tests.factories import GenderFactory
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ...labs.tests.factories import BaselineCreatinineFactory
from ...medhistorydetails.models import GoutDetail
from ...medhistorys.models import Ckd
from ...medhistorys.tests.factories import CkdFactory, GoutFactory
from ...users.choices import Roles
from ...users.tests.factories import UserFactory, create_psp
from ...utils.exceptions import GoutHelperValidationError
from ..api.mixins import CkdDetailAPIMixin
from ..api.services import GoutDetailAPI
from ..choices import DialysisChoices, DialysisDurations, Stages
from ..models import CkdDetail
from .factories import CkdDetailDataFactory, CkdDetailFactory, GoutDetailFactory, create_ckddetail


def set_mixin_attr(mixin: CkdDetailAPIMixin, **kwargs):
    for key, value in kwargs.items():
        setattr(mixin, key, value)


def prep_mixin_attrs_for_create(mixin_attrs: dict) -> None:
    """Prepare the mixin for creating a CkdDetail instance."""
    mixin_attrs.update(
        {
            "ckddetail": None,
            "ckddetail__medhistory": CkdFactory(),
        }
    )


class TestCkdDetailAPIMixin(TestCase):
    """Test suite for the CkdDetailCreator class."""

    def setUp(self):
        self.data = CkdDetailDataFactory().create_api_data()
        self.api = CkdDetailAPIMixin()
        self.ckd = CkdFactory()
        self.ckddetail = create_ckddetail(medhistory=self.ckd, dialysis=False)
        self.patient = create_psp()
        self.ckddetail__dialysis = self.ckddetail.dialysis
        self.ckddetail__dialysis_type = self.ckddetail.dialysis_type
        self.ckddetail__dialysis_duration = self.ckddetail.dialysis_duration
        self.dateofbirth = DateOfBirthFactory(value=timezone.now() - timedelta(days=50 * 365))
        self.gender = GenderFactory(value=Genders.MALE)
        self.baselinecreatinine = BaselineCreatinineFactory(value=Decimal("1.5"))
        self.ckddetail__stage = labs_stage_calculator(
            labs_eGFR_calculator(
                age=age_calc(self.dateofbirth.value),
                gender=self.gender.value,
                creatinine=self.baselinecreatinine.value,
            )
        )
        self.api_attrs = {
            "ckddetail__medhistory": self.ckd,
            "ckddetail": self.ckddetail,
            "ckddetail__dialysis": self.ckddetail__dialysis,
            "ckddetail__dialysis_type": self.ckddetail__dialysis_type,
            "ckddetail__dialysis_duration": self.ckddetail__dialysis_duration,
            "ckddetail__stage": self.ckddetail__stage,
            "dateofbirth": self.dateofbirth,
            "gender": self.gender,
            "baselinecreatinine": self.baselinecreatinine,
        }

    def test__ckd_ckddetail_conflict(self):
        ckd = CkdDetailFactory(medhistory=CkdFactory()).medhistory
        self.api_attrs.update(
            {
                "ckddetail__medhistory": ckd,
            }
        )
        set_mixin_attr(self.api, **self.api_attrs)
        self.assertTrue(self.api.ckd_ckddetail_conflict)

    def test__incomplete_info(self):
        self.api_attrs.update(
            {
                "ckddetail__dialysis": None,
                "ckddetail__stage": None,
                "baselinecreatinine": None,
            }
        )
        set_mixin_attr(self.api, **self.api_attrs)
        self.assertTrue(self.api.incomplete_info)

    def test__can_calculate_stage(self):
        self.api_attrs.update({"baselinecreatinine": None})
        set_mixin_attr(self.api, **self.api_attrs)
        self.assertFalse(self.api.can_calculate_stage)
        self.api_attrs.update({"baselinecreatinine": Decimal("1.5")})
        set_mixin_attr(self.api, **self.api_attrs)
        self.assertTrue(self.api.can_calculate_stage)

    def test__calculate_stage(self):
        self.data.update({"age": 50, "gender": Genders.MALE, "baselinecreatinine": Decimal("1.5")})
        self.api_attrs.update(
            {
                "dateofbirth": DateOfBirthFactory(value=timezone.now() - timedelta(days=50 * 365)),
                "gender": GenderFactory(value=Genders.MALE),
                "baselinecreatinine": BaselineCreatinineFactory(value=Decimal("1.5")),
            }
        )
        set_mixin_attr(self.api, **self.api_attrs)
        self.assertEqual(
            self.api.calculated_stage,
            labs_stage_calculator(
                labs_eGFR_calculator(
                    age=50,
                    gender=Genders.MALE,
                    creatinine=Decimal("1.5"),
                )
            ),
        )

    def test__stage_calculated_stage_conflict_no_stage(self):
        """Test when stage is None."""
        self.api_attrs.update(
            {
                "ckddetail__stage": None,
            }
        )
        set_mixin_attr(self.api, **self.api_attrs)
        self.assertFalse(self.api.stage_calculated_stage_conflict)

    def test__stage_calculated_stage_conflict_cannot_calculate_stage(self):
        """Test when can_calculate_stage is False."""
        self.api_attrs.update({"dateofbirth": None})
        set_mixin_attr(self.api, **self.api_attrs)
        self.assertFalse(self.api.stage_calculated_stage_conflict)

    def test__stage_calculated_stage_conflict_stage_matches(self):
        """Test when calculated stage matches the given stage."""
        set_mixin_attr(self.api, **self.api_attrs)
        self.assertFalse(self.api.stage_calculated_stage_conflict)

    def test__stage_calculated_stage_conflict_stage_does_not_match(self):
        """Test when calculated stage does not match the given stage."""
        self.api_attrs.update(
            {"baselinecreatinine": BaselineCreatinineFactory(value=Decimal("3.5")), "ckddetail__stage": Stages.ONE}
        )
        set_mixin_attr(self.api, **self.api_attrs)
        self.assertTrue(self.api.stage_calculated_stage_conflict)

    def test__dialysis_stage_conflict_no_dialysis(self):
        """Test when dialysis is False."""

        self.assertFalse(self.ckddetail.dialysis)
        set_mixin_attr(self.api, **self.api_attrs)
        self.assertFalse(self.api.dialysis_stage_conflict)

    def test__dialysis_stage_conflict_stage_not_five(self):
        """Test when dialysis is True and stage is not FIVE."""

        self.api_attrs.update({"ckddetail__dialysis": True, "ckddetail__stage": Stages.FOUR})
        set_mixin_attr(self.api, **self.api_attrs)
        self.assertTrue(self.api.dialysis_stage_conflict)

    def test__dialysis_stage_conflict_stage_five(self):
        """Test when dialysis is True and stage is FIVE."""

        self.api_attrs.update({"ckddetail__dialysis": True, "ckddetail__stage": Stages.FIVE})
        set_mixin_attr(self.api, **self.api_attrs)
        self.assertFalse(self.api.dialysis_stage_conflict)

    def test__dialysis_stage_conflict_calculated_stage_not_five(self):
        """Test when dialysis is True, can calculate stage, and calculated stage is not FIVE."""

        self.api_attrs.update({"ckddetail__dialysis": True, "ckddetail__stage": Stages.FOUR})
        set_mixin_attr(self.api, **self.api_attrs)
        self.assertTrue(self.api.dialysis_stage_conflict)

    def test__dialysis_stage_conflict_calculated_stage_five(self):
        """Test when dialysis is True, can calculate stage, and calculated stage is FIVE."""

        self.api_attrs.update(
            {
                "ckddetail__dialysis": True,
                "ckddetail__stage": None,
                "baselinecreatinine": BaselineCreatinineFactory(value=Decimal("6.0")),
            }
        )
        set_mixin_attr(self.api, **self.api_attrs)
        self.assertFalse(self.api.dialysis_stage_conflict)

    def test__dialysis_type_conflict_no_dialysis(self):
        """Test when dialysis is False."""

        self.data["dialysis"] = False
        self.data["dialysis_type"] = None
        self.api_attrs.update({"ckddetail__dialysis": False, "ckddetail__dialysis_type": None})
        set_mixin_attr(self.api, **self.api_attrs)
        self.assertFalse(self.api.dialysis_type_conflict)

    def test__dialysis_type_conflict_dialysis_no_type(self):
        """Test when dialysis is True and dialysis_type is None."""

        self.api_attrs.update({"ckddetail__dialysis": True, "ckddetail__dialysis_type": None})
        set_mixin_attr(self.api, **self.api_attrs)
        self.assertTrue(self.api.dialysis_type_conflict)

    def test__dialysis_type_conflict_dialysis_with_type(self):
        """Test when dialysis is True and dialysis_type is provided."""

        self.api_attrs.update({"ckddetail__dialysis": True, "ckddetail__dialysis_type": DialysisChoices.PERITONEAL})
        set_mixin_attr(self.api, **self.api_attrs)
        self.assertFalse(self.api.dialysis_type_conflict)

    def test__dialysis_duration_conflict_no_dialysis(self):
        """Test when dialysis is False."""

        self.api_attrs.update({"ckddetail__dialysis": False, "ckddetail__dialysis_duration": None})
        set_mixin_attr(self.api, **self.api_attrs)
        self.assertFalse(self.api.dialysis_duration_conflict)

    def test__dialysis_duration_conflict_dialysis_no_duration(self):
        """Test when dialysis is True and dialysis_duration is None."""

        self.api_attrs.update({"ckddetail__dialysis": True, "ckddetail__dialysis_duration": None})
        set_mixin_attr(self.api, **self.api_attrs)
        self.assertTrue(self.api.dialysis_duration_conflict)

    def test__dialysis_duration_conflict_dialysis_with_duration(self):
        """Test when dialysis is True and dialysis_duration is provided."""

        self.api_attrs.update(
            {"ckddetail__dialysis": True, "ckddetail__dialysis_duration": DialysisDurations.LESSTHANSIX}
        )
        set_mixin_attr(self.api, **self.api_attrs)
        self.assertFalse(self.api.dialysis_duration_conflict)

    def test__baselinecreatinine_age_gender_conflict_no_baselinecreatinine(self):
        """Test when baselinecreatinine is None."""

        self.api_attrs.update({"baselinecreatinine": None})
        set_mixin_attr(self.api, **self.api_attrs)
        self.assertFalse(self.api.baselinecreatinine_age_gender_conflict)

    def test__baselinecreatinine_age_gender_conflict_can_calculate_stage(self):
        """Test when can_calculate_stage is True."""

        set_mixin_attr(self.api, **self.api_attrs)
        self.assertFalse(self.api.baselinecreatinine_age_gender_conflict)

    def test__baselinecreatinine_age_gender_conflict_cannot_calculate_stage(self):
        """Test when can_calculate_stage is False."""

        self.api_attrs.update(
            {
                "dateofbirth": None,
            }
        )
        set_mixin_attr(self.api, **self.api_attrs)
        self.assertTrue(self.api.baselinecreatinine_age_gender_conflict)

    def test__create_ckddetail(self):
        """Test successful creation of CkdDetail."""

        prep_mixin_attrs_for_create(self.api_attrs)
        set_mixin_attr(self.api, **self.api_attrs)
        ckddetail = self.api.create_ckddetail()
        self.assertIsInstance(ckddetail, CkdDetail)
        self.assertEqual(ckddetail.dialysis, self.ckddetail__dialysis)
        self.assertEqual(ckddetail.dialysis_type, self.ckddetail__dialysis_type)
        self.assertEqual(ckddetail.dialysis_duration, self.ckddetail__dialysis_duration)
        self.assertEqual(ckddetail.stage, self.ckddetail__stage)
        self.assertTrue(isinstance(ckddetail.medhistory, Ckd))

    def test_create_ckddetail_already_exists(self):
        """Test creation when CkdDetail instance already exists."""

        set_mixin_attr(self.api, **self.api_attrs)

        with self.assertRaises(GoutHelperValidationError):
            self.api.create_ckddetail()
        self.assertTrue(self.api.errors)
        self.assertIn(("ckddetail", f"{self.ckddetail} already exists."), self.api.errors)

    def test_create_no_ckd_instance(self):
        """Test creation when no Ckd instance is provided."""
        self.create_editor.ckddetail = None
        self.create_editor.ckd = None
        with self.assertRaises(ValueError) as context:
            self.create_editor.create()
        self.assertEqual(str(context.exception), "Ckd instance required for CkdDetail creation.")

    def test_create_with_dialysis_but_no_type(self):
        """Test that there is a validation error due to dialysis being True but there being no dialysis_type."""
        self.create_editor.ckddetail = None
        self.create_editor.dialysis_type = None  # This will cause an error
        with self.assertRaises(GoutHelperValidationError) as context:
            self.create_editor.create()
        self.assertIn("Args for creating CkdDetail contain errors", str(context.exception))
        self.assertTrue(self.create_editor.errors)
        self.assertIn("dialysis_type", [tup[0] for tup in self.create_editor.errors])

    def test_create_with_dialysis_but_no_duration(self):
        """Test that there is a validation error due to dialysis being True but there being no dialysis_duration."""
        self.create_editor.ckddetail = None
        self.create_editor.dialysis_duration = None  # This will cause an error
        with self.assertRaises(GoutHelperValidationError) as context:
            self.create_editor.create()
        self.assertIn("Args for creating CkdDetail contain errors", str(context.exception))
        self.assertTrue(self.create_editor.errors)
        self.assertIn("dialysis_duration", [tup[0] for tup in self.create_editor.errors])

    def test_create_without_stage_but_can_calculate_stage(self):
        """Test that the stage is updated by _update_attrs during creation and set on the created object."""
        self.create_editor.ckddetail = None
        self.create_editor.dialysis = None
        self.create_editor.stage = None
        self.create_editor.baselinecreatinine = Decimal("1.5")
        self.create_editor.age = 50
        self.create_editor.gender = Genders.MALE
        created_ckddetail = self.create_editor.create()
        self.assertEqual(
            created_ckddetail.stage,
            labs_stage_calculator(
                labs_eGFR_calculator(
                    age=50,
                    creatinine=Decimal("1.5"),
                    gender=Genders.MALE,
                )
            ),
        )

    def test_create_with_dialysis_can_calculcate_stage_but_wont(self):
        """Test that _update_attrs is called during creation."""
        self.create_editor.ckddetail = None
        self.create_editor.dialysis = True
        self.create_editor.stage = None
        self.create_editor.baselinecreatinine = Decimal("1.5")
        self.create_editor.age = 50
        self.create_editor.gender = Genders.MALE
        created_ckddetail = self.create_editor.create()
        self.assertEqual(
            created_ckddetail.stage,
            Stages.FIVE,
        )


class TestCkdDetailUpdater(TestCase):
    def setUp(self):
        self.ckddetail = create_ckddetail(dialysis=False, medhistory=CkdFactory())
        self.ckddetail_dialysis = True
        self.ckddetail__dialysis_type = DialysisChoices.HEMODIALYSIS
        self.ckddetail__dialysis_duration = DialysisDurations.LESSTHANSIX
        self.ckddetail__stage = Stages.FIVE
        self.age = 45
        self.baselinecreatinine = Decimal("1.2")
        self.gender = Genders.MALE
        self.initial = {
            "dialysis": self.ckddetail.dialysis,
            "dialysis_type": self.ckddetail.dialysis_type,
            "dialysis_duration": self.ckddetail.dialysis_duration,
            "stage": self.ckddetail.stage,
        }

    def test_check_ckddetail_initial_error_no_conflict(self):
        """Test when there is no conflict between ckddetail and initial values."""
        try:
            self.update_editor.check_ckddetail_initial_error()
        except ValueError:
            self.fail("check_ckddetail_initial_error() raised ValueError unexpectedly!")

    def test_check_ckddetail_initial_error_with_conflict(self):
        """Test when there is a conflict between ckddetail and initial values."""
        self.update_editor.initial["dialysis"] = not self.ckddetail.dialysis  # Intentionally setting a different value
        with self.assertRaises(ValueError) as context:
            self.update_editor.check_ckddetail_initial_error()
        self.assertEqual(str(context.exception), "Initial values do not match CkdDetail instance values.")

    def test_check_ckddetail_initial_error_no_ckddetail(self):
        """Test when ckddetail is None."""
        self.update_editor.ckddetail = None
        try:
            self.update_editor.check_ckddetail_initial_error()
        except ValueError:
            self.fail("check_ckddetail_initial_error() raised ValueError unexpectedly!")

    def test_check_ckddetail_initial_error_no_initial(self):
        """Test when initial is None."""
        self.update_editor.initial = None
        try:
            self.update_editor.check_ckddetail_initial_error()
        except ValueError:
            self.fail("check_ckddetail_initial_error() raised ValueError unexpectedly!")

    def test_ckddetail_initial_conflict_no_conflict(self):
        """Test when there is no conflict between ckddetail and initial values."""
        self.assertFalse(self.update_editor.ckddetail_initial_conflict)

    def test_ckddetail_initial_conflict_with_conflict(self):
        """Test when there is a conflict between ckddetail and initial values."""
        self.update_editor.initial["dialysis"] = not self.ckddetail.dialysis  # Intentionally setting a different value
        self.assertTrue(self.update_editor.ckddetail_initial_conflict)

    def test_ckddetail_initial_conflict_no_initial(self):
        """Test when initial is None."""
        self.update_editor.initial = None
        self.assertFalse(self.update_editor.ckddetail_initial_conflict)

    def test__get_ckddetail_changed_fields(self):
        changed_fields = self.update_editor.get_ckddetail_changed_fields()
        self.assertTrue(isinstance(changed_fields, list))
        self.assertIn(("dialysis", self.ckddetail_dialysis), changed_fields)

    def test__ckddetail_has_changed(self):
        self.assertTrue(self.update_editor.ckddetail_has_changed)

    def test__ckdetail_has_not_changed(self):
        self.update_editor.dialysis = self.ckddetail.dialysis
        self.update_editor.dialysis_duration = self.ckddetail.dialysis_duration
        self.update_editor.dialysis_type = self.ckddetail.dialysis_type
        self.update_editor.stage = self.ckddetail.stage
        self.assertFalse(self.update_editor.ckddetail_has_changed)

    def test__update(self):
        """Test successful update of CkdDetail."""
        updated_ckddetail = self.update_editor.update()
        self.assertIsInstance(updated_ckddetail, CkdDetail)
        self.assertEqual(updated_ckddetail.dialysis, self.ckddetail_dialysis)
        self.assertEqual(updated_ckddetail.dialysis_type, self.ckddetail__dialysis_type)
        self.assertEqual(updated_ckddetail.dialysis_duration, self.ckddetail__dialysis_duration)
        self.assertEqual(updated_ckddetail.stage, self.ckddetail__stage)
        self.assertEqual(updated_ckddetail.medhistory, self.ckddetail.medhistory)

    def test__update_does_not_save_when_ckddetail_unchanged(self):
        self.update_editor.dialysis = self.ckddetail.dialysis
        self.update_editor.dialysis_duration = self.ckddetail.dialysis_duration
        self.update_editor.dialysis_type = self.ckddetail.dialysis_type
        self.update_editor.stage = self.ckddetail.stage
        with CaptureQueriesContext(connection=connection) as queries:
            self.update_editor.update()
        self.assertEqual(len(queries), 0)


class TestGoutDetailAPI(TestCase):
    def setUp(self):
        self.goutdetail = GoutDetailFactory()
        self.patient = create_psp()
        self.goutdetail_data = {
            "goutdetail__at_goal": False,
            "goutdetail__at_goal_long_term": False,
            "goutdetail__flaring": True,
            "goutdetail__on_ppx": False,
            "goutdetail__on_ult": False,
            "goutdetail__starting_ult": False,
        }
        self.empty_patient = UserFactory(role=Roles.PSEUDOPATIENT)
        self.empty_patient_gout = GoutFactory(user=self.empty_patient)
        self.create_mixin = GoutDetailAPI(
            gout=self.empty_patient_gout,
            patient=self.empty_patient,
            goutdetail=None,
            **self.goutdetail_data,
        )
        self.update_mixin = GoutDetailAPI(
            goutdetail=self.goutdetail,
            gout=None,
            patient=None,
            **self.goutdetail_data,
        )

    def test__init__(self):
        self.assertEqual(self.create_mixin.gout, self.empty_patient_gout)
        self.assertEqual(self.create_mixin.patient, self.create_mixin.patient)
        self.assertIsNone(self.create_mixin.goutdetail)
        self.assertEqual(self.create_mixin.goutdetail__at_goal, self.goutdetail_data["goutdetail__at_goal"])
        self.assertEqual(
            self.create_mixin.goutdetail__at_goal_long_term, self.goutdetail_data["goutdetail__at_goal_long_term"]
        )
        self.assertEqual(self.create_mixin.goutdetail__flaring, self.goutdetail_data["goutdetail__flaring"])
        self.assertEqual(self.create_mixin.goutdetail__on_ppx, self.goutdetail_data["goutdetail__on_ppx"])
        self.assertEqual(self.create_mixin.goutdetail__on_ult, self.goutdetail_data["goutdetail__on_ult"])
        self.assertEqual(self.create_mixin.goutdetail__starting_ult, self.goutdetail_data["goutdetail__starting_ult"])
        self.assertEqual(self.create_mixin.errors, [])

    def test__get_queryset(self):
        self.update_mixin.goutdetail = self.goutdetail.pk
        queryset = self.update_mixin.get_queryset()
        self.assertIsInstance(queryset, QuerySet)
        self.assertEqual(queryset.get(), self.goutdetail)

    def test__get_queryset_raises_error(self):
        with self.assertRaises(TypeError) as context:
            self.update_mixin.get_queryset()
        self.assertEqual(context.exception.args[0], "goutdetail arg must be a UUID to call get_queryset()")

    def test__set_attrs_from_qs(self):
        self.update_mixin.goutdetail = self.goutdetail.pk
        self.update_mixin.set_attrs_from_qs()
        self.assertEqual(self.update_mixin.gout, self.goutdetail.medhistory)
        self.assertEqual(self.update_mixin.patient, self.goutdetail.medhistory.user)
        self.assertEqual(self.update_mixin.goutdetail, self.goutdetail)

    def test__set_attrs_from_qs_raises_error(self):
        with self.assertRaises(TypeError) as context:
            self.update_mixin.set_attrs_from_qs()
        self.assertEqual(context.exception.args[0], "goutdetail arg must be a UUID to call get_queryset()")

    def test__create_goutdetail(self):
        new_goutdetail = self.create_mixin.create_goutdetail()
        self.assertIsInstance(new_goutdetail, GoutDetail)
        self.assertEqual(new_goutdetail.medhistory, self.empty_patient_gout)

    def test__create_goutdetail_raises_error(self):
        self.create_mixin.gout = None
        with self.assertRaises(GoutHelperValidationError) as context:
            self.create_mixin.create_goutdetail()
        error_keys = [error[0] for error in context.exception.errors]
        self.assertIn("gout", error_keys)

    def test__check_for_goutdetail_create_errors_no_gout(self):
        self.create_mixin.gout = None
        self.create_mixin.check_for_goutdetail_create_errors()
        self.assertTrue(self.create_mixin.errors)
        self.assertIn(("gout", "Gout is required to create a GoutDetail."), self.create_mixin.errors)

    def test__check_for_goutdetail_create_errors_no_goutdetail(self):
        erroneous_goutdetail = GoutDetailFactory()
        self.create_mixin.goutdetail = erroneous_goutdetail
        self.create_mixin.check_for_goutdetail_create_errors()
        self.assertTrue(self.create_mixin.errors)
        print(self.create_mixin.errors)
        self.assertIn(("goutdetail", f"{erroneous_goutdetail} already exists."), self.create_mixin.errors)

    def test__check_for_goutdetail_create_errors_at_goal_long_term_is_None(self):
        self.create_mixin.goutdetail__at_goal_long_term = None
        self.create_mixin.check_for_goutdetail_create_errors()
        self.assertTrue(self.create_mixin.errors)
        self.assertIn(
            ("goutdetail__at_goal_long_term", "at_goal_long_term is required to create a GoutDetail instance."),
            self.create_mixin.errors,
        )

    def test__check_for_goutdetail_create_errors_at_goal_long_term_but_not_at_goal(self):
        self.create_mixin.goutdetail__at_goal = False
        self.create_mixin.goutdetail__at_goal_long_term = True
        self.create_mixin.check_for_goutdetail_create_errors()
        self.assertTrue(self.create_mixin.errors)
        self.assertIn(
            ("goutdetail__at_goal_long_term", "at_goal_long_term cannot be True if at_goal is False."),
            self.create_mixin.errors,
        )

    def test__check_for_goutdetail_create_errors_on_ppx_is_None(self):
        self.create_mixin.goutdetail__on_ppx = None
        self.create_mixin.check_for_goutdetail_create_errors()
        self.assertTrue(self.create_mixin.errors)
        self.assertIn(
            ("goutdetail__on_ppx", "on_ppx is required to create a GoutDetail instance."),
            self.create_mixin.errors,
        )

    def test__check_for_goutdetail_create_errors_on_ult_is_None(self):
        self.create_mixin.goutdetail__on_ult = None
        self.create_mixin.check_for_goutdetail_create_errors()
        self.assertTrue(self.create_mixin.errors)
        self.assertIn(
            ("goutdetail__on_ult", "on_ult is required to create a GoutDetail instance."),
            self.create_mixin.errors,
        )

    def test__check_for_goutdetail_create_errors_starting_ult_is_None(self):
        self.create_mixin.goutdetail__starting_ult = None
        self.create_mixin.check_for_goutdetail_create_errors()
        self.assertTrue(self.create_mixin.errors)
        self.assertIn(
            ("goutdetail__starting_ult", "starting_ult is required to create a GoutDetail instance."),
            self.create_mixin.errors,
        )

    def test__check_for_goutdetail_create_errors_gout_with_patient_without_patient_arg(self):
        gout = GoutFactory(user=UserFactory(role=Roles.PSEUDOPATIENT))
        self.create_mixin.patient = None
        self.create_mixin.gout = gout
        self.create_mixin.check_for_goutdetail_create_errors()
        self.assertTrue(self.create_mixin.errors)
        self.assertIn(("patient", f"{gout} has a user but no patient arg."), self.create_mixin.errors)

    def test__check_for_goutdetail_create_errors_patient_has_goutdetail(self):
        self.create_mixin.gout = self.patient.gout
        self.create_mixin.patient = self.patient
        self.create_mixin.check_for_goutdetail_create_errors()
        self.assertTrue(self.create_mixin.errors)
        self.assertIn(
            ("patient", f"{self.patient} already has a GoutDetail ({self.patient.goutdetail})."),
            self.create_mixin.errors,
        )

    def test__at_goal_long_term_but_not_at_goal(self):
        self.create_mixin.goutdetail__at_goal = False
        self.create_mixin.goutdetail__at_goal_long_term = True
        self.assertTrue(self.create_mixin.at_goal_long_term_but_not_at_goal)

    def test__patient_has_goutdetail(self):
        self.create_mixin.gout = self.patient.gout
        self.create_mixin.patient = self.patient
        self.assertTrue(self.create_mixin.patient_has_goutdetail)

    def test__check_for_and_raise_errors(self):
        self.create_mixin.errors = [("field1", "Error 1"), ("field2", "Error 2")]
        with self.assertRaises(GoutHelperValidationError) as context:
            self.create_mixin.check_for_and_raise_errors(model_name="GoutDetail")
        self.assertEqual(context.exception.errors, self.create_mixin.errors)

    def test__update_goutdetail(self):
        updated_goutdetail = self.update_mixin.update_goutdetail()
        self.assertIsInstance(updated_goutdetail, GoutDetail)
        self.assertEqual(updated_goutdetail.medhistory, self.goutdetail.medhistory)
        for field, value in self.goutdetail_data.items():
            trunc_field = field.replace("goutdetail__", "")
            self.assertEqual(getattr(updated_goutdetail, trunc_field), value)

    def test__update_goutdetail_sets_attrs_from_qs(self):
        self.update_mixin.goutdetail = self.goutdetail.pk
        self.update_mixin.update_goutdetail()
        self.assertEqual(self.update_mixin.gout, self.goutdetail.medhistory)
        self.assertEqual(self.update_mixin.patient, self.goutdetail.medhistory.user)
        self.assertEqual(self.update_mixin.goutdetail, self.goutdetail)

    def test__update_goutdetail_raises_error(self):
        self.update_mixin.goutdetail = None
        with self.assertRaises(GoutHelperValidationError) as context:
            self.update_mixin.update_goutdetail()
        error_keys = [error[0] for error in context.exception.errors]
        self.assertIn("goutdetail", error_keys)

    def test__check_for_goutdetail_update_errors_no_goutdetail(self):
        self.update_mixin.goutdetail = None
        self.update_mixin.check_for_goutdetail_update_errors()
        self.assertTrue(self.update_mixin.errors)
        self.assertIn(
            ("goutdetail", "GoutDetail is required to update a GoutDetail instance."), self.update_mixin.errors
        )

    def test__check_for_goutdetail_update_errors_goutdetail_has_medhistory_that_is_not_gout(self):
        self.update_mixin.gout = CkdFactory()
        self.update_mixin.check_for_goutdetail_update_errors()
        self.assertTrue(self.update_mixin.errors)
        self.assertIn(
            ("goutdetail", f"{self.update_mixin.goutdetail} has a medhistory that is not a {self.update_mixin.gout}."),
            self.update_mixin.errors,
        )

    def test__check_for_goutdetail_update_errors_at_goal_long_term_is_None(self):
        self.update_mixin.goutdetail__at_goal_long_term = None
        self.update_mixin.check_for_goutdetail_update_errors()
        self.assertTrue(self.update_mixin.errors)
        self.assertIn(
            ("goutdetail__at_goal_long_term", "at_goal_long_term is required to update a GoutDetail instance."),
            self.update_mixin.errors,
        )

    def test__check_for_goutdetail_update_errors_at_goal_long_term_but_not_at_goal(self):
        self.update_mixin.goutdetail__at_goal = False
        self.update_mixin.goutdetail__at_goal_long_term = True
        self.update_mixin.check_for_goutdetail_update_errors()
        self.assertTrue(self.update_mixin.errors)
        self.assertIn(
            ("goutdetail__at_goal_long_term", "at_goal_long_term cannot be True if at_goal is False."),
            self.update_mixin.errors,
        )

    def test__check_for_goutdetail_update_errors_on_ppx_is_None(self):
        self.update_mixin.goutdetail__on_ppx = None
        self.update_mixin.check_for_goutdetail_update_errors()
        self.assertTrue(self.update_mixin.errors)
        self.assertIn(
            ("goutdetail__on_ppx", "on_ppx is required to update a GoutDetail instance."),
            self.update_mixin.errors,
        )

    def test__check_for_goutdetail_update_errors_on_ult_is_None(self):
        self.update_mixin.goutdetail__on_ult = None
        self.update_mixin.check_for_goutdetail_update_errors()
        self.assertTrue(self.update_mixin.errors)
        self.assertIn(
            ("goutdetail__on_ult", "on_ult is required to update a GoutDetail instance."),
            self.update_mixin.errors,
        )

    def test__check_for_goutdetail_update_errors_starting_ult_is_None(self):
        self.update_mixin.goutdetail__starting_ult = None
        self.update_mixin.check_for_goutdetail_update_errors()
        self.assertTrue(self.update_mixin.errors)
        self.assertIn(
            ("goutdetail__starting_ult", "starting_ult is required to update a GoutDetail instance."),
            self.update_mixin.errors,
        )

    def test__check_for_goutdetail_update_errors_goutdetail_has_user_who_is_not_patient(self):
        new_gout = GoutFactory(user=UserFactory(role=Roles.PSEUDOPATIENT))
        self.update_mixin.gout = new_gout
        self.update_mixin.goutdetail.medhistory = new_gout
        new_pseudopatient = create_psp()
        self.update_mixin.patient = new_pseudopatient
        self.update_mixin.check_for_goutdetail_update_errors()
        self.assertTrue(self.update_mixin.errors)
        self.assertIn(
            ("goutdetail", f"{self.update_mixin.goutdetail} has a user who is not {new_pseudopatient}."),
            self.update_mixin.errors,
        )

    def test__goutdetail_has_medhistory_that_is_not_gout(self):
        self.update_mixin.gout = CkdFactory()
        self.assertTrue(self.update_mixin.goutdetail_has_medhistory_that_is_not_gout)

    def test__goutdetail_has_user_who_is_not_patient(self):
        new_gout = GoutFactory(user=UserFactory(role=Roles.PSEUDOPATIENT))
        self.update_mixin.gout = new_gout
        self.update_mixin.goutdetail.medhistory = new_gout
        new_pseudopatient = create_psp()
        self.update_mixin.patient = new_pseudopatient
        self.assertTrue(self.update_mixin.goutdetail_has_user_who_is_not_patient)

    def test__goutdetail_needs_save(self):
        self.update_mixin.goutdetail__at_goal = not self.goutdetail.at_goal
        self.assertTrue(self.update_mixin.goutdetail_needs_save)

    def test__update_goutdetail_instance(self):
        self.update_mixin.update_goutdetail_instance()
        for field, value in self.goutdetail_data.items():
            trunc_field = field.replace("goutdetail__", "")
            self.assertEqual(getattr(self.update_mixin.goutdetail, trunc_field), value)
