from typing import Any

from django.apps import apps  # type: ignore
from django.views.generic import TemplateView  # type: ignore


class About(TemplateView):
    template_name = "contents/about.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({"content": self.content})
        return context

    @property
    def content(self):
        return apps.get_model("contents.Content").objects.get(slug="about", context=None, tag=None)


class DecisionAids(TemplateView):
    template_name = "contents/decision-aids.html"


class TreatmentAids(TemplateView):
    template_name = "contents/treatment-aids.html"


class Home(TemplateView):
    template_name = "contents/home.html"
