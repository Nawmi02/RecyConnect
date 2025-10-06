# Buyer/views.py
from decimal import Decimal, InvalidOperation
import json

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum, Avg
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import models

from RecyCon.models import Product
from Rewards.models import Activity
from Pickup.models import PickupRequest          
from Marketplace.models import MarketOrder      
from User.models import User, CollectorRating

from Education.views import (
    education_awareness_b,
    view_guide_pdf,
    download_guide_pdf,
    view_video,
    download_video,
)

def _buyer_stats(user):
    total_weight = Activity.objects.filter(user=user).aggregate(s=Sum("weight_kg"))["s"] or Decimal("0")
    return {
        "points": user.points,
        "total_pickups": user.total_pickups,
        "total_weight_kg": Decimal(total_weight).quantize(Decimal("0.001")),
        "total_co2_kg": user.total_co2_saved_kg,
    }


@login_required(login_url="user:login")
def dashboard(request):

    user = request.user
    if getattr(user, "role", None) != "buyer":
        messages.error(request, "Buyer dashboard is only for Buyer accounts.")
        return redirect("/")

    # ---------- Recycle Now (Pickup Request submit) ----------
    if request.method == "POST" and request.POST.get("action") == "request_pickup":
        kind = (request.POST.get("kind") or "").strip()
        wraw = request.POST.get("weight") or "0"
        praw = request.POST.get("price") or "0"

        try:
            weight = Decimal(wraw)
            price = Decimal(praw)
            if weight <= 0 or price < 0:
                raise InvalidOperation
        except Exception:
            messages.error(request, "Please provide valid numbers for weight and price.")
            return redirect(request.path)

        with transaction.atomic():
            # 1) Create Product snapshot for this request
            product = Product.objects.create(kind=kind, weight=weight, price=price)

            # 2) Find all approved collectors who collect this kind
            collectors = type(user).objects.filter(
                role="collector", is_approved=True, collector_product=kind
            ).only("id")

            # 3) Fan-out PickupRequest to each matching collector
            created = 0
            for c in collectors:
                _, ok = PickupRequest.objects.get_or_create(
                    requester=user,
                    collector=c,
                    product=product,
                    defaults={"status": PickupRequest.Status.PENDING},
                )
                if ok:
                    created += 1

        if created:
            messages.success(request, f"Pickup request sent to {created} matching collector(s).")
        else:
            messages.warning(request, "No approved collectors found for this product type.")
        return redirect(request.path)

    # ---------- Lists for UI ----------
    pickup_qs = (
        PickupRequest.objects
        .filter(requester=user)
        .select_related("collector", "product")
        .order_by("-created_at")[:10]
    )

    orders_qs = (
        MarketOrder.objects
        .filter(buyer=user)
        .select_related("collector", "marketplace")
        .order_by("-created_at")[:10]
    )

    # ---------- Order KPI stats ----------
    orders_all = MarketOrder.objects.filter(buyer=user)
    order_stats = {
        "total_orders": orders_all.count(),
        "pending_orders": orders_all.filter(status=MarketOrder.Status.PENDING).count(),
        "delivered_orders": orders_all.filter(status=MarketOrder.Status.DELIVERED).count(),
        "total_spent": (orders_all.aggregate(s=Sum("total_price"))["s"] or Decimal("0")).quantize(Decimal("0.01")),
    }

    ctx = {
        "stats": _buyer_stats(user),   # points / pickups / weight / CO2
        "requests": pickup_qs,         # recent pickup requests
        "orders": orders_qs,           # recent marketplace orders
        "order_stats": order_stats,    # KPI cards for marketplace
    }
    return render(request, "Buyer/b_dash.html", ctx)


# ---------------- Community ----------------

@login_required(login_url="user:login")
def community(request):
    """
    Community view for Buyer - shows all users except admin and current user.
    """
    users = (
        User.objects
        .exclude(role="admin")
        .exclude(id=request.user.id)
    )

    # Attach avg rating/count for collectors
    for u in users:
        if u.role == "collector":
            agg = CollectorRating.objects.filter(collector=u).aggregate(
                avg=Avg("stars"),
                cnt=Sum(models.Value(1))
            )
            u.average_rating = float(agg.get("avg") or 0.0)
            u.ratings_count = int(CollectorRating.objects.filter(collector=u).count())

    return render(request, "Buyer/b_community.html", {"users": users})


@login_required(login_url="user:login")
@require_POST
@csrf_exempt
def rate_collector(request, user_id):
    """
    Allow buyers to rate collectors.
    """
    try:
        data = json.loads(request.body or "{}")
        rating_value = int(data.get("rating"))

        if rating_value < 1 or rating_value > 5:
            return JsonResponse({"success": False, "error": "Rating must be between 1 and 5"})

        collector = get_object_or_404(User, id=user_id, role="collector")

        existing = CollectorRating.objects.filter(
            rater=request.user, collector=collector
        ).first()

        if existing:
            existing.stars = rating_value
            existing.save()
            message = "Rating updated successfully!"
        else:
            CollectorRating.objects.create(
                rater=request.user, collector=collector, stars=rating_value
            )
            message = "Rating submitted successfully!"

        collector.recompute_rating()

        return JsonResponse({
            "success": True,
            "message": message,
            "new_avg_rating": float(collector.average_rating),
            "new_ratings_count": collector.ratings_count,
        })

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


# ---------------- Misc pages ----------------

@login_required(login_url="user:login")
def notifications(request):
    return render(request, "Buyer/b_notifications.html")


@login_required(login_url="user:login")
def profile(request):
    return render(request, "Buyer/b_profile.html")


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

            if request.FILES.get("profile_image"):
                user.profile_image = request.FILES["profile_image"]

            try:
                user.full_clean(exclude=["password"])
                user.save()
                messages.success(request, "Profile updated successfully.")
                return redirect("buyer:settings")
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
                return redirect("buyer:settings")

        else:
            messages.error(request, "Unknown form submission.")

    return render(request, "Buyer/b_settings.html")


@login_required(login_url="user:login")
def history(request):
    return render(request, "Buyer/b_history.html")
