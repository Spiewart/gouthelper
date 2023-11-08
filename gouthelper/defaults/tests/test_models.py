import pytest
from django.test import TestCase

from ...defaults.models import DefaultTrt

pytestmark = pytest.mark.django_db


class TestDefaultGetDefaults(TestCase):
    def test_get_allopurinol_defaults(self):
        default = DefaultTrt.objects.get(
            user=None,
            trttype=DefaultTrt.TrtTypes.ULT,
            treatment=DefaultTrt.Treatments.ALLOPURINOL,
        )
        default_dict = default.get_defaults()
        assert isinstance(default_dict, dict)
