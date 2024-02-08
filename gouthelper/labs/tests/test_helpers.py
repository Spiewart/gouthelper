from datetime import timedelta
from decimal import Decimal

import pytest  # type: ignore
from django.core.exceptions import ValidationError  # type: ignore
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ...genders.choices import Genders
from ...labs.models import Urate
from ...labs.tests.factories import BaselineCreatinineFactory
from ...medhistorydetails.tests.factories import GoutDetailFactory
from ...medhistorys.tests.factories import GoutFactory
from ..helpers import (
    labs_baselinecreatinine_max_value,
    labs_eGFR_calculator,
    labs_round_decimal,
    labs_stage_calculator,
    labs_urates_chronological_dates,
    labs_urates_hyperuricemic,
    labs_urates_last_at_goal,
    labs_urates_max_value,
    labs_urates_months_at_goal,
    labs_urates_recent_urate,
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
            labs_urates_chronological_dates(
                current_urate=urate,
                previous_urate=self.urate_qs[ui - 1] if ui > 0 else None,
                first_urate=self.urate_qs[0],
            )

    def test__raises_ValueError_no_date_attr(self):
        with self.assertRaises(ValueError) as error:
            labs_urates_chronological_dates(
                current_urate=self.urate_qs_no_date[0],
                previous_urate=self.urate_qs_no_date[1],
                first_urate=self.urate_qs_no_date[0],
            )
        self.assertEqual(
            error.exception.args[0], f"Urate {self.urate_qs_no_date[0]} has no date_drawn, Flare, or annotated date."
        )

    def test__raises_ValueError_not_in_order(self):
        with self.assertRaises(ValueError) as error:
            for ui, urate in enumerate(self.urate_list):
                labs_urates_chronological_dates(
                    current_urate=urate,
                    previous_urate=self.urate_list[ui - 1] if ui > 0 else None,
                    first_urate=self.urate_list[0],
                )
        self.assertEqual(
            error.exception.args[0], "The Urates are not in chronological order. QuerySet must be ordered by date."
        )


class TestLabsUratesHyperuricemic(TestCase):
    """Tests for the labs_urates_hyperuricemic() method."""

    def test__returns_True(self):
        UrateFactory(value=Decimal("10.0"))
        urate_qs = urates_dated_qs().all()
        self.assertTrue(labs_urates_hyperuricemic(urates=urate_qs))

    def test__returns_False(self):
        UrateFactory(value=Decimal("5.0"))
        urate_qs = urates_dated_qs().all()
        self.assertFalse(labs_urates_hyperuricemic(urates=urate_qs))

    def test__changes_goutdetail(self):
        """Test that the method changes the GoutDetail associated with the Gout MedHistory
        object."""
        gout = GoutFactory(set_date=timezone.now() - timedelta(days=1))
        goutdetail = GoutDetailFactory(medhistory=gout, hyperuricemic=False)
        UrateFactory(value=Decimal("10.0"))
        urate_qs = urates_dated_qs().all()
        self.assertTrue(labs_urates_hyperuricemic(urates=urate_qs, goutdetail=goutdetail))
        # Check to make sure the GoutDetail object has changed
        self.assertTrue(goutdetail.hyperuricemic)

    def test__doesnt_change_more_recent_gout_goutdetail(self):
        """Tests that the method doesn't change the GoutDetail associated with a more
        recent Gout MedHistory object."""
        gout = GoutFactory(set_date=timezone.now() - timedelta(days=1))
        goutdetail = GoutDetailFactory(medhistory=gout, hyperuricemic=False)
        UrateFactory(value=Decimal("10.0"), date_drawn=timezone.now() - timedelta(days=5))
        urate_qs = urates_dated_qs().all()
        self.assertTrue(labs_urates_hyperuricemic(urates=urate_qs, goutdetail=goutdetail))
        # Check to make sure the GoutDetail object hasn't changed
        self.assertFalse(goutdetail.hyperuricemic)


class TestLabsUratesLastAtGoal(TestCase):
    def setUp(self):
        # Create some urates, last not at goal
        UrateFactory(value=Decimal("7.0"), date_drawn=timezone.now() - timedelta(days=10))
        UrateFactory(value=Decimal("6.0"), date_drawn=timezone.now() - timedelta(days=50))
        UrateFactory(value=Decimal("15.0"), date_drawn=timezone.now() - timedelta(days=100))
        self.gout = GoutFactory()
        self.goutdetail = GoutDetailFactory(medhistory=self.gout, hyperuricemic=True)

    def test__returns_correctly(self):
        urate_qs = urates_dated_qs().all()
        self.assertFalse(labs_urates_last_at_goal(urates=urate_qs))
        UrateFactory(value=Decimal("5.0"), date_drawn=timezone.now() - timedelta(days=5))
        urate_qs = urates_dated_qs().all()
        self.assertTrue(labs_urates_last_at_goal(urates=urate_qs))

    def test__modifies_goutdetail(self):
        self.assertTrue(self.goutdetail.hyperuricemic)
        UrateFactory(value=Decimal("5.0"), date_drawn=timezone.now() - timedelta(days=5))
        urate_qs = urates_dated_qs().all()
        self.assertTrue(labs_urates_last_at_goal(urates=urate_qs, goutdetail=self.goutdetail))
        self.assertFalse(self.goutdetail.hyperuricemic)

    def test__doesnt_modify_goutdetail_commit_False(self):
        self.assertTrue(self.goutdetail.hyperuricemic)
        UrateFactory(value=Decimal("5.0"), date_drawn=timezone.now() - timedelta(days=5))
        urate_qs = urates_dated_qs().all()
        self.assertTrue(labs_urates_last_at_goal(urates=urate_qs, goutdetail=self.goutdetail, commit=False))
        self.assertTrue(self.goutdetail.hyperuricemic)

    def test__doesnt_modify_goutdetail_gout_set_date_more_recent(self):
        self.gout.set_date = timezone.now()
        self.gout.save()
        self.assertTrue(self.goutdetail.hyperuricemic)
        UrateFactory(value=Decimal("5.0"), date_drawn=timezone.now() - timedelta(days=5))
        urate_qs = urates_dated_qs().all()
        self.assertTrue(labs_urates_last_at_goal(urates=urate_qs, goutdetail=self.goutdetail))
        self.assertTrue(self.goutdetail.hyperuricemic)

    def test__not_sorted_raises_ValueError(self):
        urates = urates_dated_qs().all()
        urates = sorted(urates, key=lambda x: x.date_drawn, reverse=False)
        with self.assertRaises(ValueError) as error:
            labs_urates_last_at_goal(urates=urates)
        self.assertEqual(
            error.exception.args[0], "The Urates are not in chronological order. QuerySet must be ordered by date."
        )

    def test__not_sorted_urates_sorted_False_returns_correctly(self):
        urates = urates_dated_qs().all()
        urates = sorted(urates, key=lambda x: x.date_drawn, reverse=False)
        self.assertFalse(labs_urates_last_at_goal(urates=urates, urates_sorted=False))


class TestLabsUrateMonthsAtGoal(TestCase):
    """These tests use the urates_dated_qs() queryset, which is a custom queryset
    that annotates each Urate with a date attr that is the date_drawn if it exists,
    or the Flare.date_started if it doesn't. This is because Flare objects don't
    require reporting a date_drawn for the Urate, but Urate's entered elsewhere do."""

    def test__returns_True(self):
        UrateFactory(value=5.0, date_drawn=timezone.now())
        UrateFactory(value=6.0, date_drawn=timezone.now() - timedelta(days=190))
        urate_qs = urates_dated_qs().all()
        self.assertTrue(labs_urates_months_at_goal(urates=urate_qs))

    def test__at_goal_not_six_months_returns_False(self):
        UrateFactory(value=5.0, date_drawn=timezone.now())
        UrateFactory(value=6.0, date_drawn=timezone.now() - timedelta(days=150))
        urate_qs = urates_dated_qs().all()
        self.assertFalse(labs_urates_months_at_goal(urates=urate_qs))

    def test__not_at_goal_returns_False(self):
        UrateFactory(value=5.0, date_drawn=timezone.now())
        UrateFactory(value=6.0, date_drawn=timezone.now() - timedelta(days=110))
        UrateFactory(value=7.0, date_drawn=timezone.now() - timedelta(days=170))
        urate_qs = urates_dated_qs().all()
        self.assertFalse(labs_urates_months_at_goal(urates=urate_qs))

    def test__most_recent_not_at_goal_returns_False(self):
        UrateFactory(value=10.0, date_drawn=timezone.now())
        UrateFactory(value=6.0, date_drawn=timezone.now() - timedelta(days=90))
        UrateFactory(value=4.0, date_drawn=timezone.now() - timedelta(days=170))
        urate_qs = urates_dated_qs().all()
        self.assertFalse(labs_urates_months_at_goal(urates=urate_qs))

    def test__doesnt_change_more_recent_gout_goutdetail(self):
        """Tests that the method doesn't change the GoutDetail associated with a more
        recent Gout MedHistory object."""
        gout = GoutFactory(set_date=timezone.now() - timedelta(days=1))
        goutdetail = GoutDetailFactory(medhistory=gout, hyperuricemic=True)
        UrateFactory(value=5.0, date_drawn=timezone.now() - timedelta(days=5))
        UrateFactory(value=6.0, date_drawn=timezone.now() - timedelta(days=190))
        urate_qs = urates_dated_qs().all()
        self.assertTrue(labs_urates_months_at_goal(urates=urate_qs, goutdetail=goutdetail))
        # Check to make sure the GoutDetail object hasn't changed
        self.assertTrue(goutdetail.hyperuricemic)


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
        self.assertTrue(labs_urates_recent_urate(urates=urates_qs))
        empty_urates_qs = Urate.objects.none()
        self.assertFalse(labs_urates_recent_urate(urates=empty_urates_qs))
        old_urates_qs = urates_dated_qs().filter(date_drawn__lte=timezone.now() - timedelta(days=200))
        self.assertFalse(labs_urates_recent_urate(urates=old_urates_qs))


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
