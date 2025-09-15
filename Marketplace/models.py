from django.db import models

class Marketplace(models.Model):
    name = models.CharField(max_length=200)
    grade = models.IntegerField()
    is_available = models.BooleanField(default=True)
    description = models.TextField(blank=True , null=True)
    location = models.CharField(max_length=200)
    weight = models.DecimalField(max_digits=6 , decimal_places=2)
    price = models.DecimalField(max_digits=6 , decimal_places=2)


    def __str__(self):
        return self.name


