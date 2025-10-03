from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth import update_session_auth_hash 
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import models
import json
from User.models import User, CollectorRating
from Marketplace.models import Marketplace, MarketTag

from Education.views import (
    education_awareness_c,
    view_guide_pdf,
    download_guide_pdf,
    view_video,
    download_video,
)

@login_required(login_url="user:login") 
def dashboard(request):
    return render(request, "Collector/c_dash.html")

#Community
@login_required(login_url="user:login")
def community(request):
    """
    Community view for Collector - shows all users except admin and current user
    """
    # Get all users except admin and current user
    users = User.objects.exclude(
        role='admin'
    ).exclude(
        id=request.user.id
    ).select_related()
    
    # Add average rating and ratings count to collector users
    for user in users:
        if user.role == 'collector':
            # Calculate average rating and count
            ratings = CollectorRating.objects.filter(collector=user)
            if ratings.exists():
                user.average_rating = ratings.aggregate(avg=models.Avg('stars'))['avg']
                user.ratings_count = ratings.count()
            else:
                user.average_rating = 0.0
                user.ratings_count = 0
    
    context = {
        'users': users
    }
    return render(request, "Collector/c_community.html", context)

#Marketplace
@login_required(login_url="user:login")
def marketplace(request):
    return render(request, "Collector/c_marketplace.html", context)

@login_required(login_url="user:login")
def rewards(request):
    return render(request, "Collector/c_rewards.html")

@login_required(login_url="user:login")
def notifications(request):
    return render(request, "Collector/c_notifications.html")

@login_required(login_url="user:login")
def profile(request):
    return render(request, "Collector/c_profile.html")

@login_required(login_url="user:login")
def settings(request):
    user = request.user
    if request.method == "POST":
        form_type = request.POST.get("form_type")

        # ---------- Profile update ----------
        if form_type == "profile":
            user.name = request.POST.get("name", "").strip()
            user.phone = request.POST.get("phone", "").strip()
            user.address = request.POST.get("address", "").strip()
            user.map_url = request.POST.get("map_url", "").strip()
            user.facebook = request.POST.get("facebook", "").strip()
            user.instagram = request.POST.get("instagram", "").strip()
            user.twitter = request.POST.get("twitter", "").strip()
            user.collector_product = request.POST.get("collector_product", "").strip()

            if request.FILES.get("profile_image"):
                user.profile_image = request.FILES["profile_image"]
            if request.FILES.get("id_card_image"):
                user.id_card_image = request.FILES["id_card_image"]

            try:
                user.full_clean(exclude=["password"])  
                user.save()
                messages.success(request, "Profile updated successfully.")
                return redirect("collector:settings")
            except ValidationError as e:
                for field, msgs in e.message_dict.items():
                    for msg in msgs:
                        messages.error(request, f"{field}: {msg}")

        # ---------- Password change ----------
        elif form_type == "password":
            old = request.POST.get("old_password", "")
            new = request.POST.get("new_password", "")
            confirm = request.POST.get("confirm_password", "")

            if not user.check_password(old):
                messages.error(request, "Current password is incorrect.")
            elif new != confirm:
                messages.error(request, "New password and Confirm password do not match.")
            elif len(new) < 8:
                messages.error(request, "New password must be at least 8 characters.")
            else:
                user.set_password(new)
                user.save()
                update_session_auth_hash(request, user)  
                messages.success(request, "Password updated successfully.")
                return redirect("collector:settings")

        else:
            messages.error(request, "Unknown form submission.")

    context = {
        "product_choices": User.ProductKind.choices, 
    }
    return render(request, "Collector/c_settings.html", context)

@login_required(login_url="user:login")
def history(request):
    return render(request, "Collector/c_history.html")
