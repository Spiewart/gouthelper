import pytest  # type: ignore
from django.db import IntegrityError  # type: ignore
from django.test import TestCase  # type: ignore

from ..choices import MedHistoryTypes
from ..models import MedHistory, Xoiinteraction
from .factories import MedHistoryFactory

pytestmark = pytest.mark.django_db


class TestMedHistory(TestCase):
    def setUp(self):
        for _ in range(10):
            MedHistoryFactory()
        self.medhistory = MedHistory.objects.last()

    def test__str__(self):
        self.assertEqual(str(self.medhistory), MedHistoryTypes(self.medhistory.medhistorytype).label)

    def test__medhistorytype_set_date_valid_constraint(self):
        with self.assertRaises(IntegrityError) as error:
            MedHistory.objects.create(medhistorytype=MedHistoryTypes.ANTICOAGULATION, set_date="2025-01-01")
        self.assertIn(
            "set_date_valid",
            str(error.exception),
        )

    def test__medhistorytype_valid_constraint(self):
        with self.assertRaises(IntegrityError) as error:
            MedHistory.objects.create(medhistorytype="invalid")
        self.assertIn(
            "medhistorytype_valid",
            str(error.exception),
        )


class TestMedHistoryDeleteSave(TestCase):
    def test__delete_creates_medhistory_history(self):
        """Test that deleting a MedHistory creates a MedHistory.history object."""
        # Count the number of MedHistory history objects with medhistorytype=MedHistoryTypes.ANGINA

        anginas = MedHistory.history.filter(medhistorytype=MedHistoryTypes.ANGINA).count()
        angina = MedHistoryFactory(medhistorytype=MedHistoryTypes.ANGINA)
        angina.delete()
        self.assertEqual(MedHistory.history.filter(medhistorytype=MedHistoryTypes.ANGINA).count(), anginas + 2)

    def test__save_creates_medhistory_history(self):
        """Test that saving a MedHistory creates a MedHistory.history object."""
        # Count the number of MedHistory history objects with medhistorytype=MedHistoryTypes.ANGINA
        anginas = MedHistory.history.filter(medhistorytype=MedHistoryTypes.ANGINA).count()
        angina = MedHistory(medhistorytype=MedHistoryTypes.ANGINA)
        angina.save()
        self.assertEqual(MedHistory.history.filter(medhistorytype=MedHistoryTypes.ANGINA).count(), anginas + 1)

    def test__save_adds_medhistorytype(self):
        xoiinteraction = Xoiinteraction()
        xoiinteraction.save()
        self.assertTrue(xoiinteraction.medhistorytype)
        self.assertEqual(xoiinteraction.medhistorytype, MedHistoryTypes.XOIINTERACTION)

    def test__save_without_clear_medhistorytype_raises_(self):
        medhistory = MedHistory()
        with self.assertRaises(ValueError) as error:
            medhistory.save()
        self.assertIn(
            f"MedHistoryType for {medhistory._meta.model.__name__.upper()} not found in MedHistoryTypes.",
            str(error.exception),
        )
