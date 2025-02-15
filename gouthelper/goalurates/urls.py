from django.urls import path  # type: ignore

from .views import GoalUrateAbout, GoalUrateCreate, GoalUrateDetail, GoalUratePseudopatientCreate, GoalUrateUpdate

app_name = "goalurates"

urlpatterns = [
    path("about/", GoalUrateAbout.as_view(), name="about"),
    path("create/", GoalUrateCreate.as_view(), name="create"),
    path("<uuid:patient>/create/", GoalUratePseudopatientCreate.as_view(), name="patient-create"),
    path("<uuid:pk>/", GoalUrateDetail.as_view(), name="detail"),
    path("update/<uuid:pk>/", GoalUrateUpdate.as_view(), name="update"),
]
