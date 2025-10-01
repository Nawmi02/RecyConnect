from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth import update_session_auth_hash
from User.models import User  

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

@login_required(login_url="user:login")
def community(request):
    return render(request, "Collector/c_community.html")

@login_required(login_url="user:login")
def marketplace(request):
    return render(request, "Collector/c_marketplace.html")

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
                update_session_auth_hash(request, user)  # keep logged in
                messages.success(request, "Password updated successfully.")
                return redirect("collector:settings")

        else:
            messages.error(request, "Unknown form submission.")

    context = {
        "product_choices": User.ProductKind.choices,  # for dropdown
    }
    return render(request, "Collector/c_settings.html", context)

@login_required(login_url="user:login")
def history(request):
    return render(request, "Collector/c_history.html")
