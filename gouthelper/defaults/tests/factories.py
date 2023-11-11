from datetime import timedelta  # type: ignore

import pytest  # type: ignore
from factory import SubFactory, fuzzy  # type: ignore
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
from ...users.tests.factories import UserFactory
from ..models import (
    DefaultFlareTrtSettings,
    DefaultMedHistory,
    DefaultPpxTrtSettings,
    DefaultTrt,
    DefaultUltTrtSettings,
)

pytestmark = pytest.mark.django_db


class DefaultMedHistoryFactory(DjangoModelFactory):
    class Meta:
        model = DefaultMedHistory

    contraindication = fuzzy.FuzzyChoice(DefaultMedHistory.Contraindications.values)
    medhistorytype = fuzzy.FuzzyChoice(DefaultMedHistory.MedHistoryTypes.values)
    treatment = fuzzy.FuzzyChoice(DefaultMedHistory.Treatments.values)
    trttype = fuzzy.FuzzyChoice(DefaultMedHistory.TrtTypes.values)
    user = SubFactory(UserFactory)


class DefaultTrtFactory(DjangoModelFactory):
    """Abstract base calss for DefaultTrt factories.
    Abstract because it is highly unlikely that randomly picking
    from each field's choices will result in a violated constraint."""

    class Meta:
        model = DefaultTrt
        abstract = True

    user = SubFactory(UserFactory)


class DefaultAllopurinolFactory(DefaultTrtFactory):
    dose = AllopurinolDoses.ONE
    dose_adj = AllopurinolDoses.FIFTY
    freq = Freqs.QDAY
    max_dose = AllopurinolDoses.SEVENFIFTY
    treatment = Treatments.ALLOPURINOL
    trttype = TrtTypes.ULT

    class Meta:
        model = DefaultTrt


class DefaultCelecoxibFlareFactory(DefaultTrtFactory):
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


class DefaultColchicineFlareFactory(DefaultTrtFactory):
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


class DefaultFebuxostatFactory(DefaultTrtFactory):
    dose = FebuxostatDoses.TWENTY
    dose_adj = FebuxostatDoses.FORTY
    freq = Freqs.QDAY
    max_dose = FebuxostatDoses.ONETWENTY
    treatment = Treatments.FEBUXOSTAT
    trttype = TrtTypes.ULT

    class Meta:
        model = DefaultTrt


class DefaultNaproxenPpxFactory(DefaultTrtFactory):
    dose = NaproxenDoses.FIVE
    dose_adj = NaproxenDoses.TWOFIFTY
    duration = None
    freq = Freqs.QDAY
    max_dose = NaproxenDoses.FIVE
    treatment = Treatments.NAPROXEN
    trttype = TrtTypes.PPX

    class Meta:
        model = DefaultTrt


class DefaultFlareTrtSettingsFactory(DefaultTrtFactory):
    class Meta:
        model = DefaultFlareTrtSettings


class DefaultPpxTrtSettingsFactory(DefaultTrtFactory):
    class Meta:
        model = DefaultPpxTrtSettings


class DefaultUltTrtSettingsFactory(DefaultTrtFactory):
    class Meta:
        model = DefaultUltTrtSettings
