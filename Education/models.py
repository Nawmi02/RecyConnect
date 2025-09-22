from django.db import models

# Choice options for guide categories
CATEGORY_CHOICES = [
    ("Sorting", "Sorting"),
    ("Environment", "Environment"),
    ("Recycling", "Recycling"),
]

# Tags (you can expand later if needed)
TAG_CHOICES = [
    ("Plastic", "Plastic"),
    ("Paper", "Paper"),
    ("E-waste", "E-waste"),
    ("Metal", "Metal"),
    ("Glass", "Glass"),
    ("Carbon footprint", "Carbon Footprint"),
    ("Green jobs", "Green Jobs"),
    ("Landfill reduction", "Landfill Reduction"),
]


class Learn(models.Model):
    """Model for storing learning guides (Education & Awareness)."""

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField()
    read_time = models.PositiveIntegerField(help_text="Reading time in minutes")
    downloads = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to="guides/", blank=True, null=True)

    # Allow multiple tags
    tags = models.ManyToManyField("Tag", blank=True)

    pdf_file = models.FileField(upload_to="guides/pdfs/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Tag(models.Model):
    """Tags like Plastic, Paper, Green Jobs, etc."""
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name
