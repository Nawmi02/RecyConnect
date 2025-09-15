from django.db import models
from django.contrib.auth.models import AbstractBaseUser

class User(AbstractBaseUser):
    ROLE_CHOICES = [
        ("household", "Household"),
        ("collector", "Collector"),
        ("recycler", "Recycler"),
        ("buyer", "Buyer"),
    ]

    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)


    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["role"]

    def __str__(self):
        return f"{self.email} ({self.role})"
