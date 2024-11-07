from django.test import TestCase  # type: ignore

from ...users.tests.factories import create_psp
from ..api.mixins import FlareAPIMixin
from ..tests.factories import CustomFlareFactory


class TestFlareAPIMixin(TestCase):
    def setUp(self):
        self.api = FlareAPIMixin()
        self.flare = CustomFlareFactory()
        self.patient = create_psp()

    def set_api_attrs(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self.api, key, value)

    def test__create_flare(self):
        pass

    def test__get_api_data(self):
        data = CustomFlareFactory().create_api_data()
        print(type(data))
        print(data.get("date_started"))
        serializer = data.drf_serializer()
        print(serializer.data)
        self.assertTrue(isinstance(data, dict))
