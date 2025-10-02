from django.urls import path
from . import views

urlpatterns = [
    path('', views.reward_list, name='reward_list'),
    path('create/', views.reward_create, name='reward_create'),
    path('update/<int:id>/', views.reward_update, name='reward_update'),
    path('delete/<int:id>/', views.reward_delete, name='reward_delete'),
    path('detail/<int:id>/', views.reward_detail, name='reward_detail'),
]