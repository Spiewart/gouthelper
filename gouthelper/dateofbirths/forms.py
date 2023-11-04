from crispy_forms.helper import FormHelper  # type: ignore

from ..utils.exceptions import EmptyRelatedModel
from ..utils.forms import OneToOneForm
from .models import DateOfBirth


class DateOfBirthForm(OneToOneForm):
    class Meta:
        model = DateOfBirth
        fields = ("value",)

    prefix = "dateofbirth"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["value"].label = "Date of Birth"
        self.helper = FormHelper()
        self.helper.form_tag = False

    def check_for_value(self):
        value = self.cleaned_data["value"]
        if not value:
            raise EmptyRelatedModel

    @property
    def required_fields(self) -> list[str]:
        """Return a list of required fields"""
        return ["value"]


class DateOfBirthFormOptional(DateOfBirthForm):
    """Subclass of DateOfBirthForm with value field not required."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["value"].required = False
