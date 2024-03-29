from factory.django import DjangoModelFactory  # type: ignore

from ..models import PatientProfile, ProviderProfile, PseudopatientProfile


class PatientProfileFactory(DjangoModelFactory):
    class Meta:
        model = PatientProfile


class ProviderProfileFactory(DjangoModelFactory):
    class Meta:
        model = ProviderProfile


class PseudopatientProfileFactory(DjangoModelFactory):
    class Meta:
        model = PseudopatientProfile
