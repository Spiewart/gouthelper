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
    path("<str:username>/create/", UltPseudopatientCreate.as_view(), name="pseudopatient-create"),
    path("<str:username>/", view=UltPseudopatientDetail.as_view(), name="pseudopatient-detail"),
    path("<str:username>/update/", UltPseudopatientUpdate.as_view(), name="pseudopatient-update"),
]
