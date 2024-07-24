from django.test import TestCase  # type: ignore

from ...flares.models import Flare
from ...flares.tests.factories import create_flare
from ...medhistorys.lists import FLARE_MEDHISTORYS, PPX_MEDHISTORYS, ULTAID_MEDHISTORYS
from ...ultaids.models import UltAid
from ...ultaids.tests.factories import create_ultaid
from ...users.models import Pseudopatient
from ...users.tests.factories import create_psp
from ..dicts import MedHistoryTypesAids, get_dict_of_aid_tuple_of_model_and_medhistorytypes


class TestGetMedHistorytypeAids(TestCase):
    def setUp(self):
        self.patient = create_psp(plus=True)
        self.patient_ultaid = create_ultaid(user=self.patient)
        self.user_mhtype_aids = MedHistoryTypesAids(ULTAID_MEDHISTORYS, self.patient)
        self.flare = create_flare()
        self.flare_mhtype_aids = MedHistoryTypesAids(FLARE_MEDHISTORYS, self.flare)

    def test__init__sets_mhtypes(self):
        self.assertEqual(self.user_mhtype_aids.mhtypes, ULTAID_MEDHISTORYS)
        self.assertEqual(self.flare_mhtype_aids.mhtypes, FLARE_MEDHISTORYS)

    def test__init__sets_related_object(self):
        self.assertEqual(self.user_mhtype_aids.related_object, self.patient)
        self.assertEqual(self.flare_mhtype_aids.related_object, self.flare)

    def test__init__sets_dict_of_aid_tuple_of_model_and_medhistorytypes(self):
        self.assertEqual(
            self.user_mhtype_aids.dict_of_aid_tuple_of_model_and_medhistorytypes,
            get_dict_of_aid_tuple_of_model_and_medhistorytypes(),
        )
        self.assertEqual(
            self.flare_mhtype_aids.dict_of_aid_tuple_of_model_and_medhistorytypes,
            get_dict_of_aid_tuple_of_model_and_medhistorytypes(),
        )

    def test__init_sets_aid_attr_and_aid_medhistorys(self):
        self.assertEqual(self.user_mhtype_aids.UltAid, UltAid)
        self.assertEqual(self.user_mhtype_aids.ULTAID_MEDHISTORYS, ULTAID_MEDHISTORYS)
        self.assertEqual(self.flare_mhtype_aids.Flare, Flare)
        self.assertEqual(self.flare_mhtype_aids.FLARE_MEDHISTORYS, FLARE_MEDHISTORYS)

    def test__mhtype_in_related_objects_medhistorys(self) -> None:
        for mhtype in ULTAID_MEDHISTORYS:
            self.assertTrue(self.user_mhtype_aids.mhtype_in_related_objects_medhistorys(mhtype, UltAid))
        for mhtype in PPX_MEDHISTORYS:
            if mhtype not in ULTAID_MEDHISTORYS:
                self.assertFalse(self.user_mhtype_aids.mhtype_in_related_objects_medhistorys(mhtype, UltAid))
        for mhtype in FLARE_MEDHISTORYS:
            self.assertTrue(self.flare_mhtype_aids.mhtype_in_related_objects_medhistorys(mhtype, Flare))
        for mhtype in ULTAID_MEDHISTORYS:
            if mhtype not in FLARE_MEDHISTORYS:
                self.assertFalse(self.flare_mhtype_aids.mhtype_in_related_objects_medhistorys(mhtype, Flare))

    def test__related_object_is_or_has_aid_type(self) -> None:
        self.assertTrue(self.user_mhtype_aids.related_object_is_or_has_aid_type("ultaid", UltAid))
        self.assertFalse(self.user_mhtype_aids.related_object_is_or_has_aid_type("flare", Flare))
        self.assertTrue(self.flare_mhtype_aids.related_object_is_or_has_aid_type("flare", Flare))
        self.assertFalse(self.flare_mhtype_aids.related_object_is_or_has_aid_type("ultaid", UltAid))
        user_ultaid_mhtype_aids = MedHistoryTypesAids(ULTAID_MEDHISTORYS, self.patient_ultaid)
        with self.assertRaises(ValueError):
            user_ultaid_mhtype_aids.related_object_is_or_has_aid_type("ultaid", UltAid)
        no_related_object_mhtype_aids = MedHistoryTypesAids(ULTAID_MEDHISTORYS)
        with self.assertRaises(ValueError):
            no_related_object_mhtype_aids.related_object_is_or_has_aid_type("ultaid", UltAid)

    def test__related_object_error_check(self) -> None:
        self.assertIsNone(self.user_mhtype_aids.related_object_error_check())
        self.assertIsNone(self.flare_mhtype_aids.related_object_error_check())
        user_ultaid_mhtype_aids = MedHistoryTypesAids(ULTAID_MEDHISTORYS, self.patient_ultaid)
        with self.assertRaises(ValueError):
            user_ultaid_mhtype_aids.related_object_error_check()
        no_related_object_mhtype_aids = MedHistoryTypesAids(ULTAID_MEDHISTORYS)
        with self.assertRaises(ValueError):
            no_related_object_mhtype_aids.related_object_error_check()

    def test__mhtype_in_aid_medhistorys(self) -> None:
        for mhtype in ULTAID_MEDHISTORYS:
            self.assertTrue(self.user_mhtype_aids.mhtype_in_aid_medhistorys(mhtype, "ultaid"))
        for mhtype in PPX_MEDHISTORYS:
            if mhtype not in ULTAID_MEDHISTORYS:
                self.assertFalse(self.user_mhtype_aids.mhtype_in_aid_medhistorys(mhtype, "ultaid"))
        for mhtype in FLARE_MEDHISTORYS:
            self.assertTrue(self.flare_mhtype_aids.mhtype_in_aid_medhistorys(mhtype, "flare"))
        for mhtype in ULTAID_MEDHISTORYS:
            if mhtype not in FLARE_MEDHISTORYS:
                self.assertFalse(self.flare_mhtype_aids.mhtype_in_aid_medhistorys(mhtype, "flare"))

    def test__related_object_is_or_has_flare(self) -> None:
        flare = create_flare()
        flare_mhtype_aids = MedHistoryTypesAids(FLARE_MEDHISTORYS, flare)
        self.assertTrue(flare_mhtype_aids.related_object_is_or_has_flare)
        self.assertFalse(self.user_mhtype_aids.related_object_is_or_has_flare)
        create_flare(user=self.patient)
        user_with_flare_qs = Pseudopatient.objects.flares_qs().filter(pk=self.patient.pk).first()
        user_with_flare_qs_mhtype_aids = MedHistoryTypesAids(FLARE_MEDHISTORYS, user_with_flare_qs)
        self.assertTrue(user_with_flare_qs_mhtype_aids.related_object_is_or_has_flare)

    def test__mhtype_in_related_object_aid(self) -> None:
        for mhtype in ULTAID_MEDHISTORYS:
            self.assertTrue(self.user_mhtype_aids.mhtype_in_related_object_aid(mhtype))
        for mhtype in PPX_MEDHISTORYS:
            if mhtype not in ULTAID_MEDHISTORYS:
                self.assertFalse(self.user_mhtype_aids.mhtype_in_related_object_aid(mhtype))
        for mhtype in FLARE_MEDHISTORYS:
            self.assertTrue(self.flare_mhtype_aids.mhtype_in_related_object_aid(mhtype))
        for mhtype in ULTAID_MEDHISTORYS:
            if mhtype not in FLARE_MEDHISTORYS:
                self.assertFalse(self.flare_mhtype_aids.mhtype_in_related_object_aid(mhtype))
