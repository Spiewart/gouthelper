from django.urls import path  # type: ignore

from .views import FlareAbout, FlareCreate, FlareDelete, FlareDetail, FlarePatientList, FlareUpdate

app_name = "flares"

urlpatterns = [
    path("about/", FlareAbout.as_view(), name="about"),
    path("create/", FlareCreate.as_view(), name="create"),
    path("<uuid:patient>/create/", FlareCreate.as_view(), name="patient-create"),
    path("<uuid:pk>/", FlareDetail.as_view(), name="detail"),
    path("update/<uuid:pk>/", FlareUpdate.as_view(), name="update"),
    path("<uuid:patient>/", view=FlarePatientList.as_view(), name="list"),
    path(
        "delete/<uuid:pk>/",
        view=FlareDelete.as_view(),
        name="delete",
    ),
]
