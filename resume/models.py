from django.db import models
import json


class Resume(models.Model):
    """Stores an uploaded resume file along with its parsed analysis data."""
    file = models.FileField(upload_to='resumes/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    original_filename = models.CharField(max_length=255, default='')
    raw_text = models.TextField(blank=True, default='')
    parsed_data = models.JSONField(default=dict, blank=True)
    ats_score = models.IntegerField(default=0)
    ats_breakdown = models.JSONField(default=dict, blank=True)
    job_matches = models.JSONField(default=list, blank=True)
    recommendations = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Resume #{self.pk} — {self.original_filename}"
