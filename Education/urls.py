from django.urls import path
from . import views

urlpatterns = [
    path('education-awareness/', views.education_awareness, name='education_awareness'),
]
