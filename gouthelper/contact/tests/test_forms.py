from unittest.mock import patch  # type: ignore

import pytest  # type: ignore
from django.conf import settings  # type: ignore
from django.core import mail  # type: ignore
from django.test import TestCase  # type: ignore
from django_recaptcha.client import RecaptchaResponse  # type: ignore

from ..choices import SubjectChoices
from ..forms import ContactForm

pytestmark = pytest.mark.django_db


class TestContactForm(TestCase):
    def setUp(self):
        self.data = {
            "name": "Ronald Weasley",
            "email": "rweasley@hogwarts.com",
            "subject": SubjectChoices.CLINICALBUG,
            "message": "Your webapp broke my big toe! It's all red and angry and I can't put a sock on.",
            "g-recaptcha-response": "PASSED",
        }
        self.form = ContactForm

    @patch("django_recaptcha.fields.client.submit")
    def test__clean(self, mocked_submit):
        """Test that the clean method works as expected."""
        # Add mocked RecaptchaResponse to mocked_submit so that the form is valid
        mocked_submit.return_value = RecaptchaResponse(is_valid=True)
        # Test that the form is valid
        form = self.form(data=self.data)
        assert form.is_valid()

        # Test that the form is invalid if the subject is "other" and the other field is empty
        self.data["subject"] = SubjectChoices.OTHER
        form = self.form(data=self.data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["other"], ['Please specify the "other" subject.'])

    @patch("django_recaptcha.fields.client.submit")
    def test__get_info(self, mocked_submit):
        """Test that the get_info method works as expected."""
        # Add mocked RecaptchaResponse to mocked_submit so that the form is valid
        mocked_submit.return_value = RecaptchaResponse(is_valid=True)
        form = self.form(data=self.data)
        self.assertTrue(form.is_valid())

        subject, msg, from_email = form.get_info()

        self.assertEqual(subject, SubjectChoices.CLINICALBUG)
        self.assertEqual(
            msg,
            f"Ronald Weasley with email {from_email} said:\n"
            f'"{SubjectChoices.CLINICALBUG}"\n\n'
            f"{self.data['message']}",
        )
        self.assertEqual(from_email, "rweasley@hogwarts.com")

    @patch("django_recaptcha.fields.client.submit")
    def test__send(self, mocked_submit):
        """Test that the send method works as expected."""
        # Add mocked RecaptchaResponse to mocked_submit so that the form is valid
        mocked_submit.return_value = RecaptchaResponse(is_valid=True)
        form = self.form(data=self.data)
        self.assertTrue(form.is_valid())

        form.send()
        self.assertEqual(len(mail.outbox), 1)
        # Assert that the emails in the outbox are from the correct email addresses
        self.assertEqual(mail.outbox[0].from_email, settings.DEFAULT_FROM_EMAIL)
        # Assert that the emails in the outbox are directed to the correct email addresses
        self.assertEqual(mail.outbox[0].to, [settings.CORRESPONDANCE_EMAIL, "rweasley@hogwarts.com"])
        # Assert that the subject is correct
        self.assertEqual(mail.outbox[0].subject, SubjectChoices.CLINICALBUG)
        # Assert that the message is correct
        self.assertEqual(
            mail.outbox[0].body,
            f"Ronald Weasley with email {self.data['email']} said:\n"
            f'"{SubjectChoices.CLINICALBUG}"\n\n'
            f"{self.data['message']}",
        )
