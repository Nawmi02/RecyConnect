from decimal import Decimal, InvalidOperation
import json
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum, Avg, Count
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.db import models
from django.db.models import Q,F, ExpressionWrapper,DecimalField, Sum

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

def _no_cache(resp):
    resp["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp["Pragma"] = "no-cache"
    resp["Expires"] = "0"
    resp["Vary"] = resp.get("Vary", "")
    if "cookie" not in resp["Vary"].lower():
        resp["Vary"] = (resp["Vary"] + ", Cookie").strip(", ")
    return resp

def _to_decimal(val, default="0"):
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val or default))


def _buyer_stats(user):
    qs = PickupRequest.objects.filter(requester_id=user.id)

    pending   = qs.filter(status=PickupRequest.Status.PENDING).count()
    accepted  = qs.filter(status=PickupRequest.Status.ACCEPTED).count()
    completed = qs.filter(status=PickupRequest.Status.COMPLETED).count()
    declined  = qs.filter(status=PickupRequest.Status.DECLINED).count()

 
    total_pickups = 0 +  completed

    weight_completed = (
        qs.filter(status=PickupRequest.Status.COMPLETED)
          .aggregate(s=Sum("weight_kg"))["s"] or Decimal("0")
    )
    weight_completed = Decimal(str(weight_completed)).quantize(Decimal("0.001"))

    total_expr = ExpressionWrapper(
        F("price") * F("weight_kg"),
        output_field=DecimalField(max_digits=12, decimal_places=2)
    )
    earnings_val = (
        qs.filter(status=PickupRequest.Status.COMPLETED)
          .aggregate(s=Sum(total_expr))["s"] or Decimal("0")
    )
    earnings = Decimal(str(earnings_val)).quantize(Decimal("0.01"))

    return {
        "points": user.points,
        "total_pickups": total_pickups,
        "total_weight_kg": weight_completed,
        "total_co2_kg": user.total_co2_saved_kg,

        "pending_pickups": pending,
        "accepted_pickups": accepted,
        "completed_pickups": completed,
        "declined_pickups": declined,
        "total_earnings": earnings,  
    }

#Dashboard
@never_cache
@login_required(login_url="user:login")
def dashboard(request):
    user = request.user
    user.refresh_from_db(fields=["points", "total_pickups", "total_co2_saved_kg"])

    if getattr(user, "role", None) != "buyer":
        messages.error(request, "Buyer dashboard is only for Buyer accounts.")
        return redirect("/")

    #  Create Pickup (POST) 
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "request_pickup":
            kind = (request.POST.get("kind") or "").strip()
            wraw = (request.POST.get("weight") or "0").strip()
            praw = (request.POST.get("price") or "0").strip()

            try:
                weight = Decimal(wraw)
                price = Decimal(praw)
                if weight <= 0 or price < 0:
                    raise InvalidOperation
            except Exception:
                messages.error(request, "Please provide valid numbers for weight and price.")
                return redirect("buyer:dashboard")  
            with transaction.atomic():
                product = Product.objects.create(kind=kind, weight=weight, price=price)

            collectors_qs = User.objects.filter(
            role="collector",
            is_approved=True
            ).filter(
            Q(collector_product__iexact=kind)
            ).only("id", "collector_product")

            #  PickupRequest
            created = 0
            for c in collectors_qs:
                    _, ok = PickupRequest.objects.get_or_create(
                        requester=user,
                        collector=c,
                        product=product,
                        defaults={
                            "status": PickupRequest.Status.PENDING,
                            "kind": kind,
                            "weight_kg": weight,
                            "price": price,
                        },
                    )
                    if ok:
                        created += 1

            if created:
                messages.success(request, f"Pickup request sent to {created} matching collector(s).")
            else:
                messages.warning(request, "No approved collectors found for this product type.")
            return redirect("buyer:dashboard")       

        messages.error(request, "Unknown form submission.")
        return redirect("buyer:dashboard")
 
    pickup_qs = (
       PickupRequest.objects
       .filter(requester_id=user.id)
       .exclude(status=PickupRequest.Status.DECLINED)   
       .select_related("collector", "product")
    .order_by("-created_at")[:10]
   )

    orders_qs = (MarketOrder.objects
                 .filter(buyer_id=user.id)
                 .select_related("collector", "marketplace")
                 .order_by("-created_at")[:10])

    orders_all = MarketOrder.objects.filter(buyer_id=user.id)
    order_stats = {
        "total_orders": orders_all.count(),
        "pending_orders": orders_all.filter(status=MarketOrder.Status.PENDING).count(),
        "delivered_orders": orders_all.filter(status=MarketOrder.Status.DELIVERED).count(),
        "total_spent": (orders_all.aggregate(s=Sum("total_price"))["s"] or Decimal("0")).quantize(Decimal("0.01")),
    }

    ctx = {
        "stats": _buyer_stats(user),
        "requests": pickup_qs,
        "orders": orders_qs,
        "order_stats": order_stats,
    }
    resp = render(request, "Buyer/b_dash.html", ctx)
    return _no_cache(resp)

#Community
@login_required(login_url="user:login")
def community(request):
    users = User.objects.exclude(role="admin").exclude(id=request.user.id)
    for u in users:
        if u.role == "collector":
            agg = CollectorRating.objects.filter(collector=u).aggregate(avg=Avg("stars"), cnt=Count("id"))
            u.average_rating = float(agg.get("avg") or 0.0)
            u.ratings_count = int(agg.get("cnt") or 0)
    return render(request, "Buyer/b_community.html", {"users": users})


@login_required(login_url="user:login")
@require_POST
@csrf_exempt
def rate_collector(request, user_id):
    try:
        data = json.loads(request.body or "{}")
        rating_value = int(data.get("rating"))
        if rating_value < 1 or rating_value > 5:
            return JsonResponse({"success": False, "error": "Rating must be between 1 and 5"})
        collector = get_object_or_404(User, id=user_id, role="collector")
        existing = CollectorRating.objects.filter(rater=request.user, collector=collector).first()
        if existing:
            existing.stars = rating_value
            existing.save()
            msg = "Rating updated successfully!"
        else:
            CollectorRating.objects.create(rater=request.user, collector=collector, stars=rating_value)
            msg = "Rating submitted successfully!"
        collector.recompute_rating()
        return JsonResponse({"success": True, "message": msg,
                             "new_avg_rating": float(collector.average_rating),
                             "new_ratings_count": collector.ratings_count})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})

#Profile
@login_required(login_url="user:login")
def profile(request):
    return render(request, "Buyer/b_profile.html")

#Settings
@login_required(login_url="user:login")
def settings(request):
    user = request.user
    if request.method == "POST":
        form_type = request.POST.get("form_type")
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


