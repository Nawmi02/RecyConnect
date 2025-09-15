from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from .models import User

# -------- Register --------
def register_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")
        role = request.POST.get("role")

        # password match check
        if password1 != password2:
            messages.error(request, "Passwords do not match")
            return redirect("register")

        # email already taken check
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("register")

        # create user
        user = User(email=email, role=role)
        user.set_password(password1)  
        user.save()

        messages.success(request, "Account created successfully. Please log in.")
        return redirect("login")

    return render(request, "register.html")


# -------- Login --------
def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            return redirect("home")   
        else:
            messages.error(request, "Invalid email or password")
            return redirect("login")

    return render(request, "login.html")


# -------- Logout --------
def logout_view(request):
    logout(request)
    return redirect("login")
