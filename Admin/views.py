# Admin/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test

def is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)

@login_required(login_url="login")
@user_passes_test(is_admin, login_url="landingPage")
def admin_home(request):
    return render(request, "adminbase.html")
