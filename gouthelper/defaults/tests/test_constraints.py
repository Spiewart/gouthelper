from datetime import timedelta
from decimal import Decimal

import pytest  # type: ignore
from django.db import IntegrityError  # type: ignore
from django.test import TestCase  # type: ignore

from ...defaults.models import DefaultTrt

pytestmark = pytest.mark.django_db


class TestDefaultTrt(TestCase):
    def test_colchicine_dose_exceeds_max_dose(self):
        with self.assertRaises(IntegrityError) as error:
            DefaultTrt.objects.create(
                treatment=DefaultTrt.Treatments.COLCHICINE,
                trttype=DefaultTrt.TrtTypes.FLARE,
                dose=Decimal("0.6"),
                dose2=Decimal("1.2"),
                dose3=Decimal("0.6"),
                max_dose=Decimal("0.6"),
                freq=DefaultTrt.Freqs.BID,
                freq2=DefaultTrt.Freqs.ONCE,
                freq3=DefaultTrt.Freqs.ONCE,
                duration=timedelta(days=7),
                duration2=None,
                duration3=None,
            )
        assert isinstance(error.exception, IntegrityError)

    def test_ibuprofen_max_dose_not_in_doses(self):
        with self.assertRaises(IntegrityError) as error:
            DefaultTrt.objects.create(
                treatment=DefaultTrt.Treatments.IBUPROFEN,
                trttype=DefaultTrt.TrtTypes.PPX,
                dose=Decimal(200),
                dose2=None,
                dose3=None,
                max_dose=Decimal(300),
                freq=DefaultTrt.Freqs.QDAY,
                freq2=None,
                freq3=None,
                duration=None,
                duration2=None,
                duration3=None,
            )
        assert isinstance(error.exception, IntegrityError)

    def test_allopurinol_dose_exceeds_max_dose(self):
        allopurinol_default = DefaultTrt.objects.get(
            user=None,
            treatment=DefaultTrt.Treatments.ALLOPURINOL,
            trttype=DefaultTrt.TrtTypes.ULT,
        )
        with self.assertRaises(IntegrityError) as error:
            allopurinol_default.dose = Decimal(800)
            allopurinol_default.save()
        assert isinstance(error.exception, IntegrityError)

    def test_probenecid_max_dose_not_in_doses(self):
        probenecid_default = DefaultTrt.objects.get(
            user=None,
            treatment=DefaultTrt.Treatments.PROBENECID,
            trttype=DefaultTrt.TrtTypes.ULT,
        )
        with self.assertRaises(IntegrityError) as error:
            probenecid_default.max_dose = Decimal(800)
            probenecid_default.save()
        assert isinstance(error.exception, IntegrityError)
