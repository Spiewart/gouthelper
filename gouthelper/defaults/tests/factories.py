from datetime import timedelta  # type: ignore

import pytest  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ...treatments.choices import (
    AllopurinolDoses,
    CelecoxibDoses,
    ColchicineDoses,
    FebuxostatDoses,
    Freqs,
    NaproxenDoses,
    Treatments,
    TrtTypes,
)
from ..models import (
    DefaultFlareTrtSettings,
    DefaultMedHistory,
    DefaultPpxTrtSettings,
    DefaultTrt,
    DefaultUltTrtSettings,
)

pytestmark = pytest.mark.django_db


class DefaultAllopurinolFactory(DjangoModelFactory):
    dose = AllopurinolDoses.ONE
    dose_adj = AllopurinolDoses.FIFTY
    freq = Freqs.QDAY
    max_dose = AllopurinolDoses.SEVENFIFTY
    treatment = Treatments.ALLOPURINOL
    trttype = TrtTypes.ULT

    class Meta:
        model = DefaultTrt


class DefaultCelecoxibFlareFactory(DjangoModelFactory):
    dose = CelecoxibDoses.TWO
    dose2 = CelecoxibDoses.FOUR
    dose_adj = CelecoxibDoses.TWO
    duration = timedelta(days=7)
    freq = Freqs.BID
    freq2 = Freqs.ONCE
    max_dose = CelecoxibDoses.FOUR
    treatment = Treatments.CELECOXIB
    trttype = TrtTypes.FLARE

    class Meta:
        model = DefaultTrt


class DefaultColchicineFlareFactory(DjangoModelFactory):
    dose = ColchicineDoses.ONEPOINTTWO
    dose2 = ColchicineDoses.POINTSIX
    dose3 = ColchicineDoses.POINTSIX
    dose_adj = ColchicineDoses.POINTSIX
    duration = timedelta(days=7)
    freq = Freqs.BID
    freq2 = Freqs.ONCE
    freq3 = Freqs.ONCE
    max_dose = ColchicineDoses.ONEPOINTTWO
    treatment = Treatments.COLCHICINE
    trttype = TrtTypes.FLARE

    class Meta:
        model = DefaultTrt


class DefaultFebuxostatFactory(DjangoModelFactory):
    dose = FebuxostatDoses.TWENTY
    dose_adj = FebuxostatDoses.FORTY
    freq = Freqs.QDAY
    max_dose = FebuxostatDoses.ONETWENTY
    treatment = Treatments.FEBUXOSTAT
    trttype = TrtTypes.ULT

    class Meta:
        model = DefaultTrt


class DefaultNaproxenPpxFactory(DjangoModelFactory):
    dose = NaproxenDoses.FIVE
    dose_adj = NaproxenDoses.TWOFIFTY
    duration = None
    freq = Freqs.QDAY
    max_dose = NaproxenDoses.FIVE
    treatment = Treatments.NAPROXEN
    trttype = TrtTypes.PPX

    class Meta:
        model = DefaultTrt


class DefaultMedHistoryFactory(DjangoModelFactory):
    class Meta:
        model = DefaultMedHistory


class DefaultFlareTrtSettingsFactory(DjangoModelFactory):
    class Meta:
        model = DefaultFlareTrtSettings


class DefaultPpxTrtSettingsFactory(DjangoModelFactory):
    class Meta:
        model = DefaultPpxTrtSettings


class DefaultUltTrtSettingsFactory(DjangoModelFactory):
    class Meta:
        model = DefaultUltTrtSettings
