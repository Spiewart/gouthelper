from decimal import Decimal

import pytest  # pylint: disable=E0401  # type: ignore
from django.test import TestCase  # pylint: disable=E0401  # type: ignore
from faker import Faker  # pylint: disable=E0401  # type: ignore

from ...genders.choices import Genders
from ..choices import DialysisChoices, DialysisDurations, Stages
from .helpers import update_or_create_ckddetail_kwargs

pytestmark = pytest.mark.django_db

fake = Faker()

ModDialysisDurations = DialysisDurations.values
ModDialysisDurations.remove("")
ModStages = Stages.values
ModStages.remove(None)


class TestUpdateOrCreateCkdDetailKwargs(TestCase):
    def test__creates_random_ckddetail_kwargs(self):
        kwargs_list = []
        for _ in range(50):
            demographic_kwargs = {}
            if fake.boolean():
                demographic_kwargs.update(
                    {"age": fake.random_int(min=18, max=100), "gender": fake.random_element(Genders)}
                )
            kwargs = update_or_create_ckddetail_kwargs(**demographic_kwargs)
            kwargs_list.append(kwargs)
            self.assertIn("baselinecreatinine", kwargs)
            if kwargs["baselinecreatinine"]:
                self.assertIsInstance(kwargs["baselinecreatinine"], Decimal)
            self.assertIn("dialysis", kwargs)
            if kwargs["dialysis"]:
                self.assertIsInstance(kwargs["dialysis"], bool)
            self.assertIn("dialysis_duration", kwargs)
            if kwargs["dialysis_duration"]:
                self.assertIn(kwargs["dialysis_duration"], DialysisDurations.values)
            self.assertIn("dialysis_type", kwargs)
            if kwargs["dialysis_type"]:
                self.assertIn(kwargs["dialysis_type"], DialysisChoices.values)
            self.assertIn("stage", kwargs)
            if kwargs["stage"]:
                self.assertIn(kwargs["stage"], Stages.values)
        self.assertTrue(
            next(iter(kwargs for kwargs in kwargs_list if kwargs["baselinecreatinine"] is not None)), False
        )
        self.assertTrue(
            next(
                iter(
                    kwargs
                    for kwargs in kwargs_list
                    if kwargs["baselinecreatinine"] is not None and kwargs["stage"] is not None
                )
            ),
            False,
        )
        self.assertTrue(
            next(iter(kwargs for kwargs in kwargs_list if kwargs["dialysis"] is True)),
            False,
        )
        self.assertTrue(
            next(iter(kwargs for kwargs in kwargs_list if not kwargs["dialysis"])),
            False,
        )
        for dialysis_type in DialysisChoices.values:
            self.assertTrue(
                next(
                    iter(kwargs for kwargs in kwargs_list if kwargs["dialysis_type"] == dialysis_type),
                    False,
                )
            )
        for dialysis_duration in ModDialysisDurations:
            self.assertTrue(
                next(
                    iter(kwargs for kwargs in kwargs_list if kwargs["dialysis_duration"] == dialysis_duration),
                    False,
                )
            )
        for stage in ModStages:
            self.assertTrue(next(iter(kwargs for kwargs in kwargs_list if kwargs["stage"] == stage), False))
