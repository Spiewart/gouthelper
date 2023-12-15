from io import StringIO

from django.core.management import call_command
from django.test import TestCase


class TestUpdateContents(TestCase):
    def test_command_output(self):
        out = StringIO()
        call_command("update_contents", stdout=out)
        self.assertIn("Successfully updated contents.", out.getvalue())
