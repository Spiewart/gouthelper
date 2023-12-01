import pytest  # type: ignore
from django.conf import settings  # type: ignore
from django.core import mail  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore

from ..choices import SubjectChoices
from ..views import ContactSuccessView, ContactView

pytestmark = pytest.mark.django_db


class TestContactSuccessView(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = ContactSuccessView.as_view()
        self.url = reverse("contact:success")

    def test__get(self):
        """Test that the view returns a 200 response."""
        request = self.factory.get(self.url)
        response = self.view(request)
        self.assertEqual(response.status_code, 200)

    def test__template(self):
        """Test that the view uses the correct template."""
        request = self.factory.get(self.url)
        response = self.view(request)
        self.assertEqual(response.template_name[0], "contact/success.html")


class TestContactView(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = ContactView.as_view()
        self.url = reverse("contact:contact")

    def test__get(self):
        """Test that the view returns a 200 response."""
        request = self.factory.get(self.url)
        response = self.view(request)
        self.assertEqual(response.status_code, 200)

    def test__template(self):
        """Test that the view uses the correct template."""
        request = self.factory.get(self.url)
        response = self.view(request)
        self.assertEqual(response.template_name[0], "contact/contact.html")

    def test__emails_sent_by_form_valid(self):
        """Test that the view returns a 302 response when a valid form is posted."""
        data = {
            "name": "Ronald Weasley",
            "email": "rweasley@hogwarts.com",
            "subject": SubjectChoices.OTHER,
            "other": "I ate a bad jellybean...",
            "message": "I ate the allopurobean and now I'm all red and angry and I can't put a sock on.",
        }

        request = self.factory.post(self.url, data=data)

        response = self.view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        # Assert that the emails in the outbox are from the correct email addresses
        self.assertEqual(mail.outbox[0].from_email, settings.DEFAULT_FROM_EMAIL)
        # Assert that the emails in the outbox are directed to the correct email addresses
        self.assertEqual(mail.outbox[0].to, [settings.DEFAULT_FROM_EMAIL, "rweasley@hogwarts.com"])
        # Assert that the subject is correct
        self.assertEqual(mail.outbox[0].subject, f"{SubjectChoices.OTHER}: I ate a bad jellybean...")
        # Assert that the message is correct
        self.assertEqual(
            mail.outbox[0].body,
            f"Ronald Weasley with email {data['email']} said:\n"
            f'"{SubjectChoices.OTHER}: I ate a bad jellybean..."\n\n'
            f"{data['message']}",
        )

    def test__form_not_valid_other_subject_without_other(self):
        """Test that the view returns a 200 response when an invalid form is posted."""
        data = {
            "name": "Ronald Weasley",
            "email": "rweasley@hogwarts.com",
            "subject": SubjectChoices.OTHER,
            "message": "I ate the allopurobean and now I'm all red and angry and I can't put a sock on.",
        }

        request = self.factory.post(self.url, data=data)

        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(response.context_data["form"].errors["other"], ['Please specify the "other" subject.'])
