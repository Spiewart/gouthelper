from django.db.models import Q  # type: ignore
from django.views.generic import DetailView, ListView  # type: ignore

from .models import Blogpost, Blogtag


class BlogDetail(DetailView):
    """DetailView to show a single blog post."""

    model = Blogpost
    template_name = "blog/detail.html"

    def get_queryset(self):
        return super().get_queryset().filter(status="published").prefetch_related("tags")


class BlogList(ListView):
    """View to list all paginated blog posts."""

    model = Blogpost
    paginate_by = 10
    template_name = "blog/list.html"

    def get_queryset(self):
        return super().get_queryset().filter(status="published").order_by("published_date").prefetch_related("tags")


class BlogAuthorList(BlogList):
    """Filter BlogList by author."""

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(Q(status="published") & Q(author__username=self.kwargs["author"]))
            .prefetch_related("tags")
        )


class BlogTagList(BlogList):
    """Filter BlogList by tag."""

    def get_queryset(self):
        tags_filter = Q(tags__in=Blogtag.objects.filter(name=self.kwargs["tag"]))
        return super().get_queryset().filter(Q(status="published") & Q(tags_filter)).prefetch_related("tags")
