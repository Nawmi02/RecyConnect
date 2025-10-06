from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError

User = get_user_model()

# Where to send normal users after login
ROLE_REDIRECTS = {
    "household": "user:dash_household",
    "buyer":     "user:dash_buyer",
    "recycler":  "user:dash_recycler",   
    "collector": "user:dash_collector",
}

# Superuser/staff land here (AdminPanel app, namespaced)
ADMIN_PANEL_NAME = "adminpanel:dashboard"


# ---------------- Register ----------------
def register_view(request):
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        password1 = request.POST.get("password1") or ""
        password2 = request.POST.get("password2") or ""
        role = (request.POST.get("role") or "").strip()
        id_image = request.FILES.get("id_card_image")  # collector/recycler only

        # basic validation
        if not email or not role:
            messages.error(request, "Email and role are required.")
            return redirect("register")

        if len(password1) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return redirect("register")

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered.")
            return redirect("register")

        # enforce ID image for collector/recycler
        if role in ("collector", "recycler") and not id_image:
            messages.error(
                request,
                "An ID or visiting card image is required for Collector and Recycling Centre accounts."
            )
            return redirect("register")

        # create inactive user (awaiting admin approval)
        user = User(email=email, role=role, is_active=False, is_approved=False)
        user.set_password(password1)
        if id_image:
            user.id_card_image = id_image

        try:
            user.full_clean()  # field validators + model.clean()
            user.save()
        except ValidationError as e:
            for field, errs in e.message_dict.items():
                for msg in errs:
                    messages.error(request, f"{field}: {msg}")
            return redirect("register")

        messages.success(
            request,
            "Registration successful. Your account is pending admin review. "
            "Please wait for an approval email before logging in."
        )
        return redirect("user:login")

    # GET
    return render(request, "register.html")


# ---------------- Login ----------------
def login_view(request):
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        password = request.POST.get("password") or ""

        if not email or not password:
            messages.error(request, "Email and password are required.")
            return redirect("login")

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return redirect("login")

        # authenticate uses USERNAME_FIELD -> pass email as 'username'
        user = authenticate(request, username=email, password=password)

        if not user:
            messages.error(request, "Invalid email or password.")
            return redirect("login")

        if not getattr(user, "is_active", True) or not getattr(user, "is_approved", True):
            messages.warning(request, "Your account is not approved yet.")
            return redirect("login")

        login(request, user)

        # staff/superusers -> AdminPanel
        if user.is_superuser or user.is_staff:
            return redirect(ADMIN_PANEL_NAME)

        # normal users -> role dashboards
        return redirect(ROLE_REDIRECTS.get(user.role, ADMIN_PANEL_NAME))

    # GET
    return render(request, "login.html")


# ---------------- Password change (modal POST) ----------------
def set_password_view(request):
    if request.method != "POST":
        return redirect("user:login")

    email = (request.POST.get("email") or "").strip().lower()
    new_password = request.POST.get("new_password") or ""
    confirm_password = request.POST.get("confirm_password") or ""

    if not email:
        messages.error(request, "Email is required.")
        return redirect("user:login")

    if len(new_password) < 8:
        messages.error(request, "Password must be at least 8 characters.")
        return redirect("user:login")

    if new_password != confirm_password:
        messages.error(request, "Passwords do not match.")
        return redirect("user:login")

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        messages.error(request, "No account found for that email.")
        return redirect("user:login")

    user.set_password(new_password)
    user.save(update_fields=["password"])
    messages.success(request, "Password changed successfully. Please log in.")
    return redirect("user:login")


# ---------------- Logout ----------------
def logout_view(request):
    logout(request)
    return redirect("user:login")


# ---------------- Role guard ----------------
def role_required(allowed_roles=()):
    def decorator(view_func):
        @login_required(login_url="user:login")
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if getattr(user, "is_superuser", False):
                return view_func(request, *args, **kwargs)
            if getattr(user, "role", None) in allowed_roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, "You are not authorized to view that page.")
            return redirect("user:login")
        return _wrapped
    return decorator


# ---------------- Dashboards ----------------
@role_required(("household",))
def household_dashboard(request):
    return render(request, "Household/h_dash.html", {"user": request.user})

@role_required(("buyer",))
def buyer_dashboard(request):
    return render(request, "Buyer/b_dash.html", {"user": request.user})

@role_required(("recycler",))
def recycler_dashboard(request):
    return render(request, "Buyer/b_dash.html", {"user": request.user}) 

@role_required(("collector",))
def collector_dashboard(request):
    return render(request, "Collector/c_dash.html", {"user": request.user})
