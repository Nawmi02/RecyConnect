# Household/urls.py
from django.urls import path
from . import views

app_name = "household"

urlpatterns = [
    path("education/", views.education_awareness, name="education_awareness"),
    path("education/<int:pk>/pdf/view/", views.view_guide_pdf, name="view_guide_pdf"),
    path("education/<int:pk>/pdf/download/", views.download_guide_pdf, name="download_guide_pdf"),
    path("education/<int:pk>/video/view/", views.view_video, name="view_video"),
    path("education/<int:pk>/video/download/", views.download_video, name="download_video"),
]
