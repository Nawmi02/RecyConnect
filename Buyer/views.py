from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import models
import json
from User.models import User, CollectorRating

from Education.views import (
    education_awareness_b,
    view_guide_pdf,
    download_guide_pdf,
    view_video,
    download_video,
)

@login_required(login_url="user:login") 
def dashboard(request):
    return render(request, "Buyer/b_dash.html")

#Community
@login_required(login_url="user:login")
def community(request):
    """
    Community view for Buyer - shows all users except admin and current user
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
    return render(request, "Buyer/b_community.html", context)

@login_required
@require_POST
@csrf_exempt
def rate_collector(request, user_id):
    """
    Allow buyers to rate collectors
    """
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
            'new_avg_rating': float(collector.average_rating),
            'new_ratings_count': collector.ratings_count
        })
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Collector not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
@login_required(login_url="user:login")
def marketplace(request):
    return render(request, "Buyer/b_marketplace.html")

@login_required(login_url="user:login")
def rewards(request):
    return render(request, "Buyer/b_rewards.html")

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

