from django.db import models

class MarketTag(models.Model):
    class Choices(models.TextChoices):
        CLEAN                 = "clean",                 "Clean"
        DRY                   = "dry",                   "Dry"
        SORTED                = "sorted",                "Sorted"
        NO_FOREIGN_MATERIALS  = "no_foreign_materials",  "No foreign materials"
        NO_BATTERY            = "no_battery",            "No battery"
        NO_LIQUID             = "no_liquid",             "No liquid"
        BROKEN                = "broken",                "Broken"
        NONFUNCTIONAL         = "nonfunctional",         "Nonfunctional"
        METAL_ONLY            = "metal_only",            "Metal only"

    name = models.CharField(
        max_length=40,
        choices=Choices.choices,
        unique=True,
        db_index=True,
        help_text="Quality/handling tags for marketplace items."
    )

    def _str_(self):
        return self.get_name_display()


class Marketplace(models.Model):
    PRODUCT_TYPES = [
        ('metal', 'Metal'),
        ('plastic', 'Plastic'),
        ('paper', 'Paper'),
        ('ewaste', 'E-waste'),
    ]

    name = models.CharField(max_length=200)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES)
    grade = models.IntegerField()
    is_available = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=200)
    weight = models.DecimalField(max_digits=6, decimal_places=2)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    tags = models.ManyToManyField(MarketTag, blank=True, related_name="items")

    def _str_(self):
        return self.name