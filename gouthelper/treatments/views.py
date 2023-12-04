from typing import Any

from django.apps import apps  # type: ignore
from django.views.generic import TemplateView  # type: ignore

from ..contents.choices import Contexts


class TreatmentAbout(TemplateView):
    """TemplateView for About pages for Treatments in general as well as
    specific treatment strategies."""

    template_name = "about.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"content": self.content})
        return context

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="about", context=Contexts.TREATMENT, tag=None)


class AboutFlare(TreatmentAbout):
    """TemplateView for the About page for Flare."""

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="flare", context=Contexts.TREATMENT, tag=None)


class AboutPpx(TreatmentAbout):
    """TemplateView for the About page for Ppx."""

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="ppx", context=Contexts.TREATMENT, tag=None)


class AboutUlt(TreatmentAbout):
    """TemplateView for the About page for Ult."""

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="ult", context=Contexts.TREATMENT, tag=None)
