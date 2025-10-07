from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth import update_session_auth_hash
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.db.models import Sum

from django.db import models 
from User.models import User, CollectorRating
from django.contrib.auth import get_user_model
from RecyCon.models import Product
from Rewards.models import Activity
from Pickup.models import PickupRequest
from django.views.decorators.cache import never_cache
from django.db.models import Q


from Education.views import (
    education_awareness_h,
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

User = get_user_model()

def _stats(user):
    total_weight = Activity.objects.filter(user=user).aggregate(s=Sum("weight_kg"))["s"] or Decimal("0")
    return {
        "points": user.points,
        "total_pickups": user.total_pickups,
        "total_weight_kg": Decimal(total_weight).quantize(Decimal("0.001")),
        "total_co2_kg": user.total_co2_saved_kg,
    }

@never_cache
@login_required(login_url="user:login")
def dashboard(request):
    user = request.user
    if getattr(user, "role", None) != "household":
        messages.error(request, "Household dashboard is only for household accounts.")
        return redirect("/")

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
                return redirect("household:dashboard")

            with transaction.atomic():
                product = Product.objects.create(kind=kind, weight=weight, price=price)
                collectors_qs = User.objects.filter(
                    role="collector", is_approved=True).filter(
                         Q(collector_product__iexact=kind) 
                      ).only("id", "collector_product")
                created = 0
                for c in collectors_qs:
                    _, ok = PickupRequest.objects.get_or_create(
                        requester=user, collector=c, product=product,
                        defaults={"status": PickupRequest.Status.PENDING,
                                  "kind": kind, "weight_kg": weight, "price": price}
                    )
                    if ok: created += 1

            if created:
                messages.success(request, f"Pickup request sent to {created} matching collector(s).")
            else:
                messages.warning(request, "No approved collectors found for this product type.")
            return redirect("household:dashboard")

        messages.error(request, "Unknown form submission.")
        return redirect("household:dashboard")

    requests_qs = (
    PickupRequest.objects
    .filter(requester_id=user.id)
    .exclude(status=PickupRequest.Status.DECLINED)   
    .select_related("collector", "product")
    .order_by("-created_at")[:10]
)

    ctx = {"stats": _stats(user), "requests": requests_qs}
    resp = render(request, "Household/h_dash.html", ctx)  
    return _no_cache(resp)

#Community
@login_required(login_url="user:login")
def community(request):
    # Get all users except admin and current user
    users = User.objects.exclude(
        role='admin'
    ).exclude(
        id=request.user.id
    ).select_related()
    
    # Add average rating and ratings count to each user
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
    return render(request, "Household/h_community.html", context)

@login_required
@require_POST
@csrf_exempt
def rate_collector(request, user_id):
    try:
        data = json.loads(request.body)
        rating_value = int(data.get('rating'))
        
        if not rating_value or rating_value < 1 or rating_value > 5:
            return JsonResponse({'success': False, 'error': 'Rating must be between 1 and 5'})
        
        collector = get_object_or_404(User, id=user_id, role='collector')
        
        # Check if user already rated this collector
        existing_rating = CollectorRating.objects.filter(
            rater=request.user,
            collector=collector
        ).first()
        
        if existing_rating:
            existing_rating.stars = rating_value
            existing_rating.save()
            message = "Rating updated successfully!"
        else:
            CollectorRating.objects.create(
                rater=request.user,
                collector=collector,
                stars=rating_value
            )
            message = "Rating submitted successfully!"
        
        # Recompute the collector's rating
        collector.recompute_rating()
        
        return JsonResponse({
            'success': True, 
            'message': message,
            'new_avg_rating': collector.average_rating,
            'new_ratings_count': collector.ratings_count
        })
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Collector not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required(login_url="user:login")
def notifications(request):
    return render(request, "Household/h_notifications.html")

#Profile
@login_required(login_url="user:login")
def profile(request):
    return render(request, "Household/h_profile.html")

#Settings
@login_required(login_url="user:login")
def settings(request):
    user = request.user

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        # -------- Profile Update --------
        if form_type == "profile":
            user.name = request.POST.get("name", "").strip()
            user.phone = request.POST.get("phone", "").strip()
            user.address = request.POST.get("address", "").strip()
            user.map_url = request.POST.get("map_url", "").strip()
            user.facebook = request.POST.get("facebook", "").strip()
            user.instagram = request.POST.get("instagram", "").strip()
            user.twitter = request.POST.get("twitter", "").strip()

            # File upload (optional)
            if request.FILES.get("profile_image"):
                user.profile_image = request.FILES["profile_image"]

            try:
                user.full_clean(exclude=["password"]) 
                user.save()
                messages.success(request, "Profile updated successfully.")
                return redirect("household:settings")
            except ValidationError as e:
    
                for field, msgs in e.message_dict.items():
                    for msg in msgs:
                        messages.error(request, f"{field}: {msg}")

        # -------- Password Change --------
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
                # keep the user logged in after password change
                update_session_auth_hash(request, user)
                messages.success(request, "Password updated successfully.")
                return redirect("household:settings")

        else:
            messages.error(request, "Unknown form submission.")

    return render(request, "Household/h_settings.html")

@login_required(login_url="user:login")
def history(request):
    return render(request, "Household/h_history.html")

