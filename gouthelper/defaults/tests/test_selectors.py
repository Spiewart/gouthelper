import pytest  # type: ignore
from django.db.models import QuerySet  # type: ignore
from django.test import TestCase  # type: ignore

from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.tests.factories import ChfFactory, GastricbypassFactory, HeartattackFactory
from ...treatments.choices import TrtTypes
from ..models import DefaultMedHistory, DefaultTrt, FlareAidSettings
from ..selectors import defaults_defaultmedhistorys_trttype, defaults_defaulttrts_trttype, defaults_flareaidsettings

pytestmark = pytest.mark.django_db


class TestDefaultsDefaultMedhistorysTrtType(TestCase):
    def setUp(self):
        self.medhistorys = [
            ChfFactory(),
            GastricbypassFactory(),
            HeartattackFactory(),
        ]

    def test__defaults_trttypes_trts_historys_no_user(self):
        default_ult_historys = defaults_defaultmedhistorys_trttype(
            medhistorys=self.medhistorys, trttype=TrtTypes.ULT, user=None
        )
        self.assertTrue(isinstance(default_ult_historys, QuerySet))
        self.assertEqual(len(default_ult_historys), 2)
        for default in default_ult_historys:
            self.assertTrue(isinstance(default, DefaultMedHistory))
            self.assertTrue(default.user is None)
            self.assertTrue(default.trttype == TrtTypes.ULT)
            # Need to include CHF and HEARTATTACK for ULT because of Febuxostat
            self.assertIn(
                default.medhistorytype,
                [
                    MedHistoryTypes.HEARTATTACK,
                    MedHistoryTypes.CHF,
                ],
            )
        default_flare_historys = defaults_defaultmedhistorys_trttype(
            medhistorys=self.medhistorys, trttype=TrtTypes.FLARE, user=None
        )
        self.assertTrue(isinstance(default_flare_historys, QuerySet))
        self.assertEqual(len(default_flare_historys), 18)
        for default in default_flare_historys:
            self.assertTrue(isinstance(default, DefaultMedHistory))
            self.assertTrue(default.user is None)
            self.assertTrue(default.trttype == TrtTypes.FLARE)
            self.assertIn(
                default.medhistorytype,
                [
                    MedHistoryTypes.CHF,
                    MedHistoryTypes.GASTRICBYPASS,
                    MedHistoryTypes.HEARTATTACK,
                ],
            )

    def test__empty_medhistorys_returns_empty_qs(self):
        """Test empty medhistorys. Should return empty QuerySet"""
        default_medhistorys = defaults_defaultmedhistorys_trttype(medhistorys=[], trttype=TrtTypes.PPX, user=None)
        self.assertTrue(isinstance(default_medhistorys, QuerySet))
        self.assertEqual(len(default_medhistorys), 0)


class TestDefaultsTrtTypeTrts(TestCase):
    def test__defaults_trttype_trts_no_user(self):
        """Test no user. Should return GoutHelper defaults for ULT"""
        default_ult_trts = defaults_defaulttrts_trttype(trttype=TrtTypes.ULT, user=None)
        self.assertTrue(isinstance(default_ult_trts, QuerySet))
        self.assertEqual(len(default_ult_trts), 3)
        for default in default_ult_trts:
            self.assertTrue(isinstance(default, DefaultTrt))
            self.assertTrue(default.user is None)
            self.assertTrue(default.trttype == TrtTypes.ULT)
        default_flare_trts = defaults_defaulttrts_trttype(trttype=TrtTypes.FLARE, user=None)
        self.assertTrue(isinstance(default_flare_trts, QuerySet))
        self.assertEqual(len(default_flare_trts), 9)
        for default in default_flare_trts:
            self.assertTrue(isinstance(default, DefaultTrt))
            self.assertTrue(default.user is None)
            self.assertTrue(default.trttype == TrtTypes.FLARE)


class TestDefaultsFlareAidSettings(TestCase):
    def test__no_user_returns_gouthelper_default(self):
        qs = defaults_flareaidsettings(user=None)
        self.assertTrue(isinstance(qs, FlareAidSettings))
        self.assertIsNone(qs.user)
