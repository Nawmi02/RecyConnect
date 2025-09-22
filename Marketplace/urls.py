from django.urls import path
from . import views

urlpatterns = [
    path('', views.marketplace_list, name='marketplace_list'),
    path('create/', views.marketplace_create, name='marketplace_create'),
    path('update/<int:id>/', views.marketplace_update, name='marketplace_update'),
    path('delete/<int:id>/', views.marketplace_delete, name='marketplace_delete'),
    path('detail/<int:id>/', views.marketplace_detail, name='marketplace_detail'),
]
