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
    path("<str:username>/create/", FlareAidPseudopatientCreate.as_view(), name="pseudopatient-create"),
    path("<str:username>/", view=FlareAidPseudopatientDetail.as_view(), name="pseudopatient-detail"),
    path("<str:username>/update/", FlareAidPseudopatientUpdate.as_view(), name="pseudopatient-update"),
]
