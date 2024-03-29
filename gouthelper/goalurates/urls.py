from django.urls import path  # type: ignore

from .views import (
    GoalUrateAbout,
    GoalUrateCreate,
    GoalUrateDetail,
    GoalUratePseudopatientCreate,
    GoalUratePseudopatientDetail,
    GoalUratePseudopatientUpdate,
    GoalUrateUpdate,
)

app_name = "goalurates"

urlpatterns = [
    path("about/", GoalUrateAbout.as_view(), name="about"),
    path("create/", GoalUrateCreate.as_view(), name="create"),
    path("<uuid:pk>/", GoalUrateDetail.as_view(), name="detail"),
    path("ultaid/<uuid:ultaid>/create", GoalUrateCreate.as_view(), name="ultaid-create"),
    path("update/<uuid:pk>/", GoalUrateUpdate.as_view(), name="update"),
    path("<str:username>/create/", GoalUratePseudopatientCreate.as_view(), name="pseudopatient-create"),
    path("<str:username>/", view=GoalUratePseudopatientDetail.as_view(), name="pseudopatient-detail"),
    path("<str:username>/update/", GoalUratePseudopatientUpdate.as_view(), name="pseudopatient-update"),
]
