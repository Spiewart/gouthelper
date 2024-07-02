from django.urls import path

from .views import (
    pseudopatient_create_view,
    pseudopatient_detail_view,
    pseudopatient_flare_create_view,
    pseudopatient_list_view,
    pseudopatient_update_view,
    user_delete_view,
    user_detail_view,
    user_redirect_view,
    user_update_view,
)

app_name = "users"
urlpatterns = [
    path("pseudopatients/create/", view=pseudopatient_create_view, name="pseudopatient-create"),
    path(
        "pseudopatients/create/<uuid:flare>/", view=pseudopatient_flare_create_view, name="pseudopatient-flare-create"
    ),
    path("pseudopatients/delete/<str:username>/", view=user_delete_view, name="pseudopatient-delete"),
    path(
        "pseudopatients/provider-create/<str:username>/",
        view=pseudopatient_create_view,
        name="provider-pseudopatient-create",
    ),
    path(
        "pseudopatients/provider-create/<str:username>/<uuid:flare>/",
        view=pseudopatient_flare_create_view,
        name="provider-pseudopatient-flare-create",
    ),
    path("pseudopatients/<str:username>/", view=pseudopatient_detail_view, name="pseudopatient-detail"),
    path("pseudopatients/<str:username>/update/", view=pseudopatient_update_view, name="pseudopatient-update"),
    path("<str:username>/pseudopatients/", view=pseudopatient_list_view, name="pseudopatients"),
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("~delete/", view=user_delete_view, name="delete"),
    path("<str:username>/", view=user_detail_view, name="detail"),
]
