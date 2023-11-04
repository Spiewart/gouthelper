from django.urls import path  # type: ignore

from .views import BlogAuthorList, BlogDetail, BlogList, BlogTagList

app_name = "blog"

urlpatterns = [
    path("", BlogList.as_view(), name="blog"),
    path("<slug:slug>/", BlogDetail.as_view(), name="blog_detail"),
    path("by-author/<str:author>/", BlogAuthorList.as_view(), name="blog_author_list"),
    path("by-tag/<str:tag>/", BlogTagList.as_view(), name="blog_tag_list"),
]
