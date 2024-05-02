from django.urls import path  # type: ignore

from .views import (
    PpxAidAbout,
    PpxAidCreate,
    PpxAidDetail,
    PpxAidPseudopatientCreate,
    PpxAidPseudopatientDetail,
    PpxAidPseudopatientUpdate,
    PpxAidUpdate,
)

app_name = "ppxaids"

urlpatterns = [
    path("about/", PpxAidAbout.as_view(), name="about"),
    path("create/", PpxAidCreate.as_view(), name="create"),
    path("<uuid:pk>/", PpxAidDetail.as_view(), name="detail"),
    path("update/<uuid:pk>/", PpxAidUpdate.as_view(), name="update"),
    path("ppx/<uuid:ppx>/create", PpxAidCreate.as_view(), name="ppx-create"),
    path("<str:username>/create/", PpxAidPseudopatientCreate.as_view(), name="pseudopatient-create"),
    path("<str:username>/", view=PpxAidPseudopatientDetail.as_view(), name="pseudopatient-detail"),
    path("<str:username>/update/", PpxAidPseudopatientUpdate.as_view(), name="pseudopatient-update"),
]
