from django.urls import path  # type: ignore

from .views import (
    UltAidAbout,
    UltAidCreate,
    UltAidDetail,
    UltAidPseudopatientCreate,
    UltAidPseudopatientDetail,
    UltAidPseudopatientUpdate,
    UltAidUpdate,
)

app_name = "ultaids"

urlpatterns = [
    path("about/", UltAidAbout.as_view(), name="about"),
    path("create/", UltAidCreate.as_view(), name="create"),
    path("<uuid:pk>/", UltAidDetail.as_view(), name="detail"),
    path("update/<uuid:pk>/", UltAidUpdate.as_view(), name="update"),
    path(
        "goutpatient-create/<uuid:pseudopatient>/create/",
        UltAidPseudopatientCreate.as_view(),
        name="pseudopatient-create",
    ),
    path("ult-create/<uuid:ult>/", UltAidCreate.as_view(), name="ult-create"),
    path(
        "goutpatient-detail/<uuid:pseudopatient>/",
        view=UltAidPseudopatientDetail.as_view(),
        name="pseudopatient-detail",
    ),
    path(
        "goutpatient-update/<uuid:pseudopatient>/update/",
        UltAidPseudopatientUpdate.as_view(),
        name="pseudopatient-update",
    ),
]
