from django.db import models

class Marketplace(models.Model):
    PRODUCT_TYPES = [
        ('metal', 'Metal'),
        ('plastic', 'Plastic'),
        ('paper', 'Paper'),
        ('ewaste', 'E-waste'),
    ]

    name = models.CharField(max_length=200)
    product_type = models.CharField(
        max_length=20,
        choices=PRODUCT_TYPES,
        default='metal'
    )
    grade = models.IntegerField()
    is_available = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)
    short_description1 = models.CharField(max_length=255, blank=True, null=True)
    short_description2 = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=200)
    weight = models.DecimalField(max_digits=6, decimal_places=2)
    price = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return self.name


