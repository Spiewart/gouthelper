from datetime import timedelta
from decimal import Decimal

import pytest  # type: ignore
from django.core.exceptions import ValidationError  # type: ignore
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ...genders.choices import Genders
from ...labs.forms import PpxUrateFormSet
from ...labs.models import Urate
from ...labs.tests.factories import BaselineCreatinineFactory, CreatinineFactory
from ...medhistorydetails.choices import Stages
from ...medhistorydetails.tests.factories import GoutDetailFactory
from ...medhistorys.tests.factories import GoutFactory
from ..helpers import (
    labs_baselinecreatinine_max_value,
    labs_calculate_baseline_creatinine_from_eGFR_age_gender,
    labs_creatinine_calculate_min_max_creatinine_from_stage_age_gender,
    labs_creatinine_within_range_for_stage,
    labs_creatinines_are_drawn_more_than_1_day_apart,
    labs_creatinines_are_improving,
    labs_eGFR_calculator,
    labs_eGFR_range_for_stage,
    labs_formset_get_most_recent_form,
    labs_formset_order_by_date_drawn_remove_deleted_and_blank_forms,
    labs_round_decimal,
    labs_sort_list_of_generics_by_date_drawn_desc,
    labs_stage_calculator,
    labs_urate_form_at_goal_within_last_month,
    labs_urate_formset_at_goal_for_six_months,
    labs_urate_within_90_days,
    labs_urates_compare_chronological_order_by_date,
    labs_urates_last_at_goal,
    labs_urates_max_value,
    labs_urates_six_months_at_goal,
)
from ..selectors import urates_dated_qs
from .factories import UrateFactory

pytestmark = pytest.mark.django_db


class TestLabsBaselineCreatinineMaxValue(TestCase):
    def test__raises_ValidationError(self):
        with self.assertRaises(ValidationError) as error:
            labs_baselinecreatinine_max_value(Decimal("11.0"))
        self.assertEqual(
            error.exception.messages[0],
            "A baseline creatinine value greater than 10 mg/dL isn't very likely. \
This would typically mean the patient is on dialysis.",
        )

    def test__doesnt_raise_ValidationError(self):
        labs_baselinecreatinine_max_value(Decimal("4.0"))


class TestLabsCreatinineWithinRangeForStage(TestCase):
    def test__returns_correct_value(self):
        self.assertTrue(
            labs_creatinine_within_range_for_stage(
                CreatinineFactory(value=Decimal("1.0")), stage=Stages.ONE, age=40, gender=Genders.MALE
            )
        )
        self.assertTrue(
            labs_creatinine_within_range_for_stage(
                CreatinineFactory(value=Decimal("2.0")), stage=Stages.THREE, age=40, gender=Genders.MALE
            )
        )


class TestLabsCreatininesAreImproving(TestCase):
    def test__returns_True(self):
        creatinines = [
            CreatinineFactory(value=Decimal("1.0")),
            CreatinineFactory(value=Decimal("2.0")),
            CreatinineFactory(value=Decimal("3.0")),
        ]
        self.assertTrue(labs_creatinines_are_improving(creatinines))

    def test__returns_False(self):
        creatinines = [
            CreatinineFactory(value=Decimal("3.0")),
            CreatinineFactory(value=Decimal("2.0")),
            CreatinineFactory(value=Decimal("1.0")),
        ]
        self.assertFalse(labs_creatinines_are_improving(creatinines))


class TestLabsCreatininesAreDrawnMoreThan24HoursApart(TestCase):
    def test__returns_True(self):
        current_creatinine = CreatinineFactory(date_drawn=timezone.now() - timedelta(days=1))
        previous_creatinine = CreatinineFactory(date_drawn=timezone.now())
        self.assertTrue(
            labs_creatinines_are_drawn_more_than_1_day_apart(
                current_creatinine=current_creatinine, prior_creatinine=previous_creatinine
            )
        )

    def test__returns_False(self):
        current_creatinine = CreatinineFactory(date_drawn=timezone.now() - timedelta(hours=23))
        previous_creatinine = CreatinineFactory(date_drawn=timezone.now())
        self.assertFalse(
            labs_creatinines_are_drawn_more_than_1_day_apart(
                current_creatinine=current_creatinine, prior_creatinine=previous_creatinine
            )
        )


