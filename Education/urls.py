
from django.urls import path
from . import views

app_name = "education"

urlpatterns = [
    path("household/", views.education_awareness_h, name="education_awareness_h"),
    path("collector/", views.education_awareness_c, name="education_awareness_c"),
    path("buyer/", views.education_awareness_b, name="education_awareness_b"),

    # Guides/Articles (PDF)
    path("<int:pk>/pdf/view/", views.view_guide_pdf, name="view_guide_pdf"),
    path("<int:pk>/pdf/download/", views.download_guide_pdf, name="download_guide_pdf"),

    # Videos
    path("<int:pk>/video/view/", views.view_video, name="view_video"),
    path("<int:pk>/video/download/", views.download_video, name="download_video"),
]

