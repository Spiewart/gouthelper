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
    path("<str:username>/create/", UltAidPseudopatientCreate.as_view(), name="pseudopatient-create"),
    path("<str:username>/", view=UltAidPseudopatientDetail.as_view(), name="pseudopatient-detail"),
    path("<str:username>/update/", UltAidPseudopatientUpdate.as_view(), name="pseudopatient-update"),
]
