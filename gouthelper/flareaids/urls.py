from django.urls import path  # type: ignore

from .views import (
    FlareAidAbout,
    FlareAidCreate,
    FlareAidDetail,
    FlareAidPseudopatientCreate,
    FlareAidPseudopatientDetail,
    FlareAidPseudopatientUpdate,
    FlareAidUpdate,
)

app_name = "flareaids"

urlpatterns = [
    path("about/", FlareAidAbout.as_view(), name="about"),
    path("create/", FlareAidCreate.as_view(), name="create"),
    path("<uuid:pk>/", FlareAidDetail.as_view(), name="detail"),
    path("update/<uuid:pk>/", FlareAidUpdate.as_view(), name="update"),
    path("flare/<uuid:flare>/create", FlareAidCreate.as_view(), name="flare-create"),
    path(
        "goutpatient-create/<uuid:pseudopatient>/", FlareAidPseudopatientCreate.as_view(), name="pseudopatient-create"
    ),
    path(
        "goutpatient-detail/<uuid:pseudopatient>/",
        view=FlareAidPseudopatientDetail.as_view(),
        name="pseudopatient-detail",
    ),
    path(
        "goutpatient-update/<uuid:pseudopatient>/", FlareAidPseudopatientUpdate.as_view(), name="pseudopatient-update"
    ),
]
