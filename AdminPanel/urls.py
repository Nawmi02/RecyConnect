from django.urls import path
from . import views

app_name = "adminpanel"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("approvals/", views.approvals, name="approvals"),
    path("approve/<int:pk>/", views.approve_user, name="approve_user"),
    path("decline/<int:pk>/", views.decline_user, name="decline_user"),  

    path("create-admin/", views.create_admin, name="create_admin"),
    path("community/", views.community, name="community"),
    path("learn/", views.learn, name="learn"),
    path("my-profile/", views.my_profile, name="my_profile"),
    path("settings/", views.settings_view, name="settings"),
]
