from django.db import models


class Learn(models.Model):
    title = models.CharField(max_length=200)  
    category = models.CharField(max_length=50, blank=True, null=True)  
    description = models.TextField(blank=True, null=True)
    read_time = models.PositiveIntegerField(help_text="Reading time in minutes") 
    downloads = models.PositiveIntegerField(default=0)  
    created_at = models.DateTimeField(auto_now_add=True) 
    def _str_(self):
        return self.title
