from django import forms  # type: ignore
from django.conf import settings  # type: ignore
from django.core.mail import send_mail  # type: ignore
from django_recaptcha.fields import ReCaptchaField

from .choices import SubjectChoices

# https://www.sitepoint.com/django-send-email/


class ContactForm(forms.Form):
    """Form for writing a contact e-mail to the GoutHelper admin(s)."""

    SubjectChoices = SubjectChoices

    name = forms.CharField(max_length=120)
    email = forms.EmailField()
    subject = forms.ChoiceField(widget=forms.Select(), choices=SubjectChoices.choices)
    other = forms.CharField(max_length=70, required=False)
    message = forms.CharField(widget=forms.Textarea)
    captcha = ReCaptchaField()

    def clean(self):
        """Overriding clean method to check for "other" subject.
        Requires the other field to be filled out if the subject
        is "other"."""

        cl_data = super().clean()
        subject = cl_data.get("subject")
        other = cl_data.get("other")
        if subject == SubjectChoices.OTHER and not other:
            self.add_error("other", forms.ValidationError('Please specify the "other" subject.'))
        return cl_data

    def get_info(self):
        """
        Method that returns formatted information
        :return: subject, msg
        """
        # Cleaned data
        cl_data = super().clean()

        name = cl_data.get("name").strip()
        from_email = cl_data.get("email")
        subject = cl_data.get("subject")
        if subject == SubjectChoices.OTHER:
            subject = subject + ": " + cl_data.get("other")
        msg = f"{name} with email {from_email} said:"
        msg += f'\n"{subject}"\n\n'
        msg += cl_data.get("message")

        return subject, msg, from_email

    def send(self):
        subject, msg, from_email = self.get_info()

        send_mail(
            subject=subject,
            message=msg,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[settings.CORRESPONDANCE_EMAIL, from_email],
        )
