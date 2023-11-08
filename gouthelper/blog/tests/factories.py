from factory import Faker, SubFactory, fuzzy  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ...users.tests.factories import AdminFactory
from ..choices import StatusChoices
from ..models import Blogpost, Blogtag


class BlogpostFactory(DjangoModelFactory):
    class Meta:
        model = Blogpost

    author = SubFactory(AdminFactory)
    status = StatusChoices.PUBLISHED
    text = Faker("text")
    title = Faker("text")


class BlogtagFactory(DjangoModelFactory):
    class Meta:
        model = Blogtag

    name = fuzzy.FuzzyText(length=100)
