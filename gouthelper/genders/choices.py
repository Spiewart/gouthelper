from django.db.models import IntegerChoices  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore


class Genders(IntegerChoices):
    MALE = 0, _("Male")
    FEMALE = 1, _("Female")
