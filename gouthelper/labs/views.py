from typing import Any

from django.apps import apps  # type: ignore
from django.views.generic import TemplateView  # type: ignore

from ..contents.choices import Contexts


class LabAbout(TemplateView):
    """TemplateView for About pages for Labs in general as well as
    specific labs."""

    template_name = "labs/about.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"content": self.content})
        return context

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="about", context=Contexts.LAB, tag=None)


class AboutHlab5801(LabAbout):
    """TemplateView for the About page for HLA-B*5801."""

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="hlab5801", context=Contexts.LAB, tag=None)


class AboutUrate(LabAbout):
    """TemplateView for the About page for Urate."""

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="urate", context=Contexts.LAB, tag=None)
