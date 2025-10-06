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
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Count

from RecyCon.models import Product
from Pickup.models import PickupRequest
from Marketplace.models import MarketOrder
from Rewards.models import Activity
from User.models import User, CollectorRating
from Marketplace.models import Marketplace, MarketTag

from Education.views import (
    education_awareness_c,
    view_guide_pdf,
    download_guide_pdf,
    view_video,
    download_video,
)

try:
    from Rewards.services import log_activity_and_update
except Exception:
    log_activity_and_update = None


def _co2_for_kind(kind: str) -> Decimal:
    return Product.CO2_PER_KG.get(kind, Decimal("0.0"))


def _collector_stats(user):
    """
    Collector KPI summary from COMPLETED pickups (as collector).
    """
    completed = PickupRequest.objects.filter(
        collector=user, status=PickupRequest.Status.COMPLETED
    )

    total_weight = completed.aggregate(s=Sum("weight_kg"))["s"] or Decimal("0")
    total_weight = Decimal(total_weight).quantize(Decimal("0.001"))

    est_co2 = Decimal("0.000")
    for pr in completed.only("kind", "weight_kg"):
        est_co2 += (Decimal(pr.weight_kg or 0) * _co2_for_kind(str(pr.kind))).quantize(Decimal("0.001"))

    return {
        "points": user.points,
        "total_pickups": completed.count(),
        "total_weight_kg": total_weight,
        "total_co2_kg": est_co2.quantize(Decimal("0.001")),
    }


@login_required(login_url="user:login")
def dashboard(request):
    """
    Collector dashboard:
    - Pickup requests for this collector (pending/accepted/completed)
    - Accept / Decline / Complete actions
    - Marketplace orders for this collector (pending/delivered) + KPI
    """
    user = request.user
    if getattr(user, "role", None) != "collector":
        messages.error(request, "Collector dashboard is only for Collector accounts.")
        return redirect("/")

    # -------- Actions --------
    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        pr_id = request.POST.get("pickup_id")
        order_id = request.POST.get("order_id")

        # Accept pickup
        if action == "pickup_accept" and pr_id:
            with transaction.atomic():
                pr = get_object_or_404(
                    PickupRequest.objects.select_for_update(), pk=pr_id, collector=user
                )
                if pr.status != PickupRequest.Status.PENDING:
                    messages.warning(request, "This request is no longer pending.")
                else:
                    pr.status = PickupRequest.Status.ACCEPTED
                    pr.save(update_fields=["status", "updated_at"])
                    # same product-এর অন্য pending কপি সরিয়ে দেই
                    (PickupRequest.objects
                        .filter(product=pr.product, status=PickupRequest.Status.PENDING)
                        .exclude(pk=pr.pk)
                        .delete())
                    messages.success(request, "Pickup accepted. Other pending copies removed.")
            return redirect(request.path)

        # Decline pickup
        if action == "pickup_decline" and pr_id:
            pr = get_object_or_404(PickupRequest, pk=pr_id, collector=user)
            if pr.status != PickupRequest.Status.PENDING:
                messages.warning(request, "Only pending requests can be declined.")
            else:
                pr.status = PickupRequest.Status.DECLINED
                pr.save(update_fields=["status", "updated_at"])
                messages.success(request, "Pickup declined.")
            return redirect(request.path)

        # Complete pickup
        if action == "pickup_complete" and pr_id:
            with transaction.atomic():
                pr = get_object_or_404(
                    PickupRequest.objects.select_for_update(), pk=pr_id, collector=user
                )
                if pr.status != PickupRequest.Status.ACCEPTED:
                    messages.warning(request, "Only accepted requests can be completed.")
                else:
                    pr.status = PickupRequest.Status.COMPLETED
                    pr.save(update_fields=["status", "updated_at"])
                    requester = getattr(pr, "requester", None) or getattr(pr, "household", None)
                    if requester and log_activity_and_update:
                        try:
                            log_activity_and_update(
                                user=requester, product=pr.product, weight_kg=pr.weight_kg
                            )
                        except Exception:
                            pass
                    messages.success(request, "Pickup marked as completed.")
            return redirect(request.path)

        # Deliver marketplace order
        if action == "order_deliver" and order_id:
            order = get_object_or_404(MarketOrder, pk=order_id, collector=user)
            if order.status == MarketOrder.Status.DELIVERED:
                messages.info(request, "Order already delivered.")
            else:
                order.status = MarketOrder.Status.DELIVERED
                order.save(update_fields=["status", "updated_at"])
                messages.success(request, "Order marked as delivered.")
            return redirect(request.path)

        messages.error(request, "Unknown action.")
        return redirect(request.path)

    # -------- Querysets --------
    pending_pickups = (
        PickupRequest.objects
        .filter(collector=user, status=PickupRequest.Status.PENDING)
        .select_related("product", "collector")
        .order_by("-created_at")[:10]
    )

    accepted_pickups = (
        PickupRequest.objects
        .filter(collector=user, status=PickupRequest.Status.ACCEPTED)
        .select_related("product", "collector")
        .order_by("-updated_at")[:10]
    )

    completed_pickups = (
        PickupRequest.objects
        .filter(collector=user, status=PickupRequest.Status.COMPLETED)
        .select_related("product", "collector")
        .order_by("-updated_at")[:10]
    )

    order_pending = (
        MarketOrder.objects
        .filter(collector=user, status=MarketOrder.Status.PENDING)
        .select_related("marketplace", "buyer")
        .order_by("-created_at")[:10]
    )

    order_delivered = (
        MarketOrder.objects
        .filter(collector=user, status=MarketOrder.Status.DELIVERED)
        .select_related("marketplace", "buyer")
        .order_by("-updated_at")[:10]
    )

    # Counts for safe template maths
    pickup_pending_count = pending_pickups.count()
    pickup_accepted_count = accepted_pickups.count()
    pickup_completed_count = completed_pickups.count()
    pickup_total_count = pickup_pending_count + pickup_accepted_count + pickup_completed_count

    order_pending_count = order_pending.count()
    order_delivered_count = order_delivered.count()
    order_total_count = order_pending_count + order_delivered_count

    # Order KPI
    orders_all = MarketOrder.objects.filter(collector=user)
    order_stats = {
        "total_orders": orders_all.count(),
        "pending": order_pending_count,
        "delivered": order_delivered_count,
        "total_revenue": (orders_all.aggregate(s=Sum("total_price"))["s"] or Decimal("0")).quantize(Decimal("0.01")),
    }

    ctx = {
        "stats": _collector_stats(user),

        "pending_pickups": pending_pickups,
        "accepted_pickups": accepted_pickups,
        "completed_pickups": completed_pickups,

        "order_pending": order_pending,
        "order_delivered": order_delivered,
        "order_stats": order_stats,

        # safe counters for tabs/badges
        "counts": {
            "pickup_pending": pickup_pending_count,
            "pickup_accepted": pickup_accepted_count,
            "pickup_completed": pickup_completed_count,
            "pickup_total": pickup_total_count,
            "order_pending": order_pending_count,
            "order_delivered": order_delivered_count,
            "order_total": order_total_count,
        },
    }
    return render(request, "Collector/c_dash.html", ctx)

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
