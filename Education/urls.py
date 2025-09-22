<<<<<<< HEAD
=======
from django.urls import path
from . import views

app_name = "education"

urlpatterns = [
    path("", views.education_awareness, name="education_awareness"),

    # Guides/Articles (PDF)
    path("<int:pk>/pdf/view/", views.view_guide_pdf, name="view_guide_pdf"),
    path("<int:pk>/pdf/download/", views.download_guide_pdf, name="download_guide_pdf"),

    # Videos
    path("<int:pk>/video/view/", views.view_video, name="view_video"),
    path("<int:pk>/video/download/", views.download_video, name="download_video"),
]
>>>>>>> 2cf989ab239de9697124b37f9b8e09007d053f63
