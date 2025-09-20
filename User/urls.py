# User/urls.py
from django.urls import path
from . import views as user_views

urlpatterns = [
    # auth
    path("register/", user_views.register_view, name="register"),
    path("login/",    user_views.login_view,    name="login"),
    path("logout/",   user_views.logout_view,   name="logout"),
    path("set-password/", user_views.set_password_view, name="set_password"),

    # dashboards
    path("dashboard/household/", user_views.household_dashboard, name="dash_household"),
    path("dashboard/buyer/",     user_views.buyer_dashboard,     name="dash_buyer"),
    path("dashboard/recycler/",  user_views.recycler_dashboard,  name="dash_recycler"),
    path("dashboard/collector/", user_views.collector_dashboard, name="dash_collector"),

    # custom admin panel (superuser only)
    path("admin/", user_views.admin_panel, name="admin_panel"),
]