class TestLabseGFRCalculator(TestCase):
    """Test sutie for the labs_eGFR_calculator() method."""

    def setUp(self):
        self.creatinine = BaselineCreatinineFactory(value=Decimal("3.0"))
        self.creatinine_value = Decimal("3.0")

    def test__returns_correct_value(self):
        # Should evaluate to 25
        eGFR = labs_eGFR_calculator(
            creatinine=self.creatinine,
            age=50,
            gender=Genders.MALE,
        )
        self.assertEqual(eGFR, 25)
        value_eGFR = labs_eGFR_calculator(
            creatinine=self.creatinine_value,
            age=50,
            gender=Genders.MALE,
        )
        self.assertEqual(value_eGFR, 25)
        # Should evaluate to 18
        eGFR = labs_eGFR_calculator(
            creatinine=self.creatinine,
            age=50,
            gender=Genders.FEMALE,
        )
        self.assertEqual(eGFR, 18)
        value_eGFR = labs_eGFR_calculator(
            creatinine=self.creatinine_value,
            age=50,
            gender=Genders.FEMALE,
        )
        self.assertEqual(value_eGFR, 18)
        # Should evaluate to 16
        eGFR = labs_eGFR_calculator(
            creatinine=self.creatinine,
            age=75,
            gender=Genders.FEMALE,
        )
        self.assertEqual(eGFR, 16)
        value_eGFR = labs_eGFR_calculator(
            creatinine=self.creatinine_value,
            age=75,
            gender=Genders.FEMALE,
        )
        self.assertEqual(value_eGFR, 16)
        self.creatinine.value = Decimal("1.2")
        self.creatinine.save()
        self.creatinine_value = Decimal("1.2")
        # Should evaluate to 47
        eGFR = labs_eGFR_calculator(
            creatinine=self.creatinine,
            age=75,
            gender=Genders.FEMALE,
        )
        self.assertEqual(eGFR, 47)
        value_eGFR = labs_eGFR_calculator(
            creatinine=self.creatinine_value,
            age=75,
            gender=Genders.FEMALE,
        )
        self.assertEqual(eGFR, 47)
        # Should evaluate to 63
        eGFR = labs_eGFR_calculator(
            creatinine=self.creatinine,
            age=75,
            gender=Genders.MALE,
        )
        self.assertEqual(eGFR, 63)
        value_eGFR = labs_eGFR_calculator(
            creatinine=self.creatinine_value,
            age=75,
            gender=Genders.MALE,
        )
        self.assertEqual(eGFR, 63)

    def test__raises_TypeError(self):
        with self.assertRaises(TypeError) as error:
            labs_eGFR_calculator(
                creatinine=300,
                age=50,
                gender=Genders.MALE,
            )
        self.assertEqual(
            error.exception.args[0], f"labs_eGFR_calculator() was called on a non-lab, non-Decimal object: {300}"
        )


class TestLabsCalculateBaselineCreatinineFromEGFRStageAgeGender(TestCase):
    def test__returns_correct_value(self):
        age = 50
        gender = Genders.FEMALE
        eGFR = 50
        creatinine = labs_calculate_baseline_creatinine_from_eGFR_age_gender(eGFR, age, gender)
        self.assertTrue(isinstance(creatinine, Decimal))
        eGFR_calc = labs_eGFR_calculator(creatinine=creatinine, age=age, gender=gender)
        self.assertEqual(eGFR_calc, eGFR)


class TestLabsCreatinineCalculateMinMaxCreatinineFromStageAgeGender(TestCase):
    def test__returns_correct_value(self):
        age = 50
        gender = Genders.MALE
        for stage in [stage for stage in Stages.values if stage is not None]:
            creatinine_range = labs_creatinine_calculate_min_max_creatinine_from_stage_age_gender(stage, age, gender)
            self.assertTrue(isinstance(creatinine_range, tuple))
            self.assertTrue(isinstance(creatinine_range[0], Decimal))
            self.assertTrue(isinstance(creatinine_range[1], Decimal))
            min_creatinine = labs_calculate_baseline_creatinine_from_eGFR_age_gender(
                labs_eGFR_range_for_stage(stage)[1], age, gender
            )
            self.assertEqual(min_creatinine, creatinine_range[0])
            max_creatinine = labs_calculate_baseline_creatinine_from_eGFR_age_gender(
                labs_eGFR_range_for_stage(stage)[0], age, gender
            )
            self.assertEqual(max_creatinine, creatinine_range[1])


