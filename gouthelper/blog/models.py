from autoslug import AutoSlugField  # type: ignore
from django.conf import settings  # type: ignore
from django.db import models  # type: ignore
from django.urls import reverse  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from markdownfield.models import RenderedMarkdownField  # type: ignore
from markdownfield.validators import VALIDATOR_CLASSY  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..utils.fields import GoutHelperMarkdownField
from ..utils.helpers import now_date
from ..utils.models import GoutHelperModel
from .choices import StatusChoices


class Blogtag(RulesModelMixin, GoutHelperModel, TimeStampedModel, metaclass=RulesModelBase):
    """Model to store tags for posts."""

    history = HistoricalRecords()
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Blogpost(RulesModelMixin, GoutHelperModel, TimeStampedModel, metaclass=RulesModelBase):
    """Model to store Blog Posts as HTML Markdown pages."""

    class Meta:
        constraints = [
            # Constrain title to be unique for entire table
            models.UniqueConstraint(
                fields=["title"],
                name="%(app_label)s_%(class)s_unique_title",
            ),
            # Enforce that status is a valid StatusChoices choice
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_valid_status",
                check=models.Q(status__in=StatusChoices.values),
            ),
        ]

    author = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blogposts")
    history = HistoricalRecords()
    published_date = models.DateField(default=now_date)
    slug = AutoSlugField(populate_from="title", unique=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default="draft")
    tags = models.ManyToManyField(to=Blogtag, related_name="posts", blank=True)
    text = GoutHelperMarkdownField(rendered_field="text_rendered", validator=VALIDATOR_CLASSY)
    text_rendered = RenderedMarkdownField()
    title = models.CharField(max_length=255)
    updated_date = models.DateField(null=True, blank=True)

    def get_absolute_url(self):
        return reverse("blog:blog_detail", kwargs={"slug": self.slug})

    def __str__(self):
        return self.title
