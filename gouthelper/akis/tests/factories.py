from decimal import Decimal

from factory import post_generation  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore
from factory.fuzzy import FuzzyChoice

from ...labs.helpers import labs_sort_list_by_date_drawn
from ...labs.models import Creatinine
from ...labs.tests.factories import CreatinineFactory
from ...utils.helpers import get_or_create_qs_attr
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
                elif isinstance(creatinine, tuple) and isinstance(creatinine[0], Decimal):
                    creatinine = CreatinineFactory(value=creatinine[0], date_drawn=creatinine[1], aki=self)
                    creatinine.full_clean()
                    creatinine.save()
                elif isinstance(creatinine, Creatinine):
                    creatinine.aki = self
                    creatinine.full_clean()
                    creatinine.save()
                else:
                    raise ValueError("creatinine must be a Decimal or Creatinine object")
                get_or_create_qs_attr(self, "creatinines").append(creatinine)
            labs_sort_list_by_date_drawn(self.creatinines_qs)
