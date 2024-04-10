import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...defaults.models import UltAidSettings
from ...ethnicitys.choices import Ethnicitys
from ...ethnicitys.tests.factories import EthnicityFactory
from ...goalurates.tests.factories import create_goalurate
from ...labs.tests.factories import Hlab5801Factory
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorydetails.choices import Stages
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import ULTAID_MEDHISTORYS
from ...medhistorys.models import Erosions, Tophi
from ...medhistorys.tests.factories import CkdFactory, XoiinteractionFactory
from ...treatments.choices import AllopurinolDoses, FebuxostatDoses, Treatments
from ..models import UltAid
from .factories import UltAidFactory

pytestmark = pytest.mark.django_db


class TestUltAid(TestCase):
    def setUp(self):
        self.ultaid = UltAidFactory(ethnicity=EthnicityFactory(value=Ethnicitys.CAUCASIANAMERICAN))

    def test___str__(self):
        self.assertEqual(str(self.ultaid), f"UltAid: created {self.ultaid.created.date()}")

    def test__aid_dict(self):
        self.assertFalse(self.ultaid.decisionaid)
        self.ultaid.update_aid()
        self.ultaid.refresh_from_db()
        self.assertTrue(self.ultaid.decisionaid)
        self.assertIn(
            Treatments.ALLOPURINOL,
            self.ultaid.aid_dict,
        )

    def test__aid_medhistorys(self):
        self.assertEqual(
            self.ultaid.aid_medhistorys(),
            ULTAID_MEDHISTORYS,
        )

    def test__contraindications_allopurinol_allergy(self):
        self.assertFalse(
            self.ultaid.contraindications,
        )
        del self.ultaid.allopurinol_allergy
        del self.ultaid.contraindications
        MedAllergyFactory(treatment=Treatments.ALLOPURINOL, ultaid=self.ultaid)
        self.assertTrue(self.ultaid.contraindications)

    def test__contraindications_xoiinteraction(self):
        self.assertFalse(
            self.ultaid.contraindications,
        )
        del self.ultaid.xoiinteraction
        del self.ultaid.contraindications
        XoiinteractionFactory(ultaid=self.ultaid)
        self.assertTrue(self.ultaid.contraindications)

    def test__contraindications_hlab5801_contra(self):
        self.assertFalse(
            self.ultaid.contraindications,
        )
        del self.ultaid.hlab5801_contra
        del self.ultaid.contraindications
        self.ultaid.hlab5801 = Hlab5801Factory(value=True)
        self.ultaid.save()
        self.assertTrue(self.ultaid.contraindications)

    def test__contraindications_febuxostat_allergys(self):
        self.assertFalse(
            self.ultaid.contraindications,
        )
        del self.ultaid.febuxostat_allergy
        del self.ultaid.contraindications
        MedAllergyFactory(treatment=Treatments.FEBUXOSTAT, ultaid=self.ultaid)
        self.assertTrue(self.ultaid.contraindications)

    def test__contraindications_probenecid_ckd_contra(self):
        self.assertFalse(
            self.ultaid.contraindications,
        )
        del self.ultaid.ckd
        del self.ultaid.probenecid_ckd_contra
        del self.ultaid.contraindications
        ckd = CkdFactory(ultaid=self.ultaid)
        CkdDetailFactory(stage=Stages.FOUR, dialysis=False, medhistory=ckd)
        self.assertTrue(self.ultaid.contraindications)

    def test__contraindications_probenecid_allergys(self):
        self.assertFalse(
            self.ultaid.contraindications,
        )
        del self.ultaid.probenecid_allergy
        del self.ultaid.contraindications
        MedAllergyFactory(treatment=Treatments.PROBENECID, ultaid=self.ultaid)
        self.assertTrue(self.ultaid.contraindications)

    def test__defaulttrtsettings(self):
        self.assertEqual(
            self.ultaid.defaulttrtsettings,
            UltAidSettings.objects.get(),
        )

    def test__erosions(self):
        self.assertEqual(
            self.ultaid.erosions,
            False,
        )
        del self.ultaid.erosions
        create_goalurate(ultaid=self.ultaid, mhs=[MedHistoryTypes.EROSIONS])
        self.assertEqual(self.ultaid.erosions, Erosions.objects.order_by("created").last())

    def test__options(self):
        self.assertTrue(isinstance(self.ultaid.options, dict))
        self.assertIn(
            Treatments.ALLOPURINOL,
            self.ultaid.options,
        )
        self.assertIn(
            Treatments.FEBUXOSTAT,
            self.ultaid.options,
        )
        self.assertIn(
            Treatments.PROBENECID,
            self.ultaid.options,
        )

    def test__recommendation(self):
        self.assertEqual(
            self.ultaid.recommendation,
            (Treatments.ALLOPURINOL, self.ultaid.options[Treatments.ALLOPURINOL]),
        )
        MedAllergyFactory(treatment=Treatments.ALLOPURINOL, ultaid=self.ultaid)
        self.ultaid.update_aid()
        self.ultaid.refresh_from_db()
        del self.ultaid.aid_dict
        del self.ultaid.options
        self.assertEqual(
            self.ultaid.recommendation,
            (Treatments.FEBUXOSTAT, self.ultaid.options[Treatments.FEBUXOSTAT]),
        )
        MedAllergyFactory(treatment=Treatments.FEBUXOSTAT, ultaid=self.ultaid)
        self.ultaid.update_aid()
        self.ultaid.refresh_from_db()
        del self.ultaid.aid_dict
        del self.ultaid.options
        self.assertEqual(
            self.ultaid.recommendation,
            (Treatments.PROBENECID, self.ultaid.options[Treatments.PROBENECID]),
        )
        ckd = CkdFactory(ultaid=self.ultaid)
        CkdDetailFactory(stage=Stages.FOUR, dialysis=False, medhistory=ckd)
        self.ultaid.update_aid()
        self.ultaid.refresh_from_db()
        del self.ultaid.aid_dict
        del self.ultaid.options
        self.assertIsNone(self.ultaid.recommendation)

    def test__tophi(self):
        self.assertEqual(
            self.ultaid.tophi,
            False,
        )
        del self.ultaid.tophi
        create_goalurate(ultaid=self.ultaid, mhs=[MedHistoryTypes.TOPHI])
        self.assertEqual(self.ultaid.tophi, Tophi.objects.order_by("created").last())

    def test__update(self):
        self.assertFalse(self.ultaid.decisionaid)
        self.assertTrue(isinstance(self.ultaid.update_aid(), UltAid))
        self.ultaid.refresh_from_db()
        self.assertTrue(self.ultaid.decisionaid)
        self.assertIn(
            Treatments.ALLOPURINOL,
            self.ultaid.aid_dict,
        )
        self.assertIn(
            Treatments.FEBUXOSTAT,
            self.ultaid.aid_dict,
        )
        self.assertIn(
            Treatments.PROBENECID,
            self.ultaid.aid_dict,
        )


