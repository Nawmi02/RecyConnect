from django.urls import path
from . import views

app_name = "buyer"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),            
    path("dashboard/", views.dashboard, name="dashboard"),
    path('community/', views.community, name='community'),
    path('rate-collector/<int:user_id>/', views.rate_collector, name='rate_collector'),
    path("notifications/", views.notifications, name="notifications"),
    path("profile/", views.profile, name="profile"),
    path("settings/", views.settings, name="settings"),
    path("history/", views.history, name="history"),
    
    path("education/", views.education_awareness_b, name="education_awareness_b"),
    path("education/<int:pk>/pdf/view/", views.view_guide_pdf, name="view_guide_pdf"),
    path("education/<int:pk>/pdf/download/", views.download_guide_pdf, name="download_guide_pdf"),
    path("education/<int:pk>/video/view/", views.view_video, name="view_video"),
    path("education/<int:pk>/video/download/", views.download_video, name="download_video"),
]
