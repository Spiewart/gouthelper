from decimal import Decimal

import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...flares.tests.factories import CustomFlareFactory
from ...ults.tests.factories import create_ult
from ...users.tests.factories import create_psp
from ...utils.exceptions import GoutHelperValidationError
from ..api.mixins import MedHistoryAPIMixin
from ..choices import MedHistoryTypes
from ..models import Heartattack, MedHistory
from .factories import HeartattackFactory, PvdFactory

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
        heartattack = HeartattackFactory()
        self.api.check_for_medhistory_create_errors(heartattack, MedHistoryTypes.HEARTATTACK)
        self.assertTrue(self.api.errors)
        self.assertIn(
            ("heartattack", f"{heartattack} already exists."),
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

    def test__patient_has_medhistory_returns_False(self):
        self.api.patient = create_psp()
        self.assertFalse(self.api.patient_has_medhistory(MedHistoryTypes.HEARTATTACK))

    # Write tests for delete_medhistory
    def test__delete_medhistory(self):
        mh = HeartattackFactory()
        self.api.heartattack__value = None
        self.api.delete_medhistory(mh, MedHistoryTypes.HEARTATTACK)
        self.assertFalse(MedHistory.objects.filter(id=mh.id).exists())

    def test__delete_medhistory_raises_errors(self):
        mh = HeartattackFactory()
        self.api.heartattack__value = Decimal("1.0")
        with self.assertRaises(GoutHelperValidationError):
            self.api.delete_medhistory(mh, MedHistoryTypes.HEARTATTACK)
            self.assertTrue(self.api.errors)
            self.assertIn(
                ("heartattack__value", f"heartattack__value must be False to delete {mh}."),
                self.api.errors,
            )

    def test__check_for_medhistory_delete_errors_medhistory__value_not_False(self):
        mh = HeartattackFactory()
        self.api.heartattack__value = Decimal("1.0")
        self.api.check_for_medhistory_delete_errors(mh, MedHistoryTypes.HEARTATTACK)
        self.assertTrue(self.api.errors)
        self.assertIn(
            ("heartattack__value", f"heartattack__value must be False to delete {mh}."),
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

    def test__medhistory_needs_update_to_False(self):
        mh = HeartattackFactory()
        self.assertFalse(self.api.medhistory_needs_update(mh))

    def test__process_medhistory_create(self):
        self.api.pvd__value = True
        self.api.process_medhistory(
            mh_val=self.api.pvd__value,
            medhistory=None,
            medhistorytype=MedHistoryTypes.PVD,
        )
        self.assertTrue(MedHistory.objects.filter(medhistorytype=MedHistoryTypes.PVD).exists())
        self.assertEqual(self.api.pvd, MedHistory.objects.get(medhistorytype=MedHistoryTypes.PVD))

    def test__process_medhistory_delete(self):
        self.api.pvd__value = None
        mh = PvdFactory()
        self.api.pvd = mh
        self.api.process_medhistory(
            mh_val=self.api.pvd__value,
            medhistory=mh,
            medhistorytype=MedHistoryTypes.PVD,
        )
        self.assertFalse(MedHistory.objects.filter(medhistorytype=MedHistoryTypes.PVD).exists())
        self.assertIsNone(self.api.pvd)

    def test__process_medhistory_updates_user(self):
        mh = PvdFactory()
        self.api.pvd__value = True
        self.api.pvd = mh
        self.api.patient = create_psp()
        self.api.process_medhistory(
            mh_val=self.api.pvd__value,
            medhistory=mh,
            medhistorytype=MedHistoryTypes.PVD,
        )
        mh.refresh_from_db()
        self.assertEqual(mh.user, self.api.patient)

    def test__process_medhistory_updates_related_object(self):
        flare = CustomFlareFactory(pvd=False).create_object()
        mh = PvdFactory()
        self.api.add_mh_relation(flare)
        self.api.pvd__value = True
        self.api.pvd = mh
        self.api.process_medhistory(
            mh_val=self.api.pvd__value,
            medhistory=mh,
            medhistorytype=MedHistoryTypes.PVD,
        )
        self.assertEqual(mh.flare, flare)

    def test__process_medhistory_updates_unrelated_object(self):
        ult = create_ult()
        mh = PvdFactory()
        self.api.add_mh_relation(ult)
        self.api.pvd__value = True
        self.api.pvd = mh
        self.api.process_medhistory(
            mh_val=self.api.pvd__value,
            medhistory=mh,
            medhistorytype=MedHistoryTypes.PVD,
        )
        self.assertIsNone(mh.ult)

    def test__process_medhistory_user_and_related_object(self):
        self.api.patient = create_psp()
        flare = CustomFlareFactory(pvd=True).create_object()
        mh = flare.pvd
        self.api.add_mh_relation(flare)
        self.api.pvd__value = True
        self.api.pvd = mh
        self.api.process_medhistory(
            mh_val=self.api.pvd__value,
            medhistory=mh,
            medhistorytype=MedHistoryTypes.PVD,
        )
        self.assertEqual(mh.user, self.api.patient)
        self.assertIsNone(mh.flare)

    def test__get_queryset(self):
        self.api.heartattack = HeartattackFactory().id
        self.assertEqual(
            self.api.get_queryset(self.api.heartattack, MedHistoryTypes.HEARTATTACK).get(), Heartattack.objects.last()
        )
