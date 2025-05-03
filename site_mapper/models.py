from django.db import models
import uuid as uuid_lib

class Link(models.Model):
    """
    Represents a link (URL) found during site mapping.
    Can be a web page, PDF, or other document type.
    """
    TYPE_CHOICES = [
        ('page', 'Web Page'),
        ('pdf', 'PDF Document'),
        ('docx', 'Word Document'),
        ('xlsx', 'Excel Document'),
        ('other', 'Other'),
        ('broken', 'Broken Link'),  # Ensure 'broken' is included in validation
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid_lib.uuid4, editable=False)
    job = models.ForeignKey('SiteMapJob', on_delete=models.CASCADE, related_name='links', null=True)
    url = models.URLField(max_length=500)
    link_text = models.TextField(null=True, blank=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='page')
    file_path = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    depth = models.IntegerField(default=0, help_text="Click depth level from starting URL")
    starting_url = models.URLField(max_length=500, null=True, blank=True, help_text="The root URL this link belongs to")
    
    def __str__(self):
        return f"{self.url} (Depth {self.depth})"

class SiteMapJob(models.Model):
    """Model for site mapping jobs."""
    
    # Job statuses
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    # Basic job information
    name = models.CharField(max_length=255)
    start_urls = models.TextField()
    output_file = models.CharField(max_length=255, default='site_map.json')
    
    # Progress tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_links = models.IntegerField(default=0)
    processed_links = models.IntegerField(default=0)
    max_depth = models.IntegerField(default=3)
    current_depth = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
class SiteFilter(models.Model):
    url = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['url']
    
    def __str__(self):
        return self.url