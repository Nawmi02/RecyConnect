from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from Education.views import (
    education_awareness_b,
    view_guide_pdf,
    download_guide_pdf,
    view_video,
    download_video,
)

@login_required(login_url="user:login") 
def dashboard(request):
    return render(request, "Buyer/b_dash.html")

@login_required(login_url="user:login")
def community(request):
    return render(request, "Buyer/b_community.html")

@login_required(login_url="user:login")
def marketplace(request):
    return render(request, "Buyer/b_marketplace.html")

@login_required(login_url="user:login")
def rewards(request):
    return render(request, "Buyer/b_rewards.html")

@login_required(login_url="user:login")
def notifications(request):
    return render(request, "Buyer/b_notifications.html")

@login_required(login_url="user:login")
def profile(request):
    return render(request, "Buyer/b_profile.html")

@login_required(login_url="user:login")
def settings(request):
    return render(request, "Buyer/b_settings.html")

@login_required(login_url="user:login")
def history(request):
    return render(request, "Buyer/b_history.html")
