from django.urls import path
from . import views as user_views

app_name = "user"

urlpatterns = [
    # Auth
    path("register/", user_views.register_view, name="register"),
    path("login/",    user_views.login_view,    name="login"),
    path("logout/",   user_views.logout_view,   name="logout"),
    path("set-password/", user_views.set_password_view, name="set_password"),

    # Dashboards
    path("household/", user_views.household_dashboard, name="dash_household"),
    path("buyer/",     user_views.buyer_dashboard,     name="dash_buyer"),
    path("recycler/",  user_views.recycler_dashboard,  name="dash_recycler"),
    path("collector/", user_views.collector_dashboard, name="dash_collector"),
]