class TestLabsRoundDecimal(TestCase):
    def test__rounds_to_single_decimal(self):
        self.assertEqual(labs_round_decimal(Decimal("1.2345"), 1), Decimal("1.2"))

    def test__rounds_no_decimal(self):
        self.assertEqual(labs_round_decimal(Decimal("1.2345"), 0), Decimal("1"))

    def test__rounds_two_decimals(self):
        self.assertEqual(labs_round_decimal(Decimal("1.2345"), 2), Decimal("1.23"))


class TestStageCalculator(TestCase):
    def test__stage1(self):
        self.assertEqual(labs_stage_calculator(Decimal("95")), 1)

    def test__stage2(self):
        self.assertEqual(labs_stage_calculator(Decimal("85")), 2)

    def test__stage3(self):
        self.assertEqual(labs_stage_calculator(Decimal("45")), 3)

    def test__stage4(self):
        self.assertEqual(labs_stage_calculator(Decimal("15")), 4)

    def test__stage5(self):
        self.assertEqual(labs_stage_calculator(Decimal("5")), 5)


class TestLabsSortListOfGenericsByDateDrawnDesc(TestCase):
    def setUp(self):
        self.creatinine1 = CreatinineFactory(date_drawn=timezone.now() - timedelta(days=10))
        self.creatinine2 = CreatinineFactory(date_drawn=timezone.now() - timedelta(days=5))
        self.creatinine3 = CreatinineFactory(date_drawn=timezone.now() - timedelta(days=1))

    def test__sorts_with_all_model_instances(self):
        unordered_list = [self.creatinine2, self.creatinine3, self.creatinine1]
        labs_sort_list_of_generics_by_date_drawn_desc(unordered_list)
        self.assertEqual(unordered_list, [self.creatinine3, self.creatinine2, self.creatinine1])

    def test__sorts_with_all_uuids(self):
        unordered_list = [self.creatinine2.pk, self.creatinine3.pk, self.creatinine1.pk]
        labs_sort_list_of_generics_by_date_drawn_desc(unordered_list)
        self.assertEqual(unordered_list, [self.creatinine3.pk, self.creatinine2.pk, self.creatinine1.pk])

    def test__sorts_with_all_dicts(self):
        unordered_list = [
            {"date_drawn": self.creatinine2.date_drawn, "pk": self.creatinine2.pk},
            {"date_drawn": self.creatinine3.date_drawn, "pk": self.creatinine3.pk},
            {"date_drawn": self.creatinine1.date_drawn, "pk": self.creatinine1.pk},
        ]
        labs_sort_list_of_generics_by_date_drawn_desc(unordered_list)
        self.assertEqual(
            unordered_list,
            [
                {"date_drawn": self.creatinine3.date_drawn, "pk": self.creatinine3.pk},
                {"date_drawn": self.creatinine2.date_drawn, "pk": self.creatinine2.pk},
                {"date_drawn": self.creatinine1.date_drawn, "pk": self.creatinine1.pk},
            ],
        )


