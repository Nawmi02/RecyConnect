# AdminPanel/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
import secrets
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from User.services import (
    send_account_approved_email,
    send_admin_created_email,
)

User = get_user_model()

def staff_or_super(u):
    return u.is_authenticated and (u.is_superuser or u.is_staff)

guard = user_passes_test(staff_or_super, login_url="user:login")  

# ---------- Dashboard (now passes pending_users) ----------
@guard
def dashboard(request):
    pending = User.objects.filter(is_approved=False).order_by("-date_joined")
    return render(request, "Admin/ad_dashboard.html", {"pending_users": pending})

# ---------- Approvals list (optional separate page) ----------
@guard
def approvals(request):
    pending = User.objects.filter(is_approved=False).order_by("-date_joined")
    return render(request, "Admin/approvals.html", {"pending_users": pending})

# ---------- Approve a user + send mail ----------
@guard
@transaction.atomic
def approve_user(request, pk):
    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("adminpanel:dashboard")

    target = get_object_or_404(User, pk=pk)

    if target.is_approved:
        messages.info(request, "This account is already approved.")
        return redirect("adminpanel:dashboard")

    # Approve + activate
    target.is_approved = True
    target.is_active = True
    target.approved_at = timezone.now()
    target.approved_by = request.user
    target.save(update_fields=["is_approved", "is_active", "approved_at", "approved_by"])

    transaction.on_commit(lambda: send_account_approved_email(target))
    messages.success(request, f"Approved. A confirmation email will be sent to {target.email}.")
    return redirect("adminpanel:dashboard")

# ---------- Decline a user (simple: leave inactive & not approved) ----------
@guard
@transaction.atomic
def decline_user(request, pk):
    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("adminpanel:dashboard")

    target = get_object_or_404(User, pk=pk)
    target.is_active = False
    target.is_approved = False
    target.save(update_fields=["is_active", "is_approved"])
    messages.success(request, f"Declined {target.email}.")
    return redirect("adminpanel:dashboard")

# ---------- Create admin + send mail ----------
@guard
@transaction.atomic
def create_admin(request):
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        name  = (request.POST.get("name") or "").strip()
        make_super = request.POST.get("is_superuser") == "on"

        if not email:
            messages.error(request, "Email is required.")
            return redirect("adminpanel:create_admin")

        if User.objects.filter(email=email).exists():
            messages.error(request, "This email is already in use.")
            return redirect("adminpanel:create_admin")

        raw_password = secrets.token_urlsafe(10)

        admin_user = User(
            email=email,
            name=name,
            role="buyer",   
            is_staff=True,
            is_superuser=bool(make_super),
            is_active=True,
            is_approved=True,
        )
        admin_user.set_password(raw_password)
        admin_user.save()

        transaction.on_commit(lambda: send_admin_created_email(admin_user, raw_password))
        messages.success(request, f"Admin created. An email has been sent to {email}.")
        return redirect("adminpanel:dashboard")

    return render(request, "Admin/create_admin.html")

@guard
def community(request):    return render(request, "Admin/ad_community.html")
@guard
def marketplace(request):  return render(request, "Admin/ad_marketplace.html")
@guard
def learn(request):        return render(request, "Admin/ad_learn.html")
@guard
def rewards(request):      return render(request, "Admin/ad_rewards.html")
@guard
def notifications(request):return render(request, "Admin/ad_notifications.html")
@guard
def my_profile(request):   return render(request, "Admin/ad_profile.html")

#Settings
User = get_user_model()

@guard
def settings_view(request):
    if request.method == "POST":
        intent = request.POST.get("intent", "profile")
        u = request.user

        # ---------- Profile update ----------
        if intent == "profile":
            u.name      = (request.POST.get("name") or "").strip()
            u.phone     = (request.POST.get("phone") or "").strip()
            u.address   = (request.POST.get("address") or "").strip()
            u.facebook  = (request.POST.get("facebook") or "").strip()
            u.instagram = (request.POST.get("instagram") or "").strip()
            u.twitter   = (request.POST.get("twitter") or "").strip()

            img = request.FILES.get("profile_image")
            if img:
                u.profile_image = img

            try:
                u.full_clean()
                u.save()
                messages.success(request, "Profile updated successfully.")
            except ValidationError as e:
                for field, errs in e.message_dict.items():
                    for msg in errs:
                        messages.error(request, f"{field}: {msg}")

            return redirect("adminpanel:settings")

        # ---------- Password change ----------
        if intent == "password":
            old_pw = request.POST.get("old_password") or ""
            new_pw = request.POST.get("new_password") or ""
            cfm_pw = request.POST.get("confirm_password") or ""

            if not u.check_password(old_pw):
                messages.error(request, "Old password is incorrect.")
                return redirect("adminpanel:settings")

            if len(new_pw) < 8:
                messages.error(request, "New password must be at least 8 characters.")
                return redirect("adminpanel:settings")

            if new_pw != cfm_pw:
                messages.error(request, "New passwords do not match.")
                return redirect("adminpanel:settings")

            # Django validators (if configured) + generic checks
            try:
                validate_password(new_pw, user=u)  # will no-op if validators not set
            except ValidationError as e:
                for msg in e.messages:
                    messages.error(request, msg)
                return redirect("adminpanel:settings")

            u.set_password(new_pw)
            u.save(update_fields=["password"])
            update_session_auth_hash(request, u)  # keep user logged in
            messages.success(request, "Password updated successfully.")
            return redirect("adminpanel:settings")

        # Fallback
        messages.error(request, "Unknown action.")
        return redirect("adminpanel:settings")

    # GET
    return render(request, "Admin/ad_settings.html")