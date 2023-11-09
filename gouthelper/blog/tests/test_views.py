import pytest  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore

from ..views import BlogAuthorList, BlogDetail, BlogList, BlogTagList
from .factories import BlogpostFactory, BlogtagFactory

pytestmark = pytest.mark.django_db


class TestBlogListViews(TestCase):
    def setUp(self):
        # Create 3 Blogposts
        self.blogpost1 = BlogpostFactory()
        self.blogpost2 = BlogpostFactory()
        self.blogpost3 = BlogpostFactory()
        # Create 3 Blogtags
        self.blogtag1 = BlogtagFactory()
        self.blogtag2 = BlogtagFactory()
        self.blogtag3 = BlogtagFactory()
        # Add Blogtags to Blogposts
        self.blogpost1.tags.add(self.blogtag1)
        self.blogpost2.tags.add(self.blogtag2)
        self.blogpost3.tags.add(self.blogtag3)

    def test__blog_author_listview(self):
        url = f"/blog/by-author/{self.blogpost1.author.username}/"

        # Act
        request = RequestFactory().get(url)
        response = BlogAuthorList.as_view()(request, author=self.blogpost1.author.username)

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.blogpost1, response.context_data["blogpost_list"])
        self.assertNotIn(self.blogpost2, response.context_data["blogpost_list"])
        self.assertNotIn(self.blogpost3, response.context_data["blogpost_list"])

    def test__blog_listview(self):
        url = "/blog/"

        # Act
        request = RequestFactory().get(url)
        response = BlogList.as_view()(request)

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.blogpost1, response.context_data["blogpost_list"])
        self.assertIn(self.blogpost2, response.context_data["blogpost_list"])
        self.assertIn(self.blogpost3, response.context_data["blogpost_list"])

    def test__blog_tag_listview(self):
        url = f"/blog/by-tag/{self.blogtag1.name}/"

        # Act
        request = RequestFactory().get(url)
        response = BlogTagList.as_view()(request, tag=self.blogtag1.name)

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.blogpost1, response.context_data["blogpost_list"])
        self.assertNotIn(self.blogpost2, response.context_data["blogpost_list"])
        self.assertNotIn(self.blogpost3, response.context_data["blogpost_list"])

    def test__blog_detailview(self):
        url = f"/blog/{self.blogpost1.slug}/"

        # Act
        request = RequestFactory().get(url)
        response = BlogDetail.as_view()(request, slug=self.blogpost1.slug)

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.blogpost1, response.context_data["blogpost"])
