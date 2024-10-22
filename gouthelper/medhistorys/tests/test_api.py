from decimal import Decimal

import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...flares.tests.factories import CustomFlareFactory
from ...users.tests.factories import create_psp
from ...utils.exceptions import GoutHelperValidationError
from ..api.mixins import MedHistoryAPIMixin
from ..choices import MedHistoryTypes
from ..models import Heartattack, MedHistory
from .factories import HeartattackFactory

pytestmark = pytest.mark.django_db


class TestMedHistoryAPIMixin(TestCase):
    """Test suite for MedHistoryAPIMixin."""

    def setUp(self):
        self.api = MedHistoryAPIMixin()
        self.api.patient = None
        self.api.mh_relations = []

    def test__create_medhistory(self):
        mh = self.api.create_medhistory(
            medhistory=None,
            medhistorytype=MedHistoryTypes.HEARTATTACK,
        )
        self.assertTrue(isinstance(mh, MedHistory))

    def test__add_mh_relation(self):
        flare = CustomFlareFactory()
        self.api.add_mh_relation(relation=flare)
        self.assertEqual(len(self.api.mh_relations), 1)
        self.assertEqual(self.api.mh_relations[0], flare)

    def test__check_for_medhistory_create_errors_medhistory_exists(self):
        self.api.medhistory = HeartattackFactory()
        self.api.check_for_medhistory_create_errors(self.api.medhistory, MedHistoryTypes.HEARTATTACK)
        self.assertTrue(self.api.errors)
        self.assertIn(
            ("heartattack", f"{self.api.medhistory} already exists."),
            self.api.errors,
        )

    def test__check_for_medhistory_create_errors_patient_has_medhistory(self):
        patient = create_psp()
        mh = HeartattackFactory(user=patient)
        self.api.patient = patient
        self.api.check_for_medhistory_create_errors(mh, MedHistoryTypes.HEARTATTACK)
        self.assertTrue(self.api.errors)
        self.assertIn(
            ("heartattack", f"{patient} already has a {patient.heartattack}."),
            self.api.errors,
        )

    def test__patient_has_medhistory(self):
        self.api.patient = create_psp()
        mh = HeartattackFactory(user=self.api.patient)
        self.assertTrue(self.api.patient_has_medhistory(mh.medhistorytype))
        self.assertFalse(self.api.patient_has_medhistory(MedHistoryTypes.CKD))

    # Write tests for delete_medhistory
    def test__delete_medhistory(self):
        mh = HeartattackFactory()
        self.api.heartattack__value = None
        self.api.delete_medhistory(mh)
        self.assertFalse(MedHistory.objects.filter(id=mh.id).exists())

    def test__delete_medhistory_raises_errors(self):
        mh = HeartattackFactory()
        self.api.heartattack__value = Decimal("1.0")
        with self.assertRaises(GoutHelperValidationError):
            self.api.delete_medhistory(mh)
            self.assertTrue(self.api.errors)
            self.assertIn(
                ("heartattack__value", f"heartattack__value must be False to delete {mh}."),
                self.api.errors,
            )

    def test__check_for_medhistory_delete_errors_medhistory__value_not_False(self):
        mh = HeartattackFactory()
        self.api.heartattack__value = Decimal("1.0")
        self.api.check_for_medhistory_delete_errors(mh)
        self.assertTrue(self.api.errors)
        self.assertIn(
            ("heartattack__value", f"heartattack__value must be False to delete {mh}."),
            self.api.errors,
        )

    def test__check_for_medhistory_delete_errors_medhistory_is_None(self):
        self.api.medhistory = None
        self.api.medhistorytype = MedHistoryTypes.HEARTATTACK
        self.api.check_for_medhistory_delete_errors(self.api.medhistory)
        self.assertTrue(self.api.errors)
        self.assertIn(
            ("heartattack", "heartattack does not exist."),
            self.api.errors,
        )

    def test__get_medhistory_model_from_medhistorytype(self):
        self.assertEqual(
            self.api.get_medhistory_model_from_medhistorytype(MedHistoryTypes.HEARTATTACK),
            Heartattack,
        )

    def test__medhistory_needs_update_to_user(self):
        mh = HeartattackFactory()
        self.api.patient = create_psp()
        self.assertTrue(self.api.medhistory_needs_update(mh))

    def test__medhistory_needs_update_to_flare(self):
        flare = CustomFlareFactory().create_object()
        mh = HeartattackFactory()
        self.api.add_mh_relation(flare)
        self.assertTrue(self.api.medhistory_needs_update(mh))
