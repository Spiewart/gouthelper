import pytest  # type: ignore
from django.db import IntegrityError  # type: ignore
from django.test import TestCase  # type: ignore

from .factories import ContentFactory

pytestmark = pytest.mark.django_db


class TestContent(TestCase):
    def setUp(self):
        self.content = ContentFactory()

    def test__unique_slug_tag_context_constraint(self):
        with pytest.raises(IntegrityError):
            ContentFactory(
                slug=self.content.slug,
                tag=self.content.tag,
                context=self.content.context,
            )

    def test__unique_slug_context_no_tag_constraint(self):
        self.content.tag = None
        self.content.save()
        with pytest.raises(IntegrityError):
            ContentFactory(
                slug=self.content.slug,
                tag=None,
                context=self.content.context,
            )

    def test__unique_slug_no_tag_or_context_constraint(self):
        self.content.tag = None
        self.content.context = None
        self.content.save()
        with pytest.raises(IntegrityError):
            ContentFactory(
                slug=self.content.slug,
                tag=None,
                context=None,
            )

    def test__context_valid_constraint(self):
        with pytest.raises(IntegrityError):
            ContentFactory(context="invalid")

    def test__tag_valid_constraint(self):
        with pytest.raises(IntegrityError):
            ContentFactory(tag="invalid")
