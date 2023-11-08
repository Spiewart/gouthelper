import pytest  # type: ignore
from django.db import IntegrityError  # type: ignore
from django.test import TestCase  # type: ignore

from .factories import BlogpostFactory, BlogtagFactory

pytestmark = pytest.mark.django_db


class TestBlogpost(TestCase):
    def setUp(self):
        self.blogpost = BlogpostFactory()

    def test___str__(self):
        assert self.blogpost.__str__() == self.blogpost.title

    def test__get_absolute_url(self):
        assert self.blogpost.get_absolute_url() == f"/blog/{self.blogpost.slug}/"

    def test__title_unique_constraint(self):
        with self.assertRaises(IntegrityError):
            BlogpostFactory(title=self.blogpost.title, slug=self.blogpost.slug)

    def test__status_valid_constraint(self):
        with self.assertRaises(IntegrityError):
            BlogpostFactory(status="invalid")


class TestBlogtag(TestCase):
    def setUp(self):
        self.blogtag = BlogtagFactory()

    def test___str__(self):
        assert self.blogtag.__str__() == self.blogtag.name
