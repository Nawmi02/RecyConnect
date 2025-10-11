from django.db import models
from django.core.exceptions import ValidationError


class Tag(models.Model):
    """Diff type of choices in learn"""
    class Choices(models.TextChoices):
        ENVIRONMENT         = "environment",         "Environment"
        RECYCLE             = "recycle",             "Recycle"
        POLLUTION           = "pollution",           "Pollution"
        PLASTIC             = "plastic",             "Plastic"
        PAPER               = "paper",               "Paper"
        E_WASTE             = "e_waste",             "E-waste"
        METAL               = "metal",               "Metal"
        GLASS               = "glass",               "Glass"
        CARBON_FOOTPRINT    = "carbon_footprint",    "Carbon Footprint"
        GREEN_JOBS          = "green_jobs",          "Green Jobs"
        LANDFILL_REDUCTION  = "landfill_reduction",  "Landfill Reduction"

    name = models.CharField(
        max_length=50,
        choices=Choices.choices,
        unique=True,
        db_index=True,
        help_text="Select a predefined tag (e.g., Plastic, Recycle, Pollution).",
    )

    def __str__(self): 
        return self.get_name_display()


class Learn(models.Model):
    class Category(models.TextChoices):
        GUIDELINE  = "guideline",  "Guideline"
        ARTICLE    = "article",    "Article"
        VIDEO      = "video",      "Video"
        QUICK_TEXT = "quick_text", "Quick Text"

    title       = models.CharField(max_length=200,null=True)
    topic       = models.CharField(max_length=120, null=True )
    category    = models.CharField(max_length=20, choices=Category.choices)
    description = models.TextField()
    read_time   = models.PositiveIntegerField(help_text="Reading time in minutes")
    downloads   = models.PositiveIntegerField(default=0)

    image       = models.ImageField(upload_to="guides/covers/", blank=True, null=True)
    pdf_file    = models.FileField(upload_to="guides/pdfs/",   blank=True, null=True)
    video_file  = models.FileField(upload_to="guides/videos/", blank=True, null=True)
    quick_text  = models.TextField(blank=True, null=True)

    tags        = models.ManyToManyField(Tag, blank=True, related_name="guides")

    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.title} [{self.get_category_display()}]"

    def clean(self):
        errors = {}
        cat = self.category

        if cat in (self.Category.GUIDELINE, self.Category.ARTICLE):
            if not self.pdf_file:
                errors["pdf_file"] = "pdf needed"
            if self.video_file:
                errors["video_file"] = "won't have video"
            if self.quick_text:
                errors["quick_text"] = "won't have quick text"

        elif cat == self.Category.VIDEO:
            if not self.video_file:
                errors["video_file"] = "file needed in video category"
            if self.pdf_file:
                errors["pdf_file"] = "no pdf in video"
            if self.quick_text:
                errors["quick_text"] = "no quick text in video"

        elif cat == self.Category.QUICK_TEXT:
            if not (self.quick_text and self.quick_text.strip()):
                errors["quick_text"] = "text needed in Quick Text "
            if self.pdf_file:
                errors["pdf_file"] = "no pdf in qick text"
            if self.video_file:
                errors["video_file"] = "no video in quick text"

        if errors:
            raise ValidationError(errors)