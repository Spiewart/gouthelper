import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ..choices import Ethnicitys
from ..helpers import ethnicitys_hlab5801_risk
from .factories import EthnicityFactory

pytestmark = pytest.mark.django_db


class TestEthnicitysHLAB5801Risk(TestCase):
    def setUp(self):
        self.high_risk_ethnicitys = [
            Ethnicitys.AFRICANAMERICAN,
            Ethnicitys.HANCHINESE,
            Ethnicitys.KOREAN,
            Ethnicitys.THAI,
        ]
        self.low_risk_ethnicitys = [
            ethnicity for ethnicity in Ethnicitys if ethnicity not in self.high_risk_ethnicitys
        ]

    def test__returns_True(self):
        for high_risk_ethnicity in self.high_risk_ethnicitys:
            ethnicity = EthnicityFactory(value=high_risk_ethnicity)
            self.assertTrue(ethnicitys_hlab5801_risk(ethnicity=ethnicity))

    def test__returns_False(self):
        for low_risk_ethnicity in self.low_risk_ethnicitys:
            ethnicity = EthnicityFactory(value=low_risk_ethnicity)
            self.assertFalse(ethnicitys_hlab5801_risk(ethnicity=ethnicity))
