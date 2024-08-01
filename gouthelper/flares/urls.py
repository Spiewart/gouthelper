from django.urls import path  # type: ignore

from .views import (
    FlareAbout,
    FlareCreate,
    FlareDetail,
    FlarePseudopatientCreate,
    FlarePseudopatientDelete,
    FlarePseudopatientDetail,
    FlarePseudopatientList,
    FlarePseudopatientUpdate,
    FlareUpdate,
)

app_name = "flares"

urlpatterns = [
    path("about/", FlareAbout.as_view(), name="about"),
    path("create/", FlareCreate.as_view(), name="create"),
    path("<uuid:pk>/", FlareDetail.as_view(), name="detail"),
    path("update/<uuid:pk>/", FlareUpdate.as_view(), name="update"),
    path("goutpatient-list/<uuid:pseudopatient>/", view=FlarePseudopatientList.as_view(), name="pseudopatient-list"),
    path("goutpatient-create/<uuid:pseudopatient>/", FlarePseudopatientCreate.as_view(), name="pseudopatient-create"),
    path(
        "goutpatient-delete/<uuid:pseudopatient>/<uuid:pk>/",
        view=FlarePseudopatientDelete.as_view(),
        name="pseudopatient-delete",
    ),
    path(
        "goutpatient-detail/<uuid:pseudopatient>/<uuid:pk>/",
        view=FlarePseudopatientDetail.as_view(),
        name="pseudopatient-detail",
    ),
    path(
        "goutpatient-update/<uuid:pseudopatient>/<uuid:pk>/",
        FlarePseudopatientUpdate.as_view(),
        name="pseudopatient-update",
    ),
]
