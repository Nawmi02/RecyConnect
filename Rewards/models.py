from django.db import models

class Reward(models.Model):
    name = models.CharField(max_length=200)                     
    description = models.TextField(blank=True, null=True)       
    image = models.ImageField(upload_to="rewards/", blank=True, null=True) 
    points_required = models.IntegerField()
    redeemed_at = models.DateTimeField(blank=True, null=True)                      

    def __str__(self):
        return self.name
