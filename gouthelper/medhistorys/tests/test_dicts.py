from django.test import TestCase  # type: ignore

from ...flareaids.models import FlareAid
from ...flares.models import Flare
from ...flares.tests.factories import create_flare
from ...medhistorys.lists import FLARE_MEDHISTORYS
from ...ppxaids.models import PpxAid
from ...ultaids.models import UltAid
from ...ults.models import Ult
from ...users.models import Pseudopatient
from ...users.tests.factories import create_psp
from ..choices import MedHistoryTypes
from ..dicts import MedHistoryTypesAids


class TestGetMedHistorytypeAids(TestCase):
    # Write tests for each MedHistoryType calling MedHistoryTypesAids and
    # testing that it returns a dict with the MedHistoryType as the key and the
    # aid types, per medhistorys/lists.py, as the value.
    def test__angina(self):
        aid_dict = MedHistoryTypesAids(MedHistoryTypes.ANGINA).get_medhistorytypes_aid_dict()
        self.assertTrue(isinstance(aid_dict, dict))
        self.assertIn(MedHistoryTypes.ANGINA, aid_dict)
        aid_list = aid_dict.get(MedHistoryTypes.ANGINA)
        self.assertTrue(isinstance(aid_list, list))
        self.assertIn(Flare, aid_list)
        self.assertIn(FlareAid, aid_list)
        self.assertIn(PpxAid, aid_list)
        self.assertIn(UltAid, aid_list)
        self.assertEqual(len(aid_list), 4)

    def test__anticoagulation(self):
        aid_dict = MedHistoryTypesAids(MedHistoryTypes.ANTICOAGULATION).get_medhistorytypes_aid_dict()
        self.assertTrue(isinstance(aid_dict, dict))
        self.assertIn(MedHistoryTypes.ANTICOAGULATION, aid_dict)
        aid_list = aid_dict.get(MedHistoryTypes.ANTICOAGULATION)
        self.assertTrue(isinstance(aid_list, list))
        self.assertIn(FlareAid, aid_list)
        self.assertIn(PpxAid, aid_list)
        self.assertEqual(len(aid_list), 2)

    def test__bleed(self):
        aid_dict = MedHistoryTypesAids(MedHistoryTypes.BLEED).get_medhistorytypes_aid_dict()
        self.assertTrue(isinstance(aid_dict, dict))
        self.assertIn(MedHistoryTypes.BLEED, aid_dict)
        aid_list = aid_dict.get(MedHistoryTypes.BLEED)
        self.assertTrue(isinstance(aid_list, list))
        self.assertIn(FlareAid, aid_list)
        self.assertIn(PpxAid, aid_list)
        self.assertEqual(len(aid_list), 2)

    def test__cad(self):
        aid_dict = MedHistoryTypesAids(MedHistoryTypes.CAD).get_medhistorytypes_aid_dict()
        self.assertTrue(isinstance(aid_dict, dict))
        self.assertIn(MedHistoryTypes.CAD, aid_dict)
        aid_list = aid_dict.get(MedHistoryTypes.CAD)
        self.assertTrue(isinstance(aid_list, list))
        self.assertIn(Flare, aid_list)
        self.assertIn(FlareAid, aid_list)
        self.assertIn(PpxAid, aid_list)
        self.assertIn(UltAid, aid_list)
        self.assertEqual(len(aid_list), 4)

    def test__chf(self):
        aid_dict = MedHistoryTypesAids(MedHistoryTypes.CHF).get_medhistorytypes_aid_dict()
        self.assertTrue(isinstance(aid_dict, dict))
        self.assertIn(MedHistoryTypes.CHF, aid_dict)
        aid_list = aid_dict.get(MedHistoryTypes.CHF)
        self.assertTrue(isinstance(aid_list, list))
        self.assertIn(Flare, aid_list)
        self.assertIn(FlareAid, aid_list)
        self.assertIn(PpxAid, aid_list)
        self.assertIn(UltAid, aid_list)
        self.assertEqual(len(aid_list), 4)

    def test__ckd(self):
        aid_dict = MedHistoryTypesAids(MedHistoryTypes.CKD).get_medhistorytypes_aid_dict()
        self.assertTrue(isinstance(aid_dict, dict))
        self.assertIn(MedHistoryTypes.CKD, aid_dict)
        aid_list = aid_dict.get(MedHistoryTypes.CKD)
        self.assertTrue(isinstance(aid_list, list))
        self.assertIn(Flare, aid_list)
        self.assertIn(FlareAid, aid_list)
        self.assertIn(PpxAid, aid_list)
        self.assertIn(UltAid, aid_list)
        self.assertIn(Ult, aid_list)
        self.assertEqual(len(aid_list), 5)

    def test__hepatitis(self):
        aid_dict = MedHistoryTypesAids(MedHistoryTypes.HEPATITIS).get_medhistorytypes_aid_dict()
        self.assertTrue(isinstance(aid_dict, dict))
        self.assertIn(MedHistoryTypes.HEPATITIS, aid_dict)
        aid_list = aid_dict.get(MedHistoryTypes.HEPATITIS)
        self.assertTrue(isinstance(aid_list, list))
        self.assertIn(UltAid, aid_list)
        self.assertEqual(len(aid_list), 1)

    def test__with_patient(self):
        for _ in range(5):
            flare = create_flare(user=create_psp())
            aid_dict = MedHistoryTypesAids(
                FLARE_MEDHISTORYS, patient=Pseudopatient.objects.flares_qs().filter(pk=flare.user.pk).get()
            ).get_medhistorytypes_aid_dict()
            for medhistorytype in FLARE_MEDHISTORYS:
                self.assertIn(medhistorytype, aid_dict)
                aid_list = aid_dict.get(medhistorytype)
                self.assertTrue(isinstance(aid_list, list))
                self.assertIn(Flare, aid_list)
