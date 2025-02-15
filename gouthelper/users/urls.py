from django.urls import path

from .views import (
    patient_create_view,
    patient_delete_view,
    patient_detail_view,
    patient_list_view,
    patient_update_view,
    user_delete_view,
    user_detail_view,
    user_redirect_view,
    user_update_view,
)

app_name = "users"
urlpatterns = [
    path("patients/create/", view=patient_create_view, name="patient-create"),
    path("patients/delete/<uuid:patient>/", view=patient_delete_view, name="patient-delete"),
    path(
        "patients/provider-create/<str:username>/",
        view=patient_create_view,
        name="provider-patient-create",
    ),
    path("patients/<uuid:patient>/", view=patient_detail_view, name="patient-detail"),
    path("patients/<uuid:patient>/update/", view=patient_update_view, name="patient-update"),
    path("<str:username>/patients/", view=patient_list_view, name="patients"),
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("~delete/", view=user_delete_view, name="delete"),
    path("<str:username>/", view=user_detail_view, name="detail"),
]
