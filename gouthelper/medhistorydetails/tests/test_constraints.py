from django.db import IntegrityError
from django.test import TransactionTestCase

from ...medhistorydetails.choices import Stages
from ...medhistorys.tests.factories import CkdFactory
from .factories import CkdDetailFactory


class TestCkdDetailConstraints(TransactionTestCase):
    def setUp(self):
        self.ckd = CkdFactory()

    def test__dialysis_not_stage_five_raises_error(self):
        with self.assertRaises(IntegrityError) as error:
            CkdDetailFactory(medhistory=self.ckd, stage=Stages.TWO, dialysis=True)
        assert isinstance(error.exception, IntegrityError)
        assert "medhistorydetails_ckddetail_dialysis_valid" in error.exception.args[0]

    def test__invalid_dialysis_duration_raises_error(self):
        with self.assertRaises(IntegrityError) as error:
            CkdDetailFactory(
                medhistory=self.ckd,
                stage=Stages.FIVE,
                dialysis=True,
                dialysis_duration="7yearsathogwarts",
            )
        assert isinstance(error.exception, IntegrityError)
        assert "historydetails_ckddetail_dialysis_duration_valid" in error.exception.args[0]

    def test__invalid_stage_raises_error(self):
        with self.assertRaises(IntegrityError) as error:
            CkdDetailFactory(medhistory=self.ckd, stage=7)
        assert isinstance(error.exception, IntegrityError)
        assert "historydetails_ckddetail_stage_valid" in error.exception.args[0]
