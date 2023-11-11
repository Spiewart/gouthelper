from django.db import models  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from markdownfield.models import RenderedMarkdownField  # type: ignore
from markdownfield.validators import VALIDATOR_CLASSY  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..utils.fields import GouthelperMarkdownField
from ..utils.models import GouthelperModel
from .choices import Contexts, Tags


class Content(RulesModelMixin, GouthelperModel, TimeStampedModel, metaclass=RulesModelBase):
    """Model to store HTML Markdown pages."""

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "context",
                    "slug",
                    "tag",
                ],
                name="%(app_label)s_%(class)s_unique_slug_tag_context",
            ),
            models.UniqueConstraint(
                fields=["slug"],
                condition=models.Q(context__isnull=True, tag__isnull=True),
                name="%(app_label)s_%(class)s_unique_slug_no_tag_context",
            ),
            # Enforce that you can only have one page with a slug and context but no tag
            models.UniqueConstraint(
                fields=["slug", "context"],
                condition=models.Q(tag__isnull=True),
                name="%(app_label)s_%(class)s_unique_slug_context_no_tag",
            ),
            # Enforce that context is a valid Contexts choice
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_valid_context",
                check=models.Q(context__in=Contexts.values),
            ),
            # Enforce that tag is a valid Tags choice
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_valid_tag",
                check=models.Q(tag__in=Tags.values),
            ),
        ]

    Contexts = Contexts
    Tags = Tags

    context = models.CharField(
        _("Context"), choices=Contexts.choices, max_length=255, null=True, blank=True, editable=False
    )
    history = HistoricalRecords()
    slug = models.SlugField(max_length=255)
    tag = models.CharField(max_length=255, choices=Tags.choices, null=True, blank=True)
    text = GouthelperMarkdownField(rendered_field="text_rendered", validator=VALIDATOR_CLASSY)
    text_rendered = RenderedMarkdownField()

    def __str__(self):
        return f"Content: {self.slug} ({self.context}, {self.tag})"
