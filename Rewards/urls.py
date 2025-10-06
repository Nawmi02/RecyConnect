from django.urls import path
from . import views

app_name = "rewards"

urlpatterns = [
    path("collector/",  views.rewards_page, {"role": "collector"},  name="collector"),
    path("buyer/",      views.rewards_page, {"role": "buyer"},      name="buyer"),
    path("household/",  views.rewards_page, {"role": "household"},  name="household"),
    path("admin/",      views.rewards_page, {"role": "admin"},      name="admin"),
]
