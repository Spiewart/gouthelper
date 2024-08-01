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
    path("ppxaid/<uuid:ppxaid>/create", PpxCreate.as_view(), name="ppxaid-create"),
    path("goutpatient-create/<uuid:pseudopatient>/", PpxPseudopatientCreate.as_view(), name="pseudopatient-create"),
    path(
        "goutpatient-detail/<uuid:pseudopatient>/", view=PpxPseudopatientDetail.as_view(), name="pseudopatient-detail"
    ),
    path("goutpatient-update/<uuid:pseudopatient>/", PpxPseudopatientUpdate.as_view(), name="pseudopatient-update"),
]
