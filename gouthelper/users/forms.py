from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from crispy_forms.helper import FormHelper  # type: ignore
from crispy_forms.layout import HTML, Div, Fieldset, Layout  # type: ignore
from django import forms  # type: ignore
from django.contrib.auth import forms as admin_forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from ..medhistorys.choices import MedHistoryTypes
from ..utils.helpers.form_helpers import (
    forms_helper_insert_dateofbirth,
    forms_helper_insert_ethnicity,
    forms_helper_insert_gender,
    forms_helper_insert_medhistory,
)
from .models import Pseudopatient

User = get_user_model()


class PseudopatientForm(forms.ModelForm):
    """Model form for creating Pseudopatient objects."""

    class Meta:
        model = Pseudopatient
        exclude = (
            "username",
            "email",
            "password",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                "",
                Div(
                    HTML(
                        """
                        <hr size="3" color="dark">
                        <legend>About the Patient</legend>
                        """
                    ),
                ),
            ),
        )
        # Insert forms for related MedHistorys
        forms_helper_insert_dateofbirth(layout=self.helper.layout)
        forms_helper_insert_ethnicity(layout=self.helper.layout)
        forms_helper_insert_gender(layout=self.helper.layout)
        forms_helper_insert_medhistory(medhistorytype=MedHistoryTypes.GOUT, layout=self.helper.layout)


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):
        model = User


class UserAdminCreationForm(admin_forms.UserCreationForm):
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    class Meta(admin_forms.UserCreationForm.Meta):
        model = User
        error_messages = {
            "username": {"unique": _("This username has already been taken.")},
        }


class UserSignupForm(SignupForm):
    """
    Form that will be rendered on a user sign up section/screen.
    Default fields will be added automatically.
    Check UserSocialSignupForm for accounts created from social.
    """


class UserSocialSignupForm(SocialSignupForm):
    """
    Renders the form when user has signed up using social accounts.
    Default fields will be added automatically.
    See UserSignupForm otherwise.
    """