class TestLabsUratesChronologicalDates(TestCase):
    def setUp(self):
        self.urate1 = UrateFactory(date_drawn=timezone.now() - timedelta(days=10))
        self.urate2 = UrateFactory(date_drawn=timezone.now() - timedelta(days=5))
        self.urate3 = UrateFactory(date_drawn=timezone.now() - timedelta(days=1))
        # Create QuerySet of urates annotated by date from date_drawn
        self.urate_qs = urates_dated_qs().all()
        # Create unannotated QuerySet of urates
        self.urate_qs_no_date = Urate.objects.all()
        # Create unordered list of urates that is not in chronological order
        self.urate_list = [self.urate2, self.urate3, self.urate1]
        # Pseudo-annotate a date attr from each urate's date_drawn
        for urate in self.urate_list:
            urate.date = urate.date_drawn

    def test__in_order(self):
        for ui, urate in enumerate(self.urate_qs):
            labs_urates_compare_chronological_order_by_date(
                current_urate=urate,
                previous_urate=self.urate_qs[ui - 1] if ui > 0 else None,
                first_urate=self.urate_qs[0],
            )

    def test__raises_ValueError_not_in_order(self):
        with self.assertRaises(ValueError) as error:
            for ui, urate in enumerate(self.urate_list):
                labs_urates_compare_chronological_order_by_date(
                    current_urate=urate,
                    previous_urate=self.urate_list[ui - 1] if ui > 0 else None,
                    first_urate=self.urate_list[0],
                )
        self.assertEqual(
            error.exception.args[0], "The Urates are not in chronological order. QuerySet must be ordered by date."
        )


class TestLabsUrateFormAtGoalWithinLastMonth(TestCase):
    """Test the labs_urate_form_at_goal_within_last_month method."""

    def test__returns_True(self):
        urate = UrateFactory(value=Decimal("5.0"), date_drawn=timezone.now())
        urate_qs = urates_dated_qs().filter(pk=urate.pk)
        formset_data = {
            "urate-TOTAL_FORMS": "2",
            "urate-INITIAL_FORMS": "1",
        }
        for urate_i, urate in enumerate(urate_qs):
            formset_data.update(
                {
                    f"urate-{urate_i}-value": urate.value,
                    f"urate-{urate_i}-date_drawn": urate.date_drawn,
                    f"urate-{urate_i}-id": str(urate.pk),
                }
            )
        formset = PpxUrateFormSet(queryset=urate_qs, data=formset_data, prefix="urate")
        self.assertTrue(formset.is_valid())
        self.assertTrue(
            labs_urate_form_at_goal_within_last_month(
                labs_formset_get_most_recent_form(
                    labs_formset_order_by_date_drawn_remove_deleted_and_blank_forms(formset)
                )
            )
        )

    def test__returns_False(self):
        urate = UrateFactory(value=Decimal("15.0"), date_drawn=timezone.now())
        urate_qs = urates_dated_qs().filter(pk=urate.pk)
        formset_data = {
            "urate-TOTAL_FORMS": "2",
            "urate-INITIAL_FORMS": "1",
        }
        for urate_i, urate in enumerate(urate_qs):
            formset_data.update(
                {
                    f"urate-{urate_i}-value": urate.value,
                    f"urate-{urate_i}-date_drawn": urate.date_drawn,
                    f"urate-{urate_i}-id": str(urate.pk),
                }
            )
        formset = PpxUrateFormSet(queryset=urate_qs, data=formset_data, prefix="urate")
        self.assertTrue(formset.is_valid())
        self.assertFalse(
            labs_urate_form_at_goal_within_last_month(
                labs_formset_get_most_recent_form(
                    labs_formset_order_by_date_drawn_remove_deleted_and_blank_forms(formset)
                )
            )
        )

        # Test with urate that is at goal but is old
        old_urate = UrateFactory(value=Decimal("5.0"), date_drawn=timezone.now() - timedelta(days=200))
        urate_qs = urates_dated_qs().filter(pk=old_urate.pk)
        formset_data = {
            "urate-TOTAL_FORMS": "2",
            "urate-INITIAL_FORMS": "1",
        }
        for urate_i, urate in enumerate(urate_qs):
            formset_data.update(
                {
                    f"urate-{urate_i}-value": urate.value,
                    f"urate-{urate_i}-date_drawn": urate.date_drawn,
                    f"urate-{urate_i}-id": str(urate.pk),
                }
            )
        formset = PpxUrateFormSet(queryset=urate_qs, data=formset_data, prefix="urate")
        self.assertTrue(formset.is_valid())
        self.assertFalse(
            labs_urate_form_at_goal_within_last_month(
                labs_formset_get_most_recent_form(
                    labs_formset_order_by_date_drawn_remove_deleted_and_blank_forms(formset)
                )
            )
        )


