from decimal import Decimal

from factory import post_generation  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore
from factory.fuzzy import FuzzyChoice  # type: ignore

from ...labs.models import Creatinine
from ...labs.tests.factories import CreatinineFactory
from ..choices import Statuses


class AkiFactory(DjangoModelFactory):
    class Meta:
        model = "akis.Aki"

    status = FuzzyChoice(choices=Statuses.values)
    user = None

    @post_generation
    def creatinines(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for creatinine in extracted:
                if isinstance(creatinine, Decimal):
                    creatinine = CreatinineFactory(value=creatinine, aki=self)
                elif isinstance(creatinine, Creatinine):
                    creatinine.aki = self
                    creatinine.full_clean()
                    creatinine.save()
                else:
                    raise ValueError("creatinine must be a Decimal or Creatinine object")
