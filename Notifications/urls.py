from django.urls import path
from . import views

urlpatterns = [
    path('', views.notification_list, name='notification_list'),
    path('create/', views.notification_create, name='notification_create'),
    path('update/<int:id>/', views.notification_update, name='notification_update'),
    path('delete/<int:id>/', views.notification_delete, name='notification_delete'),
]
