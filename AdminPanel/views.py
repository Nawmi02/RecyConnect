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
from django.apps import apps
from Education.models import Learn, Tag
from django.db.models import Q

from User.services import (
    send_account_approved_email,
    send_admin_created_email,
)

User = get_user_model()

def staff_or_super(u):
    return u.is_authenticated and (u.is_superuser or u.is_staff)

guard = user_passes_test(staff_or_super, login_url="user:login")  

# Dashboard (now passes pending_users) 
@guard
def dashboard(request):
    pending = User.objects.filter(is_approved=False).order_by("-date_joined")
    return render(request, "Admin/ad_dashboard.html", {"pending_users": pending})

#  Approvals list (optional separate page) 
@guard
def approvals(request):
    pending = User.objects.filter(is_approved=False).order_by("-date_joined")
    return render(request, "Admin/approvals.html", {"pending_users": pending})

# Approve a user + send mail 
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

# Decline a user (simple: leave inactive & not approved) 
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

# Create admin + send mail
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
         role="admin",   
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

#Community
@guard
def community(request):
    q = (request.GET.get("q") or "").strip()
    role = (request.GET.get("role") or "").strip().lower()

    users = User.objects.filter(
    Q(is_approved=True) | Q(is_staff=True) | Q(is_superuser=True)
)

    try:
        role_choices = [(c, lbl) for c, lbl in User.Role.choices]
    except Exception:
        role_choices = [
            ("buyer", "Buyer"),
            ("collector", "Collector"),
            ("household", "Household"),
            ("recycler", "Recycler"),
            ("admin", "Admin"),
        ]

    # role filter
    valid_codes = {c for c, _ in role_choices}
    if role and role in valid_codes:
        users = users.filter(role=role)

    # search
    if q:
        users = users.filter(
            Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q)
        )

    users = users.order_by("-date_joined")

    return render(
        request,
        "Admin/ad_community.html",
        {
            "users": users,
            "q": q,
            "role": role,
            "role_choices": role_choices,  
        },
    )
#Learn
@guard
def learn(request):
    for code, label in Tag.Choices.choices:
        Tag.objects.get_or_create(name=code)

    if request.method == "POST":
        title       = (request.POST.get("title") or "").strip()
        topic       = (request.POST.get("topic") or "").strip()
        category    = request.POST.get("category") or ""
        description = (request.POST.get("description") or "").strip()
        read_time   = int(request.POST.get("read_time") or 0)

        image      = request.FILES.get("image")
        pdf_file   = request.FILES.get("pdf_file")
        video_file = request.FILES.get("video_file")
        quick_text = request.POST.get("quick_text") or ""

        tag_codes = request.POST.getlist("tag_codes")  

        if not topic:
            messages.error(request, "Topic is required.")
            return redirect("adminpanel:learn")

        item = Learn(
            title=title,
            topic=topic,
            category=category,
            description=description,
            read_time=read_time,
            image=image,
            pdf_file=pdf_file,
            video_file=video_file,
            quick_text=quick_text,
        )

        try:
            with transaction.atomic():
                item.full_clean()
                item.save()
                if tag_codes:
                    tags = list(Tag.objects.filter(name__in=tag_codes))
                    item.tags.set(tags)

            messages.success(request, "Content added successfully.")
        except ValidationError as e:
            for field, errs in e.message_dict.items():
                for msg in errs:
                    messages.error(request, f"{field}: {msg}")
        except Exception as e:
            messages.error(request, f"Failed to add content: {e}")

        return redirect("adminpanel:learn")

    ctx = {
        "learns": Learn.objects.all(),
        "cat_choices": Learn.Category.choices,
        "tag_opts": Tag.Choices.choices,
    }
    return render(request, "Admin/ad_learn.html", ctx)

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

        #  Profile update 
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

        #  Password change 
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

            try:
                validate_password(new_pw, user=u)  
            except ValidationError as e:
                for msg in e.messages:
                    messages.error(request, msg)
                return redirect("adminpanel:settings")

            u.set_password(new_pw)
            u.save(update_fields=["password"])
            update_session_auth_hash(request, u)  
            messages.success(request, "Password updated successfully.")
            return redirect("adminpanel:settings")
      
        messages.error(request, "Unknown action.")
        return redirect("adminpanel:settings")

    return render(request, "Admin/ad_settings.html")