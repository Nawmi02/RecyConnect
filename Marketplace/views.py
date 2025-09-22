from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from .models import Marketplace

class MarketplaceForm(forms.ModelForm):
    class Meta:
        model = Marketplace
        fields = [
            'name', 'product_type', 'grade', 'is_available',
            'description', 'short_description1', 'short_description2',
            'location', 'weight', 'price'
        ]



def marketplace_list(request):
    products = Marketplace.objects.all().order_by('-id')
    return render(request, 'marketplace/marketplace_list.html', {'products': products})



def marketplace_create(request):
    if request.method == "POST":
        form = MarketplaceForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('marketplace_list')
    else:
        form = MarketplaceForm()
    return render(request, 'marketplace/marketplace_form.html', {'form': form})



def marketplace_update(request, id):
    product = get_object_or_404(Marketplace, id=id)
    if request.method == "POST":
        form = MarketplaceForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect('marketplace_list')
    else:
        form = MarketplaceForm(instance=product)
    return render(request, 'marketplace/marketplace_form.html', {'form': form})



def marketplace_delete(request, id):
    product = get_object_or_404(Marketplace, id=id)
    if request.method == "POST":
        product.delete()
        return redirect('marketplace_list')
    return render(request, 'marketplace/marketplace_confirm_delete.html', {'product': product})



def marketplace_detail(request, id):
    product = get_object_or_404(Marketplace, id=id)
    return render(request, 'marketplace/marketplace_detail.html', {'product': product})