class TestLabsUratesFormsetAtGoalSixMonths(TestCase):
    """Test the labs_urate_formset_at_goal_for_six_months method."""

    def test__returns_True(self):
        urate = UrateFactory(value=Decimal("5.0"), date_drawn=timezone.now())
        disant_urate = UrateFactory(value=Decimal("5.0"), date_drawn=timezone.now() - timedelta(days=185))
        urate_qs = urates_dated_qs().filter(pk__in=[urate.pk, disant_urate.pk])
        formset_data = {
            "urate-TOTAL_FORMS": "3",
            "urate-INITIAL_FORMS": "2",
        }
        for urate_i, urate in enumerate(urate_qs):
            formset_data.update(
                {
                    f"urate-{urate_i}-value": urate.value,
                    f"urate-{urate_i}-date_drawn": urate.date_drawn,
                    f"urate-{urate_i}-id": str(urate.pk),
                }
            )
        formset = PpxUrateFormSet(queryset=urate_qs, data=formset_data, prefix="urate")
        self.assertTrue(formset.is_valid())
        self.assertTrue(
            labs_urate_formset_at_goal_for_six_months(
                labs_formset_order_by_date_drawn_remove_deleted_and_blank_forms(formset)
            )
        )

    def test__returns_False(self):
        urate = UrateFactory(value=Decimal("5.0"), date_drawn=timezone.now())
        disant_urate = UrateFactory(value=Decimal("5.0"), date_drawn=timezone.now() - timedelta(days=174))
        urate_qs = urates_dated_qs().filter(pk__in=[urate.pk, disant_urate.pk])
        formset_data = {
            "urate-TOTAL_FORMS": "3",
            "urate-INITIAL_FORMS": "2",
        }
        for urate_i, urate in enumerate(urate_qs):
            formset_data.update(
                {
                    f"urate-{urate_i}-value": urate.value,
                    f"urate-{urate_i}-date_drawn": urate.date_drawn,
                    f"urate-{urate_i}-id": str(urate.pk),
                }
            )
        formset = PpxUrateFormSet(queryset=urate_qs, data=formset_data, prefix="urate")
        self.assertTrue(formset.is_valid())
        self.assertFalse(
            labs_urate_formset_at_goal_for_six_months(
                labs_formset_order_by_date_drawn_remove_deleted_and_blank_forms(formset)
            )
        )

    def test__returns_False_no_urates(self):
        urate_qs = Urate.objects.none()
        formset_data = {
            "urate-TOTAL_FORMS": "1",
            "urate-INITIAL_FORMS": "0",
        }
        formset = PpxUrateFormSet(queryset=urate_qs, data=formset_data, prefix="urate")
        self.assertTrue(formset.is_valid())
        self.assertFalse(
            labs_urate_formset_at_goal_for_six_months(
                labs_formset_order_by_date_drawn_remove_deleted_and_blank_forms(formset)
            )
        )


class TestLabsUratesHyperuricemic(TestCase):
    """Tests for the labs_urates_six_months_at_goal() method."""

    def test__returns_True(self):
        UrateFactory(value=Decimal("5.0"))
        UrateFactory(value=Decimal("5.0"), date_drawn=timezone.now() - timedelta(days=200))
        urate_qs = urates_dated_qs().all()
        self.assertTrue(labs_urates_six_months_at_goal(urates=urate_qs))

    def test__returns_False(self):
        UrateFactory(value=Decimal("5.0"))
        urate_qs = urates_dated_qs().all()
        self.assertFalse(labs_urates_six_months_at_goal(urates=urate_qs))


