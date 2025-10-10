from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Sum, F
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache

from RecyCon.models import Product
from Pickup.models import PickupRequest
from Marketplace.models import MarketOrder
from Rewards.models import Activity
from User.models import User as UserModel, CollectorRating
from Education.views import (
    education_awareness_c,
    view_guide_pdf,
    download_guide_pdf,
    view_video,
    download_video,
)

User = get_user_model()


def _no_cache(resp):
    resp["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp["Pragma"] = "no-cache"
    resp["Expires"] = "0"
    resp["Vary"] = resp.get("Vary", "")
    if "cookie" not in resp["Vary"].lower():
        resp["Vary"] = (resp["Vary"] + ", Cookie").strip(", ")
    return resp


def _co2_for_kind(kind: str) -> Decimal:
    return Product.CO2_PER_KG.get(kind, Decimal("0.0"))


def _collector_stats(user):
    completed = PickupRequest.objects.filter(
        collector=user, status=PickupRequest.Status.COMPLETED
    )
    total_weight = (
        completed.aggregate(s=Sum("weight_kg"))["s"] or Decimal("0")
    ).quantize(Decimal("0.001"))

    est_co2 = Decimal("0.000")
    for pr in completed.only("kind", "weight_kg"):
        est_co2 += (Decimal(pr.weight_kg or 0) * _co2_for_kind(str(pr.kind))).quantize(
            Decimal("0.001")
        )

    return {
        "points": user.points,
        "total_pickups": completed.count(),
        "total_weight_kg": total_weight,
        "total_co2_kg": est_co2.quantize(Decimal("0.001")),
    }


# --- Rewards helper that matches your service signature ---
def _award_activity_or_fallback(*, user, product, weight_kg: Decimal):
    """
    Try Rewards.services.log_activity_and_update(user, product, weight_kg).
    If the service isn't importable, create an Activity and update user tallies.
    """
    try:
        from Rewards.services import log_activity_and_update as svc
    except Exception:
        svc = None

    if svc:
        # Service handles: Activity, totals/CO2, points, badges (atomic inside)
        return svc(user=user, product=product, weight_kg=weight_kg)

    # ---- fallback consistent with your Activity model ----
    from Rewards.models import Activity as ActivityModel

    act = ActivityModel.objects.create(
        user=user,
        product=product,
        weight_kg=weight_kg,
        # co2_saved_kg auto-computed in Activity.save()
    )
    # After save(), co2_saved_kg is ready. Update user with F-expressions.
    user.__class__.objects.filter(pk=user.pk).update(
        total_co2_saved_kg=F("total_co2_saved_kg") + act.co2_saved_kg,
        total_pickups=F("total_pickups") + 1,
        # mirror service rule (int(co2) * 2):
        points=F("points") + (int(act.co2_saved_kg) * 2),
    )
    return act


@never_cache
@login_required(login_url="user:login")
def dashboard(request):
    user = request.user
    if getattr(user, "role", None) != "collector":
        messages.error(request, "Collector dashboard is only for Collector accounts.")
        return redirect("/")

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()

        if action in {"pickup_accept", "pickup_decline", "pickup_complete"}:
            pid = request.POST.get("pickup_id")
            pr = get_object_or_404(PickupRequest, id=pid, collector_id=user.id)

            if action == "pickup_accept":
                with transaction.atomic():
                    pr.status = PickupRequest.Status.ACCEPTED
                    pr.save(update_fields=["status", "updated_at"])
                    (
                        PickupRequest.objects.filter(
                            product=pr.product,
                            requester=pr.requester,
                            status=PickupRequest.Status.PENDING,
                        )
                        .exclude(collector=user)
                        .update(status=PickupRequest.Status.DECLINED)
                    )
                messages.success(request, "Request accepted.")
                return redirect(request.path)

            elif action == "pickup_decline":
                pr.status = PickupRequest.Status.DECLINED
                pr.save(update_fields=["status", "updated_at"])
                messages.info(request, "Request declined.")
                return redirect(request.path)

            elif action == "pickup_complete":
                with transaction.atomic():
                    pr.status = PickupRequest.Status.COMPLETED
                    pr.save(update_fields=["status", "updated_at"])

                    # Requester (household/buyer) earns
                    _award_activity_or_fallback(
                        user=pr.requester, product=pr.product, weight_kg=pr.weight_kg
                    )
                    # Collector also earns
                    _award_activity_or_fallback(
                        user=pr.collector, product=pr.product, weight_kg=pr.weight_kg
                    )

                messages.success(request, "Pickup marked as completed.")
                return redirect(request.path)

        elif action == "order_deliver":
            order_id = request.POST.get("order_id")
            order = get_object_or_404(MarketOrder, pk=order_id, collector_id=user.id)
            if order.status != MarketOrder.Status.DELIVERED:
                order.status = MarketOrder.Status.DELIVERED
                order.save(update_fields=["status", "updated_at"])
                messages.success(request, "Order marked as delivered.")
            else:
                messages.info(request, "Order already delivered.")
            return redirect(request.path)

        messages.error(request, "Unknown action.")
        return redirect(request.path)

    # ---- GET: lists ----
    qs_pending = (
        PickupRequest.objects.filter(
            collector_id=user.id, status=PickupRequest.Status.PENDING
        )
        .select_related("requester", "product")
        .order_by("-created_at")
    )
    qs_accepted = (
        PickupRequest.objects.filter(
            collector_id=user.id, status=PickupRequest.Status.ACCEPTED
        )
        .select_related("requester", "product")
        .order_by("-updated_at")
    )
    qs_completed = (
        PickupRequest.objects.filter(
            collector_id=user.id, status=PickupRequest.Status.COMPLETED
        )
        .select_related("requester", "product")
        .order_by("-updated_at")
    )

    pending_pickups = list(qs_pending[:20])
    accepted_pickups = list(qs_accepted[:20])
    completed_pickups = list(qs_completed[:20])

    order_pending = (
        MarketOrder.objects.filter(
            collector_id=user.id, status=MarketOrder.Status.PENDING
        )
        .select_related("marketplace", "buyer")
        .order_by("-created_at")[:10]
    )
    order_delivered = (
        MarketOrder.objects.filter(
            collector_id=user.id, status=MarketOrder.Status.DELIVERED
        )
        .select_related("marketplace", "buyer")
        .order_by("-updated_at")[:10]
    )

    order_stats = {
        "total_orders": MarketOrder.objects.filter(collector_id=user.id).count(),
        "pending": MarketOrder.objects.filter(
            collector_id=user.id, status=MarketOrder.Status.PENDING
        ).count(),
        "delivered": MarketOrder.objects.filter(
            collector_id=user.id, status=MarketOrder.Status.DELIVERED
        ).count(),
        "total_revenue": (
            MarketOrder.objects.filter(collector_id=user.id).aggregate(
                s=Sum("total_price")
            )["s"]
            or Decimal("0")
        ).quantize(Decimal("0.01")),
    }

    ctx = {
        "stats": _collector_stats(user),
        "pending_pickups": pending_pickups,
        "accepted_pickups": accepted_pickups,
        "completed_pickups": completed_pickups,
        "order_pending": order_pending,
        "order_delivered": order_delivered,
        "order_stats": order_stats,
        "counts": {
            "pickup_pending": qs_pending.count(),
            "pickup_accepted": qs_accepted.count(),
            "pickup_completed": qs_completed.count(),
            "pickup_total": qs_pending.count()
            + qs_accepted.count()
            + qs_completed.count(),
            "order_pending": order_stats["pending"],
            "order_delivered": order_stats["delivered"],
            "order_total": order_stats["pending"] + order_stats["delivered"],
        },
    }
    resp = render(request, "Collector/c_dash.html", ctx)
    return _no_cache(resp)


#Community
@login_required(login_url="user:login")
def community(request):
    """
    Community view for Collector - shows all users except admin and current user
    """
    users = User.objects.exclude(role='admin').exclude(id=request.user.id).select_related()

    # add rating info for collectors
    for u in users:
        if getattr(u, "role", "") == 'collector':
            ratings = CollectorRating.objects.filter(collector=u)
            if ratings.exists():
                u.average_rating = ratings.aggregate(avg=models.Avg('stars'))['avg']
                u.ratings_count = ratings.count()
            else:
                u.average_rating = 0.0
                u.ratings_count = 0

    return render(request, "Collector/c_community.html", {"users": users})


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

        # Profile update
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

        # Password change
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

    context = {"product_choices": getattr(User, "ProductKind", None).choices if hasattr(User, "ProductKind") else []}
    return render(request, "Collector/c_settings.html", context)


