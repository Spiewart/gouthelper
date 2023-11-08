import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...ethnicitys.choices import Ethnicitys
from ...ethnicitys.tests.factories import EthnicityFactory
from ...medhistorydetails.choices import Stages
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.tests.factories import (
    AllopurinolhypersensitivityFactory,
    CkdFactory,
    FebuxostathypersensitivityFactory,
)
from ...treatments.choices import AllopurinolDoses, FebuxostatDoses, Treatments
from .factories import UltAidFactory

pytestmark = pytest.mark.django_db


class TestUltAidUpdate(TestCase):
    def setUp(self):
        # Need to set ethnicity to something that won't flag a contraindiciation to allopurinol
        # due to no HLA-B*5801 test
        self.ultaid = UltAidFactory(ethnicity=EthnicityFactory(value=Ethnicitys.CAUCASIANAMERICAN))

    def test__allopurinolhypersensitivity_recommends_febuxostat(self):
        allopurinolhypersensitivity = AllopurinolhypersensitivityFactory()
        self.ultaid.add_medhistorys(medhistorys=[allopurinolhypersensitivity])
        self.ultaid.update()
        self.assertTrue(self.ultaid.aid_dict[Treatments.ALLOPURINOL]["contra"])
        self.assertNotIn(Treatments.ALLOPURINOL, self.ultaid.options)
        self.assertEqual(Treatments.FEBUXOSTAT, self.ultaid.recommendation[0])

    def test__dualhypersensitivity_recommends_probenecid(self):
        allopurinolhypersensitivity = AllopurinolhypersensitivityFactory()
        febuxostathypersensitivity = FebuxostathypersensitivityFactory()
        self.ultaid.add_medhistorys(medhistorys=[allopurinolhypersensitivity, febuxostathypersensitivity])
        self.ultaid.update()
        self.assertNotIn(Treatments.ALLOPURINOL, self.ultaid.options)
        self.assertTrue(self.ultaid.aid_dict[Treatments.ALLOPURINOL]["contra"])
        self.assertNotIn(Treatments.FEBUXOSTAT, self.ultaid.options)
        self.assertTrue(self.ultaid.aid_dict[Treatments.FEBUXOSTAT]["contra"])
        self.assertEqual(Treatments.PROBENECID, self.ultaid.recommendation[0])

    def test__ckd_3_dose_adjusts_xois(self):
        ckd = CkdFactory()
        CkdDetailFactory(stage=Stages.FOUR, dialysis=False, medhistory=ckd)
        self.ultaid.add_medhistorys(medhistorys=[ckd])
        self.ultaid.update()
        self.assertIn(Treatments.ALLOPURINOL, self.ultaid.options)
        self.assertEqual(AllopurinolDoses.FIFTY, self.ultaid.options[Treatments.ALLOPURINOL]["dose"])
        self.assertEqual(AllopurinolDoses.FIFTY, self.ultaid.options[Treatments.ALLOPURINOL]["dose_adj"])
        self.assertIn(Treatments.FEBUXOSTAT, self.ultaid.options)
        self.assertEqual(FebuxostatDoses.TWENTY, self.ultaid.options[Treatments.FEBUXOSTAT]["dose"])
        self.assertEqual(FebuxostatDoses.TWENTY, self.ultaid.options[Treatments.FEBUXOSTAT]["dose_adj"])
        self.assertNotIn(Treatments.PROBENECID, self.ultaid.options)