class TestLabsUratesLastAtGoal(TestCase):
    def setUp(self):
        # Create some urates, last not at goal
        UrateFactory(value=Decimal("7.0"), date_drawn=timezone.now() - timedelta(days=10))
        UrateFactory(value=Decimal("6.0"), date_drawn=timezone.now() - timedelta(days=50))
        UrateFactory(value=Decimal("15.0"), date_drawn=timezone.now() - timedelta(days=100))
        self.gout = GoutFactory()
        self.goutdetail = GoutDetailFactory(medhistory=self.gout, at_goal=False)

    def test__returns_correctly(self):
        urate_qs = urates_dated_qs().all()
        self.assertFalse(labs_urates_last_at_goal(urates=urate_qs))
        UrateFactory(value=Decimal("5.0"), date_drawn=timezone.now() - timedelta(days=5))
        urate_qs = urates_dated_qs().all()
        self.assertTrue(labs_urates_last_at_goal(urates=urate_qs))

    def test__not_sorted_raises_ValueError(self):
        urates = urates_dated_qs().all()
        urates = sorted(urates, key=lambda x: x.date_drawn, reverse=False)
        with self.assertRaises(ValueError) as error:
            labs_urates_last_at_goal(urates=urates)
        self.assertEqual(
            error.exception.args[0], "The Urates are not in chronological order. QuerySet must be ordered by date."
        )


class TestLabsUrateMonthsAtGoal(TestCase):
    """These tests use the urates_dated_qs() queryset, which is a custom queryset
    that annotates each Urate with a date attr that is the date_drawn if it exists,
    or the Flare.date_started if it doesn't. This is because Flare objects don't
    require reporting a date_drawn for the Urate, but Urate's entered elsewhere do."""

    def test__returns_True(self):
        UrateFactory(value=5.0, date_drawn=timezone.now())
        UrateFactory(value=6.0, date_drawn=timezone.now() - timedelta(days=190))
        urate_qs = urates_dated_qs().all()
        self.assertTrue(labs_urates_six_months_at_goal(urates=urate_qs))

    def test__at_goal_not_six_months_returns_False(self):
        UrateFactory(value=5.0, date_drawn=timezone.now())
        UrateFactory(value=6.0, date_drawn=timezone.now() - timedelta(days=150))
        urate_qs = urates_dated_qs().all()
        self.assertFalse(labs_urates_six_months_at_goal(urates=urate_qs))

    def test__not_at_goal_returns_False(self):
        UrateFactory(value=5.0, date_drawn=timezone.now())
        UrateFactory(value=6.0, date_drawn=timezone.now() - timedelta(days=110))
        UrateFactory(value=7.0, date_drawn=timezone.now() - timedelta(days=170))
        urate_qs = urates_dated_qs().all()
        self.assertFalse(labs_urates_six_months_at_goal(urates=urate_qs))

    def test__most_recent_not_at_goal_returns_False(self):
        UrateFactory(value=10.0, date_drawn=timezone.now())
        UrateFactory(value=6.0, date_drawn=timezone.now() - timedelta(days=90))
        UrateFactory(value=4.0, date_drawn=timezone.now() - timedelta(days=170))
        urate_qs = urates_dated_qs().all()
        self.assertFalse(labs_urates_six_months_at_goal(urates=urate_qs))


class LabsUratesRecentUrate(TestCase):
    def setUp(self):
        # Create a few urates
        UrateFactory(value=Decimal("7.0"), date_drawn=timezone.now() - timedelta(days=10))
        UrateFactory(value=Decimal("6.0"), date_drawn=timezone.now() - timedelta(days=50))
        UrateFactory(value=Decimal("15.0"), date_drawn=timezone.now() - timedelta(days=100))
        # Create old urate
        UrateFactory(value=Decimal("5.0"), date_drawn=timezone.now() - timedelta(days=200))

    def test__returns_correctly(self):
        urates_qs = urates_dated_qs().all()
        self.assertTrue(labs_urate_within_90_days(urates=urates_qs))
        empty_urates_qs = Urate.objects.none()
        self.assertFalse(labs_urate_within_90_days(urates=empty_urates_qs))
        old_urates_qs = urates_dated_qs().filter(date_drawn__lte=timezone.now() - timedelta(days=200))
        self.assertFalse(labs_urate_within_90_days(urates=old_urates_qs))


class TestLabsUratesMaxValue(TestCase):
    def test__raises_ValidationError(self):
        with self.assertRaises(ValidationError) as error:
            labs_urates_max_value(Decimal("31.0"))
        self.assertEqual(
            error.exception.messages[0],
            "Uric acid values above 30 mg/dL are very unlikely. \
If this value is correct, an emergency medical evaluation is warranted.",
        )

    def test__returns_correctly_None(self):
        self.assertIsNone(labs_urates_max_value(Decimal("12.0")))
