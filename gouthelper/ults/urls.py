from django.urls import path  # type: ignore

from .views import (
    UltAbout,
    UltCreate,
    UltDetail,
    UltPseudopatientCreate,
    UltPseudopatientDetail,
    UltPseudopatientUpdate,
    UltUpdate,
)

app_name = "ults"

urlpatterns = [
    path("about/", UltAbout.as_view(), name="about"),
    path("create/", UltCreate.as_view(), name="create"),
    path("<uuid:pk>/", UltDetail.as_view(), name="detail"),
    path("update/<uuid:pk>/", UltUpdate.as_view(), name="update"),
    path("goutpatient-create/<uuid:pseudopatient>/", UltPseudopatientCreate.as_view(), name="pseudopatient-create"),
    path(
        "goutpatient-detail/<uuid:pseudopatient>/", view=UltPseudopatientDetail.as_view(), name="pseudopatient-detail"
    ),
    path("goutpatient-update/<uuid:pseudopatient>/", UltPseudopatientUpdate.as_view(), name="pseudopatient-update"),
]
