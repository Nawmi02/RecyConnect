from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("delete/<int:pk>/", views.delete, name="delete"),
    path("delete-all/", views.delete_all, name="delete_all"),
]
