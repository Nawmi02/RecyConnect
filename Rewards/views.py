from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from .models import Reward



class RewardForm(forms.ModelForm):
    class Meta:
        model = Reward
        fields = [
            'title', 'points_required', 'description',
            'is_active', 'expiry_date'
        ]



def reward_list(request):
    rewards = Reward.objects.all().order_by('-id')
    return render(request, 'reward/reward_list.html', {'rewards': rewards})



def reward_create(request):
    if request.method == "POST":
        form = RewardForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('reward_list')
    else:
        form = RewardForm()
    return render(request, 'reward/reward_form.html', {'form': form})



def reward_update(request, id):
    reward = get_object_or_404(Reward, id=id)
    if request.method == "POST":
        form = RewardForm(request.POST, instance=reward)
        if form.is_valid():
            form.save()
            return redirect('reward_list')
    else:
        form = RewardForm(instance=reward)
    return render(request, 'reward/reward_form.html', {'form': form})



def reward_delete(request, id):
    reward = get_object_or_404(Reward, id=id)
    if request.method == "POST":
        reward.delete()
        return redirect('reward_list')
    return render(request, 'reward/reward_confirm_delete.html', {'reward': reward})



def reward_detail(request, id):
    reward = get_object_or_404(Reward, id=id)
    return render(request, 'reward/reward_detail.html', {'reward': reward})
