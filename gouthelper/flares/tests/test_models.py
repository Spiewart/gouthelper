from datetime import timedelta

import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ...medhistorys.tests.factories import AllopurinolhypersensitivityFactory, CkdFactory
from ..services import FlareDecisionAid
from .factories import FlareFactory

pytestmark = pytest.mark.django_db


class TestFlareMethods(TestCase):
    def setUp(self):
        self.flare = FlareFactory()

    def test__add_medhistorys_adds_flare_medhistory(self):
        ckd = CkdFactory()
        self.flare.add_medhistorys([ckd])
        self.assertIn(ckd, self.flare.medhistorys.all())

    def test__add_medhistorys_raises_TypeError_with_non_flare_medhistory(self):
        allopurinolhypersensitivity = AllopurinolhypersensitivityFactory()
        with self.assertRaises(TypeError) as error:
            self.flare.add_medhistorys([allopurinolhypersensitivity])
        self.assertEqual(
            f"{allopurinolhypersensitivity} is not a valid MedHistory for {self.flare}",
            str(error.exception),
        )

    def test__remove_medhistorys_removes_medhistory(self):
        ckd = CkdFactory()
        self.flare.medhistorys.add(ckd)
        self.flare.update()
        self.flare.refresh_from_db()
        self.flare.remove_medhistorys([ckd])
        self.assertNotIn(ckd, self.flare.medhistorys.all())

    def test__duration_returns_timedelta(self):
        duration = self.flare.duration
        self.assertTrue(isinstance(duration, timedelta))
        self.assertEqual(duration, timezone.now().date() - self.flare.date_started)

    def test__update(self):
        self.assertIsNone(self.flare.prevalence)
        self.assertIsNone(self.flare.likelihood)
        self.flare.update()
        self.flare.refresh_from_db()
        self.assertIsNotNone(self.flare.prevalence)
        self.assertIsNotNone(self.flare.likelihood)

    def test__update_with_kwarg(self):
        self.flare.update()
        decisionaid = FlareDecisionAid(pk=self.flare.pk)
        self.assertEqual(self.flare, self.flare.update(decisionaid=decisionaid))
