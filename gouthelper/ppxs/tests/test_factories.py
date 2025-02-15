from decimal import Decimal

import pytest
from django.test import TestCase  # type: ignore

from ...choices import BOOL_CHOICES
from ...labs.models import Urate
from ...labs.tests.factories import UrateFactory
from ...medhistorys.choices import MedHistoryTypes
from ...users.tests.factories import create_psp
from ..models import Ppx
from .factories import create_ppx, ppx_data_factory

pytestmark = pytest.mark.django_db


class TestPpxDataFactory(TestCase):
    def setUp(self):
        self.patient_with_ppx = create_psp()
        self.patient_ppx = create_ppx(patient=self.patient_with_ppx)
        self.patient_without_ppx = create_psp()
        self.ppx_no_patient = create_ppx()
        self.bools = [tup[0] for tup in BOOL_CHOICES]

    def test__without_patient(self):
        """Tests that the data factory returns a dict with the correct keys and values
        when called without a patient."""
        data = ppx_data_factory()
        assert isinstance(data, dict)
        self.assertIn(f"{MedHistoryTypes.GOUT}-value", data)
        self.assertTrue(data[f"{MedHistoryTypes.GOUT}-value"])
        self.assertIn("starting_ult", data)
        self.assertIn(data["starting_ult"], self.bools)
        self.assertIn("flaring", data)
        self.assertIn(data["flaring"], self.bools + [""])
        self.assertIn("at_goal", data)
        self.assertIn(data["at_goal"], self.bools + [""])
        self.assertIn("on_ppx", data)
        self.assertIn(data["on_ppx"], self.bools)
        self.assertIn("on_ult", data)
        self.assertIn(data["on_ult"], self.bools)

    def test__with_patient(self):
        """Tests that the data factory returns a dict with the correct keys and values
        when called with a patient."""
        data = ppx_data_factory(patient=self.patient_with_ppx)
        self.assertNotIn(f"{MedHistoryTypes.GOUT}-value", data)
        self.assertTrue(isinstance(data, dict))
        self.assertIn("starting_ult", data)
        self.assertEqual(data["starting_ult"], self.patient_ppx.starting_ult)
        self.assertIn("flaring", data)
        self.assertEqual(
            data["flaring"],
            self.patient_with_ppx.goutdetail.flaring if self.patient_with_ppx.goutdetail.flaring is not None else "",
        )
        self.assertIn("at_goal", data)
        self.assertEqual(
            data["at_goal"],
            self.patient_with_ppx.goutdetail.at_goal if self.patient_with_ppx.goutdetail.at_goal is not None else "",
        )
        self.assertIn("on_ppx", data)
        self.assertEqual(data["on_ppx"], self.patient_with_ppx.goutdetail.on_ppx)
        self.assertIn("on_ult", data)
        self.assertEqual(data["on_ult"], self.patient_with_ppx.goutdetail.on_ult)

    def test__with_patient_with_init_urates(self):
        """Test that the data returned contains information for the urates belonging to a patient."""
        UrateFactory.create_batch(3, patient=self.patient_with_ppx)
        urates = list(self.patient_with_ppx.urate_set.all())
        data = ppx_data_factory(patient=self.patient_with_ppx)
        for urate in urates:
            self.assertIn(urate.id, data.values())
        self.assertEqual(data["urate-INITIAL_FORMS"], len(urates))

    def test__with_ppx_with_patient(self):
        """Tests that the data factory returns a dict with the correct keys and values
        when called with a ppx with a patient."""
        data = ppx_data_factory(ppx=self.patient_ppx)
        self.assertNotIn(f"{MedHistoryTypes.GOUT}-value", data)
        self.assertTrue(isinstance(data, dict))
        self.assertIn("starting_ult", data)
        self.assertEqual(data["starting_ult"], self.patient_ppx.starting_ult)
        self.assertIn("flaring", data)
        self.assertEqual(
            data["flaring"],
            self.patient_with_ppx.goutdetail.flaring if self.patient_with_ppx.goutdetail.flaring is not None else "",
        )
        self.assertIn("at_goal", data)
        self.assertEqual(
            data["at_goal"],
            self.patient_with_ppx.goutdetail.at_goal if self.patient_with_ppx.goutdetail.at_goal is not None else "",
        )
        self.assertIn("on_ppx", data)
        self.assertEqual(data["on_ppx"], self.patient_with_ppx.goutdetail.on_ppx)
        self.assertIn("on_ult", data)
        self.assertEqual(data["on_ult"], self.patient_with_ppx.goutdetail.on_ult)

    def test__with_ppx_with_patient_with_init_urates(self):
        """Test that the data returned contains information for the urates belonging to a patient."""
        UrateFactory.create_batch(3, patient=self.patient_with_ppx)
        urates = self.patient_with_ppx.urate_set.all()
        data = ppx_data_factory(ppx=self.patient_ppx)
        for urate in urates:
            self.assertIn(urate.id, data.values())
        self.assertEqual(data["urate-INITIAL_FORMS"], len(urates))


class TestCreatePpx(TestCase):
    def test__create_ppx_without_patient(self):
        """Tests that the create_ppx function returns a Ppx object with the requisite
        MedHistory related objects."""
        ppx = create_ppx()
        assert isinstance(ppx, Ppx)
        assert ppx.medhistory_set.exists()
        assert MedHistoryTypes.GOUT in [mh.medhistorytype for mh in ppx.medhistory_set.all()]
        assert hasattr(ppx.gout, "goutdetail")
        assert hasattr(ppx, "urates_qs")
        if ppx.urates_qs:
            for urate in ppx.urates_qs:
                assert isinstance(urate, Urate)
                assert urate.value

    def test__create_ppx_with_patient(self):
        """Tests that the create_ppx function returns a Ppx object with the requisite
        MedHistory related objects and a patient."""
        ppx = create_ppx(patient=True)
        assert isinstance(ppx, Ppx)
        assert not ppx.medhistory_set.exists()
        assert ppx.patient
        assert ppx.patient.medhistory_set.exists()
        assert MedHistoryTypes.GOUT in [mh.medhistorytype for mh in ppx.patient.medhistory_set.all()]
        assert hasattr(ppx.patient.gout, "goutdetail")
        assert hasattr(ppx, "urates_qs")
        if ppx.urates_qs:
            for urate in ppx.urates_qs:
                assert isinstance(urate, Urate)
                assert urate.value
                assert urate.patient == ppx.patient

    def test__create_ppx_with_urates(self):
        """Tests that the create_ppx function returns a Ppx object with the requisite
        MedHistory related objects and Urates with the supplied values."""
        ppx = create_ppx(patient=True, labs=[Decimal("15.0"), Decimal("12.0")])
        assert isinstance(ppx, Ppx)
        assert not ppx.medhistory_set.exists()
        assert ppx.patient
        assert ppx.patient.medhistory_set.exists()
        assert MedHistoryTypes.GOUT in [mh.medhistorytype for mh in ppx.patient.medhistory_set.all()]
        assert hasattr(ppx.patient.gout, "goutdetail")
        assert hasattr(ppx, "urates_qs")
        assert next(iter([urate for urate in ppx.urates_qs if urate.value == Decimal("15.0")]))
        assert next(iter([urate for urate in ppx.urates_qs if urate.value == Decimal("12.0")]))
        for urate in ppx.urates_qs:
            assert isinstance(urate, Urate)
            assert urate.patient == ppx.patient
