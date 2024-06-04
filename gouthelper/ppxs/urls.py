from django.urls import path  # type: ignore

from .views import (
    PpxAbout,
    PpxCreate,
    PpxDetail,
    PpxPseudopatientCreate,
    PpxPseudopatientDetail,
    PpxPseudopatientUpdate,
    PpxUpdate,
)

app_name = "ppxs"

urlpatterns = [
    path("about/", PpxAbout.as_view(), name="about"),
    path("create/", PpxCreate.as_view(), name="create"),
    path("<uuid:pk>/", PpxDetail.as_view(), name="detail"),
    path("update/<uuid:pk>/", PpxUpdate.as_view(), name="update"),
    path("<str:username>/create/", PpxPseudopatientCreate.as_view(), name="pseudopatient-create"),
    path("<str:username>/", view=PpxPseudopatientDetail.as_view(), name="pseudopatient-detail"),
    path("<str:username>/update/", PpxPseudopatientUpdate.as_view(), name="pseudopatient-update"),
    path("ppxaid/<uuid:ppxaid>/create", PpxCreate.as_view(), name="ppxaid-create"),
]
