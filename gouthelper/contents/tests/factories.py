from factory import Faker, fuzzy  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ..choices import Contexts, Tags
from ..models import Content


class ContentFactory(DjangoModelFactory):
    class Meta:
        model = Content

    context = fuzzy.FuzzyChoice(Contexts.values)
    text = Faker("text")
    slug = fuzzy.FuzzyText(length=255)
    tag = fuzzy.FuzzyChoice(Tags.values)