class TestUltAidUpdate(TestCase):
    def setUp(self):
        # Need to set ethnicity to something that won't flag a contraindiciation to allopurinol
        # due to no HLA-B*5801 test
        self.ultaid = UltAidFactory(ethnicity=EthnicityFactory(value=Ethnicitys.CAUCASIANAMERICAN))

    def test__dualhypersensitivity_recommends_probenecid(self):
        MedAllergyFactory(treatment=Treatments.ALLOPURINOL, ultaid=self.ultaid)
        MedAllergyFactory(treatment=Treatments.FEBUXOSTAT, ultaid=self.ultaid)
        self.ultaid.update_aid()
        self.assertNotIn(Treatments.ALLOPURINOL, self.ultaid.options)
        self.assertTrue(self.ultaid.aid_dict[Treatments.ALLOPURINOL]["contra"])
        self.assertNotIn(Treatments.FEBUXOSTAT, self.ultaid.options)
        self.assertTrue(self.ultaid.aid_dict[Treatments.FEBUXOSTAT]["contra"])
        self.assertEqual(Treatments.PROBENECID, self.ultaid.recommendation[0])

    def test__ckd_3_dose_adjusts_xois_contraindicates_probenecid(self):
        ckd = CkdFactory(ultaid=self.ultaid)
        CkdDetailFactory(stage=Stages.FOUR, dialysis=False, medhistory=ckd)
        self.ultaid.update_aid()
        self.assertIn(Treatments.ALLOPURINOL, self.ultaid.options)
        self.assertEqual(AllopurinolDoses.FIFTY, self.ultaid.options[Treatments.ALLOPURINOL]["dose"])
        self.assertEqual(AllopurinolDoses.FIFTY, self.ultaid.options[Treatments.ALLOPURINOL]["dose_adj"])
        self.assertIn(Treatments.FEBUXOSTAT, self.ultaid.options)
        self.assertEqual(FebuxostatDoses.TWENTY, self.ultaid.options[Treatments.FEBUXOSTAT]["dose"])
        self.assertEqual(FebuxostatDoses.TWENTY, self.ultaid.options[Treatments.FEBUXOSTAT]["dose_adj"])
        self.assertNotIn(Treatments.PROBENECID, self.ultaid.options)
