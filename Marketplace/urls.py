from django.urls import path
from . import views

app_name = "marketplace"

urlpatterns = [
    path("collector/",  views.marketplace_page, {"role": "collector"},  name="collector"),
    path("buyer/",      views.marketplace_page, {"role": "buyer"},      name="buyer"),
    path("household/",  views.marketplace_page, {"role": "household"},  name="household"),
    path("admin/",      views.marketplace_page, {"role": "admin"},      name="admin"),

    path("item/<int:pk>/", views.marketplace_detail, name="detail"),
    path("buy/<int:pk>/", views.marketplace_buy, name="buy"),
]
