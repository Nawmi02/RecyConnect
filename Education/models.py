from django.db import models


class Guide(models.Model):
    title = models.CharField(max_length=200)  # e.g., "Complete Waste Segregation Guide"
    category = models.CharField(max_length=50, blank=True, null=True)  # e.g., Sorting, Environment
    description = models.TextField(blank=True, null=True)  # optional details
    read_time = models.PositiveIntegerField(help_text="Reading time in minutes")  # e.g., 10
    downloads = models.PositiveIntegerField(default=0)  # how many times downloaded/viewed
    created_at = models.DateTimeField(auto_now_add=True)  # record creation time

    def __str__(self):
        return self.title

    def short_description(self):
        """Return a shortened version of description for previews."""
        return (self.description[:100] + "...") if self.description and len(self.description) > 100 else self.description
