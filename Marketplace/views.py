from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, F
from django.http import HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404, redirect
from decimal import Decimal, InvalidOperation

from .models import Marketplace, MarketTag

ADD_ALLOWED_ROLES = {"collector"}

def _user_can_add(user) -> bool:
    """Only approved Collector may add products."""
    return (
        user.is_authenticated
        and user.role in ADD_ALLOWED_ROLES
        and getattr(user, "is_approved", False)
    )

def _template_for_role(role: str) -> str:
    """Return template path based on role."""
    if role == "collector":
        return "Collector/c_marketplace.html"
    if role in ("buyer", "recycler"):
        return "Buyer/b_marketplace.html"
    if role == "household":
        return "Household/h_marketplace.html"
    return "Admin/ad_marketplace.html"


@login_required
def marketplace_page(request, role: str):
    template = _template_for_role(role)

   
    if request.method == "POST":
        if not _user_can_add(request.user):
            messages.error(request, "Only approved Collector can add products.")
            return redirect(request.path)

        name         = (request.POST.get("name") or "").strip()
        product_type = (request.POST.get("product_type") or "").strip()
        grade        = request.POST.get("grade")
        is_available = request.POST.get("is_available") in {"1", "true", "on"}
        description  = (request.POST.get("description") or "").strip()
        location     = (request.POST.get("location") or "").strip()
        weight       = request.POST.get("weight")
        price        = request.POST.get("price")
        tag_codes    = request.POST.getlist("tags")
        img          = request.FILES.get("product_image")

        errors = {}

        if not name:
            errors["name"] = "Name is required."

        valid_types = {c.value for c in Marketplace.ProductType}
        if product_type not in valid_types:
            errors["product_type"] = "Invalid product type."

        try:
            grade_val = int(grade)
        except (TypeError, ValueError):
            errors["grade"] = "Grade must be an integer."

        try:
            weight_val = float(weight)
            if weight_val <= 0:
                raise ValueError
        except (TypeError, ValueError):
            errors["weight"] = "Weight must be > 0."

        try:
            price_val = float(price)
            if price_val < 0:
                raise ValueError
        except (TypeError, ValueError):
            errors["price"] = "Price must be ≥ 0."

        if errors:
            for f, msg in errors.items():
                messages.error(request, f"{f}: {msg}")
            return redirect(request.path)

        item = Marketplace(
            seller=request.user,
            name=name,
            product_type=product_type,
            grade=grade_val,
            is_available=is_available,
            description=description,
            location=location,
            weight=weight_val,
            price=price_val,
            product_image=img,
        )
        item.full_clean()  
        item.save()

        if tag_codes:
            tags = list(MarketTag.objects.filter(name__in=tag_codes))
            item.tags.set(tags)

        messages.success(request, "Product listed successfully.")
        return redirect("marketplace:detail", pk=item.pk)

    # LIST (filters + ordering) 
    q       = (request.GET.get("q") or "").strip()
    ptype   = (request.GET.get("type") or "").strip()
    minrate = (request.GET.get("min_rating") or "").strip()
    order   = (request.GET.get("order") or "").strip()  

    # Admin can see all items
    qs = Marketplace.objects.with_seller_info()
    if role != "admin":
        qs = qs.filter(is_available=True)

    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(location__icontains=q)
        )

    valid_types = {c.value for c in Marketplace.ProductType}
    if ptype and ptype in valid_types:
        qs = qs.filter(product_type=ptype)

    if minrate:
        try:
            qs = qs.filter(seller_average_rating_gte=float(minrate))
        except ValueError:
            pass

    if order == "price_asc":
        qs = qs.order_by("price")
    elif order == "price_desc":
        qs = qs.order_by("-price")
    else:
        qs = qs.order_by("-id")

    context = {
        "items": qs,
        "role": role,
        "can_add": _user_can_add(request.user),
        "product_types": Marketplace.ProductType.choices,
        "tag_choices": MarketTag.Choices.choices,
        "query": q, "ptype": ptype, "min_rating": minrate, "order": order,
    }
    return render(request, template, context)


@login_required
def marketplace_detail(request, pk: int):
    """Render the detail widget/page for a product."""
    item = get_object_or_404(Marketplace.objects.with_seller_info(), pk=pk)
    return render(request, "Marketplace/detail_widget.html", {"item": item})


@login_required
@transaction.atomic
def marketplace_buy(request, pk: int):
    """
    Buy Now (COD only):
    - Expect POST with 'weight' (Decimal string, e.g. "2.50")
    - Validate availability
    - Calculate total using Decimal arithmetic
    - Decrease stock atomically
    - Mark item sold out when stock hits zero
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    item = get_object_or_404(Marketplace, pk=pk, is_available=True)

    # Parse requested weight as Decimal (never float)
    raw_weight = (request.POST.get("weight") or "0").strip()
    try:
        req_weight = Decimal(raw_weight).quantize(Decimal("0.01"))
        if req_weight <= Decimal("0"):
            raise InvalidOperation
    except (InvalidOperation, TypeError, ValueError):
        messages.error(request, "Enter a valid weight (> 0).")
        return redirect("marketplace:detail", pk=pk)

    # Recheck stock inside the transaction
    item.refresh_from_db()

    if item.weight < req_weight:
        messages.error(request, f"Only {item.weight} kg available.")
        return redirect("marketplace:detail", pk=pk)

    # All-Decimal total price
    total_price = (item.price * req_weight).quantize(Decimal("0.01"))

    # Decrease stock atomically
    Marketplace.objects.filter(pk=item.pk).update(weight=F("weight") - req_weight)
    item.refresh_from_db()

    # Mark sold out if depleted
    if item.weight <= Decimal("0"):
        item.is_available = False
        item.save(update_fields=["is_available"])

    messages.success(
        request,
        (
            f"Your order has been placed successfully for {req_weight} kg. "
            f"Total amount: {total_price:.2f} BDT.\n\n"
            "Note: You cannot cancel after placing the order.\n"
            "Please pay cash on delivery and contact the Collector for more information. "
            "You can find his/her contact details from the Community section."
        )
    )
    return redirect("marketplace:detail", pk=pk)

