import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...ppxaids.tests.factories import create_ppxaid
from ..choices import Treatments
from ..helpers import treatments_stringify_trt_tuple

pytestmark = pytest.mark.django_db


class TestTreatmentsStringifyTrtTuple(TestCase):
    def setUp(self):
        self.ppxaid = create_ppxaid(mhs=[], mas=[])
        self.trt = next(iter(self.ppxaid.options))
        self.dosing = self.ppxaid.options[self.trt]

    def test__stringify_trt_tuple(self):
        trt, dosing_str = treatments_stringify_trt_tuple(trt=self.trt, dosing=self.dosing)
        for val in dosing_str.values():
            self.assertTrue(isinstance(val, str) if val else True)
        keys = dosing_str.keys()
        self.assertIn("dose", keys)
        self.assertIn("dose2", keys)
        self.assertIn("dose3", keys)
        self.assertIn("freq", keys)
        self.assertIn("freq2", keys)
        self.assertIn("freq3", keys)
        self.assertIn("duration", keys)
        self.assertIn("duration2", keys)
        self.assertIn("duration3", keys)
        self.assertIn("dose_adj", keys)
        self.assertEqual(trt, Treatments(self.trt).label)
