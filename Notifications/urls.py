from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    # Admin-panel pages (HTML)
    path("inbox/", views.inbox, name="inbox"),

    # Actions (POST)
    path("read/<int:pk>/", views.mark_read, name="mark_read"),
    path("read-all/", views.mark_all_read, name="mark_all_read"),

    # Lightweight APIs (for navbar bell)
    path("api/unread-count/", views.unread_count_api, name="unread_count_api"),
    path("api/list/", views.list_api, name="list_api"),
]