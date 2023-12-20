from django.urls import path

from gouthelper.users.views import (
    pseudopatient_create_view,
    pseudopatient_list_view,
    user_detail_view,
    user_redirect_view,
    user_update_view,
)

app_name = "users"
urlpatterns = [
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("<str:username>/", view=user_detail_view, name="detail"),
    path("pseudopatients/create/", view=pseudopatient_create_view, name="create-pseudopatient"),
    path(
        "pseudopatients/provider-create/<str:username>/",
        view=pseudopatient_create_view,
        name="provider-create-pseudopatient",
    ),
    path("<str:username>/pseudopatients/", view=pseudopatient_list_view, name="pseudopatients"),
]
