from typing import Any

from django.apps import apps  # type: ignore
from django.views.generic import TemplateView  # type: ignore

from ..contents.choices import Contexts


class DateOfBirthAbout(TemplateView):
    """About page for DateOfBirths."""

    template_name = "dateofbirths/about.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"content": self.content})
        return context

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="about", context=Contexts.DATEOFBIRTH, tag=None)
